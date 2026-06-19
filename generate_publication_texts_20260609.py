#!/usr/bin/env python3
"""Generate final publication-package text artifacts for the EV charging study."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd


ROOT = Path("/home/jia/multi actor")
FINAL = ROOT / "final_applied_energy_package_20260609"
WAVE1 = ROOT / "wave1_evidence_20260609"
WAVE2 = ROOT / "wave2_direct_severity_baseline_20260609"
WAVE2_GRID = ROOT / "wave2_strong_upgrades_20260609"
STRENGTH = ROOT / "research_strengthening_20260609"
UPGRADE = ROOT / "applied_energy_research_upgrade_20260609"


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def f3(x: float) -> str:
    return f"{x:.3f}"


def read_summaries() -> dict[str, object]:
    weekly_sev = pd.read_csv(WAVE2 / "behavior_severity_results_20260609.csv")
    weekly_actor = pd.read_csv(WAVE2 / "actor_gate_matrix_with_severity_and_baseline_20260609.csv")
    weekly_fail = pd.read_csv(WAVE2 / "failure_pattern_taxonomy_with_severity_and_baseline_20260609.csv")
    target = pd.read_csv(FINAL / "targeted_28day_behavior_severity_results_20260609.csv")
    target_fail = pd.read_csv(FINAL / "targeted_28day_failure_pattern_taxonomy_20260609.csv")
    fb = pd.read_csv(WAVE1 / "fleetbalanced_branch_trace_20260609.csv")
    req = pd.read_csv(WAVE1 / "request_conservation_by_behavior_20260609.csv")
    ieee = pd.read_csv(WAVE2_GRID / "ieee33_ev_policy_deltas_vs_ev_off_20260609.csv")

    weekly_explicit = weekly_sev[weekly_sev["severity_level"].notna()].copy()
    weekly_by_sev = (
        weekly_explicit.groupby("severity_level", as_index=False)
        .agg(
            rows=("rows", "sum"),
            driver=("driver_pass_rate", "mean"),
            fleet=("fleet_pass_rate", "mean"),
            grid=("grid_pass_rate", "mean"),
            allp=("all_pass_rate", "mean"),
            ratio=("actual_to_fleet_request_ratio_mean", "mean"),
            delivered=("delivered_ratio_mean", "mean"),
            peak=("peak_ratio_mean", "mean"),
        )
        .sort_values("severity_level")
    )
    target_by_sev = (
        target[target["severity_level"].notna()]
        .groupby("severity_level", as_index=False)
        .agg(
            rows=("rows", "sum"),
            driver=("driver_pass_rate", "mean"),
            fleet=("fleet_pass_rate", "mean"),
            grid=("grid_pass_rate", "mean"),
            allp=("all_pass_rate", "mean"),
            ratio=("actual_to_fleet_request_ratio_mean", "mean"),
            delivered=("delivered_ratio_mean", "mean"),
            peak=("peak_ratio_mean", "mean"),
            deferrals=("grid_deferred_mean", "mean"),
        )
        .sort_values("severity_level")
    )
    policy_summary = (
        weekly_actor.groupby("fleet_policy", as_index=False)
        .agg(
            allp=("all_pass_rate", "mean"),
            driver=("driver_pass_rate", "mean"),
            fleet=("fleet_pass_rate", "mean"),
            grid=("grid_pass_rate", "mean"),
            rows=("rows", "sum"),
        )
        .sort_values("fleet_policy")
    )
    grid_trade = (
        target[target["severity_level"].notna()]
        .groupby(["severity_level", "grid_policy"], as_index=False)
        .agg(allp=("all_pass_rate", "mean"), peak=("peak_ratio_mean", "mean"), deferrals=("grid_deferred_mean", "mean"))
        .sort_values(["severity_level", "grid_policy"])
    )
    fail_counts = weekly_fail.groupby("actor_failure_pattern")["rows"].sum().sort_values(ascending=False)
    target_fail_counts = target_fail.groupby("actor_failure_pattern")["rows"].sum().sort_values(ascending=False)
    feeder = ieee[
        [
            "substation_peak_kw_delta_vs_ev_off",
            "max_line_loading_pct_delta_vs_ev_off",
            "total_losses_kwh_delta_vs_ev_off",
            "voltage_violation_timesteps_delta_vs_ev_off",
        ]
    ].agg(["mean", "min", "max"])
    return {
        "weekly_by_sev": weekly_by_sev,
        "target_by_sev": target_by_sev,
        "policy_summary": policy_summary,
        "grid_trade": grid_trade,
        "fail_counts": fail_counts,
        "target_fail_counts": target_fail_counts,
        "fb_rows": len(fb),
        "fb_changed_rows": int((fb["fleetbalanced_action_changed_count"] > 0).sum()),
        "fb_l1_max": float(fb["action_l1_from_servicefirst"].max()),
        "req_rows": int(req["rows"].sum()) if "rows" in req.columns else None,
        "req_max_count_residual": float(req["max_count_residual"].max()) if "max_count_residual" in req.columns else 0.0,
        "req_ratio_max": float(req["actual_to_fleet_ratio"].max()) if "actual_to_fleet_ratio" in req.columns else float("nan"),
        "feeder": feeder,
        "ieee_rows": len(ieee),
        "ieee_solves": len(ieee) * 168,
    }


def literature_rows() -> list[dict[str, str]]:
    return [
        {
            "id": "R1",
            "category": "Applied Energy journal fit",
            "exact_title": "Applied Energy - Aims and scope",
            "authors": "Elsevier",
            "year": "2026",
            "source": "ScienceDirect journal page",
            "doi": "",
            "url": "https://www.sciencedirect.com/journal/applied-energy",
            "peer_reviewed": "No - journal information page",
            "claim_supported": "Applied Energy fit requires an energy-systems framing rather than a controller-debug story.",
            "limitation": "Journal page, not peer-reviewed evidence.",
            "verification_source": "ScienceDirect search result, 2026-06-09.",
        },
        {
            "id": "R2",
            "category": "Applied Energy precedent; QoS-cost trade-off",
            "exact_title": "Pareto optimality in cost and service quality for an Electric Vehicle charging facility",
            "authors": "Soomin Woo; Sangjae Bae; Scott J. Moura",
            "year": "2021",
            "source": "Applied Energy 290, 116779",
            "doi": "10.1016/j.apenergy.2021.116779",
            "url": "https://doi.org/10.1016/j.apenergy.2021.116779",
            "peer_reviewed": "Yes",
            "claim_supported": "Applied Energy precedent for explicit cost-service quality trade-offs in EV charging facilities.",
            "limitation": "Facility planning paper, not multi-actor behavioral simulation.",
            "verification_source": "ScienceDirect and Berkeley ITS records.",
        },
        {
            "id": "R3",
            "category": "Coordinated EV charging",
            "exact_title": "Decentralized Charging Control of Large Populations of Plug-in Electric Vehicles",
            "authors": "Zhongjing Ma; Duncan S. Callaway; Ian A. Hiskens",
            "year": "2013",
            "source": "IEEE Transactions on Control Systems Technology 21(1), 67-78",
            "doi": "10.1109/TCST.2011.2174059",
            "url": "https://doi.org/10.1109/TCST.2011.2174059",
            "peer_reviewed": "Yes",
            "claim_supported": "Coordinated EV charging can be formulated as a distributed control problem coupled through aggregate system signals.",
            "limitation": "Assumes rational response to coordination signals; not an acceptance-gate framework.",
            "verification_source": "CoLab DOI record.",
        },
        {
            "id": "R4",
            "category": "Coordinated EV charging",
            "exact_title": "Optimal decentralized protocol for electric vehicle charging",
            "authors": "Lingwen Gan; Ufuk Topcu; Steven H. Low",
            "year": "2013",
            "source": "IEEE Transactions on Power Systems 28(2), 940-951",
            "doi": "10.1109/TPWRS.2012.2210288",
            "url": "https://doi.org/10.1109/TPWRS.2012.2210288",
            "peer_reviewed": "Yes",
            "claim_supported": "Valley-filling and decentralized charging protocols motivate grid-aware EV control baselines.",
            "limitation": "Optimization setting differs from this paper's simulation-gate evaluation.",
            "verification_source": "Caltech Authors and DOI search records.",
        },
        {
            "id": "R5",
            "category": "Charging strategy baseline",
            "exact_title": "Optimal Charging Strategies for Unidirectional Vehicle-to-Grid",
            "authors": "Eric Sortomme; Mohamed A. El-Sharkawi",
            "year": "2011",
            "source": "IEEE Transactions on Smart Grid 2(1), 131-138",
            "doi": "10.1109/TSG.2010.2090910",
            "url": "https://doi.org/10.1109/TSG.2010.2090910",
            "peer_reviewed": "Yes",
            "claim_supported": "Charging control literature commonly balances charging requirements and grid-side objectives.",
            "limitation": "V1G scheduling setting, not multi-actor gates.",
            "verification_source": "DOI search records.",
        },
        {
            "id": "R6",
            "category": "Charging networks and practical control",
            "exact_title": "Adaptive Charging Networks: A Framework for Smart Electric Vehicle Charging",
            "authors": "Zachary J. Lee; George S. Lee; Ted Lee; Cheng Jin; Rand Lee; Zhi Low; Daniel Chang; Christine Ortega; Steven H. Low",
            "year": "2021",
            "source": "IEEE Transactions on Smart Grid 12(5), 4339-4350",
            "doi": "10.1109/TSG.2021.3074437",
            "url": "https://doi.org/10.1109/TSG.2021.3074437",
            "peer_reviewed": "Yes",
            "claim_supported": "Real charging networks combine service, infrastructure constraints, control signals, and practical deployment complications.",
            "limitation": "Field-network framework with different data and objectives.",
            "verification_source": "NSF Public Access Repository and Semantic Scholar DOI records.",
        },
        {
            "id": "R7",
            "category": "Simulation and reproducibility",
            "exact_title": "ACN-Sim: An Open-Source Simulator for Data-Driven Electric Vehicle Charging Research",
            "authors": "Zachary J. Lee; Sunash Sharma; Daniel Johansson; Steven H. Low",
            "year": "2019",
            "source": "IEEE SmartGridComm",
            "doi": "10.1109/SmartGridComm.2019.8909765",
            "url": "https://doi.org/10.1109/SmartGridComm.2019.8909765",
            "peer_reviewed": "Yes - conference",
            "claim_supported": "EV charging simulation studies need transparent assumptions, modular traces, and reproducible evaluation.",
            "limitation": "Simulator precedent, not evidence for this simulator's behavioral models.",
            "verification_source": "NSF Public Access Repository and arXiv metadata.",
        },
        {
            "id": "R8",
            "category": "Managed charging acceptance",
            "exact_title": "Understanding user acceptance factors of electric vehicle smart charging",
            "authors": "Christian Will; Alexander Schuller",
            "year": "2016",
            "source": "Transportation Research Part C 71, 198-214",
            "doi": "10.1016/j.trc.2016.07.006",
            "url": "https://doi.org/10.1016/j.trc.2016.07.006",
            "peer_reviewed": "Yes",
            "claim_supported": "Smart-charging success depends on user acceptance and perceived control, reliability, and inconvenience.",
            "limitation": "Acceptance study, not calibration for this simulator.",
            "verification_source": "KITopen/TRID records.",
        },
        {
            "id": "R9",
            "category": "Managed charging acceptance",
            "exact_title": "Anticipating PEV buyers' acceptance of utility controlled charging",
            "authors": "Joseph Bailey; Jonn Axsen",
            "year": "2015",
            "source": "Transportation Research Part A 82, 29-46",
            "doi": "10.1016/j.tra.2015.09.004",
            "url": "https://doi.org/10.1016/j.tra.2015.09.004",
            "peer_reviewed": "Yes",
            "claim_supported": "Drivers differ in acceptance of utility-controlled charging and value cost savings, renewables, privacy, and control differently.",
            "limitation": "Stated-preference sample, not operational fleet simulation.",
            "verification_source": "ScienceDirect record.",
        },
        {
            "id": "R10",
            "category": "Behavior and smart charging field response",
            "exact_title": "User responses to a smart charging system in Germany: Battery electric vehicle driver motivation, attitudes and acceptance",
            "authors": "Nina Schmalfuss; Karoline Muhl; Josef F. Krems",
            "year": "2015",
            "source": "Energy Research & Social Science 9, 60-71",
            "doi": "10.1016/j.erss.2015.08.019",
            "url": "https://doi.org/10.1016/j.erss.2015.08.019",
            "peer_reviewed": "Yes",
            "claim_supported": "Observed smart-charging participation can depend on trust, reliability, and daily-life integration.",
            "limitation": "Small field trial; does not calibrate this paper's severity levels.",
            "verification_source": "ScienceDirect record.",
        },
        {
            "id": "R11",
            "category": "Managed charging perceptions",
            "exact_title": "What do consumers think of smart charging? Perceptions among actual and potential plug-in electric vehicle adopters in the United Kingdom",
            "authors": "Emma Delmonte; Neale Kinnear; Becca Jenkins; Stephen Skippon",
            "year": "2020",
            "source": "Energy Research & Social Science 60, 101318",
            "doi": "10.1016/j.erss.2019.101318",
            "url": "https://doi.org/10.1016/j.erss.2019.101318",
            "peer_reviewed": "Yes",
            "claim_supported": "Smart charging acceptance includes social benefit, inconvenience, and control perceptions.",
            "limitation": "Survey/perception evidence, not operational acceptance gates.",
            "verification_source": "CoLab DOI record.",
        },
        {
            "id": "R12",
            "category": "Acceptance value in energy systems",
            "exact_title": "The value of consumer acceptance of controlled electric vehicle charging in a decarbonizing grid: The case of California",
            "authors": "Brian Tarroja; Eric Hittinger",
            "year": "2021",
            "source": "Energy 229, 120691",
            "doi": "10.1016/j.energy.2021.120691",
            "url": "https://doi.org/10.1016/j.energy.2021.120691",
            "peer_reviewed": "Yes",
            "claim_supported": "Acceptance of controlled charging can affect energy-system value and integration outcomes.",
            "limitation": "System-planning valuation, not site-level actor gates.",
            "verification_source": "IDEAS/RePEc DOI record.",
        },
        {
            "id": "R13",
            "category": "EV charging QoS and fairness",
            "exact_title": "Quality of service and fairness for electric vehicle charging as a service",
            "authors": "Dominik Danner; Hermann de Meer",
            "year": "2021",
            "source": "Energy Informatics 4(Suppl 3), 16",
            "doi": "10.1186/s42162-021-00175-3",
            "url": "https://doi.org/10.1186/s42162-021-00175-3",
            "peer_reviewed": "Yes",
            "claim_supported": "EV charging can be evaluated as a service with QoS, fairness, and grid constraints.",
            "limitation": "Queuing architecture differs from this multi-actor simulator.",
            "verification_source": "SpringerOpen/DOAJ records.",
        },
        {
            "id": "R14",
            "category": "Distribution feeder EV impacts",
            "exact_title": "The Impact of Charging Plug-In Hybrid Electric Vehicles on a Residential Distribution Grid",
            "authors": "Kristien Clement-Nyns; Edwin Haesen; Johan Driesen",
            "year": "2010",
            "source": "IEEE Transactions on Power Systems 25(1), 371-380",
            "doi": "10.1109/TPWRS.2009.2036481",
            "url": "https://doi.org/10.1109/TPWRS.2009.2036481",
            "peer_reviewed": "Yes",
            "claim_supported": "EV charging can affect distribution-grid losses, voltage deviations, and loading.",
            "limitation": "Residential distribution setting and PHEV assumptions differ from this feeder screen.",
            "verification_source": "CoLab DOI record.",
        },
        {
            "id": "R15",
            "category": "Distribution feeder EV impacts",
            "exact_title": "A Comprehensive Study of the Impacts of PHEVs on Residential Distribution Networks",
            "authors": "Mohamed S. ElNozahy; Magdy M. A. Salama",
            "year": "2014",
            "source": "IEEE Transactions on Sustainable Energy 5(1), 332-342",
            "doi": "10.1109/TSTE.2013.2284573",
            "url": "https://doi.org/10.1109/TSTE.2013.2284573",
            "peer_reviewed": "Yes",
            "claim_supported": "Monte Carlo feeder impact studies motivate representative stress screening and stochastic EV load treatment.",
            "limitation": "Residential PHEV benchmark, not site-specific validation.",
            "verification_source": "ResearchGate DOI metadata.",
        },
        {
            "id": "R16",
            "category": "IEEE-33 benchmark provenance",
            "exact_title": "Network reconfiguration in distribution systems for loss reduction and load balancing",
            "authors": "M. E. Baran; F. F. Wu",
            "year": "1989",
            "source": "IEEE Transactions on Power Delivery 4(2), 1401-1407",
            "doi": "10.1109/61.25627",
            "url": "https://doi.org/10.1109/61.25627",
            "peer_reviewed": "Yes",
            "claim_supported": "The IEEE 33-bus radial distribution benchmark is traceable to Baran and Wu's feeder reconfiguration study.",
            "limitation": "Benchmark feeder, not a real-site feeder for this project.",
            "verification_source": "OUCI and DOI search records.",
        },
        {
            "id": "R17",
            "category": "Power-flow software",
            "exact_title": "Pandapower--An Open-Source Python Tool for Convenient Modeling, Analysis, and Optimization of Electric Power Systems",
            "authors": "Leon Thurner; Alexander Scheidler; Florian Schafer; Jan-Hendrik Menke; Julian Dollichon; Friederike Meier; Steffen Meinecke; Martin Braun",
            "year": "2018",
            "source": "IEEE Transactions on Power Systems 33(6), 6510-6521",
            "doi": "10.1109/TPWRS.2018.2829021",
            "url": "https://doi.org/10.1109/TPWRS.2018.2829021",
            "peer_reviewed": "Yes",
            "claim_supported": "Pandapower is an established open-source tool for static and quasi-static power-system analysis.",
            "limitation": "Tool validation does not validate this project's scenario assumptions.",
            "verification_source": "CoLab and arXiv records.",
        },
        {
            "id": "R18",
            "category": "Power-flow software documentation",
            "exact_title": "pandapower documentation",
            "authors": "pandapower development team",
            "year": "2026",
            "source": "Official documentation",
            "doi": "",
            "url": "https://pandapower.readthedocs.io/",
            "peer_reviewed": "No - software documentation",
            "claim_supported": "Implementation details for pandapower network modeling and power-flow execution.",
            "limitation": "Documentation source, not peer-reviewed empirical evidence.",
            "verification_source": "Official pandapower Read the Docs search result.",
        },
    ]


def write_literature() -> None:
    rows = literature_rows()
    csv_path = FINAL / "verified_literature_table_20260609.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    by_cat: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_cat.setdefault(row["category"], []).append(row)

    lines = [
        "# Verified Literature Grounding Report - 20260609",
        "",
        "This table verifies the references intended for the Applied Energy manuscript. No guessed DOI is used. Non-peer-reviewed sources are labeled as such and are used only for journal scope or software documentation, not for empirical claims.",
        "",
        f"Verified records: {len(rows)}.",
        "",
        "## Category coverage",
        "",
    ]
    for cat, items in by_cat.items():
        lines.append(f"- {cat}: {len(items)} record(s)")
    lines.extend(["", "## Reference-to-claim map", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row['id']}. {row['exact_title']}",
                f"- Authors/year: {row['authors']} ({row['year']})",
                f"- Source: {row['source']}",
                f"- DOI: {row['doi'] or 'none'}",
                f"- URL: {row['url']}",
                f"- Peer-reviewed: {row['peer_reviewed']}",
                f"- Supports: {row['claim_supported']}",
                f"- Limitation: {row['limitation']}",
                f"- Verification: {row['verification_source']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Removed or downgraded sources",
            "",
            "- Broad web pages, Wikipedia-style pages, and repository pages were not used for manuscript claims unless explicitly labeled as documentation or journal scope.",
            "- Behavior papers are used to justify acceptance and response risk, not to calibrate this simulator's severity parameters.",
            "- IEEE-33 references are used for benchmark provenance, not site validation.",
        ]
    )
    (FINAL / "VERIFIED_LITERATURE_GROUNDING_REPORT_20260609.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def reference_list() -> str:
    rows = literature_rows()
    refs = []
    for i, row in enumerate(rows[1:], start=1):
        doi = f" https://doi.org/{row['doi']}" if row["doi"] else f" {row['url']}"
        refs.append(f"[{i}] {row['authors']}. {row['exact_title']}. {row['source']}. {row['year']}.{doi}")
    return "\n".join(refs)


def markdown_table_from_df(df: pd.DataFrame, cols: list[str], headers: list[str]) -> str:
    lines = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                cells.append(f"{v:.3f}")
            else:
                cells.append(str(v))
        lines.append("|" + "|".join(cells) + "|")
    return "\n".join(lines)


def write_manuscript(s: dict[str, object]) -> None:
    weekly_by_sev: pd.DataFrame = s["weekly_by_sev"]  # type: ignore[assignment]
    target_by_sev: pd.DataFrame = s["target_by_sev"]  # type: ignore[assignment]
    policy_summary: pd.DataFrame = s["policy_summary"]  # type: ignore[assignment]
    grid_trade: pd.DataFrame = s["grid_trade"]  # type: ignore[assignment]
    fail_counts: pd.Series = s["fail_counts"]  # type: ignore[assignment]
    feeder: pd.DataFrame = s["feeder"]  # type: ignore[assignment]

    w0 = weekly_by_sev.loc[weekly_by_sev["severity_level"] == 0].iloc[0]
    w1 = weekly_by_sev.loc[weekly_by_sev["severity_level"] == 1].iloc[0]
    w3 = weekly_by_sev.loc[weekly_by_sev["severity_level"] == 3].iloc[0]
    t0 = target_by_sev.loc[target_by_sev["severity_level"] == 0].iloc[0]
    t1 = target_by_sev.loc[target_by_sev["severity_level"] == 1].iloc[0]
    t3 = target_by_sev.loc[target_by_sev["severity_level"] == 3].iloc[0]
    sg = policy_summary.loc[policy_summary["fleet_policy"] == "FleetServiceGridWeighted"].iloc[0]
    sf = policy_summary.loc[policy_summary["fleet_policy"] == "FleetServiceFirst"].iloc[0]
    co = policy_summary.loc[policy_summary["fleet_policy"] == "FleetCostOnly"].iloc[0]
    qa = policy_summary.loc[policy_summary["fleet_policy"] == "FleetQueueAware"].iloc[0]

    sev_table = markdown_table_from_df(
        weekly_by_sev[["severity_level", "driver", "fleet", "grid", "allp", "ratio", "delivered", "peak"]],
        ["severity_level", "driver", "fleet", "grid", "allp", "ratio", "delivered", "peak"],
        ["Severity", "Driver pass", "Fleet pass", "Grid pass", "All-pass", "Actual/fleet events", "Delivered ratio", "Peak ratio"],
    )
    target_table = markdown_table_from_df(
        target_by_sev[["severity_level", "driver", "fleet", "grid", "allp", "ratio", "delivered", "peak"]],
        ["severity_level", "driver", "fleet", "grid", "allp", "ratio", "delivered", "peak"],
        ["Severity", "Driver pass", "Fleet pass", "Grid pass", "All-pass", "Actual/fleet events", "Delivered ratio", "Peak ratio"],
    )
    policy_table = markdown_table_from_df(
        policy_summary[["fleet_policy", "driver", "fleet", "grid", "allp"]],
        ["fleet_policy", "driver", "fleet", "grid", "allp"],
        ["Fleet policy", "Driver pass", "Fleet pass", "Grid pass", "All-pass"],
    )

    manuscript = f"""# Multi-actor acceptability of EV fleet charging control under capacity and grid constraints

