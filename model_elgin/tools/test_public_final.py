"""Synthetic software check of fixed-recipe promotion; not a data0 experiment."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

SPEC = importlib.util.spec_from_file_location("public_final_training", Path(__file__).resolve().parents[1] / "train_final.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TinyCache:
    def __init__(self):
        rng = np.random.default_rng(14)
        self.reads = rng.uniform(.2, 2, (24, 8, 9)).astype(np.float32)
        self.summary = rng.normal(size=(24, 63)).astype(np.float32)
        self.seq = rng.integers(0, 4, size=(24, 7), dtype=np.int64)

    def bag(self, index):
        return self.reads[index]


class PublicFinalTests(unittest.TestCase):
    def test_real_tiny_fixed_duration_promotes_reuses_and_detects_changed_artifact(self):
        MODULE.core.torch.set_num_threads(1)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            cache = TinyCache()
            config = dict(MODULE.core.BASE, cap=128, context_mode="none", min_sites=30)
            identity = dict(source_sha256=MODULE.core.source_hashes(), synthetic_only=True)
            y = np.asarray([0, 1] * 12)
            with contextlib.redirect_stdout(io.StringIO()):
                completed = MODULE.core.run_fit(cache, y, np.arange(24), None, config, 2026,
                                                folder / "fit", 18, 5, 256, "final_fitting", identity)
            self.assertEqual(completed["epochs_completed"], 18)
            self.assertEqual(completed["best_epoch"], 18)
            model = MODULE.promote(folder / "fit", completed)
            from model import load_model
            _, bundle = load_model(model)
            self.assertEqual(bundle["stage"], "final_data0")
            self.assertEqual(bundle["config"]["cap"], 128)
            self.assertEqual(bundle["fit_completed"]["selected_epochs"], 18)
            before = MODULE.sha256(model)
            self.assertEqual(MODULE.promote(folder / "fit", completed), model)
            self.assertEqual(MODULE.sha256(model), before)
            # Recover a crash after artifact save but before receipt commit.
            (folder / "frozen_model.json").unlink()
            MODULE.promote(folder / "fit", completed)
            self.assertEqual(MODULE.sha256(model), before)
            with mock.patch.object(MODULE.core, "fit_norm", side_effect=AssertionError("No completed-fit replay")):
                reused = MODULE.core.run_fit(cache, y, np.arange(24), None, config, 2026,
                                             folder / "fit", 18, 5, 256, "final_fitting", identity)
            self.assertEqual(reused, completed)
            bundle["state_dict"]["head.0.weight"][0, 0] += 1
            MODULE.core.torch.save(bundle, model)
            with self.assertRaisesRegex(ValueError, "artifact changed"):
                MODULE.promote(folder / "fit", completed)

    def test_incomplete_fit_cannot_be_promoted(self):
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            MODULE.promote(Path("unused"), dict(epochs_completed=17, best_epoch=17, validation_sites=0))


if __name__ == "__main__":
    unittest.main()
