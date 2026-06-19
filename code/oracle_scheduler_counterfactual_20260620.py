#!/usr/bin/env python3
"""Oracle scheduler-selection counterfactual (Reviewer-5 #1).

Question: can a BETTER or DIFFERENT scheduler rescue same-episode multi-actor
feasibility under severity-1 behavioral deviation, or is the collapse inherent to
the condition (the deviation) rather than to the scheduler?

We bound what scheduler choice alone can achieve at severity 1 with an oracle that
is strictly more generous than any deployable policy:

  (a) BEST single deployable scheduler config = max over the scheduler menu of the
      mean severity-1 all-pass (the best policy you could pick in advance).
  (b) PER-EPISODE ORACLE = for each (seed, capacity) episode, all-pass if ANY
      scheduler in the menu passes that episode (hindsight-optimal per-episode
      selection -- an upper bound no real controller can exceed).

Intervention model (stated explicitly): a scheduler observes the realized request
stream and allocates charging power and queue order subject to capacity. It does
NOT coerce a driver to issue a critical request, pre-empt energy a driver declined,
or see future requests except through the deadline/laxity signal already provided.
These are the standard managed-charging assumptions. Under them, the binding
severity-1 gate (critical-requested-not-delivered, a driver-service guarantee) is
set by whether deviating vehicles depart from their recommended critical-service
schedule -- an action outside the scheduler's action space.

Data: 20-seed service-oriented family (ServiceFirst, ServiceGridWeighted x NoGrid,
PeakPenalty; 240 severity-1 episodes) plus the EDF baseline (third scheduler
family) as a cross-family confirmation. No new simulation.
"""
import pandas as pd, numpy as np
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ROOT=Path("/home/jia/multi actor")
OUT=ROOT/"equilibrium_optimization_20260616"
PKG=ROOT/"final_applied_energy_package_20260609"

def fleet_of(p):
    if 'ServiceGridWeighted' in p: return 'ServiceGridWeighted'
    if 'ServiceFirst' in p: return 'ServiceFirst'
    if 'F_EDF' in p: return 'EDF'
    return 'other'
def grid_of(p): return 'PeakPenalty' if 'PeakPenalty' in p else 'NoGrid'

s=pd.read_csv(OUT.parent/"seed20_expansion_20260615/seed20_row_results_20260615.csv")
s1=s[s['severity_level']==1.0].copy()
s1['fleet']=s1['policy'].map(fleet_of); s1['grid']=s1['policy'].map(grid_of)
s1=s1[s1.fleet!='other']

# --- (a) best single deployable scheduler config (20 seeds x 3 caps) ---
percfg=s1.groupby(['fleet','grid'])['all_pass'].mean()
best_single=percfg.max()

# --- (b) per-episode oracle over the service scheduler menu ---
orc=s1.groupby(['seed','capacity_pct'])['all_pass'].max()
oracle=orc.mean()
orc_by_cap=s1.groupby(['seed','capacity_pct'])['all_pass'].max().groupby('capacity_pct').mean()

# bootstrap CI for the oracle (episode-level resample)
rng=np.random.RandomState(12345)
v=orc.values.astype(float)
bs=np.array([rng.choice(v,len(v),replace=True).mean() for _ in range(10000)])
ci=(np.percentile(bs,2.5),np.percentile(bs,97.5))

# --- EDF cross-family confirmation (5 seeds @35%) ---
e=pd.read_csv(OUT/"edf_baseline_rows_20260619.csv")
e1=e[e['policy'].str.contains('Severity1Mild')].copy()
edf_sev1=e1['all_pass'].mean()

# --- full-compliance reference for the level-vs-threshold contrast ---
s0=s[(s['severity_level']==0.0)].copy()
s0['fleet']=s0['policy'].map(fleet_of)
full_comp=s0[s0.fleet.isin(['ServiceFirst','ServiceGridWeighted'])]['all_pass'].mean()

print("=== Oracle scheduler-selection counterfactual (severity 1) ===")
print("per-config severity-1 all-pass:")
print(percfg.round(4).to_string())
print(f"\n(a) BEST single deployable scheduler config : {best_single:.4f}")
print(f"(b) per-episode ORACLE (best-of-menu/episode): {oracle:.4f}  "
      f"[95% CI {ci[0]:.4f}, {ci[1]:.4f}]  ({int(orc.sum())}/{len(orc)} episodes)")
print("    oracle by capacity:", {int(k):round(x,4) for k,x in orc_by_cap.items()})
print(f"    EDF (third family) severity-1 all-pass : {edf_sev1:.4f}")
print(f"    full-compliance reference all-pass     : {full_comp:.4f}")

rows=[dict(metric='best_single_scheduler',value=round(best_single,4)),
      dict(metric='per_episode_oracle',value=round(oracle,4)),
      dict(metric='oracle_ci_lo',value=round(ci[0],4)),
      dict(metric='oracle_ci_hi',value=round(ci[1],4)),
      dict(metric='oracle_cap20',value=round(orc_by_cap.get(20,np.nan),4)),
      dict(metric='oracle_cap35',value=round(orc_by_cap.get(35,np.nan),4)),
      dict(metric='oracle_cap50',value=round(orc_by_cap.get(50,np.nan),4)),
      dict(metric='edf_severity1',value=round(edf_sev1,4)),
      dict(metric='full_compliance',value=round(full_comp,4))]
pd.DataFrame(rows).to_csv(OUT/"oracle_scheduler_counterfactual_20260620.csv",index=False)

# --- figure: full-compliance plateau vs severity-1 best-achievable across the menu ---
# (EDF is reported in text as a cross-family confirmation, not on the headline bars:
#  its severity-1 estimate is a 5-seed/35%-only slice within noise of zero and its
#  full-compliance plateau is only 0.20, i.e. a weak not a rescuing scheduler.)
fig,ax=plt.subplots(figsize=(5.6,4.0))
labels=['full\ncompliance','best single\nscheduler\n(sev 1)','per-episode\nORACLE\n(sev 1)']
vals=[full_comp,best_single,oracle]
cols=['#27ae60','#e67e22','#c0392b']
bars=ax.bar(labels,vals,color=cols,width=0.58)
for b,v_ in zip(bars,vals): ax.text(b.get_x()+b.get_width()/2,v_+0.02,f"{v_*100:.1f}%",ha='center',fontsize=9,fontweight='bold')
ax.errorbar(2,oracle,yerr=[[oracle-ci[0]],[ci[1]-oracle]],fmt='none',ecolor='k',capsize=4,lw=1.2)
ax.set_ylim(0,1.08); ax.set_ylabel('same-episode all-pass feasibility')
ax.set_title('Scheduler choice cannot rescue severity-1 feasibility:\n'
             'even a hindsight-optimal per-episode oracle reaches only 5%',fontsize=9.5)
ax.grid(axis='y',alpha=0.3)
fig.tight_layout()
fig.savefig(OUT/"figures"/"fig_oracle_scheduler.pdf")
fig.savefig(OUT/"figures"/"fig_oracle_scheduler.png",dpi=120)
import shutil; shutil.copy(OUT/"figures"/"fig_oracle_scheduler.pdf",PKG/"figures"/"fig_oracle_scheduler.pdf")
print("\nfigure + csv written")
