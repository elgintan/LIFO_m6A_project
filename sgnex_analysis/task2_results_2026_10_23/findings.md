# Task2: context-qualified predicted-score patterns

This is assistant-executed descriptive analysis of the selected frozen model,
not an independent m6A assay, calibrated prevalence estimate or causal cell-line test.
All23 original prediction exports remain complete and unchanged. Metadata groups
follow sample names; separate laboratory preparations are not independently proven.

## Context determines which site keys can be compared

The audit streamed 28,670,080 saved source-site
observations. It compared all source contexts at the 451,352
coverage-union keys, including low-read observations. There were
0 keys with conflicting model-encoded
contexts across those source observations and 0
with conflicts among >=20-read scored observations. Contexts outside the complete
scoreable union were not compared; those observations were never scored by this application.
Conflicts remain in the QC evidence and original exports. No majority sequence was substituted.

Across all seven lines, before-context / primary-context / scored-only-sensitivity
common populations are: >=20 reads: 33,452 / 33,452 / 33,452, >=50 reads: 11,560 / 11,560 / 11,560, >=100 reads: 5,058 / 5,058 / 5,058.
Every comparison additionally requires annotated human keys and >=2 metadata groups
per cell line. Eligible runs are averaged within group, then groups receive equal weights.

## Patterns on one explicitly matched population

At >=20 reads, each line uses the same 33,452 common sites:

| Cell line | Mean score | Median score | Score >=0.5 |
|---|---:|---:|---:|
| A549 | 0.0816 | 0.0256 | 4.13% |
| H9 | 0.0793 | 0.0239 | 4.19% |
| HEYA8 | 0.0796 | 0.0260 | 4.05% |
| Hct116 | 0.0946 | 0.0307 | 5.20% |
| HepG2 | 0.0829 | 0.0267 | 4.16% |
| K562 | 0.0807 | 0.0240 | 4.47% |
| MCF7 | 0.0705 | 0.0200 | 3.76% |

The 0.5/0.7/0.9 cutoffs are descriptive conventions. Continuous distributions
and cutoff counts are provided together; none of these percentages measures
chemical modification prevalence or the fraction of modified molecules.
The >=50 and >=100 populations contain different subsets of sites. Changes
between their summaries mix population selection and coverage, and are not a
controlled within-site read-depth experiment.

## Concordance and pair-specific effects

`agreement_summary.csv` separates same-group sequencing runs, other groups in the
same cell line, and cross-line comparisons. Its correlations describe score ranks
on the sites shared by each pair; each estimate has its own denominator. Shared
sequence/context structure can contribute to agreement. A high correlation is not
prediction accuracy or evidence that groups are independent biological replicates.

All21 line pairs are retained at all three read thresholds. Each pair uses its own
common population, separately from the all-seven-line panel. Full pair files remain
with the comparator outputs, including small effects, overlapping group ranges and
valid extremes. Candidate flags require |mean-score difference|>=0.2, non-overlapping
group ranges and depth ratio<=2. They are exploratory screens, without a significance
test or false-discovery control. `all_pair_summary.csv` reports their denominators.

## Support, negative evidence and limits

Of the 33,452 common >=20-read sites, 22,219 have a seven-base context with fewer
than20 positive data0 training labels. They remain in every applicable analysis;
support counts are warnings, not calibrated uncertainty or an exclusion rule.
`common_site_training_context_support.csv` retains zero, sparse, well-supported and
unknown support separately. The context gate, conflicting cases, undefined correlations
and all21 pair outcomes are preserved rather than selected for favourable results.

`score_coverage_dependence.csv` records observed score/read-count associations.
`technical_metadata_counts.csv` records basecaller, platform, kit, date and spike-in
composition by line. Coverage balancing does not fully adjust expression or batch;
technical factors can be confounded with cell line. Matching seven bases does not
prove exact historical FASTA identity or nucleotide/event offsets. No genomic-region,
pathway, chemical-type, stoichiometry or causal lineage claim follows from this analysis.

## Reproduction and figures

Run `sgnex_analysis/scripts/report_task2_analysis.py --qc-dir ... --analysis-dir ...
--out NEW_DIRECTORY` from the repository root with the documented Python environment.
The reporter rechecks source completion, context-policy/input binding, complete
prediction availability, all-seven-line summaries, all63 full pair tables and QC
population denominators before writing its own completion receipt last.
PNG and editable-text SVG figures accompany the aggregate CSVs. CDF plots use an
explicit501-point grid of the empirical distribution; the score summaries use all sites.
