"""Prepare <=150 new complete contexts on existing Azure; never call a model.

Uses the exact frozen canonical window, existing verified Blob locations, and
the pinned historical normalizer. Only chosen Parquet columns/row groups are
decoded. Rejected, duplicate, or previously exposed contexts are not replaced.
"""
import argparse
import collections
import datetime
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import struct
import sys
import time
import urllib.parse

NORMALIZER_SHA = '336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd'
REFERENCE_SHA = '733875307de475a296e3da4531ad64ba99351f5e2dff109b757ad80b80b34adb'
WINDOW_SHA = '3fe7e77c7577c57ebd0b6306720500621f31673910974c0324d02734464f4c65'
KEY = ['JOB_HASH', 'SOURCE_FILE', 'SOURCE_ROW', 'RECORD_SOURCE_ROW']
FORBIDDEN = ('batch035', '01a17beb-973b-74e2-adbb-20f8d004b1fc')
SHA = re.compile(r'^[0-9a-f]{64}$')
MAX_NET = 256 * 1024**2
MAX_REFERENCE = 64 * 1024**2
MAX_CHUNK_UNCOMPRESSED = 256 * 1024**2
MAX_DOCUMENT = 128 * 1024


class GateError(Exception): pass


def need(condition, reason):
    if not condition: raise GateError(reason)


def digest(data): return hashlib.sha256(data).hexdigest()


