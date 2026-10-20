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
