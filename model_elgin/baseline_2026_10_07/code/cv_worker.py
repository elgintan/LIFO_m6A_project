"""Run disjoint outer-fold fit stages; aggregate only with train.py afterwards.

Workers never choose the architecture or score data1. Each worker owns its
specified candidate/fold directories, so concurrently writing is disjoint.
"""
import argparse,json,time,os
from pathlib import Path
import numpy as np
import torch
from common import Measure,save_json
from data import sha256
from train import ROOT,Cache,aligned_metadata,inner_split,run_fit

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',required=True)
    p.add_argument('--folds',type=int,nargs='+',required=True)
    p.add_argument('--threads',type=int,default=4)
    p.add_argument('--max-epochs',type=int,default=20)
    p.add_argument('--patience',type=int,default=5)
    args=p.parse_args();torch.set_num_threads(args.threads);torch.set_num_interop_threads(1)
    out=ROOT/'runs';finalists=json.loads((out/'finalists.json').read_text())
    config=next(c for c in finalists if c['id']==args.candidate)
    if len(set(args.folds))!=len(args.folds) or any(f not in range(5) for f in args.folds):raise ValueError('Invalid folds')
    manifest=json.loads((out/'search_manifest.json').read_text())
    if (args.threads,args.max_epochs,args.patience)!=(manifest['threads'],manifest['max_epochs'],manifest['patience']):
        raise ValueError('Worker settings must match frozen search plan')
    cache=Cache(ROOT/'cache/data0')
    if cache.source!=manifest['cache_manifest_sha256']:raise ValueError('Changed cache manifest')
    if sha256(ROOT.parent/'data0/data.info.labelled')!=manifest['labels_sha256']:raise ValueError('Changed training labels')
    for name,expected in manifest['source_sha256'].items():
        if sha256(ROOT/name)!=expected:raise ValueError('Changed training source: '+name)
    packages={'numpy':np.__version__,'pandas':__import__('pandas').__version__,'torch':str(torch.__version__)}
    if packages!=manifest['packages'] or config not in manifest['configs']:raise ValueError('Changed package/configuration')
    meta=aligned_metadata(cache,ROOT.parent/'data0/data.info.labelled',ROOT.parent/'shared_folds/data0_folds.csv')
    y=meta.label.to_numpy();genes=meta.gene_id.to_numpy();folds=meta.fold_id.to_numpy();indices=np.arange(len(y))
    record={'candidate':args.candidate,'folds':args.folds,'worker_source_sha256':sha256(__file__),
            'command':__import__('sys').argv,'status':'running','pid':os.getpid(),'started_unix':WORKER_START}
    path=out/f"worker_{args.candidate}_{'_'.join(map(str,args.folds))}.json";save_json(path,record)
    with Measure() as total:
        for f in args.folds:
            outer=indices[folds!=f];tr,va=inner_split(outer,y,genes,211+f)
            tuned=run_fit(cache,y,tr,va,config,42+f,out/f"{config['id']}_fold{f}_inner",args.max_epochs,args.patience)
            run_fit(cache,y,outer,None,config,142+f,out/f"{config['id']}_fold{f}_refit",tuned['best_epoch'],args.patience)
    record.update(status='complete',resources=total.record,finished_unix=time.time());save_json(path,record)
    print('COMPLETE disjoint fold fits:',args.candidate,args.folds,flush=True)

if __name__=='__main__':
    WORKER_START=time.time()
    with Measure() as invocation:
        invocation.output=ROOT/'runs'/f'trainer_invocation_worker_{time.time_ns()}.json'
        main()
