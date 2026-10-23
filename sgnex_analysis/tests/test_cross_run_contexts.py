"""Small independent fixtures for context identity, joins and population gates."""
import csv
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

SPEC = importlib.util.spec_from_file_location("context_audit", Path(__file__).resolve().parents[1] / "scripts/audit_cross_run_contexts.py")
qc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qc)


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with qc.csv_open(path, "wt") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def fixture(root):
    predictions = root / "outputs/predictions"
    audits = root / "outputs/input_audits"
    predictions.mkdir(parents=True); audits.mkdir(parents=True)
    model = root / "model.pt"; model.write_bytes(b"synthetic model, never loaded")
    runs = [("A1", "A", "1"), ("A2", "A", "2"), ("B1", "B", "1"), ("B2", "B", "2"), ("B3", "B", "2")]
    manifest = [{"run_id": run, "cell_line": line, "biological_replicate": group, "sequencing_run": run,
                 "prediction_file": f"outputs/predictions/{run}.csv", "min_reads": "20", "model_version": "toy", "reference_version": "unverified"}
                for run, line, group in runs]
    write_csv(root / "manifest.csv", manifest, list(manifest[0]))
    aliases = [{"run_id": "B1", "raw_transcript_id": "tx_shared.1", "transcript_id": "tx_shared"}]
    write_csv(root / "aliases.csv", aliases, list(aliases[0]))
    names = ["tx_shared", "tx_lowconf", "tx_scoreconf", "txU", "txAmb", "tx_single"]
    coverage = []
    annotation = []
    for name in names:
        counts = {run: (5 if name == "tx_lowconf" and run == "B2" else 20) for run, _, _ in runs}
        if name == "tx_single":
            counts = {run: 20 if run == "A1" else 0 for run, _, _ in runs}
        if name == "tx_lowconf":
            counts["B2"] = 0  # inherited matrix omits below20 counts
        coverage.append({"transcript_id": name, "transcript_position": 1, **counts})
        annotation.append({"transcript_id": name, "transcript_position": 1, "kind": "annotated"})
    write_csv(root / "coverage.csv.gz", coverage, [*qc.KEYS, *(run for run, _, _ in runs)])
    write_csv(root / "annotations.csv.gz", annotation, [*qc.KEYS, "kind"])
    training = [{"sequence_7mer": value, "positive_labels": pos} for value, pos in [("AAAACAA", 2), ("AAAACAC", 25), ("TAAACAA", 50)]]
    write_csv(root / "training.csv", training, ["sequence_7mer", "positive_labels"])
    for run, _, _ in runs:
        metas, preds = [], []
        for name in names:
            count = 5 if (name == "tx_lowconf" and run == "B2") or (name == "tx_single" and run != "A1") else 20
            context = "AAAACAA"
            if name in {"tx_lowconf", "tx_scoreconf"} and run == "B2": context = "AAAACAC"
            if name == "txU": context = "uaaacaa" if run == "A1" else "TAAACAA"
            if name == "txAmb": context = "AANACAA"
            transcript = "tx_shared.1" if name == "tx_shared" and run == "B1" else name
            metas.append(dict(zip(qc.METADATA_COLUMNS, [transcript, 1, context, context[1:6], count, count,
                                                       "eligible" if count >= 20 else "below_minimum_source_reads"])))
            if count >= 20:
                preds.append({"transcript_id": transcript, "transcript_position": 1, "score": "0.25"})
        metas.append(dict(zip(qc.METADATA_COLUMNS, ["outside", 100, "AAAACAA", "AAACA", 1, 1, "below_minimum_source_reads"])))
        pred = predictions / f"{run}.csv"; meta = predictions / f"{run}.site_metadata.csv.gz"
        write_csv(pred, preds, qc.KEYS + ["score"]); write_csv(meta, metas, qc.METADATA_COLUMNS)
        receipt = {"status": "complete", "identity": {"run_id": run, "model_sha256": qc.sha(model), "min_reads": 20, "input_sha256": f"toy-source-{run}"},
                   "files_sha256": {pred.name: qc.sha(pred), meta.name: qc.sha(meta)},
                   "counts": {"input_sites": len(metas), "input_reads": sum(int(row["n_reads_input"]) for row in metas), "scored_sites": len(preds),
                              "eligible_reads": sum(int(row["n_reads_input"]) for row in metas if int(row["n_reads_input"]) >= 20)}}
        qc.json_write(predictions / f"{run}.receipt.json", receipt)
        qc.json_write(audits / f"{run}.json", {"status": "complete", "run_id": run, "source_sha256": f"toy-source-{run}",
                                              "coverage_sha256": qc.sha(root / "coverage.csv.gz"), "aliases_sha256": qc.sha(root / "aliases.csv"),
                                              "coverage_key_and_count_match": True})
    return model


