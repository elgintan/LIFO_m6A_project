"""Resume the remaining authorised local pipeline after disjoint fold workers.

Every stage is a fresh process. Existing completed outputs are checked and
reused; a failed stage stops the pipeline. No publication or submission occurs.
"""
import json,os,subprocess,sys,time
from pathlib import Path
import psutil

ROOT=Path(__file__).resolve().parent
def record(obj):
    p=ROOT/'pipeline_status.json';temporary=p.with_suffix('.tmp')
    temporary.write_text(json.dumps(obj,indent=2)+'\n');os.replace(temporary,p)

def main():
    os.chdir(ROOT)
    previous=ROOT/'pipeline_status.json'
    if previous.exists():
        status=json.loads(previous.read_text())
        if status.get('status')=='complete':
            print('Pipeline already complete; retained evidence is unchanged.',flush=True)
            return
        status.setdefault('resume_history',[]).append({'resumed_unix':time.time(),
            'previous_status':status.get('status'),'previous_stage':status.get('stage'),
            'previous_error':status.get('error')})
        status.update(status='running')
        status.pop('error',None)
    else:
        status={'status':'running','started_unix':time.time(),'completed_stages':[],'commands':[]}
    record(status);finalists=json.loads((ROOT/'runs/finalists.json').read_text())
    # Current worker groups have unique ownership, established before launch.
    while True:
        missing=[(c['id'],f) for c in finalists for f in range(5)
                 if not (ROOT/f"runs/{c['id']}_fold{f}_refit/complete.json").exists()]
        if not missing:break
        owners={}
        for path in (ROOT/'runs').glob('worker_*.json'):
            worker=json.loads(path.read_text())
            for f in worker['folds']:owners[(worker['candidate'],f)]=worker
        for key in missing:
            owner=owners.get(key)
            if owner is None:raise RuntimeError(f'No worker owns unfinished fold {key}')
            if owner['status']=='complete' or not psutil.pid_exists(owner['pid']):
                raise RuntimeError(f'Worker stopped before completing {key}; inspect logs and resume its exact command')
        status['stage']='waiting_for_disjoint_fold_fits';status['pending_folds']=missing;record(status)
        time.sleep(10)
    status.pop('pending_folds',None)
    def run(name,args):
        if name in status['completed_stages']:
            print('RETAIN completed stage',name,flush=True)
            return
        command=[sys.executable,'-u',*args];status['stage']=name;status['commands'].append(command);record(status)
        print('START',name,' '.join(args),flush=True)
        with (ROOT/f'pipeline_{name}.log').open('a',encoding='utf-8') as log:
            subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT)
        status['completed_stages'].append(name);record(status);print('COMPLETE',name,flush=True)
    run('aggregate_cv',['train.py','--phase','cv','--max-epochs','20','--patience','5','--threads','4'])
    run('final_fit',['train.py','--phase','final','--max-epochs','20','--patience','5','--threads','4'])
    run('verify_final',['verify.py','--model','runs/final_model.pt','--output','verification/final_verification.json'])
    for n in range(3):
        run(f'predict_data{n}',['predict.py','--input',f'../data{n}/dataset{n}.json.gz','--model','runs/final_model.pt',
            '--output',f'predictions/LIFO_dataset{n}.csv','--threads','4','--batch-size',('8' if n==2 else '32')])
    run('predict_example',['predict.py','--input','examples/input_10_sites.json','--model','runs/final_model.pt',
        '--output','examples/predictions.csv','--threads','4','--batch-size','32'])
    frozen=json.loads((ROOT/'runs/frozen_specification.json').read_text())
    stages=[('data0_oof_development','../data0/data.info.labelled',f"runs/{frozen['config']['id']}/oof_predictions.csv"),
            ('data0_in_sample','../data0/data.info.labelled','predictions/LIFO_dataset0.csv'),
            ('data1_frozen_selection','../data1/data.info','predictions/LIFO_dataset1.csv'),
            ('data2_pending','../data2/data.info','predictions/LIFO_dataset2.csv')]
    for stage,labels,predictions in stages:
        run(f'evaluate_{stage}',['evaluate.py','--labels',labels,'--predictions',predictions,
            '--output-dir',f'evaluations/{stage}','--stage',stage])
    run('diagnostics',['plot_diagnostics.py','--runs','runs','--cache','cache/data0','--threads','4'])
    run('report',['report.py','--runs','runs','--predictions-dir','predictions'])
    status.update(status='complete',stage='complete',finished_unix=time.time());record(status)
    subprocess.run([sys.executable,'status.py'],check=True)
    print('ALL TRAINING, FROZEN EVALUATION, PREDICTIONS AND REPORT COMPLETE',flush=True)

if __name__=='__main__':
    try:main()
    except BaseException as error:
        p=ROOT/'pipeline_status.json';status=json.loads(p.read_text()) if p.exists() else {}
        status.update(status='failed_or_interrupted',error=str(error),stopped_unix=time.time());record(status)
        raise
