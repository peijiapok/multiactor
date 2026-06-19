# How the Simulation Works — Complete Methodology, Formulae, Data, and Worked Examples

This document explains, end to end, exactly how the multi-actor EV-charging simulation in this
paper is run: every state variable, every formula, every data source, how the charging
**recommendation** is produced, how the three actor gates are scored, and how the game-theoretic
mechanism layer is computed. Each formula is traced to its source code so it can be verified.

**Source files (ground truth):**
- Engine driver: `/home/jia/thirfty death BRL DQN/scripts/run_multi_actor_v2_experiment.py`
- Policy package: `.../scripts/run_behavior_applied_energy_package_v1.py` (constants, scoring)
- Core rules: `.../scripts/run_behavior_trait_screening.py` (`_arrays`, `_service_critical`, `least_laxity_actions`)
- Environment / laxity / LL charge: `.../brl_dqn_v2/train_eval_v2.py`
- Demand model fit: `/home/jia/thirftydeath/caltech_multisite_summary.json`
- Game-theory layer: `/home/jia/multi actor/equilibrium_optimization_20260616/gametheory_equilibrium_20260616.py`
- Response surface runner: `.../equilibrium_optimization_20260616/run_response_surface_20260616.py`

---

## 0. The pipeline in one picture

For each hourly timestep `t` of an episode, every car `i` passes through three decision layers,
and the realised actions feed the metrics that are checked against the actor gates:

```
ACN demand  ─►  car state (SoC, laxity, deficits)
                      │
            (1) FLEET layer:  recommended action  x^F_{i,t}   (LeastLaxity, or ServiceGridWeighted)
                      │
            (2) GRID layer:   grid-adjusted action x^G_{i,t}   (NoGridIncentive | GridPeakPenalty)
                      │
            (3) DRIVER layer: actual action        x_{i,t}     (comply w.p. p_keep, else self-serve)
                      │
                served charging  ─►  episode metrics  ─►  14 acceptability gates  ─►  ALL-PASS (AND)
```

- An **episode** is `e = (seed s, capacity c, behavior b, fleet policy f, grid policy g, horizon H)`.
- Horizon `H = 168 h` (weekly) or `672 h` (28-day). Resolution = **1 hour**.
- `POWER_KW_PROXY = 7.2 kW` (one served request ≈ 7.2 kWh over the hour).

---

## 1. Global constants

| Constant | Value | Source |
|---|---|---|
| Episode length (weekly / 28-day) | 168 h / 672 h | `EPISODE_HOURS=168`; 28-day runner |
| Charge power proxy | 7.2 kW | `POWER_KW_PROXY = 7.2` |
| Base charger slots (home/work/public) | 40 / 5 / 5 | `BASE_CAPACITY = {"home":40,"work":5,"public":5}` |
| Capacity scaling | `slots_loc = max(1, round(BASE·c/100))` | `capacity_slots()` |
| Target SoC | 0.90 | `_target_need` default |
| Reserve margin (driver anxiety buffer) | 0.12 (base) | `_reserve_need` default |
| Cheap-price tolerance | within 1.05× of min price | `_cheap_mask` |
| Capacities tested | 20%, 35%, 50% | experiment design |
| Seeds | 4541–4545 (5) or 4541–4560 (20) | runners |

**Capacity example:** at `c=35%`, `work` slots `= max(1, round(5·0.35)) = max(1,2) = 2`;
`home = round(40·0.35) = 14`; `public = 2`.

---

## 2. Data: the ACN-Data charging-demand model

Charging sessions are **not synthetic** — energy, dwell time, and arrival hour are drawn from
distributions fitted to **29,149 real sessions** from the public Adaptive Charging Network
(Caltech 11,448 + JPL 17,032 + Office001 669), 12 months. Fit in `caltech_multisite_summary.json`:

| Session variable | Distribution | Parameters | Mean / median |
|---|---|---|---|
| Delivered energy (kWh) | Lognormal | μ = 2.07956, σ = 1.01254 | 12.18 / 9.06 kWh |
| Dwell duration (h) | Lognormal | μ = 1.69938, σ = 0.72092 | 6.68 / 7.36 h |
| Arrival hour | Empirical 24-bin histogram | peak at hours 6–8 | mode ≈ 07:00 |

