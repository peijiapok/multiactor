# Figure 2 redesign report — 20260614

## Problem
Old Figure 2 (`supp_full_actor_gate_matrix` now) was a 20-row heatmap mixing
policy × behavior-severity × grid-policy on the rows and 4 gates on the columns.
A reader could not extract the main result in seconds; it asked them to decode
~80 cells. Both the user and GPT-5.5 flagged it as high-severity / unintelligible.

## Redesign (new main Figure 2)
Two panels, built by `fig2_actor_gate_matrix()` in
`figure_scripts/build_final_figures_20260609.py`:

- **Panel A** — condensed heatmap: rows = behavior severity 0/1/2/3, columns =
  Driver / Fleet / Grid gates + the **All-pass conjunction** (boxed in red). Values
  averaged over the service-oriented family (ServiceFirst + ServiceGridWeighted),
  both grid policies, all capacities. Shows 1.00→0.00 collapse at a glance.
- **Panel B** — all-pass rate vs severity, one line per service fleet policy. The two
  lines coincide (reinforcing the "no controller-superiority" claim), and severity 1
  is annotated "All-pass = 0% (gates still 0.03/0.18/0.38)".

Headline (suptitle): *"Multi-actor acceptability collapses one severity step before
the individual gates do."*

## What moved where
- New main figure file keeps the same output name
  `fig2_actor_gate_acceptability_matrix.{png,pdf}` (so the `\includegraphics` path is
  unchanged in the .tex).
- The full 20-row matrix is preserved as **supplementary** `supp_full_actor_gate_matrix.{png,pdf}`
  and referenced in-text as Figure S1, so no information is lost.

## Manuscript text
Figure 2 caption rewritten to state the joint-threshold reading explicitly and to note
it is not a physical discontinuity. Body paragraph (Results) now points the full matrix to
the supplement and keeps the comparator (CostOnly/QueueAware) discussion with Table 6.

## Verification
`python3 figure_scripts/build_final_figures_20260609.py` regenerates both figures with
exit 0. Visual check confirms the all-pass collapse is legible in <10 s.

## Other figures
Fig 1 (framework) and Fig 3 (severity curve) were judged already clear and were left
unchanged. The redesign is scoped to Figure 2, the only unintelligible main figure.
</content>
