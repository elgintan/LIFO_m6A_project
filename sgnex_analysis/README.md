# SG-NEx analysis: 23 processed runs

This folder integrates Member 4's code and scientific handover. The agreed population is **23 m6Anet-processed direct-RNA runs, seven cell lines and 17 replicate-number groups**. The broader 56-row inventory is background; expanding to it is not required for the current task. Conclusions must describe the processed subset.

**23 October:** Member 4's coverage foundation is integrated. Elgin's frozen
cap128/weight3 neural model is selected. The first full signal input passed
strict validation and exact coverage-key/count agreement, and a real small
adapter/predictor parity check passed. The first run's135,870 predictions are
complete and independently verified; the full23-run workflow is running.
Biological comparisons and interpretation remain unfinished.
See [the execution design](TASK2_EXECUTION_PLAN.md) and
[selected model information](MODEL_INFO.md).
See [actual first-run QC](first_prediction_qc/README.md),
[training-context evidence](training_context_support/README.md) and
[the sequential runner/resume guide](ELGIN_TASK2_RUNNER.md).

Read [findings.md](findings.md), [REFERENCE_STATUS.md](REFERENCE_STATUS.md) and [INTEGRATION.md](INTEGRATION.md). Original source evidence is preserved in [the received handover](provenance/member4_20261019/HANDOFF.md); its original package-relative commands differ from the integrated commands below. Older Explorer modification scores were simulated and are excluded from the coverage analysis.

## Files and storage

- `scripts/`, `tests/`, `requirements.txt`: analysis/verification code and small checks.
- `metadata/sample_manifest.csv`: the exact 23 runs, group mapping, public signal links and saved object sizes. Signal JSONs total **33,365,823,342 bytes** (33.37 GB); they are not bundled.
- `manifest.csv`, `MODEL_INFO.md`: selected-model handoff. Exact historical reference/preprocessing and nucleotide offsets remain unverified. Coverage and prediction paths use ignored `outputs/`.
- `outputs/received_member4_20261019/`: local received coverage, annotations, aliases, figures, guides and logs. These are retained on the laptop, not public site-level data uploads.
- `outputs/predictions/`: future three-column per-run CSVs and receipts.
- `provenance/member4_20261019/`: unchanged original handover, scientific/report/AI-use evidence and source inventory. This inventory describes the received package, including deliberately unpublished files.

The optional Member 3 adapter uses the canonical sibling `model_samuel/`. Its model, examples and development outputs are not duplicated here. An explicit `--candidate-dir` can identify another received local snapshot.

## 1. Setup and small checks

Run every command below from the **repository root**, the folder containing `model_elgin`, `model_samuel` and `sgnex_analysis`. A virtual environment is a folder containing an isolated Python installation and libraries.

On the current laptop use the existing analysis-capable environment:

```powershell
$py = "../advanced_model/.venv/Scripts/python.exe"
& $py -B -m unittest discover -s sgnex_analysis/tests -v
```

The analysis/reference/restoration checks use small temporary synthetic fixtures. The optional Member 3 test uses its ten-site installation example only if its files and LightGBM are available; otherwise it reports a skip. Passing tests verifies software behaviour, not biological accuracy or genuine reference compatibility.

The current laptop also has the canonical Member 3 prediction environment. Run that adapter check separately in it:

```powershell
& "model_samuel/.venv/Scripts/python.exe" -B -m unittest discover -s sgnex_analysis/tests -p test_member3_prediction.py -v
```

This separately passed the ten-site score-parity, minimum-finite-read eligibility and duplicate-refusal checks. It is not whole-run SG-NEx inference.

In the current restricted runner, system temporary/cache folders were not writable. The successful retry used workspace-local folders before the same test command:

```powershell
New-Item -ItemType Directory -Force sgnex_analysis/outputs/checks/tmp,sgnex_analysis/outputs/checks/.mplconfig | Out-Null
$taskTemp = (Resolve-Path sgnex_analysis/outputs/checks/tmp).Path
$env:TEMP = $taskTemp
$env:TMP = $taskTemp
$env:TMPDIR = $taskTemp
$env:MPLCONFIGDIR = (Resolve-Path sgnex_analysis/outputs/checks/.mplconfig).Path
& $py -B -m unittest discover -s sgnex_analysis/tests -v
```

