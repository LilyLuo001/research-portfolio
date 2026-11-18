"""Synthetic offline regression tests: no cloud, model, or real-source access."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import stage5_astra_control as controller


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value, jsonl=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((''.join(json.dumps(x) + '\n' for x in value) if jsonl else json.dumps(value) + '\n'))


class AstraControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.c = Path(self.temp.name) / 'execution_v1'
        self.c.mkdir()
        self.old_path = list(sys.path)
        self.modules = {name: sys.modules.pop(name, None) for name in ('stage5_common', 'cloud_score_adapter', 'field_score')}
        for directory in ('runtime', 'protocol'):
            shutil.copytree(controller.D / directory, self.c / directory, ignore=shutil.ignore_patterns('__pycache__'))
        self.k = self.c / 'kimi_direct_v4'; self.l = self.c / 'luna'; self.s = self.c / 'scoring_v1'
        self.a = self.c / 'astra_diagnostic_v1'
        for directory in (self.k, self.l, self.s):
            directory.mkdir()
        self.protocol = json.loads((self.c / 'protocol/CONFIRMATION_PROTOCOL.json').read_text())
        self.sources = []
        for number in range(135):
            text = 'Synthetic offline source ' + str(number)
            self.sources.append({'case':'case_' + str(number), 'protected':False,
                'row':{'record_id':'SYNTHETIC_PRIVATE_' + str(number),
                       'context_sha256':hashlib.sha256(text.encode()).hexdigest(), 'full_document':text}})
        frame = [dict(case=x['case'], **{key:x['row'][key] for key in ('record_id','context_sha256')}) for x in self.sources]
        write(self.c / 'FRAME_PRIVATE.jsonl', frame, jsonl=True)
        roster = sorted(({key:row[key] for key in ('record_id','context_sha256')} for row in frame), key=lambda row:(row['record_id'],row['context_sha256']))
        self.roster_sha = hashlib.sha256(json.dumps(roster,separators=(',', ':')).encode()).hexdigest()
        frame_freeze = {'frame_sha256':digest(self.c / 'FRAME_PRIVATE.jsonl'),
            'protocol_bundle_sha256':digest(self.c / 'protocol/PROTOCOL_FREEZE.json'),
            'frozen_before_first_request':True, 'context_count':135}
        write(self.c / 'FRAME_FREEZE_PUBLIC.json', frame_freeze)
        write(self.l / 'INPUT_PINS_PUBLIC.json', {'code_sha256':{path.name:digest(path) for path in (self.c / 'runtime').glob('stage5_*.py')}})
        write(self.c / 'EXECUTION_FREEZE_PUBLIC.json', {'frame_count':135,'new_cap_usd':50,'model_calls':0,
            'runtime_input_pin_sha256':digest(self.l / 'INPUT_PINS_PUBLIC.json'),'frame_freeze':frame_freeze})
        for directory, leg in ((self.l,'Luna'),(self.k,'Kimi')):
            write(directory / 'EXCLUSIONS_EXPORT_PRIVATE.json', {'context_sha256':[]})
            write(directory / 'OUTPUTS_PRIVATE.jsonl', [], jsonl=True)
            self.make_ledger(directory)
            final = {'runtime_version':'stage5-bounded-serial-v1','leg':leg,'terminal_no_active_requests':True,
                'outputs_accounted':135,'roster_sha256':self.roster_sha,'output_roster_sha256':self.roster_sha,
                'physical_attempts':0,'logical_calls':0,'reserved_nano':0,'last_forward_epoch':0,
                'output_sha256':digest(directory / 'OUTPUTS_PRIVATE.jsonl'),
                'exclusions_sha256':digest(directory / 'EXCLUSIONS_EXPORT_PRIVATE.json')}
            write(directory / (leg.upper() + '_FINAL_PUBLIC.json'), final)
        write(self.k / 'INPUTS_PRIVATE.jsonl', self.sources, jsonl=True)
        write(self.k / 'SCHEMA.json', {})
        (self.k / 'INSTRUCTIONS.md').write_text('Synthetic offline fixture instructions.')
        queue = []
        for source in self.sources[:2]:
            row = {key:source['row'][key] for key in ('record_id','context_sha256')}
            ranked = [self.protocol['version'], row['record_id'], row['context_sha256']]
            row['rank_sha256'] = hashlib.sha256(json.dumps(ranked,sort_keys=True,separators=(',', ':'),ensure_ascii=False).encode()).hexdigest()
            queue.append(row)
        queue.sort(key=lambda row:(row['rank_sha256'],row['record_id']))
        selected = {x['row']['record_id']:x for x in self.sources}
        requests = [{'case':selected[row['record_id']]['case'],'row':selected[row['record_id']]['row'],
                     'protected':False,'fresh_never_exposed':True,'partition':'confirmation'} for row in queue]
        scores = {'protocol_version':self.protocol['version'],'accounting':{'frame_cases':135},
                  'freeze_binding':frame_freeze,'bounded_astra_diagnostic_queue':queue}
        write(self.s / 'SCORES_PRIVATE.json', scores)
        write(self.s / 'ASTRA_SELECTION_PRIVATE.json', queue)
        write(self.s / 'ASTRA_INPUTS_PRIVATE.jsonl', requests, jsonl=True)
        write(self.s / 'JOINED_CASES_PRIVATE.jsonl', [], jsonl=True)
        write(self.s / 'JOIN_PUBLIC.json', {'cases_sha256':digest(self.s / 'JOINED_CASES_PRIVATE.jsonl')})
        write(self.s / 'SCORING_PUBLIC.json', {'status':'frozen_primary_scored_astra_prepared_not_called',
            'astra_source_only_requests':2,'primary_gate_unchanged':True,'primary_reference_overwritten':False,
            'production_admission':False,'model_calls_by_adapter':0,'scores_sha256':digest(self.s / 'SCORES_PRIVATE.json'),
            'frame_sha256':frame_freeze['frame_sha256'],'protocol_version':self.protocol['version']})
        validators = self.c / 'repo/linkup'
        field = validators / 'reuse_first_20261115/measurement_protocol_20261117/code/field_validation.py'
        frozen = validators / 'formal800_20261012/code/validate_reviews.py'
        field.parent.mkdir(parents=True); field.write_text('# Synthetic field validator fixture.\n')
        frozen.parent.mkdir(parents=True); frozen.write_text('def validate_packet(packets):\n    assert len(packets) <= 6\n')
        base = ('import json,os,sys,hashlib,datetime,subprocess,sqlite3\nfrom pathlib import Path\n'
                'C=Path(' + repr(str(self.c)) + ')\nR=C.parent\nD=C.parent\n'
                'def read(p):return json.loads(p.read_text())\n'
                'def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()\n')
        self.ns = {}
        exec(controller._source(base, ''), self.ns)
        self.ns['worker_active'] = lambda *args:False

    def tearDown(self):
        sys.path[:] = self.old_path
        for name, value in self.modules.items():
            sys.modules.pop(name, None)
            if value is not None:
                sys.modules[name] = value
        self.temp.cleanup()

    def make_ledger(self, directory, state=None, nano=0):
        with sqlite3.connect(directory / 'ADMISSION_PRIVATE.sqlite3') as db:
            db.execute('create table attempts (context text,state text,dollars_nano integer,detail text)')
            if state:
                db.execute('insert into attempts values (?,?,?,?)',('synthetic_context',state,nano,'{}'))

    def action(self, source):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            exec(source, self.ns)
        raw = out.getvalue()
        self.assertLess(len(raw.encode()),4096)
        self.assertNotIn('SYNTHETIC_PRIVATE_',raw)
        self.assertNotIn('Synthetic offline source',raw)
        return json.loads(raw)

    def prepare(self):
        return self.action(controller.PREPARE_ACTION)

    def change_json(self, path, **values):
        data = json.loads(path.read_text()); data.update(values); write(path,data)

    def finish(self, state='response_saved', nano=100_000_000):
        self.prepare()
        self.make_ledger(self.a,state,nano)
        common = sys.modules['stage5_common']; items,pins = common.load_inputs(self.a,'Astra')
        write(self.a / 'OUTPUTS_PRIVATE.jsonl', [{'case':x['case'], 'row':x['row']} for x in items], jsonl=True)
        write(self.a / 'EXCLUSIONS_EXPORT_PRIVATE.json', {'context_sha256':[]})
        final = {'runtime_version':common.VERSION,'leg':'Astra','terminal_no_active_requests':True,
            'outputs_accounted':2,'selected':2,'roster_sha256':pins['roster_sha256'],
            'output_roster_sha256':common.roster_sha256(items),'input_pins_sha256':digest(self.a / 'INPUT_PINS_PUBLIC.json'),
            'output_sha256':digest(self.a / 'OUTPUTS_PRIVATE.jsonl'),
            'exclusions_sha256':digest(self.a / 'EXCLUSIONS_EXPORT_PRIVATE.json'),
            'physical_attempts':1,'logical_calls':1,'reserved_nano':nano,'field_validation_complete':0}
        write(self.a / 'ASTRA_FINAL_PUBLIC.json',final)
        return final

    def diagnostic_public(self, final):
        return {'status':'bounded_astra_diagnostics_only','frame_count':135,'diagnostics_selected':2,
            'source_only_requests':2,'late_blocked_metadata_only':0,'physical_attempts':final['physical_attempts'],
            'reserved_usd':final['reserved_nano']/1e9,'measure_diagnostics':{x['id']:{} for x in self.protocol['measures']},
            'original_primary_scores_sha256':digest(self.s / 'SCORES_PRIVATE.json'),
            'astra_outputs_sha256':final['output_sha256'],'reference_overwritten':False,
            'primary_gates_recomputed':False,'production_admission':False,'new_model_calls_by_diagnostic_tool':0,
            'interpretation':'Third-machine agreement diagnostics; no gold labels or new qualification.'}

    def test_prepare_original_runtime_full_roster_source_subset_idempotent(self):
        first = self.prepare()
        self.assertEqual(first['selected'],2)
        self.assertEqual(len(json.loads((self.a / 'FRAME_ROSTER_PRIVATE.json').read_text())),135)
        self.assertEqual(digest(self.a / 'KIMI_FINAL_PUBLIC.json'),digest(self.k / 'KIMI_FINAL_PUBLIC.json'))
        self.assertFalse((self.a / 'ADMISSION_PRIVATE.sqlite3').exists())
        self.assertEqual(self.prepare(),first)

    def test_zero_seven_and_boolean_request_count_rejected(self):
        for count in (0,7,True):
            self.change_json(self.s / 'SCORING_PUBLIC.json',astra_source_only_requests=count)
            with self.assertRaisesRegex(AssertionError,'one_to_six'):
                self.prepare()
        self.assertFalse(self.a.exists())

    def test_kimi_nonterminal_blocks_preparation(self):
        self.change_json(self.k / 'KIMI_FINAL_PUBLIC.json',terminal_no_active_requests=False)
        with self.assertRaises(AssertionError):
            self.prepare()
        self.assertFalse(self.a.exists())

    def test_source_only_rejects_candidate_contamination(self):
        path=self.s / 'ASTRA_INPUTS_PRIVATE.jsonl'
        rows=[json.loads(x) for x in path.read_text().splitlines()]
        rows[0]['candidate']={'secret':'synthetic prior review'}
        write(path,rows,jsonl=True)
        with self.assertRaisesRegex(AssertionError,'source_only_packet'):
            self.prepare()

    def test_frozen_runtime_mutation_rejected(self):
        with (self.c / 'runtime/stage5_common.py').open('a') as out:
            out.write('\n# Modified synthetic copy\n')
        with self.assertRaisesRegex(AssertionError,'frozen_runtime_or_protocol_changed'):
            self.prepare()

    def test_launch_runs_only_original_worker_and_is_at_most_once(self):
        self.prepare()
        with patch('subprocess.Popen',return_value=types.SimpleNamespace(pid=4242)) as popen:
            result=self.action(controller.LAUNCH_ACTION)
            self.assertEqual(result['pid'],4242)
            argv=popen.call_args.args[0]
            self.assertIn(str(self.c / 'runtime/stage5_cloud_worker.py'),argv)
            self.assertIn(str(self.a),argv)
            self.assertEqual(argv[argv.index('--leg')+1],'Astra')
            with self.assertRaisesRegex(AssertionError,'no_resubmission'):
                self.action(controller.LAUNCH_ACTION)
            self.assertEqual(popen.call_count,1)

    def test_interrupted_launch_retains_intent_and_forbids_retry(self):
        self.prepare()
        with patch('subprocess.Popen',side_effect=OSError('synthetic spawn failure')) as popen:
            with self.assertRaisesRegex(AssertionError,'launch_failed_intent_retained'):
                self.action(controller.LAUNCH_ACTION)
            self.assertTrue((self.c / 'ASTRA_LAUNCH_INTENT_PRIVATE.json').exists())
            self.assertTrue((self.c / 'ASTRA_LAUNCH_FAILURE_PRIVATE.json').exists())
            with self.assertRaisesRegex(AssertionError,'no_resubmission'):
                self.action(controller.LAUNCH_ACTION)
            self.assertEqual(popen.call_count,1)

    def test_existing_admission_blocks_launch(self):
        self.prepare(); self.make_ledger(self.a)
        with patch('subprocess.Popen') as popen:
            with self.assertRaisesRegex(AssertionError,'prior_astra_admission'):
                self.action(controller.LAUNCH_ACTION)
            popen.assert_not_called()

    def test_primary_mutation_after_prepare_blocks_launch(self):
        self.prepare()
        self.change_json(self.s / 'JOIN_PUBLIC.json',other='changed')
        with patch('subprocess.Popen') as popen:
            with self.assertRaisesRegex(AssertionError,'binding_changed'):
                self.action(controller.LAUNCH_ACTION)
            popen.assert_not_called()

    def test_status_requires_terminal_ledger_and_preserves_caps(self):
        self.finish()
        result=self.action(controller.STATUS_ACTION)
        self.assertTrue(result['terminal_no_active_requests'])
        self.assertEqual(result['physical_attempts'],1)
        self.assertEqual(result['outputs_accounted'],2)

    def test_diagnostic_rejects_uncertain_admission(self):
        self.finish(state='transport_uncertain_no_retry')
        with self.assertRaises(AssertionError):
            self.action(controller.DIAGNOSE_ACTION)
        self.assertFalse((self.s / 'ASTRA_DIAGNOSTIC_PUBLIC.json').exists())

    def test_diagnostic_rejects_over_budget(self):
        self.finish(nano=8_000_000_001)
        with self.assertRaisesRegex(AssertionError,'cap_breach'):
            self.action(controller.DIAGNOSE_ACTION)

    def test_seventh_physical_attempt_rejected(self):
        self.finish()
        with sqlite3.connect(self.a / 'ADMISSION_PRIVATE.sqlite3') as db:
            db.executemany('insert into attempts values (?,?,?,?)',
                [('synthetic_context','response_saved',0,'{}')]*6)
        with self.assertRaisesRegex(AssertionError,'cap_breach'):
            self.action(controller.STATUS_ACTION)

    def test_diagnostic_transport_is_aggregate_and_primary_unchanged(self):
        final=self.finish(); before={name:digest(self.s / name) for name in ('SCORES_PRIVATE.json','JOINED_CASES_PRIVATE.jsonl','SCORING_PUBLIC.json')}
        public=self.diagnostic_public(final)
        self.ns['run_private']=lambda command,name:write(self.s / 'ASTRA_DIAGNOSTIC_PUBLIC.json',public)
        raw=(json.dumps(public)+'\n').encode()
        class Response:
            status=200
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,limit): return raw
        calls=[]
        def call(*args,**kwargs):
            calls.append((args,kwargs)); return Response()
        with patch.dict(sys.modules,{'workflow':types.SimpleNamespace(call=call)}):
            result=self.action(controller.DIAGNOSE_ACTION)
        self.assertEqual(result['sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(len(calls),2)
        self.assertFalse(result['reference_overwritten'])
        self.assertFalse(result['production_admission'])
        self.assertEqual(before,{name:digest(self.s / name) for name in before})

    def test_public_diagnostic_rejects_identifier_or_gate_changes(self):
        final=self.finish(); public=self.diagnostic_public(final)
        measures=[x['id'] for x in self.protocol['measures']]
        controller.validate_diagnostic(public,measures)
        for changes in ({'record_id':'PRIVATE'}, {'production_admission':True}, {'primary_gates_recomputed':True}, {'physical_attempts':7}):
            with self.assertRaises(AssertionError):
                controller.validate_diagnostic(dict(public,**changes),measures)

    def test_download_verifies_private_blob_and_immutable_local_copy(self):
        final=self.finish(); public=self.diagnostic_public(final)
        raw=(json.dumps(public)+'\n').encode()
        transport={'status':'bounded_Astra_diagnostic_summary_verified','blob_key':controller.BLOB_KEY,
            'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'original_primary_scores_sha256':public['original_primary_scores_sha256'],
            'source_only_requests':2,'physical_attempts':1,'reserved_usd':.1}
        write(self.c / 'control/ASTRA_DIAGNOSTIC_TRANSPORT_PUBLIC.json',transport)
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,limit): return raw
        fake=types.SimpleNamespace(HOST='https://synthetic.invalid',CONTAINER='private',
                                  call=lambda *args,**kwargs:Response(),storage_token=lambda:'synthetic-token')
        with patch.object(controller,'D',self.c), patch.dict(sys.modules,{'storage_transport':fake}):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                first=controller.download(None,None)
                second=controller.download(None,None)
            self.assertEqual(first,second)
            self.assertNotIn('synthetic-token',out.getvalue())
            self.assertEqual((self.c / 'ASTRA_DIAGNOSTIC_PUBLIC.json').read_bytes(),raw)
            (self.c / 'ASTRA_DIAGNOSTIC_PUBLIC.json').write_text('conflicting fixture')
            with self.assertRaisesRegex(AssertionError,'local_diagnostic_conflict'):
                controller.download(None,None)

    def test_duplicate_diagnostic_keys_rejected_before_download_save(self):
        with self.assertRaisesRegex(AssertionError,'duplicate_diagnostic_key'):
            controller.parse_diagnostic('{"status":"private hidden text","status":"bounded_astra_diagnostics_only"}')

    def test_all_dispatch_sources_compile_offline(self):
        for action in (controller.PREPARE_ACTION,controller.LAUNCH_ACTION,controller.STATUS_ACTION,controller.DIAGNOSE_ACTION):
            compile(controller._source('',action),'<synthetic-dispatch>','exec')


if __name__ == '__main__':
    unittest.main(verbosity=2)
