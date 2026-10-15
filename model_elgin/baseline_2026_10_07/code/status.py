"""Write a factual progress snapshot; never substitutes for completed results.md."""
import json
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo

root=Path(__file__).resolve().parent;runs=root/'runs'
def load(path):
    try:return json.loads(path.read_text())
    except (FileNotFoundError,json.JSONDecodeError):return None
screens=load(runs/'screen_results.json') or []
finalists=load(runs/'finalists.json') or []
inner=list(runs.glob('*_fold*_inner/complete.json'))
refits=list(runs.glob('*_fold*_refit/complete.json'))
repeats=list(runs.glob('repeat_*/complete.json'))
predictions=list((root/'predictions').glob('LIFO_dataset*.csv.manifest.json'))
lines=['# Actual progress','',datetime.now(timezone.utc).astimezone(ZoneInfo('Asia/Singapore')).isoformat(),'',
 'This is a status snapshot. Final results.md is written only after completed training, evaluation and prediction checks.','',
 '- Completed: strict all-read data0 cache, 121,838 sites and 11,027,106 reads; correctness and synthetic resume verification.',
 f'- Screening: {len(screens)}/6 configurations completed.',
 f'- Finalists: {", ".join(c["id"] for c in finalists) if finalists else "pending"}.',
 f'- Repeat-seed checks: {len(repeats)}/2 completed.',
 f'- Outer-fold inner epoch-selection fits: {len(inner)}/10 completed.',
 f'- Full outer-training refits: {len(refits)}/10 completed.',
 f'- Aggregated five-fold candidate reports: {len(load(runs/"cv_results.json") or [])}/2 completed.',
 f'- Frozen all-data0 final model: {"saved" if (runs/"final_model.pt").exists() else "pending"}.',
 f'- Same-model dataset predictions: {len(predictions)}/3 completed.',
 f'- Frozen data1 evaluation: {"saved" if (root/"evaluations/data1_frozen_selection/metrics.json").exists() else "pending"}.',
 f'- Actual results.md: {"saved" if (root/"results.md").exists() else "pending"}.','',
 'Data0-only training and tuning. No external weights or training data. Data1 is previously exposed selection data; data2 binary scoring and Ubuntu execution remain unverified.','',
 'Each run retains best.pt, last.pt (weights/optimizer/RNG/epoch), history.json and training.log. Repeating the same command resumes unchanged completed epoch checkpoints.']
(root/'PROGRESS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines[6:18]))
