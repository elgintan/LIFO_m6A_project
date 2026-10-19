# Context-reference neural experiment

This folder implements a portable trainer and CPU predictor for one controlled
question: **does adding training-fitted, sequence-relative signal information
help the existing sequence-aware network?** It follows the accepted
[shared rules](../../model_evaluation/SHARED_RULES.md) and preserves the archived
October 7 model and its historical results.

The code and focused correctness tests are implemented. **30 tests and a small
real data0 smoke run in both modes passed**; see the
[observed implementation check](IMPLEMENTATION_CHECK.md), including a recovered
Windows file-write interruption. Complete five-fold comparisons, a nominated
final model and new performance conclusions remain pending. Commands for those
later stages below are instructions, not completed results.
No score or gain is supplied in advance. Current background and research
questions are in [FIRST_STEPS.md](../FIRST_STEPS.md).

## 1. What changes, and what stays matched

One example is a **site**: a transcript and position with a seven-base context
and a variable-sized bag of reads. Each read has nine event measurements:
dwell time, signal standard deviation and mean current at the preceding,
central and next positions. The label belongs to the whole site; individual
reads have no supplied true modification label.

Both modes retain the existing seven-base embedding, sequence-conditioned
read network, masked attention pooling and 63 all-read mean/SD/quantile
summaries. The only intended experimental difference is the extra feature
branch:

| Mode | Meaning |
|---|---|
| `none` | Fresh matched control: the original inputs, with no added context-reference features. Sequence is still used. |
| `relative` | The same recipe, with nine context-reference features appended at the site classifier. Its input layer therefore has nine additional inputs. |

`--mode both` runs the two modes using the same data, outer groups, inner
selection rule, seeds and non-feature settings. The historical saved OOF file
is useful background, but cannot alone isolate this feature effect because
the portable trainer uses a different documented stopping arrangement.
Fresh fits never initialise from the historical all-data0 weights.

The default recipe uses attention width 48, dropout 0.25, AdamW learning rate
0.001, weight decay 0.0001 and positive-label loss weight 3. The read branch
samples at most 32 reads per training site, changing reproducibly by epoch.
All 63 summaries always use every read. Inner validation, outer assessment
and prediction also use every read in the read branch. Padding is masked.

## 2. What a context reference means

For each permitted training site, take the nine raw per-read medians from
summary columns **36–44**, using zero-based Python indexing `[:, 36:45]`.
For each feature, calculate the median of those **site medians** within the
context. Each site has equal weight, regardless of its read coverage.

Choose a reference for a site in this fixed order:

1. Its exact seven-base context, if at least **30 training sites** support it.
2. Its central five bases, if at least **30 training sites** support them.
3. The global median across the permitted training sites.

Thirty is a declared engineering choice, not an experimentally established
optimum. Support means sites, not reads or positive labels. Sparse positive
support and support for estimating this label-neutral reference are different
issues. Recognised ambiguous bases share code 4; T and U share code 3.

Subtract the selected raw reference from the raw site median. Then apply
signed `log1p(abs(x)*1000)` to dwell residuals and signed `log1p(abs(x))` to
signal-SD residuals. Mean-current residuals remain linear. Fit the resulting
nine features' centre and population SD on the permitted training sites only.
A near-zero SD below `1e-8` is replaced by 1.0. Prediction applies those saved
references and scales without updating them.

An illustrative subtraction such as `116 - 120 = -4` describes the arithmetic;
it is not an observed course-data result. These derived features describe
deviation from typical training signals. The reference is **not known
chemically unmodified signal**, and an unusual residual is not automatically
an error. Absolute inputs remain available to the network. Site scores and
attention weights do not establish molecule-level labels or stoichiometry.

## 3. Keep genes separate throughout fitting

Use the exact existing `eda/received/shared_folds/data0_folds.csv`; do not
regenerate it. A fold is a group containing many genes, rather than one gene.
All sites/transcripts from each gene stay together. Labels, cache and folds
are joined by both transcript ID and numeric position, with hashes and exact
key coverage checked.

