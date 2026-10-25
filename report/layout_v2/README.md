# Scientific report review draft - layout v2

[Open the PDF](DSA4262_LIFO_report_draft.pdf). This is an assistant-typeset draft
for team verification, not a final approved report or submission.

The PDF has **five A4 main-body pages and one separate reference page**. Body
text uses embedded Arial 11 pt; captions use Arial 9.2 pt, tables 9.3 pt and
references 10 pt. All six pages were rendered with Poppler at 130 dpi and
visually inspected. The source paragraphs and original table cells were checked
against extracted PDF text, with table cells checked in their own page regions.
The [layout receipt](layout_receipt.json) records source hashes, page geometry,
font checks, source preservation, plotting versions and review scope.

The unchanged source is [the saved scientific draft](../REPORT_DRAFT_2026_10_25.md).
Its editorial notes are excluded. SG-NEx comparison methods moved to page 3;
page 4 adds a continuation heading. The original case figure's context, positive
training-label counts and data0-key annotations moved to a readable adjacent
table and note. No metric, tradeoff or caveat was removed. Unicode dashes were
typeset with ASCII hyphens. The four references were set as separate entries.

The three report figures were recomposed at their placement width with readable
Arial labels, preserving the original scientific populations and scales:

- Figure 1 uses the original benchmark reporter's saved gene-held-out
  development scores and pretrained reference scores. Each source hash and each
  pooled curve area must match the existing benchmark summary. It never reads
  final fitted-data0 predictions. The mean-fold table remains a separate summary.
- Figure 2 uses the existing complete 20-read, all-seven-line CDF grid and cutoff
  summary: 33,452 sites per line, all seven lines and all three original cutoffs.
- Figure 3 uses the existing fixed four cases and their original run/group
  records: 92 records, 80 scored and 12 unscored. All original qualifying points
  and valid extremes remain. No new selection or score/identifier filter occurs.

Original PNGs, model files, scores, folds and source Markdown were preserved.
This work performs no training, inference, new-test prediction or cloud job.
Layout-only dependencies were re-used from the bundled PDF runtime and an
existing compatible local analysis environment; no packages or model pins were
installed or changed. Package versions are recorded separately in the receipt.

The portable [builder](../scripts/build_report_pdf.py) resolves repository paths
from its own location. With its documented Python dependencies and the saved
local benchmark inputs available, run from the repository root:

```text
python -B report/scripts/build_report_pdf.py --out report/layout_v3
```

Use a fresh output directory to preserve earlier candidates. On a system without
Windows Arial, supply `--font-dir` pointing to a directory containing licensed
`arial.ttf`, `arialbd.ttf`, `ariali.ttf` and `arialbi.ttf` files. The builder's
automatic checks precede a required separate PDF render and visual review.

Team confirmation of authorship, actual AI tool/model details, other members'
AI use and bibliography remains pending. This draft includes neither invented
contributions nor personal reflections and claims no unseen-test result.
