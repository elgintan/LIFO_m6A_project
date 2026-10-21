"""Synthetic receipt-contract tests: no real labels, training or inference."""
from copy import deepcopy
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np


def import_file(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REPORT = import_file("loss_report_tested", "report_loss_weight.py")
FIXTURE = import_file("loss_receipt_fixtures", "test_report_read_cap.py")
GENES = {fold: {"synthetic_gene_" + str(fold)} for fold in range(5)}


def recipes():
    _, baseline = FIXTURE.recipes()
    candidate = deepcopy(baseline)
    candidate["config"]["pos_weight"] = 1.
    for field, path in REPORT.PROVENANCE.items():
        digest = "a" * 64 if "entrypoint" in field else "b" * 64
        candidate["identity"][field] = digest
        candidate["identity"]["source_sha256"][path] = digest
    return baseline, candidate


def write_saved_cv(root, recipe, deltas=(0.,) * 5, failed=False):
    """Use existing receipt fixtures, adding consistent canonical-style groups."""
    FIXTURE.write_saved_cv(root, recipe, deltas=deltas, failed_invocation=failed)
    metrics = json.loads((root / "none/data0_cv_metrics.json").read_text())
    rows = metrics["per_fold"]
    for fold in range(5):
        folder = root / f"none/fold{fold}"
        audit = json.loads((folder / "split_audit.json").read_text())
        partitions = dict(initial_fit=set(range(5)) - {fold, (fold+1)%5},
                          inner_validation={(fold+1)%5}, refit=set(range(5)) - {fold}, assessment={fold})
        for population, folds in partitions.items():
            audit["populations"][population].update(
                sites=sum(rows[f]["n_sites"] for f in folds),
                positives=sum(rows[f]["n_positives"] for f in folds),
                genes=sorted(set().union(*(GENES[f] for f in folds))))
        REPORT.write_json(folder / "split_audit.json", audit)
        for stage, population in (("inner", "initial_fit"), ("refit", "refit")):
            path = folder / stage / "complete.json"
            complete = json.loads(path.read_text())
            complete["train_sites"] = audit["populations"][population]["sites"]
            complete["validation_sites"] = audit["populations"]["inner_validation"]["sites"] if stage == "inner" else 0
            signature = dict(config=recipe["config"], seed=complete["seed"],
                             max_epochs=recipe["max_epochs"] if stage == "inner" else complete["best_epoch"],
                             patience=recipe["patience"], batch_size=recipe["batch_size"], stage="cv_"+stage,
                             identity=recipe["identity"], threads=recipe["threads"], versions=REPORT.TRAINING_VERSIONS,
                             fitting=audit["populations"][population]["indices_sha256"],
                             validation=audit["populations"]["inner_validation"]["indices_sha256"] if stage == "inner" else None)
            complete["signature"] = REPORT.fingerprint(signature)
            REPORT.write_json(path, complete)
            if stage == "refit":
                result_path = folder / "fold_result.json"
                result = json.loads(result_path.read_text())
                result["refit_signature"] = complete["signature"]
                REPORT.write_json(result_path, result)
    REPORT.write_json(root.parent / "cv_arguments_synthetic.json", dict(
        phase="cv", sites=121838, genes=3852, identity=recipe["identity"], configuration=recipe["config"],
        arguments=["--phase", "cv", "--output-dir", str(root.parent)], no_data1=True, no_final_fit=True))


class RecipeChecks(unittest.TestCase):
    def test_exact_nested_provenance_and_only_loss_change(self):
        baseline, candidate = recipes()
        REPORT.validate_recipes(baseline, candidate)
        self.assertEqual(len(baseline["identity"]["source_sha256"]), 9)
        self.assertEqual(len(candidate["identity"]["source_sha256"]), 11)

    def test_extra_config_seed_cap_and_population_changes_refused(self):
        for area, key, value in (("config", "lr", .1), ("config", "cap", 32),
                                 ("config", "pos_weight", 2.), (None, "seed", 9),
                                 (None, "population_sha256", "0" * 64)):
            baseline, candidate = recipes()
            (candidate if area is None else candidate[area])[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                REPORT.validate_recipes(baseline, candidate)

    def test_parent_and_new_source_identity_must_be_preserved(self):
        for mutation in ("missing_parent", "changed_parent", "missing_new", "new_mismatch", "extra_source", "fold"):
            baseline, candidate = recipes()
            if mutation == "missing_parent":
                del candidate["identity"]["training_entrypoint_sha256"]
            elif mutation == "changed_parent":
                candidate["identity"]["source_sha256"]["train.py"] = "0" * 64
            elif mutation == "missing_new":
                del candidate["identity"]["loss_weight_plan_sha256"]
            elif mutation == "new_mismatch":
                candidate["identity"]["loss_weight_entrypoint_sha256"] = "0" * 64
            elif mutation == "extra_source":
                candidate["identity"]["source_sha256"]["extra.py"] = "0" * 64
            else:
                candidate["identity"]["folds_sha256"] = "0" * 64
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                REPORT.validate_recipes(baseline, candidate)

    def test_current_all_eleven_sources_checked_canonically(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            _, candidate = recipes()
            for name in candidate["identity"]["source_sha256"]:
                path = (repo / name if name == "model_evaluation/evaluate.py" else
                        repo / "model_elgin" / name if name in {*REPORT.PARENT_PROVENANCE.values(), *REPORT.PROVENANCE.values()}
                        else repo / "model_elgin/context_reference_v1" / name)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"synthetic source\r\n")
                candidate["identity"]["source_sha256"][name] = REPORT.hashlib.sha256(b"synthetic source\n").hexdigest()
            with mock.patch.object(REPORT, "REPO", repo):
                self.assertEqual(len(REPORT.current_source_evidence(candidate)), 11)
                path.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "Current canonical source"):
                    REPORT.current_source_evidence(candidate)


class EvidenceChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.roots = {"weight3": root / "control/cv", "weight1": root / "candidate/cv"}
        self.evidence = {name: {} for name in REPORT.NAMES}
        base, candidate = recipes()
        write_saved_cv(self.roots["weight3"], base)
        write_saved_cv(self.roots["weight1"], candidate, (-.02, .01, -.03, .005, -.01), failed=True)

    def load(self):
        return {name: REPORT.SAVED.load_mode(self.roots[name], "none", self.evidence[name]) for name in REPORT.NAMES}

    def run_report(self, output):
        with mock.patch.object(REPORT, "current_source_evidence", return_value={}), \
                mock.patch.object(REPORT, "shared_fold_genes", return_value=GENES):
            return REPORT.main(["--baseline-cv", str(self.roots["weight3"]), "--candidate-cv", str(self.roots["weight1"]), "--output-dir", str(output)])

    def test_negative_result_exact_signatures_and_resources_once(self):
        data = self.load()
        REPORT.validate_pairs(data, self.roots, self.evidence, GENES)
        REPORT.validate_training_signatures(data, self.roots, self.evidence)
        REPORT.attach_resource_provenance(data, self.roots, self.evidence)
        tables = REPORT.calculate_tables(data)
        delta = next(row for row in tables["paired_summary"] if row["metric"] == "selection_score")
        self.assertAlmostEqual(delta["candidate_minus_control_mean"], -.009)
        self.assertEqual((delta["positive_fold_deltas"], delta["negative_fold_deltas"]), (2, 3))
        self.assertAlmostEqual(delta["sample_sd_paired_delta_ddof1"], np.std([-.02, .01, -.03, .005, -.01], ddof=1))
        self.assertEqual(sum(row["wall_seconds"] for row in tables["resources"]), 210.)
        self.assertIn("**Weight3 has the higher", REPORT.report_text(data, tables, "synthetic"))

    def test_smoke_partial_tampered_prediction_and_weight_bytes_refused(self):
        path = self.roots["weight1"] / "none/progress.json"
        original = json.loads(path.read_text())
        for change in (dict(smoke=True), dict(full_five_folds=False, completed_folds=[0])):
            REPORT.write_json(path, {**original, **change})
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.load()
        REPORT.write_json(path, original)
        for name in ("predictions.csv", "inner/best.pt"):
            target = self.roots["weight1"] / "none/fold0" / name
            original_bytes = target.read_bytes()
            target.write_bytes(original_bytes + b"changed")
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.load()
            target.write_bytes(original_bytes)

    def test_matching_false_gene_flags_and_wrong_actual_lists_refused(self):
        for replacement, message in ((["synthetic_gene_2"], "Gene sets"), (["unrecognised_gene"], "actual canonical")):
            data = self.load()
            for root in self.roots.values():
                path = root / "none/fold0/split_audit.json"
                audit = json.loads(path.read_text())
                audit["populations"]["assessment"]["genes"] = replacement
                REPORT.write_json(path, audit)
            with self.subTest(replacement=replacement), self.assertRaisesRegex(ValueError, message):
                REPORT.validate_pairs(data, self.roots, self.evidence, GENES)

    def test_wrong_complete_signature_refused(self):
        data = self.load()
        path = self.roots["weight1"] / "none/fold0/inner/complete.json"
        receipt = json.loads(path.read_text()); receipt["signature"] = "0" * 64
        REPORT.write_json(path, receipt)
        with self.assertRaisesRegex(ValueError, "signature"):
            REPORT.validate_training_signatures(data, self.roots, self.evidence)

    def test_recovered_control_snapshot_retained_once_and_duplicate_refused(self):
        path = self.roots["weight3"] / "none/fold2/inner/invocation_recovered.json"
        receipt = dict(status="interrupted_or_failed", record_kind=REPORT.RECOVERED_RESOURCE_KIND,
                       checkpoint_sha256="d" * 64, checkpoint_epoch=3, resource_snapshot_index=0,
                       original_exit_receipt_absent=True, excludes_unfinished_work=True,
                       resources=dict(wall_seconds=88.1514156, cpu_seconds=329.921875,
                                      sampled_peak_process_tree_rss_mib=958.3, sampling_interval_seconds=.2, sampling_errors=0))
        REPORT.write_json(path, receipt)
        data = self.load(); REPORT.attach_resource_provenance(data, self.roots, self.evidence)
        tables = REPORT.calculate_tables(data)
        self.assertAlmostEqual(sum(row["wall_seconds"] for row in tables["resources"]), 298.1514156)
        self.assertEqual(REPORT.resource_accounting(tables["resources"])["recovered_snapshot_count"], 1)
        text = REPORT.report_text(data, tables, "synthetic")
        self.assertIn("contain lower bounds", text)
        self.assertIn("Unmeasured work after epoch 3 and before the pause is omitted", text)
        REPORT.write_json(path.with_name("invocation_duplicate.json"), receipt)
        data = self.load()
        with self.assertRaisesRegex(ValueError, "Duplicate recovered"):
            REPORT.attach_resource_provenance(data, self.roots, self.evidence)

    def test_changed_command_and_duplicate_resource_refused(self):
        data = self.load()
        path = self.roots["weight1"].parent / "cv_arguments_synthetic.json"
        record = json.loads(path.read_text()); record["no_data1"] = False
        REPORT.write_json(path, record)
        with self.assertRaisesRegex(ValueError, "Command receipt"):
            REPORT.command_receipts(self.roots, data)
        data["weight1"]["resources"].append(deepcopy(data["weight1"]["resources"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            REPORT.calculate_tables(data)

    def test_end_to_end_aggregate_manifest_commands_and_hashes(self):
        output = Path(self.temp.name) / "report"
        self.assertEqual(self.run_report(output), 0)
        manifest = json.loads((output / "comparison_manifest.json").read_text())
        signature = manifest.pop("signature")
        self.assertEqual(signature, REPORT.fingerprint(manifest))
        self.assertFalse(manifest["reads_labels"])
        self.assertFalse(manifest["loads_model_weights"])
        self.assertFalse(manifest["performs_fitting_or_inference"])
        self.assertTrue(manifest["reads_label_free_shared_folds"])
        self.assertEqual(len(manifest["executed_training_commands"]), 2)
        for name, digest in manifest["output_sha256"].items():
            self.assertEqual(REPORT.sha256(output / name), digest)
        self.assertIn("Weight3 has the higher", (output / "comparison.md").read_text())
        self.assertIn("does not validate a weight1 cutoff", (output / "comparison.md").read_text())

    def test_mid_report_mutation_fails_and_marks_old_outputs_stale(self):
        output = Path(self.temp.name) / "report"
        output.mkdir(); (output / "comparison.md").write_text("OLD NONAUTHORITATIVE REPORT")
        def mutate(*unused):
            path = self.roots["weight1"] / "none/fold0/inner/best.pt"
            path.write_bytes(path.read_bytes() + b"changed during report")
            return []
        with mock.patch.object(REPORT, "plot_tables", side_effect=mutate):
            self.assertEqual(self.run_report(output), 2)
        status = json.loads((output / "analysis_status.json").read_text())
        self.assertFalse(status["existing_outputs_are_authoritative"])


if __name__ == "__main__":
    unittest.main()
