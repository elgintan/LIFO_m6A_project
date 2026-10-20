"""Small scientific-contract checks, using synthetic sites only."""
import unittest
import numpy as np
import pandas as pd
from review_signal_cases import match_site, case_anchors, error_labels, pairs


class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.meta = pd.DataFrame([
            ['a', 10, 'g1', 0, 'AGGACTA', 'GGACT', 400, 1, .1, 'FN'],
            ['b', 20, 'g2', 0, 'AGGACTA', 'GGACT', 600, 1, .9, 'TP'],
            ['c', 30, 'g3', 0, 'TGGACTG', 'GGACT', 401, 1, .8, 'TP'],
            ['d', 40, 'g1', 0, 'AGGACTA', 'GGACT', 400, 1, .9, 'TP'],
            ['e', 50, 'g4', 1, 'AGGACTA', 'GGACT', 400, 1, .9, 'TP'],
            ['f', 60, 'g5', 0, 'AGGACTA', 'GGACT', 801, 1, .9, 'TP'],
        ], columns=['transcript_id', 'transcript_position', 'gene_id', 'fold_id', 'context',
                    'motif', 'n_reads', 'label', 'score', 'error'])

    def test_exact_context_precedes_coverage_and_excludes_gene_fold_and_depth(self):
        self.assertEqual(match_site(self.meta, 0, self.meta.error.eq('TP'), 200), (1, 'exact7'))

    def test_missing_exact_uses_central_context(self):
        self.meta.loc[1, 'n_reads'] = 801
        self.assertEqual(match_site(self.meta, 0, self.meta.error.eq('TP'), 200), (2, 'central5'))

    def test_no_crossfold_or_samegene_rescue(self):
        mask = self.meta.index.isin([3, 4, 5])
        self.assertEqual(match_site(self.meta, 0, mask, 200), (None, 'unmatched'))

    def test_high_depth_pool_enforced(self):
        self.meta.loc[0, 'n_reads'] = 200
        self.meta.loc[1, 'n_reads'] = 199
        self.meta.loc[2, 'n_reads'] = 400
        self.assertEqual(match_site(self.meta, 0, self.meta.error.eq('TP'), 200), (2, 'central5'))

    def test_reordering_does_not_change_match(self):
        target = match_site(self.meta.sample(frac=1, random_state=7), 0, self.meta.error.eq('TP'), 200)
        self.assertEqual(target, (1, 'exact7'))

    def test_median_fn_selection(self):
        self.meta.loc[0, 'score'] = .125
        extra = self.meta.iloc[[0]].copy()
        extra.index = [6]
        extra.loc[6, ['transcript_id', 'score']] = ['z', .375]
        meta = pd.concat([self.meta, extra])
        self.assertEqual(case_anchors(meta), [('GGACT', 0)])

    def test_no_fn_no_substitution(self):
        self.meta.loc[0, 'error'] = 'TP'
        self.assertEqual(case_anchors(self.meta), [('GGACT', None)])

    def test_reporting_boundary_and_invalid_scores(self):
        self.assertEqual(error_labels([1, 1, 0, 0], [.5, .49, .5, .49]).tolist(), ['TP', 'FN', 'FP', 'TN'])
        with self.assertRaises(ValueError):
            error_labels([0], [np.nan])

    def test_all_unmatched_has_explicit_empty_differences(self):
        meta = self.meta.loc[[0]]
        table, differences = pairs(meta)
        self.assertEqual(table.match_level.tolist(), ['unmatched'])
        self.assertTrue(differences.empty)
        self.assertIn('feature', differences)

    def test_zero_fn_has_explicit_empty_schemas(self):
        table, differences = pairs(self.meta.loc[self.meta.error.eq('TP')])
        self.assertTrue(table.empty and differences.empty)
        self.assertIn('match_level', table)


if __name__ == '__main__':
    unittest.main()
