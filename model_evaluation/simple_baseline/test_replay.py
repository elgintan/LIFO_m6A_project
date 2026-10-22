"""Small synthetic software checks only; never reads or fits course datasets."""
import ast
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

SPEC = importlib.util.spec_from_file_location("tested_simple_replay", Path(__file__).with_name("replay.py"))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def toy_data():
    keys = [("tx%d" % i, i) for i in range(30)]
    assigned = np.repeat(np.arange(5), 6)
    y = np.tile([0, 1, 0, 0, 1, 0], 5)
    genes = np.asarray(["gene%d" % fold for fold in assigned])
    features = np.random.RandomState(7).normal(size=(30, 18))
    features[:, 0] += 2*y
    return keys, y, assigned, genes, features


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def write_raw(self, records, compressed=False):
        path = self.folder / ("sites.json.gz" if compressed else "sites.json")
        text = "\n".join(json.dumps(record) for record in records) + "\n"
        path.write_bytes(gzip.compress(text.encode()) if compressed else text.encode())
        return path

    def test_float64_raw_mean_population_sd_and_key_order(self):
        base = np.arange(9, dtype=np.float64) + 16777217.25
        reads = np.vstack((base, base+1, base+4))
        records = [{"txA": {"2": {"AAGACCA": reads.tolist()}}},
                   {"txB": {"3": {"GGAACTA": (reads*.001).tolist()}}}]
        path = self.write_raw(records, compressed=True)
        x, counts, audit = MODULE.extract_features(path, [("txB", 3), ("txA", 2)])
        np.testing.assert_array_equal(x[1, :9], reads.mean(axis=0))
        np.testing.assert_array_equal(x[1, 9:], reads.std(axis=0, ddof=0))
        self.assertFalse(np.array_equal(x[1, :9], reads.astype(np.float32).mean(axis=0)))
        self.assertEqual(x.dtype, np.float64)
        self.assertEqual(counts.tolist(), [3, 3])
        self.assertEqual(audit["n_reads"], 6)

    def test_invalid_reads_duplicates_and_missing_sites_fail(self):
        for reads in ([[True]*9], [["1"]*9], [[float("nan")]*9], [[0]*8], []):
            path = self.write_raw([{"tx": {"0": {"AAGACCA": reads}}}])
            with self.subTest(reads=reads), self.assertRaises(ValueError):
                MODULE.extract_features(path, [("tx", 0)])
        record = {"tx": {"0": {"AAGACCA": [[0.]*9]}}}
        path = self.write_raw([record, record])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            MODULE.extract_features(path, [("tx", 0)])
        path = self.write_raw([record])
        with self.assertRaisesRegex(ValueError, "cover every"):
            MODULE.extract_features(path, [("tx", 0), ("missing", 1)])

    def test_feature_cache_reuses_only_same_hashes_and_order(self):
        path = self.write_raw([{"tx": {"0": {"AAGACCA": [[1.]*9, [3.]*9]}}}])
        identity = dict(input_sha256={"data": MODULE.SCORER.sha256(path)}, source_sha256={"fixture": "a"})
        x, receipt, reused = MODULE.prepare_features(path, [("tx", 0)], self.folder, identity)
        self.assertFalse(reused)
        with mock.patch.object(MODULE, "extract_features", side_effect=AssertionError("Must reuse")):
            other, saved, reused = MODULE.prepare_features(path, [("tx", 0)], self.folder, identity)
        np.testing.assert_array_equal(x, other)
        self.assertTrue(reused)
        self.assertEqual(receipt, saved)
        array_path = self.folder / "features/raw18_float64.npz"
        array_path.write_bytes(array_path.read_bytes()+b"changed")
        with self.assertRaisesRegex(ValueError, "cache identity/hash"):
            MODULE.prepare_features(path, [("tx", 0)], self.folder, identity)


class FoldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.keys, self.y, self.folds, self.genes, self.x = toy_data()
        self.identity = dict(fixture=True, feature_arrays_sha256="synthetic-feature-hash")

    def test_scaler_fits_training_only_and_json_matches_real_fit(self):
        train, assessment, audit = MODULE.partition(self.y, self.folds, self.genes, 0)
        self.x[assessment] += 10000
        model, messages = MODULE.fit_model(self.x, self.y, train)
        np.testing.assert_allclose(model[0].mean_, self.x[train].mean(axis=0))
        self.assertFalse(np.allclose(model[0].mean_, self.x.mean(axis=0)))
        artifact = MODULE.export_model(model, audit)
        self.assertEqual(artifact["scaler_samples_seen"], len(train))
        self.assertGreater(float(np.linalg.norm(artifact["coef"])), 0.)
        np.testing.assert_allclose(MODULE.predict_artifact(artifact, self.x[assessment]),
                                   model.predict_proba(self.x[assessment])[:, 1], atol=1e-13, rtol=0)
        self.assertEqual(model[-1].class_weight, "balanced")
        self.assertEqual(model[-1].C, 1.)

    def test_metadata_keys_genes_classes_and_overlap_checked(self):
        labels = dict(zip(self.keys, map(int, self.y)))
        genes = dict(zip(self.keys, self.genes))
        folds = {key: (str(gene), int(fold)) for key, gene, fold in zip(self.keys, self.genes, self.folds)}
        keys, y, assigned, gene_array = MODULE.align_metadata(labels, genes, folds)
        self.assertEqual(keys, self.keys)
        changed = dict(genes); changed[self.keys[0]] = "wrong_gene"
        with self.assertRaisesRegex(ValueError, "gene mismatch"):
            MODULE.align_metadata(labels, changed, folds)
        bad_genes = self.genes.copy(); bad_genes[6] = self.genes[0]
        with self.assertRaisesRegex(ValueError, "Gene leakage"):
            MODULE.partition(self.y, self.folds, bad_genes, 0)
        bad_y = self.y.copy(); bad_y[self.folds == 0] = 0
        with self.assertRaisesRegex(ValueError, "Both classes"):
            MODULE.partition(bad_y, self.folds, self.genes, 0)

    def test_five_fold_complete_resume_and_common_scorer(self):
        scores = np.full(30, np.nan)
        for fold in range(5):
            selected, receipt, reused = MODULE.run_fold(self.folder, self.x, self.y, self.folds, self.genes,
                                                       self.keys, fold, self.identity)
            scores[self.folds == fold] = selected
            self.assertFalse(reused)
            with mock.patch.object(MODULE, "fit_model", side_effect=AssertionError("No completed refit")):
                again, cached, reused = MODULE.run_fold(self.folder, self.x, self.y, self.folds, self.genes,
                                                        self.keys, fold, self.identity)
            self.assertTrue(reused)
            np.testing.assert_array_equal(selected, again)
            self.assertEqual(receipt, cached)
        predictions = dict(zip(self.keys, scores))
        labels = dict(zip(self.keys, map(int, self.y)))
        folds = {key: (str(gene), int(fold)) for key, gene, fold in zip(self.keys, self.genes, self.folds)}
        result = MODULE.SCORER.evaluate_tables(labels, predictions, "data0", folds,
                                               dict(zip(self.keys, map(int, self.folds))))
        self.assertEqual(len(result["per_fold"]), 5)
        self.assertEqual(result["pooled"]["n_sites"], 30)

    def test_changed_feature_hash_or_completed_artifact_refused(self):
        MODULE.run_fold(self.folder, self.x, self.y, self.folds, self.genes, self.keys, 0, self.identity)
        changed = dict(self.identity, feature_arrays_sha256="another-feature-hash")
        with self.assertRaisesRegex(ValueError, "identity differs"):
            MODULE.run_fold(self.folder, self.x, self.y, self.folds, self.genes, self.keys, 0, changed)
        path = self.folder / "fold0/model.json"
        path.write_bytes(path.read_bytes()+b"changed")
        with self.assertRaisesRegex(ValueError, "artifact changed"):
            MODULE.run_fold(self.folder, self.x, self.y, self.folds, self.genes, self.keys, 0, self.identity)

    def test_interrupted_fold_is_not_complete_and_can_restart(self):
        with mock.patch.object(MODULE, "fit_model", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                MODULE.run_fold(self.folder, self.x, self.y, self.folds, self.genes, self.keys, 0, self.identity)
        self.assertFalse((self.folder / "fold0/complete.json").exists())
        records = list((self.folder / "fold0").glob("invocation_*.json"))
        self.assertEqual(MODULE.read_json(records[0])["status"], "failed_or_interrupted")
        _, receipt, reused = MODULE.run_fold(self.folder, self.x, self.y, self.folds, self.genes, self.keys, 0, self.identity)
        self.assertFalse(reused)
        self.assertEqual(receipt["status"], "complete")
        self.assertEqual(len(list((self.folder / "fold0").glob("invocation_*.json"))), 2)

    def test_main_interruption_cleans_owned_lock_and_records_failure(self):
        with mock.patch.object(MODULE, "HERE", self.folder), mock.patch.object(MODULE, "execute", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                MODULE.main(["--output-dir", str(self.folder / "outputs/test")])
        output = self.folder / "outputs/test"
        self.assertFalse((output / "run.lock").exists())
        self.assertEqual(MODULE.read_json(output / "status.json")["status"], "failed_or_interrupted")
        self.assertTrue((output / "training.log").exists())

    def test_source_parses_as_python38(self):
        ast.parse(Path(MODULE.__file__).read_text(encoding="utf-8"), feature_version=(3, 8))


if __name__ == "__main__":
    unittest.main()
