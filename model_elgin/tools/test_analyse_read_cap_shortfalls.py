"""Synthetic scientific-contract checks; no real inputs, fits or inference."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np
import pandas as pd

SPEC = importlib.util.spec_from_file_location("shortfalls", Path(__file__).with_name("analyse_read_cap_shortfalls.py"))
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def synthetic_population():
    labels = [0, 1, 0, 1, 1, 0, 0, 1]
    context = ["AAAACTA", "AAAACTA", "AGGACTA", "AGGACTA", "ATAACCA", "ATAACAA", "AAAACCA", "AAAACCA"]
    patterns = dict(cap32=[.15, .75, .7, .4, .3, .65, .2, .8],
                    cap128=[.1, .8, .3, .7, .35, .6, .2, .75],
                    samuel=[.2, .7, .6, .5, .6, .4, .9, .1])
    records, scores = [], {model: [] for model in TOOL.MODELS}
    for fold in range(5):
        for i in range(8):
            sequence = context[i] if fold == 0 or i < 6 else "AGGACTA"
            records.append(dict(transcript_id=f"synthetic_{fold}_{i}", transcript_position=100 + i,
                                label=labels[i], fold_id=fold, gene_id=f"synthetic_gene_{fold}_{i}",
                                n_reads=[20, 40, 70, 150, 250, 300, 220, 260][i],
                                context=sequence, central5=sequence[1:6], unusual_flag=i == 4,
                                member1_reviewed=i == 5))
            for model in TOOL.MODELS:
                scores[model].append(patterns[model][i] + fold * .002)
    return pd.DataFrame(records), {model: np.asarray(values) for model, values in scores.items()}


def independent_ranking(y, score):
    """Pairwise ROC and grouped-threshold PR integral, independent of sklearn."""
    positive, negative = score[y == 1], score[y == 0]
    roc = np.mean([float(a > b) + .5 * float(a == b) for a in positive for b in negative])
    recalls, precisions = [0.], [1.]
    for cutoff in sorted(set(score), reverse=True):
        selected = score >= cutoff
        recalls.append(float(y[selected].sum()) / len(positive))
        precisions.append(float(y[selected].sum()) / int(selected.sum()))
    pr = sum((recalls[i] - recalls[i - 1]) * (precisions[i] + precisions[i - 1]) / 2
             for i in range(1, len(recalls)))
    return dict(roc_auc=float(roc), pr_auc_trapezoid=pr, selection_score=(roc + pr) / 2)


class AlignmentChecks(unittest.TestCase):
    def setUp(self):
        self.keys = [("synthetic_b", 2), ("synthetic_a", 1)]
        self.assignments = {self.keys[0]: ("gene_b", 3), self.keys[1]: ("gene_a", 0)}
        self.predictions = {self.keys[1]: .2, self.keys[0]: .8}
        self.folds = {key: value[1] for key, value in self.assignments.items()}

    def test_scores_follow_canonical_key_order(self):
        np.testing.assert_array_equal(TOOL.align_scores(self.keys, self.assignments, self.predictions, self.folds), [.8, .2])

    def test_missing_extra_and_wrong_fold_are_refused(self):
        missing, extra, wrong = deepcopy(self.predictions), deepcopy(self.predictions), deepcopy(self.folds)
        missing.pop(self.keys[0])
        extra[("extra_site", 3)] = .5
        wrong[self.keys[0]] = 4
        for predictions, folds in ((missing, self.folds), (extra, self.folds), (self.predictions, wrong)):
            with self.subTest(predictions=predictions, folds=folds), self.assertRaises(ValueError):
                TOOL.align_scores(self.keys, self.assignments, predictions, folds)

    def test_nonfinite_and_out_of_range_scores_refused(self):
        for value in (np.nan, np.inf, -.001, 1.001):
            changed = {**self.predictions, self.keys[0]: value}
            with self.subTest(value=value), self.assertRaises(ValueError):
                TOOL.align_scores(self.keys, self.assignments, changed, self.folds)


class FlagChecks(unittest.TestCase):
    def setUp(self):
        self.frame, _ = synthetic_population()
        self.flags = self.frame[[*TOOL.KEY, "fold_id", "label", "central5", "n_reads", "unusual_flag"]].copy()

    def test_shuffled_flag_rows_are_aligned_to_sites(self):
        shuffled = self.flags.sample(frac=1, random_state=5)
        np.testing.assert_array_equal(TOOL.verified_flags(self.frame, shuffled), self.frame.unusual_flag.to_numpy())

    def test_supplied_flag_table_overrides_a_stale_frame_flag_column(self):
        flags = self.flags.copy()
        flags["unusual_flag"] = ~flags.unusual_flag
        np.testing.assert_array_equal(TOOL.verified_flags(self.frame, flags), ~self.frame.unusual_flag.to_numpy())

    def test_duplicate_missing_extra_flags_refused(self):
        extra = self.flags.iloc[[0]].copy()
        extra["transcript_id"] = "extra_synthetic_site"
        invalid = [pd.concat([self.flags, self.flags.iloc[[0]]], ignore_index=True),
                   self.flags.iloc[1:].copy(), pd.concat([self.flags, extra], ignore_index=True)]
        for frame in invalid:
            with self.subTest(n=len(frame)), self.assertRaises(ValueError):
                TOOL.verified_flags(self.frame, frame)

    def test_flag_metadata_mismatch_refused(self):
        for column, value in (("fold_id", 4), ("label", 1), ("central5", "GGACT"), ("n_reads", 999)):
            flags = self.flags.copy()
            flags.loc[0, column] = value
            with self.subTest(column=column), self.assertRaisesRegex(ValueError, "metadata mismatch"):
                TOOL.verified_flags(self.frame, flags)

    def test_nonboolean_or_missing_flag_refused(self):
        for value in ("False", "TRUE", None):
            flags = self.flags.astype({"unusual_flag": object})
            flags.loc[0, "unusual_flag"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                TOOL.verified_flags(self.frame, flags)


class DiagnosticChecks(unittest.TestCase):
    def test_error_overlap_partitions_classes_and_preserves_direction(self):
        y = np.asarray([1, 1, 1, 1, 0, 0, 0, 0])
        control = np.asarray([.1, .9, .1, .9, .9, .1, .9, .1])
        candidate = np.asarray([.2, .8, .5, .2, .8, .2, .2, .5])
        full = np.ones(8, dtype=bool)
        overlap = TOOL.error_overlap(y, control, candidate, full)
        self.assertEqual(set(overlap.values()), {1})
        self.assertEqual(sum(overlap.values()), 8)
        mask = np.asarray([False, False, True, True, False, False, True, True])
        selected = TOOL.error_overlap(y, control, candidate, mask)
        reverse = TOOL.error_overlap(y, candidate, control, mask)
        self.assertEqual(sum(selected.values()), 4)
        for label in ("positive", "negative"):
            self.assertEqual(selected[label + "_fixed_by_candidate"], 1)
            self.assertEqual(selected[label + "_new_candidate_error"], 1)
            self.assertEqual(reverse[label + "_fixed_by_candidate"], selected[label + "_new_candidate_error"])
            self.assertEqual(reverse[label + "_new_candidate_error"], selected[label + "_fixed_by_candidate"])

    def test_one_class_and_empty_groups_have_no_fabricated_ranking(self):
        frame, scores = synthetic_population()
        rows, changes, overlaps = TOOL.analyse(frame, scores)
        for group, status, count in (("TAACC", "single_class_not_scored", 5), ("TAACA", "single_class_not_scored", 5)):
            selected = [row for row in rows if row["family"] == "central5" and row["subgroup"] == group]
            self.assertEqual(len(selected), 18)
            for row in selected:
                self.assertEqual(row["ranking_status"], status)
                self.assertTrue(row["sparse_class_support"])
                self.assertIsNone(row["roc_auc"])
                self.assertIsNone(row["pr_auc_trapezoid"])
                self.assertIsNone(row["selection_score"])
                if row["fold_id"] is None:
                    self.assertEqual(row["n_sites"], count)
        empty = [row for row in rows if row["family"] == "high_depth_central5" and row["subgroup"] == "AAACT"]
        self.assertTrue(empty)
        self.assertTrue(all(row["n_sites"] == 0 and row["ranking_status"] == "empty_not_scored" and row["selection_score"] is None for row in empty))
        no_ranking = [row for row in changes if row["family"] == "central5" and row["subgroup"] == "TAACC"]
        self.assertTrue(all(row["evaluable_folds"] == 0 and row["pooled_delta_S"] is None and row["mean_evaluable_fold_delta_S"] is None and row["sample_sd_paired_delta_S"] is None for row in no_ranking))
        self.assertTrue(all(sum(value for key, value in row.items() if key.startswith(("positive_", "negative_"))) == row["n_sites"] for row in overlaps))

    def test_sparse_two_class_group_retains_evaluable_fold_denominator(self):
        frame, scores = synthetic_population()
        rows, changes, _ = TOOL.analyse(frame, scores)
        sparse = [row for row in changes if row["family"] == "central5" and row["subgroup"] == "AAACC"]
        self.assertEqual(len(sparse), 2)
        for row in sparse:
            self.assertEqual((row["n_sites"], row["n_positives"], row["evaluable_folds"]), (2, 1, 1))
            self.assertTrue(row["sparse_class_support"])
            self.assertIsNotNone(row["mean_evaluable_fold_delta_S"])
            self.assertIsNone(row["sample_sd_paired_delta_S"])

    def test_full_primary_means_match_independent_three_model_arithmetic(self):
        frame, scores = synthetic_population()
        rows, changes, overlaps = TOOL.analyse(frame, scores)
        _, summaries = TOOL.reliability(frame.label.to_numpy(), scores)
        report = TOOL.make_report(frame, rows, changes, overlaps, summaries)
        means = {}
        for model in TOOL.MODELS:
            expected = [independent_ranking(frame.label.to_numpy()[frame.fold_id.to_numpy() == fold],
                        scores[model][frame.fold_id.to_numpy() == fold]) for fold in range(5)]
            selected = [row for row in rows if row["family"] == "all" and row["model"] == model and row["fold_id"] is not None]
            self.assertEqual(len(selected), 5)
            for row in selected:
                for metric, value in expected[row["fold_id"]].items():
                    self.assertAlmostEqual(row[metric], value, places=14)
            means[model] = {metric: float(np.mean([row[metric] for row in expected])) for metric in expected[0]}
            line = next(line for line in report.splitlines() if line.startswith("| " + model + " |"))
            for value in means[model].values():
                self.assertIn(f"{value:.9f}", line)
        for control, candidate in TOOL.PAIRS:
            result = next(row for row in changes if row["family"] == "all" and row["control"] == control)
            self.assertEqual(result["evaluable_folds"], 5)
            self.assertAlmostEqual(result["mean_evaluable_fold_delta_S"], means[candidate]["selection_score"] - means[control]["selection_score"], places=14)

    def test_reliability_includes_score_one_in_final_bin_and_empty_bins_undefined(self):
        y = np.asarray([0, 1, 1, 0])
        score = np.asarray([0., .1, .9, 1.])
        rows, summary = TOOL.reliability(y, {"synthetic": score})
        self.assertEqual(sum(row["n_sites"] for row in rows), 4)
        self.assertEqual(rows[0]["n_sites"], 1)
        self.assertEqual(rows[1]["n_sites"], 1)
        self.assertEqual(rows[9]["n_sites"], 2)
        self.assertAlmostEqual(rows[9]["mean_score"], .95)
        self.assertAlmostEqual(rows[9]["observed_positive_fraction"], .5)
        for row in rows[2:9]:
            self.assertEqual(row["n_sites"], 0)
            self.assertIsNone(row["mean_score"])
            self.assertIsNone(row["observed_positive_fraction"])
        self.assertAlmostEqual(summary[0]["brier_score"], .455)
        self.assertAlmostEqual(summary[0]["equal_width_10bin_ece"], .45)
        self.assertAlmostEqual(summary[0]["mean_score"], .5)
        self.assertAlmostEqual(summary[0]["positive_fraction"], .5)

    def test_undefined_subgroup_plot_is_marked_na_without_a_zero_height(self):
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib.axes import Axes
        heights, annotations = [], []
        original_bar, original_text = Axes.bar, Axes.text

        def capture_bar(axis, x, height, *args, **kwargs):
            heights.append(np.asarray(height, dtype=float))
            return original_bar(axis, x, height, *args, **kwargs)

        def capture_text(axis, x, y, text, *args, **kwargs):
            annotations.append(str(text))
            return original_text(axis, x, y, text, *args, **kwargs)

        changes = [dict(family=family, subgroup=group, control="cap32", pooled_delta_S=delta,
                        sparse_class_support=delta is None)
                   for family in ("coverage", "central5") for group, delta in (("one_class", None), ("both_classes", .125))]
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(Axes, "bar", new=capture_bar), mock.patch.object(Axes, "text", new=capture_text):
            outputs = TOOL.plots(Path(directory), [], changes, [])
            self.assertEqual(len(outputs), 3)
            self.assertTrue(all(path.is_file() for path in outputs))
        self.assertEqual(len(heights), 2)
        self.assertTrue(all(np.isnan(values[0]) and values[1] == .125 for values in heights))
        self.assertGreaterEqual(annotations.count("NA"), 2)


if __name__ == "__main__":
    unittest.main()
