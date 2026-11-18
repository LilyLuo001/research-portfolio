"""Synthetic original-stage semantics, not a second attempt at ad extraction."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import cloud_bind_description_sources_v2 as m

H='a'*64
P='b'*64
A='c'*64
B='d'*64
I='e'*64
L='f'*64
S='1'*64


def fixture():
    providers=[{'dataset':'Job Descriptions','selection_state':'selected_pinned_scope','manifest_sha256':P,
                'files':[{'raw_source_sha256_from_existing_allocation':H,'bytes':20,'file_name':'file.parquet','manifest_file_identity':I}]}]
    allocations=[{'metadata_sha256':A,'allocations':[{'source_sha256_from_existing_manifest':H,
                   'bytes':20,'file_name':'file.parquet','original_path':'/old/file.parquet','cluster':'fixture'}]}]
    row={'shard_id':'fixture-shard','publication_receipt_sha256':P,'source_bytes':20,'raw_rows':10,'canonical_US_ads':4}
    base={'ad_sha256':B,'ad_rows':4}
    receipt={'status':'published_verified','shard_id':'fixture-shard','shard_complete':{'status':'complete','accounting':{
        'shard_id':'fixture-shard','source_sha256_cached':H,'source_bytes':20,'source_file':'/old/file.parquet',
        'sidecar_sha256':S,'sidecar_source_files':['/old/file.parquet'],'row_conservation':True,'raw_rows':10,
        'sidecar_rows':10,'canonical_usa_rows':4},
        'lean_complete':{'status':'complete','source_sha256':L,'source_bytes':8,'source':'/work/canonical_usa.parquet','processed_rows':4}}}
    return providers,allocations,row,base,receipt


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.ps,self.als,self.row,self.base,self.receipt=fixture()
        self.a=self.receipt['shard_complete']['accounting'];self.lean=self.receipt['shard_complete']['lean_complete']

    def bind(self):
        p,a=m.build_lookups(self.ps,self.als)
        return m.bind_one(self.row,self.base,self.receipt,p,a)

    def test_distinct_raw_sidecar_and_lean_stages_are_correct(self):
        r=self.bind();self.assertEqual(r['status'],'source_provenance_bound')
        self.assertEqual(r['path_binding'],'identical_raw_full_path')
        self.assertFalse(r['source_hash_recomputed_in_this_run'])
        self.assertFalse(r['advertisement_row_identity_join_executed'])
        self.assertEqual(r['original_pipeline_bridge']['canonical_USA_lean_input_SHA'],L)
        self.assertEqual(r['original_pipeline_bridge']['disposition_sidecar_SHA'],S)

    def test_raw_source_relocation_preserved_not_claimed_exact_path(self):
        self.a['source_file']='/relocated/file.parquet';self.a['sidecar_source_files']=['/relocated/file.parquet']
        r=self.bind();self.assertEqual(r['status'],'source_provenance_bound')
        self.assertEqual(r['path_binding'],'identical_raw_basename_SHA_size_distinct_roots_preserved')

    def test_lean_SHA_difference_is_not_false_source_mismatch(self):
        self.lean['source_sha256']='2'*64
        self.assertEqual(self.bind()['status'],'source_provenance_bound')

    def test_lean_size_difference_is_not_false_source_mismatch(self):
        self.lean['source_bytes']=123
        self.assertEqual(self.bind()['status'],'source_provenance_bound')

    def test_original_accounting_size_conflict(self):
        self.row['source_bytes']=21
        self.assertEqual(self.bind()['reason'],'raw_accounting_size_disagrees')

    def test_provider_sha_conflict(self):
        self.ps[0]['files'][0]['raw_source_sha256_from_existing_allocation']='2'*64
        self.assertEqual(self.bind()['reason'],'no_provider_source_SHA_size_name_match')

    def test_provider_name_conflict(self):
        self.ps[0]['files'][0]['file_name']='different.parquet'
        self.assertEqual(self.bind()['reason'],'no_provider_source_SHA_size_name_match')

    def test_ambiguous_provider_identity_not_chosen(self):
        f=copy.deepcopy(self.ps[0]['files'][0]);f['manifest_file_identity']='2'*64
        self.ps[0]['files'].append(f)
        self.assertEqual(self.bind()['reason'],'provider_identity_ambiguous')

    def test_allocation_absence_not_invented(self):
        self.als[0]['allocations']=[]
        self.assertEqual(self.bind()['reason'],'no_allocation_source_SHA_size_name_match')

    def test_allocation_path_must_agree(self):
        self.als[0]['allocations'][0]['original_path']='/old/different.parquet'
        with self.assertRaisesRegex(ValueError,'allocation_original_path_basename_disagrees'):self.bind()

    def test_missing_source_field(self):
        del self.a['source_sha256_cached']
        self.assertEqual(self.bind()['reason'],'source_fields_missing_or_invalid')

    def test_shard_identity_conflict(self):
        self.receipt['shard_id']='other'
        self.assertEqual(self.bind()['reason'],'publication_shard_identity_mismatch')

    def test_nested_shard_identity_conflict(self):
        self.a['shard_id']='other'
        self.assertEqual(self.bind()['reason'],'accounting_shard_identity_mismatch')

    def test_no_source_mutation(self):
        before=copy.deepcopy((self.ps,self.als,self.row,self.base,self.receipt));self.bind()
        self.assertEqual(before,(self.ps,self.als,self.row,self.base,self.receipt))

    def test_signed_intermediate_path_rejected(self):
        self.lean['source']='/old/file.parquet?sig=secret'
        self.assertEqual(self.bind()['reason'],'source_fields_missing_or_invalid')

    def test_boolean_size_rejected(self):
        self.a['source_bytes']=True
        self.assertEqual(self.bind()['reason'],'source_fields_missing_or_invalid')

    def test_selected_provider_not_unique(self):
        self.ps.append(copy.deepcopy(self.ps[0]))
        with self.assertRaisesRegex(ValueError,'selected_Description_provider_not_unique'):self.bind()

    def test_duplicate_exact_allocation_declarations_preserved_once(self):
        self.als.append(copy.deepcopy(self.als[0]))
        self.assertEqual(len(self.bind()['allocation_sources']),1)

    def test_malformed_hash_rejected(self):
        with self.assertRaisesRegex(ValueError,'invalid_source_sha'):m.valid_sha('../path')

    def test_sidecar_SOURCE_FILE_binding_required(self):
        self.a['sidecar_source_files']=['/wrong/file.parquet']
        self.assertEqual(self.bind()['reason'],'sidecar_original_SOURCE_FILE_binding_disagrees')

    def test_sidecar_row_conservation_required(self):
        self.a['sidecar_rows']=9
        self.assertEqual(self.bind()['reason'],'original_raw_sidecar_row_conservation_disagrees')

    def test_canonical_lean_row_conservation_required(self):
        self.lean['processed_rows']=3
        self.assertEqual(self.bind()['reason'],'original_canonical_lean_base_row_conservation_disagrees')

    def test_canonical_base_row_conservation_required(self):
        self.base['ad_rows']=3
        self.assertEqual(self.bind()['reason'],'original_canonical_lean_base_row_conservation_disagrees')

    def test_completion_status_required(self):
        self.receipt['status']='queued'
        self.assertEqual(self.bind()['reason'],'original_stage_completion_status_not_verified')

    def test_empty_US_shard_valid_provenance(self):
        self.a['canonical_usa_rows']=0;self.lean['processed_rows']=0;self.base['ad_rows']=0;self.row['canonical_US_ads']=0
        self.assertEqual(self.bind()['status'],'source_provenance_bound')


class ReadTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.path=self.root/'fixture.json';self.data=b'{"synthetic": true}'
        self.path.write_bytes(self.data);self.h=hashlib.sha256(self.data).hexdigest()

    def tearDown(self):self.temp.cleanup()

    def test_SHA_verified_read(self):
        result,n=m.read_verified(self.path,self.h,100)
        self.assertEqual(n,len(self.data));self.assertEqual(result,{'synthetic':True})

    def test_changed_input_rejected(self):
        self.path.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'pinned_input_SHA_mismatch'):m.read_verified(self.path,self.h,100)

    def test_symlink_rejected(self):
        link=self.root/'link';link.symlink_to(self.path)
        with self.assertRaisesRegex(ValueError,'pinned_input_missing_or_not_regular'):m.read_verified(link,self.h,100)

    def test_byte_cap_rejected(self):
        with self.assertRaisesRegex(ValueError,'pinned_input_size_cap'):m.read_verified(self.path,self.h,1)

    def test_missing_input_rejected(self):
        with self.assertRaisesRegex(ValueError,'pinned_input_missing_or_not_regular'):m.read_verified(self.root/'missing',self.h,100)


if __name__=='__main__':unittest.main()
