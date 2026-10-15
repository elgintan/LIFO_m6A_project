# Samuel: copy this context into your AI

Repository: https://github.com/elgintan/LIFO_m6A_project

The common evaluation protocol below is **proposal v1, not yet agreed or
implemented**. You can inspect the project and propose model ideas now. Wait
for agreement and the shared checked evaluation files before claiming a
comparable new training result. Do not silently invent a different split.

## Starter prompt

> I am Samuel, Member 3 of the LIFO DSA4262 team. Help me develop an independent
> site-level m6A prediction pipeline in `model_samuel/`. Enhanced LightGBM is my
> provisional direction, but I can choose other features or methods with a
> justified reason. Elgin develops a separate candidate, tentatively neural.
> We compare complete pipelines under shared evaluation, rather than requiring
> identical features or architecture.
>
> First inspect the current repository. Read `PROJECT_CONTEXT.md`,
> `DATA_METHODOLOGY.md`, `model_evaluation/EVALUATION_PROTOCOL.md`,
> `eda/received/MEMBER1_CONTEXT_2026-10-13.md`,
> `eda/received/feature_specification.csv`, `eda/split_review/README.md`,
> `DATA_ACCESS.md` and my folder README. Check whether the proposal has since
> been agreed/revised. Older received handoffs assigning me only a checking
> role are outdated. Course references guide our reasoning; the handout sets
> requirements. If the AI cannot browse the repository, clone/download it and
> provide these files locally. A public URL alone does not give local AI tools
> access to the raw training files.
>
> Explain what is already implemented in any code I supply before proposing
> improvements. Use Member 1's findings to motivate actual comparisons:
> sequence changes the interpretation of signal, some motifs have only 1-2
> positives, coverage-label relationships shift between datasets, and unusual
> across-read distributions are not automatically erroneous. All candidate
> sites already satisfy DRACH, so a motif-present indicator is uninformative.
> Investigate context identity/flanks, distribution summaries and justified
> context-dependent features. Fit learned reference values on training only.
> Choose two useful EDA-motivated comparisons for our first cycle.
>
> Follow the agreed common protocol when available: data0-only fitting/tuning;
> exact shared gene groups and eligible sites; inner gene-separated stopping;
> fresh four-group refits before held-out-group predictions; one shared metric
> implementation. The proposal recommends the audited existing five groups,
> with primary mean-fold `(ROC AUC + trapezoidal PR AUC)/2`, and AP separately.
> Keep per-group scores and full-precision predictions, plus motif/coverage
> diagnostics. Model design, training-only feature engineering and tuning can
> differ from Elgin's. Document the actual search and computation performed.
>
> data0 and data1 have already been explored. data1 was evaluated on earlier
> models: it is an exposed transfer diagnostic, not a blind test. Do not use
> it for new selection, stopping or fitting in this cycle. Freeze/hash both
> candidates before its diagnostic scoring. data0/data1 share 67,320 site IDs,
> including 3,872 differing labels; retain original labels. Gene provenance is
> incomplete. Do not pool data1 by default. data2 has fractional labels and
> repeated templates; do not silently binarise them or use it for tuning.
>
> Fit all split-specific models from fresh weights; the archived all-data0
> neural checkpoint cannot seed a new held-out-data0 claim. Save checkpoints
> and logs for resuming the identical fit. Retain valid difficult sites and
> natural assessment prevalence. Do not use transcript/gene/fold IDs or
> processing offsets as predictive shortcuts. Do not force our pipeline to win.
>
> Deliver runnable training and prediction code, dependencies, a saved model
> with a small real prediction example, one concise methods/results draft,
> essential figures, configurations, commands, actual metrics/predictions and
> computation measurements. Keep work within `model_samuel/`; propose shared
> protocol changes rather than overwriting them. Do not upload raw data,
> environments, credentials/private keys or large intermediate caches. Never
> read or commit `.pem` files. Label proposed, completed and unverified work.
>
> The main narrative is EDA -> justified modelling -> fair comparison -> SG-NEx
> interpretation and interactive visualisation. We have a five-page report and
> a 28 October 2026 deadline, subject to later official announcements. Avoid
> letting an unlimited model search crowd out Task 2 and the report. Site
> probabilities/attention are not validated molecule-level labels or direct
> modification fractions. Existing dashboard modification scores are simulated.

## What to send Elgin

One short methods/results draft, code/dependencies, saved predictor/example,
the agreed per-group prediction files and metrics, two EDA-motivated comparison
results, essential figures, commands and computation details. Include limitations
and unsuccessful changes. Use the repository's simple contributing workflow;
there is no separate mandatory team-wide findings register.
