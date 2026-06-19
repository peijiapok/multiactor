# Verified Literature Grounding Report - 20260609

This table verifies the references intended for the Applied Energy manuscript. No guessed DOI is used. Non-peer-reviewed sources are labeled as such and are used only for journal scope or software documentation, not for empirical claims.

Verified records: 18.

## Category coverage

- Applied Energy journal fit: 1 record(s)
- Applied Energy precedent; QoS-cost trade-off: 1 record(s)
- Coordinated EV charging: 2 record(s)
- Charging strategy baseline: 1 record(s)
- Charging networks and practical control: 1 record(s)
- Simulation and reproducibility: 1 record(s)
- Managed charging acceptance: 2 record(s)
- Behavior and smart charging field response: 1 record(s)
- Managed charging perceptions: 1 record(s)
- Acceptance value in energy systems: 1 record(s)
- EV charging QoS and fairness: 1 record(s)
- Distribution feeder EV impacts: 2 record(s)
- IEEE-33 benchmark provenance: 1 record(s)
- Power-flow software: 1 record(s)
- Power-flow software documentation: 1 record(s)

## Reference-to-claim map

### R1. Applied Energy - Aims and scope
- Authors/year: Elsevier (2026)
- Source: ScienceDirect journal page
- DOI: none
- URL: https://www.sciencedirect.com/journal/applied-energy
- Peer-reviewed: No - journal information page
- Supports: Applied Energy fit requires an energy-systems framing rather than a controller-debug story.
- Limitation: Journal page, not peer-reviewed evidence.
- Verification: ScienceDirect search result, 2026-06-09.

### R2. Pareto optimality in cost and service quality for an Electric Vehicle charging facility
- Authors/year: Soomin Woo; Sangjae Bae; Scott J. Moura (2021)
- Source: Applied Energy 290, 116779
- DOI: 10.1016/j.apenergy.2021.116779
- URL: https://doi.org/10.1016/j.apenergy.2021.116779
- Peer-reviewed: Yes
- Supports: Applied Energy precedent for explicit cost-service quality trade-offs in EV charging facilities.
- Limitation: Facility planning paper, not multi-actor behavioral simulation.
- Verification: ScienceDirect and Berkeley ITS records.

### R3. Decentralized Charging Control of Large Populations of Plug-in Electric Vehicles
- Authors/year: Zhongjing Ma; Duncan S. Callaway; Ian A. Hiskens (2013)
- Source: IEEE Transactions on Control Systems Technology 21(1), 67-78
- DOI: 10.1109/TCST.2011.2174059
- URL: https://doi.org/10.1109/TCST.2011.2174059
- Peer-reviewed: Yes
- Supports: Coordinated EV charging can be formulated as a distributed control problem coupled through aggregate system signals.
- Limitation: Assumes rational response to coordination signals; not an acceptance-gate framework.
- Verification: CoLab DOI record.

### R4. Optimal decentralized protocol for electric vehicle charging
- Authors/year: Lingwen Gan; Ufuk Topcu; Steven H. Low (2013)
- Source: IEEE Transactions on Power Systems 28(2), 940-951
- DOI: 10.1109/TPWRS.2012.2210288
- URL: https://doi.org/10.1109/TPWRS.2012.2210288
- Peer-reviewed: Yes
- Supports: Valley-filling and decentralized charging protocols motivate grid-aware EV control baselines.
- Limitation: Optimization setting differs from this paper's simulation-gate evaluation.
- Verification: Caltech Authors and DOI search records.

### R5. Optimal Charging Strategies for Unidirectional Vehicle-to-Grid
- Authors/year: Eric Sortomme; Mohamed A. El-Sharkawi (2011)
- Source: IEEE Transactions on Smart Grid 2(1), 131-138
- DOI: 10.1109/TSG.2010.2090910
- URL: https://doi.org/10.1109/TSG.2010.2090910
- Peer-reviewed: Yes
- Supports: Charging control literature commonly balances charging requirements and grid-side objectives.
- Limitation: V1G scheduling setting, not multi-actor gates.
- Verification: DOI search records.

