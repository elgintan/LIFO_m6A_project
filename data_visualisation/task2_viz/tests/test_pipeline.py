"""Small synthetic regression checks; never downloads data or trains a model."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

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

    def context_delivery(self, manifests, rows=None):
        alias_path = self.base / "aliases.csv"
        pd.DataFrame(columns=["run_id", "raw_transcript_id", "transcript_id"]).to_csv(alias_path, index=False)
        directory = self.base / "context"
        directory.mkdir()
        if rows is None:
            rows = [{"transcript_id": "ENST1", "transcript_position": p,
                     "all_source_consistent": True, "scored_consistent": True,
                     "encoded7mer_all_source": "AAGACCA", "encoded7mer_scored": "AAGACCA",
                     "weak_positive_support_lt20": False, "training_support_known_for_all_contexts": True}
                    for p in (1, 2)]
        table = directory / "key_context_qc.csv.gz"
        pd.DataFrame(rows).to_csv(table, index=False)
        receipt = {"status": "complete", "inputs": {
            "manifest": {"sha256": lib.sha256(self.inputs / "manifest.csv")},
            "aliases": {"sha256": lib.sha256(alias_path)},
            "predictions": [{"run_id": r["run_id"], "sha256": lib.sha256(self.inputs / r["prediction_file"])}
                            for r in manifests]},
            "outputs": {table.name: {"sha256": lib.sha256(table), "size_bytes": table.stat().st_size}},
            "policy": {"primary": "all_source_consistent", "sensitivity": "scored_consistent"}}
        (directory / "complete.json").write_text(json.dumps(receipt))
        return alias_path, directory

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
        alias_path, context_dir = self.context_delivery(rows)
        report_path = self.base / "complete_report.json"
        status = validator.main(["--inputs", str(self.inputs), "--public", str(self.public),
                                 "--report", str(report_path), "--require-complete",
                                 "--aliases", str(alias_path), "--context-qc", str(context_dir)])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(report_path.read_text())["counts"]["FAIL"], 0)

    def model_info_fixture(self, text):
        pd.DataFrame({"run_id": [self.run]}).to_csv(self.public / "runs_discovered.csv", index=False)
        manifest = {"run_id": self.run, "cell_line": "A549", "biological_replicate": 5,
                    "sequencing_run": 1, "prediction_file": self.filename, "coverage_file": "synthetic-fixture",
                    "min_reads": 20, "reference_version": "synthetic-fixture", "model_version": "synthetic-fixture"}
        pd.DataFrame([manifest]).to_csv(self.inputs / "manifest.csv", index=False)
        self.predictions([["ENST1", 1, .1], ["ENST1", 2, .9]])
        (self.inputs / "MODEL_INFO.md").write_text(text)
        aliases, context = self.context_delivery([manifest])
        report = self.base / "model_info_report.json"
        args = ["--inputs", str(self.inputs), "--public", str(self.public), "--report", str(report),
                "--require-complete", "--aliases", str(aliases), "--context-qc", str(context)]
        with patch.object(fetcher, "read_pinned_inventory", return_value=[self.run]):
            status = validator.main(args)
        return status, json.loads(report.read_text())

    def test_narrative_pending_status_does_not_reject_completed_model(self):
        status, report = self.model_info_fixture(
            "# Selected model\n- Identifier: frozen-fixture.\n- SHA256: " + "a" * 64 +
            ".\nCross-run context QC and biological comparisons remain pending.\n"
            "Ubuntu verification: pending; Docker failed before Linux execution.\n")
        self.assertEqual(status, 0)
        self.assertFalse(any(i["check"] == "MODEL_INFO.md complete" and i["level"] == "FAIL"
                             for i in report["items"]))

    def test_actual_model_placeholder_markers_reject_final_delivery(self):
        for marker in ("PENDING_TEAM_SELECTION", "PENDING_MODEL", "- Model SHA256: **PENDING**.",
                       "- Artifact: TBD", "- Identifier: [PENDING]"):
            with self.subTest(marker=marker):
                self.assertTrue(validator.model_info_placeholders(marker))
        status, report = self.model_info_fixture("# Model\n- Identifier: PENDING_MODEL\n")
        self.assertEqual(status, 1)
        self.assertTrue(any(i["check"] == "MODEL_INFO.md complete" and i["level"] == "FAIL"
                            for i in report["items"]))

    def test_aliases_are_only_explicit_and_run_specific(self):
        runs = pd.DataFrame({"run_id": [self.run], "idx": [0]})
        rc = self.public / "readcount" / f"{self.run}.readcount.csv"
        pd.DataFrame({"transcript_id": ["ENST1.9", "ENST2.7"], "transcript_position": [1, 2],
                      "n_reads": [20, 50]}).to_csv(rc, index=False)
        original = rc.read_bytes()
        literal = lib.load_readcounts(self.public, runs)
        self.assertEqual(literal.transcript_id.astype(str).tolist(), ["ENST1.9", "ENST2.7"])
        changed = lib.load_readcounts(self.public, runs, {self.run: {"ENST1.9": "ENST1"}})
        self.assertEqual(changed.transcript_id.astype(str).tolist(), ["ENST1", "ENST2.7"])
        self.assertEqual(rc.read_bytes(), original)
        pd.DataFrame({"transcript_id": ["ENST1.9", "ENST1"], "transcript_position": [1, 1],
                      "n_reads": [20, 50]}).to_csv(rc, index=False)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            lib.load_readcounts(self.public, runs, {self.run: {"ENST1.9": "ENST1"}})

    def test_alias_table_duplicate_and_outside_scope_fail(self):
        path = self.base / "aliases.csv"
        row = {"run_id": self.run, "raw_transcript_id": "ENST1.9", "transcript_id": "ENST1"}
        pd.DataFrame([row, row]).to_csv(path, index=False)
        with self.assertRaisesRegex(ValueError, "repeats"):
            lib.load_aliases(path)
        pd.DataFrame([row]).to_csv(path, index=False)
        with self.assertRaisesRegex(ValueError, "outside"):
            lib.load_aliases(path, ["other_run"])

    def test_context_receipt_binds_current_predictions_and_flags(self):
        self.predictions([["ENST1", 1, .1], ["ENST1", 2, .9]])
        manifests = [{"run_id": self.run, "prediction_file": self.filename}]
        pd.DataFrame(manifests).to_csv(self.inputs / "manifest.csv", index=False)
        alias_path, directory = self.context_delivery(manifests)
        qc, info = lib.load_context_qc(directory, self.inputs / "manifest.csv", alias_path, self.inputs)
        self.assertEqual(info["n_primary_eligible"], 2)
        self.assertTrue(qc.all_source_consistent.all())
        self.predictions([["ENST1", 1, .2], ["ENST1", 2, .9]])
        with self.assertRaisesRegex(ValueError, "predictions changed"):
            lib.load_context_qc(directory, self.inputs / "manifest.csv", alias_path, self.inputs)

    def test_context_table_tamper_and_false_strings_cannot_pass(self):
        self.predictions([["ENST1", 1, .1], ["ENST1", 2, .9]])
        manifests = [{"run_id": self.run, "prediction_file": self.filename}]
        pd.DataFrame(manifests).to_csv(self.inputs / "manifest.csv", index=False)
        aliases, directory = self.context_delivery(manifests)
        table = directory / "key_context_qc.csv.gz"
        frame = pd.read_csv(table)
        frame.loc[0, "all_source_consistent"] = False
        frame.to_csv(table, index=False)
        with self.assertRaisesRegex(ValueError, "differs"):
            lib.load_context_qc(directory, self.inputs / "manifest.csv", aliases, self.inputs)
        self.assertEqual(lib.strict_bool(pd.Series(["False", "True"]), "fixture").tolist(), [False, True])
        with self.assertRaises(ValueError):
            lib.strict_bool(pd.Series(["yes"]), "fixture")

    def test_context_table_must_cover_exact_scoreable_union(self):
        qc = pd.DataFrame({"transcript_id": ["ENST1", "ENST1"], "transcript_position": [1, 2]})
        cats = pd.Index(["ENST1"])
        keys = pd.Index(builder.site_key(np.array([0, 0, 0]), np.array([1, 2, 3])))
        joined = builder.context_site_flags(qc, cats, keys, np.array([20, 50, 1]))
        self.assertEqual(joined.index.tolist(), [0, 1])
        with self.assertRaisesRegex(ValueError, "exactly every"):
            builder.context_site_flags(qc.iloc[:1], cats, keys, np.array([20, 50, 1]))
        with self.assertRaisesRegex(ValueError, "exactly every"):
            builder.context_site_flags(qc, cats, keys, np.array([20, 1, 1]))

    def test_primary_context_gate_and_thresholds_preserve_group_weights(self):
        runs = pd.DataFrame({"idx": [0, 1, 2], "gidx": [0, 0, 1], "cell_line": ["A549"] * 3})
        rows = [{"site": s, "run_idx": r, "score": score, "n": 100}
                for s, scores in enumerate(([0., 1., 1.], [.95, .95, .95]))
                for r, score in enumerate(scores)]
        pr = pd.DataFrame(rows)
        original = pr.copy(deep=True)
        result = builder.compare_lines(pr, runs, ["A549"], [True, False])
        self.assertEqual(result["20_ge2"]["common_sites"], 1)
        line = result["20_ge2"]["lines"]["A549"]
        self.assertEqual(line["median"], .75)
        self.assertEqual(line["fractions_by_cutoff"], {"0.5": 1., "0.7": 1., "0.9": 0.})
        pd.testing.assert_frame_equal(pr, original)
        self.assertEqual(builder.compare_lines(pr, runs, ["A549"], [True, True])["20_ge2"]["common_sites"], 2)

    def test_diagnostic_payload_preserves_conflict_score_and_precision(self):
        q = pd.Series({"all_source_consistent": False, "scored_consistent": True,
                       "encoded7mer_all_source": "AAGACCA|TAGACCA", "encoded7mer_scored": "AAGACCA",
                       "weak_positive_support_lt20": True, "training_support_known_for_all_contexts": True})
        score = .6999999999999998
        row = builder.site_payload(1, [20, 0], [score, np.nan], q)
        self.assertEqual(float(row[2].split(",")[0]), score)
        self.assertEqual(row[2].split(",")[1], "")
        self.assertFalse(row[3]["all_source_consistent"])
        self.assertTrue(row[3]["scored_consistent"])
        self.assertEqual(row[0], 1)

    def test_final_builder_keeps_conflicts_but_gates_primary_summary(self):
        run_ids = fetcher.read_pinned_inventory()
        pd.DataFrame({"run_id": run_ids}).to_csv(self.public / "runs_discovered.csv", index=False)
        pd.DataFrame({"checked_utc": ["2026-10-23T00:00:00Z"]}).to_csv(self.public / "download_manifest.csv", index=False)
        manifests, metadata = [], []
        for run in run_ids:
            parsed = lib.parse_run_id(run)
            manifests.append({"run_id": run, "cell_line": parsed["cell_line"], "biological_replicate": parsed["replicate"],
                              "sequencing_run": parsed["run"], "prediction_file": f"{run}.csv", "coverage_file": "synthetic-fixture",
                              "min_reads": 20, "reference_version": "synthetic-fixture", "model_version": "synthetic-fixture"})
            metadata.append({"run_id": run, "replicate_group": f"{parsed['cell_line']}:rep{parsed['replicate']}",
                             **{c: "synthetic" for c in ["protocol", "kit", "flowcell", "Platform", "basecaller_version(ENA)*",
                                                        "generation_date", "Spike in concentration"]}})
            pd.DataFrame([["ENST1", 1, .6999999999999998], ["ENST1", 2, .99]], columns=lib.PRED_COLUMNS).to_csv(self.inputs / f"{run}.csv", index=False)
            pd.DataFrame({"transcript_id": ["ENST1", "ENST1"], "transcript_position": [1, 2], "n_reads": [20, 50]}).to_csv(
                self.public / "readcount" / f"{run}.readcount.csv", index=False)
        pd.DataFrame(manifests).to_csv(self.inputs / "manifest.csv", index=False)
        (self.inputs / "MODEL_INFO.md").write_text("Synthetic regression fixture; not actual predictions.")
        sample = self.base / "samples.csv"
        pd.DataFrame(metadata).to_csv(sample, index=False)
        annotations = self.public / "annotation"
        annotations.mkdir()
        names = ["ensembl_transcript_id", "ensembl_gene_id", "hgnc_symbol", "gene_biotype", "description",
                 "chromosome_name", "start_position", "end_position", "strand", "tx_len", "nexon", "ensembl_transcript_id.version"]
        values = ["ENST1", "ENSG1", "TEST", "protein_coding", "Synthetic fixture", "1", "1", "100", "1", "100", "1", "ENST1.9"]
        (annotations / "Homo_sapiens.GRCh38.91.annotations-transcripts.txt").write_text(
            "\t".join(names) + "\n" + "\t".join(["ENST1"] + values) + "\n")
        qc_rows = [{"transcript_id": "ENST1", "transcript_position": p,
                    "all_source_consistent": p == 1, "scored_consistent": p == 1,
                    "encoded7mer_all_source": "AAGACCA" if p == 1 else "AAGACCA|TAGACCA",
                    "encoded7mer_scored": "AAGACCA" if p == 1 else "AAGACCA|TAGACCA",
                    "weak_positive_support_lt20": p == 2, "training_support_known_for_all_contexts": True} for p in (1, 2)]
        alias_path, context_dir = self.context_delivery(manifests, qc_rows)
        out, reports = self.base / "built", self.base / "reports"
        args = ["build_site_data.py", "--public", str(self.public), "--sample-metadata", str(sample),
                "--predictions", str(self.inputs), "--score-status", "final", "--member4-aliases", str(alias_path),
                "--context-qc", str(context_dir), "--out", str(out), "--reports", str(reports)]
        with patch.object(sys, "argv", args):
            self.assertEqual(builder.main(), 0)
        overview = json.loads((out / "overview.json").read_text(encoding="utf-8"))
        # Browser JSON must be UTF-8, including non-ASCII read-band labels.
        self.assertIn("20\u201349", overview["compare"]["agree_bins"])
        self.assertEqual(overview["totals"]["kept_sites"], 2)
        self.assertEqual(overview["compare"]["by_key"]["20_ge2"]["common_sites"], 1)
        self.assertEqual(overview["compare"]["before_context_diagnostic"]["20_ge2"]["common_sites"], 2)
        gene = json.loads((out / "genes" / f"b{builder.bucket_of('ENSG1'):03d}.json").read_text(encoding="utf-8"))["ENSG1"]
        sites = gene["tx"][0]["sites"]
        self.assertEqual(float(sites[0][2].split(",")[0]), .6999999999999998)
        self.assertFalse(sites[1][3]["all_source_consistent"])
        self.assertEqual(float(sites[1][2].split(",")[0]), .99)


if __name__ == "__main__":
    unittest.main()
