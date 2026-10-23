# Actual-score context QC integration

The original received coverage-only dashboard and its manifests remain historical
evidence. Build actual scores into a fresh directory using the canonical
`../../sgnex_analysis` handoff. Original prediction CSVs remain complete and retain
their literal input IDs and positions.

Final validation/build now requires the authoritative per-run alias CSV and a
completed context-audit directory. The builder applies only mappings present in
that CSV for that specific run. It does not infer mappings by stripping versions.

From this folder, after the context audit has actually completed:

```powershell
& $py scripts/validate_task2_inputs.py --inputs ../../sgnex_analysis --public public_data --require-complete --aliases ../../sgnex_analysis/outputs/received_member4_20261019/metadata/transcript_aliases_checked.csv --context-qc PATH_TO_COMPLETED_QC --report NEW_REPORT_PATH.json
```

Pass the same table as `--member4-aliases` and the same directory as `--context-qc`
to `build_site_data.py`. Keep the existing sample metadata, support cross-check,
fresh output/report paths, `--predictions ../../sgnex_analysis` and
`--score-status final` arguments. Missing public readcount/annotation files must
be obtained from their documented sources before a real build; these software
changes do not claim that download or build has occurred.

The completed audit contains `complete.json` and `key_context_qc.csv.gz`.
Validation checks the table hash/size, current manifest and alias hashes, every
current prediction hash, the complete run scope and exact scored canonical key
union. Coverage alignment in the builder independently requires precisely the
public union of sites reaching 20 reads in at least one run. Duplicate,
unaccounted or malformed keys fail.

Primary comparisons use annotated human sites passing `all_source_consistent`:
the same uppercase/U-to-T encoded seven-base context across all saved source
observations at that key, including observations below 20 reads. Scored-only
`scored_consistent` is a separately labelled sensitivity analysis. Support with
fewer than 20 positive training labels is a warning, never an exclusion. Sequence
agreement does not establish the exact reference FASTA, event offsets, assay
validity or laboratory independence of metadata groups.

Every score remains available in the gene payload, including conflicting keys.
The site format is `[position, read_counts, scores, context_qc]`. Scores use
round-trip float64 decimals; blank values remain missing. `context_qc` contains
the two consistency flags, the two encoded-context strings, the weak-support
flag and whether all observed contexts have known training support. The frontend
must show these warnings and apply the primary flag to its comparison population.
It must not present a conflicting score as missing or silently remove it from
diagnostic views.

`overview.compare.by_key` uses the primary qualified population and keeps the
existing `20_ge2`, `50_ge2`, `100_ge2` keys. The default rule is `ge2` metadata
groups per line. `scored_consistency_sensitivity` and
`before_context_diagnostic` retain separate denominators using the same key
structure. Per-line `frac_high_by_cutoff` (also `fractions_by_cutoff`) contains
descriptive fractions at 0.5, 0.7 and 0.9. Mean runs within each group, then
weight groups equally. This global explorer panel is the all-seven-line
population; Member 4's separate pairwise populations remain in the scientific
analysis and must not be substituted with these all-line counts.

Focused synthetic checks include explicit-only aliases, collision refusal,
receipt/prediction tamper guards, strict Boolean parsing, exact coverage-union
alignment, equal group weights, threshold fractions, score precision and a full
23-run/two-site final-build fixture that retains a conflict while qualifying the
primary summary. These are software tests, not biological validation or an
actual-score rebuild of the SG-NEx data.

## Actual completion on 23 October

The real build is now complete in `../outputs/real_scores_v1/site/`, preserving
all23runs and451,352scoreable sites. Its public support files are in
`../outputs/public_sources_20261023/`; historical `public_data/` is untouched.
Strict actual validation passed190checks with0warnings/0failures. An independent
aggregate audit matched189cutofffractions exactly and all three common-site
counts33452/11560/5058. Member4's144coverage support counts also match.

The Windows default encoding initially wrote one JSON file as CP1252. All132
generatedJSONs now pass strictUTF8 validation; that one file was transcoded by
preserving its decoded text, numeric literals, IDs and JSON values. Original
bytes and before/after hashes are in `qa/pre_utf8/` and `qa/utf8_check.json`.
The builder now writes explicitUTF8, verified by the full-build fixture.

From the repository root, preview the completed local page:

```powershell
& '../advanced_model/.venv/Scripts/python.exe' -B -m http.server 8765 --bind 127.0.0.1 --directory data_visualisation/outputs/real_scores_v1/site
```

Then open `http://127.0.0.1:8765/` in Chrome; pressCtrl+C in that terminal when
finished. Opening index.html directly cannot supply the required HTTP JSON
requests. DesktopChrome verified typed gene search, gene examples, context and
support warnings, missing/low-read score tables, chart toggle, 20/50/100read and
context-policy controls. Public hosting/responsive deployment QA remain pending.
The explorer's agreement panel is explicitly meanPearson in disjoint read bands,
with summed eligible-run depth for groups and repeated paired-site observations.
The scientific report separately uses per-pair Spearman with cumulative depths.
