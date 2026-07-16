#!/usr/bin/env python3
"""Optimizer baselines vs the gate screen (committee comparison table, made concrete).

Answers "why not just tune a weighted objective, or hard-constrain the optimizer?" with
real numbers, as honest post-processing over the ACHIEVABLE controller menu (no new sim).

At each behavioral severity and 35% capacity we take the achievable controllers
  {ServiceFirst, ServiceGridWeighted} x {NoGridAdjustment, GridPeakPenalty}  (+ LeastLaxity),
average each controller's objective components over seeds, and read three normalised costs:
  J_D driver   = 1 - trip reliability            (lower is better)
  J_O operator = 0.5*p95 wait + 0.5*energy cost  (min-max normalised across the menu)
  J_G grid     = 0.5*peak-to-average + 0.5*ramp  (min-max normalised across the menu)
plus each controller's mean same-episode all-pass rate.

Two optimizers, compared with the non-compensatory gate screen:
  (1) WEIGHTED-SUM optimizer: for a grid of weights (a,b,g) on the simplex, pick the
      controller minimising a*J_D + b*J_O + g*J_G, and record whether that blended
      optimum is jointly feasible. Question: can ANY weighting keep the blended optimum
      feasible once drivers deviate? (Compensatory: a surplus in one term hides a
      shortfall in another.)
  (2) HARD-CONSTRAINED optimizer (eq:optwithin): min J s.t. all-pass = 1, i.e. optimise
      only inside the jointly-feasible set. Question: is that set non-empty?

Expected and reported: at full compliance a feasible weighting/point exists; under
behavioral deviation the WHOLE achievable menu collapses, so no weighting recovers
feasibility (weighted-sum) and the hard constraint set is EMPTY (hard-constrained) --
the collapse is a behavioral property, orthogonal to the objective weighting.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, itertools

ROOT=Path("/home/jia/multi actor")
SRC=ROOT/"seed20_expansion_20260615"/"seed20_row_results_20260615.csv"
OUT=ROOT/"equilibrium_optimization_20260616"; DATE="20260716"
PKG=ROOT/"final_applied_energy_package_20260609"
CAP=35
FEAS=1.0            # a controller counts as jointly feasible if mean all-pass == 1.0 (feasible in every seed)

def norm(x):
    x=np.asarray(x,float); lo,hi=x.min(),x.max()
    return np.zeros_like(x) if hi-lo<1e-12 else (x-lo)/(hi-lo)

def controller_table(df):
    """One row per achievable controller (operator x grid), objective means + all-pass."""
    g=(df.groupby(["fleet_policy","grid_policy"])
         .agg(reliability=("reliability_pct","mean"),
              p95_wait=("p95_wait_minutes","mean"),
              energy_cost=("energy_cost_usd","mean"),
              p2a=("peak_to_average_ratio","mean"),
              ramp=("ramp_p95_kw","mean"),
              all_pass=("all_pass","mean")).reset_index())
    g["J_D"]=norm(100.0-g.reliability)
    g["J_O"]=0.5*norm(g.p95_wait)+0.5*norm(g.energy_cost)
    g["J_G"]=0.5*norm(g.p2a)+0.5*norm(g.ramp)
    return g

def simplex(step=0.05):
    pts=[]; n=int(round(1/step))
    for i in range(n+1):
        for j in range(n+1-i):
            k=n-i-j; pts.append((i/n,j/n,k/n))
    return pts

def main():
    s=pd.read_csv(SRC)
    s=s[(s.capacity_pct==CAP)&(s.policy!="LeastLaxity")&(s.fleet_policy.notna())].copy()
    weights=simplex(0.05)
    recs=[]
    for sev in [0.0,1.0,2.0,3.0]:
        d=s[s.severity_level==sev]
        if len(d)==0: continue
        g=controller_table(d)
        J=g[["J_D","J_O","J_G"]].values; ap=g.all_pass.values
        # (1) weighted-sum optimizer: argmin blend over the weight simplex
        feas_w=0; sel_ap=[]
        for (a,b,c) in weights:
            blend=a*J[:,0]+b*J[:,1]+c*J[:,2]
            idx=int(np.argmin(blend)); sel_ap.append(ap[idx])
            if ap[idx]>=FEAS: feas_w+=1
        sel_ap=np.array(sel_ap)
        # (2) hard-constrained optimizer: min J (equal-weight) s.t. all-pass==1
        feasible=g[g.all_pass>=FEAS]
        hard_nonempty=len(feasible)>0
        if hard_nonempty:
            fJ=feasible.J_D.values+feasible.J_O.values+feasible.J_G.values
            hard_pick=feasible.iloc[int(np.argmin(fJ))]
            hard_desc=f"{hard_pick.fleet_policy}/{hard_pick.grid_policy}"
        else:
            hard_desc="EMPTY (no jointly-feasible controller)"
        # best single metric (driver reliability) controller and ITS all-pass
        best_drv=g.iloc[int(g.reliability.values.argmax())]
        recs.append(dict(
            severity=int(sev), n_controllers=len(g),
            weighted_feasible_frac=round(feas_w/len(weights),3),
            weighted_sel_allpass_mean=round(float(sel_ap.mean()),3),
            weighted_sel_allpass_max=round(float(sel_ap.max()),3),
            hard_constrained=hard_desc,
            best_reliability_pct=round(float(best_drv.reliability),1),
            best_reliability_allpass=round(float(best_drv.all_pass),3),
            menu_max_allpass=round(float(ap.max()),3)))
    out=pd.DataFrame(recs)
    out.to_csv(OUT/f"weighted_optimizer_baseline_{DATE}.csv",index=False)
    (PKG/"paper_final_result").mkdir(exist_ok=True)
    out.to_csv(PKG/"paper_final_result"/f"weighted_optimizer_baseline_{DATE}.csv",index=False)
    pd.set_option("display.width",200,"display.max_columns",20)
    print("=== Optimizer baselines vs gate screen (35% cap, achievable controller menu) ===")
    print(out.to_string(index=False))

    # compact figure: fraction of weightings whose blended optimum is feasible, vs severity
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(6.0,3.9))
    ax.bar(out.severity-0.15,out.weighted_sel_allpass_mean,0.3,color="#1f77b4",
           label="weighted-sum optimum\n(mean all-pass over weight simplex)")
    ax.bar(out.severity+0.15,out.menu_max_allpass,0.3,color="#2ca02c",
           label="best achievable controller\n(hard-constrained ceiling)")
    ax.set_xticks(out.severity)
    ax.set_xticklabels([f"sev {i}\n({p})" for i,p in zip(out.severity,["0%","~5%","~20%","~45%"])])
    ax.set_ylabel("fraction feasible / max all-pass")
    ax.set_ylim(0,1.05); ax.grid(axis="y",alpha=0.3)
    ax.set_xlabel("behavioral deviation severity")
    ax.set_title("No objective weighting escapes the behavioral collapse\n(35% capacity)",fontsize=10)
    ax.legend(fontsize=7.5,loc="upper right")
    fig.tight_layout()
    fig.savefig(PKG/"figures"/"fig_weighted_optimizer_baseline_20260716.pdf")
    fig.savefig(PKG/"paper_final_result"/"fig_weighted_optimizer_baseline_20260716.png",dpi=140)
    print("\nfigure written")

if __name__=="__main__":
    main()
