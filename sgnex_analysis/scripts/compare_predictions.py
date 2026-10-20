"""Reproducible exploratory comparison of REAL frozen-model run predictions.

No training or significance/stoichiometry estimation is performed here.
Use --help and README.md. Outputs contain all eligible sites, not only hits.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

KEYS=['transcript_id','transcript_position']


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()


def validate_scores(df):
    if list(df.columns)!=KEYS+['score']:
        raise ValueError('Prediction columns must be exactly transcript_id,transcript_position,score')
    if df.empty:raise ValueError('Empty prediction file')
    if df[KEYS].isna().any().any():raise ValueError('Missing site key')
    pos=pd.to_numeric(df.transcript_position,errors='raise')
    if not (np.isfinite(pos).all() and (pos>=0).all() and (pos%1==0).all()):
        raise ValueError('Positions must be finite nonnegative integers')
    df=df.copy();df['transcript_position']=pos.astype('int64')
    score=pd.to_numeric(df.score,errors='raise')
    if not (np.isfinite(score).all() and score.between(0,1).all()):
        raise ValueError('Scores must be finite and within [0,1]')
    df['score']=score
    if df[KEYS].duplicated().any():raise ValueError('Duplicate site keys')
    return df


def aggregate_run_scores(long):
    """One site/replicate mean over eligible runs, then equal replicate weights."""
    df=long.copy();df['log_reads']=np.log(df.n_reads)
    rep=df.groupby(KEYS+['cell_line','biological_replicate'],as_index=False).agg(
        score=('score','mean'),n_runs=('run_id','nunique'),
        technical_score_min=('score','min'),technical_score_max=('score','max'),
        log_reads=('log_reads','mean'))
    cell=rep.groupby(KEYS+['cell_line'],as_index=False).agg(
        score=('score','mean'),n_replicates=('biological_replicate','nunique'),
        score_min=('score','min'),score_max=('score','max'),
        log_reads=('log_reads','mean'),n_eligible_runs=('n_runs','sum'))
    cell['geometric_mean_reads']=np.exp(cell.log_reads)
    return rep,cell


def compare_pair(a,b):
    merged=a.merge(b,on=KEYS,how='inner',suffixes=('_a','_b'),validate='one_to_one')
    merged['delta_score']=merged.score_a-merged.score_b
    merged['coverage_ratio']=np.exp(abs(merged.log_reads_a-merged.log_reads_b))
    merged['all_replicate_pairs_positive']=merged.score_min_a > merged.score_max_b
    merged['all_replicate_pairs_negative']=merged.score_max_a < merged.score_min_b
    return merged


def concordance(table, unit, coverage):
    records=[]
    labels=table[unit].drop_duplicates().tolist()
    for u,v in itertools.combinations(labels,2):
        a=table[table[unit].eq(u)][KEYS+['score']]
        b=table[table[unit].eq(v)][KEYS+['score']]
        m=a.merge(b,on=KEYS,suffixes=('_a','_b'),validate='one_to_one')
        r=float(spearmanr(m.score_a,m.score_b).statistic) if len(m)>=3 and m.score_a.nunique()>1 and m.score_b.nunique()>1 else None
        records.append({'coverage_threshold':coverage,'unit':unit,'a':u,'b':v,'n_common_sites':len(m),'spearman':r,
            'median_absolute_delta':float((m.score_a-m.score_b).abs().median()) if len(m) else None})
    return records


def main(args):
    manifest=Path(args.manifest).resolve();root=manifest.parent
    out=Path(args.out);out.mkdir(exist_ok=False,parents=True)
    m=pd.read_csv(manifest,keep_default_na=False)
    # Exact core fields proposed in the team's README. Extra verification
    # columns remain supported but are not required for interoperability.
    required=['run_id','cell_line','biological_replicate','sequencing_run',
              'prediction_file','coverage_file','min_reads','reference_version','model_version']
    if not set(required).issubset(m):raise ValueError('Missing manifest fields: '+str(set(required)-set(m)))
    if m.empty:raise ValueError('Empty run manifest')
    if m[required].astype(str).apply(lambda c:c.str.strip().eq('').any()).any():
        raise ValueError('Blank required manifest field')
    if m.run_id.duplicated().any():raise ValueError('Duplicate run IDs')
    if 'real_predictions' in m:
        if not m.real_predictions.astype(str).str.lower().eq('true').all():
            raise ValueError('Real-prediction declaration is missing; simulated data refused')
    elif not args.confirm_real_predictions:
        raise ValueError('Review MODEL_INFO.md, then declare real inputs with --confirm-real-predictions; simulated data refused')
    version_fields=['model_version','reference_version']
    if 'coordinate_convention' in m:version_fields.append('coordinate_convention')
    for col in version_fields:
        values=m[col].astype(str)
        if values.nunique()!=1 or values.str.contains('PENDING|placeholder|simulated|sim-v',case=False,regex=True).any():
            raise ValueError(f'{col}: needs one documented, identical real version across runs')
    model_info=Path(args.model_info).resolve() if args.model_info else root/'MODEL_INFO.md'
    if not model_info.is_file() or not model_info.read_text().strip():
        raise ValueError('MODEL_INFO.md is required beside the manifest, or pass --model-info')
    for row in m.itertuples():
        declared_coverage=(root/str(row.coverage_file)).resolve()
        if declared_coverage != Path(args.coverage_matrix).resolve():
            raise ValueError(f'{row.run_id}: coverage_file does not match --coverage-matrix; this adapter uses the documented wide run-column matrix')
    if args.min_replicates<2:raise ValueError('At least two independent replicate groups required')
    thresholds=[int(x) for x in args.coverage.split(',')]
    if min(thresholds)<20 or min(thresholds)<pd.to_numeric(m.min_reads).max():raise ValueError('Unsupported coverage threshold')
    cutoffs=[float(x) for x in args.cutoffs.split(',')]
    if any(t<0 or t>1 for t in cutoffs):raise ValueError('Invalid cutoff')
    cov=pd.read_csv(args.coverage_matrix);ann=pd.read_csv(args.annotations,keep_default_na=False)
    if cov[KEYS].duplicated().any() or ann[KEYS].duplicated().any():raise ValueError('Duplicate coverage/annotation keys')
    if not set(m.run_id).issubset(cov.columns):raise ValueError('Run missing from coverage matrix')
    aliases=pd.read_csv(args.aliases,keep_default_na=False) if args.aliases else None
    receipts=[];frames=[];availability=[]
    for row in m.itertuples():
        f=(root/row.prediction_file).resolve()
        if 'placeholder' in str(f).lower() or 'simulated' in str(f).lower():raise ValueError('Simulated source path refused')
        d=validate_scores(pd.read_csv(f))
        if aliases is not None:
            a=aliases[aliases.run_id.eq(row.run_id)]
            if a.raw_transcript_id.duplicated().any():raise ValueError('Ambiguous alias map')
            remap=dict(zip(a.raw_transcript_id,a.transcript_id));d['transcript_id']=d.transcript_id.replace(remap)
            if d[KEYS].duplicated().any():raise ValueError('Aliases collapse distinct site keys')
        c=cov[KEYS+[row.run_id]].rename(columns={row.run_id:'n_reads'})
        check=d.merge(c,on=KEYS,how='left',validate='one_to_one')
        if check.n_reads.isna().any() or check.n_reads.lt(20).any():
            raise ValueError(f'{row.run_id}: input contains unmatched/<20-read sites; export the documented >=20-read Task 2 table')
        expected=int(c.n_reads.ge(int(row.min_reads)).sum())
        missing=c.loc[c.n_reads.ge(int(row.min_reads)),KEYS].merge(d[KEYS],on=KEYS,how='left',indicator=True)
        missing_count=int(missing['_merge'].eq('left_only').sum())
        availability.append({'run_id':row.run_id,'expected_sites':expected,'predicted_sites':len(d),'missing_predictions':missing_count})
        if missing_count and not args.allow_missing_predictions:raise ValueError(f'{row.run_id}: {missing_count} expected sites unscored')
        check=check.merge(ann,on=KEYS,validate='one_to_one',how='left')
        if check.kind.isna().any():raise ValueError('Missing annotation')
        check['run_id']=row.run_id;check['cell_line']=row.cell_line;check['biological_replicate']=row.biological_replicate
        frames.append(check);receipts.append({'run_id':row.run_id,'path':row.prediction_file,'sha256':sha(f)})
    allrows=pd.concat(frames,ignore_index=True)
    pd.DataFrame(availability).to_csv(out/'prediction_availability.csv',index=False)
    controls=allrows[allrows.kind.ne('annotated')].copy()
    if len(controls):
        controls.assign(high=controls.score.ge(.5)).groupby(['run_id','kind'],as_index=False).agg(n_sites=('score','size'),mean_score=('score','mean'),fraction_ge05=('high','mean')).to_csv(out/'nonprimary_reference_diagnostics.csv',index=False)
    long=allrows[allrows.kind.eq('annotated')].copy()
    annotation_cols=KEYS+['gene_id','gene_name']+(['motif_5mer'] if 'motif_5mer' in ann else [])
    common_summary=[];pair_summary=[];call_summary=[];agreement=[];coverage_dependence=[]
    lines=sorted(m.cell_line.unique());pair_dir=out/'pairs';pair_dir.mkdir()
    for depth in thresholds:
        eligible=long[long.n_reads.ge(depth)]
        rep,cell=aggregate_run_scores(eligible)
        rep.to_csv(out/f'replicate_scores_cov{depth}.csv.gz',index=False)
        agreement+=concordance(eligible, 'run_id', depth)
        rep['replicate_id']=rep.cell_line.astype(str)+':rep'+rep.biological_replicate.astype(str)
        agreement+=concordance(rep,'replicate_id',depth)
        for row in eligible.groupby('run_id'):
            run,d=row
            rho=float(spearmanr(d.n_reads,d.score).statistic) if len(d)>=3 and d.n_reads.nunique()>1 and d.score.nunique()>1 else None
            coverage_dependence.append({'run_id':run,'coverage_threshold':depth,'n_sites':len(d),'spearman_score_vs_reads':rho})
        eligible_cell=cell[cell.n_replicates.ge(args.min_replicates)].copy()
        if args.require_all_replicates:
            totals=m.groupby('cell_line').biological_replicate.nunique()
            eligible_cell=eligible_cell[eligible_cell.n_replicates.eq(eligible_cell.cell_line.map(totals))]
        eligible_cell=eligible_cell.merge(ann[annotation_cols],on=KEYS,validate='many_to_one')
        eligible_cell.to_csv(out/f'cell_line_scores_cov{depth}.csv.gz',index=False)
        wide=eligible_cell.pivot(index=KEYS,columns='cell_line',values='score').reindex(columns=lines)
        common=wide.dropna()
        common.to_csv(out/f'all_line_common_scores_cov{depth}.csv.gz')
        for line in lines:
            for cutoff in cutoffs:
                common_summary.append({'coverage_threshold':depth,'cell_line':line,'score_cutoff':cutoff,'n_common_sites':len(common),'mean_score':common[line].mean(),'median_score':common[line].median(),'fraction_high':common[line].ge(cutoff).mean() if len(common) else None})
        for a,b in itertools.combinations(lines,2):
            pair=compare_pair(eligible_cell[eligible_cell.cell_line.eq(a)].drop(columns=['gene_id','gene_name']+(['motif_5mer'] if 'motif_5mer' in ann else [])),eligible_cell[eligible_cell.cell_line.eq(b)].drop(columns=['gene_id','gene_name']+(['motif_5mer'] if 'motif_5mer' in ann else [])))
            pair=pair.merge(ann[annotation_cols],on=KEYS,validate='one_to_one')
            pair['coverage_balanced']=pair.coverage_ratio.le(args.max_coverage_ratio)
            pair['replicate_separated']=pair.all_replicate_pairs_positive|pair.all_replicate_pairs_negative
            pair['candidate_large_difference']=pair.delta_score.abs().ge(args.min_delta)&pair.replicate_separated&pair.coverage_balanced
            pair.to_csv(pair_dir/f'{a}__{b}__cov{depth}.csv.gz',index=False)
            # Every eligible site is retained: discordant/small effects are evidence too.
            for subset,mask in [('all_pairwise_common',np.ones(len(pair),bool)),('coverage_balanced',pair.coverage_balanced)]:
                d=pair.loc[mask]
                pair_summary.append({'coverage_threshold':depth,'cell_line_a':a,'cell_line_b':b,'population':subset,'n_sites':len(d),'median_delta_a_minus_b':d.delta_score.median(),'median_absolute_delta':d.delta_score.abs().median(),'n_large_replicate_separated':int(d.candidate_large_difference.sum()),'n_overlapping_replicate_ranges':int((~d.replicate_separated).sum())})
                for cutoff in cutoffs:
                    high_a=d.score_a.ge(cutoff);high_b=d.score_b.ge(cutoff);union=int((high_a|high_b).sum());both=int((high_a&high_b).sum())
                    call_summary.append({'coverage_threshold':depth,'cell_line_a':a,'cell_line_b':b,'population':subset,'cutoff':cutoff,'n_common_sites':len(d),'n_both_high':both,'n_a_high_b_low':int((high_a&~high_b).sum()),'n_b_high_a_low':int((high_b&~high_a).sum()),'n_both_low':int((~high_a&~high_b).sum()),'jaccard_high_on_common':both/union if union else None})
            if 'motif_5mer' in pair:
                pair.groupby('motif_5mer',as_index=False).agg(n_sites=('delta_score','size'),median_delta=('delta_score','median')).to_csv(pair_dir/f'{a}__{b}__cov{depth}__motifs.csv',index=False)
    for name,rows in [('all_line_summary',common_summary),('pair_summary',pair_summary),('threshold_sensitivity',call_summary),('agreement',agreement),('score_coverage_dependence',coverage_dependence)]:
        pd.DataFrame(rows).to_csv(out/(name+'.csv'),index=False)
    receipt={'analysis_status':'exploratory real-model predictions; not independent validation', 'arguments':vars(args),'model_version':m.model_version.iloc[0],
        'manifest_sha256':sha(manifest),'model_info_sha256':sha(model_info),'coordinate_documentation':'manifest coordinate_convention when present; otherwise MODEL_INFO.md must document the input positions','coverage_sha256':sha(args.coverage_matrix),'annotation_sha256':sha(args.annotations),'predictions':receipts,
        'aggregation':'mean eligible run scores within replicate, then equal replicate mean; no raw-read pooling',
        'limitations':['Score differences do not estimate stoichiometry.','Coverage balancing does not fully adjust RNA abundance or batch.','Candidate flag is descriptive; no differential-modification significance test.','Common-site selection favours highly expressed transcripts.','Gene/isoform correlations preclude treating sites as independent biological replicates.'],
        'software':{'pandas':pd.__version__,'numpy':np.__version__}}
    (out/'analysis_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    plot_summary(pd.DataFrame(pair_summary),out)
    print('Analysis complete:',out)


def plot_summary(summary,out):
    if summary.empty:return
    depth=summary.coverage_threshold.min()
    d=summary[(summary.coverage_threshold==depth)&summary.population.eq('coverage_balanced')]
    labels=d.cell_line_a+' − '+d.cell_line_b
    fig,ax=plt.subplots(figsize=(8,max(4,.25*len(d))))
    ax.barh(labels,d.median_delta_a_minus_b,color='#267792');ax.axvline(0,color='#444',lw=.8);ax.invert_yaxis()
    ax.set(xlabel='Median paired score difference (A − B)',title=f'Exploratory predictions, coverage ≥{depth}, balanced coverage')
    fig.tight_layout();fig.savefig(out/'paired_score_differences.png',dpi=180);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True);p.add_argument('--coverage-matrix',required=True);p.add_argument('--annotations',required=True);p.add_argument('--aliases')
    p.add_argument('--model-info',help='Defaults to MODEL_INFO.md beside the manifest');p.add_argument('--confirm-real-predictions',action='store_true',help='Declare real predictions after reviewing MODEL_INFO.md when the optional real_predictions column is absent')
    p.add_argument('--out',required=True);p.add_argument('--coverage',default='20,50,100');p.add_argument('--cutoffs',default='0.5,0.7,0.9');p.add_argument('--min-replicates',type=int,default=2);p.add_argument('--require-all-replicates',action='store_true')
    p.add_argument('--max-coverage-ratio',type=float,default=2);p.add_argument('--min-delta',type=float,default=.2);p.add_argument('--allow-missing-predictions',action='store_true')
    a=p.parse_args()
    if a.max_coverage_ratio<1 or a.min_delta<0:p.error('Invalid coverage ratio / minimum difference')
    main(a)
