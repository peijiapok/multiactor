# Figure Rebuild Report - 20260609

All figures were generated from saved CSV evidence using `figure_scripts/build_final_figures_20260609.py`.
The figures avoid decorative imagery and use bounded labels consistent with the Wave 1 claim rules.

## Generated figures

- `fig1_multi_actor_framework`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/fig1_multi_actor_framework.png`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/fig1_multi_actor_framework.pdf`
- `fig2_actor_gate_acceptability_matrix`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/fig2_actor_gate_acceptability_matrix.png`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/fig2_actor_gate_acceptability_matrix.pdf`
- `fig3_behavioral_severity_curve`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/fig3_behavioral_severity_curve.png`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/fig3_behavioral_severity_curve.pdf`
- `fig4_failure_pattern_taxonomy`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/fig4_failure_pattern_taxonomy.png`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/fig4_failure_pattern_taxonomy.pdf`
- `fig5_grid_policy_tradeoff`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/fig5_grid_policy_tradeoff.png`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/fig5_grid_policy_tradeoff.pdf`
- `fig6_ieee33_feeder_deltas`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/fig6_ieee33_feeder_deltas.png`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/fig6_ieee33_feeder_deltas.pdf`
- `fig_robustness_acceptability`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/fig_robustness_acceptability.png`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/fig_robustness_acceptability.pdf`
- `supp_full_actor_gate_matrix`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/supp_full_actor_gate_matrix.png`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/supp_full_actor_gate_matrix.pdf`
- `supp_request_id_conservation_audit`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/supp_request_id_conservation_audit.png`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/supp_request_id_conservation_audit.pdf`
- `supp_threshold_sensitivity`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/supp_threshold_sensitivity.png`
  - `/home/jia/multi actor/final_applied_energy_package_20260609/figures/supp_threshold_sensitivity.pdf`

## Source data

- Wave 1 request conservation: `wave1_evidence_20260609/request_conservation_by_behavior_20260609.csv`
- Wave 1 FleetBalanced branch trace: `wave1_evidence_20260609/fleetbalanced_branch_trace_20260609.csv`
- Direct weekly severity and baseline matrix: `wave2_direct_severity_baseline_20260609/actor_gate_matrix_with_severity_and_baseline_20260609.csv`
- Targeted 28-day severity confirmation: `final_applied_energy_package_20260609/targeted_28day_behavior_severity_results_20260609.csv`
- IEEE-33 EV-off deltas: `wave2_strong_upgrades_20260609/ieee33_ev_policy_deltas_vs_ev_off_20260609.csv`
- Threshold sensitivity: `research_strengthening_20260609/binding_threshold_sensitivity_overall_20260609.csv`

## Claim boundaries

- FleetBalanced is shown only as an equivalence/branch audit, not a superior controller.
- Behavioral severity is labeled as request-event pressure, not true demanded-kWh amplification.
- IEEE-33 is labeled as a representative feeder stress screen with EV-off deltas, not site validation.
- Threshold results are presented as threshold-conditioned acceptability.