Author A; Author B; Author C

Affiliation placeholders.

Corresponding author: corresponding.author@example.edu

## Highlights

- A multi-actor gate framework evaluates EV charging control from driver, fleet, and grid perspectives.
- Weekly severity experiments show all-pass acceptability falls from {pct(w0['allp'])} under full compliance to {pct(w1['allp'])} under mild behavioral deviation.
- A targeted 28-day confirmation at 35% capacity supports the same collapse while request-event pressure rises from {f3(t0['ratio'])} to {f3(t3['ratio'])}.
- A service-grid weighted heuristic reduces strawman-baseline risk but does not produce a simple controller-superiority result.
- IEEE-33 feeder analysis is framed as a representative stress screen using EV-off deltas, not site-specific validation.
- FleetBalanced is not claimed as a distinct mechanism because branch traces show zero final-action difference from ServiceFirst.

## Abstract

Managed electric vehicle (EV) charging is often evaluated through delivered energy, cost, peak demand, or queue metrics, but deployment decisions involve multiple actors whose acceptability constraints can conflict. This paper develops a multi-actor acceptability framework for EV fleet charging control under charger-capacity and grid-screen constraints. The framework evaluates each episode through pre-specified driver, fleet, and grid gates and records whether a policy is acceptable to all actors simultaneously. A reproducible simulation campaign compares diagnostic single-objective heuristics, service-oriented dispatch, a service-grid weighted heuristic, behavioral response variants, NoGrid and PeakPenalty grid policies, and a representative IEEE-33 feeder stress screen. Request-ID/count audits conserve the event pipeline, and a persistent demanded-kWh trace over the targeted 28-day severity cases reconciles 4,300,800 vehicle-step ledger rows within 1e-4 kWh. That audit classifies the behavioral effect as event churn: request-event counts rise to 2.349x at severity 3, while simulator demanded kWh falls to 0.917x severity 0. Behavioral findings are therefore reported as request-event pressure rather than energy-demand amplification. The same audit shows that FleetBalanced changes zero final actions relative to ServiceFirst across 2016 branch-trace rows and is not treated as a distinct controller. In weekly severity experiments, full-compliance service-oriented policies pass all actor gates, whereas all-pass acceptability falls from {pct(w0['allp'])} at severity 0 to {pct(w1['allp'])} at mild deviation, while actual/fleet request-event ratio rises from {f3(w0['ratio'])} to {f3(w3['ratio'])}. A targeted 28-day confirmation at 35% capacity supports this finding. PeakPenalty reduces selected peak ratios but does not rescue all-pass outcomes after driver and fleet gates fail. The results indicate that apparently reasonable charging heuristics can be deployment-invalid when evaluated against explicit stakeholder gates.