Arrival histogram (connections per hour 0…23):
`[34,10,9,25,84,1256,4556,6207,2936,2491,1684,1427,1556,1315,1111,1209,1076,652,534,365,244,215,107,…]`

**Example — drawing one session (energy):** a lognormal(μ=2.07956, σ=1.01254) draw is
`E = exp(2.07956 + 1.01254·Z)`, `Z ~ N(0,1)`.
- `Z = 0` → `E = exp(2.07956) = 8.00 kWh` (the *lognormal* median; the empirical data median is 9.06 kWh, the small gap reflecting the fit).
- `Z = +1` → `E = exp(2.07956 + 1.01254) = exp(3.0921) = 22.0 kWh`.
- `Z = −1` → `E = exp(1.06702) = 2.91 kWh`.
Energy is clipped at 40 kWh and dwell at 14 h (tail truncation, disclosed in the paper).
External validation: simulator vs real KS distance = 0.087 (energy), 0.176 (dwell), 0.068 (arrival).

---

## 3. Car state variables (per car `i`, per timestep `t`)

Built by `_arrays(env, obs)` (`run_behavior_trait_screening.py:85`):

| Symbol | Code key | Meaning |
|---|---|---|
| `soc_i` | `soc` | state of charge ∈ [0,1] |
| `θ_i` | `theta` (`anxiety_thresholds`) | per-driver SoC anxiety threshold |
| `reserve_i` | `reserve` | `soc_i < θ_i + reserve_margin` (needs a safety buffer) |
| `target_i` | `target` | `soc_i < target_soc (0.90)` (still wants energy) |
| `Ti` | `target_deficit` | normalized energy gap to target |
| `Di` | `deadline_deficit` | normalized energy gap to make the next deadline |
| `time_to_i` | `time_to` | normalized hours to next mandatory trip |
| `λ_i` | `laxity` | normalized deadline laxity (slack) — see §4 |
| `masks` | `masks` | which primitive actions are legal for car `i` |

**Critical-service flag** (`_service_critical`, line 100) — a car is *service-critical* if **any** hold:
```
critical_i = reserve_i  OR  (Di > 0)  OR  (time_to_i ≤ 24/168)  OR  (λ_i ≤ 0.25)
```
i.e. it needs a reserve buffer, can't meet its deadline, has a trip within 24 h, or has ≤ 25%
slack. Critical cars are **protected** — they are never deferred by the grid weighting (§5.2).

---

## 4. Laxity (the core scheduling quantity)

Laxity = spare time before a car *must* charge to make its next trip
(`_least_laxity_charge`, `train_eval_v2.py:118`). For car `i` with a planned trip:

```
hours_to_deadline = hours until the next mandatory trip
trip_kwh   = (trip distance units at deadline) · 0.18        # 0.18 kWh per unit
usable_kwh = max(0, soc_i − soc_min) · bcap_kwh              # energy available now
deficit_kwh = max(0, trip_kwh − usable_kwh)                  # energy still needed
charge_power = location charge power (kW)

laxity_i = hours_to_deadline − deficit_kwh / charge_power           ← Eq. (L)
```
Low laxity ⇒ little slack ⇒ must charge now. If a car has no scheduled trip it gets
`laxity = 10^6 + (target_soc − soc)` (effectively infinite, charges only when slots are free).

**Worked example (laxity):** car with `hours_to_deadline = 5 h`, `trip_kwh = 2.0`,
`usable_kwh = 1.0` (so `deficit_kwh = 1.0`), `charge_power = 7.2 kW`:
```
laxity = 5 − 1.0/7.2 = 5 − 0.139 = 4.86 h  → plenty of slack (not urgent)
```
A second car with `deficit_kwh = 30 kWh`, same deadline/power:
`laxity = 5 − 30/7.2 = 5 − 4.17 = 0.83 h` → urgent. The second car charges first.

---

## 5. THE RECOMMENDATION — how the fleet decides what to charge

The "recommendation" is the **fleet layer** action vector `x^F`. Two fleet policies are used.

### 5.1 LeastLaxity (the anchor / FleetServiceFirst)

`least_laxity_actions` → `_least_laxity_charge` (`train_eval_v2.py:118`). Per location, fill the
available slots with the **lowest-laxity cars first**, reserve-need cars ahead of others:

