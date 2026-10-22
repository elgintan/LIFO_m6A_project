"""Final wrapper contract checks with synthetic receipts; no NN fit or weights."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


def import_file(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = import_file("tested_final_cap128", "final_fit_cap128.py")
FIXTURE = import_file("final_cap128_saved_fixtures", "test_report_read_cap.py")


class FinalContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        _, self.recipe = FIXTURE.recipes()

    def test_only_exact_nomination_config_and_training_rule_allowed(self):
        actual = MODULE.configuration(self.recipe)
        self.assertEqual(actual["cap"], 128)
        self.assertEqual(actual["pos_weight"], 3.)
        for area, key, value in (("config", "pos_weight", 1.), ("config", "cap", 32),
                                 ("config", "context_mode", "relative"), (None, "seed", 77),
                                 (None, "batch_size", 64), (None, "smoke", True)):
            changed = deepcopy(self.recipe)
            (changed if area is None else changed[area])[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                MODULE.configuration(changed)

    def test_actual_epoch_median_is_eighteen_not_a_tuned_constant(self):
        values, selected = MODULE.epoch_choice(dict(selected_epochs=[9, 20, 19, 18, 17]))
        self.assertEqual(values, [9, 20, 19, 18, 17])
        self.assertEqual(selected, 18)
        self.assertEqual(MODULE.epoch_choice(dict(selected_epochs=[2, 4, 5, 3, 1]))[1], 3)
        for values in ([9], [0, 1, 2, 3, 4], [9, 20, 21, 18, 17], [9., 20, 19, 18, 17]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                MODULE.epoch_choice(dict(selected_epochs=values))

    def test_nine_source_cv_identity_preserved_and_extra_provenance_refused(self):
        identity = self.recipe["identity"]
        original = deepcopy(identity)
        core = {k: v for k, v in identity["source_sha256"].items() if k not in
                ("tools/train_read_cap.py", "READ_CAP_EXPERIMENT.md")}
        def digest(path):
            key = "tools/train_read_cap.py" if Path(path) == Path(MODULE.cap.__file__) else "READ_CAP_EXPERIMENT.md"
            return identity["source_sha256"][key]
        with mock.patch.object(MODULE.fitting, "source_hashes", side_effect=lambda: dict(core)), \
                mock.patch.object(MODULE.cap, "source_sha256", side_effect=digest):
            self.assertEqual(len(MODULE.check_cv_identity(identity)), 9)
            self.assertEqual(identity, original)
            changed = deepcopy(identity); changed["final_entrypoint_sha256"] = "f" * 64
            with self.assertRaisesRegex(ValueError, "identity/source map"):
                MODULE.check_cv_identity(changed)
            changed = deepcopy(identity); changed["source_sha256"]["model.py"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "identity/source map"):
                MODULE.check_cv_identity(changed)

    def test_completed_cv_and_exact_fit_signatures_required(self):
        cv = self.folder / "cv"
        FIXTURE.write_saved_cv(cv, self.recipe)
        evidence = {}
        parent = MODULE.SAVED.load_mode(cv, "none", evidence)
        with mock.patch.object(MODULE, "CV_ROOT", cv):
            MODULE.validate_fit_signatures(parent, evidence)
            path = cv / "none/fold0/inner/complete.json"
            receipt = MODULE.read_json(path); receipt["signature"] = "0" * 64
            path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "signature mismatch"):
                MODULE.validate_fit_signatures(parent, evidence)
        progress_path = cv / "none/progress.json"
        progress = MODULE.read_json(progress_path); progress["full_five_folds"] = False
        progress_path.write_text(json.dumps(progress), encoding="utf-8")
        with self.assertRaises(ValueError):
            MODULE.SAVED.load_mode(cv, "none", {})

    def test_nomination_plan_is_separately_guarded_and_immutable(self):
        plan = self.folder / "FINAL_MODEL_SELECTION.md"
        plan.write_text("Original cap128 weight3, median18.\n", encoding="utf-8")
        with mock.patch.object(MODULE, "PLAN", plan):
            guard = MODULE.nomination_guard()
            path = self.folder / "wrapper_spec.json"
            MODULE.immutable_json(path, dict(cv_identity=self.recipe["identity"], wrapper_and_selection=guard))
            plan.write_text("Changed nomination\n", encoding="utf-8")
            changed = MODULE.nomination_guard()
            self.assertNotEqual(guard, changed)
            with self.assertRaisesRegex(ValueError, "Frozen final wrapper"):
                MODULE.immutable_json(path, dict(cv_identity=self.recipe["identity"], wrapper_and_selection=changed))

    def test_existing_lock_is_never_declared_stale_from_pid_absence(self):
        path = self.folder / "final.lock"
        previous = dict(pid=999999999, token="old-but-unverified")
        path.write_text(json.dumps(previous), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "original session"):
            with MODULE.phase_lock(path):
                self.fail("Existing lock must not be reclaimed")
        self.assertEqual(MODULE.read_json(path), previous)
        path.unlink()
        with self.assertRaises(KeyboardInterrupt):
            with MODULE.phase_lock(path):
                raise KeyboardInterrupt
        self.assertFalse(path.exists())

    def test_delegate_passes_original_identity_and_calls_only_run_final(self):
        cache, meta = object(), object()
        config = MODULE.configuration(self.recipe)
        args = SimpleNamespace(seed=2026, batch_size=256, threads=4, patience=5)
        identity = deepcopy(self.recipe["identity"])
        with mock.patch.object(MODULE.fitting, "run_final", return_value="delegated") as delegated, \
                mock.patch.object(MODULE.fitting, "run_fit", side_effect=AssertionError("Wrapper must not directly fit")), \
                mock.patch.object(MODULE.fitting.torch, "load", side_effect=AssertionError("No real weights in this test")):
            self.assertEqual(MODULE.delegate_final(cache, meta, config, args, identity), "delegated")
        delegated.assert_called_once_with(cache, meta, config, args, identity)
        self.assertEqual(len(identity["source_sha256"]), 9)

    def test_check_only_records_spec_and_never_delegates_a_fit(self):
        frozen = dict(inner_selected_epochs=[9, 20, 19, 18, 17], selected_epochs=18,
                      wrapper_and_selection=dict(final_entrypoint_sha256="a", selection_plan_sha256="b"))
        args = SimpleNamespace(check_only=True, fit=False)
        fake = (object(), object(), MODULE.configuration(self.recipe), self.recipe["identity"], frozen, {})
        with mock.patch.object(MODULE, "DEFAULT", self.folder), \
                mock.patch.object(MODULE, "preflight", return_value=fake), \
                mock.patch.object(MODULE, "unchanged"), \
                mock.patch.object(MODULE, "delegate_final", side_effect=AssertionError("Check-only cannot fit")):
            result = MODULE.execute(args)
        self.assertEqual(result["status"], "checked_no_fitting")
        self.assertEqual(result["selected_epochs"], 18)
        self.assertEqual(MODULE.read_json(self.folder / "final_phase/frozen_wrapper_specification.json"), frozen)

    def test_fit_requires_prior_checked_specification(self):
        frozen = dict(selected_epochs=18, inner_selected_epochs=[9, 20, 19, 18, 17])
        fake = (object(), object(), MODULE.configuration(self.recipe), self.recipe["identity"], frozen, {})
        with mock.patch.object(MODULE, "DEFAULT", self.folder), \
                mock.patch.object(MODULE, "preflight", return_value=fake), \
                mock.patch.object(MODULE, "delegate_final", side_effect=AssertionError("Must not fit")):
            with self.assertRaisesRegex(ValueError, "Run --check-only"):
                MODULE.execute(SimpleNamespace(check_only=False, fit=True))


if __name__ == "__main__":
    unittest.main()
