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

## 23 October 2026: Task 2 first-run evidence and sequential execution

The assistant attempted the isolated Ubuntu check. Docker's local backend
crashed before any image/package download or Linux execution. A small-context
CPU recipe and prepare-only receipt were retained; no Docker reset, WSL
installation, operating-system change or AWS success claim followed.

Member4's fixed inventory and coverage matrix determined the23-run scope,
>=20-source-read eligibility, exact key/count checks and later50/100-read
sensitivity and equal metadata-group weighting. The assistant added a strict
input auditor, selected-model adapter, resumable sequential runner and targeted
checks. Nine adapter and eight orchestration tests passed. A genuine1,024-site
probe reproduced the unchanged predictor's95 eligible scores within1.49e-8.
The first full run scored135,870sites using10,572,838reads with the original
frozen artifact;1,166,644low-depth sites remain explicitly unscored in QC.
No model fitting, imputation, per-line normalisation or threshold tuning ran.

A separate reporter independently verified hashes, every prediction/QC key
and read-count agreement with Member4, then produced actual aggregate tables,
coverage/score plots and computation scopes. The main assistant inspected the
figures. The first completed run and its resume were checked on real files:
the repeated command reverified and skipped it without inference. Full23-run
execution then started sequentially, with pinned source/data/model identities,
per-run checkpoints and logs. This is not completed biological analysis.

Context checks combined Member1's motif table with fingerprinted data0 cache
and labels. All18central motifs/all288canonical7mers occurred in training;
the15 previously evaluable motifs reflected class-support restrictions, not
three unseen motifs. Sparse positive-label counts were retained as evidence
limits, not calibrated uncertainty or exclusion criteria. One valid first-run
site slightly above the training read-depth maximum was retained. No Task2
assay labels were supplied, so score fractions are not accuracy or measured
modification prevalence. The explorer remains coverage-only until real-score
integration, and reference/coordinate and laboratory-independence limits stay
explicit. These assistant-executed checks are not the user's personal
individual-assessment reflection.

## 23 October continuation: context QC, real-score integration and Linux evidence

The assistant verified the completed23-run batch and frozen model, then added
a predeclared context audit, explicit comparison-population gate and explorer
warnings. It streamed28,670,080saved metadata rows, compared8,780,071observations
at all451,352scoreable keys and found no context conflicts or exclusions.
A separately written saved-table audit independently reproduced all key/support
flags and87population rows. Never-scored keys outside this universe were not
claimed context-validated. Sparse-positive training support remains a warning,
not an exclusion. Ten audit fixtures passed; comparator/explorer fixtures
checked joins, low-read conflicts, missingness, equal group weights and score
precision. These are software/QC checks, not independent assay validation.

Two concrete issues were detected and corrected. The received explorer generated
version-stripping aliases and rounded scores; the integrated path now uses only
the supplied per-run map and preserves float64score precision, with a regression
around the0.7cutoff. Its validator also rejected any occurrence of 'pending' in
model notes, including honest status prose. Tests now distinguish real placeholder
fields from narrative limitations; all28explorer fixtures passed.

The initial3–5minute comparison estimate was too optimistic. An unfinished run
showed poor scaling from large dictionary replacement and repeated full-table
pair filters. The attempt, source and partial outputs were preserved. Exact
dictionary lookups and one-time unit partitions replace those operations without
changing scores, group means, populations or statistics;7targeted fixtures passed
before a fresh output-directory retry. Interrupted final CPU/RSS accounting was
not flushed, so no missing resource figures are invented.

To resolve Linux execution without resetting the laptop, the assistant published
a bounded Ubuntu24.04 CI check using the existing recipe and real ten-site
example. The job passed on the frozen artifact/exact pins; downloaded artifact
hash/CRC, all result hashes, ten keys and numeric parity were independently
checked. Maximum score difference was1.49e-8within3e-6. This is Linux-container
software evidence, not AWS-host verification, retraining or model accuracy.
The earlier Docker-startup failure and all model/negative-experiment evidence
remain preserved. The five-page report and genuine human reflections remain
separate from these assistant-executed analyses.

