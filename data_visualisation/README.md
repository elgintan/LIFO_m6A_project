# Interactive visualisation — current handover

**24 October 2026: actual selected-model scores and the four biological case panels are integrated locally. Desktop and 390-pixel phone-size Chrome checks passed; public hosting remains pending.** Start with [the current explorer guide](task2_viz/README.md).

The current local artifact is `outputs/biological_cases_v5/site/`. It preserves the completed full explorer: 23 runs, 17 metadata groups, seven cell lines, 451,352 scoreable transcript/position keys and 2,983,948 scored run-site observations. The integration receipt confirms that the original 132 score-data JSON files and published four-case payload are unchanged. This adds case navigation and linked evidence without repeating training, inference, downloads or score building.

## Completed and pending

- **Completed:** all 23 selected-model predictions; cross-run context QC; strict validation and the full actual-score explorer build; independent aggregate checks; the four-case interface and scientific source review.
- **Current artifact:** HNRNPA1 persistent contrast, RAB1B training-line caution, ACTG1 shared high scores and G3BP2 inconclusive overlapping groups. Each opens its exact transcript/site and retains all 23 original run observations.
- **Pending:** publish and verify a hosted site, then assemble the final report. Local Chrome and phone-size viewport checks do not establish cross-browser or physical-device testing.

Task2 scores require at least **20 reads per run**; 50/100-read controls are nested sensitivity checks. Primary comparisons require at least **two metadata groups per line**, mean runs within each group then equal group weights, annotated human sites and agreement among all saved encoded contexts. A one-group diagnostic can remain visible without becoming comparable. Missing/unscored/ineligible values remain distinct from zero. Scores are not modified-molecule fractions or experimentally confirmed m6A.

## View the current local artifact

From the main repository root, using the existing laptop Python in PowerShell:

```powershell
& '../advanced_model/.venv/Scripts/python.exe' -B -m http.server 8765 --bind 127.0.0.1 --directory data_visualisation/outputs/biological_cases_v5/site
```

Open `http://127.0.0.1:8765/`. Stop the server with `Ctrl+C` when finished. If that port is already in use, retain the existing server or choose another port and its matching URL. Opening `index.html` directly cannot load the required JSON files.

Generated artifacts are local and ignored by Git. A public clone contains frontend source and the small published case evidence, not this full 197 MB score-data artifact. [Exact fresh-integration commands](task2_viz/README.md#integrate-the-cases-into-a-fresh-local-artifact) are documented; viewing the completed artifact needs no rebuild.

## Historical received material

Member 5's 19 October package supplied a coverage-only explorer and a pending-model manifest. The 20 October import verified its 159 checksum entries and preserved the received source/evidence. Those statements describe that delivery, not the current selected model or completed scores. See [integration notes](task2_viz/INTEGRATION_NOTES.md) and [actual-score/context completion](task2_viz/CONTEXT_QC_INTEGRATION.md).

`task2_viz/site/data/` is the historical received coverage data. Use the current artifact above for actual-score/case review. `prototype/` is the earlier simulated interface; its patterns are not scientific results.
