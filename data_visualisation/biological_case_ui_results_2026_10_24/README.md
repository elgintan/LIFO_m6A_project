# Actual-score biological-case interface — 24 October 2026

**Completed locally:** four biological cases integrated into the full selected-model
explorer, with desktop and phone-size Chrome checks. **Pending:** public hosting,
deployment checks and the final five-page report. This is interface verification,
not additional biological validation or a new model experiment.

Current artifact: `data_visualisation/outputs/biological_cases_v5/site/`.
All 23 runs, seven lines, 17 metadata groups, 451,352 scoreable keys and
2,983,948 scored run-site observations remain. All 132 original score JSONs and
the four-case payload are byte-identical to their completed source evidence.
The four cases retain 92 original records: 80 scored and 12 below-20-read
unscored; none is absent. Missing is not zero. Original scores below a selected
50/100-read threshold remain visible as diagnostics.

The interface exposes group dots, equal-weight line means, group ranges,
20/50/100-read and 0.5/0.7/0.9 controls, all-run technical metadata, training
exposure, primary literature and ranked alternatives. A comparable line needs
at least two metadata groups. G3BP2's HepG2 score of 0.709145 at 50 reads stays a
one-group diagnostic, never a qualifying pair comparison. Scores are not measured
modified-molecule fractions; group ranges are not confidence intervals.

## Verification evidence

- [Independent artifact audit](artifact_check.json): 37 checks passed, all 172
  output fingerprints, all original score data, four literal keys, 92 run-score/
  readcount reconciliations and every included local evidence link.
- [Browser checks](browser_qa.json): all 36 case/depth/cutoff combinations, four
  literal-site click/reload links, invalid-position rejection, all 92 original
  rows and legacy gene/coverage/cell-line/about views. No console warnings/errors
  were observed. Includes test-diagnostic notes; no failed trial is called a pass.
- [Integration scope/resources](integration_summary.json): 9.7223782 seconds wall,
  6.4375 seconds process CPU for validation/hash/copy/final checks; imports, final
  receipt write and child Git CPU excluded. No RSS claim. This is not inference.
- [Desktop screenshot](desktop_case_full.png) and [phone-size screenshot](mobile_chart_390.png).

Ten small integration/tamper tests passed, as did Node regressions for exact keys,
malformed routes, true zero, null, one-group diagnostics, absent-record schema,
retained original scores, depth and cutoff handling. JavaScript syntax checks
passed. Scientific review and artifact audit were independent of implementation;
browser checks were run by the implementing agent.

Browser coverage is one Chromium browser in its observed dark theme. The
390-pixel phone-size test is viewport emulation, not a physical device. Charts
and tables intentionally scroll within their panels without widening the page.
Light-mode/cross-browser/physical-device and public-hosted checks remain separate.

Intermediate versions v1–v4 are retained development snapshots. The final v5
keeps original published casebook files unchanged; extra navigation files resolve
their relative plan/analysis links. Wider analysis links to a pinned public commit.
No training, inference, download or score rebuild occurred. No RONIN restart.
The full generated artifact remains local/ignored; this compact package and
frontend/helper/test source are public. See [the explorer guide](../task2_viz/README.md)
for exact local serving and deliberate fresh-integration commands. The existing
artifact needs no rebuild. The [frozen biological case report](../../sgnex_analysis/biological_case_results_2026_10_23/README.md)
remains the source of scientific results and limitations.