The completed comparison retry took549.325s; the completed full explorer build
took240.225s. Two reporter versions took63.758/64.767s; the second only repaired
overlapping labels and made zero context exclusions visible. Exact ten-CSV
equality and publication hashes were checked. Independent scientific review
highlighted the Hct116 training-domain confound and overlapping within/cross-line
rank-agreement ranges; the narrative keeps these limits explicit.

The actual explorer passed190input checks and189exact cutoff-fraction checks.
DesktopChrome checked actual-score views, typed gene search, table/chart and
depth/context controls. One WindowsCP1252 JSON label-encoding issue was repaired
by literal-preservingUTF8transcoding;132JSONobjects were checked unchanged,
original bytes archived, and builderUTF8regression added to28passing tests.
MeanPearson/disjoint-band explorer agreement is labelled separately from report
Spearman/cumulative-depth analysis. These software checks do not validate m6A
chemistry or complete public deployment or the five-page report.

## Focused biological interpretation — 23 October

The user's follow-up exposed that the assistant's phrase 'Task2analysiscomplete'
was too broad: computational comparisons were complete, but namedgene/site
interpretation remained. The checkpoint was corrected and the user authorised
the focused next step. Before reading gene outcomes, a fixed tail-case selection
plan specified persistent contrasts, a separate training-line diagnostic, shared
high scores and an inconclusive overlap case. Gene literature did not choose cases.

All63pair tables were checked. A first selection attempt stopped because a
cell-line cache lacked a completed-reporter hash pin; the original failed run/
source were retained. The retry uses annotation from an already pinned pair table,
without changing criteria. Independent implementation reproduced all rankings:
1004persistent pair-site rows/545keys,41shared-high sites,6098inconclusive rows.
HNRNPA1/RAB1B/ACTG1/G3BP2 were selected. A separate original-export reconstruction
checked92case/run rows,80scored/12below20unscored, all group/line averages and12
depth checks. Twelve small software tests passed. Matplotlib cache-permission
warning during tests was nonfatal; actual figures completed and were inspected.

Postselection lookup found data0matching keys/labels1,0,1 for HNRNPA1/RAB1B/ACTG1,
while G3BP2was absent. This did not change ranking. Data0labels do not validate
SG-NEx or prove a false positive at a different sample. Basecaller/platform
confounding, nested thresholds and unverified preparation independence remain.
Two plot versions are retained; version2 only repairs overlapping labels/legend.

Primary studies provide gene functions and prior HNRNPA1/ACTG1 mRNA-m6A evidence,
but no selected exact-site assay correspondence was established. Direct requests
sometimes failed403/429; primary extracts/available publisher PDF supplied the
checked claims. Independent scientific/visual review found no blocking issue.
The assistant prepared case narrative, figure captions, a report paragraph,
full-precision tables and future explorer payload. No new training/inference,
RNAmodification-type discovery, causal mechanism or public UI deployment is claimed.
This is assistant-executed team-project work, not the user's personal AI reflection.

## Prediction/submission readiness clarification — 23 October

The user authorised a final readiness audit and asked whether RONIN was needed.
The assistant re-read the official handout: classmates evaluate on AWS Ubuntu,
but our own RONIN launch/AWS test receipt is not an additional explicit course
deliverable. Earlier wording made the recommended preflight sound compulsory;
current instructions now distinguish that recommendation from official rules.
The hosted Ubuntu check already passed. Actual new-test input/release naming/
upload instructions have not been supplied in this chat, rather than being
known globally unreleased. Task2's20read filter does not automatically apply.

A bounded read-only audit rechecked all seven public release pins, ten example
keys/1887 reads, five unchanged inference sources, requirements and saved Linux
results. A stale 'not executed on Ubuntu' opening in the recipe README was
corrected while preserving the earlier failed laptop attempt. The installation
guide now follows the already tested CPU-wheel-first recipe. Direct-host commands
and an independent inline CSV/hash verification are prepared, not claimed run.
The proposed small CPU-machine size is an allowance for ten sites, not measured
full-test capacity. No training, prediction, dependency install or AWS launch
occurred during this documentation audit. Browser inspection found the RONIN
login screen; the user must complete their NUS authentication themselves.

