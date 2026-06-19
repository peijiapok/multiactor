#!/usr/bin/env python3
"""Build final Applied Energy figure set from saved CSV evidence.

The figures deliberately avoid decorative elements and avoid unsupported causal
labels. Every panel maps to saved evidence generated in Wave 1, Wave 2, or the
targeted 28-day confirmation.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, Rectangle


ROOT = Path("/home/jia/multi actor")
FINAL = ROOT / "final_applied_energy_package_20260609"
FIG_DIR = FINAL / "figures"

WAVE1 = ROOT / "wave1_evidence_20260609"
WAVE2 = ROOT / "wave2_direct_severity_baseline_20260609"
WAVE2_GRID = ROOT / "wave2_strong_upgrades_20260609"
STRENGTH = ROOT / "research_strengthening_20260609"
ROBUST = ROOT / "robustness_analysis_20260614"
SEED20 = ROOT / "seed20_expansion_20260615"


def ensure_dirs() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)


def savefig(name: str) -> list[str]:
    paths = []
    for ext in ("png", "pdf"):
        out = FIG_DIR / f"{name}.{ext}"
        plt.savefig(out, dpi=300 if ext == "png" else None, bbox_inches="tight")
        paths.append(str(out))
    plt.close()
    return paths


def clean_policy(policy: str) -> str:
    if pd.isna(policy):
        return ""
    s = str(policy)
    replacements = {
        "FleetServiceGridWeighted": "ServiceGridWeighted",
        "FleetServiceFirst": "ServiceFirst",
        "FleetQueueAware": "QueueAware",
        "FleetCostOnly": "CostOnly",
        "GridPeakPenalty": "PeakPenalty",
        "NoGridIncentive": "NoGrid",
        "D_FullyCompliant__F_": "",
        "__G_": " ",
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    s = s.replace("ServiceFirst", "ServiceFirst")
    return s


def fig1_framework() -> list[str]:
    fig, ax = plt.subplots(figsize=(11.5, 5.8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")

    box_style = dict(facecolor="#f7f7f7", edgecolor="#222222", linewidth=1.2)
    gate_style = dict(facecolor="#eef5ff", edgecolor="#1f4e79", linewidth=1.1)
    fail_style = dict(facecolor="#fff4e6", edgecolor="#8a5a00", linewidth=1.1)

    boxes = [
        (0.4, 3.8, 2.1, 1.1, "Driver behavior\nrequests, compliance,\nresponse events", box_style),
        (3.0, 3.8, 2.1, 1.1, "Fleet policy\nservice, queue,\nweighted heuristic", box_style),
        (5.6, 3.8, 2.1, 1.1, "Grid policy\nNoGrid or\nPeakPenalty", box_style),
        (8.2, 3.8, 2.1, 1.1, "Capacity-limited\ncharging service\nfinal actions", box_style),
        (1.0, 1.3, 1.9, 0.85, "Driver gate\nservice + reliability", gate_style),
        (4.0, 1.3, 1.9, 0.85, "Fleet gate\ncompletion + cost", gate_style),
        (7.0, 1.3, 1.9, 0.85, "Grid gate\npeak + ramp + load", gate_style),
        (9.8, 1.2, 1.6, 1.05, "All-pass\nlogical AND", fail_style),
    ]

    for x, y, w, h, text, style in boxes:
        ax.add_patch(Rectangle((x, y), w, h, **style))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9.5)

    arrow_pairs = [
        ((2.5, 4.35), (3.0, 4.35)),
        ((5.1, 4.35), (5.6, 4.35)),
        ((7.7, 4.35), (8.2, 4.35)),
        ((9.25, 3.8), (1.95, 2.15)),
        ((9.25, 3.8), (4.95, 2.15)),
        ((9.25, 3.8), (7.95, 2.15)),
        ((2.9, 1.72), (4.0, 1.72)),
        ((5.9, 1.72), (7.0, 1.72)),
        ((8.9, 1.72), (9.8, 1.72)),
    ]
    for start, end in arrow_pairs:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12, linewidth=1.0, color="#333333"))

    ax.text(6.0, 5.45, "Multi-actor EV charging acceptability framework", ha="center", fontsize=14, weight="bold")
    ax.text(
        6.0,
        0.45,
        "Evaluation asks whether driver, fleet, and grid gates pass simultaneously, not whether one metric improves.",
        ha="center",
        fontsize=9.5,
    )
    return savefig("fig1_multi_actor_framework")


def fig2_actor_gate_matrix() -> list[str]:
    """Main result figure: the single most important finding is that the
    conjunction (all-pass) gate collapses one severity step before the
    individual gates do. Panel A condenses the service-oriented family to a
    severity x actor-gate heatmap; Panel B shows the all-pass collapse is the
    same for both service-oriented fleet policies. The full
    policy x behavior x grid matrix is moved to the supplement
    (supp_full_actor_gate_matrix).
    """
    df = pd.read_csv(SEED20 / "seed20_actor_gate_matrix_20260615.csv")
    svc = df[df["fleet_policy"].isin(["FleetServiceFirst", "FleetServiceGridWeighted"])].copy()
    svc = svc[svc["severity_level"].isin([0, 1, 2, 3])]

    # Panel A data: service family averaged over both fleet policies, both grid
    # policies, and all capacities -> severity x {driver, fleet, grid, all}.
    gate_cols = ["driver_pass_rate", "fleet_pass_rate", "grid_pass_rate", "all_pass_rate"]
    agg = svc.groupby("severity_level")[gate_cols].mean().sort_index()
    mat = agg.to_numpy()
    sev_labels = ["S0\nfull\ncompliance", "S1\nmild\ndeviation", "S2\nmoderate", "S3\nsevere"]
    col_labels = ["Driver\ngate", "Fleet\ngate", "Grid\ngate", "All-pass\n(D∧F∧G)"]

    # Panel B data: all-pass vs severity, per service fleet policy.
    byfleet = (
        svc.groupby(["fleet_policy", "severity_level"])["all_pass_rate"].mean().unstack()
    )

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.0, 4.6), gridspec_kw={"width_ratios": [1.25, 1.0]})

    # ---- Panel A: condensed heatmap ----
    im = axA.imshow(mat, vmin=0, vmax=1, cmap="viridis", aspect="auto")
    axA.set_xticks(range(4), labels=col_labels, fontsize=9)
    axA.set_yticks(range(4), labels=sev_labels, fontsize=9)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            axA.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center",
                     fontsize=11, weight="bold",
                     color="white" if mat[i, j] < 0.55 else "black")
    # Highlight the all-pass column (the headline metric).
    axA.add_patch(Rectangle((3 - 0.5, -0.5), 1, 4, fill=False, edgecolor="#d62728", lw=2.5))
    axA.set_title("(A) Actor-gate pass rate vs behavior severity\n(service-oriented family, all capacities and grid policies)",
                  fontsize=10.5, weight="bold")
    cbar = fig.colorbar(im, ax=axA, fraction=0.046, pad=0.03)
    cbar.set_label("Pass rate")

    # ---- Panel B: all-pass collapse, per fleet policy ----
    sev = sorted(svc["severity_level"].unique())
    for fleet, color, marker in (("FleetServiceFirst", "#1f77b4", "o"),
                                 ("FleetServiceGridWeighted", "#ff7f0e", "s")):
        if fleet in byfleet.index:
            axB.plot(sev, byfleet.loc[fleet, sev].to_numpy(), marker=marker,
                     color=color, lw=2, markersize=8, label=clean_policy(fleet))
    axB.set_xticks(sev)
    axB.set_xlabel("Behavior severity")
    axB.set_ylabel("All-pass acceptability rate")
    axB.set_ylim(-0.05, 1.08)
    axB.set_title("(B) Same-episode all-pass collapses at severity 1", fontsize=10.5, weight="bold")
    axB.grid(True, alpha=0.3)
    axB.legend(loc="upper right", fontsize=9)
    axB.annotate("All-pass ≈ 1% at severity 1\n(driver/fleet/grid gates 0.05/0.19/0.32)",
                 xy=(1, 0.0), xytext=(1.35, 0.42), fontsize=8.5,
                 arrowprops=dict(arrowstyle="->", color="#d62728", lw=1.5),
                 color="#d62728")
    axB.annotate("97% under full\ncompliance (20 seeds)", xy=(0, 0.967), xytext=(0.05, 0.74),
                 fontsize=8.5, color="#333333")

    fig.suptitle("Multi-actor acceptability collapses one severity step before the individual gates do",
                 fontsize=12, weight="bold", y=1.02)
    fig.tight_layout()
    return savefig("fig2_actor_gate_acceptability_matrix")


def fig_robustness_acceptability() -> list[str]:
    """Robustness of the acceptability definition. Panel A: which sub-criteria
    bind at severity 1 (broad-based vs single-gate). Panel B: all-pass-style rate
    under alternative aggregation logics + the graded fraction-of-criteria index,
    showing the collapse is not purely an artifact of the strict 14-way AND."""
    q1 = pd.read_csv(ROBUST / "q1_subcriterion_decomposition_20260614.csv")
    q2 = pd.read_csv(ROBUST / "q2_alternative_aggregation_20260614.csv")

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.5, 4.8), gridspec_kw={"width_ratios": [1.15, 1.0]})

    # Panel A: sub-criterion fail fraction at severity 1, sorted.
    q1s = q1.sort_values("fail_frac_sev1", ascending=True)
    q1s = q1s[q1s["fail_frac_sev1"] > 0.001]
    colors = {"D": "#1f77b4", "F": "#2ca02c", "G": "#d62728"}
    bar_colors = [colors[c[0]] for c in q1s["criterion"]]
    axA.barh(q1s["criterion"], q1s["fail_frac_sev1"], color=bar_colors)
    axA.set_xlabel("Fraction of episodes failing the criterion at severity 1")
    axA.set_xlim(0, 1)
    axA.set_title("(A) The collapse is broad-based across actors\n(driver=blue, fleet=green, grid=red)", fontsize=10.5, weight="bold")
    for y, v in enumerate(q1s["fail_frac_sev1"]):
        axA.text(v + 0.01, y, f"{v:.2f}", va="center", fontsize=8)

    # Panel B: aggregation logics vs severity.
    sev = q2["severity"].to_numpy()
    series = [
        ("strict_AND_3actor", "Strict all-pass (3-actor AND)", "#d62728", "o", "-"),
        ("at_least_2of3_actors", "≥2 of 3 actors pass", "#ff7f0e", "s", "-"),
        ("at_least_1of3_actors", "≥1 of 3 actors pass", "#1f77b4", "^", "-"),
        ("mean_frac_of_14_passed", "Mean fraction of 14 criteria passed", "#2ca02c", "D", "--"),
    ]
    for col, label, color, marker, ls in series:
        axB.plot(sev, q2[col].to_numpy(), marker=marker, color=color, ls=ls, lw=2, markersize=7, label=label)
    axB.set_xticks(sev)
    axB.set_xlabel("Behavior severity")
    axB.set_ylabel("Rate / fraction")
    axB.set_ylim(-0.05, 1.08)
    axB.set_title("(B) Degradation survives softer aggregation\n(graded index avoids a binary cliff)", fontsize=10.5, weight="bold")
    axB.grid(True, alpha=0.3)
    axB.legend(loc="lower left", fontsize=8)
    axB.annotate("79% of criteria still pass\nat severity 1, yet strict\nall-pass ≈ 0",
                 xy=(1, 0.793), xytext=(1.25, 0.30), fontsize=8, color="#2ca02c",
                 arrowprops=dict(arrowstyle="->", color="#2ca02c", lw=1.3))

    fig.suptitle("Robustness of the acceptability definition: multi-criterion degradation, not a single-threshold artifact",
                 fontsize=11.5, weight="bold", y=1.02)
    fig.tight_layout()
    return savefig("fig_robustness_acceptability")


def supp_full_actor_gate_matrix() -> list[str]:
    """Supplementary: the full policy x behavior x grid actor-gate matrix that
    previously served as main Figure 2. Retained for completeness; the main text
    now uses the condensed two-panel severity-collapse figure."""
    df = pd.read_csv(WAVE2 / "actor_gate_matrix_with_severity_and_baseline_20260609.csv")
    df = df.copy()
    df["severity_level"] = df["severity_level"].fillna(-1).astype(int)
    df = df[df["fleet_policy"].isin(["FleetCostOnly", "FleetQueueAware", "FleetServiceFirst", "FleetServiceGridWeighted"])]
    grouped = (
        df.groupby(["severity_level", "severity_label", "fleet_policy", "grid_policy"], as_index=False)[
            ["driver_pass_rate", "fleet_pass_rate", "grid_pass_rate", "all_pass_rate"]
        ]
        .mean()
        .sort_values(["severity_level", "fleet_policy", "grid_policy"])
    )
    row_labels = []
    values = []
    for _, r in grouped.iterrows():
        sev = "Comp." if r["severity_level"] == -1 else f"S{r['severity_level']}"
        row_labels.append(f"{sev} {clean_policy(r['fleet_policy'])} {clean_policy(r['grid_policy'])}")
        values.append([r["driver_pass_rate"], r["fleet_pass_rate"], r["grid_pass_rate"], r["all_pass_rate"]])
    mat = np.array(values)

    fig, ax = plt.subplots(figsize=(8.5, max(7.0, 0.28 * len(row_labels))))
    im = ax.imshow(mat, vmin=0, vmax=1, cmap="viridis", aspect="auto")
    ax.set_xticks(range(4), labels=["Driver", "Fleet", "Grid", "All"])
    ax.set_yticks(range(len(row_labels)), labels=row_labels, fontsize=7.6)
    ax.set_title("Full actor-gate pass rates by policy family and behavior severity (supplementary)", fontsize=11, weight="bold")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center", fontsize=6.5, color="white" if mat[i, j] < 0.55 else "black")
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Pass rate")
    ax.tick_params(axis="x", labelrotation=0)
    return savefig("supp_full_actor_gate_matrix")


def fig3_behavioral_severity_curve() -> list[str]:
    weekly = pd.read_csv(SEED20 / "seed20_behavior_severity_results_20260615.csv")
    target = pd.read_csv(FINAL / "targeted_28day_behavior_severity_results_20260609.csv")
    weekly_explicit = weekly[weekly["severity_level"].notna()].copy()
    target_explicit = target[target["severity_level"].notna()].copy()
    cols = ["driver_pass_rate", "fleet_pass_rate", "grid_pass_rate", "all_pass_rate", "actual_to_fleet_request_ratio_mean"]
    wg = weekly_explicit.groupby("severity_level", as_index=False)[cols].mean()
    tg = target_explicit.groupby("severity_level", as_index=False)[cols].mean()

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    ax = axes[0]
    colors = {"driver_pass_rate": "#1f77b4", "fleet_pass_rate": "#2ca02c", "grid_pass_rate": "#ff7f0e", "all_pass_rate": "#111111"}
    labels = {"driver_pass_rate": "Driver", "fleet_pass_rate": "Fleet", "grid_pass_rate": "Grid", "all_pass_rate": "All-pass"}
    for col in ["driver_pass_rate", "fleet_pass_rate", "grid_pass_rate", "all_pass_rate"]:
        ax.plot(wg["severity_level"], wg[col], marker="o", color=colors[col], label=f"Weekly {labels[col]}")
    ax.plot(tg["severity_level"], tg["all_pass_rate"], marker="s", color="#111111", linestyle="--", label="28-day all-pass")
    ax.set_ylim(-0.05, 1.05)
    ax.set_xticks([0, 1, 2, 3])
    ax.set_xlabel("Behavior severity")
    ax.set_ylabel("Pass rate")
    ax.set_title("Acceptability collapses at mild deviation under current gates")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8, ncol=2, loc="upper right")

    ax = axes[1]
    ax.plot(wg["severity_level"], wg["actual_to_fleet_request_ratio_mean"], marker="o", color="#7b3294", label="Weekly")
    ax.plot(tg["severity_level"], tg["actual_to_fleet_request_ratio_mean"], marker="s", color="#008837", linestyle="--", label="28-day")
    ax.set_xticks([0, 1, 2, 3])
    ax.set_xlabel("Behavior severity")
    ax.set_ylabel("Actual/fleet request-event ratio")
    ax.set_title("Request-event pressure rises with severity")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.suptitle("Behavioral severity evidence", fontsize=13, weight="bold", y=1.02)
    return savefig("fig3_behavioral_severity_curve")


def fig4_failure_taxonomy() -> list[str]:
    df = pd.read_csv(WAVE2 / "failure_pattern_taxonomy_with_severity_and_baseline_20260609.csv")
    df = df.copy()
    df["severity_level"] = df["severity_level"].fillna(-1).astype(int)
    filtered = df[df["severity_level"].isin([0, 1, 2, 3])]
    pivot = filtered.pivot_table(index="severity_level", columns="actor_failure_pattern", values="rows", aggfunc="sum", fill_value=0)
    preferred = ["all_pass", "driver_only_fail", "fleet_only_fail", "grid_only_fail", "driver_fleet_fail", "driver_grid_fail", "fleet_grid_fail", "driver_fleet_grid_fail"]
    cols = [c for c in preferred if c in pivot.columns] + [c for c in pivot.columns if c not in preferred]
    pivot = pivot[cols]
    colors = ["#4daf4a", "#377eb8", "#984ea3", "#ff7f00", "#a65628", "#f781bf", "#999999", "#e41a1c"][: len(cols)]

    fig, ax = plt.subplots(figsize=(10, 5.6))
    bottom = np.zeros(len(pivot.index))
    x = np.arange(len(pivot.index))
    for c, color in zip(cols, colors):
        vals = pivot[c].to_numpy()
        ax.bar(x, vals, bottom=bottom, label=c.replace("_", " "), color=color)
        bottom += vals
    ax.set_xticks(x, labels=[f"S{i}" for i in pivot.index])
    ax.set_xlabel("Behavior severity")
    ax.set_ylabel("Episode-policy rows")
    ax.set_title("Failure-pattern taxonomy under behavioral severity sweep", fontsize=12, weight="bold")
    ax.legend(fontsize=8, ncol=2, frameon=False)
    ax.grid(axis="y", alpha=0.25)
    return savefig("fig4_failure_pattern_taxonomy")


def fig5_grid_tradeoff() -> list[str]:
    weekly = pd.read_csv(WAVE2 / "actor_gate_matrix_with_severity_and_baseline_20260609.csv")
    target = pd.read_csv(FINAL / "targeted_28day_behavior_severity_results_20260609.csv")
    df = pd.concat([weekly.assign(horizon="weekly"), target.assign(horizon="28-day")], ignore_index=True)
    df = df[df["severity_level"].notna()].copy()
    df["severity_level"] = df["severity_level"].astype(int)
    grouped = df.groupby(["horizon", "severity_level", "grid_policy"], as_index=False)[["peak_ratio_mean", "all_pass_rate", "grid_deferred_mean"]].mean()

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharex=True)
    style = {
        ("weekly", "NoGridIncentive"): ("#1f77b4", "-"),
        ("weekly", "GridPeakPenalty"): ("#d62728", "-"),
        ("28-day", "NoGridIncentive"): ("#1f77b4", "--"),
        ("28-day", "GridPeakPenalty"): ("#d62728", "--"),
    }
    for (horizon, grid), sub in grouped.groupby(["horizon", "grid_policy"]):
        color, ls = style[(horizon, grid)]
        label = f"{horizon} {clean_policy(grid)}"
        axes[0].plot(sub["severity_level"], sub["peak_ratio_mean"], marker="o", color=color, linestyle=ls, label=label)
        axes[1].plot(sub["severity_level"], sub["all_pass_rate"], marker="o", color=color, linestyle=ls, label=label)
    axes[0].set_ylabel("Peak ratio")
    axes[0].set_title("PeakPenalty lowers peak ratio in several groups")
    axes[1].set_ylabel("All-pass rate")
    axes[1].set_title("Peak reduction does not rescue all-pass after deviation")
    for ax in axes:
        ax.set_xticks([0, 1, 2, 3])
        ax.set_xlabel("Behavior severity")
        ax.grid(True, alpha=0.25)
    axes[1].legend(fontsize=8, frameon=False)
    fig.suptitle("Grid-policy trade-off", fontsize=13, weight="bold", y=1.02)
    return savefig("fig5_grid_policy_tradeoff")


def parse_policy_family(policy: str) -> str:
    s = str(policy)
    if s == "LeastLaxity":
        return "LeastLaxity"
    if "ServiceFirst" in s:
        return "ServiceFirst"
    if "FleetBalanced" in s:
        return "FleetBalanced"
    if "CostOnly" in s:
        return "CostOnly"
    if "QueueAware" in s:
        return "QueueAware"
    if "PriceSensitive" in s:
        return "Behavior stress"
    if "SoCCompliance" in s:
        return "Behavior stress"
    if "LimitedAttention" in s:
        return "Behavior stress"
    return "Other"


def fig6_ieee33_feeder_deltas() -> list[str]:
    df = pd.read_csv(WAVE2_GRID / "ieee33_ev_policy_deltas_vs_ev_off_20260609.csv")
    df = df.copy()
    df["policy_family"] = df["policy"].map(parse_policy_family)
    keep = ["LeastLaxity", "ServiceFirst", "CostOnly", "QueueAware", "FleetBalanced"]
    df = df[df["policy_family"].isin(keep)]
    grouped = (
        df.groupby(["policy_family", "placement"], as_index=False)[
            [
                "substation_peak_kw_delta_vs_ev_off",
                "max_line_loading_pct_delta_vs_ev_off",
                "total_losses_kwh_delta_vs_ev_off",
            ]
        ]
        .mean()
        .sort_values(["policy_family", "placement"])
    )
    families = keep
    placements = ["concentrated_bus_18", "distributed_18_22_25_30_33"]
    metrics = [
        ("substation_peak_kw_delta_vs_ev_off", "Substation peak delta (kW)"),
        ("max_line_loading_pct_delta_vs_ev_off", "Max line loading delta (pct. points)"),
        ("total_losses_kwh_delta_vs_ev_off", "Losses delta (kWh/week)"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    x = np.arange(len(families))
    width = 0.36
    colors = {"concentrated_bus_18": "#b2182b", "distributed_18_22_25_30_33": "#2166ac"}
    labels = {"concentrated_bus_18": "Concentrated", "distributed_18_22_25_30_33": "Distributed"}
    for ax, (metric, ylabel) in zip(axes, metrics):
        for offset, placement in [(-width / 2, placements[0]), (width / 2, placements[1])]:
            vals = []
            for fam in families:
                m = grouped[(grouped["policy_family"] == fam) & (grouped["placement"] == placement)]
                vals.append(float(m[metric].mean()) if not m.empty else np.nan)
            ax.bar(x + offset, vals, width=width, label=labels[placement], color=colors[placement])
        ax.set_xticks(x, labels=families, rotation=30, ha="right")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.25)
    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle("IEEE-33 representative feeder stress deltas versus EV-off baseline", fontsize=13, weight="bold", y=1.02)
    return savefig("fig6_ieee33_feeder_deltas")


def supp_fleetbalanced_equivalence() -> list[str]:
    trace = pd.read_csv(WAVE1 / "fleetbalanced_branch_trace_20260609.csv")
    summary = {
        "Trace rows": len(trace),
        "Action-changed rows": int((trace["fleetbalanced_action_changed_count"] > 0).sum()),
        "Max action L1 distance": float(trace["action_l1_from_servicefirst"].max()),
    }
    fig, ax = plt.subplots(figsize=(6.8, 4.5))
    keys = list(summary.keys())
    vals = list(summary.values())
    ax.bar(keys, vals, color=["#4daf4a", "#377eb8", "#984ea3"])
    for i, v in enumerate(vals):
        ax.text(i, v + max(vals) * 0.02 if max(vals) else 0.02, f"{v:g}", ha="center", fontsize=10)
    ax.set_title("FleetBalanced branch/equivalence audit", fontsize=12, weight="bold")
    ax.set_ylabel("Count or distance")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(axis="y", alpha=0.25)
    return savefig("supp_fleetbalanced_equivalence_audit")


def supp_request_conservation() -> list[str]:
    df = pd.read_csv(WAVE1 / "request_conservation_by_behavior_20260609.csv")
    df = df.copy()
    df["label"] = df["behavior_model"].astype(str) + "\n" + df["grid_policy"].astype(str).map(clean_policy)
    # Single informative panel: the actual/fleet request-event ratio by behavior and grid
    # policy. The count-conservation residual is exactly zero in every case, so it is reported
    # in the caption rather than plotted as an empty panel.
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    ax.bar(np.arange(len(df)), df["actual_to_fleet_ratio"], color="#7b3294")
    ax.set_xticks(np.arange(len(df)), labels=df["label"], rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("Actual/fleet request-event ratio")
    ax.set_title("Behavior-specific request-event ratios", fontsize=12, weight="bold")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    return savefig("supp_request_id_conservation_audit")


def supp_threshold_sensitivity() -> list[str]:
    p = STRENGTH / "binding_threshold_sensitivity_overall_20260609.csv"
    if not p.exists():
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.axis("off")
        ax.text(0.5, 0.5, "Threshold sensitivity source file not found", ha="center", va="center")
        return savefig("supp_threshold_sensitivity")
    df = pd.read_csv(p)
    df = df.copy()
    col = "changed_all_pass_count"
    if col not in df.columns:
        numeric_cols = [c for c in df.columns if c.endswith("count") or "changed" in c]
        col = numeric_cols[0] if numeric_cols else df.select_dtypes(include=[np.number]).columns[-1]
    label_col = "threshold_name" if "threshold_name" in df.columns else df.columns[0]
    top = df.sort_values(col, ascending=False).head(14)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    y = np.arange(len(top))
    ax.barh(y, top[col], color="#377eb8")
    ax.set_yticks(y, labels=top[label_col].astype(str), fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("All-pass changes across sweep")
    ax.set_title("Threshold-conditioned acceptability sensitivity", fontsize=12, weight="bold")
    ax.grid(axis="x", alpha=0.25)
    return savefig("supp_threshold_sensitivity")


def write_report(paths: dict[str, list[str]]) -> None:
    lines = [
        "# Figure Rebuild Report - 20260609",
        "",
        "All figures were generated from saved CSV evidence using `figure_scripts/build_final_figures_20260609.py`.",
        "The figures avoid decorative imagery and use bounded labels consistent with the Wave 1 claim rules.",
        "",
        "## Generated figures",
        "",
    ]
    for name, outs in paths.items():
        lines.append(f"- `{name}`")
        for out in outs:
            rel = Path(out)
            lines.append(f"  - `{rel}`")
    lines.extend(
        [
            "",
            "## Source data",
            "",
            "- Wave 1 request conservation: `wave1_evidence_20260609/request_conservation_by_behavior_20260609.csv`",
            "- Wave 1 FleetBalanced branch trace: `wave1_evidence_20260609/fleetbalanced_branch_trace_20260609.csv`",
            "- Direct weekly severity and baseline matrix: `wave2_direct_severity_baseline_20260609/actor_gate_matrix_with_severity_and_baseline_20260609.csv`",
            "- Targeted 28-day severity confirmation: `final_applied_energy_package_20260609/targeted_28day_behavior_severity_results_20260609.csv`",
            "- IEEE-33 EV-off deltas: `wave2_strong_upgrades_20260609/ieee33_ev_policy_deltas_vs_ev_off_20260609.csv`",
            "- Threshold sensitivity: `research_strengthening_20260609/binding_threshold_sensitivity_overall_20260609.csv`",
            "",
            "## Claim boundaries",
            "",
            "- FleetBalanced is shown only as an equivalence/branch audit, not a superior controller.",
            "- Behavioral severity is labeled as request-event pressure, not true demanded-kWh amplification.",
            "- IEEE-33 is labeled as a representative feeder stress screen with EV-off deltas, not site validation.",
            "- Threshold results are presented as threshold-conditioned acceptability.",
        ]
    )
    (FINAL / "FIGURE_REBUILD_REPORT_20260609.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()
    paths = {
        "fig1_multi_actor_framework": fig1_framework(),
        "fig2_actor_gate_acceptability_matrix": fig2_actor_gate_matrix(),
        "fig3_behavioral_severity_curve": fig3_behavioral_severity_curve(),
        "fig4_failure_pattern_taxonomy": fig4_failure_taxonomy(),
        "fig5_grid_policy_tradeoff": fig5_grid_tradeoff(),
        "fig6_ieee33_feeder_deltas": fig6_ieee33_feeder_deltas(),
        "fig_robustness_acceptability": fig_robustness_acceptability(),
        "supp_full_actor_gate_matrix": supp_full_actor_gate_matrix(),
        # supp_fleetbalanced_equivalence_audit dropped from the manuscript (0-vs-0 bar chart;
        # the equivalence result is stated in the main text). Function retained below for reference.
        "supp_request_id_conservation_audit": supp_request_conservation(),
        "supp_threshold_sensitivity": supp_threshold_sensitivity(),
    }
    write_report(paths)
    for name, outs in paths.items():
        print(name)
        for out in outs:
            print(f"  {out}")


if __name__ == "__main__":
    main()
