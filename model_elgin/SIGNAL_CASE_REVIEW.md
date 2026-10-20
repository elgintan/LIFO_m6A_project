# Data0 signal-case review: fixed design

Specified before computing this investigation's outcomes, 20 October 2026.
This follows the completed read-depth diagnostic: retain all-read inference.

Research question: within similar sequence contexts and read coverage, what
read distributions accompany high-coverage missed positive **site labels**?
How do the valid unusual distributions identified by Member 1 appear under
the existing original-feature model?

- Read only data0 cache, labels, immutable five gene folds, verified original
  control out-of-fold (OOF) scores, and retained EDA evidence. Each OOF score
  was made by a model excluding that site's gene group. No fitting, model
  inference, data1/data2, calibration or threshold selection occurs here.
- Use >=200 original reads for the main error review. Define TP/TN/FP/FN
  using the existing reporting cutoff 0.5. This cutoff has not been validated
  as a biological calling rule; ranking metrics remain threshold independent.
- Rank motifs by number of positive labels in that cohort, with motif text
  as tie breaker. For each of the top four, take its FN nearest **that motif's
  FN median score**, with transcript/position ties. A motif without an FN has
  no selected case; no substitute is chosen.
- Match each FN to a TP and TN in its own fold, a different gene, >=200 reads
  and within a factor of two in coverage. Prefer exact 7-mer, otherwise the
  same central 5-mer; then closest absolute log coverage and stable site-ID
  ties. Never cross folds to manufacture a match. Missing matches are reported.
- Apply the same TP match rule to every high-coverage FN, with replacement.
  Report unmatched counts, context-match level and comparator reuse. Raw
  paired differences are descriptive; selection on model errors, reused sites
  and overlapping fitted models preclude independent biological inference.
- Summarise all received Member 1 named data0 unusual sites. Also illustrate
  the two explicitly named data0 handoff cases (28 and 29 reads), separately
  from the high-depth cohort. For each of
  `centre_current_iqr` and `centre_dwell_iqr`, illustrate the named site with
  greatest coverage (site-ID ties). Match a same-label, same-fold, different-
  gene comparator within 2x coverage, preferring exact 7-mer then central5.
  "Ordinary" means not named by Member 1, no previous cross-fitted median
  fence flag, and the relevant cached IQR at or below the same-label/context/
  fold/coverage candidate pool median. This is a descriptive comparator,
  not a trained quality filter or proven chemically unmodified control.
- Plot all cached reads in each selected site: empirical cumulative curves
  for central current, central event SD and central dwell, plus central vs
  adjacent current scatter. Cached float32 summaries may differ slightly from
  Member 1's original float64 calculations. Quantify that instead of treating
  it as a biological change. All valid sites and labels remain intact.

Limits: broad distributions do not prove a mixture or another modification;
site labels do not identify modified individual reads. Matched examples
cannot establish causality or global model superiority. This is development
analysis after prior data0 model comparisons, not new independent evaluation.
Keep full case/pair CSVs local; publish compact aggregate evidence and plots.
An interrupted descriptive run can be rerun from immutable inputs; status,
logs, hashes and a completion receipt distinguish complete output.
