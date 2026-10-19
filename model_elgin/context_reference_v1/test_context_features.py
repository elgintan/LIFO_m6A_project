"""Small synthetic checks; no raw course data, model training or labels."""
from __future__ import annotations

import copy
import hashlib
import json
import unittest

import numpy as np

from context_features import fit_reference, transform_reference


def summaries(medians):
    matrix = np.zeros((len(medians), 63), dtype=np.float64)
    matrix[:, 36:45] = np.asarray(medians, dtype=np.float64)
    return matrix


def encoded(*keys):
    return np.asarray([[int(code) for code in key] for key in keys], dtype=np.int64)


class ContextReferenceTests(unittest.TestCase):
    def test_training_only_including_context_counts_and_normalisation(self):
        seq = encoded("0012300", "0012300", "0012300", "4012304", "4444444")
        raw = summaries(np.arange(45).reshape(5, 9) / 100)
        fit = [2, 0, 1]
        before = fit_reference(seq, raw, fit, min_sites=2)
        changed = raw.copy()
        changed[3:] = np.nan
        altered_seq = seq.copy()
        altered_seq[3:] = 99
        after = fit_reference(altered_seq, changed, fit, min_sites=2)
        self.assertEqual(before, after)
        self.assertEqual(before["n_fit"], 3)
        self.assertEqual(before["exact7_counts"], {"0012300": 3})
        expected_hash = hashlib.sha256(np.asarray([0, 1, 2], dtype="<i8").tobytes()).hexdigest()
        self.assertEqual(before["fit_indices_sha256"], expected_hash)
        self.assertEqual(before, fit_reference(seq, raw, [0, 1, 2], min_sites=2))

    def test_known_same_context_arithmetic_and_population_normalisation(self):
        seq = encoded("0012300", "0012300", "0012300")
        offsets = np.array([.001, .5, 2., .002, 1., 4., .003, 1.5, 6.])
        centre = np.array([.010, 3., 120., .020, 5., 140., .030, 7., 160.])
        raw = summaries([centre-offsets, centre, centre+offsets])
        fitted = fit_reference(seq, raw, [0, 1, 2], min_sites=3)
        np.testing.assert_allclose(fitted["global_reference"], centre, atol=1e-15)
        np.testing.assert_allclose(fitted["exact7_refs"]["0012300"], centre, atol=1e-15)
        expected_magnitude = offsets.copy()
        expected_magnitude[[0, 3, 6]] = np.log1p(offsets[[0, 3, 6]] * 1000)
        expected_magnitude[[1, 4, 7]] = np.log1p(offsets[[1, 4, 7]])
        np.testing.assert_allclose(fitted["residual_mean"], np.zeros(9), atol=1e-12)
        np.testing.assert_allclose(fitted["residual_sd"], expected_magnitude*np.sqrt(2/3), rtol=1e-12)
        features = transform_reference(fitted, seq, raw)
        self.assertEqual(features.dtype, np.float32)
        np.testing.assert_allclose(features[0], -np.sqrt(3/2), rtol=1e-6)
        np.testing.assert_allclose(features[1], 0, atol=1e-6)
        np.testing.assert_allclose(features[2], np.sqrt(3/2), rtol=1e-6)

    def test_exact_then_central_then_global_and_threshold_is_site_count(self):
        # The two exact sparse contexts share central5=01230. The other exact
        # context qualifies independently. Values elsewhere in the 63-vector
        # must not influence the reference, including the nine old means.
        seq = encoded("0012300", "0012301", "0123010", "0123010", "0123010")
        raw = summaries([np.full(9, x) for x in (10., 30., 100., 120., 140.)])
        raw[:, :9] = np.array([100000, -100000, 5, 6, 7])[:, None]
        fitted = fit_reference(seq, raw, np.arange(5), min_sites=2)
        self.assertNotIn("0012300", fitted["exact7_refs"])
        np.testing.assert_array_equal(fitted["central5_refs"]["01230"], np.full(9, 20.))
        np.testing.assert_array_equal(fitted["exact7_refs"]["0123010"], np.full(9, 120.))
        np.testing.assert_array_equal(fitted["global_reference"], np.full(9, 100.))
        queries = encoded("0123010", "4012304", "4444444")
        chosen = summaries([np.full(9, x) for x in (120., 20., 100.)])
        # Each query equals the expected reference, so its pre-normalisation
        # residual is exactly zero irrespective of its chosen fallback level.
        expected = -np.asarray(fitted["residual_mean"]) / np.asarray(fitted["residual_sd"])
        output = transform_reference(fitted, queries, chosen)
        np.testing.assert_allclose(output, np.broadcast_to(expected, (3, 9)), atol=1e-6)

    def test_default_requires_thirty_sites_not_thirty_reads(self):
        seq = np.tile(encoded("0012300"), (30, 1))
        raw = summaries(np.arange(270).reshape(30, 9))
        sparse = fit_reference(seq, raw, np.arange(29))
        supported = fit_reference(seq, raw, np.arange(30))
        self.assertEqual(sparse["min_sites"], 30)
        self.assertEqual(sparse["exact7_refs"], {})
        self.assertEqual(sparse["central5_refs"], {})
        self.assertIn("0012300", supported["exact7_refs"])
        self.assertEqual(supported["exact7_counts"]["0012300"], 30)

    def test_json_roundtrip_preserves_features_and_contains_no_numpy_scalars(self):
        seq = encoded("0012300", "4012304", "4444444")
        raw = summaries(np.arange(27).reshape(3, 9)/100)
        fitted = fit_reference(seq, raw, [0, 1], min_sites=2)
        restored = json.loads(json.dumps(fitted, allow_nan=False))
        self.assertEqual(restored, fitted)
        np.testing.assert_array_equal(transform_reference(restored, seq, raw),
                                      transform_reference(fitted, seq, raw))
        self.assertFalse(fitted["feature_definitions"]["fit_uses_labels_or_ids"])

    def test_constant_scales_use_one_and_negative_residuals_remain_finite(self):
        seq = encoded("4444444", "4444444")
        raw = summaries(np.full((2, 9), 5.))
        fitted = fit_reference(seq, raw, [0, 1], min_sites=2)
        np.testing.assert_array_equal(fitted["residual_sd"], np.ones(9))
        output = transform_reference(fitted, encoded("0000000"), summaries(np.full((1, 9), 4.)))
        expected = np.array([-np.log1p(1000), -np.log1p(1), -1] * 3, dtype=np.float32)
        np.testing.assert_array_equal(output[0], expected)
        self.assertTrue(np.isfinite(output).all())
        self.assertTrue((output < 0).all())

    def test_empty_transform_has_exact_shape(self):
        seq = encoded("0000000")
        fitted = fit_reference(seq, summaries(np.ones((1, 9))), [0])
        result = transform_reference(fitted, np.empty((0, 7), dtype=np.int64), np.empty((0, 63)))
        self.assertEqual(result.shape, (0, 9))
        self.assertEqual(result.dtype, np.float32)

    def test_near_zero_nonzero_population_sd_uses_one(self):
        seq = encoded("0000000", "0000000", "0000000")
        raw = summaries(np.broadcast_to(np.array([-1e-12, 0., 1e-12])[:, None], (3, 9)))
        fitted = fit_reference(seq, raw, [0, 1, 2], min_sites=3)
        np.testing.assert_array_equal(fitted["residual_sd"], np.ones(9))
        values = transform_reference(fitted, seq, raw)
        self.assertTrue(np.isfinite(values).all())
        self.assertTrue(np.all(values[0] < 0))
        self.assertTrue(np.all(values[2] > 0))

    def test_finite_float64_that_cannot_be_output_float32_is_rejected(self):
        seq = encoded("0000000")
        fitted = fit_reference(seq, summaries(np.zeros((1, 9))), [0])
        raw = summaries(np.zeros((1, 9)))
        raw[0, 38] = 1e300  # first current column remains linear, rather than logged
        with self.assertRaisesRegex(ValueError, "finite float32"):
            transform_reference(fitted, seq, raw)

    def test_malformed_shapes_dtypes_and_index_sets_fail(self):
        seq = encoded("0012300", "0012300")
        raw = summaries(np.ones((2, 9)))
        bad_indices = ([], [[0]], [True, False], [0.0], [0, 0], [-1], [2], [2**64-1])
        for indices in bad_indices:
            with self.subTest(indices=indices), self.assertRaises(ValueError):
                fit_reference(seq, raw, indices)
        for bad_sequence, bad_summary in (
                (seq[:, :6], raw), (seq, raw[:, :62]), (seq[:1], raw),
                (seq.astype(bool), raw), (seq.astype(float), raw),
                (seq, raw.astype(str)), (seq, raw.astype(bool))):
            with self.subTest(shape=(bad_sequence.shape, bad_summary.shape)), self.assertRaises(ValueError):
                fit_reference(bad_sequence, bad_summary, [0])
        for minimum in (0, -1, True, 2.0, "30"):
            with self.subTest(min_sites=minimum), self.assertRaises(ValueError):
                fit_reference(seq, raw, [0], min_sites=minimum)

    def test_invalid_fit_values_and_invalid_transform_rows_fail(self):
        seq = encoded("0012300", "0012300")
        raw = summaries(np.ones((2, 9)))
        fitted = fit_reference(seq, raw, [0])
        bad_code = seq.copy()
        bad_code[0, 0] = 5
        bad_number = raw.copy()
        bad_number[0, 62] = np.inf
        for sequence, summary in ((bad_code, raw), (seq, bad_number)):
            with self.assertRaises(ValueError):
                fit_reference(sequence, summary, [0])
            with self.assertRaises(ValueError):
                transform_reference(fitted, sequence, summary)

    def test_corrupted_reference_rejected_instead_of_silent_fallback(self):
        seq = encoded("0012300", "0012300")
        raw = summaries(np.ones((2, 9)))
        fitted = fit_reference(seq, raw, [0, 1], min_sites=2)
        for field, value in (("version", True), ("residual_sd", [0.]*9),
                             ("global_reference", [np.nan]*9),
                             ("exact7_counts", {"0012300": 1}),
                             ("exact7_refs", {}), ("fit_indices_sha256", "bad")):
            bad = copy.deepcopy(fitted)
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                transform_reference(bad, seq, raw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
