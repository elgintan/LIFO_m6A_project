# Member 4 findings

Updated 19 October 2026. **Completed: sample/coverage analysis and Member 3 candidate software/evidence checks. Pending: final selection and full-run SG-NEx score comparisons.**

## Question

Which SG-NEx cell lines and sites can be fairly compared for predicted m6A patterns, after accounting for replicates, coverage, missingness and technical differences?

## Methods

The earlier audit matched the 23-run public m6Anet-processed listing to official sample metadata. Runs were nested within 17 replicate-number groups. Coverage was reconstructed from the supplied Explorer without reading its simulated scores, then checked against all 23 original public read-count tables. Primary comparisons use annotated human transcripts; synthetic and unresolved-reference categories remain separate. Shared populations were counted at 20/50/100 reads with >=1, >=2 or every listed group per line. Independent laboratory preparations and exact reference offsets remain to be verified.

On 19 October, Member 3's received frozen LightGBM checkpoint and sequence-reference hashes were checked. Its original ten-site prediction example was reproduced byte for byte locally; recorded data0/data1 metrics were independently recomputed using Member 1's derived labels. No training or full SG-NEx inference was performed.

## Observed results

- Available processed scope: **23 runs, seven cell lines, 17 replicate-number groups**. Broader metadata: **56 direct-RNA runs**, including **33 outside this processed subset**. The agreed working scope is these 23 processed runs; the broader table is retained as background only. This update did not refresh the public inventory.
- At >=20 reads in some run: **451,352 candidate transcript-position keys**, including **437,320 annotated-human keys**. These are measurable candidates, not predicted modified sites.

| Minimum reads | Common to all 7 lines: >=1 group/line | >=2 groups/line | Every listed group/line |
|---|---:|---:|---:|
| 20 | 59,224 | 33,452 | 26,024 |
| 50 | 20,535 | 11,560 | 9,429 |
| 100 | 8,814 | 5,058 | 4,300 |

All common sites shown are annotated-human entries. Repeated runs do not count as extra biological groups. Per-run >=20-read candidate counts span 34,202–259,535; unequal observability is substantial.

Member 3 candidate metrics matched supplied records: data0 **mean-fold ROC 0.921897, trapezoidal PR 0.498996, AP 0.499566, S 0.710446**; exposed data1 **ROC 0.821764, PR 0.382879, AP 0.383071, S 0.602322**. These are development/transfer results, not Task 2 cell-line findings or evidence of final selection. At 0.5, some development motifs have zero positive recall; the >200-read stratum is weaker. Full-precision continuous comparisons and sensitivity checks are therefore preferable to a single call threshold.

## Interpretation

Coverage and replicate support restrict the common population, motivating same-site, replicate-balanced comparisons. Member 3's candidate can now be tested using an actual checkpoint and fixed preprocessing, but no observed between-cell-line m6A score difference is established yet. Its arrival does not make it the selected final model. A missing processed site is not an unmodified site; more candidate calls do not establish more m6A.

## Limitations and pending work

Complete final model selection, per-input preprocessing/reference coordinates and group independence. Common-site/depth filtering does not fully adjust RNA abundance, isoform usage or batch. Prediction scores are not validated molecule fractions. The earlier Explorer scores remain simulated; incoming generic data0/1/2 outputs are not per-run SG-NEx results. Full-run predictions, replicated score comparisons, stronger biological interpretation, independent assay validation and fresh AWS Ubuntu evaluation remain pending.

## Evidence and commands

Essential figure: figures/coverage_and_replicate_support.png. Supporting tables: results/replicate_coverage_support.csv, public_readcount_verification.csv and public_readcount_status.json. Model/source versions: MODEL_INFO.md and metadata/member3_source_receipt.json. New checks: results/member3_metrics_check.json and member3_example_check.json. Source/analysis commands and exact prediction interfaces are documented in HANDOFF.md; new candidate and contract checks are retained in results/readme_member3_tests.log. The longer earlier report contribution is preserved as dated background in docs/background_findings.md.