def stable(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def metadata_contexts(x):
    out = set()
    if isinstance(x, dict):
        for k, v in x.items():
            if SHA.fullmatch(str(k)): out.add(k)
            if k in ('context_sha256', 'normalized_context_sha256', 'h'):
                for a in (v if isinstance(v, list) else [v]):
                    if isinstance(a, str) and SHA.fullmatch(a): out.add(a)
            if k == 'record_id' and isinstance(v, str) and v.startswith('corpus-pro-') and SHA.fullmatch(v[11:]): out.add(v[11:])
            out.update(metadata_contexts(v))
    elif isinstance(x, list):
        for v in x: out.update(metadata_contexts(v))
    return out


def key(row):
    need(all(k in row and row[k] is not None for k in KEY), 'null_or_missing_canonical_key')
    need(all(isinstance(row[k], int) and not isinstance(row[k], bool) and row[k] >= 0 for k in KEY[2:]), 'canonical_row_locator_invalid')
    return (str(row[KEY[0]]), str(row[KEY[1]]), row[KEY[2]], row[KEY[3]])


def module(path, expected, name):
    need(path.is_file() and not path.is_symlink() and digest(path.read_bytes()) == expected, name+'_code_pin_mismatch')
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def ledger_locations(root, h):
    out = []
    for cluster in ['kunshan', 'wuzhen', 'huazhong']:
        p = root/cluster/'LEDGER_PRIVATE.sqlite'
        c = sqlite3.connect(p.as_uri()+'?mode=ro', uri=True); c.execute('PRAGMA query_only=ON')
        for path, base, rel, n in c.execute('select path,root,rel,size from files where sha=? and status=?', (h, 'verified')):
            if not any(s in str(path).lower() for s in FORBIDDEN):
                out.append(dict(cluster=cluster, path=path, root=base, rel=rel, size=n, sha256=h))
        c.close()
    need(out, 'verified_source_SHA_not_located')
    need(len({x['size'] for x in out}) == 1, 'verified_source_SHA_size_conflict')
    return sorted(out, key=lambda x: (x['cluster'], x['root'], x['rel']))


class Blob:
    """Exact byte ranges, pinned snapshot path, stable ETag and hard byte cap."""
    def __init__(self, state, loc, label):
        self.state, self.loc, self.label = state, loc, label
        conf = json.loads((state.root/'private'/(loc['cluster']+'.json')).read_bytes())
        self.url = conf['container_sas'].split('?', 1)[0]+'/'+urllib.parse.quote(conf['snapshot']+'/'+Path(loc['root']).name+'/'+loc['rel'], safe='/')
        self.size, self.etag = loc['size'], None

    def read(self, start, end):
        need(0 <= start <= end <= self.size and end-start <= MAX_REFERENCE, 'range_bounds_or_request_cap')
        if start == end: return b''
        need(self.state.net+end-start <= MAX_NET, 'total_network_byte_cap')
        headers = {'x-ms-version':'2023-11-03', 'Range':f'bytes={start}-{end-1}'}
        if self.etag: headers['If-Match'] = self.etag
        with self.state.call(self.url, 'https://storage.azure.com/', headers=headers) as r:
            need(r.status == 206, 'blob_range_not_honored')
            need(r.headers.get('Content-Range') == f'bytes {start}-{end-1}/{self.size}', 'blob_range_or_size_disagrees')
            etag = r.headers.get('ETag'); need(etag and (not self.etag or self.etag == etag), 'blob_ETag_changed_or_missing')
            data = r.read(end-start+1); need(len(data) == end-start, 'blob_range_length_disagrees')
        self.etag = etag; self.state.net += len(data)
        self.state.ranges.append({'asset':self.label, 'source_sha256_from_verified_ledger':self.loc['sha256'],
            'start':start, 'end_exclusive':end, 'bytes':len(data), 'range_sha256':digest(data), 'ETag':etag})
        return data

    def metadata(self):
        tail = self.read(self.size-8, self.size)
        need(tail[4:] == b'PAR1', 'not_plain_parquet')
        n = struct.unpack('<I', tail[:4])[0]
        need(0 < n <= 8*1024**2 and n < self.size-8, 'parquet_footer_cap')
        need(self.read(0,4) == b'PAR1', 'parquet_magic_mismatch')
        footer = self.read(self.size-8-n, self.size-8)
        md = self.state.pq.read_metadata(self.state.pa.BufferReader(b'PAR1'+footer+tail))
        return md

    def projected_groups(self, md, groups, columns):
        names = md.schema.to_arrow_schema().names
        need(set(columns) <= set(names), 'required_projected_columns_absent')
        allowed = [(0,4), (max(0,self.size-65536),self.size)]
        uncompressed = 0
        for g in groups:
            rg = md.row_group(g)
            for j in range(rg.num_columns):
                c = rg.column(j)
                if c.path_in_schema not in columns: continue
                off = min(x for x in [c.dictionary_page_offset, c.data_page_offset] if x is not None and x >= 0)
                n = c.total_compressed_size; uncompressed += c.total_uncompressed_size
                need(n >= 0 and off+n <= self.size, 'parquet_column_chunk_bounds')
                allowed.append((off,off+n))
        need(uncompressed <= MAX_CHUNK_UNCOMPRESSED, 'projected_row_group_uncompressed_cap')
        stream = RangeIO(self, allowed)
        pf = self.state.pq.ParquetFile(stream, metadata=md, pre_buffer=False, buffer_size=0)
        for g in groups:
            yield g, pf.read_row_group(g, columns=columns, use_threads=False)


class RangeIO(io.RawIOBase):
    def __init__(self, blob, allowed):
        self.blob, self.allowed, self.pos = blob, sorted(allowed), 0
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        target = offset if whence == 0 else self.pos+offset if whence == 1 else self.blob.size+offset
        need(0 <= target <= self.blob.size, 'parquet_seek_bounds'); self.pos = target; return target
    def read(self, n=-1):
        need(n >= 0, 'unbounded_parquet_read_forbidden')
        end = min(self.pos+n, self.blob.size); covered = self.pos
        for a,b in self.allowed:
            if a <= covered < b: covered = max(covered,b)
        need(end <= covered or end == self.pos, 'parquet_read_outside_selected_chunks')
        data = self.blob.read(self.pos,end); self.pos=end; return data
    def readinto(self, target):
        b = self.read(len(target)); target[:len(b)] = b; return len(b)


def group_ranges(md):
    out=[]; n=0
    for g in range(md.num_row_groups):
        end=n+md.row_group(g).num_rows; out.append((n,end,g)); n=end
    return out


def exposure_files(root):
    """Bounded live metadata census, excluding text/result/cache directories."""
    e=root/'execution_20261116/run001'
    roots=[root/'astra/extraction', root/'opencode_kimi_20261115/run01',
           root/'reuse_first_20261115/run01/benchmark20', e/'qualification_frame_v1',
           e/'qualification500_v1', e/'continuation01', e/'continuation02']
    names={'STATE_PRIVATE.json','CANDIDATE_STATE_PRIVATE.json','CLAIM_PRIVATE.json',
           'EXCLUSIONS_PRIVATE.json','RUNTIME_EXCLUSIONS_PRIVATE.json','QUARANTINE_EVENTS_PRIVATE.json',
           'ACCOUNTING_PENDING_PRIVATE.json','ACCOUNTING_COMMITTED_PRIVATE.json','FRAME_PRIVATE.json','SELECTION_PRIVATE.json'}
    skip={'results','input_cache','cache','code','runs','human_audit','reference_cache','metadata_cache'}
    found={root/'AZURE_RESEARCH_IDENTITIES_PRIVATE.json'}
    for directory in roots:
        if not directory.is_dir(): continue
        queue=[(directory,0)]
        while queue:
            d,depth=queue.pop()
            for p in d.iterdir():
                if p.is_symlink() or any(s in str(p).lower() for s in FORBIDDEN): continue
                if p.is_file() and p.name in names: found.add(p)
                elif p.is_dir() and depth < 3 and p.name not in skip: queue.append((p,depth+1))
                need(len(found) <= 512 and len(queue) <= 512, 'exposure_metadata_census_cap')
    return sorted(found)


class State:
    def __init__(self, root, out):
        self.root,self.out=root,out; self.pins={}; self.ranges=[]; self.net=0; self.meta=0
    def read(self,p,expected=None,lines=False):
        need(p.is_file() and not p.is_symlink() and p.stat().st_size <= 32*1024**2, 'metadata_size_or_file_gate')
        b=p.read_bytes(); h=digest(b); need(not expected or h == expected,'metadata_SHA_mismatch')
        self.meta+=len(b); need(self.meta<=192*1024**2,'metadata_total_cap')
        need(str(p.relative_to(self.root)) not in self.pins or self.pins[str(p.relative_to(self.root))]==h,'metadata_changed_since_initial_read')
        self.pins[str(p.relative_to(self.root))]=h
        return [json.loads(x) for x in b.splitlines() if x.strip()] if lines else json.loads(b)
    def save(self,name,value,lines=False):
        b=(''.join(stable(x)+'\n' for x in value) if lines else json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
        with (self.out/name).open('xb') as f: f.write(b)
        return digest(b)


def live_union(s, initial, collect_keys=False):
    excluded=set(initial); canonical=set(); census=exposure_files(s.root)
    required=[s.root/'AZURE_RESEARCH_IDENTITIES_PRIVATE.json',
              s.root/'execution_20261116/run001/qualification_frame_v1/FRAME_PRIVATE.json',
              s.root/'reuse_first_20261115/run01/benchmark20/SELECTION_PRIVATE.json']
    need(all(p in census for p in required),'required_old_exposure_frame_missing')
    for p in census: excluded.update(metadata_contexts(s.read(p)))
    ip=s.root/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite'
    c=sqlite3.connect(ip.as_uri()+'?mode=ro',uri=True); c.execute('PRAGMA query_only=ON')
    for table in ['final_status','blocked']: excluded.update(h for h, in c.execute('select h from '+table))
    c.close()
    if collect_keys:
        b=s.root/'integration_20261116/run001'
        inv=s.read(b/'DISCOVERY_PRIVATE.json')['metadata_inventory']; seen=set()
        for m in inv:
            if not m['rel'].endswith('PACKET_MANIFEST_PRIVATE.jsonl') or m['sha256'] in seen: continue
            if any(x in m['path'].lower() for x in FORBIDDEN): continue
            seen.add(m['sha256']); rows=s.read(b/'metadata_cache'/(m['sha256']+'.metadata'),m['sha256'],True)
            excluded.update(metadata_contexts(rows))
            for row in rows:
                for k in row.get('canonical_keys',[]):
                    need(len(k)==4,'prior_manifest_key_shape'); canonical.add(tuple(k))
    need(all(isinstance(h,str) and SHA.fullmatch(h) for h in excluded),'invalid_context_exclusion_hash')
    return excluded,canonical,census


def prepare(args):
    os.umask(0o077); sys.dont_write_bytecode=True; signal.alarm(240); started=time.monotonic()
    root=Path(args.root).resolve(); out=root/args.output
    need(out.resolve().is_relative_to(root) and out != root,'output_outside_migration')
    out.mkdir(parents=True,exist_ok=False); s=State(root,out)
    s.stage='metadata'
    sys.path.insert(0,str(root/'scope_continuation_20261117/run001/parquet_runtime_20261118_run001/libraries'))
    import pyarrow as pa
    import pyarrow.parquet as pq
    s.pa,s.pq=pa,pq
    sys.path.insert(0,str(root/'code')); from workflow import call
    s.call=call
    normalizer=module(Path(args.normalizer),NORMALIZER_SHA,'stage5_pinned_normalizer')._normalize_with_flags
    scorer=module(Path(args.scorer),args.scorer_sha,'stage5_frozen_scorer')
    probe=root/'confirmation_stage5_20261118/frame_probe_v1'
    window=s.read(probe/'FINITE_SOURCE_WINDOW_PRIVATE.json',args.window_sha)
    need(not window['cursor_gate_blockers'],'finite_window_has_metadata_blockers')
    begin=window['start_cursor']; end=window['end_cursor_exclusive']
    need(begin['shard_ordinal']==end['shard_ordinal'] and 0 < end['row_offset']-begin['row_offset'] <= 150,'finite_window_bounds')
    old=s.read(probe/'KNOWN_CONTEXT_EXCLUSION_UNION_PRIVATE.json',window['context_exclusion_union_sha256'])
    # Refresh every known exposure before any Description column is read.
    excluded, canonical, census=live_union(s,old['context_sha256'],True)
    s.stage='original_10000_reference_metadata'
    reference_locs=ledger_locations(root,REFERENCE_SHA); reference_loc=reference_locs[0]
    need(0 < reference_loc['size'] <= MAX_REFERENCE,'original_reference_file_size_cap')
    refblob=Blob(s,reference_loc,'original10000_reference')
    refbytes=refblob.read(0,refblob.size); need(digest(refbytes)==REFERENCE_SHA,'original_reference_whole_SHA_mismatch')
    rf=pq.ParquetFile(pa.BufferReader(refbytes))
    need(rf.metadata.num_rows==10000 and set(KEY+['normalized_context_sha256']) <= set(rf.schema_arrow.names),'original_reference_schema_or_count')
    reference=rf.read(columns=KEY+['normalized_context_sha256'],use_threads=False).to_pylist()
    refs={}
    for row in reference:
        k=key(row); h=row['normalized_context_sha256']
        need(isinstance(h,str) and SHA.fullmatch(h) and k not in refs,'original_reference_identity_or_hash')
        refs[k]=h
    need(len(refs)==10000,'original_reference_unique_key_count')
    canonical.update(refs); excluded.update(refs.values()); del refbytes,reference,rf
    exclusions_before=set(excluded)
    s.stage='canonical_metadata_window'
    base=window['base_register_entry']; binding=window['description_source_binding']
    base_locs=ledger_locations(root,base['ad_sha256']); raw_locs=ledger_locations(root,binding['source_sha256_from_cached_receipts'])
    need(base_locs[0]['size']==base['ad_bytes'] and raw_locs[0]['size']==binding['source_bytes'],'window_source_size_changed')
    bb=Blob(s,base_locs[0],'canonical_base'); bm=bb.metadata()
    need(bm.num_rows==base['ad_rows']==window['catalog_entry']['ad_rows'],'canonical_footer_count_changed')
    span=group_ranges(bm); groups=[g for a,b,g in span if a < end['row_offset'] and b > begin['row_offset']]
    need(len(groups)<=2,'canonical_row_group_count_cap')
    selected=[]
    for g,table in bb.projected_groups(bm,groups,KEY):
        start=span[g][0]; lo=max(begin['row_offset']-start,0); hi=min(end['row_offset']-start,table.num_rows)
        for offset,row in enumerate(table.slice(lo,hi-lo).to_pylist(),start+lo):
            selected.append({'canonical_key':key(row),'catalog_row_offset':offset})
    need(len(selected)==end['row_offset']-begin['row_offset'],'canonical_window_conservation')
    skips=collections.Counter(); ready=[]; rejected=[]
    source_name=binding['source_basename']; source_path=binding['accounting_source_path']
    for item in selected:
        k=item['canonical_key']
        if k in canonical:
            skips['previous_canonical_identity']+=1; rejected.append({**item,'reason':'previous_canonical_identity'}); continue
        need(k[1]==source_path or (not Path(k[1]).is_absolute() and Path(k[1]).name==source_name),'canonical_SOURCE_FILE_source_binding_disagrees')
        ready.append(item)
    s.stage='bounded_complete_description_values'
    inputs=[]; frame=[]; locators=[]; seen=set()
    if ready:
        rb=Blob(s,raw_locs[0],'raw_Description'); rm=rb.metadata(); rspan=group_ranges(rm)
        byrow=collections.defaultdict(list)
        for item in ready:
            need(0 <= item['canonical_key'][2] < rm.num_rows,'SOURCE_ROW_outside_raw_footer')
            byrow[item['canonical_key'][2]].append(item)
        jobs={g:[r for r in byrow if a <= r < b] for a,b,g in rspan}
        jobs={g:rows for g,rows in jobs.items() if rows}
        need(len(jobs)<=4,'raw_row_group_count_cap_no_expansion')
        for g,table in rb.projected_groups(rm,sorted(jobs),['JOB_HASH','DESCRIPTION']):
            a=rspan[g][0]
            for source_row in sorted(jobs[g]):
                actual=table.column('JOB_HASH')[source_row-a].as_py()
                for item in byrow[source_row]:
                    need(str(actual)==item['canonical_key'][0],'raw_JOB_HASH_SOURCE_ROW_mismatch')
                body=table.column('DESCRIPTION')[source_row-a].as_py()
                reason=None; h=None
                if not isinstance(body,str): reason='null_or_non_string_source_description'
                elif len(body.encode('utf-8')) > MAX_DOCUMENT: reason='complete_source_description_exceeds_fixed_cap'
                else:
                    normalized,flags=normalizer(body)
                    if not normalized: reason='empty_after_pinned_normalization'
                    else:
                        h=digest(normalized.encode('utf-8'))
                        if h in excluded: reason='previously_known_or_exposed_context_SHA'
                        elif h in seen: reason='duplicate_within_fixed_window'
                for item in byrow[source_row]:
                    if reason:
                        skips[reason]+=1; rejected.append({**item,'context_sha256':h,'reason':reason}); continue
                    # A second canonical row for the same raw value is retained
                    # as excluded duplication; the frame has unique contexts.
                    if h in seen:
                        skips['duplicate_within_fixed_window']+=1
                        rejected.append({**item,'context_sha256':h,'reason':'duplicate_within_fixed_window'}); continue
                    seen.add(h); record_id='corpus-pro-'+h; case=f'case{len(frame):04d}'
                    inputs.append({'case':case,'row':{'record_id':record_id,'context_sha256':h,'full_document':normalized},
                        'partition':'confirmation','source_task':f"fresh_stage5_after_batch{window['batch_predecessor']:03d}",
                        'protected':False,'fresh_never_exposed':True})
                    frame.append({'case':case,'record_id':record_id,'context_sha256':h,'partition':'confirmation',
                        'protected':False,'fresh_never_exposed':True,'source_units_sha256':scorer.digest_json(scorer.source_units(normalized))})
                    locators.append({**item,'case':case,'record_id':record_id,'context_sha256':h,
                        'source_shard_id':base['shard_id'],'raw_source_SHA_from_verified_ledger':raw_locs[0]['sha256'],
                        'normalizer_sha256':NORMALIZER_SHA,'normalization_flags':flags,'full_source_value_used':True})
                del body
    # Recheck live metadata and file pins before declaring any context fresh.
    s.stage='final_exposure_recheck'
    refreshed,_,final_census=live_union(s,old['context_sha256'])
    refreshed.update(refs.values())
    need(refreshed==exclusions_before and final_census==census,'exposure_union_changed_during_preparation')
    need(all(digest((root/p).read_bytes())==h for p,h in s.pins.items()),'pinned_metadata_changed_during_preparation')
    need(digest(Path(args.normalizer).read_bytes())==NORMALIZER_SHA and digest(Path(args.scorer).read_bytes())==args.scorer_sha,'frozen_code_changed_during_preparation')
    need(not seen & refreshed and len(frame)==len(seen)<=150,'frame_context_exclusion_or_uniqueness')
    need(len(frame)+sum(skips.values())==len(selected),'fixed_window_accounting')
    need(all(digest(x['row']['full_document'].encode('utf-8'))==x['row']['context_sha256'] for x in inputs),'prepared_context_hash_recheck')
    outputs={}
    outputs['EXCLUSIONS_PRIVATE.json']=s.save('EXCLUSIONS_PRIVATE.json',{'context_sha256':sorted(refreshed),
        'tasks':['batch035/','01a17beb-973b-74e2-adbb-20f8d004b1fc'],
        'coverage':'all_known_status_prepared_old10000_and_bounded_live_exposure_registries',
        'original_reference_SHA':REFERENCE_SHA,'original_reference_rows':10000})
    outputs['INPUTS_PRIVATE.jsonl']=s.save('INPUTS_PRIVATE.jsonl',inputs,True)
    outputs['FRAME_PRIVATE.json']=s.save('FRAME_PRIVATE.json',frame)
    outputs['SOURCE_LOCATORS_PRIVATE.json']=s.save('SOURCE_LOCATORS_PRIVATE.json',locators)
    outputs['REJECTED_WINDOW_ROWS_PRIVATE.json']=s.save('REJECTED_WINDOW_ROWS_PRIVATE.json',rejected)
    s.save('SOURCE_RANGE_READS_PRIVATE.json',s.ranges)
    s.save('INPUT_PINS_PRIVATE.json',{'metadata':s.pins,'window_sha256':args.window_sha,
        'normalizer_sha256':NORMALIZER_SHA,'scorer_sha256':args.scorer_sha,
        'verified_blob_locators':{'reference':reference_loc,'base':base_locs[0],'Description':raw_locs[0]},
        'source_whole_content_SHA_recomputed':False,'original_reference_whole_content_SHA_recomputed':True})
    report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'fresh_finite_inputs_prepared_no_model_calls' if frame else 'fixed_window_has_no_eligible_new_contexts',
        'canonical_window_rows':len(selected),'fresh_complete_unique_contexts':len(frame),'rejected_without_replacement':dict(skips),
        'original_reference_rows_excluded':10000,'original_reference_unique_contexts_excluded':len(set(refs.values())),
        'total_known_contexts_excluded':len(refreshed),'live_metadata_files':len(census),'live_exposure_recheck_pass':True,
        'start_cursor':begin,'end_cursor_exclusive':end,'normalizer_sha256':NORMALIZER_SHA,'scorer_sha256':args.scorer_sha,
        'network_bytes_read':s.net,'source_values_selected_max':len(ready),'source_full_file_downloaded':False,
        'old_reference_whole_SHA_verified':True,'source_provenance':'verified_snapshot_ledger_SHA_size_stable_ETag_projected_byte_ranges_and_JOB_HASH_SOURCE_ROW_checks',
        'source_row_groups_decode_other_rows_at_storage_granularity':True,'no_rejected_row_replacement':True,
        'raw_text_exported_off_Azure':False,'model_calls':0,'new_resources':0,'protected_payload_reads':0,
        'old_results_changed':False,'outputs':outputs,'elapsed_seconds':time.monotonic()-started}
    s.save('FRESH_INPUT_PREPARATION_PUBLIC.json',report); print(json.dumps(report,sort_keys=True)); signal.alarm(0)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',default=str(Path.home()/'migration'))
    p.add_argument('--output',default='confirmation_stage5_20261118/fresh_inputs_v1')
    p.add_argument('--window-sha',default=WINDOW_SHA)
    p.add_argument('--normalizer',required=True)
    p.add_argument('--scorer',required=True)
    p.add_argument('--scorer-sha',required=True)
    args=p.parse_args()
    existed=(Path(args.root)/args.output).exists()
    try: prepare(args)
    except Exception as exc:
        # Never expose an HTTP exception URL, token, private text, or traceback.
        result={'status':'fresh_input_preparation_stopped_preserve_partial','error_type':type(exc).__name__,
                'reason':str(exc) if isinstance(exc,GateError) else 'unexpected_error_details_not_exported',
                'model_calls':0,'new_resources':0}
        out=Path(args.root)/args.output
        if not existed and out.is_dir() and not (out/'FAILURE_PUBLIC.json').exists():
            (out/'FAILURE_PUBLIC.json').write_text(json.dumps(result,sort_keys=True)+'\n')
        print(json.dumps(result,sort_keys=True)); raise SystemExit(2)


if __name__=='__main__': main()
