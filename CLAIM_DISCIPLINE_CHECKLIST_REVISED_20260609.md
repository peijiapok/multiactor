# Claim-discipline checklist for revised manuscript - 20260609

## Required evidence tables

| Requirement | Status | Evidence in revised manuscript |
|---|---|---|
| Exact behavioral severity parameter table | Pass | Methods Table 3 contains `keep_probability`, `reserve_margin`, and `cheap_extra_margin` for severities 0-3. |
| Exact ServiceGridWeighted score/weight table | Pass | Methods Table 2 contains score terms, definitions, normalization, weights, sign, and implementation source. |
| If values unrecoverable, mark reproducibility gap | Not needed for these two items | Values were recovered from the direct severity runner. |
| Abstract less audit-report-like | Pass | Detailed ledger row and branch-trace row counts moved out of abstract; `deployment-invalid` softened. |
| Author/affiliation placeholders | Pass | Named authors, affiliations, and corresponding-author email are inserted. |
| Event churn described conservatively | Pass | Results and Discussion state event churn, not true energy-demand amplification. |
| Figure captions state result claims | Pass | Main captions now identify the supported claim and boundary. |

## Forbidden claim scan

| Claim type | Status | Manuscript wording discipline |
|---|---|---|
| FleetBalanced superiority | Pass | Not claimed. FleetBalanced is treated as not distinct under current traces. |
| FleetBalanced mechanism | Pass | Not claimed. Branch trace has zero final-action difference. |
| FleetBalanced reduces grid deferrals | Pass | Not claimed. Grid-layer deferrals are not attributed to FleetBalanced. |
| True energy-demand amplification | Pass | Not claimed. Manuscript states the demanded-kWh ledger modestly falls and classifies the effect as event churn. |
| Field-calibrated behavior response | Pass | Not claimed. Behavior levels are stress tests, not calibrated forecasts. |
| Feeder validation or site-specific feasibility | Pass | Not claimed. IEEE-33 is a representative stress screen. |
| Threshold-independent robustness | Pass | Not claimed. Manuscript uses threshold-conditioned acceptability. |
| Heuristic optimality | Pass | Not claimed. ServiceGridWeighted is stated to be heuristic, not MPC/LP/optimal. |
| CostOnly/QueueAware as state of the art | Pass | They are called diagnostic single-objective heuristics. |

## Consistency checks

| Check | Status | Notes |
|---|---|---|
| Table numbering | Pass | No `Table 0` references found in revised manuscript files. |
| Local absolute paths | Pass | No `/home/jia` paths remain in manuscript prose. |
| Weekly sample description | Pass | Weekly design described as 240 service-oriented severity episodes plus 60 diagnostic CostOnly/QueueAware episodes. |
| Targeted 28-day description | Pass | Targeted confirmation described as 672 h, seeds 4541-4545, 35% capacity, LeastLaxity/ServiceFirst/ServiceGridWeighted, NoGrid/PeakPenalty. |
| Severity ratios separated by scope | Pass | Weekly request-event ratio and targeted demanded-kWh audit ratios are reported separately. |
| Load-factor/grid framing | Pass | Grid claims remain metric-specific and do not claim feasibility validation. |
| References | Pass with residual coauthor check | Citations follow the verified literature table; final coauthor citation review is still recommended. |
| PDF build | Pass with minor formatting warnings | Revised `.tex` compiles with Tectonic after author edits. All six referenced figure PDFs are present. Remaining warnings are table/front-matter layout polish. |

## Residual wording hits from grep

The strings `site-specific validation` and `optimal controller/control` appear only in negated limitation language. These are acceptable because they explicitly forbid overclaiming rather than asserting the claim.

## Claude joint revision pass - 20260610

- Abstract and highlights now define the severity result as same-episode all-pass failure under specified gates, not a physical collapse.
- Event churn now has an operational definition tied to request-event counts and the demanded-kWh ledger.
- Severity-0 actual/fleet ratio below one is explained by grid-layer adjustment after fleet recommendations.
- ServiceGridWeighted is downgraded from contribution to comparator robustness check.
- FleetBalanced is retained only as one bounded audit note in Methods.
- The IEEE-33 voltage-zero result is diagnosed as a base-load-determined binary metric, not feeder feasibility evidence.
