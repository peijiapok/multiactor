# New analyses for the reviewer response (2026-06-19)

## M3 — preference-form ablation (NEW RUN)
`run_preference_ablation_20260619.py` -> `preference_ablation_summary_20260619.csv`
Severity-1 (5% low-slack deviation), 35% cap, ServiceFirst, both grids, 5 seeds.
8 preference-coefficient variants (base / equal / plus50 / minus50 / reordered / no_reserve /
soc_heavy / flat_urgent). RESULT: all-pass_sev1 = 0.000 for EVERY variant (max = 0.000).
=> collapse depends on deviation prevalence/placement, not on the preference-function form.

## m9 — alternative-normalization PoA (NEW ANALYSIS, on existing surface)
Ratio-to-full-compliance normalization vs min-max:
  cap20: 1.514 vs 1.482 | cap35: 1.502 vs 1.458 | cap50: 1.560 vs 1.476
=> PoA ~1.5 robust to normalization choice.

## Q1 — threshold-relaxation margin (from envelope_e1)
Severity-1 all-pass vs global gate-slack: 1.0x=0.00, 1.25x=0.033, 1.5x=0.083, 2.0x=0.433, 3.0x=0.917.
=> recovering >50% all-pass needs ALL gates loosened >~2x; single/few-gate relaxation <=0.054.

## M4 — LeastLaxity absolute performance (from response surface, d=0)
reliability 93.6%, p95 wait ~0 min, delivered_ratio (anchor)=1.0 => strong anchor, not a low bar.

All integrated into manuscript; response letter = RESPONSE_TO_REVIEWER_20260619.md.
Manuscript compiles 45pp, 0 undefined, 0 multidef.
