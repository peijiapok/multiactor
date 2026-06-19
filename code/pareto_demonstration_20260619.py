#!/usr/bin/env python3
"""Reviewer-2 #1: concrete demonstration that Pareto-efficiency in objective space does
NOT imply same-episode all-pass acceptability. Uses the existing 9-policy matrix (no new
simulation). Shows a Pareto-efficient scheduling policy (CostOnly) that dominates the
acceptable policy (ServiceFirst) on cost and service yet scores 0% same-episode all-pass."""
import pandas as pd, numpy as np
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
OUT=Path("/home/jia/multi actor/equilibrium_optimization_20260616"); DATE="20260619"
SRC="/home/jia/multi actor/multi_actor_fleet_charging_v2_20260526/multi_actor_v2_row_results.csv"

d=pd.read_csv(SRC)
d['fleet']=d.policy.map(lambda p: str(p).split('__F_')[1].split('__')[0] if '__F_' in str(p) else 'LL')
d['behavior']=d.policy.map(lambda p: str(p).split('D_')[1].split('__')[0] if 'D_' in str(p) else 'LL')
fc=d[d.behavior=='FullyCompliant']
g=fc.groupby('fleet').agg(
  cost=('energy_cost_ratio_vs_anchor','mean'), service=('reliability_pct','mean'),
  delivered=('delivered_ratio_vs_ll','mean'), peak=('peak_ratio_vs_ll','mean'),
  wait=('p95_wait_minutes','mean'),
  driver=('driver_service_pass','mean'), fleetg=('fleet_operation_pass','mean'),
  grid=('grid_pass','mean'), all_pass=('all_pass','mean')).reset_index()
# keep the 4 canonical scheduling controllers
keep=['CostOnly','QueueAware','ServiceFirst','AvailabilityFocused']
g=g[g.fleet.isin(keep)].reset_index(drop=True)

# Pareto efficiency in objective space: minimize cost, maximize service, minimize peak, minimize wait
def dominated(i,rows):
    a=rows.iloc[i]
    for j in range(len(rows)):
        if j==i: continue
        b=rows.iloc[j]
        better_eq=(b.cost<=a.cost)and(b.service>=a.service)and(b.peak<=a.peak)and(b.wait<=a.wait)
        strict=(b.cost<a.cost)or(b.service>a.service)or(b.peak<a.peak)or(b.wait<a.wait)
        if better_eq and strict: return True
    return False
g['pareto_efficient']=[not dominated(i,g) for i in range(len(g))]

pd.set_option('display.width',220)
print("=== Full-compliance: objectives, gate pass-rates, same-episode all-pass, Pareto status ===")
print(g[['fleet','cost','service','peak','wait','driver','fleetg','grid','all_pass','pareto_efficient']].round(3).to_string(index=False))

co=g[g.fleet=='CostOnly'].iloc[0]; sf=g[g.fleet=='ServiceFirst'].iloc[0]
print(f"\nKEY: CostOnly is Pareto-efficient={co.pareto_efficient}. It DOMINATES ServiceFirst on "
      f"cost ({co.cost:.3f}<{sf.cost:.3f}) and service ({co.service:.1f}>{sf.service:.1f}), "
      f"yet same-episode all-pass = {co.all_pass:.3f} vs ServiceFirst {sf.all_pass:.3f}.")
print(f"CostOnly fails the FLEET gate (pass-rate {co.fleetg:.3f}): its p95 wait {co.wait:.1f} min "
      f"exceeds the 30-min gate, so a marginal/Pareto evaluation that does not impose the "
      f"per-episode conjunction would rank CostOnly above ServiceFirst.")
g.to_csv(OUT/f"pareto_demonstration_{DATE}.csv",index=False)

# figure: cost vs service, colored by all_pass, Pareto front marked
fig,ax=plt.subplots(figsize=(6.4,4.6))
for _,r in g.iterrows():
    col='#27ae60' if r.all_pass>0.5 else '#c0392b'
    mk='o' if r.pareto_efficient else 'x'
    ax.scatter(r.cost,r.service,s=160,c=col,marker=mk,edgecolors='k',zorder=3)
    ax.annotate(f"{r.fleet}\n(all-pass {r.all_pass:.2f})",(r.cost,r.service),
                textcoords="offset points",xytext=(8,-4),fontsize=8)
ax.set_xlabel("energy-cost ratio vs anchor  (lower = better)")
ax.set_ylabel("trip reliability %  (higher = better)")
ax.set_title("Pareto efficiency does not imply same-episode acceptability\n"
             "CostOnly dominates ServiceFirst on cost and service, yet all-pass = 0",fontsize=10)
ax.scatter([],[],c='#27ae60',marker='o',edgecolors='k',label='all-pass acceptable')
ax.scatter([],[],c='#c0392b',marker='o',edgecolors='k',label='all-pass = 0 (fails conjunction)')
ax.legend(fontsize=8,loc='lower left'); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(OUT/"figures"/"fig_eq_pareto.pdf")
import shutil; shutil.copy(OUT/"figures"/"fig_eq_pareto.pdf","/home/jia/multi actor/final_applied_energy_package_20260609/figures/")
fig.savefig(OUT/"figures"/"fig_eq_pareto.png",dpi=120)
print("\nfigure + csv written")
