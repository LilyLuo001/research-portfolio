"""Independent synthetic-only driver smoke tests; no Azure, models, or private data."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

import cloud_materialize as driver
from adapter import EXP, ENTRY, DUTY


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synthetic_review(context):
    return {'context_sha256': context, 'document_status': 'reviewed_full',
            'experience_outcomes': {x: 'not_mentioned' for x in EXP},
            'experience_clauses': [], 'entry_outcomes': {x: 'not_mentioned' for x in ENTRY},
            'entry_items': [], 'responsibility_outcomes': {x: 'not_mentioned' for x in DUTY},
            'responsibility_items': [], 'technology_inventory_status': 'not_mentioned_after_full_review',
            'technology_items': [], 'qualification_alternatives': []}


def synthetic_masks(document):
    result = {'document_status': document['document_status'],
              'technology_inventory_status': document['technology_inventory_status']}
    for family in ['experience_outcomes', 'entry_outcomes', 'responsibility_outcomes']:
        result.update({family + '.' + k: v for k, v in document[family].items()})
    return result


class DriverSmokeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'migration'
        self.output = self.root / 'reuse_execution_20261117/run001'
        self.output.mkdir(parents=True)
        self.source = self.root / 'synthetic_source.sqlite'
        self.rec = self.output / 'RECONCILED_STATE_V3_PRIVATE.sqlite'
        self.state = self.root / 'execution_20261116/run001/AZURE_RESEARCH_STATE.json'
        self.exclusions = self.root / 'SYNTHETIC_EXCLUSIONS_PRIVATE.json'
        self.allowed = ['synthetic-context-wide', 'synthetic-admask-only', 'synthetic-no-reinfer-only']
        self.denied = ['synthetic-denied-reconciliation', 'synthetic-denied-runtime', 'synthetic-denied-protected']
        db = sqlite3.connect(self.source)
        db.executescript('''
          CREATE TABLE document(d TEXT PRIMARY KEY,h TEXT,k TEXT,asset TEXT,source_sha TEXT,source_ordinal INTEGER,original_accepted INTEGER,document_json TEXT);
          CREATE TABLE field_mask(h TEXT,k TEXT,family TEXT,status TEXT,asset TEXT,source TEXT);
          CREATE TABLE ad(k TEXT,h TEXT,source TEXT,PRIMARY KEY(k,h,source));
          CREATE TABLE protected(h TEXT PRIMARY KEY);
          CREATE TABLE do_not_reinfer_context(h TEXT PRIMARY KEY,reason TEXT,source TEXT);
          CREATE TABLE metadata_resolution(k TEXT PRIMARY KEY,created TEXT,status TEXT);
          CREATE TABLE metadata_evidence(k TEXT,source_sha TEXT,row_ordinal INTEGER,source_conflict INTEGER,payload_json TEXT);
        ''')
        self.keys = {}
        for i, context in enumerate(self.allowed + self.denied):
            key = json.dumps(['synthetic-job-' + str(i), 'synthetic-file', str(i), str(i)])
            self.keys[context] = key
            asset = 'Pro' if i != 2 else 'Kimi_saved_unverified'
            original_accepted = int(i != 2)
            payload = json.dumps(synthetic_review(context)) if context in self.allowed else 'INVALID_DENIED_JSON_MUST_NOT_BE_ADAPTED'
            db.execute('INSERT INTO document VALUES(?,?,?,?,?,?,?,?)',
                       ('synthetic-document-' + str(i), context, '', asset, 'synthetic-source-' + str(i), 1, original_accepted, payload))
            db.execute('INSERT INTO ad VALUES(?,?,?)', (key, context, 'synthetic-original-binding'))
            db.execute('INSERT INTO metadata_resolution VALUES(?,?,?)', (key, '2021-01-01', 'matched_consistent'))
            db.execute('INSERT INTO metadata_evidence VALUES(?,?,?,?,?)', (key, 'synthetic-metadata-source', i + 1, 0, json.dumps({'COUNTRY': 'US'})))
            if context in self.allowed:
                for family, state in synthetic_masks(synthetic_review(context)).items():
                    # The second context has ONLY an ad-key mask. It cannot qualify
                    # a context-wide document that can reach other ads.
                    mask_key = key if i == 1 else ''
                    db.execute('INSERT INTO field_mask VALUES(?,?,?,?,?,?)',
                               (context, mask_key, family, state, asset, 'synthetic-source-' + str(i)))
        # Keep duplicate provenance bindings, but do not duplicate analysis rows.
        first = self.allowed[0]
        db.execute('INSERT INTO ad VALUES(?,?,?)', (self.keys[first], first, 'synthetic-second-binding-source'))
        other_key = json.dumps(['synthetic-another-job', 'synthetic-file', '100', '100'])
        db.execute('INSERT INTO ad VALUES(?,?,?)', (other_key, first, 'synthetic-original-binding'))
        db.execute('INSERT INTO metadata_resolution VALUES(?,?,?)', (other_key, '2022-02-02', 'matched_consistent'))
        db.execute('INSERT INTO protected VALUES(?)', (self.denied[2],))
        db.execute('INSERT INTO do_not_reinfer_context VALUES(?,?,?)',
                   (self.allowed[2], 'frozen_validation_failed_preserve_output', 'synthetic-original-failure'))
        db.commit(); db.close()
        db = sqlite3.connect(self.rec)
        db.execute('CREATE TABLE context_state(h TEXT PRIMARY KEY,original_state TEXT,carrier_present INTEGER,original_protected INTEGER,reuse_excluded INTEGER,audit_resolution TEXT)')
        for context in self.allowed + self.denied:
            db.execute('INSERT INTO context_state VALUES(?,?,?,?,?,?)',
                       (context, 'saved_unverified' if context == self.allowed[2] else 'accepted_original_scope',
                        1, int(context == self.denied[2]), int(context == self.denied[0]), 'synthetic_fixture'))
        db.commit(); db.close()
        dump(self.exclusions, {'context_sha256': [self.denied[1]]})
        dump(self.state, {'database_relative_to_migration': str(self.source.relative_to(self.root)),
                         'database_sha256': digest(self.source),
                         'runtime_exclusions_relative_to_migration': str(self.exclusions.relative_to(self.root))})
        dictionary_source = Path(__file__).resolve().parents[2] / 'variable_dictionary_20261117_v1/VARIABLE_DICTIONARY_PUBLIC.json'
        self.dictionary = self.output / 'VARIABLE_DICTIONARY_PUBLIC.json'
        self.dictionary.write_bytes(dictionary_source.read_bytes())  # Public definitions only.
        dump(self.output / 'AUTHORIZATION_PUBLIC.json', {'step1_execution_authorized': True, 'model_calls_allowed_in_step1': 0})
        self.pins = {'source_database_sha256': digest(self.source),
                     'reconciliation_database_sha256': digest(self.rec),
                     'runtime_exclusions_sha256': digest(self.exclusions),
                     'code_and_contract': {'VARIABLE_DICTIONARY_PUBLIC.json': digest(self.dictionary)}}
        dump(self.output / 'RUN_PINS_PUBLIC.json', self.pins)
        self.before = {p: digest(p) for p in [self.source, self.rec, self.state, self.exclusions]}

    def tearDown(self):
        self.temp.cleanup()

    def run_driver(self):
        called = []
        original = driver.adapt_document
        def spy(document, **kwargs):
            called.append(kwargs['context_sha256'])
            self.assertNotIn(kwargs['context_sha256'], self.denied)
            return original(document, **kwargs)
        with mock.patch.object(driver, 'ROOT', self.root), mock.patch.object(driver, 'OUT', self.output), mock.patch.object(driver, 'adapt_document', spy):
            driver.main()
        return called

    def test_end_to_end_readonly_denial_masks_and_deduplicated_created(self):
        self.assertEqual(sorted(self.run_driver()), sorted(self.allowed))
        self.assertEqual(self.before, {p: digest(p) for p in self.before})
        result = self.output / 'LINKUP_REUSED_VARIABLES_V1_PRIVATE.sqlite'
        db = sqlite3.connect(result)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM source_document').fetchone()[0], 3)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM source_document WHERE h=?', (self.allowed[2],)).fetchone()[0], 1)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM variable_value WHERE h=? AND eligible_original_scope=1', (self.allowed[1],)).fetchone()[0], 0)
        self.assertGreater(db.execute('SELECT COUNT(*) FROM variable_value WHERE h=? AND eligible_original_scope=1', (self.allowed[0],)).fetchone()[0], 0)
        self.assertIsNone(db.execute('SELECT id,ad_key,COUNT(*) FROM analysis_values_with_created GROUP BY id,ad_key HAVING COUNT(*)>1').fetchone())
        pairs = db.execute('SELECT DISTINCT ad_key,created FROM analysis_values_with_created WHERE context_fingerprint=?', (self.allowed[0],)).fetchall()
        self.assertEqual(len(pairs), 2)
        self.assertEqual({x[1] for x in pairs}, {'2021-01-01', '2022-02-02'})
        self.assertEqual(db.execute('SELECT COUNT(*) FROM ad_binding WHERE h=?', (self.allowed[0],)).fetchone()[0], 3)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM variable_value WHERE workflow_state=? AND h=?', ('saved_unverified', self.allowed[2])).fetchone()[0],
                         db.execute('SELECT COUNT(*) FROM variable_value WHERE h=?', (self.allowed[2],)).fetchone()[0])
        db.close()
        report = json.loads((self.output / 'MATERIALIZATION_PUBLIC.json').read_text())
        self.assertTrue(all(report['checks'].values()))
        self.assertEqual(report['excluded_source_documents'], 3)
        self.assertEqual(report['new_model_calls'], 0)
        self.assertEqual(report['new_production_accepted'], 0)
        self.assertIsNone(report['full_delivery_missing_unique_inputs'])
        coverage = json.loads((self.output / 'VARIABLE_COVERAGE_PUBLIC.json').read_text())
        self.assertEqual(len(coverage['variables']), 89)
        for item in coverage['variables']:
            if not item['variable_key'].startswith(('lk.exp.', 'lk.duty.', 'lk.entry.', 'lk.tech.', 'lk.qual.', 'lk.task.')):
                self.assertIsNone(item['eligible_carrier_contexts_without_projection'])
        old_result_sha = digest(result)
        with self.assertRaisesRegex(AssertionError, 'existing_output_preserved_no_duplicate_run'):
            self.run_driver()
        self.assertEqual(digest(result), old_result_sha)

    def test_reconciliation_pin_mismatch_fails_before_output(self):
        self.pins['reconciliation_database_sha256'] = 'bad-synthetic-pin'
        dump(self.output / 'RUN_PINS_PUBLIC.json', self.pins)
        with self.assertRaisesRegex(AssertionError, 'reconciliation_pin_changed'):
            self.run_driver()
        self.assertFalse((self.output / 'LINKUP_REUSED_VARIABLES_V1_PRIVATE.sqlite').exists())

    def test_runtime_exclusion_pin_mismatch_fails_before_output(self):
        self.pins['runtime_exclusions_sha256'] = 'bad-synthetic-pin'
        dump(self.output / 'RUN_PINS_PUBLIC.json', self.pins)
        with self.assertRaisesRegex(AssertionError, 'runtime_exclusions_pin_changed'):
            self.run_driver()
        self.assertFalse((self.output / 'LINKUP_REUSED_VARIABLES_V1_PRIVATE.sqlite').exists())

    def test_exact_mask_helper_never_borrows_another_asset_source_or_ad(self):
        rows = [('ad-A', 'f', 'known', 'Pro', 'source'),
                ('', 'g', 'unknown', 'Pro', 'source'),
                ('', 'wrong_asset', 'known', 'Other', 'source'),
                ('', 'wrong_source', 'known', 'Pro', 'Other')]
        self.assertEqual(driver.exact_family_masks(rows, document_key='', asset='Pro', source_sha='source'), {'g': 'unknown'})
        self.assertEqual(driver.exact_family_masks(rows, document_key='ad-B', asset='Pro', source_sha='source'), {'g': 'unknown'})
        self.assertEqual(driver.exact_family_masks(rows, document_key='ad-A', asset='Pro', source_sha='source'), {'f': 'known', 'g': 'unknown'})
        rows.append(('ad-A', 'f', 'unknown', 'Pro', 'source'))
        self.assertEqual(driver.exact_family_masks(rows, document_key='ad-A', asset='Pro', source_sha='source')['f'], 'conflicting_original_masks')


if __name__ == '__main__':
    unittest.main(verbosity=2)
