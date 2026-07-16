# Paper final results — data behind every figure and table

All CSV/JSON files used to generate the figures, tables, and reported numbers in the
manuscript (`APPLIED_ENERGY_MANUSCRIPT_SUBMISSION_REPAIR_20260614.tex`), gathered in one place.
Generating scripts are in `../code/`.

## Main-text figures

| Figure | Data file(s) | Script (in `../code/`) |
|---|---|---|
| Fig. actor-gate matrix | `seed20_actor_gate_matrix_20260615.csv`, `seed20_row_results_20260615.csv`, `multi_actor_v2_row_results.csv` | `build_final_figures_20260609.py` |
| Fig. behavioral severity curve | `seed20_behavior_severity_results_20260615.csv`, `seed20_row_results_20260615.csv` | `build_final_figures_20260609.py` |
| Fig. ACN external validation | `acn_validation_results_20260615.csv`, `sim_sessions_20260615.csv`, `acnsim_benchmark_20260615.json` | external-validation script |
| Fig. Pareto ≠ feasibility | `pareto_demonstration_20260619.csv` (← `multi_actor_v2_row_results.csv`) | `pareto_demonstration_20260619.py` |
| Fig. marginal-vs-joint | `q1_subcriterion_decomposition_20260614.csv`, `seed20_row_results_20260615.csv`, `scenario_averaged_vs_joint_20260620.csv` | `scenario_averaged_vs_jointly_feasible_20260620.py` |
| Fig. diagnostic disaggregation | `diagnostic_by_behavior_20260619.csv` | `diagnostic_disaggregation_20260619.py` |
| Fig. oracle scheduler | `oracle_scheduler_counterfactual_20260620.csv` (← `seed20_row_results`, `edf_baseline_rows`) | `oracle_scheduler_counterfactual_20260620.py` |
| Fig. robustness of acceptability | `q1_subcriterion_decomposition_20260614.csv`, `q2_alternative_aggregation_20260614.csv` | `build_final_figures_20260609.py` |
| Fig. instrument counterfactual | `instrument_counterfactual_20260630.csv` | `plot_instrument_counterfactual_20260630.py` |
| Fig. apartment vs workplace (cross-ecology) | `apartment_vs_workplace_20260630.csv` | `run_apartment_vs_workplace_20260630.py` |
| Fig. optimizer baselines vs gate screen (weighted-sum + hard-constrained) | `weighted_optimizer_baseline_20260716.csv` | `run_weighted_optimizer_baseline_20260716.py` |
| Fig. equal-budget incentive comparison | `incentive_comparison_20260716.csv` | `run_incentive_comparison_20260716.py` + `plot_incentive_comparison_20260716.py` |
| Fig. information integrity (2nd compliance axis) | `information_integrity_20260706.csv` (+ `apartment_vs_workplace_20260630.csv` for the action-axis curve) | `run_information_integrity_20260706.py` |
| Fig. game: best-response / all-pass-vs-incentive / utility-triangle / PoA | `equilibrium_surface_real_20260616.csv`, `equilibrium_rows_20260616.csv`, `equilibrium_results_real_20260616.json`, `response_surface_rows_20260616.csv`, `response_surface_rows_cliff20_20260616.csv` | `gametheory_equilibrium_20260616.py` + `make_equilibrium_figures_20260616.py` |

## Supplementary figures

| Figure | Data file(s) | Script |
|---|---|---|
| Fig. published-controller comparison | `published_controller_comparison_20260620.csv` (← `edf_baseline_rows`, `uncoordinated_baseline_rows`, `seed20_row_results`) | `published_controller_comparison_20260620.py` |
| Fig. game sensitivity | `sensitivity_20260616.csv` | `make_equilibrium_figures_20260616.py` |
| Fig. OptimizEV calibration | `optimizev_calibration_20260616.json` | `optimizev_calibration_20260616.py` |
| Fig. fleet-economics robustness | `fleet_profit_robustness_20260616.csv` | `fleet_profit_robustness_20260616.py` |
| Fig. failure-pattern taxonomy | `actor_failure_pattern_summary.csv` | `build_final_figures_20260609.py` |
| Fig. grid-policy trade-off | `fleet_grid_policy_results.csv` | `build_final_figures_20260609.py` |
| Fig. request-ID / demanded-kWh audit | `multi_actor_v2_row_results.csv` (audit columns) | `build_final_figures_20260609.py` |
| Fig. threshold sensitivity | `envelope_e1_global_scaling_20260615.csv`, `envelope_e2_oneatatime_20260615.csv` | robustness scripts |

## Tables

| Table | Data file(s) |
|---|---|
| Weekly severity / seed-capacity | `seed20_row_results_20260615.csv`, `seed20_behavior_severity_results_20260615.csv`, `seed20_summary_20260615.csv` |
| Weekly per-policy matrix | `multi_actor_v2_policy_capacity_summary.csv`, `mutual_acceptability_summary.csv`, `seed20_actor_gate_matrix_20260615.csv` |
| Published-controller comparison | `published_controller_comparison_20260620.csv` |
| Marginal-vs-joint gate-by-gate | `q1_subcriterion_decomposition_20260614.csv` |
| Robustness summary (7 checks) | `q1_subcriterion_decomposition_20260614.csv`, `q2_alternative_aggregation_20260614.csv`, `envelope_e1_global_scaling_20260615.csv`, `envelope_e2_oneatatime_20260615.csv` |
| Threshold-slack envelope | `envelope_e1_global_scaling_20260615.csv` |
| 28-day confirmation | `ratenorm_28day_20260615.csv` |
| Bootstrap CIs (96.7% / 1.2% intervals) | `q3_bootstrap_cis_20260614.csv` |
| SGW coefficient ablation | `preference_ablation_rows_20260619.csv`, `preference_ablation_summary_20260619.csv`, `equilibrium_surface_real_sgw_20260616.csv`, `equilibrium_results_real_sgw_20260616.json` |
| External validation (KS distances) | `acn_validation_results_20260615.csv`, `acnsim_benchmark_20260615.json` |

## Notes
- The behavioral **severity** convention: 0 = full compliance; 1/2/3 ≈ 5%/20%/45% vehicle-timestep deviation.
- `seed20_row_results_20260615.csv` is the primary per-episode dataset (240 episodes/severity: seeds 4541–4560, 3 capacities, 2 grid policies, 2 service fleet policies).
- All figures are reproducible by running the listed script against the corresponding data file(s).
