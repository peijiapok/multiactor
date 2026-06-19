# GPT-5.5 path-to-MINOR verdict + field-evidence anchors — 20260615

## GPT-5.5 prioritized package (codex, approval=never)

Highest impact-per-effort path to MINOR:

1. **Behavior anchoring + transparent external validity limits**
Yes, anchoring 5% / 20% / 45% deviation cases to published opt-out ranges is probably enough to blunt the “uncalibrated behavior” critique **if framed correctly**.

Do **not** claim calibration. Claim **literature-anchored scenario stress testing**:

- 5% = optimistic / low-friction case below typical reported opt-out.
- 20% = central case inside reported 16-40% per-event opt-out range.
- 45% = adverse boundary case slightly above the reported range, representing compounding distrust, incentive fatigue, or post-incentive reversion risk.

This answers: “Are your behavior knobs arbitrary?”  
It does **not** answer: “Do these actors behave like a specific real population?”

That distinction is crucial. A reviewer will tolerate no proprietary dataset if the paper stops pretending to estimate real behavior and instead says: “We test whether conclusions survive plausible acceptance regimes observed in pilots.”

Also cite the near-full reversion after incentives stop as justification for the high-severity / low-acceptance boundary, not as calibration.

2. **Increase seeds and add 20% / 50% capacity**
Yes, this is worth doing. It is probably the best empirical patch.

Move from **5 to 20 seeds**. Five seeds looks fragile for a simulation paper. Twenty is still modest, but defensible if paired with confidence intervals, bootstrapped intervals, or at least seed-level dispersion plots.

Add **20% and 50% capacity cells** around the existing 35% cap. This directly addresses the “single 35%-cap-only, 28-day” concern with low conceptual overhead.

Recommended capacity grid:

- 20% = constrained deployment
- 35% = original / medium
- 50% = expanded flexibility

This lets you show whether the decomposition / aggregation / threshold-envelope claim is robust or an artifact of one capacity setting.

If effort is limited, do **20 seeds first**, then capacity cells. But the combination is what makes the revision look serious.

3. **IEEE-33 voltage flatness**
Do **not** keep presenting zero voltage deltas as if meaningful.

Best path: **reframe and demote the voltage metric**, not drop it entirely.

Say IEEE-33 at the modeled EV penetration is voltage-insensitive, so the voltage screen is retained only as a non-binding feasibility check. The grid acceptability gate is therefore governed by the load-shape sub-gate in this study.

Do **not** run a higher-penetration feeder unless easy. It risks opening a new paper: voltage sensitivity, feeder hosting capacity, location of EV loads, reactive power, transformer constraints, etc. That can create more reviewer attack surface.

Dropping the metric entirely may look evasive. Reframing is cleaner:

- Main grid acceptability result: load-shape gate.
- Voltage result: non-binding under IEEE-33 / studied penetration.
- Limitation: voltage conclusions do not generalize to weaker feeders or higher penetration.
- Optional appendix stress test only if cheap.

4. **Smallest change set that justifies MINOR**
The minimum credible package:

1. Rename behavioral parameters as **literature-anchored scenario severities**, not calibrated behavioral estimates.
2. Add a table mapping 5% / 20% / 45% to published opt-out / reversion evidence.
3. Expand stochastic robustness from **5 to 20 seeds**, with dispersion or uncertainty intervals.
4. Add **20% / 35% / 50% capacity** sensitivity.
5. Reframe IEEE-33 voltage as a **non-binding feasibility screen**, with load-shape explicitly identified as the binding grid acceptability sub-gate.
6. Add a limitations paragraph stating no proprietary behavioral calibration, no claim of population-specific prediction, 28-day horizon, and feeder voltage insensitivity.

This is enough for MINOR if the core results survive. Without the seeds/capacity expansion, I would keep it MAJOR. The behavior anchoring alone is rhetorically useful but not sufficient; the paper needs at least one visible robustness expansion to look revised rather than merely reworded.
Highest impact-per-effort path to MINOR:

1. **Behavior anchoring + transparent external validity limits**
Yes, anchoring 5% / 20% / 45% deviation cases to published opt-out ranges is probably enough to blunt the “uncalibrated behavior” critique **if framed correctly**.

Do **not** claim calibration. Claim **literature-anchored scenario stress testing**:

- 5% = optimistic / low-friction case below typical reported opt-out.
- 20% = central case inside reported 16-40% per-event opt-out range.
- 45% = adverse boundary case slightly above the reported range, representing compounding distrust, incentive fatigue, or post-incentive reversion risk.

