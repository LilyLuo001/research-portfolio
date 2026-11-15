"""Synthetic-only tests: no cloud calls, source advertisements or real outputs."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('compare_benchmark', HERE / 'cloud_compare_benchmark.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SCHEMA = HERE.parents[1] / 'corpus_pro_review_20261026/code/FORMAL800_REVIEW_SCHEMA.json'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + '\n')


def write_lines(path, values):
    path.write_text(''.join(json.dumps(value, ensure_ascii=False) + '\n' for value in values))


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.d = self.root / 'reuse_first_20261115/run01/benchmark20'
        self.d.mkdir(parents=True)
        (self.d / 'WORKER.lock').write_text('')
        (self.d / 'SCHEMA.json').write_bytes(SCHEMA.read_bytes())
        schema = json.loads(SCHEMA.read_text())
        self.bindings, self.refs = [], []
        for i in range(20):
            binding = {'audit_id': f'SYNTHETIC-{i:02d}', 'task': f'batch999/synthetic/{i}',
                       'record_id': f'synthetic-record-{i}',
                       'context_sha256': hashlib.sha256(f'synthetic-{i}'.encode()).hexdigest()}
            review = {key: [] for key in module.ARRAYS}
            review.update(record_id=binding['record_id'], context_sha256=binding['context_sha256'],
                          document_status='reviewed_full', technology_inventory_status='not_mentioned_after_full_review',
                          unresolved_notes=[])
            for group in module.OUTCOMES:
                review[group] = {key: 'not_mentioned' for key in schema['properties'][group]['required']}
            self.bindings.append(binding)
            self.refs.append({'audit_id': binding['audit_id'], 'review': review})
            save(self.case(i) / 'RESULT_PUBLIC.json', {'status': 'frozen_validator_pass_candidate_only'})
            write_lines(self.case(i) / 'VALIDATED_PRIVATE.jsonl', [review])
        save(self.d / 'SELECTION_PRIVATE.json', self.bindings)
        write_lines(self.d / 'REFERENCES_PRIVATE.jsonl', self.refs)
        save(self.d / 'EXCLUSIONS_PRIVATE.json', {'tasks': []})
        save(self.d / 'RUN_STATUS_PUBLIC.json', {'status': 'finite_benchmark_completed', 'completed': 20,
                                                'selected': 20, 'engineering_pass': 20,
                                                'original_ledgers_unchanged': True})
        self.repin()

    def tearDown(self):
        self.temp.cleanup()

    def case(self, i):
        return self.d / 'results' / f'case{i:04d}'

    def repin(self):
        save(self.d / 'PREPARATION_PUBLIC.json', {'output_sha256': {
            name: module.sha(self.d / name)
            for name in ('SCHEMA.json', 'SELECTION_PRIVATE.json', 'REFERENCES_PRIVATE.jsonl')}})
        save(self.d / 'SHA256SUMS_PRIVATE.json', {
            str(path.relative_to(self.d)): module.sha(path) for path in self.d.rglob('*')
            if path.is_file() and path.name != 'SHA256SUMS_PRIVATE.json' and 'comparison_v1' not in path.parts})

    def candidate(self, i=0):
        return json.loads((self.case(i) / 'VALIDATED_PRIVATE.jsonl').read_text())

    def change_candidate(self, value, i=0):
        write_lines(self.case(i) / 'VALIDATED_PRIVATE.jsonl', [value])
        self.repin()

    def set_nonpass(self, i=0, status='invalid_json_preserved'):
        save(self.case(i) / 'RESULT_PUBLIC.json', {'status': status})
        state = module.read(self.d / 'RUN_STATUS_PUBLIC.json')
        state['engineering_pass'] -= 1
        save(self.d / 'RUN_STATUS_PUBLIC.json', state)

    def test01_exact20_but_never_quality_certified(self):
        r = module.compare(self.root)
        self.assertEqual(r['engineering_pass_records'], 20)
        self.assertEqual(r['full_business_structure_exact_records_among_paired'], 20)
        self.assertFalse(r['precision_recall_F1_computed'])
        self.assertFalse(r['automatic_promotion'])
        self.assertEqual(r['new_production_accepted'], 0)

    def test02_outcome_unknown_is_preserved(self):
        c = self.candidate()
        c['experience_outcomes']['general_work'] = 'unknown'
        self.change_candidate(c)
        r = module.compare(self.root)
        self.assertEqual(r['categorical_exact_agreement']['experience_outcomes.general_work']['exact'], 19)
        self.assertEqual(r['comparison_coverage']['candidate_records_with_enum_unknown'], 1)
        self.assertEqual(r['full_business_structure_disagreement_records_among_paired'], 1)

    def test03_quote_only_diagnostic_does_not_become_full_exact(self):
        item = {'target': 'explicit_new_graduate', 'conditionality': 'unconditional', 'quotes': ['synthetic quote A']}
        self.refs[0]['review']['entry_items'] = [item]
        write_lines(self.d / 'REFERENCES_PRIVATE.jsonl', self.refs)
        c = self.candidate()
        c['entry_items'] = [dict(item, quotes=['synthetic quote B'])]
        self.change_candidate(c)
        r = module.compare(self.root)
        self.assertEqual(r['full_business_structure_exact_records_among_paired'], 19)
        self.assertEqual(r['full_business_without_quotes_exact_records_among_paired'], 20)
        self.assertEqual(r['relation_array_exact_diagnostics']['entry_items']['full_exact_matched_items'], 0)
        self.assertEqual(r['relation_array_exact_diagnostics']['entry_items']['without_quotes_exact_matched_items'], 1)

    def test04_year_strength_and_branch_are_not_dropped(self):
        a = {'object': 'tool_specific', 'years_min': 3, 'strength': 'required',
             'alternative_group': 'A', 'alternative_branch': 'B', 'relation': 'OR', 'quotes': ['synthetic']}
        for key, value in [('object', 'general_work'), ('years_min', 4), ('strength', 'preferred'),
                           ('alternative_group', 'C'), ('alternative_branch', 'D'), ('relation', 'AND')]:
            b = dict(a, **{key: value})
            self.assertFalse(module.array_exact([a], [b], strip_quotes=True)['array_multiset_exact'])

    def test05_top_array_order_only_is_ignored_and_duplicates_count(self):
        a, b = {'object': 'one'}, {'object': 'two'}
        self.assertTrue(module.array_exact([a, b], [b, a])['array_multiset_exact'])
        r = module.array_exact([a, a], [a])
        self.assertFalse(r['array_multiset_exact'])
        self.assertEqual(r['matched_exact_items'], 1)

    def test06_protected_reference_and_output_not_parsed(self):
        save(self.d / 'EXCLUSIONS_PRIVATE.json', {'tasks': [self.bindings[0]['task']]})
        self.set_nonpass(status='quarantined_provider_filter')
        lines = (self.d / 'REFERENCES_PRIVATE.jsonl').read_bytes().splitlines(keepends=True)
        lines[0] = b'NOT JSON: protected reference must not be parsed\n'
        (self.d / 'REFERENCES_PRIVATE.jsonl').write_bytes(b''.join(lines))
        (self.case(0) / 'VALIDATED_PRIVATE.jsonl').write_text('NOT JSON: do not parse')
        self.repin()
        r = module.compare(self.root)
        self.assertEqual(r['comparison_coverage']['protected_records_skipped_without_reference_parse'], 1)
        self.assertEqual(r['comparison_coverage']['paired_review_records'], 19)

    def test07_nonpass_output_not_parsed_or_counted_as_agreement(self):
        self.set_nonpass()
        (self.case(0) / 'VALIDATED_PRIVATE.jsonl').write_text('NOT JSON: failed body not parsed')
        self.repin()
        r = module.compare(self.root)
        self.assertEqual(r['engineering_pass_fraction_selected20'], .95)
        self.assertEqual(r['missing_unusable_or_protected_not_counted_as_exact'], 1)
        self.assertEqual(r['comparison_coverage']['nonpass_records_excluded_from_content_comparison'], 1)

    def test08_running_state_blocks_before_reference_parse(self):
        save(self.d / 'RUN_STATUS_PUBLIC.json', {'status': 'running'})
        (self.d / 'REFERENCES_PRIVATE.jsonl').write_text('not JSON')
        with self.assertRaisesRegex(RuntimeError, 'completion_required'):
            module.compare(self.root)

    def test09_missing_result_blocks(self):
        (self.case(4) / 'RESULT_PUBLIC.json').unlink()
        with self.assertRaisesRegex(RuntimeError, 'exact20_result'):
            module.compare(self.root)

    def test10_tampered_candidate_SHA_blocks(self):
        (self.case(0) / 'VALIDATED_PRIVATE.jsonl').write_text('{}')
        with self.assertRaisesRegex(RuntimeError, 'SHA_mismatch'):
            module.compare(self.root)

    def test11_candidate_identity_mismatch_blocks(self):
        c = self.candidate()
        c['record_id'] = 'different-synthetic-record'
        self.change_candidate(c)
        with self.assertRaisesRegex(RuntimeError, 'candidate_identity_mismatch'):
            module.compare(self.root)

    def test12_duplicate_selection_blocks(self):
        self.bindings[1]['context_sha256'] = self.bindings[0]['context_sha256']
        save(self.d / 'SELECTION_PRIVATE.json', self.bindings)
        self.repin()
        with self.assertRaisesRegex(RuntimeError, 'selection_binding_not_unique20'):
            module.compare(self.root)

    def test13_source_files_unchanged_and_idempotent(self):
        before = {str(path): module.sha(path) for path in self.d.rglob('*') if path.is_file()}
        a = module.compare(self.root)
        b = module.compare(self.root)
        self.assertEqual(a, b)
        self.assertTrue(all(module.sha(path) == digest for path, digest in before.items()))

    def test14_existing_comparison_tamper_not_overwritten(self):
        module.compare(self.root)
        p = self.d / 'comparison_v1/DISAGREEMENTS_PRIVATE.jsonl'
        p.write_text('synthetic tamper')
        with self.assertRaisesRegex(RuntimeError, 'existing_comparison_SHA_mismatch'):
            module.compare(self.root)
        self.assertEqual(p.read_text(), 'synthetic tamper')

    def test15_free_text_unknown_not_a_state(self):
        self.assertEqual(module.unknown_paths({'type': 'string'}, 'unknown'), [])
        self.assertEqual(module.unknown_paths({'type': 'string', 'enum': ['known', 'unknown']}, 'unknown'), [''])

    def test16_numeric_equality_nested_branch_order_preserved(self):
        self.assertTrue(module.array_exact([{'years': 5}], [{'years': 5.0}])['array_multiset_exact'])
        self.assertFalse(module.array_exact([{'branches': ['A', 'B']}], [{'branches': ['B', 'A']}])['array_multiset_exact'])


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    report = {'status': 'pass' if result.wasSuccessful() else 'fail', 'synthetic_tests_run': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors), 'cloud_calls': 0,
              'model_calls': 0, 'private_source_ads_or_real_outputs_read': 0, 'new_production_accepted': 0}
    (HERE.parent / 'BENCHMARK_COMPARISON_OFFLINE_TEST_PUBLIC.json').write_text(json.dumps(report, indent=2) + '\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
