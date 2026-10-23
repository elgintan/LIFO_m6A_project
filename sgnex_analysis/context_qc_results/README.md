# Cross-run sequence contexts: completed

The fixed 23-run audit streamed **28,670,080** saved source-site observations.
It compared all observations at every **451,352** coverage-union key that was
scored in at least one run: **8,780,071 observations**, including low-read records.
Original identifiers and scores were retained; only documented per-run aliases
and the model's uppercase/U-to-T encoding were used inside analysis.

**No encoded sequence conflicts, literal-only differences, ambiguous contexts,
noncentral-A contexts or within-run alias collisions were found in that universe.**
Every key passes both the primary all-source rule and the scored-only sensitivity.
No score was excluded or corrected. The empty conflict table is retained locally.
The 19,890,009 outside-union observations were never scored in this application;
their cross-run contexts were not compared. These are observations, not unique keys.

All-seven-line annotated common populations, requiring >=2 metadata groups/line:

| Minimum reads per eligible run | Before context QC | Primary | Scored-only sensitivity |
|---|---:|---:|---:|
| 20 | 33,452 | 33,452 | 33,452 |
| 50 | 11,560 | 11,560 | 11,560 |
| 100 | 5,058 | 5,058 | 5,058 |

All 21 pairwise populations are also unchanged. `population_effects.csv` keeps
each pair, each line and the all-line panel separate. No redundant full comparison
is needed for identical context gates. Comparisons still use mean eligible runs
within group followed by equal group weights, with 0.5/0.7/0.9 descriptive cutoffs.

Training support remains uneven: 55,253 union keys have a seven-base context with
zero positive data0 labels; 294,896 have fewer than 20. These warnings do not remove
sites or provide calibrated uncertainty. No unseen canonical training context was
found. Context agreement does not prove historical FASTA identity, nucleotide
offsets, independent laboratory preparations, prediction accuracy or stoichiometry.

The full audit completed in 581.761 seconds of command wall time; sampled
command-tree CPU lower bound was 567.469 seconds and peak RSS 603.234 MiB.
The narrower internal timer overlaps this measurement and must not be added.
A separate saved-table audit independently reproduced all 451,352 key flags,
support counts and all 87 population rows in 22.390 seconds. It did not rescan
the 28 million source rows or rerun model inference.

Reproduce from repository root using the existing Python environment:

```powershell
& $py -B -u sgnex_analysis/scripts/audit_cross_run_contexts.py --out NEW_QC_DIRECTORY
```

Read the [predeclared rules](../CROSS_RUN_CONTEXT_QC_PLAN.md). Public files here
are compact aggregates and receipts. Full key/conflict tables remain in local
ignored `outputs/context_qc_v1`; their hashes are referenced by `complete.json`.
This is assistant-executed technical QC, not independent biological validation.
