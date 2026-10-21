"""Synthetic threshold-contract tests: no saved weights, data or inference."""
from copy import deepcopy
from fractions import Fraction
import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

SPEC = importlib.util.spec_from_file_location("threshold_study", Path(__file__).with_name("validate_calling_threshold.py"))
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def brute_force_cutoff(y, scores):
    """Directly classify all rows at every distinct score, using exact F1."""
    choices = []
    for cutoff in set(scores.tolist()):
        calls = scores >= cutoff
        tp = sum(int(label == 1 and call) for label, call in zip(y, calls))
        fp = sum(int(label == 0 and call) for label, call in zip(y, calls))
        fn = sum(int(label == 1 and not call) for label, call in zip(y, calls))
        choices.append((Fraction(2 * tp, 2 * tp + fp + fn), float(cutoff)))
    return max(choices)


class SelectionChecks(unittest.TestCase):
    def test_tied_scores_are_grouped_and_permutation_invariant(self):
        y = np.asarray([1, 0, 1, 0, 1, 0, 0, 1])
        scores = np.asarray([.8, .8, .8, .5, .5, .2, .2, .2])
        expected, curve = TOOL.select_threshold(y, scores)
        self.assertEqual([row["cutoff"] for row in curve], [.8, .5, .2])
        self.assertEqual([row["predicted_positive"] for row in curve], [3, 5, 8])
        for seed in range(12):
            order = np.random.default_rng(seed).permutation(len(y))
            with self.subTest(seed=seed):
                self.assertEqual(TOOL.select_threshold(y[order], scores[order]), (expected, curve))

    def test_all_equal_scores_include_every_site_at_observed_cutoff(self):
        y = np.asarray([0, 1, 1, 0])
        for score in (0., .5, 1.):
            with self.subTest(score=score):
                result, curve = TOOL.select_threshold(y, np.full(4, score))
                self.assertEqual(result["cutoff"], score)
                self.assertEqual(result["n_distinct_cutoffs"], 1)
                self.assertEqual((result["inner"]["tp"], result["inner"]["fp"], result["inner"]["fn"]), (2, 2, 0))
                self.assertAlmostEqual(result["inner"]["f1"], 2 / 3)
                self.assertEqual(curve[0]["predicted_positive"], 4)

    def test_exact_f1_tie_chooses_higher_cutoff(self):
        # At .9: TP1, FP0, FN1 -> 2/3. At .6: TP2, FP2, FN0 -> 4/6.
        result, curve = TOOL.select_threshold([1, 0, 0, 1], [.9, .8, .7, .6])
        self.assertEqual(result["cutoff"], .9)
        self.assertEqual(result["tie_rule"], "higher_cutoff")
        self.assertEqual(Fraction(result["f1_numerator"], result["f1_denominator"]), Fraction(2, 3))
        self.assertEqual(curve[0]["f1"], curve[-1]["f1"])

    def test_random_small_populations_match_independent_exact_brute_force(self):
        rng = np.random.default_rng(20261021)
        for trial in range(160):
            n = int(rng.integers(2, 18))
            y = rng.integers(0, 2, size=n)
            y[0], y[-1] = 0, 1
            scores = rng.choice([0., .1, .25, .5, .75, .9, 1.], size=n)
            expected_f1, expected_cutoff = brute_force_cutoff(y, scores)
            result, curve = TOOL.select_threshold(y, scores)
            with self.subTest(trial=trial):
                self.assertEqual(result["cutoff"], expected_cutoff)
                self.assertEqual(Fraction(result["f1_numerator"], result["f1_denominator"]), expected_f1)
                self.assertAlmostEqual(result["inner"]["f1"], float(expected_f1))
                self.assertEqual(len(curve), len(set(scores.tolist())))
                self.assertEqual(curve[-1]["predicted_positive"], n)

    def test_missing_classes_empty_and_misaligned_inputs_refused(self):
        for y, score in (([0, 0], [.2, .8]), ([1, 1], [.2, .8]), ([], []),
                         ([0, 1], [.3]), ([[0, 1]], [[.3, .7]])):
            with self.subTest(y=y, score=score), self.assertRaises(ValueError):
                TOOL.select_threshold(y, score)

    def test_nonbinary_labels_nonfinite_and_range_violations_refused(self):
        for y, score in (([0, 2], [.1, .9]), ([0, np.nan], [.1, .9]),
                         ([0, 1], [np.nan, .9]), ([0, 1], [np.inf, .9]),
                         ([0, 1], [-.001, .9]), ([0, 1], [.1, 1.001])):
            with self.subTest(y=y, score=score), self.assertRaises(ValueError):
                TOOL.select_threshold(y, score)


