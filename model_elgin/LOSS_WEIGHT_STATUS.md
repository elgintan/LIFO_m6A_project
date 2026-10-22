# Positive-loss-weight experiment: execution status

21 October 2026. The user authorised one final controlled training comparison.
The [fixed design](LOSS_WEIGHT_EXPERIMENT.md) changes positive loss weight3->1
while keeping cap128, architecture, features, raw labels, natural prevalence,
exact five gene folds and the inner-selection/fresh-refit procedure unchanged.

**Current stage: training and queued comparison completed; results reviewed
on22October.** Training finished on21October at17:19:42SGT; the
reporter finished at17:19:55SGT. Both exited0 before the later stop request.
The original job returned completion when the stop signal was sent; no new
training or restart was launched. Full training took95.251minutes command
elapsed, within the original90–120minute estimate from15:44SGT.

All20last/best checkpoint files across the10inner/refit fits, plus their
20history/completion files, were checked for presence and hashed into a local
timestamped pause receipt. Logs, predictions and generated comparison remain
in the experiment output folder. The user returned on22October for results
review; this completed CV was not restarted. The [checked aggregate results](loss_weight_results/README.md)
give mean-fold S0.7183812884 for weight1 versus0.7187146070 for weight3.
Retain weight3 under the predeclared criterion; the difference is small and
mixed, with higher pooled S/precision but lower mean PR/recall/F1 for weight1.
See the [decision and limits](LOSS_WEIGHT_REVIEW_2026_10_22.md). There is no
active training for this experiment.

Nine training checks passed in9.088s, including tensor-identical
weight3 delegation and exact interrupted weight1 recovery. Twelve reporter
checks passed in21.143s, including refusal of incomplete or altered evidence
and preservation of a negative outcome. The small real-data check completed
on3,328sites from100whole genes, with two inner and two fresh refit epochs.
It exited0 in31.432s command elapsed (15.594s monitored work). These are
software checks, not full candidate comparison results. Isolated full-size
one-epoch timing also exited0: inner29.565s/epoch and refit34.536s/epoch;
97.214s command elapsed (81.679s monitored work). The maximum-epoch
extrapolation is106.835minutes before startup, checks and outer inference;
early stopping can reduce work. The weight3 comparator's mean-fold S
remains0.7187146070. Neither timing fit initialises a CV fit.

The first integrator test rerun hit a Windows atomic-replace permission error;
another attempt used a restricted sandbox temporary directory and also failed.
Both failed logs were preserved. A fresh workspace temporary directory passed
all21checks. No assertion was weakened and no frozen training code was changed.

Code and models from completed experiments stay unchanged. The new experiment
uses `tools/train_loss_weight.py` and local ignored `outputs/loss_weight_v1/`.
Every completed fitting epoch retains last/best weights, optimiser/RNG states,
history and resource logs. Identical-command recovery checks identities before
reusing completed work. Do not launch a duplicate from another tool merely
because its process list cannot see the original Windows execution session.
The timestamped pipeline/training/report receipts and console logs are in
`outputs/loss_weight_v1/checks/`; `cv_status.json` records the trainer phase.
The original local job confirmed exit0. For future experiments, that original
execution session rather than an unrelated process inventory is authoritative.

The full command, from the repository root, is:

```powershell
../advanced_model/.venv/Scripts/python.exe -B -u model_elgin/tools/train_loss_weight.py --phase cv
```

The local orchestration job successfully ran the following after full CV,
keeping timestamped console logs for both commands:

```powershell
../advanced_model/.venv/Scripts/python.exe -B model_elgin/tools/report_loss_weight.py
```

This is one finite data0 experiment, with no data1/data2/SG-NEx access, final
all-data0 fit, threshold search or calibration. The previous0.5 reporting rule
belongs to the current weight3 candidate; the weight1 pipeline's calling policy
would need its own review if nominated. The measured ranking criterion decides
the leading candidate, without assuming the new model must win.

After this bounded comparison, required benchmark, final-model, prediction,
Task2, report/explorer and Ubuntu reproduction work should take priority.
