# AI use and verification — Member 4 working evidence

Human review of the complete package is still required. This is evidence to consolidate with the team's existing AI-use record, not a claim that the final disclosure is complete.

| AI tool | Prompt and output | Use in assignment | Verification/status |
|---|---|---|---|
| ChatGPT / Codex (this conversation; use the actual model name shown in the session if the team records it) | Member 4 starter prompt; inspect shared context, rubric, SG-NEx data/replicates/reference, fair biological comparisons, reproducible code and conflicting evidence | File/repository review, public sample and object inventory, coverage reconstruction, original read-count verification, analysis code, plots, notebook and draft contribution | Original inputs/repo commit recorded; all 23 original read-count tables checked; scientific correctness tests run; figures inspected. No real Task 2 scores, model training or chemical validation performed. |

## Actual detected issues and corrections in this work

1. **Over-broad transcript-version assumption.** The first upstream verifier asserted that every retained versioned MCF7 ENST ID had an exact annotation-version match. It stopped at `ENST00000633093.1`, whose prototype annotation was an unversioned unresolved-reference entry, not a verified annotation version. Inspection showed all 107,431 retained annotated-human MCF7 candidate rows matched the supplied annotated version, whereas 1,884 rows in the prototype's `alt_haplotype` category lacked that evidence. Correction: require exact matches for the primary annotated-human population, flag other aliases as coverage-only/unverified, exclude their category from primary biology, and rerun all 23 read-count checks. This preserves the limitation rather than pretending version identity was verified for every reference entry. Exact FASTA/GTF rederivation remains pending.
2. **Runtime documentation assumption.** An initial draft said Python 3.11 without checking the runtime. Executing `sys.version` showed Python 3.12.14. The README and validation record were corrected before delivery; dependency versions were read from the actual imports. A fresh Ubuntu install has not been claimed.

The first attempt to inspect all documents also assumed `bs4` was installed and failed at import. The files were subsequently inspected with available local extraction tools. This was a tooling failure, not a biological finding or a completed analysis.

## Scientific checks that prevented unsupported results

- The prototype explicitly identifies every modification score as simulated. No simulated score was read by the coverage reconstruction or used as an analysis result.
- Current processed S3 inventory, the 56-row direct-RNA metadata scope and the older 12-row RNAmod TSV disagree in scope. All are retained; the smaller list was not silently called complete.
- The script tests verify equal biological-replicate weighting, omission of missing sites from pairwise comparisons, retention of overlapping replicate ranges and rejection of nonfinite/invalid scores, invalid positions, duplicate keys and simulated-data declarations.
- All 23 public read-count files match the coverage table's retained entries. This establishes coverage consistency, not chemical truth or independence of RNA preparations.
- No p-values, stoichiometry estimates, enrichment results or real-model SG-NEx differences are filled in without data.

Original source documents, Member 1's work and Member 5's prototype remain attributed. The new scripts and prose were AI-assisted; no external model code was copied into this package. Public biological/method sources are listed in `analysis_plan.md`. The final team report must consolidate the required AI-use table and at least two actual wrong/misleading/unverified AI-output examples with detection and correction evidence, following the handout.

## 19 October 2026 continuation

AI inspected the supplied team README and Member 3 archive, aligned the handoff structure/schema, retained the candidate as unselected, reproduced its ten-site output, checked source hashes and recomputed development/exposed-transfer metrics. It added a batching adapter using the received frozen model/reference unchanged, optional metric reproduction and integration tests, and updated the concise report/handoff. Seven scientific/software tests and the updated notebook checks passed; logs and receipts identify actual results. No full-run SG-NEx predictions or final model-selection decision were invented.

The review retained a limitation in incoming prose: data2's supplied fractional-label design and response do not by themselves establish modification stoichiometry. This remains an unverified interpretation requiring experimental source evidence. Candidate arrival does not establish team final selection, and a successful Linux example is not a fresh AWS Ubuntu evaluation. Human review of the final integrated report and model-selection decision remains required.

## 19 October 2026 handover consolidation

AI inspected the saved package and execution paths, separated coverage/metadata, real development/example outputs and demonstration scores, and consolidated the handover into HANDOFF.md. It fixed the working scope at the requested 23 processed runs, added existing-inventory download links and a lightweight downloader, and reran existing software checks. Only a tiny local fixture was used to check the new downloader; no full public signal was downloaded and no new biological analysis was claimed. Coordinate evidence remains explicitly incomplete.