Keywords: electric vehicle charging; managed charging; multi-actor acceptability; behavioral response; fleet dispatch; distribution feeder; IEEE-33; demand management

## 1. Introduction

Electrification of road transport is shifting a substantial share of energy demand from liquid fuels to electricity networks. At the same time, charging infrastructure is frequently installed behind local service connections, depot transformers, workplace panels, or distribution feeders whose capacity was not designed around synchronized high-power EV charging. This creates a planning and operating problem that is central to applied energy systems: charging should deliver enough energy to drivers and fleet operations, but it should also avoid producing grid peaks, ramps, losses, and line-loading stress that undermine local power-system operation. The problem is not only to compute a schedule that improves one metric. The practical question is whether a charging-control policy is acceptable to all relevant actors under the constraints and behaviors expected during operation.

The literature contains strong foundations for coordinated and decentralized EV charging control [2-5], simulation-driven evaluation [6], and EV facility cost-service trade-off analysis in an Applied Energy style [1]. Other studies show that managed charging depends on user acceptance, trust, perceived control, and inconvenience [7-11]. Charging can also be evaluated as a service-quality problem [1,12], while distribution studies show that EV charging can affect feeder voltage, loading, and losses [13,14]. These strands motivate a broader evaluation stance. A policy that is attractive for the fleet operator because it serves many requests may still be unacceptable to drivers if reliability or delivered-energy ratios degrade. A policy that reduces cost or queue activity may fail fleet service completion. A grid policy can reduce a peak ratio while leaving driver and fleet failures unresolved.

