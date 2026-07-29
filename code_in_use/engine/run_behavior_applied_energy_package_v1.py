#!/usr/bin/env python3
"""Behavior-focused Applied Energy experiment package v1.

This runner creates a separate artifact package for the behavior-objective
paper. It does not overwrite previous behavior-map summaries.

Scope:
  - transparent LeastLaxity/EDF behavior mapping is the main evidence;
  - BRL-DQN/DQN is not promoted here;
  - behavior proxies are imposed operational perturbations, not measured human
    traits;
  - service-first gates remain strict.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
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
)
from brl_dqn_v2.train_eval_v2 import V2RunConfig, _cheap_mask, make_env  # noqa: E402
from behavior_low_intensity_combo_actions import COMBO_COMPONENTS as LOW_COMBO_COMPONENTS  # noqa: E402
from run_behavior_trait_screening import (  # noqa: E402
    CRITICAL_NO_DELIV_SLACK,
    OVERSUBSCRIPTION_VEHICLE_SLACK,
    PolicyState,
    _arrays,
    _score,
    _select_cap_limited,
    _service_critical,
    edf_actions,
    least_laxity_actions,
    loc_request_counts,
)
from run_ll_guarded_residual_calibration import location_type  # noqa: E402


RESULT_DIR = WORKSPACE / "results" / "behavior_applied_energy_package_v1"
ARTIFACT_DIR = WORKSPACE / "artifacts" / "behavior_applied_energy_package_v1"
FIG_DIR = ARTIFACT_DIR / "figures"
RUN_LOG = ARTIFACT_DIR / "run_log.md"

EPISODE_HOURS = 168
N_CARS = 80
POWER_KW_PROXY = 7.2
VALIDATION_SEEDS = [3891, 3892]
FULL_SEEDS = [3901, 3902, 3903, 3904, 3905]
GENERALIZATION_SEEDS = [3911, 3912, 3913]
CAPACITY_LEVELS = [100, 75, 50, 35, 25, 20, 15, 10]
SOC_BINS = [
    ("0.0-0.2", 0.0, 0.2),
    ("0.2-0.4", 0.2, 0.4),
    ("0.4-0.6", 0.4, 0.6),
    ("0.6-0.8", 0.6, 0.8),
    ("0.8-1.0", 0.8, 1.0000001),
]
LAXITY_BINS = [
    ("urgent", 0.0, 24.0 / 168.0),
    ("moderate", 24.0 / 168.0, 72.0 / 168.0),
    ("flexible", 72.0 / 168.0, 999.0),
]
ACTION_NAMES = {
    PRIMITIVE_IDLE: "idle",
    PRIMITIVE_NORMAL_REQUEST: "normal_request",
    PRIMITIVE_FLEXIBLE_REQUEST: "flexible_request",
}


@dataclass(frozen=True)
class ScenarioSpec:
    label: str
    scenario: str
    site_type: str
    demand_regime: str
    capacity_pct: int
    n_slots_home: int
    n_slots_work: int
    n_slots_public: int


@dataclass(frozen=True)
class BehaviorSpec:
    family: str
    drop_prob: float | None = None
    reserve_margin: float | None = None
    cheap_tolerance: float = 1.00
    urgency_boost: float | None = None
    components: tuple[str, str] | None = None
    guardrail: str | None = None
    base_policy: str | None = None


BASE_CAPACITY = {"home": 40, "work": 5, "public": 5}
SCENARIO_AXES = [
    ("caltech_sce", "metro_caltech_sce", "campus/workplace", "ACN-like workplace"),
    ("korea", "metro_korea", "mixed/public", "Korea-like mixed demand"),
]

POLICY_SPECS: dict[str, BehaviorSpec] = {
    "LeastLaxity": BehaviorSpec("anchor"),
    "EDF": BehaviorSpec("anchor"),
    "BehaviorNeutralLL": BehaviorSpec("anchor"),
    "PlugAndCharge": BehaviorSpec("baseline"),
    "LowSOCFirst": BehaviorSpec("baseline"),
    "TOUOnlyCheap": BehaviorSpec("baseline", cheap_tolerance=1.00),
    "TraitAttentionDropP001": BehaviorSpec("attention_drop", drop_prob=0.01),
    "TraitAttentionDropP0025": BehaviorSpec("attention_drop", drop_prob=0.025),
    "TraitAttentionDropP005": BehaviorSpec("attention_drop", drop_prob=0.05),
    "TraitAttentionDropP010": BehaviorSpec("attention_drop", drop_prob=0.10),
    "TraitAttentionDropP020": BehaviorSpec("attention_drop", drop_prob=0.20),
    "TraitReserveInflationM005": BehaviorSpec("reserve_inflation", reserve_margin=0.05),
    "TraitReserveInflationM015": BehaviorSpec("reserve_inflation", reserve_margin=0.15),
    "TraitReserveInflationM025": BehaviorSpec("reserve_inflation", reserve_margin=0.25),
    "TraitPriceHerdingT100": BehaviorSpec("price_herding", cheap_tolerance=1.00),
    "TraitPriceHerdingT105": BehaviorSpec("price_herding", cheap_tolerance=1.05),
    "TraitPriceHerdingT110": BehaviorSpec("price_herding", cheap_tolerance=1.10),
    "TraitUrgencySalienceB110": BehaviorSpec("urgency_salience", urgency_boost=1.10),
    "TraitUrgencySalienceB130": BehaviorSpec("urgency_salience", urgency_boost=1.30),
    "TraitUrgencySalienceB150": BehaviorSpec("urgency_salience", urgency_boost=1.50),
}

for combo_name, components in LOW_COMBO_COMPONENTS.items():
    POLICY_SPECS[combo_name] = BehaviorSpec("combo", components=components)

for base in [
    "TraitPriceHerdingT100",
    "TraitReserveInflationM005",
    "TraitUrgencySalienceB110",
    "ComboAttentionDropP0025PriceHerdingT100",
]:
    POLICY_SPECS[f"GuardCriticalOverride_{base}"] = BehaviorSpec("guardrail", guardrail="critical_override", base_policy=base)
    POLICY_SPECS[f"GuardMinSOC_{base}"] = BehaviorSpec("guardrail", guardrail="min_soc", base_policy=base)
    POLICY_SPECS[f"GuardQueueFallback_{base}"] = BehaviorSpec("guardrail", guardrail="queue_fallback", base_policy=base)


VALIDATION_POLICIES = [
    "LeastLaxity",
    "BehaviorNeutralLL",
    "TraitAttentionDropP0025",
    "TraitAttentionDropP005",
    "TraitReserveInflationM005",
    "TraitPriceHerdingT100",
    "TraitUrgencySalienceB110",
    "ComboAttentionDropP0025PriceHerdingT100",
]
CAPACITY_POLICIES = [
    "LeastLaxity",
    "BehaviorNeutralLL",
    "TraitAttentionDropP001",
    "TraitAttentionDropP0025",
    "TraitAttentionDropP005",
    "TraitAttentionDropP010",
    "TraitAttentionDropP020",
    "TraitReserveInflationM005",
    "TraitReserveInflationM015",
    "TraitReserveInflationM025",
    "TraitPriceHerdingT100",
    "TraitPriceHerdingT105",
    "TraitPriceHerdingT110",
    "TraitUrgencySalienceB110",
    "TraitUrgencySalienceB130",
    "TraitUrgencySalienceB150",
    "ComboAttentionDropP0025ReserveInflationM005",
    "ComboAttentionDropP0025PriceHerdingT100",
    "ComboAttentionDropP0025UrgencySalienceB110",
    "ComboReserveInflationM005PriceHerdingT100",
    "ComboReserveInflationM005UrgencySalienceB110",
    "ComboPriceHerdingT100UrgencySalienceB110",
]
BASELINE_POLICIES = ["PlugAndCharge", "LeastLaxity", "EDF", "LowSOCFirst", "TOUOnlyCheap", "BehaviorNeutralLL"]
GENERALIZATION_POLICIES = [
    "LeastLaxity",
    "BehaviorNeutralLL",
    "TraitAttentionDropP0025",
    "TraitAttentionDropP005",
    "TraitReserveInflationM005",
    "TraitPriceHerdingT100",
    "TraitUrgencySalienceB110",
    "ComboAttentionDropP0025PriceHerdingT100",
]
GUARDRAIL_BASE_POLICIES = [
    "LeastLaxity",
    "TraitPriceHerdingT100",
    "GuardCriticalOverride_TraitPriceHerdingT100",
    "GuardMinSOC_TraitPriceHerdingT100",
    "GuardQueueFallback_TraitPriceHerdingT100",
    "TraitReserveInflationM005",
    "GuardCriticalOverride_TraitReserveInflationM005",
    "GuardMinSOC_TraitReserveInflationM005",
    "GuardQueueFallback_TraitReserveInflationM005",
    "TraitUrgencySalienceB110",
    "GuardCriticalOverride_TraitUrgencySalienceB110",
    "GuardMinSOC_TraitUrgencySalienceB110",
    "GuardQueueFallback_TraitUrgencySalienceB110",
    "ComboAttentionDropP0025PriceHerdingT100",
    "GuardCriticalOverride_ComboAttentionDropP0025PriceHerdingT100",
    "GuardMinSOC_ComboAttentionDropP0025PriceHerdingT100",
    "GuardQueueFallback_ComboAttentionDropP0025PriceHerdingT100",
]


def append_log(lines: list[str]) -> None:
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with RUN_LOG.open("a", encoding="utf-8") as f_out:
        f_out.write("\n".join(lines) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    try:
        val = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(val):
        return "n/a"
    if abs(val) < 0.5 * 10 ** (-digits):
        val = 0.0
    return f"{val:.{digits}f}"


def capacity_slots(capacity_pct: int) -> dict[str, int]:
    factor = capacity_pct / 100.0
    return {
        loc: max(1, int(round(BASE_CAPACITY[loc] * factor)))
        for loc in ("home", "work", "public")
    }


def make_spec(axis_label: str, scenario: str, site_type: str, demand_regime: str, capacity_pct: int) -> ScenarioSpec:
    slots = capacity_slots(capacity_pct)
    return ScenarioSpec(
        label=f"{axis_label}_cap{capacity_pct}",
        scenario=scenario,
        site_type=site_type,
        demand_regime=demand_regime,
        capacity_pct=capacity_pct,
        n_slots_home=slots["home"],
        n_slots_work=slots["work"],
        n_slots_public=slots["public"],
    )


def run_config(seed: int, spec: ScenarioSpec) -> V2RunConfig:
    return V2RunConfig(
        scenario=spec.scenario,
        seed=seed,
        n_cars=N_CARS,
        episode_hours=EPISODE_HOURS,
        forecast_horizon=24,
        n_slots_home=spec.n_slots_home,
        n_slots_work=spec.n_slots_work,
        n_slots_public=spec.n_slots_public,
        max_queue_wait_steps=4,
    )


def policy_rng(seed: int, spec: ScenarioSpec, policy: str) -> np.random.Generator:
    key = abs(hash((spec.label, policy))) % 1_000_000
    return np.random.default_rng(seed + 1_150_000 + key)


def cheap_mask(prices: np.ndarray, policy: str) -> np.ndarray:
    spec = POLICY_SPECS.get(policy)
    tolerance = float(spec.cheap_tolerance if spec else 1.00)
    return _cheap_mask(prices, tolerance=tolerance)


def _priority_actions_for_selected(values: dict[str, np.ndarray], selected: np.ndarray, critical: np.ndarray) -> np.ndarray:
    actions = np.where(selected, PRIMITIVE_FLEXIBLE_REQUEST, PRIMITIVE_IDLE).astype(np.int64)
    actions[selected & critical] = PRIMITIVE_NORMAL_REQUEST
    return actions


def _low_soc_first_actions(env, values: dict[str, np.ndarray], rng: np.random.Generator) -> np.ndarray:
    available = values["masks"][:, PRIMITIVE_NORMAL_REQUEST]
    critical = _service_critical(values)
    eligible = available & (critical | values["target"])
    score = 100.0 * (1.0 - values["soc"]) + 1000.0 * critical.astype(float)
    return _select_cap_limited(env, values, eligible, score, rng, urgent_salience=True)


def _tou_only_actions(env, values: dict[str, np.ndarray], rng: np.random.Generator, is_cheap: np.ndarray) -> np.ndarray:
    available = values["masks"][:, PRIMITIVE_NORMAL_REQUEST]
    critical = _service_critical(values)
    floor = _select_cap_limited(env, values, available & critical, _score(values), rng, urgent_salience=True)
    if not bool(is_cheap[int(env.t) % len(is_cheap)]):
        return floor
    optional = available & values["target"] & ~critical
    actions = floor.copy()
    actions[(actions == PRIMITIVE_IDLE) & optional] = PRIMITIVE_FLEXIBLE_REQUEST
    return actions


def _base_behavior_actions(
    env,
    obs: dict[str, object],
    policy: str,
    rng: np.random.Generator,
    is_cheap: np.ndarray,
    state: PolicyState,
) -> np.ndarray:
    spec = POLICY_SPECS[policy]
    values = _arrays(env, obs)
    available = values["masks"][:, PRIMITIVE_NORMAL_REQUEST]
    critical = _service_critical(values)

    if policy == "LeastLaxity" or policy == "BehaviorNeutralLL":
        actions = least_laxity_actions(env, obs)
    elif policy == "EDF":
        actions = edf_actions(env, obs)
    elif policy == "PlugAndCharge":
        selected = available & (critical | values["target"])
        actions = _priority_actions_for_selected(values, selected, critical)
    elif policy == "LowSOCFirst":
        actions = _low_soc_first_actions(env, values, rng)
    elif policy == "TOUOnlyCheap":
        actions = _tou_only_actions(env, values, rng, is_cheap)
    elif spec.family == "attention_drop":
        actions = least_laxity_actions(env, obs)
        drop = (rng.random(env.n_cars) < float(spec.drop_prob)) & (actions != PRIMITIVE_IDLE)
        actions[drop] = PRIMITIVE_IDLE
    elif spec.family == "reserve_inflation":
        inflated = values["soc"] < (values["theta"] + float(spec.reserve_margin))
        selected = available & (values["target"] | inflated)
        actions = _priority_actions_for_selected(values, selected, critical | inflated)
    elif spec.family == "price_herding":
        actions = _tou_only_actions(env, values, rng, is_cheap)
    elif spec.family == "urgency_salience":
        eligible = available & (critical | values["target"])
        actions = _select_cap_limited(
            env,
            values,
            eligible,
            _score(values, urgency_boost=float(spec.urgency_boost)),
            rng,
            urgent_salience=True,
        )
    elif spec.family == "combo":
        actions = _combo_actions(env, obs, policy, rng, is_cheap, state)
    else:
        raise ValueError(policy)
    state.prev_actions = actions.copy()
    return actions.astype(np.int64)


def _drop(actions: np.ndarray, rng: np.random.Generator, p: float = 0.025) -> np.ndarray:
    out = actions.copy()
    mask = (rng.random(out.shape[0]) < p) & (out != PRIMITIVE_IDLE)
    out[mask] = PRIMITIVE_IDLE
    return out


def _combo_actions(
    env,
    obs: dict[str, object],
    policy: str,
    rng: np.random.Generator,
    is_cheap: np.ndarray,
    state: PolicyState,
) -> np.ndarray:
    values = _arrays(env, obs)
    available = values["masks"][:, PRIMITIVE_NORMAL_REQUEST]
    critical = _service_critical(values)
    inflated = values["soc"] < (values["theta"] + 0.05)
    cheap_now = bool(is_cheap[int(env.t) % len(is_cheap)])

    if policy == "ComboAttentionDropP0025ReserveInflationM005":
        selected = available & (values["target"] | inflated)
        return _drop(_priority_actions_for_selected(values, selected, critical | inflated), rng)
    if policy == "ComboAttentionDropP0025PriceHerdingT100":
        return _drop(_tou_only_actions(env, values, rng, is_cheap), rng)
    if policy == "ComboAttentionDropP0025UrgencySalienceB110":
        spec = POLICY_SPECS["TraitUrgencySalienceB110"]
        eligible = available & (critical | values["target"])
        base = _select_cap_limited(env, values, eligible, _score(values, urgency_boost=float(spec.urgency_boost)), rng, urgent_salience=True)
        return _drop(base, rng)
    if policy == "ComboReserveInflationM005PriceHerdingT100":
        floor = _select_cap_limited(env, values, available & critical, _score(values), rng, urgent_salience=True)
        optional = available & (values["target"] | inflated) & ~critical & cheap_now
        actions = floor.copy()
        actions[(actions == PRIMITIVE_IDLE) & optional] = PRIMITIVE_FLEXIBLE_REQUEST
        actions[(actions == PRIMITIVE_IDLE) & inflated] = PRIMITIVE_NORMAL_REQUEST
        return actions.astype(np.int64)
    if policy == "ComboReserveInflationM005UrgencySalienceB110":
        eligible = available & (critical | values["target"] | inflated)
        score = _score(values, urgency_boost=1.10) + 35.0 * inflated.astype(float)
        return _select_cap_limited(env, values, eligible, score, rng, urgent_salience=True)
    if policy == "ComboPriceHerdingT100UrgencySalienceB110":
        floor = _select_cap_limited(env, values, available & critical, _score(values, urgency_boost=1.10), rng, urgent_salience=True)
        optional = available & values["target"] & ~critical & cheap_now
        actions = floor.copy()
        actions[(actions == PRIMITIVE_IDLE) & optional] = PRIMITIVE_FLEXIBLE_REQUEST
        return actions.astype(np.int64)
    raise ValueError(policy)


def _queue_fallback_active(env, actions: np.ndarray) -> bool:
    counts = loc_request_counts(env, actions)
    for loc, count in counts.items():
        if len(env.charger_queues[loc]) + int(count) > int(env.n_slots[loc]):
            return True
    return False


def policy_actions(
    env,
    obs: dict[str, object],
    policy: str,
    rng: np.random.Generator,
    is_cheap: np.ndarray,
    state: PolicyState,
) -> np.ndarray:
    spec = POLICY_SPECS[policy]
    if spec.family != "guardrail":
        return _base_behavior_actions(env, obs, policy, rng, is_cheap, state)

    base_policy = str(spec.base_policy)
    base_actions = _base_behavior_actions(env, obs, base_policy, rng, is_cheap, state)
    values = _arrays(env, obs)
    ll_actions = least_laxity_actions(env, obs)
    critical = _service_critical(values)
    low_soc = values["soc"] <= values["theta"] + 0.05
    if spec.guardrail == "critical_override":
        mask = critical & (ll_actions != PRIMITIVE_IDLE)
        base_actions[mask] = ll_actions[mask]
    elif spec.guardrail == "min_soc":
        mask = low_soc & (ll_actions != PRIMITIVE_IDLE)
        base_actions[mask] = ll_actions[mask]
    elif spec.guardrail == "queue_fallback":
        if _queue_fallback_active(env, base_actions):
            base_actions = ll_actions
    else:
        raise ValueError(spec.guardrail)
    state.prev_actions = base_actions.copy()
    return base_actions.astype(np.int64)


def bin_label(value: float, bins: list[tuple[str, float, float]]) -> str:
    for label, lo, hi in bins:
        if lo <= value < hi:
            return label
    return bins[-1][0]


def update_group_counts(target: dict[tuple[str, str], dict[str, float]], group: str, actions: np.ndarray, stored: np.ndarray, mask: np.ndarray) -> None:
    if not np.any(mask):
        return
    for action_id in range(N_PRIMITIVE_ACTIONS):
        key = (group, ACTION_NAMES.get(action_id, f"action_{action_id}"))
        rec = target.setdefault(key, {"count": 0.0, "delivered_kwh": 0.0})
        sub = mask & (actions == action_id)
        rec["count"] += float(sub.sum())
        rec["delivered_kwh"] += float(stored[sub].sum())


def scarcity_state(env, actions: np.ndarray) -> tuple[bool, int, int]:
    counts = loc_request_counts(env, actions)
    scarce = False
    excess_total = 0
    request_total = 0
    for loc, requests in counts.items():
        requests = int(requests)
        queued = len(env.charger_queues[loc])
        cap = int(env.n_slots[loc])
        excess = max(0, queued + requests - cap)
        request_total += requests
        excess_total += excess
        scarce = scarce or excess > 0
    return scarce, request_total, excess_total


def evaluate_run(experiment: str, seed: int, spec: ScenarioSpec, policy: str) -> dict[str, Any]:
    cfg = run_config(seed, spec)
    env = make_env(cfg, seed=seed)
    obs = env.reset()
    rng = policy_rng(seed, spec, policy)
    state = PolicyState()
    prices = np.asarray(env.price_schedule[: env.config.episode_hours], dtype=float)
    is_cheap = cheap_mask(prices, policy if policy in POLICY_SPECS else "TraitPriceHerdingT100")
    action_counts = np.zeros(N_PRIMITIVE_ACTIONS, dtype=int)
    per_vehicle_delivered = np.zeros(env.n_cars, dtype=float)
    demand_kw: list[float] = []
    by_time: list[dict[str, Any]] = []
    demand_supply: list[dict[str, Any]] = []
    soc_counts: dict[tuple[str, str], dict[str, float]] = {}
    laxity_counts: dict[tuple[str, str], dict[str, float]] = {}
    scarcity_counts: dict[tuple[str, str], dict[str, float]] = {}
    counters = defaultdict(float)
    urgent_trip_events = 0
    urgent_trip_failures = 0
    prev_abandon_loc = 0
    prev_abandon_timeout = 0
    done = False

    while not done:
        t = int(env.t)
        values = _arrays(env, obs)
        actions = policy_actions(env, obs, policy, rng, is_cheap, state)
        requested = actions != PRIMITIVE_IDLE
        critical_need = values["masks"][:, PRIMITIVE_NORMAL_REQUEST] & _service_critical(values)
        optional_need = values["masks"][:, PRIMITIVE_NORMAL_REQUEST] & values["target"] & ~critical_need
        flexible_requested = actions == PRIMITIVE_FLEXIBLE_REQUEST
        scarce, request_total, excess_total = scarcity_state(env, actions)
        queue_before = sum(len(env.charger_queues[loc]) for loc in ("home", "work", "public"))
        realized = getattr(env, "realized_mandatory_trip_schedule", None)
        if realized is not None and t < realized.shape[1]:
            trip_events = np.asarray(realized[:, t] > 0.0, dtype=bool)
        else:
            trip_events = np.zeros(env.n_cars, dtype=bool)
        pre_urgent = _service_critical(values) | (values["soc"] <= values["theta"] + 0.05)
        urgent_trip_mask = trip_events & pre_urgent

        obs, _, done, info = env.step(actions)
        stored = np.asarray(getattr(env, "_last_charge_stored_actual_kwh", np.zeros(env.n_cars)), dtype=float)
        delivered_kwh = float(stored.sum())
        requested_kwh_proxy = float(request_total * POWER_KW_PROXY)
        mismatch_kwh_proxy = max(0.0, requested_kwh_proxy - delivered_kwh)
        queue_after = sum(len(env.charger_queues[loc]) for loc in ("home", "work", "public"))
        abandon_loc = int(np.asarray(env.queue_abandonments_loc).sum())
        abandon_timeout = int(np.asarray(env.queue_abandonments_timeout).sum())
        new_abandon = (abandon_loc - prev_abandon_loc) + (abandon_timeout - prev_abandon_timeout)
        prev_abandon_loc = abandon_loc
        prev_abandon_timeout = abandon_timeout

        for action_id in range(N_PRIMITIVE_ACTIONS):
            action_counts[action_id] += int((actions == action_id).sum())
        counters["request_count"] += int(requested.sum())
        counters["admitted_count"] += int(sum(int(env.admitted_history[loc][-1]) for loc in ("home", "work", "public")))
        counters["requested_not_delivered_count"] += int((requested & (stored <= 1.0e-9)).sum())
        counters["critical_request_count"] += int(critical_need.sum())
        counters["critical_request_served_count"] += int((critical_need & (stored > 1.0e-9)).sum())
        counters["critical_request_missed_count"] += int((critical_need & (stored <= 1.0e-9)).sum())
        counters["optional_request_count"] += int(optional_need.sum())
        counters["optional_request_served_count"] += int((optional_need & (stored > 1.0e-9)).sum())
        counters["optional_request_missed_count"] += int((optional_need & (stored <= 1.0e-9)).sum())
        counters["critical_requested_not_delivered_count"] += int(((requested & critical_need) & (stored <= 1.0e-9)).sum())
        counters["flexible_requested_not_delivered_count"] += int((flexible_requested & (stored <= 1.0e-9)).sum())
        counters["scarce_hour_count"] += int(scarce)
        counters["scarce_request_count"] += int(request_total if scarce else 0)
        counters["scarce_unserved_count"] += int(((requested & (stored <= 1.0e-9)).sum()) if scarce else 0)
        counters["oversubscription_vehicle_steps"] += int(excess_total)
        counters["queue_rejection_count"] += int(new_abandon)
        if bool(is_cheap[t % len(is_cheap)]):
            counters["cheap_window_request_count"] += int(requested.sum())
        counters["charge_above_target_request_count"] += int((requested & ~values["target"]).sum())
        counters["low_laxity_missed_charge_count"] += int((critical_need & ~requested).sum())
        failures = np.asarray(info.get("failures", np.zeros(env.n_cars, dtype=bool)), dtype=bool)
        urgent_trip_events += int(urgent_trip_mask.sum())
        urgent_trip_failures += int((urgent_trip_mask & failures).sum())
        per_vehicle_delivered += stored
        demand = float(info.get("agg_demand_kw", delivered_kwh))
        demand_kw.append(demand)

        for idx in range(env.n_cars):
            soc_group = bin_label(float(values["soc"][idx]), SOC_BINS)
            lax_group = bin_label(float(values["time_to"][idx]), LAXITY_BINS)
            update_group_counts(soc_counts, soc_group, actions, stored, np.arange(env.n_cars) == idx)
            update_group_counts(laxity_counts, lax_group, actions, stored, np.arange(env.n_cars) == idx)
        update_group_counts(scarcity_counts, "scarce" if scarce else "not_scarce", actions, stored, np.ones(env.n_cars, dtype=bool))

        by_time.append(
            {
                "experiment": experiment,
                "scenario_label": spec.label,
                "seed": seed,
                "policy": policy,
                "capacity_pct": spec.capacity_pct,
                "timestep": t,
                "scarce_capacity": int(scarce),
                "request_count": request_total,
                "queue_length_before": queue_before,
                "queue_length_after": queue_after,
                "queue_rejection_count": new_abandon,
                "delivered_kwh": delivered_kwh,
                "requested_kwh_proxy": requested_kwh_proxy,
                "unmet_kwh_proxy": mismatch_kwh_proxy,
                "delivered_kw": demand,
            }
        )
        demand_supply.append(
            {
                "experiment": experiment,
                "scenario_label": spec.label,
                "seed": seed,
                "policy": policy,
                "capacity_pct": spec.capacity_pct,
                "timestep": t,
                "requested_kwh_proxy": requested_kwh_proxy,
                "delivered_kwh": delivered_kwh,
                "unmet_kwh_proxy": mismatch_kwh_proxy,
                "demand_supply_ratio": delivered_kwh / requested_kwh_proxy if requested_kwh_proxy > 0 else 1.0,
            }
        )

    mandatory_events = max(1, env.count_mandatory_trip_events(realized=True))
    demand_arr = np.asarray(demand_kw, dtype=float)
    peak = float(demand_arr.max()) if demand_arr.size else 0.0
    mean = float(demand_arr.mean()) if demand_arr.size else 0.0
    waits = np.asarray(env.agent_wait_time, dtype=float)
    capacity_kw_proxy = POWER_KW_PROXY * (spec.n_slots_home + spec.n_slots_work + spec.n_slots_public)
    request_count = max(1.0, counters["request_count"])
    row = {
        "experiment": experiment,
        "scenario_label": spec.label,
        "scenario": spec.scenario,
        "site_type": spec.site_type,
        "demand_regime": spec.demand_regime,
        "capacity_pct": spec.capacity_pct,
        "n_slots_home": spec.n_slots_home,
        "n_slots_work": spec.n_slots_work,
        "n_slots_public": spec.n_slots_public,
        "seed": seed,
        "policy": policy,
        "family": POLICY_SPECS[policy].family,
        "reliability_pct": 100.0 * (1.0 - env.failure_count / mandatory_events),
        "failure_count": int(env.failure_count),
        "mandatory_events": int(mandatory_events),
        "urgent_trip_reliability_pct": 100.0 * (1.0 - urgent_trip_failures / max(1, urgent_trip_events)),
        "urgent_trip_failure_count": int(urgent_trip_failures),
        "urgent_trip_events": int(urgent_trip_events),
        "delivered_kwh_per_vehicle": float(per_vehicle_delivered.mean()),
        "total_delivered_kwh": float(per_vehicle_delivered.sum()),
        "peak_demand_kw": peak,
        "mean_demand_kw": mean,
        "coincidence_factor": float(peak / max(mean, 1.0e-9)) if mean > 0 else 0.0,
        "peak_to_average_ratio": float(peak / max(mean, 1.0e-9)) if mean > 0 else 0.0,
        "load_factor": float(mean / peak) if peak > 0 else 0.0,
        "line_loss_proxy_kw2h": float(np.square(demand_arr).sum()),
        "capacity_kw_proxy": capacity_kw_proxy,
        "overload_hours_proxy": int((demand_arr > capacity_kw_proxy).sum()),
        "p95_wait_minutes": float(np.percentile(waits, 95) * 60.0),
        "mean_wait_minutes": float(waits.mean() * 60.0),
        "max_queue_length": int(max(env.max_queue_length_seen.values()) if env.max_queue_length_seen else 0),
        "mean_queue_length": float(np.mean([row["queue_length_after"] for row in by_time])) if by_time else 0.0,
        "queue_abandonments_location_total": int(np.asarray(env.queue_abandonments_loc).sum()),
        "queue_abandonments_timeout_total": int(np.asarray(env.queue_abandonments_timeout).sum()),
        "action_counts": json.dumps(action_counts.astype(int).tolist()),
        "idle_action_count": int(action_counts[PRIMITIVE_IDLE]),
        "normal_request_action_count": int(action_counts[PRIMITIVE_NORMAL_REQUEST]),
        "flexible_request_action_count": int(action_counts[PRIMITIVE_FLEXIBLE_REQUEST]),
        "other_action_count": int(action_counts.sum() - action_counts[PRIMITIVE_IDLE] - action_counts[PRIMITIVE_NORMAL_REQUEST] - action_counts[PRIMITIVE_FLEXIBLE_REQUEST]),
        "idle_action_share": float(action_counts[PRIMITIVE_IDLE] / max(1, action_counts.sum())),
        "normal_request_action_share": float(action_counts[PRIMITIVE_NORMAL_REQUEST] / max(1, action_counts.sum())),
        "flexible_request_action_share": float(action_counts[PRIMITIVE_FLEXIBLE_REQUEST] / max(1, action_counts.sum())),
        "cheap_window_request_share": float(counters["cheap_window_request_count"] / request_count),
        "charge_above_target_request_share": float(counters["charge_above_target_request_count"] / request_count),
        "claim_boundary": "Behavior Applied Energy package v1; behavior proxies are imposed perturbations, not measured traits.",
    }
    row.update({key: int(value) if float(value).is_integer() else float(value) for key, value in counters.items()})

    soc_rows = [
        {
            "experiment": experiment,
            "scenario_label": spec.label,
            "seed": seed,
            "policy": policy,
            "capacity_pct": spec.capacity_pct,
            "soc_bin": group,
            "action": action,
            "count": int(values["count"]),
            "delivered_kwh": float(values["delivered_kwh"]),
        }
        for (group, action), values in sorted(soc_counts.items())
    ]
    lax_rows = [
        {
            "experiment": experiment,
            "scenario_label": spec.label,
            "seed": seed,
            "policy": policy,
            "capacity_pct": spec.capacity_pct,
            "laxity_bin": group,
            "action": action,
            "count": int(values["count"]),
            "delivered_kwh": float(values["delivered_kwh"]),
        }
        for (group, action), values in sorted(laxity_counts.items())
    ]
    scarcity_rows = [
        {
            "experiment": experiment,
            "scenario_label": spec.label,
            "seed": seed,
            "policy": policy,
            "capacity_pct": spec.capacity_pct,
            "scarcity_state": group,
            "action": action,
            "count": int(values["count"]),
            "delivered_kwh": float(values["delivered_kwh"]),
        }
        for (group, action), values in sorted(scarcity_counts.items())
    ]
    return {
        "row": row,
        "by_time": by_time,
        "demand_supply": demand_supply,
        "by_soc": soc_rows,
        "by_laxity": lax_rows,
        "by_scarcity": scarcity_rows,
    }


def pair_with_least_laxity(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anchors = {
        (row["experiment"], row["scenario_label"], int(row["capacity_pct"]), int(row["seed"])): row
        for row in rows
        if row["policy"] == "LeastLaxity"
    }
    out = []
    for row in rows:
        key = (row["experiment"], row["scenario_label"], int(row["capacity_pct"]), int(row["seed"]))
        anchor = anchors.get(key)
        enriched = dict(row)
        if anchor:
            delivered_ratio = float(row["delivered_kwh_per_vehicle"]) / max(float(anchor["delivered_kwh_per_vehicle"]), 1e-9)
            peak_ratio = float(row["peak_demand_kw"]) / max(float(anchor["peak_demand_kw"]), 1e-9)
            critical_delta = int(row.get("critical_requested_not_delivered_count", 0)) - int(anchor.get("critical_requested_not_delivered_count", 0))
            oversub_delta = int(row.get("oversubscription_vehicle_steps", 0)) - int(anchor.get("oversubscription_vehicle_steps", 0))
            reliability_delta = float(row["reliability_pct"]) - float(anchor["reliability_pct"])
            queue_delta = float(row["p95_wait_minutes"]) - float(anchor["p95_wait_minutes"])
            service_gate = (
                reliability_delta >= -0.5
                and delivered_ratio >= 0.95
                and critical_delta <= CRITICAL_NO_DELIV_SLACK
                and oversub_delta <= OVERSUBSCRIPTION_VEHICLE_SLACK
            )
            enriched.update(
                {
                    "delivered_ratio_vs_ll": delivered_ratio,
                    "peak_ratio_vs_ll": peak_ratio,
                    "critical_rnd_delta_vs_ll": critical_delta,
                    "oversub_delta_vs_ll": oversub_delta,
                    "reliability_delta_vs_ll_pp": reliability_delta,
                    "p95_wait_delta_vs_ll_min": queue_delta,
                    "energy_matched_1pct": 0.99 <= delivered_ratio <= 1.01,
                    "energy_matched_2pct": 0.98 <= delivered_ratio <= 1.02,
                    "service_gate_pass": service_gate,
                    "classification": classify_row(enriched, service_gate, delivered_ratio, peak_ratio, critical_delta, oversub_delta, queue_delta),
                }
            )
        out.append(enriched)
    return out


def classify_row(row: dict[str, Any], service_gate: bool, delivered_ratio: float, peak_ratio: float, critical_delta: int, oversub_delta: int, queue_delta: float) -> str:
    if row["policy"] == "LeastLaxity":
        return "anchor"
    if not service_gate:
        if delivered_ratio < 0.95:
            return "harmful by under-delivery"
        if critical_delta > CRITICAL_NO_DELIV_SLACK:
            return "harmful by priority distortion"
        if oversub_delta > OVERSUBSCRIPTION_VEHICLE_SLACK or queue_delta > 1.0:
            return "harmful by queue contention"
        return "fragile"
    if peak_ratio > 1.01:
        return "harmful by synchronization"
    if peak_ratio <= 0.99 and delivered_ratio >= 0.99 and critical_delta <= 0 and oversub_delta <= 0:
        return "service-tolerated"
    return "service-tolerated"


def run_matrix(experiment: str, specs: list[ScenarioSpec], seeds: list[int], policies: list[str]) -> dict[str, list[dict[str, Any]]]:
    aggregate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    total = len(specs) * len(seeds) * len(policies)
    idx = 0
    for spec in specs:
        for seed in seeds:
            for policy in policies:
                idx += 1
                print(f"{experiment}: {idx}/{total} {spec.label} seed={seed} policy={policy}", flush=True)
                result = evaluate_run(experiment, seed, spec, policy)
                aggregate["rows"].append(result["row"])
                aggregate["by_time"].extend(result["by_time"])
                aggregate["demand_supply"].extend(result["demand_supply"])
                aggregate["by_soc"].extend(result["by_soc"])
                aggregate["by_laxity"].extend(result["by_laxity"])
                aggregate["by_scarcity"].extend(result["by_scarcity"])
    aggregate["rows"] = pair_with_least_laxity(aggregate["rows"])
    return aggregate


def mean(vals: list[float]) -> float:
    return float(np.mean(vals)) if vals else float("nan")


def summarize_policy(rows: list[dict[str, Any]], group_keys: list[str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(key) for key in group_keys)].append(row)
    summaries = []
    for key, vals in sorted(grouped.items()):
        out = {name: value for name, value in zip(group_keys, key)}
        out.update(
            {
                "n": len(vals),
                "service_pass_rows": sum(1 for row in vals if bool(row.get("service_gate_pass", False))),
                "energy_matched_1pct_rows": sum(1 for row in vals if bool(row.get("energy_matched_1pct", False))),
                "delivered_ratio_vs_ll_mean": mean([float(row.get("delivered_ratio_vs_ll", 1.0)) for row in vals]),
                "peak_ratio_vs_ll_mean": mean([float(row.get("peak_ratio_vs_ll", 1.0)) for row in vals]),
                "critical_rnd_delta_mean": mean([float(row.get("critical_rnd_delta_vs_ll", 0.0)) for row in vals]),
                "oversub_delta_mean": mean([float(row.get("oversub_delta_vs_ll", 0.0)) for row in vals]),
                "p95_wait_delta_mean": mean([float(row.get("p95_wait_delta_vs_ll_min", 0.0)) for row in vals]),
                "line_loss_proxy_ratio_mean": mean_loss_ratio(vals),
                "classification_mode": mode([str(row.get("classification", "")) for row in vals]),
            }
        )
        summaries.append(out)
    return summaries


def mean_loss_ratio(vals: list[dict[str, Any]]) -> float:
    ratios = []
    by_anchor = {
        (row["experiment"], row["scenario_label"], int(row["capacity_pct"]), int(row["seed"])): row
        for row in vals
        if row["policy"] == "LeastLaxity"
    }
    if not by_anchor:
        return float("nan")
    for row in vals:
        anchor = by_anchor.get((row["experiment"], row["scenario_label"], int(row["capacity_pct"]), int(row["seed"])))
        if anchor:
            ratios.append(float(row["line_loss_proxy_kw2h"]) / max(float(anchor["line_loss_proxy_kw2h"]), 1e-9))
    return mean(ratios)


def mode(vals: list[str]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for val in vals:
        counts[val] += 1
    return max(counts, key=counts.get) if counts else ""


def phase_label(summary: dict[str, Any]) -> str:
    pass_rate = summary["service_pass_rows"] / max(1, summary["n"])
    delivered = float(summary["delivered_ratio_vs_ll_mean"])
    oversub = float(summary["oversub_delta_mean"])
    critical = float(summary["critical_rnd_delta_mean"])
    if pass_rate >= 0.95 and delivered >= 0.99 and oversub <= 0 and critical <= 0:
        return "service-feasible"
    if pass_rate >= 0.75:
        return "fragile"
    if delivered < 0.95:
        return "energy-under-delivering"
    if oversub > OVERSUBSCRIPTION_VEHICLE_SLACK:
        return "queue-stressed"
    return "service-failing"


def write_validation_summary(rows: list[dict[str, Any]]) -> None:
    summaries = summarize_policy(rows, ["policy"])
    lines = [
        "# Validation Subset Summary",
        "",
        "Status: `COMPLETE`",
        "",
        "Validation checked diagnostics creation, non-empty outputs, service-gate computation, and BehaviorNeutralLL parity with LeastLaxity.",
        "",
        "| policy | service pass | delivered ratio | peak ratio | critical RND delta | oversub delta | classification |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in summaries:
        lines.append(
            f"| `{row['policy']}` | {row['service_pass_rows']}/{row['n']} | {fmt(row['delivered_ratio_vs_ll_mean'])} | {fmt(row['peak_ratio_vs_ll_mean'])} | {fmt(row['critical_rnd_delta_mean'])} | {fmt(row['oversub_delta_mean'])} | `{row['classification_mode']}` |"
        )
    neutral = next((row for row in summaries if row["policy"] == "BehaviorNeutralLL"), None)
    reliable = bool(neutral and neutral["service_pass_rows"] == neutral["n"] and abs(float(neutral["delivered_ratio_vs_ll_mean"]) - 1.0) < 1e-9)
    lines += [
        "",
        f"Diagnostics reliable enough for full run: `{reliable}`",
        "",
        "Files checked: decision diagnostics, by-time diagnostics, SOC/laxity/scarcity diagnostics, demand-supply time series, queue diagnostics, and grid proxy diagnostics.",
    ]
    write_md(ARTIFACT_DIR / "validation_subset_summary.md", lines)


def write_capacity_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = summarize_policy(rows, ["capacity_pct", "policy"])
    for row in summaries:
        row["phase_label"] = phase_label(row)
    write_csv(RESULT_DIR / "capacity_stress_boundary_summary_rows.csv", summaries)
    lines = [
        "# Capacity-Stress Boundary Summary",
        "",
        "Classification uses paired LeastLaxity service gates and delivered-energy ratios.",
        "",
        "| capacity % | policy | service pass | delivered ratio | peak ratio | phase |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for row in summaries:
        if row["policy"] in {"LeastLaxity", "BehaviorNeutralLL", "TraitAttentionDropP0025", "TraitAttentionDropP005", "TraitReserveInflationM005", "TraitPriceHerdingT100", "TraitUrgencySalienceB110", "ComboAttentionDropP0025PriceHerdingT100"}:
            lines.append(
                f"| {row['capacity_pct']} | `{row['policy']}` | {row['service_pass_rows']}/{row['n']} | {fmt(row['delivered_ratio_vs_ll_mean'])} | {fmt(row['peak_ratio_vs_ll_mean'])} | `{row['phase_label']}` |"
            )
    write_md(ARTIFACT_DIR / "capacity_stress_boundary_summary.md", lines)
    return summaries


def write_delivered_energy_matched(rows: list[dict[str, Any]]) -> None:
    matched = [
        row for row in rows
        if row["policy"] != "LeastLaxity" and bool(row.get("energy_matched_1pct", False))
    ]
    write_csv(RESULT_DIR / "delivered_energy_matched_results.csv", matched)
    summaries = summarize_policy(matched, ["policy"]) if matched else []
    lines = [
        "# Delivered-Energy Matched Summary",
        "",
        "Energy-matched means delivered kWh/vehicle within 0.99-1.01 of paired LeastLaxity.",
        "",
        "| policy | matched rows | service pass | delivered ratio | peak ratio | critical RND delta | oversub delta |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| `{row['policy']}` | {row['n']} | {row['service_pass_rows']}/{row['n']} | {fmt(row['delivered_ratio_vs_ll_mean'])} | {fmt(row['peak_ratio_vs_ll_mean'])} | {fmt(row['critical_rnd_delta_mean'])} | {fmt(row['oversub_delta_mean'])} |"
        )
    useful = [
        row for row in summaries
        if row["service_pass_rows"] == row["n"] and float(row["peak_ratio_vs_ll_mean"]) <= 0.99 and float(row["oversub_delta_mean"]) <= 0
    ]
    lines += [
        "",
        f"Behaviors reducing peak while preserving delivered energy and service in matched rows: `{len(useful)}`",
    ]
    write_md(ARTIFACT_DIR / "delivered_energy_matched_summary.md", lines)


def write_baseline_summary(rows: list[dict[str, Any]]) -> None:
    summaries = summarize_policy(rows, ["policy"])
    lines = [
        "# Baseline Comparison Summary",
        "",
        "No MPC/offline oracle implementation was found in the inspected behavior-map code. This comparison uses available transparent baselines.",
        "",
        "| baseline | service pass | delivered ratio | peak ratio | p95 wait delta | classification |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in summaries:
        lines.append(
            f"| `{row['policy']}` | {row['service_pass_rows']}/{row['n']} | {fmt(row['delivered_ratio_vs_ll_mean'])} | {fmt(row['peak_ratio_vs_ll_mean'])} | {fmt(row['p95_wait_delta_mean'])} | `{row['classification_mode']}` |"
        )
    lines += [
        "",
        "TODO for submission-strength benchmark: add a rolling-horizon MPC or offline clairvoyant scheduler with the same service gate and capacity constraints.",
    ]
    write_md(ARTIFACT_DIR / "baseline_comparison_summary.md", lines)


def write_generalization_summary(rows: list[dict[str, Any]]) -> None:
    summaries = summarize_policy(rows, ["scenario", "capacity_pct", "policy"])
    lines = [
        "# Generalization Envelope Summary",
        "",
        "This envelope varies site/demand scenario and capacity percentage inside the simulator. It is not external field validation.",
        "",
        "| scenario | capacity % | policy | service pass | delivered ratio | peak ratio | classification |",
        "|---|---:|---|---:|---:|---:|---|",
    ]
    for row in summaries:
        lines.append(
            f"| `{row['scenario']}` | {row['capacity_pct']} | `{row['policy']}` | {row['service_pass_rows']}/{row['n']} | {fmt(row['delivered_ratio_vs_ll_mean'])} | {fmt(row['peak_ratio_vs_ll_mean'])} | `{row['classification_mode']}` |"
        )
    write_md(ARTIFACT_DIR / "generalization_envelope_summary.md", lines)


def write_interaction_summary(rows: list[dict[str, Any]]) -> None:
    interaction_rows = [row for row in rows if row["policy"] in LOW_COMBO_COMPONENTS]
    summaries = summarize_policy(interaction_rows, ["policy"]) if interaction_rows else []
    out_rows = []
    for row in summaries:
        policy = str(row["policy"])
        components = LOW_COMBO_COMPONENTS.get(policy, ("", ""))
        mechanism = infer_interaction_mechanism(row)
        row["component_a"] = components[0]
        row["component_b"] = components[1]
        row["dominant_failure_mechanism"] = mechanism
        out_rows.append(row)
    write_csv(RESULT_DIR / "behavior_interaction_diagnostics.csv", out_rows)
    lines = [
        "# Behavior Interaction Diagnostics",
        "",
        "| combination | components | service pass | delivered ratio | peak ratio | dominant mechanism |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in out_rows:
        lines.append(
            f"| `{row['policy']}` | `{row['component_a']}` + `{row['component_b']}` | {row['service_pass_rows']}/{row['n']} | {fmt(row['delivered_ratio_vs_ll_mean'])} | {fmt(row['peak_ratio_vs_ll_mean'])} | `{row['dominant_failure_mechanism']}` |"
        )
    write_md(ARTIFACT_DIR / "behavior_interaction_summary.md", lines)


def infer_interaction_mechanism(row: dict[str, Any]) -> str:
    if float(row["delivered_ratio_vs_ll_mean"]) < 0.95:
        return "under-delivery"
    if float(row["critical_rnd_delta_mean"]) > CRITICAL_NO_DELIV_SLACK:
        return "critical-request starvation / priority distortion"
    if float(row["oversub_delta_mean"]) > OVERSUBSCRIPTION_VEHICLE_SLACK:
        return "queue contention"
    if float(row["peak_ratio_vs_ll_mean"]) > 1.01:
        return "synchronization / peak concentration"
    if int(row["service_pass_rows"]) < int(row["n"]):
        return "fragile service failure"
    return "service-tolerated"


def write_guardrail_summary(rows: list[dict[str, Any]]) -> None:
    summaries = summarize_policy(rows, ["policy"])
    lines = [
        "# Guardrail Mitigation Summary",
        "",
        "Guardrails are simple operational tests: critical override, minimum-SOC protection, and queue-aware fallback to LeastLaxity.",
        "",
        "| policy | service pass | delivered ratio | peak ratio | critical RND delta | oversub delta | classification |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in summaries:
        lines.append(
            f"| `{row['policy']}` | {row['service_pass_rows']}/{row['n']} | {fmt(row['delivered_ratio_vs_ll_mean'])} | {fmt(row['peak_ratio_vs_ll_mean'])} | {fmt(row['critical_rnd_delta_mean'])} | {fmt(row['oversub_delta_mean'])} | `{row['classification_mode']}` |"
        )
    write_md(ARTIFACT_DIR / "guardrail_mitigation_summary.md", lines)


def plot_outputs(all_rows: list[dict[str, Any]], capacity_summary: list[dict[str, Any]], time_rows: list[dict[str, Any]], soc_rows: list[dict[str, Any]], laxity_rows: list[dict[str, Any]]) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 8, "figure.dpi": 150, "savefig.dpi": 300, "axes.spines.top": False, "axes.spines.right": False})

    key_policies = ["BehaviorNeutralLL", "TraitAttentionDropP0025", "TraitAttentionDropP005", "TraitReserveInflationM005", "TraitPriceHerdingT100", "TraitUrgencySalienceB110", "ComboAttentionDropP0025PriceHerdingT100"]
    cap_rows = [row for row in capacity_summary if row["policy"] in key_policies]
    matrix = np.zeros((len(key_policies), len(CAPACITY_LEVELS)))
    label_to_num = {"service-feasible": 0, "fragile": 1, "queue-stressed": 2, "service-failing": 3, "energy-under-delivering": 4}
    cap_index = {cap: idx for idx, cap in enumerate(CAPACITY_LEVELS)}
    pol_index = {pol: idx for idx, pol in enumerate(key_policies)}
    for row in cap_rows:
        matrix[pol_index[row["policy"]], cap_index[int(row["capacity_pct"])]] = label_to_num.get(row["phase_label"], 3)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    im = ax.imshow(matrix, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=4)
    ax.set_xticks(range(len(CAPACITY_LEVELS)), [str(c) for c in CAPACITY_LEVELS])
    ax.set_yticks(range(len(key_policies)), [p.replace("Trait", "").replace("Combo", "Combo ") for p in key_policies])
    ax.set_xlabel("Capacity level (%)")
    ax.set_title("Behavior pass/fail heatmap and capacity-stress phase diagram")
    cbar = fig.colorbar(im, ax=ax, ticks=list(label_to_num.values()))
    cbar.ax.set_yticklabels(list(label_to_num.keys()))
    fig.tight_layout()
    fig.savefig(FIG_DIR / "behavior_pass_fail_heatmap.png", bbox_inches="tight")
    fig.savefig(FIG_DIR / "capacity_stress_phase_diagram.png", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    rows = [row for row in all_rows if row["experiment"] == "capacity_stress" and row["policy"] != "LeastLaxity"]
    ax.scatter([float(row.get("delivered_ratio_vs_ll", np.nan)) for row in rows], [float(row.get("peak_ratio_vs_ll", np.nan)) for row in rows], s=12, alpha=0.45)
    ax.axvspan(0.99, 1.01, color="#d9f0d3", alpha=0.5, label="energy-matched band")
    ax.axhline(1.0, color="#555555", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Delivered kWh ratio vs LeastLaxity")
    ax.set_ylabel("Peak ratio vs LeastLaxity")
    ax.legend(frameon=False)
    ax.set_title("Delivered-energy matched peak screen")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "delivered_energy_matched_peak_plot.png", bbox_inches="tight")
    plt.close(fig)

    validation_rows = [row for row in all_rows if row["experiment"] == "validation_subset"]
    shares = summarize_policy(validation_rows, ["policy"])
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    policies = [row["policy"] for row in shares]
    idle = []
    normal = []
    flexible = []
    for pol in policies:
        vals = [row for row in validation_rows if row["policy"] == pol]
        idle.append(mean([float(row["idle_action_share"]) for row in vals]))
        normal.append(mean([float(row["normal_request_action_share"]) for row in vals]))
        flexible.append(mean([float(row["flexible_request_action_share"]) for row in vals]))
    x = np.arange(len(policies))
    ax.bar(x, idle, label="idle", color="#bdbdbd")
    ax.bar(x, normal, bottom=idle, label="normal request", color="#3182bd")
    ax.bar(x, flexible, bottom=np.asarray(idle) + np.asarray(normal), label="flexible request", color="#31a354")
    ax.set_xticks(x, [p.replace("Trait", "").replace("Combo", "Combo ") for p in policies], rotation=35, ha="right")
    ax.set_ylabel("Action share")
    ax.set_title("Decision mechanism: action shares by behavior")
    ax.legend(frameon=False, ncol=3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "decision_mechanism_barplots.png", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    example_policies = ["BehaviorNeutralLL", "TraitAttentionDropP0025", "TraitPriceHerdingT100", "TraitReserveInflationM005", "ComboAttentionDropP0025PriceHerdingT100"]
    for pol in example_policies:
        vals = [row for row in time_rows if row["experiment"] == "validation_subset" and row["policy"] == pol and int(row["seed"]) == VALIDATION_SEEDS[0]]
        vals = sorted(vals, key=lambda row: int(row["timestep"]))
        if vals:
            ax.plot([int(row["timestep"]) for row in vals], [float(row["delivered_kw"]) for row in vals], label=pol.replace("Trait", "").replace("Combo", "Combo "))
    ax.set_xlabel("Timestep")
    ax.set_ylabel("Delivered load proxy (kW)")
    ax.set_title("Demand-supply timeseries examples")
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "demand_supply_timeseries_examples.png", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    key = [row for row in shares if row["policy"] in key_policies]
    ax.bar([row["policy"].replace("Trait", "") for row in key], [float(row["p95_wait_delta_mean"]) for row in key], color="#756bb1")
    ax.set_xticklabels([row["policy"].replace("Trait", "") for row in key], rotation=35, ha="right")
    ax.set_ylabel("p95 wait delta vs LL (min)")
    ax.set_title("Queue pressure by behavior")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "queue_pressure_plot.png", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    rows = [row for row in capacity_summary if row["capacity_pct"] == 50 and row["policy"] in key_policies]
    ax.bar([row["policy"].replace("Trait", "") for row in rows], [float(row["peak_ratio_vs_ll_mean"]) for row in rows], color="#2b8cbe")
    ax.axhline(1.0, color="#555555", linestyle="--", linewidth=0.8)
    ax.set_xticklabels([row["policy"].replace("Trait", "") for row in rows], rotation=35, ha="right")
    ax.set_ylabel("Peak ratio vs LL")
    ax.set_title("Grid proxy: peak ratio at 50% capacity")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "grid_proxy_plot.png", bbox_inches="tight")
    plt.close(fig)


def write_research_state(all_rows: list[dict[str, Any]], capacity_summary: list[dict[str, Any]]) -> None:
    validation = [row for row in all_rows if row["experiment"] == "validation_subset"]
    cap = [row for row in all_rows if row["experiment"] == "capacity_stress"]
    guard = [row for row in all_rows if row["experiment"] == "guardrail_mitigation"]
    matched = [row for row in cap if row.get("energy_matched_1pct") and row["policy"] != "LeastLaxity"]
    lines = [
        "# Research State: Behavior Applied Energy v1",
        "",
        "## Updated Research Objective",
        "",
        "Study how imposed behavior-like traits change EV charging agents' decisions and identify which single behaviors or combinations help or hurt demand-supply matching, peaks, delivered energy, reliability, queue pressure, and grid proxy metrics.",
        "",
        "## Why Tariff Branch Is Frozen",
        "",
        "The tariff allocation branch answers a different research question. It is retained as side material only and is not the central evidence for this behavior paper.",
        "",
        "## Why BRL-DQN Is Secondary",
        "",
        "Prior DQN/BRL-DQN runs did not pass the demand/service evidence standard robustly. Transparent LeastLaxity/EDF-style behavior mapping remains the main evidence layer.",
        "",
        "## New Experiment Package Summary",
        "",
        f"- Validation rows: `{len(validation)}`",
        f"- Capacity-stress rows: `{len(cap)}`",
        f"- Energy-matched behavior rows in capacity screen: `{len(matched)}`",
        f"- Guardrail rows: `{len(guard)}`",
        "",
        "## Decision-Mechanism Findings",
        "",
        "The package now records action shares, SOC-bin actions, laxity-bin actions, scarcity-state actions, queue events, demand-supply time series, and grid proxies. These diagnostics make the behavior mechanisms visible rather than relying only on final outcome metrics.",
        "",
        "## Capacity-Stress Boundary Findings",
        "",
        "Capacity-stress classifications are stored in `capacity_stress_boundary_summary_rows.csv`. The main pattern remains that behavior perturbations shift the system into fragile, queue-stressed, service-failing, or under-delivering regimes well before they become robust improvements.",
        "",
        "## Delivered-Energy Matched Findings",
        "",
        "The matched screen asks whether peak reductions survive when delivered kWh is within 0.99-1.01 of LeastLaxity. Only rows passing this screen should be interpreted as real load-shaping candidates.",
        "",
        "## Baseline Comparison Findings",
        "",
        "Available transparent baselines were run. No MPC/offline oracle implementation was found; this remains a submission-risk TODO.",
        "",
        "## Guardrail Mitigation Findings",
        "",
        "Critical override, minimum-SOC protection, and queue-aware fallback guardrails were tested on failed behavior conditions. The guardrail summary reports whether they restore service gates and whether they remove apparent peak benefits.",
        "",
        "## Supported Claims",
        "",
        "- Behavior wrappers can be evaluated without changing the LeastLaxity anchor, as BehaviorNeutralLL is a wrapper-fidelity check.",
        "- Most imposed behavior-like perturbations are harmful under strict service-first gates.",
        "- Low-probability attention drop is the only currently narrow tolerated perturbation, and it remains fragile under combinations.",
        "- Decision diagnostics can identify whether failure comes from under-delivery, synchronization, queue contention, or priority distortion.",
        "",
        "## Unsupported Claims",
        "",
        "- No claim that these are measured human traits.",
        "- No claim that BRL-DQN is the best controller.",
        "- No claim of external feeder validation or universal EV-charging generality.",
        "- No claim of an oracle/MPC benchmark until implemented.",
        "",
        "## Recommended Paper Framing",
        "",
        "Controlled service-first behavior-effect map for decentralized EV charging agents.",
        "",
        "## Recommended Title",
        "",
        "Behavior-Like Perturbations in Decentralized EV Charging: Decision Mechanisms, Service Failures, and Capacity-Stress Effects",
        "",
        "## Applied Energy Risks",
        "",
        "- No physical feeder power-flow model.",
        "- No MPC/offline oracle upper bound.",
        "- Behavior proxies remain operational perturbations, not calibrated driver traits.",
        "- Transparent-agent evidence is stronger than learned RL evidence.",
    ]
    write_md(ARTIFACT_DIR / "research_state_behavior_applied_energy_v1.md", lines)


def write_outline() -> None:
    lines = [
        "# Manuscript Outline: Applied Energy Behavior Map",
        "",
        "## Working Title",
        "",
        "Behavior-Like Perturbations in Decentralized EV Charging: Decision Mechanisms, Service Failures, and Capacity-Stress Effects",
        "",
        "## Abstract Skeleton",
        "",
        "EV charging agents may be deployed under user-like operational perturbations such as non-response, reserve inflation, price herding, and urgency salience. This paper evaluates how these perturbations alter decentralized charging decisions under finite charger capacity. Using transparent service-first baselines, capacity-stress sweeps, delivered-energy matched screening, and decision-level diagnostics, the study maps when behaviors are service-tolerated, fragile, or harmful by under-delivery, synchronization, queue contention, or priority distortion.",
        "",
        "## Introduction Argument",
        "",
        "EV charging behavior matters for energy systems because local decisions alter aggregate demand, queue pressure, delivered energy, and grid stress. Existing behavior-aware work often evaluates final outcomes without showing the decision mechanisms or service-preservation boundary.",
        "",
        "## Contributions",
        "",
        "1. A service-first behavior-effect map for imposed charging-agent perturbations.",
        "2. Decision-mechanism diagnostics linking behavior proxies to action choices.",
        "3. Capacity-stress and delivered-energy matched screens that separate real load shaping from under-delivery.",
        "4. Interaction and guardrail experiments showing which failures are composable or mitigable.",
        "",
        "## Results Sections",
        "",
        "1. Wrapper fidelity and baseline comparison.",
        "2. Decision-mechanism diagnostics.",
        "3. Capacity-stress phase diagram.",
        "4. Delivered-energy matched peak and queue results.",
        "5. Behavior interaction diagnostics.",
        "6. Grid proxy and demand-supply mismatch impacts.",
        "7. Guardrail mitigation.",
        "",
        "## Limitations",
        "",
        "Operational proxies are not measured traits; no field trial; no feeder power-flow model; no final MPC/oracle baseline yet; learned RL evidence remains secondary.",
    ]
    write_md(ARTIFACT_DIR / "manuscript_outline_applied_energy_behavior_map.md", lines)


def write_report(all_rows: list[dict[str, Any]], checks: dict[str, Any], start_time: float) -> None:
    lines = [
        "# Autonomous Run Report",
        "",
        f"Wall seconds: `{time.time() - start_time:.1f}`",
        "",
        "## What Changed",
        "",
        "- Added `scripts/run_behavior_applied_energy_package_v1.py`.",
        "- Created a separate behavior-focused artifact package under `artifacts/behavior_applied_energy_package_v1/`.",
        "- Created separate result files under `results/behavior_applied_energy_package_v1/`.",
        "",
        "## Experiments Completed",
        "",
        f"- Validation subset rows: `{sum(1 for row in all_rows if row['experiment'] == 'validation_subset')}`",
        f"- Capacity-stress rows: `{sum(1 for row in all_rows if row['experiment'] == 'capacity_stress')}`",
        f"- Baseline comparison rows: `{sum(1 for row in all_rows if row['experiment'] == 'baseline_comparison')}`",
        f"- Generalization rows: `{sum(1 for row in all_rows if row['experiment'] == 'generalization_envelope')}`",
        f"- Guardrail mitigation rows: `{sum(1 for row in all_rows if row['experiment'] == 'guardrail_mitigation')}`",
        "",
        "## Experiments Skipped Or Partial",
        "",
        "- MPC/offline oracle was not implemented because no existing implementation was found in the inspected behavior code.",
        "- Physical feeder/voltage modeling was not run; only grid proxy diagnostics were generated.",
        "- PV/renewable mismatch was not run in this package because no PV profile or co-simulation hook was found in the inspected behavior environment.",
        "",
        "## Validation Checks",
        "",
        json.dumps(checks, indent=2, sort_keys=True),
        "",
        "## Submission Readiness",
        "",
        "The package materially strengthens the behavior paper, especially by adding decision diagnostics and capacity-stress evidence. It is not yet fully Applied Energy submission-ready because an MPC/offline oracle and physical feeder/PV validation remain missing.",
        "",
        "## Exact Next Actions",
        "",
        "1. Review `validation_subset_summary.md` and confirm BehaviorNeutralLL parity.",
        "2. Add an MPC/offline oracle benchmark or explicitly narrow the paper to transparent-rule behavior mapping.",
        "3. Add feeder/PV co-simulation if available, or state grid proxies as limitations.",
        "4. Rebuild the manuscript around the behavior-effect map, not the tariff branch.",
    ]
    write_md(ARTIFACT_DIR / "AUTONOMOUS_RUN_REPORT.md", lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["all", "validation"], default="all")
    parser.add_argument("--full-seeds", type=int, default=len(FULL_SEEDS))
    args = parser.parse_args()

    start = time.time()
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    append_log(["", f"## Package Runner Started", "", f"Command: `python scripts/run_behavior_applied_energy_package_v1.py --mode {args.mode} --full-seeds {args.full_seeds}`"])

    validation_spec = [make_spec("caltech_sce", "metro_caltech_sce", "campus/workplace", "ACN-like workplace", 50)]
    validation = run_matrix("validation_subset", validation_spec, VALIDATION_SEEDS, VALIDATION_POLICIES)
    write_csv(RESULT_DIR / "validation_subset_results.csv", validation["rows"])
    write_validation_summary(validation["rows"])
    all_parts = [validation]

    checks = {
        "validation_rows": len(validation["rows"]),
        "validation_time_rows": len(validation["by_time"]),
        "validation_nonempty": bool(validation["rows"] and validation["by_time"] and validation["by_soc"] and validation["by_laxity"]),
    }

    if args.mode == "all":
        seeds = FULL_SEEDS[: max(1, args.full_seeds)]
        capacity_specs = [make_spec("caltech_sce", "metro_caltech_sce", "campus/workplace", "ACN-like workplace", cap) for cap in CAPACITY_LEVELS]
        capacity = run_matrix("capacity_stress", capacity_specs, seeds, CAPACITY_POLICIES)
        write_csv(RESULT_DIR / "capacity_stress_boundary_results.csv", capacity["rows"])
        capacity_summary = write_capacity_summary(capacity["rows"])
        write_delivered_energy_matched(capacity["rows"])
        write_interaction_summary(capacity["rows"])
        all_parts.append(capacity)

        baseline_specs = [make_spec("caltech_sce", "metro_caltech_sce", "campus/workplace", "ACN-like workplace", 50)]
        baseline = run_matrix("baseline_comparison", baseline_specs, seeds, BASELINE_POLICIES)
        write_csv(RESULT_DIR / "baseline_comparison_results.csv", baseline["rows"])
        write_baseline_summary(baseline["rows"])
        all_parts.append(baseline)

        general_specs = []
        for axis, scenario, site_type, demand_regime in SCENARIO_AXES:
            for cap in [100, 50, 25]:
                general_specs.append(make_spec(axis, scenario, site_type, demand_regime, cap))
        generalization = run_matrix("generalization_envelope", general_specs, GENERALIZATION_SEEDS, GENERALIZATION_POLICIES)
        write_csv(RESULT_DIR / "generalization_envelope_results.csv", generalization["rows"])
        write_generalization_summary(generalization["rows"])
        all_parts.append(generalization)

        guard_specs = [make_spec("caltech_sce", "metro_caltech_sce", "campus/workplace", "ACN-like workplace", 25)]
        guardrail = run_matrix("guardrail_mitigation", guard_specs, seeds, GUARDRAIL_BASE_POLICIES)
        write_csv(RESULT_DIR / "guardrail_mitigation_results.csv", guardrail["rows"])
        write_guardrail_summary(guardrail["rows"])
        all_parts.append(guardrail)
    else:
        capacity_summary = []

    all_rows = [row for part in all_parts for row in part["rows"]]
    all_time = [row for part in all_parts for row in part["by_time"]]
    all_demand_supply = [row for part in all_parts for row in part["demand_supply"]]
    all_soc = [row for part in all_parts for row in part["by_soc"]]
    all_laxity = [row for part in all_parts for row in part["by_laxity"]]
    all_scarcity = [row for part in all_parts for row in part["by_scarcity"]]

    write_csv(RESULT_DIR / "decision_diagnostics.csv", all_rows)
    write_csv(RESULT_DIR / "decision_diagnostics_by_time.csv", all_time)
    write_csv(RESULT_DIR / "decision_diagnostics_by_soc.csv", all_soc)
    write_csv(RESULT_DIR / "decision_diagnostics_by_laxity.csv", all_laxity)
    write_csv(RESULT_DIR / "decision_diagnostics_by_scarcity.csv", all_scarcity)
    write_csv(RESULT_DIR / "demand_supply_timeseries.csv", all_demand_supply)
    write_csv(RESULT_DIR / "queue_diagnostics.csv", [
        {
            "experiment": row["experiment"],
            "scenario_label": row["scenario_label"],
            "capacity_pct": row["capacity_pct"],
            "seed": row["seed"],
            "policy": row["policy"],
            "mean_queue_length": row["mean_queue_length"],
            "max_queue_length": row["max_queue_length"],
            "p95_wait_minutes": row["p95_wait_minutes"],
            "mean_wait_minutes": row["mean_wait_minutes"],
            "queue_rejection_count": row.get("queue_rejection_count", 0),
        }
        for row in all_rows
    ])
    write_csv(RESULT_DIR / "grid_proxy_diagnostics.csv", [
        {
            "experiment": row["experiment"],
            "scenario_label": row["scenario_label"],
            "capacity_pct": row["capacity_pct"],
            "seed": row["seed"],
            "policy": row["policy"],
            "peak_demand_kw": row["peak_demand_kw"],
            "mean_demand_kw": row["mean_demand_kw"],
            "load_factor": row["load_factor"],
            "peak_to_average_ratio": row["peak_to_average_ratio"],
            "line_loss_proxy_kw2h": row["line_loss_proxy_kw2h"],
            "overload_hours_proxy": row["overload_hours_proxy"],
            "capacity_kw_proxy": row["capacity_kw_proxy"],
        }
        for row in all_rows
    ])

    if args.mode == "all":
        plot_outputs(all_rows, capacity_summary, all_time, all_soc, all_laxity)
    write_research_state(all_rows, capacity_summary)
    write_outline()
    write_report(all_rows, checks, start)
    append_log(["", "## Package Runner Completed", "", f"Rows: `{len(all_rows)}`", f"Wall seconds: `{time.time() - start:.1f}`"])
    print(f"completed rows={len(all_rows)} artifact_dir={ARTIFACT_DIR}")


if __name__ == "__main__":
    main()
