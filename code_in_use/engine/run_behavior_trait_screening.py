#!/usr/bin/env python3
"""Phase 1 transparent behavior-trait screening for EV charging agents."""
from __future__ import annotations

import csv
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np


WORKSPACE = Path("/home/jia/thirfty death BRL DQN")
SCRIPTS = WORKSPACE / "scripts"
SOURCE = Path("/home/jia/thirftydeath")
for path in (WORKSPACE, SCRIPTS, SOURCE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from brl_dqn_v2.env_action_wrapper import (  # noqa: E402
    N_PRIMITIVE_ACTIONS,
    PRIMITIVE_FLEXIBLE_REQUEST,
    PRIMITIVE_IDLE,
    PRIMITIVE_NORMAL_REQUEST,
    PRIMITIVE_URGENT_REQUEST,
)
from brl_dqn_v2.obs_adapter_v2 import batch_action_mask  # noqa: E402
from brl_dqn_v2.train_eval_v2 import (  # noqa: E402
    V2RunConfig,
    _cheap_mask,
    _least_laxity_charge,
    _reserve_need,
    _target_need,
    make_env,
)
from run_ll_guarded_residual_calibration import edf_actions, location_type  # noqa: E402


SEEDS = list(range(3613, 3623))
SCENARIOS = [
    {"label": "caltech_sce_constrained", "scenario": "metro_caltech_sce"},
    {"label": "korea_constrained", "scenario": "metro_korea"},
]
POLICIES = [
    "LeastLaxity",
    "EDF",
    "BehaviorNeutralLL",
    "TraitInertiaHigh",
    "TraitNoiseHigh",
    "TraitAttentionDropHigh",
    "TraitRationalityLow",
    "TraitSocAnxietyHigh",
    "TraitReserveInflationHigh",
    "TraitPriceHerdingHigh",
    "TraitImpatienceHigh",
    "TraitUrgencySalienceHigh",
    "TraitRiskAverseReportingHigh",
]
CRITICAL_NO_DELIV_SLACK = 24
OVERSUBSCRIPTION_VEHICLE_SLACK = 24
TOTAL_NO_DELIV_FAILURE_DELTA = 117


@dataclass
class PolicyState:
    prev_actions: np.ndarray | None = None


def run_config(seed: int, scenario: str) -> V2RunConfig:
    return V2RunConfig(
        scenario=scenario,
        seed=seed,
        n_cars=80,
        episode_hours=168,
        forecast_horizon=24,
        n_slots_home=40,
        n_slots_work=5,
        n_slots_public=5,
        max_queue_wait_steps=4,
    )


def _arrays(env, obs: dict[str, object]) -> dict[str, np.ndarray]:
    n = env.n_cars
    return {
        "masks": batch_action_mask(obs, n),
        "soc": np.asarray(obs["soc"], dtype=float),
        "theta": np.asarray(obs["anxiety_thresholds"], dtype=float),
        "reserve": _reserve_need(env, obs),
        "target": _target_need(env, obs),
        "target_deficit": np.asarray(obs.get("target_energy_deficit_norm", np.zeros(n)), dtype=float),
        "deadline_deficit": np.asarray(obs.get("deadline_energy_deficit_norm", np.zeros(n)), dtype=float),
        "time_to": np.asarray(obs.get("time_to_next_mandatory_norm", np.ones(n)), dtype=float),
        "laxity": np.asarray(obs.get("deadline_laxity_hours_norm", np.ones(n)), dtype=float),
    }


def _service_critical(values: dict[str, np.ndarray]) -> np.ndarray:
    return (
        values["reserve"]
        | (values["deadline_deficit"] > 0.0)
        | (values["time_to"] <= (24.0 / 168.0))
        | (values["laxity"] <= 0.25)
    )


def _score(values: dict[str, np.ndarray], urgency_boost: float = 1.0) -> np.ndarray:
    critical = _service_critical(values)
    return (
        100.0 * values["reserve"].astype(float)
        + 80.0 * (values["deadline_deficit"] > 0.0).astype(float) * urgency_boost
        + 40.0 * (values["time_to"] <= (24.0 / 168.0)).astype(float) * urgency_boost
        + 15.0 * values["target_deficit"]
        - 15.0 * values["laxity"]
        + 25.0 * critical.astype(float)
    )


def _priority_actions(values: dict[str, np.ndarray], selected: np.ndarray, urgent_salience: bool = False) -> np.ndarray:
    actions = np.full(selected.shape[0], PRIMITIVE_IDLE, dtype=np.int64)
    critical = _service_critical(values)
    urgent_ok = values["masks"][:, PRIMITIVE_URGENT_REQUEST]
    if urgent_salience:
        urgent = selected & critical & urgent_ok
        actions[urgent] = PRIMITIVE_URGENT_REQUEST
        actions[selected & ~urgent] = PRIMITIVE_NORMAL_REQUEST
    else:
        actions[selected] = PRIMITIVE_NORMAL_REQUEST
    return actions


def _select_cap_limited(
    env,
    values: dict[str, np.ndarray],
    eligible: np.ndarray,
    score: np.ndarray,
    rng: np.random.Generator,
    stochastic: bool = False,
    urgent_salience: bool = False,
) -> np.ndarray:
    selected = np.zeros(env.n_cars, dtype=bool)
    for loc_name in ("home", "work", "public"):
        members = np.array([i for i in np.where(eligible)[0] if location_type(env, int(i)) == loc_name], dtype=int)
        if members.size == 0:
            continue
        queued = len(getattr(env, "charger_queues", {}).get(loc_name, []))
        remaining = max(0, int(env.n_slots[loc_name]) - int(queued))
        if remaining <= 0:
            continue
        if stochastic and members.size > remaining:
            logits = score[members].astype(float)
            logits = logits - float(np.max(logits))
            probs = np.exp(logits / 40.0)
            probs = probs / max(float(probs.sum()), 1.0e-12)
            chosen = rng.choice(members, size=remaining, replace=False, p=probs)
        else:
            order = sorted(members.tolist(), key=lambda i: (-float(score[i]), int(i)))
            chosen = np.asarray(order[:remaining], dtype=int)
        selected[chosen] = True
    return _priority_actions(values, selected, urgent_salience=urgent_salience)


def least_laxity_actions(env, obs: dict[str, object]) -> np.ndarray:
    masks = batch_action_mask(obs, env.n_cars)
    charge = _least_laxity_charge(env, obs, int(env.t), masks[:, PRIMITIVE_NORMAL_REQUEST])
    return np.where(charge, PRIMITIVE_NORMAL_REQUEST, PRIMITIVE_IDLE).astype(np.int64)


def neutral_rule_actions(env, obs: dict[str, object], rng: np.random.Generator, stochastic: bool = False) -> np.ndarray:
    values = _arrays(env, obs)
    eligible = values["masks"][:, PRIMITIVE_NORMAL_REQUEST] & values["target"]
    return _select_cap_limited(env, values, eligible, _score(values), rng, stochastic=stochastic)


def apply_inertia(env, base: np.ndarray, values: dict[str, np.ndarray], state: PolicyState, rng: np.random.Generator) -> np.ndarray:
    if state.prev_actions is None:
        state.prev_actions = np.full(env.n_cars, PRIMITIVE_IDLE, dtype=np.int64)
        return base
    keep = rng.random(env.n_cars) < 0.70
    prev = state.prev_actions.copy()
    valid = values["masks"][np.arange(env.n_cars), np.clip(prev, 0, N_PRIMITIVE_ACTIONS - 1)]
    out = np.where(keep & valid, prev, base).astype(np.int64)
    return out


def behavior_actions(
    env,
    obs: dict[str, object],
    policy: str,
    rng: np.random.Generator,
    is_cheap: np.ndarray,
    state: PolicyState,
) -> np.ndarray:
    values = _arrays(env, obs)
    masks = values["masks"]
    available = masks[:, PRIMITIVE_NORMAL_REQUEST]
    score = _score(values)
    critical = _service_critical(values)

    if policy == "LeastLaxity":
        actions = least_laxity_actions(env, obs)
    elif policy == "EDF":
        actions = edf_actions(env, obs)
    elif policy == "BehaviorNeutralLL":
        actions = least_laxity_actions(env, obs)
    elif policy == "TraitInertiaHigh":
        base = least_laxity_actions(env, obs)
        actions = apply_inertia(env, base, values, state, rng)
    elif policy == "TraitNoiseHigh":
        actions = least_laxity_actions(env, obs)
        mistake = rng.random(env.n_cars) < 0.15
        drop = mistake & (actions != PRIMITIVE_IDLE)
        add = mistake & (actions == PRIMITIVE_IDLE) & available & values["target"]
        actions[drop] = PRIMITIVE_IDLE
        actions[add] = PRIMITIVE_NORMAL_REQUEST
    elif policy == "TraitAttentionDropHigh":
        actions = least_laxity_actions(env, obs)
        drop = (rng.random(env.n_cars) < 0.25) & (actions != PRIMITIVE_IDLE)
        actions[drop] = PRIMITIVE_IDLE
    elif policy == "TraitRationalityLow":
        actions = neutral_rule_actions(env, obs, rng, stochastic=True)
    elif policy == "TraitSocAnxietyHigh":
        high_target = values["soc"] < 0.95
        selected = available & high_target
        actions = np.where(selected, PRIMITIVE_FLEXIBLE_REQUEST, PRIMITIVE_IDLE).astype(np.int64)
        actions[selected & critical] = PRIMITIVE_NORMAL_REQUEST
    elif policy == "TraitReserveInflationHigh":
        inflated_reserve = values["soc"] < (values["theta"] + 0.25)
        selected = available & (values["target"] | inflated_reserve)
        actions = np.where(selected, PRIMITIVE_FLEXIBLE_REQUEST, PRIMITIVE_IDLE).astype(np.int64)
        actions[selected & (critical | inflated_reserve)] = PRIMITIVE_NORMAL_REQUEST
    elif policy == "TraitPriceHerdingHigh":
        floor = _select_cap_limited(env, values, available & critical, score, rng, urgent_salience=True)
        optional = available & values["target"] & ~critical & bool(is_cheap[int(env.t) % len(is_cheap)])
        actions = floor.copy()
        actions[(actions == PRIMITIVE_IDLE) & optional] = PRIMITIVE_FLEXIBLE_REQUEST
    elif policy == "TraitImpatienceHigh":
        crowded = np.zeros(env.n_cars, dtype=bool)
        target_available = available & values["target"]
        for loc_name in ("home", "work", "public"):
            members = np.array([i for i in np.where(target_available)[0] if location_type(env, int(i)) == loc_name], dtype=int)
            if members.size == 0:
                continue
            likely_wait = len(env.charger_queues[loc_name]) > 0 or members.size > int(env.n_slots[loc_name])
            crowded[members] = bool(likely_wait)
        eligible = available & (critical | (values["target"] & ~crowded))
        actions = _select_cap_limited(env, values, eligible, score, rng, urgent_salience=True)
    elif policy == "TraitUrgencySalienceHigh":
        eligible = available & (critical | values["target"])
        actions = _select_cap_limited(env, values, eligible, _score(values, urgency_boost=1.5), rng, urgent_salience=True)
    elif policy == "TraitRiskAverseReportingHigh":
        risk_values = dict(values)
        risk_values["time_to"] = np.maximum(0.0, values["time_to"] - (24.0 / 168.0))
        risk_values["deadline_deficit"] = np.maximum(values["deadline_deficit"], 0.5 * values["target_deficit"])
        perceived_need = values["soc"] < 0.95
        eligible = available & (values["target"] | perceived_need | _service_critical(risk_values))
        risk_score = _score(risk_values, urgency_boost=1.25) + 20.0 * perceived_need.astype(float)
        actions = _select_cap_limited(env, risk_values, eligible, risk_score, rng, urgent_salience=True)
    else:
        raise ValueError(policy)

    state.prev_actions = actions.copy()
    return actions.astype(np.int64)


def loc_request_counts(env, actions: np.ndarray) -> dict[str, int]:
    counts = {t: 0 for t in ("home", "work", "public")}
    for i in np.where(np.asarray(actions) != PRIMITIVE_IDLE)[0]:
        loc = location_type(env, int(i))
        if loc is not None:
            counts[loc] += 1
    return counts


def update_contention_counters(env, actions: np.ndarray, counters: dict[str, int]) -> None:
    request_counts = loc_request_counts(env, actions)
    counters["request_count"] += int(sum(request_counts.values()))
    for loc, requests in request_counts.items():
        queued_before = len(env.charger_queues[loc])
        cap = int(env.n_slots[loc])
        excess = max(0, queued_before + requests - cap)
        if excess > 0:
            counters["oversubscription_loc_steps"] += 1
            counters["oversubscription_vehicle_steps"] += int(excess)


def evaluate(seed: int, scenario_label: str, scenario: str, policy: str) -> dict[str, object]:
    cfg = run_config(seed, scenario)
    env = make_env(cfg, seed=seed)
    obs = env.reset()
    rng = np.random.default_rng(seed + 410_000 + 101 * POLICIES.index(policy))
    state = PolicyState()
    prices = np.asarray(env.price_schedule[: env.config.episode_hours], dtype=float)
    is_cheap = _cheap_mask(prices)
    demand_kw: list[float] = []
    action_counts = np.zeros(N_PRIMITIVE_ACTIONS, dtype=int)
    per_vehicle_delivered = np.zeros(env.n_cars, dtype=float)
    urgent_trip_events = 0
    urgent_trip_failures = 0
    counters = {
        "request_count": 0,
        "admitted_count": 0,
        "oversubscription_loc_steps": 0,
        "oversubscription_vehicle_steps": 0,
        "requested_not_delivered_count": 0,
        "critical_requested_not_delivered_count": 0,
        "flexible_requested_not_delivered_count": 0,
        "cheap_window_request_count": 0,
        "charge_above_target_request_count": 0,
        "low_laxity_missed_charge_count": 0,
    }
    done = False
    while not done:
        t = int(env.t)
        values = _arrays(env, obs)
        actions = behavior_actions(env, obs, policy, rng, is_cheap, state)
        requested = actions != PRIMITIVE_IDLE
        update_contention_counters(env, actions, counters)
        for a in range(N_PRIMITIVE_ACTIONS):
            action_counts[a] += int((actions == a).sum())
        if bool(is_cheap[t % len(is_cheap)]):
            counters["cheap_window_request_count"] += int(requested.sum())
        counters["charge_above_target_request_count"] += int((requested & ~values["target"]).sum())
        low_laxity_need = values["masks"][:, PRIMITIVE_NORMAL_REQUEST] & _service_critical(values)
        counters["low_laxity_missed_charge_count"] += int((low_laxity_need & ~requested).sum())
        critical_requested = requested & low_laxity_need
        flexible_requested = actions == PRIMITIVE_FLEXIBLE_REQUEST

        realized = getattr(env, "realized_mandatory_trip_schedule", None)
        if realized is not None and t < realized.shape[1]:
            trip_events = np.asarray(realized[:, t] > 0.0, dtype=bool)
        else:
            trip_events = np.zeros(env.n_cars, dtype=bool)
        pre_urgent = _service_critical(values) | (values["soc"] <= values["theta"] + 0.05)
        urgent_trip_mask = trip_events & pre_urgent

        obs, _, done, info = env.step(actions)
        stored = np.asarray(getattr(env, "_last_charge_stored_actual_kwh", np.zeros(env.n_cars)), dtype=float)
        counters["requested_not_delivered_count"] += int((requested & (stored <= 1.0e-9)).sum())
        counters["critical_requested_not_delivered_count"] += int((critical_requested & (stored <= 1.0e-9)).sum())
        counters["flexible_requested_not_delivered_count"] += int((flexible_requested & (stored <= 1.0e-9)).sum())
        counters["admitted_count"] += int(sum(int(env.admitted_history[loc][-1]) for loc in ("home", "work", "public")))
        failures = np.asarray(info.get("failures", np.zeros(env.n_cars, dtype=bool)), dtype=bool)
        urgent_trip_events += int(urgent_trip_mask.sum())
        urgent_trip_failures += int((urgent_trip_mask & failures).sum())
        demand_kw.append(float(info.get("agg_demand_kw", 0.0)))
        per_vehicle_delivered += stored

    mandatory_events = max(1, env.count_mandatory_trip_events(realized=True))
    demand = np.asarray(demand_kw, dtype=float)
    peak = float(demand.max()) if demand.size else 0.0
    mean = float(demand.mean()) if demand.size else 0.0
    urgent_denom = max(1, urgent_trip_events)
    waits = np.asarray(env.agent_wait_time, dtype=float)
    request_count = max(1, int(counters["request_count"]))
    row = {
        "scenario_label": scenario_label,
        "scenario": scenario,
        "seed": int(seed),
        "policy": policy,
        "reliability_pct": 100.0 * (1.0 - env.failure_count / mandatory_events),
        "failure_count": int(env.failure_count),
        "mandatory_events": int(mandatory_events),
        "urgent_trip_reliability_pct": 100.0 * (1.0 - urgent_trip_failures / urgent_denom),
        "urgent_trip_failure_count": int(urgent_trip_failures),
        "urgent_trip_events": int(urgent_trip_events),
        "delivered_kwh_per_vehicle": float(per_vehicle_delivered.mean()),
        "peak_demand_kw": peak,
        "mean_demand_kw": mean,
        "coincidence_factor": float(peak / max(mean, 1.0e-9)) if mean > 0.0 else 0.0,
        "p95_wait_minutes": float(np.percentile(waits, 95) * 60.0),
        "mean_wait_minutes": float(waits.mean() * 60.0),
        "max_queue": {k: int(v) for k, v in env.max_queue_length_seen.items()},
        "queue_abandonments_location_total": int(np.asarray(env.queue_abandonments_loc).sum()),
        "queue_abandonments_timeout_total": int(np.asarray(env.queue_abandonments_timeout).sum()),
        "action_counts": action_counts.astype(int).tolist(),
        "cheap_window_request_share": float(counters["cheap_window_request_count"] / request_count),
        "charge_above_target_request_share": float(counters["charge_above_target_request_count"] / request_count),
        "claim_boundary": "Phase 1 diagnostic screening; no policy promotion.",
    }
    row.update(counters)
    return row


def se(values: list[float]) -> float:
    arr = np.asarray(values, dtype=float)
    if arr.size <= 1:
        return 0.0
    return float(arr.std(ddof=1) / np.sqrt(arr.size))


def classify_policy(vals: list[dict[str, object]], anchors: dict[tuple[str, int], dict[str, object]]) -> dict[str, object]:
    paired = [(row, anchors[(str(row["scenario_label"]), int(row["seed"]))]) for row in vals]
    rel_delta = np.asarray([float(row["reliability_pct"]) - float(anchor["reliability_pct"]) for row, anchor in paired])
    delivered_ratio = np.asarray([
        float(row["delivered_kwh_per_vehicle"]) / max(float(anchor["delivered_kwh_per_vehicle"]), 1.0e-9)
        for row, anchor in paired
    ])
    peak_ratio = np.asarray([
        float(row["peak_demand_kw"]) / max(float(anchor["peak_demand_kw"]), 1.0e-9)
        for row, anchor in paired
    ])
    no_deliv_delta = np.asarray([
        int(row["requested_not_delivered_count"]) - int(anchor["requested_not_delivered_count"])
        for row, anchor in paired
    ])
    critical_no_deliv_delta = np.asarray([
        int(row["critical_requested_not_delivered_count"]) - int(anchor.get("critical_requested_not_delivered_count", 0))
        for row, anchor in paired
    ])
    oversub_delta = np.asarray([
        int(row["oversubscription_vehicle_steps"]) - int(anchor["oversubscription_vehicle_steps"])
        for row, anchor in paired
    ])
    gate_rows = [
        (
            float(row["reliability_pct"]) >= float(anchor["reliability_pct"]) - 0.5
            and float(row["delivered_kwh_per_vehicle"]) >= 0.95 * float(anchor["delivered_kwh_per_vehicle"])
            and int(row["critical_requested_not_delivered_count"]) <= int(anchor.get("critical_requested_not_delivered_count", 0)) + CRITICAL_NO_DELIV_SLACK
            and int(row["oversubscription_vehicle_steps"]) <= int(anchor["oversubscription_vehicle_steps"]) + OVERSUBSCRIPTION_VEHICLE_SLACK
        )
        for row, anchor in paired
    ]
    classes: list[str] = []
    if float(rel_delta.mean()) < -0.5 or not all(
        float(row["reliability_pct"]) >= float(anchor["reliability_pct"]) - 0.5 for row, anchor in paired
    ):
        classes.append("service_failure")
    if float(delivered_ratio.mean()) < 0.95 or not all(
        float(row["delivered_kwh_per_vehicle"]) >= 0.95 * float(anchor["delivered_kwh_per_vehicle"]) for row, anchor in paired
    ):
        classes.append("energy_under_delivery")
    if (
        float(critical_no_deliv_delta.mean()) > CRITICAL_NO_DELIV_SLACK
        or float(oversub_delta.mean()) > OVERSUBSCRIPTION_VEHICLE_SLACK
        or float(no_deliv_delta.mean()) > TOTAL_NO_DELIV_FAILURE_DELTA
    ):
        classes.append("queue_contention_failure")
    gate_pass = bool(all(gate_rows))
    if gate_pass and float(peak_ratio.mean()) > 1.05:
        classes.append("grid_failure")
    if gate_pass and float(peak_ratio.mean()) <= 0.95:
        classes.append("protective_trait")
    if gate_pass and not classes:
        classes.append("benign_trait")
    return {
        "service_gate_pass": gate_pass,
        "service_gate_pass_rows": int(sum(gate_rows)),
        "service_gate_total_rows": int(len(gate_rows)),
        "mean_reliability_delta_vs_ll": float(rel_delta.mean()),
        "mean_delivered_ratio_vs_ll": float(delivered_ratio.mean()),
        "mean_peak_ratio_vs_ll": float(peak_ratio.mean()),
        "mean_requested_not_delivered_delta_vs_ll": float(no_deliv_delta.mean()),
        "mean_critical_requested_not_delivered_delta_vs_ll": float(critical_no_deliv_delta.mean()),
        "mean_oversubscription_vehicle_delta_vs_ll": float(oversub_delta.mean()),
        "failure_classes": classes,
    }


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    anchors = {
        (str(row["scenario_label"]), int(row["seed"])): row
        for row in rows
        if str(row["policy"]) == "LeastLaxity"
    }
    expected_anchor_keys = {
        (str(scenario_spec["label"]), int(seed))
        for scenario_spec in SCENARIOS
        for seed in SEEDS
    }
    missing = sorted(expected_anchor_keys - set(anchors))
    if missing:
        raise RuntimeError(f"missing LeastLaxity anchor rows: {missing}")
    by_policy: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_policy.setdefault(str(row["policy"]), []).append(row)
    policy_summaries = []
    for policy, vals in by_policy.items():
        metrics = {
            "policy": policy,
            "n": len(vals),
            "reliability_mean": float(np.mean([float(v["reliability_pct"]) for v in vals])),
            "reliability_se": se([float(v["reliability_pct"]) for v in vals]),
            "delivered_kwh_per_vehicle_mean": float(np.mean([float(v["delivered_kwh_per_vehicle"]) for v in vals])),
            "delivered_kwh_per_vehicle_se": se([float(v["delivered_kwh_per_vehicle"]) for v in vals]),
            "peak_demand_kw_mean": float(np.mean([float(v["peak_demand_kw"]) for v in vals])),
            "peak_demand_kw_se": se([float(v["peak_demand_kw"]) for v in vals]),
            "p95_wait_minutes_mean": float(np.mean([float(v["p95_wait_minutes"]) for v in vals])),
            "p95_wait_minutes_se": se([float(v["p95_wait_minutes"]) for v in vals]),
            "coincidence_factor_mean": float(np.mean([float(v["coincidence_factor"]) for v in vals])),
            "coincidence_factor_se": se([float(v["coincidence_factor"]) for v in vals]),
            "requested_not_delivered_mean": float(np.mean([int(v["requested_not_delivered_count"]) for v in vals])),
            "requested_not_delivered_se": se([int(v["requested_not_delivered_count"]) for v in vals]),
            "critical_requested_not_delivered_mean": float(np.mean([int(v["critical_requested_not_delivered_count"]) for v in vals])),
            "critical_requested_not_delivered_se": se([int(v["critical_requested_not_delivered_count"]) for v in vals]),
            "oversubscription_vehicle_steps_mean": float(np.mean([int(v["oversubscription_vehicle_steps"]) for v in vals])),
            "oversubscription_vehicle_steps_se": se([int(v["oversubscription_vehicle_steps"]) for v in vals]),
            "cheap_window_request_share_mean": float(np.mean([float(v["cheap_window_request_share"]) for v in vals])),
            "charge_above_target_request_share_mean": float(np.mean([float(v["charge_above_target_request_share"]) for v in vals])),
            "low_laxity_missed_charge_mean": float(np.mean([int(v["low_laxity_missed_charge_count"]) for v in vals])),
        }
        if policy == "LeastLaxity":
            metrics.update(
                {
                    "service_gate_pass": True,
                    "service_gate_pass_rows": len(vals),
                    "service_gate_total_rows": len(vals),
                    "mean_reliability_delta_vs_ll": 0.0,
                    "mean_delivered_ratio_vs_ll": 1.0,
                    "mean_peak_ratio_vs_ll": 1.0,
                    "mean_requested_not_delivered_delta_vs_ll": 0.0,
                    "mean_critical_requested_not_delivered_delta_vs_ll": 0.0,
                    "mean_oversubscription_vehicle_delta_vs_ll": 0.0,
                    "failure_classes": ["anchor"],
                }
            )
        elif policy == "EDF":
            metrics.update(classify_policy(vals, anchors))
            metrics["failure_classes"] = ["anchor_edf"]
        else:
            metrics.update(classify_policy(vals, anchors))
        policy_summaries.append(metrics)
    policy_summaries.sort(key=lambda row: str(row["policy"]))
    return {
        "status": "COMPLETE",
        "seeds": SEEDS,
        "scenarios": SCENARIOS,
        "policies": POLICIES,
        "thresholds": {
            "critical_requested_not_delivered_slack": CRITICAL_NO_DELIV_SLACK,
            "oversubscription_vehicle_slack": OVERSUBSCRIPTION_VEHICLE_SLACK,
            "total_requested_not_delivered_failure_delta": TOTAL_NO_DELIV_FAILURE_DELTA,
        },
        "claim_boundary": "Phase 1 diagnostic behavior-trait screening; no policy promotion.",
        "policy_summaries": policy_summaries,
    }


def csv_value(value: object) -> object:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value


def write_outputs(rows: list[dict[str, object]], summary: dict[str, object]) -> None:
    result_dir = WORKSPACE / "results" / "behavior_trait_screening"
    artifact = WORKSPACE / "artifacts" / "behavior_trait_screening_summary.md"
    failure_map = WORKSPACE / "artifacts" / "behavior_failure_map.md"
    result_dir.mkdir(parents=True, exist_ok=True)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    json_path = result_dir / "behavior_trait_screening_result.json"
    csv_path = result_dir / "behavior_trait_screening_rows.csv"
    json_path.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    fieldnames = [
        "scenario_label",
        "scenario",
        "seed",
        "policy",
        "reliability_pct",
        "urgent_trip_reliability_pct",
        "delivered_kwh_per_vehicle",
        "peak_demand_kw",
        "mean_demand_kw",
        "coincidence_factor",
        "p95_wait_minutes",
        "mean_wait_minutes",
        "request_count",
        "admitted_count",
        "oversubscription_loc_steps",
        "oversubscription_vehicle_steps",
        "requested_not_delivered_count",
        "critical_requested_not_delivered_count",
        "flexible_requested_not_delivered_count",
        "queue_abandonments_location_total",
        "queue_abandonments_timeout_total",
        "cheap_window_request_share",
        "charge_above_target_request_share",
        "low_laxity_missed_charge_count",
        "failure_count",
        "mandatory_events",
        "max_queue",
        "action_counts",
        "claim_boundary",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: csv_value(row.get(name, "")) for name in fieldnames})

    lines = [
        "# Behavior Trait Screening Summary",
        "",
        f"Status: `{summary['status']}`",
        f"Claim boundary: {summary['claim_boundary']}",
        "",
        "Values are mean +/- standard error across paired scenario/seed rows.",
        "",
        "| policy | gate | classes | rel | kWh/veh | peak | p95 wait | req no-deliv | critical no-deliv | peak ratio vs LL | kWh ratio vs LL |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["policy_summaries"]:
        classes = ",".join(row["failure_classes"])
        gate = f"{row['service_gate_pass_rows']}/{row['service_gate_total_rows']}"
        lines.append(
            f"| {row['policy']} | {gate} | `{classes}` | "
            f"{row['reliability_mean']:.3f}+/-{row['reliability_se']:.3f} | "
            f"{row['delivered_kwh_per_vehicle_mean']:.3f}+/-{row['delivered_kwh_per_vehicle_se']:.3f} | "
            f"{row['peak_demand_kw_mean']:.3f}+/-{row['peak_demand_kw_se']:.3f} | "
            f"{row['p95_wait_minutes_mean']:.3f}+/-{row['p95_wait_minutes_se']:.3f} | "
            f"{row['requested_not_delivered_mean']:.3f}+/-{row['requested_not_delivered_se']:.3f} | "
            f"{row['critical_requested_not_delivered_mean']:.3f}+/-{row['critical_requested_not_delivered_se']:.3f} | "
            f"{row['mean_peak_ratio_vs_ll']:.3f} | {row['mean_delivered_ratio_vs_ll']:.3f} |"
        )
    lines.extend(["", "## Artifacts", "", f"- JSON: `{json_path}`", f"- CSV: `{csv_path}`", f"- Failure map: `{failure_map}`"])
    artifact.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fmap = [
        "# Behavior Failure Map",
        "",
        "Failure classes are assigned from paired deltas against `LeastLaxity`.",
        "",
        "| policy | service gate | failure classes | rel delta | kWh ratio | peak ratio | no-deliv delta | critical no-deliv delta | oversub veh delta |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["policy_summaries"]:
        gate = f"{row['service_gate_pass_rows']}/{row['service_gate_total_rows']}"
        fmap.append(
            f"| {row['policy']} | {gate} | `{','.join(row['failure_classes'])}` | "
            f"{row['mean_reliability_delta_vs_ll']:.3f} | {row['mean_delivered_ratio_vs_ll']:.3f} | "
            f"{row['mean_peak_ratio_vs_ll']:.3f} | {row['mean_requested_not_delivered_delta_vs_ll']:.3f} | "
            f"{row['mean_critical_requested_not_delivered_delta_vs_ll']:.3f} | "
            f"{row['mean_oversubscription_vehicle_delta_vs_ll']:.3f} |"
        )
    failure_map.write_text("\n".join(fmap) + "\n", encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {csv_path}")
    print(f"wrote {artifact}")
    print(f"wrote {failure_map}")
    print(json.dumps(summary, indent=2, sort_keys=True))


def main() -> int:
    start = time.time()
    rows = []
    for scenario_spec in SCENARIOS:
        for seed in SEEDS:
            for policy in POLICIES:
                rows.append(evaluate(seed, scenario_spec["label"], scenario_spec["scenario"], policy))
    summary = summarize(rows)
    summary["wall_seconds"] = time.time() - start
    write_outputs(rows, summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
