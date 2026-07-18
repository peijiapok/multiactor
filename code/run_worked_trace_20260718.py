#!/usr/bin/env python3
"""Pull a REAL single-vehicle trace from the simulator for the worked example.
Baseline = full compliance; deviation = a fraction self-serve (grab charge out of turn,
the ReserveSeeking motive). Log every vehicle's SoC / recommended-vs-actual / delivered
per hour, plus the REAL episode all-pass for each, then save for plotting."""
from __future__ import annotations
import importlib.util, sys
from pathlib import Path
import numpy as np

RUNNER=Path("/home/jia/thirfty death BRL DQN/scripts/run_multi_actor_v2_experiment.py")
OUT=Path("/home/jia/multi actor/equilibrium_optimization_20260616")
SEED=4541; CAP=35; DEV=0.20   # deviation prevalence for clear, visible overriders
DRV="Severity1Mild"; DRVCFG={"reserve_margin":0.05,"cheap_extra_margin":0.10}

def imp():
    spec=importlib.util.spec_from_file_location("mav2_wt",RUNNER)
    m=importlib.util.module_from_spec(spec); sys.modules["mav2_wt"]=m; spec.loader.exec_module(m); return m

def structured_p_dev(d,lax):
    lax=np.clip(np.asarray(lax,float),0,1); n=lax.shape[0]
    if d<=0 or n==0: return np.zeros(n)
    w=1-lax; mw=float(w.mean())
    return np.full(n,d) if mw<=1e-9 else np.clip((d/mw)*w,0,1)

ACTIVE_DEV=0.0; MODE="comply"; DEV_ACC=[]
def install_override(mav2):
    pkg=mav2.pkg; orig=mav2._ORIG_DRIVER
    def severity_pref(env,obs,driver,rng,is_cheap):
        v=pkg._arrays(env,obs); crit=pkg._service_critical(v)
        avail=v["masks"][:,pkg.PRIMITIVE_NORMAL_REQUEST]; cheap=bool(is_cheap[int(env.t)%len(is_cheap)])
        rt=v["theta"]+DRVCFG["reserve_margin"]+(DRVCFG["cheap_extra_margin"] if cheap else 0.0)
        need=v["soc"]<=rt; elig=avail&(crit|v["target"]|need)
        score=(260*crit+130*need+95*v["target_deficit"]+55*v["deadline_deficit"]+35*(1-v["soc"])-10*v["laxity"])
        return pkg._select_cap_limited(env,v,elig,score,rng,urgent_salience=True).astype(np.int64)
    def driver(env,obs,rec,drv,rng,is_cheap):
        if drv!=DRV: return orig(env,obs,rec,drv,rng,is_cheap)
        v=pkg._arrays(env,obs); p=structured_p_dev(ACTIVE_DEV,v["laxity"])
        keep=rng.random(env.n_cars)>=p
        alt=severity_pref(env,obs,drv,rng,is_cheap) if MODE=="deviate" else rec
        act=np.where(keep,rec,alt).astype(np.int64)
        return act,1-p,~keep,0
    mav2.apply_driver_layer=driver

def logged_episode(mav2, policy, mode, dev):
    """Replicate evaluate_run's core loop, logging per-vehicle per-hour."""
    global ACTIVE_DEV,MODE; ACTIVE_DEV=dev; MODE=mode
    pkg=mav2.pkg
    sp=pkg.make_spec("multi_actor_v2_caltech_sce","metro_caltech_sce","campus/workplace","trace",CAP)
    cfg=pkg.run_config(SEED,sp); env=pkg.make_env(cfg,seed=SEED); obs=env.reset()
    rng=pkg.policy_rng(SEED,sp,policy); state=pkg.PolicyState()
    prices=np.asarray(env.price_schedule[:env.config.episode_hours],float)
    is_cheap=pkg.cheap_mask(prices, policy if policy in pkg.POLICY_SPECS else "TraitPriceHerdingT100")
    mav2.ACTIVE=("multi_actor_v2",SEED,CAP,policy)   # diag() context for multi_actor_actions
    T=int(env.config.episode_hours); N=env.n_cars
    soc=np.zeros((T,N)); rec_charge=np.zeros((T,N),bool); act_charge=np.zeros((T,N),bool)
    stored=np.zeros((T,N)); crit=np.zeros((T,N),bool); present=np.zeros((T,N),bool)
    t=0
    done=False
    while not done and t<T:
        v=pkg._arrays(env,obs)
        actions=pkg.policy_actions(env,obs,policy,rng,is_cheap,state)
        soc[t]=v["soc"]; present[t]=v["masks"][:,pkg.PRIMITIVE_NORMAL_REQUEST]
        crit[t]=v["masks"][:,pkg.PRIMITIVE_NORMAL_REQUEST]&pkg._service_critical(v)
        act_charge[t]=actions!=pkg.PRIMITIVE_IDLE
        obs,_,done,info=env.step(actions)
        st=np.asarray(getattr(env,"_last_charge_stored_actual_kwh",np.zeros(N)),float)
        stored[t]=st
        t+=1
    return dict(soc=soc[:t],act=act_charge[:t],stored=stored[:t],crit=crit[:t],present=present[:t],T=t,N=N)

