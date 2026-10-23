# Focused biological case selection — fixed before inspecting gene outcomes

Scope: saved, context-qualified selected-model outputs in
`outputs/real_analysis_context_v2/` and completed reporter v2/QC receipts.
No model fitting, prediction rerun, identifier rewriting, source exclusions or
new significance test. Original23exports and all pair results stay intact.
Cases concern predicted m6A scores only; reference offsets, assay accuracy,
laboratory independence and technical confounding remain qualified.

## Predeclared examples

1. Robust differential, without Hct116: same transcript/position and cell-line
   pair passes the existing |delta|>=0.2, strictly separated group ranges,
   geometric-read-depth ratio<=2 rule at20,50and100reads, with unchanged nonzero
   direction. Both lines require>=2metadata groups at each depth. Rank descending
   minimum |delta| across all three depths, then descending minimum group count
   across both lines/all depths, then ascending pairA,pairB,transcriptID and numeric
   position. Choose first. Preserve the entire ranked pool and per-pair counts.
2. Same rule/ranking for Hct116-containing pairs, as a training-domain diagnostic.
   This is not a new biological cohort or proof of domain bias.
3. Shared high: same site is in all-seven common panels at all three depths,
   with every line mean>=0.7 at every depth. Rank descending minimum line/depth
   score, then ascending transcriptID/numericposition. Choose first. If and only
   if the entire0.7pool is empty, use the predeclared0.5fallback and label it.
   High line means do not imply every group/run is high or confirmed conservation.
4. Inconclusive differential: at20reads, |delta|>=0.2, depthratio<=2, both lines
   >=2groups, but group ranges are not strictly separated (touching included).
   Rank descending |delta|, descending minimum groupcount, then the same lexical/
   numeric keys. Choose first non-Hct116 pair. Preserve all qualifying pairs,
   including Hct116 rows, in the ranked pool. Group overlap does not prove zero
   biological difference. Report its50/100outcomes, including missingness.

Never relax robust-difference criteria to manufacture a case. An empty stratum
is itself a result. Training-positive-context support is joined and shown as a
warning, never used to suppress or replace a selected case. Valid extreme scores
are retained. Duplicate isoforms/sites across pair rows remain explicit; examples
are not independent discoveries. Literature availability will not change ranking.

## Checks and presentation

- Bind every used saved table to the completed reporter/QC/analysis receipts.
  Recompute pair deltas, strict group separation, coverage ratio and flags;
  preserve full precision. Context agreement and annotation must match QC.
- Record all candidate-pool sizes and ranks; distinguish pair-site rows from
  unique site keys. Tail examples are illustrative, not effect/prevalence estimates.
- Extract all23original run scores for selected canonical keys using only the
  supplied per-run alias map. Save literal source IDs, readcounts, absence and
  below-threshold reasons. Independently reconstruct group and line means at
  all depths and compare to saved tables.
- Show per-group score/depth membership and every original run. Thresholds are
  nested measurements, not three independent replications; eligible membership
  may change. Missing predictions/readcounts never become zero scores.
- Use original transcript-position keys; do not assign CDS/UTR/genomic positions
  or claim exact chemical nucleotides without established reference/offsets.
- Only after cases are frozen, research named gene functions and prior m6A work
  using primary literature. Gene-level literature is not proof of our exact site
  or cell-line mechanism. Keep evidence, interpretation and hypotheses distinct.
- Write code/tests, ranked tables, receipts, resource scope, case figures,
  biological narrative and references into fresh versioned output directories.
  Preserve failures and completed outputs. Publish compact evidence only.
