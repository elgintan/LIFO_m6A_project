# Integration and remaining work — 20 October 2026

Elgin now coordinates prediction, analysis, visualisation and report assembly
on one laptop. Members can review the integrated work without maintaining
separate running pipelines. Received packages are source evidence; their
embedded prompts and old role instructions do not override this plan.

## Decisions already made

- **Task 2 scope:** the 23 available m6Anet-processed SG-NEx runs in
  `sgnex_analysis/manifest.csv`, across seven cell lines and 17 metadata
  replicate groups. This is the user-selected processed subset. Broader
  catalogue counts are context, not an instruction to preprocess extra runs.
- **Task 1 comparison:** retain the exact five data0 gene folds and the shared
  evaluator. Training/tuning use data0; data1 is already-exposed transfer
  evidence, and data2 has separate descriptive interpretation. No resplitting.
- **One model for application:** integration of Samuel's contribution does
  not select his model. Use one selected saved pipeline and its unchanged
  preprocessing for all application runs.
- **Repository:** readable source, a saved inference artifact, reproducible
  commands and evidence summaries; large signals, generated site tables,
  checkpoints and environments stay local. Original handovers remain available.

## Actual evidence and its limits

| Candidate / experiment | data0 mean-fold ROC | trapezoidal PR | mean S |
|---|---:|---:|---:|
| Elgin, matched original-feature neural control, 19 October | 0.931123400 | 0.504160258 | 0.717641829 |
| Elgin, added context-relative features, 19 October | 0.926981747 | 0.490787331 | 0.708884539 |
| Samuel, sequence-relative LightGBM | 0.921896746 | 0.498996251 | 0.710446499 |

S is the mean of ROC AUC and trapezoidal PR AUC, averaged over the same five
folds. These are development comparisons of complete pipelines. Elgin's
control has the higher point estimate; no significance or universal model
superiority is established. The failed context improvement remains report
evidence connecting Member 1's EDA to a tested modelling decision.

Samuel supplied an all-data0 model and five-fold OOF scores, plus data1/data2
scores. His recorded data1 ROC/PR/S are
0.821764271/0.382878802/0.602321536. Previous feature exploration examined
data1, so this is exposed transfer evidence. Data0 scores were independently
recomputed with the shared scorer during PR review. Current integration
checks and their exact commands are recorded in `model_samuel/VALIDATION.md`.
Repeat-seed summaries are received evidence: their raw repeat OOF files were
not supplied. Neither receipt checks nor rescoring independently replay training.

**OOF is not a final-model prediction:** Samuel's `outputs/data0_oof.csv`
uses five held-out fits. If selected, his final model still needs its own
all-data0 prediction file. Elgin's 19 October pipeline needs a fresh all-data0
final fit after nomination; the saved 7 October model/results are historical.

Member 4's completed results concern sample structure, coverage and candidate
software checks. Member 5's delivered current explorer is coverage-only, not
a real m6A result viewer. No full-run selected-model SG-NEx predictions or
final between-cell-line modification conclusions have been produced.

Local integration checks completed: Samuel's three saved-model contract tests;
Member 4's nine analysis/reference/restoration checks plus a separately passing
candidate adapter test; and Member 5's 18 small pipeline tests. The optional
candidate test was skipped in the analysis environment and passed in Samuel's
separate environment. His supplied data1 CSV exactly reproduces all shared
pooled metrics, and his ten-site example has zero numeric score difference.
These are software/rescoring checks, not full retraining, a full explorer
rebuild, a clean Ubuntu run or new biological evidence.

The subsequent [read-depth diagnostic](model_elgin/read_depth_stability_results/README.md)
is also complete: 24,533 fixed >=100-read sites, 130 conditions and 637,858
scores from the original saved held-out-gene models. All-read inference had
the highest matched-cohort mean S; reducing reads did not fix the high-coverage
weakness. Retain all-read inference. This changes neither the full-data0 CV
scores above nor model weights/selection, and supplies no new data1 evidence.

