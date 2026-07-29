#!/usr/bin/env python3
"""Sensitivity of the equilibrium conclusions to the game's free parameters.

Reviewers will ask whether Price of Anarchy and the implementation incentive depend
on the externality strength beta, the cost-heterogeneity scale s, the anchor rho0,
and the welfare weights. We sweep them on the SAME real response surface and report
the ranges. Robust conclusions: (i) unique stable selfish NE always; (ii) selfish-NE
all-pass ~0; (iii) PoA > 1 (coordination strictly valuable); (iv) a bounded incentive
restores all-pass.
"""
from __future__ import annotations

import importlib.util
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("/home/jia/multi actor/equilibrium_optimization_20260616")
DATE = "20260616"
_spec = importlib.util.spec_from_file_location("gt", OUT / f"gametheory_equilibrium_{DATE}.py")
gt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gt)


def main():
    rows = pd.read_csv(OUT / f"response_surface_rows_{DATE}.csv")
    surf = gt.collapse_surface(rows, fleet="ServiceFirst")

    betas = [1.0, 2.0, 4.0]
    ss = [0.25, 0.40, 0.60]
    rho0s = [0.90, 0.95, 0.97]
    weight_sets = {
        "equal": dict(D=1/3, F=1/3, G=1/3),
        "driver-heavy": dict(D=0.5, F=0.25, G=0.25),
        "grid-heavy": dict(D=0.25, F=0.25, G=0.5),
    }

    recs = []
    for cap in sorted(surf["capacity_pct"].unique()):
        cap_df = surf[surf["capacity_pct"] == cap]
        cells = {g: gt.surfaces_for(cap_df[cap_df["grid"] == g]) for g in cap_df["grid"].unique()}
        base = "NoGrid" if "NoGrid" in cells else list(cells)[0]
        for beta, s, rho0, (wname, w) in itertools.product(betas, ss, rho0s, weight_sets.items()):
            gt.WELFARE_W = w
            game = gt.calibrate_driver_game(rho0_target=rho0, beta=beta, s=s)
            rho_sel, slope = game.equilibrium(0.0)
            d_sel = 1 - rho_sel
            neq = game.all_equilibria(0.0)
            ap_sel = float(cells[base]["all_pass"](d_sel))
            dis = {f"U_{k}": float(cells[base][f"U_{k}"](d_sel)) for k in ["D", "F", "G"]}
            W_sel = sum(w[k] * dis[f"U_{k}"] for k in ["D", "F", "G"])
            nbs = gt.nash_bargaining(cells, dis, w=w)
            sigma, d_star, ap = gt.stackelberg_min_sigma(game, cells[base]["all_pass"], target=0.5)
            recs.append(dict(cap=cap, beta=beta, s=s, rho0=rho0, weights=wname,
                             d_sel=d_sel, slope=slope, n_eq=neq, ap_sel=ap_sel,
                             W_sel=W_sel, W_nbs=nbs["W"], poa=nbs["W"]/W_sel if W_sel>1e-9 else np.nan,
                             sigma_star=sigma if sigma is not None else np.nan))
    df = pd.DataFrame(recs)
    df.to_csv(OUT / f"sensitivity_{DATE}.csv", index=False)

    print("=== SENSITIVITY over beta in {1,2,4}, s in {.25,.4,.6}, rho0 in {.9,.95,.97}, 3 weight sets ===")
    print(f"configs per capacity: {len(df)//df['cap'].nunique()}; capacities: {sorted(df['cap'].unique())}\n")
    print(f"Unique equilibrium in ALL configs: {(df['n_eq']==1).all()}  (n_eq max={df['n_eq'].max()})")
    print(f"Stable (|slope|<1) in ALL configs:  {(df['slope'].abs()<1).all()}  (max|slope|={df['slope'].abs().max():.3f})")
    print(f"Selfish-NE all-pass: max over ALL configs = {df['ap_sel'].max():.3f} (mean {df['ap_sel'].mean():.3f})")
    print(f"Price of Anarchy:    min={df['poa'].min():.3f}  median={df['poa'].median():.3f}  max={df['poa'].max():.3f}")
    print(f"PoA > 1 in ALL configs: {(df['poa']>1).all()}")
    print(f"Implementation incentive sigma*: min={df['sigma_star'].min():.3f} "
          f"median={df['sigma_star'].median():.3f} max={df['sigma_star'].max():.3f} "
          f"(restored all-pass in {df['sigma_star'].notna().mean()*100:.0f}% of configs)")
    print("\nPoA by capacity (median [min,max]):")
    for cap, g in df.groupby("cap"):
        print(f"  cap {cap}%: {g['poa'].median():.3f} [{g['poa'].min():.3f}, {g['poa'].max():.3f}]")
    print(f"\nSaved {OUT / f'sensitivity_{DATE}.csv'}")


if __name__ == "__main__":
    main()
