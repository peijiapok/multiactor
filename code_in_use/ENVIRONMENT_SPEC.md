# Environment & Package Specification

Human-readable extraction of the simulation environment, scenario, calibration data, and experiment
design behind the manuscript. **Every value is transcribed from the packaged code (file:line cited)
and cross-checked against the frozen primary dataset** `../results_data/seed20_row_results_20260615.csv`.
The code and the frozen CSV are authoritative; this document restates them.

> **Read Section 0 first.** The base dataclasses (`EnvV2Config`, `QueueEnvConfig`) carry library
> *defaults* that are **not** what the primary experiment ran. The primary run overrides them in
> `run_behavior_applied_energy_package_v1.py` (`N_CARS`, `EPISODE_HOURS`, `max_queue_wait_steps`,
> port power, per-scenario tariff). Where a default and the primary value differ, the **primary
> value governs the manuscript.**

---

## 0. Primary run configuration (the frozen CSV)

`seed20_row_results_20260615.csv` — the primary evidence — was produced by
`analysis/seed20_producer/run_seed20_severity_20260615.py` calling the engine `run_matrix`, with the
environment built by `run_behavior_applied_energy_package_v1.run_config` (`pkg`).

| Quantity | Primary value | Source |
|---|---|---|
| Scenario | `metro_caltech_sce` (ACN workplace, SCE TOU-EV tariff) | pkg `SCENARIO_AXES` L118 |
| Vehicles `n_cars` | **80** (not the 1000 env default) | pkg `N_CARS` L68 |
| Episode length | 168 h (1 week) | pkg `EPISODE_HOURS` L67 |
| Forecast horizon | 24 h | pkg `run_config` L291 |
| Queue max wait | **4 h** (not the 24 default) | pkg `run_config` L295 (`max_queue_wait_steps=4`) |
| Port power proxy | **7.2 kW/port** | pkg `POWER_KW_PROXY` L69 |
| Seeds (20) | **4541 … 4560** | runner `SEEDS = list(range(4541,4561))` L45 |
| Capacities | 20 %, 35 %, 50 % → see §4 | runner `CAPACITIES` L46 |
| Severities | 0,1,2,3 (full / mild / moderate / severe) | runner `SEVERITY` L50 |
| Fleet policies | `FleetServiceFirst`, `FleetServiceGridWeighted` | runner `FLEETS` L81 |
| Grid policies | `NoGridIncentive`, `GridPeakPenalty` | runner `GRIDS` L82 |
| Anchor | `LeastLaxity` (Dertouzos–Mok), severity-independent | engine `DEFAULT_POLICIES` L297 |

**Row accounting (verified against the CSV, 1 020 rows total):**
- 4 severities × (2 fleet × 2 grid) × 20 seeds × 3 caps = **4 × 240 = 960** experiment rows
  (240 per severity, confirmed by `groupby(severity).size()`).
- **+ 60** `LeastLaxity` anchor rows (20 seeds × 3 caps × 1, run once, severity-independent).
- **= 1 020** rows. The CSV carries a `capacity_kw_proxy` column with values **72.0 / 129.6 / 172.8**.

---

## 1. Environment config — `EnvV2Config`  (`simulator/env_v2.py:23`)

Library defaults; **the "primary" column is what the workplace run actually used** (via `run_config`
+ the `metro_caltech_sce` scenario overrides in `_apply_scenario_defaults`). Blank = default unchanged.

