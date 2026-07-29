# code_in_use — the actual code behind the manuscript

Snapshot of every source file used to produce the results, figures, and tables in
`../APPLIED_ENERGY_MULTI_ACTOR_final.tex`. This is a **faithful archive**: files are copied
verbatim from their working locations (absolute paths inside the scripts are unchanged), so it
records exactly what was run. See "Original locations" below for where each layer came from.

Collected 2026-07-29. Pairs with `../results_data/MANIFEST.md` (figure → data file → script) and
`ENVIRONMENT_SPEC.md` (the environment/scenario/gate specification: every config field, all 18
scenario presets, the ACN calibration, the seed20 experiment design, and the 14 acceptability-gate
thresholds — with file:line citations).

## Layers (dependency order, bottom → top)

```
simulator/            ← base EV-charging environment + queueing wrapper + scenario spec (the physics)
  env_v2.py               EVEnvironmentV2 / EnvV2Config — session sampling, SoC, price, feeder
  e12_queue_env.py        EVEnvironmentV2Queue / QueueEnvConfig — port contention + queue
  data_grounding.py       get_scenario_preset() + ScenarioPreset — the ENVIRONMENT/SCENARIO SPEC
                          (env_v2.py line 17 imports it; called at line 151)
  run_experiments.py      make_scenario_config(seed, scenario_name) -> EnvV2Config
                          (train_eval_v2.py line 27 imports it; imports env_v2 + obs_adapter)
  obs_adapter.py          flatten_agent_obs / STATE_DIM (imported by run_experiments.py)
  data/                   calibration summaries env_v2.py loads by scenario_name
    caltech_multisite_summary.json   DEFAULT + metro_caltech_sce (workplace; ACN Caltech+JPL+Office)
    caltech_summary.json             Caltech single-site
    nl_office_summary.json           nl_office scenario
    uk_home_summary.json             uk_home scenario
    acn_empirical_models/            RAW ACN grounding behind the calibration:
      acn_clean_session_features.csv    29,116 real ACN session tuples (Caltech+JPL+Office001)
      empirical_model_summary.json      fitted lognormal params (kwh/dwell) + arrival/dow hists
      jpl_session_type_*.csv, jpl_user_type_*.csv   JPL session/user type assignments
    (metro_korea apartment calibration is handled inside the engine; raw source =
     /home/jia/korea apartment.xlsx, not required at run time)

engine/               ← multi-actor 14-gate experiment engine (imports simulator/)
  brl_dqn_v2/             training/eval + agent + reward + obs/action adapters
    train_eval_v2.py        make_env, V2RunConfig  (adds /home/jia/thirftydeath to sys.path,
                            imports e12_queue_env → env_v2)
    brl_wrapper_v2.py, dqn_agent_v2.py, env_action_wrapper.py,
    obs_adapter_v2.py, reward_v2.py, __init__.py
  run_behavior_applied_energy_package_v1.py   scenario/behavior package (`pkg`: make_spec, gates)
  run_behavior_trait_screening.py             trait/behavior helpers used by pkg
  run_multi_actor_v2_experiment.py            the engine (`mav2`): MultiActorPolicy, POLICIES,
                                              the 14 acceptability gates, evaluate_run

analysis/             ← 29 scripts that drive the engine and/or read result CSVs to make figures
  seed20_producer/       the EXACT runner behind the primary dataset seed20_row_results_20260615.csv:
    run_seed20_severity_20260615.py   imports mav2, runs 20 seeds × 3 caps × 2 grid × 2 fleet,
                                       writes seed20_row_results_*.csv (to_csv @ line 375)
    build_seed20_aggregates_20260615.py   builds the actor-gate matrix / severity / summary CSVs
    run_seed20_stdout.log, SEED20_REPORT_20260615.md   run log + report
```

**Import chain:** `analysis/*` → (import `run_multi_actor_v2_experiment` as `mav2`, and
`pkg`) → `brl_dqn_v2.train_eval_v2` → (`run_experiments.make_scenario_config`) →
`e12_queue_env` → `env_v2` → (`data_grounding.get_scenario_preset`, `obs_adapter`) →
`data/*summary*.json` (+ `data/acn_empirical_models/`).

Note: `data_grounding.py`, `run_experiments.py`, `obs_adapter.py` are pulled in by **lazy /
in-function imports** inside `env_v2.py` (line 17) and `train_eval_v2.py` (line 27), so a
top-level import scan misses them — they are nonetheless required at run time.

## Original locations (verbatim copies of)
- `analysis/`  ← `/home/jia/multi actor/final_applied_energy_package_20260609/code/`
  (identical mirror of `/home/jia/multi actor/equilibrium_optimization_20260616/`)
- `engine/`    ← `/home/jia/thirfty death BRL DQN/scripts/` (+ `brl_dqn_v2/` package)
- `simulator/` ← `/home/jia/thirftydeath/` (`env_v2.py`, `e12_queue_env.py`, `data_grounding.py`,
  `run_experiments.py`, `obs_adapter.py`, `*summary*.json`)
- `simulator/data/acn_empirical_models/` ← `/home/jia/thirfty death BRL DQN/results/applied_energy_rebuild_empirical_models/`
- `analysis/seed20_producer/` ← `/home/jia/multi actor/seed20_expansion_20260615/`

Note: `/home/jia/thirfty death BRL DQN/` (the engine) and `/home/jia/thirftydeath/` (the
simulator core) are two different directories.

## The two kinds of analysis scripts
- **`run_*` / `*_baseline` / `*_counterfactual`** — invoke the engine (`mav2`) to run new
  simulations, then write a CSV/JSON into `../results_data/`.
- **`plot_*`, `make_*`, `pareto_demonstration`, `minimal_gateset`, `scenario_averaged_*`,
  `diagnostic_disaggregation`** — read existing CSVs from `../results_data/` (no new sim) and
  emit a figure into `../figures/`.

Which script produces which figure/table/data file is listed in `../results_data/MANIFEST.md`.

## Running (reproduction)
The scripts use **absolute** paths (`/home/jia/thirfty death BRL DQN`, `/home/jia/multi actor`,
`/home/jia/thirftydeath`), so on the original host they run in place from any directory:
```
python "analysis/run_minimal_gateset_20260716.py"     # reads seed20 CSV → minimal_gateset_*.csv
python "analysis/run_information_integrity_20260706.py"  # drives the engine → info_integrity CSV
```
On a different host, either recreate those three directories at the same paths, or update the
`WORKSPACE` / `ROOT` / `SOURCE` constants at the top of the affected files. `env_v2.py` finds its
calibration JSON via `os.path.dirname(__file__)`, so keep `simulator/data/*` beside `env_v2.py`
(or restore them next to the original `/home/jia/thirftydeath/env_v2.py`).

Requirements: Python 3 with numpy, pandas, matplotlib (+ scipy). The engine imports torch/gym via
`brl_dqn_v2` but the multi-actor gate experiments use scripted policies, not a trained agent.
