"""Reproducible data0 OOF error/case review; no fitting, inference or data1."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import time
import platform
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'model_elgin/context_reference_v1'))
import train as fitting
from common import Measure, save_json
from data import sha256
import summarize_context_cv as saved

DEFAULT = REPO / 'model_elgin/outputs/error_case_review_v1'
KEY = ['transcript_id', 'transcript_position']
FEATURES = ['minus1_dwell', 'minus1_event_sd', 'minus1_current',
            'centre_dwell', 'centre_event_sd', 'centre_current',
            'plus1_dwell', 'plus1_event_sd', 'plus1_current']
PAIR_FEATURES = [*FEATURES, 'centre_current_iqr', 'centre_dwell_iqr', 'centre_event_sd_iqr']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def error_labels(labels, scores):
    y, p = np.asarray(labels), np.asarray(scores, dtype=float)
    require(y.shape == p.shape and np.isin(y, [0, 1]).all()
            and np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all(), 'Invalid labels/scores')
    return np.where(y == 1, np.where(p >= .5, 'TP', 'FN'), np.where(p >= .5, 'FP', 'TN'))


def match_site(meta, anchor, mask, minimum=0):
    """Hierarchical context matching; no raw signal values enter this ranking."""
    row = meta.loc[anchor]
    candidates = meta.loc[mask & meta.fold_id.eq(row.fold_id)
        & meta.gene_id.ne(row.gene_id) & meta.n_reads.ge(minimum)
        & meta.n_reads.ge(row.n_reads / 2) & meta.n_reads.le(row.n_reads * 2)
        & meta.motif.eq(row.motif)].copy()
    if candidates.empty:
        return None, 'unmatched'
    exact = candidates.context.eq(row.context)
    if exact.any():
        candidates = candidates.loc[exact]
        level = 'exact7'
    else:
        level = 'central5'
    candidates['distance'] = np.abs(np.log(candidates.n_reads / row.n_reads))
    chosen = candidates.sort_values(['distance', *KEY], kind='stable').index[0]
    return int(chosen), level


def case_anchors(meta):
    high = meta.loc[meta.n_reads.ge(200)]
    counts = high.loc[high.label.eq(1)].groupby('motif').size().reset_index(name='positives')
    motifs = counts.sort_values(['positives', 'motif'], ascending=[False, True]).head(4).motif.tolist()
    result = []
    for motif in motifs:
        eligible = high.loc[high.motif.eq(motif) & high.error.eq('FN')].copy()
        if eligible.empty:
            result.append((motif, None))
            continue
        eligible['distance'] = np.abs(eligible.score - eligible.score.median())
        result.append((motif, int(eligible.sort_values(['distance', *KEY], kind='stable').index[0])))
    return result


def load(args):
    evidence = {}
    run = REPO / 'model_elgin/outputs/context_reference_v1'
    cv = saved.load_mode(run / 'cv', 'none', evidence)
    require(cv['recipe']['identity']['source_sha256'] == fitting.source_hashes(), 'Frozen source changed')
    cache = fitting.Cache(args.cache)
    require(cache.source == cv['recipe']['identity']['cache_manifest_sha256'], 'Wrong CV cache')
    require(sha256(args.labels) == cv['recipe']['identity']['labels_sha256'], 'Wrong label source')
    meta = fitting.align_metadata(cache, args.labels, args.folds)
    meta['site_index'] = np.arange(len(meta))
    oof = pd.read_csv(run / 'cv/none/data0_oof.csv', float_precision='round_trip')
    require(not oof.duplicated(KEY).any(), 'Duplicate OOF site')
    meta = meta.merge(oof, on=[*KEY, 'fold_id'], how='left', validate='one_to_one').set_index('site_index')
    require(len(meta) == 121838 and meta.score.notna().all(), 'Incomplete OOF alignment')
    require(int(meta.label.sum()) == 5475, 'Unexpected positive count')
    meta['motif'] = meta.context.str[1:6]
    meta['error'] = error_labels(meta.label, meta.score)
    for j, name in enumerate(FEATURES):
        meta[name] = cache.raw_summary[:, 36+j]
    for col, name in [(3, 'centre_dwell_iqr'), (4, 'centre_event_sd_iqr'), (5, 'centre_current_iqr')]:
        meta[name] = cache.raw_summary[:, 45+col] - cache.raw_summary[:, 27+col]
    diagnostic = run / 'diagnostics'
    manifest = json.loads((diagnostic / 'diagnostics_manifest.json').read_text())
    # Validate prior flags against their original report receipt before using them.
    flag_path = diagnostic / 'site_flags.csv'
    require(sha256(flag_path) == manifest['output_sha256']['site_flags.csv'], 'Changed prior flags')
    flags = pd.read_csv(flag_path)
    require(not flags.duplicated(KEY).any(), 'Duplicate prior flags')
    meta = meta.reset_index().merge(flags[[*KEY, 'unusual_flag']], on=KEY,
        how='left', validate='one_to_one').set_index('site_index')
    require(np.array_equal(meta.index, np.arange(len(meta))), 'Cache/metadata ordering changed')
    require(meta.unusual_flag.notna().all(), 'Incomplete prior flags')
    member = pd.read_csv(args.member1)
    member = member.loc[member.dataset.eq('data0')].copy()
    named = member.merge(meta.reset_index(), on=KEY, suffixes=('_eda', ''), validate='many_to_one')
    require(len(named) == len(member), 'A Member1 data0 site is absent')
    require(np.array_equal(named.coverage, named.n_reads) and
            np.array_equal(named.label_eda, named.label) and
            np.array_equal(named.sequence, named.context), 'Member1 metadata disagreement')
    named['cached_iqr'] = [float(meta.loc[r.site_index, r.ranking_feature]) for r in named.itertuples()]
    named['cache_minus_member1_iqr'] = named.cached_iqr - named.value
    inputs = {f'cv/{k}': v for k, v in evidence.items()}
    inputs.update({'cache/manifest.json': cache.source, 'labels': sha256(args.labels),
        'folds': sha256(args.folds), 'member1': sha256(args.member1),
        'prior_flags': sha256(flag_path), 'prior_diagnostic_manifest': sha256(diagnostic / 'diagnostics_manifest.json')})
    return cache, meta, named, inputs, cv


def population_tables(meta):
    tables = []
    for scope, sub in [('all_data0', meta), ('coverage_200plus', meta.loc[meta.n_reads.ge(200)])]:
        for motif, group in sub.groupby('motif', sort=True):
            counts = group.error.value_counts()
            row = dict(scope=scope, motif=motif, sites=len(group), positives=int(group.label.sum()),
                       median_coverage=float(group.n_reads.median()), flagged=int(group.unusual_flag.sum()))
            row.update({k: int(counts.get(k, 0)) for k in ['TP', 'FN', 'FP', 'TN']})
            row['recall_at_0_5'] = row['TP'] / row['positives'] if row['positives'] else np.nan
            row['median_positive_score'] = float(group.loc[group.label.eq(1), 'score'].median())
            tables.append(row)
    return pd.DataFrame(tables)


def pairs(meta):
    result = []
    for index, anchor in meta.loc[meta.n_reads.ge(200) & meta.error.eq('FN')].iterrows():
        target, level = match_site(meta, index, meta.error.eq('TP'), 200)
        row = dict(anchor_index=int(index), comparator_index=target, match_level=level,
                   motif=anchor.motif, fold_id=int(anchor.fold_id))
        if target is not None:
            other = meta.loc[target]
            row.update(coverage_ratio=float(other.n_reads / anchor.n_reads),
                       anchor_score=float(anchor.score), comparator_score=float(other.score))
            row.update({name: float(anchor[name] - other[name]) for name in PAIR_FEATURES})
        result.append(row)
    table = pd.DataFrame(result, columns=['anchor_index', 'comparator_index', 'match_level',
        'motif', 'fold_id', 'coverage_ratio', 'anchor_score', 'comparator_score', *PAIR_FEATURES])
    summaries = []
    for scope, sub in [('all_matches', table.loc[table.match_level.ne('unmatched')]),
                       ('exact7_only', table.loc[table.match_level.eq('exact7')])]:
        for name in PAIR_FEATURES:
            values = sub[name].dropna().to_numpy(float)
            if len(values):
                q25, med, q75 = np.quantile(values, [.25, .5, .75])
                summaries.append(dict(scope=scope, feature=name, pairs=len(values),
                    unique_comparators=int(sub.comparator_index.nunique()), median_fn_minus_tp=med,
                    q25=q25, q75=q75, fraction_fn_greater=float((values > 0).mean())))
    return table, pd.DataFrame(summaries, columns=['scope', 'feature', 'pairs', 'unique_comparators',
        'median_fn_minus_tp', 'q25', 'q75', 'fraction_fn_greater'])


def select_cases(meta, named):
    result, missing = [], []
    for motif, index in case_anchors(meta):
        if index is None:
            missing.append(f'Top-count motif {motif} has no FN at 0.5; no substitute.')
            continue
        entries = [('missed positive', index, 'anchor')]
        for kind in ['TP', 'TN']:
            target, level = match_site(meta, index, meta.error.eq(kind), 200)
            if target is None:
                missing.append(f'{motif} {kind} comparator unavailable under fixed rules.')
            else:
                entries.append((kind + ' comparator', target, level))
        result.append((f'high_depth_{motif}', entries))
    # Member1's two explicitly named data0 cases, plus the fixed highest-coverage examples.
    unusual = [('handoff_TGACT', int(named.loc[named.transcript_id.eq('ENST00000592107') &
        named.transcript_position.eq(370), 'site_index'].iloc[0]), 'centre_current_iqr'),
        ('handoff_GAACA', int(named.loc[named.transcript_id.eq('ENST00000369075') &
        named.transcript_position.eq(3059), 'site_index'].iloc[0]), 'centre_current_iqr')]
    for feature in ['centre_current_iqr', 'centre_dwell_iqr']:
        chosen = named.loc[named.ranking_feature.eq(feature)].sort_values(
            ['n_reads', *KEY], ascending=[False, True, True]).iloc[0]
        unusual.append((feature, int(chosen.site_index), feature))
    named_indices = set(named.site_index)
    for name, index, feature in unusual:
        anchor = meta.loc[index]
        mask = meta.label.eq(anchor.label) & ~meta.index.isin(named_indices) & ~meta.unusual_flag
        # Restrict the reference median to otherwise eligible same-fold/context/coverage sites.
        pool = meta.loc[mask & meta.fold_id.eq(anchor.fold_id) & meta.gene_id.ne(anchor.gene_id)
            & meta.motif.eq(anchor.motif) & meta.n_reads.between(anchor.n_reads / 2, anchor.n_reads * 2)]
        # Exact-context ordinary eligibility must not be defined by a different-context median.
        if pool.context.eq(anchor.context).any():
            pool = pool.loc[pool.context.eq(anchor.context)]
        ordinary = mask & meta.index.isin(pool.index) & meta[feature].le(pool[feature].median())
        target, level = match_site(meta, index, ordinary)
        entries = [('Member1 unusual', index, 'anchor')]
        if target is None:
            missing.append(name + ': ordinary comparator unavailable under fixed rules.')
        else:
            entries.append(('ordinary comparator', target, level))
        result.append(('unusual_' + name, entries))
    return result, missing


def case_plots(cache, meta, cases, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    records, read_stats = [], []
    for name, entries in cases:
        fig, axes = plt.subplots(2, 3, figsize=(13, 7.5))
        fig.suptitle(name.replace('_', ' ') + '\nRaw cached reads; site labels, fixed 0.5 reporting cutoff', fontsize=13)
        for slot, (role, index, level) in enumerate(entries):
            row = meta.loc[index]
            bag = np.asarray(cache.bag(index), dtype=float)
            require(bag.shape == (row.n_reads, 9) and np.isfinite(bag).all(), 'Invalid case read bag')
            label = f'{role}: {row.context}, n={row.n_reads}, y={row.label}, score={row.score:.3f}'
            colour = ['#bc3f3f', '#247d95', '#6d9444'][slot]
            records.append(dict(case=name, role=role, match_level=level, site_index=index,
                **{k: row[k] for k in [*KEY, 'gene_id', 'fold_id', 'context', 'motif',
                                       'n_reads', 'label', 'score', 'error', 'unusual_flag']}))
            for col, title, ax in [(5, 'Central mean-current value', axes[0, 0]),
                                    (4, 'Central event-SD value', axes[0, 1]),
                                    (3, 'Central dwell value', axes[0, 2])]:
                values = np.sort(bag[:, col])
                ax.step(values, np.arange(1, len(values)+1) / len(values), where='post', color=colour, label=label)
                if len(values) < 50:
                    ax.plot(values, np.full(len(values), .015*(slot+1)), '|', color=colour, alpha=.65)
                ax.set(xlabel=title + ' (supplied scale)', ylabel='Fraction of reads at or below value', ylim=(0, 1.03))
                q05, q25, med, q75, q95 = np.quantile(values, [.05, .25, .5, .75, .95])
                read_stats.append(dict(case=name, role=role, feature=FEATURES[col], n_reads=len(values),
                    minimum=float(values[0]), q05=q05, q25=q25, median=med, q75=q75, q95=q95,
                    maximum=float(values[-1]), iqr=q75-q25))
            for ax, col, title in [(axes[1, 0], 2, 'Minus-one mean-current'),
                                    (axes[1, 1], 8, 'Plus-one mean-current')]:
                ax.scatter(bag[:, col], bag[:, 5], s=9, alpha=.28, c=colour, rasterized=True)
                ax.set(xlabel=title + ' (supplied scale)', ylabel='Central mean-current (supplied scale)')
        axes[1, 2].axis('off')
        note = []
        for role, index, level in entries:
            row = meta.loc[index]
            note.extend([f'{role} [{level}]', f'{row.transcript_id}:{row.transcript_position}',
                         f'fold {row.fold_id}; {row.context}; n={row.n_reads}',
                         f'label {row.label}; {row.error}; score {row.score:.4f}', ''])
        axes[1, 2].text(0, 1, '\n'.join(note), va='top', fontsize=9)
        handles, labels = axes[0, 0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='lower center', fontsize=8, ncol=1)
        fig.tight_layout(rect=(0, .105, 1, .92))
        fig.savefig(output / (name + '.png'), dpi=140, bbox_inches='tight', pad_inches=.15)
        plt.close(fig)
    return pd.DataFrame(records), pd.DataFrame(read_stats)


def overview_plot(population, output):
    import matplotlib.pyplot as plt
    data = population.loc[population.scope.eq('coverage_200plus')].sort_values('positives', ascending=False)
    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(data))
    ax.bar(x, data.TP, label='Detected positive label (TP)', color='#247d95')
    ax.bar(x, data.FN, bottom=data.TP, label='Missed positive label (FN)', color='#bc3f3f')
    ax.set(xticks=x, xticklabels=data.motif, ylabel='Number of positive-labelled sites',
           title='Data0 coverage >=200: errors at the existing 0.5 reporting cutoff')
    ax.tick_params(axis='x', labelrotation=55)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / 'high_depth_positive_errors.png', dpi=150)
    plt.close(fig)


def report(meta, named, population, paired, differences, cases, missing, resources, output):
    high = meta.loc[meta.n_reads.ge(200)]
    nfn = int(high.error.eq('FN').sum())
    tp = int(high.error.eq('TP').sum())
    matched = paired.loc[paired.match_level.ne('unmatched')]
    high_table = population.loc[population.scope.eq('coverage_200plus')].sort_values(
        ['positives', 'motif'], ascending=[False, True])
    lines = ['# Data0 signal-case review: actual results', '',
        '**Completed descriptive analysis; no training, inference, data1 signal/label files or cutoff selection.**', '',
        f'The verified original-feature OOF scores cover {len(meta):,} sites and {int(meta.label.sum()):,} positive site labels. '
        f'The >=200-read group has {len(high):,} sites, {int(high.label.sum())} positives, '
        f'{tp} TP and {nfn} FN at the existing 0.5 reporting cutoff (recall {tp/(tp+nfn):.3f}). '
        'The cutoff is not a validated biological rule. The full five-fold model score remains **S=0.717642**; '
        'these case plots do not establish a new improvement.', '',
        '## Context and coverage matching', '',
        f'Among all {nfn} high-depth FNs, {len(matched)} have an eligible TP comparator; '
        f'{int(paired.match_level.eq("exact7").sum())} exact7, '
        f'{int(paired.match_level.eq("central5").sum())} central5 fallback, '
        f'{int(paired.match_level.eq("unmatched").sum())} unmatched. '
        f'{int(matched.comparator_index.nunique())} distinct TP comparators are reused with replacement. '
        'Matches share the saved model/fold, use different genes and >=200 reads, and differ by at most 2x coverage. '
        'Exact7 is preferred before coverage proximity; central5 fallback leaves flank differences.', '',
        '| Central5 | Sites | Positive labels | TP | FN | Recall at 0.5 |',
        '|---|---:|---:|---:|---:|---:|']
    for row in high_table.itertuples():
        recall = f'{row.recall_at_0_5:.3f}' if np.isfinite(row.recall_at_0_5) else 'undefined'
        lines.append(f'| {row.motif} | {row.sites} | {row.positives} | {row.TP} | {row.FN} | {recall} |')
    lines += ['', '![All high-depth positive labels](high_depth_positive_errors.png)', '',
        'Paired raw summary differences below are FN minus TP, with one pair per matched FN. '
        'They describe selected errors, not a new predictor, causal effect or significance test. '
        'Reads, reused comparators, genes and folds are not independent biological replicates.', '',
        '| Scope | Feature | Pairs | Median difference | Pair-difference Q25 / Q75 | FN greater fraction |',
        '|---|---|---:|---:|---:|---:|']
    for row in differences.loc[differences.feature.isin(['centre_current', 'centre_event_sd', 'centre_dwell',
                                                        'centre_current_iqr', 'centre_dwell_iqr'])].itertuples():
        lines.append(f'| {row.scope} | {row.feature} | {row.pairs} | {row.median_fn_minus_tp:.6g} | '
                     f'{row.q25:.6g} / {row.q75:.6g} | {row.fraction_fn_greater:.3f} |')
    lines += ['', '## Fixed representative cases', '',
        'One FN nearest its own motif FN median score was selected for each of the four motifs with most '
        'high-depth positive labels. TP and TN matches follow the prespecified rule. Examples are '
        'illustrative and were not selected for visual separation. Full local case-selection CSV records '
        'keys, folds, context, coverage and classification. All reads are plotted; lower-depth panels include rugs.', '']
    for name, _ in cases:
        if name.startswith('high_depth'):
            lines += [f'![{name}]({name}.png)', '']
    max_difference = float(named.cache_minus_member1_iqr.abs().max())
    lines += ['## Member 1 unusual valid sites', '',
        f'All {len(named)} received data0 review entries were joined to raw cache/labels/OOF scores; '
        f'{named.site_index.nunique()} distinct sites. Maximum absolute cached-IQR minus original '
        f'Member1-IQR difference is {max_difference:.8g} on supplied feature scales (float32 cache versus '
        'source calculations). Metadata, labels and coverage agree. No entry was discarded or relabelled.', '',
        'The two explicitly named handoff cases (28 and 29 reads) are reviewed separately from the >=200 cohort. '
        'Additional panels use the greatest-coverage received data0 review example for each named IQR feature. '
        'Ordinary comparators have the same site label and fold, another gene, matching sequence/coverage, '
        'no prior median-fence flag, and relevant IQR at or below their candidate pool median. '
        'They were not required to be classified correctly. A broad spread does not prove a mixture, '
        'another RNA modification or faulty reads; molecular labels and alignments are unavailable.', '']
    for name, _ in cases:
        if name.startswith('unusual'):
            lines += [f'![{name}]({name}.png)', '']
    lines += ['## Missing support', ''] + (['- '+x for x in missing] if missing else ['All prespecified illustrative matches were available.'])
    exact = differences.loc[differences.scope.eq('exact7_only')].set_index('feature')
    if not exact.empty:
        current = exact.loc['centre_current']
        spread = exact.loc['centre_current_iqr']
        lines += ['', '## What the measured patterns suggest', '',
            f'In the {int(current.pairs)} exact-7mer matched pairs, FN central-current medians exceed '
            f'TP medians in {current.fraction_fn_greater:.1%} of pairs; median difference '
            f'{current.median_fn_minus_tp:.6g} on the supplied scale. Central-current IQR is greater '
            f'in only {spread.fraction_fn_greater:.1%}, with median difference '
            f'{spread.median_fn_minus_tp:.6g}. The missed positives are therefore not uniformly '
            'broader-spread cases. The 38 exact-context pairs are a selected, limited-support '
            'subset and do not explain all high-depth errors.', '',
            'All four illustrative high-depth TP matches required central5 fallback; their flank bases '
            'differ from their anchors. Their plots cannot isolate a pure signal effect while holding '
            'the complete neural sequence input constant. The all-FN exact7 summary above provides '
            'the stronger context-controlled descriptive evidence.', '']
    lines += ['', '## Interpretation and next modelling decision', '',
        'This completes the bounded error inspection that follows Member1 EDA. Sequence, coverage and '
        'valid within-site spread are represented explicitly in the evidence. Descriptive error-conditioned '
        'contrasts cannot establish the cause of a missed label. Do not delete sites, add a hand-coded '
        'motif rule, force a better score, or interpret site scores as molecular modification fractions.', '',
        'Retain all-read inference. Any next trained candidate should change one mechanism and use the '
        'same full data0 gene-fold comparison. The required simple baseline and published m6Anet benchmark, '
        'final nomination/refit, data0-only cutoff validation, frozen exposed-data1 evaluation and real '
        'SG-NEx predictions/analysis remain pending; this investigation does not complete those tasks.', '',
        'Recommended next neural hypothesis: increase the training read-branch cap from 32 to 128, '
        'keeping original features, loss, splits, stopping and all-read inference unchanged. This lets '
        'the branch learn from larger samples of each site distribution. It is motivated by the saved '
        'training/inference mismatch and completed depth study; the case plots do not prove this '
        'mechanism caused the errors. No gain is promised and no such candidate has been trained. '
        'Compare by the full-data0 shared S, retaining results even if worse. Threshold validation '
        'is a separate data0-inner-gene task and can change recall/precision without improving ranking.', '',
        '## Reproduction, resources and limits', '',
        'From the repository root, with the original local data0 cache, canonical labels/shared folds '
        'and completed control CV bundles:', '', '```powershell',
        '../advanced_model/.venv/Scripts/python.exe -B -u model_elgin/tools/review_signal_cases.py', '```', '',
        'Dependencies use the retained advanced-model environment (NumPy, pandas, PyTorch, scikit-learn, '
        'psutil and matplotlib); their actual versions and input/output hashes are in run_manifest.json. '
        'Full case/pair/raw-summary CSVs stay in ignored outputs/error_case_review_v1. '
        'A deterministic interrupted run can be rerun; invocation records distinguish failures and completion.', '',
        f'Measured analysis wall {resources["wall_seconds"]:.3f} s; process CPU '
        f'{resources["cpu_seconds"]:.3f} s; sampled peak process-tree RSS '
        f'{resources["sampled_peak_process_tree_rss_mib"]:.1f} MiB (0.2 s sampling). '
        'Timing includes input validation, statistics and figure/table generation after imports; excludes '
        'this final report/manifest write. No GPU/cloud training occurred.', '',
        'The existing architecture and prior features were selected during development. OOF errors '
        'are useful for generating hypotheses, but further changes evaluated on these same groups '
        'remain development comparisons. Units are retained as supplied scales because physical-unit '
        'provenance has not been verified. Gene/sequence/coverage matching does not remove all confounding. '
        'The received multi-dataset Member1 review table was read and filtered to data0 entries; '
        'no data1 signal/label file or data1 evaluation was used.', '']
    (output / 'report.md').write_text('\n'.join(lines), encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=REPO.parent/'advanced_model/cache/data0')
    parser.add_argument('--labels', type=Path, default=REPO.parent/'data0/data.info.labelled')
    parser.add_argument('--folds', type=Path, default=REPO/'eda/received/shared_folds/data0_folds.csv')
    parser.add_argument('--member1', type=Path, default=REPO/'eda/received/tables/unusual_sites_review.csv')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT)
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    require(output.is_relative_to(DEFAULT.resolve()), 'Output must stay in dedicated ignored investigation directory')
    output.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR', str(output / '.matplotlib'))
    stamp = str(time.time_ns())
    status = output / 'run_status.json'
    save_json(status, dict(status='running', invocation=stamp))
    try:
        execute(args, output, stamp)
    except BaseException as error:
        save_json(status, dict(status='failed_or_interrupted', invocation=stamp,
                              error=type(error).__name__ + ': ' + str(error)))
        raise
    save_json(status, dict(status='complete', invocation=stamp,
                           manifest_sha256=sha256(output / 'run_manifest.json')))


def execute(args, output, stamp):
    with Measure() as measured:
        measured.output = output / ('invocation_' + stamp + '.json')
        print('Validating immutable data0 cache, gene folds, OOF and EDA evidence...', flush=True)
        cache, meta, named, inputs, cv = load(args)
        print('Summarising high-coverage errors and deterministic context matches...', flush=True)
        population = population_tables(meta)
        paired, differences = pairs(meta)
        cases, missing = select_cases(meta, named)
        for case, entries in cases:
            print(f'{case}: {len(entries)} sites', flush=True)
        case_table, read_stats = case_plots(cache, meta, cases, output)
        overview_plot(population, output)
        for name, table in [('motif_error_counts', population), ('matched_fn_tp_pairs', paired),
            ('paired_feature_differences', differences), ('member1_case_audit', named),
            ('selected_cases', case_table), ('case_read_statistics', read_stats)]:
            table.to_csv(output / (name + '.csv'), index=False, lineterminator='\n')
    report(meta, named, population, paired, differences, cases, missing, measured.record, output)
    files = [p for p in output.iterdir() if p.suffix in ['.csv', '.png'] or p.name == 'report.md']
    save_json(output / 'run_manifest.json', dict(status='complete', data_scope='data0_only',
        fitting=False, model_inference=False, threshold_selection=False, cutoff_reporting_only=.5,
        source_sha256={Path(__file__).name: sha256(__file__), 'SIGNAL_CASE_REVIEW.md': sha256(REPO/'model_elgin/SIGNAL_CASE_REVIEW.md')},
        inputs_sha256=inputs, frozen_model_full_cv_score=cv['metrics']['primary_score'],
        output_sha256={p.name: sha256(p) for p in files}, resources=measured.record,
        versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                      torch=fitting.torch.__version__, sklearn=fitting.sklearn.__version__),
        command=sys.argv, missing_support=missing))
    print('Completed: ' + str(output / 'report.md'), flush=True)


if __name__ == '__main__':
    main()
