"""Small file fixtures: no original score rescans, inference, or network use."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import integrate_biological_cases as integration


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")


class BiologicalCaseIntegrationTests(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parent / ".tmp"
        base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="case_integration_", dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "old/site"
        self.frontend = self.root / "frontend"
        self.package = self.root / "case_package"
        self.out = self.root / "new/site"
        self.plan = self.root / "BIOLOGICAL_CASE_SELECTION_PLAN.md"
        self.plan.write_text("Frozen fixture selection plan.\n", encoding="utf-8")
        self.source.mkdir(parents=True)
        self.frontend.mkdir()
        for name in ("app.html", "index.html"):
            (self.source / name).write_text("Original audited frontend", encoding="utf-8")
        fragment = '<style>body{margin:0}</style><p>Case – study</p><script src="case_logic.js"></script><script src="case_view.js"></script><script>fetch("data/biological_cases.json")</script>'
        split = fragment.index("</style>") + len("</style>")
        (self.frontend / "app.html").write_text(fragment, encoding="utf-8")
        (self.frontend / "index.html").write_text("<html><head>" + fragment[:split]
            + "</head><body>" + fragment[split:] + "</body></html>", encoding="utf-8")
        for name in ("case_logic.js", "case_view.js"):
            (self.frontend / name).write_text("// fixture module\n", encoding="utf-8")
        qc = {"receipt_sha256": "a" * 64, "n_keys": 4,
              "policy": {"primary": "all_source_consistent", "sensitivity": "scored_consistent"}}
        self.overview = {
            "build": {"mode": "scores", "score_status": "final", "keep_min_reads": 20,
                      "model_versions": ["elgin-cap128-weight3-18epoch-b2d38ff29a91"],
                      "n_runs_with_predictions": 2, "context_qc": qc},
            "totals": {"kept_sites": 4, "union_sites": {"20": 4}},
            "lines": [{"name": "A"}, {"name": "B"}],
            "runs": [{"id": "run_A", "line": "A", "group": "A:rep1", "n_scored": 4},
                     {"id": "run_B", "line": "B", "group": "B:rep1", "n_scored": 0}],
        }
        write_json(self.source / "data/overview.json", self.overview)
        write_json(self.source / "data/genes_index.json",
                   {"fields": ["key", "bucket"], "rows": [["GENE", 0]]})
        txs = []
        records = []
        for case_id, (tx, position) in integration.CASES.items():
            context = "AGGACAA"
            txs.append({"id": tx, "sites": [[position, "20,10", "0.75,",
                         {"all_source_consistent": True, "encoded7mer_all_source": context}]]})
            rows = []
            for run_id, line, reads, score, status in [
                    ("run_A", "A", 20, .75, "scored"),
                    ("run_B", "B", 10, None, "below_20_reads_unscored")]:
                rows.append({"case_id": case_id, "transcript_id": tx, "transcript_position": position,
                             "run_id": run_id, "cell_line": line, "n_reads": reads, "score": score,
                             "raw_transcript_id": tx if score is not None else None,
                             "measurement_status": status})
            records.append({"case": {"case_id": case_id, "transcript_id": tx,
                                     "transcript_position": position, "gene_id": "GENE",
                                     "analysis_sequence_7mer": context},
                            "original_runs": rows, "groups": [],
                            "line_scores": [{"case_id": case_id, "transcript_id": tx,
                                             "transcript_position": position, "cell_line": "A",
                                             "coverage_threshold": 20, "n_replicates": 1, "score": .75}]})
        write_json(self.source / "data/genes/b000.json", {"GENE": {"tx": txs}})
        self.contract = integration.SourceContract(runs=2, lines=2, groups=2, kept_sites=4,
            scored_observations=4, data_json_files=3, validation_passes=2)
        write_json(self.source.parent / "validation.json", {"require_complete": True,
            "counts": {"PASS": 2, "FAIL": 0, "WARN": 0}, "context_qc": qc,
            "runs": [{"run_id": "run_A", "n_scored": 4}, {"run_id": "run_B", "n_scored": 0}]})
        write_json(self.source.parent / "qa/overview_report_audit.json", {"numerical_status": "PASS",
            "n_fraction_mismatches": 0, "inputs": {"fixture/site/data/overview.json":
            integration.fingerprint(self.source / "data/overview.json")["sha256"]}})
        write_json(self.source.parent / "qa/browser_qa.json", {"status": "desktop QA completed",
            "source_app_sha256": integration.fingerprint(self.source / "app.html")["sha256"],
            "packaged_index_sha256": integration.fingerprint(self.source / "index.html")["sha256"]})
        utf8_files = []
        for path in sorted((self.source / "data").rglob("*.json")):
            pin = integration.fingerprint(path)
            utf8_files.append({"path": path.relative_to(self.source / "data").as_posix(),
                               "after_sha256": pin["sha256"], "size_bytes": pin["size_bytes"]})
        write_json(self.source.parent / "qa/utf8_check.json", {"status": "complete",
            "files_checked": 3, "files": utf8_files})
        self.package.mkdir()
        write_json(self.package / "selection_receipt.json", {"status": "complete",
            "no_training_or_inference": True,
            "inputs": [{"path": "sgnex_analysis/BIOLOGICAL_CASE_SELECTION_PLAN.md",
                        **integration.fingerprint(self.plan)}]})
        write_json(self.package / "independent_selection_audit.json", {"status": "PASS"})
        for name in ("persistent_difference_ranked.csv.gz", "shared_high_ranked.csv.gz", "inconclusive_ranked.csv.gz"):
            (self.package / name).write_bytes(b"fixture ranked alternatives preserved exactly")
        (self.package / "README.md").write_text(
            "[Selection plan](../BIOLOGICAL_CASE_SELECTION_PLAN.md)\n"
            "[Wider analysis](../task2_results_2026_10_23/README.md)\n", encoding="utf-8")
        self.payload = {"schema_version": 1, "model_sha256": integration.MODEL_SHA256,
            "selection_receipt_sha256": integration.fingerprint(self.package / "selection_receipt.json")["sha256"],
            "warnings": ["Illustrative tail-selected cases; not independent discoveries"], "cases": records}
        self.publish_payload()

    def publish_payload(self):
        write_json(self.package / "explorer_cases.json", self.payload)
        files = [{"file": path.name, **integration.fingerprint(path)}
                 for path in sorted(self.package.iterdir()) if path.name != "publication_manifest.json"]
        write_json(self.package / "publication_manifest.json", {"status": "complete", "files": files})

    def run_integration(self, **kwargs):
        return integration.integrate(self.source, self.frontend, self.package, self.out,
            self.plan, contract=self.contract, require_tracked_frontend=False, **kwargs)

    def test_preserves_score_bytes_and_source_and_publishes_exact_payload(self):
        before = integration.inventory(self.source)
        result = self.run_integration()
        self.assertEqual(before, integration.inventory(self.source))
        for name, pin in before.items():
            if name.startswith("data/"):
                self.assertEqual(pin, integration.fingerprint(self.out / name))
        self.assertEqual((self.package / "explorer_cases.json").read_bytes(),
                         (self.out / "data/biological_cases.json").read_bytes())
        self.assertEqual((self.plan).read_bytes(),
                         (self.out / "evidence/biological_cases/BIOLOGICAL_CASE_SELECTION_PLAN.md").read_bytes())
        self.assertEqual((self.package / "README.md").read_bytes(),
                         (self.out / "evidence/biological_cases/README.md").read_bytes())
        self.assertEqual(self.plan.read_bytes(),
                         (self.out / "evidence/BIOLOGICAL_CASE_SELECTION_PLAN.md").read_bytes())
        support = (self.out / "evidence/task2_results_2026_10_23/README.md").read_text(encoding="utf-8")
        self.assertIn("https://github.com/elgintan/LIFO_m6A_project/blob/" + integration.ANALYSIS_BASELINE
                      + "/sgnex_analysis/task2_results_2026_10_23/README.md", support)
        self.assertIn("navigation only", support)
        self.assertEqual(result["counts"]["case_original_run_records"], 8)
        self.assertEqual(result["counts"]["case_run_measurement_status_counts"],
                         {"scored": 4, "below_20_reads_unscored": 4})
        self.assertIsNone(result["resources"]["peak_rss_bytes"])
        self.assertTrue((self.out / "integration_complete.json").is_file())
        self.assertNotIn("integration_complete.json", result["outputs"])
        self.assertEqual(len(result["outputs"]), len(integration.inventory(self.out)) - 1)

    def test_tampered_published_payload_fails_before_copy(self):
        with (self.package / "explorer_cases.json").open("a", encoding="utf-8") as handle:
            handle.write(" ")
        with self.assertRaisesRegex(ValueError, "publication hash/size mismatch"):
            self.run_integration()
        self.assertFalse(self.out.exists())

    def test_resigned_score_disagreement_is_rejected_against_original_site(self):
        self.payload["cases"][0]["original_runs"][0]["score"] = .9
        self.publish_payload()
        with self.assertRaisesRegex(ValueError, "original-score disagreement"):
            self.run_integration()
        self.assertFalse(self.out.exists())

    def test_low_coverage_zero_is_not_missing(self):
        self.payload["cases"][0]["original_runs"][1]["score"] = 0
        self.publish_payload()
        with self.assertRaisesRegex(ValueError, "must remain unscored, not zero"):
            self.run_integration()

    def test_missing_original_run_is_rejected(self):
        self.payload["cases"][0]["original_runs"].pop()
        self.publish_payload()
        with self.assertRaisesRegex(ValueError, "missing an original run"):
            self.run_integration()

    def test_refuses_reused_output_without_modifying_it(self):
        self.out.mkdir(parents=True)
        sentinel = self.out / "retain.txt"
        sentinel.write_text("do not overwrite", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "nonempty"):
            self.run_integration()
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "do not overwrite")

    def test_source_data_tamper_fails_original_receipt(self):
        with (self.source / "data/genes/b000.json").open("a", encoding="utf-8") as handle:
            handle.write(" ")
        with self.assertRaisesRegex(ValueError, "Source data changed"):
            self.run_integration()

    def test_manifest_traversal_is_rejected_before_access(self):
        manifest = integration.load_json(self.package / "publication_manifest.json")
        manifest["files"].append({"file": "../outside.pem", "sha256": "0" * 64, "size_bytes": 0})
        write_json(self.package / "publication_manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "Unsafe manifest path"):
            self.run_integration()

    def test_stale_packaged_frontend_is_rejected(self):
        with (self.frontend / "app.html").open("a", encoding="utf-8") as handle:
            handle.write("<p>new section</p>")
        with self.assertRaisesRegex(ValueError, "index.html is stale"):
            self.run_integration()

    def test_failed_copy_never_writes_completion_receipt(self):
        real_copy = integration.shutil.copyfile

        def corrupt_payload(source, destination, *args, **kwargs):
            result = real_copy(source, destination, *args, **kwargs)
            if Path(destination) == self.out / "data/biological_cases.json":
                with Path(destination).open("ab") as handle:
                    handle.write(b" ")
            return result

        with patch.object(integration.shutil, "copyfile", side_effect=corrupt_payload):
            with self.assertRaisesRegex(ValueError, "Copied payload changed"):
                self.run_integration()
        self.assertTrue(self.out.is_dir())
        self.assertFalse((self.out / "integration_complete.json").exists())


if __name__ == "__main__":
    unittest.main()
