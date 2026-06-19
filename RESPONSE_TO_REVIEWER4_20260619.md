# Response to Reviewer 4 — Applied Energy (major revision)

The central comment -- that the framework must show WHICH episodes fail, under WHAT conditions, and
WHY, to be diagnostic rather than merely declarative -- is exactly right, and we made it the new
centerpiece of the Results.

## Major

**#1 + #4 (disaggregation -- the diagnostic centerpiece). [NEW ANALYSIS, no new sim]**
New Results subsection "Where it fails, which gate binds, and which behavior drives it" + Fig.
diagnostic, disaggregating the collapse three ways, each with a distinct operational implication:
- **WHERE (by capacity):** the severity-1 collapse is uniform across capacity (all-pass 0.038/0.000/
  0.000 at 20/35/50%), and full-compliance feasibility is slightly *lower* at higher capacity. So it
  is NOT an infrastructure problem -- adding chargers does not recover feasibility. (Directly answers
  the reviewer's "concentrated in 20/35% vs uniform" question: uniform -> compliance binds regardless
  of infrastructure.)
- **WHICH GATE (by capacity):** the driver-service gate binds first (lowest-passing, 0.15->0.00),
  ahead of fleet and grid; the grid gate is healthiest at low capacity and degrades as capacity rises.
- **WHICH BEHAVIOR (by type):** the five behavior types separate cleanly -- mild *inattention*
  (churn ~0.95x) only partially degrades (0.83/0.53) and binds the grid gate, while *self-service*
  behaviors (urgency, reserve-seeking, SoC-anxiety, price-sensitivity, SoC+queue) collapse feasibility
  to 0.00, bind the driver gate, and generate 1.3-9.5x request churn. The binding cause is self-service
  churn, not inattention -- so an intervention must suppress reserve/price-driven overriding, not
  benign inattention. (diagnostic_disaggregation_20260619.py)

**#2 (gate-set completeness/non-redundancy).** Added: we do not claim completeness; the set is
representative. Key point -- the feasible set is a *conjunction*, so the all-pass rate is monotonically
non-increasing in the number of gates: adding any further participation constraint can only shrink the
feasible set. Our feasibility is therefore a *conservative* estimate and a more complete gate set would
make the collapse sharper, not rescue it. On redundancy, correlated criteria exist but the binding ones
are distinct mechanisms across different actors (decomposition).

**#3 (Stackelberg observability).** Added a paragraph: the operator must infer compliance from session
logs (recommended-vs-delivered, opt-out/override), must separate genuine deviation from preference
changes/faults, and would estimate the response function online; measurement noise propagates into the
chosen sigma. We present the Stackelberg analysis as a characterization under known response, not an
operator-ready estimator; a noise-robust online estimator is a defined next step.

**#5 (ACN-Sim tolerance).** Added an explicit criterion (+/-10% session-mean, conventional for demand-
model validation and consistent with ACN-Sim's own configuration sensitivity); the ~4% gap (from our
40 kWh tail cap) clears it, and the framework studies relative degradation so a centred model suffices.

## Minor
- **#6** Bootstrap procedure specified: 10,000 non-stratified resamples of the *episode-level* all-pass
  indicators; episode is the resampling unit (independent draws; within-episode autocorrelation already
  collapsed into the per-episode indicator), so a timestep block bootstrap is unnecessary.
- **#7** Robustness tests are consistently numbered First-Sixth.
- **#8** Added a 5-step "Applying the framework to a new fleet, city, or network" guide to the Discussion
  (specify constraints -> calibrate demand -> bracket compliance -> compute & disaggregate feasibility
  -> choose the lever).
- **#9** Preference-function form justified via random-utility/MNL (McFadden 1974, Daina 2017).
- **#10** Figure references standardized to \figref / Supplementary \figref.

Compiles cleanly (0 undefined references). The disaggregation converts the framework's output from a
verdict into a diagnosis that points to the corrective action.
