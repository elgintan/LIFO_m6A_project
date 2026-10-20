"""Scientific correctness and failure cases. All fixtures are synthetic software tests."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/compare_predictions.py'
spec=importlib.util.spec_from_file_location('compare',SCRIPT)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


class Correctness(unittest.TestCase):
    def test_repeated_runs_do_not_increase_replicate_weight(self):
        d=pd.DataFrame({'transcript_id':['t']*3,'transcript_position':[1]*3,'cell_line':['A']*3,'biological_replicate':[1,1,2],'run_id':['r1','r2','r3'],'n_reads':[100,1000,20],'score':[0.,0.,1.]})
        r,c=mod.aggregate_run_scores(d)
        self.assertEqual(c.score.iloc[0],.5)
        self.assertNotAlmostEqual(c.score.iloc[0],d.score.mean())
        self.assertEqual(c.n_replicates.iloc[0],2)

    def test_missing_sites_excluded_from_pair_not_negative(self):
        a=pd.DataFrame({'transcript_id':['t','t'],'transcript_position':[1,2],'score':[.8,.2],'log_reads':[4.,4.],'score_min':[.7,.1],'score_max':[.9,.3]})
        b=a.iloc[[0]].copy();b['score']=.1;b['score_min']=0;b['score_max']=.2
        m=mod.compare_pair(a,b)
        self.assertEqual(len(m),1);self.assertAlmostEqual(m.delta_score.iloc[0],.7)

    def test_range_overlap_blocks_robust_direction(self):
        a=pd.DataFrame({'transcript_id':['t'],'transcript_position':[1],'score':[.8],'log_reads':[4.],'score_min':[.4],'score_max':[1.]})
        b=a.copy();b['score']=.2;b['score_min']=0;b['score_max']=.6
        m=mod.compare_pair(a,b)
        self.assertFalse(m.all_replicate_pairs_positive.iloc[0]);self.assertFalse(m.all_replicate_pairs_negative.iloc[0])

    def test_invalid_scores_positions_and_duplicates_rejected(self):
        good=pd.DataFrame({'transcript_id':['t'],'transcript_position':[1],'score':[.3]})
        for col,value in [('score',np.nan),('score',np.inf),('score',1.1),('score',-.1),('transcript_position',.5),('transcript_position',-1)]:
            bad=good.copy();bad[col]=value
            with self.subTest(col=col,value=value),self.assertRaises(ValueError):mod.validate_scores(bad)
        with self.assertRaises(ValueError):mod.validate_scores(pd.concat([good,good]))

    def test_full_cli_and_simulation_guard(self):
        # This fixture deliberately declares valid metadata to exercise analysis;
        # it is not a biological dataset and is removed when the test ends.
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);runs=['A1','A2','B1','B2'];records=[]
            base={'transcript_id':['t','t'],'transcript_position':[1,2]}
            for run,scores in zip(runs,[[.9,.2],[.8,.3],[.1,.2],[.2,.3]]):
                pd.DataFrame({**base,'score':scores}).to_csv(root/(run+'.csv'),index=False)
                records.append({'run_id':run,'cell_line':run[0],'biological_replicate':int(run[1]),'sequencing_run':1,'prediction_file':run+'.csv','coverage_file':'coverage.csv','min_reads':20,'model_version':'software-test-fixture-v1','reference_version':'fixture-ref','coordinate_convention':'fixture-position','real_predictions':True})
            m=pd.DataFrame(records);m.to_csv(root/'manifest.csv',index=False)
            (root/'MODEL_INFO.md').write_text('Synthetic SOFTWARE TEST fixture only. Model: software-test-fixture-v1; reference fixture-ref; positions are fixture coordinates. No biological claims.')
            pd.DataFrame({**base,**{r:[50,50] for r in runs}}).to_csv(root/'coverage.csv',index=False)
            pd.DataFrame({**base,'gene_id':['g','g'],'gene_name':['G','G'],'kind':['annotated','annotated']}).to_csv(root/'annotations.csv',index=False)
            cmd=[sys.executable,str(SCRIPT),'--manifest',str(root/'manifest.csv'),'--coverage-matrix',str(root/'coverage.csv'),'--annotations',str(root/'annotations.csv'),'--coverage','20,50','--out',str(root/'test_output')]
            result=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            pair=pd.read_csv(root/'test_output/pairs/A__B__cov20.csv.gz')
            self.assertAlmostEqual(pair.delta_score.iloc[0],.7)
            self.assertTrue(pair.candidate_large_difference.iloc[0]);self.assertFalse(pair.candidate_large_difference.iloc[1])
            self.assertEqual(len(pd.read_csv(root/'test_output/all_line_common_scores_cov20.csv.gz')),2)
            core=['run_id','cell_line','biological_replicate','sequencing_run','prediction_file','coverage_file','min_reads','reference_version','model_version']
            m[core].to_csv(root/'manifest.csv',index=False)
            core_cmd=cmd.copy();core_cmd[-1]=str(root/'core_output')
            core_run=subprocess.run(core_cmd+['--confirm-real-predictions'],capture_output=True,text=True)
            self.assertEqual(core_run.returncode,0,core_run.stdout+core_run.stderr)
            core_pair=pd.read_csv(root/'core_output/pairs/A__B__cov20.csv.gz')
            pd.testing.assert_frame_equal(pair,core_pair)
            # Coverage declared by the manifest must be the actual matrix used.
            wrong=m[core].copy();wrong['coverage_file']='another_sample.csv';wrong.to_csv(root/'manifest.csv',index=False)
            wrong_cmd=cmd.copy();wrong_cmd[-1]=str(root/'wrong_coverage')
            bad=subprocess.run(wrong_cmd+['--confirm-real-predictions'],capture_output=True,text=True)
            self.assertNotEqual(bad.returncode,0);self.assertIn('coverage_file does not match',bad.stderr)
            m['real_predictions']=False;m.to_csv(root/'manifest.csv',index=False)
            cmd[-1]=str(root/'refused_output');refused=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(refused.returncode,0);self.assertIn('simulated data refused',refused.stderr)


if __name__=='__main__':unittest.main(verbosity=2)
