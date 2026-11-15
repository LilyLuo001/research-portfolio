"""Synthetic only. No research data or model responses are read locally."""
import copy,json,unittest
from qualification_metrics import DIMS,FIELDS,alternatives,evaluate,extract,key,unwrap_validated_carrier
G={'known_reference_coverage_min':.8,'minimum_known_cases_per_field':50,'minimum_positive_cases_per_field':20,'minimum_negative_cases_per_field':20,'precision_min':.9,'recall_min':.8,'macro_f1_min':.85}

def fixture(positive=False):
 r={'document_status':'reviewed_full','technology_inventory_status':'not_mentioned_after_full_review','technology_items':[],'qualification_alternatives':[]}
 for fam,dims in DIMS.items():r[fam+'_outcomes']={d:'not_mentioned' for d in dims}
 for n in ('experience_clauses','entry_items','responsibility_items'):r[n]=[]
 if positive:r['entry_outcomes']['explicit_new_graduate']='present';r['entry_items']=[{'target':'explicit_new_graduate','conditionality':'unconditional','quotes':['synthetic evidence']}]
 return r

def sample():return [{'case':str(i),'split':'heldout','reference':fixture(i<50),'candidate':fixture(i<50),'reference_valid':True,'candidate_valid':True} for i in range(100)]

def field(cases):return evaluate(cases,G)['fields']['entry.explicit_new_graduate']
class MetricsTest(unittest.TestCase):
 def test_perfect_supported_field(self):self.assertTrue(field(sample())['machine_reference_field_gate_pass'])
 def test_unknown_candidate_is_missed_positive(self):
  c=sample();c[0]['candidate_valid']=False;r=field(c);self.assertEqual(r['positive_outcome']['fn'],1);self.assertEqual(r['complete_relation']['fn'],1)
 def test_unknown_reference_not_negative(self):
  c=sample();c[0]['reference_valid']=False;r=field(c);self.assertEqual(r['known_reference_cases'],99);self.assertEqual(r['unknown_reference_cases'],1);self.assertEqual(r['support']['not_mentioned'],50)
 def test_low_coverage_fails(self):
  c=sample()
  for x in c[:21]:x['reference_valid']=False
  self.assertIn('reference_coverage_below_gate',field(c)['blocking_reasons'])
 def test_no_positives_does_not_pass(self):
  c=sample()
  for x in c:x['reference']=fixture();x['candidate']=fixture()
  self.assertFalse(field(c)['machine_reference_field_gate_pass'])
 def test_development_never_in_gate(self):
  c=sample();c.append({'case':'dev','split':'development'});self.assertEqual(evaluate(c,G)['heldout_cases'],100)
 def test_duplicate_rejected(self):
  c=sample();c.append(c[0])
  with self.assertRaises(AssertionError):evaluate(c,G)
 def test_exact_quotes_not_semantic_equality(self):
  a=fixture(True);b=copy.deepcopy(a);b['entry_items'][0]['quotes']=['other synthetic quote'];self.assertEqual(extract(a,'entry.explicit_new_graduate',True),extract(b,'entry.explicit_new_graduate',True))
 def test_relation_condition_cannot_disappear(self):
  c=sample();c[0]['candidate']['entry_items'][0]['conditionality']='conditional';r=field(c)['complete_relation'];self.assertEqual((r['fp'],r['fn']),(1,1))
 def test_arbitrary_alternative_ids_and_order(self):
  r={'qualification_alternatives':[{'group':'g1','relation':'OR','branches':[{'branch':'b1','condition':'degree'},{'branch':'b2','condition':'experience'}]}]};a=alternatives(r,{'alternative_group':'g1','alternative_branch':'b1'});r['qualification_alternatives'][0].update(group='renamed');r['qualification_alternatives'][0]['branches'].reverse();r['qualification_alternatives'][0]['branches'][1]['branch']='new';self.assertEqual(a,alternatives(r,{'alternative_group':'renamed','alternative_branch':'new'}))
 def test_alternative_OR_AND_not_equivalent(self):
  r={'qualification_alternatives':[{'group':'g','relation':'OR','branches':[{'branch':'b','condition':'degree'}]}]};i={'alternative_group':'g','alternative_branch':'b'};a=alternatives(r,i);r['qualification_alternatives'][0]['relation']='AND';self.assertNotEqual(a,alternatives(r,i))
 def test_subject_other_worker_different(self):
  r=fixture();r['responsibility_outcomes']['training_mentoring']='present';r['responsibility_items']=[{'dimension':'training_mentoring','subject':'advertised_worker','relation':'current_duty','conditionality':'unconditional'}];b=copy.deepcopy(r);b['responsibility_items'][0]['subject']='other_employee';self.assertNotEqual(extract(r,'responsibility.training_mentoring',True),extract(b,'responsibility.training_mentoring',True))
 def test_known_validator_envelope_projection(self):
  schema={'properties':{'label':{}},'required':['label']};r={'label':'original','trusted_assignment':{},'evidence_resolution':[],'validation_version':'frozen'};self.assertEqual(unwrap_validated_carrier(r,schema),{'label':'original'});self.assertIn('evidence_resolution',r)
 def test_unexpected_carrier_property_is_not_dropped(self):
  schema={'properties':{'label':{}},'required':['label']};r={'label':'original','trusted_assignment':{},'evidence_resolution':[],'validation_version':'frozen','unexpected':1}
  with self.assertRaises(ValueError):unwrap_validated_carrier(r,schema)
 def test_equal_numeric_bounds(self):self.assertEqual(key({"years_min":5}),key({"years_min":5.0}))
 def test_no_automatic_production(self):self.assertFalse(evaluate(sample(),G)['production_admission'])
if __name__=='__main__':unittest.main()
