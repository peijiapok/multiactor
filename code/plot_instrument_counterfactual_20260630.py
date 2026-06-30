#!/usr/bin/env python3
"""Figure for the mechanism-targeting counterfactual: removing the self-service override
motive (what service-guarantee / override-pricing instruments do) recovers same-episode
feasibility at a FIXED deviation rate, confirming the diagnosed cause. Complementary to
raising compliance (lowering the rate): at high rates even benign deviation fails."""
import pandas as pd, numpy as np
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ROOT=Path("/home/jia/multi actor"); OUT=ROOT/"equilibrium_optimization_20260616"
PKG=ROOT/"final_applied_energy_package_20260609"
df=pd.read_csv(OUT/"instrument_counterfactual_20260630.csv")
piv=df.pivot(index="dev_target",columns="mode",values="all_pass")
x=piv.index.values*100

fig,ax=plt.subplots(figsize=(6.0,4.0))
ax.plot(x,piv["self_service"].values,'-o',color='#c0392b',lw=2.4,ms=6,label='self-service override (reserve/price churn)')
ax.plot(x,piv["benign"].values,'-s',color='#27ae60',lw=2.4,ms=6,label='override motive removed (abstain)')
ax.axhline(0,color='gray',lw=0.6)
ax.annotate('motive removed,\nsame rate', xy=(2.5,0.80), xytext=(3.6,0.78), fontsize=8,
            arrowprops=dict(arrowstyle='->',color='#27ae60'))
ax.annotate('immediate collapse', xy=(2.5,0.0), xytext=(4.0,0.10), fontsize=8,
            arrowprops=dict(arrowstyle='->',color='#c0392b'))
ax.set_xlabel('driver deviation rate (\\%)'); ax.set_ylabel('same-episode all-pass feasibility')
ax.set_ylim(-0.04,1.06); ax.set_xlim(-0.3,10.3)
ax.set_title('Targeting the diagnosed override motive recovers feasibility at fixed\n'
             'deviation rate (35\\% capacity); full recovery also needs lower deviation',fontsize=9)
ax.legend(fontsize=8,loc='upper right'); ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT/"figures"/"fig_instrument_counterfactual.pdf")
fig.savefig(OUT/"figures"/"fig_instrument_counterfactual.png",dpi=120)
import shutil; shutil.copy(OUT/"figures"/"fig_instrument_counterfactual.pdf",PKG/"figures"/"fig_instrument_counterfactual.pdf")
print("figure written; values:")
print(piv.to_string())
