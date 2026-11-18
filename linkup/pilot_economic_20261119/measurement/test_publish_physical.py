import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import publish_physical as p


class ProjectionTests(unittest.TestCase):
    def test_synthetic_conservation_independent_field_and_protection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            batch = root / 'preparation/batch0001'
            batch.mkdir(parents=True)
            (root / 'measurement').mkdir()
            text = 'Synthetic fixture only.'
            h = hashlib.sha256(text.encode()).hexdigest()
            ids = ['valid', 'invalid']
            release_sha = p.write(root / 'measurement/ECONOMIC_RELEASE_PUBLIC.json', {
                'released_measure_ids': ids, 'released_measures': [{'spec': {'id': x}} for x in ids]})
            inputs = [{'row': {'full_document': text, 'context_sha256': h}}]
            mappings = [{'physical_row_id': str(i), 'context_sha256': h, 'state': state}
                        for i, state in enumerate(['new_context_prepared', 'duplicate_context', 'protected'])]
            manifest = {'batch_id': 'batch0001', 'cumulative_physical_rows': 3, 'filenames': {}}
            for name, obj in [('inputs', inputs), ('physical_rows', mappings), ('exclusions', {})]:
                file = name + '.json'
                manifest['filenames'][name] = file
                manifest[name + '_sha256'] = p.write(batch / file, obj, name != 'exclusions')
            manifest_sha = p.write(batch / 'BATCH_MANIFEST_PUBLIC.json', manifest)
            cpu_sha = p.write(batch / 'CPU_RULE_RESULTS_PRIVATE.jsonl', [{'context_sha256':h, 'result': {'candidate_only':True}}], True)
            p.write(batch / 'CPU_RULE_RECEIPT_PUBLIC.json', {'input_sha256':manifest['inputs_sha256'], 'output_sha256':cpu_sha})
            policy_sha = p.write(root / 'policy.json', {'released_measure_ids': ids,
                'initial_batch_manifest_sha256': manifest_sha,
                'pins': {'measurement/ECONOMIC_RELEASE_PUBLIC.json': release_sha}})
            result = {'context_sha256': h, 'payload': {}, 'field_validation': {}, 'status': 'field_local_validation_complete', 'leg': 'Luna', 'policy_sha256': policy_sha}
            digest = p.write(root / 'RESULT.json', result)
            db = sqlite3.connect(root / 'ADMISSION_PRIVATE.sqlite3')
            db.execute('create table attempts(id integer, leg text, context text, result_path text, result_sha text)')
            db.execute('create table meta(key text, value text)')
            db.execute('insert into meta values(?,?)', ('identity', json.dumps({'policy_sha256': policy_sha})))
            db.execute('create table batches(id text, sha text)')
            db.execute('create table quarantine(context text, reason text)')
            db.execute('insert into batches values(?,?)', ('batch0001', manifest_sha))
            db.execute('insert into attempts values(1,?,?,?,?)', ('Luna', h, 'RESULT.json', digest))
            db.commit()
            db.close()
            scorer = root / 'scorer.py'
            scorer.write_text("def source_units(text): return []\ndef observe(review,validation,spec,*args,**kwargs):\n return {'status':'known','outcome':'present'} if spec['id']=='valid' else {'status':'invalid_local','outcome':'unknown'}\n")
            frozen = root / 'frozen.py'
            frozen.write_text('# synthetic no-op\n')
            out = root / 'output'
            args = argparse.Namespace(directory=root, through_batch='batch0001', output=out,
                                      scorer=scorer, scorer_sha256=p.sha(scorer),
                                      frozen_validator=frozen, frozen_validator_sha256=p.sha(frozen))
            with contextlib.redirect_stdout(io.StringIO()):
                p.project(args)
            result = p.lines(out / 'PHYSICAL_INCREMENT_PRIVATE.jsonl')
            self.assertEqual(len(result), 3)
            for row in result[:2]:
                fields = row['semantic_context_result']['measurements']
                self.assertEqual(fields['valid']['value'], 1)
                self.assertIsNone(fields['invalid']['value'])
                self.assertEqual(fields['valid']['structured_atoms_status'], 'saved_unverified')
            self.assertIsNone(result[2]['semantic_context_result'])
            self.assertEqual(result[2]['semantic_status'], 'protected')
            with self.assertRaises(FileExistsError), contextlib.redirect_stdout(io.StringIO()):
                p.project(args)
            db = sqlite3.connect(root / 'ADMISSION_PRIVATE.sqlite3')
            db.execute('insert into quarantine values(?,?)', (h, 'synthetic_provider_filter'))
            db.commit(); db.close()
            args.output = root / 'projection_after_quarantine'
            with contextlib.redirect_stdout(io.StringIO()):
                p.project(args)
            for row in p.lines(args.output / 'PHYSICAL_INCREMENT_PRIVATE.jsonl'):
                self.assertEqual(row['semantic_status'], 'quarantined_current_runtime')
                self.assertIsNone(row['semantic_context_result'])
                self.assertIsNone(row['CPU_context_result'])


if __name__ == '__main__':
    unittest.main()
