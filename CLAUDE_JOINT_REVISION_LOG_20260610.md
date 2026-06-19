# Claude joint revision log - 20260610

## Basis

This pass revised the manuscript against the Claude critical-review stdout already obtained for `APPLIED_ENERGY_MANUSCRIPT_DRAFT_REVISED_20260609.tex`. A fresh direct Claude planning/review call was attempted but blocked by execution policy because it would send nonpublic manuscript content to an external service. No workaround was attempted. The edits below use the prior Claude critique as the co-review checklist.

## Load-bearing Claude critiques addressed

| Claude critique | Revision made | Status |
|---|---|---|
| Abstract/headlines overstate a physical `collapse`; all-pass is a conjunction of gates. | Abstract, highlights, captions, results, discussion, and conclusion now say same-episode all-pass or joint-threshold failure. Abstract states individual severity-1 pass rates remain nonzero in the weekly sweep. | Addressed |
| Severity-0 actual/fleet ratio is 0.983, not 1.000. | Methods and Results now define actual/fleet request-event ratio as final driver-layer request events divided by fleet recommendations before grid adjustment, and explain that full-compliance drivers follow grid-adjusted actions, so grid deferrals can make the ratio below one. | Addressed with manuscript explanation |
| Event churn is label-like without an operational definition. | Methods and Results now define event churn operationally: increased driver-layer request-event counts across vehicle-timesteps while the demanded-kWh ledger remains conserved and does not increase. Results explain re-entry through reserve/cheap-window self-service. | Addressed |
| IEEE-33 zero voltage deltas look suspicious. | Feeder results now explicitly diagnose the binary voltage-violation metric as base-load determined and insensitive to incremental EV-policy differences in this setup; voltage counts are not used as feasibility evidence. | Addressed |
| ServiceGridWeighted is not a headline contribution because aggregate all-pass equals ServiceFirst. | Contribution list now removes ServiceGridWeighted as a contribution. Results section retitled as comparator robustness check and states equal aggregate all-pass means no superiority claim. | Addressed |
| FleetBalanced appears too often for a null result. | Removed FleetBalanced from highlights, abstract, introduction contribution framing, Results section, and conclusion. Kept one bounded policy-audit paragraph in Methods. | Addressed |
| Gate math/ledger math not self-contained. | Nomenclature now adds ledger terms and actual/fleet ratio symbols. Methods now explains same-episode AND gates and ledger terms. | Addressed |
| Behavior severity is a counterfactual scorer, not calibrated behavior. | Text now calls behavioral variants stress-test and comparator devices, not calibrated forecasts. | Addressed |
| Acknowledgement draft placeholder should not appear. | Removed the acknowledgement section from the LaTeX/Markdown draft. | Addressed |

## Files changed

- `APPLIED_ENERGY_MANUSCRIPT_DRAFT_REVISED_20260609.tex`
- `APPLIED_ENERGY_MANUSCRIPT_DRAFT_REVISED_20260609.md`
- `APPLIED_ENERGY_MANUSCRIPT_DRAFT_REVISED_20260609.pdf`
- `CLAUDE_JOINT_REVISION_LOG_20260610.md`
- `CLAIM_DISCIPLINE_CHECKLIST_REVISED_20260609.md`
- `FINAL_READINESS_AFTER_REVISION_20260609.md`

## Compile and scan

- LaTeX compile: pass with Tectonic.
- Figures: no missing figure failures during compile.
- Remaining LaTeX warnings: minor dense-table underfull/overfull warnings.
- Forbidden-claim scan: clean except intentional negation, `does not validate site-specific feasibility`.

## Residual risks

1. ServiceGridWeighted remains heuristic and aggregate all-pass equals ServiceFirst; it should stay a comparator check only.
2. Event churn is now operationally defined, but still simulator-internal and not field calibrated.
3. The 28-day check remains one capacity cell.
4. IEEE-33 voltage violation counts are not useful policy signals in this screen; only non-voltage deltas should be emphasized.
5. Final journal formatting still needs table readability polish.
