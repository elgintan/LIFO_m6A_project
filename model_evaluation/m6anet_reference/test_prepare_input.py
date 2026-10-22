"""Format-adapter correctness checks; no vendor imports, models or real fitting."""
import csv
import gzip
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import prepare_input as adapter


def site(transcript="ENST00000000233", position=244, count=20):
    rows = [[0.00299 + index / 100000, 2.06, 125.0, 0.0177,
             10.4, 122.0, 0.0093, 10.9, 84.1] for index in range(count)]
    return {transcript: {str(position): {"AAGACCA": rows}}}


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="m6anet_adapter_", dir=os.environ.get("M6ANET_TEST_TMP_ROOT"))
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.json.gz"
        self.output = self.root / "adapted"

    def tearDown(self):
        self.temporary.cleanup()

    def write_source(self, objects):
        with gzip.open(self.source, "wt", encoding="utf-8", newline="\n") as handle:
            for obj in objects:
                handle.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def assert_original_values(self, objects):
        expected = [adapter.decode_site(json.dumps(obj)) for obj in objects]
        with (self.output / "data.info").open("r", encoding="utf-8", newline="") as handle:
            indexed = list(csv.DictReader(handle))
        self.assertEqual(len(indexed), len(expected))
        with (self.output / "data.json").open("rb") as handle:
            for (transcript, position, context, reads), record in zip(expected, indexed):
                handle.seek(int(record["start"]))
                raw = handle.read(int(record["end"]) - int(record["start"]))
                self.assertTrue(raw.isascii())
                out_t, out_p, out_c, out_rows = adapter.decode_site(raw, 10)
                self.assertEqual((out_t, out_p, out_c), (transcript, position, context))
                self.assertEqual([row[:9] for row in out_rows], reads)
                self.assertEqual([row[9] for row in out_rows], list(range(len(reads))))
                self.assertEqual(record["transcript_position"], position)

    def test_full_preserves_values_keys_coordinates_and_unicode_byte_offsets(self):
        objects = [site(), site("ENST_\u03b2_\u57fa\u56e0", 467, 23), site(position=542)]
        self.write_source(objects)
        receipt = adapter.prepare(self.source, self.output, checkpoint_every=2)
        self.assertEqual((receipt["sites"], receipt["reads"]), (3, 63))
        self.assertEqual(receipt["population"], "full_source")
        self.assertFalse(receipt["labels_used"])
        self.assertTrue(receipt["original_signal_identity_checked"])
        self.assertIn("NOT a biological", receipt["metadata_column"])
        self.assert_original_values(objects)
        counts, _ = adapter.audit_output(self.output / "data.json", self.output / "data.info", 3)
        self.assertEqual(counts["reads"], 63)

    def test_resume_truncates_unsaved_records_and_does_not_duplicate_sites(self):
        objects = [site(position=244 + index) for index in range(5)]
        self.write_source(objects)
        with self.assertRaisesRegex(RuntimeError, "Test interruption"):
            adapter.prepare(self.source, self.output, checkpoint_every=2, stop_after=3)
        state = json.loads((self.output / ".preparing/checkpoint.json").read_text())
        self.assertEqual(state["sites"], 2)
        self.assertFalse((self.output / "complete.json").exists())
        self.assertGreater((self.output / ".preparing/data.json").stat().st_size, state["data_bytes"])
        receipt = adapter.prepare(self.source, self.output, checkpoint_every=2)
        self.assertTrue(receipt["resumed"])
        self.assertEqual(receipt["sites"], 5)
        self.assert_original_values(objects)

    def test_completed_reuse_checks_hashes_and_rejects_tampering(self):
        self.write_source([site()])
        first = adapter.prepare(self.source, self.output)
        self.assertEqual(adapter.prepare(self.source, self.output), first)
        with (self.output / "data.json").open("ab") as handle:
            handle.write(b" ")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            adapter.prepare(self.source, self.output)

    def test_pilot_is_explicit_subset_and_cannot_be_silently_extended(self):
        self.write_source([site(position=244 + index) for index in range(3)])
        receipt = adapter.prepare(self.source, self.output, limit_sites=2)
        self.assertEqual(receipt["population"], "first_sites_pilot_subset")
        self.assertEqual(receipt["sites"], 2)
        self.assertEqual(receipt["identity"]["limit_sites"], 2)
        with self.assertRaisesRegex(ValueError, "different source/options/adapter"):
            adapter.prepare(self.source, self.output)

    def test_duplicate_sites_rejected_without_complete_marker(self):
        self.write_source([site(), site()])
        with self.assertRaisesRegex(ValueError, "Duplicate site"):
            adapter.prepare(self.source, self.output)
        self.assertFalse((self.output / "complete.json").exists())

    def test_invalid_signal_and_structure_cases_are_rejected(self):
        cases = []
        for invalid in (float("nan"), float("inf"), True, "0.1"):
            obj = site()
            obj["ENST00000000233"]["244"]["AAGACCA"][0][0] = invalid
            cases.append(obj)
        wrong_width = site()
        wrong_width["ENST00000000233"]["244"]["AAGACCA"][0].append(0)
        cases.extend([wrong_width, site(count=19), {}, {"ENST": {"244": {}}},
                      {"ENST": {"0244": {"AAGACCA": [[0] * 9] * 20}}}])
        for index, obj in enumerate(cases):
            with self.subTest(index=index):
                self.write_source([obj])
                with self.assertRaises(ValueError):
                    adapter.prepare(self.source, self.root / ("bad_" + str(index)))
                self.assertFalse((self.root / ("bad_" + str(index)) / "complete.json").exists())
        with self.assertRaisesRegex(ValueError, "Duplicate JSON object"):
            adapter.decode_site('{"ENST":{},"ENST":{}}')

    def test_source_and_partial_option_change_refuse_reuse(self):
        self.write_source([site(position=244 + index) for index in range(3)])
        with self.assertRaises(RuntimeError):
            adapter.prepare(self.source, self.output, checkpoint_every=1, stop_after=1)
        with self.assertRaisesRegex(ValueError, "another source/options/adapter"):
            adapter.prepare(self.source, self.output, limit_sites=2)
        self.write_source([site(position=999)])
        with self.assertRaisesRegex(ValueError, "another source/options/adapter"):
            adapter.prepare(self.source, self.output)

    def test_saved_partial_signal_tampering_is_detected_before_resume(self):
        self.write_source([site(position=244 + index) for index in range(3)])
        with self.assertRaises(RuntimeError):
            adapter.prepare(self.source, self.output, checkpoint_every=1, stop_after=1)
        staged_signals = self.output / ".preparing/data.json"
        original = staged_signals.read_bytes()
        changed = original.replace(b"125.0", b"126.0", 1)
        self.assertEqual(len(original), len(changed))
        self.assertNotEqual(original, changed)
        staged_signals.write_bytes(changed)
        with self.assertRaisesRegex(ValueError, "Partial original-signal identity mismatch"):
            adapter.prepare(self.source, self.output)

    def test_resume_after_interrupted_publication_keeps_both_files_consistent(self):
        objects = [site(), site(position=467)]
        self.write_source(objects)
        original_replace = adapter.os.replace

        def fail_second_published_file(source, destination):
            if Path(source).name == "data.info.publishing":
                raise OSError("Test interruption during publication")
            return original_replace(source, destination)

        with mock.patch.object(adapter.os, "replace", side_effect=fail_second_published_file):
            with self.assertRaisesRegex(OSError, "Test interruption during publication"):
                adapter.prepare(self.source, self.output)
        self.assertTrue((self.output / "data.json").exists())
        self.assertTrue((self.output / "data.info.publishing").exists())
        self.assertFalse((self.output / "complete.json").exists())
        receipt = adapter.prepare(self.source, self.output)
        self.assertTrue(receipt["resumed"])
        self.assert_original_values(objects)

    def test_unrelated_output_and_byte_index_corruption_are_rejected(self):
        self.write_source([site()])
        self.output.mkdir()
        (self.output / "data.json").write_text("do not overwrite", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "without an adapter checkpoint"):
            adapter.prepare(self.source, self.output)
        self.assertEqual((self.output / "data.json").read_text(), "do not overwrite")
        other = self.root / "safe"
        adapter.prepare(self.source, other)
        info = (other / "data.info").read_text(encoding="utf-8")
        (other / "data.info").write_text(info.replace(",0,", ",1,"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Noncontiguous"):
            adapter.audit_output(other / "data.json", other / "data.info")


if __name__ == "__main__":
    unittest.main()
