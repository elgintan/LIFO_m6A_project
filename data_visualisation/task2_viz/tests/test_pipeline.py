"""Small synthetic regression checks; never downloads data or trains a model."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import task2lib as lib
import validate_task2_inputs as validator
import build_site_data as builder
import verify_rebuild as verifier
import fetch_public_data as fetcher


class PipelineTests(unittest.TestCase):
    def setUp(self):
        local = ROOT / "tests" / ".tmp"
        local.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=local)
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.inputs = self.base / "inputs"
        self.public = self.base / "public"
        self.inputs.mkdir()
        (self.public / "readcount").mkdir(parents=True)
        self.run = "SGNex_A549_directRNA_replicate5_run1"
        self.filename = f"{self.run}.csv"
        self.row = pd.Series(dict(run_id=self.run, prediction_file=self.filename, min_reads="20"))
        pd.DataFrame({"transcript_id": ["ENST1", "ENST1"], "transcript_position": [1, 2],
                      "n_reads": [20, 50]}).to_csv(self.public / "readcount" / f"{self.run}.readcount.csv", index=False)

    def predictions(self, rows):
        pd.DataFrame(rows, columns=lib.PRED_COLUMNS).to_csv(self.inputs / self.filename, index=False)

    def checked(self):
        report = validator.Report()
        result = validator.check_file(self.row, self.inputs, self.public, report)
        return result, report

    def test_good_prediction_join(self):
        self.predictions([["ENST1", 2, .8], ["ENST1", 1, .1]])
        result, report = self.checked()
        self.assertEqual(result["n_scored"], 2)
        self.assertEqual(report.counts()["FAIL"], 0)

    def test_duplicate_numeric_positions_rejected(self):
        self.predictions([["ENST1", "1", .1], ["ENST1", "1.0", .2]])
        result, report = self.checked()
        self.assertIsNone(result)
        self.assertTrue(any(i["check"] == "numeric site keys are unique" for i in report.items))

    def test_bad_score_and_duplicate_reported_together(self):
        self.predictions([["ENST1", "1", 1.5], ["ENST1", "1", .2]])
        _, report = self.checked()
        self.assertGreaterEqual(report.counts()["FAIL"], 2)

    def test_infinite_and_fractional_positions_rejected(self):
        for position in ("inf", "nan", "1.5", "-1"):
            with self.subTest(position=position):
                self.predictions([["ENST1", position, .2]])
                result, report = self.checked()
                self.assertIsNone(result)
                self.assertGreater(report.counts()["FAIL"], 0)

    def test_wrong_run_site_is_failure_missing_site_is_warning(self):
        self.predictions([["ENST_OTHER", 1, .1]])
        _, report = self.checked()
        self.assertGreater(report.counts()["FAIL"], 0)
        self.predictions([["ENST1", 1, .1]])
        _, report = self.checked()
        self.assertEqual(report.counts()["FAIL"], 0)
        self.assertGreater(report.counts()["WARN"], 0)

    def test_declared_prediction_path_stays_inside_handoff(self):
        for relative in ("../outside.csv", "/outside.csv", "secret.pem"):
            with self.subTest(path=relative), self.assertRaises(ValueError):
                lib.prediction_path(self.inputs, relative)

    def test_pending_model_blocks_build_validator(self):
        pd.DataFrame({"run_id": [self.run]}).to_csv(self.public / "runs_discovered.csv", index=False)
        manifest = {"run_id": self.run, "cell_line": "A549", "biological_replicate": 5,
                    "sequencing_run": 1, "prediction_file": self.filename, "coverage_file": "public",
                    "min_reads": 20, "reference_version": "synthetic-test", "model_version": "PENDING_TEAM_SELECTION"}
        pd.DataFrame([manifest]).to_csv(self.inputs / "manifest.csv", index=False)
        self.predictions([["ENST1", 1, .1], ["ENST1", 2, .9]])
        report = self.base / "report.json"
        result = validator.main(["--inputs", str(self.inputs), "--public", str(self.public), "--report", str(report)])
        self.assertEqual(result, 1)
        self.assertGreater(json.loads(report.read_text())["counts"]["FAIL"], 0)

    def test_rebuild_comparator_rejects_missing_empty_and_changed_data(self):
        self.assertTrue(verifier.compare_dirs(self.base / "absent_a", self.base / "absent_b"))
        a, b = self.base / "a", self.base / "b"
        a.mkdir(); b.mkdir()
        self.assertTrue(verifier.compare_dirs(a, b))
        (a / "one.json").write_text("{}")
        (b / "one.json").write_text("{}")
        self.assertFalse(verifier.compare_dirs(a, b))
        (b / "one.json").write_text('{"changed":true}')
        self.assertTrue(verifier.compare_dirs(a, b))

    def test_rebuild_comparator_ignores_only_documented_times(self):
        a, b = self.base / "a", self.base / "b"
        a.mkdir(); b.mkdir()
        (a / "overview.json").write_text(json.dumps({"build": {"generated_utc": "a", "mode": "coverage_only"}}))
        (b / "overview.json").write_text(json.dumps({"build": {"generated_utc": "b", "mode": "coverage_only"}}))
        self.assertFalse(verifier.compare_dirs(a, b))
        (b / "overview.json").write_text(json.dumps({"build": {"generated_utc": "b", "mode": "scores"}}))
        self.assertTrue(verifier.compare_dirs(a, b))

    def test_packager_preserves_existing_export_directory(self):
        site, export = self.base / "site", self.base / "export"
        site.mkdir(); export.mkdir()
        marker = export / "retain.txt"
        marker.write_text("retain")
        result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/package_site.py"),
                                 "--site", str(site), "--artifact-dir", str(export)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(), "retain")

    def test_packager_writes_html_in_synthetic_site(self):
        site = self.base / "site"
        site.mkdir()
        (site / "app.html").write_text('<style>body{color:black}</style><p>synthetic check</p>')
        result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/package_site.py"),
                                 "--site", str(site)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("synthetic check", (site / "index.html").read_text())

    def test_replicates_are_equally_weighted(self):
        runs = pd.DataFrame({"idx": [0, 1, 2], "gidx": [0, 0, 1], "cell_line": ["A549"] * 3})
        predictions = pd.DataFrame({"site": [0, 0, 0], "run_idx": [0, 1, 2],
                                    "score": [0., 1., 1.], "n": [20, 20, 20]})
        groups = builder.group_mean(predictions, runs, 20)
        self.assertEqual(groups.score.tolist(), [.5, 1.])
        comparisons = builder.compare_lines(predictions, runs, ["A549"])
        self.assertEqual(comparisons["20_ge2"]["lines"]["A549"]["median"], .75)

    def test_constant_score_agreement_is_unavailable_not_nan(self):
        runs = pd.DataFrame({"idx": [0, 1], "gidx": [0, 1], "cell_line": ["A549", "A549"],
                             "replicate": [1, 2], "run": [1, 1]})
        for constant in (.1, .5):
            with self.subTest(constant=constant):
                rows = [{"site": s, "run_idx": r, "score": constant, "n": 20} for r in (0, 1) for s in range(30)]
                result = builder.agreement(pd.DataFrame(rows), runs, ["A549"], 20)
                self.assertTrue(all(r["r"] is None for r in result))
                json.dumps(result, allow_nan=False)

    def test_empty_alias_table_has_declared_schema(self):
        result = builder.alias_table({}, pd.DataFrame({"transcript_id": [], "tx_version": []}))
        self.assertIn("version_matches_ensembl91", result)

    def test_final_mode_rejects_partial_sites_and_missing_readcounts(self):
        self.predictions([["ENST1", 1, .1]])
        report = validator.Report()
        validator.check_file(self.row, self.inputs, self.public, report, require_complete=True)
        self.assertTrue(any(i["level"] == "FAIL" and "every site" in i["check"] for i in report.items))
        absent = self.base / "no_public"
        report = validator.Report()
        validator.check_file(self.row, self.inputs, absent, report, require_complete=True)
        self.assertTrue(any(i["level"] == "FAIL" and i["check"] == "public read counts available" for i in report.items))

    def test_final_mode_rejects_missing_run_scope_and_model_info(self):
        pd.DataFrame({"run_id": [self.run]}).to_csv(self.public / "runs_discovered.csv", index=False)
        manifest = {"run_id": self.run, "cell_line": "A549", "biological_replicate": 5,
                    "sequencing_run": 1, "prediction_file": self.filename, "coverage_file": "public",
                    "min_reads": 20, "reference_version": "synthetic-test", "model_version": "synthetic-test-model"}
        pd.DataFrame([manifest]).to_csv(self.inputs / "manifest.csv", index=False)
        self.predictions([["ENST1", 1, .1], ["ENST1", 2, .9]])
        report_path = self.base / "final_report.json"
        status = validator.main(["--inputs", str(self.inputs), "--public", str(self.public),
                                 "--report", str(report_path), "--require-complete"])
        self.assertEqual(status, 1)
        report = json.loads(report_path.read_text())
        checks = {i["check"] for i in report["items"] if i["level"] == "FAIL"}
        self.assertIn("public inventory matches the agreed 23-run scope", checks)
        self.assertIn("MODEL_INFO.md present", checks)

    def test_fetch_scope_is_pinned_and_missing_required_runs_fail(self):
        pinned = fetcher.read_pinned_inventory()
        self.assertEqual(len(pinned), 23)
        additional = "SGNex_A549_directRNA_replicate999_run1"
        self.assertEqual(fetcher.select_pinned_runs(pinned + [additional], pinned), sorted(pinned))
        with self.assertRaisesRegex(ValueError, "Required runs"):
            fetcher.select_pinned_runs(pinned[:-1], pinned)
        bad_inventory = self.base / "bad_inventory.csv"
        pd.DataFrame({"run_id": pinned[:-1] + [additional]}).to_csv(bad_inventory, index=False)
        with self.assertRaisesRegex(ValueError, "agreed 23-run"):
            fetcher.read_pinned_inventory(bad_inventory)

    def test_final_mode_accepts_complete_synthetic_23_run_handoff(self):
        runs = fetcher.read_pinned_inventory()
        pd.DataFrame({"run_id": runs}).to_csv(self.public / "runs_discovered.csv", index=False)
        rows = []
        for run in runs:
            parsed = lib.parse_run_id(run)
            rows.append({"run_id": run, "cell_line": parsed["cell_line"], "biological_replicate": parsed["replicate"],
                         "sequencing_run": parsed["run"], "prediction_file": f"{run}.csv", "coverage_file": "synthetic-fixture",
                         "min_reads": 20, "reference_version": "synthetic-fixture", "model_version": "synthetic-fixture"})
            pd.DataFrame([["ENST1", 1, .1], ["ENST1", 2, .9]], columns=lib.PRED_COLUMNS).to_csv(self.inputs / f"{run}.csv", index=False)
            pd.DataFrame({"transcript_id": ["ENST1", "ENST1"], "transcript_position": [1, 2], "n_reads": [20, 50]}).to_csv(
                self.public / "readcount" / f"{run}.readcount.csv", index=False)
        pd.DataFrame(rows).to_csv(self.inputs / "manifest.csv", index=False)
        (self.inputs / "MODEL_INFO.md").write_text("Synthetic regression fixture; not actual predictions.")
        report_path = self.base / "complete_report.json"
        status = validator.main(["--inputs", str(self.inputs), "--public", str(self.public),
                                 "--report", str(report_path), "--require-complete"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(report_path.read_text())["counts"]["FAIL"], 0)


if __name__ == "__main__":
    unittest.main()
