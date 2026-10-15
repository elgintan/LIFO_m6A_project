"""Independent correctness checks; synthetic fitting is not project performance.

Reads ten real sites from data0 only. Optional --model verifies the frozen model
in a fresh interpreter on that same small real prediction example.
"""
from __future__ import annotations
import argparse
import gzip
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

from common import metrics, save_json
from data import encode_context, iter_sites, prepare, sha256, summarise
from model import SiteModel, load_model, read_transform, summary_transform
import train

ROOT = Path(__file__).resolve().parent


def expect_rejected(callback, description):
    try:
        callback()
    except (ValueError, TypeError, RuntimeError):
        return description
    raise AssertionError("Expected rejection: " + description)


def model_invariants():
    torch.manual_seed(10)
    reads = torch.rand(3, 6, 9)
    mask = torch.tensor([[1,1,1,1,1,1], [1,1,1,0,0,0], [1,0,0,0,0,0]], dtype=torch.bool)
    seq = torch.randint(0,5,(3,7))
    summaries = torch.randn(3,63)
    norm = {"read_mean": [0.]*9, "read_sd": [1.]*9,
            "summary_mean": [0.]*63, "summary_sd": [1.]*63}
    results = []
    for mode in ("summary", "deepsets", "attention", "noisyor"):
        config = dict(train.BASE, id="synthetic_"+mode, pool=mode, width=16)
        model = SiteModel(config,norm).eval()
        with torch.inference_mode():
            original = model(reads,mask,seq,summaries)
            padded = reads.clone()
            padded[~mask] = 100*torch.rand_like(padded[~mask])
            permutation = torch.tensor([5,1,4,2,0,3])
            alternatives = {
                "padding": model(padded,mask,seq,summaries),
                "permutation": model(reads[:,permutation],mask[:,permutation],seq,summaries),
                "duplicated_bag": model(reads.repeat(1,2,1),mask.repeat(1,2),seq,summaries),
            }
            differences = {name: float((original-value).abs().max())
                           for name,value in alternatives.items()}
            assert original.shape == (3,) and torch.isfinite(original).all()
            assert all(delta < 1e-6 for delta in differences.values())
        model.train()
        model(reads,mask,seq,summaries).square().mean().backward()
        assert all(parameter.grad is None or torch.isfinite(parameter.grad).all()
                   for parameter in model.parameters())
        results.append({"pool":mode, "maximum_logit_differences":differences,
                        "finite_forward_and_gradients":True})
    return results


def input_and_metric_checks():
    one_read = np.arange(1,10,dtype=float)[None,:]
    expected = np.concatenate((one_read[0],np.zeros(9),np.tile(one_read[0],5)))
    assert np.array_equal(summarise(one_read),expected)
    transformed = summary_transform(np.ones((1,63),dtype=np.float32))
    assert np.allclose(transformed[0,::3],np.log1p(1000))
    assert np.allclose(transformed[0,1::3],np.log(2))
    assert np.allclose(transformed[0,2::3],np.log(2))
    assert np.array_equal(encode_context("AuRnGCT"),[0,3,4,4,2,1,3])
    rejected = []
    for bad in ([], [[0.]*8], [[True]+[0.]*8], [[float('nan')]+[0.]*8]):
        rejected.append(expect_rejected(lambda bad=bad:summarise(bad),repr(bad)))
    rejected.append(expect_rejected(lambda:encode_context("XYZABCD"),"invalid context"))
    # Ranking: negative .1, positive .2, negative .3, positive .9.
    result = metrics([0,1,0,1],[.1,.2,.3,.9])
    assert abs(result['roc_auc']-.75)<1e-12
    assert abs(result['pr_auc_trapezoid']-19/24)<1e-12
    assert abs(result['average_precision']-5/6)<1e-12
    assert [result[key] for key in ('tn','fp','fn','tp')]==[2,0,1,1]
    for y,p in (([0,.25,1],[.1,.2,.8]),([0,1],[float('nan'),.7]),
                ([0,1],[-.1,.7]),([0,1],[.1]),([0,0],[.1,.2])):
        rejected.append(expect_rejected(lambda y=y,p=p:metrics(y,p),"invalid binary metric input"))
    return {"summary_order_ddof0_quantile_transform": "passed",
            "U_and_ambiguous_IUPAC_encoding":"passed",
            "rejected_input_cases":len(rejected),"hand_calculated_metrics":result}


