"""Offline synthetic checks for adapter only; no real data, cloud or models."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import cloud_score_adapter as a
import field_score as s
import test_field_score as fixtures


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def make_frame(self, count=3):
        packets, rows, inputs = [], [], []
        for i in range(count):
            packet = fixtures.packet('Three years of work experience required.\nSynthetic slot ' + str(i),
                                      'PRIVATE_RECORD_' + str(i))
            row = fixtures.frame_row(packet)
            row['case'] = 'case' + str(i)
            packets.append(packet)
            rows.append(row)
            inputs.append({'case': row['case'], 'row': packet, 'protected': False})
        source = self.directory / 'SOURCE_FRAME.json'
        a.write_new(source, rows)
        args = argparse.Namespace(source_frame=source, expected_source_frame_sha=s.file_sha(source),
                                  expected_count=count, no_requests_yet=True, output_directory=self.directory)
        public = a.freeze_frame(args)
        self.assertEqual(public['frame_count'], count)
        self.assertEqual(a.freeze_frame(args), public)
        a.write_new(self.directory / 'INPUTS.jsonl', inputs, jsonl=True)
        return packets, rows, inputs

    def test_freeze_uses_metadata_and_is_idempotent(self):
        _, frame, _ = self.make_frame()
        converted, receipt = a.load_frame(self.directory / 'FRAME_PRIVATE.jsonl',
                                          self.directory / 'FRAME_FREEZE_PUBLIC.json')
        self.assertEqual(frame, converted)
        self.assertEqual(receipt['protocol_bundle_sha256'], a.verify_bundle())

    def test_metadata_scanner_skips_protected_values_before_decode(self):
        # Invalid UTF-8 in protected text guarantees a full JSON decode would fail.
        raw = (b'{"payload":{"nested":["secret-\xff",{"a":"escaped \\" quote"}]},'
               b'"record_id":"blocked","context_sha256":"b","case":"case0",'
               b'"status":"blocked_protected_metadata_only"}\n')
        result = a.metadata(raw)
        self.assertNotIn('payload', result)
        path = self.directory / 'rows.jsonl'
        path.write_bytes(raw)
        self.assertEqual(a.read_selected(path, set()), {})
        with self.assertRaises(UnicodeDecodeError):
            a.read_selected(path, {('blocked', 'b')})

    def test_input_document_never_decoded_for_blocked_slot(self):
        raw = b'{"row":{"full_document":"\xff","context_sha256":"b","record_id":"blocked"},"case":"case0"}\n'
        path = self.directory / 'inputs.jsonl'
        path.write_bytes(raw)
        self.assertEqual(a.read_metadata(path)[('blocked', 'b')]['case'], 'case0')
        self.assertEqual(a.read_selected(path, set()), {})

    def test_duplicate_identity_rejected(self):
        path = self.directory / 'rows.jsonl'
        path.write_bytes(b'{"record_id":"a","context_sha256":"b"}\n' * 2)
        with self.assertRaisesRegex(ValueError, 'duplicate_source_identity'):
            a.read_metadata(path)

    def test_existing_root_context_count_receipt_is_accepted_unchanged(self):
        self.make_frame()
        receipt = a.read(self.directory / 'FRAME_FREEZE_PUBLIC.json')
        receipt['context_count'] = receipt.pop('frame_count')
        path = self.directory / 'ROOT_FRAME_FREEZE_PUBLIC.json'
        a.write_new(path, receipt)
        before = path.read_bytes()
        frame, actual = a.load_frame(self.directory / 'FRAME_PRIVATE.jsonl', path)
        self.assertEqual(len(frame), 3)
        self.assertEqual(actual['context_count'], 3)
        self.assertEqual(path.read_bytes(), before)

    def setup_outputs(self):
        packets, frame, _ = self.make_frame()
        roster = a.roster_sha(frame)
        outputs = {'Luna': [], 'Kimi': []}
        for leg in outputs:
            for packet, row in zip(packets, frame):
                payload = fixtures.positive(packet)
                if leg == 'Luna':
                    payload['experience_clauses'][0]['years_min'] = 4
                outputs[leg].append({'case': row['case'], 'record_id': packet['record_id'],
                    'context_sha256': packet['context_sha256'], 'roster_sha256': roster,
                    'leg': leg, 'payload': payload, 'field_validation': {},
                    'status': 'field_local_validation_complete'})
            a.write_new(self.directory / (leg + '.jsonl'), outputs[leg], jsonl=True)
        exclusions = self.directory / 'EXCLUSIONS.json'
        a.write_new(exclusions, {'context_sha256': [frame[-1]['context_sha256']]})
        for leg in outputs:
            a.write_new(self.directory / (leg + '_FINAL.json'), {'leg': leg, 'roster_sha256': roster,
                'output_roster_sha256': roster, 'outputs_accounted': len(frame),
                'output_sha256': s.file_sha(self.directory / (leg + '.jsonl')),
                'exclusions_sha256': s.file_sha(exclusions)})
        a.write_new(self.directory / 'KIMI_VALIDATION.json',
                    {'validated_output_sha256': s.file_sha(self.directory / 'Kimi.jsonl')})
        args = argparse.Namespace(frame=self.directory / 'FRAME_PRIVATE.jsonl',
            frame_freeze=self.directory / 'FRAME_FREEZE_PUBLIC.json', inputs=self.directory / 'INPUTS.jsonl',
            luna_outputs=self.directory / 'Luna.jsonl', kimi_outputs=self.directory / 'Kimi.jsonl',
            luna_final=self.directory / 'Luna_FINAL.json', kimi_final=self.directory / 'Kimi_FINAL.json',
            kimi_validation_receipt=self.directory / 'KIMI_VALIDATION.json',
            exclusions=[exclusions], output_directory=self.directory / 'joined', repo=s.REPO)
        return args, frame

    def test_join_preserves_every_slot_and_metadata_only_blocks(self):
        args, frame = self.setup_outputs()
        public = a.join_outputs(args)
        self.assertEqual(public['frame_count'], 3)
        self.assertEqual(public['blocked_metadata_only'], 1)
        cases = [a.parse(x) for x in (Path(args.output_directory) / 'JOINED_CASES_PRIVATE.jsonl').read_bytes().splitlines()]
        self.assertEqual(len(cases), 3)
        self.assertEqual(set(cases[-1]), {'record_id', 'context_sha256', 'protection_blocked'})
        self.assertEqual(cases[0]['candidate']['experience_clauses'][0]['years_min'], 4)
        self.assertNotIn('PRIVATE_RECORD_', json.dumps(public))

    def test_report_prepares_only_source_for_bounded_astra(self):
        args, frame = self.setup_outputs()
        a.join_outputs(args)
        cases = [a.parse(x) for x in (Path(args.output_directory) / 'JOINED_CASES_PRIVATE.jsonl').read_bytes().splitlines()]
        result = s.evaluate(frame, cases, fixtures.PROTOCOL, s.load_validator(protocol=fixtures.PROTOCOL))
        freeze = a.read(args.frame_freeze)
        result['freeze_binding'] = {key: freeze[key] for key in ('frame_sha256', 'protocol_bundle_sha256', 'frozen_before_first_request')}
        scores = Path(args.output_directory) / 'SCORES_PRIVATE.json'
        a.write_new(scores, result)
        report_args = argparse.Namespace(frame=args.frame, frame_freeze=args.frame_freeze,
            scores=scores, inputs=args.inputs, exclusions=args.exclusions, output_directory=self.directory / 'report')
        public = a.report_and_queue(report_args)
        self.assertEqual(public['astra_source_only_requests'], 2)
        self.assertNotIn('PRIVATE_RECORD_', json.dumps(public))
        requests = [a.parse(x) for x in (Path(report_args.output_directory) / 'ASTRA_INPUTS_PRIVATE.jsonl').read_bytes().splitlines()]
        for row in requests:
            self.assertEqual(set(row['row']), {'record_id', 'context_sha256', 'full_document'})
            self.assertNotIn('candidate', row)
            self.assertNotIn('reference', row)
            self.assertNotIn('measure_ids', row)

    def test_missing_quarantine_export_fails_closed(self):
        args, _ = self.setup_outputs()
        wrong = self.directory / 'WRONG_EXCLUSIONS.json'
        a.write_new(wrong, {})
        args.exclusions = [wrong]
        with self.assertRaisesRegex(ValueError, 'missing_pinned_leg_quarantine_export'):
            a.join_outputs(args)


if __name__ == '__main__':
    unittest.main(verbosity=2)
