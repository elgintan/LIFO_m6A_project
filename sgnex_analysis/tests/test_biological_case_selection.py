import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

SPEC = importlib.util.spec_from_file_location("case_selection", Path(__file__).resolve().parents[1] / "scripts/select_biological_cases.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def row(position=2, a=.8, b=.2):
    return {"transcript_id": "TX", "transcript_position": position, "cell_line_a": "A549", "cell_line_b": "H9",
            "score_a": a, "score_b": b, "n_replicates_a": 2, "n_replicates_b": 3,
            "score_min_a": a - .01, "score_max_a": a + .01, "score_min_b": b - .01, "score_max_b": b + .01,
            "log_reads_a": np.log(120), "log_reads_b": np.log(130), "delta_score": a - b,
            "coverage_ratio": 130 / 120, "coverage_balanced": True, "replicate_separated": True,
            "candidate_large_difference": True, "gene_id": "G", "gene_name": "GENE",
            "analysis_sequence_7mer": "AAGACCA", "context_motif_5mer": "AGACC"}


class CaseSelectionTests(unittest.TestCase):
    def test_original_flags_independently_recomputed(self):
        frame = pd.DataFrame([row()])
        self.assertTrue(mod.validate_pair(frame).candidate_large_difference.iloc[0])
        frame.loc[0, "coverage_balanced"] = False
        with self.assertRaises(ValueError):
            mod.validate_pair(frame)

    def test_malformed_boolean_rejected(self):
        with self.assertRaises(ValueError):
            mod.strict_bool(pd.Series(["False", "unknown"]))
        self.assertEqual(mod.strict_bool(pd.Series(["False", "True"])).tolist(), [False, True])

    def test_touching_group_ranges_are_inconclusive(self):
        record = row()
        record.update(score_min_a=.5, score_max_b=.5, replicate_separated=False, candidate_large_difference=False)
        self.assertFalse(mod.validate_pair(pd.DataFrame([record])).replicate_separated.iloc[0])

    def test_depth_absence_and_direction_flip_not_persistent(self):
        tables = {d: pd.DataFrame([row()]) for d in mod.DEPTHS}
        tables[100] = pd.DataFrame([row(a=.2, b=.8)])
        self.assertEqual(len(mod.stable_pool(tables)), 0)
        tables[100] = pd.DataFrame([row()]).iloc[:0]
        self.assertEqual(len(mod.stable_pool(tables)), 0)

    def test_numeric_position_tie_break_and_minimum_groups(self):
        tables = {d: pd.DataFrame([row(10), row(2)]) for d in mod.DEPTHS}
        pool = mod.rank_differences(mod.stable_pool(tables))
        self.assertEqual(pool.transcript_position.tolist(), [2, 10])
        self.assertEqual(pool.minimum_group_count.tolist(), [2, 2])

    def test_shared_high_requires_every_line_and_depth(self):
        tables = {}
        for depth in mod.DEPTHS:
            tables[depth] = pd.DataFrame([{**{k: v for k, v in row().items() if k in mod.KEY}, **{line: .8 for line in mod.LINES}}])
        tables[100].loc[0, "MCF7"] = .6
        self.assertEqual(len(mod.shared_pool(tables, .7)), 0)
        self.assertEqual(len(mod.shared_pool(tables, .5)), 1)


if __name__ == "__main__":
    unittest.main()
