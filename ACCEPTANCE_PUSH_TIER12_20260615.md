# Acceptance-push round — Tier 1 + Tier 2 — 20260615

AIM: improve acceptance odds at Applied Energy. Attacked the two biggest reviewer objections with achievable, data-grounded changes.

## TIER 1 (decisive): behavioral magnitude ANCHORED to real ACN-Data
Extracted observed plan-deviation from the SAME ACN-Data used to validate the demand model (29,116 sessions): ~33% early disconnection, 72% >30min departure mismatch, ~10% explicit input changes. The simulator severity-1 (5% deviation) is CONSERVATIVE vs these observed rates -> headline collapse occurs BELOW routinely observed real deviation. Integrated into severity-design section + limitations. HONEST scope: anchors deviation MAGNITUDE, not the per-timestep MECHANISM (still a model). Analysis: behavioral_anchor_20260615/run_acn_behavioral_anchor_20260615.py + csv.

## TIER 2 (novelty): demonstrated the screen catches what average/Pareto misses
At severity 1, a scenario-AVERAGED evaluation passes 11/14 gates (looks broadly acceptable: delivered 0.99, peak 0.96, cost 0.99), but SAME-EPISODE all-pass = 0% because violations fall in different episodes. Concrete proof of the framework's unique value vs Pareto/average. Added to Results + Discussion.

## Remaining (HONEST)
- Tier 3 (achievable, heavier): reproduce the headline under ACN-Sim-driven demand (cross-simulator robustness of the RESULT, not just demand means).
- Tier 4 (NEEDS COAUTHORS/external data): fit the behavioral MECHANISM to a real managed-charging trial with logged opt-out/override; real feeder/field validation. This is the gold standard reviewers most want; not doable here.

Compiles clean (33 pp, 50 refs, 0 undefined). These changes blunt the two biggest objections but do NOT eliminate the mechanism-calibration gap.
