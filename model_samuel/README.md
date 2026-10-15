# Samuel's model

Owner: Samuel (Member 3). This is an independent candidate; enhanced LightGBM
is the provisional direction. No Samuel implementation or new result has been
supplied in this repository yet. Earlier rounded teammate metrics are historical
comparison evidence, not independently rerun benchmarks here.

## First work

Start with the [AI starter/context package](AI_START_HERE.md),
`../PROJECT_CONTEXT.md`, `../DATA_METHODOLOGY.md` and `../eda/README.md`.
The concrete common recommendation is
[evaluation proposal v1](../model_evaluation/EVALUATION_PROTOCOL.md).
Inventory actual current features/code before proposing additions. Member 1's
EDA suggests testing sequence/signal relationships, robust distribution
summaries and coverage dependence. A motif-present feature is uninformative
because all supplied candidate sites already satisfy DRACH. Avoid separate
unconstrained classifiers for contexts with almost no positives.

Useful candidates may include motif/full-context encodings, distribution
features, training-fitted motif references and a with/without-coverage control.
Use the same eligible evaluation sites, actual assignments and metric
definitions as Elgin; the models may use different representations. Fit any
learned preprocessing or label-dependent sampling on training only. No next
split/ratio or training run is approved by this README. Proposal v1 now
recommends the audited five gene groups, inner stopping and fresh refits;
agreement and implementation remain pending.

## Upload and report contribution

Upload your source, dependency specification, methods/results draft and
essential evidence within this folder. Document input paths, commands, model
version, assignments, seeds, actual metrics/variation, computation and failures.
Keep a saved predictor with a small example and full-precision predictions.
Do not upload environments, raw data, tokens or private keys.

Coordinate shared comparison and the required simple-baseline/m6Anet evidence
with Elgin. Later selection should cite measured strengths, weaknesses and the
effect on SG-NEx interpretation, not presume one family must win.
