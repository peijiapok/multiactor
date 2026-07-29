#!/usr/bin/env python3
"""Information-integrity axis (second compliance axis).

The paper's baseline assumes drivers report TRUTHFUL deadlines/needs and only models ACTION-level
non-compliance (truth known, action ignored). This tests INFORMATION-level non-compliance: a share
of drivers MISREPORT urgency (claim false urgency to jump the shared-charger queue) while the gates
are scored against TRUE service. The scheduler (least-laxity) acts on the misreported priority; the
env's true state (used by the gates) is untouched.

Implementation: we re-implement the least-laxity charge selection (faithful to the engine's
_least_laxity_charge) but set laxity=-inf for misreporters (false urgency) and force them into the
served set, so they crowd out truly-urgent vehicles -> true critical service degrades -> driver gate
fails. Drivers are otherwise FULLY COMPLIANT (they follow the recommendation), isolating the
information axis from the action axis. Validation: at misreport rate 0 the result must reproduce the
truthful ServiceFirst baseline.
"""
from __future__ import annotations
import importlib.util, sys, time
from pathlib import Path
import numpy as np, pandas as pd

WORKSPACE = Path("/home/jia/thirfty death BRL DQN")
RUNNER = WORKSPACE / "scripts" / "run_multi_actor_v2_experiment.py"
OUT = Path("/home/jia/multi actor/equilibrium_optimization_20260616"); DATE="20260706"
SEEDS=list(range(4541,4561)); CAP=35; EPISODE_HOURS=168   # 20-seed expansion
RATES=[0.0,0.001,0.02,0.05,0.20,0.45]   # 0.0=orig scheduler (control); 0.001=replicated ~0 misreporters (faithfulness check); 0.02 to locate the cliff
GRIDS=("NoGridIncentive","GridPeakPenalty"); GLAB={"NoGridIncentive":"NoGrid","GridPeakPenalty":"PeakPenalty"}
POLS=["LeastLaxity","D_FullyCompliant__F_ServiceFirst__G_NoGrid","D_FullyCompliant__F_ServiceFirst__G_PeakPenalty"]
ACTIVE_RATE=0.0; MIS_SEED=0

def import_runner():
    spec=importlib.util.spec_from_file_location("mav2_info",RUNNER)
    mod=importlib.util.module_from_spec(spec); sys.modules["mav2_info"]=mod; spec.loader.exec_module(mod); return mod

def install(mav2):
    pkg=mav2.pkg; ORIG_FLEET=mav2._ORIG_FLEET
    from brl_dqn_v2.train_eval_v2 import _reserve_need,_target_need,_location_type
    def misreport_charge(env,obs):
        n=env.n_cars; soc=np.asarray(obs["soc"],float)
        masks=pkg.batch_action_mask(obs,n) if hasattr(pkg,"batch_action_mask") else pkg._arrays(env,obs)["masks"]
        avail=masks[:,pkg.PRIMITIVE_NORMAL_REQUEST]
        r=np.random.RandomState(MIS_SEED); mis=(r.random(n)<ACTIVE_RATE)&avail
        charge=np.zeros(n,bool); planned=getattr(env,"mandatory_trip_schedule",None); t=int(env.t)
        if planned is None:
            base=avail & _reserve_need(env,obs); base[mis]=True; return base
        laxity=np.full(n,np.inf)
        for i in range(n):
            if not avail[i] or (hasattr(env,"agent_queuing") and bool(env.agent_queuing[i])): continue
            future=np.asarray(planned[i,t:env.config.episode_hours],float); nz=np.flatnonzero(future>0.0)
            if nz.size==0: laxity[i]=1.0e6+max(0.0,float(getattr(env.config,"target_soc",0.90))-soc[i]); continue
            htd=float(nz[0]); trip=float(future[nz[0]])*0.18
            usable=max(0.0,soc[i]-float(env.config.soc_min))*float(env.config.bcap_kwh)
            deficit=max(0.0,trip-usable); lt=_location_type(env,i)
            if lt is None: continue
            cp=max(float(env._get_charge_power(lt)),1.0e-9); laxity[i]=htd-deficit/cp
        laxity[mis]=-1.0e9                                  # misreporters claim maximal (false) urgency
        need=(avail & _target_need(env,obs))|mis; reserve=(avail & _reserve_need(env,obs))|mis
        for lt in ("home","work","public"):
            members=np.array([i for i in np.where(need)[0] if _location_type(env,int(i))==lt],int)
            if members.size==0: continue
            queued=len(getattr(env,"charger_queues",{}).get(lt,[])); remaining=max(0,int(env.n_slots[lt])-int(queued))
            if remaining<=0: continue
            rm=members[reserve[members]]; om=members[~reserve[members]]
            sel=np.concatenate([rm[np.argsort(laxity[rm])],om[np.argsort(laxity[om])]])[:remaining]
            charge[sel]=True
        return charge
    def fleet_override(env,obs,fleet,rng,is_cheap):
        if fleet=="FleetServiceFirst" and ACTIVE_RATE>0:
            return np.where(misreport_charge(env,obs),pkg.PRIMITIVE_NORMAL_REQUEST,pkg.PRIMITIVE_IDLE).astype(np.int64)
        return ORIG_FLEET(env,obs,fleet,rng,is_cheap)
    mav2.fleet_recommendation=fleet_override

def main():
    OUT.mkdir(parents=True,exist_ok=True); mav2=import_runner(); mav2.set_output_dir(OUT/"runner_raw_info")
    mav2.pkg.EPISODE_HOURS=EPISODE_HOURS; mav2._ORIG_FLEET=mav2.fleet_recommendation
    mav2.install_policies(); install(mav2)
    spec=mav2.pkg.make_spec("ma_info","metro_caltech_sce","campus/workplace","information-integrity sweep",CAP)
    global ACTIVE_RATE,MIS_SEED
    recs=[]; start=time.time(); idx=0; total=len(RATES)*len(SEEDS)*len(POLS)
    for rate in RATES:
        rows=[]
        for seed in SEEDS:
            MIS_SEED=seed
            for pol in POLS:
                ACTIVE_RATE=0.0 if pol=="LeastLaxity" else rate   # clean anchor
                idx+=1; print(f"[{idx}/{total}] rate={rate} seed={seed} {pol}",flush=True)
                rows.append(mav2.run_one(seed,spec,pol)["row"])
        rows=mav2.pkg.pair_with_least_laxity(rows)
        sc=pd.DataFrame(mav2.add_actor_scoring(rows)); sc=sc[sc.policy!="LeastLaxity"]
        recs.append(dict(misreport_rate=rate,
            driver=round(sc["driver_service_pass"].mean(),3),fleet=round(sc["fleet_operation_pass"].mean(),3),
            grid=round(sc["grid_pass"].mean(),3),all_pass=round(sc["all_pass"].mean(),3),
            reliability=round(sc.get("reliability_pct",pd.Series([np.nan])).mean(),2),
            p95_wait=round(sc.get("p95_wait_minutes",pd.Series([np.nan])).mean(),1)))
    df=pd.DataFrame(recs); df.to_csv(OUT/f"information_integrity_{DATE}.csv",index=False)
    print(f"\nwrote {len(df)} rows in {time.time()-start:.0f}s\n"); print(df.to_string(index=False))
    print("\nSANITY: rate 0.0 all-pass should match truthful ServiceFirst baseline (~0.97 at sev0-equiv full compliance).")

if __name__=="__main__":
    main()
