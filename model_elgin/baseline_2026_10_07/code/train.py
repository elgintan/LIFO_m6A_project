"""Data0-only staged neural search, shared gene folds, resumable epoch checkpoints."""
import argparse, csv, hashlib, json, os, platform, random, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import StratifiedGroupKFold
from common import Measure, metrics, save_json
from data import sha256
from model import SiteModel,read_transform,summary_transform

ROOT=Path(__file__).resolve().parent
FOLD_SHA='986b7872084cf762f1c3944b1eacc1e8f1ff69cb2848630f80685063541da9b0'
BASE={'width':64,'dropout':.15,'lr':.001,'weight_decay':.0001,'pos_weight':1.,'cap':32,'summary_n':63}
CONFIGS=[
 {'id':'mean_sd_context','pool':'summary','summary_n':18},
 {'id':'distribution_context','pool':'summary'},
 {'id':'deepsets_distribution','pool':'deepsets'},
 {'id':'gated_attention_distribution','pool':'attention'},
 {'id':'normalized_noisyor_distribution','pool':'noisyor'},
 {'id':'attention_weighted','pool':'attention','pos_weight':3.,'dropout':.25,'width':48},
]
CONFIGS=[dict(BASE,**c) for c in CONFIGS]

class Cache:
    def __init__(self,path):
        path=Path(path);self.audit=json.loads((path/'audit.json').read_text())
        manifest=json.loads((path/'manifest.json').read_text())
        if manifest['status']!='completed':raise ValueError('Incomplete cache')
        for name,expected in manifest['cache_sha256'].items():
            if sha256(path/name)!=expected:raise ValueError('Changed cache payload: '+name)
        self.keys=pd.read_csv(path/'keys.csv')
        self.off=np.load(path/'offsets.npy',mmap_mode='r')
        self.reads=np.memmap(path/'reads.bin',dtype='<f4',mode='r',shape=(int(self.off[-1]),9))
        self.summary=summary_transform(np.load(path/'summary.npy'))
        self.seq=np.load(path/'seq.npy')
        self.source=sha256(path/'manifest.json')
    def bag(self,i): return self.reads[self.off[i]:self.off[i+1]]

def aligned_metadata(cache,labels,folds):
    if sha256(folds)!=FOLD_SHA:raise ValueError('Wrong shared fold fingerprint')
    key=['transcript_id','transcript_position']
    labs=pd.read_csv(labels);fold=pd.read_csv(folds)
    for frame in (cache.keys,labs,fold):
        if frame.duplicated(key).any():raise ValueError('Duplicate site keys')
    joined=cache.keys[key].merge(labs,on=key,how='left',validate='one_to_one',indicator=True)
    if len(joined)!=len(labs) or not (joined['_merge']=='both').all():raise ValueError('Label key mismatch')
    joined=joined.drop(columns='_merge').merge(fold,on=key,validate='one_to_one',suffixes=('','_fold'))
    if len(joined)!=len(cache.keys) or not (joined.gene_id==joined.gene_id_fold).all():raise ValueError('Fold gene mismatch')
    if set(joined.label.unique())!={0,1} or set(joined.fold_id.unique())!=set(range(5)):raise ValueError('Invalid labels/folds')
    if joined.groupby('gene_id').fold_id.nunique().max()!=1:raise ValueError('Gene leakage')
    return joined

def inner_split(indices,y,genes,seed):
    split=StratifiedGroupKFold(5,shuffle=True,random_state=seed)
    a,b=next(split.split(indices,y[indices],genes[indices]));a=indices[a];b=indices[b]
    if set(genes[a])&set(genes[b]):raise ValueError('Inner gene overlap')
    return a,b

def fit_norm(cache,indices):
    summary=cache.summary[indices].astype(np.float64)
    total=np.zeros(9);squared=np.zeros(9);n=0
    for start in range(0,len(indices),1000):
        values=read_transform(np.concatenate([cache.bag(i) for i in indices[start:start+1000]])).astype(np.float64)
        total+=values.sum(0);squared+=(values**2).sum(0);n+=len(values)
    mu=total/n;sd=np.sqrt(np.maximum(squared/n-mu**2,1e-8))
    return {'read_mean':mu.tolist(),'read_sd':sd.tolist(),'summary_mean':summary.mean(0).tolist(),
            'summary_sd':np.maximum(summary.std(0),1e-4).tolist(),
            'fit_sites':len(indices),'fit_reads':n}

