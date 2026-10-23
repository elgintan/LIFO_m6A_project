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
CONTEXT_POLICIES={'all-source-consistent':'all_source_consistent',
                  'scored-consistent':'scored_consistent'}


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


def validate_context_keys(df, label):
    """Validate keys without changing transcript strings or integer offsets."""
    if not set(KEYS).issubset(df):raise ValueError(f'{label}: missing key columns')
    if df[KEYS].isna().any().any() or df.transcript_id.astype(str).str.strip().eq('').any():
        raise ValueError(f'{label}: missing site key')
    pos=pd.to_numeric(df.transcript_position,errors='raise')
    if not (np.isfinite(pos).all() and (pos>=0).all() and (pos%1==0).all()):
        raise ValueError(f'{label}: positions must be finite nonnegative integers')
    df=df.copy();df['transcript_position']=pos.astype('int64')
    if df[KEYS].duplicated().any():raise ValueError(f'{label}: duplicate site keys')
    return df


def strict_boolean(series, label):
    values=series.astype(str)
    if not values.isin(['True','False']).all():
        raise ValueError(f'{label}: expected literal True/False values')
    return values.eq('True')


def load_context_gate(directory, policy, cov, input_hashes, prediction_receipts):
    """Bind a complete QC population to these unchanged analysis inputs.

    The QC script checked the large source metadata. This consumer rechecks its
    final table and all shared analysis-input/prediction hashes. It does not
    claim to rescan source metadata or independently prove reference identity.
    """
    if policy not in CONTEXT_POLICIES:raise ValueError('A qualified context policy is required with --context-qc')
    directory=Path(directory).resolve();receipt_path=directory/'complete.json'
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    if receipt.get('status')!='complete':raise ValueError('Context QC is not complete')
    inputs=receipt.get('inputs',{})
    for name,actual_hash in input_hashes.items():
        if inputs.get(name,{}).get('sha256')!=actual_hash:
            raise ValueError(f'Context QC {name} input hash mismatch')
    expected=inputs.get('predictions',[])
    expected_ids=[x.get('run_id') for x in expected]
    current_ids=[x['run_id'] for x in prediction_receipts]
    if len(expected_ids)!=len(set(expected_ids)) or set(expected_ids)!=set(current_ids):
        raise ValueError('Context QC prediction run universe mismatch')
    expected_hashes={x['run_id']:x.get('sha256') for x in expected}
    for item in prediction_receipts:
        if expected_hashes[item['run_id']]!=item['sha256']:
            raise ValueError(f"Context QC prediction hash mismatch: {item['run_id']}")
    table_path=directory/'key_context_qc.csv.gz'
    declared=receipt.get('outputs',{}).get(table_path.name,{})
    if declared.get('sha256')!=sha(table_path) or declared.get('size_bytes')!=table_path.stat().st_size:
        raise ValueError('Context QC table hash/size mismatch')
    qc=validate_context_keys(pd.read_csv(table_path,keep_default_na=False,dtype={'transcript_id':str}), 'Context QC')
    required=['all_source_consistent','scored_consistent','encoded7mer_all_source','encoded7mer_scored',
              'n_source_runs','n_scored_runs','n_encoded_contexts_all_source','n_encoded_contexts_scored',
              'ambiguous_context_all_source','ambiguous_context_scored']
    if not set(required).issubset(qc):raise ValueError('Context QC missing qualification columns')
    for name in ['all_source_consistent','scored_consistent','ambiguous_context_all_source','ambiguous_context_scored']:
        qc[name]=strict_boolean(qc[name], 'Context QC '+name)
    for name in ['n_source_runs','n_scored_runs','n_encoded_contexts_all_source','n_encoded_contexts_scored']:
        values=pd.to_numeric(qc[name],errors='raise')
        if not (np.isfinite(values).all() and (values>=0).all() and (values%1==0).all()):
            raise ValueError('Context QC invalid count: '+name)
        qc[name]=values.astype('int64')
    for scope,run_col in [('all_source','n_source_runs'),('scored','n_scored_runs')]:
        good=qc[scope+'_consistent']
        sequences=qc['encoded7mer_'+scope].astype(str)
        valid=sequences.str.fullmatch('[ACGT]{7}').fillna(False)&sequences.str[3].eq('A')
        if (good & (~valid | qc['ambiguous_context_'+scope] |
                    qc['n_encoded_contexts_'+scope].ne(1) | qc[run_col].lt(1))).any():
            raise ValueError('Context QC inconsistent qualification flag: '+scope)
    if (qc.all_source_consistent & (~qc.scored_consistent |
            qc.encoded7mer_all_source.ne(qc.encoded7mer_scored))).any():
        raise ValueError('Context QC all-source/scored policy contradiction')
    joined=cov[KEYS].merge(qc[KEYS],on=KEYS,how='outer',indicator=True,validate='one_to_one')
    if not joined['_merge'].eq('both').all():raise ValueError('Context QC key universe must exactly match coverage matrix')
    flag=CONTEXT_POLICIES[policy]
    qc['context_qualified']=qc[flag]
    qc['analysis_sequence_7mer']=qc['encoded7mer_'+('all_source' if policy=='all-source-consistent' else 'scored')]
    info={'policy':policy,'qc_complete_sha256':sha(receipt_path),'table_sha256':declared['sha256'],
          'n_union_keys':len(qc),'n_qualified_union_keys':int(qc.context_qualified.sum()),
          'model_sha256':inputs.get('model_sha256'),
          'scope':'analysis-layer gate; complete original prediction exports validated before qualification',
          'verification':'QC table and shared analysis/prediction hashes checked; source metadata not rescanned by comparator'}
    return qc,info


