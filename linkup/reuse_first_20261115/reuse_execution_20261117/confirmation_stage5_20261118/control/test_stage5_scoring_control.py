"""Offline engineering regressions; synthetic data only, no cloud/auth/model calls."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'protocol'
RUNTIME = ROOT / 'runtime_direct_v4'
sys.path[:0] = [str(PROTOCOL), str(RUNTIME)]
import field_score as scorer
import stage5_common as common
import test_field_score as fixtures
import test_cloud_score_adapter as adapter_fixtures
spec = importlib.util.spec_from_file_location('scoring_controller_test_target', ROOT / 'control/stage5_scoring_control.py')
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


class Capture:
    def vm(self, source, name):
        self.source = source
        return {}
    def save(self, *args):
        pass


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stage5-controller-offline-')
        self.c = Path(self.temp.name)  # Deliberately keep macOS /var path alias.
        self.p = self.c / 'protocol'
        self.k = self.c / 'kimi_direct_v4'
        self.s = self.c / 'scoring_v1'
        for path in (self.p, self.k, self.s):
            path.mkdir()
        # Reproduce the original cloud installer exactly: these two companion
        # files were not uploaded by freeze_runtime_cloud.py.
        for name in ('field_score.py', 'CONFIRMATION_PROTOCOL.json', 'PROTOCOL_FREEZE.json'):
            shutil.copy2(PROTOCOL / name, self.p / name)
        (self.k / 'OUTPUTS_PRIVATE.jsonl').write_bytes(b'')
        common.save(self.k / 'KIMI_FINAL_PUBLIC.json', {
            'terminal_no_active_requests': True, 'outputs_accounted': 135,
            'output_sha256': common.sha(self.k / 'OUTPUTS_PRIVATE.jsonl')})
        self.capture = Capture()
        with contextlib.redirect_stdout(io.StringIO()):
            controller.score(self.capture, '')
        self.environment = {'C': self.c, 'R': self.c / 'unused-no-auth',
            'read': common.read, 'sha': common.sha, 'os': os, 'sys': sys,
            'subprocess': subprocess, 'hashlib': hashlib, 'json': json, 'Path': Path}
        self.install_prefix = self.capture.source.split("\nrepo=C/'repo';", 1)[0]
        self.bundle = common.read(PROTOCOL / 'PROTOCOL_FREEZE.json')
        self.original_hashes = {n: common.sha(PROTOCOL / n) for n in self.bundle['files']}

    def tearDown(self):
        self.assertEqual(self.original_hashes, {n: common.sha(PROTOCOL / n) for n in self.bundle['files']})
        self.temp.cleanup()

    def execute(self, prefix=False):
        source = self.install_prefix if prefix else self.capture.source
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(source, '<captured-controller-offline>', 'exec'), self.environment)

    def test_missing_companions_install_exactly_and_idempotently(self):
        for name in ('README.md', 'test_field_score.py'):
            self.assertFalse((self.p / name).exists())
        self.execute(prefix=True)
        hashes = {n: common.sha(self.p / n) for n in self.bundle['files']}
        self.assertEqual(hashes, self.bundle['files'])
        self.execute(prefix=True)
        self.assertEqual(hashes, {n: common.sha(self.p / n) for n in hashes})

    def test_different_existing_companion_is_not_overwritten(self):
        target = self.p / 'README.md'
        target.write_bytes(b'SYNTHETIC_CONFLICT')
        with self.assertRaisesRegex(AssertionError, 'immutable_protocol_or_adapter_conflict'):
            self.execute(prefix=True)
        self.assertEqual(target.read_bytes(), b'SYNTHETIC_CONFLICT')

    def test_existing_freeze_is_never_replaced(self):
        target = self.p / 'PROTOCOL_FREEZE.json'
        target.write_bytes(b'{"changed":"SYNTHETIC"}')
        with self.assertRaisesRegex(AssertionError, 'existing_protocol_freeze_mismatch'):
            self.execute(prefix=True)
        self.assertEqual(target.read_bytes(), b'{"changed":"SYNTHETIC"}')
        self.assertFalse((self.p / 'README.md').exists())

    def test_changed_local_companion_fails_before_dispatch(self):
        local = self.c / 'fake-local'
        protocol = local / 'protocol'
        protocol.mkdir(parents=True)
        for name in ('PROTOCOL_FREEZE.json', 'test_field_score.py'):
            shutil.copy2(PROTOCOL / name, protocol / name)
        (protocol / 'README.md').write_bytes(b'SYNTHETIC_LOCAL_CONFLICT')
        capture = Capture()
        with patch.object(controller, 'D', local), self.assertRaisesRegex(AssertionError, 'local_frozen_companion_mismatch'):
            controller.score(capture, '')
        self.assertFalse(hasattr(capture, 'source'))

    def test_actual_135_case_CLI_chain_missing_companions_and_resume(self):
        v = self.c / 'runtime_direct_v4'
        l = self.c / 'luna'
        v.mkdir(); l.mkdir()
        for name in common.RUNTIME_FILES:
            shutil.copy2(RUNTIME / name, v / name)
        repo = self.c / 'repo'
        repo.symlink_to(scorer.REPO, target_is_directory=True)
        frame_fixture = adapter_fixtures.AdapterTests()
        frame_fixture.directory = self.c
        packets, frame, inputs = frame_fixture.make_frame(135)
        roster = common.roster_sha256(inputs)
        common.save(l / 'EXCLUSIONS_EXPORT_PRIVATE.json', {'context_sha256': [], 'tasks': []})
        luna, kimi = [], []
        for item, packet in zip(inputs, packets):
            fields = {'case': item['case'], 'record_id': packet['record_id'],
                'context_sha256': packet['context_sha256'], 'roster_sha256': roster,
                'field_validation': None}
            luna.append(dict(fields, leg='Luna', payload=fixtures.positive(packet), status='field_local_validation_complete'))
            kimi.append(dict(fields, leg='Kimi', payload=None, status='response_saved',
                response_text=json.dumps(fixtures.positive(packet)), transport=None))
        def write_lines(path, rows):
            path.write_bytes(b''.join(common.encoded(row) + b'\n' for row in rows))
        write_lines(l / 'OUTPUTS_PRIVATE.jsonl', luna)
        final = {'runtime_version': common.VERSION, 'leg': 'Luna', 'terminal_no_active_requests': True,
            'reserved_nano': 0, 'roster_sha256': roster, 'output_roster_sha256': roster,
            'outputs_accounted': 135, 'output_sha256': common.sha(l / 'OUTPUTS_PRIVATE.jsonl'),
            'exclusions_sha256': common.sha(l / 'EXCLUSIONS_EXPORT_PRIVATE.json'), 'last_forward_epoch': 0}
        common.save(l / 'LUNA_FINAL_PUBLIC.json', final)
        # Remove setup's synthetic terminal placeholders before immutable prepare.
        (self.k / 'OUTPUTS_PRIVATE.jsonl').unlink()
        (self.k / 'KIMI_FINAL_PUBLIC.json').unlink()
        protocol = common.read(PROTOCOL / 'CONFIRMATION_PROTOCOL.json')
        instructions = next(x['path'] for x in protocol['source_files'] if Path(x['path']).name == 'REVIEW_INSTRUCTIONS.md')
        command = [sys.executable, '-B', str(v / 'stage5_prepare.py'), '--leg', 'Kimi', '--directory', str(self.k),
            '--inputs', str(self.c / 'INPUTS.jsonl'), '--roster', str(self.c / 'FRAME_PRIVATE.jsonl'),
            '--schema', str(repo / protocol['schema']), '--instructions', str(repo / instructions),
            '--exclusions', str(l / 'EXCLUSIONS_EXPORT_PRIVATE.json'),
            '--field-validator', str(repo / protocol['field_validator']),
            '--frozen-validator', str(repo / protocol['frozen_validator']),
            '--predecessor-receipt', str(l / 'LUNA_FINAL_PUBLIC.json'),
            '--predecessor-exclusions', str(l / 'EXCLUSIONS_EXPORT_PRIVATE.json')]
        prepared = subprocess.run(command, capture_output=True, text=True, timeout=90)
        self.assertEqual(prepared.returncode, 0, 'synthetic prepare failed')
        write_lines(self.k / 'OUTPUTS_PRIVATE.jsonl', kimi)
        shutil.copy2(self.k / 'EXCLUSIONS_PRIVATE.json', self.k / 'EXCLUSIONS_EXPORT_PRIVATE.json')
        common.save(self.k / 'KIMI_FINAL_PUBLIC.json', dict(final, leg='Kimi',
            output_sha256=common.sha(self.k / 'OUTPUTS_PRIVATE.jsonl'),
            exclusions_sha256=common.sha(self.k / 'EXCLUSIONS_EXPORT_PRIVATE.json')))
        # Prevent any cloud/storage import: the generated code takes its existing
        # transport-receipt branch only after completing all real offline CLIs.
        common.save(self.s / 'SCORING_TRANSPORT_PUBLIC.json', {'status': 'OFFLINE_STORAGE_BRANCH_DISABLED'})
        self.execute()
        for phase in ('KIMI_VALIDATION', 'JOIN', 'FROZEN_PRIMARY_SCORE', 'REPORT'):
            self.assertEqual(common.read(self.s / (phase + '_EXECUTION_PRIVATE.json'))['returncode'], 0)
        self.assertEqual(common.read(self.k / 'VALIDATION_PUBLIC.json')['field_validation_complete'], 135)
        self.assertFalse(common.read(self.s / 'SCORING_PUBLIC.json')['production_admission'])
        saved = {p.name: common.sha(p) for p in self.s.iterdir() if p.is_file()}
        self.execute()
        self.assertEqual(saved, {p.name: common.sha(p) for p in self.s.iterdir() if p.is_file()})
        terminal = common.read(self.k / 'KIMI_FINAL_PUBLIC.json')
        terminal['terminal_no_active_requests'] = False
        common.save(self.k / 'KIMI_FINAL_PUBLIC.json', terminal)
        with self.assertRaises(AssertionError):
            self.execute()


if __name__ == '__main__':
    unittest.main()
