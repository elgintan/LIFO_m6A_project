# Historical split composition: actual descriptive check

Completed during setup, 15 October 2026, using the received data0 site summaries
and original shared gene-fold assignments. No raw reads were rescanned, no
model was fitted/scored, no rows were filtered and no new split was generated.

Run from repository root with standard-library Python:

```bash
python eda/audit_existing_split.py
```

## Actual findings

- All 121,838 summary rows match unique assignments; all 3,852 genes remain
  within a single fold. All 18 central motifs are represented globally.
- The five validation groups contain 1,083–1,105 positives each, with positive
  fractions approximately 4.45–4.53%. Global class balance is close.
- Of 90 motif-by-validation-fold groups, **8 lack both classes**, and **38 have
  fewer than 20 positive sites**. Twenty is a descriptive support reference,
  not a new filtering or quality threshold.
- In one motif/fold, the corresponding training portion has **no positive
  example of that motif**. The full counts are in `motif_support.csv`.

## How this affects decisions

Overall label balance does not guarantee reliable evaluation for every context.
We need shared information for rare motifs, subgroup denominators and honest
limits on subgroup AUCs. AUC is undefined for a one-class evaluation group.
Changing the ratio cannot make one rare positive appear independently in both
training and testing; retaining difficult examples and obtaining more suitable
labelled evidence are different decisions from hiding them through exclusions.

These findings do not prove a fold count optimal. After reviewing support and
computation, Elgin accepted the five-group development methodology on 15 October;
Samuel's acknowledgement has not yet been reported. See the
[minimum shared rules](../../model_evaluation/SHARED_RULES.md). Existing outer
assignments remain unchanged. Report the complete assessment population.

`coverage_support.csv` gives counts at the same descriptive coverage bins as
Member 1's EDA. These are not new minimum-coverage rules or causal effects.

## Files

- `composition_audit.json`: scope, checksums and summary.
- `fold_summary.csv`: gene/site/class counts per historical fold.
- `motif_support.csv`: held-out class and training-positive support per motif.
- `coverage_support.csv`: class counts by fold and coverage bin.

The source manifest has `fold_id` and no labels. The audit joins it to labels
from Member 1's summaries. An initial incorrect header assumption stopped
before outputs; the corrected script and successful records are retained.
