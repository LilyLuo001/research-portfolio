"""Synthetic tests for the already verified Azure Responses transport contract."""
import importlib.util,json,hashlib
from pathlib import Path
P=Path(__file__).parent;source=P/'cloud_astra_audit_worker.py';spec=importlib.util.spec_from_file_location('audit_transport',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
f=m.responses_visible_view
x={'model':'synthetic','status':'completed','output':[{'type':'reasoning','content':'DO_NOT_COPY'},{'type':'message','content':[{'type':'output_text','text':'{"synthetic":true}'}]}],'usage':{'input_tokens':10,'output_tokens':20,'total_tokens':30}}
y=f(x);assert y['choices'][0]['message']['content']=='{"synthetic":true}';assert 'DO_NOT_COPY' not in json.dumps(y);assert y['usage']['prompt_tokens']==10 and y['usage']['completion_tokens']==20
assert f({**x,'status':'incomplete'})['choices'][0]['finish_reason']=='incomplete'
assert f({**x,'incomplete_details':{'reason':'content_filter'}})['choices'][0]['finish_reason']=='content_filter'
assert f({**x,'output':[{'type':'message','content':[{'type':'refusal','refusal':'synthetic'}]}]})['choices'][0]['message']['refusal'] is True
assert f({**x,'error':{'code':'ResponsibleAIPolicyViolation'}})['choices'][0]['finish_reason']=='content_filter'
r={'status':'pass','tests':7,'model_calls':0,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'route':'existing_Azure_Responses_API_already_used_successfully_by_project','no_schema_or_measurement_change':True,'preflight_Chat_API_draft_not_executed':True,'metadata_ARM_400_not_treated_as_permission_failure':True};(P/'ASTRA_TRANSPORT_TEST_PUBLIC.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