```
for loc in {home, work, public}:
    members  = cars at loc that still need energy (target_i)            # eligible set
    remaining = n_slots[loc] − (cars already queued)                    # free chargers
    reserve_members = members with reserve_i = True   (safety-critical)
    other_members   = members with reserve_i = False
    ordered = [reserve_members sorted by laxity ↑] ++ [other_members sorted by laxity ↑]
    charge the first `remaining` of `ordered`                           # recommend NORMAL_REQUEST
    all others → IDLE
```
So LeastLaxity = **"serve the cars with the least slack first, up to the number of chargers,
prioritising those below their safety buffer."** This is a standard real-time-scheduling rule
(least-laxity-first) and is the recommendation `x^F_{i,t}` that everything else is measured against.

**Worked example (recommendation):** at `work`, capacity 35% ⇒ 2 slots, 0 already queued.
Four cars need energy with laxities and reserve flags:

| car | laxity (h) | reserve? |
|---|---|---|
| A | 0.20 | yes |
| B | 0.80 | no |
| C | 0.10 | no |
| D | 3.0 | no |

Ordering = reserve first (A), then others by laxity (C 0.10, B 0.80, D 3.0) → `[A, C, B, D]`.
`remaining = 2` ⇒ **recommend charging A and C**; B and D → IDLE this hour.

### 5.2 FleetServiceGridWeighted (the comparator — NOT a proposed controller)

Starts from the LeastLaxity vector and *defers* at most 20% of the **already-flexible, low-risk**
requests when a queue/peak/price trigger fires (`service_grid_weighted` in the runners; supplement
Eqs. 12–13). For candidate `i`:
```
service score   S_i = 320·C_i + 175·L_i + 120·T_i + 95·D_i + 55·X_i
deferral priority Z_i = S_i − (48·Q_i + 32·P_t + 18·R_t)·F_i
```
where `C_i`=critical, `L_i`=low-SoC, `T_i`/`D_i`=target/deadline deficit, `X_i`=inverse laxity,
`Q_i`/`P_t`/`R_t`=queue/peak/price pressure, `F_i`=flexible-low-risk flag. Defer the lowest-`Z`
flexible candidates, up to `⌊0.20·n_F⌋`.

**Why the weights (320,175,…) are not justified and don't need to be:** critical/low-SoC/deadline
cars are **excluded from the deferral-eligible set `F_i` by construction**, so no weight, however
large, can defer them — the coefficients only reorder *already-flexible, low-risk* cars. A
six-variant ablation (including an **all-weights-equal** variant that removes the ordering) leaves
the screening result unchanged. It is a robustness comparator, not a tuned model.

**Worked example (ServiceGridWeighted defer):** a flexible low-risk car (`C=L=0`, `T=0.10`,
`D=0`, `X=0.2`) under an active peak trigger (`P_t=1`, `Q=0`, `R=0`, `F=1`):
```
S = 320·0 + 175·0 + 120·0.10 + 95·0 + 55·0.2 = 12 + 11 = 23
Z = 23 − (48·0 + 32·1 + 18·0)·1 = 23 − 32 = −9
```
A negative `Z` and flexible-low-risk status make it a deferral candidate; if it is among the
bottom 20%, it is held to IDLE this hour to relieve the peak.

### 5.3 GRID layer — `x^F → x^G`

Two grid policies adjust the fleet recommendation:
- **NoGridIncentive:** pass-through, `x^G = x^F`.
- **GridPeakPenalty:** when site load/peak pressure is high, defer extra flexible requests
  (the deferrals are attributed to the grid layer, not the fleet). It can lower peak metrics but
  cannot restore all-pass once driver/fleet gates already fail.

---

## 6. THE DRIVER LAYER — compliance vs. self-service

Drivers receive the recommendation `x^G` and either **comply** (keep it) or **deviate**
(self-serve). This is the behavioral-stress layer (`direct_driver` in the runners).

Each behavior level has a keep-probability `p_keep` and reserve/cheap margins:

| Severity | label | `p_keep` (comply) | reserve_margin | cheap_extra_margin | pop-mean deviation |
|---|---|---|---|---|---|
| 0 | full compliance | 1.00 | 0.00 | 0.00 | 0% |
| 1 | mild | 0.95 | 0.05 | 0.10 | ~5% |
| 2 | moderate | (lower) | larger | larger | ~20% |
| 3 | severe | (lowest) | largest | largest | ~45% |

