#!/usr/bin/env python3
"""Simulator RESPONSE SURFACE for the multi-actor equilibrium analysis.

We need U_D(d), U_F(d), U_G(d) and all-pass(d) as functions of the aggregate
driver deviation level d (= 1 - aggregate compliance rho), per capacity and grid
policy. The game theory (driver Nash fixed point, Stackelberg incentive design,
Nash bargaining, price of anarchy) then runs analytically on these interpolated
surfaces -- so the expensive simulator is called ONCE on a deviation grid, not
inside every equilibrium iteration.

Aggregate deviation d is realized with the SAME slack-structured per-vehicle
profile validated in Option A (low-slack/inflexible vehicles deviate first),
normalized so the population-mean deviation equals d at each step:
    w_i = 1 - clip(laxity_i,0,1);  k = d / mean(w);  p_dev_i = clip(k*w_i, 0,1).
d=0 is full compliance. The full per-episode metric rows (116 columns) are saved;
utilities are computed downstream in the game-theory module.

Reuses the proven Option-A engine path; only the per-vehicle keep prob changes.
"""
from __future__ import annotations

import importlib.util
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

WORKSPACE = Path("/home/jia/thirfty death BRL DQN")
RUNNER = WORKSPACE / "scripts" / "run_multi_actor_v2_experiment.py"
OUT = Path("/home/jia/multi actor/equilibrium_optimization_20260616")
DATE = "20260616"

import os, json as _json
SEEDS = _json.loads(os.environ.get("RS_SEEDS", "[4541, 4542, 4543, 4544, 4545]"))
CAPACITIES = _json.loads(os.environ.get("RS_CAPS", "[20, 35, 50]"))
EPISODE_HOURS = 168
# Aggregate deviation grid: dense at the low-d transition, coarser high.
DEV_GRID = _json.loads(os.environ.get("RS_DEVGRID",
    "[0.0, 0.0125, 0.025, 0.0375, 0.05, 0.075, 0.10, 0.15, 0.22, 0.32, 0.45]"))
_RS_TAG = os.environ.get("RS_TAG", "")

# A single severity slot whose deviation magnitude we override per grid point.
DRIVER = "Severity1Mild"
DRIVER_CFG = {"reserve_margin": 0.05, "cheap_extra_margin": 0.10}

FLEETS = ("FleetServiceFirst", "FleetServiceGridWeighted")
GRIDS = ("NoGridIncentive", "GridPeakPenalty")
FLEET_LABEL = {"FleetServiceFirst": "ServiceFirst", "FleetServiceGridWeighted": "ServiceGridWeighted"}
GRID_LABEL = {"NoGridIncentive": "NoGrid", "GridPeakPenalty": "PeakPenalty"}

ACTIVE_DEV = 0.0
DEV_ACC: list[float] = []


