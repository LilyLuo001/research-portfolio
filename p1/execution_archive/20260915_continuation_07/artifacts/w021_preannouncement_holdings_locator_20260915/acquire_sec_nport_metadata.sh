#!/bin/sh
set -eu
SCC='qluo@scc1.bu.edu'
DEST='/projectnb/econdept/qluo/P1_Refraction_WRDS/w021_preannouncement_repair_20260915/raw'
URL='https://www.sec.gov/Archives/edgar/data/1217286/000175272422263385/primary_doc.xml'
ssh -o BatchMode=yes -o ConnectTimeout=10 "$SCC" "mkdir -p '$DEST' && cd '$DEST' && curl -L --max-time 30 -A 'research contact analyst@example.com' -sS -o primary_doc.xml '$URL' && sha256sum primary_doc.xml && stat -c '%s' primary_doc.xml && python3 - <<'PY'
import xml.etree.ElementTree as ET
r=ET.parse('primary_doc.xml').getroot()
text=' '.join(r.itertext())
assert 'S000032550' in text
assert '2022-09-30' in text
print('metadata_check=PASS series=S000032550 report_date=2022-09-30')
PY"
