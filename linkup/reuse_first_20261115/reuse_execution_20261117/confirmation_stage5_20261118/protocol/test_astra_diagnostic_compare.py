import argparse
from copy import deepcopy
from pathlib import Path
import unittest

import astra_diagnostic_compare as d
import cloud_score_adapter as a
import field_score as s
import test_cloud_score_adapter as integration
import test_field_score as fixtures


class DiagnosticTests(integration.AdapterTests):
    def prepare_diagnostics(self):
        args, frame = self.setup_outputs()
        a.join_outputs(args)
        directory = Path(args.output_directory)
        cases_path = directory / 'JOINED_CASES_PRIVATE.jsonl'
        cases = [a.parse(x) for x in cases_path.read_bytes().splitlines()]
        result = s.evaluate(frame, cases, fixtures.PROTOCOL, s.load_validator(protocol=fixtures.PROTOCOL))
        freeze = a.read(args.frame_freeze)
        result['freeze_binding'] = {key: freeze[key] for key in ('frame_sha256', 'protocol_bundle_sha256', 'frozen_before_first_request')}
        scores = directory / 'SCORES_PRIVATE.json'
        a.write_new(scores, result)
        report_dir = self.directory / 'report'
        a.report_and_queue(argparse.Namespace(frame=args.frame, frame_freeze=args.frame_freeze,
            scores=scores, inputs=args.inputs, exclusions=args.exclusions, output_directory=report_dir))
        requests = list(a.read_metadata(report_dir / 'ASTRA_INPUTS_PRIVATE.jsonl').values())
        reviews = {a.identity(row): row['reference'] for row in cases if row.get('reference')}
        outputs = [{'case': row['case'], 'record_id': a.identity(row)[0], 'context_sha256': a.identity(row)[1],
                    'roster_sha256': a.roster_sha(frame), 'leg': 'Astra',
                    'payload': deepcopy(reviews[a.identity(row)]), 'status': 'field_local_validation_complete'}
                   for row in requests]
        output_path = self.directory / 'ASTRA_OUTPUTS.jsonl'
        a.write_new(output_path, outputs, jsonl=True)
        final = {'leg': 'Astra', 'terminal_no_active_requests': True, 'roster_sha256': a.roster_sha(frame),
                 'output_roster_sha256': a.roster_sha([row['row'] for row in requests]),
                 'outputs_accounted': len(requests), 'logical_calls': len(requests), 'physical_attempts': len(requests),
                 'reserved_nano': 1_000_000_000, 'output_sha256': s.file_sha(output_path),
                 'exclusions_sha256': s.file_sha(args.exclusions[0])}
        final_path = self.directory / 'ASTRA_FINAL.json'
        a.write_new(final_path, final)
        return argparse.Namespace(frame=args.frame, frame_freeze=args.frame_freeze, scores=scores,
            joined_cases=cases_path, join_receipt=directory / 'JOIN_PUBLIC.json',
            astra_inputs=report_dir / 'ASTRA_INPUTS_PRIVATE.jsonl', astra_outputs=output_path,
            astra_final=final_path, exclusions=args.exclusions, repo=s.REPO,
            output=self.directory / 'ASTRA_DIAGNOSTICS_PUBLIC.json')

    def test_diagnostics_do_not_replace_reference_or_primary_scores(self):
        args = self.prepare_diagnostics()
        before = {path: Path(path).read_bytes() for path in (args.scores, args.joined_cases)}
        public = d.diagnose(args)
        for path, value in before.items():
            self.assertEqual(Path(path).read_bytes(), value)
        years = public['measure_diagnostics']['experience.general_work.years']
        self.assertEqual(years['astra_agrees_with_kimi_only'], 2)
        self.assertFalse(public['primary_gates_recomputed'])
        self.assertNotIn('PRIVATE_RECORD_', s.stable(public))

    def test_more_than_six_physical_attempts_rejected(self):
        args = self.prepare_diagnostics()
        final = a.read(args.astra_final)
        final['physical_attempts'] = 7
        alternate = self.directory / 'BAD_FINAL.json'
        a.write_new(alternate, final)
        args.astra_final = alternate
        with self.assertRaisesRegex(ValueError, 'astra_terminal_cap_or_roster_mismatch'):
            d.diagnose(args)


if __name__ == '__main__':
    unittest.main(verbosity=2)