For outer round `f`:

1. Set group `f` aside for assessment.
2. Set group `(f + 1) % 5` aside for inner validation. Initially fit the other
   **three** groups, including their normalisation and context references.
3. Select the number of epochs using only that inner validation group.
4. Start fresh weights and refit **all four** non-assessment groups for that
   fixed number of epochs. Refit normalisation and references on those four.
5. Score assessment group `f` without fitting anything on it.

For example, round 0 initially fits groups 2/3/4 and validates on group 1;
it then freshly refits groups 1/2/3/4 and scores group 0. Repeat for all five
outer groups. **Never fit references on all data0 before these splits.**

An **epoch** is one pass over the fit's training sites. Inner stopping uses
`S = (ROC AUC + trapezoidal PR AUC) / 2`, with default maximum 20 epochs and
patience 5. Patience counts successive epochs without improvement greater
than `1e-5`. All-data0 final fitting uses the median of the nominated mode's
five selected epoch counts, with fresh weights and no data1 stopping.

The primary comparison is the unweighted mean of the five outer scores.
Retain each component, sample SD and pooled OOF metrics separately. **OOF**
means out-of-fold: each site's prediction came from a fit that excluded its
gene group. Architecture/feature decisions based on these scores make them
development evidence, not an untouched test of the entire search procedure.

## 4. Open the terminal and select the existing environment

In VS Code choose **File > Open Folder** and open `LIFO_m6A_project`.
Choose **Terminal > New Terminal**. Select **PowerShell** from the terminal
profile menu if necessary. Run `Get-Location`; the directory should end in
`LIFO_m6A_project`. All commands below assume that repository root.

```powershell
$nnPython = '../advanced_model/.venv/Scripts/python.exe'
$nnCode = 'model_elgin/context_reference_v1'
$nnCache = '../advanced_model/cache/data0'
$nnLabels = '../data0/data.info.labelled'
$nnFolds = 'eda/received/shared_folds/data0_folds.csv'
$nnOutput = 'model_elgin/outputs/context_reference_v1'
& $nnPython --version
```

The existing environment already has the required modelling libraries. `&`
launches the specified Python executable, avoiding an unrelated Windows
`python`. A virtual environment is an isolated collection of installed Python
packages; this one lives beside the repository. `-B` below avoids creating
bytecode-cache files; `-u` makes training progress appear promptly.

