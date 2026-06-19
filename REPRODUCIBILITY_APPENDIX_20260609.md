# Reproducibility Appendix - 20260609

## Repository structure

- Root: `/home/jia/multi actor/`
- Wave 1 evidence: `wave1_evidence_20260609/`
- Direct Wave 2 severity and baseline evidence: `wave2_direct_severity_baseline_20260609/`
- IEEE-33 feeder evidence: `wave2_strong_upgrades_20260609/`
- Final package: `final_applied_energy_package_20260609/`
- Strong plan: `applied_energy_research_upgrade_20260609/STRONG_APPLIED_ENERGY_EVIDENCE_BUILDING_PROGRAM_20260609.md`

## Core scripts

- `applied_energy_research_upgrade_20260609/run_direct_wave2_severity_baseline_20260609.py`
- `applied_energy_research_upgrade_20260609/run_targeted_28day_behavior_severity_20260609.py`
- `applied_energy_research_upgrade_20260609/run_demanded_kwh_trace_audit_20260609.py`
- `final_applied_energy_package_20260609/figure_scripts/build_final_figures_20260609.py`
- `final_applied_energy_package_20260609/generate_publication_texts_20260609.py`

## Main result files

- Request audit: `wave1_evidence_20260609/request_conservation_by_behavior_20260609.csv`
- FleetBalanced branch trace: `wave1_evidence_20260609/fleetbalanced_branch_trace_20260609.csv`
- Weekly severity results: `wave2_direct_severity_baseline_20260609/behavior_severity_results_20260609.csv`
- Weekly actor-gate matrix: `wave2_direct_severity_baseline_20260609/actor_gate_matrix_with_severity_and_baseline_20260609.csv`
- Weekly failure taxonomy: `wave2_direct_severity_baseline_20260609/failure_pattern_taxonomy_with_severity_and_baseline_20260609.csv`
- Targeted 28-day results: `final_applied_energy_package_20260609/targeted_28day_behavior_severity_results_20260609.csv`
- Demanded-kWh trace audit summary: `demanded_kwh_trace_audit_20260609/demanded_kwh_severity_summary_20260609.csv`
- Demanded-kWh request trace: `demanded_kwh_trace_audit_20260609/demanded_kwh_request_trace_20260609.csv`
- Demanded-kWh session summary: `demanded_kwh_trace_audit_20260609/demanded_kwh_session_summary_20260609.csv`
- Demanded-kWh conservation audit: `demanded_kwh_trace_audit_20260609/demanded_kwh_conservation_audit_20260609.csv`
- Targeted 28-day row results: `final_applied_energy_package_20260609/targeted_28day_row_results_20260609.csv`
- IEEE-33 EV-off deltas: `wave2_strong_upgrades_20260609/ieee33_ev_policy_deltas_vs_ev_off_20260609.csv`
- Literature table: `final_applied_energy_package_20260609/verified_literature_table_20260609.csv`

## Random seeds and horizons

- Weekly direct severity/baseline runs: five seeds, 168 h horizon, capacities 20%, 35%, and 50%.
- Targeted 28-day confirmation: seeds 4541-4545, 672 h horizon, 35% capacity.
- IEEE-33 screen: 900 weekly cases, 151200 hourly power-flow solves, 168 h per case.

## Policy definitions

- `LeastLaxity`: anchor heuristic prioritizing least-laxity/deadline-risk requests.
- `FleetCostOnly`: diagnostic single-objective cost-oriented heuristic.
- `FleetQueueAware`: diagnostic queue-oriented heuristic.
- `FleetServiceFirst`: service-oriented heuristic; current manuscript treats this as the service family after the FleetBalanced audit.
- `FleetServiceGridWeighted`: heuristic comparator combining service urgency and grid pressure.
- `FleetBalanced`: audited; not claimed as distinct under current scenarios.
- `NoGridIncentive`: no grid-layer intervention.
- `GridPeakPenalty`: grid-layer peak-pressure intervention. Deferrals are attributed to this layer.

## Behavior severity definitions

- Severity 0: full compliance, upper-bound benchmark.
- Severity 1: mild deviation.
- Severity 2: moderate deviation.
- Severity 3: severe/current stress behavior.

The severity sweep evaluates request-event/action-event pressure. The demanded-kWh trace audit reconciles targeted 28-day simulator demanded-kWh sessions and classifies the behavioral effect as event churn: event counts rise while simulator demanded kWh modestly falls, so the result is not true energy-demand amplification.

## Regeneration commands

From `/home/jia`:

```bash
python '/home/jia/multi actor/applied_energy_research_upgrade_20260609/run_targeted_28day_behavior_severity_20260609.py'
python '/home/jia/multi actor/final_applied_energy_package_20260609/figure_scripts/build_final_figures_20260609.py'
python '/home/jia/multi actor/final_applied_energy_package_20260609/generate_publication_texts_20260609.py'
```

## Figure traceability

- Fig. 1: generated schematic from `build_final_figures_20260609.py`.
- Fig. 2: `actor_gate_matrix_with_severity_and_baseline_20260609.csv`.
- Fig. 3: weekly severity CSV and targeted 28-day severity CSV.
- Fig. 4: `failure_pattern_taxonomy_with_severity_and_baseline_20260609.csv`.
- Fig. 5: weekly and targeted severity grid-policy summaries.
- Fig. 6: `ieee33_ev_policy_deltas_vs_ev_off_20260609.csv`.
- Supplementary FleetBalanced audit: `fleetbalanced_branch_trace_20260609.csv`.
- Supplementary request audit: `request_conservation_by_behavior_20260609.csv`.
- Supplementary threshold sensitivity: `research_strengthening_20260609/binding_threshold_sensitivity_overall_20260609.csv`.

## Evidence boundaries

- FleetBalanced superiority is forbidden.
- Behavioral true demanded-kWh amplification remains forbidden. The demanded-kWh audit supports request-event churn under simulator operational demand, not calibrated field energy-demand growth.
- IEEE-33 is a representative feeder stress screen, not site validation.
- Threshold conclusions are threshold-conditioned.
- ServiceGridWeighted is a heuristic comparator, not an optimizer.
