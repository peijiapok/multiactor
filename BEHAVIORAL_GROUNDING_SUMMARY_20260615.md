# Behavioral grounding + acceptance push — full summary — 20260615

The behavioral layer (the #1 acceptance ceiling) is now defended on THREE fronts with PUBLIC data + literature, plus the novelty and simulator-specificity objections addressed:

## Behavioral layer — no longer 'randomly assumed'
1. MAGNITUDE anchored to real data (Tier 1): observed ACN deviation ~33% early-departure, 72% departure-mismatch, ~10% input-changes; severity-1 (5%) is conservative vs observed. (behavioral_anchor_20260615/)
2. STRUCTURE grounded in literature: non-compliant rule terms map to documented behaviors -- charge/range anxiety (schmalfuss,hardman,will), ToU price sensitivity (bailey,delmonte,marxen), deadline urgency/opt-out-when-needed (alexeenko,dudek). Cited in Methods.
3. ROBUSTNESS to structure (Option A): collapse PERSISTS (all-pass 0.000) when the same 5% deviation is concentrated in low-slack/inflexible vehicles (verified OptimizEV pattern) -- not an artifact of uniform random deviation. Driver gate binds regardless of where deviation lands. (optionA_slack_deviation_20260615/)

## Other objections
- NOVELTY (Tier 2): scenario-averaged eval passes 11/14 gates vs same-episode 0% -> screen catches what Pareto/average misses. Demonstrated, in Results + Discussion.
- SIMULATOR-SPECIFICITY (Tier 3): collapse reproduces across 3 independent real ACN charging populations (Caltech/JPL/Office). (tier3_demand_robustness_20260615/)

## HONEST remaining ceiling
Still NOT a full mechanism FIT to a behavioral dataset (no per-driver heterogeneity, no fitted p_keep(state) with held-out validation). Needs proprietary managed-charging trial data (Tier 4 guide). Disclosed in Limitations.

Compiles clean: 34 pp, 50 refs all cited, 0 undefined refs.
