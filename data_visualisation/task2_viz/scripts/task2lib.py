"""Shared helpers for the Task 2 visualisation pipeline.

Kept in one place so the input validator and the site builder read runs, read
counts, annotation, sample metadata and prediction manifests the same way.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

RUN_PATTERN = re.compile(r"^SGNex_(?P<cell_line>.+?)_directRNA_replicate(?P<replicate>\d+)_run(?P<run>\d+)$")
PRED_COLUMNS = ["transcript_id", "transcript_position", "score"]
# Team hand-off manifest (agreed nine columns; extra columns are allowed).
MANIFEST_COLUMNS = ["run_id", "cell_line", "biological_replicate", "sequencing_run", "prediction_file",
                    "coverage_file", "min_reads", "reference_version", "model_version"]

# Display order: the training cell line first, then the rest alphabetically.
CELL_LINE_ORDER = ["Hct116", "A549", "H9", "HEYA8", "HepG2", "K562", "MCF7"]
CELL_LINE_INFO = {
    "Hct116": "colon cancer; training labels come from this line",
    "A549": "lung cancer",
    "H9": "embryonic stem cells",
    "HEYA8": "ovarian cancer",
    "HepG2": "liver cancer",
    "K562": "leukaemia",
    "MCF7": "breast cancer",
}


def parse_run_id(run_id: str) -> dict:
    m = RUN_PATTERN.match(run_id)
    if not m:
        raise ValueError(f"Not an SG-NEx direct RNA run name: {run_id!r}")
    return {"run_id": run_id, "cell_line": m["cell_line"],
            "replicate": int(m["replicate"]), "run": int(m["run"])}


def load_runs(public_dir: Path) -> pd.DataFrame:
    """Runs found on S3, in display order, with integer `idx` and replicate group `group`/`gidx`.

    A metadata replicate-number group belongs to one cell line. Runs within a
    group are not counted as independent replicates. Laboratory independence of
    different groups is not established by these labels alone.
    """
    runs = pd.read_csv(public_dir / "runs_discovered.csv")
    parsed = pd.DataFrame([parse_run_id(r) for r in runs.run_id])
    unknown = sorted(set(parsed.cell_line) - set(CELL_LINE_ORDER))
    order = CELL_LINE_ORDER + unknown
    parsed["line_order"] = parsed.cell_line.map({c: i for i, c in enumerate(order)})
    parsed = parsed.sort_values(["line_order", "replicate", "run"]).reset_index(drop=True)
    parsed["idx"] = np.arange(len(parsed), dtype=np.int16)
    parsed["group"] = parsed.cell_line + ":rep" + parsed.replicate.astype(str)
    parsed["gidx"] = pd.factorize(parsed.group)[0].astype(np.int16)
    return parsed.drop(columns="line_order")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_aliases(path: Path | None, run_ids=None) -> dict[str, dict[str, str]]:
    """Only supplied per-run mappings may change an identifier; never infer aliases."""
    if path is None:
        return {}
    table = pd.read_csv(path, dtype=str, keep_default_na=False)
    cols = ["run_id", "raw_transcript_id", "transcript_id"]
    if not set(cols).issubset(table.columns) or table[cols].eq("").any().any():
        raise ValueError("Alias table needs nonempty run_id,raw_transcript_id,transcript_id")
    if table.duplicated(["run_id", "raw_transcript_id"]).any():
        raise ValueError("Alias table repeats a run/raw identifier")
    if run_ids is not None and not set(table.run_id).issubset(set(run_ids)):
        raise ValueError("Alias table names runs outside the selected scope")
    return {str(run): dict(zip(frame.raw_transcript_id, frame.transcript_id))
            for run, frame in table.groupby("run_id", sort=False)}


def strict_bool(values: pd.Series, name: str) -> pd.Series:
    mapped = values.astype(str).str.lower().map({"true": True, "false": False})
    if mapped.isna().any():
        raise ValueError(f"Context QC {name} must contain only True/False")
    return mapped.astype(bool)


def load_context_qc(directory: Path, manifest: Path, alias_path: Path,
                    prediction_root: Path) -> tuple[pd.DataFrame, dict]:
    """Load a completed context audit bound to the current unmodified prediction files."""
    complete = directory / "complete.json"
    receipt = json.loads(complete.read_text())
    if receipt.get("status") != "complete":
        raise ValueError("Context QC receipt is not complete")
    key_file = directory / "key_context_qc.csv.gz"
    expected = receipt["outputs"][key_file.name]
    if sha256(key_file) != expected["sha256"] or key_file.stat().st_size != expected["size_bytes"]:
        raise ValueError("Context QC table differs from its completed receipt")
    for role, path in (("manifest", manifest), ("aliases", alias_path)):
        if sha256(path) != receipt["inputs"][role]["sha256"]:
            raise ValueError(f"Context QC {role} differs from the current build input")
    current = read_manifest(manifest)
    source = receipt["inputs"]["predictions"]
    by_run = {row["run_id"]: row for row in source}
    if len(by_run) != len(source) or set(by_run) != set(current.run_id):
        raise ValueError("Context QC prediction run scope differs from the current manifest")
    for row in current.itertuples():
        if sha256(prediction_path(prediction_root, row.prediction_file)) != by_run[row.run_id]["sha256"]:
            raise ValueError(f"Context QC predictions changed for {row.run_id}")
    if receipt.get("policy", {}).get("primary") != "all_source_consistent" or \
            receipt.get("policy", {}).get("sensitivity") != "scored_consistent":
        raise ValueError("Context QC policy is not the declared all-source/scored sensitivity")
    qc = pd.read_csv(key_file, dtype=str, keep_default_na=False)
    required = {"transcript_id", "transcript_position", "all_source_consistent", "scored_consistent",
                "encoded7mer_all_source", "encoded7mer_scored", "weak_positive_support_lt20"}
    if not required.issubset(qc.columns) or qc.transcript_id.eq("").any():
        raise ValueError("Context QC table is missing required key/flag/context columns")
    pos = pd.to_numeric(qc.transcript_position, errors="coerce")
    if (pos.isna() | ~np.isfinite(pos) | (pos < 0) | (pos >= 2**63) | (pos != np.floor(pos))).any():
        raise ValueError("Context QC positions must be nonnegative integers")
    qc["transcript_position"] = pos.astype("int64")
    if qc.duplicated(["transcript_id", "transcript_position"]).any():
        raise ValueError("Context QC has duplicate canonical keys")
    for flag in ("all_source_consistent", "scored_consistent", "weak_positive_support_lt20"):
        qc[flag] = strict_bool(qc[flag], flag)
    if "training_support_known_for_all_contexts" in qc:
        qc["training_support_known_for_all_contexts"] = strict_bool(qc.training_support_known_for_all_contexts,
                                                                   "training_support_known_for_all_contexts")
    if (qc.all_source_consistent & ~qc.scored_consistent).any():
        raise ValueError("Context QC primary flag cannot pass when scored consistency fails")
    for flag, context in (("all_source_consistent", "encoded7mer_all_source"),
                          ("scored_consistent", "encoded7mer_scored")):
        valid = qc[context].str.fullmatch(r"[ACGT]{3}A[ACGT]{3}")
        if (qc[flag] & ~valid).any():
            raise ValueError(f"Context QC {flag} requires one encoded central-A seven-base context")
    info = {"receipt_sha256": sha256(complete), "table_sha256": expected["sha256"],
            "policy": receipt["policy"], "n_keys": len(qc),
            "n_primary_eligible": int(qc.all_source_consistent.sum()),
            "n_scored_consistent": int(qc.scored_consistent.sum()),
            "n_weak_positive_support": int(qc.weak_positive_support_lt20.sum())}
    return qc, info


def load_readcounts(public_dir: Path, runs: pd.DataFrame, aliases: dict | None = None) -> pd.DataFrame:
    """Long table: run_idx, transcript_id, transcript_position, n_reads (every site with >= 1 read).

    Only mappings supplied in aliases[run_id] are applied. Unlisted identifiers,
    including versioned IDs, remain literal. Original files are never rewritten.
    """
    frames = []
    for r in runs.itertuples():
        df = pd.read_csv(public_dir / "readcount" / f"{r.run_id}.readcount.csv",
                         dtype={"transcript_id": "string", "transcript_position": "int32", "n_reads": "int32"})
        if list(df.columns) != ["transcript_id", "transcript_position", "n_reads"]:
            raise ValueError(f"{r.run_id}: unexpected readcount columns {list(df.columns)}")
        amap = (aliases or {}).get(r.run_id, {})
        if amap:
            df["transcript_id"] = df.transcript_id.map(lambda t: amap.get(t, t)).astype("string")
            if df.duplicated(["transcript_id", "transcript_position"]).any():
                raise ValueError(f"{r.run_id}: applying the alias map created duplicate sites")
        if df.duplicated(["transcript_id", "transcript_position"]).any():
            raise ValueError(f"{r.run_id}: duplicate readcount sites")
        df["run_idx"] = np.int16(r.idx)
        frames.append(df)
    rc = pd.concat(frames, ignore_index=True)
    rc["transcript_id"] = rc["transcript_id"].astype("category")
    return rc


def load_annotation(path: Path) -> pd.DataFrame:
    """Read the SG-NEx Ensembl 91 transcript table, fixing its shifted header.

    The file was written with R row names: the header has 14 names but every
    data row has 15 fields, the first being the transcript ID again. Reading it
    naively shifts every column one place to the right. We read the extra field
    as 'row_name' and then check that the columns line up.
    """
    with path.open() as fh:
        header = fh.readline().rstrip("\n").split("\t")
    ann = pd.read_csv(path, sep="\t", header=None, skiprows=1, names=["row_name"] + header,
                      dtype=str, quoting=csv.QUOTE_NONE, keep_default_na=False)
    checks = {
        "row names equal transcript IDs": (ann.row_name == ann.ensembl_transcript_id).all(),
        "gene IDs start with ENSG": ann.ensembl_gene_id.str.startswith("ENSG").all(),
        "transcript IDs start with ENST": ann.ensembl_transcript_id.str.startswith("ENST").all(),
        "transcript IDs unique": not ann.ensembl_transcript_id.duplicated().any(),
        "transcript lengths numeric": pd.to_numeric(ann.tx_len, errors="coerce").notna().all(),
    }
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"Annotation columns do not line up: {failed}")
    return pd.DataFrame({
        "transcript_id": ann.ensembl_transcript_id,
        "gene_id": ann.ensembl_gene_id,
        "symbol": ann.hgnc_symbol,
        "biotype": ann.gene_biotype,
        "description": ann.description.str.replace(r"\s*\[Source:.*\]$", "", regex=True),
        "chromosome": ann.chromosome_name,
        "gene_start": pd.to_numeric(ann.start_position),
        "gene_end": pd.to_numeric(ann.end_position),
        "strand": pd.to_numeric(ann.strand).map({1: "+", -1: "-"}),
        "tx_len": pd.to_numeric(ann.tx_len).astype("int64"),
        "n_exons": pd.to_numeric(ann.nexon).astype("int64"),
        "tx_version": ann["ensembl_transcript_id.version"],
    })


def transcript_kind(tx_ids: pd.Series, annotated: set[str]) -> pd.Series:
    """annotated | alt_haplotype | spike_SIRV | spike_ERCC | spike_sequin | other."""
    s = tx_ids.astype(str)
    kind = pd.Series("other", index=s.index, dtype=object)
    kind[s.str.startswith("ENST")] = "alt_haplotype"   # ENST missing from the primary-assembly table
    kind[s.isin(annotated)] = "annotated"
    kind[s.str.startswith("SIRV")] = "spike_SIRV"
    kind[s.str.match(r"^(DQ|EF)\d+$")] = "spike_ERCC"
    kind[s.str.match(r"^R\d+_\d+_\d+$")] = "spike_sequin"
    return kind


def load_sample_metadata(path: Path) -> pd.DataFrame:
    """Run-level metadata from the official SG-NEx sample sheet (Member 4's sample_manifest.csv)."""
    sm = pd.read_csv(path, dtype=str, keep_default_na=False)
    pick = {"run_id": "run_id", "replicate_group": "group", "protocol": "protocol", "kit": "kit",
            "flowcell": "flowcell", "Platform": "platform", "basecaller_version(ENA)*": "basecaller",
            "generation_date": "date", "Spike in concentration": "spike_in"}
    missing = [c for c in pick if c not in sm.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    out = sm[list(pick)].rename(columns=pick)
    d = out.date.str.replace(r"\.0$", "", regex=True)
    out["date"] = np.where(d.str.fullmatch(r"\d{8}"), d.str[:4] + "-" + d.str[4:6] + "-" + d.str[6:], d)
    return out


def read_manifest(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def read_predictions(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"transcript_id": "string", "transcript_position": "string",
                                    "score": "string"}, keep_default_na=False)


def prediction_path(inputs: Path, relative: str) -> Path:
    """Resolve a declared CSV inside its hand-off folder; never follow outside paths."""
    rel = Path(relative)
    resolved = (inputs / rel).resolve()
    if rel.is_absolute() or not resolved.is_relative_to(inputs.resolve()) or rel.suffix.lower() != ".csv":
        raise ValueError("prediction_file must name a CSV inside the hand-off folder")
    return resolved
