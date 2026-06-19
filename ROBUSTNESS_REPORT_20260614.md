# Acceptability-definition robustness report — 20260614

Directly answers the fatal reviewer objection (Claude + GPT-5.5): *is the severity-1
all-pass collapse a near-tautology engineered by ANDing 14 fragile hand-thresholded gates?*

Re-analysis of the saved per-episode results (`direct_wave2_row_results_20260609.csv`),
service-oriented family, **n = 60 episodes per severity** (5 seeds × 3 capacities × 2 grid
policies × 2 service fleet policies). No new simulation.

## Q1 — Which sub-criteria actually bind at severity 1? (decomposition)

| criterion (rule) | fail frac sev0 | fail frac sev1 |
|---|---:|---:|
| D3 critical requested-not-delivered delta (≤24) | 0.00 | **0.93** |
| F4 p95 wait delta (≤30 min) | 0.00 | **0.82** |
| G4 squared-load-proxy ratio (≤1.10) | 0.00 | **0.52** |
| G2 ramp ratio (≤1.10) | 0.00 | **0.27** |
| D2 reliability delta (≥−0.5 pp) | 0.00 | 0.17 |
| G1 peak ratio (≤1.05) | 0.00 | 0.02 |
| other 8 criteria | 0.00 | 0.00 |

**Finding:** the collapse is **broad-based**, driven by **4–5 distinct criteria spanning all
three actors** (driver D3, fleet F4, grid G4/G2) — not a single intentionally-tight gate.
This refutes the "one engineered threshold did it" objection. **Correction to the prior
draft:** the binding criteria are critical-requests-not-delivered, wait time, and load-shape —
NOT the reliability-delta gate the draft emphasized (which fails only 17%). The earlier claim
"the binding gate is the driver gate" is an oversimplification and is corrected: the driver
gate fails hardest (D3), but fleet and grid gates also bind substantially.

## Q2 — Does the collapse survive softer aggregation? (tautology test)

| severity | strict 3-actor AND | ≥2 of 3 actors | ≥1 of 3 actors | driver only | fleet only | grid only | mean frac of 14 passed |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1 | 0.00 | 0.08 | 0.52 | 0.03 | 0.18 | 0.38 | **0.81** |
| 2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.60 |
| 3 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.56 |

**Finding (defends):** the degradation is visible even WITHOUT the strict AND — a single
driver gate alone falls to 3%, and "≥1 of 3 actors fully passes" falls to 52% at severity 1.
So it is not purely an aggregation artifact.

**Finding (honest concession):** the strict 14-way AND DOES dramatize the effect — on average
**81% of the 14 criteria still pass at severity 1**, yet strict all-pass = 0%. The graded
"fraction of criteria passed" tells a milder, monotonic story (1.00 → 0.81 → 0.60 → 0.56). The
manuscript must report BOTH the binary all-pass and this graded view, and must not present the
binary 100%→0% cliff as the whole story.

## Q3 — Uncertainty (bootstrap 95% CI, 10k resamples)

| severity | all-pass mean [95% CI] | driver-gate mean [95% CI] |
|---:|---|---|
| 0 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| 1 | 0.000 [0.000, 0.000] | 0.033 [0.000, 0.083] |
| 2 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| 3 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |

The severity-0→1 all-pass transition is outside overlapping CIs.

## Net verdict for the revision
The honest, defensible claim is now:
> Behavioral deviation degrades acceptability across **multiple independent criteria spanning
> all three actors simultaneously**; the strict same-episode conjunction makes this visible as
> an all-pass collapse, while a graded fraction-of-criteria index shows the same monotonic
> degradation more conservatively. The effect is therefore not an artifact of a single tight
> threshold nor purely of the AND aggregation.

This reframes the contribution away from a possibly-tautological binary cliff toward a
multi-criterion degradation finding with both strict and graded reporting — which is what both
reviewers asked for.

## Q4 — Robustness ENVELOPE over the acceptability definition (added 20260615)

Responds to the GPT-5.5 re-review's top ask: vary cut-points AND aggregation systematically.

**E1 — global threshold-slack scaling (all 14 gate margins scaled together):**

| slack | all-pass sev0 | all-pass sev1 | graded sev1 | ≥1 actor sev1 |
|---:|---:|---:|---:|---:|
| 0.50 (tighter) | 0.967 | 0.000 | 0.733 | 0.300 |
| 1.00 (nominal) | 1.000 | 0.000 | 0.806 | 0.517 |
| 1.50 | 1.000 | 0.083 | 0.865 | 0.783 |
| 2.00 | 1.000 | 0.433 | 0.951 | 1.000 |
| 3.00 (looser) | 1.000 | 0.917 | 0.994 | 1.000 |

Full compliance stays acceptable at nominal-or-looser; the severity-1 collapse persists until
the entire gate system is loosened 2–3×. Degradation indices move smoothly with slack.

**E2 — loosen ONE criterion to 3× margin (others fixed):** severity-1 strict all-pass recovers
to **at most 0.033** for every single criterion → no individual cut-point is responsible.

**Verdict:** the multi-actor degradation pattern is **stable across a wide envelope of plausible
acceptability definitions** and is not rescued by relaxing any one threshold. Files:
`envelope_e1_global_scaling_20260615.csv`, `envelope_e2_oneatatime_20260615.csv`.
