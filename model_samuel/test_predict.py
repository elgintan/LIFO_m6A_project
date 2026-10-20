"""Small saved-model contract tests; no training or label files are used.

Run with the prediction environment: python -B test_predict.py
The only model inference is the supplied ten-site example. Protection checks
use disposable copies, so a future regression cannot overwrite real artifacts.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREDICT = ROOT / "code/predict.py"
INPUT = ROOT / "examples/input_10_sites.json"
EXPECTED = ROOT / "examples/predictions.csv"
ARTIFACTS = ("model.txt", "kmer_baseline.csv", "model_card.json")
HEADER = ["transcript_id", "transcript_position", "score"]
TEMP_ROOT = ROOT / "outputs/integration_20261020/tmp"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protected_hashes():
    paths = [INPUT, EXPECTED] + [ROOT/"artifact"/name for name in ARTIFACTS]
    return {str(path.relative_to(ROOT)): digest(path) for path in paths}


def csv_scores(path):
    scores = {}
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != HEADER:
            raise AssertionError("Prediction CSV must have the exact three columns")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise AssertionError("Malformed CSV row")
            key = row["transcript_id"], int(row["transcript_position"])
            if key in scores:
                raise AssertionError("Duplicate prediction key")
            score = float(row["score"])
            if not math.isfinite(score) or not 0 <= score <= 1:
                raise AssertionError("Scores must be finite and within [0, 1]")
            scores[key] = score
    return scores


def input_keys(path):
    keys = set()
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            for transcript, positions in json.loads(line).items():
                for position in positions:
                    key = transcript, int(position)
                    if key in keys:
                        raise AssertionError("Duplicate supplied example key")
                    keys.add(key)
    return keys


class PredictionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TEMP_ROOT.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        self.original_hashes = protected_hashes()

    def tearDown(self):
        self.assertEqual(protected_hashes(), self.original_hashes,
                         "The original example or frozen artifacts changed")

    def command(self, source, output, model_dir=None):
        command = [sys.executable, "-B", str(PREDICT), "--input", str(source), "--output", str(output)]
        if model_dir is not None:
            command += ["--model-dir", str(model_dir)]
        return command

    def test_saved_ten_site_example_from_unrelated_cwd_without_labels(self):
        with tempfile.TemporaryDirectory(prefix="predict_contract_", dir=TEMP_ROOT) as temporary:
            cwd = Path(temporary)
            self.assertEqual(list(cwd.iterdir()), [])
            output = cwd/"created_parent/predictions.csv"
            # Deliberately omit --model-dir: its default must be script-relative,
            # not dependent on the caller's current working directory.
            command = self.command(INPUT, output)
            self.assertFalse(any("--labels" in item for item in command))
            completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=45)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            actual, expected = csv_scores(output), csv_scores(EXPECTED)
            self.assertEqual(set(actual), input_keys(INPUT))
            self.assertEqual(set(actual), set(expected))
            self.assertEqual(len(actual), 10)
            differences = [abs(actual[key]-expected[key]) for key in expected]
            self.assertLessEqual(max(differences), 1e-12)
            print("Verified ten-site saved-model prediction: exact unique keys, finite [0,1] scores; "
                  f"maximum expected-score difference {max(differences):.17g}", flush=True)

    def test_reject_input_overwrite_without_changing_input(self):
        with tempfile.TemporaryDirectory(prefix="predict_input_guard_", dir=TEMP_ROOT) as temporary:
            directory = Path(temporary)
            source = directory/"input.json"
            shutil.copyfile(INPUT, source)
            before = digest(source)
            completed = subprocess.run(self.command(source, source), cwd=directory,
                                       capture_output=True, text=True, timeout=45)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("output must not overwrite", completed.stderr)
            self.assertEqual(digest(source), before)

    def test_reject_each_frozen_artifact_as_output_without_changing_files(self):
        with tempfile.TemporaryDirectory(prefix="predict_artifact_guard_", dir=TEMP_ROOT) as temporary:
            directory = Path(temporary)
            model_dir = directory/"artifact"
            model_dir.mkdir()
            for name in ARTIFACTS:
                shutil.copyfile(ROOT/"artifact"/name, model_dir/name)
            before = {name: digest(model_dir/name) for name in ARTIFACTS}
            for name in ARTIFACTS:
                with self.subTest(protected_artifact=name):
                    completed = subprocess.run(self.command(INPUT, model_dir/name, model_dir),
                        cwd=directory, capture_output=True, text=True, timeout=45)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn("output must not overwrite", completed.stderr)
                    self.assertEqual({item: digest(model_dir/item) for item in ARTIFACTS}, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
