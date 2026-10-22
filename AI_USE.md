# AI use and verification evidence

This is working evidence for the required disclosure, not a claim that human
review is complete. The team should record its actual tool/model details,
prompts/output use and verification when assembling the final report.

- The October 7 neural implementation, training, evaluations, predictions and
  documentation were assistant-executed. The original work retains checkpoints,
  logs, source hashes and independent metric/output/authenticity checks.
- Member 1's supplied package reports AI-assisted EDA/code/figures/text and
  explains its own checks and detected extraction error. These remain
  attributed to that package; the current setup did not rerun raw-signal EDA.
- The October 15 setup used AI to inspect packages, copy reviewed files,
  generate project guidance and audit historical fold composition. Copied
  sources were hash-checked, including 43 EDA manifest entries and the original
  training-core source hashes. No new model was trained in repository setup.
- Initial setup code incorrectly assumed the fold CSV had a `fold` column
  and labels. It stopped with KeyError before creating audit outputs. Inspection
  showed `fold_id` and no label column. The code was corrected to join the
  actual manifest and use labels from the EDA summaries, then completed with
  exact unique coverage and documented counts. This is an actual detected/fixed
  assumption, not an invented reflection example.
- Earlier guidance risked treating the five existing folds as a default. The
  user requested genuinely EDA-driven choices. The methodology compared designs
  and audited actual class/motif/coverage support. Elgin subsequently accepted
  the five-group methodology. The minimum contract standardises outer splits,
  fitting boundaries, scores and dataset roles while retaining model freedom.
  Rotating inner roles and specific EDA comparisons are recommendations, not
  identical compulsory model-development tasks. Samuel's acknowledgement and
  new candidate training remain pending.
- The visual prototype explicitly uses simulated modification scores.
  Inspection confirmed that these cannot become evidence of model performance
  or biological differences. Its full upstream data provenance remains pending.
- Public-copy review detected a personal workspace directory literal in the
  archived report generator. Only that public copy was made portable; original
  files and training-core hashes were preserved and the receipt discloses the
  change. Git attributes preserve exact received/archive bytes across platforms.

On 15 October, AI helped draft the methodology and Samuel's starter context,
then updated them following Elgin's acceptance. Public visibility was checked
using anonymous GitHub metadata. AI implemented a common prediction validator/
scorer with 14 small correctness and failure-case tests, plus optional default
inner roles. Tests cover PR/AP distinction, joins, fold consistency, score/label
validation and mean-fold scoring. These are software checks, not new candidate
performance results. No new training or inference has run in this update.

No AI should fill missing experiments or comparisons with expected results.
Each contributor checks their section and Elgin reviews the integrated report.

## Consolidation — 20 October 2026

Elgin authorised one-laptop continuation, unpacking Samuel's merged ZIP,
integrating the new Member 4/5 code and updating the public repository. Elgin
selected the 23 available processed runs as the working Task 2 scope. Earlier
status text and simulated-score prototype descriptions are historical; current
progress is recorded in INTEGRATION_STATUS.md and each integration receipt.

AI helped inspect source, preserve original package hashes, integrate code and
portable paths, and run small software checks. Samuel's saved model reproduced
the ten-site example with exact numerical scores; the common evaluator exactly
reproduced his provided data1 metrics. No complete model training, full SG-NEx
inference, full explorer rebuild or new biological analysis ran in this update.
Member 4/5 checks and their limits are recorded in their integration notes;
passing temporary synthetic fixtures is not validation of biological claims.

Actual issues detected during consolidation included a Unix-only memory import
in the received trainer, prediction output paths that could overwrite inputs
or artifacts, destructive/reassuring empty-directory behaviours in visualisation
packaging/comparison code, and missing numeric-key/constant-correlation guards.
Narrow fixes and regression checks are disclosed; saved model weights and
preprocessing tables remain unchanged. Missing inputs, reference assumptions,
unselected model/cutoff and unrun full computations remain explicitly pending.

The final human report must still supply the actual AI-use table requested by
the handout, including prompts/output use, verification and corrections. These
working records are evidence for that disclosure, not the student's personal
reflection or a replacement for human review.

## Read-depth investigation — 20 October 2026

Elgin authorised a data0-only diagnostic before another model change. AI
implemented standalone sampling/inference and reporting code outside frozen
production modules. The plan specified matched sites, depths20/32/50/100,
three key-seeded nested draws, both-input and read-branch-only arms, and two
numerical controls before outcomes. Saved fold/model/source/normalisation
boundaries were checked; no fitting, calibration or data1 access occurred.

