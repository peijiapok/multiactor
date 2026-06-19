# Coefficient Sensitivity Ablation Report

Date: 20260614. Runtime: 342.9s.

Sweep: capacity=35%, severity {0,1}, grids {NoGridIncentive, GridPeakPenalty}, fleets {ServiceFirst (ref), ServiceGridWeighted (ablated)}, seeds [4541, 4542, 4543, 4544, 4545]. Weekly horizon (EPISODE_HOURS=168).

## All-pass rate by (variant x severity) — ablated fleet ServiceGridWeighted, mean over grid policies

| variant | severity 0 (full) | severity 1 (mild) |
| --- | ---: | ---: |
| `base` | 1.000 | 0.000 |
| `normalized` | 1.000 | 0.000 |
| `equal_service` | 1.000 | 0.000 |
| `no_grid_penalty` | 1.000 | 0.000 |
| `perturb_+25%` | 1.000 | 0.000 |
| `perturb_-25%` | 1.000 | 0.000 |

## Decision-identity check (variant 2 normalized vs base)

- Per-episode all_pass identical (base vs normalized, same seed/severity/grid): **True**

## Full per-(variant, severity, grid) summary

| variant | severity | grid | n | driver | fleet | grid | all_pass |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| `base` | 0 | `GridPeakPenalty` | 5 | 1.00 | 1.00 | 1.00 | 1.000 |
| `base` | 1 | `GridPeakPenalty` | 5 | 0.00 | 0.60 | 0.20 | 0.000 |
| `base` | 0 | `NoGridIncentive` | 5 | 1.00 | 1.00 | 1.00 | 1.000 |
| `base` | 1 | `NoGridIncentive` | 5 | 0.00 | 0.00 | 0.00 | 0.000 |
| `normalized` | 0 | `GridPeakPenalty` | 5 | 1.00 | 1.00 | 1.00 | 1.000 |
| `normalized` | 1 | `GridPeakPenalty` | 5 | 0.00 | 0.60 | 0.20 | 0.000 |
| `normalized` | 0 | `NoGridIncentive` | 5 | 1.00 | 1.00 | 1.00 | 1.000 |
| `normalized` | 1 | `NoGridIncentive` | 5 | 0.00 | 0.00 | 0.00 | 0.000 |
| `equal_service` | 0 | `GridPeakPenalty` | 5 | 1.00 | 1.00 | 1.00 | 1.000 |
| `equal_service` | 1 | `GridPeakPenalty` | 5 | 0.00 | 0.60 | 0.20 | 0.000 |
| `equal_service` | 0 | `NoGridIncentive` | 5 | 1.00 | 1.00 | 1.00 | 1.000 |
| `equal_service` | 1 | `NoGridIncentive` | 5 | 0.00 | 0.00 | 0.00 | 0.000 |
| `no_grid_penalty` | 0 | `GridPeakPenalty` | 5 | 1.00 | 1.00 | 1.00 | 1.000 |
| `no_grid_penalty` | 1 | `GridPeakPenalty` | 5 | 0.00 | 0.60 | 0.20 | 0.000 |
| `no_grid_penalty` | 0 | `NoGridIncentive` | 5 | 1.00 | 1.00 | 1.00 | 1.000 |
| `no_grid_penalty` | 1 | `NoGridIncentive` | 5 | 0.00 | 0.00 | 0.00 | 0.000 |
| `perturb_+25%` | 0 | `GridPeakPenalty` | 5 | 1.00 | 1.00 | 1.00 | 1.000 |
| `perturb_+25%` | 1 | `GridPeakPenalty` | 5 | 0.00 | 0.60 | 0.20 | 0.000 |
| `perturb_+25%` | 0 | `NoGridIncentive` | 5 | 1.00 | 1.00 | 1.00 | 1.000 |
| `perturb_+25%` | 1 | `NoGridIncentive` | 5 | 0.00 | 0.00 | 0.00 | 0.000 |
| `perturb_-25%` | 0 | `GridPeakPenalty` | 5 | 1.00 | 1.00 | 1.00 | 1.000 |
| `perturb_-25%` | 1 | `GridPeakPenalty` | 5 | 0.00 | 0.60 | 0.20 | 0.000 |
| `perturb_-25%` | 0 | `NoGridIncentive` | 5 | 1.00 | 1.00 | 1.00 | 1.000 |
| `perturb_-25%` | 1 | `NoGridIncentive` | 5 | 0.00 | 0.00 | 0.00 | 0.000 |

## VERDICT: ALL 6 weight variants show all-pass = 1.0 at severity 0 and all-pass = 0.0 at severity 1 -> the headline result is ROBUST to the magic-number weights. (sev0 all 1.0: True; sev1 all 0.0: True)

