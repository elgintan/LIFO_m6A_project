# SG-NEx analysis — Member 4

## Purpose and current status

Use the selected, frozen model to investigate predicted m6A patterns across the required SG-NEx direct-RNA samples. The scientific questions, sample scope and analysis rules should follow the handout and the available evidence.

The received visualisation prototype describes 23 runs, 17 biological replicates and seven cell lines. Its sample metadata, coverage and annotation are declared to come from real public sources; their upstream derivation still needs reproducing. **All supplied modification scores are simulated.** They cannot support cell-line findings or model-performance claims. No new biological analysis or real Task 2 prediction was performed during this repository setup.

Elgin and Samuel will develop independent candidates using one agreed evaluation methodology. Their neural-network and LightGBM directions are provisional. Final Task 2 comparisons should use the same selected model version across samples.

## First checks

- Confirm which samples the handout requires and distinguish cell line, biological replicate and sequencing run.
- Obtain public-source/download records, read-count files, annotation processing and the visualisation's missing build/validation scripts.
- Verify reference versions and transcript identifiers before joining datasets. The prototype reports removing transcript-version suffixes in one MCF7 run; review the supporting evidence rather than stripping versions indiscriminately.
- Agree eligible-site coverage, replicate aggregation and missing-data handling before interpreting comparisons.

## Draft prediction handoff — agree before implementation

Use one folder containing:

```text
manifest.csv
MODEL_INFO.md
predictions/
    <run_id>.csv
```

Each prediction file retains these exact columns:

```csv
transcript_id,transcript_position,score
```

Use unique transcript-position keys, documented position coordinates, finite scores between 0 and 1, and full numerical precision. The three-column format can stay common to both candidates and the final pipeline.

Proposed `manifest.csv` fields, pending agreement with Members 2, 3 and 5:

```text
run_id,cell_line,biological_replicate,sequencing_run,prediction_file,coverage_file,min_reads,reference_version,model_version
```

`coverage_file` identifies the matching public-source read-count file or a documented derived file. Join it by run, transcript and position; do not infer coverage from the score or from another sample. Use portable paths/public source identifiers, not private download links or credentials. A source manifest should retain download/source information and checksums.

`MODEL_INFO.md` should identify the saved model and its checksum, input/preprocessing versions, training/evaluation context, prediction command, coverage rule and limitations. Final outputs should identify one selected model consistently. Dataset0/1/2 development CSVs are separate from these run-level outputs.

## Interpretation checks

- Compare adequately covered, observed sites; a missing site is not an unmodified site.
- Preserve individual runs, but use biological replicates as biological repeats. Document how repeated runs of one replicate are combined so they do not receive unintended extra weight.
- Check whether differences could reflect coverage, RNA abundance, reference mismatches or technical/batch effects.
- State the comparison population. All-cell-line common sites and pairwise common sites answer different questions.
- Describe scores as predictions. They do not establish individual-read labels, modification stoichiometry or other chemical modification types.
- Keep full-precision results for analysis; the visualisation's packed display scores are not the analysis source.

## Member handover

Upload a short `findings.md` with the question, methods, observed results, interpretation and limitations; sample metadata; supporting tables/figures; and the code plus exact commands used. Identify the model and input versions. Mark unfinished work clearly and retain conflicting evidence. The report coordinator will integrate this section with model evaluation and visualisation; no separate findings sheet is required.
