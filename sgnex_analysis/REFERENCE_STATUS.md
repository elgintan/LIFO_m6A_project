# Input and reference evidence

Scope remains the selected 23 processed runs; the broader inventory is not another completion gate.

23 October completion update: all 23 genuine inputs passed strict source and
eligible-key/count checks and their predictions completed. Cross-run context
QC has completed: all451,352scoreable keys have consistent saved contexts,
including low-read observations. No context exclusions are needed. This does
not establish FASTA identity; see [actual QC evidence](context_qc_results/README.md).
The earlier first-run evidence below remains valid within its stated scope.

23 October: the first full Hct116rep3run4 input passed strict nine-feature
parsing and exact inherited >=20 coverage-key/count agreement. It contains
1,302,514 sites / 15,133,352 reads, with 135,870 at 20 reads, 50,332 at 50
and 21,438 at 100. All its model-encoded canonical contexts are supported by
data0 training, although positive-label support differs. This technical evidence
does not resolve the reference/coordinate uncertainties below. See
[selected model information](MODEL_INFO.md).

| Item | Evidence available | Pending / limits |
|---|---|---|
| Runs/signals | All 23 original signals retained with completed content hashes, strict parsing and coverage/count checks | Exact historical feature-preprocessing compatibility remains qualified |
| Coverage | Saved original read-count verification; retained matrix independently recounted locally | Not validation of signal-event offsets or alignments |
| Reference | Upstream-reported GRCh38/Ensembl91; inherited transcript versions/lengths | Exact FASTA/GTF filenames/hashes, complete composition and per-input provenance |
| MCF7 replicate3 run1 aliases | Explicit 46,297-row map: 13,589 inherited annotated-version matches; 32,708 coverage-only/unverified | Independent FASTA identity; no blanket suffix stripping or application to other runs |
| Literal position | Original integer key retained | Zero/one-based origin, candidate-A/event meaning and seven-base window offset |
| Reference utility | Synthetic exact-offset success/wrong-offset refusal; cross-run saved-context agreement now checked at all451,352scoreable keys | No genuine FASTA-offset validation or exon/GTF genomic conversion |
| Primary annotation | Inherited annotated-human category; other classes separate | Independent reconstruction, CDS/UTR/genomic validation |
| Replicates | 17 cell-line-plus-replicate-number metadata groups | Independent laboratory preparation provenance |
| Orthogonal assays | Matched-data flags/citations | Actual compatible labels, sample/coordinate identity, overlap/absence/coverage rules |

Keep original prediction identifiers and positions. Apply only explicit per-run aliases inside analysis. A successful count join is not evidence for the chemical nucleotide coordinate. Establish offsets from preprocessing documentation, not by choosing the offset with the most matches.

Once the exact reference and documented offset are known, export a plain CSV from genuine metadata with `transcript_id,transcript_position,sequence_7mer` and optional documented `reference_transcript_id`. From the repository root:

```powershell
& $py -B sgnex_analysis/scripts/check_reference_context.py --sites sgnex_analysis/outputs/reference_check_sites.csv --fasta $exactTranscriptFasta --window-start-offset $documentedOffset --out sgnex_analysis/outputs/reference_context_check.csv
```

The variables must hold established values. The utility adds the offset to the literal position to obtain the zero-based seven-base window start and checks context/central A. A known one-based central-A position would imply -4; a known zero-based central-A position -3. Neither is established for these inputs. Retain hashes, sampling/run scope and failures. A sampled success does not validate genomic exon mapping.

Until resolved, avoid region/genomic or chemical-fraction claims. Later same-site scores can support explicitly qualified descriptive predicted-pattern comparisons; software declarations alone do not establish missing provenance or biology.
