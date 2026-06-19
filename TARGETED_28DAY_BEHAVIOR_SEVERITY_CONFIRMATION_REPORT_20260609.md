# Targeted 28-Day Behavior Severity Confirmation Report

Rows: `85` total, `80` explicit policy rows.
Horizon hours: `672`.
Seeds: `[4541, 4542, 4543, 4544, 4545]`.
Capacities: `[35]`.

This is a targeted confirmation, not a full rerun of every policy family.

## Overall severity results

| severity | rows | driver | fleet | grid | all | actual/fleet events | delivered ratio | reliability delta pp | peak ratio | grid deferrals |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 `full_compliance` | 20 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.000 | 0.000 | 0.930 | 10.8 |
| 1 `mild_deviation` | 20 | 0.00 | 0.00 | 0.00 | 0.00 | 1.15 | 0.985 | -0.322 | 0.944 | 10.7 |
| 2 `moderate_deviation` | 20 | 0.00 | 0.00 | 0.00 | 0.00 | 1.63 | 0.954 | -0.688 | 0.956 | 10.7 |
| 3 `severe_deviation` | 20 | 0.00 | 0.00 | 0.00 | 0.00 | 2.57 | 0.936 | -0.394 | 0.979 | 10.2 |

## Grid-policy comparison

| severity | grid policy | rows | driver | fleet | grid | all | peak ratio | grid deferrals |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | `GridPeakPenalty` | 10 | 1.00 | 1.00 | 1.00 | 1.00 | 0.860 | 21.6 |
| 0 | `NoGridIncentive` | 10 | 1.00 | 1.00 | 1.00 | 1.00 | 1.000 | 0.0 |
| 1 | `GridPeakPenalty` | 10 | 0.00 | 0.00 | 0.00 | 0.00 | 0.889 | 21.4 |
| 1 | `NoGridIncentive` | 10 | 0.00 | 0.00 | 0.00 | 0.00 | 1.000 | 0.0 |
| 2 | `GridPeakPenalty` | 10 | 0.00 | 0.00 | 0.00 | 0.00 | 0.913 | 21.3 |
| 2 | `NoGridIncentive` | 10 | 0.00 | 0.00 | 0.00 | 0.00 | 1.000 | 0.0 |
| 3 | `GridPeakPenalty` | 10 | 0.00 | 0.00 | 0.00 | 0.00 | 0.966 | 20.3 |
| 3 | `NoGridIncentive` | 10 | 0.00 | 0.00 | 0.00 | 0.00 | 0.993 | 0.0 |

## Fleet-policy comparison

| severity | fleet policy | rows | driver | fleet | grid | all | peak ratio | actual/fleet events |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | `FleetServiceFirst` | 10 | 1.00 | 1.00 | 1.00 | 1.00 | 0.930 | 1.00 |
| 0 | `FleetServiceGridWeighted` | 10 | 1.00 | 1.00 | 1.00 | 1.00 | 0.930 | 1.00 |
| 1 | `FleetServiceFirst` | 10 | 0.00 | 0.00 | 0.00 | 0.00 | 0.941 | 1.15 |
| 1 | `FleetServiceGridWeighted` | 10 | 0.00 | 0.00 | 0.00 | 0.00 | 0.948 | 1.14 |
| 2 | `FleetServiceFirst` | 10 | 0.00 | 0.00 | 0.00 | 0.00 | 0.955 | 1.62 |
| 2 | `FleetServiceGridWeighted` | 10 | 0.00 | 0.00 | 0.00 | 0.00 | 0.958 | 1.63 |
| 3 | `FleetServiceFirst` | 10 | 0.00 | 0.00 | 0.00 | 0.00 | 0.969 | 2.56 |
| 3 | `FleetServiceGridWeighted` | 10 | 0.00 | 0.00 | 0.00 | 0.00 | 0.990 | 2.57 |

## Failure patterns

| pattern | rows |
| --- | ---: |
| `driver_fleet_grid_fail` | 60 |
| `all_pass` | 20 |

## Required answers

1. Weekly collapse confirmed over 28 days: `True`. Severity 0 passes all tested service-oriented rows; severity 1 eliminates all-pass acceptability under the current gates.
2. Request-event ratio increases smoothly with severity: `True`.
3. First failed actor gate: driver and fleet gates bind at severity 1 in all tested fleet/grid groups; grid also binds at severity 1 in most groups. See targeted monotonicity CSV.
4. GridPeakPenalty rescues any all-pass outcome after severity 0: `False`.
5. FleetServiceGridWeighted improves resilience relative to ServiceFirst by mean all-pass-rate difference `0.000` across severity/group summaries; this is not a superiority claim.
6. Manuscript placement: main text if behavior severity is a central result; otherwise use as a supplementary confirmation supporting the weekly figure.

## Allowed manuscript wording

Weekly severity results were supported by a targeted 28-day confirmation: under the current actor-gate thresholds, mild behavioral deviation was sufficient to eliminate all-pass acceptability in the tested service-oriented policies.

## Forbidden wording

Do not say behavior increases true energy demand. Persistent request-level demanded kWh is still not saved and reconciled.