Per car per step:
```
keep_i  ~  Bernoulli(p_keep)          # or structured: p_dev_i depends on laxity (see below)
actual action x_i = x^G_i      if keep_i        (comply)
                  = pref_i      otherwise        (deviate → self-serve)
```

**Structured (slack-dependent) deviation** — used in the response surface so deviation
concentrates in low-slack drivers (realistic):
```
w_i = 1 − clip(laxity_i, 0, 1)          # inflexibility weight
k   = target_dev_rate / mean(w)         # normalise to the target population mean (e.g. 0.05)
p_dev_i = clip(k · w_i, 0, 1)           # low-laxity ⇒ higher deviation probability
```

**Self-service preference** `pref_i` (what a deviating driver does instead — `severity_preference`):
```
score_i = 260·C_i + 130·N_i + 95·T_i + 55·D_i + 35·(1 − soc_i) − 10·λ_i
```
(`N_i` = reserve-seeking need, with the reserve threshold raised by `reserve_margin`, and further by
`cheap_extra_margin` during cheap-price windows). The deviating driver then charges according to
this self-interested score under the same slot caps. **Net effect:** mild deviation creates extra,
mistimed **request events** (churn) rather than more total energy.

**Worked example (driver compliance):** severity 1, structured deviation, a low-laxity car
(`laxity=0.1` ⇒ `w=0.9`) in a population with `mean(w)=0.45`, target rate 0.05:
```
k = 0.05 / 0.45 = 0.111
p_dev = clip(0.111 · 0.9, 0, 1) = 0.10   → this inflexible car deviates with prob 0.10
```
Draw `U ~ Uniform(0,1)`; if `U < 0.10` the car ignores the recommendation and self-serves per
`score_i`; otherwise it complies. A high-laxity car (`w=0.1`) gets `p_dev = 0.011` (rarely deviates).

---

## 7. Episode metrics (what gets measured)

After the full horizon, per episode the engine aggregates (`add_actor_scoring`):
- **Delivered**: `total_delivered_kwh`, `delivered_ratio_vs_ll`, `reliability_pct`.
- **Requests / churn**: `request_count`, `requested_not_delivered_count`,
  `critical_requested_not_delivered_count`, and the driver-vs-fleet request-event ratio
  `χ = N_actual / N_fleet`. A **demanded-kWh ledger** tracks `E_new`, `E_delivered`, `E_release`
  so that the behavioral effect is verified to be *request churn*, not energy growth
  (request-ID conservation: max count residual = 0 in every case).
- **Queue / wait**: `mean_queue_length`, `max_queue_length`, `p95_wait_minutes`.
- **Cost**: `energy_cost_usd`, `energy_cost_ratio_vs_anchor`, `demand_charge_ratio_vs_anchor`.
- **Grid load shape**: `peak_ratio_vs_ll`, `ramp_p95_ratio_vs_anchor`, `peak_to_average_ratio`,
  `squared_load_proxy_ratio_vs_anchor`, `load_factor_delta_vs_anchor`.
- **Feeder (IEEE-33 screen, not a gate):** EV-off-relative substation-peak, line-loading, loss deltas.

Most metrics are expressed **relative to an anchor**: `_vs_ll` = vs the LeastLaxity full-compliance
run; `_vs_anchor` = vs the policy's own full-compliance baseline. This is why the result is about
*degradation under behavior*, not absolute levels.

---

## 8. The 14 acceptability gates (driver / fleet / grid)

An episode **passes** a gate if its metric satisfies the threshold. Source: the `CRITERIA` list in
`run_28day_ratenorm_20260615.py`. Grouped into the three actor gates:

### Driver-service gate `A_D` (all 3 must hold)
| # | metric | comparator | threshold |
|---|---|---|---|
| D1 | `delivered_ratio_vs_ll` | ≥ | 0.95 |
| D2 | `reliability_delta_vs_ll_pp` | ≥ | −0.5 |
| D3 | `critical_rnd_delta_vs_ll` (critical requested-not-delivered) | ≤ | 24 |

### Fleet-operation gate `A_F` (all 6)
| # | metric | comparator | threshold |
|---|---|---|---|
| F1 | `requested_not_delivered_delta_vs_anchor` | ≤ | 117 |
| F2 | `mean_queue_delta_vs_anchor` | ≤ | 1.0 |
| F3 | `max_queue_delta_vs_anchor` | ≤ | 2.0 |
| F4 | `p95_wait_delta_vs_ll_min` | ≤ | 30 (min) |
| F5 | `energy_cost_ratio_vs_anchor` | ≤ | 1.10 |
| F6 | `demand_charge_ratio_vs_anchor` | ≤ | 1.10 |

