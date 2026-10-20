> Current handover (19 October 2026): read `HANDOFF.md` at the package root. The working scope is the 23 processed runs. The 56-row broader metadata is background, with no expansion required by this handover. Historical commands/status below may be superseded.

# Member 3 candidate: implications for Member 4

Received and reviewed 19 October 2026. This updates the older statement that no new candidate was available. **It does not establish team final selection or completed SG-NEx application.**

## Received evidence and actual checks

Member 3 supplied a LightGBM checkpoint, saved sequence-reference table/model card, prediction/training/feature code, ten-site public-data example, data0 out-of-fold scores, data1/data2 scores, official/local metric records, seed summaries and subgroup tables. The archive passed its integrity check. The copied snapshot uses numbered member labels; original/copy hashes and the original archive SHA256 are retained in metadata/member3_source_receipt.json. Checkpoint and baseline bytes are unchanged.

The model hash is ba268645ed3fa6c19f59f6a83ed85c794c7b19975d4e474551d211ef78406bb1; baseline hash is ae1e45448a1eb6ca0863e0764b74a529b24b7586a6497883392667f3cf3c93cc. Both match the supplied model card. The archived data0/data1 prediction hashes also match their metric records.

Actual original-example run (from an arbitrary working directory, with absolute paths resolved):

```bash
python member3_candidate/code/predict.py --input member3_candidate/examples/input_10_sites.json --output /path/to/new_example.csv
```

This reproduced the ten-row expected CSV byte for byte with zero score difference. The original sample is identified by Member 3 as SGNex_Hct116_directRNA_replicate3_run4. A ten-site installation fixture is not a representative biological sample or a complete run. Local execution was Linux, Python 3.12.14, LightGBM 4.7.0, numpy 2.4.6 and pandas 3.0.6, installed in a separate environment. It was not a fresh AWS Ubuntu installation and training was not repeated. The model card describes the source training environment, while evaluation JSONs describe the source evaluation environment; do not conflate those records with this verification environment.

ROC AUC, trapezoidal PR AUC, average precision and S were recomputed by joining supplied scores to Member 1's derived label tables. Exact shared fold assignments were checked for the data0 outputs. Recomputed values matched supplied metrics within 1e-12:

| Evaluation population | ROC AUC | Trapezoidal PR AUC | AP | S |
|---|---:|---:|---:|---:|
| data0 mean of five gene folds | 0.921897 | 0.498996 | 0.499566 | 0.710446 |
| data1 exposed transfer | 0.821764 | 0.382879 | 0.383071 | 0.602322 |

Evidence: results/member3_metrics_check.json, member3_example_check.json and readme_member3_tests.log. Numerical agreement verifies the supplied scores/metrics; it does not independently prove training exclusions, assay truth, calibration or final selection. Source labels were derived Member 1 tables, not reparsed raw assay files.

## How the candidate changes Member 4's workflow

- A real frozen candidate is now available for a labelled exploratory SG-NEx run. No fresh model training is needed for inference. The team must still select one pipeline before final comparisons; the other candidate has not been evaluated head-to-head here.
- Its 63 numeric features are mean, population SD and five read-distribution quantiles for nine event measurements, expressed relative to training-fitted sequence references. Seven sequence bases are categorical. It has no explicit read-count feature, but read depth changes feature precision and measured subgroup performance.
- Do not replace those saved reference values with per-cell-line normalisation. Sparse 7-mers use a 5-mer and then global fallback; the batching adapter writes fallback levels so unfamiliar contexts remain inspectable.
- The original predictor collects site summaries for the whole input before scoring. The new adapter processes bounded site batches with the same received feature code and saved reference/model; global duplicate keys are tracked in a temporary SQLite database. It never creates a different per-batch or per-line baseline. Tests show it reproduces the supplied example at batch size three and correctly filters the minimum finite-read subset.
- The source feature reader discards nonfinite reads and rejects a site without any complete finite read. The adapter records input versus finite counts and omitted <minimum sites; a discrepancy from public coverage is an auditable quality issue, not permission to label missing predictions zero.
- No full SG-NEx signal JSONs or 23 per-run prediction files were included. The supplied data0/1/2 CSVs remain development/transfer/stress evidence under member3_candidate/outputs/, distinct from predictions/<run_id>.csv.

## Scientific qualifications preserved

The received README discloses that data1 was printed during feature development. It is an exposed transfer diagnostic. Data0 folds also supported historical feature/configuration selection, so mean-fold scores remain development evidence. Do not compare these records with an archived neural result as if both were newly fitted under identical conditions.

Subgroup records report zero recall at cutoff 0.5 for several motifs, including GAACA, GAACC and TAACT, despite nonzero positive counts. The >200-read group has weaker ROC AUC (~0.857) than the other reported coverage groups. These are development diagnostics, not SG-NEx biological effects. Keep continuous scores, motif awareness, depth/support sensitivity and conflicting examples; do not discard those sites to improve a headline result or assume more reads always yield better model accuracy.

The incoming prose links synthetic data2 behaviour to modified fraction. The file structure and fractional labels alone do not establish experimental stoichiometry. Here it is treated as a descriptive response across supplied fractional-label groups: mean scores are ~0.027 at label 0 and ~0.276 at label 1, not estimates of those fractions. Preserve the original observations but keep chemical interpretation unresolved without source-protocol evidence.

The supplied README raises a precision-recall convention issue for tied/constant scores. This update does not change the team's scorer. Distinguish trapezoidal PR AUC from AP and retain both; any metric-policy change belongs with Members 2/3. It does not convert predictor agreement into independent validation.

## Remaining gates before final Task 2 interpretation

Team final selection; agreed full sample scope; exact per-input reference/coordinates/chemistry and event preprocessing; actual whole-run predictions plus receipts; missing-site/finite-read audit; replicate-balanced continuous comparisons; independent labels/calibration evidence if claimed. MODEL_INFO.md and manifest.csv retain pending fields until these are genuinely supplied. No automatic candidate promotion, retraining, external publication or paid-cloud action occurred.

The metric check can be reproduced when Member 1's derived tables/folds are available. It needs scikit-learn as well as the analysis dependencies; the original candidate's full requirements describe its source evaluation environment. Use the team's evaluation environment or install the compatible scikit-learn available there without mixing prediction and analysis pins:

```bash
python scripts/check_member3_metrics.py --data0-labels /path/to/Member1_Analysis/tables/data0_site_summaries.csv.gz --data1-labels /path/to/Member1_Analysis/tables/data1_site_summaries.csv.gz --folds /path/to/Member1_Analysis/shared_folds/data0_folds.csv --output /path/to/new_metrics_check.json
```