Only Markdown changes are being published. The commit skips the otherwise
automatically triggered repeat Docker check using GitHub's
[documented skip mechanism](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs).
No model, inference source, dependency pin, workflow or original receipt changes.

## Actual Ubuntu26.04 host — 24 October

The user created the RONIN machine and supplied terminal evidence:Ubuntu26.04,
x86_64, Python3.14.4, Python3.12 absent and Docker absent. The assistant retained
the existing host and prepared Astral's user-local managedPython3.12 route with
a fresh seeded virtual environment, preserving system Python and model package
pins. Actual installation and parity remain unperformed until user output
confirms them. The direct-host verifier now accepts/reports actual24.04 or26.04
and explicitly requires Python3.12; earlier Ubuntu24.04 receipts are unchanged.
This is a documentation adaptation, not a successful26.04 prediction claim.

## User-executed native AWS example — 24 October

The user ran setup and ten-site prediction in their own RONIN terminal. Actual
evidence confirms Ubuntu26.04/x86_64, managed CPython3.12.15, uv0.13.5 and all
five pinned packages; pip check passed. The assistant did not remotely execute
the commands, access SSH keys, query instance metadata, or run another model.
The user supplied all CSV rows and complete manifest text. Local independent
checks matched seven release pins, five source pins, input/readcounts, unique
finite output scores and the reconstructed CSV's SHA to the remote sidecar.
Maximum score difference1.490116119e-8 was below3e-6. Independent audit also
checked the compact evidence. CSV reconstruction is hash-supported; no binary
download or original remote JSON byte formatting is claimed.

User-local Python avoided changing system3.14 or dependency pins. The earlier
hosted24.04 result/laptop Docker failure remain. Resource0.027595s wall/0.054654s
CPU/400.625MiB sampled RSS covers the predictor's measured section, excluding
imports; installation/end-to-end timing and true instantaneous peak unknown.
This is software parity on training-data examples, not unseen accuracy, new-test
submission or training reproduction. The user was asked to Stop the cloud
machine while preserving disks; stopped state remains unconfirmed. Evidence
contains no private host address/key names/contents. Documentation and compact
evidence publication skip redundant Docker CI; no inference/pin/workflow changes.

## Actual-score biological-case interface — 24 October

The assistant implemented four case entry points, literal transcript/position
links, saved 20/50/100-read and 0.5/0.7/0.9 controls, group/line charts and all
23 original run records per case. Scientific review independently checked the
two-group rule, G3BP2's one-group diagnostic, training/literature caveats and
missing-versus-zero handling. It caught a line-object/name lookup bug before
final browser verification. Browser checks found height-triggered redraws closing
evidence disclosures; redraws now follow width changes and retain open sections.
An initial JavaScript strict-mode/destructured-parameter syntax error was fixed
before integration. The actual absent-record schema is explicitly handled;
none of the selected four cases has an absent source record.

The incremental helper validates and copies existing audited data, preserves
all 132 original score JSONs and the frozen four-case payload byte for byte,
independently matches 92 case records to their original scores/readcounts, and
writes completion last into a fresh artifact. Intermediate versions v1–v4 remain
preserved; the current local version is biological_cases_v5. Copied immutable
casebook notes retain their bytes; additional navigation files repair their
relative links and explicitly direct wider analysis to a pinned public commit.

Ten integration/tamper tests and Node route/missing/zero/one-group regressions
passed. Chrome checks exercised all 36 case/depth/cutoff combinations, four
literal-site click/reload links, invalid-position rejection, all92 run rows and
legacy tabs. Phone-size390px checking used viewport emulation, not a physical
device; horizontal scroll regions remained contained. Screenshots and visible-DOM
checks were retained. Browser console reported no warnings/errors in the checked
session. One test initially toggled already-open sections closed; the corrected
test checked open state before acting. Local preview required a loopback server
outside the restricted shell network; no cloud machine was restarted.

No model fitting, prediction, original score rewrite, new significance test,
credential access or public website deployment occurred. Copy/hash timing is
not prediction timing. Public code and compact verification are separate from
the ignored full local197MB artifact. The user previously confirmed RONIN stopped;
no new-test input or submission is implied. Final report/hosting remain pending.

## Public explorer and first report draft — 25 October

