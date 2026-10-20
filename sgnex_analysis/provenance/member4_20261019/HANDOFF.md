# Member 4 SG-NEx handover

Prepared 19 October 2026 for the receiving integration owner (Member 5). Member labels are numbered throughout. **This is the current handover; it supersedes earlier run instructions and scope requests in dated notes.**

## 1. Status and working scope

Use the **23 m6Anet-processed runs, seven cell lines and 17 replicate-number groups** in `manifest.csv`. The frozen inventory was retrieved on 15 October 2026 UTC. This handover inspected the existing package; it did not refresh public availability, train a model, run full SG-NEx inference or produce new biological comparisons.

`metadata/all_directRNA_scope.csv` contains a broader 56-row direct-RNA inventory. It is background only. **Do not expand this task to 56 runs just because that table has 56 entries.** Conclusions must describe the processed subset, not all SG-NEx data. Selection of this available subset, chemistry/batch differences and incomplete reference evidence limit generalisation.

**Immediate next work:** choose/freeze the final model; obtain the signal JSONs for these 23 runs; resolve the input/reference convention; make genuine per-run predictions; run and inspect the comparison; then integrate real results and revise the report. The supplied Member 3 LightGBM model remains a candidate until the team selects it.

### What is completed, and what is its evidence?

| Item / location | Evidence type | What is actually completed |
|---|---|---|
| `manifest.csv`, `metadata/sample_manifest.csv`, `results/cell_line_inventory.csv` | Public sample metadata + saved public S3 listing | 23 runs mapped to cell lines, replicate numbers, sequencing runs and technical metadata. Group labels follow sample names; independent laboratory preparations are not independently verified. |
| `results/coverage_matrix_ge20_union.csv.gz`, `results/site_annotations.csv.gz` | Read coverage; annotation inherited from Explorer | Reconstructed 451,352 unique transcript-position keys having >=20 reads in at least one run. 437,320 are in the supplied annotated-human category. All 23 original read-count tables matched the retained coverage entries, including nonzero entries below 20 within this union. Exact FASTA/GTF annotation reconstruction is not completed. |
| `results/public_readcount_verification.csv`, `public_readcount_status.json` | Original public read-count files | Source keys, byte sizes, SHA256 and successful key/count checks for all 23 runs. These verify coverage consistency, not modification, alignments or offsets. |
| `figures/coverage_and_replicate_support.png` and `.svg` | Read coverage + metadata | Same figure in raster/vector formats: per-run >=20-read candidates and >=1 versus >=2 replicate-group support per line. **No model scores.** |
| `figures/common_population_sensitivity.png`, `results/replicate_coverage_support.csv` | Read coverage + replicate grouping | Common-site population under read/support rules; **no model scores**. Numbers below are comparison denominators, not modified-site counts. |
| `member3_candidate/artifact/`, `code/`, `outputs/`, `results/` | Actual saved model and actual development predictions | Received frozen LightGBM checkpoint/baseline; verified hashes; recomputed supplied development metrics. Training was not rerun. `data0_oof.csv`, `data1_predictions.csv`, `data2_predictions.csv` are not the 23 per-run SG-NEx outputs. Data1 was exposed during development. |
| `member3_candidate/examples/input_10_sites.json`, `examples/predictions.csv`; `results/member3_example_check.json` | Actual model predictions on a ten-site fixture | Original example reproduced byte for byte earlier. Source is identified by Member 3 as ten sites from Hct116 replicate3 run4. This is a smoke test, not a whole-run biological analysis. The new batching adapter also matched its scores. |
| `scripts/compare_predictions.py`, `tests/` | Implemented code + synthetic software fixtures | Analysis/guard tests passed. Fixtures test code behaviour; they are not biological evidence. No real whole-run comparison has been executed. |
| `Member4_Analysis.html`, `.ipynb`, `findings.md` | Coverage/metadata write-up; candidate checks | Coverage reading guide/notebook and report draft. Candidate metrics are development evidence. No final cell-line m6A findings. The notebook's real-analysis cell remains disabled. |
| Original Explorer (not bundled here) | Demonstration modification scores; real coverage vectors | Its modification scores were explicitly simulated and were excluded from coverage reconstruction. Its score distributions, gene patterns and score agreement cannot support biology. Small display JSONs cannot replace the signal input. |

