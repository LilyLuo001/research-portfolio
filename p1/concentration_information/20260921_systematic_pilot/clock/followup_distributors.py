"""One bounded follow-up of distributor links actually found in the first pass."""
import concurrent.futures
import json
from pathlib import Path
from probe_public_metadata import fetch

sources=[
 ('P1-2023-08-01','distributor','https://www.businesswire.com/news/home/20230131005178/en/ExxonMobil-Announces-Full-Year-2022-Results'),
 ('P1-2023-08-03','distributor','https://www.businesswire.com/news/home/20230728950771/en/'),
 ('P1-2023-01-01','distributor','https://www.businesswire.com/news/home/20230202005816/en/'),
 ('P1-2023-02-02','distributor','https://www.prnewswire.com/news-releases/microsoft-earnings-press-release-available-on-investor-relations-website-301807439.html'),
 ('P1-2023-02-02','issuer_scheduled_session','https://news.microsoft.com/source/2023/04/11/microsoft-announces-quarterly-earnings-release-date-55/'),
]
if __name__=='__main__':
    rows=list(concurrent.futures.ThreadPoolExecutor(max_workers=5).map(fetch,sources))
    result={'scope':'same six events; one bounded follow-up; failed fetch is not source absence','rows':rows}
    Path(__file__).with_name('DISTRIBUTOR_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