### R6. Adaptive Charging Networks: A Framework for Smart Electric Vehicle Charging
- Authors/year: Zachary J. Lee; George S. Lee; Ted Lee; Cheng Jin; Rand Lee; Zhi Low; Daniel Chang; Christine Ortega; Steven H. Low (2021)
- Source: IEEE Transactions on Smart Grid 12(5), 4339-4350
- DOI: 10.1109/TSG.2021.3074437
- URL: https://doi.org/10.1109/TSG.2021.3074437
- Peer-reviewed: Yes
- Supports: Real charging networks combine service, infrastructure constraints, control signals, and practical deployment complications.
- Limitation: Field-network framework with different data and objectives.
- Verification: NSF Public Access Repository and Semantic Scholar DOI records.

### R7. ACN-Sim: An Open-Source Simulator for Data-Driven Electric Vehicle Charging Research
- Authors/year: Zachary J. Lee; Sunash Sharma; Daniel Johansson; Steven H. Low (2019)
- Source: IEEE SmartGridComm
- DOI: 10.1109/SmartGridComm.2019.8909765
- URL: https://doi.org/10.1109/SmartGridComm.2019.8909765
- Peer-reviewed: Yes - conference
- Supports: EV charging simulation studies need transparent assumptions, modular traces, and reproducible evaluation.
- Limitation: Simulator precedent, not evidence for this simulator's behavioral models.
- Verification: NSF Public Access Repository and arXiv metadata.

### R8. Understanding user acceptance factors of electric vehicle smart charging
- Authors/year: Christian Will; Alexander Schuller (2016)
- Source: Transportation Research Part C 71, 198-214
- DOI: 10.1016/j.trc.2016.07.006
- URL: https://doi.org/10.1016/j.trc.2016.07.006
- Peer-reviewed: Yes
- Supports: Smart-charging success depends on user acceptance and perceived control, reliability, and inconvenience.
- Limitation: Acceptance study, not calibration for this simulator.
- Verification: KITopen/TRID records.

### R9. Anticipating PEV buyers' acceptance of utility controlled charging
- Authors/year: Joseph Bailey; Jonn Axsen (2015)
- Source: Transportation Research Part A 82, 29-46
- DOI: 10.1016/j.tra.2015.09.004
- URL: https://doi.org/10.1016/j.tra.2015.09.004
- Peer-reviewed: Yes
- Supports: Drivers differ in acceptance of utility-controlled charging and value cost savings, renewables, privacy, and control differently.
- Limitation: Stated-preference sample, not operational fleet simulation.
- Verification: ScienceDirect record.

### R10. User responses to a smart charging system in Germany: Battery electric vehicle driver motivation, attitudes and acceptance
- Authors/year: Nina Schmalfuss; Karoline Muhl; Josef F. Krems (2015)
- Source: Energy Research & Social Science 9, 60-71
- DOI: 10.1016/j.erss.2015.08.019
- URL: https://doi.org/10.1016/j.erss.2015.08.019
- Peer-reviewed: Yes
- Supports: Observed smart-charging participation can depend on trust, reliability, and daily-life integration.
- Limitation: Small field trial; does not calibrate this paper's severity levels.
- Verification: ScienceDirect record.

### R11. What do consumers think of smart charging? Perceptions among actual and potential plug-in electric vehicle adopters in the United Kingdom
- Authors/year: Emma Delmonte; Neale Kinnear; Becca Jenkins; Stephen Skippon (2020)
- Source: Energy Research & Social Science 60, 101318
- DOI: 10.1016/j.erss.2019.101318
- URL: https://doi.org/10.1016/j.erss.2019.101318
- Peer-reviewed: Yes
- Supports: Smart charging acceptance includes social benefit, inconvenience, and control perceptions.
- Limitation: Survey/perception evidence, not operational acceptance gates.
- Verification: CoLab DOI record.

### R12. The value of consumer acceptance of controlled electric vehicle charging in a decarbonizing grid: The case of California
- Authors/year: Brian Tarroja; Eric Hittinger (2021)
- Source: Energy 229, 120691
- DOI: 10.1016/j.energy.2021.120691
- URL: https://doi.org/10.1016/j.energy.2021.120691
- Peer-reviewed: Yes
- Supports: Acceptance of controlled charging can affect energy-system value and integration outcomes.
- Limitation: System-planning valuation, not site-level actor gates.
- Verification: IDEAS/RePEc DOI record.

