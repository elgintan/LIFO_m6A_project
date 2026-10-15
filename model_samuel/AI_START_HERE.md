# Samuel: AI starter context

Repository: https://github.com/elgintan/LIFO_m6A_project

Elgin accepted the shared methodology on 15 October 2026. Samuel's acknowledgement
has not yet been reported. Assuming agreement, the exact splits and shared
scorer are ready. New candidate training/results remain pending.

## Copyable starter

> I am Samuel, Member 3 of the LIFO DSA4262 project. Help me develop an
> independent m6A site-prediction pipeline in `model_samuel/`. Enhanced LightGBM
> is a starting direction; features and architecture remain flexible. Elgin
> develops a separate candidate, tentatively neural.
>
> First read `model_evaluation/SHARED_RULES.md`, `PROJECT_CONTEXT.md`,
> `eda/received/MEMBER1_CONTEXT_2026-10-13.md`,
> `eda/received/feature_specification.csv`, `DATA_ACCESS.md` and my folder README.
> The detailed evaluation document gives background; the minimum shared rules
> define what must match. Older received role instructions are historical.
>
> Use the existing exact `eda/received/shared_folds/data0_folds.csv`; verify it
> against my local course data0 labels using the documented --verify-only
> command. Do not regenerate it, even with the same seed. Join by transcript
> ID and numeric position. In round f assess fold_id==f and learn only from
> the other groups; run all five rounds. Inner tuning/stopping must keep genes
> separate and exclude the assessment fold; `model_evaluation/cv_rounds.csv`
> supplies an optional default. All learned preprocessing and model weights
> are fitted within permitted training data. Do not warm-start from an old
> model fitted on all data0.
>
> Use the common evaluator and schema. Primary data0 comparison is mean across
> five fold scores of (ROC AUC + trapezoidal PR AUC)/2. AP and pooled OOF scores
> are separate. Keep one OOF prediction per site with fold_id. Freeze/refit the
> nominated model on all data0 and save/hash it before evaluating data1. data1
> is an already-exposed HEK293T transfer diagnostic, not an untouched test.
> Do not use data1 for new fitting, stopping or selection in this cycle.
>
> Model family, features, read handling, losses, optimisation, search, seed and
> stopping settings can differ from Elgin's; document them. Inspect my actual
> implementation before suggesting additions. Member 1 found context-dependent
> signal relationships, sparse positives in some motifs, coverage-label shifts
> and valid unusual read distributions. Use those findings to motivate useful
> controlled experiments. They do not mandate identical feature experiments.
> Do not delete difficult valid sites or force a model to win. IDs/processing
> offsets are metadata, not default predictive inputs. Preserve original labels.
>
> Keep code/dependencies, commands/configurations, full-precision predictions,
> actual results/plots, saved model/example, local checkpoints/logs and measured
> computation. Provide one concise methods/results draft and limitations.
> Never upload raw data, environments, credentials or private keys; never read
> `.pem` files. The public URL supplies project context, not local raw matrices.
>
> data0 is HCT116; data1 is HEK293T; data2 is synthetic with fractional/template
> structure. Exclude data2 from tuning and do not invent a binary-label rule.
> The selected saved pipeline will predict all required datasets and SG-NEx.
> Site scores/attention are not validated molecule-level truth or modification
> fractions. The dashboard's current modification scores are simulated.
> Prioritise a defensible five-page report and SG-NEx analysis/visualisation;
> references guide reasoning and the course handout defines requirements.
