# Member 4 integration evidence

Integrated 20 October 2026 from the latest `Member4_Handover_extra details/Member4_Analysis` package after the repository fast-forward. Scope is the user-selected 23 processed runs. No training, full download/inference, real-score analysis or publication was performed by this folder integration.

All 89 entries in the received inventory matched recorded SHA256. Original handover, plan, report contribution, candidate review, validation, AI-use disclosure and inventory are preserved byte for byte under `provenance/member4_20261019/`. That inventory includes deliberately unpublished files and is not an index of this public folder. `provenance/import_receipt.json` records selected source/current hashes and deliberate omissions.

Selected scripts/tests, requirements and small public-source manifests were imported. Two optional candidate utilities now default to canonical sibling `model_samuel/`; the optional test accepts `MEMBER3_CANDIDATE_DIR` and skips if candidate/dependencies are unavailable. Scientific comparison, model/features, scorer, folds, thresholds and learned preprocessing were not changed.

The nine-column manifest retains all 23 rows/group assignments and pending model/reference declarations; coverage and future prediction paths now use ignored `outputs/`. Active MODEL_INFO points to the canonical candidate. Active README/findings/reference guidance supplies repository-root commands; archived instructions retain their original package-relative paths.

The new standard-library restoration helper verifies/copies received metadata/results/figures and two reading guides locally. It protects differing existing evidence, refuses unsafe paths and records restorations. Its temporary synthetic checks cover copy/reuse, corruption refusal, unsafe paths and preservation of changed outputs.

Public omissions are deliberate: nested candidate/model/development predictions, site-level coverage/annotation/alias/version tables, derived CSVs, figures/logs and HTML/notebook. Received metadata/results/figures/guides are retained under ignored `outputs/received_member4_20261019/`. Original `render_report.py` is coupled to the full received layout and is not imported; existing guides remain available locally. Raw signals were not supplied. Small public source inventories are retained; broader sample metadata are historical local provenance, not a scope-expansion request.

Root ignore rule required: `/sgnex_analysis/outputs/`. Environment setup uses the already ignored `.venv/` pattern. Source snapshots and original hashes remain outside the repository in the received package as well.

Actual local checks (20 October 2026):

- `../advanced_model/.venv/Scripts/python.exe -B -m unittest discover -s sgnex_analysis/tests -v`: 10 tests discovered, **9 passed and 1 optional LightGBM example test skipped** because that dependency is absent in this existing environment. Test time 24.841 s; whole command wall time 31.802 s, exit 0. No candidate prediction was performed by this test run.
- Initial attempt failed on restricted system temporary/cache permissions before fixture CLI execution. Its log is preserved. Retry used `TEMP`, `TMP`, `TMPDIR` and `MPLCONFIGDIR` beneath ignored `outputs/checks/`; the README supplies exact settings. No scientific source change was needed for this environment issue.
- `../advanced_model/.venv/Scripts/python.exe -B sgnex_analysis/scripts/restore_received_data.py --source "../Other members work/Member4_Handover_extra details/Member4_Analysis"`: **35 received files restored/verified**, 1.803 s whole-command wall time, exit 0. This copied existing evidence only. A timestamped source-inventory/file-hash receipt is retained under `outputs/received_member4_20261019/restore_receipts/`.
- `model_samuel/.venv/Scripts/python.exe -B -m unittest discover -s sgnex_analysis/tests -p test_member3_prediction.py -v`: **1 test passed**, test time 19.456 s, exit 0. Uses the current canonical sibling candidate and its prepared environment; checks ten-site saved-score parity, >=25-finite-read subset parity and cross-batch duplicate refusal. No new dependency installation, training or full-run inference. Its log and whole-command timing JSON are `outputs/checks/member3_adapter_20261020.*`.

Exact command/exit/timing JSON and successful/failed logs are retained in `outputs/checks/`. Historical Member 4 validation logs remain separately identified under restored received evidence. Copying receipts or rerendering guides is not new scientific verification. These checks used the existing laptop environment, not a clean installation of the received pinned requirements.

Pending: final selection, actual signal/reference/preprocessing evidence, complete prediction/eligibility audit, replicated real-score analysis and display export. Clean Ubuntu runtime, biological independence and calibration are not established by synthetic tests.
