#!/usr/bin/env python3
"""Multi-actor EQUILIBRIUM / recovery optimization for managed EV charging.

MOTIVATION (from the diagnostic result): under low behavioral deviation the
same-episode all-pass (driver AND fleet AND grid) collapses to ~0. This runner
asks the constructive question the diagnostic paper never answered:

    Is there an OPERATING POINT at which all three actors are satisfied at the
    same time, and what does it cost to reach it?

We model a Stackelberg-style mechanism: the operator (leader) sets two levers,
drivers (followers) respond via a calibrated compliance function, and we search
for the lever setting that restores all-pass at minimum incentive cost.

LEVERS
  1. Driver-side INCENTIVE  c in [0,1]  -> raises compliance (reduces deviation),
     most effective on LOW-slack / inflexible drivers (the ones who deviate most
     and whom monetary incentives move most; OptimizEV, Alexeenko & Bitar 2023).
  2. Grid-side policy: NoGridIncentive vs GridPeakPenalty (reshapes load).

COMPLIANCE MODEL  p_keep_i(slack, c)   [soft / structural calibration]
  Baseline (c=0) deviation is the ACN-anchored severity-1 magnitude, structured
  toward low-slack vehicles (the "realistic" Option-A structure):
        w_i      = 1 - clip(laxity_i, 0, 1)          # inflexibility weight
        k0       = TARGET_DEV_RATE / mean(w)          # normalize pop-mean to 0.05
        p_dev0_i = clip(k0 * w_i, 0, 1)               # no-incentive deviation
  The incentive suppresses a fraction eff(c) of would-be deviation, weighted to
  the inflexible drivers (monetary response is largest where slack is smallest):
        eff_i(c) = c * (0.5 + 0.5 * w_i)              # in [0,1], higher for low slack
        p_dev_i  = p_dev0_i * (1 - eff_i(c))
        p_keep_i = 1 - p_dev_i
  c=0 reproduces the severity-1 collapse; c=1 drives deviation ->0 (full
  compliance reference). The SHAPE (incentive moves low-slack drivers most) is
  taken from the OptimizEV opt-in-vs-slack curve; the magnitude is ACN-anchored.
  This is a soft behavioral calibration, NOT a fitted opt-out model -- reported
  honestly as such.

INCENTIVE COST (transparent, illustrative): the operator pays the incentive only
to the vehicles whose compliance it must buy. Per episode we report the realized
mean induced-compliance mass  M = mean(p_dev0 - p_dev)  and the incentive
intensity c; a simple budget proxy is  B = c * M  (incentive intensity times the
compliance actually purchased). Lower B at equal all-pass is a better mechanism.

EQUILIBRIUM = the minimum-c lever setting (per capacity, per grid policy) at which
all-pass is restored for the service-oriented family. The multi-actor content is
that at high capacity the grid gate caps all-pass regardless of c, so the
operating point requires BOTH levers -- a joint driver+grid equilibrium.

Reuses the proven Option-A engine path; only the driver keep-probability changes.
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

SEEDS = [4541, 4542, 4543, 4544, 4545]
CAPACITIES = [35, 50]                      # 35 = canonical; 50 = grid-limited demo
EPISODE_HOURS = 168
TARGET_DEV_RATE = 0.05                     # ACN-anchored severity-1 pop-mean deviation
INCENTIVES = [0.0, 0.25, 0.50, 0.75, 1.0]  # driver-side incentive intensity c

SEVERITY: dict[str, dict[str, Any]] = {
    "Severity0Full": {
        "level": 0, "label": "full_compliance",
        "keep_probability": 1.00, "reserve_margin": 0.00, "cheap_extra_margin": 0.00,
    },
    "Severity1Mild": {
        "level": 1, "label": "mild_deviation",
        "keep_probability": 0.95, "reserve_margin": 0.05, "cheap_extra_margin": 0.10,
    },
}

FLEETS = ("FleetServiceFirst", "FleetServiceGridWeighted")
GRIDS = ("NoGridIncentive", "GridPeakPenalty")
FLEET_LABEL = {"FleetServiceFirst": "ServiceFirst", "FleetServiceGridWeighted": "ServiceGridWeighted"}
GRID_LABEL = {"NoGridIncentive": "NoGrid", "GridPeakPenalty": "PeakPenalty"}

# Mutable selector consumed by the patched driver: the active incentive intensity.
ACTIVE_INCENTIVE = 0.0
DEV_ACC: list[float] = []          # realized mean deviation (audit)
INDUCED_ACC: list[float] = []      # realized induced-compliance mass M (audit)


def import_runner():
    spec = importlib.util.spec_from_file_location("mav2_equil", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {RUNNER}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mav2_equil"] = mod
    spec.loader.exec_module(mod)
    return mod


def pkeep_incentive(laxity: np.ndarray, c: float) -> tuple[np.ndarray, float, float]:
    """Calibrated per-vehicle keep probability under incentive intensity c.

    Returns (p_keep, realized_mean_dev, induced_mass M). See module docstring.
    """
    lax = np.clip(np.asarray(laxity, dtype=float), 0.0, 1.0)
    n = lax.shape[0]
    if n == 0:
        return np.zeros(0, dtype=float), 0.0, 0.0
    w = 1.0 - lax                                  # inflexibility weight
    mean_w = float(w.mean())
    if mean_w <= 1.0e-9:
        p_dev0 = np.full(n, TARGET_DEV_RATE, dtype=float)
    else:
        p_dev0 = np.clip((TARGET_DEV_RATE / mean_w) * w, 0.0, 1.0)
    eff = np.clip(c * (0.5 + 0.5 * w), 0.0, 1.0)   # incentive efficacy, low-slack-weighted
    p_dev = np.clip(p_dev0 * (1.0 - eff), 0.0, 1.0)
    p_keep = 1.0 - p_dev
    return p_keep, float(p_dev.mean()), float((p_dev0 - p_dev).mean())


def install_direct_extensions(mav2) -> None:
    """Proven Option-A engine path; the ONLY change is that the driver keep
    probability comes from the incentive-responsive calibration pkeep_incentive."""
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
        cfg = SEVERITY[driver]
        values = pkg._arrays(env, obs)
        critical = pkg._service_critical(values)
        available = values["masks"][:, pkg.PRIMITIVE_NORMAL_REQUEST]
        cheap_now = bool(is_cheap[int(env.t) % len(is_cheap)])
        reserve_threshold = values["theta"] + float(cfg["reserve_margin"])
        if cheap_now:
            reserve_threshold = reserve_threshold + float(cfg["cheap_extra_margin"])
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
        if driver not in SEVERITY:
            return original_driver(env, obs, rec_actions, driver, rng, is_cheap)
        cfg = SEVERITY[driver]
        if float(cfg["keep_probability"]) >= 0.999:
            p = np.full(env.n_cars, float(cfg["keep_probability"]), dtype=float)
            return rec_actions.astype(np.int64), p, np.zeros(env.n_cars, dtype=bool), 0
        values = pkg._arrays(env, obs)
        laxity = np.asarray(values["laxity"], dtype=float)
        keep_prob, mean_dev, induced = pkeep_incentive(laxity, ACTIVE_INCENTIVE)
        if keep_prob.shape[0] > 0:
            DEV_ACC.append(mean_dev)
            INDUCED_ACC.append(induced)
        p_dev = 1.0 - keep_prob
        pref = severity_preference(env, obs, driver, rng, is_cheap)
        keep = rng.random(env.n_cars) >= p_dev
        actual = np.where(keep, rec_actions, pref).astype(np.int64)
        noncompliant = ~keep
        return actual, keep_prob, noncompliant, 0

    mav2.fleet_recommendation = direct_fleet
    mav2.apply_driver_layer = direct_driver

    new_specs: list[Any] = []
    for driver, cfg in SEVERITY.items():
        for fleet in FLEETS:
            for grid in GRIDS:
                name = f"D_{driver}__F_{FLEET_LABEL[fleet]}__G_{GRID_LABEL[grid]}"
                desc = f"Equilibrium severity {cfg['level']} ({cfg['label']}) {fleet} {grid}."
                new_specs.append(mav2.MultiActorPolicy(name, driver, fleet, grid, desc))
    existing = {p.name for p in mav2.POLICIES}
    for spec in new_specs:
        if spec.name not in existing:
            mav2.POLICIES.append(spec)
    mav2.POLICY_BY_NAME = {p.name: p for p in mav2.POLICIES}


def policy_list(mav2, drivers: list[str]) -> list[str]:
    names = ["LeastLaxity"]
    for driver in drivers:
        for fleet in FLEETS:
            for grid in GRIDS:
                names.append(f"D_{driver}__F_{FLEET_LABEL[fleet]}__G_{GRID_LABEL[grid]}")
    missing = [n for n in names if n != "LeastLaxity" and n not in mav2.POLICY_BY_NAME]
    if missing:
        raise RuntimeError(f"Missing policies: {missing}")
    return names


def run_setting(mav2, incentive: float, drivers: list[str], caps: list[int]) -> pd.DataFrame:
    global ACTIVE_INCENTIVE
    ACTIVE_INCENTIVE = incentive
    mav2.pkg.policy_actions = mav2._ORIG_POLICY_ACTIONS
    install_direct_extensions(mav2)
    policies = policy_list(mav2, drivers)
    aggregate = mav2.run_matrix(SEEDS, caps, policies)
    scored = mav2.add_actor_scoring(aggregate["rows"])
    rows = pd.DataFrame(scored)
    rows = rows[rows["policy"] != "LeastLaxity"].copy()
    rows["incentive"] = incentive
    rows["severity_level"] = rows["driver_behavior"].map(
        lambda x: SEVERITY.get(str(x), {}).get("level", pd.NA)
    )
    return rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    mav2 = import_runner()
    mav2.set_output_dir(OUT / "runner_raw")
    mav2.pkg.EPISODE_HOURS = EPISODE_HOURS
    mav2._ORIG_FLEET = mav2.fleet_recommendation
    mav2._ORIG_DRIVER = mav2.apply_driver_layer
    mav2._ORIG_POLICY_ACTIONS = mav2.pkg.policy_actions

    start = time.time()
    all_rows: list[pd.DataFrame] = []

    # Severity 0 (full compliance) reference: incentive-independent, run once.
    DEV_ACC.clear(); INDUCED_ACC.clear()
    sev0 = run_setting(mav2, 0.0, ["Severity0Full"], CAPACITIES)
    sev0["incentive"] = pd.NA
    all_rows.append(sev0)
    print(f"[sev0 reference] rows={len(sev0)} t={time.time()-start:.0f}s", flush=True)

    # Severity 1 under each incentive intensity.
    for c in INCENTIVES:
        DEV_ACC.clear(); INDUCED_ACC.clear()
        rows = run_setting(mav2, c, ["Severity1Mild"], CAPACITIES)
        realized_dev = float(np.mean(DEV_ACC)) if DEV_ACC else float("nan")
        realized_M = float(np.mean(INDUCED_ACC)) if INDUCED_ACC else float("nan")
        rows["realized_mean_dev"] = realized_dev
        rows["realized_induced_mass"] = realized_M
        all_rows.append(rows)
        print(f"[incentive c={c:.2f}] rows={len(rows)} realized_dev={realized_dev:.4f} "
              f"induced_M={realized_M:.4f} t={time.time()-start:.0f}s", flush=True)

    df = pd.concat(all_rows, ignore_index=True)
    raw_path = OUT / f"equilibrium_rows_{DATE}.csv"
    df.to_csv(raw_path, index=False)

    # --- Summary: all-pass by (incentive, capacity, grid) for service family ---
    serv = df[df["fleet_policy"].isin(FLEETS)].copy()
    sev1 = serv[serv["severity_level"] == 1].copy()
    sev0s = serv[serv["severity_level"] == 0].copy()

    def grid_of(p):
        return "PeakPenalty" if "PeakPenalty" in str(p) else "NoGrid"
    sev1["grid"] = sev1["policy"].map(grid_of)
    sev0s["grid"] = sev0s["policy"].map(grid_of)

    summ = (sev1.groupby(["incentive", "capacity_pct", "grid"])
                 .agg(all_pass=("all_pass", "mean"),
                      driver_pass=("driver_pass", "mean") if "driver_pass" in sev1.columns else ("all_pass", "mean"),
                      n=("all_pass", "size"),
                      realized_dev=("realized_mean_dev", "mean"),
                      induced_M=("realized_induced_mass", "mean"))
                 .reset_index())
    summ["budget_proxy"] = summ["incentive"] * summ["induced_M"]
    summ = summ.sort_values(["capacity_pct", "grid", "incentive"])
    summ.to_csv(OUT / f"equilibrium_summary_{DATE}.csv", index=False)

    ref = (sev0s.groupby(["capacity_pct", "grid"]).agg(all_pass=("all_pass", "mean")).reset_index())

    pd.set_option("display.width", 200)
    print("\n=== Severity-0 reference all-pass (full compliance) ===")
    print(ref.round(3).to_string(index=False))
    print("\n=== Severity-1 all-pass by incentive intensity / capacity / grid ===")
    print(summ.round(3).to_string(index=False))

    # Minimal-incentive equilibrium per (capacity, grid): smallest c with all_pass>=0.5
    print("\n=== Minimal-incentive equilibrium (all_pass>=0.5) ===")
    for (cap, grid), g in summ.groupby(["capacity_pct", "grid"]):
        ok = g[g["all_pass"] >= 0.5].sort_values("incentive")
        if len(ok):
            r = ok.iloc[0]
            print(f"cap={cap}% grid={grid}: c*={r['incentive']:.2f} "
                  f"all_pass={r['all_pass']:.3f} budget={r['budget_proxy']:.4f}")
        else:
            best = g.sort_values("all_pass").iloc[-1]
            print(f"cap={cap}% grid={grid}: NO c restores all-pass>=0.5 "
                  f"(best={best['all_pass']:.3f} at c={best['incentive']:.2f}) "
                  f"-> grid-limited; needs grid lever")
    print(f"\nTotal wall time: {time.time()-start:.0f}s")
    print(f"Saved: {raw_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
