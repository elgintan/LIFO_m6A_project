# SG-NEx m6A Explorer (Task 2 visualisation)

**23 October continuation:** all23 selected-model score files now exist, cross-run
context QC found no conflicts across451,352scoreable keys, and strict validation
against freshly fetched public counts passed190checks with0warnings/0failures.
The actual-score rebuild completed:451,352sites/23runs,132JSONfiles,197MB;
Member4's144coverage-support counts match. All189cutofffractions match the
scientific tables exactly. DesktopChrome checked gene changes, context/support
warnings, missingness, chart/table toggle and comparison depth/context controls.
Full local site: `../outputs/real_scores_v1/site/`; public hosting is pending.
Read [current context integration and commands](CONTEXT_QC_INTEGRATION.md).
The19October coverage-only data and received pending-model manifest below are
historical evidence; use the canonical `../../sgnex_analysis` handoff for new builds.

Integrated into LIFO on 20 October 2026. The received source package and its
historical evidence are preserved. See [integration notes](INTEGRATION_NOTES.md)
for narrow validation/packaging fixes and the tests actually run locally.
That20October statement is historical; the23October actual-score rebuild/browser
checks above supersede it. Separate model prediction passed hosted Ubuntu.

**Working scope: the 23 published m6Anet-processed direct-RNA runs.**
This imports a coverage-only explorer, not new model predictions. The original
delivered `site/data/` is retained locally and ignored by Git. A public clone
contains source and manifests; download/build the public inputs to obtain the
full view. Large alias tables and incoming predictions also remain local.

An interactive page where researchers explore candidate m6A sites across the
23 SG-NEx direct RNA runs that have m6Anet-processed data. For each gene it
shows, run by run:

- which candidate sites were measured, and with how many reads
- how many biological replicates support each site
- once predictions exist, the model's score for each site

> **Status (19 Oct 2026): real data only, no m6A scores yet.** The simulated
> prototype has been retired. Runs, replicate groups, sequencing metadata, read
> counts and gene annotation are real. Score views stay empty until the team's
> selected model has been run on all 23 runs; Member 4's manifest marks the
> model as `PENDING_TEAM_SELECTION`.

## What is in this folder

| Path | What it is |
|---|---|
| `scripts/fetch_public_data.py` | Downloads the 23 SG-NEx read-count files and the Ensembl 91 transcript table (about 0.7 GB, no AWS account needed). Checks sizes and records SHA-256. Standard library only. |
| `scripts/validate_task2_inputs.py` | Checks a prediction hand-off (team nine-column manifest) against the public read counts. Refuses a manifest whose model is still pending. |
| `scripts/build_site_data.py` | Builds the JSON files the page loads. Without `--predictions` it builds the coverage-only version. Writes the alias table and the cross-check against Member 4. |
| `scripts/package_site.py` | Wraps `site/app.html` into `site/index.html`. |
| `scripts/verify_rebuild.py` | Confirms that a rebuild reproduces the delivered `site/data` and reports exactly. |
| `scripts/task2lib.py` | Shared readers for runs, read counts, annotation, sample metadata and manifests. |
| `site/` | The page: `app.html` is the source, `index.html` is built, and `data/` holds 132 generated JSON files. |
| `team_inputs/member4_2026-10-19/` | Files received from Member 4 (see `PROVENANCE.md`). |
| `reports/` | `transcript_aliases.csv`, `crosscheck_member4.json`, and the validation report for Member 4's manifest. |
| `public_data/` | `download_manifest.csv` (sizes and SHA-256 of the public files) and `runs_discovered.csv`. The downloads themselves are not included; `fetch_public_data.py` recreates them. |
| `docs/data_contract.md` | The prediction hand-off format. |
| `docs/ai_use_log.md` | AI use and the errors caught, for the report. |
| `CHECKSUMS.sha256` | SHA-256 of every file in this package. |

## Setup

You need Python 3.12 with `numpy` and `pandas`. Run every command from this
folder. They work as written in macOS/Linux terminals and in Windows
PowerShell; on Windows, use `python` or `py` where these say `python`.

```bash
python -m venv .venv
```

Activate it (`source .venv/bin/activate` on macOS/Linux, `.venv\Scripts\Activate.ps1` on Windows), then install:

```bash
python -m pip install -r requirements.txt
```

## View the explorer

```bash
python -m http.server 8000 --directory site
```

Open http://localhost:8000. Opening `index.html` straight from disk won't work,
because browsers block the data files from loading that way.

## Rebuild and verify the data

1. Download the public inputs (about 0.7 GB). The downloader checks live
   availability but only fetches the pinned 23-run inventory, failing if a
   required run disappears. Extra folders cannot silently expand our scope.
   It skips files that are already complete.
   ```bash
   python scripts/fetch_public_data.py --out public_data
   ```