def invoke(root, output):
    return qc.run_audit(root / "manifest.csv", root / "coverage.csv.gz", root / "annotations.csv.gz", root / "aliases.csv", root / "training.csv", output,
                        expected_runs=5, model_sha=qc.sha(root / "model.pt"), model_path=root / "model.pt")


class ContextTests(unittest.TestCase):
    def test_model_encoding_and_iupac(self):
        self.assertEqual(qc.context_identity("uaaacaa"), ("TAAACAA", "TAAACAA", False, True))
        self.assertEqual(qc.context_identity("AARACAA")[1], qc.context_identity("AANACAA")[1])
        for value in ["AAAA", "AAA-XAA", "ÅAAACAA", "AAAACAA "]:
            with self.assertRaises(ValueError): qc.context_identity(value)

    def test_population_groups_not_run_count(self):
        manifest = pd.DataFrame({"run_id": ["A1", "A2", "B1", "B2"], "cell_line": ["A", "A", "B", "B"], "biological_replicate": [1, 1, 1, 2]})
        result = qc.population_effects(np.full((1, 4), 20), manifest, np.array([True]), np.array([True]), np.array([True]))
        pair = next(row for row in result if row["population_type"] == "pairwise" and row["coverage_threshold"] == 20)
        self.assertEqual(pair["n_annotated_coverage_qualified"], 0)

    def test_complete_fixture_counts_conflicts_aliases_and_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); fixture(root)
            summary = invoke(root, root / "audit")
            self.assertEqual(summary["source_totals"]["source_sites"], 35)
            self.assertEqual(summary["source_totals"]["outside_coverage_union_sites"], 5)
            self.assertEqual(summary["counts"]["coverage_union_keys"], 6)
            table = pd.read_csv(root / "audit/key_context_qc.csv.gz", keep_default_na=False).set_index("transcript_id")
            self.assertTrue(table.loc["tx_shared", "all_source_consistent"])
            self.assertFalse(table.loc["tx_lowconf", "all_source_consistent"])
            self.assertTrue(table.loc["tx_lowconf", "scored_consistent"])
            self.assertFalse(table.loc["tx_scoreconf", "scored_consistent"])
            self.assertTrue(table.loc["txU", "all_source_consistent"])
            self.assertEqual(table.loc["txU", "n_literal_contexts_all_source"], 2)
            self.assertFalse(table.loc["txAmb", "all_source_consistent"])
            self.assertTrue(table.loc["tx_lowconf", "weak_positive_support_lt20"])
            observations = pd.read_csv(root / "audit/conflicting_context_observations.csv.gz", keep_default_na=False)
            self.assertEqual(len(observations), 15)
            low = observations[(observations.transcript_id == "tx_lowconf") & (observations.run_id == "B2")].iloc[0]
            self.assertEqual(low.score, "")
            population = pd.read_csv(root / "audit/population_effects.csv")
            pair = population[(population.population_type == "pairwise") & (population.coverage_threshold == 20)].iloc[0]
            self.assertEqual(pair.n_annotated_coverage_qualified, 5)
            self.assertEqual(pair.n_primary_all_source_consistent, 2)
            self.assertEqual(pair.n_scored_only_consistent, 3)
            receipt = json.loads((root / "audit/complete.json").read_text())
            self.assertEqual(receipt["outputs"]["key_context_qc.csv.gz"]["sha256"], qc.sha(root / "audit/key_context_qc.csv.gz"))
            self.assertEqual(len(receipt["inputs"]["predictions"]), 5)
            before = qc.sha(root / "audit/complete.json")
            with self.assertRaises(FileExistsError): invoke(root, root / "audit")
            self.assertEqual(before, qc.sha(root / "audit/complete.json"))

    def test_metadata_tamper_refused_before_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); fixture(root)
            with (root / "outputs/predictions/A1.site_metadata.csv.gz").open("ab") as handle: handle.write(b"tampered")
            with self.assertRaisesRegex(ValueError, "Receipt hash mismatch"): invoke(root, root / "audit")
            self.assertFalse((root / "audit/complete.json").exists())

    def test_eligible_prediction_missing_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); fixture(root)
            pred = root / "outputs/predictions/A1.csv"
            with pred.open() as handle:
                rows = list(csv.DictReader(handle))[:-1]
            write_csv(pred, rows, qc.KEYS + ["score"])
            receipt_path = root / "outputs/predictions/A1.receipt.json"
            receipt = json.loads(receipt_path.read_text()); receipt["files_sha256"][pred.name] = qc.sha(pred); qc.json_write(receipt_path, receipt)
            with self.assertRaisesRegex(ValueError, "complete eligible coverage"): invoke(root, root / "audit")
            self.assertFalse((root / "audit/complete.json").exists())

    def test_alias_scoped_and_no_generic_strip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); fixture(root)
            aliases = qc.load_aliases(root / "aliases.csv", ["A1", "A2", "B1", "B2", "B3"])
            self.assertEqual(aliases["B1"]["tx_shared.1"], "tx_shared")
            self.assertNotIn("tx_shared.1", aliases["A1"])
            self.assertNotIn("tx_shared.2", aliases["B1"])

    def test_ambiguous_and_noncentral_no_eligible_flag(self):
        result = qc.context_summary(np.array([1, 2]), np.array([20, 5]), ["", "AAAACAA", "AAATCAA"])
        self.assertFalse(result["all_source_consistent"])
        self.assertTrue(result["scored_consistent"])
        self.assertTrue(result["noncentral_a_all_source"])

    def test_exact_integer_validation(self):
        for value in ["1.0", "1e2", "-1", "NaN", "", " 1"]:
            with self.assertRaises(ValueError): qc.integer(value)

    def test_alias_collision_preserved_and_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); fixture(root)
            with qc.csv_open(root / "aliases.csv") as handle: alias_rows = list(csv.DictReader(handle))
            alias_rows.append({"run_id": "A1", "raw_transcript_id": "tx_shared.extra", "transcript_id": "tx_shared"})
            write_csv(root / "aliases.csv", alias_rows, list(alias_rows[0]))
            audit_path = root / "outputs/input_audits/A1.json"
            audit = json.loads(audit_path.read_text()); audit["aliases_sha256"] = qc.sha(root / "aliases.csv"); qc.json_write(audit_path, audit)
            meta_path = root / "outputs/predictions/A1.site_metadata.csv.gz"
            with qc.csv_open(meta_path) as handle: rows = list(csv.DictReader(handle))
            duplicate = dict(rows[0]); duplicate.update({"transcript_id": "tx_shared.extra", "n_reads_input": 1, "n_reads_finite": 1, "prediction_status": "below_minimum_source_reads"})
            rows.append(duplicate); write_csv(meta_path, rows, qc.METADATA_COLUMNS)
            receipt_path = root / "outputs/predictions/A1.receipt.json"
            receipt = json.loads(receipt_path.read_text()); receipt["files_sha256"][meta_path.name] = qc.sha(meta_path); qc.json_write(receipt_path, receipt)
            with self.assertRaisesRegex(ValueError, "canonical key collision"): invoke(root, root / "audit")
            evidence = pd.read_csv(root / "audit/within_run_key_collisions.csv.gz")
            self.assertEqual(evidence.incoming_raw_transcript_id.iloc[0], "tx_shared.extra")
            self.assertFalse((root / "audit/complete.json").exists())

    def test_unseen_training_context_not_silently_zero_counted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); fixture(root)
            for run in ["A1", "A2", "B1", "B2", "B3"]:
                meta_path = root / f"outputs/predictions/{run}.site_metadata.csv.gz"
                with qc.csv_open(meta_path) as handle: rows = list(csv.DictReader(handle))
                for row in rows:
                    if row["transcript_id"] == "tx_single": row.update({"sequence_7mer": "CAAACAA", "motif_5mer": "AAACA"})
                write_csv(meta_path, rows, qc.METADATA_COLUMNS)
                receipt_path = root / f"outputs/predictions/{run}.receipt.json"
                receipt = json.loads(receipt_path.read_text()); receipt["files_sha256"][meta_path.name] = qc.sha(meta_path); qc.json_write(receipt_path, receipt)
            summary = invoke(root, root / "audit")
            self.assertEqual(summary["counts"]["primary_unseen_training_context_keys"], 1)
            table = pd.read_csv(root / "audit/key_context_qc.csv.gz").set_index("transcript_id")
            self.assertTrue(table.loc["tx_single", "all_source_consistent"])
            self.assertFalse(table.loc["tx_single", "training_support_known_for_all_contexts"])


if __name__ == "__main__": unittest.main()
