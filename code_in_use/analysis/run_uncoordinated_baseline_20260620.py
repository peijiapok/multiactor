#!/usr/bin/env python3
"""Reviewer-6 #1 (context baseline): apply the multi-actor framework to the
UNCOORDINATED / immediate-charging policy -- the universal "business-as-usual"
reference in the EV-charging literature (charge every vehicle as soon as a charger
is physically available, with no deferral, prioritization, or deadline ordering).

Purpose: show the framework is not arbitrarily rejecting sophisticated schedulers.
The uncoordinated baseline maximizes immediate energy delivery (a single 'service'
metric) but, lacking any load-shaping or queue management, should fail the grid
load-shape and/or fleet waiting gates -- so it too fails the same-episode
conjunction. This complements the EDF published-scheduler stress test.

Same gates, same anchor (LeastLaxity), same driver layer. Reuses the engine path
used for the EDF baseline; no change to the simulator core. Full compliance plus
severity 1, 35% capacity, both grid policies, five seeds.
"""
from __future__ import annotations
import importlib.util, sys, time
from pathlib import Path
from typing import Any
import numpy as np, pandas as pd

WORKSPACE = Path("/home/jia/thirfty death BRL DQN")
RUNNER = WORKSPACE / "scripts" / "run_multi_actor_v2_experiment.py"
OUT = Path("/home/jia/multi actor/equilibrium_optimization_20260616"); DATE="20260620"
SEEDS=[4541,4542,4543,4544,4545]; CAPACITIES=[35]; EPISODE_HOURS=168
DEV_GRID=[0.0,0.05]                         # full compliance and severity-1
DRIVER="Severity1Mild"; DRVCFG={"reserve_margin":0.05,"cheap_extra_margin":0.10}
GRIDS=("NoGridIncentive","GridPeakPenalty"); GRID_LABEL={"NoGridIncentive":"NoGrid","GridPeakPenalty":"PeakPenalty"}
ACTIVE_DEV=0.0; DEV_ACC=[]

def import_runner():
    spec=importlib.util.spec_from_file_location("mav2_unc",RUNNER)
    mod=importlib.util.module_from_spec(spec); sys.modules["mav2_unc"]=mod; spec.loader.exec_module(mod); return mod

def structured_p_dev(d,laxity):
    lax=np.clip(np.asarray(laxity,float),0,1); n=lax.shape[0]
    if d<=0 or n==0: return np.zeros(n)
    w=1-lax; mw=float(w.mean())
    return np.full(n,d) if mw<=1e-9 else np.clip((d/mw)*w,0,1)

def install(mav2):
    pkg=mav2.pkg; original_driver=mav2._ORIG_DRIVER
    def uncoordinated_fleet(env,obs,fleet,rng,is_cheap):
        # Immediate charging: every vehicle that CAN request charging does so now.
        values=pkg._arrays(env,obs)
        available=values["masks"][:,pkg.PRIMITIVE_NORMAL_REQUEST]
        actions=np.where(available,pkg.PRIMITIVE_NORMAL_REQUEST,pkg.PRIMITIVE_IDLE)
        return actions.astype(np.int64)
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
        keep_prob=1-p_dev; pref=severity_preference(env,obs,driver,rng,is_cheap)
        keep=rng.random(env.n_cars)>=p_dev; return np.where(keep,rec,pref).astype(np.int64),keep_prob,~keep,0
    mav2.fleet_recommendation=uncoordinated_fleet; mav2.apply_driver_layer=direct_driver
    specs=[]
    for grid in GRIDS:
        name=f"D_{DRIVER}__F_Uncoordinated__G_{GRID_LABEL[grid]}"
        specs.append(mav2.MultiActorPolicy(name,DRIVER,"FleetServiceFirst",grid,f"Uncoordinated immediate-charging baseline {grid}"))
    ex={p.name for p in mav2.POLICIES}
    for s in specs:
        if s.name not in ex: mav2.POLICIES.append(s)
    mav2.POLICY_BY_NAME={p.name:p for p in mav2.POLICIES}

def policy_list():
    return ["LeastLaxity"]+[f"D_{DRIVER}__F_Uncoordinated__G_{GRID_LABEL[g]}" for g in GRIDS]

def run_dev(mav2,d):
    global ACTIVE_DEV; ACTIVE_DEV=d; DEV_ACC.clear()
    mav2.pkg.policy_actions=mav2._ORIG_POLICY_ACTIONS; install(mav2)
    agg=mav2.run_matrix(SEEDS,CAPACITIES,policy_list()); rows=pd.DataFrame(mav2.add_actor_scoring(agg["rows"]))
    rows=rows[rows.policy!="LeastLaxity"].copy(); rows["dev_target"]=d
    rows["dev_realized"]=float(np.mean(DEV_ACC)) if DEV_ACC else 0.0
    return rows

def main():
    OUT.mkdir(parents=True,exist_ok=True); mav2=import_runner(); mav2.set_output_dir(OUT/"runner_raw_unc")
    mav2.pkg.EPISODE_HOURS=EPISODE_HOURS; mav2._ORIG_DRIVER=mav2.apply_driver_layer; mav2._ORIG_POLICY_ACTIONS=mav2.pkg.policy_actions
    start=time.time(); allr=[]
    for d in DEV_GRID:
        r=run_dev(mav2,d); ap=r["all_pass"].mean()
        print(f"dev={d:.3f} dev_realized={r['dev_realized'].iloc[0]:.4f}  "
              f"driver={r['driver_service_pass'].mean():.3f} fleet={r['fleet_operation_pass'].mean():.3f} "
              f"grid={r['grid_pass'].mean():.3f} all_pass={ap:.3f}  "
              f"reliability={r['reliability_pct'].mean():.2f} p95wait={r['p95_wait_minutes'].mean():.1f}")
        allr.append(r)
    out=pd.concat(allr,ignore_index=True)
    out.to_csv(OUT/f"uncoordinated_baseline_rows_{DATE}.csv",index=False)
    print(f"\nwrote {len(out)} rows in {time.time()-start:.0f}s -> uncoordinated_baseline_rows_{DATE}.csv")

if __name__=="__main__":
    main()
