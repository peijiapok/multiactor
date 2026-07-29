#!/usr/bin/env python3
"""Produce 20-seed aggregated CSVs in the schemas the figure script expects,
so Figures 2 and 3 reflect the 20-seed expansion (service-oriented family)."""
from pathlib import Path
import pandas as pd

OUT = Path("/home/jia/multi actor/seed20_expansion_20260615")
df = pd.read_csv(OUT / "seed20_row_results_20260615.csv")
df = df[df["fleet_policy"].isin(["FleetServiceFirst", "FleetServiceGridWeighted"])].copy()
df = df[df["severity_level"].isin([0, 1, 2, 3])].copy()
df["severity_level"] = df["severity_level"].astype(int)
if "severity_label" not in df:
    df["severity_label"] = df["severity_level"].map({0: "full_compliance", 1: "mild_deviation", 2: "moderate_deviation", 3: "severe_deviation"})
df["actual_to_fleet_request_ratio"] = (
    df["actual_request_count_driver_layer"] / df["fleet_recommended_request_count"].replace(0, pd.NA)
)

# 1) actor_gate_matrix-style (grouped by severity x fleet x grid x cap)
grp = ["severity_level", "severity_label", "fleet_policy", "grid_policy", "capacity_pct"]
mat = df.groupby(grp, as_index=False).agg(
    driver_pass_rate=("driver_service_pass", "mean"),
    fleet_pass_rate=("fleet_operation_pass", "mean"),
    grid_pass_rate=("grid_pass", "mean"),
    all_pass_rate=("all_pass", "mean"),
    actual_to_fleet_request_ratio_mean=("actual_to_fleet_request_ratio", "mean"),
)
mat.to_csv(OUT / "seed20_actor_gate_matrix_20260615.csv", index=False)

# 2) behavior_severity_results-style (per severity x fleet x grid x cap row;
#    fig3 regroups by severity_level mean). Reuse the same grouped frame.
mat.to_csv(OUT / "seed20_behavior_severity_results_20260615.csv", index=False)

print("wrote seed20 aggregates; severity means (service family, all caps+grid):")
print(df.groupby("severity_level")[["driver_service_pass", "fleet_operation_pass", "grid_pass", "all_pass"]].mean().round(3).to_string())
