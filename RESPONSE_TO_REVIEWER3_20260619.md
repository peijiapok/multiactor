# Response to Reviewer 3 — Applied Energy (major revision)

We thank Reviewer 3. This revision is more than point fixes: prompted by the comments, we
**re-spined the paper's identity** to make the practical contribution concrete.

## The reframing (addresses #1 and the overall "thin story")
The paper is now framed as **multi-actor compliance feasibility**, not an evaluation framework.
The thesis is concrete and actionable:
> Managed-charging deployment is a multi-actor *participation-feasibility* problem, not a
> trade-off-optimization problem; the jointly-feasible set has a sharp *compliance threshold*
> (~98.5%) below which behavioral non-compliance ejects the system via request-event churn,
> even under a near-optimal scheduler; and a Pigouvian compliance incentive (price of anarchy
> ~1.5), not a better scheduler, is the lever that restores feasibility.
New title, abstract, introduction, gate formulation, and conclusion all carry this. The decision it
changes (Reviewer #1): operators/regulators/tariff designers should treat **participation incentives,
not further scheduling optimization, as the primary deployment lever**, and must secure ~98.5%
compliance. The worked example (#1) is the Pareto demonstration already added: a cost-optimal scheduler
that Pareto-dominates the service scheduler yet has 0% feasibility.

We also add the motivation for **gates vs. multi-objective optimization**: actor requirements are
*non-compensatory* participation (individual-rationality) constraints defining a feasible set;
optimization is secondary and within it; the all-pass rate is a same-episode (chance-constraint)
feasibility probability.

## Major
**#2 (recognized baseline). [NEW RUN]** We re-ran the severity sweep under **Earliest-Deadline-First
(EDF)**, the canonical real-time deadline rule and the family of the ACN adaptive scheduler. EDF shows
the same deviation-driven collapse (feasibility 0.20 at full compliance -> 0.00 by 2.5% deviation).
The two schedulers cleanly separate the effects: **scheduler quality sets the full-compliance level
(ServiceFirst 0.967 vs EDF 0.20), behavioral compliance sets the threshold** -- so the collapse is a
property of behavior, not of LeastLaxity. (run_edf_baseline_20260619.py)

**#3 (behavioral disclosure upfront).** The abstract and introduction now state the behavioral layer is
a model-assumed preference structure calibrated to ACN magnitudes, not fitted. (Already added previously;
now also in the abstract's framing.)

**#4 (game bounded).** The game section already carries an explicit delineation ("does not re-establish
the collapse... adds equilibrium explanation, mechanism-design lever, welfare layer"). Retained.

**#5 (capacity grounding).** Added: workplace/depot port-to-vehicle ratios are typically ~1:5 to 1:20
\cite{muratori2018,powell2022}; the 35%/20% settings (~1 charger per 3/5 concurrent vehicles) sit within
the realistically constrained range that motivates managed charging, not extreme undersupply.

## Minor
- **#6** Voltage is removed from main claims: the IEEE-33 voltage result is condensed to a supplement
  boundary check and explicitly is NOT one of the gates.
- **#7** Ledger discussion already recalibrated to internal self-consistency, scope shortened.
- **#8** 28-day already softened to a single-cell consistency check in conclusions and limitations.
- **#9** The additive-linear preference form is now justified as the deterministic-utility component of
  a random-utility / multinomial-logit discrete choice \cite{mcfadden1974,daina2017}.
- **#10** Supplementary references carry in-text descriptions of their takeaways.

Compiles cleanly (0 undefined references). Note on length: the re-spine adds framing; we have moved the
IEEE-33 figure, ServiceGridWeighted equations, and the fleet-economics analysis to the Supplement to
partly offset.
