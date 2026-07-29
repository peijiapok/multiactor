#!/usr/bin/env python3
"""Compact multi-actor EV charging experiment package v2.

This runner is intentionally separate from the earlier service-first package.
It adds action-changing fleet and grid policy variants, then scores driver,
fleet, and grid outcomes independently.  The simulator, queue persistence, and
charging physics remain the existing repository implementation.

The policies are operational scenarios, not calibrated human-choice models,
global optimizers, filed tariff billing, or site-specific feeder validation.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import shutil
import sys
import time
from collections import defaultdict
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


WORKSPACE = Path("/home/jia/thirfty death BRL DQN")
SCRIPTS = WORKSPACE / "scripts"
for path in (WORKSPACE, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_behavior_applied_energy_package_v1 as pkg  # noqa: E402
from run_behavior_trait_screening import TOTAL_NO_DELIV_FAILURE_DELTA, location_type  # noqa: E402


OUT_DIR = WORKSPACE / "artifacts" / "multi_actor_fleet_charging_v2"
FIG_DIR = OUT_DIR / "figures"
PLOT_DIR = OUT_DIR / "plot_result"
EXTERNAL_COPY_DIR = Path("/home/jia/multi actor/multi_actor_fleet_charging_v2_20260526")

RESULTS_CSV = OUT_DIR / "multi_actor_v2_row_results.csv"
SUMMARY_CSV = OUT_DIR / "multi_actor_v2_policy_capacity_summary.csv"
PATTERN_CSV = OUT_DIR / "actor_failure_pattern_summary.csv"
ACCEPT_CSV = OUT_DIR / "mutual_acceptability_summary.csv"
FLEET_GRID_CSV = OUT_DIR / "fleet_grid_policy_results.csv"
FLEET_SUCCESS_CSV = OUT_DIR / "fleet_success_summary.csv"
MANIFEST_CSV = OUT_DIR / "evidence_manifest.csv"
THRESHOLD_JSON = OUT_DIR / "threshold_config.json"
THRESHOLD_MD = OUT_DIR / "threshold_config.md"
RUN_LOG = OUT_DIR / "RUN_LOG.md"
READINESS_REPORT = OUT_DIR / "MULTI_ACTOR_V2_READINESS_REPORT.md"
FLEET_BALANCED_REPORT = OUT_DIR / "FLEET_BALANCED_EXTENSION_REPORT.md"
STATE_ACTION_AUDIT = OUT_DIR / "STATE_ACTION_MAPPING.md"
TIME_CSV = OUT_DIR / "multi_actor_v2_timeseries.csv"
DRIVER_DIAG_CSV = OUT_DIR / "multi_actor_v2_driver_diagnostics.csv"
SOC_CSV = OUT_DIR / "multi_actor_v2_compliance_by_soc.csv"


DEFAULT_SEED_START = 4501
DEFAULT_SEEDS = 10
DEFAULT_CAPACITIES = [20, 35, 50]
DEMAND_CHARGE_RATE_USD_PER_KW_MONTH = 25.0
POWER_KW_PROXY = pkg.POWER_KW_PROXY


THRESHOLDS: dict[str, Any] = {
    "balanced_policy_weights": {
        "w_service": 100.0,
        "w_critical": 100.0,
        "w_queue": 10.0,
        "w_peak": 3.0,
        "w_cost": 1.0,
        "implementation_note": "FleetBalanced uses these pre-registered weights in a lexicographic-style priority score. Service/critical terms are dominant; queue pressure only penalizes high-SoC non-critical flexible requests.",
    },
    "driver": {
        "delivered_ratio_vs_anchor_min": 0.95,
        "reliability_delta_vs_anchor_min_pp": -0.5,
        "critical_requested_not_delivered_delta_max": float(pkg.CRITICAL_NO_DELIV_SLACK),
        "low_soc_event_delta_max": None,
    },
    "fleet": {
        "p95_wait_delta_max_minutes": 30.0,
        "mean_queue_delta_max": 1.0,
        "max_queue_delta_max": 2.0,
        "requested_not_delivered_delta_max": float(TOTAL_NO_DELIV_FAILURE_DELTA),
        "energy_cost_ratio_max": 1.10,
        "demand_charge_exposure_ratio_max": 1.10,
    },
    "grid": {
        "peak_ratio_vs_anchor_max": 1.05,
        "peak_to_average_ratio_vs_anchor_max": 1.10,
        "ramp_p95_ratio_vs_anchor_max": 1.10,
        "load_factor_delta_min": -0.05,
        "squared_load_proxy_ratio_max": 1.10,
        "ieee33_min_voltage_pu_min": 0.95,
        "ieee33_max_line_loading_pct_max": 100.0,
        "note": "IEEE33 thresholds are documented for later feeder-screen joins; v2 weekly runs use load-shape proxies only.",
    },
}


@dataclass(frozen=True)
class MultiActorPolicy:
    name: str
    driver: str
    fleet: str
    grid: str
    description: str


POLICIES: list[MultiActorPolicy] = [
    MultiActorPolicy(
        "D_FullyCompliant__F_ServiceFirst__G_NoGrid",
        "FullyCompliant",
        "FleetServiceFirst",
        "NoGridIncentive",
        "Baseline multi-actor row: least-laxity service-first fleet recommendation, fully compliant driver layer, no grid incentive.",
    ),
    MultiActorPolicy(
        "D_FullyCompliant__F_CostOnly__G_NoGrid",
        "FullyCompliant",
        "FleetCostOnly",
        "NoGridIncentive",
        "Fleet shifts discretionary charging to cheap windows without an explicit grid guardrail.",
    ),
    MultiActorPolicy(
        "D_FullyCompliant__F_ServiceCostly__G_NoGrid",
        "FullyCompliant",
        "FleetServiceCostly",
        "NoGridIncentive",
        "Fleet preserves urgent service but shifts discretionary charging away from cheap windows, creating a fleet economic stress case.",
    ),
    MultiActorPolicy(
        "D_FullyCompliant__F_QueueAware__G_NoGrid",
        "FullyCompliant",
        "FleetQueueAware",
        "NoGridIncentive",
        "Fleet suppresses non-urgent/high-SoC requests under queue pressure.",
    ),
    MultiActorPolicy(
        "D_FullyCompliant__F_AvailabilityFocused__G_NoGrid",
        "FullyCompliant",
        "FleetAvailabilityFocused",
        "NoGridIncentive",
        "Fleet maintains a higher readiness reserve for vehicles with likely upcoming needs.",
    ),
    MultiActorPolicy(
        "D_FullyCompliant__F_ServiceFirst__G_PeakPenalty",
        "FullyCompliant",
        "FleetServiceFirst",
        "GridPeakPenalty",
        "Service-first fleet recommendation with an action-changing peak cap.",
    ),
    MultiActorPolicy(
        "D_FullyCompliant__F_CostOnly__G_PeakPenalty",
        "FullyCompliant",
        "FleetCostOnly",
        "GridPeakPenalty",
        "Cheap-window fleet policy with a grid peak cap.",
    ),
    MultiActorPolicy(
        "D_FullyCompliant__F_QueueAware__G_PeakPenalty",
        "FullyCompliant",
        "FleetQueueAware",
        "GridPeakPenalty",
        "Queue-aware fleet policy with a grid peak cap.",
    ),
    MultiActorPolicy(
        "D_FullyCompliant__F_FleetBalanced__G_NoGrid",
        "FullyCompliant",
        "FleetBalanced",
        "NoGridIncentive",
        "Balanced fleet heuristic: service and critical need first, queue control second, peak/cost tie-breakers last.",
    ),
    MultiActorPolicy(
        "D_FullyCompliant__F_FleetBalanced__G_PeakPenalty",
        "FullyCompliant",
        "FleetBalanced",
        "GridPeakPenalty",
        "Balanced fleet heuristic with the explicit grid peak cap.",
    ),
    MultiActorPolicy(
        "D_LimitedAttentionP0025__F_ServiceFirst__G_NoGrid",
        "LimitedAttentionP0025",
        "FleetServiceFirst",
        "NoGridIncentive",
        "Low-probability missed compliance with service-first fleet recommendation.",
    ),
    MultiActorPolicy(
        "D_LimitedAttentionP0025__F_FleetBalanced__G_NoGrid",
        "LimitedAttentionP0025",
        "FleetBalanced",
        "NoGridIncentive",
        "Balanced fleet heuristic under low-probability missed compliance.",
    ),
    MultiActorPolicy(
        "D_LimitedAttentionP0025__F_FleetBalanced__G_PeakPenalty",
        "LimitedAttentionP0025",
        "FleetBalanced",
        "GridPeakPenalty",
        "Balanced fleet heuristic plus peak cap under low-probability missed compliance.",
    ),
    MultiActorPolicy(
        "D_LimitedAttentionP005__F_ServiceFirst__G_NoGrid",
        "LimitedAttentionP005",
        "FleetServiceFirst",
        "NoGridIncentive",
        "Moderate missed compliance with service-first fleet recommendation.",
    ),
    MultiActorPolicy(
        "D_SoCCompliance__F_ServiceFirst__G_NoGrid",
        "SoCCompliance",
        "FleetServiceFirst",
        "NoGridIncentive",
        "Compliance probability is higher at low SoC and lower at high SoC.",
    ),
    MultiActorPolicy(
        "D_SoCQueueCompliance__F_ServiceFirst__G_NoGrid",
        "SoCQueueCompliance",
        "FleetServiceFirst",
        "NoGridIncentive",
        "SoC-dependent compliance with queue-sensitive avoidance for non-critical high-SoC charging.",
    ),
    MultiActorPolicy(
        "D_PriceSensitive__F_ServiceFirst__G_NoGrid",
        "PriceSensitive",
        "FleetServiceFirst",
        "NoGridIncentive",
        "Driver layer biases actual requests toward cheap windows, bounded by critical/low-SoC need.",
    ),
    MultiActorPolicy(
        "D_PriceSensitive__F_FleetBalanced__G_NoGrid",
        "PriceSensitive",
        "FleetBalanced",
        "NoGridIncentive",
        "Balanced fleet heuristic under a price-sensitive driver layer.",
    ),
    MultiActorPolicy(
        "D_PriceSensitive__F_FleetBalanced__G_PeakPenalty",
        "PriceSensitive",
        "FleetBalanced",
        "GridPeakPenalty",
        "Balanced fleet heuristic plus peak cap under a price-sensitive driver layer.",
    ),
    MultiActorPolicy(
        "D_ReserveSeeking__F_ServiceFirst__G_NoGrid",
        "ReserveSeeking",
        "FleetServiceFirst",
        "NoGridIncentive",
        "Driver layer maintains a higher reserve threshold than the fleet recommendation assumes.",
    ),
    MultiActorPolicy(
        "D_UrgencyDriven__F_ServiceFirst__G_NoGrid",
        "UrgencyDriven",
        "FleetServiceFirst",
        "NoGridIncentive",
        "Driver layer prioritizes deadline/urgent charging pressure over the fleet recommendation.",
    ),
    MultiActorPolicy(
        "D_PriceSensitive__F_QueueAware__G_PeakPenalty",
        "PriceSensitive",
        "FleetQueueAware",
        "GridPeakPenalty",
        "Full interaction: price-sensitive driver response, queue-aware fleet policy, and grid peak cap.",
    ),
    MultiActorPolicy(
        "D_SoCCompliance__F_QueueAware__G_PeakPenalty",
        "SoCCompliance",
        "FleetQueueAware",
        "GridPeakPenalty",
        "Full interaction: SoC-dependent compliance, queue-aware fleet policy, and grid peak cap.",
    ),
    MultiActorPolicy(
        "D_SoCCompliance__F_FleetBalanced__G_NoGrid",
        "SoCCompliance",
        "FleetBalanced",
        "NoGridIncentive",
        "Balanced fleet heuristic under SoC-dependent compliance.",
    ),
    MultiActorPolicy(
        "D_SoCCompliance__F_FleetBalanced__G_PeakPenalty",
        "SoCCompliance",
        "FleetBalanced",
        "GridPeakPenalty",
        "Balanced fleet heuristic plus peak cap under SoC-dependent compliance.",
    ),
]

POLICY_BY_NAME = {p.name: p for p in POLICIES}
DEFAULT_POLICIES = ["LeastLaxity"] + [p.name for p in POLICIES]
SOC_BINS = [("0.0-0.2", 0.0, 0.2), ("0.2-0.4", 0.2, 0.4), ("0.4-0.6", 0.4, 0.6), ("0.6-0.8", 0.6, 0.8), ("0.8-1.0", 0.8, 1.01)]

ACTIVE: tuple[str, int, int, str] | None = None
DIAG: dict[tuple[str, int, int, str], dict[str, float]] = {}
SOC_DIAG: dict[tuple[str, int, int, str, str], dict[str, float]] = {}
TIME_DIAG: list[dict[str, Any]] = []
DELEGATE_POLICY_ACTIONS = None


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def set_output_dir(path: Path) -> None:
    global OUT_DIR, FIG_DIR, PLOT_DIR, RESULTS_CSV, SUMMARY_CSV, PATTERN_CSV, ACCEPT_CSV
    global FLEET_GRID_CSV, FLEET_SUCCESS_CSV, MANIFEST_CSV, THRESHOLD_JSON, THRESHOLD_MD
    global RUN_LOG, READINESS_REPORT, FLEET_BALANCED_REPORT, STATE_ACTION_AUDIT, TIME_CSV, DRIVER_DIAG_CSV, SOC_CSV
    OUT_DIR = path
    FIG_DIR = OUT_DIR / "figures"
    PLOT_DIR = OUT_DIR / "plot_result"
    RESULTS_CSV = OUT_DIR / "multi_actor_v2_row_results.csv"
    SUMMARY_CSV = OUT_DIR / "multi_actor_v2_policy_capacity_summary.csv"
    PATTERN_CSV = OUT_DIR / "actor_failure_pattern_summary.csv"
    ACCEPT_CSV = OUT_DIR / "mutual_acceptability_summary.csv"
    FLEET_GRID_CSV = OUT_DIR / "fleet_grid_policy_results.csv"
    FLEET_SUCCESS_CSV = OUT_DIR / "fleet_success_summary.csv"
    MANIFEST_CSV = OUT_DIR / "evidence_manifest.csv"
    THRESHOLD_JSON = OUT_DIR / "threshold_config.json"
    THRESHOLD_MD = OUT_DIR / "threshold_config.md"
    RUN_LOG = OUT_DIR / "RUN_LOG.md"
    READINESS_REPORT = OUT_DIR / "MULTI_ACTOR_V2_READINESS_REPORT.md"
    FLEET_BALANCED_REPORT = OUT_DIR / "FLEET_BALANCED_EXTENSION_REPORT.md"
    STATE_ACTION_AUDIT = OUT_DIR / "STATE_ACTION_MAPPING.md"
    TIME_CSV = OUT_DIR / "multi_actor_v2_timeseries.csv"
    DRIVER_DIAG_CSV = OUT_DIR / "multi_actor_v2_driver_diagnostics.csv"
    SOC_CSV = OUT_DIR / "multi_actor_v2_compliance_by_soc.csv"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def parse_int_list(text: str) -> list[int]:
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def fmt(value: Any, digits: int = 3) -> str:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(val):
        return "n/a"
    return f"{val:.{digits}f}"


def safe_div(numer: float, denom: float, default: float = float("nan")) -> float:
    return float(numer) / float(denom) if abs(float(denom)) > 1e-12 else default


def soc_bin(value: float) -> str:
    for label, lo, hi in SOC_BINS:
        if lo <= value < hi:
            return label
    return "0.8-1.0"


def diag() -> dict[str, float]:
    if ACTIVE is None:
        raise RuntimeError("ACTIVE multi-actor context is missing")
    return DIAG.setdefault(ACTIVE, defaultdict(float))


def self_service_actions(env, obs: dict[str, object]) -> np.ndarray:
    values = pkg._arrays(env, obs)
    critical = pkg._service_critical(values)
    available = values["masks"][:, pkg.PRIMITIVE_NORMAL_REQUEST]
    selected = available & (critical | values["target"])
    return pkg._priority_actions_for_selected(values, selected, critical)


def queue_pressure_high(env, actions: np.ndarray) -> bool:
    counts = pkg.loc_request_counts(env, actions)
    return any(len(env.charger_queues[loc]) + int(count) > int(env.n_slots[loc]) for loc, count in counts.items())


def location_queue_pressure(env, candidate_actions: np.ndarray) -> dict[str, float]:
    counts = pkg.loc_request_counts(env, candidate_actions)
    pressure: dict[str, float] = {}
    for loc in ("home", "work", "public"):
        queued = len(env.charger_queues[loc])
        slots = max(1, int(env.n_slots[loc]))
        requested = int(counts.get(loc, 0))
        pressure[loc] = max(0.0, (queued + requested - slots) / slots)
    return pressure


def capped_select_from_actions(
    env,
    values: dict[str, np.ndarray],
    base_actions: np.ndarray,
    rng: np.random.Generator,
    per_location_fraction: float,
    score: np.ndarray | None = None,
) -> tuple[np.ndarray, int]:
    if score is None:
        score = pkg._score(values)
    out = np.full(env.n_cars, pkg.PRIMITIVE_IDLE, dtype=np.int64)
    deferred = 0
    critical = pkg._service_critical(values)
    for loc in ("home", "work", "public"):
        members = np.array([i for i in np.where(base_actions != pkg.PRIMITIVE_IDLE)[0] if location_type(env, int(i)) == loc], dtype=int)
        if members.size == 0:
            continue
        queued = len(env.charger_queues[loc])
        loc_slots = int(env.n_slots[loc])
        allowed = max(1, int(math.ceil(loc_slots * per_location_fraction)) - int(queued))
        allowed = min(max(0, allowed), members.size)
        if allowed <= 0:
            deferred += int(members.size)
            continue
        # Preserve critical and low-SoC vehicles first, then use deterministic score.
        order = sorted(members.tolist(), key=lambda i: (-float(score[i]), -int(critical[i]), int(i)))
        chosen = np.asarray(order[:allowed], dtype=int)
        out[chosen] = base_actions[chosen]
        deferred += int(members.size - chosen.size)
    return out, deferred


def fleet_recommendation(env, obs: dict[str, object], fleet: str, rng: np.random.Generator, is_cheap: np.ndarray) -> np.ndarray:
    values = pkg._arrays(env, obs)
    available = values["masks"][:, pkg.PRIMITIVE_NORMAL_REQUEST]
    critical = pkg._service_critical(values)
    if fleet == "FleetServiceFirst":
        return pkg.least_laxity_actions(env, obs)
    if fleet == "FleetCostOnly":
        return pkg._tou_only_actions(env, values, rng, is_cheap)
    if fleet == "FleetServiceCostly":
        actions = pkg.least_laxity_actions(env, obs)
        cheap_now = bool(is_cheap[int(env.t) % len(is_cheap)])
        critical = pkg._service_critical(values)
        if cheap_now:
            discretionary = (actions != pkg.PRIMITIVE_IDLE) & ~critical & (values["soc"] >= values["theta"] + 0.05)
            actions[discretionary] = pkg.PRIMITIVE_IDLE
        else:
            # During non-cheap windows, admit target vehicles beyond the
            # least-laxity recommendation subject to the same slot cap. This
            # intentionally creates a fleet cost stress while still respecting
            # queue/capacity semantics.
            eligible = available & (critical | values["target"])
            score = pkg._score(values) + 5.0 * values["target"].astype(float)
            expanded = pkg._select_cap_limited(env, values, eligible, score, rng, urgent_salience=True)
            actions = np.where(actions != pkg.PRIMITIVE_IDLE, actions, expanded).astype(np.int64)
        return actions
    if fleet == "FleetQueueAware":
        eligible = available & (critical | (values["target"] & (values["soc"] <= values["theta"] + 0.10)))
        score = 130.0 * critical.astype(float) + 75.0 * (1.0 - values["soc"]) + 20.0 * values["target_deficit"] - 20.0 * values["laxity"]
        actions = pkg._select_cap_limited(env, values, eligible, score, rng, urgent_salience=True)
        if queue_pressure_high(env, actions):
            actions, _ = capped_select_from_actions(env, values, actions, rng, per_location_fraction=0.75, score=score)
        return actions
    if fleet == "FleetBalanced":
        weights = THRESHOLDS["balanced_policy_weights"]
        low_soc = values["soc"] <= (values["theta"] + 0.05)
        flexible_noncritical = values["target"] & ~critical & ~low_soc & (values["soc"] >= values["theta"] + 0.10)
        actions = pkg.least_laxity_actions(env, obs)
        pressure = location_queue_pressure(env, actions)
        pressure_vec = np.asarray([pressure.get(location_type(env, int(i)), 0.0) for i in range(env.n_cars)], dtype=float)
        price_schedule = np.asarray(getattr(env, "price_schedule", [1.0]), dtype=float)
        price_now = float(price_schedule[int(env.t) % len(price_schedule)])
        price_norm = price_now / max(float(np.nanmax(price_schedule)), 1.0e-9)
        projected_request_count = max(1, int((actions != pkg.PRIMITIVE_IDLE).sum()))
        total_slots = max(1, int(sum(env.n_slots.values())))
        projected_peak_pressure = max(0.0, (projected_request_count - 0.80 * total_slots) / total_slots)
        inverse_laxity = 1.0 - np.clip(values["laxity"], 0.0, 1.0)
        score = (
            float(weights["w_service"]) * values["target_deficit"]
            + float(weights["w_critical"]) * critical.astype(float)
            + 65.0 * low_soc.astype(float)
            + 45.0 * (1.0 - values["soc"])
            + 30.0 * inverse_laxity
        )
        score -= float(weights["w_queue"]) * pressure_vec * flexible_noncritical.astype(float)
        score -= float(weights["w_peak"]) * projected_peak_pressure * flexible_noncritical.astype(float)
        score -= float(weights["w_cost"]) * price_norm * flexible_noncritical.astype(float)
        active_score = score[actions != pkg.PRIMITIVE_IDLE]
        priority_cut = float(np.percentile(active_score, 35)) if active_score.size else -np.inf
        # Hard guardrail: queue/cost/peak terms can only defer flexible,
        # high-SoC, non-critical requests already recommended by LeastLaxity.
        # They never remove critical or low-SoC service requests.
        deferrable = (
            (actions != pkg.PRIMITIVE_IDLE)
            & flexible_noncritical
            & (score <= priority_cut)
            & (values["soc"] >= values["theta"] + 0.25)
            & (values["target_deficit"] <= 0.10)
            & (pressure_vec > 0.0)
            & ((pressure_vec >= 0.50) | ((price_norm >= 0.75) & (projected_peak_pressure > 0.0)))
        )
        actions[deferrable] = pkg.PRIMITIVE_IDLE
        return actions.astype(np.int64)
    if fleet == "FleetAvailabilityFocused":
        reserve_target = values["theta"] + 0.10
        ready_need = values["soc"] < reserve_target
        eligible = available & (critical | values["target"] | ready_need)
        score = 150.0 * critical.astype(float) + 80.0 * ready_need.astype(float) + 40.0 * (1.0 - values["soc"]) - 10.0 * values["laxity"]
        return pkg._select_cap_limited(env, values, eligible, score, rng, urgent_salience=True)
    raise ValueError(fleet)


def apply_grid_policy(env, obs: dict[str, object], actions: np.ndarray, grid: str, rng: np.random.Generator) -> tuple[np.ndarray, int]:
    if grid == "NoGridIncentive":
        return actions, 0
    values = pkg._arrays(env, obs)
    critical = pkg._service_critical(values)
    if grid == "GridPeakPenalty":
        score = 200.0 * critical.astype(float) + 90.0 * (1.0 - values["soc"]) + 30.0 * values["deadline_deficit"] - 15.0 * values["laxity"]
        return capped_select_from_actions(env, values, actions, rng, per_location_fraction=0.70, score=score)
    if grid == "GridLoadSmoothing":
        score = 180.0 * critical.astype(float) + 70.0 * (1.0 - values["soc"]) + 20.0 * values["target_deficit"] - 20.0 * values["laxity"]
        return capped_select_from_actions(env, values, actions, rng, per_location_fraction=0.80, score=score)
    raise ValueError(grid)


def soc_compliance_probability(values: dict[str, np.ndarray]) -> np.ndarray:
    out = np.full(values["soc"].shape, 0.60, dtype=float)
    out[(values["soc"] >= 0.30) & (values["soc"] < 0.60)] = 0.90
    out[values["soc"] < 0.30] = 0.995
    return out


def apply_driver_layer(
    env,
    obs: dict[str, object],
    rec_actions: np.ndarray,
    driver: str,
    rng: np.random.Generator,
    is_cheap: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    values = pkg._arrays(env, obs)
    default = self_service_actions(env, obs)
    critical = pkg._service_critical(values)
    actual = rec_actions.copy()
    p = np.ones(env.n_cars, dtype=float)
    noncompliant = np.zeros(env.n_cars, dtype=bool)
    queue_avoidance_count = 0

    if driver == "FullyCompliant":
        return actual.astype(np.int64), p, noncompliant, queue_avoidance_count
    if driver.startswith("LimitedAttentionP"):
        prob = {"LimitedAttentionP0025": 0.025, "LimitedAttentionP005": 0.05, "LimitedAttentionP010": 0.10}[driver]
        p[:] = 1.0 - prob
        noncompliant = (rng.random(env.n_cars) >= p) & (rec_actions != pkg.PRIMITIVE_IDLE)
        actual[noncompliant] = pkg.PRIMITIVE_IDLE
        return actual.astype(np.int64), p, noncompliant, queue_avoidance_count
    if driver == "SoCCompliance":
        p = soc_compliance_probability(values)
        keep = rng.random(env.n_cars) < p
        noncompliant = ~keep
        actual = np.where(keep, rec_actions, default).astype(np.int64)
        return actual, p, noncompliant, queue_avoidance_count
    if driver == "SoCQueueCompliance":
        p = soc_compliance_probability(values)
        high_q = queue_pressure_high(env, default)
        if high_q:
            p = np.maximum(0.40, p - 0.25)
        keep = rng.random(env.n_cars) < p
        noncompliant = ~keep
        actual = np.where(keep, rec_actions, default).astype(np.int64)
        if high_q:
            optional_high_soc = (values["soc"] >= values["theta"] + 0.15) & ~critical & (actual != pkg.PRIMITIVE_IDLE)
            avoided = optional_high_soc & (rng.random(env.n_cars) < 0.35)
            actual[avoided] = pkg.PRIMITIVE_IDLE
            queue_avoidance_count = int(avoided.sum())
        return actual, p, noncompliant, queue_avoidance_count
    if driver == "PriceSensitive":
        cheap_now = bool(is_cheap[int(env.t) % len(is_cheap)])
        p[:] = 0.85 if cheap_now else 0.55
        if cheap_now:
            price_pref = default.copy()
        else:
            price_pref = np.where(critical | (values["soc"] <= values["theta"] + 0.05), default, pkg.PRIMITIVE_IDLE).astype(np.int64)
        keep = rng.random(env.n_cars) < p
        noncompliant = ~keep
        actual = np.where(keep, rec_actions, price_pref).astype(np.int64)
        return actual, p, noncompliant, queue_avoidance_count
    if driver == "ReserveSeeking":
        reserve_need = values["soc"] < (values["theta"] + 0.05)
        selected = values["masks"][:, pkg.PRIMITIVE_NORMAL_REQUEST] & (reserve_need | values["target"] | critical)
        reserve_actions = pkg._priority_actions_for_selected(values, selected, critical | reserve_need)
        p[:] = 0.90
        keep = rng.random(env.n_cars) < p
        noncompliant = ~keep
        actual = np.where(keep, rec_actions, reserve_actions).astype(np.int64)
        return actual, p, noncompliant, queue_avoidance_count
    if driver == "UrgencyDriven":
        eligible = values["masks"][:, pkg.PRIMITIVE_NORMAL_REQUEST] & (critical | values["target"])
        urgent_actions = pkg._select_cap_limited(env, values, eligible, pkg._score(values, urgency_boost=1.30), rng, urgent_salience=True)
        p[:] = 0.85
        keep = rng.random(env.n_cars) < p
        noncompliant = ~keep
        actual = np.where(keep, rec_actions, urgent_actions).astype(np.int64)
        return actual, p, noncompliant, queue_avoidance_count
    raise ValueError(driver)


def update_soc_diagnostics(values: dict[str, np.ndarray], p: np.ndarray, rec: np.ndarray, actual: np.ndarray, noncompliant: np.ndarray) -> None:
    assert ACTIVE is not None
    for idx, soc in enumerate(values["soc"]):
        key = (*ACTIVE, soc_bin(float(soc)))
        row = SOC_DIAG.setdefault(key, defaultdict(float))
        row["vehicle_steps"] += 1.0
        row["probability_sum"] += float(p[idx])
        row["noncompliance_count"] += float(noncompliant[idx])
        row["recommended_request_count"] += float(rec[idx] != pkg.PRIMITIVE_IDLE)
        row["actual_request_count"] += float(actual[idx] != pkg.PRIMITIVE_IDLE)


def multi_actor_actions(env, obs: dict[str, object], policy: str, rng: np.random.Generator, is_cheap: np.ndarray, state) -> np.ndarray:
    if policy not in POLICY_BY_NAME:
        return DELEGATE_POLICY_ACTIONS(env, obs, policy, rng, is_cheap, state)

    spec = POLICY_BY_NAME[policy]
    values = pkg._arrays(env, obs)
    rec_fleet = fleet_recommendation(env, obs, spec.fleet, rng, is_cheap)
    rec_grid, grid_deferred = apply_grid_policy(env, obs, rec_fleet, spec.grid, rng)
    actual, p, noncompliant, queue_avoidance_count = apply_driver_layer(env, obs, rec_grid, spec.driver, rng, is_cheap)
    high_queue = queue_pressure_high(env, actual)

    d = diag()
    d["vehicle_steps"] += env.n_cars
    d["probability_sum"] += float(p.sum())
    d["noncompliance_count"] += float(noncompliant.sum())
    d["fleet_recommended_request_count"] += float((rec_fleet != pkg.PRIMITIVE_IDLE).sum())
    d["grid_adjusted_request_count"] += float((rec_grid != pkg.PRIMITIVE_IDLE).sum())
    d["actual_request_count"] += float((actual != pkg.PRIMITIVE_IDLE).sum())
    d["grid_deferred_request_count"] += float(grid_deferred)
    d["queue_high_timesteps"] += float(high_queue)
    d["queue_avoidance_count"] += float(queue_avoidance_count)
    d["cheap_window_timestep_count"] += float(bool(is_cheap[int(env.t) % len(is_cheap)]))
    d["cheap_window_actual_request_count"] += float((actual != pkg.PRIMITIVE_IDLE).sum()) if bool(is_cheap[int(env.t) % len(is_cheap)]) else 0.0
    d["driver_steps"] += 1.0
    update_soc_diagnostics(values, p, rec_grid, actual, noncompliant)
    assert ACTIVE is not None
    TIME_DIAG.append(
        {
            "experiment": ACTIVE[0],
            "seed": ACTIVE[1],
            "capacity_pct": ACTIVE[2],
            "policy": ACTIVE[3],
            "driver_behavior": spec.driver,
            "fleet_policy": spec.fleet,
            "grid_policy": spec.grid,
            "timestep": int(env.t),
            "fleet_recommended_request_count": int((rec_fleet != pkg.PRIMITIVE_IDLE).sum()),
            "grid_adjusted_request_count": int((rec_grid != pkg.PRIMITIVE_IDLE).sum()),
            "actual_request_count": int((actual != pkg.PRIMITIVE_IDLE).sum()),
            "grid_deferred_request_count": int(grid_deferred),
            "mean_compliance_probability": float(p.mean()),
            "noncompliance_share": float(noncompliant.mean()),
            "queue_high": int(high_queue),
            "queue_avoidance_count": int(queue_avoidance_count),
        }
    )
    state.prev_actions = actual.copy()
    return actual.astype(np.int64)


def install_policies() -> None:
    global DELEGATE_POLICY_ACTIONS
    for spec in POLICIES:
        pkg.POLICY_SPECS[spec.name] = pkg.BehaviorSpec("multi_actor")
    DELEGATE_POLICY_ACTIONS = pkg.policy_actions
    pkg.policy_actions = multi_actor_actions


def prices_for(seed: int, spec: pkg.ScenarioSpec) -> np.ndarray:
    env = pkg.make_env(pkg.run_config(seed, spec), seed=seed)
    return np.asarray(env.price_schedule[: env.config.episode_hours], dtype=float)


def add_cost_and_ramp(row: dict[str, Any], by_time: list[dict[str, Any]], seed: int, spec: pkg.ScenarioSpec) -> None:
    prices = prices_for(seed, spec)
    delivered = np.asarray([float(rec.get("delivered_kwh", 0.0)) for rec in by_time], dtype=float)
    load = np.asarray([float(rec.get("delivered_kw", rec.get("delivered_kwh", 0.0))) for rec in by_time], dtype=float)
    price_vec = prices[: len(delivered)] if len(prices) >= len(delivered) else np.resize(prices, len(delivered))
    ramps = np.abs(np.diff(load)) if load.size > 1 else np.asarray([0.0])
    row["energy_cost_usd"] = float((delivered * price_vec).sum())
    row["ramp_p95_kw"] = float(np.percentile(ramps, 95)) if ramps.size else 0.0
    row["demand_charge_exposure_usd_month_25"] = float(row.get("peak_demand_kw", 0.0)) * DEMAND_CHARGE_RATE_USD_PER_KW_MONTH


def run_one(seed: int, spec: pkg.ScenarioSpec, policy: str) -> dict[str, Any]:
    global ACTIVE
    ACTIVE = ("multi_actor_v2", int(seed), int(spec.capacity_pct), policy)
    result = pkg.evaluate_run("multi_actor_v2", seed, spec, policy)
    row = result["row"]
    row["horizon_hours"] = int(pkg.EPISODE_HOURS)
    if policy in POLICY_BY_NAME:
        m = POLICY_BY_NAME[policy]
        row["driver_behavior"] = m.driver
        row["fleet_policy"] = m.fleet
        row["grid_policy"] = m.grid
        row["multi_actor_description"] = m.description
    else:
        row["driver_behavior"] = "FullyCompliant"
        row["fleet_policy"] = "FleetServiceFirst"
        row["grid_policy"] = "NoGridIncentive"
        row["multi_actor_description"] = "LeastLaxity anchor used for paired thresholds."
    add_cost_and_ramp(row, result["by_time"], seed, spec)
    if policy in POLICY_BY_NAME:
        d = diag()
        denom = max(1.0, d["vehicle_steps"])
        row.update(
            {
                "mean_compliance_probability": d["probability_sum"] / denom,
                "noncompliance_share": d["noncompliance_count"] / denom,
                "fleet_recommended_request_count": int(d["fleet_recommended_request_count"]),
                "grid_adjusted_request_count": int(d["grid_adjusted_request_count"]),
                "actual_request_count_driver_layer": int(d["actual_request_count"]),
                "grid_deferred_request_count": int(d["grid_deferred_request_count"]),
                "queue_high_timesteps": int(d["queue_high_timesteps"]),
                "queue_avoidance_count": int(d["queue_avoidance_count"]),
                "cheap_window_actual_request_share": safe_div(d["cheap_window_actual_request_count"], d["actual_request_count"], default=0.0),
                "claim_boundary": "Operational multi-actor scenario; not causal human behavior, global optimization, filed tariff billing, or site-specific feeder validation.",
            }
        )
    ACTIVE = None
    return result


def run_matrix(seeds: list[int], capacities: list[int], policies: list[str]) -> dict[str, list[dict[str, Any]]]:
    install_policies()
    specs = [pkg.make_spec("multi_actor_v2_caltech_sce", "metro_caltech_sce", "campus/workplace", "multi-actor compact weekly matrix", cap) for cap in capacities]
    total = len(seeds) * len(capacities) * len(policies)
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    idx = 0
    for spec in specs:
        for seed in seeds:
            for policy in policies:
                idx += 1
                print(f"multi_actor_v2: {idx}/{total} {spec.label} seed={seed} policy={policy}", flush=True)
                result = run_one(seed, spec, policy)
                out["rows"].append(result["row"])
                out["by_time"].extend(result["by_time"])
                out["demand_supply"].extend(result["demand_supply"])
    out["rows"] = pkg.pair_with_least_laxity(out["rows"])
    return out


def finite(value: Any, default: float = float("nan")) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def add_actor_scoring(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anchors = {
        (row["experiment"], row["scenario_label"], int(row["capacity_pct"]), int(row["seed"])): row
        for row in rows
        if row["policy"] == "LeastLaxity"
    }
    scored: list[dict[str, Any]] = []
    for row in rows:
        key = (row["experiment"], row["scenario_label"], int(row["capacity_pct"]), int(row["seed"]))
        anchor = anchors.get(key)
        out = dict(row)
        if not anchor:
            scored.append(out)
            continue
        delivered_ratio = finite(out.get("delivered_ratio_vs_ll"), 1.0)
        reliability_delta = finite(out.get("reliability_delta_vs_ll_pp"), 0.0)
        critical_delta = finite(out.get("critical_rnd_delta_vs_ll"), 0.0)
        p95_wait_delta = finite(out.get("p95_wait_delta_vs_ll_min"), 0.0)
        oversub_delta = finite(out.get("oversub_delta_vs_ll"), 0.0)
        requested_nd_delta = finite(out.get("requested_not_delivered_count"), 0.0) - finite(anchor.get("requested_not_delivered_count"), 0.0)
        mean_queue_delta = finite(out.get("mean_queue_length"), 0.0) - finite(anchor.get("mean_queue_length"), 0.0)
        max_queue_delta = finite(out.get("max_queue_length"), 0.0) - finite(anchor.get("max_queue_length"), 0.0)
        cost_ratio = safe_div(finite(out.get("energy_cost_usd"), 0.0), finite(anchor.get("energy_cost_usd"), 0.0), default=1.0)
        demand_charge_ratio = safe_div(
            finite(out.get("demand_charge_exposure_usd_month_25"), 0.0),
            finite(anchor.get("demand_charge_exposure_usd_month_25"), 0.0),
            default=1.0,
        )
        peak_ratio = finite(out.get("peak_ratio_vs_ll"), 1.0)
        par_ratio = safe_div(finite(out.get("peak_to_average_ratio"), 0.0), finite(anchor.get("peak_to_average_ratio"), 0.0), default=1.0)
        ramp_ratio = safe_div(finite(out.get("ramp_p95_kw"), 0.0), finite(anchor.get("ramp_p95_kw"), 0.0), default=1.0)
        load_factor_delta = finite(out.get("load_factor"), 0.0) - finite(anchor.get("load_factor"), 0.0)
        loss_ratio = safe_div(finite(out.get("line_loss_proxy_kw2h"), 0.0), finite(anchor.get("line_loss_proxy_kw2h"), 0.0), default=1.0)

        driver_pass = (
            delivered_ratio >= THRESHOLDS["driver"]["delivered_ratio_vs_anchor_min"]
            and reliability_delta >= THRESHOLDS["driver"]["reliability_delta_vs_anchor_min_pp"]
            and critical_delta <= THRESHOLDS["driver"]["critical_requested_not_delivered_delta_max"]
        )
        fleet_queue_pass = (
            p95_wait_delta <= THRESHOLDS["fleet"]["p95_wait_delta_max_minutes"]
            and mean_queue_delta <= THRESHOLDS["fleet"]["mean_queue_delta_max"]
            and max_queue_delta <= THRESHOLDS["fleet"]["max_queue_delta_max"]
            and requested_nd_delta <= THRESHOLDS["fleet"]["requested_not_delivered_delta_max"]
        )
        fleet_cost_pass = (
            cost_ratio <= THRESHOLDS["fleet"]["energy_cost_ratio_max"]
            and demand_charge_ratio <= THRESHOLDS["fleet"]["demand_charge_exposure_ratio_max"]
        )
        fleet_pass = fleet_queue_pass and fleet_cost_pass
        grid_peak_pass = peak_ratio <= THRESHOLDS["grid"]["peak_ratio_vs_anchor_max"]
        grid_shape_pass = (
            par_ratio <= THRESHOLDS["grid"]["peak_to_average_ratio_vs_anchor_max"]
            and ramp_ratio <= THRESHOLDS["grid"]["ramp_p95_ratio_vs_anchor_max"]
            and load_factor_delta >= THRESHOLDS["grid"]["load_factor_delta_min"]
            and loss_ratio <= THRESHOLDS["grid"]["squared_load_proxy_ratio_max"]
        )
        grid_pass = grid_peak_pass and grid_shape_pass
        bits = (driver_pass, fleet_pass, grid_pass)
        pattern = actor_failure_pattern(*bits)
        out.update(
            {
                "anchor_policy": "LeastLaxity",
                "driver_service_pass": bool(driver_pass),
                "fleet_queue_pass": bool(fleet_queue_pass),
                "fleet_cost_pass": bool(fleet_cost_pass),
                "fleet_operation_pass": bool(fleet_pass),
                "grid_peak_pass": bool(grid_peak_pass),
                "grid_shape_pass": bool(grid_shape_pass),
                "grid_pass": bool(grid_pass),
                "all_pass": bool(driver_pass and fleet_pass and grid_pass),
                "final_acceptability_class": "mutually_acceptable" if driver_pass and fleet_pass and grid_pass else "not_mutually_acceptable",
                "actor_failure_pattern": pattern,
                "first_failed_layer": first_failed_layer(*bits),
                "requested_not_delivered_delta_vs_anchor": requested_nd_delta,
                "mean_queue_delta_vs_anchor": mean_queue_delta,
                "max_queue_delta_vs_anchor": max_queue_delta,
                "energy_cost_ratio_vs_anchor": cost_ratio,
                "energy_cost_delta_usd_vs_anchor": finite(out.get("energy_cost_usd"), 0.0) - finite(anchor.get("energy_cost_usd"), 0.0),
                "demand_charge_ratio_vs_anchor": demand_charge_ratio,
                "demand_charge_delta_usd_month_25_vs_anchor": finite(out.get("demand_charge_exposure_usd_month_25"), 0.0) - finite(anchor.get("demand_charge_exposure_usd_month_25"), 0.0),
                "peak_to_average_ratio_vs_anchor": par_ratio,
                "ramp_p95_ratio_vs_anchor": ramp_ratio,
                "load_factor_delta_vs_anchor": load_factor_delta,
                "squared_load_proxy_ratio_vs_anchor": loss_ratio,
            }
        )
        scored.append(out)
    return scored


def actor_failure_pattern(driver_pass: bool, fleet_pass: bool, grid_pass: bool) -> str:
    failed = []
    if not driver_pass:
        failed.append("driver")
    if not fleet_pass:
        failed.append("fleet")
    if not grid_pass:
        failed.append("grid")
    if not failed:
        return "all_pass"
    if len(failed) == 1:
        return f"{failed[0]}_only_fail"
    return "_".join(failed) + "_fail"


def first_failed_layer(driver_pass: bool, fleet_pass: bool, grid_pass: bool) -> str:
    if not driver_pass:
        return "driver"
    if not fleet_pass:
        return "fleet"
    if not grid_pass:
        return "grid"
    return "none"


def summarize_policy_capacity(df: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["driver_behavior", "fleet_policy", "grid_policy", "policy", "capacity_pct"]
    return (
        df.groupby(group_cols, dropna=False)
        .agg(
            rows=("policy", "size"),
            driver_pass_rows=("driver_service_pass", "sum"),
            fleet_pass_rows=("fleet_operation_pass", "sum"),
            grid_pass_rows=("grid_pass", "sum"),
            mutually_acceptable_rows=("all_pass", "sum"),
            mean_delivered_ratio=("delivered_ratio_vs_ll", "mean"),
            mean_peak_ratio=("peak_ratio_vs_ll", "mean"),
            mean_energy_cost_ratio=("energy_cost_ratio_vs_anchor", "mean"),
            mean_p95_wait_delta_min=("p95_wait_delta_vs_ll_min", "mean"),
            mean_demand_charge_delta_usd_month_25=("demand_charge_delta_usd_month_25_vs_anchor", "mean"),
            mean_ramp_p95_ratio=("ramp_p95_ratio_vs_anchor", "mean"),
            dominant_failure_pattern=("actor_failure_pattern", lambda s: s.value_counts().index[0]),
        )
        .reset_index()
    )


def summarize_patterns(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["actor_failure_pattern", "driver_behavior", "fleet_policy", "grid_policy"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["actor_failure_pattern", "rows"], ascending=[True, False])
    )


def summarize_acceptability(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["driver_behavior", "fleet_policy", "grid_policy", "final_acceptability_class"], dropna=False)
        .size()
        .reset_index(name="rows")
    )


def fleet_grid_results(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["fleet_policy", "grid_policy", "capacity_pct"], dropna=False)
        .agg(
            rows=("policy", "size"),
            driver_pass_rate=("driver_service_pass", "mean"),
            fleet_pass_rate=("fleet_operation_pass", "mean"),
            grid_pass_rate=("grid_pass", "mean"),
            mutual_acceptability_rate=("all_pass", "mean"),
            energy_cost_ratio_mean=("energy_cost_ratio_vs_anchor", "mean"),
            peak_ratio_mean=("peak_ratio_vs_ll", "mean"),
            p95_wait_delta_mean=("p95_wait_delta_vs_ll_min", "mean"),
            demand_charge_delta_mean=("demand_charge_delta_usd_month_25_vs_anchor", "mean"),
        )
        .reset_index()
    )


def fleet_success_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = df[df["policy"] != "LeastLaxity"].copy()
    return (
        rows.groupby(["driver_behavior", "fleet_policy", "grid_policy", "capacity_pct"], dropna=False)
        .agg(
            rows=("policy", "size"),
            driver_pass_rate=("driver_service_pass", "mean"),
            fleet_pass_rate=("fleet_operation_pass", "mean"),
            grid_pass_rate=("grid_pass", "mean"),
            mutual_acceptability_rate=("all_pass", "mean"),
            delivered_ratio_mean=("delivered_ratio_vs_ll", "mean"),
            requested_not_delivered_delta_mean=("requested_not_delivered_delta_vs_anchor", "mean"),
            critical_rnd_delta_mean=("critical_rnd_delta_vs_ll", "mean"),
            p95_wait_delta_mean=("p95_wait_delta_vs_ll_min", "mean"),
            mean_queue_delta_mean=("mean_queue_delta_vs_anchor", "mean"),
            max_queue_delta_mean=("max_queue_delta_vs_anchor", "mean"),
            energy_cost_ratio_mean=("energy_cost_ratio_vs_anchor", "mean"),
            peak_ratio_mean=("peak_ratio_vs_ll", "mean"),
            demand_charge_delta_mean=("demand_charge_delta_usd_month_25_vs_anchor", "mean"),
            dominant_failure_pattern=("actor_failure_pattern", lambda s: s.value_counts().index[0]),
        )
        .reset_index()
    )


def write_fleet_balanced_report(df: pd.DataFrame, fleet_success: pd.DataFrame) -> None:
    balanced = fleet_success[fleet_success["fleet_policy"] == "FleetBalanced"].copy()
    queue_aware = fleet_success[fleet_success["fleet_policy"] == "FleetQueueAware"].copy()
    service_first = fleet_success[fleet_success["fleet_policy"] == "FleetServiceFirst"].copy()
    cost_only = fleet_success[fleet_success["fleet_policy"] == "FleetCostOnly"].copy()

    def total_rate(frame: pd.DataFrame, col: str) -> str:
        if frame.empty:
            return "n/a"
        return fmt(float((frame[col] * frame["rows"]).sum() / max(1, frame["rows"].sum())), 3)

    lines = [
        "# FleetBalanced Extension Report",
        "",
        "FleetBalanced is a pre-registered heuristic demonstration policy. It is not a global optimizer and should not be presented as proof that fleet management is solved.",
        "",
        "## FleetBalanced Heuristic Contract",
        "",
        "- Dominant objective: preserve delivered service and critical requests.",
        "- Second objective: reduce queue pressure without blocking critical or low-SoC vehicles.",
        "- Third objective: reduce peak/load-shape pressure when the grid scenario adds a peak cap.",
        "- Last objective: use price only as a tie-breaker for high-SoC, non-critical, flexible requests.",
        "",
        "Weights recorded in `threshold_config.json`: `w_service=100`, `w_critical=100`, `w_queue=10`, `w_peak=3`, `w_cost=1`.",
        "",
        "## Acceptance Criteria",
        "",
        "`mutual_acceptability` means driver, fleet, and grid flags all pass on the same row. Driver pass requires delivered-kWh ratio >= 0.95, reliability delta >= -0.5 percentage points, and critical requested-not-delivered delta <= 24 vehicle-steps. Fleet pass uses queue/wait, unserved-energy, energy-cost, and illustrative demand-charge thresholds. Grid pass uses peak and load-shape proxy thresholds.",
        "",
        "## Aggregate Comparison",
        "",
        "| fleet policy | rows | driver pass rate | fleet pass rate | grid pass rate | mutual acceptability rate | mean delivered ratio | mean peak ratio |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, frame in [
        ("FleetServiceFirst", service_first),
        ("FleetCostOnly", cost_only),
        ("FleetQueueAware", queue_aware),
        ("FleetBalanced", balanced),
    ]:
        if frame.empty:
            continue
        rows_n = int(frame["rows"].sum())
        mean_del = float((frame["delivered_ratio_mean"] * frame["rows"]).sum() / max(1, rows_n))
        mean_peak = float((frame["peak_ratio_mean"] * frame["rows"]).sum() / max(1, rows_n))
        lines.append(
            f"| `{name}` | {rows_n} | {total_rate(frame, 'driver_pass_rate')} | {total_rate(frame, 'fleet_pass_rate')} | "
            f"{total_rate(frame, 'grid_pass_rate')} | {total_rate(frame, 'mutual_acceptability_rate')} | {fmt(mean_del)} | {fmt(mean_peak)} |"
        )
    lines.extend(
        [
            "",
            "## FleetQueueAware Diagnostic",
            "",
            "FleetQueueAware's lower delivered ratio appears sufficient to push the tested cases below the actor-acceptance thresholds. This is a simulator diagnostic, not a general causal proof that queue-aware fleet management is invalid.",
            "",
            "FleetBalanced differs in two ways: it starts from the service-first LeastLaxity recommendation, and it applies queue/price/peak penalties mainly to high-SoC, non-critical, flexible requests. It should be interpreted as a bounded service-preserving heuristic.",
            "",
            "## Claim Boundary",
            "",
            "FleetBalanced should be described as a simple service-preserving fleet heuristic that can succeed under compliant or mildly inattentive driver response. It should not be described as optimized, calibrated, universally superior, or robust to all driver behavior layers.",
        ]
    )
    write_text(FLEET_BALANCED_REPORT, "\n".join(lines))


def write_threshold_files() -> None:
    write_text(THRESHOLD_JSON, json.dumps(THRESHOLDS, indent=2, sort_keys=True))
    lines = [
        "# Multi-Actor Threshold Configuration",
        "",
        "Thresholds are pre-specified diagnostic screens for this compact v2 experiment. They are not universal policy standards.",
        "",
        "## Driver",
        "",
        f"- Delivered kWh ratio vs LeastLaxity anchor >= `{THRESHOLDS['driver']['delivered_ratio_vs_anchor_min']}`.",
        f"- Reliability delta vs anchor >= `{THRESHOLDS['driver']['reliability_delta_vs_anchor_min_pp']}` percentage points.",
        f"- Critical requested-not-delivered delta <= `{THRESHOLDS['driver']['critical_requested_not_delivered_delta_max']}` vehicle-steps.",
        "",
        "## Fleet",
        "",
        f"- p95 wait delta <= `{THRESHOLDS['fleet']['p95_wait_delta_max_minutes']}` minutes.",
        f"- Mean queue delta <= `{THRESHOLDS['fleet']['mean_queue_delta_max']}` vehicles.",
        f"- Max queue delta <= `{THRESHOLDS['fleet']['max_queue_delta_max']}` vehicles.",
        f"- Requested-not-delivered delta <= `{THRESHOLDS['fleet']['requested_not_delivered_delta_max']}` vehicle-steps.",
        f"- Energy-cost ratio <= `{THRESHOLDS['fleet']['energy_cost_ratio_max']}`.",
        f"- Illustrative demand-charge exposure ratio <= `{THRESHOLDS['fleet']['demand_charge_exposure_ratio_max']}`.",
        "",
        "## Grid",
        "",
        f"- Peak ratio <= `{THRESHOLDS['grid']['peak_ratio_vs_anchor_max']}`.",
        f"- Peak-to-average ratio <= `{THRESHOLDS['grid']['peak_to_average_ratio_vs_anchor_max']}` times anchor.",
        f"- p95 ramp ratio <= `{THRESHOLDS['grid']['ramp_p95_ratio_vs_anchor_max']}` times anchor.",
        f"- Load-factor delta >= `{THRESHOLDS['grid']['load_factor_delta_min']}`.",
        f"- Squared-load proxy ratio <= `{THRESHOLDS['grid']['squared_load_proxy_ratio_max']}`.",
        "",
        "Mutual acceptability requires driver, fleet, and grid pass flags to all be true. The flags are computed independently; fleet/grid flags are not copied from driver service.",
    ]
    write_text(THRESHOLD_MD, "\n".join(lines))


def write_state_action_audit() -> None:
    lines = [
        "# State, Action, and Aggregate Mapping",
        "",
        "| concept | implemented source / proxy | missing or bounded element |",
        "|---|---|---|",
        "| `s_i,t` SoC | `obs['soc']` through `pkg._arrays` | none |",
        "| `u_i,t` urgency/service pressure | `_service_critical(values)`, `time_to`, `deadline_deficit`, `laxity` | proxy, not trip-purpose model |",
        "| `q_t` queue pressure | `env.charger_queues`, `queue_length_after`, `p95_wait_minutes` | no station choice outside simulated site |",
        "| `p_t` electricity price | `env.price_schedule` | SCE-like simulator schedule, not filed bill |",
        "| `c_t` charger capacity | `env.n_slots` by location and capacity percentage | static slots over episode |",
        "| `a_i,t^rec` recommendation | fleet policy recommendation before driver layer | recorded as request counts, not per-vehicle CSV |",
        "| `a_i,t^act` actual action | post-compliance action passed to `env.step(actions)` | primitive action semantics from existing wrapper |",
        "| `e_i,t` delivered energy | `env._last_charge_stored_actual_kwh` aggregated in existing runner | per-vehicle values not written in v2 row file |",
        "| `L_t` aggregate load | `delivered_kw` by timestep | one-hour timestep proxy |",
        "| `W_i,t` waiting time | `env.agent_wait_time` summarized as mean/p95 | no monetized inconvenience calibration |",
        "| `I_i,t` inconvenience | unavailable; proxied by noncompliance and queue burden | not modeled as calibrated utility |",
        "",
        "The queue admission, persistence, charging, departure, and failure accounting remain the existing simulator implementation. v2 changes only the action policy layer and independent actor scoring.",
    ]
    write_text(STATE_ACTION_AUDIT, "\n".join(lines))


def write_manifest(command: str, rows: pd.DataFrame, seeds: list[int], capacities: list[int], policies: list[str]) -> None:
    manifest = [
        {
            "artifact_name": "multi_actor_v2_weekly_matrix",
            "path": str(RESULTS_CSV),
            "exists": RESULTS_CSV.exists(),
            "row_count": len(rows),
            "seeds": ",".join(map(str, seeds)),
            "capacities": ",".join(map(str, capacities)),
            "horizon_hours": int(pkg.EPISODE_HOURS),
            "policies": ",".join(policies),
            "command": command,
            "interpretation_allowed": "compact weekly multi-actor action-changing scenario evidence with independent actor scoring",
            "interpretation_not_allowed": "causal human behavior, global optimal control, filed tariff billing, actual feeder validation, full taxi/bus/truck routing",
        }
    ]
    write_csv(MANIFEST_CSV, manifest)


def check_multi_actor_story(df: pd.DataFrame) -> dict[str, Any]:
    rows = df[df["policy"] != "LeastLaxity"].copy()
    checks = {
        "driver_pass_fleet_fail_rows": int(((rows["driver_service_pass"]) & (~rows["fleet_operation_pass"])).sum()),
        "driver_fleet_pass_grid_fail_rows": int(((rows["driver_service_pass"]) & (rows["fleet_operation_pass"]) & (~rows["grid_pass"])).sum()),
        "driver_fail_fleet_grid_pass_rows": int(((~rows["driver_service_pass"]) & (rows["fleet_operation_pass"]) & (rows["grid_pass"])).sum()),
        "cost_only_rows": int((rows["fleet_policy"] == "FleetCostOnly").sum()),
        "cost_only_energy_cost_improved_rows": int(((rows["fleet_policy"] == "FleetCostOnly") & (rows["energy_cost_delta_usd_vs_anchor"] < 0)).sum()),
        "cost_only_harm_driver_or_grid_rows": int(((rows["fleet_policy"] == "FleetCostOnly") & ((~rows["driver_service_pass"]) | (~rows["grid_pass"]))).sum()),
        "grid_peak_penalty_rows": int((rows["grid_policy"] == "GridPeakPenalty").sum()),
        "grid_peak_penalty_grid_pass_rows": int(((rows["grid_policy"] == "GridPeakPenalty") & (rows["grid_pass"])).sum()),
        "queue_aware_rows": int((rows["fleet_policy"] == "FleetQueueAware").sum()),
        "queue_aware_driver_fleet_pass_rows": int(((rows["fleet_policy"] == "FleetQueueAware") & (rows["driver_service_pass"]) & (rows["fleet_operation_pass"])).sum()),
    }
    checks["supports_balancing_title"] = (
        checks["driver_pass_fleet_fail_rows"] > 0
        or checks["driver_fleet_pass_grid_fail_rows"] > 0
        or checks["driver_fail_fleet_grid_pass_rows"] > 0
    )
    return checks


def write_report(command: str, start: float, end: float, seeds: list[int], capacities: list[int], policies: list[str], df: pd.DataFrame, summary: pd.DataFrame, checks: dict[str, Any], stdout_text: str, stderr_text: str) -> None:
    pattern_counts = df["actor_failure_pattern"].value_counts().to_dict()
    lines = [
        "# Multi-Actor v2 Readiness Report",
        "",
        "## Execution",
        "",
        f"Command: `{command}`",
        f"Start: `{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start))}`",
        f"End: `{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end))}`",
        f"Runtime seconds: `{end - start:.1f}`",
        f"Rows: `{len(df)}`",
        f"Seeds: `{seeds}`",
        f"Capacities: `{capacities}`",
        f"Policies: `{len(policies)}`",
        "",
        "## Independent Actor Checks",
        "",
        f"- Rows where driver passes but fleet fails: `{checks['driver_pass_fleet_fail_rows']}`",
        f"- Rows where driver and fleet pass but grid fails: `{checks['driver_fleet_pass_grid_fail_rows']}`",
        f"- Rows where driver fails but fleet and grid pass: `{checks['driver_fail_fleet_grid_pass_rows']}`",
        f"- Cost-only rows with lower energy cost than anchor: `{checks['cost_only_energy_cost_improved_rows']}/{checks['cost_only_rows']}`",
        f"- Cost-only rows harming driver or grid outcomes: `{checks['cost_only_harm_driver_or_grid_rows']}/{checks['cost_only_rows']}`",
        f"- GridPeakPenalty rows passing grid diagnostics: `{checks['grid_peak_penalty_grid_pass_rows']}/{checks['grid_peak_penalty_rows']}`",
        f"- QueueAware rows preserving driver and fleet operation: `{checks['queue_aware_driver_fleet_pass_rows']}/{checks['queue_aware_rows']}`",
        "",
        "## Actor Failure Pattern Counts",
        "",
        "| pattern | rows |",
        "|---|---:|",
    ]
    for pattern, count in sorted(pattern_counts.items()):
        lines.append(f"| `{pattern}` | {int(count)} |")
    lines.extend(
        [
            "",
            "## Summary Preview",
            "",
            "| driver | fleet | grid | cap | rows | mutual | driver pass | fleet pass | grid pass | peak ratio | cost ratio |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for rec in summary.sort_values(["fleet_policy", "grid_policy", "driver_behavior", "capacity_pct"]).head(80).to_dict("records"):
        lines.append(
            f"| `{rec['driver_behavior']}` | `{rec['fleet_policy']}` | `{rec['grid_policy']}` | {int(rec['capacity_pct'])} | {int(rec['rows'])} | "
            f"{int(rec['mutually_acceptable_rows'])} | {int(rec['driver_pass_rows'])} | {int(rec['fleet_pass_rows'])} | {int(rec['grid_pass_rows'])} | "
            f"{fmt(rec['mean_peak_ratio'])} | {fmt(rec['mean_energy_cost_ratio'])} |"
        )
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            "The balancing title is supported only if independent actor failures appear in the checks above. If all failures collapse to driver-only service failure, the safer title remains a service-first diagnostic paper.",
            "",
            f"Supports balancing-title evidence: `{checks['supports_balancing_title']}`",
            "",
            "## Boundaries",
            "",
            "- Driver scenarios are operational compliance-response scenarios, not causal human-behavior estimates.",
            "- Fleet and grid policies are heuristic action-changing policy variants, not global optimization or a solved game.",
            "- Demand-charge exposure is illustrative and uses a fixed USD/kW-month rate.",
            "- Grid pass uses load-shape proxies in this weekly matrix; representative IEEE33 feeder screening remains a separate diagnostic layer.",
        ]
    )
    write_text(READINESS_REPORT, "\n".join(lines))
    write_text(
        RUN_LOG,
        "\n".join(
            [
                "# RUN LOG",
                "",
                f"command: `{command}`",
                f"start: `{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start))}`",
                f"end: `{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end))}`",
                f"runtime_seconds: `{end - start:.1f}`",
                f"rows: `{len(df)}`",
                f"seeds: `{seeds}`",
                f"capacities: `{capacities}`",
                f"policies: `{policies}`",
                "",
                "## stdout tail",
                "",
                "```",
                "\n".join(stdout_text.strip().splitlines()[-120:]),
                "```",
                "",
                "## stderr tail",
                "",
                "```",
                "\n".join(stderr_text.strip().splitlines()[-120:]),
                "```",
            ]
        ),
    )


def compliance_soc_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (experiment, seed, capacity, policy, bin_name), vals in sorted(SOC_DIAG.items()):
        denom = max(1.0, vals["vehicle_steps"])
        pol = POLICY_BY_NAME.get(policy)
        rows.append(
            {
                "experiment": experiment,
                "seed": seed,
                "capacity_pct": capacity,
                "policy": policy,
                "driver_behavior": pol.driver if pol else "",
                "fleet_policy": pol.fleet if pol else "",
                "grid_policy": pol.grid if pol else "",
                "soc_bin": bin_name,
                "vehicle_steps": int(vals["vehicle_steps"]),
                "mean_compliance_probability": vals["probability_sum"] / denom,
                "noncompliance_share": vals["noncompliance_count"] / denom,
                "recommended_request_share": vals["recommended_request_count"] / denom,
                "actual_request_share": vals["actual_request_count"] / denom,
            }
        )
    return rows


def plot_framework() -> None:
    fig, ax = plt.subplots(figsize=(8.5, 3.0))
    ax.axis("off")
    boxes = [
        (0.06, 0.55, "Fleet policy\n$ a^{rec}_{i,t} $"),
        (0.34, 0.55, "Grid incentive\npeak / smooth cap"),
        (0.62, 0.55, "Driver compliance\n$ a^{act}_{i,t} $"),
        (0.22, 0.12, "Simulator\nqueue + charging"),
        (0.54, 0.12, "Independent actor scoring\ndriver / fleet / grid"),
    ]
    for x, y, text in boxes:
        ax.text(x, y, text, ha="center", va="center", fontsize=10, bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="black", lw=1.0))
    arrows = [((0.16, 0.55), (0.26, 0.55)), ((0.44, 0.55), (0.52, 0.55)), ((0.62, 0.44), (0.34, 0.24)), ((0.34, 0.12), (0.43, 0.12))]
    for start, end in arrows:
        ax.annotate("", xy=end, xytext=start, arrowprops=dict(arrowstyle="->", lw=1.2, color="black"))
    save_figure(fig, "multi_actor_framework")


def plot_heatmap(summary: pd.DataFrame) -> None:
    plot = summary[summary["policy"] != "LeastLaxity"].copy()
    labels = []
    for rec in plot[["driver_behavior", "fleet_policy", "grid_policy", "policy"]].drop_duplicates().to_dict("records"):
        labels.append((rec["policy"], f"{rec['driver_behavior']}\n{rec['fleet_policy'].replace('Fleet','')}\n{rec['grid_policy'].replace('Grid','')}"))
    caps = sorted(plot["capacity_pct"].unique(), reverse=True)
    data = np.full((len(labels), len(caps)), np.nan)
    text = [["" for _ in caps] for _ in labels]
    for i, (policy, _) in enumerate(labels):
        for j, cap in enumerate(caps):
            sub = plot[(plot["policy"] == policy) & (plot["capacity_pct"] == cap)]
            if sub.empty:
                continue
            rec = sub.iloc[0]
            rate = rec["mutually_acceptable_rows"] / max(1, rec["rows"])
            data[i, j] = rate
            text[i][j] = f"{int(rec['mutually_acceptable_rows'])}/{int(rec['rows'])}\n{rec['dominant_failure_pattern'].replace('_fail','').replace('_','+')}"
    fig_h = max(5.0, 0.45 * len(labels))
    fig, ax = plt.subplots(figsize=(8.8, fig_h))
    im = ax.imshow(data, vmin=0, vmax=1, cmap="Greys")
    ax.set_xticks(range(len(caps)), [f"{c}%" for c in caps])
    ax.set_yticks(range(len(labels)), [lbl for _, lbl in labels], fontsize=7)
    for i in range(len(labels)):
        for j in range(len(caps)):
            ax.text(j, i, text[i][j], ha="center", va="center", fontsize=6.5, color="black" if data[i, j] < 0.65 else "white")
    ax.set_title("Mutual acceptability by driver, fleet, grid policy and capacity")
    cbar = fig.colorbar(im, ax=ax, shrink=0.7)
    cbar.set_label("mutually acceptable share")
    fig.tight_layout()
    save_figure(fig, "actor_failure_pattern_heatmap")


def plot_tradeoff(df: pd.DataFrame) -> None:
    plot = df[df["policy"] != "LeastLaxity"].copy()
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    markers = {"FleetServiceFirst": "o", "FleetCostOnly": "s", "FleetQueueAware": "^", "FleetAvailabilityFocused": "D"}
    for fleet, group in plot.groupby("fleet_policy"):
        ax.scatter(group["energy_cost_ratio_vs_anchor"], group["peak_ratio_vs_ll"], s=28, alpha=0.65, label=fleet.replace("Fleet", ""), marker=markers.get(fleet, "o"), edgecolors="none")
    ax.axvline(1.0, color="0.35", lw=0.8)
    ax.axhline(1.0, color="0.35", lw=0.8)
    ax.axhline(THRESHOLDS["grid"]["peak_ratio_vs_anchor_max"], color="0.2", lw=0.8, ls="--")
    ax.axvline(THRESHOLDS["fleet"]["energy_cost_ratio_max"], color="0.2", lw=0.8, ls="--")
    ax.set_xlabel("Energy cost ratio vs LeastLaxity anchor")
    ax.set_ylabel("Peak ratio vs LeastLaxity anchor")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Fleet cost and grid peak trade-off")
    fig.tight_layout()
    save_figure(fig, "driver_fleet_grid_tradeoff_frontier")


def plot_compliance_by_soc(soc_df: pd.DataFrame) -> None:
    if soc_df.empty:
        return
    plot = soc_df.groupby(["driver_behavior", "soc_bin"], dropna=False).agg(mean_p=("mean_compliance_probability", "mean"), noncomp=("noncompliance_share", "mean")).reset_index()
    drivers = [d for d in plot["driver_behavior"].unique() if d]
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    for driver in drivers:
        sub = plot[plot["driver_behavior"] == driver]
        ax.plot(sub["soc_bin"], sub["mean_p"], marker="o", lw=1.2, label=driver)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("SoC bin")
    ax.set_ylabel("Mean compliance probability")
    ax.legend(frameon=False, fontsize=7, ncol=2)
    ax.set_title("Compliance scenario mapping by SoC")
    fig.tight_layout()
    save_figure(fig, "compliance_by_soc")


def plot_fleet_policy_comparison(fleet_grid: pd.DataFrame) -> None:
    plot = fleet_grid.groupby(["fleet_policy", "capacity_pct"], dropna=False).agg(
        mutual=("mutual_acceptability_rate", "mean"),
        cost=("energy_cost_ratio_mean", "mean"),
        wait=("p95_wait_delta_mean", "mean"),
    ).reset_index()
    caps = sorted(plot["capacity_pct"].unique())
    fleets = sorted(plot["fleet_policy"].unique())
    x = np.arange(len(caps))
    width = 0.8 / max(1, len(fleets))
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    for k, fleet in enumerate(fleets):
        vals = [float(plot[(plot["fleet_policy"] == fleet) & (plot["capacity_pct"] == cap)]["mutual"].mean()) for cap in caps]
        ax.bar(x + (k - (len(fleets) - 1) / 2) * width, vals, width=width, label=fleet.replace("Fleet", ""), color=str(0.25 + 0.12 * k))
    ax.set_xticks(x, [f"{cap}%" for cap in caps])
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Capacity")
    ax.set_ylabel("Mutual acceptability rate")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Fleet policy comparison")
    fig.tight_layout()
    save_figure(fig, "fleet_policy_comparison")


def plot_grid_policy_comparison(fleet_grid: pd.DataFrame) -> None:
    plot = fleet_grid.groupby(["grid_policy", "capacity_pct"], dropna=False).agg(
        grid_pass=("grid_pass_rate", "mean"),
        peak=("peak_ratio_mean", "mean"),
        dc=("demand_charge_delta_mean", "mean"),
    ).reset_index()
    caps = sorted(plot["capacity_pct"].unique())
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    for grid, group in plot.groupby("grid_policy"):
        vals = [float(group[group["capacity_pct"] == cap]["peak"].mean()) for cap in caps]
        ax.plot(caps, vals, marker="o", lw=1.3, label=grid.replace("Grid", ""))
    ax.axhline(1.0, color="0.35", lw=0.8)
    ax.axhline(THRESHOLDS["grid"]["peak_ratio_vs_anchor_max"], color="0.25", lw=0.8, ls="--")
    ax.set_xlabel("Capacity (%)")
    ax.set_ylabel("Mean peak ratio vs anchor")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Grid policy comparison")
    fig.tight_layout()
    save_figure(fig, "grid_policy_comparison")


def save_figure(fig: plt.Figure, name: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def write_plot_data(df: pd.DataFrame, summary: pd.DataFrame, fleet_grid: pd.DataFrame, soc: pd.DataFrame) -> None:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(PLOT_DIR / "plot_data_multi_actor_v2_rows.csv", index=False)
    summary.to_csv(PLOT_DIR / "plot_data_policy_capacity_summary.csv", index=False)
    fleet_grid.to_csv(PLOT_DIR / "plot_data_fleet_grid_policy_results.csv", index=False)
    soc.to_csv(PLOT_DIR / "plot_data_compliance_by_soc.csv", index=False)


def generate_figures(df: pd.DataFrame, summary: pd.DataFrame, fleet_grid: pd.DataFrame, soc: pd.DataFrame) -> None:
    plot_framework()
    plot_heatmap(summary)
    plot_tradeoff(df)
    plot_compliance_by_soc(soc)
    plot_fleet_policy_comparison(fleet_grid)
    plot_grid_policy_comparison(fleet_grid)


def copy_to_multi_actor_folder() -> None:
    EXTERNAL_COPY_DIR.parent.mkdir(parents=True, exist_ok=True)
    if EXTERNAL_COPY_DIR.exists():
        backup = EXTERNAL_COPY_DIR.with_name(EXTERNAL_COPY_DIR.name + "_backup_" + time.strftime("%Y%m%d_%H%M%S"))
        shutil.copytree(EXTERNAL_COPY_DIR, backup)
    shutil.copytree(OUT_DIR, EXTERNAL_COPY_DIR, dirs_exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--seed-start", type=int, default=DEFAULT_SEED_START)
    parser.add_argument("--capacities", type=str, default=",".join(map(str, DEFAULT_CAPACITIES)))
    parser.add_argument("--policies", type=str, default=",".join(DEFAULT_POLICIES))
    parser.add_argument("--episode-hours", type=int, default=pkg.EPISODE_HOURS)
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    parser.add_argument("--copy-to-multi-actor-folder", action="store_true")
    parser.add_argument("--command", type=str, default="")
    args = parser.parse_args()
    set_output_dir(Path(args.out_dir))
    pkg.EPISODE_HOURS = int(args.episode_hours)

    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    capacities = parse_int_list(args.capacities)
    policies = [p.strip() for p in args.policies.split(",") if p.strip()]
    unknown = [p for p in policies if p != "LeastLaxity" and p not in POLICY_BY_NAME]
    if unknown:
        raise ValueError(f"Unknown policies: {unknown}")
    command = args.command or "python " + " ".join(sys.argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    write_threshold_files()
    write_state_action_audit()

    start = time.time()
    stdout_buffer, stderr_buffer = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
        aggregate = run_matrix(seeds, capacities, policies)
    end = time.time()

    rows = add_actor_scoring(aggregate["rows"])
    row_df = pd.DataFrame(rows)
    row_df.to_csv(RESULTS_CSV, index=False)
    pd.DataFrame(aggregate["by_time"]).to_csv(TIME_CSV, index=False)
    write_csv(DRIVER_DIAG_CSV, [{**{"experiment": k[0], "seed": k[1], "capacity_pct": k[2], "policy": k[3]}, **dict(v)} for k, v in sorted(DIAG.items())])
    soc_df = pd.DataFrame(compliance_soc_rows())
    soc_df.to_csv(SOC_CSV, index=False)

    summary = summarize_policy_capacity(row_df)
    patterns = summarize_patterns(row_df)
    acceptability = summarize_acceptability(row_df)
    fleet_grid = fleet_grid_results(row_df)
    fleet_success = fleet_success_summary(row_df)
    summary.to_csv(SUMMARY_CSV, index=False)
    patterns.to_csv(PATTERN_CSV, index=False)
    acceptability.to_csv(ACCEPT_CSV, index=False)
    fleet_grid.to_csv(FLEET_GRID_CSV, index=False)
    fleet_success.to_csv(FLEET_SUCCESS_CSV, index=False)
    write_manifest(command, row_df, seeds, capacities, policies)
    write_plot_data(row_df, summary, fleet_grid, soc_df)
    generate_figures(row_df, summary, fleet_grid, soc_df)
    checks = check_multi_actor_story(row_df)
    write_report(command, start, end, seeds, capacities, policies, row_df, summary, checks, stdout_buffer.getvalue(), stderr_buffer.getvalue())
    write_fleet_balanced_report(row_df, fleet_success)
    if args.copy_to_multi_actor_folder:
        copy_to_multi_actor_folder()

    print(f"wrote multi-actor v2 package: {OUT_DIR}")
    print(f"rows: {len(row_df)}")
    print(f"supports_balancing_title: {checks['supports_balancing_title']}")
    print(f"actor_failure_patterns: {row_df['actor_failure_pattern'].value_counts().to_dict()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
