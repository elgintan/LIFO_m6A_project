"""Audit real coverage in the supplied Explorer; NEVER read its simulated scores.

Usage: python scripts/audit_coverage.py --explorer PATH --out .
The source contains only sites reaching 20 reads in at least one run.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(explorer, out):
    explorer, out = Path(explorer), Path(out)
    for folder in ['metadata', 'results', 'figures']:
        (out / folder).mkdir(exist_ok=True, parents=True)
    ov = json.loads((explorer / 'data/overview.json').read_text())
    runs = ov['runs']
    ids = [r['id'] for r in runs]
    samples = pd.read_csv(out/'metadata/samples.tsv', sep='\t').dropna(subset=['sample_alias'])
    samples = samples[samples.protocol.eq('directRNA')].copy()
    assert not samples.sample_alias.duplicated().any()
    ns = {'s': 'http://s3.amazonaws.com/doc/2006-03-01/'}
    xml = ET.parse(out/'metadata/s3_m6anet_prefixes.xml').getroot()
    assert xml.findtext('s:IsTruncated', namespaces=ns) == 'false'
    live_ids = [x.text.rstrip('/').split('/')[-1] for x in xml.findall('s:CommonPrefixes/s:Prefix', ns)]
    assert set(ids) == set(live_ids), 'Explorer / public processed scope mismatch'
    meta = pd.DataFrame([{
        'run_id': r['id'], 'cell_line': r['line'], 'biological_replicate': r['rep'],
        'sequencing_run': r['run'], 'replicate_group': f"{r['line']}:rep{r['rep']}",
        'replicate_status': 'sample-name grouping; independent preparations not independently verified',
        'prediction_file': f"predictions/{r['id']}.csv", 'min_reads': 20,
        'coverage_file': 'results/coverage_matrix_ge20_union.csv.gz',
        'reference_version': 'GRCh38_Ensembl91_reported; per-input verification pending',
        'coordinate_convention': 'transcript_position copied literally; base/offset verification pending',
        'model_version': 'PENDING', 'real_predictions': False,
        'n_candidate_site_rows': r['n_sites'], 'median_site_reads': r['median'],
        **{f'n_sites_ge{t}': r['ge'][str(t)] for t in [1,5,10,20,50,100]},
        'coverage_source': 'supplied Explorer packed read-count vectors; upstream readcounts not rerun',
        'json_uri': f"s3://sg-nex-data/data/processed_data/m6Anet/{r['id']}/",
        'readcount_uri': f"s3://sg-nex-data/data/processed_data/m6Anet/{r['id']}/data.readcount",
        'input_json_uri': f"s3://sg-nex-data/data/processed_data/m6Anet/{r['id']}/data.json",
        'metadata_source': 'official docs/samples.tsv, downloaded 2026-10-15 UTC'
    } for r in runs]).merge(samples, left_on='run_id', right_on='sample_alias', how='left', validate='one_to_one')
    assert meta.sample_alias.notna().all()
    assert (meta.cell_line == meta.cellLine).all()
    meta.to_csv(out/'metadata/sample_manifest.csv', index=False)
    samples['processed_json_available'] = samples.sample_alias.isin(ids)
    samples['scope_note'] = np.where(samples.processed_json_available,
        'included in current 23-run processed inventory',
        'not in current m6Anet processed listing; scope/preprocessing decision required')
    samples.to_csv(out/'metadata/all_directRNA_scope.csv', index=False)
    # The packed format is [position, comma-separated read counts, scores].
    # Read ONLY the first two elements. The third is simulated and is ignored.
    matrices, annotations, receipts = [], [], []
    for file in sorted((explorer/'data/genes').glob('b*.json')):
        receipts.append({'path': str(file.relative_to(explorer)), 'sha256': sha(file)})
        obj = json.loads(file.read_text())
        for gene_key, gene in obj.items():
            for tx in gene['tx']:
                for site in tx['sites']:
                    counts = np.array([int(v) if v else 0 for v in site[1].split(',')], dtype=np.int32)
                    assert len(counts) == len(ids) and (counts >= 0).all()
                    assert counts.max() >= 20
                    annotations.append((tx['id'], int(site[0]), gene_key, gene['label'], gene['kind'], tx.get('ver',''), tx['len'], tx['len_known']))
                    matrices.append(counts)
    cov = np.stack(matrices)
    ann = pd.DataFrame(annotations, columns=['transcript_id','transcript_position','gene_id','gene_name','kind','annotated_transcript_version','transcript_length','length_known'])
    assert not ann[['transcript_id','transcript_position']].duplicated().any(), 'Ambiguous site keys'
    assert len(ann) == ov['totals']['kept_sites']
    assert (cov >= 20).sum() == sum(r['ge']['20'] for r in runs)
    for j, r in enumerate(runs):
        for t in [20,50,100]:
            assert int((cov[:,j] >= t).sum()) == r['ge'][str(t)]
    pd.concat([ann[['transcript_id','transcript_position']], pd.DataFrame(cov, columns=ids)], axis=1).to_csv(out/'results/coverage_matrix_ge20_union.csv.gz', index=False)
    ann.to_csv(out/'results/site_annotations.csv.gz', index=False)
    records = []
    for t in [20,50,100]:
        for population, mask in [('all_reference_types', np.ones(len(ann), bool)), ('annotated_human', ann.kind.eq('annotated').to_numpy())]:
            eligibility = []
            for line in [x['name'] for x in ov['lines']]:
                reps = sorted({r['rep'] for r in runs if r['line'] == line})
                byrep = np.stack([(cov[:,[j for j,r in enumerate(runs) if r['line']==line and r['rep']==rep]] >= t).any(axis=1) for rep in reps], axis=1)
                nreps = byrep.sum(axis=1)
                eligibility.append(nreps)
                records.append({'coverage_threshold':t,'population':population,'cell_line':line,'n_replicate_groups':len(reps),'sites_ge1_replicate':int(((nreps>=1)&mask).sum()),'sites_ge2_replicates':int(((nreps>=2)&mask).sum()),'sites_all_replicates':int(((nreps==len(reps))&mask).sum())})
            n = np.stack(eligibility, axis=1)
            records.append({'coverage_threshold':t,'population':population,'cell_line':'ALL_7_INTERSECTION','n_replicate_groups':17,'sites_ge1_replicate':int(((n>=1).all(axis=1)&mask).sum()),'sites_ge2_replicates':int(((n>=2).all(axis=1)&mask).sum()),'sites_all_replicates':int(((n==np.array([len({r['rep'] for r in runs if r['line']==x['name']}) for x in ov['lines']])).all(axis=1)&mask).sum())})
        if t in ov['sharing']['thresholds']:
            assert records[-9]['sites_ge1_replicate'] == ov['sharing']['by_T'][str(t)]['all_lines']
    support = pd.DataFrame(records)
    support.to_csv(out/'results/replicate_coverage_support.csv', index=False)
    # Transcript annotation versions are evidence for a proposal, not permission
    # to rewrite raw prediction keys. The comparison CLI requires an explicit map.
    ann[['transcript_id','annotated_transcript_version']].drop_duplicates().to_csv(out/'metadata/reference_versions_for_review.csv', index=False)
    pd.DataFrame([{'cell_line': l['name'], 'runs':l['n_runs'], 'replicate_groups':l['n_reps']} for l in ov['lines']]).to_csv(out/'results/cell_line_inventory.csv', index=False)
    safe = {'build_coverage_provenance': {k:ov['build'].get(k) for k in ['public_download_utc','annotation','version_suffix_removed']},
        'source_scores_are_simulated':ov['build'].get('simulated'), 'simulated_scores_used':False,
        'source_site_rows_all_runs':sum(r['n_sites'] for r in runs), 'union_ge20':len(ann),
        'primary_human_union_ge20':int(ann.kind.eq('annotated').sum()),
        'all_directRNA_metadata_rows':len(samples),'processed_runs':len(ids),'scope_gap_runs':len(samples)-len(ids),
        'reference_kind_counts':ann.kind.value_counts().to_dict(),
        'read_vectors_sha256':receipts,'overview_sha256':sha(explorer/'data/overview.json'),
        'note':'Coverage reproduced from supplied display shards, not original JSON/readcount files. Sites below 20 reads everywhere are absent from shards. Full-run statistics are upstream reported.'}
    (out/'results/coverage_audit.json').write_text(json.dumps(safe,indent=2)+'\n')
    plot(meta, support, out)
    print(json.dumps({k:v for k,v in safe.items() if k not in ['read_vectors_sha256']},indent=2))


def plot(meta, support, out):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    colors = dict(zip(meta.cell_line.unique(),plt.cm.tab10.colors))
    fig, axes = plt.subplots(1,2,figsize=(12,6),gridspec_kw={'width_ratios':[1.2,1]})
    labels=[f"{r.cell_line} r{r.biological_replicate} / run{r.sequencing_run}" for r in meta.itertuples()]
    axes[0].barh(labels[::-1], meta.n_sites_ge20.to_numpy()[::-1]/1000,color=[colors[x] for x in meta.cell_line][::-1])
    axes[0].set_xlabel('Candidate transcript-sites per run (thousands)')
    axes[0].set_title('A   Coverage varies between runs (≥20 reads)',loc='left',fontsize=11)
    s=support.query("coverage_threshold == 20 and population == 'annotated_human' and cell_line != 'ALL_7_INTERSECTION'")
    y=np.arange(len(s)); axes[1].barh(y+.17,s.sites_ge1_replicate/1000,height=.32,label='≥1 replicate group',color='#aac7da')
    axes[1].barh(y-.17,s.sites_ge2_replicates/1000,height=.32,label='≥2 replicate groups',color='#216b94')
    axes[1].set_yticks(y,s.cell_line);axes[1].invert_yaxis();axes[1].set_xlabel('Annotated human transcript-sites (thousands)')
    axes[1].set_title('B   Replicate support limits comparisons',loc='left',fontsize=11);axes[1].legend(frameon=False,fontsize=9)
    fig.suptitle('SG-NEx coverage audit — modification scores excluded',fontsize=15,y=.98)
    fig.text(.03,.015,'Source: supplied Explorer coverage vectors; official sample metadata/S3 listing checked 15 Oct 2026 UTC. Run counts include reference controls.',fontsize=8)
    fig.tight_layout(rect=[0,.05,1,.95]);fig.savefig(out/'figures/coverage_and_replicate_support.png',dpi=180);fig.savefig(out/'figures/coverage_and_replicate_support.svg');plt.close(fig)
    a=support.query("population == 'annotated_human' and cell_line == 'ALL_7_INTERSECTION'")
    fig,ax=plt.subplots(figsize=(6.5,4))
    for col,label in [('sites_ge1_replicate','≥1 replicate / line'),('sites_ge2_replicates','≥2 replicates / line'),('sites_all_replicates','All replicate groups / line')]:
        ax.plot(a.coverage_threshold,a[col],marker='o',label=label)
    ax.set(xlabel='Minimum reads in at least one run per contributing replicate',ylabel='Common annotated human transcript-sites',title='Seven-line common-site population shrinks with support rules')
    ax.legend(frameon=False,fontsize=9);fig.tight_layout();fig.savefig(out/'figures/common_population_sensitivity.png',dpi=180);plt.close(fig)


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--explorer',required=True);p.add_argument('--out',default='.');a=p.parse_args();main(a.explorer,a.out)
