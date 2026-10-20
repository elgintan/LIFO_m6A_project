# Task 2 model information — Member 4

**Status: PENDING_TEAM_SELECTION. No final whole-run SG-NEx predictions have been supplied.**

## Received Member 3 candidate (real checkpoint, not yet selected)

- Candidate identifier: `member3-lgbm-ba268645ed3f`.
- Method: LightGBM on 63 read-distribution summaries relative to a training-fitted 7-mer/5-mer/global reference, plus seven categorical sequence bases. Read count is not an input feature, but affects estimation precision and observed performance.
- Model: `member3_candidate/artifact/model.txt`.
- Model SHA256: `ba268645ed3fa6c19f59f6a83ed85c794c7b19975d4e474551d211ef78406bb1`.
- Sequence reference: `member3_candidate/artifact/kmer_baseline.csv`.
- Reference-table SHA256: `ae1e45448a1eb6ca0863e0764b74a529b24b7586a6497883392667f3cf3c93cc`.
- Model card: `member3_candidate/artifact/model_card.json`; recorded frozen time `2026-10-18T07:34:35Z`.
- Training source SHA256: `622410b2918692b75a880b753f1a621e8d892d6dbc13c1f430babc5543a0584e`.
- Label-file SHA256: `6758f002db36835c188c9d6fb039b4599494ca9dcc816c26cc22a2c04ee42978`.
- Existing data0 gene-fold SHA256: `986b7872084cf762f1c3944b1eacc1e8f1ff69cb2848630f80685063541da9b0`.
- Training/evaluation context: five data0 gene-group development folds; final fit on all data0. Data1 was exposed during feature selection and is an exposed transfer diagnostic, not a blind test. The supplied metrics and output hashes match the checks recorded in results/member3_metrics_check.json; training was not rerun here.
- Saved preprocessing is applied unchanged to later data. Do not fit a new 7-mer reference separately in each cell line. Fallback is 7-mer with >=50 training sites, then central 5-mer, then global mean.
- Original prediction script: `member3_candidate/code/predict.py`. Locally reproduced the supplied 10-site example byte for byte with LightGBM 4.7.0, numpy 2.4.6 and pandas 3.0.6. This is a Linux software smoke test, not a full SG-NEx or fresh AWS Ubuntu test.
- Member 4 batching adapter: `scripts/predict_member3_run.py`; preserves the received feature method/checkpoint. Use the README command and retain receipt plus site metadata. Default minimum is 20 finite reads; nonfinite-read removal is audited. No random read subsampling or model refit is performed by this adapter.

## Fields to complete before final Task 2 comparisons

- Selected model/checkpoint and selection evidence: **PENDING**. Do not automatically promote this candidate based on its arrival.
- Final model code commit and feature/prediction versions: **PENDING**. Candidate source checksums are in metadata/member3_source_receipt.json.
- Actual per-run input JSON/public source and SHA256: **PENDING**; original count sources/hashes are already available in results/public_readcount_verification.csv.
- Exact alignment/event-preprocessing versions for those inputs: **PENDING**.
- Exact reference FASTA/GTF release/hashes: **PENDING**. SG-NEx documentation reports GRCh38/Ensembl91; this does not by itself verify the candidate training or each event input.
- Meaning of transcript_position, 0/1-based convention, candidate-adenosine and seven-base offsets: **PENDING**. Preserve original values until checked; no biological coordinate shift is assumed.
- Transcript-ID aliases: explicit per-run table metadata/transcript_aliases_checked.csv. Annotated MCF7 version matches were checked against supplied annotation metadata; unverified reference identities stay flagged. Exact FASTA reconstruction remains pending.
- Final agreed eligibility/minimum-read rule and unscorable-site reasons: **PENDING**; proposed analysis rule is >=20 finite reads, with coverage sensitivity and >=2 groups per line.
- Actual per-run inference commands, software/seed/thread settings and output hashes: **PENDING**; the adapter writes receipts when genuinely run.
- Calibration or independent assay validation: **not supplied**. Site scores do not establish modified-molecule fractions.

The development CSVs under member3_candidate/outputs/ and the ten-site example do not substitute for full SG-NEx run predictions. No causal, stoichiometry or final biological finding follows from this model card alone.
