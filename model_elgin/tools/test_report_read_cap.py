"""Synthetic saved-evidence contract tests; no real training, labels or inference."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

SPEC = importlib.util.spec_from_file_location("cap_report", Path(__file__).with_name("report_read_cap.py"))
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)


def recipes():
    sources = {k: str(i) * 64 for i, k in enumerate(("train.py", "model.py", "context_features.py", "data.py", "common.py", "prepare.py", "model_evaluation/evaluate.py"), 1)}
    base = dict(config=dict(width=48, dropout=.25, lr=.001, weight_decay=.0001,
                           pos_weight=3., cap=32, summary_n=63, pool="attention", context_mode="none", min_sites=30),
                max_epochs=20, patience=5, seed=2026, batch_size=256, threads=4,
                population_sha256="a" * 64, smoke=False,
                identity=dict(cache_manifest_sha256="b" * 64, data0_input_sha256=REPORT.SAVED.DATA0_SHA,
                              labels_sha256="c" * 64, folds_sha256=REPORT.SAVED.FOLD_SHA, source_sha256=sources))
    candidate = deepcopy(base)
    candidate["config"]["cap"] = 128
    for key, source_key in REPORT.PROVENANCE.items():
        candidate["identity"][key] = "d" * 64 if key.startswith("training") else "e" * 64
        candidate["identity"]["source_sha256"][source_key] = candidate["identity"][key]
    return base, candidate


def metric_row(fold, delta=0.):
    n = 24368 if fold < 3 else 24367
    positive = 1095
    tp, fp = 600 + fold, 800 - fold
    tn, fn = n - positive - fp, positive - tp
    roc, pr = .8 + fold * .01 + delta, .4 + fold * .01 + delta
    return dict(fold_id=fold, n_sites=n, n_positives=positive, positive_fraction=positive / n,
                roc_auc=roc, pr_auc_trapezoid=pr, average_precision=pr + .01,
                selection_score=(roc + pr) / 2, threshold=.5, tn=tn, fp=fp, fn=fn, tp=tp,
                precision=tp / (tp + fp), recall=tp / positive, f1=2 * tp / (2 * tp + fp + fn),
                specificity=tn / (tn + fp), accuracy=(tn + tp) / n)


def pooled_row(rows):
    n = sum(row["n_sites"] for row in rows)
    positives = sum(row["n_positives"] for row in rows)
    counts = {key: sum(row[key] for row in rows) for key in REPORT.COUNTS}
    tn, fp, fn, tp = (counts[key] for key in REPORT.COUNTS)
    return dict(n_sites=n, n_positives=positives, positive_fraction=positives / n,
                **{key: float(np.mean([row[key] for row in rows])) for key in REPORT.RANKING},
                threshold=.5, **counts, precision=tp / (tp + fp), recall=tp / positives,
                f1=2 * tp / (2 * tp + fp + fn), specificity=tn / (tn + fp), accuracy=(tn + tp) / n)


def write_saved_cv(root, recipe, deltas=(0., 0., 0., 0., 0.), failed_invocation=False):
    """Tiny receipt graph with real population totals but synthetic score evidence."""
    root = Path(root)
    directory = root / "none"
    directory.mkdir(parents=True)
    REPORT.write_json(directory / "recipe.json", recipe)
    oof = directory / "data0_oof.csv"
    oof.write_text("SYNTHETIC RECEIPT FIXTURE; NOT A PREDICTION DATASET\n", encoding="utf-8")
    rows = [metric_row(fold, deltas[fold]) for fold in range(5)]
    metrics = dict(dataset="data0", evaluation_kind="data0_gene_grouped_oof_development",
                   data0_labels_canonical_sha256=REPORT.SAVED.LABELS_CANONICAL_SHA,
                   inputs=dict(predictions=dict(sha256=REPORT.sha256(oof)), labels=dict(sha256=recipe["identity"]["labels_sha256"]),
                               folds=dict(sha256=REPORT.SAVED.FOLD_SHA)),
                   scorer_sha256=recipe["identity"]["source_sha256"]["model_evaluation/evaluate.py"],
                   per_fold=rows, pooled=pooled_row(rows),
                   mean_fold={key: float(np.mean([row[key] for row in rows])) for key in REPORT.RANKING},
                   sample_sd_fold_ddof1={key: float(np.std([row[key] for row in rows], ddof=1)) for key in REPORT.RANKING},
                   versions=dict(python=REPORT.TRAINING_VERSIONS["python"], numpy=REPORT.TRAINING_VERSIONS["numpy"],
                                 scikit_learn=REPORT.TRAINING_VERSIONS["sklearn"]))
    metrics["primary_score"] = metrics["mean_fold"]["selection_score"]
    REPORT.write_json(directory / "data0_cv_metrics.json", metrics)
    REPORT.write_json(directory / "progress.json", dict(smoke=False, full_five_folds=True, full_data0_population=True,
                       completed_folds=list(range(5)), oof_sha256=REPORT.sha256(oof),
                       cv_metrics_sha256=REPORT.sha256(directory / "data0_cv_metrics.json")))
    for fold, row in enumerate(rows):
        folder = directory / f"fold{fold}"
        folder.mkdir()
        populations = dict(initial_fit=dict(sites=70000, indices_sha256="f" * 64, genes=["synthetic_train"]),
                           refit=dict(sites=97470, indices_sha256="a" * 64, genes=["synthetic_train", "synthetic_validation"]),
                           inner_validation=dict(sites=24470, indices_sha256="b" * 64, genes=["synthetic_validation"]),
                           assessment=dict(sites=row["n_sites"], positives=row["n_positives"], indices_sha256="c" * 64, genes=["synthetic_assessment"]))
        REPORT.write_json(folder / "split_audit.json", dict(assessment_fold=fold, inner_validation_fold=(fold + 1) % 5,
                           zero_gene_overlap=True, populations=populations))
        selected = 2 + fold
        for stage, population in (("inner", "initial_fit"), ("refit", "refit")):
            fit = folder / stage
            fit.mkdir()
            (fit / "best.pt").write_bytes(b"SYNTHETIC HASH RECEIPT ONLY; NEVER LOAD AS WEIGHTS")
            signature_values = dict(config=recipe["config"], seed=recipe["seed"] + fold + (100 if stage == "refit" else 0),
                         max_epochs=recipe["max_epochs"] if stage == "inner" else selected, patience=recipe["patience"],
                         batch_size=recipe["batch_size"], stage="cv_" + stage, identity=recipe["identity"], threads=recipe["threads"],
                         versions=REPORT.TRAINING_VERSIONS, fitting=populations[population]["indices_sha256"],
                         validation=populations["inner_validation"]["indices_sha256"] if stage == "inner" else None)
            complete = dict(signature=REPORT.fingerprint(signature_values), config=recipe["config"], seed=signature_values["seed"],
                         train_sites=populations[population]["sites"], fit_indices_sha256=populations[population]["indices_sha256"],
                         validation_sites=0 if stage == "refit" else populations["inner_validation"]["sites"],
                         best_epoch=selected, epochs_completed=selected, best_sha256=REPORT.sha256(fit / "best.pt"),
                         resources=[dict(wall_seconds=999999, cpu_seconds=999999)])
            REPORT.write_json(fit / "complete.json", complete)
            resource = dict(wall_seconds=10., cpu_seconds=20., sampled_peak_process_tree_rss_mib=50.,
                            sampling_errors=0, sampling_interval_seconds=.2)
            REPORT.write_json(fit / "invocation_1.json", dict(status="complete", resources=resource))
            if failed_invocation and fold == 0 and stage == "inner":
                REPORT.write_json(fit / "invocation_0.json", dict(status="interrupted_or_failed", resources=resource))
            if stage == "refit":
                refit_signature = complete["signature"]
        (folder / "predictions.csv").write_text(f"synthetic fold receipt {fold}\n", encoding="utf-8")
        REPORT.write_json(folder / "fold_result.json", dict(fold_id=fold, metrics=row, selected_epochs=selected,
                         refit_signature=refit_signature, predictions_sha256=REPORT.sha256(folder / "predictions.csv")))


class RecipeChecks(unittest.TestCase):
    def test_powershell_paths_remain_literal(self):
        self.assertEqual(REPORT.powershell_argument("C:/a'b/$x`n.txt"), "'C:/a''b/$x`n.txt'")

    def test_only_planned_cap_and_provenance_are_accepted(self):
        REPORT.validate_recipes(*recipes())

    def test_other_hyperparameter_and_seed_changes_refused(self):
        for area, key, value in (("config", "lr", .01), ("config", "summary_n", 72), (None, "seed", 99)):
            baseline, candidate = recipes()
            (candidate if area is None else candidate[area])[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                REPORT.validate_recipes(baseline, candidate)

    def test_core_source_or_fold_change_refused(self):
        for key in ("folds_sha256", "source_sha256"):
            baseline, candidate = recipes()
            if key == "source_sha256":
                candidate["identity"][key]["train.py"] = "0" * 64
            else:
                candidate["identity"][key] = "0" * 64
            with self.subTest(key=key), self.assertRaises(ValueError):
                REPORT.validate_recipes(baseline, candidate)

    def test_missing_unexpected_or_inconsistent_provenance_refused(self):
        for mutation in ("missing", "unexpected", "inconsistent"):
            baseline, candidate = recipes()
            if mutation == "missing":
                del candidate["identity"]["experiment_plan_sha256"]
            elif mutation == "unexpected":
                candidate["identity"]["source_sha256"]["other.py"] = "f" * 64
            else:
                candidate["identity"]["experiment_plan_sha256"] = "0" * 64
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                REPORT.validate_recipes(baseline, candidate)


class SavedEvidenceChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base_root = Path(self.temp.name) / "baseline"
        self.new_root = Path(self.temp.name) / "candidate"
        self.roots = dict(cap32=self.base_root, cap128=self.new_root)
        self.evidence = {name: {} for name in REPORT.NAMES}
        baseline, candidate = recipes()
        write_saved_cv(self.base_root, baseline)
        # Retain a negative average outcome and mixed individual fold changes.
        write_saved_cv(self.new_root, candidate, deltas=(-.02, .01, -.03, .005, -.01), failed_invocation=True)

    def load(self):
        return {name: REPORT.SAVED.load_mode(self.roots[name], "none", self.evidence[name]) for name in REPORT.NAMES}

    def test_complete_evidence_negative_result_and_resource_once(self):
        data = self.load()
        REPORT.validate_pairs(data, self.roots, self.evidence)
        REPORT.validate_training_signatures(data, self.roots, self.evidence)
        tables = REPORT.calculate_tables(data)
        summary = next(row for row in tables["paired_summary"] if row["metric"] == "selection_score")
        self.assertAlmostEqual(summary["candidate_minus_control_mean"], -.009)
        self.assertAlmostEqual(summary["sample_sd_paired_delta_ddof1"], np.std([-.02, .01, -.03, .005, -.01], ddof=1))
        self.assertEqual((summary["positive_fold_deltas"], summary["negative_fold_deltas"]), (2, 3))
        self.assertEqual(len(tables["resources"]), 21)
        self.assertEqual(sum(row["wall_seconds"] for row in tables["resources"]), 210.)
        self.assertIn("**Cap32 has the higher", REPORT.report_text(data, tables, "synthetic command"))

    def test_tampered_prediction_or_model_refused(self):
        for rel in ("none/fold0/predictions.csv", "none/fold0/inner/best.pt"):
            with self.subTest(rel=rel):
                path = self.new_root / rel
                saved = path.read_bytes()
                path.write_bytes(saved + b"changed")
                with self.assertRaises(ValueError):
                    self.load()
                path.write_bytes(saved)

    def test_incomplete_folds_and_smoke_refused(self):
        path = self.new_root / "none/progress.json"
        original = json.loads(path.read_text())
        for change in (dict(full_five_folds=False, completed_folds=[0]), dict(smoke=True)):
            REPORT.write_json(path, {**original, **change})
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.load()
        REPORT.write_json(path, original)

    def test_gene_boundary_tampering_refused(self):
        data = self.load()
        path = self.new_root / "none/fold0/split_audit.json"
        audit = json.loads(path.read_text())
        audit["populations"]["assessment"]["genes"] = ["a_different_synthetic_gene"]
        REPORT.write_json(path, audit)
        with self.assertRaisesRegex(ValueError, "Gene lists"):
            REPORT.validate_pairs(data, self.roots, self.evidence)

    def test_false_zero_overlap_flag_is_not_trusted(self):
        data = self.load()
        for root in self.roots.values():
            path = root / "none/fold0/split_audit.json"
            audit = json.loads(path.read_text())
            audit["populations"]["assessment"]["genes"] = ["synthetic_train"]
            REPORT.write_json(path, audit)
        with self.assertRaisesRegex(ValueError, "Gene sets"):
            REPORT.validate_pairs(data, self.roots, self.evidence)

    def test_fit_signature_or_environment_tampering_refused(self):
        data = self.load()
        path = self.new_root / "none/fold0/inner/complete.json"
        receipt = json.loads(path.read_text())
        receipt["signature"] = "0" * 64
        REPORT.write_json(path, receipt)
        with self.assertRaisesRegex(ValueError, "signature"):
            REPORT.validate_training_signatures(data, self.roots, self.evidence)

    def test_duplicate_resource_invocation_refused(self):
        data = self.load()
        data["cap128"]["resources"].append(deepcopy(data["cap128"]["resources"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            REPORT.calculate_tables(data)

    def test_failed_report_marks_stale_output_non_authoritative(self):
        path = self.new_root / "none/progress.json"
        progress = json.loads(path.read_text())
        progress["full_five_folds"] = False
        REPORT.write_json(path, progress)
        output = Path(self.temp.name) / "comparison"
        output.mkdir()
        (output / "comparison.md").write_text("OLD RESULT MUST NOT APPEAR CURRENT", encoding="utf-8")
        result = REPORT.main(["--baseline-cv", str(self.base_root), "--candidate-cv", str(self.new_root), "--output-dir", str(output)])
        self.assertEqual(result, 2)
        status = json.loads((output / "analysis_status.json").read_text())
        self.assertEqual(status["status"], "failed")
        self.assertFalse(status["existing_outputs_are_authoritative"])

    def test_end_to_end_synthetic_report_manifest_hashes(self):
        output = Path(self.temp.name) / "comparison"
        with mock.patch.object(REPORT, "current_source_evidence", return_value={"synthetic": {"canonical_lf_sha256": "a" * 64}}):
            result = REPORT.main(["--baseline-cv", str(self.base_root), "--candidate-cv", str(self.new_root), "--output-dir", str(output)])
        self.assertEqual(result, 0)
        manifest = json.loads((output / "comparison_manifest.json").read_text())
        signature = manifest.pop("signature")
        self.assertEqual(signature, REPORT.fingerprint(manifest))
        self.assertEqual(manifest["status"], "complete")
        self.assertFalse(manifest["reads_labels"])
        self.assertFalse(manifest["performs_fitting_or_inference"])
        for rel, digest in manifest["output_sha256"].items():
            self.assertEqual(REPORT.sha256(output / rel), digest)
        self.assertIn("Cap32 has the higher", (output / "comparison.md").read_text())


if __name__ == "__main__":
    unittest.main()
