# Applied Energy pre-submission gate report — 20260614

Authoritative manuscript: `APPLIED_ENERGY_MANUSCRIPT_SUBMISSION_REPAIR_20260614.tex`
→ compiles with `tectonic` to a 26-page PDF, 0 errors, 0 undefined references/citations.

This pass executed the full revision requested by the user, driven by the four user-raised
problems plus three additional blockers surfaced by the GPT-5.5 (codex) review
(`GPT55_REVIEW_VERDICT_20260614.md`).

## Gate results

| Gate | Requirement | Result |
|---|---|---|
| G1 Language | No "Applied Energy style / readers", "result CSVs", "evidence package", "controller-superiority story", "scripts, CSV outputs" | ✅ grep = 0 occurrences |
| G2 References | ≥ 40 verified references | ✅ 49 bibitems |
| G3 Citation hygiene | every reference cited; no cited-but-undefined | ✅ uncited = none; undefined = none |
| G4 Verified DOIs | added refs have Crossref-verified DOIs | ✅ 15/15 (see citation-purpose table) |
| G5 Weights defensible | provenance + dominance + sensitivity | ✅ normalization, dominance-by-construction, 6-variant ablation |
| G6 Weights ablation | main result invariant to weights | ✅ all 6 variants: all-pass 1.0 (sev0) → 0.0 (sev1) |
| G7 Figure 2 legible | main result obvious without text | ✅ 2-panel severity-collapse; full matrix → supplement S1 |
| G8 Severity bounded | stress-test framing + field citations | ✅ bracketing language + 4 field refs |
| G9 Thresholds | sensitivity presented near main result | ✅ moved into Results, not just Limitations |
| G10 Data/code | repo + citable DOI commitment | ✅ Zenodo-DOI-at-acceptance wording |
| G11 Compiles | PDF builds, refs resolve | ✅ tectonic exit 0, 26 pp |

## Claim-discipline preserved (no overclaiming introduced)
- No FleetBalanced superiority claim; ServiceFirst/Balanced kept as merged family.
- ServiceGridWeighted explicitly a heuristic comparator, not an optimizer/MPC.
- Behavioral effect = request-event churn, not true energy-demand amplification.
- IEEE-33 = representative stress screen, not feeder validation.
- Thresholds = normative, threshold-conditioned.
- All-pass collapse framed as joint-threshold result, not physical discontinuity.

## Key evidence added this pass
- `coeff_ablation_results_20260614.csv` + `COEFF_ABLATION_REPORT_20260614.md` — 6-variant
  weight ablation (35% cap, sev 0/1, both grid policies, 5 seeds; runtime 342.9 s).
  Verdict: severity-1 all-pass collapse is invariant to ServiceGridWeighted weights; the
  binding gate at severity 1 is the driver/compliance gate.
- New main Figure 2 (`fig2_actor_gate_acceptability_matrix`) + supplement
  `supp_full_actor_gate_matrix`.
- 15 new verified references (`REFERENCE_EXPANSION_AND_CITATION_PURPOSE_TABLE_20260614.md`).

## Residual / honest caveats
- Ablation is at 35% capacity only (matched the minimal pre-registered scope). The weekly
  20%/50% cells were not re-ablated; the manuscript does not claim they were.
- Behavioral severity remains uncalibrated by design; framed as stress test, not forecast.
- Cosmetic LaTeX warnings (underfull/overfull hbox) remain in two wide tables; non-blocking.

## Verdict
The four user-raised problems and the three GPT-5.5 blockers are resolved in the repaired
draft. The manuscript is materially closer to Applied Energy submission quality. Recommended
next human step: a coauthor read of the revised Introduction and the ablation subsection
before submission.
</content>