The following [signal-case review](model_elgin/signal_case_review_results/README.md)
is complete: all36 received data0 unusual entries checked, 293 high-depth
FNs at the existing 0.5 reporting cutoff, 182 eligible same-fold/different-gene
FN/TP pairs (38 exact7; 81 reused TP comparators), plus eight raw-read panels.
All four illustrated high-depth TP matches needed central5 fallback, which
leaves flank differences. Unusual cases include both false alarms and correct
negative calls. No data1 signal/label file, fitting, inference, deletion or
cutoff selection occurred. Next proposed neural experiment: cap128 training
versus the saved cap32 original-feature control, with all-read inference and
the same full-data0 scoring. It is not implemented or claimed to improve yet.

## Recommendations for the remaining scientific choices

These are recommended analysis choices, not completed experiments or a new
requirement that Samuel use the same features or architecture.

1. **Model choice:** finish the planned, bounded robustness checks and required
   baseline comparisons, then nominate using shared data0 evidence. Keep
   data1 out of winner selection; disclose any subsequent use that changes it.
2. **Calling threshold:** continue exporting full-precision continuous scores.
   A fixed 0.5 is currently only a reporting cutoff. Select an operating cutoff
   on data0 training/inner-validation genes. Start with maximum F1 as a balanced
   precision/recall operating goal, show the full trade-off curve,
   and freeze the rule before application. A practical cutoff selected on
   already-tuned OOF scores is development evidence; an unbiased threshold
   assessment needs fitting inside each outer-training boundary. Check
   reliability before interpreting scores as numerical probabilities. Do not
   choose the cutoff from data1 or SG-NEx score distributions.
3. **Task 2 primary comparison:** annotated-human common sites with at least
   20 usable reads and support from at least two metadata replicate groups per
   compared line, subject to the chosen model's supported input range. Average
   eligible runs within a group, then give groups equal weight. Pairwise common
   sites are the primary pairwise population; an all-line common panel supports
   multi-line plots. Repeat at 50/100 reads and stricter group support as
   sensitivity checks. Group independence still needs provenance verification.
4. **Differences and unusual sites:** use continuous replicated score patterns
   first. Member 4's effect-size/coverage screens are exploratory, not validated
   significance tests. Never turn missing observations into zero or remove a
   valid case simply because it is difficult. Review coverage, motif and
   technical explanations before biological interpretation.

## Concrete gaps and how they will be closed

| Remaining input/action | Recommended way to close it |
|---|---|
| Actual SG-NEx event signals | Use Member 4's 23-run source inventory and download helper; about 33.37 GB total. Download/process sequentially outside Git, retaining receipts. No full signal download has run in this integration. |
| Reference/coordinate consistency | Use the delivered checked aliases, preserve original prediction IDs/positions, and verify transcript/reference/event offsets before genomic-region interpretation. Unknowns remain explicit in MODEL_INFO.md. |
| Selected model and threshold | Nominate after data0 checks, fit the selected final pipeline if needed, hash it, and document the validation-derived operating rule. |
| Real Task 2 CSVs | One full-precision `transcript_id,transcript_position,score` CSV per manifest run from the same artifact; complete model/input provenance and inference receipts. |
| Biological comparisons | Run Member 4's imported analysis against those actual predictions and matching coverage; retain population sizes, sensitivity results and limitations. |
| Explorer rebuild | Use the newly supplied Member 5 validation/build/package scripts. Coverage-only mode remains until actual prediction inputs pass validation. |
| Final evaluation/report | Complete simple-baseline and published m6Anet comparisons, clean Ubuntu prediction check, concise report and runnable explorer. Do not replace missing work with expected results. |

## Report questions to carry through

- Do sequence-aware and read-distribution features improve ranking on held-out
  genes, and which EDA-driven changes actually help?
- Where does performance weaken across motif, coverage and unusual-site groups?
- Which predicted SG-NEx differences are shared or line-associated and remain
  consistent across replicate groups and coverage choices?
- Which differences are plausibly technical or uncertain rather than evidence
  of a biological effect?

Task 1 labels and outputs concern m6A sites. Neither attention weights nor site
scores establish molecule-level states, modification fractions, other chemical
modification types, or causal cell-line effects. The final report must clearly
distinguish observed measurements, model predictions and interpretation.