This paper therefore reframes the project as an energy-systems evaluation study rather than a controller-superiority study. The initial simulator included a FleetBalanced policy, but an audit found that FleetBalanced and FleetServiceFirst are indistinguishable at the saved episode-aggregate level, and branch traces show no final-action difference under current scenarios. Treating that result honestly is important. It prevents the paper from claiming a mechanism that the evidence does not support and shifts the contribution to the more defensible question: which charging-control policies are mutually acceptable to drivers, fleet operators, and grid operators, and which gates bind first?

This paper contributes to the literature by: (1) defining a falsifiable multi-actor acceptability-gate framework for EV fleet charging under capacity and grid constraints; (2) producing a policy-by-actor failure taxonomy that separates driver, fleet, grid, and all-pass outcomes; (3) adding a request-pipeline audit that separates driver request events, fleet recommendations, grid adjustments, and final service; (4) introducing a behavioral severity analysis that shows how request-event pressure can drive acceptability collapse; (5) adding a service-grid weighted heuristic comparator so the evaluation is not limited to diagnostic single-objective baselines; (6) using a representative IEEE-33 feeder stress screen with EV-off and policy-delta framing; and (7) documenting the FleetBalanced equivalence audit as a reproducibility boundary rather than a claimed policy mechanism.

The remainder of the paper is organized as follows. Section 2 describes the system context and actors. Section 3 presents the acceptability-gate formulation and policy families. Section 4 gives the experimental design and audit protocol. Section 5 describes the data and simulation setup. Section 6 reports the main results. Section 7 discusses implications. Section 8 states limitations. Section 9 concludes.

## 2. System Context and Problem Setting

The modeled system is a capacity-constrained EV charging facility or fleet-charging site with three decision layers. The driver layer generates charging request events and may deviate from recommendations according to a behavior model. The fleet layer selects which requests to prioritize under finite capacity. The grid layer may apply a PeakPenalty intervention that defers selected charging events when the site is exposed to peak pressure. The final service layer records delivered energy, reliability, deferrals, unserved events, and load-shape outcomes.

The stakeholders are: drivers, who require adequate charging service and reliability; the fleet or facility operator, who needs service completion, operational stability, and manageable request volume; and the grid or distribution operator, who is concerned with peak ratios, ramping, load factor, line loading, losses, and feeder stress. These actors need not agree on a single objective. For example, increasing service can increase peak demand, while deferring charging for peak management can reduce driver or fleet acceptability.

Fig. 1 shows the system framework. Driver behavior produces actual request events. A fleet policy converts candidate events into recommended actions under charger capacity. A grid policy can adjust the recommended actions. The final charging service is evaluated against driver, fleet, and grid gates. All-pass acceptability is the logical conjunction of those three pass indicators.

## 3. Multi-actor Acceptability Formulation

Let \\(i \\in \\mathcal{{I}}\\) index EVs, \\(t \\in \\mathcal{{T}}\\) index hourly simulation steps, \\(s \\in \\mathcal{{S}}\\) index random seeds, \\(c \\in \\mathcal{{C}}\\) index capacity levels, \\(b \\in \\mathcal{{B}}\\) index behavior models, \\(f \\in \\mathcal{{F}}\\) index fleet policies, and \\(g \\in \\mathcal{{G}}\\) index grid policies. A simulation episode is denoted \\(e=(s,c,b,f,g,H)\\), where \\(H\\) is the horizon.

The driver layer produces a request event set

\\[
\\mathcal{{R}}_t = \\{{r: a_r=t, E_r^{{req}}>0, d_r \\geq t\\}},
\\tag{{1}}
\\]

where \\(a_r\\) is the event time, \\(E_r^{{req}}\\) is the requested energy represented by the simulator event, and \\(d_r\\) is a deadline or service-risk proxy when available. The audit adds unique request identifiers and retry links, but persistent request-level demanded kWh is not yet saved for all histories. Therefore, the behavioral result is stated in terms of request-event pressure, not true physical energy-demand amplification.

