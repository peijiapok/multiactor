# Tier 4 — How to fit the behavioral-response MECHANISM (the gold-standard, coauthor-led step)

This is the single change that would most move the paper from "plausible" to "likely accepted" at
Applied Energy. It is the one thing I could not do here, because it needs data with **logged
compliance/opt-out/override decisions** that is not in the workspace. This guide makes it concrete.

## What the paper currently has vs what Tier 4 adds
- **Now (Tier 1, done):** the deviation *magnitude* (severity 1 = 5%) is anchored to observed
  plan-deviation rates in ACN-Data (~10% input changes, ~33% early disconnects). Magnitude only.
- **Tier 4:** fit the deviation *mechanism* — the probability a driver deviates and what they do —
  as a function of state, to a real managed-charging dataset, then re-run the screen.

## Step 1 — Get a dataset with logged recommended-vs-actual actions
You need, per charging session or per decision point: the **recommended/scheduled action** the
system issued, and the **actual action** taken (kept / opted out / overrode / unplugged early),
ideally with state (SoC, deadline/slack, time-of-use window, incentive offered).

Candidate sources (most need a data-sharing agreement — start the request now, it is the long pole):
1. **A utility managed-charging pilot** (SmartCharge / EV managed-charging programs). Utilities log
   per-event opt-out. This is the cleanest source.
2. **Electric Nation trial** (EA Technology / Western Power Distribution, ~700 EVs) — has app
   override ("boost") logs.
3. **Aggregator logs** (ev.energy, WeaveGrid, Optiwatt, Optiwize) — per-session managed vs overridden.
4. **ACN adaptive-scheduling logs** (Caltech ACN) if the *scheduled vs delivered* action stream is
   available, not just sessions (the public ACN-Data has sessions, not the scheduler's recommended
   action per timestep — ask the ACN team).
5. **Your own pilot**, if any coauthor's group runs one.

## Step 2 — Estimate a state-dependent compliance model
Replace the fixed severity parameter $p_{keep}$ with a fitted function $p_{keep}(\text{state})$:
- Regress the observed keep/deviate decision on state: SoC, deadline laxity/slack, time-of-use
  window, incentive, vehicle/user fixed effects. A logistic model is enough to start.
- Fit the **deviation response** too: when a driver deviates, what do they do (charge now / delay /
  unplug)? Fit the noncompliant preference rule (currently `260C+130N+95T+...`) to observed choices.

A lighter, partially-achievable version ("soft Tier 4"): the **OptimizEV pilot** (Alexeenko & Bitar
2023, already cited) reports **opt-in vs scheduling slack** (~10% opt-in at low slack rising to ~80%
at high slack). Digitize that published curve and fit $p_{keep}(\text{slack})$ to it. That turns the
constant 5% into a slack-dependent compliance function calibrated to a real published behavioral
curve — weaker than full trial fitting, but a real mechanism anchor obtainable from the literature.

## Step 3 — Re-run the screen under the fitted model and report
- Swap the fitted $p_{keep}(\text{state})$ into the simulator's driver layer (replaces the fixed
  severity levels) and re-run the acceptability sweep.
- Report whether the **all-pass collapse persists under the empirically fitted behavioral model**.
  If it does, the headline is no longer "under bracketed scenario deviations" but "under an
  empirically fitted behavioral response" — the framing reviewers want.
- Keep the stress-test severities as a sensitivity sweep around the fitted operating point.

## Step 4 — Validate the behavioral model
- **Hold-out:** fit on part of the trial, predict opt-out on held-out sessions, report ROC/AUC or
  calibration. This is the evidence a reviewer will ask for.
- **Consistency check:** confirm the fitted deviation distribution is consistent with the
  ACN-anchored magnitudes already in the paper (Tier 1).

## What to say in the cover letter / response
If Tier 4 is done: lead with it — "the central behavioral mechanism is fitted to and validated
against [dataset]." If it cannot be done before submission: state explicitly that the contribution
is a **screening framework with literature-/ACN-anchored stress scenarios**, and that mechanism
calibration against a managed-charging trial is the defined next step — and pre-empt the reviewer by
offering the OptimizEV-curve soft calibration (Step 2) as a partial response if asked.

## Bottom line
Tier 1 (done) anchors *how much* drivers deviate to real data. Tier 4 anchors *when and how* they
deviate. The first is achievable from public data (done); the second needs trial data with logged
decisions and is the highest-value thing the coauthors can pursue. Start the data-access request now.
</content>
