# Member 1: Data exploration and biological context

DSA4262 RNA modifications project | EDA completed 13 October 2026; handoff revised 14 October 2026, Singapore time

This revision covers Member 1's responsibilities: the measurements, labels, sequence patterns, coverage, unusual cases, and ideas that can inform the shared model. It includes a dataset-split proposal. All numerical findings below were recomputed from the supplied signal and label files. No model was trained or evaluated in this analysis. No existing model predictions or performance records were used.

The analysis is exploratory. Proposed splits, transformations and feature improvements are recommendations, not completed experiments. The original team handoff and source files are preserved.

## 1. Data inventory and immediate recommendation

| Item | data0 | data1 | data2 |
|---|---:|---:|---:|
| Sites, matched exactly between JSON and metadata | 121,838 | 90,810 | 1,323 |
| Transcript identifiers | 5,333 | 4,451 | 7 anonymous IDs |
| Gene identifiers supplied | 3,852 | None | None |
| Label values | 0 and 1 | 0 and 1 | 0, 0.25, 0.5, 0.7, 0.75, 0.95, 1 |
| Sites labelled 1 | 5,475 (4.49%) | 6,593 (7.26%) | 189; binary prevalence is not an appropriate summary |
| Sites labelled 0 | 116,363 | 84,217 | 189 |
| Site-read entries | 11,027,106 | 7,907,952 | 1,171,940 |
| Median reads per site | 47 | 40 | 814 |
| Coverage middle 50% | 32–84 | 27–77 | 440–1,269.5 |
| Coverage range | 20–991 | 20–994 | 26–3,438 |
| Central 5-mers | All 18 DRACH motifs | All 18 DRACH motifs | All 18 DRACH motifs |
| Distinct 7-base contexts | 288 | 288 | 139 |

Site-read entries count the rows inside each site's signal matrix. They are not a count of unique molecules: a read can cover several sites, and read IDs are absent from these inputs.

**Recommended immediate design:** keep the exact shared five gene folds for data0 development; use data1 as an already-exposed dataset-shift diagnostic; keep data2 separate for descriptive stress testing until its label meaning and construction are confirmed. Neither splitting every file randomly nor treating data2 as the sole ordinary binary test is supported by the observed structure.

### Sources inspected

- `Team_Project.zip`: all three compressed JSON files, all three label tables, the project handout, course slides, student-evaluation guidance and sample submission. The handout in the archive matches the separately supplied current handout.
- `TEAM_AI_HANDOFF_2026-10-12.md`: role allocation, existing data exposure and team conventions. Its historical model results were not used here.
- `LIFO_shared_folds.zip`: original assignments, metadata, summary and verification script. The exact file passes the supplied read-only verifier. No folds were regenerated.
- Official SG-NEx and m6Anet sources: possible additional data, described in Section 8. Those external signal datasets were not downloaded or analysed in this revision.

The handout identifies the provided training data as HCT116. A sample manifest linking the generic data1/data2 names to cell lines, runs, chemistry and experimental construction was not supplied. Do not call data1 a different-cell-line test or identify data2 as a particular published experiment without that evidence.

## 2. What the measurements and labels mean

m6A is N6-methyladenosine, a chemical modification of adenosine in RNA. The project asks whether nanopore event measurements and local sequence can distinguish sites carrying the supplied m6A labels. These inputs contain summaries of electrical signal events, not complete raw signal waveforms.

Each JSON line contains one transcript-position site, a seven-base sequence, and a matrix with one row per covering read. The nine entries in each row are ordered as follows.

| Columns in the read vector, counted from 1 | Position | Measurements in order |
|---|---|---|
| 1–3 | −1 neighbour | Dwell time, event current standard deviation, mean current |
| 4–6 | Central position | Dwell time, event current standard deviation, mean current |
| 7–9 | +1 neighbour | Dwell time, event current standard deviation, mean current |

For `AAGACCA`, the overlapping 5-mers are `AAGAC`, `AGACC`, and `GACCA`. The central 5-mer is `sequence[1:6]` in Python. DRACH means D = A/G/T, R = A/G, and H = A/C/T; the middle A is the candidate site. The files use T to encode sequence context even though this is an RNA project.

Every analysed site already has a central DRACH motif. Therefore, asking whether “having a DRACH motif” predicts the label is uninformative here. Compare which DRACH motif is present and the two additional flanking bases.

