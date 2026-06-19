#!/usr/bin/env python3
"""Reviewer Major-3: sensitivity of the severity-1 all-pass collapse to the FORM of the
non-compliant driver preference function (Eq. 3 coefficients 260/130/95/55/35/-10).

We hold severity-1 deviation prevalence fixed (5%, low-slack-structured = the realistic case)
and vary only the preference COEFFICIENTS across a reasonable family. If the collapse is
insensitive to the coefficient choice, the result depends on prevalence/placement, not on a
finely tuned non-compliant utility model (the modest claim the reviewer asks for).

Reuses the proven Option-A engine path; only the preference coefficients change.
"""
from __future__ import annotations
import importlib.util, math, sys, time
from pathlib import Path
from typing import Any
import numpy as np, pandas as pd

WORKSPACE = Path("/home/jia/thirfty death BRL DQN")
RUNNER = WORKSPACE / "scripts" / "run_multi_actor_v2_experiment.py"
OUT = Path("/home/jia/multi actor/equilibrium_optimization_20260616"); DATE="20260619"
SEEDS=[4541,4542,4543,4544,4545]; CAPACITIES=[35]; EPISODE_HOURS=168; TARGET_DEV=0.05
FLEETS=("FleetServiceFirst",); GRIDS=("NoGridIncentive","GridPeakPenalty")
FLEET_LABEL={"FleetServiceFirst":"ServiceFirst"}; GRID_LABEL={"NoGridIncentive":"NoGrid","GridPeakPenalty":"PeakPenalty"}
DRIVER="Severity1Mild"; DRVCFG={"reserve_margin":0.05,"cheap_extra_margin":0.10}

# Preference-coefficient variants: [critical, reserve, target_deficit, deadline_deficit, (1-soc), laxity]
VARIANTS = {
    "base":        [260,130, 95, 55, 35,-10],
    "equal":       [100,100,100,100,100,  0],   # removes the ordering entirely
    "plus50":      [390,195,142, 82, 52,-15],
    "minus50":     [130, 65, 47, 27, 17, -5],
    "reordered":   [ 55, 95,130,260, 35,-10],    # swap the priority ordering
    "no_reserve":  [260,  0, 95, 55, 35,-10],    # drop the reserve-seeking term
    "soc_heavy":   [120, 80, 80, 80,200, -5],    # weight low-SoC strongly instead
    "flat_urgent": [200,200, 50, 50, 20,  0],
}
ACTIVE = VARIANTS["base"]; DEV_ACC=[]

def import_runner():
    spec=importlib.util.spec_from_file_location("mav2_pref",RUNNER)
    mod=importlib.util.module_from_spec(spec); sys.modules["mav2_pref"]=mod; spec.loader.exec_module(mod); return mod

def structured_p_dev(d, laxity):
    lax=np.clip(np.asarray(laxity,float),0,1); n=lax.shape[0]
    if d<=0 or n==0: return np.zeros(n)
    w=1-lax; mw=float(w.mean())
    return np.full(n,d) if mw<=1e-9 else np.clip((d/mw)*w,0,1)

def install(mav2):
    pkg=mav2.pkg; original_driver=mav2._ORIG_DRIVER
    def severity_preference(env,obs,driver,rng,is_cheap):
        v=ACTIVE; values=pkg._arrays(env,obs); critical=pkg._service_critical(values)
        available=values["masks"][:,pkg.PRIMITIVE_NORMAL_REQUEST]; cheap=bool(is_cheap[int(env.t)%len(is_cheap)])
        rt=values["theta"]+float(DRVCFG["reserve_margin"])+(float(DRVCFG["cheap_extra_margin"]) if cheap else 0.0)
        reserve_need=values["soc"]<=rt; eligible=available&(critical|values["target"]|reserve_need)
        score=(v[0]*critical.astype(float)+v[1]*reserve_need.astype(float)+v[2]*values["target_deficit"]
               +v[3]*values["deadline_deficit"]+v[4]*(1.0-values["soc"])+v[5]*values["laxity"])
        return pkg._select_cap_limited(env,values,eligible,score,rng,urgent_salience=True).astype(np.int64)
    def direct_driver(env,obs,rec,driver,rng,is_cheap):
        if driver!=DRIVER: return original_driver(env,obs,rec,driver,rng,is_cheap)
        values=pkg._arrays(env,obs); p_dev=structured_p_dev(TARGET_DEV,np.asarray(values["laxity"],float))
        if p_dev.shape[0]>0: DEV_ACC.append(float(p_dev.mean()))
        keep_prob=1-p_dev; pref=severity_preference(env,obs,driver,rng,is_cheap)
        keep=rng.random(env.n_cars)>=p_dev; actual=np.where(keep,rec,pref).astype(np.int64)
        return actual,keep_prob,~keep,0
    mav2.apply_driver_layer=direct_driver
    specs=[]
    for fleet in FLEETS:
        for grid in GRIDS:
            name=f"D_{DRIVER}__F_{FLEET_LABEL[fleet]}__G_{GRID_LABEL[grid]}"
            specs.append(mav2.MultiActorPolicy(name,DRIVER,fleet,grid,f"pref-abl {fleet} {grid}"))
    ex={p.name for p in mav2.POLICIES}
    for s in specs:
        if s.name not in ex: mav2.POLICIES.append(s)
    mav2.POLICY_BY_NAME={p.name:p for p in mav2.POLICIES}

def policy_list():
    names=["LeastLaxity"]
    for fleet in FLEETS:
        for grid in GRIDS: names.append(f"D_{DRIVER}__F_{FLEET_LABEL[fleet]}__G_{GRID_LABEL[grid]}")
    return names

def run_variant(mav2,name,coeffs):
    global ACTIVE; ACTIVE=coeffs; DEV_ACC.clear()
    mav2.pkg.policy_actions=mav2._ORIG_POLICY_ACTIONS; install(mav2)
    agg=mav2.run_matrix(SEEDS,CAPACITIES,policy_list()); rows=pd.DataFrame(mav2.add_actor_scoring(agg["rows"]))
    rows=rows[rows.policy!="LeastLaxity"].copy(); rows["variant"]=name
    return rows

def main():
    OUT.mkdir(parents=True,exist_ok=True); mav2=import_runner(); mav2.set_output_dir(OUT/"runner_raw_pref")
    mav2.pkg.EPISODE_HOURS=EPISODE_HOURS; mav2._ORIG_DRIVER=mav2.apply_driver_layer; mav2._ORIG_POLICY_ACTIONS=mav2.pkg.policy_actions
    start=time.time(); allr=[]
    for name,co in VARIANTS.items():
        r=run_variant(mav2,name,co); ap=r["all_pass"].mean()
        allr.append(r); print(f"[{name:11}] coeffs={co} all_pass_sev1={ap:.3f} realized_dev={np.mean(DEV_ACC):.4f} t={time.time()-start:.0f}s",flush=True)
    df=pd.concat(allr,ignore_index=True); df.to_csv(OUT/f"preference_ablation_rows_{DATE}.csv",index=False)
    summ=df.groupby("variant")["all_pass"].mean().reset_index().rename(columns={"all_pass":"all_pass_sev1"})
    summ.to_csv(OUT/f"preference_ablation_summary_{DATE}.csv",index=False)
    print("\n=== SUMMARY: severity-1 all-pass by preference-coefficient variant (35% cap, ServiceFirst) ===")
    print(summ.to_string(index=False))
    print(f"\nmax all-pass across variants = {summ['all_pass_sev1'].max():.3f}  (collapse holds if all near 0)")
    print(f"Total wall time: {time.time()-start:.0f}s")

if __name__=="__main__": main()
