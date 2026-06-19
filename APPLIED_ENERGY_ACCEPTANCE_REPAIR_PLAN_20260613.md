# Applied Energy Acceptance Repair Plan - 20260613

## Status

This is a repair plan for moving the EV charging multi-actor manuscript from an internally useful draft toward an Applied Energy submission. The plan responds to four concrete problems found in the current revised manuscript:

1. the revised draft has only 17 references, while a later submission variant has 34;
2. the manuscript still contains journal-inappropriate process language such as "Applied Energy style", "result CSVs", "scripts, CSV outputs", and "For Applied Energy readers";
3. the policy families are difficult to understand without reading equations and code;
4. the ServiceGridWeighted coefficients and Figure 2 are not defensible enough for peer review.

A Claude external-review attempt was blocked by the environment because it would send nonpublic manuscript material outside the workspace. This plan is therefore Codex-only unless the user explicitly approves external sharing.

## Target Standard

The paper should read as a real Applied Energy energy-systems manuscript, not as a project report. The main contribution remains:

> EV charging control should be evaluated as a three-actor acceptability problem: driver service, fleet/facility operation, and grid impact can fail separately even when a single metric appears acceptable.

The paper must not claim FleetBalanced superiority, true energy-demand amplification, feeder validation, threshold-independent robustness, or optimality of heuristic policies.

## Phase 1 - Fix Submission Credibility Before Any More Writing

### Step 1.1 - Choose one authoritative manuscript source

Use the latest three-actor revised LaTeX as the structural base, but merge improvements from the submission-oriented file.

Input candidates:

- `APPLIED_ENERGY_MANUSCRIPT_DRAFT_REVISED_THREE_ACTOR_20260609.tex`
- `APPLIED_ENERGY_MANUSCRIPT_SUBMISSION_20260610.tex`

Output:

- `APPLIED_ENERGY_MANUSCRIPT_SUBMISSION_REPAIR_20260613.tex`
- `APPLIED_ENERGY_MANUSCRIPT_SUBMISSION_REPAIR_20260613.md` if needed

Pass criterion:

- one manuscript file is treated as authoritative; no split-brain state where one draft has 17 references and another has 34.

### Step 1.2 - Merge and expand references with a citation-purpose matrix

The revised draft has 17 references. That is not enough for Applied Energy unless the paper is extremely narrow, which this is not. The later submission file has 34 references, but the expansion was not merged back into the latest revised/three-actor draft.

Actions:

1. Merge the 34-reference bibliography from `APPLIED_ENERGY_MANUSCRIPT_SUBMISSION_20260610.tex` into the authoritative repaired draft.
2. Add only targeted references that support specific claims. Do not pad the list.
3. Target 40-55 references for a full Applied Energy research article.
4. Build a citation-purpose table with these columns:
   - citation key;
   - exact claim supported;
   - section used;
   - role: framing / method precedent / behavior evidence / grid impact / benchmark / software;
   - limitation;
   - DOI or URL verified.

Minimum reference families:

- coordinated and decentralized EV charging control;
- multi-objective managed charging and fleet/depot charging;
- EV charging service quality, reliability, fairness, and waiting/queue metrics;
- user acceptance, opt-out, override behavior, and managed-charging participation;
- demand response and behavioral flexibility under user control;
- distribution feeder impacts of EV charging;
- IEEE-33 benchmark origin and common use;
- pandapower or power-flow software documentation;
- cost-service trade-off precedent, including the Woo et al. reference paper;
- evaluation frameworks involving multiple stakeholders or acceptability constraints.

Pass criterion:

- every paragraph in the Introduction and Methods that makes a literature claim has at least one appropriate reference;
- no exact numeric threshold is implied to be literature-proven unless it actually is;
- references are verified, not guessed.

## Phase 2 - Remove All Project-Report Language

### Step 2.1 - Purge forbidden journal-inappropriate phrases

Search and replace the following:

| Current wording | Problem | Replacement |
|---|---|---|
| "in an Applied Energy style" | sounds like manuscript self-commentary | "cost-service trade-off analysis" or "EV charging facility cost-service analysis" |
| "For Applied Energy readers" | addresses journal audience awkwardly | "This study contributes a reproducible energy-systems evaluation framework..." |
| "result CSVs" | file-format/process language | "persisted simulation outputs" or "recorded simulation outputs" |
| "scripts, CSV outputs" | project-package language | "analysis code, simulation outputs, and trace files" only in Data/code availability, not main Results |
| "manuscript reports" | internal process tone | "the analysis reports" or direct substantive wording |
| "evidence package" | internal audit tone | "simulation campaign" or "analysis" |
| "controller-superiority story" | informal | "controller-superiority claim" or "policy-ranking claim" |

Pass criterion:

