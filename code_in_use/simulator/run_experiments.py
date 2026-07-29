import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

from behavioral_wrapper import BehavioralConfig, BehavioralWrapper, generate_ablation_configs, generate_rationality_sweep, generate_sensitivity_grid
from data_grounding import get_scenario_preset
from env_v2 import EVEnvironmentV2, EnvV2Config, get_kepco_price
from obs_adapter import flatten_agent_obs, STATE_DIM, CHARGE_AVAILABLE_INDEX


RESULTS_DIR = Path(__file__).parent / "results"
TRAINED_AGENTS_DIR = Path(__file__).parent / "trained_agents"
SEEDS = [42, 123, 256, 512, 1024]
TRAIN_SEEDS = [42, 123, 256]
EVAL_SEEDS = [42, 123, 256, 512, 1024]
# Expanded to 20 seeds for revision (Wilcoxon exact floor at n=20 is p < 10^-6 in the
# one-sided paired sense, which addresses the "just-significant p-value" critique).
MAIN_EVIDENCE_SEEDS = [
    42, 123, 256, 512, 1024, 7, 11, 19, 29, 37,
    43, 59, 71, 89, 101, 211, 307, 401, 509, 701,
]

_TRAINED_CACHE: dict[tuple[str, str, int], Any] = {}


def _map_binary_action(action_idx: int) -> int:
    return 0 if int(action_idx) == 0 else 6


_TARIFF_VARIANT_SUFFIXES = ("_uncertain", "_flat", "_2tier", "_sce")


def _find_checkpoint(agent_name: str, scenario_name: str, seed: int) -> Path:
    fname = f"{agent_name.lower()}_{scenario_name}_seed{seed}.pt"
    path = TRAINED_AGENTS_DIR / fname
    if path.exists():
        return path
    # Fallback: if scenario is a tariff/uncertainty variant of metro_korea or metro_caltech,
    # reuse the base-scenario checkpoint (zero-shot transfer).
    for suf in _TARIFF_VARIANT_SUFFIXES:
        if scenario_name.endswith(suf):
            base = scenario_name[: -len(suf)]
            fallback = TRAINED_AGENTS_DIR / f"{agent_name.lower()}_{base}_seed{seed}.pt"
            if fallback.exists():
                return fallback
    raise FileNotFoundError(
        f"Missing trained checkpoint: {path}. Run train_agents.py first."
    )


def _load_trained_dqn(scenario_name: str, seed: int):
    key = ("DQN", scenario_name, seed)
    if key in _TRAINED_CACHE:
        return _TRAINED_CACHE[key]
    import torch
    from dqn_agent import DQNAgent, DQNConfig
    agent = DQNAgent(DQNConfig(state_dim=STATE_DIM, action_dim=2, charge_available_index=CHARGE_AVAILABLE_INDEX))
    state = torch.load(_find_checkpoint("DQN", scenario_name, seed), map_location="cpu")
    agent.policy_net.load_state_dict(state)
    agent.policy_net.eval()
    _TRAINED_CACHE[key] = agent
    return agent


def _load_trained_sac(scenario_name: str, seed: int):
    key = ("SAC", scenario_name, seed)
    if key in _TRAINED_CACHE:
        return _TRAINED_CACHE[key]
    import torch
    from discrete_sac_agent import DiscreteSACAgent, DiscreteSACConfig
    agent = DiscreteSACAgent(DiscreteSACConfig(state_dim=STATE_DIM, action_dim=2, charge_available_index=CHARGE_AVAILABLE_INDEX))
    state = torch.load(_find_checkpoint("SAC", scenario_name, seed), map_location="cpu")
    agent.actor.load_state_dict(state["actor"])
    agent.actor.eval()
    _TRAINED_CACHE[key] = agent
    return agent


def _load_trained_lagsac(scenario_name: str, seed: int):
    key = ("Lag-SAC", scenario_name, seed)
    if key in _TRAINED_CACHE:
        return _TRAINED_CACHE[key]
    import torch
    from discrete_sac_agent import DiscreteSACAgent, DiscreteSACConfig
    agent = DiscreteSACAgent(DiscreteSACConfig(state_dim=STATE_DIM, action_dim=2, charge_available_index=CHARGE_AVAILABLE_INDEX))
    state = torch.load(_find_checkpoint("Lag-SAC", scenario_name, seed), map_location="cpu")
    agent.actor.load_state_dict(state["actor"])
    agent.actor.eval()
    _TRAINED_CACHE[key] = agent
    return agent


def make_trained_lagsac_agent(scenario_name: str, seed: int, greedy: bool = False):
    agent = _load_trained_lagsac(scenario_name, seed)

    def agent_fn(car_idx, obs, t):
        s = flatten_agent_obs(obs, car_idx)
        return _map_binary_action(agent.select_action(s, greedy=greedy))

    return agent_fn


def _load_trained_marl(scenario_name: str, seed: int):
    key = ("MARL-DQN", scenario_name, seed)
    if key in _TRAINED_CACHE:
        return _TRAINED_CACHE[key]
    import torch
    from marl_agent import MARLDQNAgent, MARLDQNConfig
    agent = MARLDQNAgent(MARLDQNConfig(state_dim=STATE_DIM, action_dim=2, charge_available_index=CHARGE_AVAILABLE_INDEX))
    state = torch.load(_find_checkpoint("MARL-DQN", scenario_name, seed), map_location="cpu")
    agent.policy_net.load_state_dict(state)
    agent.policy_net.eval()
    _TRAINED_CACHE[key] = agent
    return agent


def make_trained_marl_agent(scenario_name: str, seed: int, greedy: bool = True):
    """MARL-DQN agent — computes fleet context from the observation dict directly."""
    from marl_agent import fleet_context
    agent = _load_trained_marl(scenario_name, seed)

    def agent_fn(car_idx, obs, t):
        fvec = fleet_context(obs=obs, prev_demand_kw=0.0)
        s = flatten_agent_obs(obs, car_idx)
        return _map_binary_action(agent.select_action(s, fvec, greedy=greedy))

    return agent_fn


def _load_trained_brl_dqn(scenario_name: str, seed: int, variant: str = "default"):
    """variant='default' → retuned BRL (η=0.5); variant='v1' → original BRL (η=1.5)."""
    key = ("BRL-DQN", scenario_name, seed, variant)
    if key in _TRAINED_CACHE:
        return _TRAINED_CACHE[key]
    import torch
    from dqn_agent import DQNAgent, DQNConfig
    agent = DQNAgent(DQNConfig(state_dim=STATE_DIM, action_dim=2, charge_available_index=CHARGE_AVAILABLE_INDEX))
    if variant == "v1":
        path = TRAINED_AGENTS_DIR / f"brl-dqn_{scenario_name}_seed{seed}_v1.pt"
        if not path.exists():
            raise FileNotFoundError(f"Missing v1 checkpoint: {path}")
    else:
        path = _find_checkpoint("BRL-DQN", scenario_name, seed)
    state = torch.load(path, map_location="cpu")
    agent.policy_net.load_state_dict(state)
    agent.policy_net.eval()
    _TRAINED_CACHE[key] = agent
    return agent