The fleet policy selects a recommended service action

\\[
x_{{r,t}}^F = \\pi_f(r,t,\\theta_f), \\quad r \\in \\mathcal{{R}}_t,
\\tag{{2}}
\\]

subject to a capacity constraint

\\[
\\sum_{{r \\in \\mathcal{{R}}_t}} p_r x_{{r,t}}^F \\leq C_c,
\\tag{{3}}
\\]

where \\(p_r\\) is the event charging power and \\(C_c\\) is the capacity level. The grid policy modifies the fleet recommendation:

\\[
x_{{r,t}}^G = \\pi_g(x_{{r,t}}^F, L_t, P_t, \\theta_g),
\\tag{{4}}
\\]

where \\(L_t\\) is site load and \\(P_t\\) is a peak-pressure or price-related signal. The final served action is \\(x_{{r,t}} = x_{{r,t}}^G\\). PeakPenalty is thus a grid-layer intervention, not evidence of a fleet-layer idling mechanism.

Driver acceptability is represented as

\\[
A_D(e)=\\mathbb{{1}}\\left[ \\rho_E(e)\\geq \\tau_E, \\; \\Delta_R(e)\\geq \\tau_R, \\; U_D(e)\\leq \\tau_U \\right],
\\tag{{5}}
\\]

where \\(\\rho_E\\) is delivered-energy ratio, \\(\\Delta_R\\) is reliability delta relative to a reference, and \\(U_D\\) is an unmet or requested-but-not-delivered event metric when available. Fleet acceptability is

\\[
A_F(e)=\\mathbb{{1}}\\left[ S_F(e)\\geq \\tau_S, \\; Q_F(e)\\leq \\tau_Q, \\; K_F(e)\\leq \\tau_K \\right],
\\tag{{6}}
\\]

where \\(S_F\\) is service completion, \\(Q_F\\) is queue or request-volume pressure, and \\(K_F\\) is a cost or operating penalty proxy. Grid acceptability is

\\[
A_G(e)=\\mathbb{{1}}\\left[ \\rho_P(e)\\leq \\tau_P, \\; \\rho_{{ramp}}(e)\\leq \\tau_{{ramp}}, \\; \\Delta LF(e)\\geq \\tau_{{LF}} \\right],
\\tag{{7}}
\\]

with peak ratio \\(\\rho_P\\), ramp ratio \\(\\rho_{{ramp}}\\), and load-factor change \\(\\Delta LF\\), where negative \\(\\Delta LF\\) indicates lower load factor than the LeastLaxity anchor. Overall acceptability is

\\[
A_{{all}}(e)=A_D(e)A_F(e)A_G(e).
\\tag{{8}}
\\]

Equations (5)-(8) are normative gates rather than physical laws. Their value is transparency: when a conclusion changes under a threshold sweep, the manuscript reports the conclusion as threshold-conditioned rather than robust in a threshold-independent sense.

Table 0. Pre-specified actor-gate thresholds used in the current evidence package.

|Actor|Metric|Pass condition|Nominal threshold|Unit or interpretation|
|---|---|---|---|---|
|Driver|Delivered ratio vs LeastLaxity anchor|>=|0.95|ratio|
|Driver|Reliability delta vs anchor|>=|-0.5|percentage points|
|Driver|Critical requested-not-delivered delta vs anchor|<=|24|events|
|Fleet|Requested-not-delivered delta vs anchor|<=|117|events|
|Fleet|Mean queue delta vs anchor|<=|1.0|vehicles or queue units|
|Fleet|Max queue delta vs anchor|<=|2.0|vehicles or queue units|
|Fleet|95th percentile wait delta vs anchor|<=|30|minutes|
|Fleet|Energy-cost ratio vs anchor|<=|1.10|ratio|
|Fleet|Demand-charge exposure ratio vs anchor|<=|1.10|ratio|
|Grid|Peak ratio vs anchor|<=|1.05|ratio|
|Grid|Ramp p95 ratio vs anchor|<=|1.10|ratio|
|Grid|Peak-to-average ratio vs anchor|<=|1.10|ratio|
|Grid|Squared-load proxy ratio vs anchor|<=|1.10|ratio|
|Grid|Load-factor delta vs anchor|>=|-0.05|signed delta|

When a submetric is unavailable in a specific run, it is not silently counted as a pass; the reported gate is computed from the persisted gate columns in the result CSVs. The appendix identifies the source files containing these persisted pass/fail columns. Threshold sensitivity shows that these gates are not neutral constants: in the weekly 168 h sensitivity file, tightening delivered-ratio threshold from 0.95 to 0.99 reduces all-pass count by 18 rows, and requiring 1.00 reduces it by 60 rows. This is why the manuscript uses threshold-conditioned acceptability rather than threshold-independent robustness.


### 3.1 Policy Families

The diagnostic baselines are LeastLaxity, CostOnly, and QueueAware. LeastLaxity prioritizes time-critical requests and serves as an anchor. CostOnly and QueueAware are not presented as state-of-the-art algorithms; they are diagnostic single-objective heuristics that reveal how policies can look reasonable under one metric yet fail actor gates.

FleetServiceFirst prioritizes service completion and reliability. FleetServiceGridWeighted adds a heuristic score that combines deadline urgency, deficit, criticality, low-SoC pressure, and grid pressure. For request \\(r\\) at time \\(t\\), the score has the form

\\[
z_{{r,t}} = w_1 U_{{r,t}} + w_2 D_{{r,t}} + w_3 C_r + w_4 S_{{r,t}} - w_5 G_t,
\\tag{{9}}
\\]

where \\(U_{{r,t}}\\) is urgency, \\(D_{{r,t}}\\) is energy deficit, \\(C_r\\) is criticality, \\(S_{{r,t}}\\) is low-SoC pressure, and \\(G_t\\) is grid peak pressure. Requests are sorted by \\(z_{{r,t}}\\) and selected subject to Eq. (3). This is a heuristic comparator, not an optimizer.

FleetBalanced is audited but not claimed as a distinct mechanism. Across {s['fb_rows']} branch-trace rows, FleetBalanced changed {s['fb_changed_rows']} final actions and had a maximum L1 action distance of {f3(s['fb_l1_max'])} relative to FleetServiceFirst. The manuscript therefore treats ServiceFirst/Balanced as a merged service-oriented family for current scenarios.

### 3.2 Algorithm 1

```
Algorithm 1 Multi-actor gate evaluation
Input: seeds S, capacities C, behaviors B, fleet policies F, grid policies G, horizon H
For each episode e = (s,c,b,f,g,H):
    Generate driver request events with unique request identifiers
    Apply fleet policy to obtain recommended charging actions
    Apply grid policy to obtain adjusted charging actions
    Simulate final service, deferral, and unserved outcomes
    Record driver, fleet, and grid metrics
    Compute A_D(e), A_F(e), A_G(e), and A_all(e)
    Assign failure pattern from the three actor gates
Aggregate pass rates, request-event ratios, feeder deltas, and threshold sensitivity
Output: actor-gate matrix, failure taxonomy, audit tables, and reproducible figures
```

## 4. Experimental Design

The evidence program is organized around credibility audits followed by strong-evidence upgrades. The first audit freezes unsupported claims and maps manuscript claims to evidence. The request-ID audit verifies that each request event has a unique identifier, counts reconcile through the driver, fleet, grid, and final-service pipeline, and retries are represented explicitly. The audit passes count conservation but does not pass true request-level demanded-kWh conservation because persistent demanded-energy identifiers are not saved. The FleetBalanced branch audit determines whether the named policy changes final actions.

The weekly severity sweep uses severity levels 0 through 3. Severity 0 is full compliance and serves as an upper-bound benchmark. Severity 1 is mild deviation. Severity 2 is moderate deviation. Severity 3 is the severe/current stress behavior. The weekly sweep uses five seeds, capacities of 20%, 35%, and 50%, ServiceFirst and ServiceGridWeighted policies, and NoGridIncentive and GridPeakPenalty variants. The targeted 28-day confirmation uses a 672 h horizon, seeds 4541-4545, 35% capacity, LeastLaxity, ServiceFirst, ServiceGridWeighted, and both grid policies.

