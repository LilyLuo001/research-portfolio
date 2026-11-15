"""Only transport fixed cloud-selected source inputs to the existing OpenCode route."""
import base64,gzip,json,ssl,subprocess,urllib.request,zlib
import certifi
from control import HERE,W,vm,save,sha
answer=vm('TRANSFER_PUBLIC_KEY='+repr((W/'transfer_public.pem').read_text())+'\n'+(HERE/'cloud_prepare_kimi_transport.py').read_text(),'prepare_kimi_transport001')
save(W/'PREPARE_RESPONSE_PRIVATE.json',answer);report=answer['report']
url='https://stlinkup70d455c0261104.blob.core.windows.net/migration-receipts/reuse-execution/20261116/run001/qualification500_v1/kimi_reference350_v1/INPUT_BUNDLE_PRIVATE.json.gz'
assert report['source_url']==url
pieces=[]
for encrypted in answer['encrypted_storage_token']:
    p=subprocess.run(['openssl','pkeyutl','-decrypt','-inkey',str(W/'transfer_key.pem'),'-pkeyopt','rsa_padding_mode:oaep','-pkeyopt','rsa_oaep_md:sha256'],input=base64.b64decode(encrypted),capture_output=True,check=True)
    pieces.append(p.stdout)
credential=zlib.decompress(b''.join(pieces)).decode()
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
opener=urllib.request.build_opener(NoRedirect,urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where())))
with opener.open(urllib.request.Request(url,headers={'Authorization':'Bearer '+credential,'x-ms-version':'2023-11-03'}),timeout=120) as r:data=r.read(report['source_bytes']+1)
credential=None;pieces.clear();p=W/'INPUT_BUNDLE_PRIVATE.json.gz';p.write_bytes(data)
assert len(data)==report['source_bytes'] and sha(p)==report['source_sha256']
(W/'INPUT_BUNDLE_PRIVATE.json').write_bytes(gzip.decompress(data))
report.pop('source_url');save(HERE/'KIMI_TRANSPORT_PUBLIC.json',report)
print(json.dumps(report))
