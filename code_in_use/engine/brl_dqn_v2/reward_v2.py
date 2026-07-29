from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt


@dataclass
class LagrangianRewardConfig:
    base_cost_scale: float = 1000.0
    base_cost_clip: float = 200.0
    failure_penalty: float = 100.0
    urgent_failure_penalty: float = 50.0
    queue_wait_penalty: float = 2.0
    peak_kw_penalty: float = 0.01
    excess_service_penalty: float = 0.05
    shortfall_penalty: float = 10.0
    low_soc_penalty: float = 2.0
    useful_service_credit: float = 40.0
    inaction_shortfall_penalty: float = 20.0
    reserve_deficit_penalty: float = 2.0
    inaction_reserve_penalty: float = 5.0
    reserve_target_soc: float = 0.75
    flexible_request_penalty: float = 0.0
    normal_request_penalty: float = 0.05
    urgent_request_penalty: float = 0.10
    defer_action_penalty: float = 0.0
    urgent_soc_margin: float = 0.05
    service_target_soc: float = 0.90
    target_deficit_penalty: float = 0.0
    deadline_deficit_penalty: float = 0.0
    negative_laxity_penalty: float = 0.0
    target_progress_credit: float = 0.0
    deadline_progress_credit: float = 0.0
    inaction_target_penalty: float = 0.0
    departure_target_deficit_penalty: float = 0.0


