"""Data0-only cap128 experiment using the unchanged, resumable original trainer."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import time
import psutil
import numpy as np

REPO = Path(__file__).resolve().parents[2]
CORE = REPO / 'model_elgin/context_reference_v1'
sys.path.insert(0, str(CORE))
import train as fitting
from common import Measure, save_json
from data import sha256
from model import source_sha256
import summarize_context_cv as saved

PLAN = REPO / 'model_elgin/READ_CAP_EXPERIMENT.md'
DEFAULT = REPO / 'model_elgin/outputs/read_cap_v1'
BASELINE = REPO / 'model_elgin/outputs/context_reference_v1'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def configuration(recipe, cap=128):
    require(cap in (32, 128), 'Only prespecified training caps32/128 are allowed')
    expected = dict(fitting.BASE, context_mode='none', min_sites=30)
    require(recipe['config'] == expected and expected['cap'] == 32,
            'Comparator must be the unchanged original-feature cap32 recipe')
    for key, value in dict(max_epochs=20, patience=5, seed=2026, batch_size=256, threads=4, smoke=False).items():
        require(recipe[key] == value, 'Unexpected comparator setting: ' + key)
    return dict(expected, cap=cap)


def experiment_identity(original):
    require(original['source_sha256'] == fitting.source_hashes(), 'Frozen core source changed')
    wrapper, plan = source_sha256(__file__), source_sha256(PLAN)
    sources = dict(original['source_sha256'])
    sources.update({'tools/train_read_cap.py': wrapper, 'READ_CAP_EXPERIMENT.md': plan})
    return dict(original, source_sha256=sources, training_entrypoint_sha256=wrapper,
                experiment_plan_sha256=plan)


@contextmanager
def process_lock(path):
    """One writer per phase, including after process death; preserve stale records."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    owner = dict(pid=os.getpid(), process_created=psutil.Process().create_time(), token=str(time.time_ns()))
    while True:
        try:
            with path.open('x', encoding='utf-8') as handle:
                json.dump(owner, handle)
            break
        except FileExistsError:
            previous = json.loads(path.read_text(encoding='utf-8'))
            alive = False
            try:
                alive = abs(psutil.Process(previous['pid']).create_time() - previous['process_created']) < .01
            except psutil.NoSuchProcess:
                pass
            require(not alive, 'This phase already has an active process; do not start a duplicate')
            path.replace(path.with_name(path.name + '.stale.' + str(time.time_ns()) + '.json'))
    try:
        yield
    finally:
        if path.exists() and json.loads(path.read_text(encoding='utf-8')) == owner:
            path.unlink()


def delegate_cv(cache, meta, population, config, args, identity):
    """No new fitting algorithm: call the exact frozen CV implementation."""
    require(config['cap'] in (32, 128) and config['context_mode'] == 'none', 'Invalid experiment config')
    return fitting.run_cv(cache, meta, population, config, args, identity)


def benchmark(cache, meta, config, args, identity):
    population = np.arange(len(meta), dtype=np.int64)
    initial, inner, refit, held, audit = fitting.partition(meta, population, 0)
    root = args.output_dir / 'benchmark'
    save_json(root / 'split_audit.json', audit)
    result = []
    for cap, stage, indices, validation, seed in [(32, 'inner', initial, inner, 2026),
                                                 (128, 'inner', initial, inner, 2026),
                                                 (128, 'refit', refit, None, 2126)]:
        directory = root / f'cap{cap}_{stage}'
        print(f'TIMING ONLY cap{cap}/{stage}: {len(indices)} fitting sites; one epoch', flush=True)
        record = fitting.run_fit(cache, meta.label.to_numpy(), indices, validation,
            dict(config, cap=cap), seed, directory, 1, 5, 256, 'smoke', identity)
        history = json.loads((directory/'history.json').read_text())
        result.append(dict(cap=cap, fit_stage=stage, fit_sites=len(indices),
            validation_sites=0 if validation is None else len(validation),
            epoch_wall_seconds=history[0]['wall_seconds'],
            fit_resources=record['resources'], artifact_sha256=record['best_sha256'],
            interpretation='one-epoch timing only; never promoted into CV or final model'))
    estimate = dict(benchmark=result,
        maximum_cv_epoch_work_seconds=5*(20*result[1]['epoch_wall_seconds'] + 20*result[2]['epoch_wall_seconds']),
        note='Maximum epoch-work extrapolation excludes startup/normalisation/checks/outer inference and is not a guaranteed ETA. Early stopping/refit duration may shorten work.')
    save_json(root / 'timing_summary.json', estimate)
    print('Saved timing summary (not candidate comparison metrics).', flush=True)


