# Response to Reviewer 6 — Applied Energy (minor revision)

We thank the reviewer for the positive assessment and for an exceptionally clear set of targeted
requests. All changes below were made without re-running the main experiment campaign; the one new
controller (uncoordinated immediate charging) was run through the existing engine. Manuscript
locations are given by section/figure/table.

## Major

### 1. Apply the framework to recognized published controllers [NEW SUBSECTION + ANALYSIS]
Addressed with a new Results subsection, **"Applying the framework to recognized published
controllers"** (Section sec:published, new **Table tab:published**, new Supplementary
Fig. fig:published). Two points:

- **Our anchors are canonical, not invented.** Least-laxity-first \cite{dertouzos1989llf} and
  earliest-deadline-first \cite{liu1973scheduling} are classical real-time scheduling algorithms,
  and the production ACN adaptive charging scheduler belongs to this deadline-driven family
  \cite{lee2021adaptive}. We now state this explicitly and add the two foundational citations.
- **The framework discriminates among established controllers.** At full compliance (where the
  controller, not behavior, is on trial), all three controllers reach high trip reliability
  (91.9–95.4%) — the conventional single metric — yet the same-episode 14-gate conjunction
  separates them sharply:
  - **EDF** (recognized deadline scheduler): 94.6% reliability, passes the fleet and grid gates
    *entirely*, but clears the joint screen in only **20%** of episodes, because it fails the
    relative critical-service driver gate in 80% — a *subtle* failure invisible to a reliability
    reading.
  - **Uncoordinated immediate charging** (the universal business-as-usual baseline
    \cite{clement2010,ma2013}): 91.9% reliability and lowest cost, but **0%** all-pass through
    severe queue congestion and load-shape degradation — a *gross* failure.
  - The competent least-laxity-anchored service policy passes (1.00 in this cell).

  Three published/canonical controllers, three different verdicts, each invisible to a
  single-metric view — exactly the demonstration the reviewer asked for, and evidence the screen
  is not arbitrarily rejecting sophisticated schedulers.
  Code: `equilibrium_optimization_20260616/run_uncoordinated_baseline_20260620.py`,
  `published_controller_comparison_20260620.py`.

### 2. Show the scenario-averaged vs. same-episode contrast as a primary table [NEW TABLE]
Addressed. In addition to the figure added in the prior round (Fig. fig:marginaljoint), we now
give the explicit gate-by-gate **Table tab:marginaljoint** in Results: the scenario-averaged
(marginal) pass rate for each of the 14 criteria beside the same-episode conjunction. Ten of 14
criteria pass marginally in ≥87% of episodes (mean 0.79), yet the joint rate is 0.012 — the table
is the precise, auditable form of the contrast, placed as a primary result.

### 3. Stackelberg observability [ALREADY ADDRESSED — confirmed]
The Limitations section already contains a dedicated observability paragraph: the operator does not
observe decision-level compliance but would infer Φ from charging-session logs (recommended vs.
delivered actions, opt-out/override rates); the response function must be estimated online and
measurement noise in d* propagates into σ; we therefore present the Stackelberg analysis "as a
characterization of the lever under known response, not as an estimator an operator could run
today," with online noise-robust estimation flagged as a next step. No reviewer-facing gap remains.

## Minor

**4. Gate completeness / non-redundancy.** Strengthened (Section formulation): the count of 14 is
set by the principal sub-concerns (3 driver, 6 fleet, 5 grid), not a target number; monotonicity of
the conjunction means a larger set only lowers feasibility; and we now state explicitly that the
four *binding* criteria are **not mutually collinear** (different actors' service-completion,
waiting, and load-shape metrics), so the result does not rest on a repeated constraint.

**5. Table 2 caption.** The caption now states that the severity-vs-field comparison is a
plausibility bracket, **not a conversion** between directly comparable quantities (per-session
opt-out vs. per-timestep p_keep).

**6. IEEE-33 voltage.** Trimmed. We no longer spend sentences justifying the zero voltage result;
the paragraph now reports the three metrics that vary (substation peak, line loading, losses) and
states in one clause that voltage is base-load-determined and not used for conclusions.

**7. Confidence intervals up front.** The non-overlapping intervals (severity-0 96.7% [94.2%,
98.8%] vs. severity-1 1.2% [0.0%, 2.9%]) now appear in the **abstract** and in the **first Results
paragraph** alongside the point estimates, not only in Section robust.

**8. Data availability for peer review.** The Data Availability statement now points to a public
repository, **https://github.com/peijiapok/multiactor**, openly available **for review** and after
publication, listing the archived analyses, result tables, and figure code; DOI archival at
acceptance.

**9. Capacity justification at first mention.** Added at the first appearance of the 20/35/50%
capacities (Section design): a one-sentence note that these are fractions of base provision
(≈1 charger per 3 and per 5 demanding vehicles), within the realistic constrained range for shared
workplace/depot charging (port-to-vehicle ≈1:5–1:20), with the full justification in Section data.

## Build
Compiles with `tectonic`, 0 undefined references/citations; 2 new citations (Liu & Layland 1973;
Dertouzos & Mok 1989). The new EDF-vs-uncoordinated figure is placed in the Supplement to keep the
main text lean; the primary Table tab:published remains in Results.