def make_trained_dqn_agent(scenario_name: str, seed: int, greedy: bool = True):
    agent = _load_trained_dqn(scenario_name, seed)

    def agent_fn(car_idx, obs, t):
        s = flatten_agent_obs(obs, car_idx)
        return _map_binary_action(agent.select_action(s, greedy=greedy))

    return agent_fn


def make_trained_sac_agent(scenario_name: str, seed: int, greedy: bool = False):
    """Default greedy=False to preserve SAC's stochastic policy signature — this is what we
    want to compare against: the entropy-regularized policy's actual behavior at evaluation."""
    agent = _load_trained_sac(scenario_name, seed)

    def agent_fn(car_idx, obs, t):
        s = flatten_agent_obs(obs, car_idx)
        return _map_binary_action(agent.select_action(s, greedy=greedy))

    return agent_fn


def make_trained_brl_dqn_agent(scenario_name: str, seed: int,
                                params: dict[str, float] | None = None,
                                variant: str = "default"):
    """BRL-DQN wraps a trained DQN checkpoint with the BehavioralWrapper.
    variant='default' uses retuned BehavioralConfig (η=0.5). variant='v1' loads the
    original high-reserve checkpoint and uses η=1.5 (matches first-round training)."""
    agent = _load_trained_brl_dqn(scenario_name, seed, variant=variant)
    p = params or {}
    default_eta = 1.5 if variant == "v1" else 0.5
    brl_config = BehavioralConfig(
        rho=float(p.get("rho", 0.3)),
        kappa=float(p.get("kappa", 2.0)),
        sigma=float(p.get("sigma", 0.5)),
        eta=float(p.get("eta", default_eta)),
        lambda_kt=float(p.get("lambda_kt", 2.25)),
        alpha_0=float(p.get("alpha_0", -1.0)),
        alpha_1=float(p.get("alpha_1", 0.5)),
        attention_mode=str(p.get("attention_mode", "random")),
        lambda_rationality=float(p.get("lambda_rationality", 5.0)),
        use_inertia=bool(p.get("use_inertia", True)),
        use_noise=bool(p.get("use_noise", True)),
        use_loss_aversion=bool(p.get("use_loss_aversion", True)),
        use_attention=bool(p.get("use_attention", True)),
    )
    wrapper = BehavioralWrapper(brl_config)
    wrapper.reset()
    import torch

    def agent_fn(car_idx, obs, t):
        s = flatten_agent_obs(obs, car_idx)
        with torch.no_grad():
            q = agent.policy_net(torch.as_tensor(s, dtype=torch.float32).unsqueeze(0)).squeeze(0).cpu().numpy()
        q8 = np.array([q[0], q[0], q[0], q[0], q[0], q[0], q[1], -2.0], dtype=np.float64)
        if "charge_available" in obs and not bool(np.asarray(obs["charge_available"], dtype=bool)[car_idx]):
            q8[:6] = -1.0e9
        soc = float(np.asarray(obs["soc"])[car_idx])
        theta = float(np.asarray(obs["anxiety_thresholds"])[car_idx])
        selected = int(wrapper.select_action(q_values=q8, soc=soc, anxiety_threshold=theta))
        return 0 if selected < 6 else 6

    return agent_fn


def make_scenario_config(seed: int, scenario_name: str, **overrides: Any) -> EnvV2Config:
    preset = get_scenario_preset(scenario_name)
    config_kwargs: dict[str, Any] = preset.to_config_dict()
    config_kwargs["seed"] = seed
    config_kwargs.update(overrides)
    config_kwargs["scenario_preset_materialized"] = True
    return EnvV2Config(**config_kwargs)


@dataclass
class ExperimentResult:
    experiment: str
    agent: str
    seed: int
    reliability_pct: float
    avg_cost_krw: float
    herding_index: float
    peak_demand_kw: float
    renewable_utilization_pct: float
    failure_count: int
    reliability_adjusted_cost: float
    hourly_demand_profile: list[float]
    config: dict[str, Any]


def run_single_episode(
    env: EVEnvironmentV2,
    agent_fn: Callable[[int, dict[str, Any], int], int],
    seed: int,
) -> dict[str, Any]:
    env.config.seed = seed
    env.rng = np.random.default_rng(seed)
    obs = env.reset()

    total_rewards = np.zeros(env.n_cars)
    hourly_demand = np.zeros(env.config.episode_hours)
    solar_charging = 0.0
    total_charging = 0.0
    critical_state_count = 0
    critical_idle_count = 0
    total_invalid_charge_requests = 0
    total_raw_charge_requests = 0

    def next_mandatory_trip(agent_idx: int, t_now: int) -> tuple[int | None, float]:
        target = env.realized_mandatory_trip_schedule
        if target is None or t_now >= target.shape[1]:
            return None, 0.0
        future = target[agent_idx, t_now:]
        hits = np.flatnonzero(future > 0)
        if hits.size == 0:
            return None, 0.0
        trip_t = int(t_now + hits[0])
        return trip_t, float(target[agent_idx, trip_t] * 0.18 / env.config.bcap_kwh)

    def charge_mode_if_requested(agent_idx: int, t_now: int) -> str:
        loc = int(env.location_schedule[agent_idx, t_now]) if env.location_schedule is not None and t_now < env.location_schedule.shape[1] else int(env.locations[agent_idx])
        if loc == 1 and env.has_work_access[agent_idx]:
            return "work"
        if loc == 0 and env.has_home_access[agent_idx]:
            return "home"
        if env.has_public_access[agent_idx] and env.public_fallback[agent_idx]:
            return "public"
        return "none"

    def max_reachable_soc(agent_idx: int, t_now: int, include_current: bool) -> float:
        trip_t, _ = next_mandatory_trip(agent_idx, t_now)
        if trip_t is None:
            return float(env.soc[agent_idx])
        max_soc = float(env.soc[agent_idx])
        start = t_now if include_current else t_now + 1
        if env.location_schedule is None:
            return max_soc
        for tau in range(start, min(trip_t, env.location_schedule.shape[1])):
            mode = charge_mode_if_requested(agent_idx, tau)
            if mode == "none":
                continue
            eta = env._get_efficiency(mode)
            p_charge = env._get_charge_power(mode)
            max_soc = min(env.config.soc_max, max_soc + (eta * p_charge / env.config.bcap_kwh))
        return max_soc

    for t in range(env.config.episode_hours):
        actions = np.array([agent_fn(i, obs, t) for i in range(env.n_cars)])
        if "charge_available" in obs:
            available = np.asarray(obs["charge_available"], dtype=bool)
            actions = actions.copy()
            actions[(actions <= 5) & ~available] = 6
        for i in range(env.n_cars):
            trip_t, required_soc = next_mandatory_trip(i, t)
            if trip_t is None or required_soc <= 0:
                continue
            mode_now = charge_mode_if_requested(i, t)
            if mode_now == "none":
                continue
            reachable_if_charge = max_reachable_soc(i, t, include_current=True)
            reachable_if_idle = max_reachable_soc(i, t, include_current=False)
            if reachable_if_charge >= required_soc and reachable_if_idle < required_soc:
                critical_state_count += 1
                if int(actions[i]) > 5:
                    critical_idle_count += 1
        obs, rewards, done, info = env.step(actions)
        total_invalid_charge_requests += int(info.get("invalid_charge_request_count", 0))
        raw_for_count = info.get("raw_policy_actions", info.get("raw_actions", actions))
        total_raw_charge_requests += int((np.asarray(raw_for_count) <= 5).sum())
        total_rewards += rewards

        demand_this_hour = sum(
            env._get_charge_power(str(env._current_charge_modes[i])) if actions[i] <= 5 and str(env._current_charge_modes[i]) != "none" else 0.0
            for i in range(env.n_cars)
        )
        hourly_demand[t] = demand_this_hour

        if 11 <= (t % 24) < 15:
            solar_charging += demand_this_hour
        total_charging += demand_this_hour

        if done:
            break

    mandatory_trips = max(1, env.count_mandatory_trip_events(realized=True))
    reliability = 100.0 * (1.0 - env.failure_count / mandatory_trips)
    avg_cost = -total_rewards.mean()
    herding = float(np.var(hourly_demand))
    peak = float(hourly_demand.max())
    renew_util = 100.0 * solar_charging / max(1.0, total_charging)
    rac = avg_cost + env.config.shadow_price_failure * env.failure_count / env.n_cars

    return {
        "reliability_pct": reliability,
        "mandatory_trip_events": mandatory_trips,
        "avg_cost_krw": avg_cost,
        "herding_index": herding,
        "peak_demand_kw": peak,
        "renewable_utilization_pct": renew_util,
        "failure_count": env.failure_count,
        "reliability_adjusted_cost": rac,
        "hourly_demand_profile": hourly_demand.tolist(),
        "critical_state_count": critical_state_count,
        "critical_idle_count": critical_idle_count,
        "critical_idle_rate": float(critical_idle_count / critical_state_count) if critical_state_count > 0 else 0.0,
        "total_invalid_charge_requests": int(total_invalid_charge_requests),
        "total_raw_charge_requests": int(total_raw_charge_requests),
        "invalid_charge_request_fraction": float(total_invalid_charge_requests / max(1, total_raw_charge_requests)),
    }


