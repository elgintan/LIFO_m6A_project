"""Synthetic scientific-contract checks for the isolated loss-weight wrapper."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

import train_loss_weight as loss
from test_train import SyntheticCache
from data import summarise
from model import summary_transform


class VariableReadCache(SyntheticCache):
    def __init__(self):
        super().__init__()
        self.bags = [np.tile(values, (60, 1))[:[20, 40, 80, 160][i % 4]]
                     for i, values in enumerate(self.bags)]
        self.off = np.r_[0, np.cumsum([len(bag) for bag in self.bags])]
        self.raw_summary = np.stack([summarise(bag) for bag in self.bags])
        self.summary = summary_transform(self.raw_summary)


def recipe():
    return dict(config=dict(loss.fitting.BASE, cap=128, context_mode="none", min_sites=30),
                max_epochs=20, patience=5, seed=2026, batch_size=256, threads=4, smoke=False)


def synthetic_parent_identity():
    core = dict(cache_manifest_sha256="a" * 64, data0_input_sha256=loss.fitting.DATA0_INPUT_SHA,
                labels_sha256="b" * 64, folds_sha256=loss.SAVED.FOLD_SHA, source_sha256=loss.fitting.source_hashes())
    return loss.cap.experiment_identity(core)


class LossWeightChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.cache = VariableReadCache()

    def assert_tensor_tree_equal(self, actual, expected):
        if isinstance(actual, torch.Tensor):
            torch.testing.assert_close(actual, expected, rtol=0, atol=0)
        elif isinstance(actual, dict):
            self.assertEqual(set(actual), set(expected))
            for key in actual:
                self.assert_tensor_tree_equal(actual[key], expected[key])
        elif isinstance(actual, (list, tuple)):
            self.assertEqual(len(actual), len(expected))
            for left, right in zip(actual, expected):
                self.assert_tensor_tree_equal(left, right)
        else:
            self.assertEqual(actual, expected)

    def test_only_positive_loss_weight_changes(self):
        parent = recipe()
        config = loss.configuration(parent)
        self.assertEqual({key for key in config if config[key] != parent["config"][key]}, {"pos_weight"})
        self.assertEqual(config["pos_weight"], 1.)
        self.assertEqual(config["cap"], 128)
        self.assertEqual(parent["config"]["pos_weight"], 3.)
        for changed in (dict(parent, batch_size=128), dict(parent, threads=1),
                        dict(parent, config=dict(parent["config"], cap=32)),
                        dict(parent, config=dict(parent["config"], dropout=.1))):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                loss.configuration(changed)
        for weight in (0., 2., True, float("nan")):
            with self.subTest(weight=weight), self.assertRaises(ValueError):
                loss.configuration(parent, weight)

    def test_cap128_summary_and_all_read_inference_are_unchanged(self):
        cache = self.cache
        chosen = np.arange(4)
        sampled = loss.fitting.batch(cache, chosen, None, np.random.default_rng(2026), cap=128)
        all_reads = loss.fitting.batch(cache, chosen, None)
        self.assertEqual(sampled[1].sum(1).tolist(), [20, 40, 80, 128])
        self.assertEqual(all_reads[1].sum(1).tolist(), [20, 40, 80, 160])
        np.testing.assert_array_equal(sampled[3], cache.summary[chosen])
        np.testing.assert_array_equal(all_reads[3], cache.summary[chosen])
        self.assertIsNone(sampled[4])
        self.assertIsNone(all_reads[4])

    def test_weight3_delegation_is_tensor_identical_to_original(self):
        cache = self.cache
        config = loss.configuration(recipe(), 3.)
        common = dict(phase="smoke", max_epochs=2, patience=5, seed=2026,
                      batch_size=16, threads=1, outer_folds=[0])
        with tempfile.TemporaryDirectory(prefix=".loss_eq_") as directory:
            root = Path(directory)
            direct, wrapped = [SimpleNamespace(**common, output_dir=root / name) for name in ("direct", "wrapped")]
            identity = dict(synthetic_only=True)
            population = np.arange(len(cache.keys))
            loss.fitting.run_cv(cache, cache.keys, population, config, direct, identity)
            loss.delegate_cv(cache, cache.keys, population, config, wrapped, identity)
            for stage in ("inner", "refit"):
                a = torch.load(root / f"direct/smoke/none/fold0/{stage}/last.pt", weights_only=False)
                b = torch.load(root / f"wrapped/smoke/none/fold0/{stage}/last.pt", weights_only=False)
                self.assertEqual(a["signature"], b["signature"])
                self.assertEqual(a["norm"], b["norm"])
                self.assertEqual([row["loss"] for row in a["history"]], [row["loss"] for row in b["history"]])
                for key in a["state_dict"]:
                    torch.testing.assert_close(a["state_dict"][key], b["state_dict"][key], rtol=0, atol=0)
            self.assertEqual((root / "direct/smoke/none/fold0/predictions.csv").read_bytes(),
                             (root / "wrapped/smoke/none/fold0/predictions.csv").read_bytes())

    def test_weight1_real_interrupted_resume_and_identity_rejection(self):
        cache = self.cache
        with tempfile.TemporaryDirectory(prefix=".loss_resume_") as directory:
            root = Path(directory)
            arguments = dict(cache=cache, y=cache.keys.label.to_numpy(), indices=np.arange(24),
                             validation=np.arange(24, 40), config=loss.configuration(recipe()), seed=2026,
                             max_epochs=2, patience=5, batch_size=8, stage="smoke",
                             identity=dict(loss_weight_plan_sha256="synthetic_fixed_plan", loss_weight_entrypoint_sha256="synthetic_fixed_wrapper"))
            loss.fitting.run_fit(directory=root / "full", **arguments)
            original = loss.fitting.atomic_torch

            def interrupt(path, payload):
                original(path, payload)
                if Path(path).name == "last.pt" and payload["epoch"] == 1:
                    raise KeyboardInterrupt("synthetic completed-epoch interruption")

            with patch.object(loss.fitting, "atomic_torch", side_effect=interrupt), self.assertRaises(KeyboardInterrupt):
                loss.fitting.run_fit(directory=root / "resume", **arguments)
            for changed in (dict(arguments, identity=dict(arguments["identity"], loss_weight_plan_sha256="changed_plan")),
                            dict(arguments, config=dict(arguments["config"], pos_weight=3.))):
                with self.assertRaisesRegex(ValueError, "Checkpoint settings/source/split differ"):
                    loss.fitting.run_fit(directory=root / "resume", **changed)
            loss.fitting.run_fit(directory=root / "resume", **arguments)
            a = torch.load(root / "full/last.pt", weights_only=False)
            b = torch.load(root / "resume/last.pt", weights_only=False)
            self.assertEqual(a["norm"], b["norm"])
            self.assertEqual([row["loss"] for row in a["history"]], [row["loss"] for row in b["history"]])
            for key in a["state_dict"]:
                torch.testing.assert_close(a["state_dict"][key], b["state_dict"][key], rtol=0, atol=0)
            self.assert_tensor_tree_equal(a["optimizer"], b["optimizer"])
            torch.testing.assert_close(a["torch_rng"], b["torch_rng"], rtol=0, atol=0)
            self.assertEqual(a["python_rng"], b["python_rng"])
            self.assertEqual(a["numpy_rng"][0], b["numpy_rng"][0])
            np.testing.assert_array_equal(a["numpy_rng"][1], b["numpy_rng"][1])
            self.assertEqual(a["numpy_rng"][2:], b["numpy_rng"][2:])
            with patch.object(loss.fitting, "fit_norm", side_effect=AssertionError("must reuse completed fit")):
                loss.fitting.run_fit(directory=root / "resume", **arguments)

    def test_identity_inherits_every_parent_field_and_adds_exactly_two_sources(self):
        parent = synthetic_parent_identity()
        original = deepcopy(parent)
        with tempfile.TemporaryDirectory(prefix=".loss_identity_") as directory:
            plan = Path(directory) / "synthetic_plan.md"
            plan.write_text("Synthetic loss-weight plan fixture.\n", encoding="utf-8")
            with patch.object(loss, "PLAN", plan):
                candidate = loss.experiment_identity(parent)
                self.assertEqual(candidate["source_sha256"], loss.current_sources())
            self.assertEqual(parent, original)
            self.assertEqual(len(parent["source_sha256"]), 9)
            self.assertEqual(len(candidate["source_sha256"]), 11)
            self.assertEqual(set(candidate) - set(parent), set(loss.NEW_PROVENANCE))
            for key, value in parent.items():
                if key == "source_sha256":
                    self.assertTrue(all(candidate[key][name] == digest for name, digest in value.items()))
                else:
                    self.assertEqual(candidate[key], value)
            for identity_key, source_key in loss.NEW_PROVENANCE.items():
                self.assertEqual(candidate[identity_key], candidate["source_sha256"][source_key])

    def test_changed_parent_source_or_identity_is_refused(self):
        parent = synthetic_parent_identity()
        for change in ("source", "wrapper_identity", "unknown_field"):
            altered = deepcopy(parent)
            if change == "source":
                altered["source_sha256"]["train.py"] = "0" * 64
            elif change == "wrapper_identity":
                altered["training_entrypoint_sha256"] = "0" * 64
            else:
                altered["unexpected"] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                loss.experiment_identity(altered)

    def test_runtime_environment_check_rejects_mismatch_before_parent_data_access(self):
        self.assertEqual(loss.check_environment(), loss.reference.TRAINING_VERSIONS)
        wrong = dict(loss.reference.TRAINING_VERSIONS, torch="different_torch_build")
        args = SimpleNamespace(phase="smoke")
        with patch.object(loss, "runtime_versions", return_value=wrong), patch.object(loss.SAVED, "load_mode", side_effect=AssertionError("must refuse before parent access")):
            with self.assertRaisesRegex(ValueError, "Runtime differs"):
                loss.execute(args)

    def test_output_scope_resolves_traversal_and_has_no_creation_side_effect(self):
        with tempfile.TemporaryDirectory(prefix=".loss_scope_") as directory:
            root = Path(directory)
            with patch.object(loss, "DEFAULT", root / "allowed"):
                accepted = loss.output_directory(root / "allowed/subdir")
                self.assertEqual(accepted, (root / "allowed/subdir").resolve())
                self.assertFalse(accepted.exists())
                for rejected in (root / "outside", root / "allowed/../outside", root):
                    with self.subTest(rejected=rejected), self.assertRaisesRegex(ValueError, "dedicated loss-weight"):
                        loss.output_directory(rejected)

    def test_benchmark_uses_fresh_separate_one_epoch_training_populations(self):
        cache = self.cache
        called = []
        with tempfile.TemporaryDirectory(prefix=".loss_bench_") as directory:
            args = SimpleNamespace(output_dir=Path(directory))

            def mock_fit(cache_arg, y, indices, validation, config, seed, folder, epochs, patience, batch, stage, identity):
                called.append(dict(indices=indices, validation=validation, config=config, seed=seed, folder=folder,
                                   epochs=epochs, patience=patience, batch=batch, stage=stage, identity=identity))
                folder.mkdir(parents=True)
                (folder / "history.json").write_text(json.dumps([dict(wall_seconds=2.)]))
                return dict(resources=[dict(wall_seconds=3.)], best_sha256="synthetic_hash")

            with patch.object(loss.fitting, "run_fit", side_effect=mock_fit):
                loss.benchmark(cache, cache.keys, loss.configuration(recipe()), args, dict(synthetic=True))
            self.assertEqual(len(called), 2)
            for row in called:
                self.assertEqual((row["config"]["cap"], row["config"]["pos_weight"], row["epochs"], row["patience"], row["batch"], row["stage"]),
                                 (128, 1., 1, 5, 256, "smoke"))
                self.assertFalse((cache.keys.iloc[row["indices"]].fold_id == 0).any())
            self.assertIsNotNone(called[0]["validation"])
            self.assertIsNone(called[1]["validation"])
            self.assertEqual((called[0]["seed"], called[1]["seed"]), (2026, 2126))
            self.assertNotEqual(called[0]["folder"], called[1]["folder"])
            summary = json.loads((Path(directory) / "benchmark/timing_summary.json").read_text())
            self.assertEqual(summary["maximum_cv_epoch_work_seconds"], 400.)


if __name__ == "__main__":
    unittest.main()
