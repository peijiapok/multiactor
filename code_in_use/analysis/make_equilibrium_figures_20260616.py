#!/usr/bin/env python3
"""Figures for the multi-actor equilibrium analysis. Reads the surface CSV + results
JSON produced by gametheory_equilibrium_20260616.py and rebuilds the game objects to
draw self-explanatory figures:

  FIG A  best-response map Phi(rho) with 45-deg line + unique fixed point, sigma=0 vs
         sigma* -> "the collapse is a Nash equilibrium; the incentive shifts it".
  FIG B  all-pass vs incentive sigma, NoGrid vs PeakPenalty, per capacity, with the
         acceptability threshold + selfish-NE start -> "the mechanism restores all-pass;
         both levers needed at high capacity".
  FIG C  three-actor utility triangle at selfish-NE vs Nash-bargaining vs implemented.
  FIG D  Price of Anarchy and minimum incentive sigma* vs capacity.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path("/home/jia/multi actor/equilibrium_optimization_20260616")
FIGDIR = OUT / "figures"
DATE = "20260616"
TAG = "real"

_spec = importlib.util.spec_from_file_location("gt", OUT / f"gametheory_equilibrium_{DATE}.py")
gt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gt)


def load():
    surf = pd.read_csv(OUT / f"equilibrium_surface_{TAG}_{DATE}.csv")
    results = json.loads((OUT / f"equilibrium_results_{TAG}_{DATE}.json").read_text())
    return surf, {int(r["capacity"]): r for r in results}


def cells_for(surf, cap):
    cap_df = surf[surf["capacity_pct"] == cap]
    return {g: gt.surfaces_for(cap_df[cap_df["grid"] == g]) for g in cap_df["grid"].unique()}


def fig_bestresponse(surf, results, cap=35):
    r = results[cap]
    game = gt.calibrate_driver_game(rho0_target=r["selfish"]["rho"] if False else 0.95,
                                    beta=r["game"]["beta"])
    game.mu, game.s = r["game"]["mu"], r["game"]["s"]
    sig_star = r["stackelberg"]["NoGrid"]["sigma"] or 0.0
    lo = 0.85
    rho = np.linspace(lo, 1.0, 400)
    fig, ax = plt.subplots(figsize=(5.4, 4.8))
    ax.plot(rho, rho, "k--", lw=1, label=r"$45^\circ$: fixed-point line $\Phi(\rho)=\rho$")
    for sigma, col, lab in [(0.0, "#c0392b", r"no incentive ($\sigma=0$)"),
                            (sig_star, "#27ae60", rf"Pigouvian incentive ($\sigma^*={sig_star:.2f}$)")]:
        ax.plot(rho, game.Phi(rho, sigma), color=col, lw=2.2,
                label=r"best response $\Phi(\rho)$: " + lab)
        rstar, _ = game.equilibrium(sigma)
        ax.plot([rstar], [rstar], "o", color=col, ms=10, zorder=5)
        ax.annotate(rf"$\rho^*={rstar:.3f}$" + "\n" + rf"$d^*={1-rstar:.3f}$",
                    (rstar, rstar), textcoords="offset points", xytext=(-78, 6),
                    color=col, fontsize=9, fontweight="bold")
    ax.set_xlabel(r"aggregate compliance $\rho$")
    ax.set_ylabel(r"best-response compliance $\Phi(\rho)$")
    ax.set_title(f"Driver compliance is a congestion game (capacity {cap}%)\n"
                 "unique stable Nash equilibrium; the incentive shifts it toward full compliance",
                 fontsize=10)
    ax.legend(fontsize=8, loc="lower left")
    ax.set_xlim(lo, 1.0); ax.set_ylim(lo, 1.0)
    ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIGDIR / "fig_eq_bestresponse.pdf"); plt.close(fig)


def fig_allpass_vs_incentive(surf, results):
    caps = sorted(results)
    fig, axes = plt.subplots(1, len(caps), figsize=(4.2 * len(caps), 4.2), sharey=True)
    if len(caps) == 1:
        axes = [axes]
    sig = np.linspace(0, 6, 120)
    for ax, cap in zip(axes, caps):
        cells = cells_for(surf, cap)
        game = gt.calibrate_driver_game(beta=results[cap]["game"]["beta"])
        game.mu, game.s = results[cap]["game"]["mu"], results[cap]["game"]["s"]
        for grid, col in [("NoGrid", "#2c7fb8"), ("PeakPenalty", "#d95f0e")]:
            if grid not in cells:
                continue
            ap = []
            for s in sig:
                rstar, _ = game.equilibrium(s)
                ap.append(float(cells[grid]["all_pass"](1 - rstar)))
            ax.plot(sig, ap, color=col, lw=2, label=grid)
        ax.axhline(0.5, color="gray", ls=":", lw=1)
        ap0 = float(cells["NoGrid"]["all_pass"](1 - results[cap]["selfish"]["rho"]))
        ax.plot([0], [ap0], "rv", ms=9)
        ax.annotate("selfish NE\n(no incentive)", (0, ap0), textcoords="offset points",
                    xytext=(8, 6), fontsize=8, color="r")
        ax.set_title(f"capacity {cap}%")
        ax.set_xlabel("compliance incentive $\\sigma$")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("all-pass acceptability")
    axes[0].legend(fontsize=9, title="grid lever")
    fig.suptitle("A bounded compliance incentive restores all-pass acceptability at every "
                 "capacity;\nthe grid policy modulates the incentive required (capacity-dependent)",
                 fontsize=11)
    fig.tight_layout(); fig.savefig(FIGDIR / "fig_eq_allpass_vs_incentive.pdf"); plt.close(fig)


def fig_utility_triangle(surf, results, cap=35):
    r = results[cap]
    s = r["selfish"]; nb = r["nbs"]
    cells = cells_for(surf, cap)
    # implemented Stackelberg point (best grid by lowest sigma achieving target)
    grid_imp = min(r["stackelberg"], key=lambda g: (r["stackelberg"][g]["sigma"] is None,
                                                    r["stackelberg"][g]["sigma"] or 1e9))
    d_imp = r["stackelberg"][grid_imp]["d_star"]
    imp = {k: float(cells[grid_imp][f"U_{k}"](d_imp)) for k in ["D", "F", "G"]}
    labels = ["Driver\n$U_D$", "Fleet\n$U_F$", "Grid\n$U_G$"]
    ang = np.linspace(0, 2 * np.pi, 4)[:3] + np.pi / 2
    fig, ax = plt.subplots(figsize=(5.2, 5.0), subplot_kw=dict(polar=True))
    for pt, col, lab in [((s["U_D"], s["U_F"], s["U_G"]), "#c0392b",
                          f"selfish NE (all-pass {s['all_pass']:.2f})"),
                         ((imp["D"], imp["F"], imp["G"]), "#27ae60",
                          f"implemented $\\sigma^*$ ({grid_imp})"),
                         ((nb["U_D"], nb["U_F"], nb["U_G"]), "#2980b9",
                          f"Nash bargaining (target)")]:
        v = list(pt) + [pt[0]]
        a = list(ang) + [ang[0]]
        ax.plot(a, v, "o-", color=col, lw=2, label=lab)
        ax.fill(a, v, color=col, alpha=0.08)
    ax.set_xticks(ang); ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 1)
    ax.set_title(f"Three-actor utilities (capacity {cap}%)\nmechanism moves all three "
                 f"toward the bargaining target", fontsize=10, pad=18)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.32), fontsize=8)
    fig.tight_layout(); fig.savefig(FIGDIR / "fig_eq_utility_triangle.pdf"); plt.close(fig)


def fig_poa(surf, results):
    caps = sorted(results)
    poa = [results[c]["price_of_anarchy"] for c in caps]
    sig_ng = [results[c]["stackelberg"]["NoGrid"]["sigma"] for c in caps]
    sig_pp = [results[c]["stackelberg"]["PeakPenalty"]["sigma"] for c in caps]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4))
    a1.bar([str(c) for c in caps], poa, color="#8e44ad")
    a1.axhline(1, color="k", ls="--", lw=1)
    a1.set_ylabel("Price of Anarchy  $W_{NBS}/W_{selfish}$")
    a1.set_xlabel("capacity %"); a1.set_title("value of coordination")
    x = np.arange(len(caps)); w = 0.38
    a2.bar(x - w / 2, [v if v is not None else np.nan for v in sig_ng], w, label="NoGrid", color="#2c7fb8")
    a2.bar(x + w / 2, [v if v is not None else np.nan for v in sig_pp], w, label="PeakPenalty", color="#d95f0e")
    for i, v in enumerate(sig_ng):
        if v is None:
            a2.text(i - w / 2, 0.05, "n/a\n(grid-limited)", ha="center", fontsize=7, color="#2c7fb8")
    a2.set_xticks(x); a2.set_xticklabels([str(c) for c in caps])
    a2.set_ylabel("minimum incentive $\\sigma^*$ to restore all-pass")
    a2.set_xlabel("capacity %"); a2.set_title("incentive cost of implementation")
    a2.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIGDIR / "fig_eq_poa.pdf"); plt.close(fig)


def main():
    FIGDIR.mkdir(parents=True, exist_ok=True)
    surf, results = load()
    fig_bestresponse(surf, results)
    fig_allpass_vs_incentive(surf, results)
    fig_utility_triangle(surf, results)
    fig_poa(surf, results)
    print(f"Figures written to {FIGDIR}")


if __name__ == "__main__":
    main()