Verified annotated-human common populations:

| Minimum reads | >=1 group per line | >=2 groups per line | Every listed group per line |
|---|---:|---:|---:|
| 20 | 59,224 | 33,452 | 26,024 |
| 50 | 20,535 | 11,560 | 9,429 |
| 100 | 8,814 | 5,058 | 4,300 |

Source: `results/replicate_coverage_support.csv`, rows `cell_line=ALL_7_INTERSECTION`, `population=annotated_human`. A group passes coverage if at least one of its runs passes. Finite-read/model failures can reduce these populations further. No figure supplied here comes from full-run model predictions.

Candidate development checks: mean-fold data0 ROC AUC 0.921897, trapezoidal PR AUC 0.498996, AP 0.499566; exposed data1 ROC AUC 0.821764, PR AUC 0.382879, AP 0.383071. See `docs/MEMBER3_REVIEW.md` and `results/member3_metrics_check.json`. Metric agreement is not independent validation of training exclusions, chemical truth or calibration.

## 2. Input files and download locations

### The actual signal inputs

Each run needs the public processed file **`data.json`**, containing newline-delimited nested objects:

```text
{transcript_id: {transcript_position: {sequence_7mer: [[9 measurements per read], ...]}}}
```

The received feature code interprets the nine measurements as dwell, signal SD and mean current at three adjacent event positions. Compatibility with the selected model's training inputs still needs confirmation; a matching array shape alone does not prove equivalent preprocessing.

For every run, `metadata/sample_manifest.csv` now contains:

- `input_json_uri`: exact S3 signal object.
- `signal_download_url`: exact public HTTPS download link.
- `signal_size_bytes`: size from the saved S3 listing.
- `signal_local_path`: suggested relative destination `<run_id>/data.json`.
- `cell_line`, `biological_replicate`, `sequencing_run`, `replicate_group`: run mapping.
- Original technical fields, `readcount_uri` and source provenance.

The original object inventory is preserved once in `metadata/s3_object_inventory.csv` and its XML snapshot. **23 signal files total 33,365,823,342 bytes (33.37 GB, about 31.07 GiB).** Have additional disk space for environments, outputs and temporary data; runtime/RAM for the full set have not been benchmarked.

All links follow this exact public prefix plus the run ID and filename:

```text
https://sg-nex-data.s3.ap-southeast-1.amazonaws.com/data/processed_data/m6Anet/<run_id>/data.json
s3://sg-nex-data/data/processed_data/m6Anet/<run_id>/data.json
```

Links are from the saved inventory, not newly revalidated downloads in this handover. No AWS credentials are needed for the public HTTPS route.

### Run mapping (retain exact case/spelling)

| Cell line | Replicate number -> sequencing run number(s) | Runs / groups |
|---|---|---:|
| A549 | 5 -> 1; 6 -> 1 | 2 / 2 |
| H9 | 2 -> 1,2; 3 -> 1,2; 4 -> 1,2 | 6 / 3 |
| HEYA8 | 1 -> 1,2; 2 -> 1,2; 3 -> 1 | 5 / 3 |
| Hct116 | 3 -> 1,4; 4 -> 3 | 3 / 2 |
| HepG2 | 5 -> 2; 6 -> 1 | 2 / 2 |
| K562 | 4 -> 1; 5 -> 1; 6 -> 1 | 3 / 3 |
| MCF7 | 3 -> 1; 4 -> 1 | 2 / 2 |

Exact ID format: `SGNex_<cell_line>_directRNA_replicate<replicate>_run<run>`. For example `SGNex_Hct116_directRNA_replicate3_run4`. `manifest.csv` and the enriched metadata contain all 23 complete IDs and links. Within one cell line, multiple runs sharing a replicate number are one group; never group different cell lines together by replicate number alone.

### Download and inclusion status

