#!/usr/bin/env python3
"""Equal-budget incentive comparison (the committee's "most persuasive" extension).

Question: given a FIXED incentive budget, does it matter WHERE the money goes?
We compare four allocation rules that all spend the same average transfer per
present vehicle b (so the budget is held equal across schemes), plus a revenue-
generating override fee, and measure joint all-pass feasibility.

Behavioral model (calibrated to the game-layer, NOT measured in the field):
  Each present vehicle i has an override probability p0_i (laxity-weighted, so
  urgent/low-slack drivers override more --- the same structured_p_dev used in the
  severity and instrument experiments). A transfer tau_i to driver i removes a
  fraction min(tau_i/kappa_i, 1) of that override motive, where kappa_i is the
  retention cost: urgent drivers cost MORE to retain (kappa rises with urgency).
  This is exactly the incentive-compatibility relation in the game section
  (follow iff transfer >= override benefit). Effective override:
      p_i = p0_i * (1 - min(tau_i/kappa_i, 1)).

Equal-budget allocation rules (all spend the same total b*N per timestep):
  none        : tau_i = 0                                  (baseline collapse)
  flat_tou    : tau_i = b                                  (uniform off-peak discount)
  slack       : tau_i proportional to slack (laxity)       (pays those who can wait)
  compliance  : tau_i proportional to urgency (1-laxity)   (pays likely deviators;
                                                            = compliance bonus / service guarantee)
  override_fee: budget-free deterrent; raises every driver's effective threshold by
                phi (funded by the deviators themselves), so it is NOT equal-budget ---
                reported separately to show the feasibility gain comes at driver-welfare cost.

The point is a mechanism-design one: under an equal budget, spending on the drivers
who would otherwise override (the binding incentive-compatibility constraint) buys
more joint feasibility than a flat discount or a slack discount that mostly pays
drivers who would have complied anyway. Same gates, same anchor, same engine path
as the EDF/uncoordinated/instrument baselines.
"""
from __future__ import annotations
import importlib.util, sys, time
from pathlib import Path
import numpy as np, pandas as pd

WORKSPACE = Path("/home/jia/thirfty death BRL DQN")
RUNNER = WORKSPACE / "scripts" / "run_multi_actor_v2_experiment.py"
OUT = Path("/home/jia/multi actor/equilibrium_optimization_20260616"); DATE="20260716"
SEEDS=[4541,4542,4543,4544,4545]; CAPACITIES=[35]; EPISODE_HOURS=168
DEV_TARGET=0.05                       # the collapse point (all-pass ~ 0 with no incentive)
BUDGETS=[0.0,0.02,0.05,0.10,0.15,0.20]  # average transfer per present vehicle (utility units)
KAPPA_MIN=0.05; KAPPA_SLOPE=0.15      # retention cost kappa_i = MIN + SLOPE*urgency  (0.05..0.20)
OVERRIDE_FEE_PHI=0.10                 # deterrent threshold add for the override-fee scheme
DRIVER="Severity1Mild"; DRVCFG={"reserve_margin":0.05,"cheap_extra_margin":0.10}
GRIDS=("NoGridIncentive","GridPeakPenalty"); GRID_LABEL={"NoGridIncentive":"NoGrid","GridPeakPenalty":"PeakPenalty"}
SCHEME="none"; BUDGET=0.0; DEV_ACC=[]

def import_runner():
    spec=importlib.util.spec_from_file_location("mav2_incent",RUNNER)
    mod=importlib.util.module_from_spec(spec); sys.modules["mav2_incent"]=mod; spec.loader.exec_module(mod); return mod

def structured_p_dev(d,laxity):
    lax=np.clip(np.asarray(laxity,float),0,1); n=lax.shape[0]
    if d<=0 or n==0: return np.zeros(n)
    w=1-lax; mw=float(w.mean())
    return np.full(n,d) if mw<=1e-9 else np.clip((d/mw)*w,0,1)

