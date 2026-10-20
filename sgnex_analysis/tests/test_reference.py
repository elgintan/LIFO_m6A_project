"""Exact reference-window and mismatch checks on a synthetic software fixture."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import pandas as pd

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/check_reference_context.py'

class ReferenceCheck(unittest.TestCase):
    def test_verified_offset_and_mismatch(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'ref.fa').write_text('>t.1\nTTAAGACCAT\n')
            (p/'sites.csv').write_text('transcript_id,transcript_position,sequence_7mer,reference_transcript_id\nt,5,AAGACCA,t.1\n')
            cmd=[sys.executable,str(SCRIPT),'--sites',str(p/'sites.csv'),'--fasta',str(p/'ref.fa'),'--window-start-offset','-3','--out',str(p/'checked.csv')]
            good=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(good.returncode,0,good.stderr)
            d=pd.read_csv(p/'checked.csv');self.assertEqual(d.candidate_adenosine_zero_based.iloc[0],5)
            self.assertTrue(d.context_match.iloc[0])
            cmd[-3]='-2';bad=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(bad.returncode,0)
            self.assertFalse(pd.read_csv(p/'checked.csv').context_match.iloc[0])

if __name__=='__main__':unittest.main(verbosity=2)