class AlignmentChecks(unittest.TestCase):
    def setUp(self):
        self.meta = pd.DataFrame([dict(transcript_id="synthetic_b", transcript_position=20, fold_id=3),
                                  dict(transcript_id="synthetic_a", transcript_position=10, fold_id=1)])
        self.prediction = pd.DataFrame([dict(transcript_id="synthetic_a", transcript_position=10, fold_id=1, score=.2),
                                        dict(transcript_id="synthetic_b", transcript_position=20, fold_id=3, score=.8)])

    def test_key_alignment_preserves_metadata_order(self):
        np.testing.assert_array_equal(TOOL.align_prediction(self.meta, self.prediction), [.8, .2])

    def test_missing_extra_wrong_fold_and_duplicate_keys_refused(self):
        extra = self.prediction.iloc[[0]].copy()
        extra["transcript_id"] = "extra_synthetic_site"
        wrong = self.prediction.copy()
        wrong.loc[0, "fold_id"] = 0
        cases = [(self.meta, self.prediction.iloc[[0]]),
                 (self.meta, pd.concat([self.prediction, extra], ignore_index=True)),
                 (self.meta, wrong),
                 (self.meta, pd.concat([self.prediction, self.prediction.iloc[[0]]], ignore_index=True)),
                 (pd.concat([self.meta, self.meta.iloc[[0]]], ignore_index=True), self.prediction)]
        for meta, prediction in cases:
            with self.subTest(n_meta=len(meta), n_predictions=len(prediction)), self.assertRaises(ValueError):
                TOOL.align_prediction(meta, prediction)

    def test_invalid_prediction_score_refused(self):
        for score in (np.nan, np.inf, -.1, 1.1):
            prediction = self.prediction.copy()
            prediction.loc[0, "score"] = score
            with self.subTest(score=score), self.assertRaises(ValueError):
                TOOL.align_prediction(self.meta, prediction)


class CheckpointMetadataChecks(unittest.TestCase):
    def setUp(self):
        self.recipe = dict(config=dict(cap=128, context_mode="none", summary_n=63), identity=dict(cache="synthetic_cache", folds="synthetic_folds"))
        self.complete = dict(best_epoch=3, seed=2028, signature="synthetic_fit_signature", train_sites=12)
        self.bundle = dict(kind="context_reference_v1", stage="cv_inner", config=deepcopy(self.recipe["config"]),
                           epoch=3, seed=2028, fit_signature="synthetic_fit_signature",
                           input_fingerprints=deepcopy(self.recipe["identity"]),
                           norm=dict(fit_indices_sha256="synthetic_training_partition", fit_sites=12), context_reference=None)

    def test_matching_inner_checkpoint_metadata_is_accepted(self):
        TOOL.verify_bundle(self.bundle, self.recipe, self.complete, "synthetic_training_partition")

    def test_model_stage_config_epoch_seed_identity_and_boundary_mismatches_refused(self):
        mutations = [("kind", "wrong_kind"), ("stage", "cv_refit"), ("epoch", 4), ("seed", 2029),
                     ("fit_signature", "wrong_signature"), ("config", {"cap": 32}),
                     ("input_fingerprints", {"cache": "different_cache"}),
                     ("norm", dict(fit_indices_sha256="assessment_partition", fit_sites=12)),
                     ("norm", dict(fit_indices_sha256="synthetic_training_partition", fit_sites=13)),
                     ("context_reference", {"unexpected_fitted_feature_reference": True})]
        for key, value in mutations:
            bundle = deepcopy(self.bundle)
            bundle[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                TOOL.verify_bundle(bundle, self.recipe, self.complete, "synthetic_training_partition")


class DecisionChecks(unittest.TestCase):
    def test_pooled_confusion_counts_are_not_unweighted_fold_means(self):
        labels = [np.asarray([1, 0]), np.asarray([1, 1, 1, 1, 0, 0, 0, 0])]
        calls = [np.asarray([True, False]), np.asarray([False, False, False, False, True, True, True, True])]
        folded = [TOOL.decisions(y, called) for y, called in zip(labels, calls)]
        pooled = TOOL.decisions(np.concatenate(labels), np.concatenate(calls))
        for count in ("n_sites", "n_positives", "tn", "fp", "fn", "tp"):
            self.assertEqual(pooled[count], sum(row[count] for row in folded))
        for metric in ("precision", "recall", "f1", "specificity", "accuracy"):
            self.assertAlmostEqual(pooled[metric], .2)
            self.assertAlmostEqual(np.mean([row[metric] for row in folded]), .5)

    def test_decisions_require_boolean_calls_and_aligned_binary_labels(self):
        for labels, calls in (([0, 1], [0, 1]), ([0, 1], [.1, .9]), ([0, 2], [False, True]),
                              ([0, 1], [True]), ([[0, 1]], [[False, True]])):
            with self.subTest(labels=labels, calls=calls), self.assertRaises(ValueError):
                TOOL.decisions(labels, calls)

    def test_one_class_decisions_preserve_undefined_rates(self):
        negative = TOOL.decisions([0, 0], [False, True])
        positive = TOOL.decisions([1, 1], [False, True])
        self.assertIsNone(negative["recall"])
        self.assertIsNone(positive["specificity"])
        self.assertEqual((negative["tn"], negative["fp"], negative["tp"], negative["fn"]), (1, 1, 0, 0))
        self.assertEqual((positive["tn"], positive["fp"], positive["tp"], positive["fn"]), (0, 0, 1, 1))


if __name__ == "__main__":
    unittest.main()
