"""Launcher safety/validation checks with tiny fixtures and mocked vendor calls.

No Torch, vendor package, published model or real course signals are imported.
"""
import argparse
import ast
import copy
import csv
import gzip
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

import numpy as np

import prepare_input as adapter
import inference_runner as runner


def source_site(position):
    return {"ENST_test": {str(position): {"AAGACCA": [[0.01, 2.0, 120.0] * 3 for _ in range(20)]}}}


class FakeDataset:
    def __init__(self, input_dir):
        self.input_dir = input_dir
        self.indices = np.arange(9)
        self.count = 2
        self.invalid_norm = False
        self.corrupt_features = False

    def __len__(self):
        return self.count

    def get_norm_factor(self, kmers):
        return np.zeros(9), np.zeros(9) if self.invalid_norm else np.ones(9)

    def load_data(self, index):
        with (self.input_dir / "data.json").open("rb") as handle:
            transcript, position, context, rows = adapter.decode_site(next(handle), 10)
        values = np.asarray([row[:9] for row in rows])
        if self.corrupt_features:
            values = values + 1
        return transcript, int(position), np.arange(len(rows)), values, context


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="m6anet_runner_", dir=os.environ.get("M6ANET_TEST_TMP_ROOT"))
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.json.gz"
        with gzip.open(self.source, "wt", encoding="utf-8") as handle:
            for position in (244, 467):
                handle.write(json.dumps(source_site(position)) + "\n")
        self.input_dir = self.root / "input"
        self.output_dir = self.root / "output"
        self.receipt = adapter.prepare(self.source, self.input_dir)
        self.dataset = FakeDataset(self.input_dir)
        self.vocabulary = {"AAGAC", "AGACC", "GACCA"}
        self.expected = {
            ("ENST_test", "244"): {"n_reads": 20, "central_kmer": "AGACC"},
            ("ENST_test", "467"): {"n_reads": 20, "central_kmer": "AGACC"},
        }
        self.site_rows = [[key[0], key[1], item["n_reads"], score, item["central_kmer"], 0.9]
                          for (key, item), score in zip(self.expected.items(), (0.25, 0.75))]
        self.individual_rows = [[key[0], key[1], ordinal, 0.1]
                                for key, item in self.expected.items()
                                for ordinal in range(item["n_reads"])]

    def tearDown(self):
        self.temporary.cleanup()

    def write_csv(self, path, header, rows):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)

    def write_outputs(self, output_dir):
        self.write_csv(output_dir / "data.site_proba.csv", runner.SITE_HEADER, self.site_rows)
        self.write_csv(output_dir / "data.indiv_proba.csv", runner.INDIV_HEADER, self.individual_rows)

    def fake_preflight(self):
        return ({
            "kind": "mocked_test_no_vendor", "parameters": dict(runner.FIXED),
            "runner": runner.file_record(runner.__file__),
            "adapter": runner.file_record(adapter.__file__),
            "input_completion_receipt": runner.file_record(self.input_dir / "complete.json"),
            "input_files": self.receipt["files"], "vendor_files": {"dummy": "identity"},
        }, self.expected, self.root, object())

    def mocked_vendor_modules(self, behavior):
        fake_torch = types.ModuleType("torch")
        fake_torch.set_num_threads = mock.Mock()
        fake_inference = types.ModuleType("m6anet.scripts.inference")
        parsed = argparse.Namespace(out_dir=str(self.output_dir))
        fake_parser = mock.Mock()
        fake_parser.parse_args.return_value = parsed
        fake_inference.argparser = mock.Mock(return_value=fake_parser)
        fake_inference.main = behavior
        fake_scripts = types.ModuleType("m6anet.scripts")
        fake_scripts.inference = fake_inference
        fake_m6anet = types.ModuleType("m6anet")
        fake_m6anet.scripts = fake_scripts
        return {"torch": fake_torch, "m6anet": fake_m6anet, "m6anet.scripts": fake_scripts}, fake_parser

    def test_full_input_audit_uses_no_labels_and_confirms_nine_columns(self):
        receipt, expected, audit = runner.audit_prepared_input(self.input_dir, self.dataset, self.vocabulary)
        self.assertEqual(receipt, self.receipt)
        self.assertEqual(expected, self.expected)
        self.assertEqual((audit["sites"], audit["reads"]), (2, 40))
        self.assertEqual(audit["vendor_feature_indices"], list(range(9)))
        self.assertTrue(audit["vendor_first_site_exact_original_nine_values"])

    def test_input_hash_vocabulary_normalization_and_feature_guards(self):
        with self.assertRaisesRegex(ValueError, "outside vendor vocabulary"):
            runner.audit_prepared_input(self.input_dir, self.dataset, {"AAGAC"})
        self.dataset.invalid_norm = True
        with self.assertRaisesRegex(ValueError, "normalization"):
            runner.audit_prepared_input(self.input_dir, self.dataset, self.vocabulary)
        self.dataset.invalid_norm = False
        self.dataset.indices = np.arange(1, 10)
        with self.assertRaisesRegex(ValueError, "nine feature columns"):
            runner.audit_prepared_input(self.input_dir, self.dataset, self.vocabulary)
        self.dataset.indices = np.arange(9)
        self.dataset.count = 1
        with self.assertRaisesRegex(ValueError, "excluded"):
            runner.audit_prepared_input(self.input_dir, self.dataset, self.vocabulary)
        self.dataset.count = 2
        self.dataset.corrupt_features = True
        with self.assertRaisesRegex(ValueError, "preserve nine signals"):
            runner.audit_prepared_input(self.input_dir, self.dataset, self.vocabulary)
        self.dataset.corrupt_features = False
        with (self.input_dir / "data.json").open("ab") as handle:
            handle.write(b" ")
        with self.assertRaisesRegex(ValueError, "Input file identity mismatch"):
            runner.audit_prepared_input(self.input_dir, self.dataset, self.vocabulary)

    def test_site_validation_checks_correct_score_column_and_full_coverage(self):
        path = self.root / "site.csv"
        self.write_csv(path, runner.SITE_HEADER, self.site_rows)
        result = runner.validate_site_csv(path, self.expected)
        self.assertEqual(result["score_column"], "probability_modified")
        self.assertEqual((result["minimum_score"], result["maximum_score"]), (0.25, 0.75))
        self.assertTrue(result["unique_exact_input_coverage"])

    def test_invalid_site_outputs_never_pass_validation(self):
        cases = [("missing", self.site_rows[:1]),
                 ("duplicate", self.site_rows + [self.site_rows[0]])]
        for name, column, value in (("NaN", 3, "nan"), ("infinity", 3, "inf"),
                                    ("negative", 3, -0.1), ("above_one", 3, 1.01),
                                    ("wrong_count", 2, 19), ("wrong_context", 4, "AAAAA"),
                                    ("invalid_ratio", 5, "nan"), ("wrong_key", 1, 999),
                                    ("noncanonical_key", 1, "0244")):
            rows = copy.deepcopy(self.site_rows)
            rows[0][column] = value
            cases.append((name, rows))
        path = self.root / "site.csv"
        for name, rows in cases:
            with self.subTest(name=name):
                self.write_csv(path, runner.SITE_HEADER, rows)
                with self.assertRaises(ValueError):
                    runner.validate_site_csv(path, self.expected)

    def test_individual_validation_preserves_only_local_ordinal_identity(self):
        path = self.root / "individual.csv"
        self.write_csv(path, runner.INDIV_HEADER, self.individual_rows)
        result = runner.validate_individual_csv(path, self.expected)
        self.assertEqual(result["rows"], 40)
        self.assertFalse(result["biological_read_identifiers"])
        for name, rows in (("missing", self.individual_rows[:-1]),
                           ("extra", self.individual_rows + [self.individual_rows[0]]),
                           ("wrong_order", list(reversed(self.individual_rows)))):
            with self.subTest(name=name):
                self.write_csv(path, runner.INDIV_HEADER, rows)
                with self.assertRaises(ValueError):
                    runner.validate_individual_csv(path, self.expected)
        for column, value in ((2, 0.5), (2, "nan"), (3, "inf")):
            rows = copy.deepcopy(self.individual_rows)
            rows[0][column] = value
            self.write_csv(path, runner.INDIV_HEADER, rows)
            with self.assertRaises(ValueError):
                runner.validate_individual_csv(path, self.expected)

    def test_reuse_and_input_output_overlap_refused_before_vendor_import(self):
        self.output_dir.mkdir()
        protected = self.output_dir / "existing.txt"
        protected.write_text("keep")
        with mock.patch.object(runner, "preflight") as preflight:
            with self.assertRaisesRegex(ValueError, "nonempty"):
                runner.run(self.input_dir, self.output_dir)
            with self.assertRaisesRegex(ValueError, "separate"):
                runner.run(self.input_dir, self.input_dir / "nested")
            preflight.assert_not_called()
        self.assertEqual(protected.read_text(), "keep")

    def test_failed_preflight_preserves_failure_receipt_without_complete(self):
        with mock.patch.object(runner, "preflight", side_effect=ValueError("test bad input")):
            with self.assertRaisesRegex(ValueError, "test bad input"):
                runner.run(self.input_dir, self.output_dir)
        status = json.loads((self.output_dir / "runner_status.json").read_text())
        self.assertEqual(status["status"], "failed_partial_outputs_preserved")
        self.assertEqual(status["exit_code"], 1)
        self.assertFalse((self.output_dir / "complete.json").exists())

    def test_mocked_success_records_exact_parameters_hashes_and_complete(self):
        modules, parser = self.mocked_vendor_modules(lambda arguments: self.write_outputs(self.output_dir))
        with mock.patch.object(runner, "preflight", return_value=self.fake_preflight()), \
                mock.patch.dict(sys.modules, modules), \
                mock.patch.object(runner, "vendor_inventory", return_value={"dummy": "identity"}), \
                mock.patch.object(runner.multiprocessing, "set_start_method") as spawn:
            result = runner.run(self.input_dir, self.output_dir)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["site_output_audit"]["sites"], 2)
        self.assertEqual(result["individual_output_audit"]["rows"], 40)
        self.assertIn("parent_process_cpu_seconds", result["total_resources"])
        self.assertTrue((self.output_dir / "complete.json").exists())
        spawn.assert_called_once_with("spawn", force=True)
        arguments = parser.parse_args.call_args.args[0]
        self.assertEqual(arguments[arguments.index("--save_per_batch") + 1], "2147483647")
        self.assertEqual(arguments[arguments.index("--seed") + 1], "2026")
        self.assertEqual(arguments[arguments.index("--num_iterations") + 1], "1000")
        modules["torch"].set_num_threads.assert_called_once_with(4)

    def test_mocked_vendor_failure_keeps_partial_file_and_fails_closed(self):
        def fail(arguments):
            (self.output_dir / "data.site_proba.csv").write_text("partial fixture")
            raise RuntimeError("mocked vendor failure")
        modules, _parser = self.mocked_vendor_modules(fail)
        with mock.patch.object(runner, "preflight", return_value=self.fake_preflight()), \
                mock.patch.dict(sys.modules, modules), \
                mock.patch.object(runner.multiprocessing, "set_start_method"):
            with self.assertRaisesRegex(RuntimeError, "mocked vendor failure"):
                runner.run(self.input_dir, self.output_dir)
        self.assertEqual((self.output_dir / "data.site_proba.csv").read_text(), "partial fixture")
        status = json.loads((self.output_dir / "runner_status.json").read_text())
        self.assertEqual(status["status"], "failed_partial_outputs_preserved")
        self.assertFalse((self.output_dir / "complete.json").exists())

    def test_changed_input_after_mocked_vendor_call_cannot_receive_complete(self):
        def change_input(arguments):
            self.write_outputs(self.output_dir)
            with (self.input_dir / "data.info").open("ab") as handle:
                handle.write(b" ")
        modules, _parser = self.mocked_vendor_modules(change_input)
        with mock.patch.object(runner, "preflight", return_value=self.fake_preflight()), \
                mock.patch.dict(sys.modules, modules), \
                mock.patch.object(runner, "vendor_inventory", return_value={"dummy": "identity"}), \
                mock.patch.object(runner.multiprocessing, "set_start_method"):
            with self.assertRaisesRegex(ValueError, "Input data changed"):
                runner.run(self.input_dir, self.output_dir)
        self.assertFalse((self.output_dir / "complete.json").exists())

    def test_preflight_only_creates_no_output_and_child_seed_is_module_scope(self):
        with mock.patch.object(runner, "preflight", return_value=self.fake_preflight()):
            result = runner.run(self.input_dir, self.output_dir, inspect_only=True)
        self.assertEqual(result["status"], "preflight_complete_no_forward_pass")
        self.assertFalse(self.output_dir.exists())
        tree = ast.parse(Path(runner.__file__).read_text(encoding="utf-8"))
        calls = [node.value for node in tree.body if isinstance(node, ast.Expr)
                 and isinstance(node.value, ast.Call)]
        seed_calls = [node for node in calls if isinstance(node.func, ast.Attribute)
                      and node.func.attr == "seed"]
        self.assertEqual(len(seed_calls), 1)
        self.assertIsInstance(seed_calls[0].args[0], ast.Name)
        self.assertEqual(seed_calls[0].args[0].id, "FIXED_SEED")
        self.assertEqual(runner.FIXED_SEED, 2026)
        self.assertEqual(runner.FIXED["n_processes"], 1)
        main_calls = [node for node in tree.body if isinstance(node, ast.If)
                      and "__main__" in ast.dump(node.test)]
        self.assertEqual(len(main_calls), 1)


if __name__ == "__main__":
    unittest.main()