def execute(args):
    evidence = {}
    print('Checking completed cap32 comparator and unchanged source/data provenance...', flush=True)
    baseline = saved.load_mode(BASELINE / 'cv', 'none', evidence)
    config = configuration(baseline['recipe'])
    identity = experiment_identity(baseline['recipe']['identity'])
    cache = fitting.Cache(args.cache)
    require(cache.source == identity['cache_manifest_sha256'], 'Wrong data0 cache')
    require(sha256(args.labels) == identity['labels_sha256'], 'Changed data0 labels')
    require(sha256(args.folds) == identity['folds_sha256'], 'Changed shared gene folds')
    meta = fitting.align_metadata(cache, args.labels, args.folds)
    require(len(meta) == 121838 and int(meta.label.sum()) == 5475, 'Unexpected data0 population')
    population = fitting.choose_population(meta, 20 if args.phase == 'smoke' else None, 2026)
    if args.phase != 'smoke':
        require(fitting.index_hash(population) == baseline['recipe']['population_sha256'], 'Population changed')
    args.max_epochs, args.patience, args.seed = (2 if args.phase == 'smoke' else 20), 5, 2026
    args.batch_size, args.threads = 256, 4
    args.outer_folds = [0] if args.phase == 'smoke' else list(range(5))
    fitting.torch.set_num_threads(4)
    before = dict(source_sha256=fitting.source_hashes(), wrapper=source_sha256(__file__), plan=source_sha256(PLAN))
    invocation = dict(phase=args.phase, sites=len(population), genes=int(meta.iloc[population].gene_id.nunique()),
        identity=identity, configuration=config, arguments=sys.argv[1:],
        no_data1=True, no_final_fit=True, baseline_full_data0_score=baseline['metrics']['primary_score'])
    save_json(args.output_dir / f'{args.phase}_arguments_{time.time_ns()}.json', invocation)
    # Audit all five split boundaries before fitting, even in one-fold smoke.
    audits = []
    for fold in range(5):
        *_, audit = fitting.partition(meta, population, fold)
        audits.append(audit)
    save_json(args.output_dir / (args.phase + '_split_preflight.json'), audits)
    if args.phase == 'benchmark':
        benchmark(cache, meta, config, args, identity)
    else:
        print(f'{args.phase.upper()}: cap128, {len(population)} data0 sites, folds{args.outer_folds}', flush=True)
        delegate_cv(cache, meta, population, config, args, identity)
    require(before == dict(source_sha256=fitting.source_hashes(), wrapper=source_sha256(__file__),
                           plan=source_sha256(PLAN)), 'Source/plan changed during execution')
    print('Completed requested phase; no data1 or final all-data0 model fit.', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['smoke', 'benchmark', 'cv'], default='smoke')
    parser.add_argument('--cache', type=Path, default=REPO.parent/'advanced_model/cache/data0')
    parser.add_argument('--labels', type=Path, default=REPO.parent/'data0/data.info.labelled')
    parser.add_argument('--folds', type=Path, default=REPO/'eda/received/shared_folds/data0_folds.csv')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT)
    args = parser.parse_args(argv)
    args.output_dir = args.output_dir.resolve()
    require(args.output_dir.is_relative_to(DEFAULT.resolve()), 'Output must stay in dedicated experiment tree')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with process_lock(args.output_dir / (args.phase+'.lock')):
        status = args.output_dir / (args.phase+'_status.json')
        stamp = str(time.time_ns())
        save_json(status, dict(status='running', phase=args.phase, invocation=stamp))
        try:
            with Measure() as measured:
                measured.output = args.output_dir / f'{args.phase}_invocation_{stamp}.json'
                execute(args)
        except BaseException as error:
            save_json(status, dict(status='interrupted_or_failed', phase=args.phase, invocation=stamp,
                                   error=type(error).__name__+': '+str(error)))
            raise
        save_json(status, dict(status='complete', phase=args.phase, invocation=stamp,
                               resources=measured.record, full_candidate_cv=args.phase=='cv'))


if __name__ == '__main__':
    main()
