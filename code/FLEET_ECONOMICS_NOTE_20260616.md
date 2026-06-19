# Fleet-economics robustness (user question: "fleet cares about money") — 2026-06-16

USER POINT: a fleet operator cares most about earnings, but our U_F is service+waiting, not money.
DISCUSSED with GPT-5.5 (agreed) + data analysis.

KEY DATA (35% cap, response surface): as driver deviation rises,
- delivered energy (revenue proxy) FALLS ~4%
- energy cost FALLS ~5% (offsets), demand charge FLAT, p95 wait BLOWS UP (0->90 min)
=> a profit=revenue-cost objective is near-neutral / mildly REWARDS deviation (cost offset),
   while service/availability degrades sharply.

FINDING (fleet_profit_robustness_20260616.py): price of anarchy under
- service U_F (main): 1.48/1.46/1.48 at 20/35/50%
- profit-weighted U_F: 1.29/1.05/1.33  <- WEAKENS via cost-offset

INTERPRETATION (honest): the fleet's economic harm from deviation runs through SERVICE/AVAILABILITY
(missed trips = lost revenue), NOT energy cost. The profit objective is uninformative here for two
SIM reasons: (1) synthetic-scale cost units, (2) demand charge insensitive to deviation. Both
UNDERSTATE real fleet cost exposure -- in deployment, uncoordinated charging RAISES demand charges
(fleet's biggest cost), which would STRENGTHEN the fleet's exposure. So we model fleet on the
service/revenue channel and keep cost in the fleet gate; the profit variant is a check that the
result is not an artifact of excluding costs.

MANUSCRIPT CHANGES: reframed U_F as service/revenue proxy (Methods); added "Fleet economics: why
service, not energy cost" paragraph (game results) reporting PoA weakening honestly; supplement
Fig fig:eqfleet (revenue & cost fall together, service degrades); demand-charge limitation added.
Compiles 43pp, 0 undefined. Aligned with GPT-5.5 guidance ("frame main welfare loss as
reliability/service revenue rather than total operating profit; add explicit profit robustness check").
