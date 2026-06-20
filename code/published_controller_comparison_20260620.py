#!/usr/bin/env python3
"""Reviewer-6 #1: apply the framework to RECOGNIZED PUBLISHED controllers and show
single-metric success but same-episode multi-actor-conjunction failure.

Consolidates, at FULL COMPLIANCE (the cleanest case -- the controller, not driver
behavior, is on trial), the per-gate pass rates and a headline single metric
(trip reliability) for:
  * EDF -- Earliest-Deadline-First (Liu & Layland 1973), the canonical real-time
    deadline scheduler and the family of the ACN adaptive charging algorithm.
  * Uncoordinated immediate charging -- the universal business-as-usual baseline.
  * (reference) the in-framework LeastLaxity-anchored ServiceFirst, for contrast.

Output: published_controller_comparison_20260620.csv + a compact bar figure.
No new simulation (reads the EDF and uncoordinated baseline result CSVs).
"""
import pandas as pd, numpy as np
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ROOT=Path("/home/jia/multi actor")
OUT=ROOT/"equilibrium_optimization_20260616"
PKG=ROOT/"final_applied_energy_package_20260609"

def fc(df): return df[df.dab==0.0] if 'dab' in df else df[df.dev_target==0.0]

edf=pd.read_csv(OUT/"edf_baseline_rows_20260619.csv")
edf0=edf[edf.dev_target==0.0]
unc=pd.read_csv(OUT/"uncoordinated_baseline_rows_20260620.csv")
unc0=unc[unc.dev_target==0.0]
# ServiceFirst (LeastLaxity-anchored) reference at full compliance, 35% cap,
# restricted to the SAME 5 seeds (4541-4545) as the EDF/uncoordinated runs for
# exact comparability.
s=pd.read_csv(ROOT/"seed20_expansion_20260615/seed20_row_results_20260615.csv")
sf0=s[(s.severity_level==0.0)&(s.capacity_pct==35)&(s.policy.str.contains('ServiceFirst'))
      &(s.seed.isin([4541,4542,4543,4544,4545]))]

def row(name, df, cite):
    return dict(
        controller=name, citation=cite,
        trip_reliability_pct=round(df['reliability_pct'].mean(),1),
        driver_gate=round(df['driver_service_pass'].mean(),3),
        fleet_gate=round(df['fleet_operation_pass'].mean(),3),
        grid_gate=round(df['grid_pass'].mean(),3),
        all_pass=round(df['all_pass'].mean(),3),
        p95_wait_min=round(df['p95_wait_minutes'].mean(),1),
    )

rows=[
    row("ServiceFirst (LeastLaxity-anchored)", sf0, "Dertouzos-Mok 1989 (LLF)"),
    row("Earliest-Deadline-First (EDF)", edf0, "Liu-Layland 1973; ACN family Lee 2021"),
    row("Uncoordinated immediate charging", unc0, "Clement-Nyns 2010; Ma 2013"),
]
tab=pd.DataFrame(rows)
print("=== Published-controller comparison at FULL COMPLIANCE (35% cap) ===")
print(tab.to_string(index=False))
tab.to_csv(OUT/"published_controller_comparison_20260620.csv",index=False)

# figure: single metric (reliability, scaled to [0,1]) vs same-episode all-pass
fig,ax=plt.subplots(figsize=(7.2,4.0))
labels=[r['controller'].replace(' (','\n(') for r in rows]
x=np.arange(len(rows)); w=0.38
rel=[r['trip_reliability_pct']/100 for r in rows]
ap=[r['all_pass'] for r in rows]
b1=ax.bar(x-w/2,rel,w,color='#3498db',label='trip reliability (single metric)')
b2=ax.bar(x+w/2,ap,w,color='#c0392b',label='same-episode all-pass (14-gate conjunction)')
for b,v in zip(b1,rel): ax.text(b.get_x()+b.get_width()/2,v+0.015,f"{v*100:.0f}%",ha='center',fontsize=8)
for b,v in zip(b2,ap): ax.text(b.get_x()+b.get_width()/2,v+0.015,f"{v*100:.0f}%",ha='center',fontsize=8,fontweight='bold')
ax.set_xticks(x); ax.set_xticklabels(labels,fontsize=8)
ax.set_ylim(0,1.08); ax.set_ylabel('rate (full compliance)')
ax.set_title('Recognized published controllers: high single-metric reliability,\n'
             'low same-episode multi-actor feasibility',fontsize=9.5)
ax.legend(fontsize=8,loc='center right'); ax.grid(axis='y',alpha=0.3)
fig.tight_layout()
fig.savefig(OUT/"figures"/"fig_published_controllers.pdf")
fig.savefig(OUT/"figures"/"fig_published_controllers.png",dpi=120)
import shutil; shutil.copy(OUT/"figures"/"fig_published_controllers.pdf",PKG/"figures"/"fig_published_controllers.pdf")
print("\nfigure + csv written")
