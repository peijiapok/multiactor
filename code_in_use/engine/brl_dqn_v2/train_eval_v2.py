from __future__ import annotations

import json
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import torch


WORKSPACE = Path("/home/jia/thirfty_death_BRL_DQN")
SOURCE = Path("/home/jia/thirftydeath")
for path in (WORKSPACE, SOURCE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from brl_dqn_v2.brl_wrapper_v2 import QGapConfig, QGapSoftmaxWrapper  # noqa: E402
from brl_dqn_v2.dqn_agent_v2 import DQNV2Agent, DQNV2Config  # noqa: E402
from brl_dqn_v2.env_action_wrapper import BRLDQNPrimitiveEnv, N_PRIMITIVE_ACTIONS, PRIMITIVE_NORMAL_REQUEST  # noqa: E402
from brl_dqn_v2.obs_adapter_v2 import STATE_DIM_V2, batch_action_mask, batch_flatten_obs_v2  # noqa: E402
from brl_dqn_v2.reward_v2 import LagrangianRewardConfig, compute_lagrangian_reward  # noqa: E402
from e12_queue_env import QueueEnvConfig  # noqa: E402
from run_experiments import make_scenario_config  # noqa: E402


@dataclass
class V2RunConfig:
    scenario: str = "metro_caltech_sce"
    seed: int = 3200
    n_cars: int = 80
    episode_hours: int = 72
    forecast_horizon: int = 24
    n_slots_home: int = 40
    n_slots_work: int = 5
    n_slots_public: int = 5
    max_queue_wait_steps: int = 4
    train_episodes: int = 12
    hidden_dim: int = 64
    lr: float = 3.0e-4
    gamma: float = 0.99
    batch_size: int = 32
    min_buffer_size: int = 32
    epsilon_decay: float = 0.80


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def make_env_config(cfg: V2RunConfig, seed: int | None = None) -> QueueEnvConfig:
    base = make_scenario_config(
        seed=cfg.seed if seed is None else seed,
        scenario_name=cfg.scenario,
        episode_hours=cfg.episode_hours,
        forecast_horizon=cfg.forecast_horizon,
    )
    base.n_cars = cfg.n_cars
    qcfg = QueueEnvConfig(**vars(base))
    qcfg.n_slots_home = cfg.n_slots_home
    qcfg.n_slots_work = cfg.n_slots_work
    qcfg.n_slots_public = cfg.n_slots_public
    qcfg.max_queue_wait_steps = cfg.max_queue_wait_steps
    qcfg.prevent_nonreserve_charging_above_target = False
    return qcfg


def make_env(cfg: V2RunConfig, seed: int | None = None) -> BRLDQNPrimitiveEnv:
    return BRLDQNPrimitiveEnv(make_env_config(cfg, seed=seed))


def _cheap_mask(prices: np.ndarray, tolerance: float = 1.05) -> np.ndarray:
    return prices <= float(prices.min()) * tolerance


def _cheap_run_position(is_cheap: np.ndarray, t: int) -> tuple[int, int] | None:
    if not bool(is_cheap[t]):
        return None
    start = t
    while start > 0 and bool(is_cheap[start - 1]):
        start -= 1
    end = t
    while end + 1 < len(is_cheap) and bool(is_cheap[end + 1]):
        end += 1
    return t - start, end - start + 1


def _reserve_need(env: BRLDQNPrimitiveEnv, obs: dict[str, object]) -> np.ndarray:
    soc = np.asarray(obs["soc"], dtype=float)
    theta = np.asarray(obs["anxiety_thresholds"], dtype=float)
    return soc < (theta + float(getattr(env.config, "reserve_margin", 0.12)))


def _target_need(env: BRLDQNPrimitiveEnv, obs: dict[str, object]) -> np.ndarray:
    return np.asarray(obs["soc"], dtype=float) < float(getattr(env.config, "target_soc", 0.90))


def _location_type(env: BRLDQNPrimitiveEnv, agent_idx: int) -> str | None:
    if hasattr(env, "_charge_location_type_for_agent"):
        return env._charge_location_type_for_agent(int(agent_idx))
    loc = int(np.asarray(env.locations)[agent_idx])
    if loc == 1 and bool(env.has_work_access[agent_idx]):
        return "work"
    if loc == 0 and bool(env.has_home_access[agent_idx]):
        return "home"
    if bool(env.has_public_access[agent_idx]) and bool(env.public_fallback[agent_idx]):
        return "public"
    return None


def _least_laxity_charge(env: BRLDQNPrimitiveEnv, obs: dict[str, object], t: int, available: np.ndarray) -> np.ndarray:
    soc = np.asarray(obs["soc"], dtype=float)
    charge = np.zeros(env.n_cars, dtype=bool)
    planned = getattr(env, "mandatory_trip_schedule", None)
    if planned is None:
        return available & _reserve_need(env, obs)

    laxity = np.full(env.n_cars, np.inf, dtype=float)
    for i in range(env.n_cars):
        if not available[i] or (hasattr(env, "agent_queuing") and bool(env.agent_queuing[i])):
            continue
        future = np.asarray(planned[i, t : env.config.episode_hours], dtype=float)
        nz = np.flatnonzero(future > 0.0)
        if nz.size == 0:
            laxity[i] = 1.0e6 + max(0.0, float(getattr(env.config, "target_soc", 0.90)) - soc[i])
            continue
        hours_to_deadline = float(nz[0])
        trip_kwh = float(future[nz[0]]) * 0.18
        usable_kwh = max(0.0, soc[i] - float(env.config.soc_min)) * float(env.config.bcap_kwh)
        deficit_kwh = max(0.0, trip_kwh - usable_kwh)
        loc_type = _location_type(env, i)
        if loc_type is None:
            continue
        charge_power = max(float(env._get_charge_power(loc_type)), 1.0e-9)
        laxity[i] = hours_to_deadline - deficit_kwh / charge_power

    need = available & _target_need(env, obs)
    reserve = available & _reserve_need(env, obs)
    for loc_type_name in ("home", "work", "public"):
        members = np.array([i for i in np.where(need)[0] if _location_type(env, int(i)) == loc_type_name], dtype=int)
        if members.size == 0:
            continue
        queued = len(getattr(env, "charger_queues", {}).get(loc_type_name, []))
        remaining = max(0, int(env.n_slots[loc_type_name]) - int(queued))
        if remaining <= 0:
            continue
        reserve_members = members[reserve[members]]
        other_members = members[~reserve[members]]
        ordered_reserve = reserve_members[np.argsort(laxity[reserve_members])]
        ordered_other = other_members[np.argsort(laxity[other_members])]
        selected = np.concatenate([ordered_reserve, ordered_other])[:remaining]
        charge[selected] = True
    return charge


def train_dqn_v2(
    cfg: V2RunConfig,
    reward_config: LagrangianRewardConfig | None = None,
) -> tuple[DQNV2Agent, list[dict[str, float]]]:
    seed_everything(cfg.seed)
    agent = DQNV2Agent(
        DQNV2Config(
            state_dim=STATE_DIM_V2,
            action_dim=N_PRIMITIVE_ACTIONS,
            hidden_dim=cfg.hidden_dim,
            lr=cfg.lr,
            gamma=cfg.gamma,
            batch_size=cfg.batch_size,
            min_buffer_size=cfg.min_buffer_size,
            epsilon_start=1.0,
            epsilon_end=0.05,
            epsilon_decay=cfg.epsilon_decay,
        )
    )
    reward_cfg = reward_config or LagrangianRewardConfig()
    history: list[dict[str, float]] = []
    for ep in range(cfg.train_episodes):
        env = make_env(cfg, seed=cfg.seed + ep)
        obs = env.reset()
        done = False
        ep_reward = 0.0
        updates = 0
        while not done:
            states = batch_flatten_obs_v2(obs, env.n_cars)
            masks = batch_action_mask(obs, env.n_cars)
            actions = agent.select_actions_batch(states, masks, greedy=False)
            next_obs, base_rewards, done, info = env.step(actions)
            shaped_rewards, _ = compute_lagrangian_reward(env, base_rewards, info, reward_cfg)
            next_states = batch_flatten_obs_v2(next_obs, env.n_cars)
            next_masks = batch_action_mask(next_obs, env.n_cars)
            for i in range(env.n_cars):
                agent.store_transition(states[i], int(actions[i]), float(shaped_rewards[i]), next_states[i], bool(done), next_masks[i])
            update_info = agent.update()
            updates += int(bool(update_info))
            ep_reward += float(shaped_rewards.mean())
            obs = next_obs
        agent.end_episode()
        history.append({"episode": ep + 1, "mean_reward": ep_reward, "updates": updates, "epsilon": float(agent.epsilon)})
    return agent, history


def _metrics_from_env(
    env: BRLDQNPrimitiveEnv,
    demand_kw: list[float],
    delivered_kwh: float,
    action_counts: np.ndarray,
    invalid_request_count: int = 0,
    invalid_urgent_count: int = 0,
    urgent_trip_events: int = 0,
    urgent_trip_failures: int = 0,
) -> dict[str, object]:
    mandatory_events = max(1, env.count_mandatory_trip_events(realized=True))
    waits = np.asarray(env.agent_wait_time, dtype=float)
    demand_arr = np.asarray(demand_kw, dtype=float)
    mean_demand = float(demand_arr.mean()) if demand_arr.size else 0.0
    peak_demand = float(demand_arr.max()) if demand_arr.size else 0.0
    urgent_denom = max(1, int(urgent_trip_events))
    return {
        "reliability_pct": 100.0 * (1.0 - env.failure_count / mandatory_events),
        "failure_count": int(env.failure_count),
        "mandatory_events": int(mandatory_events),
        "urgent_trip_reliability_pct": 100.0 * (1.0 - int(urgent_trip_failures) / urgent_denom),
        "urgent_trip_failure_count": int(urgent_trip_failures),
        "urgent_trip_events": int(urgent_trip_events),
        "delivered_kwh_per_vehicle": float(delivered_kwh / max(1, env.n_cars)),
        "peak_demand_kw": peak_demand,
        "mean_demand_kw": mean_demand,
        "coincidence_factor": float(peak_demand / max(mean_demand, 1.0e-9)) if mean_demand > 0.0 else 0.0,
        "p95_wait_minutes": float(np.percentile(waits, 95) * 60.0),
        "mean_wait_minutes": float(waits.mean() * 60.0),
        "max_queue": {k: int(v) for k, v in env.max_queue_length_seen.items()},
        "action_counts": action_counts.astype(int).tolist(),
        "nondegenerate_actions": int((action_counts > 0).sum()),
        "invalid_request_count": int(invalid_request_count),
        "invalid_urgent_count": int(invalid_urgent_count),
    }


def evaluate_policy(
    cfg: V2RunConfig,
    policy_name: str,
    agent: DQNV2Agent | None = None,
    seed: int | None = None,
) -> dict[str, object]:
    env = make_env(cfg, seed=cfg.seed if seed is None else seed)
    obs = env.reset()
    done = False
    demand_kw: list[float] = []
    delivered_kwh = 0.0
    action_counts = np.zeros(N_PRIMITIVE_ACTIONS, dtype=int)
    rng = np.random.default_rng(cfg.seed if seed is None else seed)
    wrapper = QGapSoftmaxWrapper(QGapConfig(seed=cfg.seed if seed is None else seed))
    prices = np.asarray(env.price_schedule[: env.config.episode_hours], dtype=float)
    is_cheap = _cheap_mask(prices)
    max_run = max(1, int(is_cheap.sum()))
    jitter_offsets = rng.integers(0, max_run, size=(env.n_cars, env.config.episode_hours))
    invalid_request_count = 0
    invalid_urgent_count = 0
    urgent_trip_events = 0
    urgent_trip_failures = 0
    while not done:
        t = int(env.t)
        states = batch_flatten_obs_v2(obs, env.n_cars)
        masks = batch_action_mask(obs, env.n_cars)
        if policy_name == "DQN-V2":
            if agent is None:
                raise ValueError("DQN-V2 evaluation requires an agent")
            actions = agent.select_actions_batch(states, masks, greedy=True)
        elif policy_name == "Native-BRL-v1":
            if agent is None:
                raise ValueError("Native-BRL-v1 evaluation requires an agent")
            q_values = agent.q_values_batch(states)
            actions = np.asarray([wrapper.select_action(q_values[i], masks[i]) for i in range(env.n_cars)], dtype=int)
        elif policy_name == "FeasibleAlways":
            actions = np.where(masks[:, PRIMITIVE_NORMAL_REQUEST], PRIMITIVE_NORMAL_REQUEST, 0).astype(int)
        elif policy_name == "FeasibleRandom50":
            charge = (rng.random(env.n_cars) < 0.5) & masks[:, PRIMITIVE_NORMAL_REQUEST]
            actions = np.where(charge, PRIMITIVE_NORMAL_REQUEST, 0).astype(int)
        elif policy_name in {"RandomizedStart", "FeasibleRandom50-x-RandomizedStart"}:
            run = _cheap_run_position(is_cheap, t)
            if run is None:
                cheap_after_delay = np.zeros(env.n_cars, dtype=bool)
            else:
                pos, length = run
                offsets = jitter_offsets[:, t - pos] % max(length, 1)
                cheap_after_delay = pos >= offsets
            reserve = _reserve_need(env, obs)
            target = _target_need(env, obs)
            nonreserve_gate = target & cheap_after_delay
            if policy_name == "FeasibleRandom50-x-RandomizedStart":
                nonreserve_gate &= rng.random(env.n_cars) < 0.50
            charge = masks[:, PRIMITIVE_NORMAL_REQUEST] & (reserve | nonreserve_gate)
            actions = np.where(charge, PRIMITIVE_NORMAL_REQUEST, 0).astype(int)
        elif policy_name == "LeastLaxity":
            charge = _least_laxity_charge(env, obs, t, masks[:, PRIMITIVE_NORMAL_REQUEST])
            actions = np.where(charge, PRIMITIVE_NORMAL_REQUEST, 0).astype(int)
        else:
            raise ValueError(policy_name)
        for a in range(N_PRIMITIVE_ACTIONS):
            action_counts[a] += int((actions == a).sum())
        realized = getattr(env, "realized_mandatory_trip_schedule", None)
        if realized is not None and t < realized.shape[1]:
            trip_events = np.asarray(realized[:, t] > 0.0, dtype=bool)
        else:
            trip_events = np.zeros(env.n_cars, dtype=bool)
        soc = np.asarray(obs["soc"], dtype=float)
        theta = np.asarray(obs["anxiety_thresholds"], dtype=float)
        shortfall = np.asarray(obs.get("energy_shortfall_norm", np.zeros(env.n_cars)), dtype=float)
        time_to = np.asarray(obs.get("time_to_next_mandatory_norm", np.ones(env.n_cars)), dtype=float)
        pre_urgent = (shortfall > 0.0) | (time_to <= (24.0 / 168.0)) | (soc <= theta + 0.05)
        urgent_trip_mask = trip_events & pre_urgent
        obs, _, done, info = env.step(actions)
        failures = np.asarray(info.get("failures", np.zeros(env.n_cars, dtype=bool)), dtype=bool)
        urgent_trip_events += int(urgent_trip_mask.sum())
        urgent_trip_failures += int((urgent_trip_mask & failures).sum())
        invalid_request_count += int(info.get("primitive_invalid_request_count", 0))
        invalid_urgent_count += int(info.get("primitive_invalid_urgent_count", 0))
        demand_kw.append(float(info.get("agg_demand_kw", 0.0)))
        delivered_kwh += float(np.asarray(getattr(env, "_last_charge_stored_actual_kwh", np.zeros(env.n_cars))).sum())
    out = _metrics_from_env(
        env,
        demand_kw,
        delivered_kwh,
        action_counts,
        invalid_request_count=invalid_request_count,
        invalid_urgent_count=invalid_urgent_count,
        urgent_trip_events=urgent_trip_events,
        urgent_trip_failures=urgent_trip_failures,
    )
    out["policy"] = policy_name
    return out


def save_agent(agent: DQNV2Agent, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(agent.policy_net.state_dict(), path)


def run_training_smoke(cfg: V2RunConfig) -> dict[str, object]:
    start = time.time()
    agent, history = train_dqn_v2(cfg)
    policies = ["DQN-V2", "Native-BRL-v1", "FeasibleAlways", "FeasibleRandom50", "LeastLaxity"]
    evals = [evaluate_policy(cfg, name, agent=agent, seed=cfg.seed + 100) for name in policies]
    model_path = WORKSPACE / "results" / "dqn_v2_training_smoke" / f"dqn_v2_seed{cfg.seed}.pt"
    save_agent(agent, model_path)
    dqn_eval = next(row for row in evals if row["policy"] == "DQN-V2")
    native_eval = next(row for row in evals if row["policy"] == "Native-BRL-v1")
    status = "PASS"
    failures = []
    if dqn_eval["nondegenerate_actions"] < 2:
        status = "FAIL"
        failures.append("dqn_degenerate_actions")
    if sum(dqn_eval["action_counts"][1:]) <= 0 or dqn_eval["delivered_kwh_per_vehicle"] <= 0.0:
        status = "FAIL"
        failures.append("dqn_zero_charge")
    if native_eval["nondegenerate_actions"] < 2:
        status = "FAIL"
        failures.append("native_brl_degenerate_actions")
    if sum(native_eval["action_counts"][1:]) <= 0 or native_eval["delivered_kwh_per_vehicle"] <= 0.0:
        status = "FAIL"
        failures.append("native_brl_zero_charge")
    return {
        "status": status,
        "failures": failures,
        "config": asdict(cfg),
        "history": history,
        "evals": evals,
        "model_path": str(model_path),
        "wall_seconds": time.time() - start,
    }


def write_training_smoke_outputs(result: dict[str, object]) -> None:
    outdir = WORKSPACE / "results" / "dqn_v2_training_smoke"
    artifact = WORKSPACE / "artifacts" / "dqn_v2_training_smoke_summary.md"
    outdir.mkdir(parents=True, exist_ok=True)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    json_path = outdir / "dqn_v2_training_smoke_result.json"
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# DQN-V2 Training Smoke Summary",
        "",
        f"Status: `{result['status']}`",
        f"Model: `{result['model_path']}`",
        f"Wall seconds: `{result['wall_seconds']:.3f}`",
        "",
        "| policy | reliability | delivered kWh/veh | peak kW | p95 wait min | actions |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in result["evals"]:
        lines.append(
            f"| {row['policy']} | {row['reliability_pct']:.3f} | "
            f"{row['delivered_kwh_per_vehicle']:.3f} | {row['peak_demand_kw']:.3f} | "
            f"{row['p95_wait_minutes']:.3f} | `{row['action_counts']}` |"
        )
    artifact.write_text("\n".join(lines) + "\n", encoding="utf-8")
