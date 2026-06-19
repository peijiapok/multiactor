#!/usr/bin/env python3
"""Fleet-economics robustness: does the equilibrium result depend on modelling the
fleet operator as service-oriented rather than profit-oriented?

The main analysis uses a SERVICE/revenue-proxy fleet utility U_F (completion + low
waiting): the fleet's economic exposure to driver deviation runs through lost vehicle
availability and service shortfall (lost paid trips), not through energy cost. Here we
add an explicit PROFIT-weighted fleet utility and show that fleet profit is near-neutral
to deviation (because lower delivered energy mechanically lowers cost), so the
"fleet is harmed" result is specifically about service revenue, while the
selfish-equilibrium collapse and incentive-restoration conclusions (driven by the driver
and grid gates) are unchanged. Uses the existing response surface; no new simulation.
"""
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

OUT = Path("/home/jia/multi actor/equilibrium_optimization_20260616"); DATE="20260616"
sp=importlib.util.spec_from_file_location("gt", OUT/f"gametheory_equilibrium_{DATE}.py")
gt=importlib.util.module_from_spec(sp); sp.loader.exec_module(gt)

def mm(x):
    x=np.asarray(x,float); lo,hi=np.nanmin(x),np.nanmax(x)
    return np.full_like(x,0.5) if hi-lo<1e-12 else (x-lo)/(hi-lo)

rows=pd.read_csv(OUT/f"response_surface_rows_{DATE}.csv")
surf=gt.collapse_surface(rows, fleet="ServiceFirst")   # has U_D,U_F(service),U_G per (cap,grid,dev)
# attach raw cost/revenue from rows (mean over seeds), merge back
rows['grid']=rows['policy'].map(lambda p:'PeakPenalty' if 'PeakPenalty' in str(p) else 'NoGrid')
rows['fleet']=rows['policy'].map(lambda p:'SGW' if 'ServiceGridWeighted' in str(p) else 'SF')
sf=rows[rows.fleet=='SF']
econ=(sf.groupby(['capacity_pct','grid','dev_realized'])
        .agg(delivered=('total_delivered_kwh','mean'),
             ecost=('energy_cost_usd','mean'),
             dcharge=('demand_charge_exposure_usd_month_25','mean')).reset_index())
surf=surf.merge(econ,on=['capacity_pct','grid','dev_realized'],how='left')

LAM=1.0  # full cost offset = "pure profit" stress case
recs=[]; rows_out=[]
for cap,gc in surf.groupby('capacity_pct'):
    gc=gc.copy()
    gc['cost_norm']=mm(gc['ecost']+gc['dcharge'])
    gc['rev_norm']=mm(gc['delivered'])             # revenue proxy = energy delivered
    # profit-weighted fleet utility: service-revenue minus normalized cost, renormalized
    gc['UF_profit']=0.0
    for grid,g2 in gc.groupby('grid'):
        idx=g2.index
        prof = g2['U_F'].to_numpy() - LAM*g2['cost_norm'].to_numpy()   # service(rev) minus cost
        gc.loc[idx,'UF_profit']=mm(prof)
    for _,r in gc.iterrows():
        rows_out.append(dict(cap=cap,grid=r['grid'],dev=r['dev_realized'],
                             UF_service=r['U_F'],UF_profit=r['UF_profit']))
    # equilibrium comparison at this capacity (NoGrid base, selfish d=0.05 ; NBS via Nash product)
    base=gc[gc.grid=='NoGrid']
    cells={grid:gt.surfaces_for(gc[gc.grid==grid]) for grid in gc.grid.unique()}
    # profit surfaces
    def surf1d(sub,col): 
        d=sub['dev_realized'].to_numpy(); 
        o=np.argsort(d); return lambda x: np.interp(np.clip(x,d[o][0],d[o][-1]),d[o],sub[col].to_numpy()[o])
    UFp={grid:surf1d(gc[gc.grid==grid],'UF_profit') for grid in gc.grid.unique()}
    dsel=0.05
    for tag,UFsel in [('service',float(cells['NoGrid']['U_F'](dsel))),('profit',float(UFp['NoGrid'](dsel)))]:
        UD=float(cells['NoGrid']['U_D'](dsel)); UG=float(cells['NoGrid']['U_G'](dsel))
        Wsel=(UD+UFsel+UG)/3
        # NBS over grid x dev grid
        best=None
        for grid in cells:
            dg=np.linspace(0,0.45,300)
            for d in dg:
                uD,uG=float(cells[grid]['U_D'](d)),float(cells[grid]['U_G'](d))
                uF=float(cells[grid]['U_F'](d)) if tag=='service' else float(UFp[grid](d))
                gains=(max(uD-UD,0)+1e-9)*(max(uF-UFsel,0)+1e-9)*(max(uG-UG,0)+1e-9)
                W=(uD+uF+uG)/3
                if best is None or gains>best[0]: best=(gains,W,grid,d,uD,uF,uG)
        poa=best[1]/Wsel if Wsel>1e-9 else float('nan')
        recs.append(dict(cap=cap,fleet_model=tag,UF_selfish=round(UFsel,3),UF_nbs=round(best[5],3),
                         poa=round(poa,3),nbs_grid=best[2],nbs_d=round(best[3],3)))