The handout describes binary labels as site-level calls obtained using m6ACE-seq. They do not assign a true modification state to each individual read. A site labelled 1 can contain heterogeneous reads. A label-0 site should be described as label 0 under the supplied assay, without claiming that every molecule is chemically unmodified. The m6Anet paper explains this distinction between site-level supervision and missing molecule-level labels [R1].

Two kinds of variability must be kept separate: **event SD** is a supplied feature within one read's event; **across-read IQR** is the spread of a feature across the reads at one site. IQR means the 75th percentile minus the 25th percentile. Our plots use the numerical units in the supplied files; no additional unit conversion is assumed.

## 3. Completed quality checks

Across 213,971 sites and 20,106,998 site-read entries:

- Every JSON site has exactly one matching metadata row, joined on both transcript ID and numeric transcript position. No duplicate site keys or unmatched records were found.
- Every read vector has nine finite, strictly positive values. No missing or non-finite measurements were found in the parsed matrices.
- All sequences have seven A/C/G/T characters, and all central motifs satisfy DRACH.
- Supplied `n_reads` values in data1 and data2 match the actual matrix lengths exactly. Coverage for data0 was calculated directly from its matrices.
- Source-file SHA256 hashes are recorded in `tables/source_manifest.json`. These identify the inputs; they do not establish biological provenance.
- The shared data0 fold CSV has 121,838 unique assignments, correct genes, all five fold IDs, both classes in every partition and zero gene overlap between training and validation.

These checks establish structural consistency. They cannot establish correct event alignment, correct labels, independent biological replication or the absence of batch effects. Complete ordered signal matrices differ for every matched data0/data1 site; this does not rule out partial read reuse or common source material.

Metadata columns `start` and `end` must not be assumed to be gene-region coordinates. They are processing metadata in the supplied tables, not verified biological annotation. Gene/transcript IDs, fold IDs and byte-offset metadata are not predictive features.

## 4. Observed patterns and their limits

### A. Sequence composition strongly changes the label comparison

**Observed:** GGACT is the most label-1-enriched central motif in both binary datasets: 1,440/6,376 sites (22.58%) in data0 and 1,186/5,415 (21.90%) in data1. In data0, TAACA has only 1 positive among 4,695 sites (0.021%); TAACC has 2/2,966 and AAACC has 11/6,502.

**Interpretation:** motif identity is associated with the supplied labels, but an enriched motif is not a guarantee of modification. The very small positive counts for some motifs make their apparent signal differences unstable. This is a reason to show denominators, not a reason to delete the motifs.

**Hypotheses to test:** part of the association may reflect biological sequence preference; part may reflect candidate selection or the labelling assay. These files alone cannot separate those explanations.

### B. Pooling motifs can reverse the apparent signal relationship

We first took the median of each feature across all reads at each site, then compared those site summaries. Each site has equal weight in these comparisons.

| Pooled central-feature comparison | data0, label 0 → label 1 | data1, label 0 → label 1 |
|---|---:|---:|
| Median of site median current | 114 → 118 | 116 → 118 |
| Median of site median event SD | 4.30 → 4.66 | 4.47 → 4.72 |
| Median of site median dwell time | 0.00662 → 0.00679 | 0.006475 → 0.00666 |
| Median of within-site current IQR | 3.50 → 4.00 | 3.25 → 4.00 |

**Observed:** pooled current is higher for label 1. However, among motifs with at least 20 sites in each label, central current is lower for label 1 in 11/15 motifs in data0 and 9/17 in data1. The remaining motifs include higher values and exact ties. Central event SD is lower within 14/15 such motifs in data0 and all 17 in data1.

The direction often persists after coarse coverage stratification. Among motif-by-coverage strata with at least 20 sites per label, central current is lower in 33/43 data0 strata and 34/58 data1 strata; central event SD is lower in 39/43 and 51/58, respectively.

**Interpretation:** the pooled comparison mixes different sequence compositions. A universal rule such as “m6A makes current higher” is not justified. Sequence-conditioned comparisons are more useful for this dataset. Coarse bins do not fully control coverage, gene effects, or the outer two bases. These counts are descriptive, not independent replication or significance tests.

**Feature ideas:** retain sequence context; consider signal-by-motif interactions or motif-conditioned residuals; preserve read-distribution summaries such as median, IQR and selected quantiles. Their value must be tested by the modelling team on the fixed gene folds.

