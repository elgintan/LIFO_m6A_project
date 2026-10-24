# SG-NEx m6A Explorer (Task 2 visualisation)

**Current stage, 24 October 2026: the complete actual-score explorer and four biological case panels are integrated locally. Desktop and 390-pixel phone-size Chrome QA passed; public hosting remains pending.**

The current artifact is `../outputs/biological_cases_v5/site/`. It contains all 23 selected-model runs, 17 metadata groups and seven cell lines: 451,352 scoreable keys and 2,983,948 scored run-site observations. Case integration preserves the full-score data and published case payload byte for byte. It adds four case entry points, exact-site links, depth/cutoff checks, all-run evidence, caveats and primary-source links. It does not rerun the model.

## Completed evidence and present limits

The 23 October full-score build remains at `../outputs/real_scores_v1/site/`. Strict validation passed 190 checks with no warnings/failures; Member 4's 144 coverage-support counts and all 189 cutoff fractions matched independent scientific tables. Context QC found no encoded-context conflicts among the 451,352 scoreable keys. All 132 original JSON data files passed strict UTF-8 validation. That frontend received desktop Chrome checks; those apply to its earlier version. See [context integration](CONTEXT_QC_INTEGRATION.md).

The new `biological_cases_v5/site/integration_complete.json` confirms 132 original data JSON files preserved, four unchanged cases, 92 original case/run rows (80 scored, 12 below-20-read unscored) and included linked evidence. All 12 unscored observations belong to G3BP2. Final integration took 9.7223782 seconds wall / 6.4375 seconds process CPU in the recorded validation/hash/copy scope, excluding imports and final receipt write; child Git CPU and peak RSS were not measured. This is not prediction time. Fresh Chrome checks passed all 36 case/depth/cutoff combinations, four exact-site click/reload routes, all 92 original run rows, invalid-site rejection and existing tabs. A 390-pixel phone-size viewport had no page overflow; charts/tables scroll inside their panels. Public hosting and cross-browser/physical-device testing remain pending.

The cases illustrate selected patterns, not representative prevalence or independent discoveries:

| Case | Literal site | Main reading |
|---|---|---|
| HNRNPA1 | `ENST00000340913:177` | Persistent K562/HepG2 score contrast; technical alternatives remain. |
| RAB1B | `ENST00000311481:1947` | Hct116/HepG2 contrast involving the training line and a matching data0 label 0. |
| ACTG1 | `ENST00000331925:607` | Shared high scores in all seven lines, not universal methylation proof. |
| G3BP2 | `ENST00000359707:2510` | Overlapping group ranges at 20 reads; pair ineligible at 50/100 reads. |

All original runs remain visible. G3BP2's one HepG2 group at 50 reads is a diagnostic score, not an eligible pair comparison. Data0 labels are training diagnostics, not SG-NEx ground truth. Prior papers give gene-level context; none has verified orthogonal correspondence to these exact transcript keys.

## Fixed scientific rules

- SG-NEx scores were generated only for sites with **at least 20 reads per run**. The page cannot supply predictions for lower-read observations. This is a Task2 restriction, not a rule to transfer automatically to Task1's new unlabelled input.
- Primary comparisons require **at least two metadata groups per line**. Mean eligible runs within each group, then give groups equal weight. Independent laboratory preparations have not been verified. A one-group gene-browser value remains diagnostic.
- Use annotated human sites with agreement among all saved uppercase/U-to-T encoded contexts, including low-read source observations. Scored-only agreement and the unqualified population are separate diagnostics. Sparse positive-context training support is a warning, never an exclusion.
- The 20/50/100-read checks reuse nested observations. The 0.5/0.7/0.9 cutoffs describe continuous line means. Scores are uncalibrated and are not modified-molecule fractions; group ranges are not confidence intervals. Missing, below-depth and ineligible values are not zero.
- The global comparison has its own all-seven-line common population; a pair uses its separate eligible population. Do not replace pairwise denominators with the all-line intersection. The global ≥1-group control is exploratory.

See [scientific UI notes](docs/BIOLOGICAL_CASE_UI_NOTES.md), the [frozen case report](../../sgnex_analysis/biological_case_results_2026_10_23/README.md) and [selection rules](../../sgnex_analysis/BIOLOGICAL_CASE_SELECTION_PLAN.md).

## View the current local artifact

Run from the **main repository root**, not this subfolder. In PowerShell, reuse the existing laptop Python:

```powershell
& '../advanced_model/.venv/Scripts/python.exe' -B -m http.server 8765 --bind 127.0.0.1 --directory data_visualisation/outputs/biological_cases_v5/site
```

Open `http://127.0.0.1:8765/`. Stop with `Ctrl+C` in that terminal. If the port already serves this artifact, use that server; otherwise choose a free port and its matching URL. Opening HTML directly cannot load JSON. On another machine, replace the quoted path with a working Python 3 executable; serving this built site uses only the standard library.