An initial synthetic recovery test correctly rejected inconsistent toy gene
metadata, exposing an overly long Windows atomic-write name in its error
recording. The toy fixture and temporary-name construction were fixed before
real full-cohort execution. Sixteen checks then passed; a500-site trial and
report preceded the completed24,533-site/130-condition run. Independent
receipt arithmetic reproduced all main reporter metric means, output hashes
were checked and three figures were visually reviewed. Tiny rounding and
single-class trial metrics were disclosed rather than treated as improvements.

The actual result supports all-read inference; reducing reads did not improve
the tested pipeline. Full predictions/logs/checkpoints remain local; only code,
aggregate metrics, a concise report and figures are shared. The result does
not demonstrate a new full-CV improvement or establish biological mechanisms.

## Signal-case review — 20 October 2026

AI implemented a standalone data0-only descriptive review using verified saved
OOF predictions and raw cached reads. Selection and matching rules were
written before outcomes: top positive-count motifs, median-score FNs,
same-fold/different-gene sequence and coverage matches, and Member1 examples.
The received multi-dataset EDA table was filtered to data0; no data1 signal or
label file, fitting, inference, threshold tuning or relabelling was used.

A read-only second-agent review identified round-trip score parsing, missing-
match schemas and stale completion status on interruption as issues to fix.
Ten synthetic checks then passed. An initial decimal-tie fixture incorrectly
assumed .1/.3 had equal binary floating-point distances; exact-representable
.125/.375 corrected that fixture, with its failed log preserved. Actual
data0 tables and eight case panels plus the aggregate figure were checked.
Limited exact-context support and comparator reuse are disclosed. No causal
biology, independent significance or performance improvement is claimed.

Human authors should choose the strongest few figures for the final five-page
report and verify interpretations. A larger training bag cap is a proposed
single-mechanism experiment, not completed training or a guaranteed gain.

## Larger training-read experiment — 20 October 2026

The user authorised cap32->128 after the diagnostic review. AI added a
standalone wrapper calling the unchanged frozen trainer, plus an immutable
experiment design and a saved-evidence reporter. The wrapper records its own
and the plan's hashes inside fitting signatures and refuses duplicate writers.
Read-only review checked that only the cap changes and that smoke/timing
artifacts cannot become full-CV starting weights. Six real synthetic fitting/
recovery checks and14 reporting checks passed, followed by actual small data0
fits and full-sized one-epoch timing trials. A default temporary-folder
permission failure in the integrator's report-test run was fixed with local
temporary/cache directories; the failed log is retained and training continued.

Full cap128 five-fold training started around17:08SGT. Its comparison, and any
performance improvement, remain pending. No data1 tuning or final all-data0
fit is part of this experiment. Logs, RNG/optimiser checkpoints, exact commands
and measured resources are retained. The earlier statement that the hypothesis
had not been trained describes the state before this newly authorised run.

The local post-training report helper initially assumed an absent PID meant
training had stopped. The original execution session and newer checkpoint
timestamps showed that Windows tool invocations expose isolated process
lists. A later timestamp timeout also stopped the helper while training
subsequently advanced. It now waits for authoritative completion/failure
status without inferring failure from PID visibility or inactivity; both
failed attempts are retained. The immutable training wrapper was left
unchanged, and its PID-based duplicate guard is explicitly limited to a shared
process namespace. Confirm actual cessation before resuming a training job.

AI also independently verified existing logistic-regression OOF scores using
the common data0 scorer:121838 exact keys and all five historical fold metrics
agree. This audited saved results rather than replaying historical training.
Missing historical fold artifacts/source fingerprints and baseline pipeline
integration are disclosed. No m6Anet installation, scoring or download occurred.

The user subsequently requested an immediate pause. Training and waiting
helper sessions were interrupted; both returned exit1. Five retained last
checkpoints loaded successfully with finite weights, optimiser/RNG states and
matching histories; completed-fold hashes and all frozen source hashes agree.
Two folds are complete and third-fold inner epoch3 is saved. Original artifacts
remain in place; a117-file ZIP was verified against per-file hashes. Stale
running statuses were marked paused and lock files preserved under renamed
pause filenames. Two backup-receipt bookkeeping mistakes were fixed without
changing model files; failed logs and both ZIP attempts were retained. No
training, inference or automatic report was restarted during preservation.

## 21 October 2026: authorised checkpoint resume

The user's explicit "continue" authorised resuming the paused experiment.
The assistant checked saved source/input/settings/environment signatures,
checkpoint hashes, finite weights, optimiser/RNG states and histories before
launch. Two completed folds were reused; the new console log confirms third-fold
inner training continued at epoch4. Frozen core sources, wrapper and experiment
plan were not edited. New timestamped logs preserve the original console log.
The same PowerShell job runs the saved-evidence reporter only after successful
training; the older separate waiting helper remains stopped.