### Grid load-shape gate `A_G` (all 5)
| # | metric | comparator | threshold |
|---|---|---|---|
| G1 | `peak_ratio_vs_ll` | ≤ | 1.05 |
| G2 | `ramp_p95_ratio_vs_anchor` | ≤ | 1.10 |
| G3 | `peak_to_average_ratio_vs_anchor` | ≤ | 1.10 |
| G4 | `squared_load_proxy_ratio_vs_anchor` | ≤ | 1.10 |
| G5 | `load_factor_delta_vs_anchor` | ≥ | −0.05 |

Thresholds are **normative** (chosen, not universal). Two gates (D3, F1) are *extensive* counts;
under the 28-day horizon they are scaled ×(672/168)=4 ("horizon-fair" rescaling) so the result is
not a threshold artifact.

**Worked example (one gate):** an episode delivers 12.0 kWh/vehicle vs the LeastLaxity anchor's
12.4 kWh ⇒ `delivered_ratio_vs_ll = 12.0/12.4 = 0.968 ≥ 0.95` ⇒ **D1 passes**. If instead the
critical requested-not-delivered count rose by 30 vs anchor ⇒ `30 > 24` ⇒ **D3 fails**, so the
driver gate `A_D` fails for that episode.

---

## 9. ALL-PASS acceptability

```
A_D = (D1 ∧ D2 ∧ D3)
A_F = (F1 ∧ … ∧ F6)
A_G = (G1 ∧ … ∧ G5)
A_all (episode) = A_D ∧ A_F ∧ A_G          ← all three actors acceptable in the SAME episode
all-pass rate   = mean(A_all) over episodes
```
**Headline result:** full compliance → all-pass ≈ 0.967; low-deviation severity-1 → all-pass ≈
0.012 (weekly) / 0.000 (28-day), because the binding violations (critical-not-delivered, p95 wait,
load shape) land in *different* episodes — so almost no single episode clears all 14 at once.

**Worked example (all-pass):** severity-1 episode with `A_D=0` (D3 fails on critical churn),
`A_F=0` (F4 wait blows up), `A_G=1` ⇒ `A_all = 0∧0∧1 = 0`. Even though the grid is fine, the
episode is unacceptable. A scenario-*averaged* check would pass 11/14 gates (each on its own
average) yet same-episode all-pass is ~0.

---

## 10. The game-theory layer (mechanism analysis)

This is a **calibrated overlay** computed on the simulator response surface, not new simulation.
Source: `gametheory_equilibrium_20260616.py`.

### 10.1 Driver compliance as a congestion game
Aggregate compliance `ρ` (fraction complying; deviation `d = 1−ρ`). A driver complies iff
`σ + β(1−ρ) ≥ κ_i`, with private cost `κ_i ~ Logistic(μ, s)`. The compliance rate is the fixed point
```
ρ = Φ(ρ; σ) = F_κ(σ + β(1−ρ)),     F_κ(x) = 1/(1+e^{−(x−μ)/s})
```
`σ` = operator incentive (normalized utility units), `β` = externality strength. Because `Φ` is
decreasing in `ρ`, the fixed point is **unique** (single crossing). Calibrated so that at `σ=0` the
equilibrium reproduces the ACN-anchored deviation: `ρ* = 0.95` (`d* = 0.05`).

**Worked example (fixed point):** `β=2`, `s=0.4`, calibrated `μ` so `ρ*(σ=0)=0.95`.
- `μ = β(1−ρ0) − s·logit(ρ0) = 2(0.05) − 0.4·ln(0.95/0.05) = 0.10 − 0.4(2.944) = −1.078`.
- Check: `Φ(0.95;0) = F_κ(0 + 2·0.05) = 1/(1+e^{−(0.10+1.078)/0.4}) = 1/(1+e^{−2.945}) = 0.950` ✓.
- Slope `|Φ'| = β·f_κ ≈ 0.12 < 1` ⇒ unique & stable.
At this equilibrium the simulator says **all-pass = 0.000** → the collapse *is* the uncoordinated
compliance equilibrium of the calibrated game.