### R13. Quality of service and fairness for electric vehicle charging as a service
- Authors/year: Dominik Danner; Hermann de Meer (2021)
- Source: Energy Informatics 4(Suppl 3), 16
- DOI: 10.1186/s42162-021-00175-3
- URL: https://doi.org/10.1186/s42162-021-00175-3
- Peer-reviewed: Yes
- Supports: EV charging can be evaluated as a service with QoS, fairness, and grid constraints.
- Limitation: Queuing architecture differs from this multi-actor simulator.
- Verification: SpringerOpen/DOAJ records.

### R14. The Impact of Charging Plug-In Hybrid Electric Vehicles on a Residential Distribution Grid
- Authors/year: Kristien Clement-Nyns; Edwin Haesen; Johan Driesen (2010)
- Source: IEEE Transactions on Power Systems 25(1), 371-380
- DOI: 10.1109/TPWRS.2009.2036481
- URL: https://doi.org/10.1109/TPWRS.2009.2036481
- Peer-reviewed: Yes
- Supports: EV charging can affect distribution-grid losses, voltage deviations, and loading.
- Limitation: Residential distribution setting and PHEV assumptions differ from this feeder screen.
- Verification: CoLab DOI record.

### R15. A Comprehensive Study of the Impacts of PHEVs on Residential Distribution Networks
- Authors/year: Mohamed S. ElNozahy; Magdy M. A. Salama (2014)
- Source: IEEE Transactions on Sustainable Energy 5(1), 332-342
- DOI: 10.1109/TSTE.2013.2284573
- URL: https://doi.org/10.1109/TSTE.2013.2284573
- Peer-reviewed: Yes
- Supports: Monte Carlo feeder impact studies motivate representative stress screening and stochastic EV load treatment.
- Limitation: Residential PHEV benchmark, not site-specific validation.
- Verification: ResearchGate DOI metadata.

### R16. Network reconfiguration in distribution systems for loss reduction and load balancing
- Authors/year: M. E. Baran; F. F. Wu (1989)
- Source: IEEE Transactions on Power Delivery 4(2), 1401-1407
- DOI: 10.1109/61.25627
- URL: https://doi.org/10.1109/61.25627
- Peer-reviewed: Yes
- Supports: The IEEE 33-bus radial distribution benchmark is traceable to Baran and Wu's feeder reconfiguration study.
- Limitation: Benchmark feeder, not a real-site feeder for this project.
- Verification: OUCI and DOI search records.

### R17. Pandapower--An Open-Source Python Tool for Convenient Modeling, Analysis, and Optimization of Electric Power Systems
- Authors/year: Leon Thurner; Alexander Scheidler; Florian Schafer; Jan-Hendrik Menke; Julian Dollichon; Friederike Meier; Steffen Meinecke; Martin Braun (2018)
- Source: IEEE Transactions on Power Systems 33(6), 6510-6521
- DOI: 10.1109/TPWRS.2018.2829021
- URL: https://doi.org/10.1109/TPWRS.2018.2829021
- Peer-reviewed: Yes
- Supports: Pandapower is an established open-source tool for static and quasi-static power-system analysis.
- Limitation: Tool validation does not validate this project's scenario assumptions.
- Verification: CoLab and arXiv records.

### R18. pandapower documentation
- Authors/year: pandapower development team (2026)
- Source: Official documentation
- DOI: none
- URL: https://pandapower.readthedocs.io/
- Peer-reviewed: No - software documentation
- Supports: Implementation details for pandapower network modeling and power-flow execution.
- Limitation: Documentation source, not peer-reviewed empirical evidence.
- Verification: Official pandapower Read the Docs search result.

## Removed or downgraded sources

- Broad web pages, Wikipedia-style pages, and repository pages were not used for manuscript claims unless explicitly labeled as documentation or journal scope.
- Behavior papers are used to justify acceptance and response risk, not to calibrate this simulator's severity parameters.
- IEEE-33 references are used for benchmark provenance, not site validation.
