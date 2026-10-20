# Interactive visualisation — current handover

Start with [the imported Task 2 explorer](task2_viz/README.md). Member 5's
19 October source package now supplies the frontend, downloader, validator,
data builder, packaging/rebuild checks, source manifests and Member 4 metadata.
The team is proceeding with **23 processed runs, 17 biological replicate
groups and seven cell lines** on Elgin's laptop.

**Current data mode: coverage only. No real m6A scores are supplied.**
The explorer shows measured read coverage, missingness, gene/transcript
annotation and replicate support. Score comparisons stay empty until actual
predictions from the selected model are validated and built into the view.

## Completed integration, 20 October 2026

- The received package's 159 checksum entries matched. Original files remain
  preserved outside the active repository; the prior README is backed up locally.
- Source, small metadata, documentation and manifests are prepared for Git.
  Full generated view data and large alias tables remain local and ignored.
- Eighteen small synthetic regression checks passed. Narrow fixes prevent
  destructive export/rebuild deletion, reject numerically duplicate keys and
  invalid positions, enforce prediction validation during a score build, and
  handle undefined correlations without writing invalid JSON.
- The downloader uses the pinned 23-run scope. Final score builds require
  complete eligible-site/run delivery; exploratory gaps remain explicit.
- No training, full-run inference, downloads, full data rebuild, browser test
  or hosting was performed during this integration.

See [integration notes](task2_viz/INTEGRATION_NOTES.md) and the import receipt
for source provenance and limitations. Member 5's earlier macOS rebuild report
is received evidence, not a fresh local/Ubuntu execution.

## Next use

The delivered coverage data are already retained locally. To preview later,
from repository root run:

```text
python -m http.server 8000 --directory data_visualisation/task2_viz/site
```

Then open `http://localhost:8000` and stop with `Ctrl+C`. A public clone needs
the source download/build steps in the imported README because generated data
are excluded from Git. These preview instructions have not started a server.

Before final score views: choose the saved model; produce a three-column CSV
for each run; complete `sgnex_analysis/manifest.csv` and model provenance;
validate; build into a new output directory; review replicate aggregation,
coverage eligibility and common-site populations. Full-precision source CSVs,
not rounded display values, support scientific analysis.

## Archived interface

`prototype/` is the earlier simulated-score version and is retained only as
historical interface evidence. It is not the recommended entry point and its
modification patterns cannot be reported as scientific results.
