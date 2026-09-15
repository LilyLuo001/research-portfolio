"""Outcome-blind archive audit: stat and decode DBN metadata only, never records.

No network/vendor calls, no full-file hashing, no prices or response values.
Outputs are acquisition metadata, not usable-quote claims.
"""
import csv
import hashlib
import json
import struct
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import databento_dbn as dbn
import zstandard

BASE = Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914/databento_final_native')
C = BASE / 'control'
OUT = BASE / 'gate1_20260915'

def rows(p):
    with p.open(newline='') as f:
        return list(csv.DictReader(f))

def main():
    OUT.mkdir(exist_ok=True)
    manifest = rows(C/'download_manifest.csv')
    jobs = rows(C/'core_grouped_jobs.csv') + rows(C/'alternative_grouped_jobs.csv')
    byid = {r['job_id']: r for r in manifest}
    assert len(byid) == len(manifest), 'duplicate manifest IDs'
    result = []
    for j in jobs:
        r = byid.get(j['job_id'])
        status = 'NOT_DOWNLOADED'
        m = None
        n = 0
        if r:
            p = Path(r['path'])
            assert p.is_relative_to(BASE), 'path outside archive'
            if not p.exists():
                status = 'FILE_MISSING'
            else:
                n = p.stat().st_size
                status = 'SIZE_MISMATCH' if n != int(r['bytes']) else 'HEADER_UNKNOWN'
                try:
                    with p.open('rb') as raw:
                        magic = raw.read(4)
                        raw.seek(0)
                        stream = zstandard.ZstdDecompressor().stream_reader(raw) if magic == b'\x28\xb5\x2f\xfd' else raw
                        try:
                            prefix = stream.read(8)
                            assert len(prefix) == 8 and prefix[:3] == b'DBN'
                            size = struct.unpack('<I', prefix[4:8])[0]
                            assert size <= 1048576, 'unexpected header size'
                            body = stream.read(size)
                            assert len(body) == size
                            m = dbn.Metadata.decode(prefix + body)
                        finally:
                            if stream is not raw:
                                stream.close()
                    expected_start = int(datetime.fromisoformat(j['start'].replace('Z','+00:00')).timestamp()*1e9)
                    expected_end = int(datetime.fromisoformat(j['end'].replace('Z','+00:00')).timestamp()*1e9)
                    good = m.dataset == j['dataset'] and str(m.schema) == j['schema'] and m.start == expected_start and m.end == expected_end and set(m.symbols) == set(j['symbols'].split(';'))
                    if status != 'SIZE_MISMATCH':
                        status = 'HEADER_CONTRACT_MATCH' if good else 'HEADER_CONTRACT_MISMATCH'
                except Exception as e:
                    status = 'HEADER_ERROR_' + type(e).__name__
        for symbol in j['symbols'].split(';'):
            mapping_status = 'UNKNOWN'
            if m is not None:
                d = datetime.fromisoformat(j['start'].replace('Z','+00:00')).date()
                ids = {v['symbol'] for v in m.mappings.get(symbol,[]) if v['start_date'] <= d < v['end_date']}
                mapping_status = 'NOT_FOUND' if symbol in m.not_found else 'PARTIAL' if symbol in m.partial else 'DATE_VALID_UNIQUE' if len(ids)==1 else 'NO_DATE_VALID_MAPPING' if not ids else 'AMBIGUOUS'
            result.append(dict(job_id=j['job_id'],dataset=j['dataset'],symbol=symbol,analysis_access=j['analysis_access'],file_status=status,mapping_status=mapping_status,bytes=n))
    with (OUT/'job_symbol_header_audit.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(result[0])); w.writeheader(); w.writerows(result)
    job_status = {r['job_id']:r['file_status'] for r in result}
    receipt = dict(utc=datetime.now(timezone.utc).isoformat(),planned_jobs=len(jobs),manifest_jobs=len(manifest),job_status=dict(Counter(job_status.values())),job_symbol_rows=len(result),mapping_status=dict(Counter(r['mapping_status'] for r in result)),record_decoding=False,full_file_hashing=False,body_integrity='NOT_ASSESSED',quote_coverage='NOT_ASSESSED',inputs={name:hashlib.sha256((C/name).read_bytes()).hexdigest() for name in ['download_manifest.csv','core_grouped_jobs.csv','alternative_grouped_jobs.csv']},code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'header_audit_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__ == '__main__':
    main()
