# Shared project context

## Direction and ownership

Elgin and Samuel independently develop one candidate each. Neural networks
and enhanced LightGBM are provisional directions. Elgin integrates the final
report. Member 1 supplies EDA directly to Elgin; Member 4 owns SG-NEx analysis;
Member 5 owns visualisation. Candidate evaluation is a shared responsibility,
with Elgin coordinating consolidation. Everyone contributes to writing,
model development and implementation.

The handout defines requirements; scientific questions define our direction.
Course references inform ideas and checks rather than prescribe a model or
conclusion. Our narrative is exploration -> justified method development ->
measured comparison -> supported SG-NEx interpretation and visualisation.

## Inputs and targets

Each JSON site has a transcript ID, position, seven-base sequence and variable
number of nine-feature reads: dwell, event SD and mean current at minus-one,
central and plus-one positions. These are event summaries, not raw waveforms.
All supplied candidate sites have a central DRACH motif. IDs are joining keys,
not default predictive features. Site labels come from m6ACE-seq; individual
read labels are unavailable. A site score is not a modified-molecule fraction,
and attention weights are not verified read modification probabilities.

Data0 has 121,838 sites/5,475 positives and gene IDs. Data1 has 90,810 sites/
6,593 positives, substantial data0 overlap, incomplete gene mapping and prior
evaluation exposure. Data2 has 1,323 rows over repeated templates and seven
fractional-label groups of unconfirmed experimental meaning. Do not silently
pool, relabel, or treat those rows as ordinary independent binary examples.

## Actual starting evidence

The archived Elgin network was trained/tuned on data0 with five shared gene
folds, then refitted on all data0 and frozen before its production data1
evaluation. Mean development ROC/PR was 0.93301027/0.50388135; data1 ROC/PR
was 0.82785418/0.38137868, mean 0.60461643. LightGBM's teammate-reported rounded
mean was approximately 0.590, with no raw baseline scores supplied locally.
The neural model had higher recall/F1 at 0.5, while LightGBM had higher
precision/specificity/accuracy. These are historical pipeline comparisons,
not universal algorithm rankings or a blind independent final test.

The user reports an intermediate rank in the middle of the pack. Exact
leaderboard scores were not supplied. Existing weights learned all data0:
fresh partition evaluations must not warm-start from those weights.

Member 1's received numerical EDA is completed; her follow-up protocols are
proposals. Her files include historical role instructions that predate the
two-independent-model plan; this document states the current arrangement.
The explorer has metadata for 23 runs/17 biological replicates/seven cell
lines, but every modification score is explicitly simulated. Its source
pipeline and required sample scope still need verification/completion.

## How EDA affects this project

Sequence-conditioned effects, sparse motifs, coverage changes, unusual
distributions, dataset overlap and repeated-template labels must influence
the next protocol. The concrete [evaluation proposal v1](model_evaluation/EVALUATION_PROTOCOL.md)
now recommends retaining the audited five gene groups, with inner stopping and
fresh four-group refits, because of their overall support, training fraction
and assessment coverage. It is not yet agreed or executed. Sparse contexts
still need honest diagnostics; a new split cannot create extra positive sites.
Choose quality rules for technical reasons, not to hide poor predictions.
See DATA_METHODOLOGY.md for decisions and planned comparisons.

For Task 2, account for biological replicates, coverage, RNA abundance,
missingness and technical differences. Missing sites are not negative sites;
reads are not independent biological replicates. Report predicted differences
unless independent validation supports stronger claims. Public code does not
establish calibrated probabilities, stoichiometry or causal cell-line effects.

## Reference guides

- [m6Anet](https://doi.org/10.1038/s41592-022-01666-1), [documentation](https://m6anet.readthedocs.io/)
- [xPore](https://doi.org/10.1038/s41587-021-00949-w)
- [SG-NEx](https://doi.org/10.1038/s41592-025-02623-4)
- [m6ACE-seq](https://doi.org/10.1038/s41467-019-13561-z)
- [Zhong et al. benchmark](https://pmc.ncbi.nlm.nih.gov/articles/PMC10076423/)
- [Attention MIL](https://proceedings.mlr.press/v80/ilse18a.html)

Keep actual results, failed experiments and limitations. A shared findings-sheet
process is unnecessary: each owner supplies a short report draft, essential
evidence and code. Elgin can use one AI editor for integration; owners verify
their sections and Elgin checks the final report against supporting files.