### C. Coverage matters differently in data0 and data1

**Observed:** median coverage is 47 versus 48 for labels 0 and 1 in data0, but 39 versus 47 in data1. In data1, label-1 prevalence rises from 6.28% at 20–49 reads to 10.63% at 500+ reads. Data0 does not show that same monotonic pattern: its corresponding values are 4.44% and 4.32%.

**Interpretation:** coverage may track assay detection, abundance, selection or technical differences. It also changes how precisely a site's read distribution can be estimated. The observed association does not show that additional reads cause modification.

**Hypotheses to test:** some signal differences may weaken after coverage matching; a model might exploit coverage patterns that do not transfer between datasets. Compare features with and without coverage and repeat summaries after controlled read subsampling. The present analysis used all reads and did not perform that subsampling experiment.

All supplied sites have at least 20 reads. We cannot infer behaviour below 20 or validate that threshold from these files. Data2's much higher coverage is a further shift. Missing sites are not negative sites.

### D. data0 and data1 are related, with genuine label disagreement in the files

There are **67,320 shared transcript-position IDs**, representing 55.25% of data0 and 74.13% of data1. All shared sites have the same seven-base context. No paired site has an identical complete ordered signal matrix.

| data0 label | data1 label 0 | data1 label 1 |
|---|---:|---:|
| 0 | 61,312 | 2,717 |
| 1 | 1,155 | 2,136 |

Thus, 3,872/67,320 shared sites (5.75%) have differing labels. This is not a classification-error table: neither axis is a model prediction. Central-current site medians are highly correlated across shared sites (Spearman correlation 0.9947), but this pooled correlation can be dominated by sequence context; it does not establish modification agreement.

**Possible explanations:** different samples or conditions; assay variation and thresholds; or a preparation/annotation mismatch. Source metadata is needed to distinguish them. Do not relabel a row simply to make the files agree. If samples are genuinely distinct, retain a dataset/sample key alongside transcript and position.

There are 23,490 data1-only site IDs. They are not automatically new genes. Mapping data1 through data0's unique transcript-to-gene mapping resolves 75,673 sites across 2,508 already-observed genes. Another 15,137 sites on 1,019 transcripts remain unmapped. These are unknown-gene sites, not verified unseen-gene sites.

### E. data2 repeats a matched sequence design across seven label groups

Each anonymous transcript ID contains 189 rows and exactly one label.

| Anonymous transcript | Supplied label | Rows |
|---|---:|---:|
| tx_id_0 | 1.00 | 189 |
| tx_id_1 | 0.95 | 189 |
| tx_id_2 | 0.75 | 189 |
| tx_id_3 | 0.70 | 189 |
| tx_id_4 | 0.50 | 189 |
| tx_id_5 | 0.25 | 189 |
| tx_id_6 | 0.00 | 189 |

All groups use positions 0, 10, …, 1,880. At every one of the 189 matching positions, the same seven-base context occurs in all seven groups. There are 139 distinct contexts because some occur at multiple positions.

**Observed:** relative to the label-0 row at the same position, median central-current differences across the 189 matched positions are −0.6, −1.9, −2.5, −2.9, −3.0 and −3.0 for labels 0.25, 0.5, 0.7, 0.75, 0.95 and 1. The figure's band is an IQR across positions, not a confidence interval. Central dwell-time changes are smaller and heterogeneous.

**Hypothesis:** the layout is consistent with a constructed mixture or matched-condition experiment. The files do not establish what the fractions represent, the source molecules, independence across groups or whether fractions refer to a site, sample or mixing protocol.

**Consequence:** do not round the labels, silently discard intermediate groups, report ordinary binary ROC/PR AUC on all rows, or claim that a site score estimates a modified-molecule fraction. Transcript ID would directly reveal the group label here. Treat the 189 repeated positions as matched templates for descriptive comparisons, not 1,323 independent biological replicates.

### F. Unusual cases are review candidates, not automatic errors

| Dataset and site | Label | Reads | Central-current IQR | Median IQR for its motif in that dataset |
|---|---:|---:|---:|---:|
| data0: ENST00000592107, position 370 (TGACT) | 0 | 28 | 17.75 | 5.00 |
| data0: ENST00000369075, position 3059 (GAACA) | 0 | 29 | 17.00 | 2.65 |
| data1: ENST00000591247, position 1166 (GAACA) | 0 | 23 | 18.55 | 2.60 |

