"""Synthetic fixture only: proves cursor binding, exclusion and no-overwrite."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import tempfile

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('probe', HERE/'cloud_probe_finite_frame.py')
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)


def write(path, value, lines=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (''.join(json.dumps(x)+'\n' for x in value) if lines else json.dumps(value)).encode()
    path.write_bytes(data); return hashlib.sha256(data).hexdigest()


with tempfile.TemporaryDirectory(prefix='linkup-stage5-probe-fixture-') as tmp:
    p.R = R = Path(tmp)
    p.B = B = R/'integration_20261116/run001'
    p.E = E = R/'execution_20261116/run001'
    p.O = O = R/'confirmation_stage5_20261118/frame_probe_v1'
    h = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(10)]
    idxpath = B/'revision003/STATUS_INDEX_PRIVATE.sqlite'; idxpath.parent.mkdir(parents=True)
    idx = sqlite3.connect(idxpath)
    idx.executescript('create table final_status(h text,state text); create table blocked(h text);')
    idx.execute('insert into final_status values(?,?)', (h[0], 'not_reconciled'))
    idx.execute('insert into blocked values(?)', (h[1],)); idx.commit(); idx.close()
    cache = B/'metadata_cache'; cache.mkdir()
    manifest = [{'record_id':'corpus-pro-'+h[2], 'context_sha256':h[2], 'canonical_keys':[['job','raw',1,1]]}]
    staged = cache/'stage'; mh = write(staged, manifest, True); staged.rename(cache/(mh+'.metadata'))
    prep = {'status':'prepared_not_reviewed', 'prepared_contexts':1, 'next_cursor':{'shard_ordinal':0,'row_offset':100}, 'packet_manifest_sha256':mh}
    ph = write(staged, prep); staged.rename(cache/(ph+'.metadata'))
    def m(name, digest, batch=73):
        return {'rel':name, 'path':'/old/corpus_pro_review_20261026/batch%03d/%s'%(batch,name), 'sha256':digest}
    metadata = [m('PACKET_MANIFEST_PRIVATE.jsonl',mh),m('PACKET_PREPARATION_PUBLIC.json',ph),
                m('PACKET_MANIFEST_PRIVATE.jsonl',h[9],35)]
    # Missing protected file is intentional: opening it would fail the test.
    write(B/'DISCOVERY_PRIVATE.json', {'metadata_inventory':metadata})
    required = [R/'AZURE_RESEARCH_IDENTITIES_PRIVATE.json', R/'astra/extraction/STATE_PRIVATE.json',
                R/'reuse_first_20261115/run01/benchmark20/SELECTION_PRIVATE.json', E/'qualification_frame_v1/FRAME_PRIVATE.json']
    for i, path in enumerate(required): write(path, [{'context_sha256':h[3+i]}])
    catalog = [{'shard_id':'s%04d'%i,'ad_rows':1000,'ad_bytes':123,'ad_path':'/old/base%04d'%i} for i in range(2464)]
    p.CAT_SHA = write(R/'full_scope_catalog_preflight_20261115/20261115T120402Z/CORPUS_RELEASE_CATALOG_PRIVATE.jsonl',catalog,True)
    scope = R/'scope_continuation_20261117/run001'
    bh = write(scope/'BASE_SHARD_SCOPE_REGISTER_PRIVATE.json', [{'shard_id':'s0000','ad_sha256':h[7],'ad_rows':1000}])
    p.SCOPE_SHA = write(scope/'SCOPE_REGISTER_PUBLIC.json', {'outputs':[{'file':'BASE_SHARD_SCOPE_REGISTER_PRIVATE.json','sha256':bh}]})
    p.MAP_SHA = write(R/'source_binding_20261118/run002/DESCRIPTION_TO_BASE_SOURCE_BINDING_PRIVATE.jsonl',
          [{'shard_id':'s0000','status':'source_provenance_bound','base_artifact_sha256_from_existing_register':h[7],
            'source_sha256_from_cached_receipts':h[8]}],True)
    for cluster in ['kunshan','wuzhen','huazhong']:
        d = R/cluster/'LEDGER_PRIVATE.sqlite'; d.parent.mkdir()
        c = sqlite3.connect(d); c.execute('create table files(path text,root text,rel text,size int,status text,sha text)')
        if cluster == 'kunshan':
            for x in metadata[:2]: c.execute('insert into files values(?,?,?,?,?,?)',(x['path'],'/old',x['rel'],123,'verified',x['sha256']))
            for digest in [h[7],h[8]]: c.execute('insert into files values(?,?,?,?,?,?)',('/old/source','/old','source',123,'verified',digest))
        c.commit(); c.close()
    out = io.StringIO()
    with contextlib.redirect_stdout(out): p.main()
    report = json.loads(out.getvalue())
    assert report['status'] == 'finite_source_window_identified'
    assert report['next_cursor'] == {'shard_ordinal':0,'row_offset':100}
    assert report['canonical_rows_max'] == 150 and report['excluded_unique_contexts'] == 7
    assert report['protected_metadata_entries_skipped'] == 1
    assert report['raw_text_reads'] == report['network_calls'] == report['model_calls'] == 0
    union = json.loads((O/'KNOWN_CONTEXT_EXCLUSION_UNION_PRIVATE.json').read_text())
    assert h[0] in union['context_sha256']  # unresolved never becomes new input.
    try:
        p.main()
        raise AssertionError('no-overwrite guard did not fail')
    except FileExistsError:
        pass
    print(json.dumps({'synthetic_smoke':'pass','cursor_binding':'pass','max_window_150':'pass',
          'all_status_and_prepared_exclusion':'pass','protected_metadata_not_opened':'pass',
          'no_overwrite_guard':'pass','real_private_data_read':False}))
