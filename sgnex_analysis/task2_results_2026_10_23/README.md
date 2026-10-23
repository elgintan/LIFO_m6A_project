# Task 2 actual-score analysis — 23 October 2026

The frozen selected cap128/positive-weight3 model supplied all 23 runs. Context
QC, Member 4's full comparison and the scientific reporter completed with exit0.
These are predicted-score patterns, not measured modification fractions.

Read [findings](findings.md) and [the interpretation draft](INTERPRETATION.md).
Four PNG/SVG figure pairs and all aggregate CSVs are copied byte-for-byte from
the completed local `outputs/task2_report_v2/`. The second reporter version
only repairs figure layout; all ten numerical CSVs match version 1 exactly.
All 21 pair outcomes at all three depths remain available. Candidate flags
are exploratory screens with no significance or false-discovery claim.

The primary rule is annotated human keys, agreement across all saved source
contexts at a scoreable key (including low-read records), and at least two
metadata groups per line. Mean eligible runs within group, then equal group
weights. The all-seven population is separate from each pair's own population.
Depths 20/50/100 and cutoffs 0.5/0.7/0.9 are retained. No valid extreme was removed.

`complete.json` and `analysis_receipt.json` are exact original receipts. They
reference large local files, not files bundled in this public folder. Full
per-site matrices, all pair tables, original predictions, conflict/key tables,
source metadata and monitor logs remain in ignored local `outputs/` directories.
See [the context audit](../context_qc_results/README.md) for scope and exclusions.
`publication_manifest.json` pins the public copies. `resources.json` reports
separate actual command scopes; no CPU durations are added across overlaps.

The original slow comparison was stopped and retained as an incomplete attempt.
The completed retry used exact dictionary lookups and prepartitioned pairs;
regression checks preserved the original statistical definitions.

The full local actual-score explorer is
`data_visualisation/outputs/real_scores_v1/site/` (197 MB data, all 451,352 sites).
Its validation passed 190 checks with no warnings/failures; an independent
aggregate audit matched all 189 cutoff fractions exactly. It displays actual
scores, context/support warnings, missingness and equal-group summaries.
UTF-8 label repair preserved original numeric/identifier literals and values.
The explorer's separate agreement panel uses mean Pearson r in disjoint read
bands; this report uses per-pair Spearman correlations at cumulative thresholds.
The local dashboard is not yet publicly hosted. Final report assembly remains
pending. Source reproduction commands are in the analysis and explorer READMEs.
