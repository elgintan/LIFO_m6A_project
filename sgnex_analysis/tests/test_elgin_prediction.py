"""Selected-model export contracts on synthetic fixtures; no real inference.

The mocked subprocess writes explicitly marked fixture probabilities. These
tests establish QC, byte preservation, completeness and interruption behaviour,
not biological performance. The real model CLI is checked separately.
"""
import csv
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("elgin_run_adapter_test", ROOT / "scripts/predict_elgin_run.py")
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)


class ElginPrediction(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "outputs/checks/tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="elgin-adapter-", dir=scratch)
        self.folder = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def record(self, position, reads, value=1.0):
        return json.dumps({"ENST_SOFTWARE.7": {str(position): {"AGGACAC": [[value] * 9 for _ in range(reads)]}}},
                          separators=(",", ":")).encode("ascii")

    def arguments(self, source=None, output="pred.csv", minimum=20):
        if source is None:
            source = self.folder / "input.json"
        return ADAPTER.parser().parse_args(["--input", str(source), "--run-id", "synthetic-software-fixture",
                                             "--output", str(self.folder / output), "--min-reads", str(minimum)])

    def fake_inference(self, args, paths):
        # Fixed mock values are confined to temporary software fixtures.
        sites = list(ADAPTER.DATA.iter_sites(paths["eligible_input"]))
        with paths["raw_export"].open("x", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(["transcript_id", "transcript_position", "score"])
            for transcript, position, _context, _reads in sites:
                writer.writerow([transcript, position, "0.12345678901234567"])
        paths["log"].write_text("MOCK inference: synthetic software fixture only\n", encoding="utf-8")
        ADAPTER.save_json(paths["core_manifest"], dict(
            status="complete", stage="final_data0", model_sha256=ADAPTER.SELECTED_MODEL_SHA,
            input_sha256=ADAPTER.sha(paths["eligible_input"]), output_sha256=ADAPTER.sha(paths["raw_export"]),
            code_sha256={name: ADAPTER.code_sha(ADAPTER.CORE / name) for name in ADAPTER.CORE_FILES},
            all_reads_used=True, labels_read=False, exact_input_key_coverage=True,
            threads=args.threads, batch_size_limit=args.batch_size, max_padded_reads_budget=args.max_padded_reads,
            n_sites=len(sites), n_reads=sum(len(row[3]) for row in sites), resources={"synthetic_fixture_only": True}))

    def test_coverage_boundary_outliers_byte_identity_and_complete_reuse(self):
        records = [self.record(101, 19), self.record(102, 20), self.record(103, 21, value=1e6)]
        # Different newline styles and a final unterminated record are retained.
        original = records[0] + b"\r\n" + records[1] + b"\n" + records[2]
        source = self.folder / "input.json"
        source.write_bytes(original)
        args = self.arguments()
        with patch.object(ADAPTER, "run_core_prediction", side_effect=self.fake_inference) as inference:
            result = ADAPTER.predict(args)
            paths = ADAPTER.paths_for(args.output)
            self.assertEqual(result["counts"]["input_sites"], 3)
            self.assertEqual(result["counts"]["eligible_sites"], 2)
            self.assertEqual(result["counts"]["scored_sites"], 2)
            self.assertEqual(result["counts"]["below_minimum_source_reads"], 1)
            self.assertEqual(result["counts"]["input_reads"], 60)
            self.assertEqual(result["counts"]["eligible_reads"], 41)
            self.assertEqual(result["counts"]["reads_discarded_nonfinite"], 0)
            with gzip.open(paths["eligible_input"], "rb") as handle:
                self.assertEqual(handle.read(), records[1] + b"\n" + records[2])
            with gzip.open(paths["metadata"], "rt", newline="") as handle:
                meta = list(csv.DictReader(handle))
            self.assertEqual([row["n_reads_input"] for row in meta], ["19", "20", "21"])
            self.assertEqual([row["prediction_status"] for row in meta],
                             ["below_minimum_source_reads", "eligible", "eligible"])
            self.assertTrue(all(row["transcript_id"] == "ENST_SOFTWARE.7" for row in meta))
            self.assertTrue(all(row["sequence_7mer"] == "AGGACAC" for row in meta))
            self.assertEqual(paths["task2"].read_bytes(), paths["raw_export"].read_bytes())
            self.assertIn(b"0.12345678901234567", paths["task2"].read_bytes())
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(ADAPTER.predict(args), result)
            self.assertEqual(inference.call_count, 1)

    def test_nonfinite_below_minimum_aborts_before_any_model_invocation(self):
        source = self.folder / "input.json"
        original = self.record(101, 20) + b"\n" + self.record(102, 1, value=float("nan")) + b"\n"
        source.write_bytes(original)
        args = self.arguments()
        with patch.object(ADAPTER, "run_core_prediction") as inference:
            with self.assertRaisesRegex(ValueError, "non-finite"):
                ADAPTER.predict(args)
            inference.assert_not_called()
        paths = ADAPTER.paths_for(args.output)
        self.assertFalse(paths["receipt"].exists())
        self.assertFalse(paths["task2"].exists())
        self.assertFalse(paths["lock"].exists())
        self.assertTrue(paths["eligible_partial"].exists())
        self.assertIn("failed_partial", ADAPTER.read_json(paths["status"])["status"])
        self.assertEqual(source.read_bytes(), original)

    def test_duplicate_site_even_below_minimum_is_not_silently_ignored(self):
        source = self.folder / "input.json"
        source.write_bytes(self.record(101, 20) + b"\n" + self.record(101, 1) + b"\n")
        args = self.arguments()
        with patch.object(ADAPTER, "run_core_prediction") as inference:
            with self.assertRaisesRegex(ValueError, "duplicate transcript-position"):
                ADAPTER.predict(args)
            inference.assert_not_called()
        self.assertFalse(ADAPTER.paths_for(args.output)["receipt"].exists())

    def test_changed_completed_outputs_or_arguments_are_refused(self):
        source = self.folder / "input.json"
        source.write_bytes(self.record(101, 20) + b"\n")
        args = self.arguments()
        with patch.object(ADAPTER, "run_core_prediction", side_effect=self.fake_inference):
            ADAPTER.predict(args)
        with self.assertRaisesRegex(ValueError, "invocation"):
            ADAPTER.predict(self.arguments(minimum=21))
        paths = ADAPTER.paths_for(args.output)
        altered = paths["task2"].read_bytes() + b"changed\n"
        paths["task2"].write_bytes(altered)
        with self.assertRaisesRegex(ValueError, "Changed completed"):
            ADAPTER.predict(args)
        self.assertEqual(paths["task2"].read_bytes(), altered)

    def test_gzip_source_is_selected_without_numeric_or_record_changes(self):
        source = self.folder / "source.json.gz"
        original = self.record(101, 2) + b"\n" + self.record(102, 20) + b"\n"
        with gzip.open(source, "wb") as handle:
            handle.write(original)
        args = self.arguments(source=source)
        with patch.object(ADAPTER, "run_core_prediction", side_effect=self.fake_inference):
            result = ADAPTER.predict(args)
        paths = ADAPTER.paths_for(args.output)
        with gzip.open(paths["eligible_input"], "rb") as handle:
            self.assertEqual(handle.read(), self.record(102, 20) + b"\n")
        self.assertEqual(result["counts"]["input_reads"], 22)
        self.assertEqual(result["counts"]["eligible_reads"], 20)

    def test_wrong_model_and_bad_core_receipt_never_complete(self):
        source = self.folder / "input.json"
        source.write_bytes(self.record(101, 20) + b"\n")
        wrong = self.folder / "wrong-model.pt"
        wrong.write_bytes(b"not-the-selected-artifact")
        args = self.arguments()
        args.model = wrong
        with self.assertRaisesRegex(ValueError, "selected cap128"):
            ADAPTER.predict(args)
        args = self.arguments()
        def corrupted(arguments, paths):
            self.fake_inference(arguments, paths)
            receipt = ADAPTER.read_json(paths["core_manifest"])
            receipt["n_sites"] += 1
            ADAPTER.save_json(paths["core_manifest"], receipt)
        with patch.object(ADAPTER, "run_core_prediction", side_effect=corrupted):
            with self.assertRaisesRegex(ValueError, "inference receipt differs"):
                ADAPTER.predict(args)
        self.assertFalse(ADAPTER.paths_for(args.output)["receipt"].exists())

    def test_child_interruption_preserves_qc_and_refuses_partial_reuse(self):
        source = self.folder / "input.json"
        source.write_bytes(self.record(101, 20) + b"\n")
        args = self.arguments()
        with patch.object(ADAPTER, "run_core_prediction", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                ADAPTER.predict(args)
        paths = ADAPTER.paths_for(args.output)
        self.assertTrue(paths["eligible_input"].exists())
        self.assertTrue(paths["qc"].exists())
        self.assertFalse(paths["lock"].exists())
        self.assertFalse(paths["receipt"].exists())
        with self.assertRaisesRegex(ValueError, "Incomplete prior work"):
            ADAPTER.predict(args)

    def test_changed_derived_input_or_compute_arguments_never_complete(self):
        source = self.folder / "input.json"
        source.write_bytes(self.record(101, 20) + b"\n")
        for fault in ("derived_input", "threads", "batch_size_limit", "max_padded_reads_budget"):
            with self.subTest(fault=fault):
                args = self.arguments(output=fault + ".csv")
                def corrupt(arguments, paths):
                    self.fake_inference(arguments, paths)
                    if fault == "derived_input":
                        with paths["eligible_input"].open("ab") as handle:
                            handle.write(b"changed after inference")
                    else:
                        receipt = ADAPTER.read_json(paths["core_manifest"])
                        receipt[fault] += 1
                        ADAPTER.save_json(paths["core_manifest"], receipt)
                with patch.object(ADAPTER, "run_core_prediction", side_effect=corrupt):
                    with self.assertRaisesRegex(ValueError, "inference receipt differs"):
                        ADAPTER.predict(args)
                self.assertFalse(ADAPTER.paths_for(args.output)["receipt"].exists())

    def test_own_child_is_terminated_if_wait_is_interrupted(self):
        args = self.arguments()
        paths = ADAPTER.paths_for(args.output)
        process = Mock()
        process.wait.side_effect = [KeyboardInterrupt, 0]
        process.poll.return_value = None
        with patch.object(ADAPTER.subprocess, "Popen", return_value=process):
            with self.assertRaises(KeyboardInterrupt):
                ADAPTER.run_core_prediction(args, paths)
        process.terminate.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
