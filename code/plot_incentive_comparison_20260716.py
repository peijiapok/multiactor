#!/usr/bin/env python3
"""Figure: equal-budget incentive comparison. all-pass vs budget, one line per allocation rule."""
from pathlib import Path
import pandas as pd, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC=Path("/home/jia/multi actor/equilibrium_optimization_20260616/incentive_comparison_20260716.csv")
FIGDIR=Path("/home/jia/multi actor/final_applied_energy_package_20260609/figures")
RESDIR=Path("/home/jia/multi actor/final_applied_energy_package_20260609/paper_final_result")
df=pd.read_csv(SRC)

LAB={"none":"No incentive","flat_tou":"Flat off-peak discount (uniform)",
     "slack":"Slack-based discount (pays those who can wait)",
     "compliance":"Compliance bonus (pays likely deviators)",
     "override_fee":"Override fee (revenue-generating deterrent)"}
COL={"none":"#888888","flat_tou":"#1f77b4","slack":"#d62728","compliance":"#2ca02c","override_fee":"#9467bd"}
MK={"none":"o","flat_tou":"s","slack":"^","compliance":"D","override_fee":"v"}

fig,ax=plt.subplots(figsize=(6.4,4.2))
for sc in ["flat_tou","slack","compliance","override_fee"]:
    d=df[df.scheme==sc].sort_values("budget")
    if len(d)==0: continue
    ls="--" if sc=="override_fee" else "-"
    ax.plot(d.budget,d.all_pass,ls,color=COL[sc],marker=MK[sc],lw=2,ms=6,label=LAB[sc])
# none: horizontal baseline at its single value
n0=df[df.scheme=="none"].all_pass.iloc[0]
ax.axhline(n0,color=COL["none"],ls=":",lw=1.5,label=LAB["none"]+f" (={n0:.2f})")
ax.set_xlabel("Incentive budget  (mean transfer per present vehicle, normalised utility units)")
ax.set_ylabel("Joint all-pass feasibility")
ax.set_ylim(-0.03,1.05); ax.set_xlim(-0.005,0.205)
ax.set_title("Equal-budget incentive comparison (5% deviation, 35% capacity)")
ax.grid(alpha=0.3); ax.legend(fontsize=7.5,loc="center left")
fig.tight_layout()
out=FIGDIR/"fig_incentive_comparison_20260716.pdf"
fig.savefig(out); fig.savefig(RESDIR/"fig_incentive_comparison_20260716.png",dpi=140)
print("wrote",out)

# print the equal-budget crossing points for the text
eqb=df[df.scheme!="override_fee"]
piv=eqb.pivot_table(index="budget",columns="scheme",values="all_pass")
print(piv.to_string())
for sc in ["flat_tou","compliance","slack"]:
    d=df[(df.scheme==sc)&(df.all_pass>=1.0)]
    b=d.budget.min() if len(d) else float("nan")
    print(f"{sc}: all-pass=1.0 first at budget={b}")