def population_counts(long, manifest, depth, min_replicates, require_all=False):
    """Report denominators for all lines and each distinct pair, without scores."""
    observed=long[long.n_reads.ge(depth)].groupby(KEYS+['cell_line']).biological_replicate.nunique()
    observed=observed.reset_index(name='n_replicates')
    good=observed.n_replicates.ge(min_replicates)
    if require_all:
        totals=manifest.groupby('cell_line').biological_replicate.nunique()
        good &= observed.n_replicates.eq(observed.cell_line.map(totals))
    observed=observed[good]
    lines=sorted(manifest.cell_line.unique())
    sets={line:set(map(tuple,observed.loc[observed.cell_line.eq(line),KEYS].itertuples(index=False,name=None))) for line in lines}
    records=[{'coverage_threshold':depth,'population':'all_line_common','cell_line_a':'ALL','cell_line_b':'ALL',
              'n_sites':len(set.intersection(*(sets[line] for line in lines)))}]
    for line in lines:
        records.append({'coverage_threshold':depth,'population':'eligible_cell_line','cell_line_a':line,'cell_line_b':'',
                        'n_sites':len(sets[line])})
    for a,b in itertools.combinations(lines,2):
        records.append({'coverage_threshold':depth,'population':'pairwise_common','cell_line_a':a,'cell_line_b':b,
                        'n_sites':len(sets[a]&sets[b])})
    return records


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
    if table[unit].isna().any():raise ValueError('Missing concordance unit')
    # Partition once. Repeatedly filtering the full multi-million-row table
    # for every pair is needlessly quadratic in the number of run/group units.
    partitions={label:part[KEYS+['score']] for label,part in table.groupby(unit,sort=False,observed=True)}
    labels=list(partitions)
    for u,v in itertools.combinations(labels,2):
        a=partitions[u]
        b=partitions[v]
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
    if args.min_replicates<2:raise ValueError('At least two metadata replicate groups required')
    thresholds=[int(x) for x in args.coverage.split(',')]
    if min(thresholds)<20 or min(thresholds)<pd.to_numeric(m.min_reads).max():raise ValueError('Unsupported coverage threshold')
    cutoffs=[float(x) for x in args.cutoffs.split(',')]
    if any(t<0 or t>1 for t in cutoffs):raise ValueError('Invalid cutoff')
    cov=validate_context_keys(pd.read_csv(args.coverage_matrix,dtype={'transcript_id':str}), 'Coverage')
    ann=validate_context_keys(pd.read_csv(args.annotations,keep_default_na=False,dtype={'transcript_id':str}), 'Annotations')
    if not set(m.run_id).issubset(cov.columns):raise ValueError('Run missing from coverage matrix')
    aliases=pd.read_csv(args.aliases,keep_default_na=False) if args.aliases else None
    receipts=[];frames=[];availability=[]
    for row in m.itertuples():
        f=(root/row.prediction_file).resolve()
        if 'placeholder' in str(f).lower() or 'simulated' in str(f).lower():raise ValueError('Simulated source path refused')
        d=validate_scores(pd.read_csv(f,float_precision='round_trip',dtype={'transcript_id':str}))
        d['raw_transcript_id']=d.transcript_id
        if aliases is not None:
            a=aliases[aliases.run_id.eq(row.run_id)]
            if a.raw_transcript_id.duplicated().any():raise ValueError('Ambiguous alias map')
            remap=dict(zip(a.raw_transcript_id,a.transcript_id))
            d['transcript_id']=d.transcript_id.map(lambda value:remap.get(value,value))
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
        print(f'Validated complete predictions {len(frames)}/{len(m)}: {row.run_id}',flush=True)
    allrows=pd.concat(frames,ignore_index=True)
    pd.DataFrame(availability).to_csv(out/'prediction_availability.csv',index=False)
    # Complete original exports have now passed all key/coverage/score checks.
    # Qualification changes only analysis populations, never the source CSVs.
    context_dir=getattr(args,'context_qc',None)
    context_policy=getattr(args,'context_policy','unqualified-diagnostic')
    if context_dir:
        input_hashes={'manifest':sha(manifest),'coverage':sha(args.coverage_matrix),
                      'annotations':sha(args.annotations),'aliases':sha(args.aliases) if args.aliases else None}
        qc,context_info=load_context_gate(context_dir,context_policy,cov,input_hashes,receipts)
        gate_cols=KEYS+['context_qualified','analysis_sequence_7mer','all_source_consistent','scored_consistent',
                       'n_encoded_contexts_all_source','n_encoded_contexts_scored']
        allrows=allrows.merge(qc[gate_cols],on=KEYS,how='left',validate='many_to_one')
        if allrows.context_qualified.isna().any():raise ValueError('Prediction key missing context QC qualification')
    else:
        if context_policy!='unqualified-diagnostic':raise ValueError('Qualified context policy requires --context-qc')
        allrows['context_qualified']=True
        context_info={'policy':'unqualified-diagnostic','warning':'No cross-run context qualification; diagnostic output only'}
        print('UNQUALIFIED_CONTEXT_DIAGNOSTIC: no context-QC gate; do not use as qualified primary analysis')
    controls=allrows[allrows.kind.ne('annotated')].copy()
    if len(controls):
        controls.assign(high=controls.score.ge(.5)).groupby(['run_id','kind'],as_index=False).agg(n_sites=('score','size'),mean_score=('score','mean'),fraction_ge05=('high','mean')).to_csv(out/'nonprimary_reference_diagnostics.csv',index=False)
    annotated=allrows[allrows.kind.eq('annotated')].copy()
    excluded=annotated[~annotated.context_qualified].copy()
    excluded.to_csv(out/'context_excluded_run_scores.csv.gz',index=False)
    long=annotated[annotated.context_qualified].copy()
    if context_dir:
        # True contexts come from saved model inputs; do not infer them from
        # annotation or training frequencies. Weak support is not an exclusion.
        long['context_motif_5mer']=long.analysis_sequence_7mer.str[1:6]
    qualification=[];population_impact=[]
    for depth in thresholds:
        for run in m.run_id:
            before=annotated[annotated.run_id.eq(run)&annotated.n_reads.ge(depth)]
            after=long[long.run_id.eq(run)&long.n_reads.ge(depth)]
            qualification.append({'run_id':run,'coverage_threshold':depth,'annotation_population':'annotated',
                                  'n_before_context_qc':len(before),'n_after_context_qc':len(after),
                                  'n_excluded_context_qc':len(before)-len(after)})
        for stage,table in [('before_context_qc',annotated),('after_context_qc',long)]:
            population_impact.extend(dict(record,stage=stage,context_policy=context_policy) for record in
                population_counts(table,m,depth,args.min_replicates,args.require_all_replicates))
    pd.DataFrame(qualification).to_csv(out/'context_qualification_by_run_depth.csv',index=False)
    pd.DataFrame(population_impact).to_csv(out/'context_population_impact.csv',index=False)
    analysis_ann=ann
    annotation_cols=KEYS+['gene_id','gene_name']+(['motif_5mer'] if 'motif_5mer' in ann else [])
    if context_dir:
        context_annotations=qc[KEYS+['analysis_sequence_7mer']].copy()
        context_annotations['context_motif_5mer']=context_annotations.analysis_sequence_7mer.str[1:6]
        analysis_ann=ann.merge(context_annotations,on=KEYS,how='left',validate='one_to_one')
        annotation_cols+=['analysis_sequence_7mer','context_motif_5mer']
    common_summary=[];pair_summary=[];call_summary=[];agreement=[];coverage_dependence=[]
    lines=sorted(m.cell_line.unique());pair_dir=out/'pairs';pair_dir.mkdir()
    for depth in thresholds:
        print(f'Comparing annotated context-qualified scores at >= {depth} reads',flush=True)
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
        eligible_cell=eligible_cell.merge(analysis_ann[annotation_cols],on=KEYS,validate='many_to_one')
        eligible_cell.to_csv(out/f'cell_line_scores_cov{depth}.csv.gz',index=False)
        wide=eligible_cell.pivot(index=KEYS,columns='cell_line',values='score').reindex(columns=lines)
        common=wide.dropna()
        common.to_csv(out/f'all_line_common_scores_cov{depth}.csv.gz')
        for line in lines:
            for cutoff in cutoffs:
                common_summary.append({'coverage_threshold':depth,'cell_line':line,'score_cutoff':cutoff,'n_common_sites':len(common),'mean_score':common[line].mean(),'median_score':common[line].median(),'fraction_high':common[line].ge(cutoff).mean() if len(common) else None})
        for a,b in itertools.combinations(lines,2):
            pair=compare_pair(eligible_cell[eligible_cell.cell_line.eq(a)].drop(columns=annotation_cols[2:]),eligible_cell[eligible_cell.cell_line.eq(b)].drop(columns=annotation_cols[2:]))
            pair=pair.merge(analysis_ann[annotation_cols],on=KEYS,validate='one_to_one')
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
            motif_col='context_motif_5mer' if context_dir else ('motif_5mer' if 'motif_5mer' in pair else None)
            if motif_col:
                pair.groupby(motif_col,as_index=False).agg(n_sites=('delta_score','size'),median_delta=('delta_score','median')).to_csv(pair_dir/f'{a}__{b}__cov{depth}__motifs.csv',index=False)
        print(f'Completed all 21 cell-line pairs at >= {depth} reads',flush=True)
    for name,rows in [('all_line_summary',common_summary),('pair_summary',pair_summary),('threshold_sensitivity',call_summary),('agreement',agreement),('score_coverage_dependence',coverage_dependence)]:
        pd.DataFrame(rows).to_csv(out/(name+'.csv'),index=False)
    receipt={'analysis_status':'exploratory real-model predictions; not independent validation', 'arguments':vars(args),'model_version':m.model_version.iloc[0],
        'manifest_sha256':sha(manifest),'model_info_sha256':sha(model_info),'coordinate_documentation':'manifest coordinate_convention when present; otherwise MODEL_INFO.md must document the input positions','coverage_sha256':sha(args.coverage_matrix),'annotation_sha256':sha(args.annotations),'predictions':receipts,
        'aliases_sha256':sha(args.aliases) if args.aliases else None,'script_sha256':sha(Path(__file__)),
        'context_qualification':context_info,
        'n_annotated_run_sites_before_context_qc':len(annotated),'n_annotated_run_sites_excluded_context_qc':len(excluded),
        'aggregation':'mean eligible run scores within replicate, then equal replicate mean; no raw-read pooling',
        'limitations':['Score differences do not estimate stoichiometry.','Coverage balancing does not fully adjust RNA abundance or batch.','Candidate flag is descriptive; no differential-modification significance test.','Common-site selection favours highly expressed transcripts.','Gene/isoform correlations preclude treating sites as independent biological replicates.'],
        'software':{'pandas':pd.__version__,'numpy':np.__version__}}
    plot_summary(pd.DataFrame(pair_summary),out)
    receipt['status']='complete'
    (out/'analysis_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
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
    p.add_argument('--context-qc',help='Completed cross-run context-QC directory; input/output hashes and complete key universe are checked')
    p.add_argument('--context-policy',choices=['unqualified-diagnostic']+list(CONTEXT_POLICIES),default='unqualified-diagnostic',help='Explicit analysis population; default legacy output is labelled unqualified diagnostic')
    p.add_argument('--max-coverage-ratio',type=float,default=2);p.add_argument('--min-delta',type=float,default=.2);p.add_argument('--allow-missing-predictions',action='store_true')
    a=p.parse_args()
    if a.max_coverage_ratio<1 or a.min_delta<0:p.error('Invalid coverage ratio / minimum difference')
    main(a)