| Input/artifact | Included here? | Known location/status |
|---|---|---|
| All 23 full `data.json` signals | **No** | Not downloaded in this work; none found in the inspected workspace. The small ten-site example is the only bundled signal excerpt. This says nothing about downloads on other members' computers. Download using the commands below. |
| Original 23 `data.readcount` tables | **No** | Previously downloaded to `/workspace/scratch/26441f60de3a/readcount_cache/<run_id>.readcount` in the preparation workspace and verified. That path is not on the receiving computer. Total 659,329,250 bytes. Public keys/hashes are in `results/public_readcount_verification.csv`; verifier can redownload them. |
| `data.index` / `data.info` | **No** | Saved listing records these sibling objects. Supplied sequential candidate inference reads only `data.json`; other model loaders may require them. Replace the filename in the same run URL if needed and document the dependency. |
| Derived coverage matrix, annotations, aliases and official sample snapshots | **Yes** | Existing `results/` and `metadata/` folders; no raw signal required to read completed results. |
| Final selected model and 23 prediction CSVs | **No** | Team selection and full-run inference pending. Member 3 candidate checkpoint is included, separately labelled. |
| Exact transcript reference FASTA/GTF and matched expression/orthogonal validation files | **No** | Exact references/hashes and relevant preprocessing provenance remain unknown; obtain before coordinate-dependent claims. |
| Explorer prototype, its full gene shards and build tooling | **No** | Original separate Explorer archive is needed only to rerun shard reconstruction or continue that interface. Build/download/validation scripts described by that prototype were not supplied in this package; the final scientific display exporter/integration is not implemented here. |
| Member 1 label tables/folds and project-wide scorer/training infrastructure | **No** | Optional independent recheck of development metrics needs Member 1 tables/folds. Local score/train scripts refer to external team files. Ordinary Member 4 inference/comparison does not need retraining. |

## 3. Software and paths on the receiving computer

Use a working extraction of this ZIP. **Run every command below from the `Member4_Analysis/` folder containing this file.** Commands use Bash syntax (macOS/Linux; on Windows use WSL or adapt shell activation). Python **3.12** matches the earlier local verification; installation on the receiving computer and clean AWS Ubuntu evaluation have not been performed.

Set these two locations to actual paths on the receiving computer; keep the large input directory outside ordinary Git uploads:

```bash
cd "/absolute/path/to/extracted/Member4_Analysis"
export SGNEX_INPUT_ROOT="/absolute/path/outside/repository/sgnex_signals"
```

All package-internal paths are relative to this folder, and manifest prediction/coverage paths are resolved relative to the manifest. No `/workspace/...` path is required by core inference/comparison. Historical logs/receipts contain old provenance paths and do not need rewriting. Change any `/path/to/...` examples in optional scripts/docs. Keep `manifest.csv` beside `MODEL_INFO.md` unless deliberately adjusting all relative paths.

### A. Read coverage results and test analysis

```bash
python3.12 -m venv .venv-analysis
.venv-analysis/bin/python -m pip install -r requirements.txt
.venv-analysis/bin/python -m unittest discover -s tests -v
```

`requirements.txt`: numpy 2.3.5, pandas 2.2.3, matplotlib 3.10.8, scipy 1.17.0. All other standard-library imports ship with Python. The candidate prediction test normally skips in this environment because LightGBM is separate. Optional notebook:

```bash
.venv-analysis/bin/python -m pip install jupyterlab
.venv-analysis/bin/python -m jupyterlab Member4_Analysis.ipynb
```

Open `Member4_Analysis.html` directly for the reading guide. No full signals are needed for these steps.

### B. Download one signal run, then the 23-run set

The new small `scripts/download_signal_inputs.py` helper uses only Python's standard library and the existing enriched sample manifest. It was checked with a tiny local fixture; **it has not downloaded the large signal files here**. Start with one run:

```bash
python3.12 scripts/download_signal_inputs.py --dest "$SGNEX_INPUT_ROOT" --run-id SGNex_Hct116_directRNA_replicate3_run4
```

After inspecting that input and successful smoke inference, fetch the remaining set (the first complete file is reused):

```bash
python3.12 scripts/download_signal_inputs.py --dest "$SGNEX_INPUT_ROOT" --all
```

Expected destination: `$SGNEX_INPUT_ROOT/<run_id>/data.json` for each requested run, plus `download_receipts.jsonl` with source, bytes and local SHA256. Incomplete transfers remain `.partial` and restart on the next attempt; there is no resume support. The helper checks size against the snapshot and fails on a mismatch. It reuses size-matched existing files and hashes them; without a published upstream SHA256, size is not independent content authentication. Keep actual hashes in final provenance; inspect parsing/coverage against the downloaded inputs. It never downloads the broader metadata-only runs.

