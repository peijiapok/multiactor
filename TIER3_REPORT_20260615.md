# Tier-3 Demand-Distribution Robustness Report

Date: 20260615. Runtime: 228.0s (3.8 min).

Command: `python3 "/home/jia/multi actor/tier3_demand_robustness_20260615/run_tier3_demand_robustness_20260615.py"`

## Question

Is the EV-charging acceptability headline -- same-episode all-pass = 1.0 at behavior severity 0 (full compliance) and 0.0 at severity 1 (mild deviation) -- robust to the charging DEMAND distribution? We re-draw per-session ENERGY and DWELL from three independent real ACN populations (Caltech main, JPL, Office001) instead of only the combined ('acn_all') fit.

## Method (engine read-only; monkeypatch override)

Per-session energy and dwell are drawn in `env_v2.EVEnvironmentV2._generate_caltech_schedule` (env_v2.py:532,534) from four lognormal scalars loaded from `caltech_multisite_summary.json` (env_v2.py:508-509). We monkeypatch that class method with a body byte-for-byte identical to the engine's EXCEPT the four lognormal params are injected from the chosen demand source; arrival-hour and day-of-week histograms are unchanged. The 'combined' source injects the JSON's own params (identity baseline). No engine or /home/jia/thirftydeath/ file is modified.

Sweep: severity {0,1}, capacity 35%, grids {NoGridIncentive, GridPeakPenalty}, fleets {ServiceFirst, ServiceGridWeighted}, seeds [4541, 4542, 4543, 4544, 4545]. Weekly horizon EPISODE_HOURS=168. Episodes per (demand_source, severity): 20 (= 5 seeds x 2 fleets x 2 grids).

## Per-site lognormal params used (energy kwh + dwell h)

| demand_source | kwh mu | kwh sigma | dwell mu | dwell sigma | kwh median = exp(mu) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `combined` | 2.0796 | 1.0125 | 1.6994 | 0.7209 | 8.00 |
| `Caltech` | 1.7048 | 1.0664 | 1.4815 | 0.8845 | 5.50 |
| `JPL` | 2.3173 | 0.8956 | 1.8090 | 0.6648 | 10.15 |
| `Office001` | 2.4195 | 0.9134 | 1.5453 | 0.7045 | 11.24 |

## All-pass rate by (demand_source x severity)

| demand_source | severity 0 (full) | severity 1 (mild) |
| --- | ---: | ---: |
| `combined` (baseline) | 1.000 | 0.000 |
| `Caltech` | 1.000 | 0.000 |
| `JPL` | 1.000 | 0.000 |
| `Office001` | 0.900 | 0.000 |

- combined baseline reproduces the headline (sev0=1.0, sev1=0.0): **True**

## Diagnostic: the single Office001 severity-0 deviation

Office001 severity-0 all-pass is 0.900: 2 of 20 episodes fail, both on seed 4543
(FleetServiceGridWeighted, NoGridIncentive and GridPeakPenalty). Both failures are
on `grid_pass` ONLY -- `driver_service_pass` = True and `fleet_operation_pass` =
True in both. So this is a grid-shape/peak miss under Office001's highest-energy
demand (kwh median 11.24 kWh, the largest of the four sources), NOT a breakdown of
the driver-fleet service-acceptability that the headline concerns. The
severity-1 collapse to all-pass = 0.000 still reproduces across ALL four demand
distributions including Office001.

## VERDICT: DOES NOT cleanly reproduce across all real-site demand distributions. Severity-0 all-pass: Caltech=1.000, JPL=1.000, Office001=0.900. Severity-1 all-pass: Caltech=0.000, JPL=0.000, Office001=0.000. See table for exact rates.

(Qualifier: the severity-1 collapse to 0.000 is universal across all four sources.
The only deviation from the strict pattern is 2/20 Office001 severity-0 episodes
failing on grid-shape only, not on service acceptability.)