def real_example(directory):
    """Preserve original JSON text/all reads; no labels are read."""
    source = ROOT.parent/'data0/dataset0.json.gz'
    example = directory/'data0_first10.json'
    with gzip.open(source,'rt',encoding='utf-8') as handle:
        lines = [next(handle) for _ in range(10)]
    example.write_text(''.join(lines),encoding='utf-8')
    sites = list(iter_sites(example))
    assert len(sites)==10
    norm = {"read_mean":[0.]*9,"read_sd":[1.]*9,
            "summary_mean":[0.]*63,"summary_sd":[1.]*63}
    results = []
    for mode in ('summary','deepsets','attention','noisyor'):
        model = SiteModel(dict(train.BASE,pool=mode,width=16),norm).eval()
        scores = []
        for _,_,context,values in sites:
            reads = torch.from_numpy(read_transform(values)[None,:])
            mask = torch.ones((1,len(values)),dtype=torch.bool)
            seq = torch.from_numpy(encode_context(context)[None,:])
            summary = torch.from_numpy(summary_transform(summarise(values)[None,:]))
            with torch.inference_mode():
                score = float(torch.sigmoid(model(reads,mask,seq,summary))[0])
            assert np.isfinite(score) and 0<=score<=1
            scores.append(score)
        results.append({"pool":mode,"all_ten_scores_finite_in_0_1":True})
    return example, {"source":"data0/dataset0.json.gz","example_path":str(example),
                     "example_sha256":sha256(example),"n_sites":10,
                     "n_reads_total":sum(len(site[3]) for site in sites),
                     "labels_read":False,"frozen_model_test":False,
                     "untrained_architecture_forward_checks":results}


