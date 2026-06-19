# Round 8 — final reviewer fixes (8.3/10 review) — 20260615

All 6 reviewer asks executed; key item resolved with real evidence, not just a caveat.

1. 28-day THRESHOLD SCALING (the key methodological item): the 28-day (672h) reused weekly (168h) ABSOLUTE count thresholds, making 2 of 14 gates ~4x stricter. Recomputed gates with HORIZON-FAIR x4 thresholds (critical-RND 24->96, RND 117->468) from saved 28-day data (no re-sim). Sanity: recompute matches engine all_pass 100%. RESULT: severity-1 collapse UNCHANGED (sev0 1.000, sev1 0.000 under x4) -> not a horizon artifact. Integrated into 28-day paragraph. (GPT-5.5 recommended computing it, not just a caveat.) Data: robustness_analysis_20260614/run_28day_ratenorm_20260615.py + ratenorm_28day_20260615.csv.
2. Dangling Supp figures: BOTH S1 (full actor-gate matrix) and S4 (threshold sensitivity) were referenced but not included. Added Supplementary figures S1-S4 (also S2 fleetbalanced, S3 request-conservation) with S-numbering; in-text refs now resolve to S1/S4. Supp tables S1 (SGW ablation), S2 (SGW provenance, moved from Methods).
3. mild_deviation -> low_deviation (severity table label).
4. SGW provenance table (tab:sgwterms) moved Methods -> Supplement; main text keeps pointer + dominance argument.
5. Softened external-validation 'if anything conservative' sentence.
6. Abstract: added 'under the specified gates'. Also defined n_F.

Verified: compiles clean (tectonic), 34 pp, 50 refs all cited, 0 undefined refs, supp S-numbering correct, 0 stale items. Figures present locally for clean build.
