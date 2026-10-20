"""Data0-only frozen-CV read-depth diagnostic; never fits or calibrates a model.

Primary 'both' replaces the MIL read bag and recomputes all 63 summaries from
the same nested subset. Secondary 'bag-only' preserves the original all-read
summary, matching the cap32/full-summary distinction in training. All-cache
reproduces saved OOF; all-recomputed isolates float32-cache summary precision.
Completed conditions resume after hash checks. Interrupted conditions restart,
preserving their partial CSV and attempt log. Trial selection is label-free.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

import numpy as np
import pandas as pd
import sklearn
import torch

REPO = Path(__file__).resolve().parents[2]
CORE = REPO / 'model_elgin/context_reference_v1'
ALLOWED_OUTPUT = REPO / 'model_elgin/outputs/read_depth_stability_v1'
sys.path.insert(0, str(CORE))
import train as fitting
import model as network
from common import Measure
from data import sha256, summarise

SCORER = fitting.SCORER
DEPTHS = (20, 32, 50, 100)
SEEDS = (2026, 2027, 2028)
HEADER = ['site_index', 'transcript_id', 'transcript_position', 'gene_id', 'fold_id',
          'label', 'coverage', 'motif', 'n_reads_used', 'perturbation', 'depth',
          'repeat_id', 'repeat_seed', 'score', 'baseline_score', 'sample_indices_sha256']
COHORT_COLUMNS = ['site_index', 'transcript_id', 'transcript_position', 'gene_id',
                  'fold_id', 'label', 'coverage', 'context', 'motif', 'baseline_score']
TOLERANCE = 1e-6


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fingerprint(value):
    return fitting.fingerprint(value)


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep atomic-write names short on Windows, including deeply nested tests.
    temporary = path.with_name(f'.j{time.time_ns():x}.tmp')
    with temporary.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, path)


def immutable_json(path, value):
    path = Path(path)
    if path.exists():
        require(json.loads(path.read_text(encoding='utf-8')) == value,
                'Existing settings/source hashes differ; use a new output directory: ' + str(path))
    else:
        save_json(path, value)


def nested_indices(coverage, depth, repeat_seed, transcript, position):
    """Uniform prefix without replacement; restore original within-bag row order."""
    require(type(coverage) is int and coverage > 0, 'Coverage must be a positive integer')
    require(type(depth) is int and 1 <= depth <= coverage, 'Depth must be in 1..coverage')
    require(type(repeat_seed) is int and repeat_seed >= 0, 'Repeat seed must be nonnegative integer')
    key = ['read-depth-stability-v1', repeat_seed, str(transcript), int(position), coverage]
    seed = int(fingerprint(key)[:32], 16)
    order = np.random.Generator(np.random.PCG64(seed)).permutation(coverage)
    return np.sort(order[:depth]).astype(np.int64)


def select_cohort(meta, trial=False, genes_per_fold=20, sites_per_fold=100):
    """Only coverage, fold, gene and site identity enter selection; never labels."""
    require(genes_per_fold > 0 and sites_per_fold > 0, 'Trial limits must be positive')
    eligible = meta.loc[meta.n_reads.ge(100)].copy()
    if trial:
        keep = []
        for fold in range(5):
            part = eligible.loc[eligible.fold_id.eq(fold)]
            genes = sorted(part.gene_id.unique(), key=lambda g: fingerprint(['trial-genes', 2026, fold, str(g)]))[:genes_per_fold]
            part = part.loc[part.gene_id.isin(genes)]
            ranked = sorted(part.index, key=lambda i: fingerprint(['trial-sites', 2026, fold,
                             str(part.loc[i, 'transcript_id']), int(part.loc[i, 'transcript_position'])]))
            keep.extend(ranked[:sites_per_fold])
        eligible = eligible.loc[keep]
    require(not eligible.empty and set(eligible.fold_id) == set(range(5)), 'Cohort must contain sites from all five folds')
    eligible['site_index'] = eligible.index.astype(np.int64)
    eligible['coverage'] = eligible.n_reads.astype(np.int64)
    eligible['motif'] = eligible.context.str[1:6]
    return eligible.sort_values(['fold_id', 'coverage', 'site_index'], kind='stable')


def condition_specs(depths=DEPTHS, seeds=SEEDS, perturbations=('both', 'bag-only')):
    specifications = []
    for fold in range(5):
        for name in ('all-cache', 'all-recomputed'):
            specifications.append(dict(condition_id=f'fold{fold}/{name}', fold_id=fold,
                                       perturbation=name, depth='all', repeat_id=-1, repeat_seed='all'))
        for name in perturbations:
            for depth in depths:
                for repeat, seed in enumerate(seeds):
                    specifications.append(dict(condition_id=f'fold{fold}/{name}/depth{depth}/seed{seed}',
                        fold_id=fold, perturbation=name, depth=depth, repeat_id=repeat, repeat_seed=seed))
    return specifications


def _fit_signature(recipe, fold, audit, stage, selected_epochs):
    populations = audit['populations']
    is_refit = stage == 'cv_refit'
    return fingerprint(dict(config=recipe['config'], seed=recipe['seed']+(100 if is_refit else 0)+fold,
        max_epochs=selected_epochs if is_refit else recipe['max_epochs'], patience=recipe['patience'],
        batch_size=recipe['batch_size'], stage=stage, identity=recipe['identity'], threads=recipe['threads'],
        versions=dict(python=platform.python_version(), torch=str(torch.__version__), numpy=np.__version__,
                      pandas=pd.__version__, sklearn=sklearn.__version__),
        fitting=populations['refit' if is_refit else 'initial_fit']['indices_sha256'],
        validation=None if is_refit else populations['inner_validation']['indices_sha256']))


def validate_bundle(bundle, completed, recipe, fold, audit, selected_epochs):
    """Reject training-stage, mode, identity and non-heldout refit mismatches."""
    require(bundle.get('kind') == 'context_reference_v1' and bundle.get('stage') == 'cv_refit', 'Only frozen cv_refit bundles are allowed')
    require(bundle.get('config') == recipe['config'] and recipe['config']['context_mode'] == 'none', 'Need the original-feature control configuration')
    require(bundle.get('context_reference') is None, 'Control must not carry active relative references')
    require(bundle.get('input_fingerprints') == recipe['identity'], 'Model inputs/source fingerprints differ')
    expected = _fit_signature(recipe, fold, audit, 'cv_refit', selected_epochs)
    require(bundle.get('fit_signature') == completed.get('signature') == expected, 'Refit signature/config/split/packages differ')
    require(bundle.get('epoch') == completed.get('epochs_completed') == selected_epochs, 'Incomplete prescribed refit epochs')
    require(bundle.get('seed') == completed.get('seed') == recipe['seed']+100+fold, 'Refit seed differs')
    require(completed.get('validation_sites') == 0 and completed.get('train_sites') == audit['populations']['refit']['sites'], 'Wrong refit population')
    norm = bundle['norm']
    require(norm.get('fit_indices_sha256') == completed.get('fit_indices_sha256') == audit['populations']['refit']['indices_sha256'], 'Preprocessing was not fitted on the four permitted groups')
    require(norm.get('fit_sites') == completed['train_sites'], 'Normalization fit population differs')


def preflight(args):
    directory = args.cv_dir.resolve()
    recipe = json.loads((directory/'recipe.json').read_text())
    progress = json.loads((directory/'progress.json').read_text())
    require(progress.get('full_five_folds') is True and progress.get('full_data0_population') is True
            and progress.get('smoke') is False and progress.get('completed_folds') == list(range(5)), 'Need complete full-population control CV')
    require(recipe.get('smoke') is False and recipe['config']['context_mode'] == 'none'
            and recipe['config']['cap'] == 32 and recipe['config']['summary_n'] == 63, 'Wrong model recipe/training cap')
    require(recipe['identity']['data0_input_sha256'] == fitting.DATA0_INPUT_SHA, 'Wrong source dataset')
    require(recipe['identity']['source_sha256'] == fitting.source_hashes(), 'Fitting sources/shared scorer changed')
    require(sha256(args.labels) == recipe['identity']['labels_sha256'] and sha256(args.folds) == recipe['identity']['folds_sha256'], 'Data0 label/fold bytes changed')
    require(sha256(directory/'data0_oof.csv') == progress['oof_sha256']
            and sha256(directory/'data0_cv_metrics.json') == progress['cv_metrics_sha256'], 'Completed CV evidence hashes changed')
    cache = fitting.Cache(args.cache)
    meta = fitting.align_metadata(cache, args.labels, args.folds)
    require(cache.source == recipe['identity']['cache_manifest_sha256'], 'Cache manifest differs from fitted input')
    require(recipe['population_sha256'] == fitting.index_hash(np.arange(len(meta))), 'CV was not fitted on the full original population')
    predictions, assigned = SCORER.read_predictions(directory/'data0_oof.csv', 'data0')
    keys = list(zip(meta.transcript_id.astype(str), meta.transcript_position.astype(int)))
    fold_values = meta.fold_id.to_numpy()
    require(set(keys) == set(predictions) and all(assigned[k] == int(fold_values[i]) for i,k in enumerate(keys)), 'OOF keys/fold assignments differ')
    meta['baseline_score'] = [predictions[key] for key in keys]
    models = []
    for fold in range(5):
        result = fitting.verify_saved_fold(directory, fold)
        fold_dir = directory/f'fold{fold}'
        audit = json.loads((fold_dir/'split_audit.json').read_text())
        _, _, _, _, expected_audit = fitting.partition(meta, np.arange(len(meta)), fold)
        require(audit == expected_audit and audit['zero_gene_overlap'], 'Saved genes/split audit differs')
        inner = json.loads((fold_dir/'inner/complete.json').read_text())
        completed = json.loads((fold_dir/'refit/complete.json').read_text())
        selected = result['selected_epochs']
        require(inner['best_epoch'] == selected and inner['signature'] == _fit_signature(recipe, fold, audit, 'cv_inner', selected), 'Inner selection signature differs')
        model_path = fold_dir/'refit/best.pt'
        model, bundle = network.load_model(model_path, allow_development_model=True)
        validate_bundle(bundle, completed, recipe, fold, audit, selected)
        fold_scores, fold_ids = SCORER.read_predictions(fold_dir/'predictions.csv', 'data0')
        expected_keys = {key for i,key in enumerate(keys) if int(fold_values[i]) == fold}
        require(set(fold_scores) == expected_keys and all(fold_ids[k] == fold and abs(fold_scores[k]-predictions[k]) <= 1e-12 for k in expected_keys), 'Fold and merged OOF differ')
        models.append(dict(fold_id=fold, model_sha256=sha256(model_path), stage=bundle['stage'],
            selected_epochs=selected, fit_signature=bundle['fit_signature'],
            refit_indices_sha256=completed['fit_indices_sha256'],
            split_audit_sha256=sha256(fold_dir/'split_audit.json'), fit_complete_sha256=sha256(fold_dir/'refit/complete.json')))
        del model, bundle
    return cache, meta, recipe, progress, models


def batch_indices(indices, coverage, depth, batch_size, budget):
    """Same coverage order for both all-read controls; bounded padded tensors."""
    pending = []
    maximum = 0
    for index in indices:
        size = int(coverage[index]) if depth == 'all' else int(depth)
        require(size <= budget, 'One site exceeds the padded-read budget; increase it explicitly')
        if pending and (len(pending) == batch_size or (len(pending)+1)*max(maximum,size) > budget):
            yield np.asarray(pending, dtype=np.int64)
            pending, maximum = [], 0
        pending.append(int(index)); maximum = max(maximum, size)
    if pending:
        yield np.asarray(pending, dtype=np.int64)


@torch.inference_mode()
def score_batch(model, cache, indices, meta, specification):
    name, depth = specification['perturbation'], specification['depth']
    precision = None
    if depth == 'all':
        samples = [np.arange(len(cache.bag(i)), dtype=np.int64) for i in indices]
    else:
        samples = [nested_indices(len(cache.bag(i)), int(depth), int(specification['repeat_seed']),
                   meta.iloc[i].transcript_id, int(meta.iloc[i].transcript_position)) for i in indices]
    sample_hashes = [fitting.index_hash(sample) for sample in samples]
    if name == 'all-cache':
        # Original training inference function and original cached summaries.
        values = fitting.predict_cache(model, cache, indices, None, batch_size=len(indices))
        return values, sample_hashes, precision
    if name == 'all-recomputed':
        tensors = list(fitting.batch(cache, indices, None))
        raw_summary = np.stack([summarise(cache.bag(i)) for i in indices])
        differences = np.abs(raw_summary.astype(np.float64)-cache.raw_summary[indices].astype(np.float64))
        precision = dict(max_abs_per_feature=differences.max(0).tolist(), sum_abs_per_feature=differences.sum(0).tolist())
        tensors[3] = torch.from_numpy(network.summary_transform(raw_summary))
    else:
        require(name in ('both', 'bag-only'), 'Unknown perturbation')
        bags = [np.asarray(cache.bag(i)[sample], dtype=np.float32) for i,sample in zip(indices,samples)]
        width = max(map(len,bags))
        reads = np.zeros((len(indices),width,9), dtype=np.float32)
        mask = np.zeros((len(indices),width), dtype=bool)
        for j,bag in enumerate(bags):
            reads[j,:len(bag)] = network.read_transform(bag)
            mask[j,:len(bag)] = True
        summaries = (cache.summary[indices] if name == 'bag-only' else
                     network.summary_transform(np.stack([summarise(bag) for bag in bags])))
        tensors = [torch.from_numpy(x) for x in (reads,mask,cache.seq[indices],summaries)] + [None]
    values = torch.sigmoid(model(*tensors)).cpu().numpy().astype(np.float64)
    require(values.shape == (len(indices),) and np.isfinite(values).all() and ((values>=0)&(values<=1)).all(), 'Invalid frozen-model scores')
    return values, sample_hashes, precision


def metrics_or_undefined(labels, scores):
    labels, scores = np.asarray(labels), np.asarray(scores, dtype=np.float64)
    if set(np.unique(labels)) == {0,1}:
        return dict(ranking_metrics_defined=True, **SCORER.metrics(labels,scores))
    require(set(np.unique(labels)) <= {0,1} and len(labels)>0, 'Invalid labels')
    require(scores.shape == labels.shape and np.isfinite(scores).all() and ((scores>=0)&(scores<=1)).all(), 'Invalid scores')
    positive = scores>=.5
    tn,fp,fn,tp = [int(mask.sum()) for mask in ((labels==0)&~positive,(labels==0)&positive,(labels==1)&~positive,(labels==1)&positive)]
    return dict(ranking_metrics_defined=False, n_sites=len(labels), n_positives=int(labels.sum()),
        roc_auc=None, pr_auc_trapezoid=None, average_precision=None, selection_score=None,
        threshold=.5, tn=tn,fp=fp,fn=fn,tp=tp,precision=tp/(tp+fp) if tp+fp else 0.,
        recall=tp/(tp+fn) if tp+fn else None, explanation='Single-class trial cohort: ranking metrics undefined; selection was not altered using labels.')


def verify_condition_csv(path, cohort, specification):
    frame = pd.read_csv(path, dtype={'transcript_id':str,'depth':str,'repeat_seed':str}, float_precision='round_trip')
    require(list(frame.columns) == HEADER and len(frame) == len(cohort), 'Incomplete/malformed condition CSV')
    for column in ('site_index','transcript_id','transcript_position','gene_id','fold_id','label','coverage','motif','baseline_score'):
        require(np.array_equal(frame[column].to_numpy(),cohort[column].to_numpy()), 'Condition cohort metadata/order differs: '+column)
    depth = specification['depth']
    expected_n = cohort.coverage.to_numpy() if depth == 'all' else np.full(len(cohort),int(depth))
    require(np.array_equal(frame.n_reads_used.to_numpy(),expected_n), 'Condition read depth differs')
    require(frame.perturbation.eq(specification['perturbation']).all()
            and frame.depth.eq(str(depth)).all() and frame.repeat_id.eq(specification['repeat_id']).all()
            and frame.repeat_seed.eq(str(specification['repeat_seed'])).all(), 'Condition identifiers differ')
    require(np.isfinite(frame.score).all() and frame.score.between(0,1).all(), 'Invalid saved probabilities')
    require(frame.sample_indices_sha256.str.fullmatch('[0-9a-f]{64}').all(), 'Missing sample index fingerprints')
    return frame


def run_condition(output, experiment, cohort, cache, meta, model, specification, args):
    fold = specification['fold_id']
    folder = output/'conditions'/specification['condition_id']
    folder.mkdir(parents=True,exist_ok=True)
    identity = dict(**specification, experiment_signature=experiment['signature'],
        cohort_sha256=experiment['cohort_sha256'], model_sha256=experiment['models'][fold]['model_sha256'])
    signature = fingerprint(identity)
    immutable_json(folder/'condition.json',dict(signature=signature,**identity))
    complete_path, csv_path = folder/'complete.json', folder/'predictions.csv'
    if complete_path.exists():
        record = json.loads(complete_path.read_text())
        require(record.get('status') == 'complete' and record.get('signature') == signature
                and record.get('predictions_sha256') == sha256(csv_path), 'Completed condition changed; refusing overwrite')
        verify_condition_csv(csv_path,cohort,specification)
        return record
    if csv_path.exists():
        csv_path.rename(folder/f'predictions.orphan-{time.time_ns()}.csv')
    attempt = str(time.time_ns())
    partial = folder/f'attempt-{attempt}.partial.csv'
    indices = cohort.site_index.to_numpy(dtype=np.int64)
    precision_max, precision_sum = np.zeros(63), np.zeros(63)
    maximum_padded, batches = 0, 0
    measured = Measure()
    try:
        with measured:
            with partial.open('x',newline='',encoding='utf-8') as handle:
                writer=csv.writer(handle,lineterminator='\n');writer.writerow(HEADER)
                try:
                    for selected in batch_indices(indices,meta.n_reads.to_numpy(),specification['depth'],args.batch_size,args.max_padded_reads):
                        probabilities,sample_hashes,precision = score_batch(model,cache,selected,meta,specification)
                        if precision:
                            precision_max=np.maximum(precision_max,precision['max_abs_per_feature'])
                            precision_sum+=precision['sum_abs_per_feature']
                        depth=specification['depth']
                        maximum_padded=max(maximum_padded,len(selected)*(int(meta.iloc[selected].n_reads.max()) if depth=='all' else int(depth)))
                        for index,probability,sample_hash in zip(selected,probabilities,sample_hashes):
                            row=meta.iloc[index]
                            writer.writerow([int(index),row.transcript_id,int(row.transcript_position),row.gene_id,fold,
                                int(row.label),int(row.n_reads),row.context[1:6],int(row.n_reads) if depth=='all' else depth,
                                specification['perturbation'],depth,specification['repeat_id'],specification['repeat_seed'],
                                format(float(probability),'.17g'),format(float(row.baseline_score),'.17g'),sample_hash])
                        batches+=1;handle.flush()
                finally:
                    handle.flush();os.fsync(handle.fileno())
            frame=verify_condition_csv(partial,cohort,specification)
            differences=frame.score.to_numpy()-frame.baseline_score.to_numpy()
            drift=dict(max_absolute=float(np.abs(differences).max()),mean_absolute=float(np.abs(differences).mean()),
                mean_signed=float(differences.mean()),n_threshold_flips=int(((frame.score>=.5)!=(frame.baseline_score>=.5)).sum()))
            if specification['perturbation']=='all-cache':
                require(drift['max_absolute']<=TOLERANCE,'All-cache control differs from saved OOF by more than 1e-6; preserve evidence and inspect grouping/source, never tune tolerance automatically')
            metrics=metrics_or_undefined(frame.label.to_numpy(),frame.score.to_numpy())
        record=dict(status='complete',signature=signature,**identity,predictions_sha256=sha256(partial),
            n_sites=len(frame),n_positives=int(frame.label.sum()),metrics=metrics,score_drift_from_saved_oof=drift,
            resources=measured.record,n_batches=batches,maximum_padded_reads=maximum_padded,
            measurement_scope='One condition inference, summary calculation, CSV write/verification and metrics; model loading/preflight excluded',
            all_control_batching_identical=True if specification['depth']=='all' else None)
        if specification['perturbation']=='all-recomputed':
            record['raw_summary_precision_vs_original_cache']=dict(max_abs_per_feature=precision_max.tolist(),
                mean_abs_per_feature=(precision_sum/len(frame)).tolist(),max_absolute=float(precision_max.max()),
                explanation='Original cached summaries derived from raw float64 JSON; recomputed summaries from retained float32 read cache. Read tensors/order/batches identical to all-cache.')
        require(not csv_path.exists() and not complete_path.exists(),'Condition destination appeared during execution')
        os.replace(partial,csv_path);save_json(complete_path,record)
        save_json(folder/f'attempt-{attempt}.json',dict(status='complete',signature=signature,resources=measured.record))
        return record
    except BaseException as error:
        save_json(folder/f'attempt-{attempt}.json',dict(status='interrupted_or_failed',signature=signature,
            partial_csv=partial.name,error=str(error),resources=getattr(measured,'record',{})))
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=REPO.parent/'advanced_model/cache/data0')
    parser.add_argument('--labels',type=Path,default=REPO.parent/'data0/data.info.labelled')
    parser.add_argument('--folds',type=Path,default=SCORER.DEFAULT_FOLDS)
    parser.add_argument('--cv-dir',type=Path,default=REPO/'model_elgin/outputs/context_reference_v1/cv/none')
    parser.add_argument('--output-dir',type=Path,default=ALLOWED_OUTPUT,
                        help='Experiment parent; creates full/ or trial/. An explicit matching full/trial path is also accepted.')
    parser.add_argument('--depths',default='20,32,50,100');parser.add_argument('--seeds',default='2026,2027,2028')
    parser.add_argument('--perturbation',default='both,bag-only',help='Comma-separated both (primary), bag-only (secondary)')
    parser.add_argument('--threads',type=int,default=4);parser.add_argument('--batch-size',type=int,default=64)
    parser.add_argument('--max-padded-reads',type=int,default=65536)
    parser.add_argument('--trial',action='store_true');parser.add_argument('--trial-genes-per-fold',type=int,default=20)
    parser.add_argument('--trial-sites-per-fold',type=int,default=100)
    args=parser.parse_args(argv)
    depths=tuple(map(int,args.depths.split(',')));seeds=tuple(map(int,args.seeds.split(',')))
    perturbations=tuple(args.perturbation.split(','))
    require(depths and len(set(depths))==len(depths) and set(depths)<=set(DEPTHS),'Depths must be distinct choices from 20,32,50,100')
    require(seeds==SEEDS,'This prespecified experiment uses seeds 2026,2027,2028')
    require(perturbations and len(set(perturbations))==len(perturbations) and set(perturbations)<= {'both','bag-only'},'Unknown perturbation')
    require(args.threads==4 and min(args.batch_size,args.max_padded_reads)>0,'Use four CPU threads and positive batching limits')
    output=args.output_dir.resolve()
    require(output==ALLOWED_OUTPUT.resolve() or output.is_relative_to(ALLOWED_OUTPUT.resolve()),'Outputs must stay under the ignored read_depth_stability_v1 directory')
    run_name='trial' if args.trial else 'full'
    if output.name in ('trial','full'):
        require(output.name==run_name,'Output run name does not match --trial setting')
    else:output=output/run_name
    output.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(args.threads);torch.set_num_interop_threads(1)
    invocation=output/'invocations'/f'invocation-{time.time_ns()}.json'
    with Measure() as total:
        total.output=invocation
        cache,meta,recipe,cv_progress,models=preflight(args)
        cohort=select_cohort(meta,args.trial,args.trial_genes_per_fold,args.trial_sites_per_fold)
        cohort_frame=cohort[COHORT_COLUMNS].reset_index(drop=True)
        cohort_bytes=cohort_frame.to_csv(index=False,float_format='%.17g',lineterminator='\n').encode()
        cohort_hash=hashlib.sha256(cohort_bytes).hexdigest()
        specs=condition_specs(depths,seeds,perturbations)
        experiment=dict(format='read_depth_stability_v1',is_trial=args.trial,minimum_original_coverage=100,
            depths=list(depths),repeat_seeds=list(seeds),perturbations=list(perturbations),models=models,
            expected_condition_ids=[s['condition_id'] for s in specs],cohort_sha256=cohort_hash,
            cohort_sites=len(cohort),cohort_positives=int(cohort.label.sum()),cohort_genes=int(cohort.gene_id.nunique()),
            condition_csv_columns=HEADER,source_fingerprints=recipe['identity'],cv_progress=cv_progress,
            tool_source_sha256=network.source_sha256(__file__),training_recipe_sha256=sha256(args.cv_dir/'recipe.json'),
            settings=dict(threads=args.threads,batch_size=args.batch_size,max_padded_reads=args.max_padded_reads,
                trial_genes_per_fold=args.trial_genes_per_fold if args.trial else None,
                trial_sites_per_fold=args.trial_sites_per_fold if args.trial else None),
            versions=dict(python=platform.python_version(),numpy=np.__version__,torch=str(torch.__version__),pandas=pd.__version__,sklearn=sklearn.__version__),
            inference_method='Original frozen per-outer-fold cv_refit models; no fitting/calibration; raw float32 reads transformed exactly once',
            sampling='PCG64 permutation seeded by SHA256(version,repeat_seed,transcript,position,coverage); sorted nested prefixes without replacement; labels excluded',
            controls='all-cache uses original cached summary and production predict_cache; all-recomputed uses identical production read tensors/batches with float32-cache summaries recomputed',
            all_cache_oof_max_absolute_tolerance=TOLERANCE)
        experiment['signature']=fingerprint(experiment)
        immutable_json(output/'experiment.json',experiment)
        cohort_path=output/'cohort.csv'
        if cohort_path.exists():require(sha256(cohort_path)==cohort_hash,'Existing cohort changed')
        else:
            temporary=output/f'cohort.attempt-{time.time_ns()}.tmp';temporary.write_bytes(cohort_bytes);os.replace(temporary,cohort_path)
        completed=[];receipt_hashes={};current_fold=None;model=None
        for specification in specs:
            fold=specification['fold_id']
            if fold!=current_fold:
                model,_=network.load_model(args.cv_dir/f'fold{fold}/refit/best.pt',allow_development_model=True)
                current_fold=fold
            require(sha256(args.cv_dir/f'fold{fold}/refit/best.pt')==models[fold]['model_sha256'],'Model changed during run')
            require(fitting.source_hashes()==recipe['identity']['source_sha256']
                    and network.source_sha256(__file__)==experiment['tool_source_sha256'],'Source changed during run')
            part=cohort_frame.loc[cohort_frame.fold_id.eq(fold)].reset_index(drop=True)
            record=run_condition(output,experiment,part,cache,meta,model,specification,args)
            completed.append(specification['condition_id'])
            receipt_hashes[specification['condition_id']]=sha256(output/'conditions'/specification['condition_id']/'complete.json')
            progress=dict(experiment_signature=experiment['signature'],is_trial=args.trial,all_completed=False,
                completed_condition_ids=completed,expected_condition_ids=experiment['expected_condition_ids'],complete_receipt_sha256=receipt_hashes)
            save_json(output/'progress.json',progress)
            message=f"Complete {specification['condition_id']}: {record['n_sites']} sites; {len(completed)}/{len(specs)} conditions"
            print(message,flush=True)
            with (output/'run.log').open('a',encoding='utf-8') as handle:handle.write(message+'\n')
        # Complete status only after full payload/model/source revalidation.
        fitting.Cache(args.cache)
        require(fitting.source_hashes()==recipe['identity']['source_sha256'],'Sources changed before completion')
        require(all(sha256(args.cv_dir/f'fold{f}/refit/best.pt')==models[f]['model_sha256'] for f in range(5)),
                'A source model changed before completion')
        progress['all_completed']=True;save_json(output/'progress.json',progress)
        save_json(output/'invocation_arguments.json',dict(arguments=list(sys.argv[1:] if argv is None else argv),
                  purpose='trial pipeline check' if args.trial else 'data0 frozen-model stability diagnostic'))
    print(f"Completed {'TRIAL' if args.trial else 'FULL'} data0 diagnostic: {output}; no training or data1 access",flush=True)


if __name__=='__main__':
    main()
