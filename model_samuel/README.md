# Samuel's model

Owner: Samuel (Member 3). Enhanced LightGBM is a provisional direction; model
family and features remain his choice. No new Samuel implementation or result
has been supplied yet. Historical rounded baseline metrics are not a fresh
controlled comparison.

## Start here

Read the [minimum shared rules](../model_evaluation/SHARED_RULES.md) and
[AI context](AI_START_HERE.md), then Member 1's findings in `../eda/received/`.
Elgin accepted the methodology on 15 October 2026. Samuel's acknowledgement has
not yet been reported. Assuming agreement, use the existing exact outer splits
and common scorer. No new split needs generating.

The common requirements are data0-only fitting/tuning, the exact five outer
gene groups and assessment sites, training-only learning, common scores and
frozen all-data0 models before the exposed data1 transfer diagnostic. Inner
validation must keep genes separate when used; supplied inner roles are an
optional default. Features, architecture, search, loss and stopping settings
can differ from Elgin's. Record them rather than matching them artificially.

Member 1's EDA suggests context-dependent signals, sparse-motif fallbacks,
distribution summaries and coverage-shift checks. These guide experiments;
they do not require both owners to run identical feature comparisons. All
sites already satisfy DRACH, so a motif-present flag adds no information.

## Upload and report contribution

Keep source/dependencies, a saved predictor and small real example, one concise
methods/results draft, essential plots, full-precision predictions, commands,
configurations, input/split hashes and computation measurements. Retain local
checkpoints/logs for resuming fits and record unsuccessful changes. Do not
upload raw inputs, environments, large caches or credentials/private keys.

Use the common scoring commands in the shared rules. Coordinate any changes
to shared evaluation with Elgin. No model family is presumed to win.