def _risk_objective(metrics: dict[str, Any], p_fail: float, n_cars: int) -> float:
    return (
        float(metrics["avg_cost_krw"])
        + p_fail * float(metrics["failure_count"]) / max(1, n_cars)
        + 0.001 * float(metrics["herding_index"])
    )


def make_uncoordinated_agent():
    def agent_fn(car_idx, obs, t):
        return 0

    return agent_fn


def make_rule_tou_agent(params: dict[str, float] | None = None):
    p = params or {}
    reserve_margin = p.get("reserve_margin", 0.12)
    target_soc = p.get("target_soc", 0.90)
    emergency_soc = p.get("emergency_soc", 0.32)

    def agent_fn(car_idx, obs, t):
        soc = obs["soc"][car_idx]
        theta = obs["anxiety_thresholds"][car_idx]
        h = t % 24
        cheap_window = h in {23, 0, 1, 2, 3, 4, 5, 11, 12, 13, 14}
        if soc < max(emergency_soc, theta + reserve_margin):
            return 0
        if cheap_window and soc < target_soc:
            return 0
        return 6

    return agent_fn


def make_mpc_agent(params: dict[str, float] | None = None):
    """Historical experiment label: MPC-24h.

    This is not optimization-based MPC. It is a deterministic 24-hour
    tariff-threshold heuristic with a reserve trigger. The manuscript reports
    it as PriceThresh-24h to avoid overstating the comparator.
    """
    p = params or {}
    horizon = int(p.get("horizon", 24))
    reserve_margin = p.get("reserve_margin", 0.12)
    target_soc = p.get("target_soc", 0.90)
    price_tolerance = p.get("price_tolerance", 0.05)

    def agent_fn(car_idx, obs, t):
        soc = obs["soc"][car_idx]
        theta = obs["anxiety_thresholds"][car_idx]
        now_price = obs["price"]
        if soc < theta + reserve_margin:
            return 0

        future_prices = [get_kepco_price((t + h) % 24) for h in range(1, horizon + 1)]
        min_future = min(future_prices) if future_prices else now_price
        if soc < target_soc and now_price <= (1.0 + price_tolerance) * min_future:
            return 0
        return 6

    return agent_fn


def make_dqn_agent(params: dict[str, float] | None = None):
    p = params or {}
    charge_below = p.get("charge_below", 0.8)

    def agent_fn(car_idx, obs, t):
        soc = obs["soc"][car_idx]
        if soc < charge_below:
            return 0
        return 6

    return agent_fn


def make_action_smoothing_agent(params: dict[str, float] | None = None, seed: int = 777):
    p = params or {}
    charge_below = float(p.get("charge_below", 0.8))
    keep_previous_prob = float(p.get("keep_previous_prob", 0.75))
    rng = np.random.default_rng(seed)
    previous_actions: dict[int, int] = {}

    def agent_fn(car_idx, obs, t):
        soc = obs["soc"][car_idx]
        base_action = 0 if soc < charge_below else 6
        prev = previous_actions.get(car_idx)
        if prev is not None and prev != base_action and rng.random() < keep_previous_prob:
            action = prev
        else:
            action = base_action
        previous_actions[car_idx] = int(action)
        return int(action)

    return agent_fn


def make_random_div_agent(params: dict[str, float] | None = None, seed: int = 333):
    """RandomDiv: each car assigned a fixed random preferred off-peak hour at init.
    Charges only at that hour unless SoC critical.
    Tests whether pre-assigned fleet diversity (without learning or behavioral ingredients)
    achieves the same load-factor property as BRL."""
    p = params or {}
    rng = np.random.default_rng(seed)
    off_peak = p.get("off_peak_hours", (23, 0, 1, 2, 3, 4, 5, 11, 12, 13, 14))
    safety_margin = float(p.get("safety_margin", 0.05))
    target_soc = float(p.get("target_soc", 0.90))
    emergency_soc = float(p.get("emergency_soc", 0.30))
    car_preferred_hour: dict[int, int] = {}

    def _pref(i: int) -> int:
        if i not in car_preferred_hour:
            car_preferred_hour[i] = int(rng.choice(off_peak))
        return car_preferred_hour[i]

    def agent_fn(car_idx, obs, t):
        soc = float(obs["soc"][car_idx])
        theta = float(obs["anxiety_thresholds"][car_idx])
        h = t % 24
        if soc < max(emergency_soc, theta + safety_margin):
            return 0
        if h == _pref(car_idx) and soc < target_soc:
            return 0
        return 6

    return agent_fn


