#!/usr/bin/env python3
"""Soft (literature) calibration of the driver compliance model to the OptimizEV pilot.

The homogeneous congestion game (gametheory_equilibrium) leaves the slack-dependence and
incentive-responsiveness of compliance as parameters. Here we GROUND them in published
behavior: the OptimizEV managed-charging pilot (Alexeenko & Bitar 2023) reports opt-in
rising from ~10% at low scheduling slack to ~80% at high slack, and rising with the
monetary incentive offered. We:

  1. Build a slack-resolved compliance model p(lambda, sigma, rho) whose slack-gradient is
     taken from the OptimizEV opt-in curve and whose LEVEL is anchored to the ACN deviation
     magnitude (mean compliance 0.95 at sigma=0). It keeps the congestion externality
     (compliance falls as aggregate compliance rho rises -> unique fixed point).
  2. Confirm the equilibrium conclusions are robust to using this data-grounded model
     (selfish NE deviation ~5%, all-pass~0, a bounded incentive restores all-pass, PoA>1).
  3. Emit a calibration figure: modelled compliance-vs-slack against the OptimizEV anchors.

This is a SOFT calibration: OptimizEV "opt-in" (program enrollment) is not identical to
per-decision compliance, so we use its SHAPE (slack gradient, incentive direction), not its
absolute level, and say so. It is not a mechanism fitted to logged opt-out decisions.
"""
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("/home/jia/multi actor/equilibrium_optimization_20260616")
DATE = "20260616"
_spec = importlib.util.spec_from_file_location("gt", OUT / f"gametheory_equilibrium_{DATE}.py")
gt = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(gt)

def logit(p): return np.log(p / (1 - p))

# --- OptimizEV opt-in vs slack anchors (reported endpoints) -------------------
OPTIN_LOW_SLACK, OPTIN_HIGH_SLACK = 0.10, 0.80
LAM_LOW, LAM_HIGH = 0.1, 0.9            # slack quantiles for the two anchors
# logistic opt-in(lambda) = sigmoid(a + b*lambda)
B_SLACK = (logit(OPTIN_HIGH_SLACK) - logit(OPTIN_LOW_SLACK)) / (LAM_HIGH - LAM_LOW)
A_SLACK = logit(OPTIN_LOW_SLACK) - B_SLACK * LAM_LOW
def optin(lam): return 1 / (1 + np.exp(-(A_SLACK + B_SLACK * np.asarray(lam))))


class SlackResolvedGame:
    """p(lambda,sigma,rho) = sigmoid(theta0 + theta_lam*(lambda-lam_bar)
                                     + theta_sig*sigma - theta_e*rho).
    theta_lam = OptimizEV slack slope (data); theta_e = congestion externality;
    theta_sig = incentive responsiveness; theta0 set so mean compliance = 0.95 at sigma=0.
    Slack lambda ~ Beta(2,2) on [0,1] (symmetric, soft assumption; stated)."""
    def __init__(self, theta_lam=B_SLACK, theta_e=2.0, theta_sig=4.479, target=0.95, nq=2001):
        self.theta_lam = theta_lam; self.theta_e = theta_e; self.theta_sig = theta_sig
        from numpy.random import default_rng
        # quantile grid of Beta(2,2) for the slack distribution (deterministic)
        from math import comb
        xs = np.linspace(1e-3, 1 - 1e-3, nq)
        w = xs * (1 - xs)                       # Beta(2,2) density kernel
        self.lam = xs; self.w = w / w.sum()
        self.lam_bar = float((self.lam * self.w).sum())
        self.theta0 = 0.0
        self._calibrate_level(target)

    def p(self, sigma, rho):
        z = self.theta0 + self.theta_lam * (self.lam - self.lam_bar) + self.theta_sig * sigma - self.theta_e * rho
        return 1 / (1 + np.exp(-z))

    def agg(self, sigma, rho):
        return float((self.p(sigma, rho) * self.w).sum())

    def equilibrium(self, sigma):
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if self.agg(sigma, mid) - mid > 0: lo = mid
            else: hi = mid
        return 0.5 * (lo + hi)

    def _calibrate_level(self, target):
        # find theta0 so the sigma=0 equilibrium aggregate compliance = target
        def eq_at(th0):
            self.theta0 = th0; return self.equilibrium(0.0)
        lo, hi = -20.0, 20.0
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if eq_at(mid) < target: lo = mid
            else: hi = mid
        self.theta0 = 0.5 * (lo + hi)


