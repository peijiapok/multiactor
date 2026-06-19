# Option A: Slack-Structured Deviation Robustness Report

Date: 20260615. Runtime: 142.3s (2.4 min).

Command: `python3 "/home/jia/multi actor/optionA_slack_deviation_20260615/run_optionA_slack_deviation_20260615.py"`

## Question

Is the EV-charging severity-1 all-pass collapse an artifact of UNIFORM random deviation, or does it persist when the SAME ~5% deviation is REALISTICALLY STRUCTURED toward low-slack (low-laxity / inflexible) sessions, as seen in the OptimizEV pilot (opt-out concentrates in low-flexibility sessions)?

## Method (engine read-only; monkeypatch of the driver keep/deviate draw)

The driver layer's deviation draw `keep = rng.random(n_cars) < p` (p = keep probability, uniform 0.95 at severity 1) is replaced by a STRUCTURED per-vehicle draw `keep_i = rng.random() >= p_dev_i`, where p_dev_i is built from the deadline-laxity slack proxy `pkg._arrays(env, obs)['laxity']` (LOW laxity = inflexible = low slack). The non-compliant self-service preference rule, fleet/grid policies, actor gates, and weekly horizon are IDENTICAL to the proven direct-extension path. No engine or /home/jia/thirftydeath/ file is modified.

### Deviation structures (all population-mean p_dev ~= 0.05, severity-1-matched)

- `uniform` (baseline): `p_dev_i = 0.05` (the existing severity-1 draw).
- `low_slack_concentrated` (realistic, main test): `p_dev_i = clip(k*(1 - laxity_i), 0, 1)`, `k = 0.05 / mean(1 - laxity)` per step.
- `high_slack_concentrated` (anti-realistic contrast): `p_dev_i = clip(k*laxity_i, 0, 1)`, `k = 0.05 / mean(laxity)` per step.

k is recomputed PER STEP from that step's laxity vector so the population-mean deviation probability stays ~0.05. Severity 0 (full compliance) is structure-independent (no vehicle deviates) and is run once as the shared reference.

Sweep: severity {0,1}, capacity 35%, grids {NoGridIncentive, GridPeakPenalty}, fleets {ServiceFirst, ServiceGridWeighted}, seeds [4541, 4542, 4543, 4544, 4545]. Weekly horizon EPISODE_HOURS=168. Episodes per (structure, severity-1): 20 (= 5 seeds x 2 fleets x 2 grids).

## k-normalization audit (realized population-mean deviation probability)

| structure | mean p_dev | min | max | steps |
| --- | ---: | ---: | ---: | ---: |
| `uniform` | 0.0500 | 0.0500 | 0.0500 | 3360 |
| `low_slack_concentrated` | 0.0494 | 0.0125 | 0.0500 | 3360 |
| `high_slack_concentrated` | 0.0500 | 0.0500 | 0.0500 | 3360 |

## All-pass rate by (deviation_structure x severity)

| deviation_structure | severity | n | driver | fleet | grid | all_pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `reference` (reference) | 0 | 20 | 1.000 | 1.000 | 1.000 | 1.000 |
| `uniform` | 1 | 20 | 0.000 | 0.050 | 0.250 | 0.000 |
| `low_slack_concentrated` | 1 | 20 | 0.000 | 0.050 | 0.050 | 0.000 |
| `high_slack_concentrated` | 1 | 20 | 0.000 | 0.600 | 0.500 | 0.000 |

## Severity-1 all-pass head-to-head

| structure | severity-1 all-pass | collapsed (<=0.001)? |
| --- | ---: | :---: |
| `uniform` (baseline) | 0.000 | True |
| `low_slack_concentrated` (realistic) | 0.000 | True |
| `high_slack_concentrated` (contrast) | 0.000 | True |

- Severity-0 reference all-pass (full compliance): **1.000**

## VERDICT: PERSISTS. The severity-1 all-pass collapse holds under realistic low-slack-concentrated deviation (all-pass = 0.000), identical to uniform (0.000); high-slack-concentrated = 0.000. Concentrating the SAME ~5% deviation in low-laxity (inflexible) sessions does NOT rescue acceptability -- the collapse is NOT an artifact of uniform random deviation.

