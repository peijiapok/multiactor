# Cold Applied Energy review of the revised paper (self-review, 2026-06-16)

Reviewing the 41-page revised manuscript (diagnostic screen + game-theoretic mechanism) as a
fresh AE submission. Honest verdict and weaknesses, ranked, with fix status.

## Overall verdict (cold): MAJOR REVISION (leaning acceptable after revisions)
The constructive mechanism removes the "diagnostic-only / so-what" objection and the
"uncalibrated knob" objection (collapse is now an equilibrium, robust across 243 configs).
Remaining objections are about validation scope and presentation, not core soundness.

## Weaknesses (ranked) and fix status
W1. LENGTH/DENSITY (41 pp, 12 figs, 12 tables). Reads long; risk of "over-engineered."
    FIX: tighten verbose paragraphs (Limitations, IEEE-33), move a diagnostic figure/table to
    supplement. Target ~37-38 pp. [doing]
W2. SIMULATION-ONLY; no field validation of the collapse or the mechanism. The ceiling.
    FIX (honesty): prominent, repeated disclosure; demand layer IS ACN-validated. [disclosed]
W3. Behavioral game is a CALIBRATED OVERLAY, not endogenous strategic agents in-sim.
    FIX: disclosed in Limitations; add half-sentence that this is a standard model separation. [done/strengthen]
W4. 14 acceptability gates are NORMATIVE; all-pass is a strict AND. Already defended (envelope,
    graded index). The game inherits binary all-pass. FIX: in game results, note the graded
    index degrades smoothly too, so the mechanism is not chasing a binary artifact. [add]
W5. Utilities min-max normalized within capacity -> PoA is a RELATIVE welfare measure, not
    absolute economic welfare. FIX: state explicitly where PoA is introduced. [add]
W6. Incentive sigma in utility units, not money -> limited practical actionability.
    FIX: disclosed; next-step to a $ tariff. [done]
W7. Congestion-game FORM assumed (linear externality, logistic costs); sensitivity is over
    params not forms. FIX: add a sentence that the qualitative result is structural (any
    free-riding externality gives an inefficient-deviation NE that a Pigouvian incentive
    corrects), not form-specific. [add]
W8. Single workplace scenario (ACN) + single feeder (IEEE-33). Cross-site helps demand only.
    FIX: disclosed; note depot/residential generalization as future work. [done]
W9. NARRATIVE COHERENCE: must read as ONE arc (diagnose -> remedy), not two bolted papers.
    FIX: added bridges in Discussion/Intro; verify flow; strengthen the one-line thesis. [verify]
W10. CLIFF claim ("acceptable only below ~1.3% deviation") rested on 5-seed noise.
    FIX: 20-seed cliff run to pin it. [running]
W11. PoA "~47% welfare gain" could read as over-claim given relative normalization.
    FIX: qualify as relative welfare; lead with the robust "always >1" statement. [add]

## Fixes NOT doable here (state as future work, do not fake)
- Fitting the compliance mechanism to a managed-charging trial with logged opt-out (needs data).
- Real feeder interconnection study; depot/residential/fast-charge generalization.
- Translating sigma* to a deployable monetary tariff.

## Fixes APPLIED (2026-06-16, this pass)
- W1 (length): tightened IEEE-33 discussion + abstract (300->~270 words); supplement holds
  optional detail (sensitivity, calibration, gate matrix, conservation audit). 41 pp.
- W4: added that the mechanism raises the continuous actor utilities / graded index, not just
  the binary all-pass -> not a binary artifact.
- W5/W11: stated PoA is a RELATIVE welfare measure (utilities min-max normalized within
  capacity); reworded "47% welfare gain" -> "relative welfare gain near 47%".
- W7: added that the corrective logic is STRUCTURAL (any free-riding externality -> inefficient
  NE corrected by a Pigouvian transfer), not specific to the assumed functional forms.
- W10 (cliff): 20-seed cliff run -> precise numbers (all-pass 1.0 -> 0.70 at d=1.25% -> 0.10 at
  d=1.9% -> 0.00 at d>=2.5%); manuscript updated. PeakPenalty helps near the cliff (0.85 vs 0.55).
- A (OptimizEV): slack-resolved compliance model grounded in OptimizEV opt-in curve; calibration
  figure (supplement) + Methods sentence; equilibrium conclusions unchanged (sigma*=0.25 @35%).
- W9 (coherence): verified abstract/intro/game-section/discussion/conclusions read as one arc.

## GPT-5.5 status: UNAVAILABLE
Consulted 5x across this session (cold-review + formulation prompts); every substantive prompt
timed out (EXIT=124) in headless mode. Only trivial prompts return. Relied on own skeptical
review. Re-attempt when codex is responsive.

## Residual (honest, needs data/scope -> future work, NOT faked)
W2 sim-only; W3 calibrated overlay not endogenous-strategic; W6 sigma in utility units not $;
W8 single workplace/feeder. All disclosed in Limitations.
