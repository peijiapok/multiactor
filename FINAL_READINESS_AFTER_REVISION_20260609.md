# Final readiness after hostile-review manuscript revision - 20260609

## Readiness category

**Ready for internal coauthor review after Claude-driven claim tightening. Not yet ready for Applied Energy submission.**

The hostile-review revision resolved the two largest manuscript reproducibility gaps: exact behavioral severity parameters and exact ServiceGridWeighted weights/selection logic are now in the manuscript. The subsequent polish pass inserted the named authors/affiliations, removed remaining author placeholders, softened the abstract claim language, verified all referenced figure PDFs, and recompiled the LaTeX successfully. The manuscript is substantially more defensible, but Applied Energy submission should wait for coauthor review, final formatting polish, and a decision on whether to add broader calibration or field-validation evidence.

## What improved in this revision

- The abstract now reads as an Applied Energy-style energy-systems abstract rather than an internal audit summary.
- Behavioral severity is quantitatively defined using recovered simulator values.
- ServiceGridWeighted is reproducibly specified with weights, normalization, trigger logic, and capacity-selection behavior.
- Event churn is explained as request-event fragmentation/reissue pressure, not increased true energy demand.
- Actor gates are justified as pre-specified normative stakeholder criteria, with sensitivity analysis used to expose threshold dependence.
- Limitations are expanded and moved into explicit interpretation boundaries.
- Main figure captions state supported result claims without overclaiming.
- The LaTeX manuscript compiles to PDF.

## Allowed manuscript claims after revision

1. Under the current actor-gate thresholds, fully compliant service-oriented charging can satisfy all actor gates in the tested weekly and targeted 28-day scenarios.
2. In the tested severity design, severity-1 behavioral deviation eliminates all-pass acceptability under current gates.
3. Behavioral severity increases request-event pressure and creates event churn.
4. The demanded-kWh trace does not support a claim of true energy-demand amplification.
5. PeakPenalty can reduce selected peak metrics but does not necessarily rescue all-pass outcomes after driver/fleet gates fail.
6. ServiceGridWeighted is a more credible heuristic comparator than single-objective CostOnly/QueueAware, but it does not create a simple controller-superiority story.
7. IEEE-33 provides representative feeder stress-screen deltas, not site-specific validation.
8. FleetBalanced is not a distinct mechanism under current branch traces and should remain merged/dropped from main contribution claims.

## Forbidden manuscript claims

- FleetBalanced improves performance or reduces deferrals.
- FleetBalanced has a proven mechanism in the current scenarios.
- Behavioral severity increases true energy demand.
- Behavior models are calibrated forecasts of real driver behavior.
- IEEE-33 validates real feeder feasibility.
- Actor-gate conclusions are threshold-independent or universally robust.
- ServiceGridWeighted is optimal, MPC, LP, or state-of-the-art control.

## Remaining reviewer risks

1. **Behavior calibration risk remains high.** Severity levels are exact and reproducible, but not empirically calibrated to observed opt-out or override behavior.
2. **Demanded-kWh tracing remains targeted.** The trace audit covers targeted 35% 28-day service-oriented cases, not every weekly policy/capacity combination.
3. **28-day confirmation scope remains limited.** It confirms the severity collapse at 35% capacity, not across all capacities.
4. **ServiceGridWeighted remains heuristic.** It reduces strawman-baseline risk but is not a full MPC/LP/state-of-the-art optimizer.
5. **IEEE-33 remains representative.** The feeder screen supports relative deltas, not deployment validation.
6. **Simulation-only evidence remains a limitation.** Coauthors should decide whether the paper needs field or empirical calibration evidence before journal submission.
7. **Formatting polish remains.** The revised PDF builds and all referenced figure PDFs are present, but dense reproducibility tables produce minor TeX layout warnings that should be polished before submission.

## Exact next action

Send the revised Markdown, LaTeX, PDF, revision log, claim checklist, and readiness note to coauthors for internal review. Ask reviewers to focus on whether the event-churn framing is credible without field calibration, whether the targeted demanded-kWh trace is sufficient for the central behavioral result, and whether the CRediT/funding/acknowledgement statements are correct for submission.

## Claude-driven revision pass - 20260610

A Claude critical-review pass identified overclaiming and clarity risks around all-pass collapse, event churn, ServiceGridWeighted, FleetBalanced, and IEEE-33 voltage deltas. The manuscript now narrows those claims and compiles successfully. This improves internal-review readiness but does not remove the need for coauthor review, table-format polishing, and final journal-style citation/format checks.
