# Task 2 selected model and interpretation limits

**23 October 2026: model selected; full 23-run predictions and biological comparisons are not complete.** Samuel's received LightGBM remains comparison evidence; it is not the selected Task 2 application model.

## Frozen model

- Identifier: `elgin-cap128-weight3-18epoch-b2d38ff29a91`.
- Artifact: `../model_elgin/artifacts/cap128_weight3_v1/model.pt`.
- SHA256: `b2d38ff29a918cb6213ad7df2c76786c5f56d3640bd055ff179d211b0e979668`.
- Model/code release: main commit `e9dddcd5bb6cf67019445b2ac7252645ba9e8d78`.
- Method: sequence-aware attention multiple-instance neural network, with a seven-base embedding, read encoder, attention/mean/SD pooling and 63 all-read distribution summaries. The extra relative-reference branch is off.
- Training: fresh weights and normalisers fitted on all121,838 data0 sites for18 prescribed epochs, seed2026, positive loss weight3 and training read cap128. No data1, data2 or SG-NEx fitting or per-cell-line normaliser fitting.
- Prediction uses the unchanged saved transformations and **all reads at each eligible site**. A20-read eligibility rule does not mean sampling20 reads.
- Training input SHA256: `622410b2918692b75a880b753f1a621e8d892d6dbc13c1f430babc5543a0584e`.
- Training label SHA256: `6758f002db36835c188c9d6fb039b4599494ca9dcc816c26cc22a2c04ee42978`.
- Shared gene folds SHA256: `986b7872084cf762f1c3944b1eacc1e8f1ff69cb2848630f80685063541da9b0`.
- [Fixed selection decision](../model_elgin/FINAL_MODEL_SELECTION.md) and [actual Task1 results](../model_elgin/final_cap128_results/results.md).

## How Member4's findings affect execution

Use exactly the23 processed runs in `metadata/sample_manifest.csv`: seven cell lines and17 metadata replicate groups. Score sites with >=20 source reads and retain an explicit QC record for lower-coverage sites. Do not treat unscored/missing sites as negatives. Check every raw site/read for valid shape, context and finite values, including sites below the coverage rule.

Use50/100-read sensitivity analyses and at least two metadata groups per line. Average eligible runs within a group, then weight groups equally. Compare matching eligible sites, with separate pairwise/all-line populations. Keep valid unusual sites; review coverage, context, agreement and technical explanations before biological interpretation.

Each actual run must retain original input/model/code hashes, source/eligible counts, three-column predictions, all-site QC/context metadata, derived eligible input, console log and completion receipts. No per-run normalisation or calibration is fitted. The0.5 working threshold is a reporting convention; continuous scores drive primary exploration.

## Input and reference evidence

The first downloaded run, `SGNex_Hct116_directRNA_replicate3_run4`, is1,495,098,391bytes, SHA256 `9a745cfa717474a7d46ad8e52198e6640283e5a8e3beb2406530104d330166bd`. Its full strict-parser audit checked1,302,514sites/15,133,352reads. The >=20 keys/counts agree exactly with Member4's matrix:135,870at20reads,50,332at50 and21,438at100. All contexts in this run have unambiguous centralA. No inference was performed by that audit.

The nine supplied measurements are dwell time, signalSD and mean signal for three neighbouring events, in their existing order. Upstream material describes this format; matching shape/counts does not establish every historical preprocessing version. Do not silently drop a possible tenth metadata column in another run; a format change requires a separately audited adaptation.

`reference_version=GRCh38_Ensembl91_upstream_reported_unverified` records the upstream report, **not independently established FASTA/GTF identity**. Preserve literal transcript IDs/positions. Exact reference composition, event-generator version and nucleotide origin/window offset remain unverified. Apply only Member4's explicit per-run aliases inside analysis, preserving raw prediction IDs; do not generally strip transcript versions. Cross-run sequence context consistency must be checked before pooling literal-site comparisons.

Sources: [official SG-NEx m6Anet tutorial](https://github.com/GoekeLab/sg-nex-data/blob/master/docs/SG-NEx_m6Anet_tutorial.md), [official access documentation](https://github.com/GoekeLab/sg-nex-data/blob/master/docs/AWS_data_access_tutorial.md). See [reference evidence and limits](REFERENCE_STATUS.md).

## Training-context support

Read-only checks of data0's fingerprinted sequence cache and Member1's motif summary confirm all18central5 motifs and all288canonical seven-base contexts were present in training (minimum39sites per7mer). Therefore the first eligible run has no unseen canonical context. This is feature support, not proof of equally accurate motif predictions.

AAACC,TAACA andTAACC have fewer than20positive training labels each. They account for15,708/135,870(11.561%) of the first run's eligible sites. Flag their sparse positive-label validation support in later subgroup analysis; retain predictions and valid unusual sites. Do not incorrectly label these motifs as unseen or remove them to improve results.

## Claims supported and not yet supported

Native Windows Task1 prediction is verified. Clean Ubuntu/AWS execution is still unverified; Docker failed before Linux execution. Metadata replicate labels do not independently establish separate laboratory preparations. No compatible independent Task2 assay validation was supplied.

Results may describe replicated **predicted m6A patterns** on the documented population. They do not establish modified-molecule fractions, other RNA marks, chemical nucleotide/genomic coordinates, causal lineage effects or formal differential-modification significance. Coverage/common-site/context selection and possible training-cell-line overlap remain explicit limitations.
