"""Synthetic-only checks of paired read-depth reporting; no project data read."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

SPEC = importlib.util.spec_from_file_location("depth_report", Path(__file__).with_name("report_read_depth_stability.py"))
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)


def synthetic_scores():
    cohort = pd.DataFrame([
        {"site_index": fold * 4 + i, "transcript_id": f"synthetic_{fold}_{i}",
         "transcript_position": 100 + i, "gene_id": f"synthetic_gene_{fold}",
         "fold_id": fold, "label": i % 2, "coverage": 220 if i >= 2 else 120,
         "motif": "AAAAA" if i % 2 else "CCCCC"}
        for fold in range(5) for i in range(4)
    ])
    rows = []
    for site in cohort.to_dict("records"):
        cached = .55 if site["label"] else .45
        recomputed = .60 if site["label"] else .40
        for arm in ("all-cache", "all-recomputed"):
            rows.append({**site, "perturbation": arm, "depth": "all", "repeat_id": -1,
                         "repeat_seed": "all", "n_reads_used": site["coverage"],
                         "score": cached if arm == "all-cache" else recomputed,
                         "baseline_score": cached})
        for arm in REPORT.ARM_REFERENCE:
            for depth in (20, 32, 50, 100):
                for repeat in range(3):
                    score = (.45 if site["label"] else .60) if depth == 20 else cached
                    rows.append({**site, "perturbation": arm, "depth": str(depth), "repeat_id": repeat,
                                 "repeat_seed": str(2026 + repeat), "n_reads_used": depth,
                                 "score": score, "baseline_score": cached})
    return pd.DataFrame(rows), cohort


def write_synthetic_run(directory, frame, cohort):
    """Write a tiny complete receipt graph without any real project inputs."""
    directory = Path(directory)
    cohort_path = directory / "cohort.csv"
    cohort.to_csv(cohort_path, index=False)
    specs = []
    for (fold, arm, depth, repeat, seed), _ in frame.groupby(["fold_id", "perturbation", "depth", "repeat_id", "repeat_seed"]):
        cid = f"fold{fold}/{arm}" if depth == "all" else f"fold{fold}/{arm}/depth{depth}/seed{seed}"
        specs.append(dict(condition_id=cid, fold_id=int(fold), perturbation=arm,
                          depth=depth if depth == "all" else int(depth), repeat_id=int(repeat),
                          repeat_seed=seed if seed == "all" else int(seed)))
    experiment = dict(is_trial=False, depths=[20, 32, 50, 100], repeat_seeds=[2026, 2027, 2028],
                      perturbations=["both", "bag-only"], cohort_sha256=REPORT.sha256(cohort_path),
                      cohort_sites=len(cohort), cohort_positives=int(cohort.label.sum()),
                      expected_condition_ids=[spec["condition_id"] for spec in specs],
                      models=[dict(fold_id=f, model_sha256=f"synthetic_model_{f}") for f in range(5)])
    experiment["signature"] = REPORT.fingerprint(experiment)
    REPORT.write_json(directory / "experiment.json", experiment)
    receipts = {}
    for specification in specs:
        cid = specification["condition_id"]
        path = directory / "conditions" / cid
        path.mkdir(parents=True)
        part = frame[(frame.fold_id == specification["fold_id"]) & (frame.perturbation == specification["perturbation"])
                     & (frame.depth == str(specification["depth"])) & (frame.repeat_id == specification["repeat_id"])]
        part.to_csv(path / "predictions.csv", index=False, float_format="%.17g")
        identity = dict(**specification, experiment_signature=experiment["signature"],
                        cohort_sha256=experiment["cohort_sha256"], model_sha256=f"synthetic_model_{specification['fold_id']}")
        record = dict(status="complete", signature=REPORT.fingerprint(identity), **identity,
                      n_sites=len(part), n_positives=int(part.label.sum()), resources={},
                      predictions_sha256=REPORT.sha256(path / "predictions.csv"))
        REPORT.write_json(path / "complete.json", record)
        receipts[cid] = REPORT.sha256(path / "complete.json")
    REPORT.write_json(directory / "progress.json", dict(experiment_signature=experiment["signature"],
                      all_completed=True, completed_condition_ids=list(receipts), complete_receipt_sha256=receipts))
    REPORT.write_json(directory / "invocation_arguments.json", {"arguments": []})


class ReportChecks(unittest.TestCase):
    def setUp(self):
        self.frame, self.cohort = synthetic_scores()

    def test_arm_correct_references(self):
        REPORT.validate_frame(self.frame, self.cohort)
        joined = REPORT.attach_reference(self.frame)
        both = joined[(joined.perturbation == "both") & (joined.label == 1) & (joined.depth == "32")]
        bag = joined[(joined.perturbation == "bag-only") & (joined.label == 1) & (joined.depth == "32")]
        np.testing.assert_allclose(both.score_delta, -.05)
        np.testing.assert_allclose(bag.score_delta, 0.)

    def test_fold_mean_and_flip_directions(self):
        tables = REPORT.calculate_tables(self.frame, self.cohort)
        summary = tables["depth_metrics"]
        for metric in REPORT.RANKING:
            expected = tables["fold_repeat_metrics"].query("population == 'matched_ge100' and perturbation == 'both' and depth == '20'").groupby("fold_id")[metric].mean().mean()
            row = summary.query("population == 'matched_ge100' and perturbation == 'both' and depth == '20'").iloc[0]
            self.assertAlmostEqual(row[f"mean_fold_{metric}"], expected)
        drift = tables["score_drift"].query("population == 'matched_ge100' and perturbation == 'both' and depth == '20'")
        positives = drift[drift.label_stratum == "1"].iloc[0]
        negatives = drift[drift.label_stratum == "0"].iloc[0]
        self.assertEqual(positives.new_false_negative_fraction, 1.)
        self.assertEqual(positives.new_false_positive_fraction, 0.)
        self.assertEqual(negatives.new_false_positive_fraction, 1.)
        self.assertEqual(negatives.new_false_negative_fraction, 0.)
        self.assertTrue(tables["motif_descriptive_metrics"][REPORT.RANKING].isna().all().all())

    def test_changed_cohort_and_duplicate_fail(self):
        changed = self.frame.copy()
        changed.loc[0, "label"] = 1 - changed.loc[0, "label"]
        with self.assertRaisesRegex(ValueError, "metadata"):
            REPORT.validate_frame(changed, self.cohort)
        with self.assertRaisesRegex(ValueError, "Duplicate site"):
            REPORT.validate_frame(pd.concat([self.frame, self.frame.iloc[[0]]]), self.cohort)

    def test_reference_consistency_and_score_bounds_fail(self):
        changed = self.frame.copy()
        changed.loc[0, "baseline_score"] += .001
        with self.assertRaisesRegex(ValueError, "OOF reference"):
            REPORT.validate_frame(changed, self.cohort)
        changed = self.frame.copy()
        changed.loc[0, "score"] = float("nan")
        with self.assertRaisesRegex(ValueError, "Non-finite"):
            REPORT.validate_frame(changed, self.cohort)

    def test_figures_and_descriptive_report(self):
        tables = REPORT.calculate_tables(self.frame, self.cohort)
        temporary_parent = (REPORT.ALLOWED_ROOT / "trial/analysis").resolve()
        self.assertTrue(temporary_parent.is_relative_to(REPORT.ALLOWED_ROOT.resolve()))
        temporary_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="synthetic_depth_report_", dir=temporary_parent) as directory:
            REPORT.make_figures(tables, Path(directory))
            self.assertEqual(len(list(Path(directory).glob("*.png"))), 3)
        text = REPORT.report_text(tables, self.cohort, {"is_trial": True}, "python synthetic_test.py")
        self.assertIn("TRIAL ONLY", text)
        self.assertIn("pool sites across held-out models", text)
        self.assertIn("not independently sequenced", text)

    def test_completed_recipe_and_receipt_tamper_guards(self):
        temporary_parent = (REPORT.ALLOWED_ROOT / "trial/analysis").resolve()
        self.assertTrue(temporary_parent.is_relative_to(REPORT.ALLOWED_ROOT.resolve()))
        temporary_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="synthetic_receipts_", dir=temporary_parent) as directory:
            write_synthetic_run(directory, self.frame, self.cohort)
            frame, cohort, *_ = REPORT.load_completed(Path(directory))
            self.assertEqual(len(frame), len(self.frame))
            self.assertEqual(len(cohort), len(self.cohort))
            marker = next((Path(directory) / "conditions").rglob("complete.json"))
            changed = REPORT.read_json(marker)
            changed["model_sha256"] = "another_model"
            REPORT.write_json(marker, changed)
            with self.assertRaisesRegex(ValueError, "Condition signature"):
                REPORT.load_completed(Path(directory))


if __name__ == "__main__":
    unittest.main()
