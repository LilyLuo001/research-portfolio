"""Synthetic equivalence tests against every original v1 QA SQL property."""
import json
import sqlite3
import unittest

import test_cloud_materialize as fixture_module
import cloud_verify_materialization_v2 as qa


def legacy(db, report):
    scalar=lambda sql:db.execute(sql).fetchone()[0]
    checks={
        'sqlite_integrity':scalar('PRAGMA integrity_check')=='ok',
        'document_count_matches_receipt':scalar('SELECT COUNT(*) FROM source_document')==report['processed_documents'],
        'atom_count_matches_receipt':scalar('SELECT COUNT(*) FROM variable_value')==report['materialized_variable_rows'],
        '89_dictionary_definitions':scalar('SELECT COUNT(*) FROM dictionary_definition')==89,
        'no_runtime_excluded_document':scalar('SELECT COUNT(*) FROM source_document d JOIN context_state c ON c.h=d.h WHERE c.reuse_excluded=1')==0,
        'no_orphan_atoms':scalar('SELECT COUNT(*) FROM variable_value v LEFT JOIN source_document d ON v.d=d.d WHERE d.d IS NULL')==0,
        'no_unknown_or_invalid_promoted':scalar("SELECT COUNT(*) FROM variable_value WHERE eligible_original_scope=1 AND measurement_state NOT IN ('known','not_mentioned','not_applicable','null_preserved')")==0,
        'saved_documents_not_promoted':scalar('SELECT COUNT(*) FROM variable_value v JOIN source_document d ON v.d=d.d WHERE v.eligible_original_scope=1 AND d.original_accepted=0')==0,
        'no_new_semantic_acceptance':scalar("SELECT COUNT(*) FROM variable_value WHERE COALESCE(json_extract(metadata_json,'$.new_semantic_acceptance_granted'),1)!=0")==0,
        'negative_derivation_requires_complete_review':scalar("SELECT COUNT(*) FROM variable_value WHERE eligible_original_scope=1 AND json_extract(metadata_json,'$.complete_review_required')=1 AND COALESCE(json_extract(metadata_json,'$.complete_review_requirement_met'),0)!=1")==0,
        'analysis_join_no_source_binding_duplication':scalar('SELECT COUNT(*) FROM (SELECT id,ad_key,created,created_state,COUNT(*) n FROM analysis_values_with_created GROUP BY id,ad_key,created,created_state HAVING n>1)')==0,
        'analysis_join_respects_source_ad_key':scalar("SELECT COUNT(*) FROM analysis_values_with_created WHERE k!='' AND k!=ad_key")==0,
    }
    counts={name:scalar('SELECT COUNT(*) FROM '+name) for name in
            ['source_document','variable_value','metadata_value','ad_binding','deferred_mapping','adapter_issue','context_state','original_mask']}
    summary={
        'variable_measurement_rows':dict(db.execute('SELECT measurement_state,COUNT(*) FROM variable_value GROUP BY measurement_state')),
        'variable_workflow_rows':dict(db.execute('SELECT workflow_state,COUNT(*) FROM variable_value GROUP BY workflow_state')),
        'source_contexts_by_original_acceptance_nonadditive':dict(db.execute('SELECT original_accepted,COUNT(DISTINCT h) FROM source_document GROUP BY original_accepted')),
        'bound_ad_keys':scalar('SELECT COUNT(DISTINCT k) FROM ad_binding'),
        'bound_created_states':dict(db.execute('SELECT created_state,COUNT(*) FROM ad_binding GROUP BY created_state')),
        'ad_keys_with_any_original_scope_atom':scalar('SELECT COUNT(DISTINCT ad_key) FROM analysis_values_with_created WHERE eligible_original_scope=1'),
        'contexts_with_any_original_scope_atom':scalar('SELECT COUNT(DISTINCT h) FROM variable_value WHERE eligible_original_scope=1'),
        'deferred_variable_keys':[r[0] for r in db.execute('SELECT DISTINCT variable_key FROM deferred_mapping ORDER BY variable_key')],
        'never_add_atom_rows_to_ad_or_context_counts':True,
        'some_original_scope_atom_not_all_fields_complete':True,
    }
    return checks,counts,summary


