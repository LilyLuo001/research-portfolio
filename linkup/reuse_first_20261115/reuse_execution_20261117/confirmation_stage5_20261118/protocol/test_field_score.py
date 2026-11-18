"""Synthetic-only regressions; no real records, human labels or model calls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

import field_score as s

ROOT = Path(__file__).resolve().parent
PROTOCOL = json.loads((ROOT / 'CONFIRMATION_PROTOCOL.json').read_text())


def packet(text, record_id='synthetic'):
    return {'record_id': record_id, 'context_sha256': hashlib.sha256(text.encode()).hexdigest(),
            'full_document': text,
            'assignment': {'packet_id': 'synthetic', 'reviewer_role': 'primary',
                           'provenance': 'synthetic_regression_fixture'}}


def blank(p):
    result = {k: p[k] for k in ('record_id', 'context_sha256')}
    result.update(document_status='reviewed_full', technology_items=[],
                  technology_inventory_status='not_mentioned_after_full_review',
                  qualification_alternatives=[], unresolved_notes=[])
    for family, (dims, inventory, _) in s.FAMILIES.items():
        result[family + '_outcomes'] = {dim: 'not_mentioned' for dim in dims}
        result[inventory] = []
    return result


def clause(quote='Three years of work experience required.', **overrides):
    result = {'object': 'general_work', 'object_detail': 'work experience', 'strength': 'required',
              'conditionality': 'unconditional', 'years_min': 3, 'years_max': None,
              'years_relation': 'at_least', 'alternative_group': None, 'alternative_branch': None,
              'quotes': [quote]}
    result.update(overrides)
    return result


def positive(p):
    r = blank(p)
    r['experience_outcomes']['general_work'] = 'present'
    r['experience_clauses'] = [clause()]
    return r


def frame_row(p, partition='confirmation'):
    return {'record_id': p['record_id'], 'context_sha256': p['context_sha256'], 'partition': partition,
            'protected': False, 'fresh_never_exposed': True,
            'source_units_sha256': s.digest_json(s.source_units(p['full_document']))}


def spec(kind, field='experience.general_work'):
    return next(v for v in PROTOCOL['measures'] if v['field'] == field and v['kind'] == kind)


class ScorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = s.load_validator(protocol=PROTOCOL)

    def obs(self, p, r, kind, field='experience.general_work'):
        validation = self.validator.validate(p, r, protected=False)
        return s.observe(r, validation, spec(kind, field), p, s.source_units(p['full_document']),
                         self.validator.frozen)

    def test_cosmetic_object_description_is_not_scored(self):
        p = packet('Three years of work experience required.')
        a = positive(p)
        b = deepcopy(a)
        b['experience_clauses'][0]['object_detail'] = 'A completely different display paraphrase'
        self.assertTrue(s.lists_equal(self.obs(p, a, 'clause_relation')['atoms'],
                                      self.obs(p, b, 'clause_relation')['atoms']))

    def test_quote_boundary_differences_match_same_source_unit(self):
        p = packet('Requirements: Three years of work experience required.')
        a, b = positive(p), positive(p)
        b['experience_clauses'][0]['quotes'] = [p['full_document']]
        x, y = self.obs(p, a, 'years'), self.obs(p, b, 'years')
        result = s.summarize([(x, y)], spec('years'), PROTOCOL['gate'], qualify=True)
        self.assertEqual(result['source_unit_supported_relation']['tp'], 1)
        self.assertEqual(result['exact_quote_span_diagnostic_not_gate']['tp'], 0)

    def test_wrong_years_do_not_match(self):
        p = packet('Three years of work experience required.')
        a, b = positive(p), positive(p)
        b['experience_clauses'][0]['years_min'] = 5
        self.assertFalse(s.lists_equal(self.obs(p, a, 'years')['atoms'], self.obs(p, b, 'years')['atoms']))

    def test_years_cannot_move_between_distinct_source_units(self):
        p = packet('Three years accounting experience. Five years sales experience.')
        a = blank(p)
        a['experience_outcomes']['occupation_task'] = 'present'
        a['experience_clauses'] = [clause('Three years accounting experience.', object='occupation_task'),
                                    clause('Five years sales experience.', object='occupation_task', years_min=5)]
        b = deepcopy(a)
        b['experience_clauses'][0]['years_min'], b['experience_clauses'][1]['years_min'] = 5, 3
        self.assertFalse(s.lists_equal(self.obs(p, a, 'years', 'experience.occupation_task')['atoms'],
                                      self.obs(p, b, 'years', 'experience.occupation_task')['atoms']))

    def grouped(self):
        p = packet('Bachelor degree and three years work experience; master degree and one year work experience. '
                   'Five years professional experience applies to either path.')
        a = blank(p)
        a['experience_outcomes']['general_work'] = 'present'
        a['qualification_alternatives'] = [{'group': 'g', 'relation': 'OR', 'branches': [
            {'branch': 'a', 'condition': 'Bachelor plus work', 'quotes': ['Bachelor degree and three years work experience;']},
            {'branch': 'b', 'condition': 'Master plus work', 'quotes': ['master degree and one year work experience.']}]}]
        a['experience_clauses'] = [
            clause('Bachelor degree and three years work experience;', alternative_group='g', alternative_branch='a',
                   conditionality='conditional'),
            clause('master degree and one year work experience.', years_min=1, alternative_group='g',
                   alternative_branch='b', conditionality='conditional')]
        return p, a

    def test_group_ids_order_and_condition_display_are_not_scored(self):
        p, a = self.grouped()
        b = deepcopy(a)
        group = b['qualification_alternatives'][0]
        group['group'] = 'renamed'
        group['branches'].reverse()
        for branch in group['branches']:
            branch['condition'] = 'Cosmetic paraphrase of the evidenced branch'
            branch['branch'] += '_new'
        for item in b['experience_clauses']:
            item['alternative_group'] = 'renamed'
            item['alternative_branch'] += '_new'
        self.assertTrue(s.lists_equal(self.obs(p, a, 'group')['atoms'], self.obs(p, b, 'group')['atoms']))

    def test_or_and_are_distinct(self):
        p, a = self.grouped()
        b = deepcopy(a)
        b['qualification_alternatives'][0]['relation'] = 'AND'
        self.assertFalse(s.lists_equal(self.obs(p, a, 'group')['atoms'], self.obs(p, b, 'group')['atoms']))

    def test_shared_and_branch_scope_are_distinct(self):
        p, a = self.grouped()
        shared = clause('Five years professional experience applies to either path.', years_min=5,
                        alternative_group='g', conditionality='conditional')
        a['experience_clauses'].append(shared)
        b = deepcopy(a)
        b['experience_clauses'][-1]['alternative_branch'] = 'a'
        self.assertFalse(s.lists_equal(self.obs(p, a, 'group')['atoms'], self.obs(p, b, 'group')['atoms']))

    def test_unrelated_quote_error_is_field_local(self):
        p = packet('Three years of work experience required.')
        r = positive(p)
        r['responsibility_outcomes']['training_mentoring'] = 'present'
        r['responsibility_items'] = [{'dimension': 'training_mentoring', 'subject': 'advertised_worker',
                                     'relation': 'current_duty', 'conditionality': 'unconditional',
                                     'quotes': ['THIS QUOTE IS NOT IN THE DOCUMENT']}]
        self.assertEqual(self.obs(p, r, 'years')['status'], 'known')
        self.assertEqual(self.obs(p, r, 'mention', 'responsibility.training_mentoring')['status'], 'invalid_local')

    def test_unknown_candidate_is_false_negative(self):
        p = packet('Three years of work experience required.')
        reference = self.obs(p, positive(p), 'mention')
        unknown = {'status': 'unprocessed', 'outcome': 'unknown', 'atoms': []}
        result = s.summarize([(reference, unknown)], spec('mention'), PROTOCOL['gate'], qualify=True)
        self.assertEqual(result['class_metrics']['present']['fn'], 1)
        self.assertEqual(result['class_metrics']['present']['recall'], 0)

    def test_unknown_reference_reduces_coverage(self):
        unknown = {'status': 'reviewed_unknown', 'outcome': 'unknown', 'atoms': []}
        result = s.summarize([(unknown, unknown)], spec('mention'), PROTOCOL['gate'], qualify=True)
        self.assertEqual(result['known_reference_coverage'], 0)
        self.assertIn('known_reference_coverage_below_gate', result['blocking_reasons'])

    def test_partial_nonmention_does_not_become_negative(self):
        p = packet('A position description.')
        r = blank(p)
        r['document_status'] = 'reviewed_partial'
        self.assertEqual(self.obs(p, r, 'mention')['outcome'], 'unknown')

    def test_waiver_is_separate_from_nonmention(self):
        p = packet('No work experience is required.')
        waiver = blank(p)
        waiver['experience_clauses'] = [clause(p['full_document'], strength='explicitly_waived',
                                               years_min=None, years_relation='not_stated')]
        self.assertEqual(self.obs(p, waiver, 'mention')['outcome'], 'not_mentioned')
        self.assertEqual(self.obs(p, waiver, 'waiver')['outcome'], 'present')
        self.assertEqual(self.obs(p, blank(p), 'waiver')['outcome'], 'not_mentioned')

    def test_unresolved_years_do_not_block_independent_mention(self):
        p = packet('Three years of work experience required.')
        r = positive(p)
        r['experience_clauses'][0]['years_relation'] = 'unresolved'
        self.assertEqual(self.obs(p, r, 'mention')['outcome'], 'present')
        self.assertEqual(self.obs(p, r, 'years')['outcome'], 'unknown')

    def test_strict_duty_excludes_prior_experience(self):
        p = packet('Prior experience supervising people required.')
        r = blank(p)
        r['responsibility_outcomes']['people_supervision'] = 'present'
        r['responsibility_items'] = [{'dimension': 'people_supervision', 'subject': 'advertised_worker',
                                     'relation': 'prior_experience', 'conditionality': 'unconditional',
                                     'quotes': [p['full_document']]}]
        self.assertEqual(self.obs(p, r, 'mention', 'responsibility.people_supervision')['outcome'], 'present')
        self.assertEqual(self.obs(p, r, 'strict_current_duty', 'responsibility.people_supervision')['outcome'], 'not_mentioned')

    def test_one_to_one_evidence_matching(self):
        p = packet('Three years of work experience required. Three years professional experience required.')
        a = positive(p)
        b = deepcopy(a)
        b['experience_clauses'].append(clause('Three years professional experience required.'))
        x, y = self.obs(p, a, 'years'), self.obs(p, b, 'years')
        result = s.summarize([(x, y)], spec('years'), PROTOCOL['gate'], qualify=True)
        self.assertEqual(result['source_unit_supported_relation']['tp'], 1)
        self.assertEqual(result['source_unit_supported_relation']['fp'], 1)

    def test_complete_accounting_support_and_challenge_separation(self):
        frame, cases = [], []
        for index in range(61):
            text = ('Three years of work experience required.' if index % 2 == 0 else 'Position description.')
            p = packet(text + f'\nSynthetic unique fixture {index}.', str(index))
            r = positive(p) if index % 2 == 0 else blank(p)
            frame.append(frame_row(p, 'challenge' if index == 60 else 'confirmation'))
            cases.append({'record_id': p['record_id'], 'context_sha256': p['context_sha256'],
                          'packet': p, 'reference': r, 'candidate': deepcopy(r)})
        output = s.evaluate(frame, cases, PROTOCOL, self.validator)
        measure = 'experience.general_work.mention'
        result = output['measure_results']['confirmation'][measure]
        self.assertTrue(result['machine_reference_measure_gate_pass'])
        self.assertEqual(result['cases'], 60)
        self.assertEqual(result['support'], {'present': 30, 'not_mentioned': 30})
        self.assertFalse(output['measure_results']['challenge'][measure]['machine_reference_measure_gate_pass'])
        self.assertFalse(output['production_admission'])
        self.assertEqual(len(output['modules_retained']), 5)
        # Missing entire rows remain in the denominator, never silently omitted.
        output = s.evaluate(frame, cases[1:], PROTOCOL, self.validator)
        self.assertEqual(output['measure_results']['confirmation'][measure]['cases'], 60)
        self.assertEqual(output['accounting']['missing_case_rows'], 1)

    def test_protection_checked_before_review_access(self):
        p = packet('A description.')
        class Guarded(dict):
            def get(self, name, default=None):
                if name in ('packet', 'reference', 'candidate'):
                    raise AssertionError('protected payload accessed')
                return super().get(name, default)
        case = Guarded(record_id=p['record_id'], protection_blocked=True)
        output = s.evaluate([frame_row(p)], [case], PROTOCOL, self.validator)
        self.assertEqual(output['accounting']['quarantined_after_freeze'], 1)

    def test_original_reviews_are_not_modified(self):
        p = packet('Three years of work experience required.')
        r = positive(p)
        before = deepcopy(r)
        self.obs(p, r, 'clause_relation')
        self.assertEqual(r, before)

    def test_duplicate_frame_identity_rejected(self):
        p = packet('A description.')
        with self.assertRaisesRegex(ValueError, 'duplicate_frame'):
            s.evaluate([frame_row(p), frame_row(p)], [], PROTOCOL, self.validator)

    def test_astra_queue_is_bounded_and_deterministic(self):
        frame, cases = [], []
        for index in range(8):
            p = packet('Three years of work experience required.\nFixture ' + str(index), str(index))
            reference, candidate = positive(p), positive(p)
            candidate['experience_clauses'][0]['years_min'] = 99
            frame.append(frame_row(p))
            cases.append({'record_id': p['record_id'], 'packet': p,
                          'reference': reference, 'candidate': candidate})
        first = s.evaluate(frame, cases, PROTOCOL, self.validator)
        reversed_order = s.evaluate(list(reversed(frame)), list(reversed(cases)), PROTOCOL, self.validator)
        self.assertEqual(len(first['bounded_astra_diagnostic_queue']), 6)
        self.assertEqual(first['bounded_astra_diagnostic_queue'], reversed_order['bounded_astra_diagnostic_queue'])

    def test_source_units_must_match_preoutput_frame(self):
        p = packet('Three years of work experience required.')
        r = positive(p)
        metadata = frame_row(p)
        metadata['source_units_sha256'] = '0' * 64
        result = s.evaluate([metadata], [{'record_id': p['record_id'], 'packet': p,
                                         'reference': r, 'candidate': deepcopy(r)}], PROTOCOL, self.validator)
        measure = result['measure_results']['confirmation']['experience.general_work.mention']
        self.assertEqual(measure['known_reference_cases'], 0)
        self.assertEqual(measure['status_counts']['reference:shared_input_invalid'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