| Field | Library default | Primary run | Meaning |
|---|---|---|---|
| `n_cars` | 1000 | **80** | vehicles per episode |
| `episode_hours` | 168 | 168 | 1-week episode |
| `bcap_kwh` | 64.0 | 64.0 | battery capacity (kWh) |
| `eta_dcfc` | 0.85 | | charging efficiency |
| `soc_min` / `soc_max` | 0.20 / 0.95 | | usable SoC bounds |
| `degradation_cost_per_kwh` | 0.15 | | throughput degradation (KRW/kWh) |
| `off_peak_price_krw_per_kwh` | 57.6 | **98.0** | TOU off-peak (SCE super-off-peak) |
| `mid_peak_price_krw_per_kwh` | 109.0 | **238.0** | TOU mid-peak (SCE daytime) |
| `on_peak_price_krw_per_kwh` | 232.5 | **588.0** | TOU on-peak (SCE 4–9 pm band) |
| `solar_off_price_krw_per_kwh` | 65.0 | **238.0** | TOU solar-offset window |
| `p_fail` | 100000 | 2000 | unmet-mandatory-trip penalty (preset sets 2000) |
| `p_cancel` / `p_anxiety` | 2000 / 500 | | cancellation / low-SoC penalties |
| `shadow_price_failure` | 50000 | | reliability-adjusted-cost shadow price |
| `forecast_horizon` | 168 | **24** | forecast look-ahead (h) |
| `forecast_noise_std` | 0.0 | 0.10 | multiplicative forecast noise (`metro_caltech_sce` preset) |
| `trip_uncertainty_std` | 0.0 | 0.10 | trip timing/energy uncertainty (preset) |
| `trip_scale` | 1.0 | 1.0 | mandatory-trip demand scale |
| `init_soc_low`/`init_soc_high` | 0.30/0.90 | 0.35/0.80 | initial-SoC range (preset) |
| `home_access_prob` | 1.0 | 0.25 | P(home access) — workplace preset |
| `work_access_prob` | 1.0 | 0.90 | P(work access) |
| `public_access_prob` | 1.0 | 0.40 | P(public access) |
| `public_fallback_prob` | 0.0 | 0.35 | P(use public as fallback) |

### Port capacity — `QueueEnvConfig(EnvV2Config)`  (`simulator/e12_queue_env.py:38`)
| Field | Library default | Primary run | Meaning |
|---|---|---|---|
| `n_slots_home` / `n_slots_work` / `n_slots_public` | 9999 each | **set per capacity, §4** | charger counts per location |
| `max_queue_wait_steps` | 24 | **4** | hours a vehicle waits before abandoning |
| `target_soc` | 0.90 | 0.90 | charging target |
| `reserve_margin` | 0.12 | 0.12 (env) | SoC reserve headroom (driver-layer margins are separate, §4) |
| `queue_discipline` | `fifo` | `fifo` | queue service order |

---

## 2. TOU tariff — `metro_caltech_sce`  (`env_v2.py:175`, windows `env_v2.py:68-71`)

SCE TOU-EV-9 (2024 CA rates), converted at 1 USD ≈ 1400 KRW. Overrides the `EnvV2Config` price
defaults:

| Window | Hours (of day) | Price (KRW/kWh) | USD/kWh |
|---|---|---|---|
| Off-peak (overnight) | 23, 0–5 (`OFF_PEAK_HOURS`) | **98.0** | ≈0.07 |
| Mid-peak (daytime) | 6–10, 15, 16 (`MID_PEAK_HOURS`) | **238.0** | ≈0.17 |
| Solar-offset | 11–14 (`SOLAR_OFF_HOURS`) | **238.0** | — |
| On-peak | 17–22 (`ON_PEAK_HOURS`) | **588.0** | ≈0.42 |

Price schedule is built hour-by-hour over the 168-h episode (`_build_price_schedule`, `env_v2.py:132`).
(The source comment labels on-peak "4–9 pm"; the code's `ON_PEAK_HOURS = range(17,23)` = 5–10 pm is
authoritative.)

---

## 3. Session calibration data  (`simulator/data/`)

`env_v2.py:508-518` selects a summary file by `scenario_name` and draws each session's **energy
(kWh)** and **dwell (h)** from fitted lognormals, **arrival hour / day-of-week** from empirical
histograms. `metro_caltech_sce` uses the default → `caltech_multisite_summary.json`.

| Field (caltech_multisite) | Value |
|---|---|
| sessions (raw) | 29,149 = Caltech 11,448 + JPL 17,032 + Office001 669 |
| kWh lognormal (μ, σ) | 2.0796, 1.0125 (mean 12.18 kWh) |
| dwell lognormal (μ, σ) | 1.6994, 0.7209 (mean 6.68 h) |
| arrival / dow | `hour_of_day_connection_hist` (24), `dow_connection_hist` (7) |