def make_beta_div_agent(params: dict[str, float] | None = None, seed: int = 555):
    """BetaDiv: per-car charge propensity drawn from Beta(alpha,beta). Drives heterogeneous
    charging intensity across the fleet without using any behavioral-economics machinery.
    Meant as 'simple heterogeneity' baseline."""
    p = params or {}
    rng = np.random.default_rng(seed)
    alpha = float(p.get("alpha", 2.0))
    beta = float(p.get("beta", 5.0))
    safety_margin = float(p.get("safety_margin", 0.05))
    emergency_soc = float(p.get("emergency_soc", 0.30))
    target_soc = float(p.get("target_soc", 0.90))
    price_cutoff = float(p.get("price_cutoff", 80.0))
    car_propensity: dict[int, float] = {}

    def _prop(i: int) -> float:
        if i not in car_propensity:
            car_propensity[i] = float(rng.beta(alpha, beta))
        return car_propensity[i]

    def agent_fn(car_idx, obs, t):
        soc = float(obs["soc"][car_idx])
        theta = float(obs["anxiety_thresholds"][car_idx])
        price = float(obs["price"])
        if soc < max(emergency_soc, theta + safety_margin):
            return 0
        propensity = _prop(car_idx)
        if price < price_cutoff and soc < target_soc:
            return 0 if rng.random() < propensity else 6
        return 0 if rng.random() < propensity * 0.3 else 6

    return agent_fn


def make_temperature_dqn_agent(params: dict[str, float] | None = None, seed: int = 991):
    p = params or {}
    charge_below = float(p.get("charge_below", 0.8))
    temperature = float(p.get("temperature", 0.08))
    rng = np.random.default_rng(seed)

    def agent_fn(car_idx, obs, t):
        soc = float(obs["soc"][car_idx])
        z = (soc - charge_below) / max(temperature, 1e-6)
        p_charge = 1.0 / (1.0 + np.exp(z))
        return 0 if rng.random() < p_charge else 6

    return agent_fn


def make_sac_agent(params: dict[str, float] | None = None, seed: int = 99):
    p = params or {}
    rng = np.random.default_rng(seed)
    price_cutoff = p.get("price_cutoff", 70.0)
    soc_target = p.get("soc_target", 0.90)
    critical_soc = p.get("critical_soc", 0.30)
    low_soc_idle_prob = p.get("low_soc_idle_prob", 0.15)
    default_charge_prob = p.get("default_charge_prob", 0.30)

    def agent_fn(car_idx, obs, t):
        soc = obs["soc"][car_idx]
        price = obs["price"]
        if price < price_cutoff and soc < soc_target:
            return 0
        if soc < critical_soc:
            return 0 if rng.random() > low_soc_idle_prob else 6
        return 0 if rng.random() < default_charge_prob else 6

    return agent_fn


def make_cpo_agent(params: dict[str, float] | None = None):
    p = params or {}
    reserve_margin = p.get("reserve_margin", 0.15)
    price_cutoff = p.get("price_cutoff", 80.0)
    soc_cap = p.get("soc_cap", 0.88)

    def agent_fn(car_idx, obs, t):
        soc = obs["soc"][car_idx]
        theta = obs["anxiety_thresholds"][car_idx]
        price = obs["price"]
        reserve = min(0.95, theta + reserve_margin)
        if soc < reserve:
            return 0
        if price < price_cutoff and soc < soc_cap:
            return 0
        return 6

    return agent_fn


def make_lagsac_agent(params: dict[str, float] | None = None, seed: int = 199):
    p = params or {}
    rng = np.random.default_rng(seed)
    reserve_margin = p.get("reserve_margin", 0.08)
    reserve_idle_prob = p.get("reserve_idle_prob", 0.20)
    price_cutoff = p.get("price_cutoff", 70.0)
    soc_cap = p.get("soc_cap", 0.88)
    default_charge_prob = p.get("default_charge_prob", 0.80)

    def agent_fn(car_idx, obs, t):
        soc = obs["soc"][car_idx]
        theta = obs["anxiety_thresholds"][car_idx]
        price = obs["price"]
        if soc < theta + reserve_margin:
            return 0 if rng.random() > reserve_idle_prob else 6
        if price < price_cutoff and soc < soc_cap:
            return 0
        return 0 if rng.random() < default_charge_prob else 6

    return agent_fn


def make_brl_dqn_agent(params: dict[str, float] | None = None):
    p = params or {}
    brl_config = BehavioralConfig(
        rho=float(p.get("rho", 0.3)),
        kappa=float(p.get("kappa", 2.0)),
        sigma=float(p.get("sigma", 0.5)),
        eta=float(p.get("eta", 1.5)),
        lambda_kt=float(p.get("lambda_kt", 2.25)),
        alpha_0=float(p.get("alpha_0", -1.0)),
        alpha_1=float(p.get("alpha_1", 0.5)),
        attention_mode=str(p.get("attention_mode", "random")),
        lambda_rationality=float(p.get("lambda_rationality", 5.0)),
        use_inertia=bool(p.get("use_inertia", True)),
        use_noise=bool(p.get("use_noise", True)),
        use_loss_aversion=bool(p.get("use_loss_aversion", True)),
        use_attention=bool(p.get("use_attention", True)),
    )
    wrapper = BehavioralWrapper(brl_config)

    charge_threshold = float(p.get("charge_threshold", 0.8))
    low_price_cutoff = float(p.get("low_price_cutoff", 70.0))
    high_price_cutoff = float(p.get("high_price_cutoff", 200.0))
    low_price_boost = float(p.get("low_price_boost", 2.0))
    high_price_penalty = float(p.get("high_price_penalty", 1.0))

    def agent_fn(car_idx, obs, t):
        soc = obs["soc"][car_idx]
        theta = obs["anxiety_thresholds"][car_idx]
        q_values = np.array([
            2.0 if soc < charge_threshold else -1.0,
            1.5,
            1.0,
            0.5,
            0.3,
            0.1,
            -0.5 if soc > 0.5 else -3.0,
            -2.0,
        ])
        price = obs["price"]
        if price < low_price_cutoff:
            q_values[0] += low_price_boost
        elif price > high_price_cutoff:
            q_values[0] -= high_price_penalty
        if "charge_available" in obs and not bool(np.asarray(obs["charge_available"], dtype=bool)[car_idx]):
            q_values[:6] = -1.0e9
        return wrapper.select_action(q_values=q_values, soc=soc, anxiety_threshold=theta)

    return agent_fn


AGENT_FACTORIES = {
    "UC": lambda: make_uncoordinated_agent(),
    "Rule-TOU": lambda: make_rule_tou_agent(),
    "MPC-24h": lambda: make_mpc_agent(),
    "DQN": lambda: make_dqn_agent(),
    "SAC": lambda: make_sac_agent(),
    "CPO": lambda: make_cpo_agent(),
    "Lag-SAC": lambda: make_lagsac_agent(),
    "BRL-DQN": lambda: make_brl_dqn_agent(),
    "Action-Smooth": lambda: make_action_smoothing_agent(),
    "Temp-DQN": lambda: make_temperature_dqn_agent(),
}


