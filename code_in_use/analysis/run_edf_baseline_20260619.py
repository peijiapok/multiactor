#!/usr/bin/env python3
"""Reviewer-3 #2: is the compliance collapse a property of LeastLaxity specifically, or of
behavioral non-compliance under ANY competent scheduler? We re-run the severity sweep with a
second, recognized real-time scheduler -- Earliest-Deadline-First (EDF), the canonical
deadline-driven rule and the family the ACN adaptive scheduler belongs to -- in place of the
LeastLaxity-based ServiceFirst fleet policy, and check whether all-pass still collapses.
Same driver/severity layer, same gates. Reuses the proven Option-A engine path."""
from __future__ import annotations
import importlib.util, sys, time
from pathlib import Path
from typing import Any
import numpy as np, pandas as pd

WORKSPACE = Path("/home/jia/thirfty death BRL DQN")
RUNNER = WORKSPACE / "scripts" / "run_multi_actor_v2_experiment.py"
OUT = Path("/home/jia/multi actor/equilibrium_optimization_20260616"); DATE="20260619"
SEEDS=[4541,4542,4543,4544,4545]; CAPACITIES=[35]; EPISODE_HOURS=168
DEV_GRID=[0.0,0.0125,0.025,0.05]           # full-compliance -> below/at the cliff
DRIVER="Severity1Mild"; DRVCFG={"reserve_margin":0.05,"cheap_extra_margin":0.10}
GRIDS=("NoGridIncentive","GridPeakPenalty"); GRID_LABEL={"NoGridIncentive":"NoGrid","GridPeakPenalty":"PeakPenalty"}
ACTIVE_DEV=0.0; DEV_ACC=[]

def import_runner():
    spec=importlib.util.spec_from_file_location("mav2_edf",RUNNER)
    mod=importlib.util.module_from_spec(spec); sys.modules["mav2_edf"]=mod; spec.loader.exec_module(mod); return mod

def structured_p_dev(d,laxity):
    lax=np.clip(np.asarray(laxity,float),0,1); n=lax.shape[0]
    if d<=0 or n==0: return np.zeros(n)
    w=1-lax; mw=float(w.mean())
    return np.full(n,d) if mw<=1e-9 else np.clip((d/mw)*w,0,1)

def install(mav2, edf_actions):
    pkg=mav2.pkg; original_driver=mav2._ORIG_DRIVER
    def edf_fleet(env,obs,fleet,rng,is_cheap):
        return edf_actions(env,obs)            # EDF recommendation for the FleetEDF policy
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
    mav2.fleet_recommendation=edf_fleet; mav2.apply_driver_layer=direct_driver
    specs=[]
    for grid in GRIDS:
        name=f"D_{DRIVER}__F_EDF__G_{GRID_LABEL[grid]}"
        specs.append(mav2.MultiActorPolicy(name,DRIVER,"FleetServiceFirst",grid,f"EDF baseline {grid}"))
    ex={p.name for p in mav2.POLICIES}
    for s in specs:
        if s.name not in ex: mav2.POLICIES.append(s)
    mav2.POLICY_BY_NAME={p.name:p for p in mav2.POLICIES}

def policy_list():
    return ["LeastLaxity"]+[f"D_{DRIVER}__F_EDF__G_{GRID_LABEL[g]}" for g in GRIDS]

def run_dev(mav2,d,edf_actions):
    global ACTIVE_DEV; ACTIVE_DEV=d; DEV_ACC.clear()
    mav2.pkg.policy_actions=mav2._ORIG_POLICY_ACTIONS; install(mav2,edf_actions)
    agg=mav2.run_matrix(SEEDS,CAPACITIES,policy_list()); rows=pd.DataFrame(mav2.add_actor_scoring(agg["rows"]))
    rows=rows[rows.policy!="LeastLaxity"].copy(); rows["dev_target"]=d
    rows["dev_realized"]=float(np.mean(DEV_ACC)) if DEV_ACC else 0.0
    return rows

def main():
    OUT.mkdir(parents=True,exist_ok=True); mav2=import_runner(); mav2.set_output_dir(OUT/"runner_raw_edf")
    mav2.pkg.EPISODE_HOURS=EPISODE_HOURS; mav2._ORIG_DRIVER=mav2.apply_driver_layer; mav2._ORIG_POLICY_ACTIONS=mav2.pkg.policy_actions
    # import EDF scheduler
    sys.path.insert(0,str(WORKSPACE/"scripts"))
    from run_ll_guarded_residual_calibration import edf_actions
    start=time.time(); allr=[]
    for d in DEV_GRID:
        r=run_dev(mav2,d,edf_actions); ap=r["all_pass"].mean()
        allr.append(r); print(f"[EDF d={d:.4f}] all_pass={ap:.3f} realized_dev={r['dev_realized'].iloc[0]:.4f} t={time.time()-start:.0f}s",flush=True)
    df=pd.concat(allr,ignore_index=True); df.to_csv(OUT/f"edf_baseline_rows_{DATE}.csv",index=False)
    summ=df.groupby('dev_realized')['all_pass'].mean().reset_index()
    print("\n=== EDF scheduler: all-pass vs deviation (35% cap, both grids, 5 seeds) ===")
    print(summ.round(3).to_string(index=False))
    print(f"\nFull compliance all_pass={summ.iloc[0].all_pass:.3f}; collapses to {summ.iloc[-1].all_pass:.3f} by d={summ.iloc[-1].dev_realized:.3f}")
    print(f"Total wall time: {time.time()-start:.0f}s")

if __name__=="__main__": main()
