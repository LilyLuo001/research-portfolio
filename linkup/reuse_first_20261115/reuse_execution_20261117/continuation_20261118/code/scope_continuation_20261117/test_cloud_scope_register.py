"""Synthetic metadata only; no real research computation or cloud access."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import cloud_scope_register as m


def fixture():
    h = {'Job Descriptions': 'a' * 64, 'Job Records': 'b' * 64}
    loc = {'cluster': 'synthetic', 'path': '/synthetic/manifest.json', 'root': '/synthetic', 'rel': 'manifest.json', 'size': 1, 'status': 'verified'}
    metadata = []
    for ds, name, size in [('Job Descriptions', 'descriptions.parquet', 100), ('Job Records', 'records.parquet', 50)]:
        metadata.append({'sha256': h[ds], 'name': 'dewey-audit-manifest.json', 'locator': loc,
                         'value': {'describe': {'dataset_name': ds, 'dataset_version_timestamp': 'synthetic-v1'},
                                   'files': [{'file_name': name, 'file_size_bytes': size}],
                                   'metadata': {'total_files': 1, 'total_size': size}}})
    metadata.append({'sha256': 'c' * 64, 'name': 'job_records_manifest.tsv', 'locator': loc,
                     'value': [{'file': '/synthetic/records.parquet', 'bytes': '50', 'footer_rows': '12'}]})
    for i, schema in enumerate(['d' * 64, 'e' * 64]):
        metadata.append({'sha256': str(i) * 64, 'name': 'source_report.json', 'locator': loc,
                         'value': {'source': {'file': '/synthetic/records.parquet', 'bytes': 50, 'footer_rows': 12,
                                              'skinny_schema_sha256': schema}, 'status': 'complete', 'output_rows': 12,
                                   'outputs': [{'path': '/synthetic/v%d/part.parquet' % i, 'bytes': 20 + i, 'rows': 12, 'prefix': 'part'}]}})
        metadata.append({'sha256': str(i + 2) * 64, 'name': 'index_manifest.json', 'locator': loc,
                         'value': {'status': 'complete' if i == 0 else 'pilot_complete', 'rows': 12,
                                   'source_files': 1, 'available_source_files': 1, 'output_footer_rows': 12,
                                   'columns': ['JOB_HASH', 'RECORD_SOURCE_ROW'] if i == 0 else ['PILOT_ONLY'],
                                   'records_dir': '/synthetic/v%d' % i, 'record_source_file_mapping': 'output basename plus source row'}})
    metadata.append({'sha256': 'f' * 64, 'name': 'RECORDS_INVENTORY_PRIVATE.json', 'locator': loc,
                     'value': {'kind': 'records', 'bytes': 20, 'files': [{'path': '/inventory/part.parquet', 'bytes': 20, 'rows': 12}]}})
    catalog = [{'shard_id': 'synthetic-1', 'ad_rows': 7, 'ad_bytes': 5, 'ad_path': '/synthetic/base.parquet',
                'ad_sha256_from_original_receipt': '8' * 64, 'original_receipt_sha256': '9' * 64}]
    accounting = [{'shard_id': 'synthetic-1', 'canonical_US_ads': 7, 'source_bytes': 100, 'raw_rows': 10,
                   'catalog_receipt_sha256': '9' * 64}]
    return metadata, catalog, accounting, h


class ScopeRegisterTests(unittest.TestCase):
    def test_preserves_versions_without_double_count(self):
        a = m.build_register(*fixture())
        self.assertEqual(a['counts']['Records_source_metadata_keys'], 1)
        self.assertEqual(a['counts']['Records_source_footer_rows_once'], 12)
        self.assertEqual(a['counts']['Records_source_reports_preserved'], 2)
        self.assertEqual(len(a['records_sources'][0]['derived_versions']), 2)

    def test_pilot_columns_not_promoted(self):
        a = m.build_register(*fixture())
        self.assertNotIn('PILOT_ONLY', a['records_sources'][0]['identity_columns_declared_by_complete_index_manifests'])
        self.assertEqual(len(a['index_versions']), 2)

    def test_no_false_global_identity(self):
        a = m.build_register(*fixture())
        self.assertIsNone(a['counts']['global_unique_ads'])
        self.assertIsNone(a['counts']['global_per_field_missing_inputs'])
        self.assertEqual(a['counts']['exact_provider_Description_file_to_base_shard_bindings'], 0)
        self.assertEqual(a['base_shards'][0]['provider_file_binding'], 'not_available_in_combined_accounting')

    def test_inventory_metadata_source_mapping(self):
        a = m.build_register(*fixture())
        q = a['records_inventories'][0]['files'][0]
        self.assertEqual(q['source_binding_status'], 'unique_basename_size_rows_source_metadata_match')
        self.assertTrue(q['mapping_does_not_attest_output_content_SHA'])
        self.assertEqual(len(q['source_metadata_keys']), 1)

    def test_actual_inventory_field_spellings(self):
        args = list(fixture())
        args[0][-1]['value']['files'] = [{'path': '/inventory/part.parquet', 'relative_path': 'part.parquet',
                                        'size_bytes': 20, 'rows': 12, 'source_id': 'synthetic-source', 'sha256': '7' * 64}]
        a = m.build_register(*args)
        q = a['records_inventories'][0]['files'][0]
        self.assertEqual(q['source_binding_status'], 'unique_basename_size_rows_source_metadata_match')
        self.assertEqual(q['sha256'], '7' * 64)
        self.assertEqual(q['source_id'], 'synthetic-source')

    def test_description_existing_SHA_not_ad_identity(self):
        args = list(fixture())
        args[0].append({'sha256': '6' * 64, 'name': 'description_regions_disjoint_manifest.json', 'locator': {},
                        'value': {'union_count': 1, 'union_bytes': 100,
                                  'kunshan': [{'file_name': 'descriptions.parquet', 'path': '/synthetic/descriptions.parquet',
                                               'bytes': 100, 'sha256': '5' * 64}], 'wuzhen': []}})
        a = m.build_register(*args)
        self.assertEqual(a['counts']['Description_provider_files_with_existing_source_SHA_binding'], 1)
        self.assertEqual(a['providers'][0]['files'][0]['raw_source_sha256_from_existing_allocation'], '5' * 64)
        self.assertEqual(a['counts']['exact_provider_Description_file_to_base_shard_bindings'], 0)

    def test_missing_inventory_match_is_not_missing_input(self):
        args = list(fixture()); args[0][-1]['value']['files'][0]['path'] = '/unknown/other.parquet'
        a = m.build_register(*args)
        self.assertEqual(a['records_inventories'][0]['files'][0]['source_binding_status'], 'no_preserved_source_metadata_match')
        self.assertIsNone(a['counts']['global_per_field_missing_inputs'])

    def test_source_rows_nonconservation_rejected(self):
        args = list(fixture()); args[0][3]['value']['output_rows'] = 11
        with self.assertRaisesRegex(ValueError, 'derived_source_row_nonconservation'):
            m.build_register(*args)

    def test_partition_rows_nonconservation_rejected(self):
        args = list(fixture()); args[0][3]['value']['outputs'][0]['rows'] = 11
        with self.assertRaisesRegex(ValueError, 'derived_partition_row_nonconservation'):
            m.build_register(*args)

    def test_base_mismatch_rejected(self):
        args = list(fixture()); args[2][0]['canonical_US_ads'] = 8
        with self.assertRaisesRegex(ValueError, 'base_catalog_combined_accounting_mismatch'):
            m.build_register(*args)

    def test_signed_path_rejected(self):
        with self.assertRaisesRegex(ValueError, 'signed_or_fragment_path_not_allowed'):
            m.safe_path('https://example.invalid/file?' + 'sig=' + 'synthetic')

    def test_provider_missing_rejected(self):
        args = list(fixture()); args[0] = args[0][1:]
        with self.assertRaisesRegex(ValueError, 'pinned_provider_missing_or_duplicate'):
            m.build_register(*args)

    def test_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'public.json'
            m.write_json(p, {'synthetic': True})
            with self.assertRaisesRegex(ValueError, 'existing_output_preserved'):
                m.write_json(p, {'synthetic': False})
            self.assertEqual(json.loads(p.read_text()), {'synthetic': True})

    def test_metadata_sha_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); (p / 'metadata_cache').mkdir()
            d = 'a' * 64
            inv = [{'sha256': d, 'locator': {'rel': 'manifest.json', 'path': '/synthetic/manifest.json'}}]
            (p / 'VERIFIED_DELIVERY_METADATA_PRIVATE.json').write_text(json.dumps(inv))
            (p / 'metadata_cache' / (d + '.metadata')).write_text('{}')
            with self.assertRaisesRegex(ValueError, 'metadata_total_cap_or_SHA_mismatch'):
                m.loaded_metadata(p, {})


if __name__ == '__main__':
    unittest.main()
