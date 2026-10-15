# Data methodology for the two model candidates

Status: proposed protocol, 15 October 2026. No new split, training run, cleaning rule or model result has been created under this protocol.

Elgin and Samuel will build separate candidates. Elgin currently intends to explore neural networks; Samuel may enhance LightGBM. These are starting directions, not restrictions. Both candidates must answer the same prediction question on the same eligible evaluation sites.

## Why exploration must change our decisions

Member 1's package provides more than background figures. Its findings should determine which contexts we preserve, which features we test, what quality checks we use, and what our evaluation can claim. The original received package remains the evidence source; its proposed actions are not completed experiments.

| Finding in the received EDA | Consequence for the next design | Controlled comparison or check | Evidence for the report |
|---|---|---|---|
| Pooled current is higher in label 1, but lower within many sequence motifs. | Preserve the seven-base sequence and investigate how signal interpretation depends on sequence. Do not impose one universal current direction. | Compare signal-only, sequence-only and combined inputs where feasible; test a specific context interaction or training-fitted motif reference against the current implementation. Examine per-motif counts and performance. | Motif counts, within-motif effects, and the measured outcome of the comparison. |
| Some motifs have extremely few positive sites. | Share information between contexts and provide a fallback for sparse/unseen groups. Inspect their representation before choosing partitions. | Report positive/negative counts by motif and partition; avoid unreliable subgroup AUC when only one class or very few examples are present. | Counts and limitations alongside motif plots, including groups with weak support. |
| Read distributions vary between sites; unusual broad distributions occur even in label 0. | Retain distribution information; investigate unusual cases before any quality rule. | Compare a justified robust-feature or aggregation change with the current approach. Inspect selected unusual cases against same-context, similar-coverage controls. | Read-distribution examples, actual feature comparison and any rule's exclusions/counts. |
| Coverage relates to labels differently in data0 and data1. | Treat coverage as possible biological/technical context and a possible shortcut. Do not assume including it always helps. | Compare explicit coverage inclusion/exclusion and sensitivity to fewer reads. Keep evaluation prevalence and eligible sites fixed. | Coverage/label plots, subgroup counts and stability results. |
| data0/data1 share 67,320 site IDs, including 3,872 opposing labels; sample provenance is incomplete. | Keep samples and original labels distinct. Establish provenance and gene mapping before considering pooling. | Report shared-site and new-site diagnostics separately, with gene-overlap qualifications. Investigate disagreement without relabelling to force agreement. | Overlap table, label-concordance table and limitations. |
| data2 contains seven fractional-label groups on 189 repeated position/context templates. | Keep its target and grouping separate until official meaning and construction are known. | Initially describe matched-template patterns. Prespecify suitable scoring only after label semantics and source reuse are clarified. | Template structure, coverage difference and explicitly qualified descriptive trends. |

The existing Elgin network already uses sequence-conditioned read processing, attention, and 63 all-read mean/SD/quantile features, including medians and quartiles. Adding these cannot be presented as a new contribution. First compare actual implementations with Member 1's feature specification. A new comparison could remove an existing component to measure its contribution, or test a genuinely different conditioning/robustness method. Samuel should make the same inventory of his actual inputs.

## What the target means

The current target is the supplied site-level m6A label. It is not a true label for each individual read, a direct measurement of modification fraction, or a label for other chemical modification types. Attention weights are not validated modified-read probabilities. A site score is not automatically calibrated as a probability or interpretable as stoichiometry.

Site-read entries are not independent biological replicates. Transcript/gene IDs, dataset identity, processing offsets and fold IDs are metadata for joining and checks, not default predictive inputs. The supplied `start`/`end` columns are not verified biological region annotations.

## Choose the shared evaluation design before training

The main development question is how well a learned predictor handles eligible sites from genes excluded from its fitting. Task 2 asks a further question: how predictions vary across SG-NEx samples and how much evidence supports those differences. A gene split alone does not establish transfer to an unseen cell line.

Both candidate models need the same grouping rule and actual assignments. Gene grouping is justified because sites and transcript isoforms from one gene are related. Randomly separating rows can place closely related examples in both training and evaluation.

The number of folds and train/validation/test ratio are **not selected yet**. They should depend on class/motif/coverage representation, available computation and the remaining time, rather than inheriting a five-fold setting automatically.

Two practical options remain:

- **Grouped cross-validation:** train on some gene groups and validate on the remainder, rotating the held-out groups. This uses limited positives efficiently and shows variation between partitions, but costs more training. Compare models on identical rotations. Hyperparameter tuning and early stopping need separate gene groups inside each round's training portion, or a documented fixed setting decided before scoring that round. Scores used to select models are development results.
- **One fixed gene-grouped training/validation/test allocation:** training learns the model, validation selects settings, and the reserved test is assessed after choices are frozen. This is simpler and cheaper, but one partition may contain too few positives for rare contexts and gives a less stable comparison. Retrospectively separating already explored data does not turn it into a blind independent test.

The original five-gene-fold manifest and its checksum must be retained as historical evidence. It may be reused if its composition and cost suit the new question; it must not be selected merely because it already exists. Any proposed replacement should explain the benefit and keep the old results clearly separate.

A descriptive check of the existing assignments is now complete: [composition audit](eda/split_review/README.md), with gene/class totals, central motif and coverage counts. Overall positive prevalence is balanced, but 8 of 90 motif-by-fold validation groups lack both classes, 38 have fewer than 20 positives, and one training motif/fold has no positive example. These are subgroup-support limitations, not reasons to remove those sites. The audit generated no new assignments and selected no design. Compare feasible designs using this evidence, agree one shared protocol, and export one shared assignment file before either new candidate trains. Do not independently regenerate nominally identical splits.