### Raw ACN grounding  (`simulator/data/acn_empirical_models/`)
- **`acn_clean_session_features.csv` — 29,116 cleaned session tuples** (26 columns). This is the
  set for output-level KS validation and joint-session resampling.
- `empirical_model_summary.json` — fitted `distribution_fits`, session/user typologies, cleaning
  rules, quality.
- **29,149 vs 29,116:** 29,149 raw 12-month sessions; cleaning drops 33 invalid-dwell rows (30 + 2 +
  1) → **29,116** clean tuples. Cleaning rules: `min_dwell_h 0.0167`, `max_dwell_h 48`,
  `max_kwh_delivered 150`.

---

## 4. Experiment design — capacity, severity, RNG

### Capacity (the corrected rule)
Capacity is **not** a fraction of `n_cars`. The engine scales a **fixed base charger provision**
`BASE_CAPACITY = {home: 40, work: 5, public: 5}` (`pkg` L117) by the capacity percentage
(`capacity_slots`, `pkg` L263):

```python
slots[loc] = max(1, int(round(BASE_CAPACITY[loc] * capacity_pct/100)))   # Python round = banker's
capacity_kw_proxy = (n_home + n_work + n_public) * 7.2   # POWER_KW_PROXY
```

| capacity_pct | home | work | public | total ports | kW proxy (× 7.2) |
|---|---|---|---|---|---|
| 20 % | 8 | 1 | 1 | 10 | **72.0** |
| 35 % | 14 | 2 | 2 | 18 | **129.6** |
| 50 % | 20 | 2 | 2 | 24 | **172.8** |

(35 %: `round(1.75)=2`; 50 %: `round(2.5)=2` under banker's rounding — matches the frozen
`capacity_kw_proxy` column exactly.)

### Behavioral severity — the driver-compliance knob  (`run_seed20_severity_20260615.py:50`)
Overlaid on the fleet recommendation by the severity driver layer; the driver overrides toward
self-service with probability `1 − keep_probability`, and inflates its reserve thresholds by
`reserve_margin` (+ `cheap_extra_margin` in cheap price windows).

| Level | Label | keep_prob | reserve_margin | cheap_extra_margin | ≈ vehicle-timestep deviation |
|---|---|---|---|---|---|
| 0 | full_compliance | 1.00 | 0.00 | 0.00 | 0 % |
| 1 | mild_deviation | 0.95 | 0.05 | 0.10 | ~5 % |
| 2 | moderate_deviation | 0.80 | 0.15 | 0.30 | ~20 % |
| 3 | severe_deviation | 0.55 | 0.25 | 0.60 | ~45 % |

Severity 0 = the maintained full-compliance assumption; the headline all-pass collapse is 0 → 1.

### RNG streams
- **Environment** (session sampling, trip schedule, forecast noise): `make_env(cfg, seed=seed)` →
  `env.rng = default_rng(seed)`, seed ∈ {4541…4560}.
- **Policy / driver-compliance coin**: `policy_rng(seed, spec, policy)` =
  `default_rng(seed + 1_150_000 + abs(hash((spec.label, policy))) % 1_000_000)` (`pkg` L299).
  The severity keep-coin `rng.random(n_cars) < keep_probability` draws from this stream.
  ⚠️ **Reproducibility caveat:** the offset uses Python's built-in `hash()` of a tuple containing a
  string, which is process-salted unless `PYTHONHASHSEED` is fixed; the frozen CSV is the canonical
  realization.

---

## 5. Controller & gate definitions

### Least-laxity anchor  (`run_behavior_trait_screening.py:165`, `_select_cap_limited` L134)
`least_laxity_actions` charges a vehicle when the least-laxity charge mask is set (Dertouzos–Mok /
EDF family); it is the reference all gates score deltas against. When eligible requests exceed
available slots, `_select_cap_limited` (L159) keeps the highest-scoring vehicles, **ties broken by
ascending vehicle index** — `sorted(members, key=lambda i: (-score[i], i))` — i.e. fully
deterministic given the seed.