def allocate(scheme,budget,lax):
    """Return per-vehicle transfer tau_i with sum(tau)=budget*N (equal budget),
    except override_fee which returns zeros (handled via threshold)."""
    n=lax.shape[0]
    if n==0 or budget<=0 or scheme in ("none","override_fee"): return np.zeros(n)
    urg=1-lax
    if scheme=="flat_tou":   w=np.ones(n)
    elif scheme=="slack":    w=lax
    elif scheme=="compliance": w=urg
    else: w=np.ones(n)
    sw=float(w.sum())
    if sw<=1e-9: return np.full(n,budget)
    return budget*n*(w/sw)   # sum = budget*n

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
        values=pkg._arrays(env,obs); lax=np.asarray(values["laxity"],float)
        p0=structured_p_dev(DEV_TARGET,lax)
        urg=1-np.clip(lax,0,1); kappa=KAPPA_MIN+KAPPA_SLOPE*urg
        tau=allocate(SCHEME,BUDGET,np.clip(lax,0,1))
        retain=np.clip(tau/np.maximum(kappa,1e-9),0,1)
        if SCHEME=="override_fee" and BUDGET>0:   # deterrent: raise effective threshold for all
            retain=np.clip(OVERRIDE_FEE_PHI/np.maximum(kappa,1e-9),0,1)
        p_dev=p0*(1-retain)
        if p_dev.shape[0]>0: DEV_ACC.append(float(p_dev.mean()))
        keep_prob=1-p_dev; keep=rng.random(env.n_cars)>=p_dev
        alt=severity_preference(env,obs,driver,rng,is_cheap)   # self-serving override
        return np.where(keep,rec,alt).astype(np.int64),keep_prob,~keep,0
    mav2.apply_driver_layer=direct_driver

def run_cell(mav2,scheme,budget):
    global SCHEME,BUDGET; SCHEME=scheme; BUDGET=budget; DEV_ACC.clear()
    mav2.pkg.policy_actions=mav2._ORIG_POLICY_ACTIONS
    install(mav2)
    pols=["LeastLaxity"]+[f"D_{DRIVER}__F_ServiceFirst__G_{GRID_LABEL[g]}" for g in GRIDS]
    ex={p.name for p in mav2.POLICIES}
    for g in GRIDS:
        nm=f"D_{DRIVER}__F_ServiceFirst__G_{GRID_LABEL[g]}"
        if nm not in ex: mav2.POLICIES.append(mav2.MultiActorPolicy(nm,DRIVER,"FleetServiceFirst",g,f"{scheme} {g}"))
    mav2.POLICY_BY_NAME={p.name:p for p in mav2.POLICIES}
    agg=mav2.run_matrix(SEEDS,CAPACITIES,pols); rows=pd.DataFrame(mav2.add_actor_scoring(agg["rows"]))
    rows=rows[rows.policy!="LeastLaxity"].copy()
    return float(rows["all_pass"].mean()), float(np.mean(DEV_ACC)) if DEV_ACC else 0.0

def main():
    OUT.mkdir(parents=True,exist_ok=True); mav2=import_runner(); mav2.set_output_dir(OUT/"runner_raw_incent")
    mav2.pkg.EPISODE_HOURS=EPISODE_HOURS; mav2._ORIG_DRIVER=mav2.apply_driver_layer
    mav2._ORIG_POLICY_ACTIONS=mav2.pkg.policy_actions
    recs=[]; start=time.time()
    SCHEMES=["none","flat_tou","slack","compliance","override_fee"]
    for scheme in SCHEMES:
        for b in BUDGETS:
            if scheme=="none" and b>0: continue          # none is budget-independent
            ap,dr=run_cell(mav2,scheme,b)
            recs.append(dict(scheme=scheme,budget=b,dev_realized=round(dr,4),all_pass=round(ap,4)))
            print(f"{scheme:12s} b={b:.3f} realized_dev={dr:.4f} -> all_pass={ap:.4f}",flush=True)
    df=pd.DataFrame(recs); df.to_csv(OUT/f"incentive_comparison_{DATE}.csv",index=False)
    print(f"\nwrote {len(df)} rows in {time.time()-start:.0f}s")
    eqb=df[df.scheme!="override_fee"]
    piv=eqb.pivot_table(index="budget",columns="scheme",values="all_pass")
    print("\n=== all-pass by equal budget b and allocation scheme (dev=5%, 35% cap) ===")
    print(piv.to_string())
    print("\noverride_fee (revenue-generating, not equal-budget):")
    print(df[df.scheme=='override_fee'][['budget','all_pass','dev_realized']].to_string(index=False))

if __name__=="__main__":
    main()
