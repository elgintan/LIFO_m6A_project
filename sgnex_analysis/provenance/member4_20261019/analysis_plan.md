> Current handover (19 October 2026): read `HANDOFF.md` at the package root. The working scope is the 23 processed runs. The 56-row broader metadata is background, with no expansion required by this handover. Historical commands/status below may be superseded.

> 19 October update: Member 3 candidate/checkpoint is now included. Scientific comparisons remain proposed; use the current README/manifest.csv/MODEL_INFO.md contract. The candidate was not automatically selected; full-run predictions remain pending.

# Scientific questions, comparisons and marking alignment

The handout is authoritative. It gives 50 percentage points to report plus interactive visualisation, 5 to reproducible documentation/code, 5 to model performance and 5 to individual contribution. It names clarity/presentation, domain understanding, methodology and innovation/creativity as assessment qualities; it provides no finer numerical rubric. No method can guarantee a particular mark.

## Comparison design

| Priority and question | Population and output | Evidence needed / limitations |
|---|---|---|
| 1. Are predictions reproducible within a cell line? | Same-site eligible scores; same-replicate run pairs separated from different-replicate pairs. Correlation, median absolute difference and technical score ranges. | At least two independent RNA preparations should be verified from provenance. Reads/runs are not extra biological replicates. High correlation can reflect motif preferences rather than accurate m6A calls. Repeat after coverage matching and within motifs when sequence metadata arrives. |
| 2. Which sites have consistently different predictions between a pair of lines? | At least two replicate groups per line, both lines observed at the same site. Continuous paired score difference, replicate ranges, coverage ratio and complete evidence table. | Main candidate screen: |mean score difference| ≥0.2, non-overlapping replicate score ranges and geometric mean coverage ratio ≤2. This is a descriptive prioritisation rule, not FDR or a chemical effect estimate. Check stricter all-replicate support and depth thresholds before selecting examples. |
| 3. What patterns are shared across all seven processed lines? | One all-line common-site panel, requiring ≥2 replicate groups/line. Replicate-balanced scores; high-score overlaps on exactly that panel. | Report denominator at every threshold. The current ≥20-read coverage ceiling is 33,452 common sites before any model failures. This selection favours well-observed transcripts and cannot describe all RNAs. Pairwise populations can be larger but cannot be mixed into one global ranking. |
| 4. What does one convincing locus show? | Choose a reproducible candidate after full analysis, show every replicate/run score and coverage, transcript ID/position, annotation, motif, and a matched nondiffering/discordant example. | Preserve low-coverage/missing cases as context. Avoid picking an attractive gene name before observing results. Read-level signal checks require raw event matrices; attention weights are not molecule labels. |
| 5. Are there region, motif or functional patterns? | Optional motif summaries; validated 5′UTR/CDS/3′UTR or metagene plots; exploratory pathway analysis. | Motif requires true 7-mer from corresponding JSON. Region mapping needs exact FASTA/GTF versions, transcript offsets, CDS bounds and strand. GO/background must be tested observable genes, with multiple-testing correction and gene/isoform deduplication. Not run; lower priority than sound primary comparisons. |

All 21 cell-line pairs are exploratory and retained. If one pair is selected for the short report, explain the biological question and show that its effect persists across prespecified checks; avoid selecting solely for the largest score difference. H9-versus-cancer comparisons combine many cell-type differences and cannot isolate a cancer mechanism. No biological direction is assumed in advance.

## What coverage and abundance checks can establish

Coverage is the number of reads in a site's input matrix/read-count table. Transcript abundance is the amount of RNA produced, often estimated using a separate quantification method. Site counts/read depth are not TPM. The current package does not contain matched, independently checked per-sample expression quantification.

Common-site filtering addresses unequal observability. Coverage thresholds and ratio filtering reduce some depth imbalance. They do not establish that RNA abundance, 3′ sequencing bias, isoform usage, alignment ambiguity, chemistry and batch have been removed. Ask for matched transcript abundance estimates if a claim requires expression adjustment; retain raw sample identity and quantification provenance. With only 2–3 replicate groups per line and substantial technical confounding, do not fit an elaborate adjustment and treat its coefficient as causal.

Technical covariates available in the manifest are kit, flowcell, platform, sample date and the metadata's ENA basecaller field. All 23 processed runs are listed as SQK-RNA002. The broader scope includes RNA001 and RNA004, which should not be treated as interchangeable without model/input compatibility checks. The metadata's basecaller field may describe archived ENA data rather than the effective basecaller used to produce the processed JSON. Public release notes mention rebasecalling later FASTQ/BAMs; that does not prove older processed event features were regenerated.

Do not normalise predicted scores separately within each cell line to make distributions match. Use one frozen model and the same trained preprocessing. Read subsampling plus inference can test depth sensitivity, but needs original matrices and is not performed by the coverage/score comparison scripts.

## Uncertainty and independent validation

