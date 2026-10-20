# Working together

This repository collects the team's code, checked findings and report contributions. Use the project handout for the requirements. The model approaches below are starting directions, not fixed commitments.

## Who puts what where?

**20 October update:** Elgin now continues all integrated code on one laptop
from the delivered packages. The attribution below records contributions;
Members 4/5 do not need to run parallel pipelines or wait for further handovers.
They can review findings when actual selected-model predictions exist. See
[integration status](INTEGRATION_STATUS.md) for the 23-run scope and remaining work.

- **Member 1 -> Elgin:** Send the EDA/context package directly to Elgin. Member 1 does not need to upload to GitHub. Elgin reviews and organises the shareable material in `eda/`, retaining its attribution.
- **Elgin -> `model_elgin/`:** Develop one candidate, currently exploring neural networks. Retain methods, code, actual results and model records.
- **Samuel -> `model_samuel/`:** Develop a separate candidate, currently considering LightGBM improvements. Retain the same kinds of evidence.
- **Elgin and Samuel -> `model_evaluation/`:** Agree the common methodology, compare candidates fairly and evaluate the selected final model. Keep required baseline and m6Anet comparisons here when completed.
- **Member 4 -> `sgnex_analysis/`:** Maintain sample metadata, reproducible cell-line comparisons and interpretations.
- **Member 5 -> `data_visualisation/`:** Develop the researcher interface, input-data instructions and a short explanation of the questions it answers.

For a completed contribution, provide a short findings/methods draft, the code that produced it, and essential result tables or figures. State the dataset/sample and model version used, important limitations and anything still pending. No separate handover form is required.

## Before new training

Elgin and Samuel use the [minimum shared rules](model_evaluation/SHARED_RULES.md), accepted by Elgin on 15 October and used by Samuel's submitted candidate. Reuse the exact existing outer assignments and common scorer. No new split is needed. Model family, features, tuning and stopping settings remain independent inside the common fitting boundaries. Member 1's findings guide useful experiments and report interpretation.

Treat findings as hypotheses to test. Do not relabel or discard unusual sites simply because a model disagrees. Fit learned preprocessing using the appropriate training partition. Record previous evaluation exposure honestly: data1 has already been inspected and cannot become an untouched test by renaming it.

## Everyday upload process

1. Pull the latest team changes before starting. Work mainly in your assigned folder; coordinate changes to shared files with Elgin.
2. Edit and save your files. Check that tables, plots and claims correspond to the same dataset and model version.
3. In VS Code **Source Control**, review the changed files, stage only your intended contribution, enter a clear commit message and select **Commit**.
4. Select **Push** to upload the commit. Open GitHub and check that the files appear. A local commit alone is not an upload.

If Git reports a conflict or rejects a push, stop and inspect it with Elgin rather than using force push. See [the setup guide](GITHUB_VSCODE_SETUP.md) for the initial connection and exact clicks.

## Public files

The repository is intended to be public. Review all files before staging. Never upload credentials, private keys, tokens, personal access details, `.env`, or private URLs. Keep raw datasets, virtual environments, temporary caches and redundant archives out of normal Git history; use the documented data-access procedure instead. Do not override `.gitignore` to upload an excluded file without understanding why it was excluded.

Keep original received packages unchanged outside this repository. Public copies can be edited for portability, privacy and current roles, with the original authors credited. Preserve actual errors and negative results; do not present proposed or example results as completed work.