- no local file format language appears in Introduction, Methods narrative, Results interpretation, Discussion, or Conclusion;
- data/code details are restricted to Data/code availability and reproducibility notes;
- the conclusion does not name the target journal audience.

### Step 2.2 - Recast the Introduction as a publishable literature argument

New Introduction logic:

1. EV charging creates local energy-system coordination pressure.
2. Existing work optimizes charging for cost, service, grid, or decentralized coordination.
3. User acceptance and behavior studies show managed charging depends on trust, control, inconvenience, and compliance.
4. Distribution studies show grid constraints cannot be ignored.
5. Gap: policy evaluation often reports single metrics or separated stakeholder outcomes rather than same-episode driver/fleet/grid acceptability.
6. Contribution: a three-actor acceptability framework plus request-pipeline audit and feeder screen.

Pass criterion:

- the Introduction never says the paper is written in the style of another paper;
- it states a genuine literature gap and explains why the result matters beyond this simulator.

## Phase 3 - Make Policy Families Understandable Before Equations

### Step 3.1 - Add a reader-facing policy family table

Insert this table before the policy equations.

Columns:

- policy family;
- layer: driver behavior / fleet dispatch / grid adjustment;
- decision principle in plain language;
- controlled action;
- actor primarily protected;
- expected risk/trade-off;
- role in experiments;
- evidence status/reference.

Rows:

- FullyCompliant;
- severity 1, 2, 3 behavior variants;
- LeastLaxity;
- CostOnly;
- QueueAware;
- ServiceFirst / merged Balanced;
- ServiceGridWeighted;
- NoGridIncentive;
- GridPeakPenalty;
- FleetBalanced audit row, if kept in supplement only.

Pass criterion:

- a reader can understand all policy names before seeing any equation;
- CostOnly and QueueAware are clearly labeled diagnostic single-objective heuristics, not state-of-the-art baselines;
- ServiceGridWeighted is clearly labeled a heuristic comparator, not an optimizer.

### Step 3.2 - Split policy explanation into three subsections

Replace the dense current policy section with:

1. Driver behavior variants;
2. Fleet dispatch policies;
3. Grid adjustment policies.

Each subsection should contain:

- one paragraph of plain-language purpose;
- one compact equation or rule;
- one sentence explaining what claim it can and cannot support.

Pass criterion:

- no policy is introduced first through a symbol-heavy formula;
- Figure 1 and the algorithm use the same layer names as the text.

## Phase 4 - Defend or Simplify ServiceGridWeighted Coefficients

### Step 4.1 - Create a coefficient provenance table

The current formula

`S_i = 320 C_i + 175 L_i + 120 T_i + 95 D_i + 55 X_i`

looks arbitrary. This is a serious reviewer risk.

Add a table with:

- coefficient;
- term definition;
- implementation source;
- value source: fixed heuristic / code default / calibrated / literature;
- whether tuned on outcomes: yes/no;
- qualitative rationale;
- dominance relation;
- sensitivity status.

Required honest wording:

- If these weights were chosen by the authors and not calibrated, say: "The coefficients are fixed ordinal heuristic weights chosen before the reported sweep; they are not estimated from data and are not claimed to be optimal."
- If they are code artifacts, say that explicitly and downgrade ServiceGridWeighted to a comparator only.

Pass criterion:

- no reader can reasonably say the numbers appear without explanation.

### Step 4.2 - Add a dominance proof or remove fake precision

One of these must happen.

Option A - Keep the exact coefficients:

- prove the intended dominance logic in text;
- show maximum possible grid penalty cannot override protected-request eligibility because eligibility prevents critical/low-SoC requests from being deferred;
- explain that the weights rank low-risk flexible requests, not all service requests.

Option B - Rescale the formula:

- convert to interpretable normalized weights, e.g., `3.20`, `1.75`, `1.20`, `0.95`, `0.55`, if rankings are unchanged;
- state that scaling does not change decisions;
- avoid unnecessary apparent precision.

Option C - Move full formula to supplement:

- main text explains principle;
- supplementary table gives exact reproducibility values.

Recommended path:

- Use Option B + C: normalized weights in main text, exact code values in supplement, with a statement that scaling preserves ranking.

Pass criterion:

- ServiceGridWeighted becomes reproducible and defensible without pretending to be an optimized controller.

### Step 4.3 - Decide whether a small sensitivity check is needed

If reviewers could say the result depends on random weights, run a small coefficient sensitivity/ablation:

- base ServiceGridWeighted;
- no price penalty;
- no peak penalty;
- doubled grid penalty;
- service-only scoring;
- equal normalized weights.

Minimum run:

- weekly, 35% capacity, seeds already used, severity 0 and severity 1, NoGrid and PeakPenalty if compatible.

Pass criterion:

- if all-pass collapse remains, the main behavioral conclusion does not depend on exact ServiceGridWeighted weights;
- if it changes, report threshold/policy dependence honestly.

