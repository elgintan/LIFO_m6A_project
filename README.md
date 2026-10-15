# LIFO: m6A prediction and SG-NEx exploration

NUS DSA4262 team project. We develop two candidate predictors, compare them
under one evidence-based protocol, and use the selected model to explore m6A
patterns across the required SG-NEx direct-RNA datasets.

**Current stage: methodology accepted by Elgin, 15 October 2026.**
Samuel's acknowledgement has not yet been reported. No new model has been
trained under this methodology.
The saved October 7 neural model is a historical starting point. The explorer
is a prototype: its modification scores are simulated.

## Start here

1. Read [project context](PROJECT_CONTEXT.md).
2. Read the [minimum shared evaluation rules](model_evaluation/SHARED_RULES.md).
   Use the existing exact gene assignments and common scoring code. Features,
   architecture and tuning remain independent. The [detailed methodology](model_evaluation/EVALUATION_PROTOCOL.md)
   and [EDA rationale](DATA_METHODOLOGY.md) provide background.
3. Open your folder below and follow its README.
4. Use [contributing instructions](CONTRIBUTING.md) for simple handovers.

| Folder | Owner and purpose |
|---|---|
| [eda](eda/README.md) | Member 1's received findings; Elgin curates her direct handoff |
| [model_elgin](model_elgin/README.md) | Elgin's independent candidate; neural-network direction is provisional |
| [model_samuel](model_samuel/README.md) | Samuel's independent candidate; enhanced LightGBM is provisional |
| [model_evaluation](model_evaluation/README.md) | Shared candidate comparison, selection and final evaluation |
| [sgnex_analysis](sgnex_analysis/README.md) | Member 4's sample inventory, comparisons and interpretation |
| [data_visualisation](data_visualisation/README.md) | Member 5's interface and real-data integration |

Member 1's work must influence features/context, quality decisions and how
evaluation populations are constructed. Every important change should connect
an EDA observation to a decision, a controlled comparison and report evidence.
Retaining an existing choice also needs a reason. Keep difficult valid examples
and distinguish technical quality from cases that are merely hard to predict.

## What is available

- Received EDA, code, six figures, derived tables and historical folds in
  `eda/received/`; originals were copied unchanged.
- An actual archived neural model, source, small prediction example, metrics,
  history and three prediction CSVs in `model_elgin/baseline_2026_10_07/`.
- The supplied explorer in `data_visualisation/prototype/`. Its scores are
  simulated and cannot support scientific conclusions.
- A new descriptive [historical-split composition audit](eda/split_review/README.md).
- A [source receipt](SOURCE_RECEIPT.json) identifying unchanged copies and one
  disclosed portable-path edit in the archived report generator.

Raw data, environments, large caches and intermediate checkpoints are excluded
from Git. See [data access](DATA_ACCESS.md). Original full local run records
remain outside this clean repository.

## Next actions

Samuel acknowledges the shared rules, verifies his local data against the
existing fold manifest, then each owner develops a fresh candidate. Use the
common scorer for five-fold data0 results, freeze/refit on all data0 and
evaluate on already-exposed data1. Samuel can use the
[AI starter/context package](model_samuel/AI_START_HERE.md). Candidate comparison and
the required simple-baseline/m6Anet checks precede selecting one pipeline for
real SG-NEx predictions. Members 4/5 can prepare inventory, analysis and the
interface in parallel.

The course report plus interactive visualisation carries 50 percentage points;
model performance carries 5, assessed with ROC/PR AUC. Ranking against other
teams does not determine the grade. The final report limit is five pages,
excluding permitted front matter/references. The supplied handout deadline is
28 October 2026, 23:59 Singapore time; check later announcements.

The repository is public at [elgintan/LIFO_m6A_project](https://github.com/elgintan/LIFO_m6A_project).
For collaborator setup, follow [GitHub/VS Code setup](GITHUB_VSCODE_SETUP.md).
For evidence of AI assistance and corrections, see [AI use](AI_USE.md).
