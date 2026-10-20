"""Shared helpers for the Task 2 visualisation pipeline.

Kept in one place so the input validator and the site builder read runs, read
counts, annotation, sample metadata and prediction manifests the same way.
"""
from __future__ import annotations

import csv
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
VERSIONED_ID = re.compile(r"^(ENST\d+)\.\d+$")


def parse_run_id(run_id: str) -> dict:
    m = RUN_PATTERN.match(run_id)
    if not m:
        raise ValueError(f"Not an SG-NEx direct RNA run name: {run_id!r}")
    return {"run_id": run_id, "cell_line": m["cell_line"],
            "replicate": int(m["replicate"]), "run": int(m["run"])}


def load_runs(public_dir: Path) -> pd.DataFrame:
    """Runs found on S3, in display order, with integer `idx` and replicate group `group`/`gidx`.

    A replicate group is one biological replicate of one cell line. Runs within a
    group are repeat sequencing of the same sample and are not independent repeats.
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


def versioned_aliases(ids: pd.Series) -> dict[str, str]:
    """Explicit alias map for Ensembl IDs written with a version (ENST..9 -> ENST..)."""
    uniq = pd.Series(ids.unique()).astype(str)
    m = uniq.str.extract(VERSIONED_ID)[0]
    return {raw: base for raw, base in zip(uniq[m.notna()], m[m.notna()])}


def load_readcounts(public_dir: Path, runs: pd.DataFrame, aliases: dict | None = None) -> pd.DataFrame:
    """Long table: run_idx, transcript_id, transcript_position, n_reads (every site with >= 1 read).

    One SG-NEx run (MCF7 replicate 3 run 1) labels transcripts with Ensembl
    versions while the other runs do not. For such runs an explicit alias map
    (raw ID -> unversioned ID) is built and applied, and returned through
    `aliases[run_id]` so it can be checked and published. IDs that are not
    versioned are never changed.
    """
    frames = []
    for r in runs.itertuples():
        df = pd.read_csv(public_dir / "readcount" / f"{r.run_id}.readcount.csv",
                         dtype={"transcript_id": "string", "transcript_position": "int32", "n_reads": "int32"})
        if list(df.columns) != ["transcript_id", "transcript_position", "n_reads"]:
            raise ValueError(f"{r.run_id}: unexpected readcount columns {list(df.columns)}")
        amap = versioned_aliases(df.transcript_id)
        if amap:
            df["transcript_id"] = df.transcript_id.map(lambda t: amap.get(t, t)).astype("string")
            if df.duplicated(["transcript_id", "transcript_position"]).any():
                raise ValueError(f"{r.run_id}: applying the alias map created duplicate sites")
            if aliases is not None:
                aliases[r.run_id] = amap
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
