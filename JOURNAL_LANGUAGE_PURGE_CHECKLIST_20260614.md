# Journal-language purge checklist — 20260614

Target file: `APPLIED_ENERGY_MANUSCRIPT_SUBMISSION_REPAIR_20260614.tex`
Verified by grep after edits (see gate report). All forbidden phrases removed.

| # | Forbidden phrase | Where it was | Replacement | Status |
|---|---|---|---|---|
| 1 | "in an Applied Energy style" | Introduction (lit review) | "facility-level EV charging cost-service trade-off analysis" | ✅ removed |
| 2 | "For Applied Energy readers" | Conclusions | clause deleted; contribution stated directly | ✅ removed |
| 3 | "result CSVs" | Methods (gate computation) | "the recorded simulation outputs" | ✅ removed |
| 4 | "simulation scripts, CSV outputs" | Data & code availability | "analysis code, simulation outputs, figure-generation code, trace files, and environment metadata" (+ Zenodo DOI commitment) | ✅ removed |
| 5 | "controller-superiority story" | Results (matrix subsection) | "the paper makes no controller-superiority claim" | ✅ removed |

Also confirmed ABSENT (never present or already clean): "evidence package", "old story",
"Applied Energy readers", "scripts, CSV outputs", stray "\bcsv\b" tokens outside Data/code section.

Note: "controller-superiority **study**" (Introduction) is retained — it is a legitimate
description of study type, not process/file language.
</content>
