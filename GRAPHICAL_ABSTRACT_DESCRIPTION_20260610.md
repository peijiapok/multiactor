# Graphical abstract description - Applied Energy submission

Use `graphical_abstract_candidate_20260610.pdf` as the initial graphical abstract candidate. It is derived from the multi-actor framework figure and should be exported to the journal-requested image format if the submission system does not accept PDF.

The graphical abstract should show, from left to right:

1. Driver behavior layer generating charging request events.
2. Fleet policy layer selecting service under charger-capacity limits.
3. Grid policy layer applying PeakPenalty or NoGrid intervention.
4. Final charging service and request-event/demand-kWh trace audit.
5. Driver, fleet, and grid acceptability gates joined by a logical AND.
6. Main result: severity-1 behavior removes same-episode all-pass outcomes under the specified gates, while event churn rises without increased simulator demanded kWh.

Do not present the graphic as a real-site validation. The IEEE-33 feeder component should be labeled as a representative stress screen.
