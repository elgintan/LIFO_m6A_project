import sys
from pathlib import Path
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from report_biological_cases import training_keys


class TrainingKeyTests(unittest.TestCase):
    def setUp(self):
        self.cases = pd.DataFrame([{"case_id": "known", "gene_id": "G1", "gene_name": "GENE1", "transcript_id": "TX1", "transcript_position": 1},
                                   {"case_id": "new", "gene_id": "G2", "gene_name": "GENE2", "transcript_id": "TX2", "transcript_position": 2}])
        self.labels = pd.DataFrame([{"gene_id": "G1", "transcript_id": "TX1", "transcript_position": 1, "label": 0}])

    def test_unseen_key_is_unknown_not_negative(self):
        result = training_keys(self.cases, self.labels)
        self.assertEqual(result.training_key_present.tolist(), [True, False])
        self.assertEqual(result.label.iloc[0], 0)
        self.assertTrue(pd.isna(result.label.iloc[1]))
        self.assertFalse(result.independent_validation.any())

    def test_conflicting_gene_identity_fails(self):
        self.labels.loc[0, "gene_id"] = "OTHER"
        with self.assertRaises(ValueError):
            training_keys(self.cases, self.labels)

    def test_duplicate_training_key_fails(self):
        with self.assertRaises(ValueError):
            training_keys(self.cases, pd.concat([self.labels, self.labels]))


if __name__ == "__main__":
    unittest.main()