def import_runner():
    spec = importlib.util.spec_from_file_location("mav2_rs", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {RUNNER}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mav2_rs"] = mod
    spec.loader.exec_module(mod)
    return mod


def structured_p_dev(d: float, laxity: np.ndarray) -> np.ndarray:
    lax = np.clip(np.asarray(laxity, dtype=float), 0.0, 1.0)
    n = lax.shape[0]
    if n == 0:
        return np.zeros(0, dtype=float)
    if d <= 0.0:
        return np.zeros(n, dtype=float)
    w = 1.0 - lax
    mw = float(w.mean())
    if mw <= 1.0e-9:
        return np.full(n, d, dtype=float)
    return np.clip((d / mw) * w, 0.0, 1.0)


def install_direct_extensions(mav2) -> None:
    pkg = mav2.pkg
    original_fleet = mav2._ORIG_FLEET
    original_driver = mav2._ORIG_DRIVER

    def service_grid_weighted(env, obs, rng, is_cheap):
        values = pkg._arrays(env, obs)
        critical = pkg._service_critical(values)
        base_actions = pkg.least_laxity_actions(env, obs)
        actions = base_actions.copy().astype(np.int64)
        pressure = mav2.location_queue_pressure(env, base_actions)
        pressure_vec = np.asarray([pressure.get(mav2.location_type(env, int(i)), 0.0) for i in range(env.n_cars)], dtype=float)
        max_pressure = max(pressure.values()) if pressure else 0.0
        price_schedule = np.asarray(getattr(env, "price_schedule", [1.0]), dtype=float)
        price_now = float(price_schedule[int(env.t) % len(price_schedule)])
        price_norm = price_now / max(float(np.nanmax(price_schedule)), 1.0e-9)
        total_slots = max(1, int(sum(env.n_slots.values())))
        request_count = int((base_actions != pkg.PRIMITIVE_IDLE).sum())
        peak_pressure = max(0.0, (request_count - 0.85 * total_slots) / total_slots)
        low_soc = values["soc"] <= (values["theta"] + 0.05)
        inverse_laxity = 1.0 - np.clip(values["laxity"], 0.0, 1.0)
        service_score = (
            320.0 * critical.astype(float)
            + 175.0 * low_soc.astype(float)
            + 120.0 * values["target_deficit"]
            + 95.0 * values["deadline_deficit"]
            + 55.0 * inverse_laxity
        )
        flexible_low_risk = (
            (base_actions != pkg.PRIMITIVE_IDLE)
            & ~critical
            & ~low_soc
            & (values["soc"] >= values["theta"] + 0.20)
            & (values["target_deficit"] <= 0.12)
        )
        pressure_trigger = (max_pressure >= 0.35) or (peak_pressure > 0.0) or (price_norm >= 0.80)
        if not pressure_trigger or not bool(flexible_low_risk.any()):
            return actions
        grid_penalty = 48.0 * pressure_vec + 32.0 * peak_pressure + 18.0 * price_norm
        priority = service_score - grid_penalty * flexible_low_risk.astype(float)
        candidates = np.where(flexible_low_risk)[0]
        max_defer = max(1, int(math.floor(0.20 * len(candidates))))
        order = sorted(candidates.tolist(), key=lambda i: (float(priority[i]), int(i)))
        defer = np.asarray(order[:max_defer], dtype=int)
        actions[defer] = pkg.PRIMITIVE_IDLE
        return actions.astype(np.int64)

    def direct_fleet(env, obs, fleet, rng, is_cheap):
        if fleet == "FleetServiceGridWeighted":
            return service_grid_weighted(env, obs, rng, is_cheap)
        return original_fleet(env, obs, fleet, rng, is_cheap)

    def severity_preference(env, obs, driver, rng, is_cheap):
        values = pkg._arrays(env, obs)
        critical = pkg._service_critical(values)
        available = values["masks"][:, pkg.PRIMITIVE_NORMAL_REQUEST]
        cheap_now = bool(is_cheap[int(env.t) % len(is_cheap)])
        reserve_threshold = values["theta"] + float(DRIVER_CFG["reserve_margin"])
        if cheap_now:
            reserve_threshold = reserve_threshold + float(DRIVER_CFG["cheap_extra_margin"])
        reserve_need = values["soc"] <= reserve_threshold
        eligible = available & (critical | values["target"] | reserve_need)
        score = (
            260.0 * critical.astype(float)
            + 130.0 * reserve_need.astype(float)
            + 95.0 * values["target_deficit"]
            + 55.0 * values["deadline_deficit"]
            + 35.0 * (1.0 - values["soc"])
            - 10.0 * values["laxity"]
        )
        return pkg._select_cap_limited(env, values, eligible, score, rng, urgent_salience=True).astype(np.int64)

    def direct_driver(env, obs, rec_actions, driver, rng, is_cheap):
        if driver != DRIVER:
            return original_driver(env, obs, rec_actions, driver, rng, is_cheap)
        if ACTIVE_DEV <= 0.0:
            p = np.ones(env.n_cars, dtype=float)
            return rec_actions.astype(np.int64), p, np.zeros(env.n_cars, dtype=bool), 0
        values = pkg._arrays(env, obs)
        laxity = np.asarray(values["laxity"], dtype=float)
        p_dev = structured_p_dev(ACTIVE_DEV, laxity)
        if p_dev.shape[0] > 0:
            DEV_ACC.append(float(p_dev.mean()))
        keep_prob = 1.0 - p_dev
        pref = severity_preference(env, obs, driver, rng, is_cheap)
        keep = rng.random(env.n_cars) >= p_dev
        actual = np.where(keep, rec_actions, pref).astype(np.int64)
        noncompliant = ~keep
        return actual, keep_prob, noncompliant, 0

    mav2.fleet_recommendation = direct_fleet
    mav2.apply_driver_layer = direct_driver

    new_specs: list[Any] = []
    for fleet in FLEETS:
        for grid in GRIDS:
            name = f"D_{DRIVER}__F_{FLEET_LABEL[fleet]}__G_{GRID_LABEL[grid]}"
            desc = f"Response-surface deviation driver {fleet} {grid}."
            new_specs.append(mav2.MultiActorPolicy(name, DRIVER, fleet, grid, desc))
    existing = {p.name for p in mav2.POLICIES}
    for spec in new_specs:
        if spec.name not in existing:
            mav2.POLICIES.append(spec)
    mav2.POLICY_BY_NAME = {p.name: p for p in mav2.POLICIES}


def policy_list(mav2) -> list[str]:
    names = ["LeastLaxity"]
    for fleet in FLEETS:
        for grid in GRIDS:
            names.append(f"D_{DRIVER}__F_{FLEET_LABEL[fleet]}__G_{GRID_LABEL[grid]}")
    return names


def run_dev(mav2, d: float) -> pd.DataFrame:
    global ACTIVE_DEV
    ACTIVE_DEV = d
    mav2.pkg.policy_actions = mav2._ORIG_POLICY_ACTIONS
    install_direct_extensions(mav2)
    aggregate = mav2.run_matrix(SEEDS, CAPACITIES, policy_list(mav2))
    scored = mav2.add_actor_scoring(aggregate["rows"])
    rows = pd.DataFrame(scored)
    rows = rows[rows["policy"] != "LeastLaxity"].copy()
    rows["dev_target"] = d
    return rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    mav2 = import_runner()
    mav2.set_output_dir(OUT / "runner_raw_rs")
    mav2.pkg.EPISODE_HOURS = EPISODE_HOURS
    mav2._ORIG_FLEET = mav2.fleet_recommendation
    mav2._ORIG_DRIVER = mav2.apply_driver_layer
    mav2._ORIG_POLICY_ACTIONS = mav2.pkg.policy_actions

    start = time.time()
    all_rows: list[pd.DataFrame] = []
    for d in DEV_GRID:
        DEV_ACC.clear()
        rows = run_dev(mav2, d)
        realized = float(np.mean(DEV_ACC)) if DEV_ACC else 0.0
        rows["dev_realized"] = realized
        all_rows.append(rows)
        print(f"[d={d:.4f}] rows={len(rows)} realized_dev={realized:.4f} t={time.time()-start:.0f}s", flush=True)

    df = pd.concat(all_rows, ignore_index=True)
    path = OUT / f"response_surface_rows{_RS_TAG}_{DATE}.csv"
    df.to_csv(path, index=False)
    print(f"\nSaved {len(df)} rows -> {path}")
    print(f"Total wall time: {time.time()-start:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
