"""Synthetic-only tests of the exact status view used by the cloud integration."""
import ast,json,sqlite3
from pathlib import Path
p=Path(__file__).parent
code=(p/'cloud_integrate.py').read_text();start=code.index('CREATE VIEW final_status');end=code.index("''')",start);sql=code[start:end]
db=sqlite3.connect(':memory:')
db.executescript('CREATE TABLE context(h TEXT PRIMARY KEY);CREATE TABLE blocked(h TEXT PRIMARY KEY);CREATE TABLE event(h TEXT,asset TEXT,state TEXT,source TEXT,detail TEXT,PRIMARY KEY(h,asset,state,source));CREATE TABLE field(h TEXT,status TEXT);CREATE TABLE ad(k TEXT,h TEXT);')
for h in ['protected','accepted','saved','pending','absent','transport','unknown_accepted']:db.execute('INSERT INTO context VALUES(?)',(h,))
db.execute("INSERT INTO blocked VALUES('protected')")
for h,states in [('protected',['accepted','saved_unverified']),('accepted',['accepted','saved_unverified']),('saved',['saved_unverified','unprocessed_asof_checkpoint']),('pending',['unprocessed_asof_checkpoint']),('transport',['not_reconciled']),('unknown_accepted',['accepted'])]:
 for state in states:db.execute('INSERT INTO event VALUES(?,?,?,?,?)',(h,'synthetic',state,'synthetic',''))
db.execute("INSERT INTO field VALUES('unknown_accepted','unknown')");db.executescript(sql)
actual=dict(db.execute('SELECT h,state FROM final_status'))
expected={'protected':'quarantined','accepted':'accepted_original_scope','saved':'saved_unverified','pending':'unprocessed_asof_checkpoint','absent':'not_reconciled','transport':'not_reconciled','unknown_accepted':'accepted_original_scope'}
checks={k:actual[k]==v for k,v in expected.items()};checks['unknown_not_overwritten']=db.execute("SELECT status FROM field WHERE h='unknown_accepted'").fetchone()[0]=='unknown';checks['partition_conservation']=len(actual)==7
try:db.execute("INSERT INTO event VALUES('accepted','synthetic','accepted','synthetic','')");checks['duplicate_event_rejected']=False
except sqlite3.IntegrityError:checks['duplicate_event_rejected']=True
# Execute only the pure canonical-key helper, not any cloud orchestration.
node=next(n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name=='canonical');scope={'json':json};exec(compile(ast.Module(body=[node],type_ignores=[]),'<canonical-only>','exec'),scope)
checks['canonical_four_key_order']=scope['canonical']({'RECORD_SOURCE_ROW':2,'SOURCE_ROW':1,'JOB_HASH':'synthetic-job','SOURCE_FILE':'synthetic-file'})==scope['canonical'](['synthetic-job','synthetic-file','1','2'])
assert all(checks.values())
r={'status':'pass','tests':len(checks),'checks':checks,'data_type':'synthetic_control_plane_only','model_calls':0,'semantic_accuracy_test':False}
(p/'INDEX_CONTRACT_TEST_PUBLIC.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