def build_agent(agent_name: str, params: dict[str, float] | None, seed: int,
                scenario_name: str = "metro_korea"):
    """RL agent names (DQN, SAC, BRL-DQN) now load trained checkpoints from
    trained_agents/. Rule-based baselines (UC, Rule-TOU, MPC-24h, Action-Smooth, Temp-DQN)
    are kept as stylized non-RL references. CPO and Lag-SAC are dropped."""
    if agent_name == "DQN":
        return make_trained_dqn_agent(scenario_name, seed, greedy=True)
    if agent_name == "SAC":
        return make_trained_sac_agent(scenario_name, seed, greedy=False)
    if agent_name == "Lag-SAC":
        return make_trained_lagsac_agent(scenario_name, seed, greedy=False)
    if agent_name == "MARL-DQN":
        return make_trained_marl_agent(scenario_name, seed, greedy=True)
    if agent_name == "BRL-DQN":
        return make_trained_brl_dqn_agent(scenario_name, seed, params=params, variant="default")
    if agent_name == "BRL-DQN-v1":
        # Original high-reserve variant (η=1.5) for comparison with retuned default
        base_scen = scenario_name.replace("_uncertain", "")  # v1 trained only on base scenarios
        return make_trained_brl_dqn_agent(base_scen, seed, params=params, variant="v1")
    if agent_name == "Rule-TOU":
        return make_rule_tou_agent(params=params)
    if agent_name == "MPC-24h":
        return make_mpc_agent(params=params)
    if agent_name == "UC":
        return make_uncoordinated_agent()
    if agent_name == "Action-Smooth":
        return make_action_smoothing_agent(params=params, seed=seed + 71)
    if agent_name == "Temp-DQN":
        return make_temperature_dqn_agent(params=params, seed=seed + 89)
    if agent_name == "RandomDiv":
        return make_random_div_agent(params=params, seed=seed + 333)
    if agent_name == "BetaDiv":
        return make_beta_div_agent(params=params, seed=seed + 555)
    raise ValueError(f"Unsupported agent: {agent_name}")


def candidate_from_aggressiveness(agent_name: str, aggressiveness: float) -> dict[str, float]:
    a = float(np.clip(aggressiveness, 0.0, 1.0))
    if agent_name == "SAC":
        return {
            "price_cutoff": 58.0 + 40.0 * a,
            "soc_target": 0.75 + 0.20 * a,
            "critical_soc": 0.18 + 0.22 * a,
            "low_soc_idle_prob": 0.24 - 0.22 * a,
            "default_charge_prob": 0.35 + 0.50 * a,
        }
    if agent_name == "CPO":
        return {
            "reserve_margin": 0.08 + 0.22 * a,
            "price_cutoff": 62.0 + 45.0 * a,
            "soc_cap": 0.78 + 0.17 * a,
        }
    if agent_name == "Lag-SAC":
        return {
            "reserve_margin": 0.04 + 0.18 * a,
            "reserve_idle_prob": 0.30 - 0.25 * a,
            "price_cutoff": 60.0 + 35.0 * a,
            "soc_cap": 0.78 + 0.15 * a,
            "default_charge_prob": 0.55 + 0.35 * a,
        }
    if agent_name == "BRL-DQN":
        return {
            "rho": 0.08 + 0.52 * a,
            "eta": 0.6 + 2.6 * a,
            "lambda_rationality": 2.0 + 10.0 * a,
            "charge_threshold": 0.70 + 0.22 * a,
            "alpha_0": -1.2 + 0.3 * a,
            "alpha_1": 0.2 + 0.6 * a,
            "sigma": 0.7 - 0.4 * a,
        }
    raise ValueError(f"Unsupported agent for calibration: {agent_name}")


def _e2_stress_config(seed: int, p_fail: float) -> EnvV2Config:
    return EnvV2Config(
        seed=seed,
        p_fail=float(p_fail),
        n_cars=1000,
        episode_hours=168,
        forecast_horizon=24,
        forecast_noise_std=0.15,
        trip_uncertainty_std=0.20,
        trip_scale=1.35,
        init_soc_low=0.20,
        init_soc_high=0.65,
    )


def calibrate_agent_for_penalty(agent_name: str, p_fail: float) -> tuple[dict[str, float], float, float]:
    base = float(np.clip((np.log10(max(1.0, p_fail)) - 1.0) / 3.5, 0.0, 1.0))
    candidates = sorted({
        float(np.clip(base - 0.40, 0.0, 1.0)),
        float(np.clip(base - 0.20, 0.0, 1.0)),
        base,
        float(np.clip(base + 0.20, 0.0, 1.0)),
        float(np.clip(base + 0.40, 0.0, 1.0)),
    })

    best_params: dict[str, float] | None = None
    best_score = float("inf")
    best_aggr = base

    for aggr in candidates:
        params = candidate_from_aggressiveness(agent_name, aggr)
        scores = []
        for seed in TRAIN_SEEDS:
            env = EVEnvironmentV2(_e2_stress_config(seed=seed, p_fail=p_fail))
            metrics = run_single_episode(env, build_agent(agent_name, params=params, seed=seed), seed)
            scores.append(_risk_objective(metrics, p_fail=p_fail, n_cars=env.n_cars))
        mean_score = float(np.mean(scores))
        if mean_score < best_score:
            best_score = mean_score
            best_params = params
            best_aggr = aggr

    if best_params is None:
        raise RuntimeError(f"Calibration failed for {agent_name} at p_fail={p_fail}")
    return best_params, best_score, best_aggr


def run_experiment_e1(scenario_name: str = "metro_korea"):
    """E1 — main comparison. Primary controllers include trained DQN, SAC, Lag-SAC,
    MARL-DQN, and BRL-DQN, plus UC and RandomDiv references and the classical
    MPC-24h baseline."""
    print("=" * 60)
    print(f"E1: Main Comparison ({scenario_name})")
    print("=" * 60)
    results = []
    agents = ["UC", "MPC-24h", "DQN", "SAC", "Lag-SAC", "MARL-DQN", "RandomDiv", "BRL-DQN"]
    for agent_name in agents:
        for seed in MAIN_EVIDENCE_SEEDS:
            env = EVEnvironmentV2(make_scenario_config(seed=seed, scenario_name=scenario_name))
            agent_fn = build_agent(agent_name, params=None, seed=seed, scenario_name=scenario_name)
            metrics = run_single_episode(env, agent_fn, seed)
            results.append(
                ExperimentResult(
                    experiment=f"E1_{scenario_name}",
                    agent=agent_name,
                    seed=seed,
                    reliability_pct=float(metrics["reliability_pct"]),
                    avg_cost_krw=float(metrics["avg_cost_krw"]),
                    herding_index=float(metrics["herding_index"]),
                    peak_demand_kw=float(metrics["peak_demand_kw"]),
                    renewable_utilization_pct=float(metrics["renewable_utilization_pct"]),
                    failure_count=int(metrics["failure_count"]),
                    reliability_adjusted_cost=float(metrics["reliability_adjusted_cost"]),
                    hourly_demand_profile=list(metrics["hourly_demand_profile"]),
                    config={
                        "scenario_name": scenario_name,
                        "data_grounded": True,
                        "reliability_basis": "realized_mandatory_trip_events",
                        "mandatory_trip_events": int(metrics["mandatory_trip_events"]),
                    },
                )
            )
            print(f"  {agent_name:8s} seed={seed}: R={metrics['reliability_pct']:.1f}% C={metrics['avg_cost_krw']:.0f} HI={metrics['herding_index']:.0f}")
    return results