2. Use a new build directory, preserving the delivered files. From this folder:
   ```bash
   python -c "from pathlib import Path; import shutil; p=Path('../outputs/rebuild_coverage/site'); p.mkdir(parents=True, exist_ok=True); shutil.copy2('site/app.html',p/'app.html')"
   ```
3. Rebuild. This takes about a minute.
   ```bash
   python scripts/build_site_data.py --public public_data --sample-metadata team_inputs/member4_2026-10-19/sample_manifest.csv --member4-support team_inputs/member4_2026-10-19/replicate_coverage_support.csv --member4-aliases team_inputs/member4_2026-10-19/transcript_aliases_checked.csv --out ../outputs/rebuild_coverage/site/data --reports ../outputs/rebuild_coverage/reports
   ```
4. Re-package the page.
   ```bash
   python scripts/package_site.py --site ../outputs/rebuild_coverage/site
   ```
5. Compare the rebuild with the delivered copy.
   ```bash
   python scripts/verify_rebuild.py --reference site/data --rebuilt ../outputs/rebuild_coverage/site/data --reference-reports reports --rebuilt-reports ../outputs/rebuild_coverage/reports
   ```

Expected output:

- step 1: `Done: 0.70 GB in 24 files`, with the same SHA-256 values as `public_data/download_manifest.csv`
- step 3: `Member 4 replicate-support cross-check: 144 values, 0 mismatches`
- step 5: `PASS: the rebuild reproduces the reference exactly (apart from build timestamps).`

**Member 5 reported a clean-copy rebuild on 19 Oct 2026** (macOS, Python 3.12.14,
numpy 2.5.3, pandas 3.0.6). That report concerns the original received source;
it is not a new local or Ubuntu verification. The command above uses the large
received alias table, retained on Elgin's laptop and excluded from Git. Restore
it from the original handover to reproduce this exact cross-check. A public
clone can omit `--member4-aliases` and still build the coverage explorer, but
its cross-check metadata differs from the full delivery. The comparator reports
such differences honestly. Without the delivered data, first build the view;
do not claim a match to an unavailable reference. Choose a new output directory
for another rebuild; existing generated genes are never recursively deleted.

Check Member 4's manifest with the validator:

```bash
python scripts/validate_task2_inputs.py --inputs team_inputs/member4_2026-10-19 --public public_data --report reports/validation_member4_2026-10-19.json
```

The received19October check ended with `3 PASS, 1 WARN, 24 FAIL`: its model was
pending and scores had not yet been supplied. That historical result does not
describe the completed23October exports or current strict-validation result.

## Adding the team's predictions

1. Use the canonical team template at `../../sgnex_analysis/manifest.csv` and
   its model-info template. Put the completed hand-off at `task2_inputs/`.
   The format is in `docs/data_contract.md`; replace pending fields with actual
   saved-model and prediction provenance. The received Member 4 snapshot is historical.
2. Run `validate_task2_inputs.py --inputs task2_inputs`. Fix every FAIL at the source, and read every WARN.
3. Rebuild into a new output directory using the step 3 command plus
   `--predictions task2_inputs --score-status exploratory`, then package that
   output's site. The builder now runs the validator itself before reading
   predictions. Use `--score-status final` only after selecting the model.
   Final mode automatically adds `--require-complete`: missing eligible sites,
   missing runs/readcounts, mismatched scope or incomplete model provenance
   block the build. For a standalone final check, run:
   `python scripts/validate_task2_inputs.py --inputs task2_inputs --public public_data --require-complete`.
   Exploratory mode keeps incomplete-coverage warnings visible. A display
   mode flag is not evidence that predictions exist or are valid.

The page code doesn't change. It switches from the read-count view to the
score view and labels exploratory scores as such.

## Checks against Member 4's independent analysis

- **Replicate support:** all 144 counts match Member 4's recount (per line and for the 7-line intersection, at 20/50/100 reads, for both populations).
- **Transcript aliases:** both tables map the same 46,297 versioned IDs in MCF7 replicate 3 run 1 to identical transcripts.
  - This pipeline verifies 43,704 against the full Ensembl 91 table.
  - Member 4 verified 13,589, because they checked only against transcripts with well-covered sites.

## Remaining modelling/analysis decisions

- **Scope:** the team is proceeding with the 23 processed runs.
- **Minimum reads to score:** proposed 20.
- **Replicate rule for cell-line comparisons:** ≥1 or ≥2 replicates per line. The page supports both.
- **Which model to run on all 23 runs.**
- **Technical batch effects:** replicates differ in device and basecaller (e.g. A549, HepG2).
