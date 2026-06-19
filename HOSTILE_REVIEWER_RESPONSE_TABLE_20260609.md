# Hostile Reviewer Response Table - 20260609

|Reviewer criticism|Risk|Evidence response|Manuscript wording response|Remaining limitation|Resolved before submission?|
|---|---|---|---|---|---|
|Gates are arbitrary.|High|Threshold sensitivity and explicit gate table make assumptions visible.|Call gates pre-specified normative thresholds.|Needs stronger empirical or stakeholder justification before submission.|Partial|
|Threshold dependence undermines conclusions.|High|Sensitivity is treated as a result, not hidden.|Use threshold-conditioned acceptability, not robust.|Some conclusions may change under different thresholds.|Partial|
|Behavior models are uncalibrated.|High|Manuscript labels them as stress-test variants.|Do not call them forecasts or realistic behavior.|Needs calibration against observed opt-out/override data.|No|
|Request amplification may be artifact.|Medium|Request-ID/count conservation passed; persistent demanded-kWh tracing reconciled 4,300,800 vehicle-step rows within 1e-4 kWh. Severity 3 raises request-event counts to 2.349x while simulator demanded kWh falls to 0.917x severity 0, so the effect is event churn rather than demanded-kWh growth.|Say behavioral deviation amplifies request-event pressure; do not say it increases true energy demand.|Trace is targeted to 35% 28-day service-oriented cases and uses simulator operational demand, not calibrated field demand.|Partial|
|FleetBalanced is identical to ServiceFirst.|High|Branch trace shows zero final-action changes and zero L1 distance.|Merge/drop FleetBalanced as a distinct mechanism.|Does not prove all possible scenario equivalence.|Yes|
|IEEE-33 is not real feeder validation.|High|EV-off and policy-delta analysis added.|Call it representative feeder stress screen.|No site-specific feeder data.|Partial|
|Voltage violations show infeasibility.|Medium|Voltage deltas vs EV-off are zero on average; base-load dominates.|Treat voltage as boundary condition.|Absolute voltage screen remains stressed.|Partial|
|GridPeakPenalty does not rescue all-pass outcomes.|Medium|Results explicitly show this.|Frame as grid trade-off, not rescue.|PeakPenalty design may be too simple.|Yes|
|CostOnly/QueueAware are strawmen.|Medium|ServiceGridWeighted added as stronger service-grid heuristic.|Call CostOnly/QueueAware diagnostic single-objective heuristics.|Still no full MPC/LP benchmark.|Partial|
|New weighted baseline is still heuristic.|Medium|Parameters and score formula documented.|Call it heuristic comparator.|No optimization proof.|Partial|
|Simulation-only study lacks field validation.|High|Reproducibility and audit package are transparent.|State simulation-only limitation.|Needs field or calibrated dataset for stronger claim.|No|
|No optimization proof.|Medium|Manuscript avoids optimality claims.|Use heuristic/control policy wording.|Could add LP/MPC baseline later.|Yes|
|Results may not generalize beyond selected seeds/capacities.|Medium|Weekly multi-capacity plus targeted 28-day confirmation included.|Bound claims to tested seeds/capacities.|28-day confirmation only at 35% capacity.|Partial|
|Figures may overstate mechanism.|Medium|Figures label request-event pressure and feeder deltas only.|Avoid causal or validation labels.|Manuscript captions must remain disciplined.|Partial|
