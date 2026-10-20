# Task 2 prediction hand-off (data contract)

**Status (19 Oct 2026):** this follows the team's nine-column manifest, the
format in Member 4's package. The validator and site builder implement it.

## What to send

Send one folder, zipped and shared by link:

```
task2_inputs/
├── manifest.csv
├── MODEL_INFO.md
└── predictions/
    ├── SGNex_A549_directRNA_replicate5_run1.csv
    └── ... one file per run, at the path named in manifest.csv
```

Never put AWS keys, `.pem` files or other credentials in the folder.

### `manifest.csv` (one row per run)

```text
run_id,cell_line,biological_replicate,sequencing_run,prediction_file,coverage_file,min_reads,reference_version,model_version
```

| column | meaning |
|---|---|
| `run_id` | SG-NEx run name, e.g. `SGNex_HepG2_directRNA_replicate5_run2` |
| `cell_line`, `biological_replicate`, `sequencing_run` | must agree with the run name (checked) |
| `prediction_file` | path to that run's CSV, relative to the folder |
| `coverage_file` | the read-count source used (public `data.readcount` or a documented derived file) |
| `min_reads` | minimum reads a site needed to be scored (proposed: 20) |
| `reference_version` | reference used for the input JSON |
| `model_version` | one value for every row; a selected model, not `PENDING…` |

`n_sites_scored` may be added as an optional extra column. The validator then
checks it against each file's row count.

### Each prediction file

- Header, exactly: `transcript_id,transcript_position,score`
- One row per scored site. Keep the transcript IDs and positions exactly as they appear in that run's `data.json`.
  - MCF7 replicate 3 run 1 keeps its versioned IDs; the pipeline joins them through an explicit, checked alias table.
- `score` is a full-precision probability in [0, 1]. Each site appears once.
- Keep one file per run; don't merge runs or replicates.

### `MODEL_INFO.md`

- the selected model and its checksum
- input and preprocessing versions
- coordinate convention
- training/evaluation exposure
- the exact prediction command
- the coverage rule
- limitations

## What the validator checks

```bash
python scripts/validate_task2_inputs.py --inputs task2_inputs --public public_data
```

**FAIL (blocks the build):**
- missing columns
- run columns that disagree with the run name
- mixed or pending `model_version`
- a missing file
- a wrong header
- duplicate sites
- scores outside 0–1
- sites not present in that run's public read counts (wrong run, changed IDs or shifted positions)

**WARN (needs reading):**
- scored sites below `min_reads`
- sites with enough reads but no score (shown on the page as "missing prediction")
- runs not delivered
- MODEL_INFO.md still listing pending fields

Problems go back to whoever made the files; nothing is patched silently.

For a final delivery, add `--require-complete`. Missing eligible predictions,
missing/extra runs against the fixed 23-run inventory, unavailable readcounts,
inconsistent coverage rules/reference and missing or pending model information
then FAIL. `build_site_data.py --score-status final` invokes this strict mode
automatically. Exploratory mode keeps the documented warnings visible.

## Build

```bash
python scripts/build_site_data.py --public public_data \
    --sample-metadata team_inputs/member4_2026-10-19/sample_manifest.csv \
    --predictions task2_inputs --score-status exploratory --out site/data
python scripts/package_site.py
```

Cell-line scores are the mean over a line's replicates. Each replicate's score
is the mean of its runs with enough reads, so repeat runs of one sample don't
get extra weight. Comparisons use only sites measured in every line, under
either a ≥1 or a ≥2 replicates-per-line rule.
