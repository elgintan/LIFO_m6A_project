# Files received from Member 4

- Source: `Member4_Analysis_Package.zip` (shared with Member 5 on 19 Oct 2026)
- Zip SHA-256: `5b5b3bf3734bf195704046aaf10adfd9967dabf7f7d5a567e15e2378964cadf6`
- Copied unchanged from the zip: manifest.csv, MODEL_INFO.md, findings.md,
  metadata/sample_manifest.csv, metadata/samples.tsv (official SG-NEx sample sheet,
  downloaded by Member 4 on 15 Oct 2026), metadata/transcript_aliases_checked.csv,
  results/replicate_coverage_support.csv, results/cell_line_inventory.csv
- The package contains no full-run SG-NEx predictions; its manifest marks the model
  as PENDING_TEAM_SELECTION.

How these files are used:

- `sample_manifest.csv` supplies run metadata (replicate group, protocol, kit, flowcell,
  basecaller, sequencing date, spike-ins) for the run table.
- `replicate_coverage_support.csv` is used only as an independent cross-check of the
  pipeline's own replicate-support counts (reports/crosscheck_member4.json).
- `transcript_aliases_checked.csv` is compared with the pipeline's own alias table
  (reports/transcript_aliases.csv).
- `manifest.csv` is the agreed nine-column template for the real prediction hand-off.
