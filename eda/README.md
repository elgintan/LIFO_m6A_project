# Member 1: exploration and model context

This folder is for Member 1's reviewed findings, figures, tables and reproducible analysis code. Member 1 sends her context package directly to Elgin; Elgin prepares the material for the public repository.

## Current handover status

Received and inspected locally: `Member1_Analysis_Package/Member1_Analysis`, supplied in `Other members work`. It contains six completed figures, full site-summary tables, source hashes, EDA scripts, a context handoff and a proposed follow-up plan. No new model was trained or evaluated in that package.

All 43 manifest-listed files matched their supplied hashes. Selected small-table totals and signal-effect directions were independently checked; the raw signals were not reparsed for that review. The original five-gene-fold CSV is intact and matches the historical file. This does not decide the next split design.

The received package has been copied unchanged into `received/`; `../SOURCE_RECEIPT.json` records its hashes. It is included in the public project repository. The old handoff describes Samuel mainly as evaluator; the current plan is that **Elgin and Samuel each build a separate candidate model**. The [minimum shared rules](../model_evaluation/SHARED_RULES.md), accepted by Elgin, define the common comparison and take precedence over older received role/evaluation wording.

## Findings both model builders should use

- **Sequence changes signal interpretation.** Pooled positive sites have higher median current, yet positives have lower current within many motifs. Keep context and test how it interacts with signal.
- **Some motifs have very few positives.** Examine their counts when choosing partitions and show uncertainty/limitations rather than claiming a reliable model for every subgroup.
- **Read distributions matter.** Medians, variability and tails may contain information that averages hide. Broad distributions deserve investigation before any cleaning or exclusion.
- **Coverage relationships shift.** Coverage has different associations with labels in data0 and data1. Compare coverage handling and sensitivity to fewer reads.
- **The files are not interchangeable.** data0 and data1 share 67,320 site IDs, including 3,872 label disagreements. data2 contains repeated positions across fractional-label groups. These findings affect pooling, grouping and evaluation claims.

The existing Elgin network already receives sequence, individual reads, and all-read means/SD/quantiles. Its next changes must address a specific gap or test a component's contribution. Samuel's candidate should be reviewed against the same feature specification.

Read [the minimum shared rules](../model_evaluation/SHARED_RULES.md) and [EDA-informed methodology](../DATA_METHODOLOGY.md). Elgin accepted reuse of the audited five outer gene groups; Samuel's acknowledgement has not yet been reported. Model design remains independent. The [historical composition audit](split_review/README.md) describes context, class and coverage support. Gene-separated inner validation is required when used, with optional default roles supplied. No new candidate has been fitted.

## Material to retain here

- A concise findings/context document with observed patterns, interpretation, proposed model implications and limitations.
- The essential figures and source tables supporting report claims.
- EDA scripts and dependency/run instructions.
- Input hashes and an explanation of how to obtain the original datasets, rather than bundling raw data indiscriminately.

The full received package can remain a preserved source copy; the report needs only its strongest relevant findings. No separate findings register is required.

## Pending work

The package proposes exact-context/coverage-controlled comparisons, repeated read-subsampling stability and unusual-site read-level case reviews. These have **not** been completed. Site-summary tables alone cannot recreate the individual-read matrices for the latter two analyses.

The official intermediate leaderboard slides confirm data0 as HCT116, data1 as HEK293T and data2 as synthetic sequences. Exact run provenance, complete data1 gene mapping, fractional-label scoring/source dependence, and SG-NEx sample/replicate inventory remain unresolved. Confirm broad identities from that official source rather than generic filenames; predicted differences alone do not establish biological mechanisms or modification fractions.

For a useful handoff, explain: **what was observed → what it might mean → what model/data decision it suggests → how we will check it**. Keep plausible biology separate from verified evidence.
