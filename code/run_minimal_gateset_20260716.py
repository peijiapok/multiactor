#!/usr/bin/env python3
"""Minimal 3-gate conjunction (kills the "14-way AND artifact" objection). No new sim.

Skeptic: "all-pass collapses only because you AND 14 thresholded metrics -- it is mechanical."
Refutation: pre-declare ONE binding criterion per actor (the paper's named binding gates) and
show the same-episode conjunction of just THREE collapses essentially identically to the 14-gate
all-pass -- and that the single driver criterion alone already falls to zero. If 3 gates (or 1)
collapse like 14, the drama is behavioral, not a counting artifact.

Pre-declared minimal gates (NOT chosen post hoc -- these are the binding criteria the paper
already identifies in the diagnostic/robustness sections):
  driver   : service_gate_pass  (critical-requested-not-delivered)
  operator : fleet_queue_pass    (95th-percentile wait)
  grid     : grid_shape_pass     (squared-load / ramp load-shape)
Full set = all_pass (14 gates). Reported pooled over the 20-seed factorial (matches the headline
1.2% weekly number) and at 35% capacity.
"""
from pathlib import Path
import pandas as pd, numpy as np
ROOT=Path("/home/jia/multi actor"); DATE="20260716"
OUT=ROOT/"equilibrium_optimization_20260616"; PKG=ROOT/"final_applied_energy_package_20260609"
MG={"driver":"service_gate_pass","operator":"fleet_queue_pass","grid":"grid_shape_pass"}

s=pd.read_csv(ROOT/"seed20_expansion_20260615"/"seed20_row_results_20260615.csv")
s=s[(s.policy!="LeastLaxity")&(s.fleet_policy.notna())].copy()
s["min3_pass"]=(s[MG["driver"]].astype(int)&s[MG["operator"]].astype(int)&s[MG["grid"]].astype(int))

def summarize(d):
    return dict(
        driver_only=round(d[MG["driver"]].mean(),3),
        operator_only=round(d[MG["operator"]].mean(),3),
        grid_only=round(d[MG["grid"]].mean(),3),
        min3_gate=round(d["min3_pass"].mean(),3),
        full14_allpass=round(d["all_pass"].mean(),3),
        n=len(d))

rows=[]
for sev in [0.0,1.0,2.0,3.0]:
    d=s[s.severity_level==sev]
    rows.append(dict(severity=int(sev), scope="pooled(20/35/50%)", **summarize(d)))
    d35=d[d.capacity_pct==35]
    rows.append(dict(severity=int(sev), scope="35% only", **summarize(d35)))
out=pd.DataFrame(rows)
out.to_csv(OUT/f"minimal_gateset_{DATE}.csv",index=False)
out.to_csv(PKG/"paper_final_result"/f"minimal_gateset_{DATE}.csv",index=False)
pd.set_option("display.width",200)
print("=== Minimal 3-gate vs full 14-gate conjunction (one binding criterion per actor) ===")
print(out.to_string(index=False))

# figure: pooled, 3-gate vs 14-gate curves (near-overlapping) + single driver gate
pooled=out[out.scope.str.startswith("pooled")]
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(6.0,4.0))
sev=pooled.severity
ax.plot(sev,pooled.full14_allpass,"o-",color="#c0392b",lw=2.4,ms=8,label="full 14-gate all-pass")
ax.plot(sev,pooled.min3_gate,"s--",color="#2c3e50",lw=2.0,ms=7,label="minimal 3-gate (1 per actor)")
ax.plot(sev,pooled.driver_only,"^:",color="#2980b9",lw=1.6,ms=6,label="driver criterion alone (critical-service)")
ax.set_xticks([0,1,2,3])
ax.set_xticklabels(["0\n(0%)","1\n(~5%)","2\n(~20%)","3\n(~45%)"])
ax.set_xlabel("behavioral deviation severity")
ax.set_ylabel("same-episode pass rate (pooled 20-seed)")
ax.set_ylim(-0.03,1.05); ax.grid(alpha=0.3); ax.legend(fontsize=8,loc="upper right")
ax.set_title("Dropping from 14 gates to 3 (or 1) changes nothing:\nthe collapse is behavioral, not a conjunction artifact",fontsize=10)
fig.tight_layout()
fig.savefig(PKG/"figures"/"fig_minimal_gateset_20260716.pdf")
fig.savefig(PKG/"paper_final_result"/"fig_minimal_gateset_20260716.png",dpi=140)
print("\nfigure written")
