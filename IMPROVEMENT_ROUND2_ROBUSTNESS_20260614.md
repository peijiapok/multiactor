# Improvement round 2 — robustness / tautology defense — 20260614

## Why this round
The critical Claude + GPT-5.5 review of the 20260614 repaired draft rated it
**Reject / Major**, with a single fatal objection both reviewers shared:

> "All-pass" is a logical AND of 14 hand-thresholded binary criteria; ANDing 14 fragile
> tests makes collapse under any stress mathematically expected. The 100%→0% headline may be
> an artifact of the metric design, not a property of EV charging.

This round attacks that objection directly with a data re-analysis (no new simulation) plus
manuscript integration.

## What was done
New analysis (`robustness_analysis_20260614/`, integrated into Results Section "Robustness of
the acceptability definition", Fig. `fig_robustness_acceptability`):

1. **Decomposition (Q1).** Per-criterion fail fraction at severity 1 (n=60 episodes/severity).
   The collapse is broad-based: 4–5 distinct criteria across all three actors bind —
   critical-requests-not-delivered (driver, 0.93), p95 wait (fleet, 0.82), squared-load shape
   (grid, 0.52), ramp (grid, 0.27). The "intentionally tight" reliability gate fails only 0.17.
   → It is NOT a single engineered gate.
2. **Alternative aggregation (Q2).** Degradation survives softer logic: driver gate alone →
   0.03; "≥1 of 3 actors passes" → 0.52 at severity 1. → NOT purely an AND artifact.
3. **Honest concession.** The graded fraction-of-14-criteria index only drops to 0.81 at
   severity 1 — so the strict AND does dramatize an 80%-still-pass situation. The paper now
   reports BOTH the binary all-pass and the graded index and refuses the binary-cliff reading.
4. **Bootstrap 95% CIs** on the headline (sev1 all-pass [0,0]; driver gate [0,0.083]).
5. **Correction.** The earlier (wrong) claim "the binding gate is the driver gate" is replaced
   by the accurate multi-criteria statement.
6. **Threshold grounding.** Binding criteria mapped to established service-quality and
   grid-stress constructs with citations; cut-points still normative with sensitivity reported.
7. **Novelty vs Pareto.** Discussion now argues the per-episode joint-satisfaction test differs
   from scenario-averaged Pareto fronts by localising which actor/metric binds in-scenario.

## Manuscript edits
Abstract (graded index added), Methods (threshold grounding), Results (new Section + Fig.),
ablation subsection (corrected claim), Discussion (Pareto novelty), Limitations (binary-AND
caveat + sample-size honesty). Compiles clean (tectonic, 28 pp, 0 undefined refs, 49 refs).

## Net effect on the fatal objection
The contribution is reframed from a possibly-tautological binary cliff to a **multi-criterion
degradation finding**, reported with both strict and graded aggregation and with the binding
criteria identified. This is the specific defense both reviewers asked for.

## What still remains (honest)
- Uncalibrated custom simulator and uncalibrated behavioral severities (framed as stress
  tests; full calibration / ACN-Sim benchmarking is future work).
- 5 seeds; 28-day & ablation at 35% capacity only.
- IEEE-33 voltage deltas insensitive.
These are research-program items, disclosed in Limitations; they keep the realistic ceiling at
"Major revision" rather than "Accept", but the design-artifact objection is now defused.
</content>