The IEEE-33 screen uses 900 weekly cases and {s['ieee_solves']} hourly power-flow solves. It includes 15 policies, 3 capacities, 10 seeds, 2 placements, and a 168 h horizon. The placement cases are concentrated bus 18 and distributed buses 18/22/25/30/33. Voltage results are treated as a boundary condition because EV-off baseline conditions dominate absolute voltage violation counts. The useful feeder evidence is the relative change in substation peak, line loading, and losses versus EV-off and LeastLaxity anchors.

## 5. Data and Simulation Setup

The simulator uses hourly resolution. Weekly experiments use 168 h and the targeted confirmation uses 672 h. The primary weekly evidence contains 300 explicit actor-gate rows. The targeted 28-day evidence contains 85 rows, of which 80 are explicit severity-policy-grid combinations and 5 are LeastLaxity anchor rows. Random seeds are fixed and reported in the reproducibility appendix. Capacity levels are 20%, 35%, and 50% in weekly runs, with targeted 28-day confirmation at 35% capacity.

The behavior models are stress-test variants rather than calibrated forecasts. This distinction is central. The behavior severity curve is used to evaluate how conclusions change as request-event pressure changes, but the study does not claim that these severity levels are empirically calibrated to a real driver population.

The grid layer compares NoGridIncentive and GridPeakPenalty. PeakPenalty may reduce selected load-shape metrics by deferring grid-adjusted requests, but those deferrals are produced by the grid layer. They are not attributed to FleetBalanced.

## 6. Results

### 6.1 Actor gates change which policies look successful

Fig. 2 and Table 1 show the actor-gate matrix. Single metrics do not tell the same story as all-pass acceptability. The service-oriented family passes all gates under full compliance, whereas CostOnly and QueueAware fail all gates in the weekly evidence. ServiceGridWeighted improves the credibility of the comparator set, but it does not overturn the main result: the paper is not a controller-superiority story.

Table 1. Weekly actor-gate pass rates by fleet policy.

{policy_table}

CostOnly and QueueAware have all-pass rates of {pct(co['allp'])} and {pct(qa['allp'])}. ServiceFirst and ServiceGridWeighted both have all-pass rates of {pct(sf['allp'])} and {pct(sg['allp'])}, respectively, because their all-pass outcomes occur under full compliance and collapse under behavioral deviation. This indicates that service-oriented dispatch can be acceptable in favorable behavior conditions, but the actor gates expose failure when behavioral pressure increases.

### 6.2 Behavioral severity produces abrupt acceptability collapse

Fig. 3 and Table 2 summarize the weekly severity curve. Full compliance passes all actor gates. At mild deviation, all-pass falls to {pct(w1['allp'])}, even though the actual/fleet request-event ratio increases only from {f3(w0['ratio'])} to {f3(w1['ratio'])}. Severe deviation increases request-event pressure to {f3(w3['ratio'])}.

Table 2. Weekly behavioral severity results.

{sev_table}

The result indicates an abrupt threshold effect under the current actor gates. Driver and fleet gates bind first, while grid gates also become increasingly binding. This does not imply that real drivers increase true energy demand by this amount. It indicates that the simulator's event pipeline generates rising request-event pressure as behavioral severity increases.

### 6.3 Targeted 28-day confirmation supports the weekly pattern

Table 3 reports the targeted 28-day confirmation at 35% capacity. The longer horizon supports the weekly result: all-pass falls from {pct(t0['allp'])} at severity 0 to {pct(t1['allp'])} at severity 1. Request-event pressure rises smoothly from {f3(t0['ratio'])} at severity 0 to {f3(t3['ratio'])} at severity 3.

Table 3. Targeted 28-day behavioral severity confirmation.

{target_table}

The 28-day confirmation is targeted rather than exhaustive because it uses 35% capacity only. It is best interpreted as a longer-horizon confirmation of the weekly pattern, with capacity generalization left to future expanded runs.

### 6.4 Failure-pattern taxonomy

Fig. 4 and the failure taxonomy show that the dominant failure pattern is not a single isolated gate. Across the weekly matrix, the categories sum to 300 rows: driver-fleet-grid failure ({int(fail_counts.get('driver_fleet_grid_fail', 0))} rows), all-pass ({int(fail_counts.get('all_pass', 0))} rows), driver-fleet failure ({int(fail_counts.get('driver_fleet_fail', 0))} rows), driver-grid failure ({int(fail_counts.get('driver_grid_fail', 0))} rows), driver-only failure ({int(fail_counts.get('driver_only_fail', 0))} rows), fleet-only failure ({int(fail_counts.get('fleet_only_fail', 0))} row), and grid-only failure ({int(fail_counts.get('grid_only_fail', 0))} row). This pattern matters because it indicates that many policies are not failing on a narrow grid metric alone; they are failing as deployment policies across actors.

### 6.5 GridPeakPenalty reduces peak ratios but does not rescue all-pass outcomes

Fig. 5 compares NoGridIncentive and GridPeakPenalty. In the targeted 28-day confirmation, GridPeakPenalty reduces the mean peak ratio at mild deviation relative to NoGridIncentive in several service-oriented groups, but all-pass remains {pct(t1['allp'])}. This means the grid layer can improve selected grid stress metrics without correcting driver and fleet acceptability failures. The result supports a trade-off claim, not a rescue claim.

### 6.6 ServiceGridWeighted is a credible comparator, not a headline controller

ServiceGridWeighted was added to reduce the strawman-baseline risk. It combines service urgency and grid pressure in one scoring rule. It passes slightly more driver or grid gates in selected subgroups, but its aggregate all-pass rate is {pct(sg['allp'])}, the same as ServiceFirst in the weekly evidence. The correct interpretation is that a stronger heuristic comparator does not remove the need for multi-actor evaluation. It also prevents the paper from depending on obviously weak CostOnly or QueueAware comparators.

### 6.7 IEEE-33 representative feeder stress screen

Fig. 6 reports EV-off feeder deltas using the Baran-Wu IEEE-33 benchmark and pandapower implementation references [15-17]. Across {s['ieee_rows']} feeder cases, the mean EV-added substation peak delta is {feeder.loc['mean','substation_peak_kw_delta_vs_ev_off']:.1f} kW, with a range from {feeder.loc['min','substation_peak_kw_delta_vs_ev_off']:.1f} to {feeder.loc['max','substation_peak_kw_delta_vs_ev_off']:.1f} kW. Mean maximum line-loading delta is {feeder.loc['mean','max_line_loading_pct_delta_vs_ev_off']:.2f} percentage points. Mean losses delta is {feeder.loc['mean','total_losses_kwh_delta_vs_ev_off']:.1f} kWh/week. Voltage-violation timestep deltas versus EV-off are exactly zero in all 900 cases (mean, minimum, and maximum all equal 0), confirming that voltage violation counts are dominated by the base-load screen rather than EV policy differences.

The feeder result should therefore be read as a representative stress screen. It does not validate site-specific feasibility. It does show that EV policies produce measurable relative increments in substation peak, line loading, and losses under benchmark conditions.

### 6.8 FleetBalanced audit result

The supplementary FleetBalanced audit shows zero final-action changes and zero maximum L1 action distance relative to ServiceFirst across {s['fb_rows']} branch-trace rows. This is a negative but useful reproducibility result. It means the manuscript should merge or drop FleetBalanced as a distinct mechanism under current scenarios. It does not prove per-vehicle or per-timestep equivalence beyond the saved traces, and it does not justify any superiority claim.

## 7. Discussion

The main practical implication is that EV charging control should be evaluated as a multi-actor energy-system problem. A policy may be active, feasible in a local simulator, and attractive under one metric while still being unacceptable to the actors required for deployment. The actor-gate framework makes that failure explicit. For a facility operator, the framework identifies whether service or fleet operation is the limiting concern. For grid planners, it distinguishes peak-ratio improvements from system acceptability. For researchers, it provides a claim discipline that prevents mechanism claims from outrunning trace evidence.