res=pd.DataFrame(recs); ro=pd.DataFrame(rows_out)
res.to_csv(OUT/f"fleet_profit_robustness_{DATE}.csv",index=False)
print("=== Fleet utility at selfish-NE (d=0.05) vs Nash-bargaining point, per capacity ===")
print(res.to_string(index=False))
print()
print("=== Fleet utility vs deviation (35% cap, NoGrid): service degrades, profit ~flat ===")
s35=ro[(ro.cap==35)&(ro.grid=='NoGrid')].sort_values('dev')
for _,r in s35.iterrows(): print(f"  d={r.dev:.3f}: U_F_service={r.UF_service:.3f}  U_F_profit={r.UF_profit:.3f}")

# figure: clean mechanism view (35% NoGrid) -- revenue & cost fall TOGETHER (profit offsets),
# while the service/availability utility degrades.
g35=surf[(surf.capacity_pct==35)&(surf.grid=='NoGrid')].sort_values('dev_realized')
dd=g35['dev_realized'].to_numpy()
fig,ax=plt.subplots(figsize=(6.4,4.3))
ax.plot(dd, mm(g35['delivered']),'-o',color='#2980b9',lw=2,ms=4,label='delivered energy (fleet revenue proxy)')
ax.plot(dd, mm(g35['ecost']+g35['dcharge']),'-s',color='#7f8c8d',lw=2,ms=4,label='energy + demand-charge cost')
ax.plot(dd, g35['U_F'].to_numpy(),'-^',color='#c0392b',lw=2.4,ms=5,label='fleet service utility $U_F$ (availability/waiting)')
ax.axvline(0.05,color='k',ls='--',lw=1); ax.text(0.055,0.04,'selfish NE\n$d^*=5\\%$',fontsize=8)
ax.set_xlabel('driver deviation $d$'); ax.set_ylabel('normalised (35% capacity, NoGrid)')
ax.set_title('Why fleet harm runs through service, not energy cost: revenue and cost\n'
             'fall together with deviation (profit offsets), but service/availability degrades',fontsize=8.5)
ax.legend(fontsize=7.5,loc='upper right'); ax.grid(alpha=0.3); ax.set_xlim(0,0.3); ax.set_ylim(-0.03,1.05)
fig.tight_layout(); fig.savefig(OUT/"figures"/"fig_eq_fleet_profit.pdf")
import shutil; shutil.copy(OUT/"figures"/"fig_eq_fleet_profit.pdf","/home/jia/multi actor/final_applied_energy_package_20260609/figures/")
fig.savefig(OUT/"figures"/"fig_eq_fleet_profit.png",dpi=120)
print("\nfigure + csv written")
