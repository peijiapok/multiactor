# Demanded-kWh Trace Audit Report - 20260609

## Research question

Does increasing behavioral severity change traceable simulator demanded kWh, or does it primarily increase request-event churn?

## Non-claim

This is a simulator demanded-kWh ledger. It is not calibrated real-world driver demand and must not be described as true field energy-demand amplification.

## Design

- Horizon: `672` h.
- Seeds: `[4541, 4542, 4543, 4544, 4545]`.
- Capacity: `[35]`.
- Fleet policies: `['ServiceFirst', 'ServiceGridWeighted']`.
- Grid policies: `['NoGrid', 'PeakPenalty']`.
- Demand definition: `max(target_SOC deficit kWh, next-trip deadline deficit kWh)`.
- Session open rule: a vehicle session opens when demanded kWh is positive or when a request event occurs.
- Session close rule: a session closes when demanded kWh falls to zero, or is marked `unserved_at_episode_end` with remaining kWh at the horizon.
- Conservation identity per vehicle step: `remaining_pre + new_increment = delivered_to_demand + remaining_post + demand_release +/- tolerance`. Same-step created-and-served demand is counted inside `new_increment`.
- Numerical tolerance: `0.0001` kWh.

## Definitions

- `requested_kwh_initial`: demanded kWh when the session opens.
- `new_demand_increment_kwh`: increase in demanded kWh not explained by undelivered previous demand, including same-step demand that was created and served before appearing as post-step remaining demand.
- `delivered_kwh_to_demand`: delivered kWh credited to outstanding demanded kWh.
- `excess_delivered_kwh`: delivered kWh beyond the current demanded-kWh balance.
- `demand_release_kwh`: decline in demanded kWh not explained by delivered charging; this closes the conservation identity explicitly.

## Classification rule

- `event_churn`: request-event count rises by more than `5%` while simulator demanded kWh does not rise relative to severity 0. Here, event churn means more simulator-emitted request interactions without a corresponding increase in the demanded-kWh ledger.
- `demand_shift`: demanded-kWh ratio rises by more than `5%` and event ratio is not more than `1.25x` demanded-kWh ratio.
- `mixed_event_churn_and_demand_shift`: both rise, but request-event ratio dominates demanded-kWh ratio.
- `unresolved`: conservation residual exceeds tolerance or the baseline is missing.

## Audit outputs

- Request-event rows: `282368`.
- Demand-session rows: `148378`.
- Conservation rows: `4300800`.
- Classification: `event_churn`.
- Reason: aggregate request-event ratio rises to 2.349 at severity 3, while aggregate demanded-kWh ratio falls to 0.917 at severity 3. Across seeds, severity-3 event ratios range from 2.306 to 2.401 and demanded-kWh ratios range from 0.908 to 0.923.

## Severity summary

| severity | fleet | grid | request events | total demanded kWh | event ratio vs S0 | demand ratio vs S0 | unserved kWh | max residual |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | `FleetServiceFirst` | `GridPeakPenalty` | 11792 | 78797.63 | 1.000 | 1.000 | 12048.23 | 2.05994e-05 |
| 0 | `FleetServiceFirst` | `NoGridIncentive` | 11794 | 78786.91 | 1.000 | 1.000 | 12048.23 | 2.05994e-05 |
| 0 | `FleetServiceGridWeighted` | `GridPeakPenalty` | 11790 | 78797.63 | 1.000 | 1.000 | 12060.83 | 2.05994e-05 |
| 0 | `FleetServiceGridWeighted` | `NoGridIncentive` | 11792 | 78786.91 | 1.000 | 1.000 | 12060.83 | 2.05994e-05 |
| 1 | `FleetServiceFirst` | `GridPeakPenalty` | 13217 | 77213.97 | 1.121 | 0.980 | 12199.41 | 2.28882e-05 |
| 1 | `FleetServiceFirst` | `NoGridIncentive` | 13177 | 76918.73 | 1.117 | 0.976 | 11995.11 | 2.21252e-05 |
| 1 | `FleetServiceGridWeighted` | `GridPeakPenalty` | 13183 | 76814.62 | 1.118 | 0.975 | 11966.61 | 1.78337e-05 |
| 1 | `FleetServiceGridWeighted` | `NoGridIncentive` | 13125 | 77010.13 | 1.113 | 0.977 | 12149.87 | 2.13623e-05 |
| 2 | `FleetServiceFirst` | `GridPeakPenalty` | 18110 | 74239.43 | 1.536 | 0.942 | 12206.06 | 1.83105e-05 |
| 2 | `FleetServiceFirst` | `NoGridIncentive` | 17915 | 74036.33 | 1.519 | 0.940 | 12025.28 | 2.05994e-05 |
| 2 | `FleetServiceGridWeighted` | `GridPeakPenalty` | 17888 | 74250.05 | 1.517 | 0.942 | 12099.76 | 1.70708e-05 |
| 2 | `FleetServiceGridWeighted` | `NoGridIncentive` | 17794 | 74097.81 | 1.509 | 0.940 | 12063.52 | 1.90735e-05 |
| 3 | `FleetServiceFirst` | `GridPeakPenalty` | 27816 | 72458.07 | 2.359 | 0.920 | 12128.85 | 1.98364e-05 |
| 3 | `FleetServiceFirst` | `NoGridIncentive` | 27644 | 72102.28 | 2.344 | 0.915 | 12102.73 | 1.67847e-05 |
| 3 | `FleetServiceGridWeighted` | `GridPeakPenalty` | 27603 | 72131.36 | 2.341 | 0.915 | 12051.76 | 1.98364e-05 |
| 3 | `FleetServiceGridWeighted` | `NoGridIncentive` | 27728 | 72190.85 | 2.351 | 0.916 | 12071.05 | 1.83105e-05 |

## Seed-spread check

| severity | event ratio mean | event ratio range | demanded-kWh ratio mean | demanded-kWh ratio range |
|---:|---:|---:|---:|---:|
| 0 | 1.000 | 1.000-1.000 | 1.000 | 1.000-1.000 |
| 1 | 1.118 | 1.113-1.121 | 0.977 | 0.975-0.981 |
| 2 | 1.521 | 1.508-1.538 | 0.941 | 0.937-0.945 |
| 3 | 2.352 | 2.306-2.401 | 0.916 | 0.908-0.923 |
## Manuscript implication

Allowed wording: under the audited envelope, behavioral severity increases simulator-emitted request-event counts while simulator demanded kWh modestly falls; this is event churn, not evidence of true or field-calibrated energy-demand growth.

Forbidden wording remains: behavior models are calibrated forecasts or field-observed true energy-demand amplification.