These were selected mechanically as large-spread examples within their motif, not from model errors. A full review list is in `tables/unusual_sites_review.csv`. Low coverage can make spread estimates unstable. Mixed read populations, event-alignment problems, or valid biology are other hypotheses. A broad IQR alone does not prove bimodality or modification.

Next, inspect per-read histograms and adjacent-position scatterplots for these cases and matched ordinary sites. Confirm any technical explanation with alignments or source metadata. No outlier was removed or relabelled in this analysis.

## 5. Prioritised exploration plan and plot questions

The first six figures have been generated. Further experiments are clearly marked as proposed.

| Priority / status | Plot or check | Question and inputs | Main limit or next decision |
|---|---|---|---|
| P0, completed | Figure 1: coverage CDF and binary label proportions | Are datasets comparable in size, coverage and label balance? Uses every site's coverage and supplied label. | CDF means the fraction of sites at or below a coverage value. data2 is excluded from binary prevalence. |
| P0, completed | Figure 5: paired-label table and signal scatter | How much overlap exists, and do paired sites have different labels or signals? Join data0/data1 on transcript and numeric position. | Scatter shows 5,000 deterministically sampled sites, seed 42; counts and correlations use all pairs. It is not a prediction confusion matrix. |
| P1, completed | Figure 2: motif counts and positive proportions | Are particular motifs enriched among label-1 sites? Uses central 5-mer and site label, with counts. | Rare positive groups and assay selection can distort interpretation. |
| P1, completed | Figure 3: signal differences within motifs | Which of the nine site-median measurements differ after separating motifs? Difference is scaled by pooled site IQR within that motif. | Grey cells have fewer than 20 sites in either class. Threshold is for displaying effects, not an exclusion rule. No significance claim. |
| P1, completed | Figure 4: coverage by label and label rate by coverage | Does coverage relate to labels similarly across datasets? Uses bins 20–49, 50–99, 100–199, 200–499 and 500+. | Bins are descriptive and do not establish causation or remove all confounding. |
| P1, completed | Figure 6: matched-position data2 differences | Does signal change across fractional groups while holding the repeated position/context fixed? | Fraction semantics and replicate structure remain unverified. |
| P2, proposed | Coverage-matched signal panels | Do motif-specific differences remain at comparable coverage? Refine the supplied motif-by-coverage table; consider exact 7-mers. | State which sites have common support; do not treat sparse cells as reliable effects. |
| P2, proposed | Read-subsampling stability curves | How much do site medians/IQRs change when fewer reads are available? For sites with at least 100 reads, sample 20, 50 and 100 without replacement, with 100 repeats, seed 42. | Measures finite-read sensitivity within observed sites, not biological reproducibility. Keep the same sites at all three depths. |
| P2, proposed | Unusual-case per-read histograms and neighbour scatter | Are broad distributions caused by a few extreme reads, two populations, or broad variation? Use raw matrices plus typical same-motif, similar-coverage sites. | Visual multimodality alone does not identify methylated reads. |
| P3, proposed | Gene/region annotations | Do labelled groups differ by CDS/UTR or proximity to transcript ends? Requires version-matched annotation and coordinate checks. | Do not infer these regions from `start/end` processing metadata or anonymous data2 IDs. |

For a short team report, prioritise the motif/signal finding and the dataset-overlap/split rationale. Use the remaining figures as supporting material. Member 1 does not need to produce the team's complete model-evaluation or SG-NEx results section.

## 6. Proposed training and testing design

### Preferred design with the current evidence

**Step 1: data0 development.** Use the exact existing five-fold manifest, grouped by `gene_id`. In round k, validate on fold k and train on the other four folds. This gives roughly 80% training and 20% validation per round while keeping every gene intact. These are development folds because the team has already used them for model choices. They are not a newly untouched test set.

**Step 2: data1 diagnostic evaluation.** Freeze choices before the next comparison. Use data1 to examine dataset shift and report shared-site and data1-only-site strata separately. Both strata still need gene-overlap qualification. Previously inspected data1 cannot be made blind by running it again. A clean unseen-gene subset cannot yet be identified from its incomplete gene mapping.

**Step 3: data2 separate analysis.** Describe matched-template signal trends and, once appropriate predictions exist, assess group ordering as a diagnostic. First obtain the official meaning of its fractional labels and intended metrics. If they are validated quantitative modification fractions, quantitative assessment may be appropriate; that would be a different target from binary site classification. Do not silently change the target.

