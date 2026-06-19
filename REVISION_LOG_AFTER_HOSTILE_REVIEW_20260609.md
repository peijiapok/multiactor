# Revision log after hostile-review pass - 20260609

## Revised files

- `APPLIED_ENERGY_MANUSCRIPT_DRAFT_REVISED_20260609.md`
- `APPLIED_ENERGY_MANUSCRIPT_DRAFT_REVISED_20260609.tex`
- `APPLIED_ENERGY_MANUSCRIPT_DRAFT_REVISED_20260609.pdf`

The revised LaTeX manuscript compiles successfully with Tectonic. Remaining TeX warnings are minor table-layout underfull/overfull boxes, not build failures or evidence inconsistencies.

## Hostile-review issues addressed

### 1. Behavioral severity levels defined quantitatively

Added an exact behavioral severity parameter table in Methods. Values were recovered from `run_direct_wave2_severity_baseline_20260609.py`:

| Severity | Label | keep_probability | reserve_margin | cheap_extra_margin | Interpretation |
|---:|---|---:|---:|---:|---|
| 0 | `full_compliance` | 1.00 | 0.00 | 0.00 | upper-bound compliance benchmark |
| 1 | `mild_deviation` | 0.95 | 0.05 | 0.10 | small noncompliance stress test |
| 2 | `moderate_deviation` | 0.80 | 0.15 | 0.30 | intermediate stress test |
| 3 | `severe_deviation` | 0.55 | 0.25 | 0.60 | boundary stress case |

The text now explains that, at each vehicle-timestep, the driver keeps the grid-adjusted fleet recommendation with probability `keep_probability`; otherwise the vehicle uses a reserve/price-window self-service score. These labels are explicitly stress-test levels, not field-calibrated behavior forecasts.

### 2. Event churn explained

Added a Results paragraph and Discussion interpretation explaining that behavioral severity increases request-event pressure while the demanded-kWh ledger does not increase. The manuscript now states that the mechanism is event churn: request interactions become more frequent or fragmented, increasing timing volatility, retry/reissue burden, and service-accounting stress. The manuscript explicitly rejects true energy-demand amplification as an allowed claim.

### 3. Actor-gate threshold justification strengthened

Expanded Methods text around the actor-gate table. Driver gates are framed as service adequacy, reliability, and critical unmet service; fleet gates as operational burden, queue/wait pressure, cost, and demand-charge exposure; grid gates as peak, ramp, load-shape, and load-factor discipline. The manuscript now states that thresholds are pre-specified normative criteria, not universal constants, and that threshold sensitivity exposes dependence rather than proving threshold-independent robustness.

### 4. Abstract shortened and polished

Rewrote the abstract to foreground the energy-systems contribution and the main results. Removed audit-report density from the opening and retained only the core numbers: weekly 100% to 0% all-pass collapse at severity 1, targeted 28-day 100% to 0% confirmation at 35% capacity, event-churn classification, PeakPenalty not rescuing all-pass outcomes, and FleetBalanced not being claimed as distinct.

### 5. Broader introduction paragraph added

Added a near-end Introduction paragraph explaining why the result matters beyond the simulator: managed charging and fleet controllers often assume high compliance and evaluate energy, cost, or peak metrics separately, but deployment readiness requires stakeholder gates and request-pipeline audits when behavioral deviations create event churn.

### 6. ServiceGridWeighted baseline specified

Added a Methods equation and exact term table for ServiceGridWeighted. Values recovered from `run_direct_wave2_severity_baseline_20260609.py`:

- Service score: `320*C_i + 175*L_i + 120*T_i + 95*D_i + 55*X_i`.
- Flexible low-risk eligibility: already recommended by LeastLaxity; not critical; not low SoC; `SoC_i >= theta_i + 0.20`; target deficit `<= 0.12`.
- Trigger: maximum queue pressure `>= 0.35`, projected peak pressure positive, or normalized price `>= 0.80`.
- Grid penalty: `48*Q_i + 32*P_t + 18*R_t`, applied only to flexible low-risk candidates.
- Deferral cap: at most `floor(0.20*n_F)`, with at least one candidate allowed when the flexible set is non-empty.

The manuscript now states that weights are fixed, not tuned across seeds/capacities/outcomes, and that the baseline is a heuristic comparator, not MPC, LP, or an optimizer.

### 7. Limitations expanded

Rewrote Limitations as separate paragraphs covering normative gates, uncalibrated behavior stress tests, demanded-kWh trace scope, targeted 28-day scope, IEEE-33 representativeness, ServiceGridWeighted heuristic status, FleetBalanced non-distinctness, and simulation-only evidence.

### 8. Figure captions clarified

Updated main figure captions to state result claims directly while preserving claim discipline:

- Fig. 2: service-oriented policies pass under full compliance but behavioral deviation eliminates all-pass outcomes.
- Fig. 3: request-event pressure rises while acceptability collapses abruptly.
- Fig. 5: PeakPenalty lowers selected peak metrics but does not rescue all-pass outcomes.
- Fig. 6: IEEE-33 results are EV-off-relative feeder stress deltas, not validation.

### 9. Audit-report tone reduced

Searched for and revised internal project wording. The manuscript now uses journal-style terms such as `this study`, `simulation campaign`, `trace audit`, `evaluated scenarios`, and `supplementary audit`. Local absolute paths are not used in manuscript prose.

### 10. Consistency and claim discipline checked

Final scan found no unsupported claims of FleetBalanced superiority, true energy-demand amplification, feeder validation, site-specific feasibility, threshold-independent robustness, or optimality. Remaining matches for `site-specific validation` and `optimal controller/control` occur only in explicit negations.

## Additional coauthor-review polish after author details

### 11. Author and end-matter placeholders cleaned

Inserted Peijia Pok, Soomin Woo, and Hwasoo Yeo with KAIST/Konkuk affiliations and corresponding-author email. Replaced placeholder CRediT text with named author roles. Replaced acknowledgement placeholder language with a neutral no-acknowledgement/no-funding declaration for draft circulation.

### 12. Abstract claim language softened

Replaced `deployment-invalid` with `not mutually acceptable under explicit stakeholder gates` and shortened the abstract methods-list sentence.

### 13. Compile and figure check

Verified that all six referenced figure PDFs exist and compiled the revised LaTeX with Tectonic. The manuscript builds successfully. Remaining warnings are minor front-matter/table layout warnings, mainly from dense reproducibility tables.
