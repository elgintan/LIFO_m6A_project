"""Small synthetic checks only; no real cache/model/labels are loaded."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import torch

import read_depth_stability as subject


class StabilityChecks(unittest.TestCase):
    def test_nested_uniform_prefix_and_order_independence(self):
        small=subject.nested_indices(200,20,2026,'transcript',10)
        medium=subject.nested_indices(200,50,2026,'transcript',10)
        large=subject.nested_indices(200,100,2026,'transcript',10)
        np.testing.assert_array_equal(small,subject.nested_indices(200,20,2026,'transcript',10))
        self.assertEqual(len(set(small)),20)
        self.assertTrue(set(small)<=set(medium)<=set(large))
        self.assertTrue(np.all(np.diff(large)>0))
        self.assertFalse(np.array_equal(small,subject.nested_indices(200,20,2027,'transcript',10)))
        np.testing.assert_array_equal(subject.nested_indices(100,100,2026,'t',1),np.arange(100))
        for depth in (0,201,-1):
            with self.assertRaises(ValueError):subject.nested_indices(200,depth,2026,'t',1)

    def test_trial_cohort_is_label_free_and_matched(self):
        rows=[]
        for fold in range(5):
            for site in range(8):
                rows.append(dict(transcript_id=f't{fold}_{site}',transcript_position=site,gene_id=f'g{fold}_{site//2}',
                    fold_id=fold,label=site%2,n_reads=99 if site==0 else 100+site,context='AAGACCA',baseline_score=.2))
        meta=pd.DataFrame(rows)
        first=subject.select_cohort(meta,True,2,3)
        changed=meta.copy();changed['label']=1-changed.label
        second=subject.select_cohort(changed,True,2,3)
        np.testing.assert_array_equal(first.site_index,second.site_index)
        self.assertTrue(first.coverage.ge(100).all())
        self.assertEqual(set(first.fold_id),set(range(5)))
        self.assertTrue(first.groupby('fold_id').size().le(3).all())

    def test_both_branches_recomputed_and_bag_only_preserved(self):
        raw=np.arange(100*9,dtype=np.float32).reshape(100,9)/1000
        summary=subject.summarise(raw)[None,:]
        cache=SimpleNamespace(bag=lambda i:raw,raw_summary=summary,summary=subject.network.summary_transform(summary),seq=np.array([[0,0,2,0,1,1,0]],dtype=np.int64))
        meta=pd.DataFrame([dict(transcript_id='t',transcript_position=1)])
        selected=subject.nested_indices(100,20,2026,'t',1)
        captured=[]
        class Recorder:
            def __call__(self,reads,mask,sequence,summaries,extra=None):
                captured.append((reads.numpy(),mask.numpy(),summaries.numpy()))
                return torch.zeros(len(reads))
        spec=dict(perturbation='both',depth=20,repeat_seed=2026)
        scores,hashes,_=subject.score_batch(Recorder(),cache,np.array([0]),meta,spec)
        np.testing.assert_array_equal(captured[-1][0][0],subject.network.read_transform(raw[selected]))
        np.testing.assert_array_equal(captured[-1][2],subject.network.summary_transform(subject.summarise(raw[selected])[None,:]))
        np.testing.assert_array_equal(scores,[.5]);self.assertEqual(len(hashes[0]),64)
        spec['perturbation']='bag-only'
        subject.score_batch(Recorder(),cache,np.array([0]),meta,spec)
        np.testing.assert_array_equal(captured[-1][2],cache.summary)
        self.assertFalse(np.array_equal(cache.summary,subject.network.summary_transform(subject.summarise(raw[selected])[None,:])))

    def test_single_class_has_no_fabricated_auc(self):
        result=subject.metrics_or_undefined([0,0],[.1,.8])
        self.assertFalse(result['ranking_metrics_defined']);self.assertIsNone(result['selection_score'])
        self.assertEqual((result['tn'],result['fp']),(1,1))

    def test_depth100_on_100_reads_matches_recomputed_all_inputs(self):
        raw=np.arange(900,dtype=np.float32).reshape(100,9)/1000
        summary=subject.summarise(raw)[None,:]
        cache=SimpleNamespace(bag=lambda i:raw,raw_summary=summary,summary=subject.network.summary_transform(summary),seq=np.zeros((1,7),dtype=np.int64))
        meta=pd.DataFrame([dict(transcript_id='t',transcript_position=1)])
        captured=[]
        class Recorder:
            def __call__(self,*tensors):
                captured.append([None if x is None else x.numpy().copy() for x in tensors])
                return torch.zeros(1)
        subject.score_batch(Recorder(),cache,np.array([0]),meta,dict(perturbation='both',depth=100,repeat_seed=2026))
        subject.score_batch(Recorder(),cache,np.array([0]),meta,dict(perturbation='all-recomputed',depth='all'))
        for left,right in zip(captured[0][:4],captured[1][:4]):
            np.testing.assert_array_equal(left,right)

    def test_real_network_forward_equivalence_on_synthetic_float32_bag(self):
        raw=np.arange(900,dtype=np.float32).reshape(100,9)/1000
        summary=subject.summarise(raw)[None,:]
        cache=SimpleNamespace(bag=lambda i:raw,off=np.array([0,100]),raw_summary=summary,
            summary=subject.network.summary_transform(summary),seq=np.zeros((1,7),dtype=np.int64))
        meta=pd.DataFrame([dict(transcript_id='t',transcript_position=1)])
        norm={'read_mean':[0.]*9,'read_sd':[1.]*9,'summary_mean':[0.]*63,'summary_sd':[1.]*63}
        torch.manual_seed(42)
        model=subject.network.SiteModel(dict(width=8,dropout=0.,pool='attention',context_mode='none',summary_n=63),norm)
        model.eval()
        cached,_,_=subject.score_batch(model,cache,np.array([0]),meta,dict(perturbation='all-cache',depth='all'))
        recomputed,_,_=subject.score_batch(model,cache,np.array([0]),meta,dict(perturbation='all-recomputed',depth='all'))
        hundred,_,_=subject.score_batch(model,cache,np.array([0]),meta,dict(perturbation='both',depth=100,repeat_seed=2026))
        np.testing.assert_array_equal(cached,recomputed)
        np.testing.assert_allclose(hundred,recomputed,rtol=0,atol=1e-6)

    def test_padded_budget_and_prespecified_condition_count(self):
        coverage=np.array([100,150,200])
        batches=list(subject.batch_indices(np.arange(3),coverage,'all',64,250))
        self.assertEqual([len(b) for b in batches],[1,1,1])
        self.assertEqual(len(subject.condition_specs()),130)
        self.assertEqual(sum(s['depth']=='all' for s in subject.condition_specs()),10)
        with self.assertRaises(ValueError):list(subject.batch_indices([2],coverage,'all',64,199))

    def test_immutable_settings_and_completed_hash_guard(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'settings.json'
            subject.immutable_json(path,{'signature':'first'})
            subject.immutable_json(path,{'signature':'first'})
            with self.assertRaisesRegex(ValueError,'differ'):
                subject.immutable_json(path,{'signature':'changed'})
            self.assertEqual(path.read_text().count('first'),1)

    def test_wrong_stage_or_preprocessing_split_rejected(self):
        recipe={'config':{'context_mode':'none'},'identity':{'data0':'fixed'},'seed':2026,
                'max_epochs':20,'patience':5,'batch_size':256,'threads':4}
        audit={'populations':{'refit':{'sites':8,'indices_sha256':'four-training-groups'},
                             'initial_fit':{'indices_sha256':'initial'},'inner_validation':{'indices_sha256':'inner'}}}
        signature=subject._fit_signature(recipe,0,audit,'cv_refit',9)
        complete=dict(signature=signature,seed=2126,epochs_completed=9,train_sites=8,validation_sites=0,fit_indices_sha256='four-training-groups')
        bundle=dict(kind='context_reference_v1',stage='cv_refit',config=recipe['config'],input_fingerprints=recipe['identity'],
                    context_reference=None,seed=2126,epoch=9,fit_signature=signature,norm={'fit_indices_sha256':'four-training-groups','fit_sites':8})
        subject.validate_bundle(bundle,complete,recipe,0,audit,9)
        for change in ({'stage':'final_data0'},{'norm':{'fit_indices_sha256':'includes-heldout','fit_sites':8}},{'input_fingerprints':{'data1':'wrong'}}):
            bad=copy.deepcopy(bundle);bad.update(change)
            with self.assertRaises(ValueError):subject.validate_bundle(bad,complete,recipe,0,audit,9)

    def test_completed_condition_resumes_and_hash_change_is_refused(self):
        raw=np.arange(900,dtype=np.float32).reshape(100,9)/1000
        summary=subject.summarise(raw)[None,:]
        cache=SimpleNamespace(bag=lambda i:raw,raw_summary=summary,summary=subject.network.summary_transform(summary),seq=np.zeros((1,7),dtype=np.int64))
        meta=pd.DataFrame([dict(transcript_id='t',transcript_position=1,gene_id='g0',fold_id=0,label=0,
                               n_reads=100,context='AAGACCA',baseline_score=.5)])
        cohort=subject.select_cohort(pd.concat([meta.assign(fold_id=f,gene_id=f'g{f}') for f in range(5)],ignore_index=True))
        cohort=cohort.loc[cohort.fold_id.eq(0),subject.COHORT_COLUMNS].reset_index(drop=True)
        experiment=dict(signature='synthetic-experiment',cohort_sha256='synthetic-cohort',models=[{'model_sha256':'synthetic-model'}])
        args=SimpleNamespace(batch_size=64,max_padded_reads=65536)
        specification=dict(condition_id='fold0/both/depth20/seed2026',fold_id=0,perturbation='both',depth=20,repeat_id=0,repeat_seed=2026)
        class Constant:
            def __call__(self,*tensors):return torch.zeros(len(tensors[0]))
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)
            first=subject.run_condition(output,experiment,cohort,cache,meta,Constant(),specification,args)
            with patch.object(subject,'score_batch',side_effect=AssertionError('Completed condition must not rerun inference')):
                second=subject.run_condition(output,experiment,cohort,cache,meta,Constant(),specification,args)
            self.assertEqual(first,second)
            saved=output/'conditions'/specification['condition_id']/'predictions.csv'
            saved.write_text(saved.read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'Completed condition changed'):
                subject.run_condition(output,experiment,cohort,cache,meta,Constant(),specification,args)


if __name__=='__main__':
    unittest.main(verbosity=2)