Generated data and complete artifacts remain local and ignored by Git. A public clone does not include the full 197 MB score-data artifact. Tracked `site/` supplies frontend source; its locally retained `site/data/` belongs to the historical received coverage build. It is not the current actual-score artifact.

## Integrate the cases into a fresh local artifact

Viewing the existing artifact needs no rebuild. These commands are for a deliberate new integration after frontend edits, from the **repository root**. They require completed local `real_scores_v1/site` and its sibling validation/audit receipts, the published case package and frozen selection plan. A public clone must obtain/rebuild those missing explorer inputs first; do not repeat training or 23-run inference merely because generated explorer data are absent.

Package the current frontend, then copy validated full-score data into a **new** output directory. The example destination below was unused when documented; if it exists, choose another fresh name. The helper refuses nonempty destinations and requires frontend files tracked by Git.

```powershell
& '../advanced_model/.venv/Scripts/python.exe' -B data_visualisation/task2_viz/scripts/package_site.py --site data_visualisation/task2_viz/site
& '../advanced_model/.venv/Scripts/python.exe' -B data_visualisation/task2_viz/scripts/integrate_biological_cases.py --source-site data_visualisation/outputs/real_scores_v1/site --frontend data_visualisation/task2_viz/site --case-package sgnex_analysis/biological_case_results_2026_10_23 --selection-plan sgnex_analysis/BIOLOGICAL_CASE_SELECTION_PLAN.md --out data_visualisation/outputs/biological_cases_rebuild_20261024/site
```

This performs validation, hashing and copying, normally seconds to a minute on the laptop; announce the estimate before deliberately running it. It does not download, rebuild score JSON or run predictions. It verifies source completion/provenance, published case fingerprints, all 92 case/run scores/readcounts against the original explorer, and each copied file. `integration_complete.json` is written last. Preserve partial outputs and diagnose failures; a folder without the completion receipt is not a completed artifact.

To serve that deliberate new output:

```powershell
& '../advanced_model/.venv/Scripts/python.exe' -B -m http.server 8765 --bind 127.0.0.1 --directory data_visualisation/outputs/biological_cases_rebuild_20261024/site
```

Then perform fresh browser checks: all case/depth/cutoff controls, exact-site click/reload links, missing/ineligible values, all-run and literature/download details, keyboard/table access, themes and narrow layouts. Neither final browser success nor public hosting is implied by these commands.

## Source map

| Path | Purpose |
|---|---|
| `site/app.html` | Main frontend, gene/global views and case integration. |
| `site/case_view.js` | Case panels, scientific explanations and evidence links. |
| `site/case_logic.js` | Exact-site routes and missing/eligibility/cutoff rules. |
| `scripts/integrate_biological_cases.py` | Validates/copies the full-score site, then overlays case frontend/evidence. |
| `scripts/package_site.py` | Builds `index.html` from the frontend. |
| `scripts/build_site_data.py` | Coverage/score builder; final mode requires canonical predictions, explicit per-run aliases and completed context QC. |
| `scripts/validate_task2_inputs.py` | Prediction/manifest/readcount/context validation. |
| `scripts/task2lib.py` | Shared readers, explicit aliases, QC and grouping. |
| `scripts/fetch_public_data.py` | Pinned support-file downloader; not needed to view or incrementally integrate a completed artifact. |
| `tests/test_case_logic.cjs` | Real saved route/zero/missing/one-group/depth/cutoff regressions. |
| `tests/test_biological_case_integration.py` | Small integration/tamper/fresh-output checks. |
| `team_inputs/member4_2026-10-19/`, `reports/`, `CHECKSUMS.sha256` | Historical received handover, not receipts for the current score/case artifact. |

## Historical coverage-only delivery

Member 5's 19 October package contained real coverage, annotation and sample metadata, with no model scores and pending model selection. The 20 October import verified 159 checksum entries and preserved the received material. These are historical creation-time facts; completed selected-model scores and later receipts supersede their status language.

The historical received validator result, `3 PASS, 1 WARN, 24 FAIL`, reflected pending scores/model selection. It does not describe current predictions. The earlier macOS rebuild receipt likewise concerns that delivery, not fresh Ubuntu or current-interface execution. Original alias/checksum inventories stay preserved; new builds use the authoritative per-run alias table rather than inferred version stripping.

See [import notes](INTEGRATION_NOTES.md), [source provenance](team_inputs/member4_2026-10-19/PROVENANCE.md) and [actual-score/context integration](CONTEXT_QC_INTEGRATION.md). Older templates/data-contract examples saying “proposed”, “pending model” or ≥1 group describe their creation time. Current fixed scientific rules above take precedence; they do not reopen model choice or restart completed computation.