def synthetic_training(directory):
    rng=np.random.default_rng(123)
    synthetic=directory/'synthetic100.json'
    with synthetic.open('w',encoding='utf-8') as handle:
        for i in range(100):
            values=rng.uniform(.01,2.,size=(3+i%6,9))
            handle.write(json.dumps({f'synthetic_{i}':{'1':{'AAGACCA':values.tolist()}}})+'\n')
    audit=prepare(synthetic,directory/'synthetic_cache')
    cache=train.Cache(directory/'synthetic_cache')
    y=np.arange(100)%2
    tr=np.arange(70);va=np.arange(70,100)
    config=dict(train.BASE,id='verification_only',pool='deepsets',width=16,cap=4,dropout=.1)
    # Independent manual normalization agrees, and validation extremes do not
    # participate in either fitted summary or fitted read mean/SD.
    norm=train.fit_norm(cache,tr)
    all_train=read_transform(np.concatenate([cache.bag(i) for i in tr])).astype(np.float64)
    assert np.allclose(norm['read_mean'],all_train.mean(0),rtol=0,atol=1e-12)
    assert np.allclose(norm['summary_mean'],cache.summary[tr].astype(np.float64).mean(0),rtol=0,atol=1e-12)
    before=cache.summary[va].copy();cache.summary[va]+=10000
    shifted=train.fit_norm(cache,tr);cache.summary[va]=before
    assert shifted==norm
    split_a,split_b=train.inner_split(np.arange(100),y,np.arange(100)//2,4)
    assert not set((split_a//2).tolist()) & set((split_b//2).tolist())
    assert set(y[split_a])=={0,1} and set(y[split_b])=={0,1}
    continuous=directory/'continuous'
    replay=directory/'interrupted_resume'
    complete=train.run_fit(cache,y,tr,va,config,555,continuous,2,2,batch_size=16)
    original_atomic=train.atomic_torch
    interrupted=False
    def interrupt_after_epoch_one(path,obj):
        original_atomic(path,obj)
        if path.name=='last.pt' and obj['epoch']==1:
            raise RuntimeError('verification-only simulated epoch-boundary interruption')
    train.atomic_torch=interrupt_after_epoch_one
    try:
        train.run_fit(cache,y,tr,va,config,555,replay,2,2,batch_size=16)
    except RuntimeError as error:
        assert 'verification-only simulated' in str(error)
        interrupted=True
    finally:
        train.atomic_torch=original_atomic
    assert interrupted
    resumed=train.run_fit(cache,y,tr,va,config,555,replay,2,2,batch_size=16)
    a=torch.load(continuous/'last.pt',map_location='cpu',weights_only=False)
    b=torch.load(replay/'last.pt',map_location='cpu',weights_only=False)
    assert a['epoch']==b['epoch']==2
    assert all(torch.equal(a['state_dict'][key],b['state_dict'][key]) for key in a['state_dict'])
    assert [row['loss'] for row in a['history']]==[row['loss'] for row in b['history']]
    model_a,_=train.restore(continuous/'best.pt');model_b,_=train.restore(replay/'best.pt')
    pred_a=train.predict_cache(model_a,cache,va);pred_b=train.predict_cache(model_b,cache,va)
    assert np.array_equal(pred_a,pred_b)
    best_hash=sha256(continuous/'best.pt')
    reused=train.run_fit(cache,y,tr,va,config,555,continuous,2,2,batch_size=16)
    assert reused==complete and sha256(continuous/'best.pt')==best_hash
    changed=y.copy();changed[0]=1-y[0]
    expect_rejected(lambda:train.run_fit(cache,changed,tr,va,config,555,continuous,2,2,batch_size=16),
                    'changed labels resume')
    expect_rejected(lambda:train.run_fit(cache,y,tr,va,config,555,continuous,2,2,batch_size=32),
                    'changed batch size resume')
    assert len(resumed['resources'])==2
    # Payload corruption must be caught by the training Cache loader.
    payload=directory/'synthetic_cache/seq.npy'
    original=payload.read_bytes();payload.write_bytes(original[:-1]+bytes([original[-1]^1]))
    try:
        expect_rejected(lambda:train.Cache(directory/'synthetic_cache'),'corrupted cache payload')
    finally:
        payload.write_bytes(original)
    return {"scope":"synthetic-only correctness; no real model performance",
            "sites":100,"training_sites":70,"validation_sites":30,"epochs":2,
            "train_only_normalization":"passed","inner_gene_isolation":"passed",
            "epoch_boundary_resume_exact_weights_losses_predictions":"passed",
            "complete_checkpoint_reuse_without_fit":"passed",
            "changed_labels_or_batch_size_rejected":"passed",
            "cache_payload_corruption_rejected":"passed",
            "resume_resource_records":len(resumed['resources']),
            "synthetic_cached_reads":audit['n_reads_total']}


def final_model_fresh_process(path,example,directory):
    model,bundle=load_model(path)
    scores=[]
    for _,_,context,values in iter_sites(example):
        with torch.inference_mode():
            score=torch.sigmoid(model(torch.from_numpy(read_transform(values)[None,:]),
                torch.ones((1,len(values)),dtype=torch.bool),
                torch.from_numpy(encode_context(context)[None,:]),
                torch.from_numpy(summary_transform(summarise(values)[None,:]))))[0].item()
        assert np.isfinite(score) and 0<=score<=1
        scores.append(score)
    child_scores=directory/'fresh_process_scores.json'
    command=[sys.executable,str(Path(__file__).resolve()),'--fresh-process-only',
             '--model',str(path),'--example',str(example),'--output',str(child_scores)]
    subprocess.run(command,check=True,capture_output=True,text=True)
    child=json.loads(child_scores.read_text())
    assert np.allclose(scores,child['scores'],rtol=0,atol=1e-7)
    return {'status':'passed','model_sha256':sha256(path),'kind':bundle['kind'],
            'sites':len(scores),'all_finite_in_0_1':True,
            'fresh_process_max_probability_difference':float(np.max(np.abs(np.array(scores)-child['scores']))),
            'command':command}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'verification/verification.json')
    parser.add_argument('--fresh-process-only',action='store_true')
    parser.add_argument('--example',type=Path)
    args=parser.parse_args()
    torch.set_num_threads(1)
    if args.fresh_process_only:
        model,_=load_model(args.model);scores=[]
        for _,_,context,values in iter_sites(args.example):
            with torch.inference_mode():
                p=torch.sigmoid(model(torch.from_numpy(read_transform(values)[None,:]),
                    torch.ones((1,len(values)),dtype=torch.bool),torch.from_numpy(encode_context(context)[None,:]),
                    torch.from_numpy(summary_transform(summarise(values)[None,:]))))[0].item()
            scores.append(p)
        save_json(args.output,{'scores':scores,'model_sha256':sha256(args.model)})
        return
    directory=args.output.parent/('artifacts_'+str(time.time_ns()))
    directory.mkdir(parents=True,exist_ok=False)
    report={'status':'running','command':sys.argv,'scope':'correctness only; data0 ten-site example and synthetic fitting',
            'data1_or_data2_accessed':False,'source_sha256':{name:sha256(ROOT/name)
                 for name in ('verify.py','train.py','model.py','common.py','data.py')}}
    try:
        report['model_invariants']=model_invariants()
        report['input_metrics']=input_and_metric_checks()
        example,report['real_example']=real_example(directory)
        report['synthetic_training']=synthetic_training(directory)
        if args.model:
            report['frozen_final_fresh_process']=final_model_fresh_process(args.model.resolve(),example,directory)
        else:
            report['frozen_final_fresh_process']={'status':'pending final model exists; rerun with --model'}
        report['status']='passed'
    except BaseException as error:
        report['status']='failed';report['error']=str(error)
        save_json(args.output,report)
        raise
    save_json(args.output,report)
    print(json.dumps({'status':report['status'],'verification':str(args.output),
                      'frozen_final_fresh_process':report['frozen_final_fresh_process']},indent=2))


if __name__=='__main__':
    main()
