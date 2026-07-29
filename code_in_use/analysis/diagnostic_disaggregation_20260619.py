#!/usr/bin/env python3
"""Reviewer-4 #1,#4: disaggregate the all-pass collapse to show WHERE it fails, WHICH gate
binds first, and WHICH behavior drives it -- the diagnostic value of the framework.
All from existing data (seed20 sweep + 9-behavior matrix); no new simulation."""
import pandas as pd, numpy as np
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
OUT=Path("/home/jia/multi actor/equilibrium_optimization_20260616"); DATE="20260619"

d=pd.read_csv('/home/jia/multi actor/seed20_expansion_20260615/seed20_row_results_20260615.csv')
d['grid']=d.policy.map(lambda p:'PeakPenalty' if 'PeakPenalty' in str(p) else 'NoGrid')
b=pd.read_csv('/home/jia/multi actor/multi_actor_fleet_charging_v2_20260526/multi_actor_v2_row_results.csv')
b['behavior']=b.policy.map(lambda p: str(p).split('D_')[1].split('__')[0] if 'D_' in str(p) else 'LL')
b['fleet']=b.policy.map(lambda p: str(p).split('__F_')[1].split('__')[0] if '__F_' in str(p) else 'LL')
bf=b[b.fleet=='ServiceFirst'].copy()
churn=bf.groupby('behavior').apply(lambda x:(x['actual_request_count_driver_layer']/x['fleet_recommended_request_count'].replace(0,np.nan)).mean(),include_groups=False)
bg=bf.groupby('behavior')[['driver_service_pass','fleet_operation_pass','grid_pass','all_pass']].mean()
bg['churn']=churn
ORD=['FullyCompliant','LimitedAttentionP0025','LimitedAttentionP005','UrgencyDriven','ReserveSeeking','SoCCompliance','PriceSensitive','SoCQueueCompliance']
bg=bg.reindex([x for x in ORD if x in bg.index])
LAB={'FullyCompliant':'Full\ncompliance','LimitedAttentionP0025':'Inattention\n2.5%','LimitedAttentionP005':'Inattention\n5%','UrgencyDriven':'Urgency','ReserveSeeking':'Reserve-\nseeking','SoCCompliance':'SoC\nanxiety','PriceSensitive':'Price-\nsensitive','SoCQueueCompliance':'SoC+queue'}

fig,axes=plt.subplots(1,3,figsize=(15,4.4))
# A: all-pass by capacity x grid, severity 0 vs 1
ax=axes[0]; caps=[20,35,50]; x=np.arange(len(caps)); w=0.2
for i,(sev,grid,col,hatch) in enumerate([(0,'NoGrid','#27ae60',''),(0,'PeakPenalty','#2ecc71','//'),(1,'NoGrid','#c0392b',''),(1,'PeakPenalty','#e74c3c','//')]):
    vals=[d[(d.severity_level==sev)&(d.capacity_pct==c)&(d.grid==grid)]['all_pass'].mean() for c in caps]
    ax.bar(x+(i-1.5)*w,vals,w,color=col,hatch=hatch,edgecolor='k',lw=0.4,label=f"sev{sev} {grid}")
ax.set_xticks(x); ax.set_xticklabels([f"{c}%" for c in caps]); ax.set_xlabel('charger capacity'); ax.set_ylabel('all-pass feasibility')
ax.set_title('(A) Collapse is uniform across capacity\n(more chargers do not help)',fontsize=9.5)
ax.legend(fontsize=7,ncol=2); ax.set_ylim(0,1.05); ax.grid(alpha=0.3,axis='y')
# B: actor-gate pass by capacity at severity 1 (which gate binds first)
ax=axes[1]; s1=d[d.severity_level==1]
for j,(g,col) in enumerate([('driver_service_pass','#c0392b'),('fleet_operation_pass','#e67e22'),('grid_pass','#2980b9')]):
    vals=[s1[s1.capacity_pct==c][g].mean() for c in caps]
    ax.bar(x+(j-1)*0.25,vals,0.25,color=col,edgecolor='k',lw=0.4,label=g.split('_')[0])
ax.set_xticks(x); ax.set_xticklabels([f"{c}%" for c in caps]); ax.set_xlabel('charger capacity'); ax.set_ylabel('gate pass rate (severity 1)')
ax.set_title('(B) The driver gate binds first\n(lowest-passing actor across capacity)',fontsize=9.5)
ax.legend(fontsize=8,title='actor gate'); ax.set_ylim(0,1.05); ax.grid(alpha=0.3,axis='y')
# C: all-pass + churn by behavior type
ax=axes[2]; xb=np.arange(len(bg))
ax.bar(xb,bg['all_pass'],0.6,color=['#27ae60' if v>0.5 else '#c0392b' for v in bg['all_pass']],edgecolor='k',lw=0.4,label='all-pass')
ax.set_xticks(xb); ax.set_xticklabels([LAB[i] for i in bg.index],fontsize=7); ax.set_ylabel('all-pass feasibility'); ax.set_ylim(0,1.05)
ax2=ax.twinx(); ax2.plot(xb,bg['churn'],'k^-',ms=6,label='request churn x')
ax2.set_ylabel('request-event churn ratio (x)'); ax2.set_ylim(0,10)
ax.set_title('(C) Self-service behaviors (high churn) collapse it;\ninattention (low churn) does not',fontsize=9.5)
ax.grid(alpha=0.3,axis='y')
h1,l1=ax.get_legend_handles_labels(); h2,l2=ax2.get_legend_handles_labels(); ax.legend(h1+h2,l1+l2,fontsize=8,loc='upper right')
fig.suptitle('Disaggregated diagnosis: where it fails (all capacities), which gate (driver), and which behavior (self-service churn)',fontsize=11,y=1.02)
fig.tight_layout(); fig.savefig(OUT/"figures"/"fig_eq_diagnostic.pdf",bbox_inches='tight')
import shutil; shutil.copy(OUT/"figures"/"fig_eq_diagnostic.pdf","/home/jia/multi actor/final_applied_energy_package_20260609/figures/")
fig.savefig(OUT/"figures"/"fig_eq_diagnostic.png",dpi=120,bbox_inches='tight')
bg.round(3).to_csv(OUT/f"diagnostic_by_behavior_{DATE}.csv")
print("=== behavior-type diagnostic ==="); print(bg.round(3).to_string())
print("\nfigure written")
