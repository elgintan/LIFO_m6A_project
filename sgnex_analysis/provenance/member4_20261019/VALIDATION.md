# Validation record

Executed locally during this preparation, 16 October 2026 Singapore.

- Python 3.12.14; numpy 2.3.5, pandas 2.2.3, matplotlib 3.10.8, scipy 1.17.0.
- All 128 supplied gene shards parsed. Packed read vectors have exactly 23 nonnegative integer entries. Unique transcript-position keys; 451,352 retained sites.
- Each run's retained ≥20/50/100 counts match the upstream overview. The all-reference sum at ≥20 is 2,983,948 run-site entries, not unique sites.
- Recomputed shared/replicate-aware coverage populations at 20/50/100 reads; ≥20/50 all-line one-replicate counts match the supplied coverage-only sharing summary.
- Official current processed prefix listing is not truncated and contains exactly the same 23 run IDs. Each has a unique official sample-metadata row with matching cell line. The broader direct-RNA table has 56 rows; 33 are outside the processed listing.
- All 23 original public read-count files were downloaded and checked. Every retained site/run value matches its original count or absence from that run table, and every original ≥20-read key is represented. Original files total 659,329,250 bytes. SHA256 per file is in `results/public_readcount_verification.csv`.
- MCF7 suffix normalisation causes no key collisions. Retained annotated-human versioned IDs match the supplied annotation versions; unresolved-reference IDs remain flagged and excluded from primary biology. Exact reference FASTA/GTF and signal-event offsets have not been rederived.
- `python -m unittest discover -s tests -v`: analysis correctness tests passed, including a complete small synthetic-fixture CLI run and refusal of simulated declarations. Fixtures are software checks and are deleted after testing.
- Scientific figure PNGs were visually inspected; no score data appears in them.

Not executed: final-model inference on SG-NEx, actual real-score comparisons, motif/region/pathway analysis, independent experimental validation, fresh AWS Ubuntu installation or full reconstruction of Member 5's interface. No claims that these steps are complete should be inferred from code being present.

Additional checks: the reference-context utility passed a synthetic exact-offset check and rejected a deliberately wrong offset. The notebook validated with nbformat 5.11.1 and its code cells executed with IPython 9.17.1 in a temporary QA dependency directory; the real-analysis cell remained disabled. HTML internal anchors and embedded images passed structural checks. A full browser render was not performed because no browser executable was installed. The two scientific PNGs were visually inspected.

## 19 October 2026 update: README alignment and Member 3

- The supplied README was inspected locally. Top-level manifest.csv now has its exact nine proposed columns, with 23 unique run rows and documented portable wide-coverage paths. MODEL_INFO.md and predictions/ are present; final model/reference fields and real run CSVs remain pending.
- The comparison CLI accepts the nine-column contract without requiring extra metadata columns. It requires the documented real-input declaration when the optional real_predictions column is absent, checks MODEL_INFO.md exists and coverage_file matches the actual matrix, and retains richer optional metadata support.
- Received Member 3 model/baseline hashes match its card; development prediction hashes match its metric records. The original ten-site predictor ran on Linux with the received pinned prediction dependencies and reproduced its expected CSV byte for byte (zero absolute score difference).
- Recomputed data0 pooled/mean-fold and data1 ROC, trapezoidal PR, AP and S match supplied metric records within 1e-12, using Member 1 derived labels and exact shared fold assignments. The packaged metric-check script was executed successfully. This is not a training rerun, raw-assay audit or final selection decision.
- Seven tests pass in the separate prediction environment: original scientific checks, nine-column end-to-end compatibility and matching coverage declaration, simulation refusal, batched candidate prediction parity/eligibility, cross-batch duplicate rejection, and reference-context checks. Log: results/readme_member3_tests.log. Synthetic test fixtures are software checks, not biological results.
- Updated notebook schema and code cells were verified with the real-analysis cell disabled. The HTML guide's new candidate update reports checked development metrics separately from the unchanged coverage plots.
- Candidate inference requirements remain separate from the analysis environment to avoid conflicting numpy/pandas pins. Actual local runtime was Python 3.12.14; prediction used LightGBM 4.7.0, numpy 2.4.6 and pandas 3.0.6. This does not establish clean AWS Ubuntu installation.
- Personal member names were removed from the received source-copy prose/docstrings; original model/baseline bytes and numerical source outputs remain unchanged. Source/copy checksums are retained. No new external push, deployment, team message or cloud provision occurred.

Still not performed: selected-model/full-run SG-NEx inference, final score comparisons/biological interpretation, independent modification validation, exact FASTA/GTF/offset reconstruction or a new public-inventory refresh. Earlier candidate-unavailable statements in dated background documents are superseded; the original simulation warnings still apply to the earlier Explorer.

## 19 October 2026 handover inspection

- Current source ZIP was resolved to its saved identity/version; the local ZIP carried matching identity/version and size. Existing files were extracted once into a new working folder.
- Working scope fixed to the 23 processed runs per the user's handover instruction. Broader metadata retained only as background; no new public inventory refresh or expansion.
- Existing signal object keys/sizes joined to the 23 sample rows; added exact public HTTPS links, portable local paths and explicit not-downloaded status to metadata/sample_manifest.csv. Signal total: 33,365,823,342 bytes. All link/size/path mappings matched the saved object inventory.
- Added a standard-library signal download helper. A temporary tiny local file tested transfer, size validation, hash receipts, reuse and wrong-size refusal. No full public signals were downloaded.
- Reran analysis tests in the existing analysis runtime: six passed, optional LightGBM test skipped (results/handover_analysis_tests.log). Reran in the existing candidate runtime: all seven passed (results/handover_candidate_tests.log), including batched example parity, eligibility and duplicate rejection. No fresh environment installation claim.
- Candidate model and baseline bytes still match the model card SHA256 values. No full-run signal files or prediction CSVs are bundled. No real-score comparison was executed.
- Consolidated current instructions into HANDOFF.md; removed the competing lower-case handoff; retained existing code, metadata, figures and write-up in place. Historical notes are marked subordinate.
- Added explicit limitations for parser aborts, missing universal-model/export adapters, absent motif enrichment, missing display build/integration tooling, and unverified reference/coordinate conventions. Existing reference utility tests remain synthetic software checks.

Not performed in this handover: full signal downloads, full SG-NEx inference, final model selection, real-score biological comparison, live endpoint verification, independent FASTA/GTF/context audit, new figures, interface integration or external publication.
