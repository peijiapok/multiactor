# Response to Reviewer — Applied Energy (minor revision, round 2)

We thank the reviewer for moving to Minor Revision and for the precise comments, which let us
sharpen the game/welfare section in particular. No new experiments were required; changes below.

## Major concerns

**C1 — Game section partly tautological; delineate what it adds vs inherits.**
Addressed by a new paragraph at the head of Section (mechanism) stating this explicitly: "We do
*not* use the congestion game to re-establish the simulator's collapse... once the game's
no-incentive equilibrium is calibrated to the 5% deviation level, 'the collapse is an equilibrium
that an incentive removes' is largely entailed by the deviation--acceptability cliff already shown.
What the game layer adds is three things the simulator alone does not provide: (1) an *equilibrium
explanation* endogenizing why deviation concentrates near 5% (unique, stable Nash equilibrium of a
free-riding congestion game); (2) a *mechanism-design characterization* of the corrective lever as
Pigouvian internalization of the externality; (3) a *welfare layer* (Nash-bargaining target + price
of anarchy). The section is a complementary explanatory and welfare layer, not an independent
re-derivation of the collapse." (Wording developed with care to claim only the explanatory/normative
value, not new empirical evidence.)

**C2 — Behavioral mechanism model-assumed; move caveat to abstract.**
Done. The abstract now states: "The severity levels are a model-assumed preference structure
calibrated to ACN deviation *magnitudes*, not fitted to observed compliance decisions, so the
headline rests on assumed behavioral dynamics that we keep explicit throughout."

**C3 — Welfare weights unjustified; state the three sets.**
Done. The robustness sentence now names them: "an *equal*/utilitarian weighting (1/3,1/3,1/3), a
*driver-heavy* weighting (0.5,0.25,0.25) representing a user-/adoption-centric stance, and a
*grid-heavy* weighting (0.25,0.25,0.5) representing a system-operator stance." The PoA stays
>1 across all three.

**C4 — sigma* range (0.13-1.77) undermines "bounded."**
Addressed with a direct explanation: the spread "is driven almost entirely by the assumed *incentive
responsiveness*: the required incentive rises monotonically with the cost-heterogeneity scale (mean
0.45/0.65/0.93 at s=0.25/0.40/0.60)... maximum 1.77 at the least-responsive corner." We now read
"bounded" precisely (finite, <~2 utility units across all 243 configs) and emphasize that the
practical magnitude depends on an empirically unknown elasticity of compliance a trial could measure
-- itself a useful design statement.

## Minor concerns

**C5 — 0.000 vs 0.012:** added a compact side-by-side table (Table evalunits) of the two evaluation
units (5-seed per-capacity surface vs 20-seed pooled weekly).

**C6 — ACN-Sim 11.65 discrepancy:** now explained -- ACN-Sim applies no energy cap and matches the
data (12.19 vs 12.17), whereas our 40 kWh clip removes the upper tail and pulls our mean to 11.65;
the ~4% gap is a known consequence of tail truncation, within tolerance for a relative-degradation study.

**C7 — 28-day weight in conclusions:** softened to match Limitations -- "a single-capacity 28-day
check (35% capacity, five seeds) consistent with this collapse rather than constituting an
independent multi-capacity confirmation."

**C8 — SGW ablation only severity 0/1:** added a note that all-pass is already 0.000 for *all*
policies at severities 2/3, so no coefficient choice can lower it further; the 1.00->0.00 transition
between severity 0 and 1 is the only discriminating case, which is where we confirm weight-insensitivity.

**C9 — Fleet-economics paragraph placement:** moved out of Results into the Supplement (next to its
figure), with the pointer in the Methods U_F definition updated to point there.

All changes compile cleanly (46 pp, 0 undefined references). The small length increase reflects the
reviewer-requested abstract caveat (C2), the welfare-weight description (C3), the sigma* discussion
(C4), and the evaluation-units table (C5); we offset by moving the fleet-economics paragraph and
figure to the Supplement.