**Step 4: genuinely future evaluation.** The handout says a new final evaluation dataset will be released. Reserve any eligible future dataset or external labelled sample from model selection if an independent test is required. Inspect only what is necessary for format/provenance and prespecify the evaluation. No such untouched test was created in this revision.

### Assessment of the suggested alternatives

| Option | What it would measure | Recommendation |
|---|---|---|
| Train on data0, evaluate on data1 | Transfer between the supplied files, including many familiar genes/sites | Useful diagnostic; not a fully independent unseen-gene or blind test. |
| Train on data0 + data1, test on data2 | Transfer to a high-coverage, repeated-template dataset with a different label structure | Do not use as the only main binary evaluation. It answers a different and currently ambiguous question. |
| Randomly use two-thirds of each file for training and one-third for testing | Performance on related sites, genes and repeated templates mixed across partitions | Reject for the main result. File-level stratification does not prevent gene or template leakage. |
| Split two-thirds/one-third by gene across pooled data0 + data1 | Generalisation to withheld genes in both files, if all gene mappings are correct | Conceptually valid as a new exploratory design, but currently blocked by unmapped data1 transcripts and prior exposure. It would also replace the team's comparison convention. |
| Retain data0 folds; add eligible data1 genes to training within each round | Whether more sample diversity improves a fixed development comparison | A useful second-phase experiment after provenance and complete gene mapping. Keep the original data0 assignments unchanged and extend them consistently. |

### Concrete rules if the team later pools data0 and data1

1. Obtain a version-matched transcript-to-gene mapping and sample/protocol manifest. Do not group unknown transcripts separately and assume that this guarantees gene independence. Resolve or conservatively exclude unresolved rows under a documented rule, with counts.
2. Retain the original data0 gene-to-fold assignments. A data1 row mapped to a data0 gene inherits that gene's fold, even when its site or transcript is absent from data0.
3. Assign genuinely additional genes once using a documented deterministic, group-aware five-fold extension, seed 42. Export and share one new manifest. The extension is proposed, not generated here; record its exact algorithm, ordering, counts and hash.
4. For round k, train using eligible rows from either dataset whose gene is outside fold k. Evaluate held-out fold-k rows separately for data0 and data1. Never add a data1 copy of a held-out data0 gene to training.
5. Keep rows from distinct samples distinct. Investigate opposite labels before pooling; do not majority-vote them away. Confirm whether assay definitions and coordinate references are compatible.
6. Compare data0-only and augmented training on the same data0 validation sites. This isolates the effect of adding data1. Pooled cross-validation measures withheld genes represented in the pooled domains; it does not prove transfer to an unseen cell line.
7. Treat all such comparisons as development. Preserve a separately reserved future external evaluation for an independent generalisation claim.

### Common settings to share

| Setting | Agreed existing convention or proposed rule |
|---|---|
| Main fold manifest | `shared_folds/data0_folds.csv`, exact bytes |
| Existing folds and seed | 5 gene folds; original generation used seed 42 |
| Fold labels | 0, 1, 2, 3, 4; do not independently regenerate them |
| Join keys | Transcript ID plus numeric transcript position, with unique and complete matches |
| Existing fold CSV SHA256 | `986b7872084cf762f1c3944b1eacc1e8f1ff69cb2848630f80685063541da9b0` |
| New stochastic EDA | Seed 42; record the operation and library versions |
| Proposed final robustness repeats | Training seeds 42, 43 and 44 on unchanged folds, if time permits; not a requirement to rerun every idea |
| Inner tuning / early stopping | Gene-separated inner partitions from the outer training data only; seed 42; never use the outer validation fold for early stopping and then call its score unbiased |
| Preprocessing | Fit learned parameters using the relevant training partition only |
| Reporting | Preserve per-fold values and label/coverage/motif counts; distinguish development from independent evaluation |

## 7. Standardisation and model-independent ideas

These are candidate experiments for Members 2 and 3, not demonstrated improvements.

