"""Bounded arithmetic and category checks; no real project analysis."""
import importlib.util
import itertools
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

SPEC = importlib.util.spec_from_file_location("task2_report", Path(__file__).resolve().parents[1] / "scripts/report_task2_analysis.py")
report = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(report)


class ReporterTests(unittest.TestCase):
    def test_real_threshold_arithmetic_and_cdf(self):
        wide = pd.DataFrame({"A": [0, .5, .7, .9, 1], "B": [.1, .2, .3, .4, .5]})
        summary, cdf = report.common_summaries(wide, 20)
        a = summary[summary.cell_line.eq("A")].set_index("score_cutoff")
        self.assertEqual(a.loc[.5, "n_high"], 4)
        self.assertEqual(a.loc[.9, "fraction_high"], .4)
        end = cdf[(cdf.cell_line == "A") & (cdf.score_grid == 1)].iloc[0]
        self.assertEqual(end.empirical_fraction_le_score, 1)
        self.assertEqual(len(cdf), 1002)

    def test_metadata_groups_are_never_called_independent_replicates(self):
        manifest = pd.DataFrame({"run_id": ["A1", "A2", "A3", "B1"], "cell_line": ["A", "A", "A", "B"], "biological_replicate": ["1", "1", "2", "1"]})
        table = pd.DataFrame({"unit": ["run_id"]*3+["replicate_id"]*2,
                              "a": ["A1", "A1", "A1", "A:rep1", "A:rep1"],
                              "b": ["A2", "A3", "B1", "A:rep2", "B:rep1"]})
        result = report.classify_agreement(table, manifest)
        self.assertEqual(result.metadata_relationship.tolist(), report.RELATIONS)
        table.loc[0, "a"] = "UNKNOWN"
        with self.assertRaisesRegex(ValueError, "unknown run"): report.classify_agreement(table, manifest)

    def test_undefined_correlations_preserved(self):
        table = pd.DataFrame({"coverage_threshold": [20, 20], "metadata_relationship": [report.RELATIONS[0]]*2,
                              "spearman": [.8, np.nan], "n_common_sites": [10, 1], "median_absolute_delta": [.1, .2]})
        row = report.agreement_summary(table).iloc[0]
        self.assertEqual(row.n_pair_estimates, 2)
        self.assertEqual(row.n_defined_correlations, 1)
        self.assertEqual(row.median_spearman, .8)

    def test_pair_effects_and_screen_recomputed(self):
        pair = pd.DataFrame({"transcript_id": ["x", "y"], "transcript_position": [1, 2], "score_a": [.8, .3], "score_b": [.1, .4],
                             "delta_score": [.7, -.1], "coverage_balanced": [True, False], "coverage_ratio": [1.5, 3.],
                             "candidate_large_difference": [True, False], "score_min_a": [.7, .2], "score_max_a": [.9, .4],
                             "score_min_b": [.05, .3], "score_max_b": [.2, .5], "n_replicates_a": [2, 2], "n_replicates_b": [2, 2]})
        summary = pd.DataFrame({"population": ["all_pairwise_common", "coverage_balanced"], "n_sites": [2, 1],
                                "n_large_replicate_separated": [1, 1], "median_delta_a_minus_b": [.3, .7]})
        report.validate_pair_summary(pair, summary)
        pair.loc[1, "candidate_large_difference"] = True
        with self.assertRaisesRegex(ValueError, "Candidate flags"): report.validate_pair_summary(pair, summary)

    def test_empty_population_has_undefined_fraction_not_zero(self):
        summary, cdf = report.common_summaries(pd.DataFrame({"A": []}), 100)
        self.assertTrue(summary.fraction_high.isna().all())
        self.assertTrue(cdf.empirical_fraction_le_score.isna().all())
        with self.assertRaises(ValueError): report.validate_scores([float("nan")], "fixture")

    def test_all_four_figure_shapes(self):
        lines = [f"Line{i}" for i in range(7)]
        populations, common, cdf, pairs, agreements = [], [], [], [], []
        for depth in report.DEPTHS:
            populations.append({"population_type": "all_lines", "coverage_threshold": depth, "n_annotated_coverage_qualified": 3,
                                "n_primary_all_source_consistent": 2, "n_scored_only_consistent": 3})
            summary, cdf_table = report.common_summaries(pd.DataFrame({line: [.1, .8] for line in lines}), depth)
            common.append(summary); cdf.append(cdf_table)
            for a, b in itertools.combinations(lines, 2):
                populations.append({"population_type": "pairwise", "cell_lines": f"{a}|{b}", "coverage_threshold": depth,
                                    "n_annotated_coverage_qualified": 3, "n_excluded_primary_context": 1})
                pairs.append({"coverage_threshold": depth, "cell_line_a": a, "cell_line_b": b, "population": "all_pairwise_common",
                              "median_delta_a_minus_b": -.01, "n_large_replicate_separated": 0, "n_sites": 2})
            for relationship in report.RELATIONS:
                agreements.append({"coverage_threshold": depth, "metadata_relationship": relationship, "spearman": .7})
        with tempfile.TemporaryDirectory() as directory:
            report.figures(Path(directory), pd.DataFrame(populations), pd.concat(common), pd.concat(cdf), pd.DataFrame(agreements), pd.DataFrame(pairs))
            self.assertEqual(len(list(Path(directory).glob("*.png"))), 4)
            self.assertEqual(len(list(Path(directory).glob("*.svg"))), 4)


if __name__ == "__main__": unittest.main()
