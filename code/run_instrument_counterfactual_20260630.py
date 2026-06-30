#!/usr/bin/env python3
"""Mechanism-targeting counterfactual (does the SOLUTION work, by the diagnosed mechanism?).

The diagnosis (Section sec:diagnostic) attributes the collapse to the self-service reserve/price
OVERRIDE MOTIVE, not to the deviation rate per se: at 5% deviation, self-service behaviors give
all-pass 0.00 while benign request-dropping gives ~0.53. The concrete instruments (service
guarantees, congestion-aware override pricing) act on that motive. We therefore test, in the real
multi-actor engine, whether REMOVING the override motive while HOLDING the deviation rate fixed
restores feasibility---the causal claim the instruments rely on.

Two driver conditions, matched deviation rate d in {0, 2.5%, 5%, 10%}, 35% capacity, both grid
policies, five seeds:
  * self_service : deviating vehicles self-serve (reserve/cheap-window churn)  [the collapse]
  * benign       : deviating vehicles ABSTAIN (idle) instead of self-serving   [motive removed]

This is a mechanism-targeting counterfactual, NOT a claim that real service guarantees or prices
will work; the behavioral response of a real instrument remains the calibration gap. Same gates,
same anchor (LeastLaxity). Reuses the engine path used for the EDF/uncoordinated baselines.
"""
from __future__ import annotations
import importlib.util, sys, time
from pathlib import Path
import numpy as np, pandas as pd

WORKSPACE = Path("/home/jia/thirfty death BRL DQN")
RUNNER = WORKSPACE / "scripts" / "run_multi_actor_v2_experiment.py"
OUT = Path("/home/jia/multi actor/equilibrium_optimization_20260616"); DATE="20260630"
SEEDS=[4541,4542,4543,4544,4545]; CAPACITIES=[35]; EPISODE_HOURS=168
DEV_GRID=[0.0,0.025,0.05,0.10]
DRIVER="Severity1Mild"; DRVCFG={"reserve_margin":0.05,"cheap_extra_margin":0.10}
GRIDS=("NoGridIncentive","GridPeakPenalty"); GRID_LABEL={"NoGridIncentive":"NoGrid","GridPeakPenalty":"PeakPenalty"}
ACTIVE_DEV=0.0; MODE="self_service"; DEV_ACC=[]

def import_runner():
    spec=importlib.util.spec_from_file_location("mav2_inst",RUNNER)
    mod=importlib.util.module_from_spec(spec); sys.modules["mav2_inst"]=mod; spec.loader.exec_module(mod); return mod

def structured_p_dev(d,laxity):
    lax=np.clip(np.asarray(laxity,float),0,1); n=lax.shape[0]
    if d<=0 or n==0: return np.zeros(n)
    w=1-lax; mw=float(w.mean())
    return np.full(n,d) if mw<=1e-9 else np.clip((d/mw)*w,0,1)

def install(mav2):
    pkg=mav2.pkg; original_driver=mav2._ORIG_DRIVER
    def severity_preference(env,obs,driver,rng,is_cheap):
        values=pkg._arrays(env,obs); critical=pkg._service_critical(values)
        available=values["masks"][:,pkg.PRIMITIVE_NORMAL_REQUEST]; cheap=bool(is_cheap[int(env.t)%len(is_cheap)])
        rt=values["theta"]+float(DRVCFG["reserve_margin"])+(float(DRVCFG["cheap_extra_margin"]) if cheap else 0.0)
        reserve_need=values["soc"]<=rt; eligible=available&(critical|values["target"]|reserve_need)
        score=(260*critical.astype(float)+130*reserve_need.astype(float)+95*values["target_deficit"]
               +55*values["deadline_deficit"]+35*(1-values["soc"])-10*values["laxity"])
        return pkg._select_cap_limited(env,values,eligible,score,rng,urgent_salience=True).astype(np.int64)
    def direct_driver(env,obs,rec,driver,rng,is_cheap):
        if driver!=DRIVER: return original_driver(env,obs,rec,driver,rng,is_cheap)
        values=pkg._arrays(env,obs); p_dev=structured_p_dev(ACTIVE_DEV,np.asarray(values["laxity"],float))
        if p_dev.shape[0]>0: DEV_ACC.append(float(p_dev.mean()))
        keep_prob=1-p_dev; keep=rng.random(env.n_cars)>=p_dev
        if MODE=="self_service":
            alt=severity_preference(env,obs,driver,rng,is_cheap)          # self-serving override
        else:  # benign: override motive removed -> deviating vehicles abstain (idle)
            alt=np.full(env.n_cars,pkg.PRIMITIVE_IDLE,dtype=np.int64)
        return np.where(keep,rec,alt).astype(np.int64),keep_prob,~keep,0
    mav2.apply_driver_layer=direct_driver

def run_cell(mav2,d,mode):
    global ACTIVE_DEV,MODE; ACTIVE_DEV=d; MODE=mode; DEV_ACC.clear()
    mav2.pkg.policy_actions=mav2._ORIG_POLICY_ACTIONS   # restore true original so install_policies re-captures it
    install(mav2)
    pols=["LeastLaxity"]+[f"D_{DRIVER}__F_ServiceFirst__G_{GRID_LABEL[g]}" for g in GRIDS]
    ex={p.name for p in mav2.POLICIES}
    for g in GRIDS:
        nm=f"D_{DRIVER}__F_ServiceFirst__G_{GRID_LABEL[g]}"
        if nm not in ex: mav2.POLICIES.append(mav2.MultiActorPolicy(nm,DRIVER,"FleetServiceFirst",g,f"{mode} {g}"))
    mav2.POLICY_BY_NAME={p.name:p for p in mav2.POLICIES}
    agg=mav2.run_matrix(SEEDS,CAPACITIES,pols); rows=pd.DataFrame(mav2.add_actor_scoring(agg["rows"]))
    rows=rows[rows.policy!="LeastLaxity"].copy()
    return float(rows["all_pass"].mean()), float(np.mean(DEV_ACC)) if DEV_ACC else 0.0

def main():
    OUT.mkdir(parents=True,exist_ok=True); mav2=import_runner(); mav2.set_output_dir(OUT/"runner_raw_inst")
    mav2.pkg.EPISODE_HOURS=EPISODE_HOURS; mav2._ORIG_DRIVER=mav2.apply_driver_layer
    mav2._ORIG_POLICY_ACTIONS=mav2.pkg.policy_actions
    recs=[]; start=time.time()
    for mode in ("self_service","benign"):
        for d in DEV_GRID:
            ap,dr=run_cell(mav2,d,mode)
            recs.append(dict(mode=mode,dev_target=d,dev_realized=round(dr,4),all_pass=round(ap,4)))
            print(f"{mode:12s} d={d:.3f} (realized {dr:.4f}) -> all_pass={ap:.4f}")
    df=pd.DataFrame(recs); df.to_csv(OUT/f"instrument_counterfactual_{DATE}.csv",index=False)
    print(f"\nwrote {len(df)} rows in {time.time()-start:.0f}s")
    piv=df.pivot(index="dev_target",columns="mode",values="all_pass")
    print("\n=== all-pass by deviation rate and deviation TYPE (35% cap) ===")
    print(piv.to_string())

if __name__=="__main__":
    main()
