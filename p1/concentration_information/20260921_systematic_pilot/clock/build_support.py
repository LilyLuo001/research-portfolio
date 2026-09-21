"""Build public six-event evidence table, not a licensed research sample."""
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]

def main():
    files=[ROOT/'clock/PUBLIC_METADATA_RECEIPT.json',ROOT/'clock/DISTRIBUTOR_RECEIPT.json']
    evidence=[row for f in files for row in json.loads(f.read_text())['rows']]
    # These are source-specific adjudications of saved metadata, not price-selected anchors.
    decisions=[
      ('P1-2023-08-01','EXXONMOBIL','2023-01-31T06:30:00-05:00','PREMARKET','ISSUER_AND_SYNDICATED_WIRE_AGREE',0,'SOURCE_SUPPORTED_MINUTE_CANDIDATE','Issuer and syndicated wire agree; no contemporaneous capture or proof against earlier publication.'),
      ('P1-2023-08-03','EXXONMOBIL','2023-07-28T06:30:00-04:00','PREMARKET','ISSUER_WIRE_CONFLICT',1800,'UNRESOLVED_CONFLICT','Issuer page 06:00 versus wire 06:30; neither silently selected as first-public.'),
      ('P1-2023-06-02','UNITEDHEALTH','2023-04-14T05:55:00-04:00','PREMARKET','WIRE_PRECEDES_ISSUER_PAGE',143.332,'EARLIEST_OBSERVED_WIRE_CANDIDATE','Wire 05:55; issuer JSON-LD 05:57:23.332; difference can reflect publication/distribution sequence, not certified first release.'),
      ('P1-2023-01-01','APPLE','2023-02-02T16:30:00-05:00','AFTERHOURS','SYNDICATED_WIRE_MINUTE_ISSUER_DATE_ONLY',None,'SOURCE_SUPPORTED_MINUTE_CANDIDATE','Wire datePublished 21:30 UTC, modification 21:32:31; issuer supplies date only.'),
      ('P1-2023-01-03','APPLE','2023-08-03T16:30:00-04:00','AFTERHOURS','SYNDICATED_WIRE_MINUTE_ISSUER_DATE_ONLY',None,'SOURCE_SUPPORTED_MINUTE_CANDIDATE','Wire datePublished 20:30 UTC, modification 20:34:51; issuer supplies date only.'),
      ('P1-2023-02-02','MICROSOFT','2023-04-25T16:07:00-04:00','AFTERHOURS','AVAILABILITY_NOTICE_NOT_ORIGINAL_RELEASE',None,'ORIGINAL_RELEASE_TIME_UNRESOLVED','PRNewswire 16:07 says results already available; issuer advance schedule says after close; 03:00 ET page time cannot be inherited as actual release.'),
    ]
    rows=[]
    for event,issuer,stamp,session,provenance,span,status,note in decisions:
        src=[r for r in evidence if r['event_id']==event and r['status']=='METADATA_FETCHED']
        instant=datetime.fromisoformat(stamp)
        assert instant.astimezone(ZoneInfo('America/New_York')).utcoffset()==instant.utcoffset()
        rows.append(dict(event_id=event,issuer=issuer,population='FIXED_SIX_TECHNICAL_PROBES',stage='PUBLIC_TIME_PROVENANCE',denominator=6,
          observed_distribution_time_et=stamp,observed_distribution_time_utc=instant.astimezone(ZoneInfo('UTC')).isoformat(),
          distribution_or_notice_session=session,evidence_status=provenance,known_source_timestamp_difference_seconds=span,
          first_public_status='NOT_CERTIFIED',measurement_status=status,primary_response_released=False,
          sources=';'.join(r['url'] for r in src),note=note))
    with (ROOT/'CLOCK_SUPPORT.csv').open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    summary={'population':'fixed six technical probes; not analysis sample','event_count':len(rows),
      'observed_distribution_or_notice_session_counts':{s:sum(r['distribution_or_notice_session']==s for r in rows) for s in ['PREMARKET','RTH','AFTERHOURS']},
      'all_session_counts_are_source_time_not_certified_first_public':True,
      'first_public_certified_count':0,'empirical_primary_released_count':0,
      'http_attempts':len(evidence),'http_successes':sum(r['status']=='METADATA_FETCHED' for r in evidence),
      'source_hashes':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
      'earliest_release_lower_bounds':'UNPROVEN; observed timestamp span is not a proven global release interval',
      'financial_value_handling':'Search-engine snippets incidentally exposed public release values; not extracted to data, not used as news signal, no prices or research responses read.'}
    (ROOT/'clock/CLOCK_COUNTS.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
