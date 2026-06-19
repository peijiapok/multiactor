# ServiceGridWeighted coefficient provenance — 20260614

Addresses the reviewer concern (user + GPT-5.5) that the weights in
`S_i = 320 C_i + 175 L_i + 120 T_i + 95 D_i + 55 X_i` and the grid penalty
`(48 Q_i + 32 P_t + 18 R_t)` are undefined-looking magic numbers.

## What the weights are (and are not)

- **Source:** fixed ordinal salience weights written into the `service_grid_weighted`
  closure of `run_direct_wave2_severity_baseline_20260609.py` **before** the severity
  sweep was run. They are author-chosen, not estimated from data, not tuned on any
  outcome, seed, or capacity.
- **They are not:** calibrated parameters, an optimizer's solution, an MPC cost, or a
  claim of optimality. ServiceGridWeighted is a transparent comparator that exists only
  to remove strawman-baseline risk (so the matrix is not just CostOnly/QueueAware).

## Provenance / dominance table

| term | symbol | meaning | weight (integer) | normalized (/100) | role |
|---|---|---|---:|---:|---|
| Critical service | C | reserve need OR deadline deficit>0 OR near-mandatory OR laxity≤0.25 | 320 | 3.20 | protect (highest) |
| Low SoC | L | SoC ≤ θ+0.05 | 175 | 1.75 | protect |
| Target deficit | T | target-energy-deficit state | 120 | 1.20 | protect |
| Deadline deficit | D | deadline-energy-deficit state | 95 | 0.95 | protect |
| Inverse laxity | X | 1−clip(laxity,0,1) | 55 | 0.55 | order flexible |
| Queue pressure | Q | local (queued+requested−slots)/slots | 48 | 0.48 | grid penalty (flexible only) |
| Peak pressure | P | (n_req−0.85·n_slots)/n_slots | 32 | 0.32 | grid penalty (flexible only) |
| Price pressure | R | price / schedule-max | 18 | 0.18 | grid penalty (flexible only) |

## Two-line defense (now in the manuscript)

1. **Rescaling is decision-identical.** The deferral rule depends only on candidate
   *ranking*, so dividing every coefficient by 100 (or any positive constant) changes no
   decision. The integer magnitudes carry no physical meaning beyond order.
2. **Dominance by construction, not by magnitude.** Critical / low-SoC / deadline-risk
   requests are excluded from the deferral-eligible set `F_i` *by the eligibility filter*
   (must be non-critical, non-low-SoC, SoC ≥ θ+0.20, target deficit ≤ 0.12). Therefore **no
   grid penalty, however large, can defer a protected request.** The weights only order the
   already-flexible, low-risk candidates among themselves. This is why ServiceGridWeighted
   can never collapse into a cost-only or grid-only controller regardless of the exact numbers.

## Empirical robustness

The above is backed by a coefficient sensitivity ablation (5 variants: base, normalized,
equal-service, no-grid-penalty, ±25% perturbation) at 35% capacity, severity 0 and 1, both
grid policies, 5 seeds — see `COEFF_ABLATION_REPORT_20260614.md` and manuscript
Section "ServiceGridWeighted coefficient sensitivity". Verdict: the headline severity-1
all-pass collapse is invariant to the weight choice.
</content>