The original interrupted fold2 inner exit receipt had not been flushed. Its
actual epoch3 checkpoint resource snapshot was recovered in a separate record,
explicitly marked as a lower bound omitting unmeasured work after that epoch.
The reporter now preserves this provenance and counts that snapshot once,
separately from resumed invocation measurements, without adding cumulative
checkpoint totals again. All15 report tests passed on the integrator's rerun
in15.648s. Full five-fold metrics and scientific review are still pending.

The resumed training subsequently finished at 10:03 SGT with exit0; the queued
report also exited0. All121,838data0 sites and five folds are included. Cap128
mean S is0.7187146070 versus cap32's0.7176418289, with all five paired S
changes positive. Precision, recall, F1 and accuracy at the unvalidated0.5
reporting cutoff were slightly worse. The assistant checked report/plot hashes
and viewed both figures; aggregate report, tables, resource limits and plots
are retained in `model_elgin/read_cap_results/`. No additional fit or inference
was launched to check completion, and no final superiority or data1/SG-NEx
result is inferred from these data0 development results.

The user then requested the shortfall investigation and recommendations for
further changes. A new saved-score tool rescored all three candidates and
existing motif, coverage and training-defined unusual-signal groups using
data0 only. It fits no model, calibrator or threshold and runs no inference.
Fourteen synthetic contract tests passed on the integrator's rerun in5.002s.
The tests exposed two guard/display issues before final publication: a stale
input flag column could shadow the checked flag table, and undefined plot
values could appear as zero. Both were fixed and covered by regression tests.
The initial source/results ZIP and failed test log remain local; the final
analysis was rerun, with unchanged scientific scores, in45.477s measured work
(51.927s command elapsed). No training code or weights changed.

The assistant and a read-only reviewer checked input/source/output hashes,
independently recomputed target subgroup metrics/error overlaps, and viewed
all three diagnostic figures. Cap128 has modest high-depth/unusual-group
ranking gains without improved high-depth recall at0.5. Samuel has stronger
precision and descriptive score reliability, while cap128 leads the shared
mean-fold score. The recommended training-side threshold study and a possible
isolated positive-loss-weight3-to1 experiment are explicitly pending. Neither
is recorded as an improvement already achieved. Public results contain
aggregate tables/plots and receipts; site predictions/checkpoints stay local.

## 21 October 2026: completed training-side threshold study

The user authorised proceeding. The assistant fixed the design before inner
inference, then implemented exact grouped-score maximum-F1 selection with
higher-cutoff ties. Fourteen synthetic tests passed on the integrator's run
in0.136s, including160 independent exact brute-force cases. Each trusted inner
best checkpoint was verified against saved sources, normalisation, split and
selected epoch; its all-read predictions reproduced the selected history.
Cutoffs used only the appropriate inner labels and were applied to matching
excluded-outer refit scores. No weights, training recipe, OOF scores or data1
inputs changed; there was no new neural training or calibration fitting.

The command exited0 in41.862s, with27.480s measured post-preflight work and
71.031s process CPU. The policy reduced false positives by204 and true
positives by78; pooled F1 declined slightly while mean-fold F1 barely rose.
The assistant retained both summaries and the worse high-depth result.
The five-cutoff median0.510309 is explicitly an unevaluated final-model
proposal; it was not presented as the global cutoff behind the outer results.
The working reporting rule remains0.5. Inner prediction CSVs, full selection
curves, checkpoint receipts and logs remain local; only aggregate results,
figures, source/design and compact hash provenance are published.

## 21 October 2026: authorised positive-loss-weight comparison underway

The user authorised proceeding with one bounded cap128 experiment, changing
positive loss weight3 to1 while preserving architecture, features, all sites,
the exact five data0 gene folds and fresh inner-selection/refit procedure.
The assistant wrote a separately fingerprinted wrapper/design and reporter,
without editing the frozen original core, then ran actual local checks.
Nine training tests passed in9.088s and12report tests in21.143s. Tests verify
exact weight3 delegation, interrupted weight1 recovery, source/split guards,
incomplete-evidence refusal and preservation of negative outcomes.

Earlier integrator test attempts failed on Windows file permissions: one
atomic replacement and one restricted sandbox temporary directory. Those logs
remain local. A fresh workspace temporary directory passed the full suite;
no assertions or frozen model code were changed to make the checks pass.
The real-data software check used100whole genes/3,328sites and exited0 in
31.432s. Separate fresh full-size one-epoch timing fits exited0 in97.214s.
These limited fits are software/timing evidence and are never CV warm starts.

Full five-fold training launched at15:44SGT, with original per-epoch checkpoint,
optimizer/RNG and resource logging. One local job queues the reporter only
after full success and pins its source hash. No full candidate result is
available at this snapshot. No data1/data2/SG-NEx access, calibration, new
cutoff selection or final all-data0 fitting is included. Final nomination and
required benchmark/application/report work remain pending.

