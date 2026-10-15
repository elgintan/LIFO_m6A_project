"""Read-only, model-independent EDA: one row per site, using every supplied read.
Run: python scripts/extract_sites.py --data-root /path/Team_Project --out .
No fitting, label changes, filtering, or fold generation is performed.
"""
import argparse, gzip, hashlib, json, platform
from pathlib import Path
import numpy as np
import pandas as pd

FEATURES = [f'{p}_{s}' for p in ['minus1','centre','plus1']
            for s in ['dwell','event_sd','current']]

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(2**20),b''): h.update(chunk)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--data-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out=a.out; (out/'tables').mkdir(parents=True,exist_ok=True)
    records=[];manifest=[]
    for d in range(3):
        name=f'data{d}';folder=a.data_root/name
        mp=folder/('data.info.labelled' if d==0 else 'data.info')
        jp=folder/f'dataset{d}.json.gz';meta=pd.read_csv(mp)
        keys=['transcript_id','transcript_position']
        assert not meta.duplicated(keys).any(), 'duplicate metadata site keys'
        assert not meta[keys+['label']].isna().any().any()
        rows=[];reads=0;mins=np.full(9,np.inf);maxs=np.full(9,-np.inf)
        zeros=np.zeros(9,dtype=np.int64);negs=zeros.copy();nonfinite=0
        with gzip.open(jp,'rt') as f:
            for line_num,line in enumerate(f,1):
                obj=json.loads(line);assert len(obj)==1
                tx,positions=next(iter(obj.items()));assert len(positions)==1
                pos,motifs=next(iter(positions.items()));assert len(motifs)==1
                seq,vals=next(iter(motifs.items()));x=np.asarray(vals,dtype=float)
                assert x.ndim==2 and x.shape[1]==9 and len(x)>0, (name,line_num,x.shape)
                nonfinite+=int((~np.isfinite(x)).sum());assert np.isfinite(x).all()
                assert len(seq)==7 and set(seq)<=set('ACGT'),(name,seq)
                med=np.quantile(x,[.25,.5,.75],axis=0)
                row={'transcript_id':tx,'transcript_position':int(pos),'sequence':seq,
                     'motif':seq[1:6],'coverage':len(x),
                     'ordered_signal_sha256':hashlib.sha256(x.astype('<f8').tobytes()).hexdigest()}
                for stat,values in [('mean',x.mean(0)),('median',med[1]),
                                    ('iqr',med[2]-med[0]),('read_sd',x.std(0))]:
                    row.update({f'{k}_{stat}':float(v) for k,v in zip(FEATURES,values)})
                rows.append(row);reads+=len(x)
                mins=np.minimum(mins,x.min(0));maxs=np.maximum(maxs,x.max(0))
                zeros+=(x==0).sum(0);negs+=(x<0).sum(0)
                if line_num%25000==0: print(name,line_num,'sites',flush=True)
        df=pd.DataFrame(rows);assert not df.duplicated(keys).any()
        m=df.merge(meta,on=keys,how='outer',validate='one_to_one',indicator=True)
        join=m['_merge'].value_counts().to_dict();assert (m['_merge']=='both').all(),join
        m=m.drop(columns='_merge');m.insert(0,'dataset',name)
        drach=m.motif.str.match(r'^[AGT][AG]AC[ACT]$')
        mismatch=int((m.n_reads!=m.coverage).sum()) if 'n_reads' in m else None
        m.to_csv(out/'tables'/f'{name}_site_summaries.csv.gz',index=False,float_format='%.10g')
        qc={'dataset':name,'n_sites':len(m),'n_reads':reads,'n_transcripts':m.transcript_id.nunique(),
            'n_genes':m.gene_id.nunique() if 'gene_id' in m else None,
            'n_7mers':m.sequence.nunique(),'n_5mers':m.motif.nunique(),
            'label_counts':{str(k):int(v) for k,v in m.label.value_counts().sort_index().items()},
            'coverage_quantiles':{str(q):float(v) for q,v in m.coverage.quantile([0,.25,.5,.75,.9,.95,.99,1]).items()},
            'json_metadata_join':{str(k):int(v) for k,v in join.items()},
            'nonfinite_measurements':nonfinite,'non_DRACH_sites':int((~drach).sum()),
            'metadata_readcount_mismatches':mismatch,
            'feature_min':dict(zip(FEATURES,mins.tolist())),
            'feature_max':dict(zip(FEATURES,maxs.tolist())),
            'feature_zero_counts':dict(zip(FEATURES,zeros.tolist())),
            'feature_negative_counts':dict(zip(FEATURES,negs.tolist()))}
        records.append(qc)
        for path in [mp,jp]:manifest.append({'source':f'{name}/{path.name}','size_bytes':path.stat().st_size,'sha256':sha(path)})
        print(json.dumps(qc),flush=True)
        (out/'tables'/'inventory.json').write_text(json.dumps(records,indent=2))
    (out/'tables'/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
    (out/'tables'/'runtime.json').write_text(json.dumps({'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__},indent=2))

if __name__=='__main__':main()