| Evidence from this analysis | Candidate change | Fair check |
|---|---|---|
| Pooled and within-motif signal directions differ | Add sequence conditioning or signal-by-motif interactions | Compare on the same held-out genes; examine per-motif behaviour. |
| Label-1 sites have larger typical across-read current IQR | Add robust distribution features: median, IQR, quartiles and selected tails | Hold model family/splits fixed; check benefit after motif and coverage adjustment. |
| A few motifs have almost no positive sites | Share information across motifs, with a fallback for sparse/unseen contexts | Report sparse groups; avoid separate unconstrained classifiers per rare motif. |
| Coverage association differs across datasets | Compare models with/without log coverage and/or use repeated read subsampling | Check both global and coverage-stratified results; do not pick thresholds on the diagnostic dataset. |
| Paired sites can have different labels | Preserve sample identity for provenance and inspect discordant cases | Do not use identity as a label shortcut or average conflicting targets automatically. |
| data2 is a different design and coverage regime | Use it for a separate stress test after clarifying labels | Do not optimise on it while reporting it as independent testing. |

For methods that need numerical scaling, consider logging strictly positive dwell-time features and using `log1p(coverage)`. Fit any centring/scaling on training data only and reuse it unchanged on validation and later data. Median/IQR scaling is one reasonable candidate; standard mean/SD scaling is another. Do not independently standardise each test file, because that changes the deployment rule and can hide dataset shift. Zero-scale features need a defined fallback, such as scale 1.

Motif-conditioned residuals must also use training-only reference statistics. Specify a minimum support threshold and a fallback to a broader context or global training reference before evaluation. A descriptive heatmap based on all EDA sites is not a fitted preprocessing transform for cross-validation.

If class weights or oversampling are used, calculate and apply them within training only. Retain natural label prevalence in validation/test data. Do not change the labels, discard hard cases, or resplit folds in response to poor results.

For uncertainty on future effect estimates, resample genes or biological replicates as appropriate, rather than treating all reads as independent. No inferential confidence intervals or significance tests were produced here.

## 8. Additional data: useful candidates, with separate roles

| Candidate source | Verified availability | Potential role | Checks needed before use |
|---|---|---|---|
| SG-NEx processed direct-RNA data | The official repository provides m6Anet-format JSON data and sample information; its tutorial gives an A549 direct-RNA example [R2, R3]. | Required Task 2 application; coverage and motif shift checks. Labelled compatible samples could support a future external test. | Sample IDs, chemistry, preprocessing, reference, biological replicates and overlap with supplied data. Label availability must be verified sample by sample. |
| HEK293T with knockout and mixture variants | The m6Anet paper identifies ENA PRJEB40872 [R1]. | Potential external or controlled-response diagnostic. | Retrieve the actual files and label provenance; check compatibility and prior reuse. A knockout does not establish that every site/read is a perfect negative. |
| Curlcakes synthetic data | The same paper identifies GEO GSE124309 [R1]. | Potential controlled sequence/modification stress test. | Synthetic design differs from cellular RNA; avoid making it the sole test of cellular generalisation. Do not assume it is data2. |
| m6Anet demonstration data | Official documentation supplies a small example for the software workflow [R4]. | Installation and prediction-format checks. | Too limited and potentially reused to claim a new biological benchmark. |

Only data0, data1 and data2 were analysed at the signal level here. Additional-source availability was checked through official documentation or the original paper; completeness, compatibility and independence have not been established. Unlabelled SG-NEx predictions are not trusted training labels. Member 4 owns the full Task 2 sample inventory and biological comparison; Member 1 can provide the data-quality checks and interpretation cautions above.

## 9. Short report contribution

### Introduction and data-description draft

Our project studies whether nanopore direct RNA sequencing measurements can distinguish sites carrying m6A labels. Each candidate site has a seven-base sequence context and read-level summaries of dwell time, current variability and mean current at three neighbouring positions. The supplied labels describe sites rather than individual RNA molecules. We therefore examined sequence context, read distributions and coverage before proposing model features and evaluation splits.

We analysed 121,838 sites in data0, 90,810 in data1 and 1,323 in data2. The positive-label proportion was 4.49% in data0 and 7.26% in data1. Sequence context substantially affected the observed signal comparisons. Although pooled central current was higher for label-1 sites, it was lower within many individual motifs. Data0 and data1 also shared 67,320 site IDs, including 3,872 with different labels. These findings motivate sequence-aware analysis and gene-based validation. Data2 had repeated sequence contexts across fractional-label groups and much higher coverage, so we considered it separately while its experimental interpretation remains unresolved.

This paragraph describes completed EDA. The report should describe the split in Section 6 as proposed until the modelling team actually follows and documents it.