This is the only optional new experiment in the plan. Do not add broad new experiments.

## Phase 5 - Rewrite Algorithm Section for Comprehension

### Step 5.1 - Replace dense algorithm prose with a pipeline algorithm

Algorithm 1 should be:

1. initialize episode;
2. generate driver request events under behavior variant;
3. compute fleet recommendation under selected fleet policy;
4. apply grid adjustment under selected grid policy;
5. allocate charging subject to capacity;
6. update request/session ledger;
7. compute driver, fleet, grid metrics;
8. apply actor gates;
9. record failure pattern.

Pass criterion:

- Algorithm 1 explains the whole simulator/evaluation pipeline, not only one controller.

### Step 5.2 - Move policy-specific math to a compact rule table

Table columns:

- policy;
- score/rule;
- eligibility constraint;
- action selected;
- actor risk.

Pass criterion:

- the reader can map each policy to Algorithm 1 without hunting through paragraphs.

## Phase 6 - Redesign Figure 2 Around the Main Result

### Step 6.1 - Replace current Figure 2 if it is visually hard to parse

Current Figure 2 should not ask readers to decode too many policy/behavior/grid combinations at once.

Recommended new main Figure 2:

- Panel A: heatmap with severity 0-3 on rows and actor gates on columns: driver pass, fleet pass, grid pass, all-pass.
- Panel B: grouped bars or dot plot comparing ServiceFirst and ServiceGridWeighted all-pass by severity.
- Add direct annotation: "All-pass falls to 0 at severity 1 under specified gates."

Move the full policy-by-actor matrix to supplementary material.

Pass criterion:

- a reader understands the main result in 10 seconds;
- the caption states the claim without overclaiming;
- Figure 2 no longer tries to carry every policy comparison.

### Step 6.2 - Add one simple policy-family schematic if needed

If the policy table is still dense, add a small diagram:

Driver behavior -> fleet policy -> grid policy -> final charging -> actor gates.

But do not add decorative graphics.

Pass criterion:

- the paper explains both the system pipeline and the evidence result visually.

## Phase 7 - Rebuild Manuscript Sections in Acceptance-Oriented Order

Recommended order of edits:

1. Fix references and literature positioning.
2. Remove all journal-unfit wording.
3. Add policy family table.
4. Rework ServiceGridWeighted coefficient explanation.
5. Rewrite Algorithm/Methods flow.
6. Redesign Figure 2.
7. Recheck Results for result-vs-method clarity.
8. Rewrite Conclusion without target-journal audience language.
9. Compile PDF and inspect tables/figures.
10. Run hostile reviewer checklist.

Do not start with the abstract. The abstract should be rewritten last after the manuscript logic is fixed.

## Phase 8 - Acceptance-Oriented Quality Gates

Before calling the paper submission-ready, require all of these:

- Reference count is at least 40 unless a coauthor deliberately approves fewer with justification.
- Every reference has a verified DOI/URL or is clearly labeled as official documentation.
- No phrase remains: "Applied Energy style", "Applied Energy readers", "result CSVs", "evidence package", "old story", "controller-superiority story".
- Every policy has a plain-language definition before equations.
- ServiceGridWeighted coefficients have provenance and dominance explanation or sensitivity evidence.
- Figure 2 makes the main result obvious without requiring text.
- CostOnly/QueueAware are labeled diagnostic heuristics.
- FleetBalanced remains audit/supplement only unless new evidence shows final-action differences.
- Behavioral result is event churn, not true energy-demand amplification.
- IEEE-33 remains a representative feeder stress screen, not validation.
- Thresholds are normative and threshold-conditioned.
- Conclusion states contribution to energy-system evaluation, not to "Applied Energy readers".

## Final Recommended Deliverables

Create:

1. `APPLIED_ENERGY_MANUSCRIPT_SUBMISSION_REPAIR_20260613.tex`
2. `APPLIED_ENERGY_MANUSCRIPT_SUBMISSION_REPAIR_20260613.pdf`
3. `POLICY_FAMILY_EXPLANATION_TABLE_20260613.md`
4. `SERVICEGRIDWEIGHTED_COEFFICIENT_PROVENANCE_20260613.md`
5. `REFERENCE_EXPANSION_AND_CITATION_PURPOSE_TABLE_20260613.csv`
6. `FIGURE2_REDESIGN_REPORT_20260613.md`
7. `JOURNAL_LANGUAGE_PURGE_CHECKLIST_20260613.md`
8. `APPLIED_ENERGY_PRE_SUBMISSION_GATE_REPORT_20260613.md`

## Hard Verdict

The user criticism is correct. The current revised manuscript is not ready for Applied Energy submission because the reference coverage, journal tone, policy explanation, coefficient provenance, and Figure 2 readability are not yet strong enough. The paper can still become submission-quality, but only if the next revision is structural and evidence-disciplined, not just language polishing.