### C. Candidate environment and ten-site smoke test

Only if using/testing the received Member 3 candidate:

```bash
python3.12 -m venv .venv-member3
.venv-member3/bin/python -m pip install -r member3_candidate/requirements-predict.txt
mkdir -p smoke_check
.venv-member3/bin/python member3_candidate/code/predict.py --input member3_candidate/examples/input_10_sites.json --output smoke_check/original_example.csv
.venv-member3/bin/python -m unittest discover -s tests -p test_member3_prediction.py -v
```

Pins: LightGBM 4.7.0, numpy 2.4.6, pandas 3.0.6. Keep these separate from analysis pins. CPU inference is supported; no GPU is required by this candidate. LightGBM may need an OpenMP runtime: `brew install libomp` on macOS when the loader reports a missing OpenMP library, or `sudo apt-get install libgomp1` on Ubuntu when absent. The earlier successful test was Linux, not a verification of this particular computer.

Expected smoke output: ten full-precision rows matching `member3_candidate/examples/predictions.csv`; no whole-run results are created. These tests use temporary paths and do not modify supplied artifacts. Avoid installing the full training requirements just for inference.

### D. Run the saved Member 3 candidate on real signal files

Use this route only if the candidate is intentionally being evaluated, or the team actually selects this unchanged artifact. The adapter loads its saved model/baseline; it never trains or refits normalisation.

```bash
.venv-member3/bin/python scripts/predict_member3_run.py --input "$SGNEX_INPUT_ROOT/SGNex_Hct116_directRNA_replicate3_run4/data.json" --run-id SGNex_Hct116_directRNA_replicate3_run4 --output predictions/SGNex_Hct116_directRNA_replicate3_run4.csv --min-reads 20 --batch-sites 512 --threads 4
```

After inspecting the first complete run, run remaining runs sequentially:

```bash
.venv-member3/bin/python - <<'PY'
import csv, os, subprocess, sys
from pathlib import Path
base = Path(os.environ['SGNEX_INPUT_ROOT'])
for row in csv.DictReader(open('manifest.csv', newline='')):
    output = Path(row['prediction_file'])
    receipt = output.with_suffix('.receipt.json')
    if output.exists() or receipt.exists():
        print('Existing output: review its receipt/hash before reusing:', output)
        continue
    subprocess.run([sys.executable, 'scripts/predict_member3_run.py',
                    '--input', str(base / row['run_id'] / 'data.json'),
                    '--run-id', row['run_id'], '--output', str(output),
                    '--min-reads', '20', '--batch-sites', '512', '--threads', '4'], check=True)
PY
```

Each successful run writes three files:

1. `predictions/<run_id>.csv`: exact three-column eligible-site scores.
2. `<run_id>.site_metadata.csv.gz`: all successfully parsed input sites, raw/finite read counts, 7-mer, status and reference fallback level.
3. `<run_id>.receipt.json`: arguments, input/model/baseline/output hashes, software and scoring counts.

Defaults use >=20 reads with nine finite measurements. Source read-count coverage includes input reads; finite-read eligibility can differ. A site with malformed measurements, zero complete finite reads or duplicate keys **aborts inference**; it is not silently omitted with a completed receipt. Ordinary below-minimum finite-read sites are recorded in the sidecar. Failed runs can leave `.partial` files; preserve/inspect the failure and move those files aside before a clean rerun. An adapter receipt deliberately says `completed_candidate_inference` and `final_model_selected:false`; selection evidence must be recorded separately even if this candidate is later chosen. Do not alter historical receipts to imply a selection that they did not record.

This adapter batches sites and uses temporary SQLite for duplicate detection, but retains all reads for each batch. Full-run wall time, peak RAM and performance have not been measured. System temporary disk is also used.

## 4. Prediction interface and connecting the final model

The analysis consumes prediction CSVs, not a checkpoint. If a different final model wins, use **its own saved preprocessing and inference entry point**, then export the same interface. A universal adapter for an arbitrary other checkpoint is **not supplied**. Do not rename another model's artifact into the LightGBM folder or recompute per-cell-line sequence baselines.

