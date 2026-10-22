"""Run-boundary orchestration checks using explicit synthetic local fixtures.

No download, real prediction, model training or biological comparison is run.
Mock probabilities/audits exist only in temporary software-test folders.
"""
import contextlib
import csv
import gzip
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("elgin_pipeline_test", ROOT / "scripts/run_elgin_task2.py")
PIPELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PIPELINE)
FIXTURE_SPEC = importlib.util.spec_from_file_location("elgin_pipeline_mock_fixture", Path(__file__).with_name("test_elgin_prediction.py"))
FIXTURE = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(FIXTURE)


class ElginPipeline(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "outputs/checks/tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="elgin-pipeline-", dir=scratch)
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.ids = ["SGNex_Software_replicate{}_run1".format(i+1) for i in range(23)]
        self.chosen = self.ids[0]
        helper = FIXTURE.ElginPrediction("test_coverage_boundary_outliers_byte_identity_and_complete_reuse")
        original = helper.record(101, 19) + b"\n" + helper.record(102, 20) + b"\n"
        self.source = self.folder / "signals" / self.chosen / "data.json"
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(original)
        self.inventory = [dict(run_id=run, cell_line="Software", biological_replicate=str(i+1), sequencing_run="1",
                               signal_local_path=run+"/data.json", signal_size_bytes=str(len(original)),
                               signal_download_url="https://example.org/"+run+"/data.json", n_candidate_site_rows="2",
                               n_sites_ge1="2", n_sites_ge5="2", n_sites_ge10="2", n_sites_ge20="1", n_sites_ge50="0", n_sites_ge100="0")
                          for i, run in enumerate(self.ids)]
        self.active = [dict(run_id=run, cell_line="Software", biological_replicate=str(i+1), sequencing_run="1",
                            prediction_file="outputs/predictions/"+run+".csv", coverage_file="coverage.csv.gz",
                            min_reads="20", reference_version="software-fixture-unverified-reference",
                            model_version=PIPELINE.MODEL_VERSION) for i, run in enumerate(self.ids)]
        self.write_rows(self.folder / "inventory.csv", self.inventory)
        self.write_rows(self.folder / "manifest.csv", self.active)
        self.write_rows(self.folder / "aliases.csv", [dict(run_id=self.chosen, raw_transcript_id="ENST_SOFTWARE.7", transcript_id="ENST_SOFTWARE.1")])
        self.coverage(20)
        download = dict(run_id=self.chosen, status="downloaded_size_checked", url=self.inventory[0]["signal_download_url"],
                        size_bytes=len(original), sha256=PIPELINE.sha(self.source))
        (self.folder / "signals/download_receipts.jsonl").write_text(json.dumps(download)+"\n", encoding="utf-8")
        self.helper = helper

    def write_rows(self, path, records):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)

    def coverage(self, count):
        with gzip.open(self.folder / "coverage.csv.gz", "wt", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["transcript_id", "transcript_position"] + self.ids)
            writer.writerow(["ENST_SOFTWARE.1", "102"] + [count]*23)

    def arguments(self):
        return PIPELINE.parser().parse_args([
            "--run-id", self.chosen, "--inventory", str(self.folder / "inventory.csv"),
            "--manifest", str(self.folder / "manifest.csv"), "--coverage", str(self.folder / "coverage.csv.gz"),
            "--aliases", str(self.folder / "aliases.csv"), "--signals-dir", str(self.folder / "signals"),
            "--audit-dir", str(self.folder / "audits"), "--state-dir", str(self.folder / "state")])

    def produce_completed_fixture(self):
        args = self.arguments()
        chosen = PIPELINE.selection(args)
        identity = PIPELINE.identity_for(args, chosen)
        download = PIPELINE.verified_download(self.inventory[0], args.signals_dir)
        adapter_args = PIPELINE.ADAPTER.parser().parse_args([
            "--input", str(self.source), "--run-id", self.chosen,
            "--output", str(self.folder / self.active[0]["prediction_file"])])
        with patch.object(PIPELINE.ADAPTER, "run_core_prediction", side_effect=self.helper.fake_inference):
            PIPELINE.ADAPTER.predict(adapter_args)
        audit = dict(status="complete", run_id=self.chosen, source_sha256=download["source_sha256"],
                     source_size_bytes=self.source.stat().st_size, inventory_sha256=identity["source_sha256"]["inventory"],
                     coverage_sha256=identity["source_sha256"]["coverage"], aliases_sha256=identity["source_sha256"]["aliases"],
                     auditor_sha256=identity["source_sha256"]["auditor"], strict_parser_sha256=identity["source_sha256"]["core/data.py"],
                     n_source_sites=2, n_reads=39, coverage_key_and_count_match=True, labels_read=False,
                     fitting_or_inference=False, sites_at_least_reads={"1":2,"5":2,"10":2,"20":1,"50":0,"100":0},
                     synthetic_fixture_only=True)
        PIPELINE.json_write(args.audit_dir / (self.chosen+".json"), audit)
        return args, identity, download, audit

    def test_explicit_selection_and_exact_scope_are_required(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            PIPELINE.parser().parse_args([])
        args = self.arguments()
        self.assertEqual(len(PIPELINE.selection(args)), 1)
        self.active[0]["cell_line"] = "Wrong"
        self.write_rows(args.manifest, self.active)
        with self.assertRaisesRegex(ValueError, "identity differs"):
            PIPELINE.selection(args)

    def test_plan_only_makes_no_state_or_subprocess(self):
        args = self.arguments()
        args.plan_only = True
        with patch.object(PIPELINE, "command_run", side_effect=AssertionError("No subprocess allowed")), contextlib.redirect_stdout(io.StringIO()):
            PIPELINE.run(args)
        self.assertFalse(args.state_dir.exists())

    def test_existing_raw_bytes_need_prior_sha_not_only_size(self):
        args = self.arguments()
        self.assertIsNotNone(PIPELINE.verified_download(self.inventory[0], args.signals_dir))
        original = self.source.read_bytes()
        self.source.write_bytes(original.replace(b"1.0", b"2.0", 1))
        self.assertEqual(self.source.stat().st_size, len(original))
        with self.assertRaisesRegex(ValueError, "prior download SHA"):
            PIPELINE.verified_download(self.inventory[0], args.signals_dir)

    def test_cached_audit_requires_exact_alias_and_source_pins(self):
        args, identity, download, audit = self.produce_completed_fixture()
        path = args.audit_dir / (self.chosen+".json")
        self.assertEqual(PIPELINE.verified_audit(path, self.inventory[0], download, identity), audit)
        audit["aliases_sha256"] = "0"*64
        PIPELINE.json_write(path, audit)
        with self.assertRaisesRegex(ValueError, "Cached full-input audit differs"):
            PIPELINE.verified_audit(path, self.inventory[0], download, identity)

    def test_prediction_verification_uses_explicit_alias_and_coverage_counts(self):
        args, identity, download, audit = self.produce_completed_fixture()
        proof = PIPELINE.verify_prediction(self.inventory[0], self.active[0], args, identity, download, audit)
        self.assertTrue(proof["coverage_key_and_count_match"])
        self.assertEqual(proof["eligible_sites"], 1)
        self.coverage(21)
        with self.assertRaisesRegex(ValueError, "Member4 eligible coverage"):
            PIPELINE.verify_prediction(self.inventory[0], self.active[0], args, identity, download, audit)

    def test_complete_run_is_reverified_and_resumed_without_child_work(self):
        args, _identity, _download, _audit = self.produce_completed_fixture()
        with patch.object(PIPELINE, "command_run", side_effect=AssertionError("No subprocess allowed")), contextlib.redirect_stdout(io.StringIO()):
            PIPELINE.run(args)
            first = PIPELINE.json_read(args.state_dir / "checkpoint.json")
            PIPELINE.run(args)
        final = PIPELINE.json_read(args.state_dir / "checkpoint.json")
        self.assertEqual(final["status"], "complete")
        self.assertEqual(final["completed_run_ids"], [self.chosen])
        self.assertEqual(first["runs"][self.chosen]["verification"], final["runs"][self.chosen]["verification"])
        events = (args.state_dir / "events.jsonl").read_text()
        self.assertIn("completed_run_reverified", events)
        self.assertFalse((args.state_dir / "run.lock").exists())

    def test_changed_identity_and_existing_lock_are_refused_without_overwrite(self):
        state = self.folder / "state"
        identity = {"selected_run_ids": [self.chosen], "test": "one"}
        initial = PIPELINE.prepare_state(state, identity)
        lock = state / "run.lock"
        before = lock.read_bytes()
        with self.assertRaises(FileExistsError):
            PIPELINE.prepare_state(state, identity)
        self.assertEqual(lock.read_bytes(), before)
        lock.unlink()
        checkpoint = (state / "checkpoint.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "identity changed"):
            PIPELINE.prepare_state(state, dict(identity, test="two"))
        self.assertEqual((state / "checkpoint.json").read_bytes(), checkpoint)
        self.assertFalse(lock.exists())
        self.assertEqual(initial["status"], "prepared")

    def test_interrupted_download_preserves_partial_and_checkpoint(self):
        args = self.arguments()
        self.source.unlink()
        partial = self.source.with_name("data.json.partial")
        def interrupted(_command, _log):
            partial.write_bytes(b"synthetic incomplete transfer")
            raise KeyboardInterrupt
        with patch.object(PIPELINE, "command_run", side_effect=interrupted), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(KeyboardInterrupt):
                PIPELINE.run(args)
        self.assertEqual(partial.read_bytes(), b"synthetic incomplete transfer")
        self.assertFalse((args.state_dir / "run.lock").exists())
        self.assertIn("interrupted_or_failed", PIPELINE.json_read(args.state_dir / "checkpoint.json")["status"])
        with patch.object(PIPELINE, "command_run", side_effect=AssertionError("No retry may overwrite partial")), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "Interrupted download preserved"):
                PIPELINE.run(args)
        self.assertEqual(partial.read_bytes(), b"synthetic incomplete transfer")


if __name__ == "__main__":
    unittest.main(verbosity=2)
