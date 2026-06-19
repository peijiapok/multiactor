# Multi-actor equilibrium results — summary (2026-06-16)

## What was built
A game-theoretic mechanism layer turning the paper from diagnostic to constructive.
Pipeline (all in `equilibrium_optimization_20260616/`):
1. `run_response_surface_20260616.py` — sweeps aggregate deviation d over a grid (slack-
   structured), 3 capacities, 5 seeds, both grid policies, both service fleets → 660-row
   simulator response surface (`response_surface_rows_20260616.csv`). One expensive run (~17 min).
2. `gametheory_equilibrium_20260616.py` — pure analytics on the surface: utilities U_D/U_F/U_G,
   driver-Nash fixed point, Stackelberg incentive, Nash bargaining solution, price of anarchy.
   Validated first on a synthetic surface (`--selftest`).
3. `sensitivity_equilibrium_20260616.py` — robustness over β, s, ρ0, welfare weights (243 configs/cap).
4. `make_equilibrium_figures_20260616.py` — 4 figures (best-response, all-pass vs incentive,
   utility triangle, PoA).

## Methodology (the "sexy" core)
- **Driver compliance = aggregative CONGESTION / free-riding game.** A coordinated schedule is a
  public good (uncongested queue + healthy load shape); benefit of complying falls as others comply
  → drivers free-ride. Comply iff σ + β(1−ρ) ≥ κ_i, κ_i~Logistic(μ,s). Compliance = fixed point
  ρ=Φ(ρ;σ)=F_κ(σ+β(1−ρ)). Φ decreasing → **unique stable Nash equilibrium**.
- **Calibration:** μ set so σ=0 equilibrium = ACN-anchored d*=0.05 (ρ*=0.95). Soft behavioral
  calibration (magnitude + slack structure from data), NOT a fitted opt-out model.
- **Target = Nash Bargaining Solution** over (U_D,U_F,U_G), disagreement = selfish NE.
- **Mechanism = Stackelberg**: operator sets incentive σ (Pigouvian) + grid policy; drivers follow;
  min σ* restoring all-pass via bisection.
- **Price of Anarchy** = W(NBS)/W(selfish).

## Key results (ServiceFirst, baseline β=2,s=0.4,ρ0=0.95, equal weights)
- **Selfish NE = ρ*=0.95 (d*=0.05), UNIQUE, stable (|Φ'|=0.12), all-pass=0.000.** The collapse IS
  the equilibrium of the uncoordinated game (not a knob).
- Utilities at selfish NE (35% cap): U_D=0.73, U_F=0.25, U_G=0.55 → **fleet is worst-off actor**.
- **Bounded Pigouvian incentive σ*≈0.44–0.68 restores majority all-pass** at every capacity.
- **NBS** picks GridPeakPenalty, d≈0, all-pass=1.0, lifts all three utilities (35%: 0.98/0.56/0.70).
- **Price of Anarchy = 1.48 / 1.46 / 1.48** at 20/35/50% → coordination worth ~47% welfare.

## Robustness (243 configs/capacity)
- Unique equilibrium in ALL configs; selfish-NE all-pass = 0.000 in ALL.
- PoA ∈ [1.18, 1.83], always > 1; median 1.42.
- σ* ∈ [0.13, 1.77] restores all-pass in 100% of configs.
- Stable (|Φ'|<1) everywhere except extreme β=4 & s=0.25 (uniqueness still holds).

## Honest caveats (in manuscript)
- Driver game is a soft-calibrated behavioral model, not fitted to logged opt-out decisions.
- Welfare weights normative (sensitivity reported); utilities min-max normalized within capacity.
- Incentive σ is in normalized utility units, not a $ tariff — translating it + fitting the
  compliance response to a managed-charging trial are the defined next steps.
- Grid-lever effect on σ* is capacity-dependent (helps at 50%, not 35%) — reported, not overclaimed.

## Manuscript integration
New Section "A game-theoretic mechanism that restores multi-actor acceptability" (sec:game) inserted
after Results, before Discussion. Title, abstract, contributions (added #4), organization sentence,
and Conclusions all reframed: collapse = selfish equilibrium; mechanism = contribution. 4 new figures
(Figs 9–12). Compiles clean with tectonic: **39 pages, 0 undefined refs/cites**.
Backup: `APPLIED_ENERGY_MANUSCRIPT_SUBMISSION_REPAIR_20260614.tex.bak_pre_equilibrium`.