The assignment file should identify dataset/sample, transcript, numeric position, gene, partition/fold and exclusions where relevant. Record input versions, generation rule, seed, counts and checksum. Keep the shared protocol in this document and implementation in shared code; a separate team-wide administration system is unnecessary.

### Prevent accidental evaluation leakage

- Each evaluated candidate must start from a fresh fit for that partition. The previous final model was fitted on all data0. Warm-starting from it and scoring a held-out data0 subset would leak that subset into the model's history. Historical weights remain useful as an archived predictor, not as a clean starting point for that comparison.
- Fit scalers, motif reference statistics, imputation, feature selection, class weights and calibration only on the permitted training portion. Apply them unchanged to held-out inputs. Do not normalise each evaluation dataset independently to hide a shift.
- Use validation for model selection; use the agreed final assessment only after freezing the model and scoring rule. Report all previous evaluation exposure honestly. Prior EDA and model development have already examined supplied data.
- Keep natural label prevalence in validation/evaluation. Training reweighting or sampling must not alter the evaluation population.
- Define ROC AUC and the exact PR AUC calculation consistently for both candidates. Average precision is a different summary and should be labelled separately. Keep actual scores and subgroup denominators; do not select the easier subset for a better headline number.

## Dataset roles and unresolved questions

**data0:** the present labelled development source, with gene IDs. It contains 121,838 sites and 5,475 positive labels. Inspect context and coverage support when deciding the next shared partitions.

**data1:** 90,810 sites and 6,593 positive labels; already exposed in earlier model comparisons and Member 1's EDA. Only 75,673 sites map to genes through data0, leaving 15,137 sites on 1,019 transcripts unresolved. New site IDs do not prove new genes. Confirm sample/cell line, run, chemistry, preprocessing, assay definition and reference annotation before pooling or claiming independence. A new split cannot erase prior exposure.

**data2:** 1,323 rows, seven fractional-label groups, 189 repeated positions and much higher coverage. Do not round fractions into binary labels, use its transcript IDs as predictors, call rows independent biological replicates, or score all rows with ordinary binary ROC/PR. Official label meaning, construction and possible source-read reuse remain unresolved. A future template grouping would also need to address underlying source dependence.

**SG-NEx:** establish sample/run/cell-line/biological-replicate metadata and reference compatibility. Missing sites are not negative sites. Coverage and RNA abundance can change which sites are observed. These application predictions do not become trusted training labels simply because a model produced them.

**Future official/eligible external evaluation:** verify provenance and overlap and reserve it from selection if an independent generalisation assessment is intended. None has been established by the received EDA package.

Pooling data0 and data1 is a possible later experiment, not the default. It requires resolved compatibility and gene grouping across both sources. Keep every copy of a held-out gene outside training, preserve distinct samples and original labels, and compare augmentation against data0-only training on identical eligible validation targets. Do not majority-vote away conflicting labels.

## Quality handling that remains defensible

Member 1 reports complete joins, positive finite nine-value read vectors and no duplicate site keys. Those structural checks do not establish perfect alignments, labels or biological independence. No technical outlier-exclusion rule has been validated.

Before exclusions, define a measurable technical criterion and its reason, check counts and affected contexts, and preserve an audit of original and eligible populations. A rule learned from data must be fitted using training only. Where feasible compare keeping versus applying a proposed rule, and report excluded or unscorable sites rather than quietly dropping them from evaluation.

Low coverage and rare motifs deserve separate counts and diagnostics. All supplied sites have at least 20 reads; behaviour below that is unsupported. Do not discard difficult sites because of poor predictions, change their labels to match the model, or treat an unusual distribution as proof of error. Fixed extreme-value clipping, if proposed, also needs a justified comparison and training-only thresholds when estimated.

Read-subsampling stability and individual-read case reviews in Member 1's action plan remain unrun. They may guide robustness choices; repeated reads are not biological replication and the all-read summary is a reference estimate, not ground truth.

## What we retain and report

Keep one concise results file in each model folder, backed by configurations, commands, input/split identifiers, actual per-partition metrics, prediction scores, computation measurements, checkpoints and logs. Record failures and rejected changes as well as improvements. Model selection should consider the agreed metrics, stability, coverage/context weaknesses and reproducibility alongside runtime.

For each meaningful change, the report needs: **EDA observation → modelling/data decision → controlled result → interpretation and limitation**. The report should describe the protocol actually executed; proposals in this document are not results. The final evaluation folder will hold the selected model's verified comparisons, including the required simple baseline and m6Anet evidence.

## Evidence inspected

- Received `Other members work/Member1_Analysis_Package/Member1_Analysis/`: context, handoff, action plan, feature specification, scripts, tables, six figure files, manifest and shared-fold files.
- All 43 listed package hashes matched during the read-only review. The packaged historical fold CSV matches the original SHA256 `986b7872084cf762f1c3944b1eacc1e8f1ff69cb2848630f80685063541da9b0`.
- Small supplied-table totals and motif/coverage effect-direction counts were independently recomputed. Raw signal parsing was not rerun in that review.
- Existing Elgin `advanced_model/model.py`, `data.py` and `train.py` were inspected to distinguish existing functionality from proposed additions.
- Consult the supplied course handout for official deliverables. The package recommendations and this document do not replace it.
