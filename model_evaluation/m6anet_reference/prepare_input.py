"""Preserve course nine-feature JSON signals in the m6Anet 2.1 input format.

The tenth value is a per-site row ordinal for vendor bookkeeping, NOT a
biological read identifier. This adapter never receives labels or fits a model.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import time


SCHEMA = "course9_to_m6anet21_row_ordinal_v1"
HEADER = ["transcript_id", "transcript_position", "start", "end", "n_reads"]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json_atomic(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(str(temporary), str(path))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key: {!r}".format(key))
        result[key] = value
    return result


def decode_site(raw, expected_width=9):
    """Validate one already-processed site without changing coordinates/signals."""
    obj = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(obj, dict) or len(obj) != 1:
        raise ValueError("Each source line must contain exactly one transcript")
    transcript, positions = next(iter(obj.items()))
    if not isinstance(transcript, str) or not transcript or any(
        char in transcript for char in "\r\n\t"
    ):
        raise ValueError("Invalid transcript identifier")
    if not isinstance(positions, dict) or len(positions) != 1:
        raise ValueError("Each source line must contain exactly one position")
    position, contexts = next(iter(positions.items()))
    if not isinstance(position, str) or not position.isascii() or not position.isdigit():
        raise ValueError("Position must be a nonnegative decimal integer string")
    if str(int(position)) != position:
        raise ValueError("Position must use canonical decimal notation")
    if not isinstance(contexts, dict) or len(contexts) != 1:
        raise ValueError("Each position must contain exactly one context")
    context, reads = next(iter(contexts.items()))
    if len(context) != 7 or any(char not in "ACGT" for char in context):
        raise ValueError("Expected an uppercase seven-base A/C/G/T context")
    if not isinstance(reads, list) or len(reads) < 20:
        raise ValueError("Site has fewer than 20 reads; no silent coverage filtering")
    for row in reads:
        if not isinstance(row, list) or len(row) != expected_width:
            raise ValueError("Every read must have exactly {} values".format(expected_width))
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("Signal values must be numeric, excluding booleans")
            if not math.isfinite(value):
                raise ValueError("Signal values must be finite")
    return transcript, position, context, reads


def csv_row_bytes(values):
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\n").writerow(values)
    return buffer.getvalue().encode("utf-8")


def signal_chain_update(previous, transcript, position, context, rows):
    """Ordered hash chain of canonical site keys/context/original nine values."""
    payload = json.dumps(
        {transcript: {position: {context: rows}}},
        ensure_ascii=True, allow_nan=False, separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(bytes.fromhex(previous) + payload).hexdigest()


def audit_output(data_path, info_path, expected_sites=None):
    """Read back every indexed byte slice and check metadata/ordinals/coverage."""
    seen = set()
    total_reads = 0
    last_end = 0
    value_chain = "0" * 64
    with Path(data_path).open("rb") as signals, Path(info_path).open(
        "r", encoding="utf-8", newline=""
    ) as index_handle:
        reader = csv.DictReader(index_handle)
        if reader.fieldnames != HEADER:
            raise ValueError("Unexpected data.info column order")
        for index_row in reader:
            start, end = int(index_row["start"]), int(index_row["end"])
            if start != last_end or end <= start:
                raise ValueError("Noncontiguous or invalid byte index")
            signals.seek(start)
            raw = signals.read(end - start)
            if not raw.endswith(b"\n") or len(raw) != end - start:
                raise ValueError("Indexed record is incomplete")
            transcript, position, context, rows = decode_site(raw, 10)
            key = (transcript, position)
            if key != (index_row["transcript_id"], index_row["transcript_position"]):
                raise ValueError("Indexed site key mismatch")
            if key in seen:
                raise ValueError("Duplicate site key")
            seen.add(key)
            if len(rows) != int(index_row["n_reads"]):
                raise ValueError("Indexed read count mismatch")
            if [row[-1] for row in rows] != list(range(len(rows))):
                raise ValueError("Row ordinals are not the declared per-site sequence")
            value_chain = signal_chain_update(
                value_chain, transcript, position, context, [row[:9] for row in rows])
            total_reads += len(rows)
            last_end = end
        signals.seek(0, os.SEEK_END)
        if signals.tell() != last_end:
            raise ValueError("Unindexed trailing JSON bytes")
    if expected_sites is not None and len(seen) != expected_sites:
        raise ValueError("Site count differs from checkpoint")
    return {"sites": len(seen), "reads": total_reads, "data_bytes": last_end,
            "original_signal_chain_sha256": value_chain}, seen


def checked_existing(output, identity):
    receipt_path = output / "complete.json"
    if not receipt_path.exists():
        return None
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("identity") != identity:
        raise ValueError("Completed output belongs to a different source/options/adapter")
    for name in ("data.json", "data.info"):
        if sha256(output / name) != receipt["files"][name]["sha256"]:
            raise ValueError("Completed output hash mismatch: " + name)
    counts, _seen = audit_output(output / "data.json", output / "data.info", receipt["sites"])
    if counts["original_signal_chain_sha256"] != receipt["original_signal_chain_sha256"]:
        raise ValueError("Completed original-signal identity mismatch")
    return receipt


def prepare(source, output, limit_sites=None, checkpoint_every=1000, stop_after=None):
    """Create or safely resume a format-only conversion; complete.json is the gate.

    stop_after is a test hook that simulates a process stopping after unsaved
    writes. It is not exposed by the normal command line.
    """
    started = time.perf_counter()
    source, output = Path(source).resolve(), Path(output).resolve()
    if limit_sites is not None and limit_sites < 1:
        raise ValueError("limit_sites must be positive")
    if checkpoint_every < 1:
        raise ValueError("checkpoint_every must be positive")
    if source == output or source in output.parents:
        raise ValueError("Output cannot replace the source")
    identity = {
        "schema": SCHEMA,
        "source_sha256": sha256(source),
        "source_bytes": source.stat().st_size,
        "adapter_sha256": sha256(__file__),
        "limit_sites": limit_sites,
        "minimum_reads": 20,
    }
    output.mkdir(parents=True, exist_ok=True)
    existing = checked_existing(output, identity)
    if existing is not None:
        return existing
    stage = output / ".preparing"
    allowed_output = {".preparing", "data.json", "data.info", "data.json.publishing", "data.info.publishing"}
    if any(path.name not in allowed_output for path in output.iterdir()):
        raise ValueError("Refusing unrelated existing files in output directory")
    if not (stage / "checkpoint.json").exists() and any(
        path.name != ".preparing" for path in output.iterdir()
    ):
        raise ValueError("Refusing to overwrite output without an adapter checkpoint")
    stage.mkdir(exist_ok=True)
    state_path = stage / "checkpoint.json"
    data_path, info_path = stage / "data.json", stage / "data.info"
    resumed = state_path.exists()
    if resumed:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state["identity"] != identity:
            raise ValueError("Partial output belongs to another source/options/adapter")
        if state["source_lines"] != state["sites"]:
            raise ValueError("Checkpoint source-line/site counts are inconsistent")
        for path, field in ((data_path, "data_bytes"), (info_path, "info_bytes")):
            if not path.exists() or path.stat().st_size < state[field]:
                raise ValueError("Partial output is shorter than its checkpoint")
            with path.open("r+b") as handle:
                handle.truncate(state[field])
        counts, seen = audit_output(data_path, info_path, state["sites"])
        if counts["reads"] != state["reads"]:
            raise ValueError("Partial read-count checkpoint mismatch")
        if counts["original_signal_chain_sha256"] != state["original_signal_chain_sha256"]:
            raise ValueError("Partial original-signal identity mismatch")
    else:
        if any(stage.iterdir()):
            raise ValueError("Unrecognised partial output; choose a fresh directory")
        data_path.write_bytes(b"")
        info_path.write_bytes(csv_row_bytes(HEADER))
        state = {
            "identity": identity, "sites": 0, "reads": 0, "source_lines": 0,
            "data_bytes": 0, "info_bytes": info_path.stat().st_size,
            "original_signal_chain_sha256": "0" * 64,
        }
        write_json_atomic(state_path, state)
        seen = set()
    first_site_count = state["sites"]
    opener = gzip.open if source.suffix.lower() == ".gz" else open
    with opener(str(source), "rb") as input_handle, data_path.open("ab") as signals, info_path.open("ab") as index_handle:
        def checkpoint():
            for handle in (signals, index_handle):
                handle.flush()
                os.fsync(handle.fileno())
            state["data_bytes"], state["info_bytes"] = signals.tell(), index_handle.tell()
            write_json_atomic(state_path, state)

        for line_number, raw in enumerate(input_handle, 1):
            if line_number <= state["source_lines"]:
                continue
            if limit_sites is not None and state["sites"] >= limit_sites:
                break
            try:
                transcript, position, context, reads = decode_site(raw)
            except (ValueError, TypeError, OverflowError) as error:
                raise ValueError("Invalid source line {}: {}".format(line_number, error)) from error
            key = (transcript, position)
            if key in seen:
                raise ValueError("Duplicate site at source line {}: {!r}".format(line_number, key))
            seen.add(key)
            state["original_signal_chain_sha256"] = signal_chain_update(
                state["original_signal_chain_sha256"], transcript, position, context, reads)
            vendor_rows = [row + [ordinal] for ordinal, row in enumerate(reads)]
            encoded = (json.dumps(
                {transcript: {position: {context: vendor_rows}}},
                ensure_ascii=True, allow_nan=False, separators=(",", ":"),
            ) + "\n").encode("ascii")
            start = signals.tell()
            signals.write(encoded)
            end = signals.tell()
            index_handle.write(csv_row_bytes([transcript, position, start, end, len(reads)]))
            state["sites"] += 1
            state["reads"] += len(reads)
            state["source_lines"] = line_number
            if state["sites"] % checkpoint_every == 0:
                checkpoint()
            if stop_after is not None and state["sites"] - first_site_count >= stop_after:
                raise RuntimeError("Test interruption after unsaved writes")
        checkpoint()
    if state["sites"] == 0:
        raise ValueError("Source contains no sites")
    # The compressed input was hashed before conversion; recheck before publishing.
    if sha256(source) != identity["source_sha256"]:
        raise ValueError("Source changed during conversion")
    counts, _seen = audit_output(data_path, info_path, state["sites"])
    if counts["reads"] != state["reads"]:
        raise ValueError("Output read count differs from source count")
    if counts["original_signal_chain_sha256"] != state["original_signal_chain_sha256"]:
        raise ValueError("Output original nine signals differ from source identity")
    files = {}
    for name in ("data.json", "data.info"):
        item = stage / name
        files[name] = {"bytes": item.stat().st_size, "sha256": sha256(item)}
    receipt = {
        "identity": identity,
        "sites": state["sites"], "reads": state["reads"],
        "source_lines_consumed": state["source_lines"],
        "population": "full_source" if limit_sites is None else "first_sites_pilot_subset",
        "metadata_column": "zero-based per-site row ordinal; NOT a biological read ID",
        "signal_columns": "original values in columns 0..8; no fitted transforms",
        "original_signal_identity_checked": True,
        "original_signal_chain_sha256": state["original_signal_chain_sha256"],
        "signal_chain_definition": "SHA256(previous_digest_bytes + canonical_JSON_of_site_with_original_9_columns), initial_digest_32_zero_bytes",
        "positions": "unchanged already-processed coordinates; no offset added",
        "labels_used": False, "resumed": resumed,
        "current_invocation_wall_seconds": time.perf_counter() - started,
        "files": files,
    }
    # Keep staging copies after publication: a crash between these copies and the
    # complete marker can resume safely. Complete marker is always written last.
    for name in ("data.json", "data.info"):
        temporary = output / (name + ".publishing")
        with (stage / name).open("rb") as source_handle, temporary.open("wb") as dest:
            for block in iter(lambda: source_handle.read(1024 * 1024), b""):
                dest.write(block)
            dest.flush()
            os.fsync(dest.fileno())
        os.replace(str(temporary), str(output / name))
    write_json_atomic(output / "complete.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--limit-sites", type=int)
    parser.add_argument("--checkpoint-every", type=int, default=1000)
    args = parser.parse_args()
    receipt = prepare(args.source, args.output, args.limit_sites, args.checkpoint_every)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
