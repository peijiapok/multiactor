# Reproducibility package — Multi-actor compliance feasibility of managed EV charging

This repository contains the manuscript, analysis code, derived data, and figures for the paper.

## Layout
- `APPLIED_ENERGY_MANUSCRIPT_SUBMISSION_REPAIR_20260614.tex` / `.pdf` — the manuscript.
- `SUBMISSION_PACKAGE_20260615/` — submission bundle (manuscript, highlights, cover letter, figures, graphical abstract).
- `figures/` — all main-text and supplementary figures (PDF + PNG).
- `code/` — analysis scripts (Python) and derived result data (CSV/JSON):
  - `gametheory_equilibrium_*.py` — congestion-game equilibrium, Nash bargaining, price of anarchy.
  - `run_response_surface_*.py` — simulator response surface over deviation/capacity/grid (source data: `response_surface_rows_*.csv`).
  - `pareto_demonstration_*.py` — Pareto-vs-conjunction demonstration.
  - `run_edf_baseline_*.py` — earliest-deadline-first recognized-scheduler baseline.
  - `oracle_scheduler_counterfactual_*.py` — oracle scheduler-selection counterfactual (best single scheduler 1.7%, per-episode oracle 5.0% at severity 1; `fig_oracle_scheduler`).
  - `scenario_averaged_vs_jointly_feasible_*.py` — scenario-averaged-vs-same-episode primary figure (79% marginal vs 1.2% joint; `fig_marginal_vs_joint`).
  - `diagnostic_disaggregation_*.py` — disaggregation by capacity / gate / behavior type.
  - `sensitivity_*`, `optimizev_calibration_*`, `run_preference_ablation_*`, `fleet_profit_robustness_*` — robustness analyses.
  - `make_equilibrium_figures_*.py`, `make_graphical_abstract_*.py` — figure generation.
  - `*_NOTE_*.md`, `*REVIEW*.md` — analysis notes and reviewer-response records.
- `*.csv` (top level) — diagnostic, decomposition, envelope, ablation, and validation result tables used in the manuscript.
- `RESPONSE_TO_REVIEWER*_*.md` — point-by-point reviewer responses.
- `SIMULATION_METHODOLOGY_DETAILED_*.md` — full methodology, formulae, and worked examples.

## Reproducing the analyses
The game-theory / Pareto / diagnostic analyses are deterministic given the response-surface CSVs and
run with standard scientific Python (numpy, pandas, matplotlib). The simulation **engine** that
produced the raw per-episode metrics (the multi-actor charging simulator and ACN-Data demand model)
is a separate component; the derived per-episode and aggregated result tables required to reproduce
every manuscript figure and table are included here.

## Data
The charging-demand model is calibrated to the public Adaptive Charging Network (ACN) dataset
(Caltech/JPL/Office; n=29,116 cleaned sessions). Lognormal fit parameters are documented in the
methodology note. Derived simulation outputs are provided as CSV.
