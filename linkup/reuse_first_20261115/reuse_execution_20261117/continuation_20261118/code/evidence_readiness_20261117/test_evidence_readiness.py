"""Synthetic only: no LinkUp advertisement payloads or cloud services."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

import cloud_evidence_readiness as module


def h(x):
    return hashlib.sha256(x.encode()).hexdigest()


def fixture(root, count=3, denied_runtime=(), denied_original=(), denied_reuse=(),
            denied_context_protected=(), bad_anchor=()):
    r = root / "reuse_execution_20261117/run001"
    s = root / "execution_20261116/run001"
    r.mkdir(parents=True); s.mkdir(parents=True)
    source = r / "LINKUP_REUSED_VARIABLES_V1_PRIVATE.sqlite"
    d = sqlite3.connect(source)
    d.executescript("""
    CREATE TABLE context_state(h TEXT PRIMARY KEY,reuse_excluded INTEGER,original_protected INTEGER);
    CREATE TABLE source_document(d TEXT PRIMARY KEY,h TEXT,k TEXT,asset TEXT,source_sha TEXT,source_ordinal INTEGER);
    CREATE TABLE variable_value(id TEXT PRIMARY KEY,d TEXT,h TEXT,k TEXT,variable_key TEXT,source_path TEXT,
       item_anchor_json TEXT,dimension TEXT,value_json TEXT,value_present INTEGER,measurement_state TEXT,
       workflow_state TEXT,engineering_state TEXT,eligible_original_scope INTEGER,derived INTEGER,original_mask TEXT,metadata_json TEXT);
    CREATE INDEX variable_key ON variable_value(variable_key);
    CREATE INDEX variable_context ON variable_value(h,variable_key);
    """)
    forbidden = set(denied_runtime)|set(denied_original)|set(denied_reuse)|set(denied_context_protected)
    for i in range(count):
        context, src, doc = h('context'+str(i)), h('source'+str(i)), h('document'+str(i))
        anchor = {"context_sha256":context,"source_sha":src,"source_ordinal":i,
                  "array_path":"experience_clauses","item_index":0,"anchor_id":h('anchor'+str(i))}
        if i in bad_anchor:
            anchor["context_sha256"] = h('wrong')
        value = {"quotes":["test"],"source_item_anchor":anchor,
                 "verification":"retained_original_not_reverified_against_full_text",
                 "evidence_resolution":[{"path":"/experience_clauses/0/quotes/0","quote":"test",
                    "occurrences":[{"start":1,"end":5}],"offset_unit":"Unicode_code_points",
                    "repeated_ambiguity":False}]}
        # Forbidden rows contain invalid JSON so accidental parsing cannot pass.
        raw = '{forbidden payload must never be parsed' if i in forbidden or i in bad_anchor else json.dumps(value)
        d.execute("INSERT INTO context_state VALUES(?,?,?)", (context,int(i in denied_reuse),int(i in denied_context_protected)))
        d.execute("INSERT INTO source_document VALUES(?,?,?,?,?,?)", (doc,context,'ad'+str(i),'synthetic',src,i))
        values = (h('atom'+str(i)),doc,context,'ad'+str(i),'lk.evidence.ref','experience_clauses[0].quotes',json.dumps(anchor),
                  None,raw,1,'known' if i%2==0 else 'unknown','original_accepted' if i%2==0 else 'saved_unverified',
                  'retained',int(i%2==0),0,'known' if i%2==0 else 'unknown',json.dumps({'source_family':'synthetic','new_semantic_acceptance_granted':False}))
        d.execute("INSERT INTO variable_value VALUES("+','.join('?' for _ in values)+")",values)
    d.commit(); d.close()
    old = s/'ORIGINAL.sqlite'; d=sqlite3.connect(old);d.execute('CREATE TABLE protected(h TEXT PRIMARY KEY)')
    d.executemany('INSERT INTO protected VALUES(?)',[(h('context'+str(i)),) for i in denied_original]);d.commit();d.close()
    runtime=s/'EXCLUSIONS_PRIVATE.json';runtime.write_text(json.dumps({'context_sha256':[h('context'+str(i)) for i in denied_runtime],'tasks':[]}))
    state=s/'AZURE_RESEARCH_STATE.json';state.write_text(json.dumps({'runtime_exclusions_relative_to_migration':str(runtime.relative_to(root)),'database_relative_to_migration':str(old.relative_to(root))}))
    (r/'STEP1_RELEASE_PUBLIC.json').write_text(json.dumps({'first_materialized_release_complete':True,'private_output_bytes':source.stat().st_size,'private_output_sha256':h('previous_release_digest')}))
    return source, runtime


class DeclarationTests(unittest.TestCase):
    def setUp(self):
        self.anchor={'anchor_id':h('anchor')}
        self.value={'source_item_anchor':self.anchor,'quotes':['test'],
                    'evidence_resolution':[{'path':'/experience_clauses/0/quotes/0','quote':'test',
                        'occurrences':[{'start':2,'end':6}],'offset_unit':'Unicode_code_points','repeated_ambiguity':False}]}

    def inspect(self):
        return module.inspect_declarations(json.dumps(self.value),'experience_clauses[0].quotes',self.anchor)

    def test_single_declaration_is_not_reverification(self):
        r=self.inspect();self.assertEqual(r['state'],'all_quotes_have_retained_single_position_declarations')
        self.assertFalse(r['full_text_reverified']);self.assertFalse(r['new_semantic_acceptance'])

    def test_exact_pointer_required_not_quote_only(self):
        self.value['evidence_resolution'][0]['path']='/experience_clauses/1/quotes/0'
        self.assertEqual(self.inspect()['bound_quote_declarations'],0)

    def test_exact_quote_required_not_path_only(self):
        self.value['evidence_resolution'][0]['quote']='xxxx'
        self.assertEqual(self.inspect()['bound_quote_declarations'],0)

    def test_duplicate_pointer_unresolved(self):
        self.value['evidence_resolution']*=2
        self.assertEqual(self.inspect()['bound_quote_declarations'],0)

    def test_repeat_preserved_not_arbitrarily_selected(self):
        d=self.value['evidence_resolution'][0];d['occurrences'].append({'start':8,'end':12});d['repeated_ambiguity']=True
        r=self.inspect();self.assertEqual(r['declared_occurrences'],2)
        self.assertEqual(r['state'],'all_quotes_have_retained_repeated_position_declarations')

    def test_boolean_offsets_are_invalid(self):
        self.value['evidence_resolution'][0]['occurrences'][0]['start']=True
        self.assertEqual(self.inspect()['state'],'retained_offsets_present_but_internally_inconsistent')

    def test_wrong_length_is_not_valid_declaration(self):
        self.value['evidence_resolution'][0]['occurrences'][0]['end']=7
        self.assertEqual(self.inspect()['bound_quote_declarations'],0)

    def test_unknown_offset_unit(self):
        self.value['evidence_resolution'][0]['offset_unit']='bytes'
        self.assertEqual(self.inspect()['bound_quote_declarations'],0)

    def test_absent_resolution_is_quotes_only(self):
        self.value['evidence_resolution']=None
        self.assertEqual(self.inspect()['state'],'retained_quotes_without_offset_declarations')

    def test_unknown_resolution_shape_not_guessed(self):
        self.value['evidence_resolution']={'start':2,'end':6}
        self.assertEqual(self.inspect()['state'],'resolution_shape_unrecognized_or_over_limit')

    def test_empty_quotes_not_a_negative(self):
        self.value['quotes']=[]
        self.assertEqual(self.inspect()['state'],'empty_quote_list_not_a_negative_or_complete_review')

    def test_source_anchor_must_agree(self):
        self.value['source_item_anchor']={}
        self.assertEqual(self.inspect()['state'],'value_anchor_mismatch_or_unknown_shape')

    def test_path_grammar(self):
        self.assertEqual(module.quote_pointer('qualification_alternatives[2].branches[3].quotes',1),'/qualification_alternatives/2/branches/3/quotes/1')
        self.assertIsNone(module.quote_pointer('ambiguous path',0))


class SidecarTests(unittest.TestCase):
    def test_cap_and_idempotence_preserve_original(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source,_=fixture(root,3);before=source.read_bytes();out=root/'audit'
            a=module.run(root,out,max_atoms=2);b=module.run(root,out,max_atoms=2)
            self.assertEqual(a['status'],'atom_cap_reached_cursor_preserved')
            self.assertEqual(a['remaining_allowed_evidence_atoms'],1)
            self.assertEqual(a['processed_evidence_atoms'],b['processed_evidence_atoms'])
            self.assertEqual(a['cursor_rowid'],b['cursor_rowid']);self.assertEqual(before,source.read_bytes())

    def test_all_protection_sources_excluded_before_payload(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);fixture(root,6,denied_runtime=[0],denied_original=[1],denied_reuse=[2],denied_context_protected=[3])
            r=module.run(root,root/'audit')
            self.assertEqual(r['excluded_context_union'],4);self.assertEqual(r['excluded_evidence_atoms'],4)
            self.assertEqual(r['processed_evidence_atoms'],2);self.assertEqual(r['remaining_allowed_evidence_atoms'],0)
            self.assertNotIn('invalid_saved_value_json',r['state_counts'])

    def test_missing_protection_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);_,runtime=fixture(root);runtime.unlink()
            with self.assertRaises(FileNotFoundError):module.run(root,root/'audit')
            self.assertFalse((root/'audit/EVIDENCE_READINESS_V1_PRIVATE.sqlite').exists())

    def test_bad_anchor_payload_not_read(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);fixture(root,2,bad_anchor=[1]);r=module.run(root,root/'audit')
            self.assertEqual(r['state_counts']['source_trace_incomplete_payload_not_read'],1)
            self.assertNotIn('invalid_saved_value_json',r['state_counts'])

    def test_original_states_retained_and_no_acceptance(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);fixture(root,2);out=root/'audit';r=module.run(root,out)
            db=sqlite3.connect(out/'EVIDENCE_READINESS_V1_PRIVATE.sqlite')
            self.assertEqual(db.execute('SELECT SUM(new_semantic_acceptance),SUM(full_text_reverified) FROM evidence_readiness').fetchone(),(0,0))
            self.assertEqual(db.execute("SELECT original_mask,original_eligible_scope FROM evidence_readiness WHERE original_workflow_state='saved_unverified'").fetchone(),('unknown',0));db.close()
            self.assertFalse(r['entire_delivery_or_all_variables_complete'])

    def test_changed_protection_snapshot_cannot_resume(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);_,runtime=fixture(root);out=root/'audit';module.run(root,out,max_atoms=1)
            runtime.write_text(json.dumps({'context_sha256':[h('new_protected')],'tasks':[]}))
            with self.assertRaisesRegex(ValueError,'pins_changed'):module.run(root,out,max_atoms=1)

    def test_missing_index_does_not_fall_back_to_table_scan(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source,_=fixture(root);db=sqlite3.connect(source);db.execute('DROP INDEX variable_key');db.commit();db.close()
            with self.assertRaisesRegex(ValueError,'required_existing_index'):module.run(root,root/'audit')

    def test_above_authorized_cap_rejected(self):
        with self.assertRaises(ValueError):module.run(Path('/unused'),Path('/unused'),max_atoms=200001)

    def test_sidecar_actual_sha_after_close(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);fixture(root,2);out=root/'audit';r=module.run(root,out)
            self.assertEqual(r['output_database_sha256'],hashlib.sha256((out/'EVIDENCE_READINESS_V1_PRIVATE.sqlite').read_bytes()).hexdigest())
            self.assertEqual(r['output_hash_status'],'complete')

    def test_deadline_rolls_back_partial_batch_and_keeps_cursor(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);fixture(root,3);out=root/'audit'
            inspect=module.inspect_declarations
            def slow(*args):
                time.sleep(.2)
                return inspect(*args)
            with mock.patch.object(module,'inspect_declarations',slow):
                r=module.run(root,out,max_seconds=.05)
            self.assertEqual(r['status'],'time_cap_reached_cursor_preserved')
            self.assertEqual(r['processed_evidence_atoms'],0)
            self.assertEqual(r['cursor_rowid'],0)
            self.assertEqual(r['remaining_allowed_evidence_atoms'],3)

    def test_existing_index_query_plan_uses_range(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source,_=fixture(root,2);db=sqlite3.connect(source)
            plan=db.execute("EXPLAIN QUERY PLAN SELECT rowid,id FROM variable_value INDEXED BY variable_key WHERE variable_key=? AND rowid>? ORDER BY rowid LIMIT ?",('lk.evidence.ref',0,100)).fetchall();db.close()
            details=' '.join(str(r[-1]) for r in plan)
            self.assertIn('USING INDEX variable_key',details)
            self.assertNotIn('TEMP B-TREE',details)


if __name__=='__main__':
    unittest.main()
