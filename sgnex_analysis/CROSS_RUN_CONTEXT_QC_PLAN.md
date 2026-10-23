# Cross-run context QC: fixed analysis rules

Declared on 23 October 2026, before running the new context audit or comparing
cell-line scores. This analysis uses the completed 23-run exports; it performs
no training, inference, calibration, reference correction or score replacement.

## Question and scope

For a matching transcript/position key, do the saved observations describe the
same seven-base sequence? The complete analysis universe is Member 4's 451,352
coverage-union keys: every key scored at >=20 reads in at least one selected
run. Stream all 28,670,080 saved source-site metadata rows, including low-depth
observations, and check contexts at every union key. Report rows outside that
union as never-scored observations outside this comparison audit; make no
cross-run consistency claim for their keys.

Use only the explicit alias rows for the specified run. Preserve raw transcript
IDs and positions in every original score export. Do not strip versions,
change position offsets, pick a majority context, or correct a sequence.
Compare sequences after the model's existing uppercase and U-to-T encoding.
Retain literal contexts as well, so encoding-equivalent differences can be
distinguished from genuine encoded conflicts. Invalid/ambiguous contexts and
alias collisions must be explicit findings or failures, never silent joins.

## Primary population and sensitivity

The primary context-qualified key must have one unambiguous encoded seven-base
context across **all saved source observations at that union key**, including
observations below 20 reads. This conservative rule is fixed before inspecting
comparative score outcomes. A separate sensitivity population requires context
agreement only among >=20-read scored observations. Preserve every conflicted
observation with raw and aliased key, run, cell line, metadata group, read count,
context, eligibility and score when available. Do not silently discard scores.

The gate is an analysis-layer table covering every union key. Original CSVs,
the canonical 23-run manifest, completed prediction receipts and model remain
unchanged. Validate complete original export coverage before applying a gate.
An unqualified comparison, if generated, is explicitly diagnostic. Quantify
before/after populations for each depth, each of the 21 pairs and all seven
lines; keep different populations separate.

Member 4's fixed design remains: annotated human keys, >=20 reads (50 and 100
as sensitivities), >=2 metadata groups per cell line, arithmetic mean of eligible
runs within each group followed by equal group weights. Continuous scores are
primary; 0.5/0.7/0.9 are descriptive cutoffs. Valid unusual values remain.
Training-context positive-label counts are warnings/support summaries, not
filters or calibrated uncertainties. Missing/unscored observations never become
zero. Agreeing contexts do not establish historical FASTA identity, chemical
coordinates, independent laboratory preparations, accuracy or stoichiometry.

## Evidence and verification

Write to fresh output folders. Preserve failures. Bind the audit to input and
source hashes, model/receipt identities, all prediction and metadata exports,
coverage, annotations, aliases and training support. Verify score/metadata/
coverage keys and counts exactly. Save per-run counts, complete key QC, full
conflict observations, population consequences, summary and completion receipt.
Record wall/process CPU and sampled memory with their actual measurement scope.
Write completion last. Software fixtures must cover encoding equivalence,
explicit-only aliases, alias collisions, low-depth-only conflicts, missing keys,
unscored handling, coverage/group eligibility and before/after denominators.

Next, apply the explicit context gate to Member 4's comparator; then reconcile
the same population and warnings in Member 5's genuine-score explorer. Biological
interpretation must follow observed results and preserve conflicting evidence.