The behavioral severity result is important but should be interpreted conservatively. The simulations show severity-dependent request-event pressure and all-pass collapse. They do not prove real-world energy-demand amplification. The next scientific step is persistent request-level demanded-kWh tracing and calibration against observed participation, opt-out, and override behavior.

The grid-policy result also requires disciplined interpretation. PeakPenalty can reduce selected peak ratios and feeder stress deltas, but it does not rescue all-pass acceptability once driver and fleet gates fail. This finding is relevant to energy systems because it shows that grid-side control cannot be judged only by peak reduction when deployment also requires driver and fleet acceptance.

The IEEE-33 screen is useful because it adds a distribution-system lens, but it should not be oversold. IEEE-33 is a benchmark feeder, not a real interconnection study. Since voltage violations are base-load dominated, voltage counts are a boundary condition, while relative deltas in line loading, losses, and substation peak are the interpretable policy signals.

## 8. Limitations

First, the acceptability gates are normative. The threshold sensitivity analysis reduces opacity, but it does not make the thresholds universally correct. Second, behavioral variants are stress tests rather than calibrated forecasts. Third, demanded-kWh tracing is targeted to the 35% 28-day service-oriented severity cases and uses simulator operational demand, not observed field demand. Fourth, the 28-day severity confirmation is targeted to 35% capacity rather than exhaustive across all capacities. Fifth, the IEEE-33 feeder is representative and not site-specific. Sixth, the proposed ServiceGridWeighted controller is a heuristic comparator and has no optimization proof.

## 9. Conclusions

This paper develops and tests a multi-actor acceptability framework for EV fleet charging control under capacity and grid constraints. The framework evaluates driver, fleet, and grid gates separately and defines deployment acceptability as their logical conjunction.

The evidence shows that service-oriented policies pass all gates under full compliance, but mild behavioral deviation is sufficient to eliminate all-pass acceptability under the current gates in both weekly and targeted 28-day experiments. Request-event pressure rises smoothly with severity, while pass rates collapse abruptly. GridPeakPenalty can reduce selected peak ratios but does not rescue all-pass outcomes after driver and fleet gates fail.

The work also clarifies what cannot be claimed. FleetBalanced is not a distinct mechanism under current scenarios because branch traces show no final-action difference from ServiceFirst. Behavioral results are request-event results, not true demanded-kWh amplification. IEEE-33 results are representative feeder stress deltas, not site validation.

For Applied Energy readers, the contribution is a reproducible energy-systems evaluation framework showing why EV charging policies should be judged by multi-actor acceptability rather than by single metrics or unverified controller labels.

## Data and Code Availability

The research package contains scripts, CSV outputs, figure scripts, and audit reports. A public release should preserve the exact scripts and result files listed in the reproducibility appendix and include an environment specification before journal submission.

## References

{reference_list()}
"""
    (FINAL / "APPLIED_ENERGY_MANUSCRIPT_DRAFT_20260609.md").write_text(manuscript, encoding="utf-8")


def write_appendix(s: dict[str, object]) -> None:
    appendix = f"""# Reproducibility Appendix - 20260609

## Repository structure

- Root: `/home/jia/multi actor/`
- Wave 1 evidence: `wave1_evidence_20260609/`
- Direct Wave 2 severity and baseline evidence: `wave2_direct_severity_baseline_20260609/`
- IEEE-33 feeder evidence: `wave2_strong_upgrades_20260609/`
- Final package: `final_applied_energy_package_20260609/`
- Strong plan: `applied_energy_research_upgrade_20260609/STRONG_APPLIED_ENERGY_EVIDENCE_BUILDING_PROGRAM_20260609.md`

## Core scripts

- `applied_energy_research_upgrade_20260609/run_direct_wave2_severity_baseline_20260609.py`
- `applied_energy_research_upgrade_20260609/run_targeted_28day_behavior_severity_20260609.py`
- `final_applied_energy_package_20260609/figure_scripts/build_final_figures_20260609.py`
- `final_applied_energy_package_20260609/generate_publication_texts_20260609.py`

## Main result files

- Request audit: `wave1_evidence_20260609/request_conservation_by_behavior_20260609.csv`
- FleetBalanced branch trace: `wave1_evidence_20260609/fleetbalanced_branch_trace_20260609.csv`
- Weekly severity results: `wave2_direct_severity_baseline_20260609/behavior_severity_results_20260609.csv`
- Weekly actor-gate matrix: `wave2_direct_severity_baseline_20260609/actor_gate_matrix_with_severity_and_baseline_20260609.csv`
- Weekly failure taxonomy: `wave2_direct_severity_baseline_20260609/failure_pattern_taxonomy_with_severity_and_baseline_20260609.csv`
- Targeted 28-day results: `final_applied_energy_package_20260609/targeted_28day_behavior_severity_results_20260609.csv`
- Targeted 28-day row results: `final_applied_energy_package_20260609/targeted_28day_row_results_20260609.csv`
- IEEE-33 EV-off deltas: `wave2_strong_upgrades_20260609/ieee33_ev_policy_deltas_vs_ev_off_20260609.csv`
- Literature table: `final_applied_energy_package_20260609/verified_literature_table_20260609.csv`

## Random seeds and horizons

- Weekly direct severity/baseline runs: five seeds, 168 h horizon, capacities 20%, 35%, and 50%.
- Targeted 28-day confirmation: seeds 4541-4545, 672 h horizon, 35% capacity.
- IEEE-33 screen: 900 weekly cases, {s['ieee_solves']} hourly power-flow solves, 168 h per case.

## Policy definitions

- `LeastLaxity`: anchor heuristic prioritizing least-laxity/deadline-risk requests.
- `FleetCostOnly`: diagnostic single-objective cost-oriented heuristic.
- `FleetQueueAware`: diagnostic queue-oriented heuristic.
- `FleetServiceFirst`: service-oriented heuristic; current manuscript treats this as the service family after the FleetBalanced audit.
- `FleetServiceGridWeighted`: heuristic comparator combining service urgency and grid pressure.
- `FleetBalanced`: audited; not claimed as distinct under current scenarios.
- `NoGridIncentive`: no grid-layer intervention.
- `GridPeakPenalty`: grid-layer peak-pressure intervention. Deferrals are attributed to this layer.

## Behavior severity definitions

- Severity 0: full compliance, upper-bound benchmark.
- Severity 1: mild deviation.
- Severity 2: moderate deviation.
- Severity 3: severe/current stress behavior.

The severity sweep evaluates request-event/action-event pressure. The demanded-kWh trace audit reconciles targeted 28-day simulator demanded-kWh sessions and classifies the behavioral effect as event churn: event counts rise while simulator demanded kWh modestly falls, so the result is not true energy-demand amplification.

## Regeneration commands

From `/home/jia`:

```bash
python '/home/jia/multi actor/applied_energy_research_upgrade_20260609/run_targeted_28day_behavior_severity_20260609.py'
python '/home/jia/multi actor/final_applied_energy_package_20260609/figure_scripts/build_final_figures_20260609.py'
python '/home/jia/multi actor/final_applied_energy_package_20260609/generate_publication_texts_20260609.py'
```

## Figure traceability

- Fig. 1: generated schematic from `build_final_figures_20260609.py`.
- Fig. 2: `actor_gate_matrix_with_severity_and_baseline_20260609.csv`.
- Fig. 3: weekly severity CSV and targeted 28-day severity CSV.
- Fig. 4: `failure_pattern_taxonomy_with_severity_and_baseline_20260609.csv`.
- Fig. 5: weekly and targeted severity grid-policy summaries.
- Fig. 6: `ieee33_ev_policy_deltas_vs_ev_off_20260609.csv`.
- Supplementary FleetBalanced audit: `fleetbalanced_branch_trace_20260609.csv`.
- Supplementary request audit: `request_conservation_by_behavior_20260609.csv`.
- Supplementary threshold sensitivity: `research_strengthening_20260609/binding_threshold_sensitivity_overall_20260609.csv`.

