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
