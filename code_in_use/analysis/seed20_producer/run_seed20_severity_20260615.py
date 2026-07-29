#!/usr/bin/env python3
"""20-seed expansion of the weekly EV-charging behavioral-severity sweep.

Reviewer asked to move from 5 seeds to 20. NO new modeling: this imports the
SAME engine (`run_multi_actor_v2_experiment.py`, referenced as `mav2`, with
`pkg = mav2.pkg`) and reuses the SAME direct multi-actor extensions
(install_direct_extensions) as the original 5-seed baseline runner
(`run_direct_wave2_severity_baseline_20260609.py`). Only the seed list grows.

Scope vs the original baseline runner:
  - SEEDS 4541..4560 (20 total; original 5 were 4541..4545).
  - CAPACITIES [20, 35, 50].
  - 4 severity levels (Severity0Full..Severity3Severe) -- unchanged config.
  - Fleet policies: FleetServiceFirst, FleetServiceGridWeighted (service family).
  - Grid policies: NoGridIncentive, GridPeakPenalty.
  - DROP the diagnostic CostOnly / QueueAware comparator policies (not needed).
  - Weekly horizon EPISODE_HOURS = 168.

run_matrix is called ONCE over all seeds/caps/policies (the simplest path; this
avoids the engine install_policies() re-wrap RecursionError that only bites when
run_matrix is called multiple times). We still snapshot the pristine
pkg.policy_actions and restore it before the single run, defensively.

Does NOT modify anything under the engine workspace; writes only into the
seed20 output directory.
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
OUT = Path("/home/jia/multi actor/seed20_expansion_20260615")
DATE = "20260615"

# 20 seeds: original 5 (4541-4545) + 15 new (4546-4560).
SEEDS = list(range(4541, 4561))
CAPACITIES = [20, 35, 50]
EPISODE_HOURS = 168

# Severity config: identical to the original 5-seed baseline runner.
SEVERITY: dict[str, dict[str, Any]] = {
    "Severity0Full": {
        "level": 0,
        "label": "full_compliance",
        "keep_probability": 1.00,
        "reserve_margin": 0.00,
        "cheap_extra_margin": 0.00,
    },
    "Severity1Mild": {
        "level": 1,
        "label": "mild_deviation",
        "keep_probability": 0.95,
        "reserve_margin": 0.05,
        "cheap_extra_margin": 0.10,
    },
    "Severity2Moderate": {
        "level": 2,
        "label": "moderate_deviation",
        "keep_probability": 0.80,
        "reserve_margin": 0.15,
        "cheap_extra_margin": 0.30,
    },
    "Severity3Severe": {
        "level": 3,
        "label": "severe_deviation",
        "keep_probability": 0.55,
        "reserve_margin": 0.25,
        "cheap_extra_margin": 0.60,
    },
}

FLEETS = ("FleetServiceFirst", "FleetServiceGridWeighted")
GRIDS = ("NoGridIncentive", "GridPeakPenalty")
FLEET_LABEL = {"FleetServiceFirst": "ServiceFirst", "FleetServiceGridWeighted": "ServiceGridWeighted"}
GRID_LABEL = {"NoGridIncentive": "NoGrid", "GridPeakPenalty": "PeakPenalty"}


def import_runner():
    spec = importlib.util.spec_from_file_location("mav2_seed20", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {RUNNER}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mav2_seed20"] = mod
    spec.loader.exec_module(mod)
    return mod


def install_direct_extensions(mav2) -> None:
    """Identical to install_direct_extensions() in the original baseline runner,
    restricted to the service-family fleets and the two grid policies. The
    severity driver layer and ServiceGridWeighted scoring are byte-for-byte the
    same logic; this is the reviewer's 'same engine, same policies' requirement.
    """
    pkg = mav2.pkg
    original_fleet = mav2.fleet_recommendation
    original_driver = mav2.apply_driver_layer

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
        p = np.full(env.n_cars, float(cfg["keep_probability"]), dtype=float)
        if float(cfg["keep_probability"]) >= 0.999:
            return rec_actions.astype(np.int64), p, np.zeros(env.n_cars, dtype=bool), 0
        pref = severity_preference(env, obs, driver, rng, is_cheap)
        keep = rng.random(env.n_cars) < p
        actual = np.where(keep, rec_actions, pref).astype(np.int64)
        noncompliant = ~keep
        return actual, p, noncompliant, 0

    mav2.fleet_recommendation = direct_fleet
    mav2.apply_driver_layer = direct_driver

    new_specs: list[Any] = []
    for driver, cfg in SEVERITY.items():
        for fleet in FLEETS:
            for grid in GRIDS:
                name = f"D_{driver}__F_{FLEET_LABEL[fleet]}__G_{GRID_LABEL[grid]}"
                desc = (
                    f"Seed20 multi-actor severity level {cfg['level']} ({cfg['label']}) with "
                    f"{fleet} and {grid}; keep_probability={cfg['keep_probability']}."
                )
                new_specs.append(mav2.MultiActorPolicy(name, driver, fleet, grid, desc))
    existing = {p.name for p in mav2.POLICIES}
    for spec in new_specs:
        if spec.name not in existing:
            mav2.POLICIES.append(spec)
    mav2.POLICY_BY_NAME = {p.name: p for p in mav2.POLICIES}


def policy_list(mav2) -> list[str]:
    names = ["LeastLaxity"]  # anchor needed for actor scoring / delta computation
    for driver in SEVERITY:
        for fleet in FLEETS:
            for grid in GRIDS:
                names.append(f"D_{driver}__F_{FLEET_LABEL[fleet]}__G_{GRID_LABEL[grid]}")
    missing = [n for n in names if n != "LeastLaxity" and n not in mav2.POLICY_BY_NAME]
    if missing:
        raise RuntimeError(f"Missing policies: {missing}")
    return names


def add_direct_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["severity_level"] = out["driver_behavior"].map(lambda x: SEVERITY.get(str(x), {}).get("level", pd.NA))
    out["severity_label"] = out["driver_behavior"].map(lambda x: SEVERITY.get(str(x), {}).get("label", "comparator"))
    out["service_family_decision"] = out["fleet_policy"].map(
        lambda x: "ServiceFirst/Balanced merged family" if str(x) == "FleetServiceFirst" else ("strong service-grid baseline" if str(x) == "FleetServiceGridWeighted" else "comparator")
    )
    out["actual_to_fleet_request_ratio"] = out["actual_request_count_driver_layer"] / out["fleet_recommended_request_count"].replace(0, pd.NA)
    return out


def summarize(rows: pd.DataFrame) -> pd.DataFrame:
    """Grouped by (severity_level, capacity_pct): pass rates over the explicit
    multi-actor policy rows (drop the LeastLaxity anchor), plus the seed-level
    std of all_pass (per-seed all-pass means first, then std across the 20 seeds).
    """
    direct = rows[rows["severity_level"].notna()].copy()
    direct["all_pass"] = direct["all_pass"].astype(float)

    records: list[dict[str, Any]] = []
    for (sev, cap), grp in direct.groupby(["severity_level", "capacity_pct"], dropna=False):
        per_seed = grp.groupby("seed")["all_pass"].mean()
        records.append({
            "severity_level": int(sev),
            "severity_label": SEVERITY_BY_LEVEL[int(sev)],
            "capacity_pct": int(cap),
            "n_episodes": int(len(grp)),
            "n_seeds": int(per_seed.size),
            "driver_pass_rate": float(grp["driver_service_pass"].mean()),
            "fleet_pass_rate": float(grp["fleet_operation_pass"].mean()),
            "grid_pass_rate": float(grp["grid_pass"].mean()),
            "all_pass_rate": float(grp["all_pass"].mean()),
            "all_pass_seed_std": float(per_seed.std(ddof=1)) if per_seed.size > 1 else float("nan"),
            "all_pass_seed_min": float(per_seed.min()),
            "all_pass_seed_max": float(per_seed.max()),
        })
    return pd.DataFrame(records).sort_values(["severity_level", "capacity_pct"]).reset_index(drop=True)


SEVERITY_BY_LEVEL = {cfg["level"]: cfg["label"] for cfg in SEVERITY.values()}


def write_report(summary: pd.DataFrame, rows: pd.DataFrame, elapsed: float, command: str) -> None:
    direct = rows[rows["severity_level"].notna()].copy()
    direct["all_pass"] = direct["all_pass"].astype(float)
    caps = CAPACITIES
    levels = sorted(summary["severity_level"].unique())

    # all_pass_rate pivot (severity rows x capacity cols)
    pivot = summary.pivot(index="severity_level", columns="capacity_pct", values="all_pass_rate")

    lines = [
        "# Seed-20 Behavioral-Severity Expansion Report",
        "",
        f"Date: {DATE}. Runtime: {elapsed:.1f}s ({elapsed/60.0:.1f} min).",
        "",
        f"Command: `{command}`",
        "",
        "Reviewer request: move the weekly behavioral-severity sweep from 5 seeds "
        "to 20 seeds. Same engine, same policies, same thresholds; only the seed "
        "list grows. No new modeling.",
        "",
        f"- Seeds (20): {SEEDS[0]}..{SEEDS[-1]} (original 5: 4541-4545; added 15: 4546-4560).",
        f"- Capacities: {CAPACITIES}.",
        "- Severity levels: 0 (full) / 1 (mild) / 2 (moderate) / 3 (severe).",
        f"- Fleet policies: {', '.join(FLEETS)}.",
        f"- Grid policies: {', '.join(GRIDS)}.",
        f"- Weekly horizon EPISODE_HOURS = {EPISODE_HOURS}.",
        f"- Explicit multi-actor episodes (excl. LeastLaxity anchor): {int(len(direct))}.",
        "",
        "## All-pass rate by severity x capacity (20 seeds)",
        "",
        "| severity | " + " | ".join(f"cap {c}%" for c in caps) + " |",
        "| --- | " + " | ".join("---:" for _ in caps) + " |",
    ]
    for lvl in levels:
        cells = " | ".join(f"{float(pivot.loc[lvl, c]):.3f}" for c in caps)
        lines.append(f"| {int(lvl)} `{SEVERITY_BY_LEVEL[int(lvl)]}` | {cells} |")

    lines += [
        "",
        "## Seed-level dispersion of all-pass (severity 0 and 1)",
        "",
        "Per-seed all-pass means computed first, then std/min/max across the 20 seeds, per capacity.",
        "",
        "| severity | capacity | all_pass_rate | seed std | seed min | seed max |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for lvl in (0, 1):
        for c in caps:
            r = summary[(summary["severity_level"] == lvl) & (summary["capacity_pct"] == c)].iloc[0]
            std = r["all_pass_seed_std"]
            std_s = "n/a" if not math.isfinite(std) else f"{std:.3f}"
            lines.append(
                f"| {lvl} `{SEVERITY_BY_LEVEL[lvl]}` | {c}% | {r['all_pass_rate']:.3f} | "
                f"{std_s} | {r['all_pass_seed_min']:.3f} | {r['all_pass_seed_max']:.3f} |"
            )

    # VERDICT: headline pattern = all-pass ~1.0 at severity 0, ~0.0 at severity 1,
    # across all three capacities.
    sev0 = summary[summary["severity_level"] == 0]
    sev1 = summary[summary["severity_level"] == 1]
    sev0_ok = bool((sev0["all_pass_rate"] >= 0.999).all())
    sev1_ok = bool((sev1["all_pass_rate"] <= 0.001).all())
    if sev0_ok and sev1_ok:
        verdict = (
            "VERDICT: HOLDS. At 20 seeds the headline pattern is confirmed across all three "
            "capacities (20/35/50%): same-episode all-pass = 1.000 at severity 0 (full compliance) "
            "and 0.000 at severity 1 (mild deviation)."
        )
    else:
        sev0_str = ", ".join(f"{int(r.capacity_pct)}%={r.all_pass_rate:.3f}" for r in sev0.itertuples())
        sev1_str = ", ".join(f"{int(r.capacity_pct)}%={r.all_pass_rate:.3f}" for r in sev1.itertuples())
        verdict = (
            "VERDICT: PARTIAL / DOES NOT cleanly hold at all capacities. "
            f"Severity-0 all-pass by capacity: {sev0_str}. Severity-1 all-pass by capacity: {sev1_str}. "
            "See table above for the exact rates."
        )

    lines += ["", "## " + verdict, ""]
    (OUT / f"SEED20_REPORT_{DATE}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return verdict


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    mav2 = import_runner()
    mav2.set_output_dir(OUT / "runner_raw")
    mav2.pkg.EPISODE_HOURS = EPISODE_HOURS

    # Defensive: snapshot the pristine engine policy dispatcher before any
    # install_policies() wrapping, and restore it before the single run_matrix
    # call. (We only call run_matrix once, so the RecursionError the ablation
    # runner guards against cannot arise here; this is belt-and-suspenders.)
    pristine_policy_actions = mav2.pkg.policy_actions

    install_direct_extensions(mav2)
    policies = policy_list(mav2)

    command = (
        'python3 "/home/jia/multi actor/seed20_expansion_20260615/'
        'run_seed20_severity_20260615.py"'
    )
    start = time.time()
    print(f"seed20: seeds={SEEDS} capacities={CAPACITIES} policies={len(policies)}", flush=True)

    mav2.pkg.policy_actions = pristine_policy_actions
    aggregate = mav2.run_matrix(SEEDS, CAPACITIES, policies)
    scored = mav2.add_actor_scoring(aggregate["rows"])
    rows = add_direct_columns(pd.DataFrame(scored))

    rows_path = OUT / f"seed20_row_results_{DATE}.csv"
    rows.to_csv(rows_path, index=False)

    summary = summarize(rows)
    summary_path = OUT / f"seed20_summary_{DATE}.csv"
    summary.to_csv(summary_path, index=False)

    elapsed = time.time() - start
    verdict = write_report(summary, rows, elapsed, command)

    explicit = int((rows["policy"] != "LeastLaxity").sum())
    n_seeds = rows["seed"].nunique()
    print(f"seed20 complete: rows={len(rows)} explicit={explicit} seeds={n_seeds} "
          f"runtime={elapsed:.1f}s out={OUT}", flush=True)
    print(verdict, flush=True)
    print(summary.to_string(index=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