This answers: “Are your behavior knobs arbitrary?”  
It does **not** answer: “Do these actors behave like a specific real population?”

That distinction is crucial. A reviewer will tolerate no proprietary dataset if the paper stops pretending to estimate real behavior and instead says: “We test whether conclusions survive plausible acceptance regimes observed in pilots.”

Also cite the near-full reversion after incentives stop as justification for the high-severity / low-acceptance boundary, not as calibration.

2. **Increase seeds and add 20% / 50% capacity**
Yes, this is worth doing. It is probably the best empirical patch.

Move from **5 to 20 seeds**. Five seeds looks fragile for a simulation paper. Twenty is still modest, but defensible if paired with confidence intervals, bootstrapped intervals, or at least seed-level dispersion plots.

Add **20% and 50% capacity cells** around the existing 35% cap. This directly addresses the “single 35%-cap-only, 28-day” concern with low conceptual overhead.

Recommended capacity grid:

- 20% = constrained deployment
- 35% = original / medium
- 50% = expanded flexibility

This lets you show whether the decomposition / aggregation / threshold-envelope claim is robust or an artifact of one capacity setting.

If effort is limited, do **20 seeds first**, then capacity cells. But the combination is what makes the revision look serious.

3. **IEEE-33 voltage flatness**
Do **not** keep presenting zero voltage deltas as if meaningful.

Best path: **reframe and demote the voltage metric**, not drop it entirely.

Say IEEE-33 at the modeled EV penetration is voltage-insensitive, so the voltage screen is retained only as a non-binding feasibility check. The grid acceptability gate is therefore governed by the load-shape sub-gate in this study.

Do **not** run a higher-penetration feeder unless easy. It risks opening a new paper: voltage sensitivity, feeder hosting capacity, location of EV loads, reactive power, transformer constraints, etc. That can create more reviewer attack surface.

Dropping the metric entirely may look evasive. Reframing is cleaner:

- Main grid acceptability result: load-shape gate.
- Voltage result: non-binding under IEEE-33 / studied penetration.
- Limitation: voltage conclusions do not generalize to weaker feeders or higher penetration.
- Optional appendix stress test only if cheap.

4. **Smallest change set that justifies MINOR**
The minimum credible package:

1. Rename behavioral parameters as **literature-anchored scenario severities**, not calibrated behavioral estimates.
2. Add a table mapping 5% / 20% / 45% to published opt-out / reversion evidence.
3. Expand stochastic robustness from **5 to 20 seeds**, with dispersion or uncertainty intervals.
4. Add **20% / 35% / 50% capacity** sensitivity.
5. Reframe IEEE-33 voltage as a **non-binding feasibility screen**, with load-shape explicitly identified as the binding grid acceptability sub-gate.
6. Add a limitations paragraph stating no proprietary behavioral calibration, no claim of population-specific prediction, 28-day horizon, and feeder voltage insensitivity.

This is enough for MINOR if the core results survive. Without the seeds/capacity expansion, I would keep it MAJOR. The behavior anchoring alone is rhetorically useful but not sufficient; the paper needs at least one visible robustness expansion to look revised rather than merely reworded.

## Verified field-evidence anchors (subagent, Crossref-checked)

- Per-event opt-out in residential managed-charging pilots ~16-40%:
  - OptimizEV (Alexeenko & Bitar 2023, TR-D, DOI 10.1016/j.trd.2023.103658): session opt-in ~60% overall (~40% opt-out), ~10% opt-in (~90% opt-out) for low-flexibility sessions, up to ~80% for high-slack.
  - Electric Nation (Dudek 2021, IEEE P&E Mag, DOI 10.1109/MPE.2021.3072714): ~700 EVs; customer override used; >60% changed default preference.
  - Bailey/Brown/Shaffer/Wolak 2025 (AEJ:EP, DOI 10.1257/pol.20230653): charge-timing reverts ~fully once incentives withdrawn; 49% peak-hour reduction under reward.
  - (SEPA 2021 ~84% opt-in / ~16% opt-out: directional, report not opened firsthand — NOT cited as a hard figure.)
- Mapping used in manuscript Table (literature anchoring):
  - severity 1 (~5% deviation) = conservative, below typical opt-out
  - severity 2 (~20%) = central, within observed range
  - severity 3 (~45%) = adverse boundary (low-flexibility / withdrawn incentives)