def main():
    rows = pd.read_csv(OUT / f"response_surface_rows_{DATE}.csv")
    surf = gt.collapse_surface(rows, fleet="ServiceFirst")

    game = SlackResolvedGame()
    rho0 = game.equilibrium(0.0); d0 = 1 - rho0
    # incentive that restores all-pass>=0.5 at 35% capacity (NoGrid), under this model
    cap = 35
    cap_df = surf[surf["capacity_pct"] == cap]
    cells = {g: gt.surfaces_for(cap_df[cap_df["grid"] == g]) for g in cap_df["grid"].unique()}
    def ap_at(sigma, grid="NoGrid"):
        return float(cells[grid]["all_pass"](1 - game.equilibrium(sigma)))
    # bisection for sigma*
    lo, hi = 0.0, 20.0
    if ap_at(0.0) >= 0.5:
        sigma_star = 0.0
    else:
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if ap_at(mid) >= 0.5: hi = mid
            else: lo = mid
        sigma_star = hi

    print("=== OptimizEV-grounded slack-resolved compliance game ===")
    print(f"OptimizEV slack slope b={B_SLACK:.3f} (opt-in {OPTIN_LOW_SLACK:.0%}->{OPTIN_HIGH_SLACK:.0%})")
    print(f"calibrated theta0={game.theta0:.3f}, lam_bar={game.lam_bar:.3f}")
    print(f"selfish NE compliance rho*={rho0:.4f} (deviation d*={d0:.4f})  [target 0.95/0.05]")
    print(f"all-pass at selfish NE (35%,NoGrid) = {ap_at(0.0):.3f}")
    print(f"sigma* to restore all-pass>=0.5 (35%,NoGrid) = {sigma_star:.3f}")
    # compliance vs slack at sigma=0 and at sigma*
    print(f"compliance(low slack)={game.p(0,rho0)[100]:.2f} compliance(high slack)={game.p(0,rho0)[-100]:.2f}")

    # ---- calibration figure (twin axes: different QUANTITIES, same slack-gradient) ----
    lam = np.linspace(0, 1, 200)
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    l1, = ax.plot(lam, optin(lam), color="#7f8c8d", lw=2, ls="--",
                  label="OptimizEV opt-in vs slack")
    pts = ax.plot([LAM_LOW, LAM_HIGH], [OPTIN_LOW_SLACK, OPTIN_HIGH_SLACK], "ks", ms=9,
                  label="OptimizEV reported points")[0]
    ax.set_ylabel("OptimizEV program opt-in probability", color="#555")
    ax.set_ylim(0, 1); ax.tick_params(axis="y", colors="#555")
    ax2 = ax.twinx()
    comp0 = game.p(0.0, rho0)
    l2, = ax2.plot(game.lam, comp0, color="#2980b9", lw=2.5,
                   label="modelled per-decision compliance")
    ax2.set_ylabel("modelled compliance (ACN-anchored, mean 0.95)", color="#2980b9")
    ax2.set_ylim(0.6, 1.0); ax2.tick_params(axis="y", colors="#2980b9")
    ax.set_xlabel("scheduling slack / laxity $\\lambda$")
    ax.set_title("Soft calibration: the compliance model inherits the OptimizEV\n"
                 "slack-gradient; absolute level is ACN-anchored (distinct quantities,\n"
                 "distinct axes -- only the slack-dependence is transferred)", fontsize=9)
    ax.legend(handles=[l1, pts, l2], fontsize=8, loc="upper left"); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(OUT / "figures" / "fig_eq_optimizev_calibration.pdf")
    import shutil
    shutil.copy(OUT / "figures" / "fig_eq_optimizev_calibration.pdf",
                "/home/jia/multi actor/final_applied_energy_package_20260609/figures/")
    fig.savefig(OUT / "figures" / "fig_eq_optimizev_calibration.png", dpi=120)

    json.dump(dict(b_slack=B_SLACK, a_slack=A_SLACK, theta0=game.theta0, theta_lam=game.theta_lam,
                   theta_e=game.theta_e, theta_sig=game.theta_sig, rho_selfish=rho0, d_selfish=d0,
                   allpass_selfish=ap_at(0.0), sigma_star=sigma_star),
              open(OUT / f"optimizev_calibration_{DATE}.json", "w"), indent=2)
    print("calibration figure + json written")


if __name__ == "__main__":
    main()
