# Minimum shared rules for Elgin and Samuel

**Accepted by Elgin on 15 October 2026. Status updated 20 October:** Elgin's
matched neural comparison has completed all five folds. Samuel's candidate PR
was merged, its source is unpacked, and its saved data0 metrics reproduce with
this scorer. Final selection and Task 2 predictions remain pending. The
comparison contract below is unchanged; integration is not model selection.

## What must match

1. **Data and target:** use the supplied data0 version and original binary
   site labels for fitting and tuning. Use the same eligible assessment sites,
   retaining natural class proportions and valid difficult examples. Keep
   data1 out of fitting, stopping, hyperparameter choice and winner selection
   in this cycle. Record input versions/hashes; see [data access](../DATA_ACCESS.md).
2. **Exact outer splits:** read the existing
   [data0_folds.csv](../eda/received/shared_folds/data0_folds.csv), joining by
   BOTH transcript ID and numeric transcript position. For round `f`, assess
   `fold_id == f` and fit only using `fold_id != f`; run all five rounds,
   `f=0,1,2,3,4`. Never regenerate the split, even with the same random seed.
   Every site/transcript from one gene stays together. The file SHA256 is
   `986b7872084cf762f1c3944b1eacc1e8f1ff69cb2848630f80685063541da9b0`.
3. **Fitting boundaries:** fit fresh model weights and learned preprocessing
   inside the permitted training groups. The old all-data0 model/scalers
   cannot initialise a held-out-data0 fit. If tuning or early stopping needs
   inner validation, keep those genes separate from its fitting genes, never
   inspect the outer assessment fold for that choice, and document the rule.
   [cv_rounds.csv](cv_rounds.csv) supplies a convenient shared inner-validation
   default, explained below. It does not prescribe a model's optimiser or
   stopping criterion.
4. **Scores and outputs:** use [evaluate.py](evaluate.py) with its
   [pinned scoring dependencies](requirements.txt). The primary data0 score is
   the arithmetic mean of five fold scores, each
   `S = (ROC AUC + trapezoidal PR AUC) / 2`. Retain both components and fold
   variation. AP is separate; pooled out-of-fold metrics are supplementary.
   Provide one out-of-fold score for every data0 site, with columns
   `transcript_id,transcript_position,score,fold_id`. A score must come from
   the fit that excluded that site's fold. Missing/extra/duplicate sites and
   invalid scores are errors, not reasons to silently drop rows.
5. **Final refit and data1:** freeze each nominated configuration, fit its
   final model afresh on all data0, and save/hash it BEFORE evaluating data1.
   Each frozen candidate predicts all data1 sites with columns
   `transcript_id,transcript_position,score`, scored by the same evaluator.
   data1 is an already-exposed HCT116-to-HEK293T transfer diagnostic. Preserve
   its result even if unfavourable. If it prompts another revision or changes
   selection, disclose that development use. One selected saved pipeline then
   produces all required dataset/SG-NEx predictions. Its data0 predictions are
   in-sample, distinct from the four-column out-of-fold development file.

## What can differ

Model family, features, signal transformations fitted on permitted training
data, read aggregation, loss, optimiser, hyperparameter search, training seed,
stopping metric/patience and computation budget can differ. Record them so the
comparison is understandable. Extra EDA experiments and repeat-seed checks are
recommendations, not identical compulsory modelling tasks for both people.

This compares complete pipelines; it does not isolate architecture effects.

## Optional common inner-validation default

The outer assignments above are mandatory. If using the supplied default,
round `f` reserves `(f+1)%5` for inner validation and initially fits the other
three groups. Choose the stopping duration, then fit afresh on all four
non-assessment groups for that fixed duration before scoring group `f`.

For example: assess group 0; initially fit groups 2/3/4 and stop on group 1;
then freshly refit groups 1/2/3/4 and predict group 0. A fixed-duration model
can fit the four groups directly. A different documented inner strategy is
allowed if it respects the same outer boundary and keeps inner genes separate.

## Verify and score from the repository root

Use your own Python environment. Keep label files local; they are not inputs
to the prediction script. Replace `LOCAL_DATA` with your actual data folder.

```text
python eda/received/shared_folds/create_shared_folds.py --labels LOCAL_DATA/data0/data.info.labelled --output-dir eda/received/shared_folds --verify-only
python -m pip install -r model_evaluation/requirements.txt
python model_evaluation/evaluate.py --dataset data0 --labels LOCAL_DATA/data0/data.info.labelled --predictions model_samuel/outputs/data0_oof.csv --output model_samuel/results/data0_cv_metrics.json
python model_evaluation/evaluate.py --dataset data1 --labels LOCAL_DATA/data1/data.info --predictions model_samuel/outputs/data1_predictions.csv --output model_samuel/results/data1_metrics.json
```

Elgin substitutes his own model/output folder. The verifier checks the frozen
split and labels; the scorer checks prediction joins and metric calculations.
Neither can prove that a model actually followed the training boundary:
training code, configurations, logs and checkpoints remain necessary evidence.

Use a separate scoring environment if these pinned metric dependencies
conflict with your model's environment. There is no requirement that both
models use the same modelling libraries.

For EDA rationale, dataset limitations and report suggestions, see
[the detailed methodology](EVALUATION_PROTOCOL.md). Those suggestions do not
add shared architecture or feature requirements to this minimum contract.
