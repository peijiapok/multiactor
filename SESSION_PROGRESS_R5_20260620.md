# Session progress — Reviewer-5 revision + compression (2026-06-20)

## What was done (all committed locally)
1. **Data Availability statement** rewritten to point to the live public repo
   `https://github.com/peijiapok/multiactor` (was "available upon publication"). [R5 #10]
2. **Oracle scheduler-selection counterfactual** added (new `fig:oracle`, Section robust "Seventh").
   Best single deployable scheduler = **1.7%** all-pass at severity 1; per-episode **oracle** = **5.0%**
   (95% CI [0.0%, 11.7%]), entirely at 20% capacity, exactly 0% at 35%/50%, vs 96.7% full compliance.
   Confirms the spine: infeasibility is inherent to the deviation, not the scheduler.
   Script: `equilibrium_optimization_20260616/oracle_scheduler_counterfactual_20260620.py`. [R5 #1]
3. **Scenario-averaged-vs-same-episode primary figure** added (new `fig:marginaljoint`):
   9/14 criteria pass marginally in ≥98% of episodes, mean 0.79 (≈11/14), yet same-episode all-pass = 1.2%.
   Script: `equilibrium_optimization_20260616/scenario_averaged_vs_jointly_feasible_20260620.py`. [R5 #4]
4. **Framing fixes**: scope to US workplace/campus (abstract + conclusions) [#2]; full-factorial design
   rationale [#3]; 95% CI [0.0%, 2.9%] on the 1.2% headline (abstract + conclusions) [#5]; preference-score
   coefficient units/normalization note [#6]; severity 0–3 defined at first use in the intro [#7]; LeastLaxity
   anchor dual-role (reference vs candidate) non-circularity clarification [#8]; behavior-type literature
   grounding retained/signposted [#9].
5. **Compression (Strategy A, GPT-endorsed)**: moved four secondary floats to the Supplement —
   failure-pattern taxonomy figure, grid-policy trade-off figure, 28-day table, threshold-envelope table.
   Main narrative now runs gates → joint feasibility → threshold → oracle → congestion-game incentive
   uninterrupted; all headline figures retained in main text.
6. **Response letter**: `RESPONSE_TO_REVIEWER5_20260620.md` (point-by-point, all 10 items).

## Build status
`tectonic` compiles clean (EXIT=0), **no undefined references or citations**. Main text ends ~page 41;
references 41–48; supplement 49–55.

## Reviewer 6 (Minor Revision) — also done this session
- **#1 published controllers** (main ask): new Results subsection `sec:published` + `tab:published`
  + supplementary `fig:published`. Applied the framework to EDF (Liu&Layland 1973 — canonical
  scheduler, ACN family) and uncoordinated immediate charging. At full compliance all three hit
  91.9–95.4% reliability, but same-episode all-pass = 100% (ServiceFirst) / 20% (EDF) / 0%
  (uncoordinated) — framework discriminates among established controllers (single-metric pass,
  conjunction fail). Ran `run_uncoordinated_baseline_20260620.py`; consolidated in
  `published_controller_comparison_20260620.py`. Added Liu&Layland 1973 + Dertouzos&Mok 1989 cites.
- **#2 gate-by-gate table** `tab:marginaljoint` (marginal vs joint, primary result).
- **#3 Stackelberg observability** already present (Limitations) — confirmed.
- Minor: gate collinearity note; Table 2 caption (per-session vs per-timestep); IEEE-33 voltage
  trim; CIs in first Results paragraph; capacity justification at first mention.
- `RESPONSE_TO_REVIEWER6_20260620.md`. Compiles clean, 0 undefined, 58–59pp.

## Git state — ACTION NEEDED
Local repo is **5 commits ahead** of the GitHub remote (`origin` has only the initial `5026c72`):
- `f4f6fd4` R5 revision (oracle + marginal-vs-joint + data availability + framing)
- `cfb6941` Compression (Strategy A)
- `fbbd1fa` README update
- `686c3ce` / PDF-rebuild commits
- `15bae51` R6 (published-controller comparison + gate-by-gate table + minor fixes)

**These are NOT yet on GitHub.** Push them with fresh credentials after rotating the token (below):
```
cd "/home/jia/multi actor/final_applied_energy_package_20260609"
git push https://github.com/peijiapok/multiactor.git master:master
```
(Use a credential helper or `gh auth login` rather than embedding a token in the URL.)

## SECURITY — rotate the exposed token
A live GitHub PAT was pasted into the chat in the previous session and is compromised. **Revoke it now:**
GitHub → Settings → Developer settings → Personal access tokens → delete it. Generate a fresh one for the push.
