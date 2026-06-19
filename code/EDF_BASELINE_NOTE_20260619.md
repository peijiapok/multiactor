# EDF recognized-baseline result (R3#2) — 2026-06-19
run_edf_baseline_20260619.py, 35% cap, both grids, 5 seeds, EDF (earliest-deadline-first) fleet scheduler.
all-pass vs deviation: d=0:0.200, d=0.0125:0.200, d=0.025:0.000, d=0.05:0.000.
=> EDF collapses by ~2.5% deviation, SAME threshold as LeastLaxity-based ServiceFirst.
KEY: scheduler quality sets the FULL-COMPLIANCE LEVEL (ServiceFirst 0.967 vs EDF 0.20),
behavioral compliance sets the THRESHOLD. The compliance cliff is scheduler-agnostic.