Each `predictions/<run_id>.csv` must contain exactly these columns in this order:

```csv
transcript_id,transcript_position,score
```

| Field | Required meaning / checks |
|---|---|
| `transcript_id` | Original signal transcript ID. Preserve case and version suffixes in the raw prediction file. The explicit per-run alias map is applied only inside analysis. No general suffix stripping. |
| `transcript_position` | Original integer key from the processed signal; nonnegative, finite, no fractional values. **Its biological base/offset convention is not yet verified.** Do not shift it to make joins work. |
| `score` | Full-precision finite number in [0,1] from the same saved model/preprocessing across all 23 runs. It is a predicted site score, not validated stoichiometry. |

Keys must be unique and nonmissing; empty files are refused. No index, count, cell-line or metadata columns in this three-column export. Keep supplementary fields/receipts separately. The supplied analysis accepts only sites belonging to the coverage union and having >=20 source reads for that run. If another model emits all sites, retain that original export, then make a separate eligible Task 2 export by joining to the run-specific source coverage; do not mutate scores or raw identifiers. No general-purpose export adapter for another model is bundled. Unknown keys/version mismatches must be investigated before filtering them away.

`manifest.csv` has the team's nine fields:

```text
run_id,cell_line,biological_replicate,sequencing_run,prediction_file,coverage_file,min_reads,reference_version,model_version
```

- Keep the 23 rows and correct group mapping. Set one genuine `model_version` and reference description across the runs only after confirming their compatibility. Use e.g. the checkpoint SHA256 as the model identifier, with the full record in `MODEL_INFO.md`.
- `coverage_file` is the supplied wide `results/coverage_matrix_ge20_union.csv.gz`: join transcript-position, then use the column named by `run_id`. This is not one coverage file per run. Zeros mean no entry in that run's processed candidate table within this union, not a negative modification label or measured zero expression.
- `min_reads=20` is the current working export/coverage minimum. If changed, update the reasoning and thresholds consistently. Missing finite-read predictions are checked separately against source-count eligibility.
- Complete `MODEL_INFO.md` with the selection decision, actual checkpoint/code/preprocessing/input hashes, software/commands, training/evaluation exposure, reference/coordinate evidence and limitations. Existing `PENDING_TEAM_SELECTION` prevents accidental final analysis. The CLI's version check looks for `PENDING`, not every possible unresolved wording; it **cannot verify** that a reference is truly known. Never replace uncertainty with a fake version to make validation pass. If using an explicitly exploratory operational reference label, retain unknowns in MODEL_INFO and withhold coordinate-dependent claims.
- Optional `coordinate_convention` and `real_predictions` columns are supported but not needed by the nine-field contract. If absent, document coordinates in `MODEL_INFO.md` and use `--confirm-real-predictions` only for genuine model outputs. That flag declares input provenance; it does not validate chemistry or coordinates.

After obtaining consistent real outputs and reviewing provenance:

```bash
.venv-analysis/bin/python scripts/compare_predictions.py --manifest manifest.csv --model-info MODEL_INFO.md --coverage-matrix results/coverage_matrix_ge20_union.csv.gz --annotations results/site_annotations.csv.gz --aliases metadata/transcript_aliases_checked.csv --confirm-real-predictions --out real_analysis_v1
```

Use a fresh output directory on each attempt; the script creates it before validating and will refuse an existing directory. If expected >=minimum-source-read sites are missing, the default fails. Investigate the sidecars/parser/model eligibility first. For an explicitly incomplete exploratory run, append `--allow-missing-predictions`; keep `prediction_availability.csv`, missing counts/reasons and the resulting changed population in the report. Do not fill omitted predictions with zero. The flag logs counts but does not automatically explain reasons or repair model input problems.

### Expected comparison outputs (not produced yet)

- `prediction_availability.csv`, `analysis_receipt.json`: per-run missing counts and input/code-interface provenance.
- `replicate_scores_cov20/50/100.csv.gz`, `cell_line_scores_cov20/50/100.csv.gz`: run means within group, then equal group means, with ranges/support.
- `all_line_common_scores_cov20/50/100.csv.gz`, `all_line_summary.csv`: a separate seven-line common population.
- `pairs/<line_a>__<line_b>__cov<depth>.csv.gz`, `pair_summary.csv`: same-site pair differences, coverage ratio, ranges, candidate flags and conflicting/small effects retained.
- `threshold_sensitivity.csv`, `agreement.csv`, `score_coverage_dependence.csv`; `nonprimary_reference_diagnostics.csv` when such sites occur.
- `paired_score_differences.png`: a newly generated real-prediction figure, distinct from the two supplied coverage figures.

