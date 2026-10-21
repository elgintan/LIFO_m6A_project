# Cap128 calling-threshold study: fixed design

Specified before scoring inner checkpoints, 21 October 2026. Keep this file
unchanged after the first inference receipt; its hash identifies the study.

Use only the completed cap128 data0 five-gene-fold experiment. Do not change
weights, source, normalisers, reference features, continuous scores or splits.
No new neural training, probability calibration, data1/data2 access, SG-NEx
inference, model-family selection or loss-weight experiment is included.

For each outer round f, load its verified `inner/best.pt`, trained on the
three groups excluding f and (f+1)%5. Predict every site in inner group
(f+1)%5 with all reads, its saved normalisation and the original predictor
(batch64, four CPU threads). Check selected epoch, config, fit/source hashes
and agreement with that epoch's recorded inner metrics. Never substitute the
four-group refit to score this group: that refit trained on it.

Choose a raw-score cutoff maximising site-level F1 on this inner group only.
Use `score >= cutoff`, group equal scores before computing counts, and compare
F1 fractions with integer cross-products. Test each distinct observed score;
the minimum includes the all-positive decision. An all-negative candidate has
F1=0 and cannot beat the positive-F1 optimum when both classes are present.
On an exact F1 tie, select the higher cutoff. Refuse missing classes, malformed
scores, incomplete keys or incompatible sources; do not invent a fallback.

Apply this fixed per-round cutoff to only its corresponding excluded outer
fold's existing four-group-refit scores. Compare with that same fold at0.5.
Preserve all five cutoffs, selected-inner counts/F1, outer confusion counts,
precision, recall, F1, specificity and accuracy. Show unweighted fold means
and sample SD separately from pooled confusion counts. Pooled learned-policy
decisions use five cutoffs; they do not evaluate one global cutoff. Show the
original ROC/PR/S unchanged. Supplementary coverage groups follow the existing
20–29,30–49,50–99,100–199,200+ boundaries; no group-specific cutoffs are fitted.

The proposed final all-data0 aggregation is the median of the five selected
inner cutoffs, frozen as a deployment-rule proposal. Do not apply it to all
outer labels and call that an independent validation; its five components
collectively use all data0 groups. It is not guaranteed to maximise final-model
F1 and its transfer to a future all-data0 refit remains untested. Choosing an
epoch and cutoff on the same inner group is internal selection; inner F1 is
optimistic. Excluded outer assessment remains boundary-separated for this
procedure, but reused architecture-development folds are not a new blind test.

Write checkpointed inference receipts and full inner prediction CSVs locally.
Completed rounds may be reused only after matching source/plan/config/input
and prediction/result hashes. Interrupted rounds restart without overwriting
completed evidence. Measure resource use; logs and actual inputs remain local.
Publish only code, this plan, aggregate reports/plots and compact provenance.
Keep negative results. A threshold cannot improve ranking or establish
biological truth, calibrated probability or a modified-molecule fraction.

Exact command from the repository root:

```powershell
../advanced_model/.venv/Scripts/python.exe -B -u model_elgin/tools/validate_calling_threshold.py
```
