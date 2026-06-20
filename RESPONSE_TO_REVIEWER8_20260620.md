# Response to Reviewer 8 — Applied Energy (minor revision)

We thank the reviewer for the careful and positive assessment. Two of the three major requests were
already met in the current revision (the reviewed version predates them); we point to their
locations and have made two targeted additions for the genuinely open items (the welfare-weight
supplementary table and the Stackelberg information sentence at the formulation). No new simulation
was required.

## Major

### 1. Describe the three welfare-weight sets — now in a supplementary table [NEW TABLE]
Addressed with a new **Supplementary Table tab:weights**, listing the three weight vectors
$(w_D,w_F,w_G)$ explicitly:

| Label | Stance | $w_D$ | $w_F$ | $w_G$ |
|---|---|---|---|---|
| Equal / utilitarian | no actor prioritized | 1/3 | 1/3 | 1/3 |
| Driver-heavy | user-/adoption-centric | 0.50 | 0.25 | 0.25 |
| Grid-heavy | system-operator | 0.25 | 0.25 | 0.50 |

The main-text description in Section sec:game now cross-references this table. We also state that
these are the three canonical normative stances bracketing the weight simplex (not chosen to support
the result) and that the PoA stays above one for all of them, so the [1.18, 1.83] range and the
"above one in every tested case" claim are now fully reproducible.

### 2. Stackelberg information requirement [NEW SENTENCE at the formulation + existing Limitations]
Addressed at the formulation itself (Section sec:game), where $\sigma^\star$ is introduced: we now
state that $\sigma^\star$ is a **post-calibration planning instrument**, not a quantity an operator
could set without prior information — computing it requires estimating the compliance-response
function $\Phi$ (hence $s$ and $\beta$) by fitting $\Phi$ to a pilot or historical dataset before
deployment. Because $\sigma^\star$ is monotone in these parameters, **mis-specifying $\Phi$ shifts
the required incentive within the [0.13, 1.77] band already mapped by the sweep** without changing
the qualitative conclusion (over-estimating responsiveness under-provides the incentive and slows
convergence, which re-estimation corrects). The planning value is the existence and bounded
magnitude of a restoring incentive, not a single deployable number. This complements the dedicated
observability paragraph already in the Limitations (operator infers $\Phi$ from session logs, online
estimation, noise propagation).

### 3. Apply the framework to an external published controller [DONE]
Already addressed: Section sec:published ("Applying the framework to recognized published
controllers"), Table tab:published. We apply the screen to **Earliest-Deadline-First** — the family
of the production **ACN adaptive charging** scheduler (Lee et al. 2021), the reviewer's named
example — which reaches 94.6% trip reliability yet clears the same-episode conjunction in only 20%
of episodes (failing the relative critical-service driver gate in 80%). We add an **uncoordinated
immediate-charging** baseline (0% all-pass via congestion) and map our existing **CostOnly** policy
to the price-responsive / valley-seeking family of Ma et al. (2013) (Pareto-efficient yet 0%
all-pass). Three external/recognized families, three distinct failure modes — demonstrating the lens
generates non-trivial conclusions outside our own policy universe.

## Minor

### 4. Bootstrap intervals at first statement [DONE]
The non-overlapping intervals (96.7% [94.2%, 98.8%] vs. 1.2% [0.0%, 2.9%]) now appear in the
**abstract**, in the **first Results paragraph** (Section sec:results, beside the point estimates),
and in the Conclusions — not only in the robustness section.

### 5. Data for peer review [DONE]
The Data Availability statement points to a public repository,
**https://github.com/peijiapok/multiactor**, **openly available for review** now (not only at
acceptance), listing the gate-scoring, game, Pareto, scheduler-baseline, oracle, and disaggregation
code, the result tables and seeds, and the figure code; DOI archival at acceptance.

### 6. Scenario-averaged vs. same-episode table [DONE]
Already present: **Table tab:marginaljoint** in Results gives the gate-by-gate scenario-averaged
pass rate for each of the 14 criteria beside the same-episode conjunction (0.012), with the binding
criteria highlighted — the definitive illustration of what same-episode screening adds.

### 7. Guidance for applying the framework elsewhere [DONE]
Already present: the Discussion's five-step "Applying the framework to a new fleet, city, or
network" guide separates the portable methodology (conjunction logic, per-episode evaluation, audit,
disaggregation) from the scenario-specific choices (the 14 thresholds, anchor policy, capacity,
episode horizon).

## Build
Compiles with `tectonic`, 0 undefined references/citations.
