# Task 2 interpretation draft

Assistant-authored report material for team review; not a submitted final report
or the user's individual AI reflection. Every numerical statement below comes
from the saved aggregate CSVs in this folder.

The same frozen model was applied to 23 processed SG-NEx runs from seven cell
lines and 17 metadata groups. Cross-run matching used only explicit per-run
aliases and the model's uppercase/U-to-T encoding. All 451,352 scoreable keys
had consistent, unambiguous central-A contexts across 8,780,071 saved source
observations, including low-read records. Thus context qualification excluded
zero sites. This check does not establish exact historical FASTA or event-offset
identity; the 19,890,009 observations outside the scoreable union were not
cross-run context-compared.

Requiring at least two metadata groups per line left 33,452 sites common to all
seven lines at 20 reads, falling to 11,560 and 5,058 at 50 and 100. On the same
33,452-site panel, mean scores ranged from 0.0705 (MCF7) to 0.0946 (Hct116), and
3.76–5.20% of sites met or exceeded 0.5. Only 15–31 sites per line met or exceeded 0.9.
These are descriptive prediction summaries. Hct116 is also the training cell
line, so elevated scores may reflect training-domain affinity, biological or
technical differences; this design cannot separate them. Exact overlap with
historical training source runs remains unverified.

At 20 reads, median Spearman agreement was 0.7904 across six same-group run
pairs, 0.7934 across 28 different-group same-line run pairs, and 0.7815 across
219 cross-line run pairs. Their ranges overlap substantially. Shared site and
sequence structure may explain much of this agreement; it does not demonstrate
sharply separated cell-line biology or independent assay accuracy. Correlations
rise at stricter depth thresholds, but those thresholds select different site
populations, so this is not a controlled within-site depth experiment.

Across all 21 pair-specific populations at 20 reads, median paired score
differences range from -0.00287 (H9 minus Hct116) to +0.00614 (Hct116 minus
MCF7). Broad shifts are small despite local candidate flags. For example,
2,331 Hct116–HepG2 sites pass the exploratory large/separated/depth-balanced
screen among 120,195 shared sites. Preserve the full pair results and valid
extremes; no significance or false-discovery control was performed.

Training-context support remains a major limitation: 22,219/33,452 common sites
(66.4%) have fewer than 20 positive data0 labels for their seven-base context,
including 4,290 with none. These sites were retained with warnings. Together
with confounded technical metadata, uncertain independent laboratory replication
and absent compatible external assay labels, this limits chemical, prevalence
and causal claims. The defensible outcome is a reproducible resource for
examining candidate scores and prioritising later validation.

For the five-page main report, prioritise the matched-site score/CDF figure,
one compact agreement summary and the explicit coverage/context denominators.
The full 21-pair figure supports completeness but is too dense to carry the
main narrative at small print size. Essential limitations must remain in the
graded main body; the ungraded appendix is supporting evidence only.
