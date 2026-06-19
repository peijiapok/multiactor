# Response to Reviewer — Applied Energy (major revision)

We thank the reviewer for an unusually constructive and specific report. Below we respond
point by point; manuscript changes are quoted or located by section. New analyses were run
where requested; nothing was fabricated, and items needing proprietary data are stated as such.

## Major concerns

**M1 — Binary collapse is threshold-conditioned; lead with graded index / label tables.**
Addressed. The abstract and the Results now **lead with the AND-free evidence**: the collapse
"is already visible at the single-actor level (the driver gate alone falls to 5%) and driven by a
few criteria failing hard (critical requests-not-delivered fail in 92% of episodes), not by the
strict 14-gate conjunction." We added that **9 of the 14 criteria still fail in <2% of episodes**,
so the degradation is concentrated, not a fragile-AND artifact. The main severity table caption now
states the all-pass indicator is threshold-conditioned and points to the single-actor/graded columns
and Section (robustness). The strict 1.2% is presented as the aggregate consequence, read with the
graded fraction-of-criteria index (0.79).

**M2 — Game calibrated to reproduce the finding; incentive tested only within the model.**
Addressed by **narrowing the claim** (no end-to-end empirical mechanism claimed). We added to
Section (mechanism): the result "separates into two mappings… The *physical* mapping from aggregate
deviation d to acceptability is simulator-validated (every all-pass(d) is a real simulator output);
the *behavioral* mapping from an incentive σ to a lower equilibrium deviation is a calibrated model
assumption. We therefore claim only the conditional—*if* an incentive reduces deviation to d, the
simulator shows acceptability recovers accordingly—and treat whether an incentive elicits that
compliance as a design hypothesis for field validation." We also already state the equilibrium
placement is "a reframing, not an independent discovery."

**M3 — Non-compliant preference *form* sensitivity untested. [NEW RUN]**
Addressed with a new **preference-coefficient ablation** (Section robust, "Fifth"). Holding the
severity-1 deviation rate at 5% (low-slack-structured), we re-ran the screen under **8 preference
variants**: base; all-weights-equal (removes ordering); ordering reversed; reserve term dropped;
SoC-dominated; and ±50% scaling. **Same-episode all-pass = 0.000 for every variant.** We frame it
modestly: "within this family of non-compliant preferences, the collapse is driven by the prevalence
and placement of deviation, not by a finely tuned non-compliant utility model." Code/results:
`equilibrium_optimization_20260616/run_preference_ablation_20260619.py`, `preference_ablation_summary_20260619.csv`.

**M4 — LeastLaxity anchor consequential and unjustified.**
Addressed. We now justify the anchor and report its **absolute** performance: "LeastLaxity… is
near-optimal for deadline-driven service and is not itself a poor baseline: under full compliance it
achieves 93.6% trip reliability with a 95th-percentile queue wait of essentially zero minutes, so
passing a relative driver gate corresponds to genuinely high absolute service rather than a low bar…
a weaker anchor would only make the gates easier to pass, not harder."

**M5 — IEEE-33 occupies disproportionate space.**
Addressed. The IEEE-33 results are **condensed to a single paragraph** and **Figure 6 moved to the
Supplement**; the paragraph notes interpretable substation-peak/line-loading/loss deltas and that
voltage deltas are exactly zero (a non-binding base-load-determined check), and connects the grid
gate to the load-shape sub-gate instead.

## Minor concerns

**m6 — Define the capacity baseline.** Added: "100% capacity denotes the base charger provision of
the site (40 home, 5 work, 5 public slots per location group); the percentages are fractions of that
base, so 35% provides roughly one charger per three concurrently demanding vehicles… stress settings,
not claims about typical provisioning."

**m7 — 28-day uses one capacity / 5 seeds.** Added to Limitations: the 0% 28-day figure is "a
single-capacity confirmation with higher per-estimate variance… consistent with, not a stronger
generalization of, the weekly collapse."

**m8 — "No energy amplification" is architecture-dependent.** Added: the churn-vs-amplification
decomposition "is mediated by the simulator's ledger accounting… a simulator with a different
demand-accounting structure could partition the same behavior differently"; what is
architecture-independent is that the failure is driven by request timing/frequency, not total energy.

**m9 — PoA normalization-sensitive. [NEW ANALYSIS]** Added a direct alternative-normalization check:
under ratio-to-full-compliance normalization the price of anarchy is **1.50/1.50/1.56** vs 1.48/1.46/
1.48 under min–max—"the magnitude near 1.5 is robust to this normalisation choice, while remaining a
relative rather than absolute-surplus index."

**m10 — ServiceGridWeighted adds limited value.** Already condensed: equations + coefficient table
moved to the Supplement in the prior revision; the main text is a short description + the eligibility
dominance defense (which preempts the magic-number concern), incl. the all-weights-equal ablation.

**m11 — Load-factor gate notation.** Rephrased: "ΔLF ≥ −0.05 should be read as 'load factor must not
decline by more than 5 percentage points relative to the anchor.'"

## Specific questions

**Q1 — Threshold determination + relaxation table. [NEW ANALYSIS]** The envelope discussion now states
explicitly: "recovering a *majority* (>50%) of severity-1 all-pass requires loosening *every* gate
simultaneously by more than about 2× (the 2× envelope reaches 0.46; only 3× clears 0.5), whereas no
single- or few-gate relaxation exceeds 0.054."

**Q2 — FleetBalanced.** **Removed** from the manuscript (it was decision-equivalent to ServiceFirst
and only invited this question).

**Q3 — σ* to monetary tariff.** Added an order-of-magnitude anchor: managed-charging pilots move
per-session compliance with incentives "on the order of a few dollars per session," which sets the
rough target scale; we do not claim a precise utility-to-money conversion.

**Q4 — Generalization beyond US workplace arrivals.** Added: the cross-site test establishes
robustness to demand *magnitude* across real populations "but not to qualitatively different arrival
distributions; generalization to residential overnight, public fast-charge, or non-US arrival patterns
is left to future work."

## Positive aspects (retained and, per the reviewer, given more prominence)
The same-episode joint-feasibility framing, the demanded-kWh ledger audit, and the low-slack deviation
concentration test are retained; the low-slack result and the joint-vs-marginal contrast are now
foregrounded in the abstract.

## Net length
Per the reviewer's length concern we condensed the IEEE-33 section and moved its figure and the
ServiceGridWeighted equations to the Supplement; the small net increase (43→45 pp) reflects the new
robustness analyses the reviewer requested (preference-form ablation, alternative normalization,
threshold-relaxation margin, anchor justification).

## Items requiring data we do not have (stated honestly as future work)
A *fitted, held-out-validated* behavioral compliance mechanism, and a field-tested incentive, require
decision-level managed-charging trial data (logged recommended-vs-actual actions) not available to us.
These remain the defined next steps; the paper's claims are bounded accordingly throughout.