def main():
    global ACTIVE_DEV,MODE
    mav2=imp(); pkg=mav2.pkg; mav2.set_output_dir(OUT/"runner_raw_trace")
    sp=pkg.make_spec("multi_actor_v2_caltech_sce","metro_caltech_sce","campus/workplace","trace",CAP)
    name_comply="D_FullyCompliant__F_ServiceFirst__G_NoGrid"
    name_dev=f"D_{DRV}__F_ServiceFirst__G_NoGrid_TRACE"
    if name_dev not in {p.name for p in mav2.POLICIES}:
        mav2.POLICIES.append(mav2.MultiActorPolicy(name_dev,DRV,"FleetServiceFirst","NoGridIncentive","trace deviate"))
    mav2.POLICY_BY_NAME={p.name:p for p in mav2.POLICIES}
    mav2.install_policies()                      # wraps policy_actions ONCE, registers POLICY_SPECS for all POLICIES
    mav2._ORIG_DRIVER=mav2.apply_driver_layer    # capture runner's real driver layer
    install_override(mav2)                        # set mav2.apply_driver_layer = our logging/deviation driver

    # --- real episode all-pass for each (via run_one); LeastLaxity anchor needed for scoring ---
    ACTIVE_DEV=0.0; MODE="comply"
    r_ll=mav2.run_one(SEED,sp,"LeastLaxity")
    r0=mav2.run_one(SEED,sp,name_comply)
    ACTIVE_DEV=DEV; MODE="deviate"
    r1=mav2.run_one(SEED,sp,name_dev)
    scored={row["policy"]:row for row in mav2.add_actor_scoring([r_ll["row"],r0["row"],r1["row"]])}
    ap0=scored[name_comply]; ap1=scored[name_dev]
    print(f"COMPLY  all_pass={ap0['all_pass']} driver={ap0['driver_service_pass']} op={ap0['fleet_operation_pass']} grid={ap0['grid_pass']}")
    print(f"DEVIATE all_pass={ap1['all_pass']} driver={ap1['driver_service_pass']} op={ap1['fleet_operation_pass']} grid={ap1['grid_pass']}")

    # --- logged per-vehicle traces (same seed -> same trajectories as run_one) ---
    A=logged_episode(mav2,name_comply,"comply",0.0)
    B=logged_episode(mav2,name_dev,"deviate",DEV)

    # cumulative delivered per vehicle
    cumA=A["stored"].cumsum(0); cumB=B["stored"].cumsum(0)
    # candidate OVERRIDER: charges much earlier under deviation (max early-SoC gain)
    early=slice(0,min(A["T"],48))
    gain=(B["soc"][early]-A["soc"][early]).mean(0)
    over=int(np.argsort(-gain)[:5][0]); overs=np.argsort(-gain)[:5]
    # candidate DISPLACED: served critical in comply but missed under deviate
    crit_missed_B=((B["crit"]&(B["stored"]<=1e-9)).sum(0))
    crit_missed_A=((A["crit"]&(A["stored"]<=1e-9)).sum(0))
    displaced_score=crit_missed_B-crit_missed_A
    disp=int(np.argsort(-displaced_score)[0]); disps=np.argsort(-displaced_score)[:5]
    print("\ntop overrider candidates (idx: early-SoC gain):", [(int(i),round(float(gain[i]),3)) for i in overs])
    print("top displaced candidates (idx: extra critical misses):", [(int(i),int(displaced_score[i])) for i in disps])

    np.savez(OUT/"worked_trace_20260718.npz",
             socA=A["soc"],socB=B["soc"],actA=A["act"],actB=B["act"],
             critA=A["crit"],critB=B["crit"],storedA=A["stored"],storedB=B["stored"],
             presentA=A["present"],presentB=B["present"],cumA=cumA,cumB=cumB,
             over=over,disp=disp,
             ap0=float(ap0["all_pass"]),ap1=float(ap1["all_pass"]),
             d0=float(ap0["driver_service_pass"]),d1=float(ap1["driver_service_pass"]),
             o0=float(ap0["fleet_operation_pass"]),o1=float(ap1["fleet_operation_pass"]),
             g0=float(ap0["grid_pass"]),g1=float(ap1["grid_pass"]))
    print(f"\nsaved worked_trace_20260718.npz  (overrider=#{over}, displaced=#{disp}, T={A['T']}, N={A['N']})")

if __name__=="__main__":
    main()
