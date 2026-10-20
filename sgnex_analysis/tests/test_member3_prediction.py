"""Optional candidate-inference checks; no model training or biological test."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=Path(os.environ.get('MEMBER3_CANDIDATE_DIR', ROOT.parent/'model_samuel')).resolve()
AVAILABLE=all((CANDIDATE/p).is_file() for p in [
    'code/features.py','artifact/model.txt','artifact/model_card.json',
    'artifact/kmer_baseline.csv','examples/input_10_sites.json','examples/predictions.csv'])

@unittest.skipUnless(importlib.util.find_spec('lightgbm'), 'Install the separate Member 3 prediction environment')
@unittest.skipUnless(AVAILABLE, 'Provide the canonical model_samuel files or set MEMBER3_CANDIDATE_DIR')
class Member3Prediction(unittest.TestCase):
    def test_batched_inference_preserves_model_and_audits_eligibility(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);source=CANDIDATE/'examples/input_10_sites.json'
            expected=pd.read_csv(CANDIDATE/'examples/predictions.csv')
            base=[sys.executable,str(ROOT/'scripts/predict_member3_run.py'),'--candidate-dir',str(CANDIDATE),'--input',str(source),'--run-id','software-smoke-example','--batch-sites','3']
            good=subprocess.run(base+['--output',str(d/'pred.csv')],capture_output=True,text=True)
            self.assertEqual(good.returncode,0,good.stdout+good.stderr)
            actual=pd.read_csv(d/'pred.csv');pd.testing.assert_frame_equal(expected.iloc[:,:2],actual.iloc[:,:2]);np.testing.assert_allclose(expected.score,actual.score,rtol=0,atol=1e-12)
            side=pd.read_csv(d/'pred.site_metadata.csv.gz');self.assertEqual(len(side),10);self.assertTrue(side.prediction_status.eq('scored').all())
            high=subprocess.run(base+['--output',str(d/'higher.csv'),'--min-reads','25'],capture_output=True,text=True)
            self.assertEqual(high.returncode,0,high.stderr)
            selected=pd.read_csv(d/'higher.csv');self.assertEqual(len(selected),2)
            subset=expected.merge(side.query('n_reads_finite >=25')[['transcript_id','transcript_position']],on=['transcript_id','transcript_position'])
            np.testing.assert_allclose(subset.score,selected.score,rtol=0,atol=1e-12)
            # Cross-batch duplicates fail and never become a completed CSV.
            duplicate=d/'duplicate.json';lines=source.read_text().splitlines();duplicate.write_text('\n'.join(lines+[lines[0]])+'\n')
            fail=[sys.executable,str(ROOT/'scripts/predict_member3_run.py'),'--candidate-dir',str(CANDIDATE),'--input',str(duplicate),'--run-id','duplicate-software-fixture','--batch-sites','3','--output',str(d/'bad.csv')]
            bad=subprocess.run(fail,capture_output=True,text=True)
            self.assertNotEqual(bad.returncode,0);self.assertFalse((d/'bad.csv').exists());self.assertFalse((d/'bad.receipt.json').exists())

if __name__=='__main__':unittest.main(verbosity=2)
