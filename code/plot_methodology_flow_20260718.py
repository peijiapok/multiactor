#!/usr/bin/env python3
"""Methodology flow figure (replaces fig1_multi_actor_framework): two stages --
(1) the deployability screen and its factorial sweep, (2) the game-theory/incentive layer.
Same visual style as the worked-example schematic."""
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

PKG=Path("/home/jia/multi actor/final_applied_energy_package_20260609")
BLUE="#1565c0"; BLUEF="#e3f2fd"; GREEN="#2e7d32"; GREENF="#e8f5e9"
AMBER="#f9a825"; AMBERF="#fff8e1"; GREY="#455a64"

fig,ax=plt.subplots(figsize=(11.2,7.2)); ax.set_xlim(0,11.2); ax.set_ylim(0,10); ax.axis("off")

def box(x,y,w,h,text,fc,ec,fs=8.0,weight="normal",tc="black"):
    ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle="round,pad=0.03,rounding_size=0.10",fc=fc,ec=ec,lw=1.5))
    ax.text(x,y,text,ha="center",va="center",fontsize=fs,weight=weight,color=tc)
def arr(x1,y1,x2,y2,color=GREY,lw=1.7):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=13,color=color,lw=lw))

ax.text(5.6,9.72,"How the study works: measuring deployability, then the incentive that restores it",
        ha="center",fontsize=12,weight="bold")

xs=[1.25,3.4,5.55,7.7,9.85]; W=1.82; H=1.35
# ---- STAGE 1 band ----
ax.add_patch(FancyBboxPatch((0.2,6.45),10.8,2.55,boxstyle="round,pad=0.02,rounding_size=0.08",
             fc="#f5faff",ec=BLUE,lw=1.0,ls="--"))
ax.text(0.42,8.82,"STAGE 1 — THE SCREEN:  is a charging plan deployable?",fontsize=9,weight="bold",color=BLUE)
s1=["INPUTS\nACN-calibrated demand\ncapacity 20 / 35 / 50%",
    "THREE ACTORS ACT\nGrid: peak signal\nOperator: least-laxity plan\nDriver: follow or override",
    "SIMULATE\none episode\n(168 h)",
    "MEASURE per actor\ndriver  ·  operator\n·  grid",
    "14 GATES (same episode)\ndo all three pass?\n= ALL-PASS  ✓/✗"]
for i,t in enumerate(s1):
    box(xs[i],7.9,W,H,t,BLUEF,BLUE,7.6,"normal")
    if i: arr(xs[i-1]+W/2,7.9,xs[i]-W/2,7.9)
box(5.6,6.75,10.2,0.62,"repeat over every combination:  behavior severity (0 / 5 / 20 / 45%)  ×  capacity  ×  grid  ×  operator policy  ×  seeds   →   ALL-PASS RATE",
    "#eef6ff",BLUE,8.0,"bold",BLUE)

# connector
arr(5.6,6.4,5.6,5.55,BLUE,2.0)
ax.text(5.85,5.95,"the all-pass rate collapses under small non-compliance",fontsize=8,style="italic",color=GREEN)

# ---- STAGE 2 band ----
ax.add_patch(FancyBboxPatch((0.2,1.55),10.8,3.35,boxstyle="round,pad=0.02,rounding_size=0.08",
             fc="#f6fbf6",ec=GREEN,lw=1.0,ls="--"))
ax.text(0.42,4.72,"STAGE 2 — THE MECHANISM:  why it collapses, and the lever that fixes it",fontsize=9,weight="bold",color=GREEN)
s2=[("FINDING\nall-pass collapses\n~97% → ~1%\nat ~5% override",GREENF,GREEN),
    ("GAME MODEL\ndrivers comply only if\nreward ≥ their\nprivate cost",GREENF,GREEN),
    ("SELFISH EQUILIBRIUM\n= the collapse\n(no reason\nto cooperate)",GREENF,GREEN),
    ("INCENTIVE σ\noperator pays\nto comply (Pigouvian,\nStackelberg leader)",AMBERF,AMBER),
    ("FEASIBILITY RESTORED\nequilibrium back in\nthe feasible set\nprice of anarchy ~1.5",GREENF,GREEN)]
for i,(t,fc,ec) in enumerate(s2):
    box(xs[i],3.55,W,1.55,t,fc,ec,7.5,"normal")
    if i: arr(xs[i-1]+W/2,3.55,xs[i]-W/2,3.55, AMBER if i==4 else GREY, 2.0 if i==4 else 1.7)

box(5.6,0.85,10.6,0.85,
    "Stage 1 is the deployability screen (this paper's method); Stage 2 is the game-theory layer that\n"
    "explains the collapse as a selfish equilibrium and identifies the compliance incentive that removes it.",
    "#fbfbf6",GREY,8.2,"normal")

fig.savefig(PKG/"figures"/"fig1_multi_actor_framework.pdf",bbox_inches="tight")
fig.savefig(PKG/"paper_final_result"/"fig1_multi_actor_framework.png",dpi=150,bbox_inches="tight")
print("wrote fig1_multi_actor_framework.pdf")
