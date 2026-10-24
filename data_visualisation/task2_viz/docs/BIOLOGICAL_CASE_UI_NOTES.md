# Biological case explorer: scientific wording and acceptance notes

Prepared 24 October 2026 from the frozen public case package, its primary-source
notes and the existing explorer. The implementation status below supersedes the
earlier specification-only status. Suggested prose and acceptance criteria remain
review guidance; this document does not change the frozen case evidence.

## Current implementation and verification status

The four-case frontend is implemented in `site/case_view.js` and `site/case_logic.js`
and connected to `site/app.html`. The current local artifact is
`data_visualisation/outputs/biological_cases_v5/site/`, with a completed
`integration_complete.json`. It preserves the 132 original score-data JSONs and
published case payload byte for byte: 23 runs, seven lines, 17 metadata groups,
451,352 scoreable keys, 2,983,948 run-site scores and four cases/92 original rows.
This receipt establishes validation/copy completion; separate saved Chrome
checks now establish the bounded browser QA below, not public hosting. No new training, inference, downloads or score rebuild occurred.

Scientific source review verified the two-group rule, G3BP2's one-group 50-read
diagnostic, true-zero/missing distinction, all 23 original runs and literal
transcript/position navigation. A line-name lookup defect was fixed. During fresh
browser QA, height-triggered resize redraws closed expanded evidence; the frontend
was changed to redraw on width changes and preserve open sections. Fresh Chrome
checks passed all 36 case/depth/cutoff combinations, four literal-site click/reload
routes, all 92 original run rows, invalid-site rejection and existing tabs. A
390-pixel viewport retained contained horizontal chart/table scrolling with no
page overflow. No console warnings/errors were observed. This is one-browser,
dark-theme viewport emulation, not physical-device/cross-browser/light-mode QA.
Public hosting remains pending. See the separate compact verification package
`data_visualisation/biological_case_ui_results_2026_10_24/`.

The visible chart explanation now states that scores are not modified-molecule
fractions and technical differences can contribute to any pattern. Group ranges
are labelled as ranges, not confidence intervals; training-label and unmatched-site
literature caveats remain accessible. Task2 scoring needs at least 20 reads per
run; primary case comparisons need at least two metadata groups per line and
equal group weights. The gene view can retain a one-group diagnostic without
making it comparable.

