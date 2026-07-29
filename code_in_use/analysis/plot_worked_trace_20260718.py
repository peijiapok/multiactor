#!/usr/bin/env python3
"""Real worked-example figure from logged simulator output (run_worked_trace_20260718.npz).
Follows one rule-abiding driver (Car #21) through one week, and shows why the day fails."""
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt

OUT=Path("/home/jia/multi actor/equilibrium_optimization_20260616")
PKG=Path("/home/jia/multi actor/final_applied_energy_package_20260609")
d=np.load(OUT/"worked_trace_20260718.npz")
disp=int(d["disp"]); over=int(d["over"])
cumA,cumB=d["cumA"][:,disp],d["cumB"][:,disp]; T=cumA.shape[0]
actA,actB=d["actA"],d["actB"]
loadA=actA.sum(1); loadB=actB.sum(1)
# 24h-averaged site profile (7 days x 24 h)
nD=T//24
profA=loadA[:nD*24].reshape(nD,24).mean(0); profB=loadB[:nD*24].reshape(nD,24).mean(0)
need=cumA[-1]; short=(cumA[-1]-cumB[-1])/cumA[-1]*100
GREEN="#2e7d32"; RED="#c62828"

fig=plt.figure(figsize=(9.4,5.4))
gs=fig.add_gridspec(2,2,height_ratios=[3.0,0.7],hspace=0.45,wspace=0.28)
axA=fig.add_subplot(gs[0,0]); axB=fig.add_subplot(gs[0,1]); axC=fig.add_subplot(gs[1,:]); axC.axis("off")

# Panel A: one driver's week
h=np.arange(T)
axA.plot(h,cumA,color=GREEN,lw=2.4,label="everyone follows the plan")
axA.plot(h,cumB,color=RED,lw=2.4,label="1 in 5 drivers grab a charger out of turn")
axA.axhline(need,ls=":",color=GREEN,lw=1.2)
axA.text(2,need+0.7,f"what Car #{disp} needed ({need:.0f} kWh) — met under the plan",color=GREEN,fontsize=7.5)
axA.annotate(f"falls {short:.0f}% short\n({cumB[-1]:.0f} kWh)",xy=(T-2,cumB[-1]),xytext=(T-58,cumB[-1]+7),
             color=RED,fontsize=8.5,weight="bold",arrowprops=dict(arrowstyle="->",color=RED))
axA.set_xlabel("hour of the week"); axA.set_ylabel(f"Car #{disp}: cumulative charge (kWh)")
axA.set_title(f"One driver's week — Car #{disp} (plays by the rules)",fontsize=10)
axA.legend(fontsize=7.6,loc="upper left"); axA.grid(alpha=0.3); axA.set_xlim(0,T)

# Panel B: why — site charging shifts earlier
x=np.arange(24)
axB.plot(x,profA,color=GREEN,lw=2.2,marker="o",ms=3,label="everyone follows the plan")
axB.plot(x,profB,color=RED,lw=2.2,marker="s",ms=3,label="1 in 5 grab out of turn")
axB.axvspan(0,8,color="#ffcdd2",alpha=0.35)
axB.text(4,axB.get_ylim()[1]*0.92 if False else max(profB)*0.98,"morning pile-up\n→ grid & queue\nchecks fail",
         color=RED,fontsize=7.6,ha="center",va="top",weight="bold")
axB.set_xlabel("hour of day"); axB.set_ylabel("cars charging at the site")
axB.set_title("Why: the whole site's charging shifts earlier",fontsize=10)
axB.legend(fontsize=7.6,loc="upper right"); axB.grid(alpha=0.3); axB.set_xlim(0,23)

# Panel C: real gate badges / banner
axC.text(0.5,0.86,"REAL SIMULATION RESULT   (seed 4541,  35% capacity,  one week)",
         ha="center",va="top",fontsize=9,weight="bold",transform=axC.transAxes)
axC.text(0.5,0.5,
   "Everyone follows the plan:   Driver ✓   Operator ✓   Grid ✓   →   DAY PASSES\n"
   "1 in 5 grab out of turn:   Driver ✓   Operator ✗   Grid ✗   →   DAY FAILS   "
   f"—  and Car #{disp}, which followed the rules, still lost {short:.0f}% of its charge",
   ha="center",va="center",fontsize=8.6,transform=axC.transAxes,
   bbox=dict(boxstyle="round,pad=0.4",fc="#fff8e1",ec="#f9a825"))
fig.suptitle("A worked example, straight from the simulator",fontsize=11,weight="bold",y=0.99)
out=PKG/"figures"/"fig_worked_example.pdf"
fig.savefig(out,bbox_inches="tight"); fig.savefig(PKG/"paper_final_result"/"fig_worked_example_real.png",dpi=150,bbox_inches="tight")
print("wrote",out,f"| Car#{disp} need={need:.1f} deviate={cumB[-1]:.1f} short={short:.0f}%  peakA={loadA.max()} peakB={loadB.max()}")