def compute_lagrangian_reward(
    env,
    base_rewards: npt.ArrayLike,
    info: dict[str, object],
    config: LagrangianRewardConfig | None = None,
) -> tuple[np.ndarray, dict[str, float]]:
    """Compute V2 reward components without service-floor repair.

    This is a Lagrangian-style scalar reward used by the training loop. It does
    not alter simulator physics or repair actions.
    """

    cfg = config or LagrangianRewardConfig()
    base = np.asarray(base_rewards, dtype=float)
    failures = np.asarray(info.get("failures", np.zeros_like(base, dtype=bool)), dtype=bool)
    urgent = np.asarray(env.soc < (env.anxiety_thresholds + cfg.urgent_soc_margin), dtype=bool)
    queued = np.asarray(getattr(env, "agent_queuing", np.zeros_like(base, dtype=bool)), dtype=bool)
    stored = np.asarray(getattr(env, "_last_charge_stored_actual_kwh", np.zeros_like(base)), dtype=float)
    agg_kw = float(info.get("agg_demand_kw", 0.0))
    if hasattr(env, "_urgency_features"):
        urgency = env._urgency_features()
        shortfall = np.asarray(urgency.get("energy_shortfall_norm", np.zeros_like(base)), dtype=float)
        target_deficit = np.asarray(
            urgency.get("target_energy_deficit_norm", np.maximum(0.0, cfg.service_target_soc - env.soc)),
            dtype=float,
        )
        deadline_deficit = np.asarray(
            urgency.get("deadline_energy_deficit_norm", shortfall),
            dtype=float,
        )
        deadline_laxity = np.asarray(
            urgency.get("deadline_laxity_hours_norm", np.ones_like(base)),
            dtype=float,
        )
    else:
        shortfall = np.zeros_like(base, dtype=float)
        target_deficit = np.maximum(0.0, cfg.service_target_soc - np.asarray(env.soc, dtype=float))
        deadline_deficit = shortfall.copy()
        deadline_laxity = np.ones_like(base, dtype=float)

    cost_component = np.clip(np.maximum(0.0, -base) / max(cfg.base_cost_scale, 1.0), 0.0, cfg.base_cost_clip)
    failure_component = cfg.failure_penalty * failures.astype(float)
    urgent_component = cfg.urgent_failure_penalty * (failures & urgent).astype(float)
    queue_component = cfg.queue_wait_penalty * queued.astype(float)
    peak_component = np.full(base.shape, cfg.peak_kw_penalty * agg_kw / max(1, base.size), dtype=float)
    service_component = cfg.excess_service_penalty * np.maximum(0.0, stored)
    shortfall_component = cfg.shortfall_penalty * shortfall
    target_deficit_component = cfg.target_deficit_penalty * target_deficit
    deadline_deficit_component = cfg.deadline_deficit_penalty * deadline_deficit
    negative_laxity_component = cfg.negative_laxity_penalty * np.maximum(0.0, -deadline_laxity)
    low_soc_component = cfg.low_soc_penalty * np.maximum(0.0, env.anxiety_thresholds - env.soc)
    reserve_deficit = np.maximum(0.0, cfg.reserve_target_soc - env.soc)
    reserve_component = cfg.reserve_deficit_penalty * reserve_deficit
    pre_soc = np.asarray(info.get("pre_step_soc", env.soc), dtype=float)
    pre_reserve_deficit = np.maximum(0.0, cfg.reserve_target_soc - pre_soc)
    reserve_progress = np.maximum(0.0, pre_reserve_deficit - reserve_deficit)
    pre_shortfall = np.asarray(info.get("pre_step_energy_shortfall_norm", shortfall), dtype=float)
    shortfall_progress = np.maximum(0.0, pre_shortfall - shortfall)
    pre_target_deficit = np.asarray(info.get("pre_step_target_energy_deficit_norm", target_deficit), dtype=float)
    target_progress = np.maximum(0.0, pre_target_deficit - target_deficit)
    pre_deadline_deficit = np.asarray(info.get("pre_step_deadline_energy_deficit_norm", deadline_deficit), dtype=float)
    deadline_progress = np.maximum(0.0, pre_deadline_deficit - deadline_deficit)
    trip_event = np.asarray(info.get("pre_step_mandatory_trip_event", np.zeros_like(base, dtype=bool)), dtype=bool)
    useful_service_credit = (
        cfg.useful_service_credit * np.maximum(reserve_progress, shortfall_progress)
        + cfg.target_progress_credit * target_progress
        + cfg.deadline_progress_credit * deadline_progress
    )
    primitive_actions = np.asarray(info.get("primitive_actions", np.ones_like(base)), dtype=int)
    idle = primitive_actions == 0
    primitive_action_mask = np.asarray(
        info.get("primitive_action_mask", np.ones((base.size, 4), dtype=bool)),
        dtype=bool,
    )
    if primitive_action_mask.shape != (base.size, 4):
        service_feasible = np.ones_like(base, dtype=bool)
    else:
        service_feasible = primitive_action_mask[:, 1:].any(axis=1)
    idle_while_feasible = idle & service_feasible
    inaction_component = cfg.inaction_shortfall_penalty * shortfall * idle_while_feasible.astype(float)
    inaction_reserve_component = cfg.inaction_reserve_penalty * reserve_deficit * idle_while_feasible.astype(float)
    inaction_target_component = cfg.inaction_target_penalty * target_deficit * idle_while_feasible.astype(float)
    departure_target_component = cfg.departure_target_deficit_penalty * pre_target_deficit * trip_event.astype(float)
    priority_component = np.zeros_like(base, dtype=float)
    priority_component[primitive_actions == 1] = cfg.flexible_request_penalty
    priority_component[primitive_actions == 2] = cfg.normal_request_penalty
    priority_component[primitive_actions == 3] = cfg.urgent_request_penalty

    reward = -(
        cost_component
        + failure_component
        + urgent_component
        + queue_component
        + peak_component
        + service_component
        + shortfall_component
        + target_deficit_component
        + deadline_deficit_component
        + negative_laxity_component
        + low_soc_component
        + reserve_component
        + inaction_component
        + inaction_reserve_component
        + inaction_target_component
        + departure_target_component
        + priority_component
        - useful_service_credit
    )
    components = {
        "raw_base_mean": float(base.mean()),
        "base_cost_mean": float(cost_component.mean()),
        "failure_mean": float(failure_component.mean()),
        "urgent_failure_mean": float(urgent_component.mean()),
        "queue_wait_mean": float(queue_component.mean()),
        "peak_mean": float(peak_component.mean()),
        "excess_service_mean": float(service_component.mean()),
        "shortfall_mean": float(shortfall_component.mean()),
        "target_deficit_mean": float(target_deficit_component.mean()),
        "deadline_deficit_mean": float(deadline_deficit_component.mean()),
        "negative_laxity_mean": float(negative_laxity_component.mean()),
        "low_soc_mean": float(low_soc_component.mean()),
        "useful_service_credit_mean": float(useful_service_credit.mean()),
        "target_progress_credit_mean": float((cfg.target_progress_credit * target_progress).mean()),
        "deadline_progress_credit_mean": float((cfg.deadline_progress_credit * deadline_progress).mean()),
        "reserve_deficit_mean": float(reserve_component.mean()),
        "inaction_shortfall_mean": float(inaction_component.mean()),
        "inaction_reserve_mean": float(inaction_reserve_component.mean()),
        "inaction_target_mean": float(inaction_target_component.mean()),
        "departure_target_deficit_mean": float(departure_target_component.mean()),
        "priority_request_mean": float(priority_component.mean()),
        "defer_action_mean": float(priority_component.mean()),
        "reward_mean": float(reward.mean()),
    }
    return reward.astype(np.float32), components