The assistant reused the already completed hosting archive dated 24 October
(49,505,191 bytes), rather than repeating scientific computation. Its existing
receipt was directly inspected and its fingerprints checked. A fresh ignored
Sites checkout received all174 public static assets, byte-identical to that
archive. The private local integration receipt was excluded. The native Sites
workflow pushed the exact source, packaged it and deployed a saved version;
public access was then set for the researcher-facing hosting requested in the
continuation. Site identity/version/commit are retained, without credentials.
Source credentials stayed in session memory and hidden stdin, never files/output.
An initial restricted-network source push was interrupted after DNS failure;
the same Site succeeded with network permission. No duplicate Site was created.

Hosted Chrome checks exercised36 case/depth/cutoff combinations,four literal-site
click/reload routes and an actual CSV download; its SHA matches the frozen case
run evidence. An initial short wait missed a cold gene load, then explicit
network-aware waits passed. One combined browser call took unexpectedly long.
Full-page screenshot capture timed out; documented viewport capture succeeded.
No browser console warning/error was observed in the checked session. Scope is
one desktop Chromium browser/observed dark theme, not a new physical/mobile or
cross-browser test. The live tab was retained as a deliverable.

The anonymous HTTP checker first assumed a verbose gene-index schema; inspecting
the actual fields/rows format corrected it without changing data. A default
Python client received403; a named verification client and normal browser worked,
with no cookies/authentication/bypass token. Of15 sampled assets,13 non-HTML files
match exact bytes. Two raw HTML hashes differ because Cloudflare adds one 938-byte
JavaScript-detection script to each. Local comparison isolated that identified
addition and verified every original HTML byte; no hosting security was disabled.
Raw mismatches are retained separately instead of claiming exact served HTML.
All 174 deployment-source assets and original 132 score JSON files remain unchanged.

A separate agent mapped official report requirements to primary saved evidence
and wrote a first scientific draft with three existing figure slots and a small
benchmark table. The main agent reviewed source tables, completed hosted status
and primary bibliography metadata, without another experiment/model search.
Early five-model history is separated from later strict CV; stronger unpromoted
external ranking, exposed data1 and Task2 confounding remain. This is an untypeset
draft for team review, not a five-page/font-verified report, final submission,
personal reflection or invented contribution statement. Other members' AI use
still needs their own confirmation. Two documented project-level AI corrections
remain in the draft. The user confirmed on 25 October that new test input has not
been received and will update later. No RONIN restart/training/prediction occurred.

## Formatted report review PDF — 25 October

After the user resumed, the assistant completed the independent hosting audit
and pushed the reviewed deployment evidence/first Markdown draft. A separate
layout agent then created a PDF with five main-body pages and one references
page. The main agent independently inspected every rendered page. Body text
uses embedded Arial 11, captions 9.2 pt, tables 9.3 pt and references 10 pt. The PDF is a
review draft, not a team approval or course submission; actual teammate AI use
and final wording remain for human confirmation.

Original plots became too small at report width. New report-only figures were
recomposed from the exact original saved OOF/development/reference scores and
summary/case tables. All four pooled curve areas had to match the saved benchmark
summary; final fitted-data0 predictions were never used as validation. Original
figures/data/model/folds stayed unchanged. Figure 2 uses the fixed 33,452-site,
20-read all-line population; Figure 3 retains every original qualifying case
point and distinguishes one-group diagnostics/unscored observations. No new
training, inference, case selection, score filter or significance claim occurred.

The builder checked 28 paragraphs and 49 table cells against extracted PDF text,
source hashes, public hyperlinks, font embedding and page geometry. Six pages
were rendered using bundled Poppler and reviewed by both agents. A bibliography
paragraph split, a cutoff-legend placement and a table-text extraction check
were repaired. Failed layout v1 is preserved locally; reviewed layout v2 is
separate. QA images/font caches stay ignored. Layout-only plotting packages
were reused from an existing compatible environment alongside bundled PDF
libraries; no install or model dependency-pin change. Versions are recorded
separately from model software. Full layout CPU/RSS totals were not measured;
no inference-cost comparison is inferred. The original source Markdown and
its creation-time receipt remain unchanged beside the new layout evidence.
