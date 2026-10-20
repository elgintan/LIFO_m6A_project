"""Apply the supplied frozen Member 3 candidate in bounded site batches.

Uses the received feature extractor and fixed saved sequence reference unchanged.
Default output: eligible (>=20 finite reads) three-column predictions, plus an
all-input-site metadata sidecar and an inference receipt. This is a candidate
workflow, not evidence the team selected this model. No training occurs.
"""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import numpy as np
import pandas as pd
import lightgbm as lgb


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()


def predict(a):
    if a.min_reads<20 or a.batch_sites<1:raise ValueError('Require min_reads >=20 and batch_sites >=1')
    candidate=Path(a.candidate_dir).resolve()
    sys.path.insert(0,str(candidate/'code'))
    from features import KEY,KmerBaseline,read_sites
    card=json.loads((candidate/'artifact/model_card.json').read_text())
    for name,filename in [('model','model.txt'),('kmer_baseline','kmer_baseline.csv')]:
        if sha(candidate/'artifact'/filename)!=card[name+'_sha256']:raise ValueError(filename+' checksum mismatch')
    booster=lgb.Booster(model_file=str(candidate/'artifact/model.txt'))
    baseline=KmerBaseline.from_frame(pd.read_csv(candidate/'artifact/kmer_baseline.csv',index_col=[0,1]),card['kmer_baseline_min_sites'])
    out=Path(a.output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    metadata=out.with_suffix('.site_metadata.csv.gz');receipt=out.with_suffix('.receipt.json')
    partial=out.with_suffix(out.suffix+'.partial');meta_partial=metadata.with_suffix(metadata.suffix+'.partial')
    if any(p.exists() for p in [out,metadata,receipt,partial,meta_partial]):raise ValueError('Use a fresh output filename; previous evidence is preserved')
    counters={'input_sites':0,'scored_sites':0,'below_minimum_finite_reads':0,'reads_discarded_nonfinite':0,'7mer':0,'5mer':0,'global':0}
    opener=gzip.open if str(a.input).endswith('.gz') else open
    with tempfile.TemporaryDirectory(prefix='member3-infer-') as temp:
        temp=Path(temp);db=sqlite3.connect(temp/'keys.sqlite')
        db.execute('CREATE TABLE seen (tx TEXT, pos INTEGER, PRIMARY KEY(tx,pos))')
        with partial.open('w',newline='') as output,gzip.open(meta_partial,'wt',newline='') as meta:
            writer=csv.writer(output);writer.writerow(KEY+['score'])
            mw=csv.writer(meta);mw.writerow(KEY+['sequence_7mer','motif_5mer','n_reads_input','n_reads_finite','prediction_status','reference_level'])
            records=[];raw_counts={}
            def flush():
                if not records:return
                file=temp/'batch.json';file.write_text('\n'.join(records)+'\n')
                sites=read_sites(file)
                db.executemany('INSERT INTO seen VALUES (?,?)',[(str(t),int(p)) for t,p in sites[KEY].itertuples(index=False,name=None)]);db.commit()
                x,levels=baseline.transform(sites)
                accepted=sites.n_reads.ge(a.min_reads).to_numpy()
                scores=booster.predict(x.loc[accepted,card['features']],num_threads=a.threads) if accepted.any() else np.array([])
                if not np.isfinite(scores).all() or not ((scores>=0)&(scores<=1)).all():raise ValueError('Invalid model score')
                for row,score in zip(sites.loc[accepted,KEY].itertuples(index=False,name=None),scores):writer.writerow([*row,format(float(score),'.17g')])
                for row,level,ok in zip(sites.itertuples(index=False),levels,accepted):
                    nraw=raw_counts[(row.transcript_id,row.transcript_position)]
                    mw.writerow([row.transcript_id,row.transcript_position,row.kmer,row.kmer[1:6],nraw,row.n_reads,'scored' if ok else 'below_minimum_finite_reads',level])
                    counters['reads_discarded_nonfinite']+=nraw-int(row.n_reads)
                    if ok:counters[str(level)]+=1
                counters['input_sites']+=len(sites);counters['scored_sites']+=int(accepted.sum());counters['below_minimum_finite_reads']+=int((~accepted).sum())
                records.clear();raw_counts.clear()
            with opener(a.input,'rt') as source:
                for line in source:
                    if not line.strip():continue
                    for transcript,positions in json.loads(line).items():
                        for position,kmers in positions.items():
                            for kmer,reads in kmers.items():
                                key=(transcript,int(position))
                                if key in raw_counts:raise ValueError('Duplicate key inside batch')
                                raw_counts[key]=len(reads)
                                records.append(json.dumps({transcript:{position:{kmer:reads}}},separators=(',',':')))
                                if len(records)>=a.batch_sites:flush()
            flush();db.close()
    partial.replace(out);meta_partial.replace(metadata)
    payload={'run_id':a.run_id,'status':'completed_candidate_inference','final_model_selected':False,
        'candidate_id':'member3-lgbm-'+card['model_sha256'][:12],'model_sha256':card['model_sha256'],
        'kmer_baseline_sha256':card['kmer_baseline_sha256'],'input_sha256':sha(a.input),'output_sha256':sha(out),
        'arguments':vars(a),'counts':counters,'software':{'python':sys.version.split()[0],'numpy':np.__version__,'pandas':pd.__version__,'lightgbm':lgb.__version__},
        'coverage_warning':'Source read-count coverage and finite-read eligibility can differ. Audit the sidecar; do not silently fill omitted predictions with zero.',
        'interpretation':'Predicted candidate site scores; not validated modification fractions; coordinate mapping and final selection require separate evidence.'}
    receipt.write_text(json.dumps(payload,indent=2)+'\n');print(json.dumps(counters))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--run-id',required=True)
    p.add_argument('--candidate-dir',default=str(Path(__file__).resolve().parents[2]/'model_samuel'));p.add_argument('--min-reads',type=int,default=20);p.add_argument('--batch-sites',type=int,default=512);p.add_argument('--threads',type=int,default=4)
    predict(p.parse_args())