For a new Windows analysis environment instead:

```powershell
py -3.12 -m venv sgnex_analysis/.venv
& "sgnex_analysis/.venv/Scripts/python.exe" -m pip install -r sgnex_analysis/requirements.txt
```

Then set `$py` to `sgnex_analysis/.venv/Scripts/python.exe`. On Ubuntu use `python3.12 -m venv sgnex_analysis/.venv` and `sgnex_analysis/.venv/bin/python -m pip install -r sgnex_analysis/requirements.txt`. A clean Ubuntu installation was not verified in this integration. Keep the received analysis pins separate from Member 3's prediction environment.

## 2. Restore the received local coverage evidence

The public folder keeps code and small source manifests. Supply the original extracted `Member4_Analysis` package to restore large tables locally. On the current workspace:

```powershell
& $py -B sgnex_analysis/scripts/restore_received_data.py --source "../Other members work/Member4_Handover_extra details/Member4_Analysis"
```

On another computer replace `--source` with its extraction folder. The helper checks received sizes/SHA256, copies metadata/results/figures and the two reading guides into `sgnex_analysis/outputs/received_member4_20261019/`, and records a local receipt. SHA256 is a content fingerprint for detecting changed files. Repeating the command reuses identical evidence and refuses differing existing files. It performs no download, prediction or scientific reconstruction, and excludes the nested candidate.

Expected files include `results/coverage_matrix_ge20_union.csv.gz`, `results/site_annotations.csv.gz` and `metadata/transcript_aliases_checked.csv` beneath that local destination. Its HTML/notebook describe the received coverage work; the notebook's real-analysis cell remains disabled. Original logs retain historical preparation paths, not required paths on this laptop.

## 3. Genuine signals and selected-model predictions

Obtain one run first, then validate its full input against inherited coverage:

```powershell
$signals = "sgnex_analysis/outputs/signals"
& $py -B sgnex_analysis/scripts/download_signal_inputs.py --dest $signals --run-id SGNex_Hct116_directRNA_replicate3_run4
& $py -B sgnex_analysis/scripts/audit_elgin_input.py --input "$signals/SGNex_Hct116_directRNA_replicate3_run4/data.json" --run-id SGNex_Hct116_directRNA_replicate3_run4 --output sgnex_analysis/outputs/preflight/first_full_input_audit.json
```

The helper uses the fixed public HTTPS inventory without AWS credentials.
Interrupted `.partial` downloads restart; byte-range resume is not implemented.
The first actual download and full audit completed on 23 October:
1,302,514 sites / 15,133,352 reads, with exactly 135,870 eligible >=20-read
sites matching Member 4. Size/count agreement is not independent upstream
SHA authentication or proof of exact historical reference identity.

The selected-model adapter checks **every** source site, including low-coverage
ones, and copies eligible original JSON record bytes verbatim into gzip before
calling the unchanged predictor. All available reads are used at each eligible
site. All-source QC/sequence/count metadata records why others are unscored.

```powershell
& $py -B sgnex_analysis/scripts/predict_elgin_run.py --input "$signals/SGNex_Hct116_directRNA_replicate3_run4/data.json" --run-id SGNex_Hct116_directRNA_replicate3_run4 --output sgnex_analysis/outputs/predictions/SGNex_Hct116_directRNA_replicate3_run4.csv --min-reads 20 --threads 4
```

Nine targeted contract tests passed. A real 1,024-source-site probe scored
95 eligible sites / 51,056 reads, with maximum score difference 1.49e-8 from
the unchanged predictor on the original source (tolerance 3e-6). This checks
software parity, not biological accuracy. Completed adapter runs can be reused
only when every input/model/code/output fingerprint matches. Partial work is
preserved and requires a fresh output filename; completed runs, rather than
individual partial CSV batches, are resumable.