def batch(cache,indices,config,rng=None,cap=None):
    # Summary controls never need read tensors; the full bag was already summarised.
    if config['pool']=='summary':
        reads=np.zeros((len(indices),1,9),dtype=np.float32);mask=np.ones((len(indices),1),dtype=bool)
    else:
        bags=[]
        for i in indices:
            values=cache.bag(i)
            if cap is not None and len(values)>cap:
                # Sampling varies by epoch; no first-read truncation or read labels.
                values=values[rng.choice(len(values),cap,replace=False)]
            bags.append(read_transform(values))
        width=max(map(len,bags));reads=np.zeros((len(indices),width,9),dtype=np.float32)
        mask=np.zeros((len(indices),width),dtype=bool)
        for j,values in enumerate(bags):reads[j,:len(values)]=values;mask[j,:len(values)]=True
    return tuple(torch.from_numpy(x) for x in (reads,mask,cache.seq[indices],cache.summary[indices]))

@torch.inference_mode()
def predict_cache(model,cache,indices,batch_size=64,cap=None,seed=915):
    model.eval();indices=np.asarray(indices);scores=np.empty(len(indices),dtype=np.float64)
    order=np.argsort(np.diff(cache.off)[indices],kind='stable');rng=np.random.default_rng(seed)
    for start in range(0,len(indices),batch_size):
        at=order[start:start+batch_size]
        scores[at]=torch.sigmoid(model(*batch(cache,indices[at],model.config,rng,cap))).numpy()
    if not np.isfinite(scores).all():raise ValueError('Nonfinite inference')
    return scores

def atomic_torch(path,obj):
    tmp=path.with_suffix('.tmp');torch.save(obj,tmp);os.replace(tmp,path)

def run_fit(cache,y,train_idx,val_idx,config,seed,directory,max_epochs,patience,batch_size=256):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    signature=hashlib.sha256(json.dumps({'config':config,'seed':seed,'max_epochs':max_epochs,'patience':patience,
        'label_values_sha256':hashlib.sha256(y.astype(np.int8).tobytes()).hexdigest(),
        'batch_size':batch_size,'threads':torch.get_num_threads(),
        'versions':{'torch':str(torch.__version__),'numpy':np.__version__,'pandas':pd.__version__},
        'source':cache.source,'train':train_idx.tolist(),'val':None if val_idx is None else val_idx.tolist(),
        'code':{name:sha256(ROOT/name) for name in ('train.py','model.py','data.py','common.py')}},sort_keys=True).encode()).hexdigest()
    done=directory/'complete.json';last=directory/'last.pt'
    if done.exists():
        result=json.loads(done.read_text())
        if result['signature']!=signature or sha256(directory/'best.pt')!=result['best_sha256']:raise ValueError('Changed completed run')
        return result
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    if last.exists():
        state=torch.load(last,map_location='cpu',weights_only=False)
        if state['signature']!=signature:raise ValueError('Changed interrupted run')
        norm=state['norm']
    else:
        norm=fit_norm(cache,train_idx);state=None
    model=SiteModel(config,norm)
    opt=torch.optim.AdamW(model.parameters(),lr=config['lr'],weight_decay=config['weight_decay'])
    criterion=torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(config['pos_weight']))
    best=-1.;best_epoch=0;stale=0;start_epoch=1;history=[];previous=[]
    if state:
        model.load_state_dict(state['state_dict']);opt.load_state_dict(state['optimizer'])
        torch.set_rng_state(state['torch_rng']);start_epoch=state['epoch']+1
        best=state['best'];best_epoch=state['best_epoch'];stale=state['stale'];history=state['history'];previous=state.get('resources',[])
    with Measure() as measure:
        measure.output=directory/f'invocation_{time.time_ns()}.json'
        for epoch in range(start_epoch,max_epochs+1):
            if val_idx is not None and stale>=patience:break
            began=time.perf_counter();model.train();rng=np.random.default_rng(seed*100000+epoch)
            shuffled=rng.permutation(train_idx);loss_sum=0.
            for start in range(0,len(shuffled),batch_size):
                idx=shuffled[start:start+batch_size];tensors=batch(cache,idx,config,rng,config['cap'])
                opt.zero_grad(set_to_none=True);pred=model(*tensors)
                loss=criterion(pred,torch.tensor(y[idx],dtype=torch.float32))
                if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
                loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5.);opt.step()
                loss_sum+=float(loss.detach())*len(idx)
            row={'epoch':epoch,'loss':loss_sum/len(train_idx)}
            if val_idx is not None:
                row.update(metrics(y[val_idx],predict_cache(model,cache,val_idx)))
                score=row['selection_score']
            else:score=float(epoch)
            row['wall_seconds']=time.perf_counter()-began;history.append(row)
            if score>best+1e-5:
                best=score;best_epoch=epoch;stale=0
                atomic_torch(directory/'best.pt',{'config':config,'norm':norm,'state_dict':model.state_dict()})
            else:stale+=1
            cp={'signature':signature,'config':config,'norm':norm,'state_dict':model.state_dict(),'optimizer':opt.state_dict(),
                'epoch':epoch,'best':best,'best_epoch':best_epoch,'stale':stale,'history':history,
                'torch_rng':torch.get_rng_state(),'resources':previous+[measure.snapshot()]}
            atomic_torch(last,cp);save_json(directory/'history.json',history)
            with (directory/'training.log').open('a',encoding='utf-8') as log:log.write(json.dumps(row)+'\n')
            print(f"{directory.name}: epoch {epoch}, loss {row['loss']:.4f}, " +
                  (f"inner score {score:.5f}, " if val_idx is not None else '')+f"{row['wall_seconds']:.1f}s",flush=True)
    result={'signature':signature,'config':config,'seed':seed,'best_epoch':best_epoch,'best_score':best,
            'epochs_completed':len(history),'train_sites':len(train_idx),'validation_sites':0 if val_idx is None else len(val_idx),
            'history':history,'resources':previous+[measure.record],'best_sha256':sha256(directory/'best.pt')}
    save_json(done,result);return result

