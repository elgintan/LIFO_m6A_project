"""Synthetic checks of split isolation and actual interrupted-fit recovery."""
from pathlib import Path
from types import SimpleNamespace
import json
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import torch

import train
from data import encode_context, summarise
from model import summary_transform, load_model

ROOT = Path(__file__).resolve().parent


def metadata():
    return pd.DataFrame([dict(gene_id=f"gene{f}_{g}", fold_id=f,
                              transcript_id=f"transcript{f}_{g}", transcript_position=j,
                              label=j % 2)
                         for f in range(5) for g in range(4) for j in range(4)])


class SyntheticCache:
    def __init__(self):
        rng = np.random.default_rng(50)
        self.keys = metadata()
        self.seq = np.stack([encode_context("AAGACCA" if i % 2 else "TAGACCT")
                             for i in range(len(self.keys))])
        self.bags = []
        for i in range(len(self.keys)):
            values = rng.uniform(.5, 2., size=(3 + i % 6, 9)).astype(np.float32)
            values[:, [0, 3, 6]] *= .01
            values[:, [2, 5, 8]] *= 100
            self.bags.append(values)
        self.off = np.r_[0, np.cumsum([len(x) for x in self.bags])]
        self.raw_summary = np.stack([summarise(x) for x in self.bags])
        self.summary = summary_transform(self.raw_summary)

    def bag(self, index):
        return self.bags[index]


class TrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_gene_roles_and_whole_gene_smoke_population(self):
        meta = metadata()
        population = train.choose_population(meta, smoke_genes=2)
        changed_labels = meta.copy()
        changed_labels["label"] = 1 - changed_labels.label
        np.testing.assert_array_equal(population, train.choose_population(changed_labels, 2))
        selected_genes = set(meta.iloc[population].gene_id)
        self.assertEqual(len(selected_genes), 10)
        self.assertEqual(set(population), set(np.flatnonzero(meta.gene_id.isin(selected_genes))))
        for fold in range(5):
            initial, inner, refit, assessment, audit = train.partition(meta, population, fold)
            self.assertEqual(set(meta.iloc[assessment].fold_id), {fold})
            self.assertEqual(set(meta.iloc[inner].fold_id), {(fold + 1) % 5})
            self.assertEqual(set(refit), set(initial) | set(inner))
            self.assertFalse(set(meta.iloc[refit].gene_id) & set(meta.iloc[assessment].gene_id))
            self.assertTrue(audit["zero_gene_overlap"])

    def test_cross_fold_gene_rejected(self):
        meta = metadata()
        meta.loc[meta.fold_id == 1, "gene_id"] = "gene0_0"
        with self.assertRaisesRegex(ValueError, "Gene leakage|Assessment gene"):
            train.partition(meta, np.arange(len(meta)), 0)

    def test_normalization_does_not_learn_from_held_out_values(self):
        cache = SyntheticCache()
        indices = np.arange(12)
        original = train.fit_norm(cache, indices)
        cache.summary[12:] = 999999
        for bag in cache.bags[12:]:
            bag[:] = 999999
        self.assertEqual(original, train.fit_norm(cache, indices))

    def test_real_epoch_checkpoint_resume_is_exact_for_both_modes(self):
        cache = SyntheticCache()
        y = cache.keys.label.to_numpy()
        fitting, validation = np.arange(32), np.arange(32, 48)
        for mode in ("none", "relative"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix=".resume_test_", dir=ROOT) as temp:
                root = Path(temp)
                config = dict(train.BASE, context_mode=mode, min_sites=2)
                arguments = dict(cache=cache, y=y, indices=fitting, validation=validation,
                                 config=config, seed=120, max_epochs=2, patience=3,
                                 batch_size=8, stage="smoke", identity={"synthetic": True})
                full = train.run_fit(directory=root / "full", **arguments)
                original_atomic = train.atomic_torch

                def interrupt_after_checkpoint(path, payload):
                    original_atomic(path, payload)
                    if Path(path).name == "last.pt" and payload["epoch"] == 1:
                        raise KeyboardInterrupt("simulated interruption after a completed epoch")

                with patch.object(train, "atomic_torch", side_effect=interrupt_after_checkpoint):
                    with self.assertRaises(KeyboardInterrupt):
                        train.run_fit(directory=root / "resumed", **arguments)
                self.assertFalse((root / "resumed/complete.json").exists())
                resumed = train.run_fit(directory=root / "resumed", **arguments)
                a = torch.load(root / "full/last.pt", weights_only=False)
                b = torch.load(root / "resumed/last.pt", weights_only=False)
                self.assertEqual(full["best_epoch"], resumed["best_epoch"])
                self.assertEqual([x["loss"] for x in a["history"]], [x["loss"] for x in b["history"]])
                for name, expected in a["state_dict"].items():
                    torch.testing.assert_close(expected, b["state_dict"][name], rtol=0, atol=0)
                with patch.object(train, "fit_norm", side_effect=AssertionError("should reuse completed fit")):
                    self.assertEqual(resumed, train.run_fit(directory=root / "resumed", **arguments))
                changed = dict(arguments, config=dict(config, dropout=.1))
                with self.assertRaisesRegex(ValueError, "Completed fit changed"):
                    train.run_fit(directory=root / "resumed", **changed)

    def test_fitting_validation_overlap_rejected_before_fitting(self):
        cache = SyntheticCache()
        with tempfile.TemporaryDirectory(prefix=".overlap_test_", dir=ROOT) as temp:
            with self.assertRaisesRegex(ValueError, "overlap"):
                train.run_fit(cache, cache.keys.label.to_numpy(), np.arange(10), np.arange(5, 15),
                              dict(train.BASE, context_mode="none", min_sites=2), 1, temp,
                              1, 1, 8, "smoke", {})

    def test_recovery_after_best_save_before_epoch_checkpoint(self):
        cache = SyntheticCache()
        with tempfile.TemporaryDirectory(prefix=".best_gap_test_", dir=ROOT) as temp:
            root = Path(temp)
            arguments = dict(cache=cache, y=cache.keys.label.to_numpy(), indices=np.arange(16),
                             validation=None, config=dict(train.BASE, context_mode="none", min_sites=2),
                             seed=17, max_epochs=2, patience=2, batch_size=8,
                             stage="smoke", identity={"synthetic": True})
            train.run_fit(directory=root / "full", **arguments)
            original_atomic = train.atomic_torch

            def interrupt_ahead_best(path, payload):
                original_atomic(path, payload)
                if Path(path).name == "best.pt" and payload["epoch"] == 2:
                    raise KeyboardInterrupt("best saved but epoch2 not committed")

            with patch.object(train, "atomic_torch", side_effect=interrupt_ahead_best):
                with self.assertRaises(KeyboardInterrupt):
                    train.run_fit(directory=root / "resumed", **arguments)
            self.assertEqual(torch.load(root / "resumed/last.pt", weights_only=False)["epoch"], 1)
            train.run_fit(directory=root / "resumed", **arguments)
            a = torch.load(root / "full/best.pt", weights_only=False)
            b = torch.load(root / "resumed/best.pt", weights_only=False)
            for name, expected in a["state_dict"].items():
                torch.testing.assert_close(expected, b["state_dict"][name], rtol=0, atol=0)

    def test_final_epoch_resume_recreates_logs(self):
        cache = SyntheticCache()
        with tempfile.TemporaryDirectory(prefix=".log_gap_test_", dir=ROOT) as temp:
            root = Path(temp)
            arguments = dict(cache=cache, y=cache.keys.label.to_numpy(), indices=np.arange(16),
                             validation=None, config=dict(train.BASE, context_mode="none", min_sites=2),
                             seed=17, max_epochs=1, patience=2, batch_size=8,
                             stage="smoke", identity={"synthetic": True}, directory=root)
            original_atomic = train.atomic_torch

            def interrupt_last(path, payload):
                original_atomic(path, payload)
                if Path(path).name == "last.pt":
                    raise KeyboardInterrupt("final checkpoint committed but logs not flushed")

            with patch.object(train, "atomic_torch", side_effect=interrupt_last):
                with self.assertRaises(KeyboardInterrupt):
                    train.run_fit(**arguments)
            self.assertFalse((root / "history.json").exists())
            train.run_fit(**arguments)
            self.assertEqual(len(json.loads((root / "history.json").read_text())), 1)
            self.assertEqual(len((root / "training.log").read_text().splitlines()), 1)

    def test_final_requires_full_cv_and_same_recipe_before_any_fit(self):
        with tempfile.TemporaryDirectory(prefix=".final_guard_", dir=ROOT) as temp:
            root = Path(temp)
            cv = root / "cv/relative"
            cv.mkdir(parents=True)
            config = dict(train.BASE, context_mode="relative", min_sites=30)
            recipe = dict(config=config, identity={}, seed=2026, batch_size=256, threads=1)
            (cv / "recipe.json").write_text(json.dumps(recipe))
            (cv / "progress.json").write_text(json.dumps(dict(full_five_folds=False, full_data0_population=True)))
            args = SimpleNamespace(output_dir=root, seed=2026, batch_size=256, threads=1, patience=5)
            with patch.object(train, "run_fit", side_effect=AssertionError("must not fit")):
                with self.assertRaisesRegex(ValueError, "full-population"):
                    train.run_final(None, metadata(), config, args, {})
                (cv / "progress.json").write_text(json.dumps(dict(full_five_folds=True, full_data0_population=True)))
                args.seed += 1
                with self.assertRaisesRegex(ValueError, "differs"):
                    train.run_final(None, metadata(), config, args, {})

    def test_completed_fit_promotes_portable_final_and_rejects_modified_artifact(self):
        # Synthetic CV receipts stand in for prior evaluation; this tests final-fit
        # promotion, not the immutable course-data scoring or any predictive claim.
        cache = SyntheticCache()
        for mode in ("none", "relative"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix=".promotion_test_", dir=ROOT) as temp:
                root = Path(temp)
                cv = root / "cv" / mode
                cv.mkdir(parents=True)
                config = dict(train.BASE, context_mode=mode, min_sites=2)
                identity = {"source_sha256": train.source_hashes(), "synthetic_only": True}
                args = SimpleNamespace(output_dir=root, seed=2, batch_size=16, threads=1, patience=5)
                (cv / "recipe.json").write_text(json.dumps(dict(config=config, identity=identity,
                    seed=2, batch_size=16, threads=1)))
                (cv / "data0_oof.csv").write_text("synthetic receipt only\n")
                (cv / "data0_cv_metrics.json").write_text('{"synthetic_only": true}')
                (cv / "progress.json").write_text(json.dumps(dict(full_five_folds=True,
                    full_data0_population=True, oof_sha256=train.sha256(cv / "data0_oof.csv"),
                    cv_metrics_sha256=train.sha256(cv / "data0_cv_metrics.json"))))
                with patch.object(train, "verify_saved_fold", return_value={"selected_epochs": 1}):
                    train.run_final(cache, cache.keys, config, args, identity)
                    path = root / "final" / mode / "model.pt"
                    model, bundle = load_model(path)
                    self.assertEqual(bundle["fit_completed"]["epochs_completed"], 1)
                    self.assertEqual(bundle["stage"], "final_data0")
                    self.assertEqual(model.context_mode, mode)
                    with self.assertRaisesRegex(ValueError, "requires final_data0"):
                        load_model(path.with_name("best.pt"))
                    train.run_final(cache, cache.keys, config, args, identity)
                    changed = torch.load(path, weights_only=False)
                    changed["state_dict"]["head.0.weight"][0, 0] += 1
                    torch.save(changed, path)
                    with self.assertRaisesRegex(ValueError, "frozen model changed"):
                        train.run_final(cache, cache.keys, config, args, identity)


if __name__ == "__main__":
    unittest.main(verbosity=2)
