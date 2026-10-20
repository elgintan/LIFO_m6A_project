"""Scientific-contract checks of delegation, read limits and real recovery."""
from pathlib import Path
from types import SimpleNamespace
import json
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import torch
import train_read_cap as cap
from test_train import SyntheticCache
from data import summarise
from model import summary_transform


class LargerReadCache(SyntheticCache):
    def __init__(self):
        super().__init__()
        self.bags = [np.tile(values, (60, 1))[:[20, 40, 80, 160][i % 4]]
                     for i, values in enumerate(self.bags)]
        self.off = np.r_[0, np.cumsum([len(x) for x in self.bags])]
        self.raw_summary = np.stack([summarise(x) for x in self.bags])
        self.summary = summary_transform(self.raw_summary)


class CapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.cache = LargerReadCache()

    def recipe(self):
        return dict(config=dict(cap.fitting.BASE, context_mode='none', min_sites=30),
                    max_epochs=20, patience=5, seed=2026, batch_size=256, threads=4, smoke=False)

    def test_config_only_changes_cap(self):
        recipe = self.recipe()
        candidate = cap.configuration(recipe)
        self.assertEqual({k for k in candidate if candidate[k] != recipe['config'][k]}, {'cap'})
        self.assertEqual(candidate['cap'], 128)
        self.assertEqual(recipe['config']['cap'], 32)
        with self.assertRaises(ValueError):
            cap.configuration(dict(recipe, batch_size=128))

    def test_training_bounds_summary_and_allread_assessment(self):
        cache = self.cache
        indices = np.arange(4)
        reads, mask, seq, summary, extra = cap.fitting.batch(cache, indices, None,
            np.random.default_rng(2026), cap=128)
        self.assertEqual(mask.sum(1).tolist(), [20, 40, 80, 128])
        np.testing.assert_array_equal(summary, cache.summary[indices])
        all_reads = cap.fitting.batch(cache, indices, None)
        self.assertEqual(all_reads[1].sum(1).tolist(), [20, 40, 80, 160])
        np.testing.assert_array_equal(all_reads[3], cache.summary[indices])
        with torch.no_grad():
            self.assertEqual(extra, None)

    def test_cap32_delegation_is_tensor_identical_to_original(self):
        cache = self.cache
        population = np.arange(len(cache.keys))
        config = cap.configuration(self.recipe(), 32)
        with tempfile.TemporaryDirectory(prefix='.cap_eq_', dir=Path(__file__).parent) as temp:
            root = Path(temp)
            common = dict(phase='smoke', max_epochs=2, patience=5, seed=2026,
                          batch_size=16, threads=1, outer_folds=[0])
            direct = SimpleNamespace(**common, output_dir=root/'direct')
            wrapped = SimpleNamespace(**common, output_dir=root/'wrapped')
            identity = dict(synthetic=True)
            cap.fitting.run_cv(cache, cache.keys, population, config, direct, identity)
            cap.delegate_cv(cache, cache.keys, population, config, wrapped, identity)
            for stage in ['inner', 'refit']:
                a = torch.load(root/f'direct/smoke/none/fold0/{stage}/last.pt', weights_only=False)
                b = torch.load(root/f'wrapped/smoke/none/fold0/{stage}/last.pt', weights_only=False)
                self.assertEqual(a['norm'], b['norm'])
                self.assertEqual(a['signature'], b['signature'])
                self.assertEqual([r['loss'] for r in a['history']], [r['loss'] for r in b['history']])
                for name in a['state_dict']:
                    torch.testing.assert_close(a['state_dict'][name], b['state_dict'][name], rtol=0, atol=0)
            self.assertEqual((root/'direct/smoke/none/fold0/predictions.csv').read_bytes(),
                             (root/'wrapped/smoke/none/fold0/predictions.csv').read_bytes())

    def test_cap128_real_interrupted_resume_and_source_rejection(self):
        cache = self.cache
        with tempfile.TemporaryDirectory(prefix='.cap_resume_', dir=Path(__file__).parent) as temp:
            root = Path(temp)
            config = cap.configuration(self.recipe())
            arguments = dict(cache=cache, y=cache.keys.label.to_numpy(), indices=np.arange(24),
                validation=np.arange(24, 40), config=config, seed=2026, max_epochs=2,
                patience=5, batch_size=8, stage='smoke', identity=dict(wrapper='fixed'))
            cap.fitting.run_fit(directory=root/'full', **arguments)
            original = cap.fitting.atomic_torch
            def interrupt(path, payload):
                original(path, payload)
                if Path(path).name == 'last.pt' and payload['epoch'] == 1:
                    raise KeyboardInterrupt('synthetic epoch-boundary interruption')
            with patch.object(cap.fitting, 'atomic_torch', side_effect=interrupt):
                with self.assertRaises(KeyboardInterrupt):
                    cap.fitting.run_fit(directory=root/'resume', **arguments)
            changed = dict(arguments, identity=dict(wrapper='changed'))
            with self.assertRaisesRegex(ValueError, 'Checkpoint settings/source/split differ'):
                cap.fitting.run_fit(directory=root/'resume', **changed)
            cap.fitting.run_fit(directory=root/'resume', **arguments)
            a = torch.load(root/'full/last.pt', weights_only=False)
            b = torch.load(root/'resume/last.pt', weights_only=False)
            for name in a['state_dict']:
                torch.testing.assert_close(a['state_dict'][name], b['state_dict'][name], rtol=0, atol=0)
            with patch.object(cap.fitting, 'fit_norm', side_effect=AssertionError('must reuse completed fit')):
                cap.fitting.run_fit(directory=root/'resume', **arguments)

    def test_lock_refuses_live_duplicate_and_releases(self):
        with tempfile.TemporaryDirectory(prefix='.cap_lock_', dir=Path(__file__).parent) as temp:
            path = Path(temp)/'cv.lock'
            with cap.process_lock(path):
                with self.assertRaisesRegex(ValueError, 'active process'):
                    with cap.process_lock(path):
                        pass
            self.assertFalse(path.exists())

    def test_stale_lock_is_preserved(self):
        with tempfile.TemporaryDirectory(prefix='.cap_stale_', dir=Path(__file__).parent) as temp:
            path = Path(temp)/'cv.lock'
            path.write_text(json.dumps(dict(pid=cap.os.getpid(), process_created=0, token='old')))
            with cap.process_lock(path):
                pass
            self.assertEqual(len(list(path.parent.glob('cv.lock.stale.*.json'))), 1)


if __name__ == '__main__':
    unittest.main()
