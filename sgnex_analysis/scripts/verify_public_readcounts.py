"""Download public read-count tables, validate every coverage row against shards.
No prediction scores are read. Network downloads ~660 MB; no AWS account needed.
python scripts/verify_public_readcounts.py --out . --cache ../../readcount_cache
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''): h.update(b)
    return h.hexdigest()


def main(out,cache):
    out,cache=Path(out),Path(cache);cache.mkdir(exist_ok=True,parents=True)
    ns={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
    root=ET.parse(out/'metadata/s3_m6anet_objects.xml').getroot()
    assert root.findtext('s:IsTruncated',namespaces=ns)=='false'
    objects=[]
    for x in root.findall('s:Contents',ns):
        key=x.findtext('s:Key',namespaces=ns)
        if key.endswith('/data.readcount'):
            objects.append((key,int(x.findtext('s:Size',namespaces=ns))))
    def get(item):
        key,size=item;run=key.split('/')[-2];dest=cache/(run+'.readcount')
        if not dest.exists() or dest.stat().st_size!=size:
            tmp=dest.with_suffix('.partial')
            with urllib.request.urlopen('https://sg-nex-data.s3.ap-southeast-1.amazonaws.com/'+key,timeout=120) as r, tmp.open('wb') as f:
                while True:
                    b=r.read(2**20)
                    if not b:break
                    f.write(b)
            assert tmp.stat().st_size==size
            tmp.replace(dest)
        print('Available:',run,flush=True)
        return run,dest,key,size
    with ThreadPoolExecutor(max_workers=4) as pool: downloaded=list(pool.map(get,objects))
    counts=pd.read_csv(out/'results/coverage_matrix_ge20_union.csv.gz')
    keys=['transcript_id','transcript_position']
    ann=pd.read_csv(out/'results/site_annotations.csv.gz',keep_default_na=False)
    versions=ann[['transcript_id','annotated_transcript_version']].drop_duplicates()
    expected_versions=dict(zip(versions.transcript_id,versions.annotated_transcript_version))
    kinds=ann[['transcript_id','kind']].drop_duplicates().set_index('transcript_id').kind.to_dict()
    summary=[];aliases=[]
    for run,path,key,size in downloaded:
        raw=pd.read_csv(path)
        print(run,'columns',raw.columns.tolist(),flush=True)
        raw=raw.rename(columns={'transcript_position':'transcript_position','position':'transcript_position','read_count':'n_reads'})
        assert set(keys+['n_reads']).issubset(raw.columns),raw.columns
        assert not raw[keys].duplicated().any()
        raw['transcript_position']=pd.to_numeric(raw.transcript_position,errors='raise')
        raw['n_reads']=pd.to_numeric(raw.n_reads,errors='raise')
        assert (raw.n_reads>=1).all() and np.isfinite(raw.n_reads).all()
        assert ((raw.n_reads%1)==0).all()
        orig=raw.transcript_id.copy()
        # Restrict suffix removal to Ensembl IDs. Every retained affected site
        # must agree with the annotation version supplied in the Explorer.
        raw['transcript_id']=orig.str.replace(r'^(ENST\d+)\.\d+$',r'\1',regex=True)
        affected=orig.ne(raw.transcript_id)
        needed=affected & raw.n_reads.ge(20)
        for base,ver in zip(raw.loc[needed,'transcript_id'],orig[needed]):
            if kinds.get(base)=='annotated':
                assert expected_versions.get(base)==ver,(run,base,ver,expected_versions.get(base))
        for old,new in zip(orig[affected].drop_duplicates(), raw.loc[affected].drop_duplicates('transcript_id').transcript_id):
            verified=expected_versions.get(new)==old and kinds.get(new)=='annotated'
            aliases.append({'run_id':run,'raw_transcript_id':old,'transcript_id':new,
                'primary_annotation_version_verified':verified,
                'evidence':('exact version match to supplied Ensembl91 annotation; sequence/offset verification pending' if verified else 'coverage-key normalisation only; reference identity unverified; excluded from primary biology')})
        assert not raw[keys].duplicated().any(),'Suffix removal collapsed source keys'
        # Outer join also detects sites omitted from the packed union.
        selected=raw[raw.n_reads.ge(20)][keys+['n_reads']]
        packed=counts.loc[counts[run].ge(20),keys+[run]]
        joined=selected.merge(packed,on=keys,how='outer',validate='one_to_one',indicator=True)
        assert joined['_merge'].eq('both').all(),run
        assert joined.n_reads.eq(joined[run]).all(),run
        # Every nonzero shard entry must match its source, including <20.
        low=counts.loc[counts[run].gt(0),keys+[run]].merge(raw[keys+['n_reads']],on=keys,how='left',validate='one_to_one')
        assert low[run].eq(low.n_reads).all(),run
        # Coverage zeros are absence from processed candidate table, not measured zero expression.
        total=counts[keys+[run]].merge(raw[keys+['n_reads']],on=keys,how='left',validate='one_to_one')
        assert total[run].eq(total.n_reads.fillna(0)).all(),run
        row={'run_id':run,'source_key':key,'size_bytes':size,'sha256':sha(path),'source_rows':len(raw),'suffix_rows':int(affected.sum()),'shard_values_checked':len(total),'coverage_exact_match':True,**{f'n_sites_ge{t}':int(raw.n_reads.ge(t).sum()) for t in [1,5,10,20,50,100]},'median_site_reads':float(raw.n_reads.median())}
        summary.append(row);print('Verified:',run,len(raw),flush=True)
    pd.DataFrame(summary).to_csv(out/'results/public_readcount_verification.csv',index=False)
    pd.DataFrame(aliases,columns=['run_id','raw_transcript_id','transcript_id','primary_annotation_version_verified','evidence']).to_csv(out/'metadata/transcript_aliases_checked.csv',index=False)
    (out/'results/public_readcount_status.json').write_text(json.dumps({'completed':True,'n_runs':len(summary),'all_coverage_exact_match':True,'scope':'all retained shard sites, all 23 public run readcount files','limitations':['Annotation versions in supplied shards were not independently rederived from reference FASTA/GTF.','Original signal JSONs and alignment offsets not validated.','Coverage cannot establish biological independence.']},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='.');p.add_argument('--cache',required=True);a=p.parse_args();main(a.out,a.cache)
