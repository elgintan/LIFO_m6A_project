import sys
from pathlib import Path
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from extract_biological_case_evidence import aggregate_cases


class EvidenceTests(unittest.TestCase):
    def fixture(self):
        return pd.DataFrame([{"case_id": "CASE", "transcript_id": "TX", "transcript_position": 1,
                              "cell_line": "A549", "biological_replicate": group, "run_id": run,
                              "score": score, "n_reads": reads}
                             for group, run, score, reads in [(1, "a", .2, 20), (1, "b", .8, 100),
                                                             (2, "c", .9, 100), (3, "d", None, 0)]])

    def test_equal_group_weights_and_absence(self):
        groups, lines = aggregate_cases(self.fixture(), 20)
        self.assertEqual(len(groups), 2)
        self.assertAlmostEqual(lines.score.iloc[0], .7)
        self.assertEqual(lines.n_eligible_runs.iloc[0], 3)
        self.assertEqual(lines.n_replicates.iloc[0], 2)

    def test_depth_changes_eligible_runs_not_original_scores(self):
        original = self.fixture()
        before = original.copy(deep=True)
        groups, lines = aggregate_cases(original, 50)
        self.assertAlmostEqual(lines.score.iloc[0], .85)
        self.assertEqual(lines.n_eligible_runs.iloc[0], 2)
        self.assertEqual(groups.n_runs.tolist(), [1, 1])
        pd.testing.assert_frame_equal(original, before)

    def test_insufficient_groups_remain_explicit(self):
        frame = self.fixture()
        frame.loc[frame.run_id.eq("c"), "n_reads"] = 30
        _, lines = aggregate_cases(frame, 100)
        self.assertEqual(lines.n_replicates.iloc[0], 1)
        self.assertAlmostEqual(lines.score.iloc[0], .8)


if __name__ == "__main__":
    unittest.main()