Exact incremental integration and local-serving commands are in
[the current explorer README](../README.md#integrate-the-cases-into-a-fresh-local-artifact).
Viewing the existing artifact needs no rebuild. A deliberate reintegration needs
a fresh output directory and another browser check. No command/checklist here
establishes final QA, hosting or scientific site validation.

## Suggested introduction

**Explore four selected patterns**

> These examples show contrasting patterns among saved model scores: a persistent
> difference, a training-line caution, shared high scores and an inconclusive
> difference. They were selected by fixed ranking rules and are not a representative
> sample of all sites. Scores are predictions, not the fraction of modified RNA
> molecules or experimental confirmation of m6A.

Use the four case names below as entry points to the exact transcript and position.
Keep the full gene/site browser, all 23 runs, global summaries and access to the
selection rules and ranked alternatives available.

## Suggested case titles and short narratives

### HNRNPA1 — persistent score contrast

**Exact key:** `ENST00000340913:177`; encoded context `CGGACTG`.

> K562 has a higher mean score than HepG2 at this RNA-processing gene's transcript
> site (0.642 versus 0.078 at 20 reads). The contrast remains at 50 and 100 reads,
> using the same qualifying runs. It is a candidate score difference; technical
> differences between the cell-line samples remain alternative explanations.

At 20 reads: K562 has 3 metadata groups/3 runs and HepG2 2 groups/2 runs. A signed
high-minus-low display must say **K562 minus HepG2: +0.563**. The supplied table's
`delta_score` uses its opposite A/B ordering; do not relabel it without changing
the sign. K562's line mean exceeds 0.5, but not 0.7 or 0.9.

Protein-function context: hnRNPA1 regulates alternative splice-site choice in the
tested in-vitro system ([Mayeda and Krainer, 1992](https://doi.org/10.1016/0092-8674(92)90477-T)).
Prior gene-level m6A evidence: DART-FISH studied HNRNPA1 A1225 in HEK293T cells
([Sheehan et al., 2023](https://doi.org/10.1093/nar/gkad787)). That coordinate was
**not matched** to this literal 177 key. Neither source shows that our score
contrast changes splicing.

### RAB1B — training-line caution

**Exact key:** `ENST00000311481:1947`; encoded context `AGGACAA`.

> Hct116 has a higher mean score than HepG2 at this transcript site (0.586 versus
> 0.035 at 20 reads). Hct116 is the training cell line, and the matching data0 key
> has label 0. This is a cautionary diagnostic rather than independent validation
> or a proven SG-NEx prediction error.

At 20 reads: Hct116 has 2 metadata groups/3 runs and HepG2 2 groups/2 runs. A signed
high-minus-low display must say **Hct116 minus HepG2: +0.551**. The means remain
unchanged at 50/100 reads because the same participating runs qualify. The Hct116
mean exceeds 0.5, but not 0.7 or 0.9.

Protein-function context: Rab1b supports ER-to-Golgi and successive Golgi transport
in reconstituted assays ([Plutner et al., 1991](https://doi.org/10.1083/jcb.115.1.31)).
This is not an m6A assay. No direct RAB1B mRNA-m6A assay was verified in the focused
search; that does not establish that none exists. Our scores show no change in
cellular trafficking.

### ACTG1 — shared high scores

**Exact key:** `ENST00000331925:607`; encoded context `TGGACTC`.

> All seven cell lines have high mean scores at this gamma-actin transcript site
> (0.942–0.959 at 20 reads). The result remains above 0.9 at all three read-depth
> thresholds. This is a shared predicted candidate, not proof that the site is
> methylated in every line or that the whole gene is uniformly modified.

All 23 runs have 248–936 reads; each line has 2–3 metadata groups. All seven line
means exceed each descriptive cutoff, 0.5/0.7/0.9, at each depth. These are repeated
checks on nested observations, not independent replications.

Protein-function context: Actg1-null mouse experiments support gamma-actin's role
in cytoskeletal maintenance, especially auditory stereocilia
([Belyantseva et al., 2009](https://doi.org/10.1073/pnas.0900221106)); this does not
establish a function for our human RNA site. Prior gene-level m6A evidence: SCARPET
detected m6A at a tested ACTG1 mRNA site using HEK293T poly(A) RNA
([Mirza et al., 2024](https://doi.org/10.1261/rna.079776.123)). No sequence,
accession/version or coordinate match to this 607 key has been established.

### G3BP2 — overlapping groups; inconclusive

**Exact key:** `ENST00000359707:2510`; encoded context `AGGACAT`.

> HepG2 has a higher mean than HEYA8 at 20 reads (0.786 versus 0.293), but their
> metadata-group score ranges overlap. At 50 and 100 reads the pair no longer has
> enough qualifying groups. This example shows why a large difference between
> means alone is inconclusive.

At 20 reads: HEYA8 has 3 metadata groups/3 runs; HepG2 2 groups/2 runs. HEYA8's group
range is 0.031–0.724 and HepG2's 0.709–0.862. A signed high-minus-low display must
say **HepG2 minus HEYA8: +0.493**. The HepG2 line mean exceeds 0.5/0.7 but not 0.9;
HEYA8's mean exceeds none. Do not convert these mean classifications into claims
that all contributing groups are above/below the cutoff.

At 50 reads HepG2 still has a score of 0.709145 from **one group**. It may remain
visible as a diagnostic, marked **Not eligible for the comparison: fewer than two
groups**. It must not be used as an eligible pair mean, filled into the missing
HEYA8 result, or joined to a zero on the chart. At 100 reads there is no qualifying
pair either.

Protein-function context: G3BP2 can support stress-granule assembly in the tested
arsenite-stress rescue system ([Yang et al., 2020](https://doi.org/10.1016/j.cell.2020.03.046)).
This study does not establish stress exposure, altered granule behaviour or m6A
at our selected transcript site.

## Labels and explanations shared by all cases

- **Model score:** a continuous, uncalibrated site-level prediction between 0 and
  1. Use neutral continuous colours and a common 0–1 scale. Avoid “methylated”,
  “unmodified”, “confirmed”, “significant”, “true positive” or “false positive”
  as status labels for these SG-NEx cases.
- **Metadata group:** a group identified by sample metadata. Runs are averaged
  within each group; groups then receive equal weight in the line mean. Independent
  laboratory preparations have not been verified. Do not call every run an
  independent replicate, or weight lines by their total run/read counts.
- **Comparison eligibility:** an eligible run meets the selected read threshold;
  each compared line needs at least two eligible metadata groups. Eligibility is
  separate from the score itself. Context agreement and the annotated-human
  population remain required by the primary comparison.
- **Group range:** minimum to maximum of group means. It is not a confidence
  interval, an uncertainty interval or a significance test. Show the individual
  group means so that G3BP2's overlap is visible.
- **Read-depth check:** 20/50/100 reads changes which original runs qualify; it
  does not retrain the model or independently repeat an experiment. Keep the main
  interpretation at the fixed 20-read design and make the selected threshold
  visible. Do not silently change it when opening an example.
- **Descriptive cutoff:** 0.5/0.7/0.9 is applied to the continuous line mean for
  the displayed summary. It is not a calibrated probability, significance level
  or fraction of modified molecules. Compare at full numerical precision; round
  only labels. Line-mean cutoff checks are not group-unanimity checks.
- **Missing states:** distinguish no source observation, below the selected read
  threshold, eligible reads but no prediction, and a scored line with too few
  groups for comparison. A real numeric zero remains a real score. Never apply
  numeric coercion to a null before checking its state.
- **Training-context support:** HNRNPA1/RAB1B/ACTG1/G3BP2 have respectively
  48/41/133/40 positive data0 labels for their encoded contexts. These context-wide
  counts are not labels for the selected SG-NEx site, independent validation,
  calibration or proof of adequate transfer performance. They were not selection
  filters. Keep the global sparse-support/conflict evidence accessible.
- **Training-key diagnostic:** show matching data0 key/label as HNRNPA1 1, RAB1B 0,
  ACTG1 1, G3BP2 absent. “Absent” is not label 0. These checks were performed after
  selection was frozen. Matching literal keys do not prove identical samples,
  historical references or assays.
- **Technical alternatives:** HepG2 basecaller metadata includes albacore and
  Guppy flipflop, while the selected K562/Hct116 comparisons use other Guppy
  versions. Platform/date effects also differ. Stable group separation cannot
  disentangle cell-line biology from these confounded technical differences.
- **Position and prior literature:** retain the literal transcript key. Encoded
  seven-base agreement does not validate exact nucleotide offsets, historical
  reference identity, genomic/CDS/UTR location or correspondence to an orthogonal
  assay. Literature explains gene/protein context; none of the four exact sites
  has verified orthogonal confirmation here.

The SG-NEx and m6Anet primary papers provide context for coverage/sample structure
and signal/basecaller compatibility, not instructions to change our model:
[Chen et al., 2025](https://doi.org/10.1038/s41592-025-02623-4),
[Hendra et al., 2022](https://doi.org/10.1038/s41592-022-01666-1).

## Acceptance criteria for the case panel

1. Each entry opens its exact gene/transcript/position in both click and reload/
   link navigation; a gene's default transcript or deepest site is insufficient.
   A user can see which exact case is active and return to ordinary exploration.
2. Every case retains all 23 original run rows. Across the supplied four cases,
   there are 92 rows: 80 scored and 12 below-20-read unscored observations; all 12
   unscored observations are G3BP2. No missing score is imputed. At higher thresholds,
   retain original scored observations in diagnostic evidence while distinguishing
   exclusion from the current comparison.
3. At 20 reads the displayed line means, group/run counts and ranges reproduce
   the supplied payload. Group-first equal weighting is preserved. Table fallback
   or accessible labels expose scores, readcounts and group membership.
4. The case panel requires at least two groups per line even if the general gene
   browser displays a one-group diagnostic mean. The payload's pair availability
   and displayed group counts agree. G3BP2 reads **Not eligible** at 50/100, never
   0, “no difference”, or a valid comparison of a single HepG2 group.
5. Cutoff controls say which line mean is above which cutoff; unchanged numerical
   scores remain visible. Signed differences identify the subtraction direction.
   ACTG1 shows all seven lines rather than an arbitrary pair.
6. HNRNPA1/RAB1B/ACTG1 stable-depth panels explicitly state that nested checks reuse
   observations. No confidence interval, p-value, false-discovery result or causal
   claim is invented. G3BP2 group overlap is visible rather than hidden by its
   large mean difference.
7. Context, support, training-key and main technical caveats are reachable beside
   the case. Case summaries retain a short score/confirmation caveat without
   overwhelming the first view; detailed methods and literature can be expanded.
8. Sources open primary papers with the unmatched-site caveat. Selection rules and
   ranked alternatives remain accessible, and four selected extremes are never
   presented as prevalence or four independent discoveries.
9. Case-data failure is visible and does not produce fabricated summaries or make
   the existing gene/global explorer unavailable. Implementation fingerprints,
   file sizes and internal receipt fields belong in provenance/methods, not the
   main biological reading flow.

## Review provenance

Read-only payload hash check: `explorer_cases.json` SHA256
`1821dc0f9aeacabb36815e9f20c2f011e690147901bed653f0f4d3f98374796b`, matching
`publication_manifest.json`. Source package:
`sgnex_analysis/biological_case_results_2026_10_23/`.

The payload uses `groups`, `original_runs`, `line_scores` and `comparison_checks`.
The historical field names `biological_replicate`/`n_replicates` must be translated
to **metadata group** in the reading interface. Pair checks and line diagnostics
have different eligibility scopes; `line_scores` deliberately includes some
one-group diagnostic means. The existing generic gene map permits these, so its
displayed line score alone is insufficient to assert case-comparison eligibility.

Scientific review inspected the frontend and frozen evidence independently. The
main agent implemented the interface and ran browser checks; a separate agent
audited the final copied artifact. No model, original score or cloud job changed.