### Critical-request definition  (`_service_critical`, `run_behavior_trait_screening.py:100`)
A request is **critical** if **any** hold:
- `reserve` — SoC at/below the (behavior-inflated) reserve threshold, **or**
- `deadline_deficit > 0` — behind the energy needed for the next mandatory trip, **or**
- `time_to ≤ 24/168` — a mandatory trip within 24 h (time normalized by the 168-h week), **or**
- `laxity ≤ 0.25` — little scheduling slack remaining.

### Grid cap algorithm  (`apply_grid_policy`, `engine:515`)
- `NoGridIncentive` → pass-through, no cap (`return actions, 0`).
- `GridPeakPenalty` → `capped_select_from_actions(per_location_fraction = 0.70, score = 200·critical
  + 90·(1−soc) + 30·deadline_deficit − 15·laxity)`. Per location per step it admits at most
  `ceil(loc_slots × 0.70) − queued` charging requests, choosing the highest-scoring (engine L421);
  suppressed vehicles idle. This is an **action-changing** cap, not a price signal.

### Fleet policies
`FleetServiceFirst` = the least-laxity service recommendation. `FleetServiceGridWeighted` adds the
pre-registered priority weights `w_service=100, w_critical=100, w_queue=10, w_peak=3, w_cost=1`
(engine `THRESHOLDS.balanced_policy_weights` L74) — service/critical dominant, queue only penalizing
high-SoC non-critical flexible requests.

### The 14 acceptability gates — `THRESHOLDS`  (`engine:73`)
Each episode passes an actor's gate only if **all** its criteria hold, evaluated as a delta/ratio
**vs the LeastLaxity anchor**; `all_pass` = driver ∧ fleet ∧ grid on the same episode.

**Driver** (`driver_service_pass`): delivered-kWh ratio ≥ 0.95; reliability delta ≥ −0.5 pp;
critical-requested-not-delivered delta ≤ 24 (`CRITICAL_NO_DELIV_SLACK`); low-SoC-event delta disabled.

**Fleet / operator**: p95 wait delta ≤ 30 min; mean-queue delta ≤ 1.0; max-queue delta ≤ 2.0;
requested-not-delivered delta ≤ 117 (`TOTAL_NO_DELIV_FAILURE_DELTA`); energy-cost ratio ≤ 1.10;
demand-charge-exposure ratio ≤ 1.10.

**Grid**: peak ratio ≤ 1.05; peak-to-average ratio ≤ 1.10; ramp-p95 ratio ≤ 1.10; load-factor delta
≥ −0.05; squared-load proxy ratio ≤ 1.10; IEEE-33 min-voltage ≥ 0.95 pu and max-line-loading ≤ 100 %
(*documented, non-binding in weekly runs*, `note` L104).

Named **binding** gates (minimal-gateset analysis): driver = critical-requested-not-delivered,
operator = p95 wait, grid = squared-load / ramp load-shape.

---

## 6. Other scenario presets  (`data_grounding.py:140`)

18 presets exist; the primary paper uses **`metro_caltech_sce`** (§0). The apartment cross-ecology
extension uses **`metro_korea`**, whose infrastructure-access values are derived at load time from
`korea apartment.xlsx` (579 households/complex, 2.48 chargers/100 hh, 40.5 % EVs>chargers) and
clamped (`data_grounding.py:142-144`); `data_grounding.py` bakes in fallback stats so the preset is
deterministic without the raw file. The `nl_office*` / `uk_home*` presets are the international
external-validity scenarios (session distributions from `{nl_office,uk_home}_summary.json`). Full
per-preset access/slot/SoC/forecast values are in `data_grounding.py`.

---

## 7. Reproducing the primary run
```python
# from /home/jia/thirfty death BRL DQN  (engine + brl_dqn_v2 on path; simulator on /home/jia/thirftydeath)
python "analysis/seed20_producer/run_seed20_severity_20260615.py"
# → seed20_row_results_20260615.csv  (1020 rows: seeds 4541-4560 × caps {20,35,50} × 4 policies × 4 severities + 60 anchor)
```
The multi-actor experiments use **scripted** driver/fleet/grid policies — no trained RL agent. The
trained-agent loaders in `run_experiments.py` are inherited engine scaffolding and are **not** on
the paper's path.
