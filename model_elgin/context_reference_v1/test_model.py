"""Synthetic-only model/serialization/CLI checks; no training or course data."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

from context_features import fit_reference
from data import encode_context, summarise
from model import SiteModel, load_model, source_sha256
from predict import score_batch

ROOT = Path(__file__).resolve().parent
CONFIG = {"id": "synthetic_test_only", "pool": "attention", "width": 48,
          "dropout": .25, "lr": .001, "weight_decay": .0001,
          "pos_weight": 3., "cap": 32, "summary_n": 63}
NORM = {"read_mean": [0.]*9, "read_sd": [1.]*9,
        "summary_mean": [0.]*63, "summary_sd": [1.]*63}


def synthetic_sites():
    rng = np.random.default_rng(72)
    contexts = ("AAGACCA", "TAGACCT", "AAGACCA", "UAGACCN")
    sites = []
    for number, context in enumerate(contexts):
        values = rng.uniform(.5, 2., size=(3+number, 9))
        values[:, [0, 3, 6]] *= .01
        values[:, [2, 5, 8]] *= 100
        sites.append((f"synthetic_{number}", number, context, values))
    return sites


def synthetic_reference(sites):
    sequence = np.stack([encode_context(row[2]) for row in sites])
    summaries = np.stack([summarise(row[3]) for row in sites])
    return fit_reference(sequence, summaries, np.arange(len(sites)), min_sites=1)


def bundle_for(mode, stage="final_data0"):
    torch.manual_seed(44)
    config = dict(CONFIG, context_mode=mode)
    model = SiteModel(config, NORM).eval()
    reference = synthetic_reference(synthetic_sites()) if mode == "relative" else None
    bundle = {"kind": "context_reference_v1", "stage": stage, "config": config,
                   "norm": NORM, "context_reference": reference,
                   "state_dict": model.state_dict(), "synthetic_unit_test_only": True,
                   "input_fingerprints": {"source_sha256": {
                       name: source_sha256(ROOT/name)
                       for name in ("model.py", "context_features.py", "data.py")}}}
    if stage == "final_data0":
        bundle.update(epoch=2, fit_signature="a"*64, fit_completed={
            "signature": "a"*64, "best_artifact_sha256": "b"*64,
            "epochs_completed": 2, "selected_epochs": 2})
    return model, bundle


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_extra_features_change_only_head_input_width(self):
        plain = SiteModel(dict(CONFIG, context_mode="none"), NORM)
        relative = SiteModel(dict(CONFIG, context_mode="relative"), NORM)
        self.assertEqual(plain.encoder[0].in_features, 37)
        self.assertEqual(relative.encoder[0].in_features, 37)
        self.assertEqual(plain.head[0].in_features, 235)
        self.assertEqual(relative.head[0].in_features, 244)
        self.assertEqual(plain.embedding.weight.shape, (5, 4))

    def test_padding_permutation_and_bag_duplication_invariance(self):
        torch.manual_seed(9)
        reads = torch.rand(2, 6, 9)
        mask = torch.tensor([[1,1,1,1,1,1], [1,1,0,0,0,0]], dtype=torch.bool)
        sequence = torch.randint(0, 5, (2, 7))
        summaries = torch.randn(2, 63)
        permutation = torch.tensor([4, 1, 3, 0, 5, 2])
        for mode in ("none", "relative"):
            model = SiteModel(dict(CONFIG, context_mode=mode), NORM).eval()
            extra = torch.randn(2, 9) if mode == "relative" else None
            with torch.inference_mode():
                expected = model(reads, mask, sequence, summaries, extra)
                padded = reads.clone()
                padded[~mask] = 100*torch.rand_like(padded[~mask])
                variants = [model(padded, mask, sequence, summaries, extra),
                    model(reads[:, permutation], mask[:, permutation], sequence, summaries, extra),
                    model(reads.repeat(1, 2, 1), mask.repeat(1, 2), sequence, summaries, extra)]
                self.assertTrue(torch.isfinite(expected).all())
                for value in variants:
                    torch.testing.assert_close(value, expected, rtol=0, atol=1e-6)

    def test_saved_reload_predictions_match_for_both_modes(self):
        sites = synthetic_sites()
        with tempfile.TemporaryDirectory(prefix=".context_model_test_", dir=ROOT) as temporary:
            for mode in ("none", "relative"):
                original, bundle = bundle_for(mode)
                path = Path(temporary)/(mode+".pt")
                torch.save(bundle, path)
                restored, loaded = load_model(path)
                first = score_batch(original, sites, bundle["context_reference"])
                second = score_batch(restored, sites, loaded["context_reference"])
                np.testing.assert_array_equal(first, second)
                self.assertTrue(np.isfinite(second).all())
                self.assertTrue(((second >= 0) & (second <= 1)).all())

    def test_api_rejects_development_by_default(self):
        with tempfile.TemporaryDirectory(prefix=".context_stage_test_", dir=ROOT) as temporary:
            for stage in ("cv_inner", "cv_refit", "final_fitting", "smoke"):
                _, bundle = bundle_for("none", stage)
                path = Path(temporary)/(stage+".pt")
                torch.save(bundle, path)
                with self.assertRaisesRegex(ValueError, "final_data0"):
                    load_model(path)
                _, accepted = load_model(path, allow_development_model=True)
                self.assertEqual(accepted["stage"], stage)

    def test_final_requires_complete_promotion_metadata(self):
        with tempfile.TemporaryDirectory(prefix=".context_final_test_", dir=ROOT) as temporary:
            path = Path(temporary)/"final.pt"
            _, valid = bundle_for("none")
            cases = []
            missing = dict(valid); missing.pop("fit_completed"); cases.append(missing)
            partial = dict(valid); partial["fit_completed"] = dict(valid["fit_completed"], epochs_completed=1)
            cases.append(partial)
            mismatch = dict(valid); mismatch["fit_completed"] = dict(valid["fit_completed"], signature="c"*64)
            cases.append(mismatch)
            for bundle in cases:
                torch.save(bundle, path)
                for allow in (False, True):
                    with self.assertRaisesRegex(ValueError, "completed"):
                        load_model(path, allow_development_model=allow)
            torch.save(valid, path)
            load_model(path)

    def test_semantic_source_fingerprints_required_and_checked(self):
        with tempfile.TemporaryDirectory(prefix=".context_source_test_", dir=ROOT) as temporary:
            path = Path(temporary)/"source_test.pt"
            for stage in ("final_data0", "smoke"):
                _, bundle = bundle_for("none", stage)
                bundle["input_fingerprints"]["source_sha256"]["context_features.py"] = "0"*64
                torch.save(bundle, path)
                with self.assertRaisesRegex(ValueError, "source differs"):
                    load_model(path, allow_development_model=True)
            _, bundle = bundle_for("none")
            bundle.pop("input_fingerprints")
            torch.save(bundle, path)
            with self.assertRaisesRegex(ValueError, "source fingerprint"):
                load_model(path)
            lf = Path(temporary)/"lf.py"; crlf = Path(temporary)/"crlf.py"
            lf.write_bytes(b"x = 1\ny = 2\n")
            crlf.write_bytes(b"x = 1\r\ny = 2\r\n")
            self.assertEqual(source_sha256(lf), source_sha256(crlf))

    def test_incomplete_reference_or_nonfinite_weights_rejected(self):
        with tempfile.TemporaryDirectory(prefix=".context_invalid_test_", dir=ROOT) as temporary:
            path = Path(temporary)/"invalid.pt"
            _, bundle = bundle_for("relative")
            bundle["context_reference"] = None
            torch.save(bundle, path)
            with self.assertRaisesRegex(ValueError, "reference"):
                load_model(path)
            _, bundle = bundle_for("none")
            bundle["state_dict"]["head.6.bias"][0] = float("nan")
            torch.save(bundle, path)
            with self.assertRaisesRegex(ValueError, "non-finite"):
                load_model(path)

    def test_relative_mode_requires_exact_nine_feature_tensor(self):
        model = SiteModel(dict(CONFIG, context_mode="relative"), NORM)
        inputs = [torch.zeros(2, 1, 9), torch.ones(2, 1, dtype=torch.bool),
                  torch.zeros(2, 7, dtype=torch.int64), torch.zeros(2, 63)]
        with self.assertRaisesRegex(ValueError, "N x 9"):
            model(*inputs)
        with self.assertRaisesRegex(ValueError, "N x 9"):
            model(*inputs, torch.zeros(2, 8))
        bad = torch.zeros(2, 9); bad[0, 0] = float("inf")
        with self.assertRaisesRegex(ValueError, "finite"):
            model(*inputs, bad)

    def test_cli_stage_guard_all_read_csv_manifest_and_reuse(self):
        with tempfile.TemporaryDirectory(prefix=".context_cli_test_", dir=ROOT) as temporary:
            directory = Path(temporary)
            source = directory/"input.json"
            model_path = directory/"smoke.pt"
            destination = directory/"predictions.csv"
            sites = synthetic_sites()[:2]
            with source.open("w", encoding="utf-8") as handle:
                for transcript, position, context, values in sites:
                    handle.write(json.dumps({transcript: {str(position): {context: values.tolist()}}})+"\n")
            _, bundle = bundle_for("relative", "smoke")
            torch.save(bundle, model_path)
            command = [sys.executable, "-B", str(ROOT/"predict.py"), "--input", str(source),
                       "--model", str(model_path), "--output", str(destination),
                       "--threads", "1", "--batch-size", "32", "--max-padded-reads", "6"]
            denied = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(denied.returncode, 0)
            self.assertIn("final_data0", denied.stderr)
            self.assertFalse(destination.exists())
            accepted = subprocess.run(command+["--allow-development-model"], capture_output=True, text=True)
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            before = destination.read_bytes()
            with destination.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, ["transcript_id", "transcript_position", "score"])
                rows = list(reader)
            self.assertEqual(len(rows), 2)
            manifest = json.loads(destination.with_suffix(".csv.manifest.json").read_text())
            self.assertEqual(manifest["n_sites"], 2)
            self.assertEqual(manifest["n_reads"], sum(len(row[3]) for row in sites))
            self.assertEqual(manifest["n_batches"], 2)
            self.assertEqual(manifest["stage"], "smoke")
            self.assertTrue(manifest["all_reads_used"])
            self.assertFalse(manifest["labels_read"])
            self.assertEqual(manifest["input_basename"], "input.json")
            reused = subprocess.run(command+["--allow-development-model"], capture_output=True, text=True)
            self.assertEqual(reused.returncode, 0, reused.stderr)
            self.assertEqual(destination.read_bytes(), before)
            # Permission remains necessary even when a valid old output exists.
            denied_again = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(denied_again.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