def run_experiment_e2():
    print("=" * 60)
    print("E2: Penalty Sweep with Per-Penalty Calibration")
    print("=" * 60)
    results = []
    penalties = [20, 200, 2000, 20000]
    agents = ["SAC", "CPO", "Lag-SAC", "BRL-DQN"]

    for p_fail in penalties:
        for agent_name in agents:
            best_params, train_score, aggressiveness = calibrate_agent_for_penalty(agent_name, p_fail)
            for seed in EVAL_SEEDS:
                env = EVEnvironmentV2(_e2_stress_config(seed=seed, p_fail=float(p_fail)))
                metrics = run_single_episode(env, build_agent(agent_name, params=best_params, seed=seed), seed)
                results.append(
                    ExperimentResult(
                        experiment="E2",
                        agent=agent_name,
                        seed=seed,
                        reliability_pct=float(metrics["reliability_pct"]),
                        avg_cost_krw=float(metrics["avg_cost_krw"]),
                        herding_index=float(metrics["herding_index"]),
                        peak_demand_kw=float(metrics["peak_demand_kw"]),
                        renewable_utilization_pct=float(metrics["renewable_utilization_pct"]),
                        failure_count=int(metrics["failure_count"]),
                        reliability_adjusted_cost=float(metrics["reliability_adjusted_cost"]),
                        hourly_demand_profile=list(metrics["hourly_demand_profile"]),
                        config={
                            "p_fail": float(p_fail),
                            "protocol": "per_penalty_calibration",
                            "train_seeds": TRAIN_SEEDS,
                            "eval_seeds": EVAL_SEEDS,
                            "selected_aggressiveness": aggressiveness,
                            "calibration_score": train_score,
                            "params": best_params,
                            "reliability_basis": "realized_mandatory_trip_events",
                            "mandatory_trip_events": int(metrics["mandatory_trip_events"]),
                        },
                    )
                )
            print(f"  {agent_name} p_fail={p_fail}: calibrated aggressiveness={aggressiveness:.2f}")
    return results


def run_experiment_e3(scenario_name: str = "metro_korea"):
    """E3 — behavioral ablation: same trained DQN checkpoint, different BehavioralWrapper configs.
    Isolates which behavioral ingredient drives desynchronization."""
    print("=" * 60)
    print(f"E3: Behavioral Ablation ({scenario_name})")
    print("=" * 60)
    results = []
    for name, brl_cfg in generate_ablation_configs():
        cfg_params = asdict(brl_cfg)
        for seed in MAIN_EVIDENCE_SEEDS:
            env = EVEnvironmentV2(make_scenario_config(seed=seed, scenario_name=scenario_name))
            agent_fn = make_trained_brl_dqn_agent(scenario_name, seed, params=cfg_params)
            metrics = run_single_episode(env, agent_fn, seed)
            results.append(
                ExperimentResult(
                    experiment=f"E3_{scenario_name}",
                    agent=f"BRL-{name}",
                    seed=seed,
                    reliability_pct=float(metrics["reliability_pct"]),
                    avg_cost_krw=float(metrics["avg_cost_krw"]),
                    herding_index=float(metrics["herding_index"]),
                    peak_demand_kw=float(metrics["peak_demand_kw"]),
                    renewable_utilization_pct=float(metrics["renewable_utilization_pct"]),
                    failure_count=int(metrics["failure_count"]),
                    reliability_adjusted_cost=float(metrics["reliability_adjusted_cost"]),
                    hourly_demand_profile=list(metrics["hourly_demand_profile"]),
                    config={
                        **cfg_params,
                        "scenario_name": scenario_name,
                        "reliability_basis": "realized_mandatory_trip_events",
                        "mandatory_trip_events": int(metrics["mandatory_trip_events"]),
                    },
                )
            )
    return results


def run_experiment_e4(scenario_name: str = "metro_korea"):
    """E4 — rationality sweep: vary logit λ from low (near-uniform) to high (near-argmax).
    Tests Thm 3 (Rationality Amplifies Herding) empirically."""
    print("=" * 60)
    print(f"E4: Rationality Sweep ({scenario_name})")
    print("=" * 60)
    results = []
    for lam, brl_cfg in generate_rationality_sweep():
        cfg_params = asdict(brl_cfg)
        for seed in MAIN_EVIDENCE_SEEDS:
            env = EVEnvironmentV2(make_scenario_config(seed=seed, scenario_name=scenario_name))
            agent_fn = make_trained_brl_dqn_agent(scenario_name, seed, params=cfg_params)
            metrics = run_single_episode(env, agent_fn, seed)
            results.append(
                ExperimentResult(
                    experiment=f"E4_{scenario_name}",
                    agent=f"BRL-lambda={lam}",
                    seed=seed,
                    reliability_pct=float(metrics["reliability_pct"]),
                    avg_cost_krw=float(metrics["avg_cost_krw"]),
                    herding_index=float(metrics["herding_index"]),
                    peak_demand_kw=float(metrics["peak_demand_kw"]),
                    renewable_utilization_pct=float(metrics["renewable_utilization_pct"]),
                    failure_count=int(metrics["failure_count"]),
                    reliability_adjusted_cost=float(metrics["reliability_adjusted_cost"]),
                    hourly_demand_profile=list(metrics["hourly_demand_profile"]),
                    config={
                        "lambda": lam,
                        "scenario_name": scenario_name,
                        "reliability_basis": "realized_mandatory_trip_events",
                        "mandatory_trip_events": int(metrics["mandatory_trip_events"]),
                    },
                )
            )
    return results


