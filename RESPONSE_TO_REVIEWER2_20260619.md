# Response to Reviewer 2 — Applied Energy (major revision)

We thank Reviewer 2 for the detailed report. Only one comment required a new analysis (#1); it
used existing simulator outputs (no new runs). All others are addressed by reframing/clarification.

## Major

**#1 — Concrete Pareto vs same-episode demonstration. [NEW ANALYSIS]**
Added a paragraph + figure (Fig. pareto) in the Results "Actor gates change which policies look
successful" subsection. Using the existing 9-policy matrix: in the headline objective space of energy
cost and trip reliability, **CostOnly is Pareto-efficient and dominates the only acceptable policy,
ServiceFirst, on BOTH objectives** (cost 0.955<1.004, reliability 94.5%>93.3%) -- a multi-objective
optimizer would prefer CostOnly -- **yet CostOnly's same-episode all-pass is 0.000 vs ServiceFirst's
0.967**, because its 30.9-min wait and load-shape/critical-delivery costs fail the driver, fleet, and
grid gates. The two objective-optimal policies (CostOnly, QueueAware) both score 0%; the only
acceptable policy is objective-dominated. This makes the abstract "Pareto != conjunction" claim
concrete. (Also linked from the Discussion.) Code: pareto_demonstration_20260619.py.

**#2 — Which gates drive the collapse + defend THOSE thresholds.**
Added a paragraph in the robustness section: the load-bearing gates are critical-not-delivered (driver,
92%) and p95-wait (fleet, 81%); the other twelve fail <2%. We defend each cut-point: critical-not-
delivered <=24/week (~3.4/day) is a generous trip-readiness tolerance (severity-1 mean 46, ~2x over);
p95-wait <=30 min is a conventional service-level target (severity-1 mean 49, ~1.6x over). Both binding
failures overshoot defensible thresholds by 1.6-2x, and one-at-a-time loosening of either to 3x recovers
at most 0.054 -- so the collapse is not a fragile or one-loose-gate artifact.

**#3 — Single-d vs 5 behavior types.**
Addressed by connecting the preference-form ablation: because the screen outcome is insensitive to the
non-compliant preference form (5 behavior types + 8 coefficient variants) and governed by prevalence/
placement, collapsing to a scalar d preserves the relevant structure; a multi-type game adds state
without changing the diagnosis (every deviating type breaks the same per-vehicle guarantees). Framed as
a refinement for future incentive design.

**#4 — Energy-accounting ledger overstated.**
Recalibrated: the ledger "confirms the simulator's internal energy accounting is self-consistent...
ruling out numerical errors... It is an internal consistency check, not a validation against field
measurements." Removed the overclaiming framing.

**#5 — LeastLaxity laxity inputs vs action selection.**
Clarified: our model applies non-compliance at the level of ACTION selection (drivers override the
recommendation) with truthful scheduler inputs; we do NOT model information-level non-compliance
(misreported deadlines/needs) that would corrupt the laxity calculation. Such misreporting would degrade
LeastLaxity further, so our results are a conservative reading; input distortion is future work.

## Minor
- **#6** Fig 2 caption now has a reading guide (across severity / down actor gates / all-pass vs gate rows).
- **#7** Clarified all 14 gates are normative; the one physical limit (voltage) is NOT a gate, entering
  only via the separate non-binding IEEE-33 screen.
- **#8** Added a bridge: the five behavior types are operationalizations of the Eq.-preference under
  different p_keep and reserve/cheap margins.
- **#9** "request-event churn" now defined on first body use (more frequent request interactions without
  higher total energy demand).
- **#10** PoA distribution shape now reported: median 1.42, IQR [1.37,1.60], 41% in [1.4,1.6], 11% >1.7
  (concentrated, not uniform across [1.18,1.83]).

Compiles cleanly (0 undefined references). We are mindful of length and follow this revision with a
compression pass moving secondary robustness detail to the Supplement.
