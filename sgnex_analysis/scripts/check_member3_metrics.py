"""Recompute supplied Member 3 metrics against Member 1 derived label tables.

Labels can be the .csv.gz tables from Member1_Analysis_Package.zip. No training
or assay validation is performed. This utility does not rank/select models.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score,precision_recall_curve,auc,average_precision_score

KEY=['transcript_id','transcript_position']


def metrics(frame):
    p,r,_=precision_recall_curve(frame.label,frame.score,drop_intermediate=False)
    roc=roc_auc_score(frame.label,frame.score);pr=auc(r,p)
    return {'roc_auc':float(roc),'pr_auc_trapezoid':float(pr),'average_precision':float(average_precision_score(frame.label,frame.score)),'selection_score':float((roc+pr)/2)}


def check(a):
    src=Path(a.candidate_dir);result={}
    for dataset,labels_path in [('data0',a.data0_labels),('data1',a.data1_labels)]:
        labels=pd.read_csv(labels_path,usecols=KEY+['label'])
        pred=pd.read_csv(src/'outputs'/('data0_oof.csv' if dataset=='data0' else 'data1_predictions.csv'))
        frame=labels.merge(pred,on=KEY,how='outer',validate='one_to_one',indicator=True)
        if not frame['_merge'].eq('both').all() or not np.isfinite(frame.score).all() or not frame.score.between(0,1).all():raise ValueError('Prediction/label join or score check failed')
        expected=json.loads((src/'results'/('data0_cv_metrics.json' if dataset=='data0' else 'data1_metrics.json')).read_text())
        got=metrics(frame)
        for k,v in got.items():
            if abs(v-expected['pooled'][k])>1e-12:raise ValueError(dataset+' '+k+' differs')
        result[dataset]={'n_sites':len(frame),'n_positives':int(frame.label.sum()),'pooled':got,'matches_supplied_metrics':True}
        if dataset=='data0':
            folds=pd.read_csv(a.folds,usecols=KEY+['fold_id'])
            joined=frame.merge(folds,on=KEY,validate='one_to_one',suffixes=('','_shared'))
            if len(joined)!=len(frame) or not joined.fold_id.eq(joined.fold_id_shared).all():raise ValueError('OOF shared fold mismatch')
            per=[metrics(d) for _,d in frame.groupby('fold_id')]
            avg={k:float(np.mean([d[k] for d in per])) for k in per[0]}
            for k,v in avg.items():
                if abs(v-expected['mean_fold'][k])>1e-12:raise ValueError('Mean-fold metric differs')
            result[dataset]['mean_fold']=avg
    result['limitations']=['Derived-label agreement is not a raw-assay or training-isolation audit.','data1 was exposed during development.','No final-model selection or full-run SG-NEx analysis is performed.']
    Path(a.output).write_text(json.dumps(result,indent=2)+'\n');print('All recomputed metrics matched supplied records')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data0-labels',required=True);p.add_argument('--data1-labels',required=True);p.add_argument('--folds',required=True);p.add_argument('--candidate-dir',default=str(Path(__file__).resolve().parents[2]/'model_samuel'));p.add_argument('--output',required=True);check(p.parse_args())