class IndependentQATest(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture_module.DriverSmokeTest(methodName='test_end_to_end_readonly_denial_masks_and_deduplicated_created')
        self.fixture.setUp();self.fixture.run_driver()
        self.path=self.fixture.output/'LINKUP_REUSED_VARIABLES_V1_PRIVATE.sqlite'
        self.report=json.loads((self.fixture.output/'MATERIALIZATION_PUBLIC.json').read_text())
        self.db=sqlite3.connect(self.path)

    def tearDown(self):
        self.db.close();self.fixture.tearDown()

    def compare(self):
        oldchecks,oldcounts,oldsummary=legacy(self.db,self.report)
        checks,counts,summary=qa.scan_properties(self.db,self.report)
        for name,value in oldchecks.items():self.assertEqual(checks[name],value,name)
        self.assertEqual(counts,oldcounts)
        for name,value in oldsummary.items():self.assertEqual(summary[name],value,name)
        return checks,summary

    def test_all_original_properties_and_aggregate_interfaces_match(self):
        checks,summary=self.compare()
        self.assertTrue(all(checks.values()))
        self.assertEqual(summary['metadata_field_inventory'],[{'physical_column':'COUNTRY','rows_present':6,'nonnull_rows':6}])

    def test_all_failed_value_guards_still_fail(self):
        # Synthetic corruption only: checks must detect each v1 failure.
        self.db.execute("UPDATE variable_value SET d='nonexistent-document' WHERE id=(SELECT id FROM variable_value LIMIT 1)")
        self.db.execute("UPDATE variable_value SET eligible_original_scope=1,measurement_state='unknown' WHERE h=?",(self.fixture.allowed[2],))
        self.db.execute("UPDATE variable_value SET metadata_json=? WHERE h=?",
                        (json.dumps({'new_semantic_acceptance_granted':True,'complete_review_required':True,'complete_review_requirement_met':False}),self.fixture.allowed[2]))
        self.db.execute('UPDATE context_state SET reuse_excluded=1 WHERE h=?',(self.fixture.allowed[0],))
        self.db.commit()
        checks,_=self.compare()
        for name in ['no_runtime_excluded_document','no_orphan_atoms','no_unknown_or_invalid_promoted',
                     'saved_documents_not_promoted','no_new_semantic_acceptance','negative_derivation_requires_complete_review']:
            self.assertFalse(checks[name],name)

    def test_duplicate_generating_view_cannot_pass_structural_proof(self):
        self.db.execute('DROP VIEW analysis_values_with_created')
        bad=qa.EXPECTED_VIEW.replace('(SELECT DISTINCT k,h,created,created_state FROM ad_binding)','ad_binding')
        self.db.execute(bad);self.db.commit()
        self.assertFalse(legacy(self.db,self.report)[0]['analysis_join_no_source_binding_duplication'])
        with self.assertRaisesRegex(AssertionError,'analysis_schema_proof_failed'):
            qa.scan_properties(self.db,self.report)

    def test_wrong_key_view_cannot_pass_structural_proof(self):
        self.db.execute('DROP VIEW analysis_values_with_created')
        self.db.execute(qa.EXPECTED_VIEW.replace(" AND (v.k='' OR v.k=b.k)",''))
        self.db.execute("UPDATE variable_value SET k='wrong-ad-key' WHERE id=(SELECT id FROM variable_value WHERE h=? LIMIT 1)",(self.fixture.allowed[0],))
        self.db.commit()
        self.assertFalse(legacy(self.db,self.report)[0]['analysis_join_respects_source_ad_key'])
        with self.assertRaisesRegex(AssertionError,'analysis_schema_proof_failed'):
            qa.scan_properties(self.db,self.report)

    def test_space_instead_of_empty_literal_cannot_pass_view_pin(self):
        self.db.execute('DROP VIEW analysis_values_with_created')
        self.db.execute(qa.EXPECTED_VIEW.replace("v.k=''", "v.k=' '"))
        self.db.commit()
        self.assertNotEqual(qa.normalized_sql(qa.EXPECTED_VIEW),
                            qa.normalized_sql(qa.EXPECTED_VIEW.replace("v.k=''", "v.k=' '")))
        with self.assertRaisesRegex(AssertionError,'analysis_schema_proof_failed'):
            qa.scan_properties(self.db,self.report)

    def test_nonempty_literal_case_variants_both_rejected_by_view_pin(self):
        for literal in ("'A'", "'a'"):
            with self.subTest(literal=literal):
                self.db.execute('DROP VIEW analysis_values_with_created')
                self.db.execute(qa.EXPECTED_VIEW.replace("v.k=''", 'v.k='+literal))
                self.db.commit()
                with self.assertRaisesRegex(AssertionError,'analysis_schema_proof_failed'):
                    qa.scan_properties(self.db,self.report)

    def test_null_primary_ids_fail_closed(self):
        self.db.execute('UPDATE variable_value SET id=NULL WHERE id=(SELECT id FROM variable_value LIMIT 1)')
        self.db.commit()
        checks,_,_=qa.scan_properties(self.db,self.report)
        self.assertFalse(checks['variable_ids_nonnull'])
        self.assertFalse(checks['analysis_join_no_source_binding_duplication'])

    def test_completed_scan_reuse_has_identical_results_without_second_variable_scan(self):
        complete={}
        def checkpoint(phase,data):
            if phase.endswith('_complete') and phase[:-9] in {'integrity','structure','variable_scan','remaining_metadata'}:
                complete[phase[:-9]]=data
        before=qa.scan_properties(self.db,self.report,checkpoint=checkpoint)
        sql=[];self.db.set_trace_callback(sql.append)
        after=qa.scan_properties(self.db,self.report,completed=complete)
        self.assertEqual(before,after)
        self.assertFalse(any('FROM variable_value' in s for s in sql))
        self.assertFalse(any(s=='PRAGMA integrity_check' for s in sql))
        self.assertEqual(set(complete),{'integrity','structure','variable_scan','remaining_metadata'})


class SQLTokenPinTest(unittest.TestCase):
    def test_only_outside_formatting_and_ascii_case_are_normalized(self):
        self.assertEqual(qa.normalized_sql(" SELECT  a , 'A b' FROM x ; \n"),
                         qa.normalized_sql("select a,'A b' from x"))
        self.assertNotEqual(qa.normalized_sql('SELECT a'),qa.normalized_sql('SELECTa'))
        self.assertNotEqual(qa.normalized_sql('SELECT k'),qa.normalized_sql('SELECT K'))

    def test_all_quote_types_preserve_spaces_case_and_doubled_escapes(self):
        for quoted in ("'A b''C'", '"A b""C"', '`A b``C`', '[A b]]C]'):
            with self.subTest(quoted=quoted):
                tokens=qa.normalized_sql('SELECT '+quoted)
                self.assertEqual(tokens,('select',quoted))
                self.assertNotEqual(tokens,qa.normalized_sql('SELECT '+quoted.replace(' ','').lower()))
        self.assertNotEqual(qa.normalized_sql("SELECT 'A'"),qa.normalized_sql("SELECT 'a'"))
        self.assertNotEqual(qa.normalized_sql("SELECT ''"),qa.normalized_sql("SELECT ' '"))
        self.assertNotEqual(qa.normalized_sql("SELECT 'a''b'"),qa.normalized_sql("SELECT 'a' 'b'"))

    def test_literal_semicolon_not_removed_and_unterminated_quotes_fail_closed(self):
        self.assertEqual(qa.normalized_sql("SELECT ';';"),('select',"';'"))
        for text in ("SELECT 'a", 'SELECT "a', 'SELECT `a', 'SELECT [a'):
            with self.assertRaisesRegex(ValueError,'unterminated_quoted_sql_token'):
                qa.normalized_sql(text)


if __name__=='__main__':unittest.main(verbosity=2)
