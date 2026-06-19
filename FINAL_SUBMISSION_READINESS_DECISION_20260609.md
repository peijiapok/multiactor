# Final Submission Readiness Decision - 20260609

## Category

Ready for internal coauthor review.

This is not yet Ready for Applied Energy submission. The evidence spine, verified literature table, final figure set, manuscript draft, reproducibility appendix, hostile reviewer table, and targeted demanded-kWh trace audit now exist, but the paper still needs coauthor review, manuscript polishing, consistency checks, and conservative behavioral calibration/framing.

## Completed evidence

- Targeted 28-day behavioral severity confirmation completed at 35% capacity, seeds 4541-4545, 672 h horizon.
- Literature DOI/URL table generated with no guessed DOI entries.
- Final main and supplementary figures generated from source CSVs.
- Manuscript rewritten from zero around multi-actor acceptability.
- Reproducibility appendix created.
- Hostile Applied Energy reviewer table created.
- Persistent demanded-kWh trace audit completed for targeted 28-day service-oriented severity cases.

## Targeted 28-day decision

- Severity 0 all-pass rate: 100.0%.
- Severity 1 all-pass rate: 0.0%.
- Severity 3 actual/fleet request-event ratio: 2.566.
- Decision: the 28-day run supports the weekly collapse at mild behavioral deviation under the current gates.

## Demanded-kWh audit decision

- Vehicle-step conservation rows: 4,300,800.
- Maximum session residual: 2.29e-5 kWh, within the 1e-4 kWh tolerance.
- Maximum step residual: 7.63e-7 kWh.
- Classification: event_churn.
- Interpretation: behavioral severity increases request-event counts while simulator demanded kWh modestly falls in this targeted audit.

## Allowed manuscript claims

- EV charging policies can pass individual metrics while failing multi-actor acceptability gates.
- Under current gates, full-compliance service-oriented policies pass, while mild behavioral deviation eliminates all-pass acceptability in the tested weekly and targeted 28-day scenarios.
- Behavioral severity increases request-event/action-event pressure.
- Targeted demanded-kWh tracing classifies this behavioral effect as event churn: request-event counts rise while simulator demanded kWh modestly falls.
- GridPeakPenalty can reduce selected peak ratios but does not rescue all-pass outcomes after driver/fleet failures.
- ServiceGridWeighted reduces strawman-baseline risk but does not produce a simple controller-superiority result.
- IEEE-33 provides representative feeder stress deltas versus EV-off baseline.
- FleetBalanced is not a distinct mechanism under current scenarios.

## Forbidden manuscript claims

- FleetBalanced superiority.
- FleetBalanced mechanism unless future traces show final-action and gate-outcome differences.
- Behavioral true energy-demand amplification or calibrated field demand growth.
- Feeder validation or site-specific feasibility.
- Threshold-independent robustness.
- Optimality of heuristic policies.

## Remaining risks

- Behavior models are not calibrated forecasts.
- Demanded-kWh tracing is targeted to 35% capacity, 28-day service-oriented cases only.
- 28-day confirmation is targeted to 35% capacity only.
- No full MPC/LP optimization baseline is included.
- IEEE-33 screen is representative only.
- Gate thresholds remain normative.

## Exact next steps

1. Coauthor/internal review of `APPLIED_ENERGY_MANUSCRIPT_DRAFT_20260609.md`.
2. Decide whether coauthors require calibration or literature-bounded behavioral parameters before submission.
3. Decide whether to expand the 28-day confirmation to 20% and 50% capacity.
4. Polish figure typography and captions after coauthor review.
5. Convert manuscript to journal LaTeX or DOCX once claims are approved.