## 22 October 2026: completed loss-weight results review

The five-fold run and queued comparison had already finished successfully
at17:19SGT on21October, before the user later asked to stop. The assistant
confirmed the original session's exit0 and checked20saved last/best
checkpoints plus20history/completion files. A timestamped local pause receipt
preserves their hashes. The pause did not interrupt a fit and no recovery fit
was needed when the user returned on22October.

The assistant reviewed the generated tables and both figures, with separate
read-only scientific and saved-evidence checks. Weight1 mean-fold S0.7183812884
is slightly below weight3's0.7187146070; its pooled S and three individual
folds improve. Weight1 also raises precision but lowers recall/F1 at0.5.
The predeclared mean-fold criterion was retained rather than switching to
the more favourable pooled score. Retain weight3 as the leading neural
candidate; no significance or universal-superiority claim is made.

This review changes no model weights, checkpoint, source recipe, threshold
or prediction. No training, model inference or data1/SG-NEx access was run.
The negative ablation remains in the report progression, with aggregate
tables/plots, provenance and commands published separately from local site
predictions and checkpoints. Required benchmark, final artifact, Task2 and
report/explorer/Ubuntu work remain pending.

## 22 October 2026: required reference benchmarks and checks

The assistant implemented a fixed 18-feature logistic-regression replay and a
deterministic launcher of unmodified published m6Anet, executed actual data0
comparisons and retained models, scores, logs, hashes and measured resources.
The shared scorer was unchanged. Independent review checked gene separation,
training-only scalers, learned coefficients and exact prediction coverage.
Published pretraining provenance is explicitly different from our held-out
fits; no data1 result was used to choose a winner in this work.

Two setup assumptions required correction. A broad assistant recommendation
that Bioconda could not be used on Windows overlooked the noarch m6Anet
package with available Windows dependencies. Actual Conda solving and native
execution established the feasible route, preserving the handout's Python3.8
and Conda requirement. Separately, requesting `cpuonly` did not by itself
prevent the solver selecting a legacy CUDA Torch build. Inspecting the dry-run
package plan detected this; an explicit CPU build was pinned before installing.
The original plans and corrections remain in local setup logs.

Source inspection also found that the official output-flush condition can omit
the final batch and that its parent seed does not seed fresh Windows pool
workers. A documented large CLI flush interval and module-level child seeding
preserve vendor algorithms while addressing those issues. Two actual two-batch
pilots matched official CSV hashes. The computation batch size was amended
before any labelled scoring, with both old and new pilot evidence retained.
These checks support the measured benchmark, not an unseen-data guarantee.

## 22 October 2026: original-model selection and final release

The assistant initially described the separate external neural trial as a
clear recommended winner after checking its higher ranking score. The user
pointed out that its own review classified replacement as inconclusive.
Rereading that review confirmed unresolved high-coverage recall and motif
tradeoffs. The assistant corrected the promotion claim, retained the contrary
score evidence and followed the user's instruction to finalise the original
cap128/positive-weight3 pipeline. A valid numerical audit did not itself
justify promotion. The external trial remains separate.

The assistant added an isolated final-fit delegate, a public fixed-recipe
training interface and an artifact packager without changing frozen model or
CV code. Nine delegate tests, three existing final/resume guard tests and two
public-fit/promotion tests passed. A real full-input check of the public
interface passed without fitting a second real-data model. The actual fresh
all-data0 final fit completed18epochs in679.823seconds, with optimizer/RNG
checkpoints, logs and measured resources retained. The packaged model and
real ten-site example passed independent byte/source checks.

Supplied-data application uses that one saved artifact. Validation continues
to refer to the earlier held-out-gene OOF predictions; fitting all data0 does
not create a new validation result. Data1 remains previously exposed transfer
evidence, and data2's fractional labels are not silently binarised. Clean
Ubuntu execution and new unlabelled-test submission remain unverified.

Actual inference and shared data1 scoring completed by23October00:21SGT.
All121,838/90,810/1,323 data0/data1/data2 predictions use the same model hash;
independent full-CSV checks matched all supplied keys and valid score ranges.
Data1 neural S0.604865501 is slightly above LightGBM0.602321536; LightGBM
has better PR/precision/specificity/accuracy and neural better ROC/recall/F1.
Those outcomes are retained without choosing a new threshold or another model.

A separate reporter independently rescored both stored OOF and data1 files
with the unchanged common evaluator and reproduced all saved metrics. It
generated aggregate tables, actual training-loss and data1 ROC/PR figures,
resource scopes and exact commands. The main assistant inspected both figures
and checked all final CSV keys, package receipts and unchanged historical CV
hashes. The report is evidence for the final scientific write-up, not the
finished five-page report or completed Task2 analysis.
