# Applied Energy submission package — 20260615

- manuscript.tex / manuscript.pdf : main manuscript (supplement embedded after Conclusions; 33 pp)
- figures/ : all 12 figures (8 main + 4 supplementary), referenced by the .tex
- highlights.txt, cover_letter.md, graphical_abstract.pdf

Compile: `tectonic manuscript.tex` (self-contained; verified clean from an empty folder).
NOTE: references are embedded (\begin{thebibliography}); no separate .bib needed.
At submission, if Applied Energy requires the supplement as a SEPARATE file, split the
"Supplementary material" section (after Conclusions) into its own document — but note this
will break the main-text cross-references \ref{sec:supp}, \ref{fig:suppmatrix},
\ref{fig:suppthresh}, \ref{tab:sgwablation}, \ref{tab:sgwterms} unless the `xr` package is
used or the numbers are hard-coded. For initial submission/review, the combined PDF is accepted.
