# Task 2 coverage findings and pending real-score work

The agreed population is 23 processed SG-NEx runs, seven cell lines and 17 replicate-number groups. This is a processed subset; expanding to the broader inventory is not required by the current working scope.

The received matrix has 451,352 unique transcript-position keys reaching 20 reads in some run, including 437,320 in the inherited annotated-human category. It contains 2,983,948 run-site observations at >=20 reads, not that many unique sites. Member 4's saved receipts report agreement against all 23 public read-count files, totalling 659,329,250 bytes. The receiving laptop independently recounted the retained derived matrix; it did not redownload those files.

| Minimum reads | Common to all seven lines: >=1 group/line | >=2 groups/line | Every listed group/line |
|---|---:|---:|---:|
| 20 | 59,224 | 33,452 | 26,024 |
| 50 | 20,535 | 11,560 | 9,429 |
| 100 | 8,814 | 5,058 | 4,300 |

These annotated-human denominators were independently reproduced during the read-only package audit. A group passes when at least one run passes coverage. These are comparison populations, not modified-site counts. Model/finite-read failures may reduce them. An absent candidate does not prove zero expression or an unmodified site.

Public-source manifests, scientific code and original report/AI-use evidence are integrated. All 89 hashes in the latest package inventory matched the received files. Large tables, figures and original logs remain local under ignored `outputs/received_member4_20261019/`; local checks are recorded in INTEGRATION.md.

**23 October: the first selected-model run is complete; the full23-run
collection and biological comparisons are not.** Hct116rep3run4 has135,870
verified eligible scores from the frozen Elgin model. The sequential workflow
is running; see [first-run QC](first_prediction_qc/README.md). The older Member3
checkpoint/example remains comparison evidence. Historical Explorer modification
scores were simulated and excluded from coverage and current prediction work.

Next, apply one selected frozen model consistently after input/reference checks, then compare within-group run means and equally weighted group means on common-site populations. Preserve effects that weaken under depth/support controls and overlapping replicate ranges. Descriptive score cutoffs/difference screens are not calibration, significance or stoichiometry.

Exact FASTA/GTF content, event offsets and independent preparation provenance remain unresolved. Motif, region/genomic, abundance/pathway and orthogonal-assay interpretation require additional evidence. Conclusions must concern predicted patterns with technical and observational limitations. The unchanged original contribution is retained in `provenance/member4_20261019/findings.md`.
