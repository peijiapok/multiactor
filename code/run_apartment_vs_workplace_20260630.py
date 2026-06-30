#!/usr/bin/env python3
"""Role-inversion test: does the FIRST-BINDING actor depend on the charging ecology?

Same multi-actor 14-gate framework, two real data-grounded scenarios already in the engine:
  * metro_caltech : workplace/campus (ACN-calibrated; morning arrivals, ~6.6h dwell)
  * metro_korea   : Korean apartment / multi-unit-dwelling charging (real apartment data:
                    579 households/building, 2.48 chargers/100 households, 40.5% with EVs>chargers)
                    -> residential, shared scarce chargers. Apartment shared charging IS a fleet
                    (a building/operator deferring across a constrained pool); 3 actors + 14 gates apply.

Hypothesis: workplace -> DRIVER gate binds first (our main result); apartment/overnight -> GRID
load-shape binds harder while driver may relax (large overnight slack) -> binding actor is
context-dependent. Scenario stress test (apartment behavioral layer = same assumed model), not
empirical validation of Korean apartment behavior.

Severity injected via the same structured-deviation driver override as the EDF/counterfactual runs.
"""
from __future__ import annotations
import importlib.util, sys, time
from pathlib import Path
import numpy as np, pandas as pd

WORKSPACE = Path("/home/jia/thirfty death BRL DQN")
RUNNER = WORKSPACE / "scripts" / "run_multi_actor_v2_experiment.py"
OUT = Path("/home/jia/multi actor/equilibrium_optimization_20260616"); DATE="20260630"
SEEDS=list(range(4541,4561)); CAP=35; EPISODE_HOURS=168   # 20-seed expansion (matches paper robustness standard)
GRIDS=("NoGridIncentive","GridPeakPenalty"); GLAB={"NoGridIncentive":"NoGrid","GridPeakPenalty":"PeakPenalty"}
DRVCFG={"reserve_margin":0.05,"cheap_extra_margin":0.10}
DEV_BY_DRIVER={"Sev0":0.0,"Sev1":0.05,"Sev2":0.20,"Sev3":0.45}   # full severity sweep: tests whether grid benefit survives falling compliance
SCENARIOS=[("caltech","metro_caltech_sce","campus/workplace"),
           ("korea","metro_korea","apartment/residential")]
DEV_ACC=[]

def import_runner():
    spec=importlib.util.spec_from_file_location("mav2_apt",RUNNER)
    mod=importlib.util.module_from_spec(spec); sys.modules["mav2_apt"]=mod; spec.loader.exec_module(mod); return mod

def structured_p_dev(d,laxity):
    lax=np.clip(np.asarray(laxity,float),0,1); n=lax.shape[0]
    if d<=0 or n==0: return np.zeros(n)
    w=1-lax; mw=float(w.mean())
    return np.full(n,d) if mw<=1e-9 else np.clip((d/mw)*w,0,1)

def install(mav2):
    pkg=mav2.pkg; original_driver=mav2._ORIG_DRIVER
    def severity_preference(env,obs,rng,is_cheap):
        v=pkg._arrays(env,obs); crit=pkg._service_critical(v)
        avail=v["masks"][:,pkg.PRIMITIVE_NORMAL_REQUEST]; cheap=bool(is_cheap[int(env.t)%len(is_cheap)])
        rt=v["theta"]+DRVCFG["reserve_margin"]+(DRVCFG["cheap_extra_margin"] if cheap else 0.0)
        rneed=v["soc"]<=rt; elig=avail&(crit|v["target"]|rneed)
        score=(260*crit.astype(float)+130*rneed.astype(float)+95*v["target_deficit"]
               +55*v["deadline_deficit"]+35*(1-v["soc"])-10*v["laxity"])
        return pkg._select_cap_limited(env,v,elig,score,rng,urgent_salience=True).astype(np.int64)
    def direct_driver(env,obs,rec,driver,rng,is_cheap):
        if driver not in DEV_BY_DRIVER: return original_driver(env,obs,rec,driver,rng,is_cheap)
        d=DEV_BY_DRIVER[driver]; v=pkg._arrays(env,obs)
        p_dev=structured_p_dev(d,np.asarray(v["laxity"],float))
        if p_dev.shape[0]>0: DEV_ACC.append(float(p_dev.mean()))
        keep=rng.random(env.n_cars)>=p_dev; pref=severity_preference(env,obs,rng,is_cheap)
        return np.where(keep,rec,pref).astype(np.int64),1-p_dev,~keep,0
    mav2.apply_driver_layer=direct_driver
    specs=[]
    for drv in DEV_BY_DRIVER:
        for g in GRIDS:
            specs.append(mav2.MultiActorPolicy(f"D_{drv}__F_ServiceFirst__G_{GLAB[g]}",drv,"FleetServiceFirst",g,f"{drv} {g}"))
    ex={p.name for p in mav2.POLICIES}
    for s in specs:
        if s.name not in ex: mav2.POLICIES.append(s)
        pkg.POLICY_SPECS[s.name]=pkg.BehaviorSpec("multi_actor")   # evaluate_run looks up .family here
    mav2.POLICY_BY_NAME={p.name:p for p in mav2.POLICIES}

