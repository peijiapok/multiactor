# Response to Reviewer 7 — Applied Energy (minor revision)

We thank the reviewer for a precise and constructive report. Several of the requested changes had
already been incorporated in the current revision (the version under review appears to predate
them); we point to where each now lives, and we have made targeted additions for the points that
were genuinely open (#2 reassurance, #3 mapping, #7, #9). No new simulation was required.

## Major

### 1. Move the scenario-averaged vs. same-episode contrast to a primary Results display [DONE]
This is now a primary result in Section~\ref{sec:results}, not a Discussion aside. It appears as
**Fig. fig:marginaljoint** (the marginal dashboard vs. the joint conjunction) and, immediately
after, as the explicit gate-by-gate **Table tab:marginaljoint**, which lists each of the 14
criteria's scenario-averaged pass rate beside the same-episode all-pass (0.012). The text states
the 79%-marginal-to-1.2%-joint gap as "the framework's central measurement."

### 2. Describe the three welfare-weight sets [DONE + reassurance added]
The three sets are defined in Section~\ref{sec:game} (game results): an **equal/utilitarian**
weighting (1/3, 1/3, 1/3), a **driver-heavy** weighting (0.5, 0.25, 0.25, user-/adoption-centric),
and a **grid-heavy** weighting (0.25, 0.25, 0.5, system-operator), and they also appear in the
sensitivity-figure caption. We have **added a sentence** stating explicitly that these are the
three canonical normative stances bracketing the weight simplex, were **not** chosen to support the
price-of-anarchy finding, and that the PoA stays above one for all of them.

### 3. Apply the framework to an external published controller [DONE + strengthened]
Section~\ref{sec:published} ("Applying the framework to recognized published controllers") now
does this with **Table tab:published**. We have **strengthened the mapping to the reviewer's three
named examples**:
- **ACN adaptive charging** — covered directly: we run Earliest-Deadline-First (EDF), and the
  production ACN adaptive scheduler is a deadline-driven member of this family \cite{lee2021adaptive}.
  EDF reaches 94.6% trip reliability yet clears the same-episode conjunction in only 20% of episodes.
- **Valley-filling / price-responsive** — our CostOnly policy is a deliberately simplified member of
  this family (cost-window charging); it is Pareto-efficient on cost and reliability yet scores 0%
  same-episode all-pass (Fig. fig:pareto), so this family fails the conjunction too, for a third
  distinct reason. We are careful not to oversell CostOnly as a full load-variance-minimizing
  valley-fill.
- **ADMM / decentralized optimization** — we note that, because the screen is a post-hoc evaluation
  of any controller's realized per-episode trajectories, an ADMM or projected-gradient scheme can be
  passed through the identical gates without modifying the method; we flag this as a natural
  extension rather than implement it.
- We also add an **uncoordinated immediate-charging** baseline (0% all-pass via congestion), so the
  set spans naive, sophisticated-deadline, and price-responsive control.

### 4. Procedural guidance for applying the framework elsewhere [DONE]
The Discussion contains a five-step "Applying the framework to a new fleet, city, or network"
guide (specify participation constraints → calibrate demand → bracket compliance → compute and
disaggregate feasibility → choose the lever), which separates the portable methodology (conjunction
logic, per-episode evaluation, audit, disaggregation) from the scenario-specific inputs (the 14
thresholds, capacity levels, ACN demand).

### 5. Bootstrap intervals with the primary result statements [DONE]
The non-overlapping intervals (severity-0 96.7% [94.2%, 98.8%]; severity-1 1.2% [0.0%, 2.9%]) now
appear in the **abstract** and in the **first Results paragraph** (Section~\ref{sec:results}),
alongside the point estimates, in addition to the robustness section.

### 6. Drop the IEEE-33 voltage discussion [DONE]
Trimmed. The feeder paragraph now reports only the three varying metrics (substation peak, line
loading, losses) and states in a single clause that voltage is base-load-determined and not used
for conclusions.

## Minor

### 7. Coefficient magnitudes are not calibrated; behavioral validity of the function is open [DONE]
We have **added an explicit statement** in the robustness section: the coefficient magnitudes in
Eq. severitypref (e.g. the 26:1 critical-to-laxity ratio) are author-chosen, not calibrated to a
behavioral dataset—the ablation bounds but does not validate them; and the citations ground the
preference's **term structure**, not its additive-logit **functional form** or parameters, so the
behavioral validity of the preference function as a whole remains an open empirical question that
only decision-level data could settle. We make no claim it is a fitted model.

### 8. Data availability for peer review [DONE]
The Data Availability statement points to a public repository,
**https://github.com/peijiapok/multiactor**, openly available **for review** (now, not only at
acceptance), listing the gate-scoring, game, Pareto, scheduler-baseline, oracle, and disaggregation
code, the result tables and seed information, and the figure code; DOI archival at acceptance.

### 9. Add the interpretive caveat to the abstract [DONE]
The abstract's mechanism sentence now reads "within a calibrated but deliberately interpretive
game-theoretic model—subordinate to the screening result and not an empirical mechanism claim—…",
matching the Section~\ref{sec:game} language, so the game result cannot be overread as empirical.

## Build
Compiles with `tectonic`, 0 undefined references/citations.
