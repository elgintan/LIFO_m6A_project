"""Strict same-site binary evaluation; no training, calibration or threshold fitting."""
import argparse,os,json,time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve,precision_recall_curve
from common import Measure,metrics,save_json
from data import sha256

def evaluate(labels,predictions,out,stage):
    key=['transcript_id','transcript_position'];out=Path(out);out.mkdir(parents=True,exist_ok=True)
    label_path=Path(labels);label_hash=sha256(labels);prediction_hash=sha256(predictions)
    with Measure() as measure:
        labels=pd.read_csv(labels);pred=pd.read_csv(predictions,float_precision='round_trip')
        if pred.columns.tolist()!=key+['score']:raise ValueError('Prediction columns differ from contract')
        if labels.duplicated(key).any() or pred.duplicated(key).any():raise ValueError('Duplicate keys')
        joined=labels.merge(pred,on=key,validate='one_to_one',how='outer',indicator=True)
        if not (joined['_merge']=='both').all():raise ValueError('Different site coverage')
        y=joined.label.to_numpy();p=joined.score.to_numpy()
        if not np.isfinite(y).all() or np.any((y<0)|(y>1)):raise ValueError('Invalid label values')
        if not np.isfinite(p).all() or np.any((p<0)|(p>1)):raise ValueError('Invalid probability values')
        if stage=='data2_pending':
            result={'stage':stage,'n_sites':len(y),'label_values':sorted(np.unique(y).tolist()),'binary_metrics':None,
                'status':'coverage_passed_scoring_pending'}
        else:
            result={'stage':stage,**metrics(y,p),'status':'complete'}
            plot(y,p,result,out,stage)
    if label_hash!=sha256(label_path) or prediction_hash!=sha256(predictions):raise ValueError('Evaluation source changed')
    result['resources']=measure.record;result['predictions_sha256']=prediction_hash;result['labels_sha256']=label_hash
    save_json(out/'metrics.json',result);print(stage,result,flush=True);return result

def plot(y,p,result,out,stage):
    os.environ['MPLCONFIGDIR']=str(Path(__file__).resolve().parent/'.matplotlib_cache')
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fpr,tpr,_=roc_curve(y,p);pr,rec,_=precision_recall_curve(y,p)
    for name,x,z,xlabel,ylabel,score in [('roc',fpr,tpr,'False positive rate','True positive rate',result['roc_auc']),
            ('pr',rec,pr,'Recall','Precision',result['pr_auc_trapezoid'])]:
        fig,ax=plt.subplots(figsize=(6,5));ax.plot(x,z,label=f'Advanced model AUC {score:.4f}')
        if name=='roc':ax.plot([0,1],[0,1],'--',color='gray')
        else:ax.axhline(y.mean(),color='gray',linestyle='--',label=f'Positive fraction {y.mean():.4f}')
        ax.set(xlim=(0,1),ylim=(0,1),xlabel=xlabel,ylabel=ylabel,title=stage);ax.legend();fig.tight_layout()
        fig.savefig(out/f'{name}_curve.png',dpi=150);plt.close(fig)
    confusion=np.array([[result['tn'],result['fp']],[result['fn'],result['tp']]])
    fig,ax=plt.subplots(figsize=(5,4));ax.imshow(confusion,cmap='Blues')
    for a in range(2):
        for b in range(2):ax.text(b,a,f'{confusion[a,b]:,}',ha='center',va='center',color='white' if confusion[a,b]>confusion.max()/2 else 'black')
    ax.set(xticks=[0,1],yticks=[0,1],xticklabels=['Unmodified','Modified'],yticklabels=['Unmodified','Modified'],
        xlabel='Predicted at 0.5',ylabel='Actual',title=stage);fig.tight_layout();fig.savefig(out/'confusion_matrix.png',dpi=150);plt.close(fig)
    # Fixed ten bins: a descriptive calibration diagnostic, never used to refit.
    fig,ax=plt.subplots(figsize=(5,4));means=[];observed=[];counts=[]
    for b in range(10):
        at=(p>=b/10)&(p<(b+1)/10 if b<9 else p<=1)
        if at.any():means.append(float(p[at].mean()));observed.append(float(y[at].mean()));counts.append(int(at.sum()))
    ax.plot([0,1],[0,1],'--',color='gray');ax.plot(means,observed,'o-');ax.set(xlabel='Mean predicted probability',ylabel='Observed positive fraction',title=stage)
    fig.tight_layout();fig.savefig(out/'reliability.png',dpi=150);plt.close(fig)
    save_json(out/'reliability.json',{'mean_prediction':means,'positive_fraction':observed,'sites':counts})

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels',type=Path,required=True);parser.add_argument('--predictions',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--stage',choices=['data0_oof_development','data0_in_sample','data1_frozen_selection','data2_pending'],required=True)
    args=parser.parse_args()
    output=args.output_dir/'metrics.json'
    if output.exists():
        old=json.loads(output.read_text())
        if old['stage']!=args.stage or old['predictions_sha256']!=sha256(args.predictions) or old['labels_sha256']!=sha256(args.labels):raise ValueError('Changed existing evaluation')
        print('Reused saved evaluation',output);return
    if args.stage=='data1_frozen_selection':
        root=Path(__file__).resolve().parent
        frozen=json.loads((root/'runs/final_model_manifest.json').read_text())
        pred_manifest=json.loads(args.predictions.with_suffix('.csv.manifest.json').read_text())
        if frozen['model_sha256']!=pred_manifest['model_sha256']:raise ValueError('Data1 requires frozen final model')
        log_path=root/'runs/data1_evaluation_log.json'
        entries=json.loads(log_path.read_text()) if log_path.exists() else []
        entries.append({'time_unix':time.time(),'model_sha256':frozen['model_sha256'],
                        'predictions_sha256':sha256(args.predictions),'status':'evaluation_started'})
        save_json(log_path,entries)
        result=evaluate(args.labels,args.predictions,args.output_dir,args.stage)
        entries[-1]['status']='complete';entries[-1]['metrics_sha256']=sha256(output);save_json(log_path,entries)
        frozen.setdefault('data1_evaluation_count_at_freeze',frozen.get('data1_evaluation_count',0))
        frozen['data1_evaluation_count']=sum(e['status']=='complete' and e['model_sha256']==frozen['model_sha256'] for e in entries)
        save_json(root/'runs/final_model_manifest.json',frozen)
    else:evaluate(args.labels,args.predictions,args.output_dir,args.stage)

if __name__=='__main__':main()