### Limitations to pass to the integration chat

- data1 has been exposed previously and substantially overlaps data0; it is not an untouched independent test.
- data1 gene mapping and sample provenance are incomplete. data2 label semantics and source templates are unresolved.
- Site-level labels and event summaries do not identify the modification state of each molecule or establish stoichiometry.
- Motif and coverage comparisons are descriptive and contain correlated sites within genes. No causal claims or statistical significance claims follow from them.
- Only candidate DRACH sites with at least 20 reads are represented. No conclusions about excluded motifs, missing sites or lower coverage are supported.

## 10. Files, reproducibility and handoff

The bundle contains:

- This context file and a self-contained HTML reading copy with six figures.
- `figures/01_inventory.png` through `figures/06_data2_groups.png`.
- `tables/data0_site_summaries.csv.gz`, `data1_site_summaries.csv.gz`, and `data2_site_summaries.csv.gz`: all-read site summaries and join metadata; no model predictions.
- Inventory, motif, coverage, within-motif and motif-by-coverage effects, paired-label counts, discordant-site list, data2 template checks, and unusual-case review tables.
- `scripts/extract_sites.py` and `scripts/analyse_sites.py`, plus an explanation of columns and reproducible commands in `README.md`.
- The unchanged shared-fold files and their recorded checksums. Use the provided verifier; do not run generation for a new split.

Hashes identify source inputs and the exact existing fold manifest. Numerical display is rounded; tables retain more precision. No filtered or relabelled training set, pooled fold manifest, model, test score or experimental validation is included.

**Ready to hand over:** the short report paragraph, the motif and signal figures, source tables supporting the numbers, the split proposal, and the limitations above. This is one consolidated Member 1 handoff, not a new team-wide administration process.

**Next questions with the highest value:** What samples and assays generated data1? What exactly do data2 fractions mean, and were reads reused across groups? Which transcript annotation version matches the files? These answers determine whether pooling or a separate external test is defensible.

### Source references

- [S1] Supplied `handout_project2_RNAModifications.html`, sections “Format description”, “Training data”, “Task 2”, and “Project Team Submission Requirements”.
- [S2] Supplied `05_NUS_Genomics_TeamProject_2026.pdf`, page 53 (measurements/labels) and page 55 (split by gene ID).
- [S3] Supplied `shared_folds/README.md`, CSV and metadata; verification rerun successfully on 13 October 2026.
- [S4] Supplied team handoff dated 12 October 2026, for role boundaries and historical data exposure only.
- [R1] Hendra et al. (2022), *Detection of m6A from direct RNA sequencing using a multiple instance learning framework*. Nature Methods. https://doi.org/10.1038/s41592-022-01666-1 ; full-text data-availability record: https://pmc.ncbi.nlm.nih.gov/articles/PMC9718678/
- [R2] Official SG-NEx repository and data access description: https://github.com/GoekeLab/sg-nex-data
- [R3] Official SG-NEx m6Anet data tutorial: https://github.com/GoekeLab/sg-nex-data/blob/master/docs/SG-NEx_m6Anet_tutorial.md
- [R4] Official m6Anet training/demo documentation: https://m6anet.readthedocs.io/en/latest/training.html

External references were checked on 13 October 2026. They establish context and potential sources; all dataset-specific counts above come from the supplied files.

### AI-use and verification note

The assistant inspected the supplied files, wrote and ran the EDA scripts, generated the figures, and drafted the interpretation and split proposal. Member 1 should verify the claims they include in the report. During earlier inspection, an incomplete extracted fold CSV was initially mistaken for an archive defect; re-extraction restored the exact expected checksum, and the intact original file passed verification. The current revision independently verified the exact received fold file. The apparent data2 mixture design remains a hypothesis because the required provenance is absent. These points should remain explicit instead of becoming unsupported statements in the integrated report.


## 11. Member 2 handoff update — 14 October 2026

This revision adds a detailed follow-up plan in MEMBER2_ACTION_PLAN.md and exact column definitions in feature_specification.csv. The plan covers controlled context/coverage comparisons, read-subsampling stability, unusual-case inspection, current-feature auditing and three controlled model comparisons. These follow-ups remain proposed; no new analyses or performance results have been added. Original findings and six figures are unchanged. The ZIP also contains the updated MEMBER2_AI_HANDOFF.md and a START_HERE.md reading guide.
