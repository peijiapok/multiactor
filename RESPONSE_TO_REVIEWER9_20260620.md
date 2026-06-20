# Response to Reviewer 9 — Applied Energy (minor revision)

We thank the reviewer. This report overlaps closely with the prior round, and all three major
concerns are already addressed in the current manuscript; we give locations and note the two items
that were added most recently. No new simulation was required.

## Major

**1. Describe the three welfare-weight sets [DONE — Supplementary Table tab:weights].**
The three vectors $(w_D,w_F,w_G)$ are now listed explicitly in **Supplementary Table tab:weights**:
equal/utilitarian $(1/3,1/3,1/3)$, driver-heavy $(0.5,0.25,0.25)$, grid-heavy $(0.25,0.25,0.5)$.
The main-text passage (Section sec:game) cross-references it and states these are the three
canonical normative stances bracketing the weight simplex (not chosen to support the finding), with
the PoA above one for all of them — so [1.18, 1.83] is now reproducible.

**2. Stackelberg observability / estimation of $\Phi$ [DONE].**
At the formulation (Section sec:game) we now state that $\sigma^\star$ is a **post-calibration
planning instrument** requiring prior estimation of $\Phi$ (hence $\mu,\beta,s$) from a pilot or
historical dataset, and that **mis-specifying $\Phi$ shifts $\sigma^\star$ within the [0.13, 1.77]
band already mapped by the sweep** without changing the qualitative conclusion. The Limitations
section additionally details how the operator would infer $\Phi$ from session logs, the online
estimation requirement, and noise propagation.

**3. Apply the framework to a published external policy at severity 0 and 1 [DONE].**
The reviewer's named example — the ACN Adaptive Charging Network (Lee et al. 2021) — is covered:
ACN's production scheduler is in the deadline-driven (EDF/least-laxity) family, and we run EDF
through the gates at **severity 0** (Section sec:published, Table tab:published: 94.6% reliability,
0.20 all-pass) **and across the severity sweep** (Section sec:robust, "Sixth": EDF feasibility falls
from 0.20 at full compliance to 0.00 by 2.5% deviation — i.e. severity 1). We also add an
uncoordinated immediate-charging baseline (0%) and map our CostOnly policy to the price-responsive /
valley-seeking family (0%), so three recognized families fail the conjunction for three distinct
reasons.

## Minor

**4. Bootstrap CIs at first statement [DONE].** Present in the abstract, the first Results
paragraph (Section sec:results), and the Conclusions: 96.7% [94.2%, 98.8%] vs. 1.2% [0.0%, 2.9%],
non-overlapping.

**5. Data for peer review [DONE].** Public repository openly available **for review** now:
https://github.com/peijiapok/multiactor.

**6. 28-day single-capacity qualifier in Conclusions [DONE].** The Conclusions read "a
single-capacity 28-day check (35% capacity, five seeds) consistent with this collapse rather than
constituting an independent multi-capacity confirmation," matching the Limitations framing.

**7. Distinguish portable methodology from scenario-specific parameters [DONE — sharpened].**
The Discussion's five-step application guide now explicitly separates the **portable** elements
(same-episode conjunction logic, per-episode evaluation, request-pipeline audit, bootstrap and
threshold-envelope robustness protocol, disaggregation/failure-taxonomy) from the
**scenario-specific** choices (gate set and thresholds, anchor policy, demand calibration, capacity
scenarios, compliance bracket), and states that a threshold is justified for a new deployment by its
own service-level commitments, not by matching ours.

## Build
Compiles with `tectonic`, 0 undefined references/citations.