### 10.2 Actor utilities (normalized to [0,1], from the gate metrics)
```
U_D = 0.5·reliability + 0.5·minmax(delivered_ratio)            # driver service/availability
U_F = 0.5·(critical served/critical count) + 0.5·(1 − minmax(p95_wait))   # fleet service/revenue
U_G = 1 − mean(minmax(squared_load), minmax(ramp), minmax(peak_to_avg))   # grid (low stress)
```
(Utilities are min–max normalized **within each capacity**, so the welfare comparison is relative.)

### 10.3 Nash bargaining target + Stackelberg incentive + price of anarchy
- **NBS** = the point maximizing `∏_k (U_k − d_k)`, disagreement `d_k` = selfish-equilibrium utilities.
- **Stackelberg incentive `σ*`** = the smallest `σ` whose induced `d*(σ)` makes all-pass ≥ 0.5
  (monotone ⇒ bisection). Nominal `σ* ≈ 0.44–0.68` across capacities.
- **Price of anarchy** `PoA = W_NBS / W_selfish`, `W = Σ w_k U_k`. `PoA ≈ 1.47` (≈47% relative gain).

**Worked example (incentive recovery):** raising `σ` from 0 to ≈0.44 shifts the fixed point from
`ρ*=0.95` to `ρ*≈0.985` (`d*≈0.015`), which the simulator surface maps to all-pass ≈ 0.5 — i.e. a
bounded incentive moves the modelled equilibrium back across the acceptability cliff (raw cliff:
all-pass 1.0 at d=0, 0.70 at d=1.25%, 0.10 at d=1.9%, 0.00 at d≥2.5%).

---

## 11. End-to-end worked example (one car, one hour)

Severity 1, 35% capacity, FleetServiceFirst + NoGridIncentive. Car at `work`, `soc=0.30`,
`θ=0.40`, scheduled trip in 5 h needing 2 kWh, has 1 kWh usable, `charge_power=7.2 kW`.

1. **State:** `reserve = (0.30 < 0.40+0.12) = True` (critical, since reserve). `laxity = 5 − 1/7.2 = 4.86 h` (but reserve flag already makes it critical/eligible-first).
2. **Fleet recommendation:** as a reserve car it sorts ahead of non-reserve cars; with 2 work
   slots it is recommended to charge → `x^F = NORMAL_REQUEST`.
3. **Grid layer:** NoGridIncentive ⇒ `x^G = x^F = NORMAL_REQUEST`.
4. **Driver layer:** structured deviation, `w = 1−clip(4.86 normalized)` — high-laxity ⇒ low `p_dev`
   (say 0.012). Draw `U=0.4 > 0.012` ⇒ **complies** ⇒ `x = NORMAL_REQUEST`. The car charges ≈ 7.2 kWh.
   (Had it been a low-laxity car with `p_dev=0.10` and `U=0.05`, it would deviate and self-serve.)
5. **Metric contribution:** this served critical request lowers `critical_requested_not_delivered`;
   across the episode the mix of complying/deviating cars determines D1–G5 and hence `A_all`.

---

## 12. Reproducibility

- Seeds are fixed and reported; weekly = 5 or 20 seeds, 3 capacities, 2 grid policies, 2 service
  fleet policies → 240 episodes per severity cell (20-seed).
- Demand calibration: `caltech_multisite_summary.json` (= independent fit of 29,149 ACN sessions).
- Game layer is deterministic given the response-surface CSV (`response_surface_rows_20260616.csv`).
- All analysis code: `equilibrium_optimization_20260616/` (response surface, game theory, sensitivity,
  fleet-profit, figures).

---

### One-paragraph summary
Sessions are drawn from ACN-fitted lognormals; each hour the **fleet** recommends charging the
lowest-laxity (least-slack) cars up to the number of chargers (LeastLaxity), protecting
safety-critical cars; the **grid** layer may defer extra flexible requests under peak pressure; the
**driver** then complies with probability `p_keep` or self-serves (deviates), with deviation
concentrated in low-slack cars. The realised charging produces episode metrics that are checked
against **14 normative gates** in three actor groups; an episode is **all-pass** only if all three
gates hold simultaneously. A calibrated congestion-game overlay then interprets the low-deviation
all-pass collapse as an uncoordinated compliance equilibrium and computes the bounded incentive that
moves the modelled equilibrium back into the acceptable region.
