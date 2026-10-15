# Interactive visualisation — Member 5

## Current status

The received **SG-NEx m6A Explorer** is retained in `prototype/` as a starting interface. Its gene explorer, coverage views, cell-line comparisons and data explanations can be developed further.

**Every modification score in this prototype is simulated.** The supplied metadata identifies `placeholder-sim-v0` and `simulated: true`. Score distributions, high-score overlaps and score-agreement figures are therefore demonstrations, not project results. Keep their warning labels until real predictions are incorporated and checked.

The package declares that sample metadata, read counts and Ensembl 91 annotations come from real SG-NEx public files. Inspection confirmed that its 128 gene shards parse, index references resolve and read/score vectors match its 23 runs. Those checks establish internal consistency; upstream downloads, annotations and derivation have not been independently reproduced. The package describes 23 runs, 17 biological replicates and seven cell lines. The required final sample scope still needs checking against the handout.

The received package does **not** include the preprocessing, validation and packaging scripts named inside the page. Obtain these and the public-source/download manifest from Member 5 before claiming a reproducible data build. No live application test, hosting or real SG-NEx prediction has been completed as part of this repository setup.

## Preview locally

The page fetches JSON files, so opening `index.html` directly from disk may fail. From the repository root, with Python installed, run:

```bash
python -m http.server 8000 --directory data_visualisation/prototype
```

Then open `http://localhost:8000` in a browser. Stop the server with `Ctrl+C`. This command is provided for the user; repository preparation has not started a server.

The page uses D3 7.9.0 from cdnjs and fonts from Google Fonts, requiring network access. This prototype is plain HTML/JavaScript, with no supplied package-manager setup.

## Connecting the selected model

Elgin and Samuel are developing independent candidate models. Their neural-network and LightGBM directions are tentative. The selected, frozen model should supply all final Task 2 predictions using the same documented pipeline.

A draft shared handoff is described in [`../sgnex_analysis/README.md`](../sgnex_analysis/README.md). It consists of a run manifest, model information and one three-column prediction CSV per run. Agree the schema with the model and SG-NEx owners before implementing the data builder. Existing dataset0/1/2 CSVs do not substitute for SG-NEx run predictions.

Keep full-precision prediction CSVs as the analysis source. The prototype packs scores to hundredths for display; do not use those rounded values for scientific calculations. Join coverage from the matching run's documented read-count source. Keep no reads, insufficient coverage and a low score distinct.

The current cell-line view averages eligible runs. This is a placeholder rule: repeated runs of one biological replicate must not unintentionally count as additional biological replicates. Agree replicate-level aggregation and the set of comparable sites with Member 4. A score is not the fraction of molecules carrying m6A.

## Member handover

Upload a short `findings.md` explaining the researcher questions, implemented views, current status and limitations; application/build code with run instructions; and selected screenshots or other supporting evidence. Clearly distinguish simulation, real predictions and verified biological findings. Record the exact model/data versions used. No separate findings register is required.