Use one selected saved checkpoint and its unchanged trained preprocessing across all runs. The interface is exactly:

```csv
transcript_id,transcript_position,score
```

Preserve original IDs/positions, unique keys, finite scores in `[0,1]` and full
precision. The `.model_export.csv` preserves the core's complete **eligible-input**
export; the Task 2 CSV is byte-identical. Low-coverage source sites remain in QC
metadata and the raw source. Investigate unmatched keys and finite-read failures
rather than silently dropping malformed reads or calling missing scores zero.

This optional command is specific to the received Member 3 candidate, **not final selection or an adapter for another checkpoint**. Use its documented prediction environment and canonical files:

```powershell
$member3py = "model_samuel/.venv/Scripts/python.exe"
& $member3py -B sgnex_analysis/scripts/predict_member3_run.py --candidate-dir model_samuel --input "$signals/SGNex_Hct116_directRNA_replicate3_run4/data.json" --run-id SGNex_Hct116_directRNA_replicate3_run4 --output sgnex_analysis/outputs/predictions/SGNex_Hct116_directRNA_replicate3_run4.csv --min-reads 20 --batch-sites 512 --threads 4
```

The current laptop already has this environment, prepared during canonical candidate integration. A fresh clone still needs the candidate's documented prediction setup. The adapter uses saved references without per-line refitting and audits raw/finite read counts. Malformed, duplicate or no-finite-read sites abort a run. Existing outputs are refused; failed partial inference does not resume automatically. Successful CSV, metadata and receipt files retain candidate status independently of any later team selection. Full-run runtime/RAM are unmeasured. For another selected model use its own predictor; no universal model/export adapter is supplied here.

## 4. Compare real predictions after prerequisites are complete

The active manifest identifies the selected artifact consistently across
23 rows. Its reference string records upstream-reported but unverified
provenance, not established FASTA identity. Full comparisons still need actual
CSVs, matching coverage, aliases, cross-run context checks and provenance review.
Missing prediction files cause failure. A real-input declaration does not
establish biological validity.

```powershell
& $py -B sgnex_analysis/scripts/compare_predictions.py --manifest sgnex_analysis/manifest.csv --model-info sgnex_analysis/MODEL_INFO.md --coverage-matrix sgnex_analysis/outputs/received_member4_20261019/results/coverage_matrix_ge20_union.csv.gz --annotations sgnex_analysis/outputs/received_member4_20261019/results/site_annotations.csv.gz --aliases sgnex_analysis/outputs/received_member4_20261019/metadata/transcript_aliases_checked.csv --confirm-real-predictions --out sgnex_analysis/outputs/real_analysis_v1
```

Use a fresh output directory, including after failure: the received CLI creates it before validation. Missing expected predictions cause failure. `--allow-missing-predictions` is for a documented incomplete exploratory population; missing scores never become zero.

Defaults are coverage **20/50/100**, >=**2** groups per line, score displays **0.5/0.7/0.9**, and candidate differences with `|delta| >=0.2`, separated group score ranges and geometric-mean coverage ratio <=**2**. Average eligible runs within group, then equally weight groups. A stricter run adds `--require-all-replicates` with another output directory. These are descriptive choices, not calibrated chemical calls, significance tests or false discovery control.

Future outputs include group/line means, separate pairwise/all-line common populations, all 21 pair tables, missingness, depth/threshold sensitivity, agreement, coverage diagnostics, a receipt and a paired-score plot. None of those real-score outputs exists from this integration. The bundled annotation has no motif column; motif summaries require a verified context join. Genomic mapping, expression adjustment, subsampling, formal differential testing, pathway analysis and Explorer display export are not implemented by this command.

Describe replicated **predicted patterns**, retaining conflicting examples. Scores are not individual-read labels, modified-molecule fractions, other modification types or causal cell-line effects. Common-site selection, sequence preference, chemistry/batch, abundance and isoforms limit interpretation. Replicate-number labels do not independently prove separate laboratory preparations.

The laptop can continue from Member 4's code. Selection is complete; real
predictions, remaining input/reference checks, comparisons and display
integration continue within the same 23-run scope.
