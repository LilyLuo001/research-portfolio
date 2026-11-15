"""Offline synthetic regression tests; no private ads, cloud or model calls."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare_benchmark', HERE/'cloud_prepare_benchmark.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SCHEMA = Path('/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git/linkup/corpus_pro_review_20261026/code/FORMAL800_REVIEW_SCHEMA.json')


def save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False)+'\n')


def lines(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in rows))


def fixture(root, all_unknown=False, protected_alias=False):
    base=root/'opencode_kimi_20261115/run01/bulk_1309_20261115'
    audit=base/'human_audit';results=base.parent/'results/bulk1309'
    schema=json.loads(SCHEMA.read_text())
    schema_path=root/'astra/extraction/FORMAL800_REVIEW_SCHEMA.json';save(schema_path,schema)
    inst=root/'astra/extraction/REVIEW_INSTRUCTIONS.md';inst.write_text('Synthetic instructions only.\n')
    validator=root/'code/validate_reviews.py';validator.parent.mkdir(parents=True);validator.write_text('# synthetic validator fixture\n')
    pins={str(p.relative_to(root)):module.sha(p) for p in (schema_path,inst,validator)}
    old=root/'astra/extraction/STATE_PRIVATE.json';save(old,{'accepted':{}})
    policy=root/'research_policy_20261115_ai_review/POLICY_V4_ECONOMICS_FIRST_PUBLIC.json'
    save(policy,{'human_review_required':False,'frozen_business_schema_and_evidence_rules_preserved':True,
                 'execution':{'no_protected_content_reroute_or_reinference':True}})
    bodies=[f'Synthetic source {i}. This string contains unknown as free text.' for i in range(200)]
    if protected_alias:bodies[17]=bodies[0]
    tasks=[f'batch999/packet_{i//5:04d}/{i%5}' for i in range(200)]
    forms=[];keys=[];identities=[];candidates={};exceptions={};handled={}
    for i in range(1309):handled[tasks[i] if i<200 else f'synthetic-unselected-{i}']={'batch_id':0,'status':'frozen_validator_pass_candidate_only'}
    for i in range(200):
        rid=f'RID-{i:04d}';aid=f'BLIND-{i+1:04d}';task=tasks[i]
        h=hashlib.sha256(bodies[i].encode()).hexdigest()
        state='quarantined_provider_content_filter' if i<4 else 'local_or_transport_boundary_exception' if i in (11,12,13) else 'frozen_validator_pass_candidate_only'
        handled[task]['status']=state
        forms.append({'audit_id':aid,'full_document':bodies[i],'gold_review':None,'reviewer_id':None,'reviewed_at_utc':None,'human_independence_attestation':None})
        keys.append({'audit_id':aid,'task':task,'record_id':rid,'context_sha256':h,'execution_state':state})
        identities.append({'task':task,'record_id':rid,'context_sha256':h,'execution_state':'accepted' if i==14 else 'unprocessed'})
        if i<4 or i in (11,12,13):
            exceptions[task]={'status':state,'disposition':'quarantined' if i<4 else 'saved_unverified','retry_forbidden':True}
            continue
        d=results/'batch0000'/f'{i:03d}'
        review={'record_id':rid,'context_sha256':h,'document_status':'reviewed_full',
                'experience_outcomes':{k:'not_mentioned' for k in schema['properties']['experience_outcomes']['properties']},
                'experience_clauses':[],'qualification_alternatives':[],
                'entry_outcomes':{k:'not_mentioned' for k in schema['properties']['entry_outcomes']['properties']},'entry_items':[],
                'responsibility_outcomes':{k:'not_mentioned' for k in schema['properties']['responsibility_outcomes']['properties']},'responsibility_items':[],
                'technology_items':[],'technology_inventory_status':'not_mentioned_after_full_review','unresolved_notes':[]}
        if 4<=i<=8 or all_unknown:review['experience_outcomes']['general_work']='unknown'
        if i in (9,10):review['document_status']='reviewed_partial'
        if i==15:review['unresolved_notes']=['synthetic pending ambiguity']
        if i==16:review['technology_items']=[{'technology':'test','family':'unresolved','role':'background_mention','developed_object':'','context_note':'','quotes':[bodies[i]]}]
        vp=d/'CLOUD_VALIDATED_PRIVATE.jsonl';lines(vp,[review])
        lines(d/'INPUT_PRIVATE.jsonl',[{'record_id':rid,'context_sha256':h,'full_document':bodies[i],'assignment':{'packet_id':'old','reviewer_role':'primary'}}])
        candidates[task]={'record_id':rid,'context_sha256':h,'path':str(vp),'validated_sha256':module.sha(vp),
                          'semantic_quality':'not_certified','validation':'frozen_validator_pass','batch_id':0}
    bp=results/'batch0000';save(bp/'SHA256SUMS.json',{str(p.relative_to(bp)):module.sha(p) for p in bp.rglob('*') if p.is_file()})
    lines(audit/'BLIND_HUMAN_REVIEW_FORM_PRIVATE.jsonl',forms);lines(audit/'SEALED_MATCH_KEY_PRIVATE.jsonl',keys)
    save(base/'CANDIDATE_STATE_PRIVATE.json',{'engineering_candidates':candidates,'exceptions':exceptions,'handled':handled,'production_promoted':0,'semantic_quality_certified':False})
    save(base/'CLAIM_PRIVATE.json',{'old_accepted_sha256':module.sha(old),'pins':pins,'known_completed_tasks':[tasks[14]]})
    ids=root/'AZURE_RESEARCH_IDENTITIES_PRIVATE.json';save(ids,{'rows':identities})
    save(root/'AZURE_RESEARCH_STATE.json',{'private_record_index':{'sha256':module.sha(ids)},'quarantine_register':[],'deduplication':{}})
    save(base/'QUARANTINE_EVENTS_PRIVATE.json',{'events':[{'task':tasks[0],'disposition':'quarantined','retry_forbidden':True}]})
    save(base/'FINAL_PUBLIC.json',{'handled':1309,'frozen_pass_candidates':len(candidates),
         'audit_file_sha256':{p.name:module.sha(p) for p in audit.iterdir()}})
    return dict(expected_policy_sha=module.sha(policy),expected_pins=pins,expected_form_sha=module.sha(audit/'BLIND_HUMAN_REVIEW_FORM_PRIVATE.jsonl'))


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.args=fixture(self.root)
        self.base=self.root/'opencode_kimi_20261115/run01/bulk_1309_20261115'
    def tearDown(self):self.temp.cleanup()
    def test01_prepares_exact20_and_excludes_states(self):
        r=module.prepare(self.root,**self.args)
        self.assertEqual(r['selected_n'],20);self.assertEqual(r['selected_audit_ids'][0],'BLIND-0018')
        self.assertEqual(r['exclusions'],{'protected':4,'prior_unknown_or_unresolved':7,'prior_partial_or_unresolved':2,'prior_exception_or_non_candidate':3,'already_accepted_or_reviewed_unknown':1})
        self.assertEqual(r['eligible_existing_candidates'],183);self.assertEqual(r['protected_source_rows_parsed'],0)
        self.assertTrue(r['old_files_unchanged']);self.assertEqual(r['model_calls'],0)
    def test02_references_separate_and_source_not_truncated(self):
        r=module.prepare(self.root,**self.args);out=Path(r['output_directory'])
        inputs=module.jsonl(out/'INPUTS_PRIVATE.jsonl');refs=module.jsonl(out/'REFERENCES_PRIVATE.jsonl')
        self.assertEqual(len(inputs),20);self.assertEqual(len(refs),20)
        self.assertEqual(set(inputs[0]),{'audit_id','task','row'})
        self.assertNotIn('experience_outcomes',inputs[0]['row'])
        for x in inputs:self.assertEqual(hashlib.sha256(x['row']['full_document'].encode()).hexdigest(),x['row']['context_sha256'])
    def test03_idempotent_replay(self):
        a=module.prepare(self.root,**self.args);b=module.prepare(self.root,**self.args);self.assertEqual(a,b)
    def test04_modified_output_replay_blocked(self):
        r=module.prepare(self.root,**self.args);Path(r['input_path']).write_text('changed')
        with self.assertRaisesRegex(RuntimeError,'output_changed'):module.prepare(self.root,**self.args)
    def test05_modified_old_ledger_replay_blocked(self):
        module.prepare(self.root,**self.args);(self.base/'CANDIDATE_STATE_PRIVATE.json').write_text('{}')
        with self.assertRaisesRegex(RuntimeError,'source_changed'):module.prepare(self.root,**self.args)
    def test06_policy_pin_required(self):
        self.args['expected_policy_sha']='bad'
        with self.assertRaisesRegex(RuntimeError,'policy_pin'):module.prepare(self.root,**self.args)
    def test07_original_form_hash_required(self):
        self.args['expected_form_sha']='bad'
        with self.assertRaisesRegex(RuntimeError,'audit_form_changed'):module.prepare(self.root,**self.args)
    def test08_identity_manifest_pin_required(self):
        (self.root/'AZURE_RESEARCH_IDENTITIES_PRIVATE.json').write_text('{}')
        with self.assertRaisesRegex(RuntimeError,'identity_index_pin'):module.prepare(self.root,**self.args)
    def test09_frozen_validator_pin_required(self):
        (self.root/'code/validate_reviews.py').write_text('tampered')
        with self.assertRaisesRegex(RuntimeError,'frozen_pin'):module.prepare(self.root,**self.args)
    def test10_eligible_input_hash_required(self):
        ip=self.base.parent/'results/bulk1309/batch0000/017/INPUT_PRIVATE.jsonl';ip.write_text('{}\n')
        with self.assertRaisesRegex(RuntimeError,'source_input_manifest_hash'):module.prepare(self.root,**self.args)
    def test11_partial_output_not_overwritten(self):
        (self.root/'reuse_first_20261115/run01/benchmark20').mkdir(parents=True)
        with self.assertRaisesRegex(RuntimeError,'partial_benchmark'):module.prepare(self.root,**self.args)
    def test12_not_enough_eligible_no_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);args=fixture(root,all_unknown=True)
            with self.assertRaisesRegex(RuntimeError,'fewer_than20'):module.prepare(root,**args)
    def test13_protected_hash_alias_also_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);args=fixture(root,protected_alias=True);r=module.prepare(root,**args)
            self.assertEqual(r['exclusions']['protected'],5);self.assertEqual(r['selected_audit_ids'][0],'BLIND-0019')
    def test14_free_text_unknown_is_not_outcome(self):
        self.assertFalse(module.enum_unknown({'type':'string'},'unknown'))
        self.assertTrue(module.enum_unknown({'type':'string','enum':['unknown','present']},'unknown'))
    def test15_promoted_source_blocked(self):
        p=self.base/'CANDIDATE_STATE_PRIVATE.json';x=module.read(p);x['production_promoted']=1;save(p,x)
        with self.assertRaisesRegex(RuntimeError,'no_longer_unpromoted'):module.prepare(self.root,**self.args)


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'status':'pass' if result.wasSuccessful() else 'fail','synthetic_tests_run':result.testsRun,
            'failures':len(result.failures),'errors':len(result.errors),'private_advertisements_read':0,
            'model_calls':0,'cloud_jobs':0,'production_changes':0}
    (HERE/'BENCHMARK_PREPARATION_OFFLINE_TEST_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
