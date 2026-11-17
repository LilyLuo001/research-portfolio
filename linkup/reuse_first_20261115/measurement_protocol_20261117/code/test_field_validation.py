"""Synthetic regression tests only. Set LINKUP_PROTOCOL_REPO to the repository."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import unittest

from field_validation import DIMS, FIELDS, FieldValidator, canonical_logic, parse_review


def fixtures():
    text = 'At least 5 years of accounting experience. Mentors colleagues. Graduate applicants welcome.'
    packet = {'record_id': 'synthetic', 'context_sha256': hashlib.sha256(text.encode()).hexdigest(),
              'full_document': text,
              'assignment': {'packet_id': 'synthetic', 'reviewer_role': 'primary', 'provenance': 'synthetic'}}
    review = {'record_id': 'synthetic', 'context_sha256': packet['context_sha256'],
              'document_status': 'reviewed_full', 'experience_clauses': [],
              'entry_items': [], 'responsibility_items': [], 'qualification_alternatives': [],
              'technology_items': [], 'technology_inventory_status': 'not_mentioned_after_full_review',
              'unresolved_notes': []}
    for fam, dims in DIMS.items():
        review[fam + '_outcomes'] = {dim: 'not_mentioned' for dim in dims}
    return packet, review


def add_experience(review):
    review['experience_outcomes']['occupation_task'] = 'present'
    review['experience_clauses'] = [{
        'object': 'occupation_task', 'object_detail': 'accounting', 'strength': 'required',
        'conditionality': 'unconditional', 'years_min': 5, 'years_max': None,
        'years_relation': 'at_least', 'alternative_group': None, 'alternative_branch': None,
        'quotes': ['At least 5 years of accounting experience.']}]


def add_mentoring(review):
    review['responsibility_outcomes']['training_mentoring'] = 'present'
    review['responsibility_items'] = [{'dimension': 'training_mentoring',
        'subject': 'advertised_worker', 'relation': 'current_duty', 'conditionality': 'unconditional',
        'quotes': ['Mentors colleagues.']}]


class FieldValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(os.environ['LINKUP_PROTOCOL_REPO'])
        source = root / 'linkup/formal800_20261012/code/validate_reviews.py'
        spec = importlib.util.spec_from_file_location('frozen_validator', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.schema = json.loads((root / 'linkup/formal800_20261012/FORMAL800_REVIEW_SCHEMA.json').read_text())
        cls.engine = FieldValidator(cls.schema, module)

    def run_review(self, p, r):
        return self.engine.validate(p, r, protected=False)['fields']

    def test_valid_nonmention_remains_known_nonmention(self):
        p, r = fixtures()
        fields = self.run_review(p, r)
        self.assertTrue(all(x['status'] == 'engineering_valid' for x in fields.values()))
        self.assertTrue(all(not x['semantic_accuracy_certified'] for x in fields.values()))

    def test_unknown_is_not_nonmention_or_processing_failure(self):
        p, r = fixtures()
        r['experience_outcomes']['industry_domain'] = 'unknown'
        fields = self.run_review(p, r)
        self.assertEqual(fields['experience.industry_domain']['status'], 'reviewed_unknown')
        self.assertEqual(fields['experience.general_work']['status'], 'engineering_valid')

    def test_bad_mentoring_quote_preserves_twelve_fields(self):
        p, r = fixtures()
        add_experience(r); add_mentoring(r)
        r['responsibility_items'][0]['quotes'] = ['Invented quotation.']
        fields = self.run_review(p, r)
        self.assertEqual(fields['responsibility.training_mentoring']['status'], 'invalid_local')
        self.assertEqual(sum(x['status'] == 'engineering_valid' for x in fields.values()), 12)

    def test_bad_year_bounds_only_block_related_experience(self):
        p, r = fixtures()
        add_experience(r)
        r['experience_clauses'][0].update(years_max=2, years_relation='range')
        fields = self.run_review(p, r)
        self.assertEqual(fields['experience.occupation_task']['status'], 'invalid_local')
        self.assertEqual(fields['experience.industry_domain']['status'], 'engineering_valid')

    def test_subject_error_only_blocks_mentoring(self):
        p, r = fixtures()
        add_mentoring(r)
        r['responsibility_items'][0]['subject'] = 'other_employee'
        fields = self.run_review(p, r)
        self.assertEqual(fields['responsibility.training_mentoring']['status'], 'invalid_local')
        self.assertEqual(fields['responsibility.client_ownership']['status'], 'engineering_valid')

    def test_missing_one_outcome_only_blocks_that_field(self):
        p, r = fixtures()
        del r['entry_outcomes']['explicit_new_graduate']
        fields = self.run_review(p, r)
        self.assertEqual(fields['entry.explicit_new_graduate']['status'], 'invalid_local')
        self.assertEqual(fields['entry.explicit_no_experience']['status'], 'engineering_valid')

    def test_unassignable_item_blocks_family_not_all_fields(self):
        p, r = fixtures()
        r['experience_clauses'] = [{'object': 'unresolved'}]
        fields = self.run_review(p, r)
        self.assertTrue(all(fields['experience.' + d]['status'] == 'invalid_local' for d in DIMS['experience']))
        self.assertEqual(fields['technology']['status'], 'engineering_valid')

    def test_unknown_dimension_not_silently_dropped(self):
        p, r = fixtures()
        r['entry_outcomes']['invented_dimension'] = 'present'
        fields = self.run_review(p, r)
        self.assertEqual(fields['entry.explicit_new_graduate']['status'], 'invalid_local')
        self.assertEqual(fields['experience.general_work']['status'], 'engineering_valid')

    def test_identity_error_blocks_shared_record(self):
        p, r = fixtures()
        r['context_sha256'] = '0' * 64
        result = self.engine.validate(p, r, protected=False)
        self.assertEqual(result['status'], 'shared_input_invalid')
        self.assertEqual(len(result['fields']), len(FIELDS))

    def test_protection_checked_before_packet_access(self):
        result = self.engine.validate(None, None, protected=True)
        self.assertEqual(result['status'], 'quarantined')
        self.assertEqual(result['fields'], {})

    def test_partial_review_cannot_claim_nonmention(self):
        p, r = fixtures()
        r['document_status'] = 'reviewed_partial'
        add_experience(r)
        fields = self.run_review(p, r)
        self.assertEqual(fields['entry.explicit_new_graduate']['status'], 'invalid_local')
        self.assertEqual(fields['experience.occupation_task']['status'], 'engineering_valid')
        self.assertFalse(fields['experience.occupation_task']['field_review_complete'])

    def test_missing_group_blocks_only_dependent_field(self):
        p, r = fixtures()
        add_experience(r)
        r['experience_clauses'][0].update(alternative_group='g', alternative_branch='a')
        fields = self.run_review(p, r)
        self.assertEqual(fields['experience.occupation_task']['status'], 'invalid_local')
        self.assertEqual(fields['experience.general_work']['status'], 'engineering_valid')

    def test_all_branches_remain_evidence_checked(self):
        p, r = fixtures()
        add_experience(r)
        r['experience_clauses'][0].update(alternative_group='g', alternative_branch='a')
        r['qualification_alternatives'] = [{'group': 'g', 'relation': 'OR', 'branches': [
            {'branch': 'a', 'condition': 'accounting', 'quotes': ['accounting experience']},
            {'branch': 'b', 'condition': 'alternative', 'quotes': ['Invented qualification.']}]}]
        fields = self.run_review(p, r)
        self.assertEqual(fields['experience.occupation_task']['status'], 'invalid_local')
        self.assertEqual(fields['responsibility.training_mentoring']['status'], 'engineering_valid')

    def test_shared_null_branch_retained(self):
        p, r = fixtures()
        add_experience(r)
        r['experience_clauses'][0].update(alternative_group='g', alternative_branch=None)
        r['qualification_alternatives'] = [{'group': 'g', 'relation': 'OR', 'branches': [
            {'branch': 'a', 'condition': 'synthetic branch', 'quotes': ['accounting experience']}]}]
        self.assertEqual(self.run_review(p, r)['experience.occupation_task']['status'], 'engineering_valid')

    def test_other_dimension_in_same_group_is_dependency(self):
        p, r = fixtures()
        add_experience(r)
        r['experience_clauses'][0].update(alternative_group='g', alternative_branch='a')
        linked = deepcopy(r['experience_clauses'][0])
        linked.update(object='tool_specific', years_min=5, years_max=2, years_relation='range')
        r['experience_clauses'].append(linked)
        r['experience_outcomes']['tool_specific'] = 'present'
        r['qualification_alternatives'] = [{'group': 'g', 'relation': 'OR', 'branches': [
            {'branch': 'a', 'condition': 'synthetic', 'quotes': ['accounting experience']}]}]
        fields = self.run_review(p, r)
        self.assertEqual(fields['experience.occupation_task']['status'], 'invalid_local')
        self.assertEqual(fields['experience.tool_specific']['status'], 'invalid_local')
        self.assertEqual(fields['responsibility.training_mentoring']['status'], 'engineering_valid')

    def test_invalid_shared_condition_propagates_to_group_fields(self):
        p, r = fixtures()
        add_experience(r)
        r['experience_clauses'][0].update(alternative_group='g', alternative_branch='a')
        shared = deepcopy(r['experience_clauses'][0])
        shared.update(object='general_work', alternative_branch=None, quotes=['Invented shared condition.'])
        r['experience_clauses'].append(shared)
        r['experience_outcomes']['general_work'] = 'present'
        r['qualification_alternatives'] = [{'group': 'g', 'relation': 'OR', 'branches': [
            {'branch': 'a', 'condition': 'synthetic', 'quotes': ['accounting experience']}]}]
        fields = self.run_review(p, r)
        self.assertEqual(fields['experience.occupation_task']['status'], 'invalid_local')
        self.assertEqual(fields['experience.general_work']['status'], 'invalid_local')
        self.assertEqual(fields['entry.explicit_new_graduate']['status'], 'engineering_valid')

    def test_unrelated_bad_group_preserved_without_global_block(self):
        p, r = fixtures()
        r['qualification_alternatives'] = [{'group': 'unused', 'branches': 'malformed'}]
        before = deepcopy(r)
        result = self.engine.validate(p, r, protected=False)
        self.assertTrue(all(x['status'] == 'engineering_valid' for x in result['fields'].values()))
        self.assertEqual(before, r)
        self.assertFalse(result['production_admission'])

    def test_nonfinite_direct_values_block_only_field(self):
        p, r = fixtures()
        add_experience(r)
        r['experience_clauses'][0]['years_min'] = float('nan')
        fields = self.run_review(p, r)
        self.assertEqual(fields['experience.occupation_task']['status'], 'invalid_local')
        self.assertEqual(fields['technology']['status'], 'engineering_valid')

    def test_source_review_is_unchanged(self):
        p, r = fixtures()
        add_experience(r); add_mentoring(r)
        before = deepcopy((p, r))
        self.run_review(p, r)
        self.assertEqual((p, r), before)


class RepresentationTests(unittest.TestCase):
    def test_duplicate_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate_json_key'):
            parse_review('{"x": 1, "x": 2}')

    def test_nonfinite_json_rejected(self):
        for payload in ('{"x": NaN}', '{"x": 1e999}'):
            with self.assertRaisesRegex(ValueError, 'nonfinite'):
                parse_review(payload)

    def test_order_preserved_as_boolean_equivalence_not_word_guess(self):
        atoms = {'accounting', 'finance'}
        a = {'op': 'or', 'args': [{'atom': 'accounting'}, {'atom': 'finance'}]}
        b = {'op': 'or', 'args': list(reversed(a['args']))}
        self.assertEqual(canonical_logic(a, atoms), canonical_logic(b, atoms))
        b['op'] = 'and'
        self.assertNotEqual(canonical_logic(a, atoms), canonical_logic(b, atoms))

    def test_mixed_logic_groups_do_not_collapse(self):
        atoms = {'a', 'b', 'c'}
        a = {'op': 'and', 'args': [{'atom': 'a'}, {'op': 'or', 'args': [{'atom': 'b'}, {'atom': 'c'}]}]}
        b = {'op': 'or', 'args': [{'atom': 'a'}, {'op': 'and', 'args': [{'atom': 'b'}, {'atom': 'c'}]}]}
        self.assertNotEqual(canonical_logic(a, atoms), canonical_logic(b, atoms))

    def test_unknown_synonym_needs_semantic_review(self):
        with self.assertRaisesRegex(ValueError, 'unresolved_atom'):
            canonical_logic({'atom': 'finance and accounting'}, {'accounting', 'finance'})


if __name__ == '__main__':
    unittest.main()