def run_experiment_e5():
    print("=" * 60)
    print("E5: Scalability")
    print("=" * 60)
    results = []
    for n_cars in [100, 500, 1000, 5000]:
        for agent_name in ["DQN", "SAC", "CPO", "Lag-SAC", "BRL-DQN"]:
            for seed in SEEDS:
                cfg = EnvV2Config(seed=seed, n_cars=n_cars)
                env = EVEnvironmentV2(cfg)
                metrics = run_single_episode(env, build_agent(agent_name, params=None, seed=seed), seed)
                results.append(
                    ExperimentResult(
                        experiment="E5",
                        agent=agent_name,
                        seed=seed,
                        reliability_pct=float(metrics["reliability_pct"]),
                        avg_cost_krw=float(metrics["avg_cost_krw"]),
                        herding_index=float(metrics["herding_index"]),
                        peak_demand_kw=float(metrics["peak_demand_kw"]),
                        renewable_utilization_pct=float(metrics["renewable_utilization_pct"]),
                        failure_count=int(metrics["failure_count"]),
                        reliability_adjusted_cost=float(metrics["reliability_adjusted_cost"]),
                        hourly_demand_profile=list(metrics["hourly_demand_profile"]),
                        config={
                            "n_cars": n_cars,
                            "reliability_basis": "realized_mandatory_trip_events",
                            "mandatory_trip_events": int(metrics["mandatory_trip_events"]),
                        },
                    )
                )
    return results


def run_experiment_e6():
    print("=" * 60)
    print("E6: Forecast Robustness")
    print("=" * 60)
    results = []
    for horizon in [6, 24, 72, 168]:
        for agent_name in ["DQN", "SAC", "CPO", "Lag-SAC", "BRL-DQN"]:
            for seed in SEEDS:
                cfg = EnvV2Config(seed=seed, forecast_horizon=horizon)
                env = EVEnvironmentV2(cfg)
                metrics = run_single_episode(env, build_agent(agent_name, params=None, seed=seed), seed)
                results.append(
                    ExperimentResult(
                        experiment="E6",
                        agent=agent_name,
                        seed=seed,
                        reliability_pct=float(metrics["reliability_pct"]),
                        avg_cost_krw=float(metrics["avg_cost_krw"]),
                        herding_index=float(metrics["herding_index"]),
                        peak_demand_kw=float(metrics["peak_demand_kw"]),
                        renewable_utilization_pct=float(metrics["renewable_utilization_pct"]),
                        failure_count=int(metrics["failure_count"]),
                        reliability_adjusted_cost=float(metrics["reliability_adjusted_cost"]),
                        hourly_demand_profile=list(metrics["hourly_demand_profile"]),
                        config={
                            "forecast_horizon": horizon,
                            "reliability_basis": "realized_mandatory_trip_events",
                            "mandatory_trip_events": int(metrics["mandatory_trip_events"]),
                        },
                    )
                )
    return results


def run_experiment_e7():
    print("=" * 60)
    print("E7: Sensitivity Analysis")
    print("=" * 60)
    results = []
    for params, brl_cfg in generate_sensitivity_grid("rho_eta", n_points=5):
        cfg_params = asdict(brl_cfg)
        cfg_params.update(params)
        for seed in SEEDS[:2]:
            env = EVEnvironmentV2(EnvV2Config(seed=seed))
            metrics = run_single_episode(env, make_brl_dqn_agent(params=cfg_params), seed)
            results.append(
                ExperimentResult(
                    experiment="E7",
                    agent="BRL-sensitivity",
                    seed=seed,
                    reliability_pct=float(metrics["reliability_pct"]),
                    avg_cost_krw=float(metrics["avg_cost_krw"]),
                    herding_index=float(metrics["herding_index"]),
                    peak_demand_kw=float(metrics["peak_demand_kw"]),
                    renewable_utilization_pct=float(metrics["renewable_utilization_pct"]),
                    failure_count=int(metrics["failure_count"]),
                    reliability_adjusted_cost=float(metrics["reliability_adjusted_cost"]),
                    hourly_demand_profile=list(metrics["hourly_demand_profile"]),
                    config={
                        **params,
                        "reliability_basis": "realized_mandatory_trip_events",
                        "mandatory_trip_events": int(metrics["mandatory_trip_events"]),
                    },
                )
            )
    return results


def run_experiment_e8(scenario_name: str = "metro_korea"):
    """E8 — reduced: trained DQN/SAC/BRL-DQN vs rule-based Rule-TOU/MPC-24h under uncertainty.
    Positions BRL against non-RL classical references."""
    print("=" * 60)
    print(f"E8: Uncertainty + Classical Baselines ({scenario_name})")
    print("=" * 60)
    results = []
    uncertainty_levels = [0.0, 0.1, 0.2]
    agents = ["Rule-TOU", "MPC-24h", "DQN", "SAC", "BRL-DQN"]

    for sigma in uncertainty_levels:
        for agent_name in agents:
            for seed in MAIN_EVIDENCE_SEEDS:
                cfg = make_scenario_config(
                    seed=seed,
                    scenario_name=scenario_name,
                    forecast_horizon=24,
                    forecast_noise_std=sigma,
                    trip_uncertainty_std=sigma,
                    p_fail=2000.0,
                )
                env = EVEnvironmentV2(cfg)
                agent_fn = build_agent(agent_name, params=None, seed=seed, scenario_name=scenario_name)
                metrics = run_single_episode(env, agent_fn, seed)
                results.append(
                    ExperimentResult(
                        experiment=f"E8_{scenario_name}",
                        agent=agent_name,
                        seed=seed,
                        reliability_pct=float(metrics["reliability_pct"]),
                        avg_cost_krw=float(metrics["avg_cost_krw"]),
                        herding_index=float(metrics["herding_index"]),
                        peak_demand_kw=float(metrics["peak_demand_kw"]),
                        renewable_utilization_pct=float(metrics["renewable_utilization_pct"]),
                        failure_count=int(metrics["failure_count"]),
                        reliability_adjusted_cost=float(metrics["reliability_adjusted_cost"]),
                        hourly_demand_profile=list(metrics["hourly_demand_profile"]),
                        config={
                            "scenario_name": scenario_name,
                            "data_grounded": True,
                            "forecast_noise_std": sigma,
                            "trip_uncertainty_std": sigma,
                            "reliability_basis": "realized_mandatory_trip_events",
                            "mandatory_trip_events": int(metrics["mandatory_trip_events"]),
                        },
                    )
                )
    return results


def run_experiment_e9(scenario_name: str = "metro_korea"):
    """E9 — simple baselines vs BRL-DQN. Tests whether simple temporal smoothing
    (Action-Smooth, Temp-DQN) or simple fleet diversity heuristics (RandomDiv, BetaDiv)
    replicate BRL's coordination effect without behavioral machinery."""
    print("=" * 60)
    print(f"E9: Simple Baselines ({scenario_name})")
    print("=" * 60)
    results = []
    agents = ["DQN", "Action-Smooth", "Temp-DQN", "RandomDiv", "BetaDiv", "BRL-DQN"]
    for agent_name in agents:
        for seed in MAIN_EVIDENCE_SEEDS:
            env = EVEnvironmentV2(make_scenario_config(seed=seed, scenario_name=scenario_name))
            agent_fn = build_agent(agent_name, params=None, seed=seed, scenario_name=scenario_name)
            metrics = run_single_episode(env, agent_fn, seed)
            results.append(
                ExperimentResult(
                    experiment=f"E9_{scenario_name}",
                    agent=agent_name,
                    seed=seed,
                    reliability_pct=float(metrics["reliability_pct"]),
                    avg_cost_krw=float(metrics["avg_cost_krw"]),
                    herding_index=float(metrics["herding_index"]),
                    peak_demand_kw=float(metrics["peak_demand_kw"]),
                    renewable_utilization_pct=float(metrics["renewable_utilization_pct"]),
                    failure_count=int(metrics["failure_count"]),
                    reliability_adjusted_cost=float(metrics["reliability_adjusted_cost"]),
                    hourly_demand_profile=list(metrics["hourly_demand_profile"]),
                    config={
                        "scenario_name": scenario_name,
                        "data_grounded": True,
                        "reliability_basis": "realized_mandatory_trip_events",
                        "mandatory_trip_events": int(metrics["mandatory_trip_events"]),
                    },
                )
            )
    return results


