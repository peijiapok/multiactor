#!/usr/bin/env python3
"""Multi-actor EV-charging EQUILIBRIUM analysis (game theory on the response surface).

Reads the simulator response surface (run_response_surface_20260616.py) and runs,
per capacity and grid policy:

  (1) UTILITIES  U_D, U_F, U_G in [0,1] from continuous gate metrics.
  (2) DRIVER NASH EQUILIBRIUM of an aggregative congestion game:
        a driver complies iff  sigma + beta*S(rho) >= kappa_i ;
        compliance fraction is the fixed point  rho* = Phi(rho*; sigma)
        with Phi(rho) = F_kappa(sigma + beta*S(rho)),  S(rho)=service quality.
      Solved by damped iteration; existence (Brouwer) + uniqueness (|Phi'|<1) checked.
      sigma=0 reproduces the ACN-anchored selfish collapse (d*=1-rho*~0.05).
  (3) STACKELBERG mechanism: smallest incentive sigma* (per capacity, grid) whose
      induced driver equilibrium restores all-pass acceptability. Monotone -> bisection.
  (4) NASH BARGAINING SOLUTION: operating point maximizing prod_k (U_k - d_k),
      disagreement d_k = selfish-NE utilities. The cooperative "optimize all three" target.
  (5) PRICE OF ANARCHY  PoA = W(social/NBS) / W(selfish NE),  W = sum_k w_k U_k.

Run with --selftest to validate the solvers on a synthetic monotone surface before
the real CSV exists; run with no args once response_surface_rows_*.csv is present.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("/home/jia/multi actor/equilibrium_optimization_20260616")
DATE = "20260616"
RS_CSV = OUT / f"response_surface_rows_{DATE}.csv"

GRIDS = ["NoGrid", "PeakPenalty"]
WELFARE_W = dict(D=1 / 3, F=1 / 3, G=1 / 3)   # welfare weights (reported w/ sensitivity)

# ----------------------------------------------------------------------------- #
# Utilities from gate metrics
# ----------------------------------------------------------------------------- #
def _minmax(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    lo, hi = np.nanmin(x), np.nanmax(x)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi - lo < 1e-12:
        return np.full_like(x, 0.5)
    return (x - lo) / (hi - lo)


def build_utilities(surf: pd.DataFrame) -> pd.DataFrame:
    """Add U_D, U_F, U_G in [0,1]. Normalization is per-capacity (min-max over the
    deviation grid), so utilities are comparable within a capacity for NBS/PoA."""
    surf = surf.copy()
    for col in ["U_D", "U_F", "U_G"]:
        surf[col] = np.nan
    for cap, g in surf.groupby("capacity_pct"):
        idx = g.index
        # Driver: service reliability + delivered-energy ratio (higher better)
        rel = g["reliability_pct"].to_numpy() / 100.0
        dele = np.clip(g["delivered_ratio_vs_ll"].to_numpy(), 0.0, 1.5)
        U_D = 0.5 * np.clip(rel, 0, 1) + 0.5 * _minmax(dele)
        # Fleet: critical-service completion (higher better) + low wait (lower better)
        served = g["critical_request_served_count"].to_numpy()
        crit = np.clip(g["critical_request_count"].to_numpy(), 1, None)
        compl = np.clip(served / crit, 0, 1)
        wait = g["p95_wait_minutes"].to_numpy()
        U_F = 0.5 * compl + 0.5 * (1.0 - _minmax(wait))
        # Grid: low load-shape stress (squared-load, ramp, peak-to-average; lower better)
        sql = g["squared_load_proxy_ratio_vs_anchor"].to_numpy()
        ramp = g["ramp_p95_ratio_vs_anchor"].to_numpy()
        pav = g["peak_to_average_ratio"].to_numpy()
        stress = (_minmax(sql) + _minmax(ramp) + _minmax(pav)) / 3.0
        U_G = 1.0 - stress
        surf.loc[idx, "U_D"] = U_D
        surf.loc[idx, "U_F"] = U_F
        surf.loc[idx, "U_G"] = U_G
    return surf


def collapse_surface(rows: pd.DataFrame, fleet: str = "ServiceFirst") -> pd.DataFrame:
    """Mean over seeds -> one row per (capacity, grid, dev). Adds grid label & U_*."""
    df = rows.copy()
    df["grid"] = df["policy"].map(lambda p: "PeakPenalty" if "PeakPenalty" in str(p) else "NoGrid")
    df["fleet"] = df["policy"].map(lambda p: "ServiceGridWeighted" if "ServiceGridWeighted" in str(p) else "ServiceFirst")
    df = df[df["fleet"] == fleet].copy()
    df = df.rename(columns={"driver_service_pass": "driver_pass",
                            "fleet_operation_pass": "fleet_pass"})
    keep = ["reliability_pct", "delivered_ratio_vs_ll", "critical_request_served_count",
            "critical_request_count", "p95_wait_minutes",
            "squared_load_proxy_ratio_vs_anchor", "ramp_p95_ratio_vs_anchor",
            "peak_to_average_ratio", "all_pass", "driver_pass", "fleet_pass", "grid_pass"]
    g = (df.groupby(["capacity_pct", "grid", "dev_realized"])[keep]
           .mean().reset_index().sort_values(["capacity_pct", "grid", "dev_realized"]))
    return build_utilities(g)


# ----------------------------------------------------------------------------- #
# Interpolators over deviation d
# ----------------------------------------------------------------------------- #
class Surf1D:
    """Monotone-friendly 1-D interpolation of a quantity over deviation d in [0,1]."""
    def __init__(self, d, y):
        order = np.argsort(d)
        self.d = np.asarray(d, float)[order]
        self.y = np.asarray(y, float)[order]

    def __call__(self, d):
        return np.interp(np.clip(d, self.d[0], self.d[-1]), self.d, self.y)


def surfaces_for(cell: pd.DataFrame) -> dict:
    d = cell["dev_realized"].to_numpy()
    return {
        "U_D": Surf1D(d, cell["U_D"]), "U_F": Surf1D(d, cell["U_F"]),
        "U_G": Surf1D(d, cell["U_G"]), "all_pass": Surf1D(d, cell["all_pass"]),
        "driver_pass": Surf1D(d, cell["driver_pass"]),
        "fleet_pass": Surf1D(d, cell["fleet_pass"]),
        "grid_pass": Surf1D(d, cell["grid_pass"]),
        "d_grid": d,
    }


# ----------------------------------------------------------------------------- #
# (2) Driver aggregative-game Nash equilibrium
# ----------------------------------------------------------------------------- #
class DriverGame:
    """Aggregative CONGESTION / free-riding public-good game in driver compliance.

    A coordinated charging schedule (drivers deferring/complying) produces a public
    good: an uncongested queue and a healthy grid load shape. The marginal private
    benefit of complying DECREASES as more others comply, because a healthy system
    can absorb one defection -> each driver is tempted to free-ride (charge now /
    reserve-seek). Driver i complies iff
        sigma + beta * (1 - rho)  >=  kappa_i,
    where rho = aggregate compliance, (1-rho) = congestion/scarcity that makes
    complying privately worthwhile, kappa_i ~ Logistic(mu, s) is the heterogeneous
    private compliance cost (higher for low-slack drivers), and sigma is the
    operator's compliance incentive. The compliance fraction is the fixed point
        rho = Phi(rho; sigma) = F_kappa( sigma + beta*(1-rho) ).
    Phi is DECREASING in rho -> a UNIQUE interior Nash equilibrium (stable). The
    incentive sigma is Pigouvian: it internalizes the deviation externality and
    raises the equilibrium compliance toward the social optimum.
    """
    def __init__(self, beta: float, mu: float, s: float):
        self.beta = beta
        self.mu = mu
        self.s = s

    def F_kappa(self, x):        # logistic CDF P(kappa <= x)
        return 1.0 / (1.0 + np.exp(-(x - self.mu) / self.s))

    def Phi(self, rho, sigma):
        return self.F_kappa(sigma + self.beta * (1.0 - rho))

    def equilibrium(self, sigma):
        """Unique fixed point via bisection on g(rho)=Phi(rho)-rho (strictly
        decreasing in rho), with a stability/uniqueness slope diagnostic."""
        def g(r):
            return self.Phi(r, sigma) - r
        lo, hi = 0.0, 1.0
        glo, ghi = g(lo), g(hi)
        if glo <= 0:            # equilibrium at 0
            rho = 0.0
        elif ghi >= 0:          # equilibrium at 1
            rho = 1.0
        else:
            for _ in range(100):
                mid = 0.5 * (lo + hi)
                if g(mid) > 0:
                    lo = mid
                else:
                    hi = mid
            rho = 0.5 * (lo + hi)
        h = 1e-5
        slope = (self.Phi(min(rho + h, 1.0), sigma) - self.Phi(max(rho - h, 0.0), sigma)) / (2 * h)
        return float(np.clip(rho, 0, 1)), float(slope)

    def all_equilibria(self, sigma, n=4001):
        rg = np.linspace(0, 1, n)
        gg = self.Phi(rg, sigma) - rg
        sign = np.sign(gg)
        return max(int(np.sum(sign[:-1] * sign[1:] < 0)), 1)


def calibrate_driver_game(rho0_target=0.95, beta=2.0, s=0.4):
    """Pick mu so the sigma=0 equilibrium compliance equals rho0_target (ACN anchor:
    ~5% deviation). beta = externality strength, s = cost-heterogeneity scale (sets
    incentive responsiveness drho*/dsigma). Phi decreasing -> unique equilibrium.
        rho0 = F_kappa(beta*(1-rho0))  =>  logit(rho0) = (beta*(1-rho0) - mu)/s
    """
    logit = np.log(rho0_target / (1 - rho0_target))
    mu = beta * (1.0 - rho0_target) - s * logit
    return DriverGame(beta=beta, mu=mu, s=s)


# ----------------------------------------------------------------------------- #
# (3) Stackelberg incentive design  &  (4) NBS  &  (5) PoA
# ----------------------------------------------------------------------------- #
def stackelberg_min_sigma(game: DriverGame, allpass_of_d: Surf1D, target=0.5,
                          smax=20.0):
    """Smallest sigma whose induced equilibrium gives all_pass(d*(sigma)) >= target.
    d*(sigma) is monotone decreasing in sigma -> bisection on sigma."""
    def ap(sigma):
        rho, _ = game.equilibrium(sigma)
        return float(allpass_of_d(1.0 - rho)), 1.0 - rho
    ap0, d0 = ap(0.0)
    aphi, dhi = ap(smax)
    if ap0 >= target:
        return 0.0, d0, ap0          # already acceptable with no incentive
    if aphi < target:
        return None, dhi, aphi       # not implementable by incentive alone (grid-limited)
    lo, hi = 0.0, smax
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        apm, dm = ap(mid)
        if apm >= target:
            hi = mid
        else:
            lo = mid
    apf, df = ap(hi)
    return hi, df, apf


def nash_bargaining(cells: dict, disagreement: dict, w=WELFARE_W, n=400):
    """Maximize prod_k (U_k - d_k)_+ over the achievable set: every deviation level
    on a fine grid, across both grid policies. Returns the argmax operating point."""
    best = None
    for grid in cells:
        S = cells[grid]
        dg = np.linspace(S["d_grid"][0], S["d_grid"][-1], n)
        for d in dg:
            uD, uF, uG = float(S["U_D"](d)), float(S["U_F"](d)), float(S["U_G"](d))
            gains = [max(uD - disagreement["U_D"], 0.0),
                     max(uF - disagreement["U_F"], 0.0),
                     max(uG - disagreement["U_G"], 0.0)]
            nash = (gains[0] + 1e-9) * (gains[1] + 1e-9) * (gains[2] + 1e-9)
            W = w["D"] * uD + w["F"] * uF + w["G"] * uG
            rec = dict(grid=grid, d=float(d), U_D=uD, U_F=uF, U_G=uG, nash=nash, W=W,
                       all_pass=float(S["all_pass"](d)))
            if best is None or nash > best["nash"]:
                best = rec
    return best


def analyze_capacity(cap, cells_raw, fleet_label, rho0=0.95, beta=1.0, target=0.5):
    """cells_raw: {grid: DataFrame for this capacity}. Returns a result dict."""
    cells = {grid: surfaces_for(cells_raw[grid]) for grid in cells_raw}
    base_grid = "NoGrid" if "NoGrid" in cells else list(cells)[0]
    game = calibrate_driver_game(rho0_target=rho0, beta=beta)

    rho_sel, slope_sel = game.equilibrium(0.0)
    d_sel = 1.0 - rho_sel
    n_eq = game.all_equilibria(0.0)
    disagreement = dict(U_D=float(cells[base_grid]["U_D"](d_sel)),
                        U_F=float(cells[base_grid]["U_F"](d_sel)),
                        U_G=float(cells[base_grid]["U_G"](d_sel)))
    W_sel = sum(WELFARE_W[k[-1]] * disagreement[f"U_{k[-1]}"] for k in ["U_D", "U_F", "U_G"])
    ap_sel = float(cells[base_grid]["all_pass"](d_sel))

    # Stackelberg per grid policy
    stack = {}
    for grid in cells:
        sigma, d_star, ap = stackelberg_min_sigma(game, cells[grid]["all_pass"], target=target)
        stack[grid] = dict(sigma=sigma, d_star=d_star, all_pass=ap)

    nbs = nash_bargaining(cells, disagreement)
    poa = (nbs["W"] / W_sel) if W_sel > 1e-9 else float("inf")

    return dict(
        capacity=cap, fleet=fleet_label,
        selfish=dict(rho=rho_sel, d=d_sel, slope=slope_sel, n_equilibria=n_eq,
                     all_pass=ap_sel, W=W_sel, **disagreement),
        stackelberg=stack, nbs=nbs, price_of_anarchy=poa,
        game=dict(beta=game.beta, mu=game.mu, s=game.s),
    )


# ----------------------------------------------------------------------------- #
# Self-test on a synthetic monotone surface
# ----------------------------------------------------------------------------- #
def synthetic_surface():
    d = np.array([0.0, 0.0125, 0.025, 0.0375, 0.05, 0.075, 0.10, 0.15, 0.22, 0.32, 0.45])
    rows = []
    for cap in (20, 35, 50):
        for grid in GRIDS:
            peak_relief = 0.12 if grid == "PeakPenalty" else 0.0
            for dd in d:
                rel = 100 * (1 - 1.9 * dd)                       # driver service falls with d
                deliv = 1.0 - 1.2 * dd
                served = 100 * (1 - 1.6 * dd)
                critc = 100.0
                wait = 5 + 120 * dd
                # grid stress rises with d AND with capacity; PeakPenalty relieves
                sql = 1.0 + (2.5 * dd + 0.004 * cap) * (1 - peak_relief)
                ramp = 1.0 + (1.8 * dd + 0.003 * cap) * (1 - peak_relief)
                pav = 1.5 + 2.0 * dd
                # all-pass: collapses with d, capacity-limited even at d=0 for high cap
                base = 1.0 - 0.02 * (cap - 20) / 30
                ap = base * np.exp(-((dd / 0.02) ** 1.1)) + (0.1 if grid == "PeakPenalty" else 0)
                ap = float(np.clip(ap, 0, 1))
                rows.append(dict(capacity_pct=cap, policy=f"D_x__F_ServiceFirst__G_{grid}",
                                 dev_realized=dd, reliability_pct=rel,
                                 delivered_ratio_vs_ll=deliv,
                                 critical_request_served_count=served,
                                 critical_request_count=critc, p95_wait_minutes=wait,
                                 squared_load_proxy_ratio_vs_anchor=sql,
                                 ramp_p95_ratio_vs_anchor=ramp,
                                 peak_to_average_ratio=pav, all_pass=ap,
                                 driver_pass=float(dd < 0.03), fleet_pass=float(dd < 0.08),
                                 grid_pass=float(sql < 1.0 + 0.004 * cap + 0.05)))
    return pd.DataFrame(rows)


def run(rows: pd.DataFrame, tag: str, fleet="ServiceFirst"):
    surf = collapse_surface(rows, fleet=fleet)
    results = []
    for cap in sorted(surf["capacity_pct"].unique()):
        cap_df = surf[surf["capacity_pct"] == cap]
        cells_raw = {grid: cap_df[cap_df["grid"] == grid] for grid in cap_df["grid"].unique()}
        results.append(analyze_capacity(int(cap), cells_raw, fleet))

    print(f"\n================ EQUILIBRIUM RESULTS [{tag}, fleet={fleet}] ================")
    for r in results:
        s = r["selfish"]
        print(f"\n--- capacity {r['capacity']}% ---")
        print(f"  SELFISH NASH EQ: compliance rho*={s['rho']:.3f} (deviation d*={s['d']:.3f}), "
              f"|Phi'|={s['slope']:.3f} ({'unique/stable' if abs(s['slope'])<1 else 'CHECK'}), "
              f"#equilibria={s['n_equilibria']}")
        print(f"     utilities U_D={s['U_D']:.3f} U_F={s['U_F']:.3f} U_G={s['U_G']:.3f}  "
              f"all_pass={s['all_pass']:.3f}  welfare W={s['W']:.3f}")
        for grid, st in r["stackelberg"].items():
            if st["sigma"] is None:
                print(f"  STACKELBERG [{grid}]: incentive alone CANNOT restore all-pass "
                      f"(max all_pass={st['all_pass']:.3f} at d*={st['d_star']:.3f}) -> grid-limited")
            else:
                print(f"  STACKELBERG [{grid}]: sigma*={st['sigma']:.3f} -> d*={st['d_star']:.3f}, "
                      f"all_pass={st['all_pass']:.3f}")
        nb = r["nbs"]
        print(f"  NASH BARGAINING: grid={nb['grid']} d={nb['d']:.3f}  "
              f"U=({nb['U_D']:.3f},{nb['U_F']:.3f},{nb['U_G']:.3f}) all_pass={nb['all_pass']:.3f} W={nb['W']:.3f}")
        print(f"  PRICE OF ANARCHY W(NBS)/W(selfish) = {r['price_of_anarchy']:.3f}")

    out = OUT / f"equilibrium_results_{tag}_{DATE}.json"
    out.write_text(json.dumps(results, indent=2, default=float))
    surf.to_csv(OUT / f"equilibrium_surface_{tag}_{DATE}.csv", index=False)
    print(f"\nSaved {out}")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        run(synthetic_surface(), tag="selftest")
        return
    if not RS_CSV.exists():
        print(f"Response surface not found: {RS_CSV}\nRun run_response_surface first, "
              f"or use --selftest.")
        sys.exit(1)
    rows = pd.read_csv(RS_CSV)
    run(rows, tag="real", fleet="ServiceFirst")
    run(rows, tag="real_sgw", fleet="ServiceGridWeighted")


if __name__ == "__main__":
    main()
