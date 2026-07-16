# Research review of the Chapter-2 committee feedback
*(Reviewed against the current manuscript + stress-tested with GPT. Note: no "research-review" skill is installed on this machine — only `zero-trial` and code/PR-review plugins — so this is a manual expert review.)*

## Overall verdict
The feedback is **high-quality and constructive**. Roughly **half is already addressed** in the current
manuscript; the other half are **genuine improvements**, and it correctly identifies **one intellectually
load-bearing gap**: the gates are not yet grounded in explicit **mechanism-design formalism** (individual
rationality, incentive compatibility, budget balance) + an **"optimize *within* the feasible set"** statement.
Without that, the gates read as an "ad-hoc checklist"; with it, they are a defensible participation-feasibility
object. The one place the feedback **overreaches** is asking the *paper* to become a broad managed-charging
practice review (fine for the thesis chapter; a short paragraph in the paper).

## Section-by-section status

| # | Feedback item | Status in current paper | Action |
|---|---|---|---|
| 2 | Gates = deployability screen, complementary to optimization (not a replacement) | ✅ **Done** (abstract + intro) | keep |
| 3 | Blended objective is compensatory | ✅ **Done** (abstract) | keep |
| 4 | Ground gates in constrained-opt / IR / participation | 🟡 Partial (IR/participation yes; IC/viability not formal) | **ADD formalism** |
| 5 | Comparison table vs weighted/multi-obj/hierarchical | 🟡 Partial (Pareto compared) | add table (thesis) |
| 6 | `min J` **s.t.** all-pass gates (optimize within feasible set) | 🟡 Mentioned, not formal | **ADD (high value)** |
| 7 | Rename **fleet → charging operator** | ❌ Not done | **DO (global)** |
| 8 | Define decentralization | 🟡 Partial | define formally |
| 9 | Actor motivations (driver/operator/grid) | 🟡 Mostly (gates map to these) | make explicit (thesis) |
| 10 | Synergy/trade-off + override→peak-returns loop | 🟡 Loop is implicit | state the loop |
| 11 | Mechanism-design foundations (IR, IC, budget) | ❌ Not formal | **ADD — #1 GAP** |
| 12 | Define the mechanism `M=(r,p,π)` | ❌ Not done | **ADD** |
| 13 | Real-world managed-charging practice review | 🟡 Cites pilots only | thesis: add; **paper: short para only (overreach otherwise)** |
| 14 | Compare with hierarchical control ("feasible but behaviorally unstable") | 🟡 Implicit | state explicitly (nice framing) |
| 15 | Define grid policy operationally | 🟡 Partial (PeakPenalty defined) | sharpen definitions |
| 16 | Rename terms (self-service→**recommendation-override**; benign→**additional coordinated requests**; define actor-gate/all-pass/churn) | ❌ Not done | **DO (term renames + glossary)** |
| 17 | Why game theory (players/actions/utilities/info/outside options) | 🟡 Mostly (game section) | add explicit tuple |
| 18 | Rebuild methodology: actor→decision→constraint→behavior→utility→gate | 🟡 Structure exists | reorder (thesis) |
| 19 | 6 p.m. worked example | ❌ Not done | thesis: add; **paper: compact box or omit** |

## Prioritized plan (GPT-convergent)

**Tier 1 — do for BOTH paper and thesis (highest value, defensibility):**
1. **Mechanism-design formalism** — add IR (`U_i(M) ≥ U_i^0`), incentive compatibility (`U_D(follow) ≥ U_D(deviate)`), budget balance (`Σ p_i ≤ B`), and define the mechanism `M=(r,p,π)`. *This is the #1 gap — it makes the gates intellectually defensible.*
2. **Optimize-within-feasible-set** — state `min_x J(x) s.t. A_D=A_O=A_G=1` explicitly. Cleanly kills the "gates replace optimization" criticism.
3. **Rename `fleet operator → charging operator`** globally (with a one-line definition). "Fleet" wrongly implies vehicle ownership.
4. **Term renames + glossary** — self-service deviation → **recommendation-override**; benign request increase → **additional coordinated requests**; define *actor gate*, *all-pass feasibility*, *request-event churn*.

**Tier 2 — thesis chapter (pedagogical; would bloat the concise paper):**
5. Methodology reorder (actor→decision→constraint→behavior→utility→gate).
6. The comparison table (weighted / multi-objective / hierarchical / gates).
7. Real-world managed-charging practice review (TOU, DLC, opt-in/out, aggregators, override).
8. The 6 p.m. worked example (compact box in the paper if space allows).
9. Explicit game tuple (players, actions, utilities, information, outside options, equilibrium).
10. Formal decentralization definition + the hierarchical-control "feasible but behaviorally unstable" framing.

**Overreach to resist:** turning the *paper* into a managed-charging practice survey (keep to one paragraph).

## Key scope question
The feedback is titled "**Chapter 2**" (thesis), but the content lives in the Applied Energy manuscript.
Tier-1 items improve **both**; Tier-2 items are **thesis-appropriate** and would bloat the 56-pp paper.
Decision needed: revise the **paper**, a separate **thesis chapter**, or **both**.
