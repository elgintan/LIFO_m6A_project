"""Publish a completed cap128 artifact and a small real prediction example.

No fitting or model selection. Large epoch checkpoints remain in local outputs.
"""
import argparse
import csv
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys

import final_fit_cap128 as final

REPO = final.REPO
SOURCE = final.DEFAULT / "final/none"
DESTINATION = REPO / "model_elgin/artifacts/cap128_weight3_v1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DESTINATION)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    status = final.read_json(final.DEFAULT / "final_phase/status.json")
    if status["status"] != "final_model_complete_no_predictions":
        raise ValueError("Complete and review the final fit before packaging")
    for name, digest in status["final_files_sha256"].items():
        if final.sha256(SOURCE / name) != digest:
            raise ValueError("Changed final artifact: " + name)
    if final.nomination_guard() != status["wrapper_and_selection"]:
        raise ValueError("Final nomination or wrapper changed")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Preserve previous packages; use a fresh output directory")
    output.mkdir(parents=True, exist_ok=True)
    model_path = output / "model.pt"
    shutil.copyfile(SOURCE / "model.pt", model_path)
    if final.sha256(model_path) != status["model_sha256"]:
        raise ValueError("Packaged model bytes differ from the frozen fit")
    from model import load_model
    model, bundle = load_model(model_path)
    if (bundle["config"]["cap"] != 128 or bundle["config"]["pos_weight"] != 3
            or bundle["epoch"] != 18 or bundle["norm"]["fit_sites"] != 121838
            or bundle["norm"]["fit_reads"] != 11027106):
        raise ValueError("Wrong nominated artifact or all-data0 normalisers")
    del model
    specification = final.read_json(SOURCE / "frozen_specification.json")
    final.cap.save_json(output / "training_specification.json", specification)
    example = output / "example"
    example.mkdir()
    raw = REPO.parent / "data0/dataset0.json.gz"
    if final.sha256(raw) != bundle["input_fingerprints"]["data0_input_sha256"]:
        raise ValueError("Example source differs from agreed training data0")
    with gzip.open(raw, "rb") as source, (example / "input.json").open("wb") as destination:
        for _ in range(10):
            record = source.readline()
            if not record:
                raise ValueError("Insufficient real example sites")
            destination.write(record)
    predictor = REPO / "model_elgin/context_reference_v1/predict.py"
    command = [sys.executable, "-B", str(predictor), "--input", str(example / "input.json"),
               "--model", str(model_path), "--output", str(example / "expected.csv"), "--threads", "4"]
    result = subprocess.run(command, capture_output=True, text=True)
    (output / "example_check.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError("Actual packaged-model CLI example failed; partial files preserved")
    manifest = final.read_json(example / "expected.csv.manifest.json")
    if manifest["n_sites"] != 10 or manifest["model_sha256"] != status["model_sha256"] or not manifest["all_reads_used"]:
        raise ValueError("Packaged example coverage/model mismatch")
    final.cap.save_json(output / "metadata.json", dict(
        model_sha256=status["model_sha256"], stage="final_data0", config=bundle["config"],
        epochs=18, seed=2026, training_sites=121838, training_reads=11027106,
        calling_rule="0.5 working reporting cutoff; continuous outputs; no fitted calibrator",
        selection_plan_sha256=status["wrapper_and_selection"]["selection_plan_sha256"],
        final_entrypoint_sha256=status["wrapper_and_selection"]["final_entrypoint_sha256"],
        example_sites=10, example_reads=manifest["n_reads"],
        example_scope="First ten data0 sites, for software checks only; not unseen validation",
        training_data="data0 only; no data1/data2/SG-NEx fitting",
        validation="Use saved five-fold OOF scores, not fitted-data0 final predictions"))
    files = {str(p.relative_to(output)).replace("\\", "/"): final.sha256(p)
             for p in sorted(output.rglob("*")) if p.is_file()}
    final.cap.save_json(output / "complete.json", dict(status="complete", files_sha256=files))
    print(json.dumps(dict(status="complete", model_sha256=status["model_sha256"],
                         example_sites=10, example_reads=manifest["n_reads"])), flush=True)


if __name__ == "__main__":
    main()