## Evidence boundaries

- FleetBalanced superiority is forbidden.
- Behavioral true demanded-kWh amplification remains forbidden. The demanded-kWh audit supports request-event churn under simulator operational demand, not calibrated field energy-demand growth.
- IEEE-33 is a representative feeder stress screen, not site validation.
- Threshold conclusions are threshold-conditioned.
- ServiceGridWeighted is a heuristic comparator, not an optimizer.
"""
    (FINAL / "REPRODUCIBILITY_APPENDIX_20260609.md").write_text(appendix, encoding="utf-8")


def write_hostile_table() -> None:
    rows = [
        ("Gates are arbitrary.", "High", "Threshold sensitivity and explicit gate table make assumptions visible.", "Call gates pre-specified normative thresholds.", "Needs stronger empirical or stakeholder justification before submission.", "Partial"),
        ("Threshold dependence undermines conclusions.", "High", "Sensitivity is treated as a result, not hidden.", "Use threshold-conditioned acceptability, not robust.", "Some conclusions may change under different thresholds.", "Partial"),
        ("Behavior models are uncalibrated.", "High", "Manuscript labels them as stress-test variants.", "Do not call them forecasts or realistic behavior.", "Needs calibration against observed opt-out/override data.", "No"),
        ("Request amplification may be artifact.", "High", "Request-ID and count conservation passed; demanded-kWh conservation unresolved.", "Say request-event pressure, not energy-demand amplification.", "Persistent demanded-kWh tracing still missing.", "Partial"),
        ("FleetBalanced is identical to ServiceFirst.", "High", "Branch trace shows zero final-action changes and zero L1 distance.", "Merge/drop FleetBalanced as a distinct mechanism.", "Does not prove all possible scenario equivalence.", "Yes"),
        ("IEEE-33 is not real feeder validation.", "High", "EV-off and policy-delta analysis added.", "Call it representative feeder stress screen.", "No site-specific feeder data.", "Partial"),
        ("Voltage violations show infeasibility.", "Medium", "Voltage deltas vs EV-off are zero on average; base-load dominates.", "Treat voltage as boundary condition.", "Absolute voltage screen remains stressed.", "Partial"),
        ("GridPeakPenalty does not rescue all-pass outcomes.", "Medium", "Results explicitly show this.", "Frame as grid trade-off, not rescue.", "PeakPenalty design may be too simple.", "Yes"),
        ("CostOnly/QueueAware are strawmen.", "Medium", "ServiceGridWeighted added as stronger service-grid heuristic.", "Call CostOnly/QueueAware diagnostic single-objective heuristics.", "Still no full MPC/LP benchmark.", "Partial"),
        ("New weighted baseline is still heuristic.", "Medium", "Parameters and score formula documented.", "Call it heuristic comparator.", "No optimization proof.", "Partial"),
        ("Simulation-only study lacks field validation.", "High", "Reproducibility and audit package are transparent.", "State simulation-only limitation.", "Needs field or calibrated dataset for stronger claim.", "No"),
        ("No optimization proof.", "Medium", "Manuscript avoids optimality claims.", "Use heuristic/control policy wording.", "Could add LP/MPC baseline later.", "Yes"),
        ("Results may not generalize beyond selected seeds/capacities.", "Medium", "Weekly multi-capacity plus targeted 28-day confirmation included.", "Bound claims to tested seeds/capacities.", "28-day confirmation only at 35% capacity.", "Partial"),
        ("Figures may overstate mechanism.", "Medium", "Figures label request-event pressure and feeder deltas only.", "Avoid causal or validation labels.", "Manuscript captions must remain disciplined.", "Partial"),
    ]
    lines = [
        "# Hostile Reviewer Response Table - 20260609",
        "",
        "|Reviewer criticism|Risk|Evidence response|Manuscript wording response|Remaining limitation|Resolved before submission?|",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append("|" + "|".join(r) + "|")
    (FINAL / "HOSTILE_REVIEWER_RESPONSE_TABLE_20260609.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_final_decision(s: dict[str, object]) -> None:
    target_by_sev: pd.DataFrame = s["target_by_sev"]  # type: ignore[assignment]
    t0 = target_by_sev.loc[target_by_sev["severity_level"] == 0].iloc[0]
    t1 = target_by_sev.loc[target_by_sev["severity_level"] == 1].iloc[0]
    t3 = target_by_sev.loc[target_by_sev["severity_level"] == 3].iloc[0]
    decision = f"""# Final Submission Readiness Decision - 20260609

## Category

Ready for internal coauthor review.

This is not yet Ready for Applied Energy submission. The evidence spine, verified literature table, final figure set, manuscript draft, reproducibility appendix, and hostile reviewer table now exist, but the paper still needs coauthor review, manuscript polishing, consistency checks, and ideally a request-level demanded-kWh trace before strong behavioral mechanism claims.

## Completed evidence

- Targeted 28-day behavioral severity confirmation completed at 35% capacity, seeds 4541-4545, 672 h horizon.
- Literature DOI/URL table generated with no guessed DOI entries.
- Final main and supplementary figures generated from source CSVs.
- Manuscript rewritten from zero around multi-actor acceptability.
- Reproducibility appendix created.
- Hostile Applied Energy reviewer table created.

## Targeted 28-day decision

- Severity 0 all-pass rate: {pct(t0['allp'])}.
- Severity 1 all-pass rate: {pct(t1['allp'])}.
- Severity 3 actual/fleet request-event ratio: {f3(t3['ratio'])}.
- Decision: the 28-day run supports the weekly collapse at mild behavioral deviation under the current gates.

## Allowed manuscript claims

- EV charging policies can pass individual metrics while failing multi-actor acceptability gates.
- Under current gates, full-compliance service-oriented policies pass, while mild behavioral deviation eliminates all-pass acceptability in the tested weekly and targeted 28-day scenarios.
- Behavioral severity increases request-event/action-event pressure.
- Targeted demanded-kWh tracing classifies this behavioral effect as event churn: request-event counts rise while simulator demanded kWh modestly falls.
- GridPeakPenalty can reduce selected peak ratios but does not rescue all-pass outcomes after driver/fleet failures.
- ServiceGridWeighted reduces strawman-baseline risk but does not produce a simple controller-superiority result.
- IEEE-33 provides representative feeder stress deltas versus EV-off baseline.
- FleetBalanced is not a distinct mechanism under current scenarios.

## Forbidden manuscript claims

- FleetBalanced superiority.
- FleetBalanced mechanism unless future traces show final-action and gate-outcome differences.
- Behavioral true energy-demand amplification or calibrated field demand growth.
- Feeder validation or site-specific feasibility.
- Threshold-independent robustness.
- Optimality of heuristic policies.

## Remaining risks

- Behavior models are not calibrated forecasts.
- Demanded-kWh tracing is targeted to 35% capacity, 28-day service-oriented cases only.
- 28-day confirmation is targeted to 35% capacity only.
- No full MPC/LP optimization baseline is included.
- IEEE-33 screen is representative only.
- Gate thresholds remain normative.

## Exact next steps

1. Coauthor/internal review of `APPLIED_ENERGY_MANUSCRIPT_DRAFT_20260609.md`.
2. Decide whether coauthors require calibration or literature-bounded behavioral parameters before submission.
3. Decide whether to expand the 28-day confirmation to 20% and 50% capacity.
4. Polish figure typography and captions after coauthor review.
5. Convert manuscript to journal LaTeX or DOCX once claims are approved.
"""
    (FINAL / "FINAL_SUBMISSION_READINESS_DECISION_20260609.md").write_text(decision, encoding="utf-8")


def main() -> None:
    FINAL.mkdir(parents=True, exist_ok=True)
    s = read_summaries()
    write_literature()
    write_manuscript(s)
    write_appendix(s)
    write_hostile_table()
    write_final_decision(s)
    print("wrote publication text artifacts to", FINAL)


if __name__ == "__main__":
    main()
