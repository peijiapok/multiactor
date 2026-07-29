#!/usr/bin/env python3
"""Worked-example schematic (Zobel Ch.19 / committee #19): follow ONE car through one
episode and show how a single comply-vs-override choice flips the whole day pass->fail.
Illustrative diagram of the model's mechanism, not a logged trace."""
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

PKG=Path("/home/jia/multi actor/final_applied_energy_package_20260609")
GREEN="#2e7d32"; GREENF="#e8f5e9"; RED="#c62828"; REDF="#fdecea"
GREY="#455a64"; GREYF="#eceff1"; BLUEF="#e3f2fd"; BLUE="#1565c0"

fig,ax=plt.subplots(figsize=(8.2,6.8)); ax.set_xlim(0,10); ax.set_ylim(0,10); ax.axis("off")

def box(x,y,w,h,text,fc,ec,fs=8.5,weight="normal",tc="black"):
    ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle="round,pad=0.03,rounding_size=0.10",
                 fc=fc,ec=ec,lw=1.4))
    ax.text(x,y,text,ha="center",va="center",fontsize=fs,weight=weight,color=tc,wrap=True)

def arrow(x1,y1,x2,y2,color="black",lw=1.6):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=13,color=color,lw=lw))

# ---- shared header ----
box(5,9.5,8.6,0.9,"CAR #17 arrives 8:00 AM  •  battery 25%  •  needs ~80% by 5:00 PM\n"
    "parked 9 h but needs only ~3 h of charging  →  plenty of slack, NOT urgent",BLUEF,BLUE,8.6,"bold")
box(5,8.35,7.4,0.7,"Charging company's plan:  “Wait now, I'll charge you midday\n"
    "when the lot is quiet and the grid is calm (urgent cars go first).”",GREYF,GREY,8.2)
ax.text(5,7.55,"9:00 AM  —  the driver decides:",ha="center",va="center",fontsize=9,weight="bold")
arrow(5,8.0,3.0,7.05); arrow(5,8.0,7.0,7.05)

# ---- LEFT: follows ----
box(3.0,6.7,3.7,0.7,"FOLLOWS the plan",GREENF,GREEN,9.5,"bold",GREEN)
box(3.0,5.75,3.7,0.7,"waits  •  charges midday\nleaves at 82% full",GREENF,GREEN,8.4)
for i,(lab) in enumerate(["Driver ✓","Company ✓","Grid ✓"]):
    box(1.75+i*1.25,4.75,1.15,0.55,lab,GREENF,GREEN,8.0,"bold",GREEN)
arrow(3.0,5.4,3.0,5.05)
box(3.0,3.85,3.3,0.7,"ALL THREE HAPPY\nDAY PASSES ✓",GREEN,GREEN,9.5,"bold","white")

# ---- RIGHT: overrides ----
box(7.0,6.7,3.7,0.7,"IGNORES plan — grabs a\ncharger now, out of turn",REDF,RED,9.0,"bold",RED)
casc=["bumps urgent Car #4  →  #4 misses its noon trip",
      "everyone charges at once  →  grid peak spikes",
      "out-of-turn requests  →  queue jams, long waits"]
for i,t in enumerate(casc):
    box(7.0,5.95-i*0.62,3.7,0.5,t,REDF,RED,7.7)
for i,(lab) in enumerate(["Driver ✗","Company ✗","Grid ✗"]):
    box(5.75+i*1.25,3.75,1.15,0.55,lab,REDF,RED,8.0,"bold",RED)
box(7.0,2.75,3.9,0.72,"Car #17 itself leaves fine (85%)\nbut the DAY FAILS ✗",RED,RED,8.8,"bold","white")

# ---- bottom banner ----
box(5,1.35,9.2,1.0,"Only about 1 driver in 20 does this — but with dozens of cars, almost every day gets one.\n"
    "One selfish grab, in one hour, flips the whole day.  That is why “all three happy”\n"
    "crashes from ~97% of days to ~1% of days  —  and why the fix is a small, targeted reward to wait.",
    "#fff8e1","#f9a825",8.6,"bold")
ax.text(5,0.35,"Illustrative trace of the model's mechanism (workplace scenario); one episode = one day.",
        ha="center",va="center",fontsize=7.2,style="italic",color="#666")

fig.tight_layout()
out=PKG/"figures"/"fig_worked_example.pdf"
fig.savefig(out,bbox_inches="tight"); fig.savefig(PKG/"paper_final_result"/"fig_worked_example.png",dpi=150,bbox_inches="tight")
print("wrote",out)
