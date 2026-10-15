"""Predict every JSON site using one frozen saved model, on CPU, without labels."""
import argparse, csv, json, os
from pathlib import Path
import numpy as np
import torch
from data import iter_sites,summarise,encode_context,sha256
from model import load_model,read_transform,summary_transform
from common import Measure,save_json

@torch.inference_mode()
def score_batch(model,sites):
    summaries=summary_transform(np.stack([summarise(row[3]) for row in sites]))
    sequences=np.stack([encode_context(row[2]) for row in sites])
    if model.config['pool']=='summary':
        reads=np.zeros((len(sites),1,9),np.float32);mask=np.ones((len(sites),1),bool)
    else:
        maximum=max(len(row[3]) for row in sites)
        reads=np.zeros((len(sites),maximum,9),np.float32);mask=np.zeros((len(sites),maximum),bool)
        for i,(_,_,_,bag) in enumerate(sites):reads[i,:len(bag)]=read_transform(bag);mask[i,:len(bag)]=True
    p=torch.sigmoid(model(*(torch.from_numpy(x) for x in (reads,mask,sequences,summaries)))).numpy()
    if not np.isfinite(p).all() or np.any((p<0)|(p>1)):raise ValueError('Invalid probabilities')
    return p

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--threads',type=int,default=4)
    parser.add_argument('--batch-size',type=int,default=64)
    args=parser.parse_args();torch.set_num_threads(args.threads);torch.set_num_interop_threads(1)
    if args.batch_size<1:raise ValueError('Batch size must be positive')
    args.output.parent.mkdir(parents=True,exist_ok=True);manifest_path=args.output.with_suffix('.csv.manifest.json')
    model_hash=sha256(args.model);input_hash=sha256(args.input)
    if args.output.exists():
        if not manifest_path.exists():raise ValueError('Existing output lacks validation manifest')
        old=json.loads(manifest_path.read_text())
        if old['model_sha256']!=model_hash or old['input_sha256']!=input_hash or old['output_sha256']!=sha256(args.output):
            raise ValueError('Existing prediction fingerprints changed')
        print('Reused complete verified prediction:',args.output);return
    model,bundle=load_model(args.model);temporary=args.output.with_suffix('.csv.tmp')
    keys=set();n=0;total_reads=0
    with Measure() as measure:
        with temporary.open('w',newline='',encoding='utf-8') as handle:
            writer=csv.writer(handle);writer.writerow(['transcript_id','transcript_position','score']);pending=[]
            def write(rows):
                nonlocal n,total_reads
                scores=score_batch(model,rows)
                for row,p in zip(rows,scores):
                    key=(row[0],row[1]);keys.add(key);total_reads+=len(row[3]);n+=1
                    writer.writerow([key[0],key[1],format(float(p),'.17g')])
            for site in iter_sites(args.input):
                pending.append(site)
                if len(pending)==args.batch_size:
                    write(pending);pending=[]
                    if n%10048==0:print(f'Predicted {n:,} sites',flush=True)
            if pending:write(pending)
        if not n:raise ValueError('Empty input')
        # Independently reload the exact CSV about to be committed.
        seen=set()
        with temporary.open(newline='',encoding='utf-8') as handle:
            reader=csv.DictReader(handle)
            if reader.fieldnames!=['transcript_id','transcript_position','score']:raise ValueError('Wrong output header')
            for row in reader:
                key=(row['transcript_id'],int(row['transcript_position']));p=float(row['score'])
                if key in seen or not np.isfinite(p) or not 0<=p<=1:raise ValueError('Invalid CSV')
                seen.add(key)
        if seen!=keys or len(seen)!=n:raise ValueError('Incomplete CSV input coverage')
        if sha256(args.model)!=model_hash or sha256(args.input)!=input_hash:raise ValueError('Source changed during prediction')
        os.replace(temporary,args.output)
    save_json(manifest_path,{'status':'complete','input_sha256':input_hash,'model_sha256':model_hash,
        'output_sha256':sha256(args.output),'n_sites':n,'n_reads':total_reads,
        'exact_input_key_coverage':True,'all_reads_used':True,'labels_or_genes_required':False,
        'resources':measure.record,'threads':args.threads,'batch_size':args.batch_size})
    print(f'PASS {n:,} unique sites, all {total_reads:,} reads, same frozen model {model_hash}',flush=True)

if __name__=='__main__':main()