The CLI includes optional per-motif summaries only when annotation contains `motif_5mer`; the bundled `site_annotations.csv.gz` has **no motif column**, so those summaries will not appear automatically. Joining true sequence context from inference sidecars and validating it is remaining work. The CLI does not create the Explorer's packed display shards.

Proposed exploratory settings: coverage 20/50/100, >=2 groups per line, cutoffs 0.5/0.7/0.9, absolute paired delta >=0.2 with nonoverlapping group ranges and geometric mean coverage ratio <=2. These are descriptive settings, not a differential-modification test or calibration result. Repeat with `--require-all-replicates` into another new output directory. No read-depth subsampling, leave-one-group-out analysis, expression adjustment or region/pathway analysis is implemented by this command. Coverage sensitivity alone cannot remove abundance, isoform or batch confounding.

## 5. Reference and coordinate checks: verified versus unknown

| Check | Verified evidence | Still unknown / consequence |
|---|---|---|
| Signal/read-count keys versus coverage | All 23 original `data.readcount` files match retained coverage keys/counts after explicit documented aliases. `results/public_readcount_verification.csv` and status JSON. | Full signal JSON content has not been compared; no event-coordinate offset validation follows. |
| Reference release | Existing notes report **GRCh38 / Ensembl91**; supplied annotation metadata carries transcript versions/lengths. | Exact FASTA/GTF filenames, release files, content hashes, complete reference composition and per-run preprocessing provenance were not verified or bundled. This is an upstream-reported reference, not a reconstructed one. |
| Transcript suffix handling | Explicit `metadata/transcript_aliases_checked.csv`: 46,297 alias rows for MCF7 replicate3 run1, including 13,589 matching supplied annotated versions and 32,708 coverage-only/unverified aliases. No key collisions in the source checks. | Version agreement is to supplied annotation, not independently rebuilt FASTA. Unverified aliases are not permission for biological mapping; nonprimary annotation categories are excluded from primary comparisons. Do not apply this one-run map indiscriminately to other runs. |
| `transcript_position` | Copied literally from input/count keys; equality checked for coverage. | 0- versus 1-based origin, candidate-A position versus event position, 7-mer window start and exact offset are **unknown**. No genomic/region mapping is verified. |
| Reference-context utility | `scripts/check_reference_context.py` passed synthetic correct-offset tests and rejected a wrong offset. | No genuine SG-NEx reference-context validation ran. A software test is not reference verification. |
| Annotation classes / coordinates | Supplied `kind`, gene and transcript metadata retained. Primary comparisons use `kind=annotated`; other kinds remain separate diagnostics. | Putative alternate/unresolved categories, CDS/UTR bounds and genomic conversion still need source/reference evidence. No GTF exon mapping script is supplied. |

To check real context later, export a **plain CSV** with `transcript_id,transcript_position,sequence_7mer` from a real sidecar; optionally provide `reference_transcript_id` for a documented FASTA-ID mapping. The utility matches the first whitespace-delimited FASTA header token exactly. Obtain the exact transcript FASTA and establish the offset from preprocessing documentation (not by choosing the offset with the most matches):

```bash
export SGNEX_FASTA="/absolute/path/to/exact/transcripts.fa.gz"
export SGNEX_WINDOW_START_OFFSET="REPLACE_WITH_DOCUMENTED_INTEGER"
.venv-analysis/bin/python scripts/check_reference_context.py --sites reference_check_sites.csv --fasta "$SGNEX_FASTA" --window-start-offset "$SGNEX_WINDOW_START_OFFSET" --out reference_context_check.csv
```

The offset is the additive conversion from the literal input position to the zero-based start of its seven-base window; the utility then checks central base index 3 is A. Example arithmetic, **not a claim about these inputs**: a one-based central-A position would imply offset -4; a zero-based central-A position would imply -3. Establish the convention separately before using either. Keep failures, reference hashes, how sites were sampled and the tested-run coverage. A successful sampled check is limited to those sites; it does not validate genomic exon mapping.

