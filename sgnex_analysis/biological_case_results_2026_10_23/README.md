# Focused m6A case analysis — 23 October 2026

The saved scores now support four named, reproducibly selected biological cases.
This is completed **descriptive biological interpretation**, not experimental
confirmation of differential RNA methylation. The full comparison remains in
[the Task2 results](../task2_results_2026_10_23/README.md).

## What was selected and why

The [selection plan](../BIOLOGICAL_CASE_SELECTION_PLAN.md) was fixed before reading
gene outcomes or literature. All63pair/depth tables were checked. Persistent
contrasts pass the original difference>=0.2, non-overlapping group ranges and
depthratio<=2 screen at20/50/100reads with unchanged direction. Cases rank by
minimum absolute difference, then group count and fixed identifier tie-breaks.
Hct116-containing contrasts are a separate training-domain diagnostic.

There were1004persistent pair-site rows representing545unique transcript/position
keys (539non-Hct116pair rows,465Hct116pair rows). There were41sites with every
line mean>=0.7 at every depth; no0.5fallback was used.6098pair-site rows had a
large20read contrast but overlapping/touching group ranges. These pools contain
correlated sites/isoforms/pairs; they are not independent discoveries or prevalence
estimates. All ranked pools, including valid extremes, are retained.

| Case / literal key | Actual20read result | Interpretation |
|---|---|---|
| **HNRNPA1**, ENST00000340913:177, CGGACTG | K5620.641884 versus HepG20.078402; difference0.563482. K5623groups/3runs, HepG22groups/2runs; reads275–384 versus390–445. | A persistent predicted-score contrast at a transcript of an RNA-processing gene. It remains at50/100reads using the same qualifying runs. K562 exceeds0.5 but not0.7/0.9: continuous score separation is more informative than a single working cutoff. |
| **RAB1B**, ENST00000311481:1947, AGGACAA | Hct1160.586144 versus HepG20.035133; difference0.551011. Hct1162groups/3runs, HepG22groups/2runs; reads135–267 versus159–179. | Persistent predicted contrast involving the training cell line and an early secretory-trafficking gene. Hct116 exceeds0.5 but not0.7/0.9. The matching data0 key has label0, making this an important cautionary diagnostic. |
| **ACTG1**, ENST00000331925:607, TGGACTC | All seven line means0.941538–0.958513. All23runs have248–936reads,2–3groups per line. | Shared high predicted signal at a gamma-actin transcript, retained across all three depths and all0.5/0.7/0.9cutoffs. This is a shared predicted candidate, not proof of universal conserved methylation. |
| **G3BP2**, ENST00000359707:2510, AGGACAT | HepG20.785731 versus HEYA80.292908. HEYA8group range0.031039–0.724455 overlaps HepG20.709145–0.862317. | A mean difference alone would be misleading: group scores overlap and the pair fails>=2groups per line at50/100reads. It is retained as an inconclusive example at a stress-granule-associated gene. |

The transcript positions above are unchanged input keys. We have not established
their exact chemical nucleotide, genomic/CDS/UTR location or historical reference
offset. Never describe a whole gene as uniformly modified based on one site.

## Biological context and direct prior evidence

HNRNPA1 encodes a regulator of alternative pre-mRNA splicing, supported by
[Mayeda and Krainer1992](https://doi.org/10.1016/0092-8674(92)90477-T).
Independent DART-FISH research detected methylation at an HNRNPA1 mRNA site,
reported as A1225 in HEK293T cells
([Sheehan etal2023](https://doi.org/10.1093/nar/gkad787)). That coordinate has
not been matched to our literal177key. Our result suggests a candidate difference
worth testing, not a demonstrated change in splicing or validation of this site.

ACTG1 provides a shared-high contrast to HNRNPA1. Independent SCARPET experiments
detected m6A at a tested ACTG1 mRNA site
([Mirza etal2024](https://doi.org/10.1261/rna.079776.123)). This is useful
gene-level prior evidence; no sequence/accession/coordinate match to our607key
was established, and that work did not test our seven SG-NEx lines.

Rab1b's ER–Golgi transport function is experimentally supported
([Plutner etal1991](https://doi.org/10.1083/jcb.115.1.31)). G3BP2 can support
stress-granule assembly in the tested arsenite-stress system
([Yang etal2020](https://doi.org/10.1016/j.cell.2020.03.046)). These protein
functions contextualize the transcripts. Our scores establish neither altered
trafficking nor stress-granule behaviour. No exact-site orthogonal assay was
verified for any selected case. No pathway enrichment or causal mechanism is claimed.

## Evidence that limits the interpretation

- All four contexts have40–133positive data0labels. This was **not** a selection
  filter. The global sparse-support warnings and all ranked alternatives remain.
- HNRNPA1/RAB1B/ACTG1 have matching literal data0keys with labels1/0/1; G3BP2's
  key is absent. This lookup happened after cases were frozen and did not change
  ranking. Matching keys do not establish identical samples/reference/assays.
  Labels from data0 are not SG-NEx ground truth: RAB1B is not automatically a
  proven SG-NEx false positive, nor are label1cases independent validation.
- The HepG2 runs use albacore/guppy-flipflop metadata, whereas selected K562 and
  Hct116 comparisons use other Guppy versions; platforms/dates also differ.
  Repeated group separation does not remove this cell-line/technical confounding.
- Nested depth sensitivities reuse observations. The stable HNRNPA1 and RAB1B
  pair means here are unchanged because their participating runs all exceed100reads.
  They are not three independent replications. Metadata groups are not verified
  independent laboratory preparations.
- A score is uncalibrated and is not the proportion of modified molecules. Local
  contrasts have no differential-methylation significance or false-discovery control.

## Verification and files

Twelve synthetic software checks passed. An independent implementation reproduced
all rankings/selected keys from63tables/2238466pair-site rows. A separate extraction
verified all23original prediction hashes and reconstructed every selected group/
line mean:92case/run rows,80scored,12below20unscored,0absent in these examples.
Original identifiers are included where a prediction exists; scores are never
imputed for low-read observations. Full precision is retained in the CSVs.

Two figure pairs show run/group patterns and nested-depth sensitivity. Figure
version2 repairs layout only; numerical case/training tables match version1.
Receipts are copied exactly as selection_receipt/evidence_receipt/report_receipt;
they reference ignored local sources, not a publicly bundled full SG-NEx dataset.
`publication_manifest.json` pins the public files. Separate command resource scopes
are in resources.json. The failed first selection attempt and original figure
version remain local. No new model training, inference or RONIN job occurred.

Read [the report paragraph](REPORT_PARAGRAPH.md), [figure captions](FIGURE_CAPTIONS.md), [primary-source notes](LITERATURE.md)
and [the explorer integration specification](EXPLORER_INTEGRATION.md). The small
`explorer_cases.json` is ready for integration; a new case-entry panel is **not
yet implemented or deployed**. The existing full explorer already contains these
scores and can be searched by gene, transcript and site.