def main():
    OUT.mkdir(parents=True,exist_ok=True); mav2=import_runner(); mav2.set_output_dir(OUT/"runner_raw_apt")
    mav2.pkg.EPISODE_HOURS=EPISODE_HOURS; mav2._ORIG_DRIVER=mav2.apply_driver_layer
    mav2.install_policies(); install(mav2)
    pols=["LeastLaxity"]+[f"D_{d}__F_ServiceFirst__G_{GLAB[g]}" for d in DEV_BY_DRIVER for g in GRIDS]
    recs=[]; start=time.time(); idx=0; total=len(SCENARIOS)*len(SEEDS)*len(pols)
    for slab,scenario,site in SCENARIOS:
        spec=mav2.pkg.make_spec(f"ma_apt_{slab}",scenario,site,"apartment-vs-workplace compare",CAP)
        rows=[]
        for seed in SEEDS:
            for pol in pols:
                idx+=1; print(f"[{idx}/{total}] {slab} seed={seed} {pol}",flush=True)
                rows.append(mav2.run_one(seed,spec,pol)["row"])
        rows=mav2.pkg.pair_with_least_laxity(rows)
        sc=pd.DataFrame(mav2.add_actor_scoring(rows))
        sc=sc[sc.policy!="LeastLaxity"].copy()
        sc["sev"]=sc.policy.map(lambda p: next((int(s[3]) for s in ("Sev0","Sev1","Sev2","Sev3") if s in p), -1))
        for sev,g in sc.groupby("sev"):
            recs.append(dict(scenario=slab,severity=int(sev),
                driver=round(g["driver_service_pass"].mean(),3),fleet=round(g["fleet_operation_pass"].mean(),3),
                grid=round(g["grid_pass"].mean(),3),all_pass=round(g["all_pass"].mean(),3),
                grid_peak=round(g.get("grid_peak_pass",pd.Series([np.nan])).mean(),3),
                grid_shape=round(g.get("grid_shape_pass",pd.Series([np.nan])).mean(),3),
                peak_to_avg=round(g.get("peak_to_average_ratio",pd.Series([np.nan])).mean(),3),
                reliability=round(g.get("reliability_pct",pd.Series([np.nan])).mean(),2),
                p95_wait=round(g.get("p95_wait_minutes",pd.Series([np.nan])).mean(),1)))
    df=pd.DataFrame(recs).sort_values(["scenario","severity"])
    df.to_csv(OUT/f"apartment_vs_workplace_{DATE}.csv",index=False)
    print(f"\nwrote {len(df)} rows in {time.time()-start:.0f}s\n"); print(df.to_string(index=False))
    print("\n=== FIRST-BINDING ACTOR (lowest-passing gate) ===")
    for _,r in df.iterrows():
        gates={"driver":r.driver,"fleet":r.fleet,"grid":r.grid}; b=min(gates,key=gates.get)
        print(f"  {r.scenario:8s} sev{r.severity}: driver={r.driver} fleet={r.fleet} grid={r.grid} -> {b.upper()} (all-pass {r.all_pass})")

if __name__=="__main__":
    main()
