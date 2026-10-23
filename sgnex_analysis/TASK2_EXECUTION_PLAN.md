# Task 2: from Member 4's coverage evidence to actual predictions

Current update, 23 October: all 23 runs completed and passed verification at
05:46:47 SGT, exit0, with 2,983,948 scored run-site observations. The original
plan below describes the completed application procedure; it is not a request
to repeat downloads or inference. Cross-run context QC now precedes scientific
comparison; see [its fixed rules](CROSS_RUN_CONTEXT_QC_PLAN.md). No biological
conclusion follows merely from completion.

The chain is **Member 1's training-data EDA -> frozen Task 1 model -> Member 4's
run/coverage/reference design -> real predictions -> replicate-aware analysis
-> Member 5's explorer and scientific report**. The model is not retrained on
unlabelled SG-NEx signals.

## Fixed application design

1. Retain all23 processed runs. Download one first; validate the full raw
   nine-feature input and original read counts against Member4's matrix.
   Preserve raw input/source hashes and original IDs.
2. Check every source site, including low-coverage sites. Prepare eligible
   original JSON records with >=20reads and retain all-site QC with reasons
   for unscored sites. Do not remove difficult valid eligible sites.
3. Use the same frozen `elgin-cap128-weight3-18epoch-b2d38ff29a91` artifact, with all
   reads and unchanged transformations. Save full-precision three-column CSVs,
   source/eligible counts, context, commands, resources and hash receipts.
4. Check the first real small adapter example against the unchanged predictor,
   then the whole run's coverage and metadata before continuing sequentially.
   Reuse completed runs only after provenance matches; preserve partial evidence.
5. Check cross-run context consistency and sparse positive-label training
   support before biological comparison. Retain difficult/conflicting cases as
   explicit diagnostic groups. Exact genomic mapping remains separate.
6. Analyse annotated-human common sites with >=2metadata groups per line;
   average eligible run scores within group and then groups equally. Keep
   pairwise and all-line populations, read-depth/threshold sensitivity and
   missingness. Missing scores never become zero.
7. Connect actual results to Member5's validated explorer and report figures.
   Any hosted subset must disclose selection and omissions. Predictions do not
   become independent assay labels merely because they are plotted.

## Decisions directly supported by Member 4

Her451,352-key union is not a universally comparable population. The inherited
annotated all-line panel with >=2groups/line has33,452sites at20reads,
11,560at50 and5,058at100. These are **coverage denominators, not modified-site
counts**. They motivate matched-site populations, equal group weights and
sensitivity analyses. Real-input/context checks may change eligibility.

First run,Hct116replicate3run4: all1,302,514source sites/15,133,352reads passed
strict parsing and exact Member4 coverage agreement. Eligible counts are
135,870/50,332/21,438at20/50/100reads. Local evidence:
`outputs/preflight/first_full_input_audit.json`; the audit performs no prediction.
Its18central5 motifs and288possible canonical7mers were all present in data0
training. Sparse positive-label support in some motifs is a separate limitation.

## Remaining interpretation and software gaps

Exact historical FASTA/GTF/preprocessing and nucleotide/event offsets are not
established. Metadata groups are not independently confirmed laboratory
preparations. Compare literal matching keys with documented aliases and
contexts; withhold genomic/chemical/causal claims. No formal differential test,
calibration or independent assay validation has been supplied.

Use the existing0.5 working reporting cutoff, descriptive0.7/0.9 sensitivity
and continuous-score comparisons. These are not biological thresholds or
controlled false-discovery rates. Unusual scores do not become training labels.

The local Docker backend crashed before Ubuntu execution. The same isolated
[Ubuntu check recipe](../model_elgin/reproducibility/README.md) later passed on
a hosted Ubuntu24.04 runner with exact pins and ten-site numerical parity;
[actual evidence](../model_elgin/ubuntu_prediction_results_2026_10_23/README.md)
is retained. Fresh AWS-host verification remains open.
New unlabelled final-test inputs/instructions are a separate outstanding Task1
submission requirement.