[requirements.txt](requirements.txt) pins the five libraries used in the
checked Python 3.12.14 environment (PyTorch's installed build is 2.14.1+cpu).
Creating a new environment/clean Linux verification remains separate work;
use the existing environment for this local step.

These paths are the existing local layout, not requirements for other
computers. Change the variables to matching local inputs on another machine.
The scripts take explicit paths. A public clone does not include the raw
datasets, large cache, environment or training checkpoints. See
[data access](../../DATA_ACCESS.md). Keep retained local runs under the ignored
`model_elgin/outputs/` directory; no upload or submission is performed.

## 5. Verify or prepare the data0 cache

The existing complete cache can be reused. It contains all reads, offsets,
raw 63-feature summaries, sequence codes and site keys; training checks its
payload fingerprints. Reusing it does not mean reusing learned statistics.
Every fit still learns its own normalisation and references.

To check/reuse that cache through the preparation interface:

```powershell
& $nnPython -B "$nnCode/prepare.py" --input '../data0/dataset0.json.gz' --output-dir $nnCache
```

Preparation rejects malformed, empty, duplicate or non-finite sites instead
of silently dropping them. Only a successfully completed full scan receives
a completed manifest. A new machine can set `$nnCache` to a separate local
cache directory and run the same preparation command. Its manifest must
identify the agreed data0 input; another dataset cannot become training data
merely by supplying its cache path.

## 6. Run the small checks before a full comparison

The focused tests use synthetic inputs to check train-only reference fitting,
fallback arithmetic, save/load behaviour, masks, prediction-stage guards and
CSV coverage. They are software correctness checks, not predictive results.

```powershell
& $nnPython -B -m unittest discover -s $nnCode -p 'test_*.py' -v
```

Then run one outer round, one epoch, in both modes:

```powershell
& $nnPython -B -u "$nnCode/train.py" --cache $nnCache --labels $nnLabels --folds $nnFolds --output-dir $nnOutput --phase smoke --mode both --outer-folds 0 --max-epochs 1 --patience 5 --batch-size 128 --threads 4 --smoke-genes-per-fold 20
```

The smoke population selects up to **20 whole genes per original fold**,
deterministically, without choosing genes by their labels/scores. That can
mean up to 100 genes in total. Round 0 retains the same three-group fit,
one-group inner validation and fresh four-group refit structure. A tiny
population lacking either class triggers an error; increase the gene count
in a separate smoke output directory rather than rebalance assessment rows.

Expected files are under `$nnOutput/smoke/none/fold0/` and
`$nnOutput/smoke/relative/fold0/`. Each has a split audit, `inner/` and `refit/`
fits, a prediction CSV and fold-result record. They are labelled **smoke**.
Their scores do not establish which mode is better, and smoke fits cannot
qualify as full CV or an all-data0 final model.

To verify the predictor on the real archived ten-site input using that
development artifact:

```powershell
& $nnPython -B "$nnCode/predict.py" --input 'model_elgin/baseline_2026_10_07/examples/input_10_sites.json' --model "$nnOutput/smoke/relative/fold0/refit/best.pt" --output "$nnOutput/smoke/relative/example_predictions.csv" --threads 4 --batch-size 8 --allow-development-model
```

The development flag is deliberately required because this is a smoke model.
The output manifest records that status. It does **not** make these ten
training-source sites an independent test or permit using a smoke artifact
as the final scientific/submission predictor.

## 7. Complete the matched five-fold comparison

After the small checks are reviewed, use the full data0 population:

```powershell
& $nnPython -B -u "$nnCode/train.py" --cache $nnCache --labels $nnLabels --folds $nnFolds --output-dir $nnOutput --phase cv --mode both --max-epochs 20 --patience 5 --batch-size 256 --threads 4
```

Omitting `--outer-folds` uses all five, 0/1/2/3/4. Each mode has ten fits:
five inner stopping fits and five fresh outer-training refits. The default
seed is 2026. The shared scorer runs after all five full-population rounds
are present. Results are retained separately:

```text
model_elgin/outputs/context_reference_v1/
  cv/none/recipe.json
  cv/none/fold0/ ... fold4/
  cv/none/data0_oof.csv
  cv/none/data0_cv_metrics.json
  cv/relative/recipe.json
  cv/relative/fold0/ ... fold4/
  cv/relative/data0_oof.csv
  cv/relative/data0_cv_metrics.json
```

The OOF header is `transcript_id,transcript_position,score,fold_id`.
Compare the two modes' actual full five-fold scores, fold variation and
context/coverage limitations. A lower, equal or inconclusive result remains
valid evidence. Do not select a mode from a smoke result or from data1.

## 8. Nominate, refit and predict with one saved final model

**The command below is an example if `relative` is nominated after reviewing
data0. It is not a statement that this mode has been selected or has won.**

```powershell
& $nnPython -B -u "$nnCode/train.py" --cache $nnCache --labels $nnLabels --folds $nnFolds --output-dir $nnOutput --phase final --mode relative --max-epochs 20 --patience 5 --batch-size 256 --threads 4
```

Final fitting requires that mode's complete full-population five-fold
evaluation and matching candidate/input identity. `--mode both` is rejected
for this phase. For a nominated control use `--mode none` and its corresponding
artifact path. Only after all final epochs finish is the portable artifact
promoted to `$nnOutput/final/relative/model.pt`, labelled `final_data0` with
completion metadata. It includes the configuration, fresh weights,
preprocessing, references and input fingerprints. During fitting, `best.pt`
and `last.pt` remain resumable training artifacts labelled `final_fitting`;
they must not be accepted as a completed final predictor. This distinction
prevents an interrupted all-data0 fit from being mistaken for the nominated
finished model.

Only after it exists, use the same saved artifact for every input dataset:

```powershell
$nnFinal = "$nnOutput/final/relative/model.pt"
& $nnPython -B "$nnCode/predict.py" --input '../data0/dataset0.json.gz' --model $nnFinal --output "$nnOutput/predictions/dataset0.csv" --threads 4 --batch-size 32
& $nnPython -B "$nnCode/predict.py" --input '../data1/dataset1.json.gz' --model $nnFinal --output "$nnOutput/predictions/dataset1.csv" --threads 4 --batch-size 32
& $nnPython -B "$nnCode/predict.py" --input '../data2/dataset2.json.gz' --model $nnFinal --output "$nnOutput/predictions/dataset2.csv" --threads 4 --batch-size 8
```

Prediction requires only the JSON input and saved bundle, with no labels,
folds, gene lookup or retraining. It uses every read. It limits batch padding
to reduce memory, but even a single site larger than that budget keeps all
its reads. Reduce batch size/read budget if necessary; do not truncate sites.

The exact header is `transcript_id,transcript_position,score`. Each input site
must appear once with a finite probability in [0,1]. A `.csv.manifest.json`
records full unique key coverage, all-read counts, stage and input/model/code/
output fingerprints. The model hash must match across the three datasets.
Dataset0 final predictions are in-sample and distinct from four-column OOF.

Keep data1 out of fitting, stopping, reference construction, calibration and
winner selection. Its later frozen evaluation is an already-exposed transfer
diagnostic, not a newly blind test. Data2's official scoring/label
interpretation must be followed separately; these scripts do not turn its
fractional labels into binary ground truth. Wider SG-NEx application and
biological comparisons remain separate Task 2 work.

## 9. Interruption recovery and common errors

Each fit saves:

- `last.pt`: completed epoch, weights, optimiser, Python/NumPy/PyTorch RNG
  state, fitted preprocessing/references, history and signature.
- `best.pt`: selected weights and inference bundle for that fit's stage.
- `history.json` and `training.log`: actual epoch losses, validation metrics
  where applicable and durations.
- `complete.json`: completed-fit settings, counts, resource measurements and
  selected artifact fingerprint.

Rerun **the exact original training command** to resume an interrupted fit.
An unfinished current epoch restarts from the last completed epoch. A matching
completed fit is reused; there is no `--resume` flag. Avoid simultaneous
invocations writing the same mode/fold directories.

Signatures bind configuration, data/cache/labels/folds, fit/validation indices,
source/scorer code, relevant package versions, threads, seed, batch size and
epoch/stopping settings. Editing those settings is a new experiment, not a
compatible continuation; preserve the old output and choose a new output root.
The predictor also checks saved semantic source fingerprints for the model,
raw parser and context transforms; CRLF/LF line endings are normalised.
Rebuilding/moving cache metadata or changing machines/environments can affect
fingerprints or numerical behaviour. CPU prediction is designed to be portable,
but a clean Ubuntu/RONIN run has not been verified here.

The predictor accepts the completed `model.pt`/`final_data0` bundle by default.
Inner/refit/smoke bundles need `--allow-development-model` for explicit software
checks. Incomplete `final_fitting` checkpoints are not final prediction
artifacts; the development flag does not turn them into completed models.
The predictor rejects changed
existing-output fingerprints, incomplete CSV/manifest pairs and interrupted
temporary CSVs. Preserve an interrupted prediction and use a fresh output
filename; prediction does not resume halfway through a JSON file. It also
rejects attempts to overwrite the input or model.

If a path is missing, first check `Get-Location`, the variables in section 4,
and which stage has actually finished. If final fitting reports incomplete
CV, inspect both `cv/<mode>/progress.json` and its five fold results; do not
substitute smoke outputs. If hashes/signatures differ, investigate the changed
input/source instead of altering recorded fingerprints. Retain errors and
fixes alongside measured outcomes for the report.