A model score is a predicted site-level signal, not the proportion of modified molecules. Differences in mean score are not differences in modification fraction. Comparing the team's model with m6Anet can show algorithmic agreement/disagreement but is not independent experimental validation because both use nanopore signal features.

Use replicate distributions, technical-run ranges and all-replicate separation as descriptive uncertainty. Check whether sign/interpretation changes when removing a replicate, increasing depth or balancing coverage; two replicates offer little information after one is removed. Do not derive tiny p-values by treating millions of reads/sites as independent biological repeats. The included CLI intentionally makes no significance claims. A formal differential-modification method such as xPore would answer a different signal-mixture question and requires compatible original inputs and a separately justified design; it is optional rather than a substitute for the required selected-model analysis.

For orthogonal validation, obtain actual compatible m6ACE-seq or another assay's labels, exact sample/condition identity, coordinates, overlap/absence rules and provenance. `matched_RNA_modification_data=Yes` or a paper citation is not itself an available validation label. Failure to detect a site in an orthogonal assay can reflect assay sensitivity/coverage. Synthetic spike-ins can become useful negative controls only after confirming their modification chemistry and candidate validity.

## Reference and missingness rules

- Preserve raw IDs and positions in submitted prediction CSVs. Use an explicit, audited alias mapping only within analysis. Do not remove arbitrary suffixes or shift positions to improve overlap.
- Current coverage matching checks transcript-position identity; it does not establish the 0/1-based chemical nucleotide coordinate. Verify the 7-mer and candidate adenosine against the exact transcript FASTA before any genomic/regional interpretation.
- Primary population: supplied annotated human transcripts; alternate haplotypes and synthetic spike-ins analysed separately. Gene annotation provenance remains partly upstream-reported until independently rebuilt.
- A key absent from a processed candidate table is “not observed in the processed table.” It does not prove absent expression, an unmodified site or true read coverage of zero.
- Retain sites with overlapping replicate score ranges and effects that weaken under controls. The report discussion must reflect them, even if a favourable example is selected.

## Rubric-to-evidence mapping

| Assessment quality / requirement | Member 4 contribution | Completion |
|---|---|---|
| Domain understanding | Distinguish prediction, modification, molecule fraction, RNA abundance and coordinate systems | Explained; no chemical validation claimed |
| Methodology | Scope audit, same-site populations, replicate hierarchy, coverage sensitivity, controls | Coverage completed; real-score analysis code tested, analysis pending |
| Clear results | One compact coverage panel now; eventually replicate agreement + one paired locus/pair result | Coverage panel supplied; real-score panels pending |
| Innovation/creativity | Coverage-aware researcher comparison with transparent missingness and conflicting evidence | Analysis contract implemented; interface integration pending Member 5 |
| Reproducibility | Public source keys, hashes, scripts, derived tables, commands and scientific failure tests | Local checks completed; fresh Ubuntu installation pending |
| Working sample scope | 23 processed runs; broader metadata retained only as background | Analyse these 23 runs and state that results do not generalise to all SG-NEx direct-RNA data |
| Report limits | Short Methods/Results/Discussion contribution and essential figures | Draft supplied; final biological paragraph awaits predictions |
| AI disclosure | Actual tool use, verification and detected limitations/errors | `AI_use_member4.md`; human verification still required |

Proposed allocation within the team's five-page report: about 0.6–0.9 pages for Task 2 results with one composite figure, plus 2–3 methods sentences and a short limitations paragraph. This is a writing recommendation, not a course rule. Report uses Arial 11, captions/tables 9–11; include the repository/platform links, required AI-use table and at least two actual error/verification instances across the team. The supplied team deadline is 28 October 2026, 23:59 Singapore time; the no-questions period starts 26 October at 21:00. Check subsequent announcements.

## Primary references and source roles

1. Course handout and student evaluation guide supplied by the user: assessment, output schema, report/prediction/interface requirements.
2. Chen Y. et al. Nature Methods 22, 801–812 (2025), https://doi.org/10.1038/s41592-025-02623-4 : SG-NEx resource, protocols and transcript analysis context.
3. Official samples table, processed listing and annotation/access instructions: https://github.com/GoekeLab/sg-nex-data ; https://github.com/GoekeLab/sg-nex-data/blob/master/docs/samples.tsv ; https://github.com/GoekeLab/sg-nex-data/blob/master/docs/AWS_data_access_tutorial.md . Used for sample and file inventory, not as experimental validation.
4. Hendra C. et al. Nature Methods 19, 1590–1598 (2022), https://doi.org/10.1038/s41592-022-01666-1 : site-level multiple-instance prediction context.
5. Pratanwanich P.N. et al. Nature Biotechnology (2021), https://doi.org/10.1038/s41587-021-00949-w : xPore as an optional separately designed differential signal analysis, not run here.

Required SG-NEx access statement for integration: “The SG-NEx data was accessed on 15 October 2026 at registry.opendata.aws/sg-nex-data.” Cite the paper separately. The access here covered metadata, S3 listings and read-count tables, not full signal JSONs.
