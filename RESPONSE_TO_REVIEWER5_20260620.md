# Response to Reviewer 5 — Applied Energy (major revision)

We thank Reviewer 5 for a careful, constructive report. The two substantive requests —
an oracle counterfactual on scheduling, and elevating the marginal-vs-joint contrast to a
primary figure — materially strengthened the paper. Below we respond point by point;
manuscript changes are located by section/figure. New analyses were run from the existing
simulation outputs (no new simulation was required); all code and derived data are now public
(point 10).

## 1 — Oracle counterfactual: can a better/different scheduler rescue feasibility? [NEW ANALYSIS]
Addressed with a new oracle analysis (Section robust, "Seventh"; new **Fig. (fig:oracle)**).
We state the intervention model explicitly (a scheduler observes the realized request stream
and allocates power/queue order; it does not coerce a critical request, pre-empt declined
energy, or see the future beyond the deadline/laxity signal). Under this model we bound what
scheduler choice can achieve at severity 1: the **best single deployable scheduler reaches
only 1.7% all-pass**, and a **per-episode oracle that retrospectively assigns each episode its
best-passing scheduler** — an upper bound no controller can exceed — **reaches just 5.0%**
(95% interval [0.0%, 11.7%]), versus 96.7% at full compliance. The residual is entirely at the
lowest (20%) capacity and is exactly 0% at 35%/50%; the EDF family confirms the same ceiling.
The reason is structural and follows from the diagnosis: the binding gate is the
critical-requested-not-delivered driver guarantee, set by whether deviating vehicles depart
from their recommended critical-service schedule — an action in the driver's choice set, not
the scheduler's. This confirms the paper's spine (the infeasibility is inherent to the
condition, not the scheduler) and motivates the compliance-incentive lever.
Code: `equilibrium_optimization_20260616/oracle_scheduler_counterfactual_20260620.py`.

## 2 — Scope of the quantitative claims [DONE]
Addressed. The abstract and Conclusions now state the quantitative findings are established for
**US workplace and campus charging populations (the ACN-Data sites)**, with generalization to
residential-overnight, public fast-charge, and non-US arrival patterns left to future work
(this matches the cross-site robustness paragraph in Section extval). The framework itself
(participation-constraint gates, same-episode feasibility) remains portable; only the numeric
thresholds and magnitudes are population-specific.

## 3 — Justify the factorial design [DONE]
Addressed (Section design). We now state that the design is a deliberate **full factorial**
over (behavior severity × capacity × grid policy × fleet policy) rather than one-factor-at-a-time,
because the central claim is about a same-episode **interaction** — that deviation breaks
feasibility regardless of the infrastructure/policy context — which can only be established by
crossing the behavioral factor with the deployment factors, and because the factorial enables
the diagnostic disaggregation that attributes residual feasibility to specific capacity/gate cells.

## 4 — Scenario-averaged vs same-episode as a PRIMARY figure [NEW FIGURE]
Addressed with a new primary figure (**Fig. (fig:marginaljoint)**) placed at the
marginal-vs-joint paragraph in Results. Panel (A) is the scenario-averaged dashboard a planner
would conventionally read (9 of 14 criteria pass in ≥98% of episodes; mean fraction-of-criteria
= 0.79, ≈11 of 14 — looks acceptable); panel (B) shows that requiring all 14 in the same
episode collapses acceptability to 1.2%. We frame the 79%-marginal-to-1.2%-joint gap as the
core quantity the framework measures.
Code: `equilibrium_optimization_20260616/scenario_averaged_vs_jointly_feasible_20260620.py`.

## 5 — Report uncertainty on the 1.2% headline [DONE]
Addressed. The 1.2% severity-1 all-pass now carries its **95% episode-bootstrap interval
[0.0%, 2.9%]** in both the abstract and the Conclusions (it was already reported in Section
robust); the full-compliance 96.7% interval [94.2%, 98.8%] is non-overlapping.

## 6 — Units of the preference-score coefficients (Eq. severitypref) [DONE]
Addressed (Section design). We now define all six terms (cheap-window, reserve need,
target-SoC deficit, deadline deficit, SoC, laxity), state that **every term is normalized to
[0,1]** so the coefficients are **dimensionless utility weights** and the score is an ordinal
utility index (not a physical quantity), and note that only the relative ordering/ratios matter
— with robustness to the weights established in Section robust.

## 7 — Severity terminology defined early [DONE]
Addressed. The Introduction now defines the **0–3 severity scale at first use** (severity 0 =
full compliance; 1/2/3 ≈ 5%/20%/45% vehicle-timestep deviation), with a forward reference to
the precise definitions in Section design (Table severityparams), so a reader no longer meets
"severity 1" cold.

## 8 — LeastLaxity anchor: clarify its dual role [DONE]
Addressed (Section formulation, baselines). We now explicitly separate the anchor's two roles —
fixed **reference** for the relative gates vs. one deployable **scheduler** among those
evaluated — and explain why this is not circular: the anchor is computed once under full
compliance and held fixed (gates measure degradation from a fixed reference, not a moving
target), and re-running the entire screen with an EDF anchor reproduces the same threshold
(Section robust, "Sixth"), so the result is not an artifact of using LeastLaxity as both
reference and candidate.

## 9 — Ground the behavior types in managed-charging literature [DONE]
The non-compliant preference structure is grounded term-by-term in the behavioral literature
(reserve/range anxiety; time-of-use price sensitivity; deadline-driven opt-out), and the
additive-linear score is identified as the deterministic-utility component of a multinomial-logit
discrete choice — the standard travel/charging-behavior model. The five behavior types
(self-service, limited-attention, price-sensitive, SoC-compliance, SoC-queue-compliance) are
operationalizations of this one preference under different keep-probability and margin settings.
We have retained and signposted this grounding (Section design).

## 10 — Data and code availability [DONE]
Addressed. The Data and code availability statement now points to a live public repository,
**https://github.com/peijiapok/multiactor**, openly available for review and after publication,
containing the game-theoretic, Pareto, scheduler-baseline, oracle, and disaggregation analyses,
the response-surface/severity result tables, and the figure code; the demand model is calibrated
to public ACN-Data. The repository will be archived with a citable DOI at acceptance.

## Net effect on length
These changes add two figures and the oracle analysis (+3 pp). We are separately compressing the
manuscript (candidate moves of secondary figures/tables to the Supplement) to offset this and
address the length concern raised across reviews; the compression does not touch the new
primary evidence above.
