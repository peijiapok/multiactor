#!/usr/bin/env python3
"""Scenario-averaged vs same-episode feasibility (Reviewer-5 #4, PRIMARY figure).

Core thesis of the paper made visual: averaging acceptability over scenarios (the
conventional managed-charging evaluation) hides the joint infeasibility that a
same-episode multi-actor requirement exposes.

At severity 1, on a *scenario-averaged dashboard* most criteria look healthy:
9 of the 14 gate criteria pass in >=98% of episodes, 11 of 14 pass on average
(mean fraction-of-criteria = 0.79). A planner checking each criterion's average
would conclude the system is acceptable. But the *same-episode* conjunction --
all 14 criteria satisfied within the SAME episode, the actual deployment
requirement -- holds in only 1.25% of episodes. The gap between 79% (marginal
average) and 1.25% (joint) is the paper's central measurement.

Data: q1 per-criterion decomposition (robustness_analysis_20260614) for the
marginal pass rates; seed20 for the same-episode all-pass. No new simulation.
"""
import pandas as pd, numpy as np
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ROOT=Path("/home/jia/multi actor")
OUT=ROOT/"equilibrium_optimization_20260616"
PKG=ROOT/"final_applied_energy_package_20260609"

q1=pd.read_csv(ROOT/"robustness_analysis_20260614/q1_subcriterion_decomposition_20260614.csv")
q1['pass_frac']=1-q1['fail_frac_sev1']
q1=q1.sort_values('pass_frac')
marg_mean=q1['pass_frac'].mean()
n_pass98=int((q1['pass_frac']>=0.98).sum())

s=pd.read_csv(ROOT/"seed20_expansion_20260615/seed20_row_results_20260615.csv")
joint=s[s.severity_level==1.0]['all_pass'].mean()
# actor-gate marginal pass (driver/fleet/grid alone)
s1=s[s.severity_level==1.0]
actor={'driver':s1['driver_service_pass'].mean(),'fleet':s1['fleet_operation_pass'].mean(),
       'grid':s1['grid_pass'].mean()}

print(f"marginal mean fraction-of-14: {marg_mean:.3f}  ({n_pass98}/14 pass >=98%)")
print(f"same-episode all-pass: {joint:.4f}")
print("actor-gate marginal pass:", {k:round(v,3) for k,v in actor.items()})

fig,(axA,axB)=plt.subplots(1,2,figsize=(11.0,4.6),gridspec_kw={'width_ratios':[1.45,1]})

# Panel A: per-criterion marginal pass (the "dashboard" view)
colors=['#c0392b' if p<0.75 else ('#e67e22' if p<0.95 else '#27ae60') for p in q1['pass_frac']]
y=np.arange(len(q1))
axA.barh(y,q1['pass_frac'],color=colors,height=0.7)
axA.set_yticks(y); axA.set_yticklabels(q1['criterion'],fontsize=7.5)
axA.axvline(marg_mean,color='k',ls='--',lw=1.3)
axA.text(marg_mean+0.01,0.3,f"mean = {marg_mean:.2f}\n(≈11 of 14)",fontsize=8,va='bottom')
axA.set_xlim(0,1.02); axA.set_xlabel('fraction of episodes passing the criterion (scenario-averaged)')
axA.set_title('(A) Marginal view: each criterion checked alone\n'
              f'{n_pass98} of 14 pass in ≥98% of episodes — looks acceptable',fontsize=9)
axA.grid(axis='x',alpha=0.3)

# Panel B: the collapse from marginal-average to joint same-episode
labels=['mean criterion\n(marginal avg)','best single\nactor gate','weakest single\nactor gate','SAME-EPISODE\nall 14 gates']
vals=[marg_mean,max(actor.values()),min(actor.values()),joint]
cols=['#27ae60','#2ecc71','#e67e22','#c0392b']
bars=axB.bar(labels,vals,color=cols,width=0.62)
for b,v_ in zip(bars,vals): axB.text(b.get_x()+b.get_width()/2,v_+0.02,f"{v_*100:.1f}%",ha='center',fontsize=8.5,fontweight='bold')
axB.set_ylim(0,1.05); axB.set_ylabel('acceptability')
axB.set_title('(B) Joint view: require all 14 in the same episode\n'
              f'{marg_mean*100:.0f}% marginal → {joint*100:.1f}% jointly feasible',fontsize=9)
axB.grid(axis='y',alpha=0.3)
axB.tick_params(axis='x',labelsize=7.5)

fig.suptitle('Scenario-averaged acceptability is a mirage: most criteria pass on average, '
             'almost none pass together',fontsize=10.5,y=1.0)
fig.tight_layout(rect=[0,0,1,0.97])
fig.savefig(OUT/"figures"/"fig_marginal_vs_joint.pdf")
fig.savefig(OUT/"figures"/"fig_marginal_vs_joint.png",dpi=120)
import shutil; shutil.copy(OUT/"figures"/"fig_marginal_vs_joint.pdf",PKG/"figures"/"fig_marginal_vs_joint.pdf")

pd.DataFrame([dict(metric='marginal_mean_frac14',value=round(marg_mean,4)),
              dict(metric='n_pass_98pct',value=n_pass98),
              dict(metric='best_actor_gate',value=round(max(actor.values()),4)),
              dict(metric='weakest_actor_gate',value=round(min(actor.values()),4)),
              dict(metric='same_episode_all_pass',value=round(joint,4))]
            ).to_csv(OUT/"scenario_averaged_vs_joint_20260620.csv",index=False)
print("figure + csv written")
