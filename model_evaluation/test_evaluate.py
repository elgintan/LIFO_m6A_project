"""Small scorer correctness/contract checks; these do not train any model."""

import csv
import importlib.util
import json
import statistics
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("shared_evaluate", Path(__file__).with_name("evaluate.py"))
scorer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scorer)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        # Keep temporary fixtures inside the writable checkout in restricted shells.
        self.temporary = tempfile.TemporaryDirectory(prefix=".scorer_test_", dir=Path(__file__).resolve().parent)
        if Path(self.temporary.name).resolve().parent != Path(__file__).resolve().parent:
            raise RuntimeError("Temporary test path escaped the evaluation directory")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write_csv(self, name, header, rows):
        path = self.root / name
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)
        return path

    def test_known_auc_and_average_precision_are_distinct(self):
        result = scorer.metrics([0, 1, 0, 1], [.1, .2, .3, .4])
        self.assertAlmostEqual(result["roc_auc"], .75)
        self.assertAlmostEqual(result["pr_auc_trapezoid"], 19 / 24)
        self.assertAlmostEqual(result["average_precision"], 5 / 6)
        self.assertAlmostEqual(result["selection_score"], (.75 + 19 / 24) / 2)
        self.assertEqual((result["tn"], result["fp"], result["fn"], result["tp"]), (2, 0, 2, 0))

    def test_exact_half_uses_positive_class(self):
        result = scorer.metrics([0, 1], [.49, .5])
        self.assertEqual((result["tn"], result["tp"]), (1, 1))

    def test_key_join_is_independent_of_row_order(self):
        labels_path = self.write_csv("labels.csv", scorer.KEY_COLUMNS + ["label"],
                                     [["a", 10, 0], ["b", 20, 1], ["c", 30, 0], ["d", 40, 1]])
        pred_path = self.write_csv("pred.csv", scorer.KEY_COLUMNS + ["score"],
                                  [["d", "40.0", .4], ["a", 10, .1], ["c", 30, .3], ["b", 20, .2]])
        result = scorer.evaluate_files(labels_path, pred_path, "data1")
        self.assertAlmostEqual(result["pooled"]["roc_auc"], .75)
        self.assertEqual(result["evaluation_kind"], "data1_exposed_transfer")
        self.assertEqual(result["inputs"]["predictions"]["sha256"], scorer.sha256(pred_path))

    def test_missing_extra_and_duplicate_prediction_keys_rejected(self):
        labels = {("a", 1): 0, ("b", 2): 1}
        for predictions in ({("a", 1): .1}, {("a", 1): .1, ("c", 3): .9}):
            with self.subTest(predictions=predictions), self.assertRaisesRegex(ValueError, "coverage differs"):
                scorer.evaluate_tables(labels, predictions, "data1")
        path = self.write_csv("duplicate.csv", scorer.KEY_COLUMNS + ["score"], [["a", 1, .1], ["a", "1.0", .2]])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            scorer.read_predictions(path, "data1")

    def test_invalid_scores_rejected(self):
        for value in ("nan", "inf", "-0.01", "1.01", "", "oops"):
            with self.subTest(value=value):
                path = self.write_csv("bad.csv", scorer.KEY_COLUMNS + ["score"], [["a", 1, value]])
                with self.assertRaisesRegex(ValueError, "Scores must"):
                    scorer.read_predictions(path, "data1")

    def test_fractional_positions_and_labels_rejected(self):
        for value in ("1.2", "nan", "inf", "-1", ""):
            with self.subTest(position=value), self.assertRaises(ValueError):
                scorer.integer(value, "position")
        for value in ("0.25", "nan", "inf", "2", ""):
            with self.subTest(label=value):
                path = self.write_csv("badlabel.csv", scorer.KEY_COLUMNS + ["label"], [["a", 1, value]])
                with self.assertRaisesRegex(ValueError, "binary"):
                    scorer.read_labels(path)

    def test_prediction_schema_is_strict(self):
        for header in (scorer.KEY_COLUMNS + ["score", "extra"], ["score"] + scorer.KEY_COLUMNS,
                       scorer.KEY_COLUMNS + ["score", "fold_id"]):
            path = self.write_csv("schema.csv", header, [])
            with self.subTest(header=header), self.assertRaisesRegex(ValueError, "expected columns"):
                scorer.read_predictions(path, "data1")

    def toy_folds(self):
        labels, predictions, folds, assigned = {}, {}, {}, {}
        for fold in range(5):
            for label in range(2):
                key = (f"tx{fold}_{label}", 1)
                labels[key] = label
                predictions[key] = (.01 + .2 * fold) + .05 * label
                folds[key] = (f"gene{fold}_{label}", fold)
                assigned[key] = fold
        return labels, predictions, folds, assigned

    def test_five_fold_primary_is_mean_fold_not_pooled(self):
        labels, predictions, folds, assigned = self.toy_folds()
        result = scorer.evaluate_tables(labels, predictions, "data0", folds, assigned)
        self.assertEqual(len(result["per_fold"]), 5)
        self.assertAlmostEqual(result["primary_score"], 1.)
        self.assertAlmostEqual(result["sample_sd_fold_ddof1"]["selection_score"], 0.)
        self.assertLess(result["pooled"]["selection_score"], result["primary_score"])

    def test_wrong_fold_and_wrong_gene_rejected(self):
        labels, predictions, folds, assigned = self.toy_folds()
        changed = dict(assigned)
        changed[next(iter(changed))] = 4
        with self.assertRaisesRegex(ValueError, "Prediction fold_id differs"):
            scorer.evaluate_tables(labels, predictions, "data0", folds, changed)
        genes = {key: gene for key, (gene, _) in folds.items()}
        genes[next(iter(genes))] = "different"
        with self.assertRaisesRegex(ValueError, "Label gene_id differs"):
            scorer.evaluate_tables(labels, predictions, "data0", folds, assigned, genes)

    def test_nonzero_fold_deviation_uses_sample_sd(self):
        labels, predictions, folds, assigned = self.toy_folds()
        predictions[("tx0_0", 1)], predictions[("tx0_1", 1)] = .99, .01
        result = scorer.evaluate_tables(labels, predictions, "data0", folds, assigned)
        values = [row["selection_score"] for row in result["per_fold"]]
        self.assertAlmostEqual(result["sample_sd_fold_ddof1"]["selection_score"], statistics.stdev(values))
        self.assertNotAlmostEqual(result["sample_sd_fold_ddof1"]["selection_score"], statistics.pstdev(values))

    def test_fold_manifest_rejects_cross_fold_gene_and_wrong_hash(self):
        path = self.write_csv("folds.csv", scorer.KEY_COLUMNS + ["gene_id", "fold_id"],
                              [["a", 1, "gene", 0], ["b", 2, "gene", 1]])
        with self.assertRaisesRegex(ValueError, "more than one fold"):
            scorer.read_folds(path)
        with self.assertRaisesRegex(ValueError, "SHA256 differs"):
            scorer.evaluate_files(path, path, "data0", folds_path=path)

    def test_duplicate_labels_and_single_class_rejected(self):
        path = self.write_csv("labels.csv", scorer.KEY_COLUMNS + ["label"], [["a", 1, 0], ["a", 1, 1]])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            scorer.read_labels(path)
        with self.assertRaisesRegex(ValueError, "both classes"):
            scorer.metrics([0, 0], [.1, .2])

    def test_failed_validation_preserves_existing_output(self):
        labels = self.write_csv("labels.csv", scorer.KEY_COLUMNS + ["label"], [["a", 1, 0], ["b", 2, 1]])
        predictions = self.write_csv("pred.csv", scorer.KEY_COLUMNS + ["score"], [["a", 1, .1]])
        output = self.root / "metrics.json"
        output.write_text('{"keep": true}\n', encoding="utf-8")
        with self.assertRaises(SystemExit) as error:
            scorer.main(["--labels", str(labels), "--predictions", str(predictions),
                         "--dataset", "data1", "--output", str(output)])
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(json.loads(output.read_text()), {"keep": True})

    def test_cli_happy_path_and_input_overwrite_guard(self):
        labels = self.write_csv("labels.csv", scorer.KEY_COLUMNS + ["label"], [["a", 1, 0], ["b", 2, 1]])
        predictions = self.write_csv("pred.csv", scorer.KEY_COLUMNS + ["score"], [["a", 1, .1], ["b", 2, .9]])
        output = self.root / "metrics.json"
        arguments = ["--labels", str(labels), "--predictions", str(predictions), "--dataset", "data1", "--output"]
        self.assertEqual(scorer.main(arguments + [str(output)]), 0)
        self.assertEqual(json.loads(output.read_text())["primary_score"], 1.)
        original = predictions.read_bytes()
        with self.assertRaises(SystemExit):
            scorer.main(arguments + [str(predictions)])
        self.assertEqual(predictions.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
