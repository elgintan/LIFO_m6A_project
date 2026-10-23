# Primary sources and limits

Cases were frozen before literature research. Source claims below are paraphrases,
not instructions to change the model or scoring rules. No selected exact-site
correspondence to an orthogonal assay has been established.

| Primary source | Claim supported | Application boundary |
|---|---|---|
| Mayeda and Krainer1992, *Regulation of alternative pre-mRNA splicing by hnRNP A1 and splicing factor SF2*. [DOI](https://doi.org/10.1016/0092-8674(92)90477-T), [primary abstract](https://pubmed.ncbi.nlm.nih.gov/1531115/) | In-vitro experiments show hnRNPA1/SF2 influence alternative splice-site choice. | Gene/protein-function context, not proof that our HNRNPA1 RNA-site score changes splicing. |
| Sheehan etal2023, *In situ visualization of m6A sites in cellular mRNAs*. [DOI](https://doi.org/10.1093/nar/gkad787), [primary full-text record](https://pmc.ncbi.nlm.nih.gov/articles/PMC10639046/) | DART-FISH studied HNRNPA1 mRNA methylation at reported A1225 in HEK293T cells. | Not matched to our ENST00000340913:177. Do not import that experiment's stoichiometry, cell proportions or stress result into SG-NEx. |
| Mirza etal2024, *SCARPET: site-specific quantification of methylated and nonmethylated adenosines reveals m6A stoichiometry*. [DOI](https://doi.org/10.1261/rna.079776.123), [publisher PDF](https://rnajournal.cshlp.org/content/30/3/308.full.pdf) | Results subsection on mRNA/SuppFig2A–B reports biochemical m6A detection at a tested ACTG1 mRNA site; this section uses HEK293T poly(A) RNA. | Gene-level prior, not validation of ENST00000331925:607 or all seven lines. |
| Plutner etal1991, *Rab1b regulates vesicular transport between the endoplasmic reticulum and successive Golgi compartments*. [DOI](https://doi.org/10.1083/jcb.115.1.31) | Reconstituted transport assays support Rab1b function in ER/cis/medial Golgi trafficking. | Protein function is not a methylation assay. No direct RAB1B mRNA-m6A assay was verified in this focused search; this is not proof none exists. |
| Belyantseva etal2009, *Gamma-actin is required for cytoskeletal maintenance but not development*. [DOI](https://doi.org/10.1073/pnas.0900221106) | Actg1-null mouse experiments support cytoskeletal maintenance, particularly auditory stereocilia. | Cross-system function context only; no functional consequence for our human RNA position follows. |
| Yang etal2020, *G3BP1 Is a Tunable Switch that Triggers Phase Separation to Assemble Stress Granules*. [DOI](https://doi.org/10.1016/j.cell.2020.03.046), [primary full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC7448383/) | G3BP1/2 knockout and rescue experiments show G3BP2 can support arsenite-induced stress-granule assembly in the tested system. | The selected G3BP2 transcript score is inconclusive; neither stress exposure nor altered granule function was established in our lines. |
| Chen etal2025, original SG-NEx study. [DOI](https://doi.org/10.1038/s41592-025-02623-4) | Direct-RNA coverage and sample/technical structure require measured-population denominators. | Paper processing descriptions do not independently identify every historical input JSON/reference/offset. |
| Hendra etal2022, original m6Anet study. [DOI](https://doi.org/10.1038/s41592-022-01666-1) | Site/read targets differ; chemistry/basecalling/signal-reference compatibility matter. | Their validated read-level stoichiometry procedure is not our site score or fraction above a site cutoff. |

Official identity checks for RAB1B/ACTG1: [NCBI81876](https://www.ncbi.nlm.nih.gov/gene/81876)
and [NCBI71](https://www.ncbi.nlm.nih.gov/gene/71). Current database mappings do
not validate historical coordinates; inherited annotation and the independently
checked matching data0gene IDs remain the sources for this case analysis.

Relevant primary abstracts/results/full-text extracts were checked. Some direct
publisher/NCBI requests returned403/429/browser checks; equivalent primary search
extracts and the available publisher PDF were used. The SCARPET ACTG1 statement
was checked in the publisher PDF. No review, search-result speculation, protein
association alone or unsourced pathway story was used as exact-site validation.
