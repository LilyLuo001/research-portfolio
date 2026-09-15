"""Actual first-20 fieldwise source backtrace; outputs only aggregate checks."""
import csv, hashlib, json, re, xml.etree.ElementTree as ET
from pathlib import Path
from project_w021_xml_metadata import candidate, txt

def fixtures():
    base=['NS','EC','Long','123456789','1']
    assert candidate(*base)
    cases=[(0,'USD'),(1,'DBT'),(2,'Short'),(3,'000000000'),(3,'123'),(4,'0'),(4,'-1'),(4,''),(4,'NaN')]
    for idx,value in cases:
        args=base.copy(); args[idx]=value
        assert not candidate(*args), (idx,value)
    assert txt(ET.fromstring('<x xmlns="urn:test"><units>NS</units></x>'),'units')=='NS'
    return 11

def main():
    ntests=fixtures()
    p=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/w021_preannouncement_repair_20260915')
    src=p/'raw/primary_doc.xml'; out=p/'projection_v2/w021_projection.csv'
    digest=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
    assert digest(src)=='cb68bd2cd53956060fd3d27a3224450628ff5e086580b1d992ee172a2f86aa2d'
    root=ET.parse(src).getroot()
    def rawtext(element,tag):
        v=element.find('.//{*}'+tag)
        return '' if v is None or v.text is None else v.text.strip()
    assert rawtext(root,'seriesId')=='S000032550'
    assert rawtext(root,'repPdDate')=='2022-09-30'
    with out.open() as handle: rows=list(csv.DictReader(handle))
    positions=root.findall('.//{*}invstOrSec')
    assert len(rows)==len(positions)==41
    fields={'series_id','report_date','accession','position_index','cusip','isin','security_title','issuer_name','units','assetcat','payoffprofile','country','rawsharebalance','common_equity_candidate'}
    assert set(rows[0])==fields
    direct={'cusip':'cusip','security_title':'title','issuer_name':'name','units':'units','assetcat':'assetCat','payoffprofile':'payoffProfile','country':'invCountry','rawsharebalance':'balance'}
    for i,(row,raw) in enumerate(zip(rows[:20],positions[:20]),1):
        expected={key:rawtext(raw,tag) for key,tag in direct.items()}
        expected['cusip']=expected['cusip'].upper()
        isin=raw.find('.//{*}identifiers/{*}isin')
        expected['isin']='' if isin is None else (isin.attrib.get('value') or isin.text or '').strip()
        expected.update(series_id='S000032550',report_date='2022-09-30',accession='0001752724-22-263385',position_index=str(i))
        try: positive=float(expected['rawsharebalance'])>0
        except (TypeError,ValueError): positive=False
        expected['common_equity_candidate']=str(bool(expected['units']=='NS' and expected['assetcat'] in ('','EC') and expected['payoffprofile'] in ('','Long') and positive and re.fullmatch('[A-Z0-9]{9}',expected['cusip']) and len(set(expected['cusip']))>1)).lower()
        assert row==expected, f'Field mismatch at position {i}'
    receipt={'status':'PASS','synthetic_fixture_assertions':ntests,'raw_positions_checked':20,'fields_checked_per_position':len(fields),'all_exported_fields_equal_raw_projection':True,'projection_rows':len(rows),'source_sha256':digest(src),'projection_sha256':digest(out),'parser_sha256':digest(Path(__file__).with_name('project_w021_xml_metadata.py')),'checker_sha256':digest(Path(__file__)),'row_values_printed':False,'supersedes':'Prior index-only first20 check was not a fieldwise backtrace.'}
    (p/'projection_v2/FIELDWISE_BACKTRACE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__': main()