def restore(path):
    bundle=torch.load(path,map_location='cpu',weights_only=False);model=SiteModel(bundle['config'],bundle['norm'])
    model.load_state_dict(bundle['state_dict']);model.eval();return model,bundle

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=ROOT/'cache/data0')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'runs')
    parser.add_argument('--max-epochs',type=int,default=20)
    parser.add_argument('--patience',type=int,default=5)
    parser.add_argument('--threads',type=int,default=4)
    parser.add_argument('--phase',choices=['screen','cv','final','all'],default='all')
    args=parser.parse_args();torch.set_num_threads(args.threads);torch.set_num_interop_threads(1)
    cache=Cache(args.cache);out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
    meta=aligned_metadata(cache,ROOT.parent/'data0/data.info.labelled',ROOT.parent/'shared_folds/data0_folds.csv')
    y=meta.label.to_numpy();genes=meta.gene_id.to_numpy();folds=meta.fold_id.to_numpy();indices=np.arange(len(y))
    plan={'configs':CONFIGS,'max_epochs':args.max_epochs,'patience':args.patience,'threads':args.threads,
          'cache_manifest_sha256':cache.source,'shared_fold_sha256':FOLD_SHA,
          'labels_sha256':sha256(ROOT.parent/'data0/data.info.labelled'),
          'packages':{'numpy':np.__version__,'pandas':pd.__version__,'torch':str(torch.__version__)},
          'source_sha256':{n:sha256(ROOT/n) for n in ('train.py','model.py','data.py','common.py')},
          'dataset_roles':'data0 only; data1/data2 never accessed by this script',
          'validation':'screen on inner genes of shared folds 1-4; finalist epoch selection on inner training genes for each outer fold; refit before outer scoring; outer scores used for architecture selection are development evidence',
          'hardware':{'platform':platform.platform(),'processor':platform.processor(),'logical_cpus':os.cpu_count(),
                      'ram_bytes':__import__('psutil').virtual_memory().total,'torch':torch.__version__,'gpu_available':torch.cuda.is_available()},
          'command':sys.argv}
    old=out/'search_manifest.json'
    if old.exists():
        prior=json.loads(old.read_text())
        for key in ('configs','max_epochs','patience','cache_manifest_sha256','shared_fold_sha256','source_sha256','labels_sha256','packages','threads'):
            if prior[key]!=plan[key]:raise ValueError('Run manifest changed: '+key)
    else:save_json(old,plan)
    if args.phase in ('screen','all'):
        tr,va=inner_split(indices[folds!=0],y,genes,111)
        screen=[]
        for config in CONFIGS:
            result=run_fit(cache,y,tr,va,config,42,out/('screen_'+config['id']),args.max_epochs,args.patience)
            screen.append({'config':config,'inner_score':result['best_score'],'best_epoch':result['best_epoch']})
            save_json(out/'screen_results.json',screen)
        # A genuinely read-level finalist always receives complete five-fold evaluation.
        ranked=sorted(screen,key=lambda r:r['inner_score'],reverse=True)
        first=ranked[0];read_best=next(r for r in ranked if r['config']['pool']!='summary')
        second=read_best if read_best!=first else next(r for r in ranked if r!=first)
        finalists=[first['config'],second['config']]
        save_json(out/'finalists.json',finalists)
        # Repeat the two finalists on the SAME inner genes with an independent seed.
        for config in finalists:
            run_fit(cache,y,tr,va,config,43,out/('repeat_'+config['id']),args.max_epochs,args.patience)
    if args.phase in ('cv','all'):
        finalists=json.loads((out/'finalists.json').read_text());summaries=[]
        for config in finalists:
            oof=np.full(len(y),np.nan);fold_results=[]
            for f in range(5):
                outer_train=indices[folds!=f];hold=indices[folds==f]
                tr,va=inner_split(outer_train,y,genes,211+f)
                tuned=run_fit(cache,y,tr,va,config,42+f,out/f"{config['id']}_fold{f}_inner",args.max_epochs,args.patience)
                refit=run_fit(cache,y,outer_train,None,config,142+f,out/f"{config['id']}_fold{f}_refit",tuned['best_epoch'],args.patience)
                model,_=restore(out/f"{config['id']}_fold{f}_refit"/'best.pt')
                with Measure() as measure:p=predict_cache(model,cache,hold)
                oof[hold]=p;row={'fold_id':f,'selected_epochs':tuned['best_epoch'],**metrics(y[hold],p),'inference_resources':measure.record}
                fold_results.append(row)
                dest=out/config['id'];dest.mkdir(exist_ok=True)
                frame=cache.keys.iloc[hold][['transcript_id','transcript_position']].copy();frame['score']=p
                frame.to_csv(dest/f'fold{f}_predictions.csv',index=False,float_format='%.17g')
                save_json(dest/'fold_metrics.json',fold_results)
            if not np.isfinite(oof).all():raise ValueError('Incomplete OOF')
            frame=cache.keys[['transcript_id','transcript_position']].copy();frame['score']=oof
            frame.to_csv(out/config['id']/'oof_predictions.csv',index=False,float_format='%.17g')
            mean={k:float(np.mean([r[k] for r in fold_results])) for k in ('roc_auc','pr_auc_trapezoid','average_precision','selection_score')}
            sd={k:float(np.std([r[k] for r in fold_results],ddof=1)) for k in mean}
            report={'config':config,'folds':fold_results,'mean':mean,'sample_sd':sd,'pooled_oof':metrics(y,oof)}
            save_json(out/config['id']/'cv_metrics.json',report);summaries.append(report);save_json(out/'cv_results.json',summaries)
        selected=max(summaries,key=lambda r:r['mean']['selection_score'])
        epochs=int(np.median([r['selected_epochs'] for r in selected['folds']]))
        freeze={'config':selected['config'],'epochs':epochs,'selected_from':'data0 mean shared-fold development score only',
                'data1_exposures_this_run':0,'data1_evaluation_allowed_after_final_model_saved':True,
                'cv_metrics_sha256':sha256(out/selected['config']['id']/'cv_metrics.json')}
        save_json(out/'frozen_specification.json',freeze)
    if args.phase in ('final','all'):
        spec=json.loads((out/'frozen_specification.json').read_text());config=spec['config']
        final=run_fit(cache,y,indices,None,config,2026,out/'final_fit',spec['epochs'],args.patience)
        model,bundle=restore(out/'final_fit/best.pt')
        bundle.update(kind='final_data0_model',schema_version=1,trained_sites=len(y),trained_positives=int(y.sum()),
            shared_folds_sha256=FOLD_SHA,training_input_sha256=cache.audit.get('input_sha256'),
            frozen_specification=spec,predict_all_reads=True,read_sampling_train_cap=config['cap'],
            context_codes={'A':0,'C':1,'G':2,'T/U':3,'other_IUPAC':4},summary_features='9 means,9 population SD,9 each quantiles .1,.25,.5,.75,.9',
            excluded_features=['transcript_id','transcript_position','gene_id','label','fold_id','file_offset'])
        artifact=out/'final_model.pt'
        if artifact.exists():
            old=torch.load(artifact,map_location='cpu',weights_only=False)
            if old['frozen_specification']!=spec:raise ValueError('Refusing changed final artifact')
            prior=json.loads((out/'final_model_manifest.json').read_text())
            if sha256(artifact)!=prior['model_sha256']:raise ValueError('Changed frozen model')
        else:atomic_torch(artifact,bundle)
        manifest={'model_sha256':sha256(artifact),'bytes':artifact.stat().st_size,
            'parameters':sum(p.numel() for p in model.parameters()),'config':config,'epochs':spec['epochs'],
            'data1_evaluation_count':0,'final_fit_resources':final['resources']}
        if not (out/'final_model_manifest.json').exists():save_json(out/'final_model_manifest.json',manifest)
        print('FROZEN FINAL MODEL:',artifact,flush=True)

if __name__=='__main__':
    with Measure() as total:
        total.output=ROOT/'runs'/f'trainer_invocation_{time.time_ns()}.json'
        main()
