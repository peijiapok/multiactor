#!/usr/bin/env python3
"""Graphical abstract: the diagnostic -> mechanism arc.
Left  (PROBLEM): all-pass acceptability collapses at the selfish Nash equilibrium.
Right (SOLUTION): a Stackelberg compliance incentive restores joint acceptability and
lifts all three actors toward the Nash bargaining optimum.
"""
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path("/home/jia/multi actor/equilibrium_optimization_20260616")
DATE = "20260616"
_spec = importlib.util.spec_from_file_location("gt", OUT / f"gametheory_equilibrium_{DATE}.py")
gt = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(gt)

surf = pd.read_csv(OUT / f"equilibrium_surface_real_{DATE}.csv")
results = {int(r["capacity"]): r for r in json.loads((OUT / f"equilibrium_results_real_{DATE}.json").read_text())}
cap = 35
r = results[cap]
cap_df = surf[surf["capacity_pct"] == cap]
cells = {g: gt.surfaces_for(cap_df[cap_df["grid"] == g]) for g in cap_df["grid"].unique()}
game = gt.calibrate_driver_game(beta=r["game"]["beta"]); game.mu, game.s = r["game"]["mu"], r["game"]["s"]

fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 4.3))

# LEFT: all-pass vs deviation (raw), collapse at selfish NE d*=0.05
d = cells["NoGrid"]["d_grid"]
ap = [float(cells["NoGrid"]["all_pass"](x)) for x in d]
axL.plot(d, ap, "-o", color="#c0392b", lw=2.5, ms=5)
axL.axvline(0.05, color="k", ls="--", lw=1)
axL.annotate("selfish Nash equilibrium\n$d^*=5\\%$  $\\Rightarrow$  all-pass $=0$",
             (0.05, 0.0), xytext=(0.13, 0.45), fontsize=10,
             arrowprops=dict(arrowstyle="->", color="k"))
axL.set_xlabel("driver deviation $d$"); axL.set_ylabel("all-pass acceptability")
axL.set_title("PROBLEM: uncoordinated behavior\ncollapses joint acceptability", fontsize=11, color="#c0392b")
axL.set_xlim(0, 0.35); axL.set_ylim(-0.03, 1.05); axL.grid(alpha=0.3)

# RIGHT: all-pass vs incentive, restored
sig = np.linspace(0, 4, 120)
for grid, col in [("NoGrid", "#2c7fb8"), ("PeakPenalty", "#d95f0e")]:
    if grid in cells:
        y = [float(cells[grid]["all_pass"](1 - game.equilibrium(s)[0])) for s in sig]
        axR.plot(sig, y, color=col, lw=2.5, label=grid)
axR.plot([0], [0], "rv", ms=11)
sstar = r["stackelberg"]["NoGrid"]["sigma"]
axR.annotate(f"Pigouvian incentive $\\sigma^*\\approx{sstar:.2f}$\nrestores all-pass",
             (sstar, 0.5), xytext=(1.4, 0.35), fontsize=10,
             arrowprops=dict(arrowstyle="->", color="#27ae60"))
axR.set_xlabel("compliance incentive $\\sigma$ (Stackelberg leader)")
axR.set_ylabel("all-pass acceptability")
axR.set_title("SOLUTION: a bounded incentive implements\nthe Nash bargaining optimum (PoA $\\approx1.5$)",
              fontsize=11, color="#27ae60")
axR.legend(fontsize=9, title="grid lever", loc="lower right"); axR.grid(alpha=0.3)
axR.set_xlim(0, 4); axR.set_ylim(-0.03, 1.05)

fig.suptitle("Multi-actor EV charging: from a behavioral equilibrium collapse to a "
             "mechanism that restores driver, fleet & grid acceptability", fontsize=12, y=1.02)
fig.tight_layout()
fig.savefig(OUT / "figures" / "graphical_abstract_equilibrium.pdf", bbox_inches="tight")
fig.savefig(OUT / "figures" / "graphical_abstract_equilibrium.png", dpi=130, bbox_inches="tight")
print("graphical abstract written")
