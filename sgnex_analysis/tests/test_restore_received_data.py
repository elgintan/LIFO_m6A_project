"""Integrity/protected-evidence checks; temporary synthetic files only."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/restore_received_data.py'
spec = importlib.util.spec_from_file_location('restore_received', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class RestoreEvidence(unittest.TestCase):
    def fixture(self, root):
        source = root / 'source'
        source.mkdir()
        entries = []
        for path in sorted(mod.REQUIRED):
            target = source / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'synthetic integrity fixture, not biological data\n')
            entries.append({'path': path, 'bytes': target.stat().st_size, 'sha256': mod.sha(target)})
        (source / 'PACKAGE_MANIFEST.json').write_text(json.dumps({'files': entries}))
        return source

    def test_restore_reuse_and_protect_changed_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.fixture(root)
            with patch.object(mod, 'LOCAL_ROOT', root / 'outputs'):
                target = root / 'outputs' / 'received'
                first = mod.restore(source, target)
                self.assertFalse(any(r['reused'] for r in first['files']))
                second = mod.restore(source, target)
                self.assertTrue(all(r['reused'] for r in second['files']))
                original = target / next(iter(mod.REQUIRED))
                original.write_bytes(b'preserve this changed evidence')
                with self.assertRaisesRegex(ValueError, 'Existing evidence differs'):
                    mod.restore(source, target)
                self.assertEqual(original.read_bytes(), b'preserve this changed evidence')

    def test_refuse_corruption_before_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.fixture(root)
            (source / next(iter(mod.REQUIRED))).write_bytes(b'changed')
            with patch.object(mod, 'LOCAL_ROOT', root / 'outputs'):
                with self.assertRaisesRegex(ValueError, 'size/SHA256 mismatch'):
                    mod.restore(source, root / 'outputs' / 'received')
            self.assertFalse((root / 'outputs').exists())

    def test_refuse_escape_credentials_and_public_destination(self):
        for path in ['../secret', 'metadata/../../secret', 'C:/secret', 'metadata\\secret',
                     '/absolute', 'metadata/key.pem', 'metadata/token.keys']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                mod.safe_relative(path)
        with self.assertRaisesRegex(ValueError, 'Destination must be'):
            mod.restore('unused', SCRIPT.parent)


if __name__ == '__main__':
    unittest.main(verbosity=2)