## 6. Optional reproduction and missing dependencies

Completed coverage results are already bundled; these steps are optional. Use a separate working copy because reconstruction overwrites generated metadata/results. The original Explorer archive is needed for the first command; point to the directory containing `data/overview.json` and `data/genes/`:

```bash
.venv-analysis/bin/python scripts/audit_coverage.py --explorer "/absolute/path/to/SG-NEx_m6A_Explorer" --out .
.venv-analysis/bin/python scripts/verify_public_readcounts.py --out . --cache "/absolute/path/outside/repository/readcount_cache"
```

The first command extracts counts only, never simulated scores. It regenerates the older richer manifest format and will remove the new download columns from `metadata/sample_manifest.csv`; use a throwaway copy or preserve that enriched file. The second can run independently using the already bundled matrix/XML and redownloads ~659 MB of raw counts. `audit_coverage.py` alone has stale provenance text about the original-count check; the successful verifier/status record supplies the later verification evidence. Do not mistake rerendering a report for rerunning scientific validation.

Optional inventory refresh (metadata/listing only):

```bash
.venv-analysis/bin/python scripts/refresh_inventory.py --out metadata/new_snapshot
```

Use a new destination. Do not replace the fixed 23-run scope automatically if the public listing changes. Refresh can save multiple listing pages; older audit/verifier entry points expect the saved nontruncated single-page snapshot and need explicit adaptation for paginated replacements.

Optional development-metric recheck requires Member 1 files (not bundled) and scikit-learn in a compatible evaluation environment. The full candidate requirements describe the received source environment, not the minimal prediction setup:

```bash
python scripts/check_member3_metrics.py --data0-labels "/path/to/Member1_Analysis/tables/data0_site_summaries.csv.gz" --data1-labels "/path/to/Member1_Analysis/tables/data1_site_summaries.csv.gz" --folds "/path/to/Member1_Analysis/shared_folds/data0_folds.csv" --output new_metrics_check.json
```

Existing metric-check receipts are included. Training/scoring infrastructure, original assay parsing, fresh model comparison and label validation are outside the completed Member 4 work.

## 7. Remaining work and integration checklist

1. **Model selection and genuine inference:** record the final decision; use the same saved model/preprocessing for all 23 runs; retain signal hashes, prediction receipts and failed/unscorable-site evidence. Do not promote the candidate solely because it is bundled.
2. **Input/reference validation:** inspect real input structure/read counts and reference context, confirm chemistry/event-feature compatibility, resolve transcript-ID and offset assumptions, and verify independence of replicate-number groups where provenance permits.
3. **Real-score analysis:** execute the comparison, inspect support/coverage sensitivity and replicate disagreement, and preserve attenuated/conflicting examples. Compare pairwise common sites separately from the all-line panel. Call differences predicted patterns only.
4. **Additional biology, only where justified:** validated motif/region/locus analysis, abundance information, supported external-assay overlap and functional interpretation. These are not completed. No available independent calibration establishes modified-molecule fractions; data2's fractional labels do not establish stoichiometry by themselves.
5. **Display integration:** recover or implement the missing Explorer builder/export/validation path; generate display data from full-precision real outputs; use within-group then equal-group weighting; keep missing observation, insufficient reads, missing prediction and low score distinguishable. Small simulated-score display files are not inference inputs. No final dashboard integration has been run here.
6. **Report and reproducibility:** revise `findings.md` using actual outcomes, add newly produced real-score plots and precise populations/limitations, consolidate AI disclosure from `AI_use_member4.md`, and check installation/runtime on the receiving machine. Keep large inputs and environments out of ordinary Git uploads. No GitHub push, deployment or final submission was performed.

The handover retains original code, checkpoint, metadata, tables, figures and write-up once in their existing folders. `README.md` points here; earlier lower-case `handoff.md` has been replaced by this single file. Dated historical notes remain explicitly subordinate. `PACKAGE_MANIFEST.json` lists file hashes for integrity, excluding itself. `VALIDATION.md` and the new handover validation log distinguish historical scientific checks from this packaging check. **The final whole-run predictions, real biological comparisons and integrated interface remain unfinished.**
