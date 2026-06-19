# Multi-actor EV-charging equilibrium — research design (autonomous build, 2026-06-16)

## Aim
Turn the paper from a *diagnostic* ("naive policies fail the joint driver/fleet/grid
acceptability test") into a *constructive* contribution: formalize the three-actor
problem as a game, characterize the equilibrium, and design a mechanism that
**restores all-pass acceptability** — "charge without peaks, without wasted EV/fleet
energy, with a happy grid." This is the novelty the author intended.

## The sexy methodology (three nested ideas)

### 1. The collapse IS a Nash equilibrium of a congestion game (reframe, not new run)
Drivers interact through shared charging capacity and a shared feeder. Deviating from
the coordinated schedule (self-serving / reserve-seeking) gives a driver a private
short-term benefit but imposes a **congestion + grid-shape externality** on everyone.
This is a textbook congestion / common-pool game. Its **selfish Nash equilibrium** has
high deviation → driver/fleet/grid gates fail jointly. So the headline collapse is not
an artifact of an arbitrary "severity knob"; it is *the Nash equilibrium of the
uncoordinated game*. This single reframing answers the reviewer's "the drama comes from
your uncalibrated knob" objection: the operating point is an equilibrium, not a setting.

### 2. The target: cooperative Nash Bargaining Solution (NBS)
Define each actor's utility from simulator outputs (below). The cooperative benchmark is
the **Nash bargaining solution**: the feasible operating point maximizing the Nash product
  max  ∏_{k∈{D,F,G}} (U_k − d_k)^{w_k}
over the achievable utility set, with disagreement point d = the selfish-NE (uncoordinated)
outcome. The NBS is unique, Pareto-efficient, and "fair" (axiomatic) — it is exactly
"optimize all three actors' benefits simultaneously." This is the normative target.

### 3. The mechanism: Stackelberg incentive design that IMPLEMENTS the NBS
Drivers are self-interested and will not cooperate for free. The operator (leader) commits
to an **incentive** σ (payment for keeping the coordinated schedule, possibly slack-
dependent) and a **grid signal** π_G (peak penalty). Drivers (followers) play their Nash
equilibrium compliance response. We solve the **bilevel Stackelberg program**: choose
(σ, π_G) so the induced driver equilibrium lands in the all-pass region at minimum
incentive budget — i.e. *implement* the bargaining target as a non-cooperative equilibrium.
**Price of Anarchy** PoA = welfare(NBS) / welfare(selfish NE) quantifies how much the
mechanism is worth.

## Formal game

Players: N drivers i; fleet operator F; grid operator G.

Driver compliance as an **aggregative game**. Driver i complies (keeps the recommended
action) iff net benefit ≥ private cost:
    comply_i  ⇔  σ_i + β·S(ρ)  ≥  κ_i
- ρ = aggregate compliance rate (fraction complying) → S(ρ) = service quality of the
  coordinated schedule, **increasing in ρ** (more cooperation → better service for all):
  the externality. β = how much the driver values that shared service.
- κ_i = driver i's private inconvenience/cost of complying (giving up reserve-seeking),
  heterogeneous and **higher for low-slack/inflexible drivers** (they deviate first;
  consistent with OptimizEV and the paper's Option-A structure).
- σ_i = incentive paid for compliance (operator's lever).
Best response of i depends on others only through ρ ⇒ aggregative game ⇒ Nash equilibrium
is a **fixed point** ρ* = Φ(ρ*; σ, π_G), Φ(ρ) = Pr_i[ σ + β·S(ρ) ≥ κ_i ] = F_κ(σ + β·S(ρ)).
Existence by Brouwer (Φ: [0,1]→[0,1] continuous). Uniqueness / stability checked
numerically via the slope |Φ'| (contraction ⇒ unique & damped-iteration-stable).

Calibration of (κ-distribution, β, S):
- F_κ shape from the slack distribution; level set so that at σ=0 the equilibrium aggregate
  deviation = ACN-anchored severity-1 magnitude (≈5%) — ties the game to data.
- S(ρ) increasing, calibrated so the simulator's realized service metric matches at the
  endpoints ρ∈{selfish NE, full compliance}.
- Incentive response (dρ*/dσ) shape anchored to the OptimizEV opt-in-vs-slack curve.

Utilities (from simulator gate metrics, normalized to [0,1]):
- U_D (driver): delivered-energy ratio & critical-service reliability (− inconvenience).
- U_F (fleet): service completion − queue/cost penalty.
- U_G (grid): − load-shape stress (squared-load, ramp, peak) → grid "comfort".
- Welfare W = w_D U_D + w_F U_F + w_G U_G (and the Nash product for NBS).

## Solver architecture
1. **Inner — driver Nash:** damped fixed-point iteration ρ_{k+1}=(1−η)ρ_k+η Φ(ρ_k) to ρ*(σ,π_G);
   then realize ρ* in the ACN-calibrated simulator (per-vehicle p_keep with aggregate ρ*)
   to read the actual gate outcomes & utilities. Report convergence + |Φ'|.
2. **Outer — Stackelberg:** optimize (σ, π_G) — minimize incentive budget B(σ) s.t.
   all-pass ≥ target; or maximize welfare/feasibility score. Method: coarse grid → local
   refine (Nelder–Mead / 1-D bisection on σ since monotone). Two levers: σ (driver),
   π_G∈{NoGrid,PeakPenalty} (grid) ⇒ show **both levers needed** at high capacity.
3. **Benchmark — NBS & PoA:** sample achievable utility set over (σ,π_G, capacity) grid;
   compute NBS (max Nash product, disagreement = selfish NE); PoA = W(NBS)/W(selfishNE).

## Deliverables
- `gametheory_equilibrium.py`: utility model + driver-NE fixed point + Stackelberg outer
  + NBS + PoA, validated in the simulator.
- Figures: (a) best-response map & fixed point (collapse = selfish NE); (b) all-pass vs
  incentive with the implementation threshold + both-levers-needed at high cap; (c) utility
  simplex / Pareto set with selfish-NE, NBS, and implemented point; (d) PoA vs capacity.
- Manuscript: new Methods (game + mechanism), new Results (equilibrium + PoA), reframed
  Intro/Abstract (collapse = motivating selfish equilibrium; mechanism = contribution).
- GPT-5.5 review of formulation & claims.

## Honesty guardrails
- The driver game is a *calibrated behavioral model*, not a fitted opt-out dataset — state it.
- NBS weights w_k are normative — report sensitivity.
- Incentive "budget" is an illustrative proxy unless a real $ value is justified.
- Keep the ACN demand calibration + IEEE-33 as the validated substrate; the game rides on top.

## Progress log
- [2026-06-16] Design written. Baseline linear-incentive sweep running (selfish-response
  reference, no equilibrium). Next: implement utility model + driver-NE fixed point.

## Progress log (continued)
- [2026-06-16] DELIVERED. Response surface (660 rows) + game-theory module + 243-config
  sensitivity + 4 main figures + graphical abstract + supplementary sensitivity figure.
  Congestion-game model gives UNIQUE selfish NE at d*=5% with all-pass=0 (collapse = the
  equilibrium); bounded Pigouvian incentive sigma*~0.44-0.68 restores all-pass; NBS lifts
  all three actors; PoA~1.47. Robust across 243 configs (PoA in [1.18,1.83], sigma* in
  [0.13,1.77]). Acceptability is a sharp cliff: survives only for d<~1.3% (raw sim).
  Integrated as Section 7 (sec:game) + reframed title/abstract/contributions/conclusions
  /discussion + limitations caveat. Compiles tectonic 40pp, 0 undefined. Package + cover
  letter + highlights + graphical abstract all updated.
- GPT-5.5 consult attempted 4x; all timed out (headless review prompts hang this session).
  Relied on own skeptical review; verified every manuscript number against the results JSON.
- OPEN / next steps (need user steer): (a) quantitative soft-calibration of the compliance
  response to the OptimizEV opt-in-vs-slack curve (approximated from published endpoints);
  (b) more seeds to pin the acceptability cliff threshold; (c) length management (40pp is
  long for AE) — decide what to trim; (d) re-run GPT review when codex is responsive.