def run_experiment_e10():
    print("=" * 60)
    print("E10: Thrifty Death Timing Trap")
    print("=" * 60)
    results = []
    scenario_name = "thrifty_death_timing_trap"
    for agent_name in ["UC", "DQN", "SAC", "CPO", "Lag-SAC", "BRL-DQN"]:
        for seed in MAIN_EVIDENCE_SEEDS:
            env = EVEnvironmentV2(make_scenario_config(seed=seed, scenario_name=scenario_name))
            metrics = run_single_episode(env, build_agent(agent_name, params=None, seed=seed), seed)
            results.append(
                ExperimentResult(
                    experiment="E10",
                    agent=agent_name,
                    seed=seed,
                    reliability_pct=float(metrics["reliability_pct"]),
                    avg_cost_krw=float(metrics["avg_cost_krw"]),
                    herding_index=float(metrics["herding_index"]),
                    peak_demand_kw=float(metrics["peak_demand_kw"]),
                    renewable_utilization_pct=float(metrics["renewable_utilization_pct"]),
                    failure_count=int(metrics["failure_count"]),
                    reliability_adjusted_cost=float(metrics["reliability_adjusted_cost"]),
                    hourly_demand_profile=list(metrics["hourly_demand_profile"]),
                    config={
                        "scenario_name": scenario_name,
                        "data_grounded": True,
                        "reliability_basis": "realized_mandatory_trip_events",
                        "mandatory_trip_events": int(metrics["mandatory_trip_events"]),
                    },
                )
            )
            print(
                f"  {agent_name} seed={seed}: R={metrics['reliability_pct']:.1f}% F={metrics['failure_count']} "
                f"C={metrics['avg_cost_krw']:.0f} HI={metrics['herding_index']:.0f}"
            )
    return results


def run_experiment_e11():
    print("=" * 60)
    print("E11: Critical-State Idle Analysis")
    print("=" * 60)
    results = []
    scenario_name = "thrifty_death_timing_trap"
    for agent_name in ["DQN", "SAC", "BRL-DQN", "CPO", "Lag-SAC"]:
        for seed in MAIN_EVIDENCE_SEEDS:
            env = EVEnvironmentV2(make_scenario_config(seed=seed, scenario_name=scenario_name))
            metrics = run_single_episode(env, build_agent(agent_name, params=None, seed=seed), seed)
            results.append(
                ExperimentResult(
                    experiment="E11",
                    agent=agent_name,
                    seed=seed,
                    reliability_pct=float(metrics["reliability_pct"]),
                    avg_cost_krw=float(metrics["avg_cost_krw"]),
                    herding_index=float(metrics["herding_index"]),
                    peak_demand_kw=float(metrics["peak_demand_kw"]),
                    renewable_utilization_pct=float(metrics["renewable_utilization_pct"]),
                    failure_count=int(metrics["failure_count"]),
                    reliability_adjusted_cost=float(metrics["reliability_adjusted_cost"]),
                    hourly_demand_profile=list(metrics["hourly_demand_profile"]),
                    config={
                        "scenario_name": scenario_name,
                        "data_grounded": True,
                        "critical_state_count": int(metrics["critical_state_count"]),
                        "critical_idle_count": int(metrics["critical_idle_count"]),
                        "critical_idle_rate": float(metrics["critical_idle_rate"]),
                        "reliability_basis": "realized_mandatory_trip_events",
                        "mandatory_trip_events": int(metrics["mandatory_trip_events"]),
                    },
                )
            )
            print(
                f"  {agent_name} seed={seed}: critical={metrics['critical_state_count']} "
                f"idle={metrics['critical_idle_count']} rate={metrics['critical_idle_rate']:.3f} "
                f"R={metrics['reliability_pct']:.1f}%"
            )
    return results


def save_results(results: list[ExperimentResult], filename: str):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / filename
    data = [asdict(r) for r in results]
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Saved {len(results)} results to {path}")


RUNNERS = {
    "E1": ("E1_main_comparison_{scen}.json", run_experiment_e1),
    "E3": ("E3_ablation_{scen}.json", run_experiment_e3),
    "E4": ("E4_rationality_sweep_{scen}.json", run_experiment_e4),
    "E8": ("E8_uncertainty_baselines_{scen}.json", run_experiment_e8),
    "E9": ("E9_simple_smoothing_{scen}.json", run_experiment_e9),
}


def run_selected(experiment_ids: list[str], scenarios: list[str] | None = None):
    """Run selected experiments across the given scenarios (default: both base scenarios)."""
    scenarios = scenarios or ["metro_korea", "metro_caltech"]
    _TRAINED_CACHE.clear()
    all_results: list[ExperimentResult] = []
    for exp_id in experiment_ids:
        filename_tmpl, run_fn = RUNNERS[exp_id]
        for scen in scenarios:
            start = time.time()
            results = run_fn(scenario_name=scen)
            elapsed = time.time() - start
            save_results(results, filename_tmpl.format(scen=scen))
            all_results.extend(results)
            print(f"  -> {len(results)} results ({exp_id}/{scen}) in {elapsed:.1f}s\n")

    if all_results:
        save_results(all_results, "all_results_subset.json")


def run_all():
    run_selected(list(RUNNERS.keys()))


def parse_args():
    parser = argparse.ArgumentParser(description="Run paper experiments (trained-agent pipeline)")
    parser.add_argument(
        "--experiments",
        nargs="+",
        default=["ALL"],
        help="Experiment IDs to run: E1 E3 E4 E8 E9, or ALL",
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=["metro_korea", "metro_caltech"],
        help="Scenarios to evaluate in (default both).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    selected = [x.upper() for x in args.experiments]
    if "ALL" in selected:
        run_selected(list(RUNNERS.keys()), scenarios=args.scenarios)
    else:
        unknown = [x for x in selected if x not in RUNNERS]
        if unknown:
            raise ValueError(f"Unknown experiment IDs: {unknown}. Valid: {sorted(RUNNERS.keys())} or ALL")
        run_selected(selected, scenarios=args.scenarios)
