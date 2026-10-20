# AI use and verification log: Task 2 visualisation (Member 5)

The report needs an AI-use table plus at least two cases where AI output was
wrong or rested on an unchecked assumption. Entries are added as work happens.

## AI use

| Date | Tool | What it was asked to do | How the output was used |
|---|---|---|---|
| 13 Oct 2026 | Claude Code (Claude Opus 5.5) | Inventory the SG-NEx m6Anet files on public S3, profile read counts, and write the fetch, placeholder, validation, build and packaging scripts plus the prototype page | Scripts and page kept in `task2_viz/`. Every number on the page comes from those scripts. Findings checked as listed below. |
| 19 Oct 2026 | Claude Code (Claude Opus 5.5) | Remove the simulated version; integrate Member 4's package (team manifest format, sample metadata, replicate grouping); rebuild the page from real data only | Placeholder data and generator moved to the Trash. Pipeline v0.2.0 builds a coverage-only page. Its counts and aliases were cross-checked against Member 4's independent files (case 5). |
| 19 Oct 2026 | Claude Code (Claude Opus 5.5) | Package the scripts for the team after Member 1 found them missing; add `verify_rebuild.py` | Clean-copy rebuild reproduced all 132 data files and both reports exactly (macOS). A negative test confirmed the verifier flags altered files. Ubuntu not yet tested. |

## Cases where the AI output was wrong or unverified

### 1. Wrong count of runs

- **What happened:** the assistant first said S3 held 22 m6Anet-processed runs.
- **How it was caught:** recounting the S3 listing, after spotting that the count had dropped the listing's own folder entry, gave 23 runs (7 cell lines, 17 replicates). That count is now produced by `fetch_public_data.py` and written to `runs_discovered.csv`.
- **Action:** corrected in chat; the pipeline discovers the runs itself rather than relying on a typed number.

### 2. Inflated share of unannotated transcripts, caused by an unnoticed ID-format difference

- **What happened:** the assistant estimated that about 5% of well-covered sites sat on transcripts missing from the annotation.
- **How it was caught:** a supposedly "unannotated" transcript appeared as `ENST00000000233.9`. Counting versioned IDs per file showed that one run (MCF7 replicate 3 run 1) uses versioned IDs throughout, while the other 22 runs don't.
- **How the fix was checked:**
  - All 43,704 of its versioned IDs that appear in the table match the Ensembl 91 versions exactly.
  - After stripping the suffix, its sites overlap the other MCF7 run 87.8%, close to the HepG2 replicate pair's 89.4%.
- **Action:** the pipeline now strips version suffixes before joining, and the page records this. The corrected share is 2.7% (11,965 of 451,352 sites).
- **Effect if missed:** the bug had also created a false "MCF7-only" group of 440k sites in the cell-line sharing chart.

### 3. Placeholder generator produced a fake disagreement

- **What happened:** the simulated scores gave the two MCF7 runs a near-zero correlation, unlike every other line.
- **Cause:** the generator hashed the raw transcript IDs, so the versioned and unversioned copies of each site got unrelated simulated scores.
- **How it was caught:** looking at the agreement chart in the browser.
- **Action:** the generator now hashes the version-free IDs. MCF7 agreement is now 0.89 / 0.95 / 0.98 across the three read bands, matching the other lines by construction.
- **Lesson:** a pattern in simulated data can come from a bug, and every chart needs a sanity check.

### 4. Validator missed duplicate rows when scores were also bad

- **What happened:** the first validator stopped checking a file once it found an out-of-range score, so a duplicate site in the same file went unreported.
- **How it was caught:** a negative test with seven deliberately planted defects: shifted positions, a duplicate row, an out-of-range score, another run's file, a missing file, an extra column, and mixed model versions.
- **Action:** the duplicate check now runs first. The negative test reports all seven defects and exits with code 1.

## Checks that passed

- **Downloads:** all 24 public files match the sizes S3 reports. SHA-256 values are in `public_data/download_manifest.csv`.
- **Annotation table:** the header shift was confirmed on all 200,310 rows. After the fix, every gene ID starts with ENSG, every transcript ID starts with ENST, and there are no duplicates.
- **Unannotated transcripts:** four examples were looked up in Ensembl REST. All sit on alternative haplotype or patch scaffolds, e.g. `HG2030_PATCH`, `HSCHR15_5_CTG8`.
- **TP53 gap:** TP53's absence from the site list is real. No TP53 site reaches 20 reads in any run (highest 15), and K562 has almost no TP53 reads.

### 5. Wrong example in a caveat about technical differences (19 Oct 2026)

- **What happened:** the page's issue list said replicates were "sequenced years apart", with HepG2 as the example.
- **How it was caught:** checking the claim against the sample sheet. HepG2's two runs are about seven weeks apart (2018-10-11 and 2018-11-21); they differ in device and basecaller, not in year. A549's runs, in December 2018 and March 2020, are the correct example.
- **Action:** the sentence now names A549 and states only what the sample sheet shows: different dates, devices and basecallers.

### Cross-checks against Member 4's independent package (19 Oct 2026)

- **Replicate support:** sites measured in ≥1, ≥2 or every replicate of each line, and the 7-line intersection, at 20/50/100 reads, for annotated genes and for all transcripts. All 144 values match Member 4's `replicate_coverage_support.csv` exactly (`reports/crosscheck_member4.json`).
- **Alias tables:** both map the same 46,297 versioned IDs to identical transcripts.
  - Member 4 marked 13,589 as verified; this pipeline verifies 43,704 against the full Ensembl 91 table.
  - Member 4's verified set is exactly this pipeline's verified set restricted to transcripts with a ≥20-read site, the only annotation Member 4 had.
  - No ID verified by Member 4 fails here.
- **Member 4's package itself:** it contains no full-run predictions, and its manifest says `PENDING_TEAM_SELECTION`. The validator correctly refuses it: 24 FAIL (pending model, 23 missing files).
