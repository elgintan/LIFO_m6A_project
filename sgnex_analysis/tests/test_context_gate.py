"""Synthetic scientific-contract checks; no real model or signals are executed."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/compare_predictions.py'
SPEC=importlib.util.spec_from_file_location('compare_context',SCRIPT)
mod=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mod)


class ContextGate(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.runs=['A1','A1b','A2','B1','B2','C1','C2']
        keys={'transcript_id':['t']*4,'transcript_position':[1,2,3,4]}
        manifest=[]
        scores={'A1':.9,'A1b':.7,'A2':.6,'B1':.2,'B2':.4,'C1':.5,'C2':.5}
        for run in self.runs:
            positions=[1,3,4] if run.startswith('C') else [1,2,3,4]
            raw='t.v1' if run=='A1' else 't'
            pd.DataFrame({'transcript_id':[raw]*len(positions),'transcript_position':positions,
                          'score':[scores[run]]*len(positions)}).to_csv(self.root/(run+'.csv'),index=False)
            manifest.append({'run_id':run,'cell_line':run[0],
                'biological_replicate':1 if run.endswith('1') or run.endswith('b') else 2,
                'sequencing_run':2 if run.endswith('b') else 1,
                'prediction_file':run+'.csv','coverage_file':'coverage.csv','min_reads':20,
                'reference_version':'synthetic_ref','model_version':'synthetic_software_model'})
        self.manifest=pd.DataFrame(manifest);self.manifest.to_csv(self.root/'manifest.csv',index=False)
        self.cov=pd.DataFrame({**keys,**{run:[100,0 if run.startswith('C') else (25 if run=='B2' else 100),100,100] for run in self.runs}})
        self.cov.to_csv(self.root/'coverage.csv',index=False)
        pd.DataFrame({**keys,'kind':['annotated']*4,'gene_id':['g']*4,'gene_name':['G']*4}).to_csv(self.root/'annotations.csv',index=False)
        pd.DataFrame({'run_id':['A1'],'raw_transcript_id':['t.v1'],'transcript_id':['t']}).to_csv(self.root/'aliases.csv',index=False)
        (self.root/'MODEL_INFO.md').write_text('Synthetic software fixture; no biological data or model.')
        self.qc=self.root/'qc';self.qc.mkdir()
        self.table=pd.DataFrame({**keys,'all_source_consistent':[True,True,False,False],
            'scored_consistent':[True,True,True,False],
            'encoded7mer_all_source':['AAAACAA','AAAACAA','',''],
            'encoded7mer_scored':['AAAACAA','AAAACAA','AAAACAA',''],
            'n_source_runs':[7,7,7,7],'n_scored_runs':[7,5,7,7],
            'n_encoded_contexts_all_source':[1,1,2,2],'n_encoded_contexts_scored':[1,1,1,2],
            'ambiguous_context_all_source':[False]*4,'ambiguous_context_scored':[False]*4})
        self.input_hashes={name:mod.sha(self.root/file) for name,file in
            [('manifest','manifest.csv'),('coverage','coverage.csv'),('annotations','annotations.csv'),('aliases','aliases.csv')]}
        self.predictions=[{'run_id':run,'path':run+'.csv','sha256':mod.sha(self.root/(run+'.csv'))} for run in self.runs]
        self.receipt={'status':'complete','inputs':{**{k:{'sha256':v} for k,v in self.input_hashes.items()},
                      'predictions':self.predictions,'model_sha256':'synthetic_software_fixture'},'outputs':{}}
        self.write_qc()

    def write_qc(self):
        path=self.qc/'key_context_qc.csv.gz';self.table.to_csv(path,index=False)
        self.receipt['outputs'][path.name]={'sha256':mod.sha(path),'size_bytes':path.stat().st_size}
        (self.qc/'complete.json').write_text(json.dumps(self.receipt))

    def load(self,policy='all-source-consistent'):
        return mod.load_context_gate(self.qc,policy,self.cov,self.input_hashes,self.predictions)

    def args(self,policy,out):
        return argparse.Namespace(manifest=str(self.root/'manifest.csv'),out=str(self.root/out),
            coverage_matrix=str(self.root/'coverage.csv'),annotations=str(self.root/'annotations.csv'),
            aliases=str(self.root/'aliases.csv'),model_info=None,confirm_real_predictions=True,
            coverage='20,50,100',cutoffs='0.5,0.7,0.9',min_replicates=2,
            require_all_replicates=False,max_coverage_ratio=2,min_delta=.2,
            allow_missing_predictions=False,context_qc=str(self.qc),context_policy=policy)

    def test_policies_preserve_low_read_conflict_as_distinct_sensitivity(self):
        primary,_=self.load();scored,_=self.load('scored-consistent')
        self.assertEqual(primary.context_qualified.tolist(),[True,True,False,False])
        self.assertEqual(scored.context_qualified.tolist(),[True,True,True,False])

    def test_gate_is_bound_to_inputs_predictions_and_final_table(self):
        for name in self.input_hashes:
            with self.subTest(input=name):
                changed=dict(self.input_hashes);changed[name]='changed'
                with self.assertRaisesRegex(ValueError,'input hash mismatch'):
                    mod.load_context_gate(self.qc,'all-source-consistent',self.cov,changed,self.predictions)
        bad=[dict(p) for p in self.predictions];bad[0]['sha256']='changed'
        with self.assertRaisesRegex(ValueError,'prediction hash mismatch'):
            mod.load_context_gate(self.qc,'all-source-consistent',self.cov,self.input_hashes,bad)
        with (self.qc/'key_context_qc.csv.gz').open('ab') as handle:handle.write(b'x')
        with self.assertRaisesRegex(ValueError,'hash/size mismatch'):self.load()

    def test_missing_extra_duplicate_keys_and_unknown_boolean_rejected(self):
        original=self.table.copy()
        for change in ['missing','extra','duplicate','boolean']:
            with self.subTest(change=change):
                self.table=original.copy()
                if change=='missing':self.table=self.table.iloc[:-1]
                elif change=='extra':self.table.loc[3,'transcript_position']=99
                elif change=='duplicate':self.table.loc[3,'transcript_position']=1
                else:self.table['all_source_consistent']=self.table.all_source_consistent.astype(str);self.table.loc[0,'all_source_consistent']='unknown'
                self.write_qc()
                with self.assertRaises(ValueError):self.load()

    def test_inconsistent_safe_flag_and_incomplete_or_wrong_run_receipt_rejected(self):
        original=self.table.copy()
        self.table.loc[0,'encoded7mer_all_source']='AAANCAA';self.write_qc()
        with self.assertRaisesRegex(ValueError,'qualification flag'):self.load()
        self.table=original;self.write_qc()
        self.receipt['status']='running';self.write_qc()
        with self.assertRaisesRegex(ValueError,'not complete'):self.load()
        self.receipt['status']='complete';self.receipt['inputs']['predictions']=self.predictions[:-1];self.write_qc()
        with self.assertRaisesRegex(ValueError,'run universe'):self.load()

    def test_original_exports_validated_before_exclusion(self):
        # Even a key vetoed by context QC cannot hide an invalid source score.
        bad=pd.read_csv(self.root/'A2.csv');bad.loc[bad.transcript_position.eq(4),'score']=2
        bad.to_csv(self.root/'A2.csv',index=False)
        with self.assertRaisesRegex(ValueError,'Scores must be finite'):
            mod.main(self.args('all-source-consistent','invalid_source'))
        self.assertFalse((self.root/'invalid_source'/'analysis_receipt.json').exists())

    def test_full_analysis_keeps_hierarchy_separate_populations_and_excluded_evidence(self):
        original_hashes={run:mod.sha(self.root/(run+'.csv')) for run in self.runs}
        mod.main(self.args('all-source-consistent','primary'))
        out=self.root/'primary'
        pair=pd.read_csv(out/'pairs/A__B__cov20.csv.gz')
        all_line=pd.read_csv(out/'all_line_common_scores_cov20.csv.gz')
        self.assertEqual(pair.transcript_position.tolist(),[1,2])
        self.assertEqual(all_line.transcript_position.tolist(),[1])
        self.assertAlmostEqual(pair.loc[pair.transcript_position.eq(1),'score_a'].iloc[0],.7)
        self.assertAlmostEqual(pair.loc[pair.transcript_position.eq(1),'score_b'].iloc[0],.3)
        self.assertEqual(len(pd.read_csv(out/'pairs/A__B__cov50.csv.gz')),1)
        excluded=pd.read_csv(out/'context_excluded_run_scores.csv.gz')
        self.assertEqual(set(excluded.transcript_position),{3,4})
        self.assertEqual(len(excluded),14)
        self.assertEqual(excluded.loc[excluded.run_id.eq('A1'),'raw_transcript_id'].unique().tolist(),['t.v1'])
        impacts=pd.read_csv(out/'context_population_impact.csv')
        counts=impacts[(impacts.coverage_threshold==20)&(impacts.population=='all_line_common')].set_index('stage').n_sites
        self.assertEqual(counts.to_dict(),{'before_context_qc':3,'after_context_qc':1})
        receipt=json.loads((out/'analysis_receipt.json').read_text())
        self.assertEqual(receipt['context_qualification']['policy'],'all-source-consistent')
        self.assertEqual(receipt['aliases_sha256'],self.input_hashes['aliases'])
        self.assertEqual(receipt['script_sha256'],mod.sha(SCRIPT))
        self.assertEqual(original_hashes,{run:mod.sha(self.root/(run+'.csv')) for run in self.runs})
        mod.main(self.args('scored-consistent','sensitivity'))
        self.assertEqual(len(pd.read_csv(self.root/'sensitivity/pairs/A__B__cov20.csv.gz')),3)


class ConcordancePartitionTests(unittest.TestCase):
    def test_shared_keys_rank_arithmetic_constant_and_unit_order(self):
        rows=[]
        for unit,values in [('C',[.1,.2,.3]),('A',[.1,.2,.3]),('B',[.3,.2,.1]),('D',[.4,.4,.4])]:
            rows.extend({'transcript_id':'tx.v1','transcript_position':i+1,'score':value,'run_id':unit}
                        for i,value in enumerate(values))
        rows.append({'transcript_id':'unmatched','transcript_position':99,'score':.99,'run_id':'C'})
        result=mod.concordance(pd.DataFrame(rows),'run_id',20)
        self.assertEqual([(r['a'],r['b']) for r in result],[('C','A'),('C','B'),('C','D'),('A','B'),('A','D'),('B','D')])
        self.assertTrue(all(r['n_common_sites']==3 for r in result))
        self.assertAlmostEqual(result[0]['spearman'],1)
        self.assertEqual(result[0]['median_absolute_delta'],0)
        self.assertAlmostEqual(result[1]['spearman'],-1)
        self.assertAlmostEqual(result[1]['median_absolute_delta'],.2)
        self.assertIsNone(result[2]['spearman'])
        self.assertAlmostEqual(result[2]['median_absolute_delta'],.2)
        self.assertEqual(rows[0]['transcript_id'],'tx.v1')


if __name__=='__main__':unittest.main(verbosity=2)
