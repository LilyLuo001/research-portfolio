"""Synthetic-only tests: no Azure, private records, runtime install or model."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import cloud_bind_description_sources as m

H='a'*64
P='b'*64
A='c'*64
B='d'*64
I='e'*64


def fixture():
    providers=[{'dataset':'Job Descriptions','selection_state':'selected_pinned_scope','manifest_sha256':P,
                'files':[{'raw_source_sha256_from_existing_allocation':H,'bytes':20,'file_name':'file.parquet','manifest_file_identity':I}]}]
    allocations=[{'metadata_sha256':A,'allocations':[{'source_sha256_from_existing_manifest':H,
                   'bytes':20,'file_name':'file.parquet','original_path':'/old/file.parquet','cluster':'fixture'}]}]
    row={'shard_id':'fixture-shard','publication_receipt_sha256':P,'source_bytes':20}
    base={'ad_sha256':B}
    receipt={'shard_id':'fixture-shard','shard_complete':{'accounting':{
        'shard_id':'fixture-shard','source_sha256_cached':H,'source_bytes':20,'source_file':'/old/file.parquet'},
        'lean_complete':{'source_sha256':H,'source_bytes':20,'source':'/old/file.parquet'}}}
    return providers,allocations,row,base,receipt


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.ps,self.als,self.row,self.base,self.receipt=fixture()

    def bind(self):
        p,a=m.build_lookups(self.ps,self.als)
        return m.bind_one(self.row,self.base,self.receipt,p,a)

    def test_exact_source_binding(self):
        r=self.bind();self.assertEqual(r['status'],'source_provenance_bound')
        self.assertEqual(r['path_binding'],'identical_full_path')
        self.assertFalse(r['source_hash_recomputed_in_this_run'])
        self.assertFalse(r['advertisement_row_identity_join_executed'])

    def test_distinct_root_is_not_claimed_exact_path(self):
        self.receipt['shard_complete']['lean_complete']['source']='/new/file.parquet'
        r=self.bind();self.assertEqual(r['status'],'source_provenance_bound')
        self.assertEqual(r['path_binding'],'identical_basename_SHA_size_distinct_roots_preserved')
        self.assertEqual(r['lean_source_path'],'/new/file.parquet')

    def test_receipt_hash_conflict(self):
        self.receipt['shard_complete']['lean_complete']['source_sha256']='f'*64
        self.assertEqual(self.bind()['reason'],'cached_source_sections_disagree')

    def test_receipt_size_conflict(self):
        self.receipt['shard_complete']['lean_complete']['source_bytes']=21
        self.assertEqual(self.bind()['reason'],'cached_source_sections_disagree')

    def test_receipt_name_conflict(self):
        self.receipt['shard_complete']['lean_complete']['source']='/old/other.parquet'
        self.assertEqual(self.bind()['reason'],'cached_source_sections_disagree')

    def test_original_accounting_size_conflict(self):
        self.row['source_bytes']=21
        self.assertEqual(self.bind()['reason'],'cached_source_sections_disagree')

    def test_provider_sha_conflict(self):
        self.ps[0]['files'][0]['raw_source_sha256_from_existing_allocation']='f'*64
        self.assertEqual(self.bind()['reason'],'no_provider_source_SHA_size_name_match')

    def test_ambiguous_provider_identity_not_chosen(self):
        f=copy.deepcopy(self.ps[0]['files'][0]);f['manifest_file_identity']='f'*64
        self.ps[0]['files'].append(f)
        self.assertEqual(self.bind()['reason'],'provider_identity_ambiguous')

    def test_allocation_absence_not_invented(self):
        self.als[0]['allocations']=[]
        self.assertEqual(self.bind()['reason'],'no_allocation_source_SHA_size_name_match')

    def test_allocation_path_must_agree(self):
        self.als[0]['allocations'][0]['original_path']='/old/different.parquet'
        with self.assertRaisesRegex(ValueError,'allocation_original_path_basename_disagrees'):self.bind()

    def test_missing_source_field(self):
        del self.receipt['shard_complete']['accounting']['source_sha256_cached']
        self.assertEqual(self.bind()['reason'],'source_fields_missing_or_invalid')

    def test_shard_identity_conflict(self):
        self.receipt['shard_id']='other'
        self.assertEqual(self.bind()['reason'],'publication_shard_identity_mismatch')

    def test_nested_shard_identity_conflict(self):
        self.receipt['shard_complete']['accounting']['shard_id']='other'
        self.assertEqual(self.bind()['reason'],'accounting_shard_identity_mismatch')

    def test_no_source_mutation(self):
        before=copy.deepcopy((self.ps,self.als,self.row,self.base,self.receipt));self.bind()
        self.assertEqual(before,(self.ps,self.als,self.row,self.base,self.receipt))

    def test_signed_path_rejected(self):
        self.receipt['shard_complete']['lean_complete']['source']='/old/file.parquet?sig=secret'
        self.assertEqual(self.bind()['reason'],'source_fields_missing_or_invalid')

    def test_boolean_size_rejected(self):
        self.receipt['shard_complete']['accounting']['source_bytes']=True
        self.assertEqual(self.bind()['reason'],'source_fields_missing_or_invalid')

    def test_selected_provider_not_unique(self):
        self.ps.append(copy.deepcopy(self.ps[0]))
        with self.assertRaisesRegex(ValueError,'selected_Description_provider_not_unique'):self.bind()

    def test_duplicate_exact_allocation_declarations_preserved_once(self):
        self.als.append(copy.deepcopy(self.als[0]))
        self.assertEqual(len(self.bind()['allocation_sources']),1)

    def test_malformed_hash_rejected(self):
        with self.assertRaisesRegex(ValueError,'invalid_source_sha'):m.valid_sha('../path')


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
