"""Create only the frozen pay-per-token benchmark deployment in the existing account.

No VM, GPU, PTU, network, key, role, quota-increase or reservation changes.
Existing deployments are compared before/after. Never overwrites a conflicting name.
"""
import argparse, datetime, hashlib, json, sys, time, urllib.error
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--inventory',required=True);p.add_argument('--output',required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    config=json.loads(Path(a.config).read_text())
    assert config['model']=='gpt-6-luna' and config['model_version']=='2026-09-22'
    assert config['deployment_type']=='GlobalStandard' and config['deployment_capacity_units']<=100
    assert config['max_records']==20 and config['run_reservation_cap_usd']<=1
    acct=next(x for x in json.loads(Path(a.inventory).read_text())['accounts'] if x['name']=='rg-linkup')
    assert acct['state']=='Succeeded' and acct['location']=='eastus'
    sys.path.insert(0,str(Path.home()/'.codex/private/linkup_azure_migration_20261104'))
    import azure_control as az
    api='2024-10-01';base=acct['id']+'/deployments';name=config['deployment_name']
    before,_=az.call(base,api)
    existing={x['name']:x for x in before['value']};assert not before.get('nextLink')
    model={'format':'OpenAI','name':config['model'],'version':config['model_version']}
    receipt={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'config_sha256':hashlib.sha256(Path(a.config).read_bytes()).hexdigest(),'account':acct['name'],'deployment':name,'model':model,'action':'not_executed','model_calls':0,'new_vm_gpu_ptu_resources':0,'role_network_or_keys_changed':False}
    if name in existing:
        assert existing[name]['properties']['model']==model,'existing_deployment_conflict'
        assert existing[name]['sku']['name']=='GlobalStandard','existing_sku_conflict'
        receipt['action']='reused_exact_existing_deployment'
    elif a.execute:
        az.call(base+'/'+name,api,method='PUT',body={'sku':{'name':'GlobalStandard','capacity':config['deployment_capacity_units']},'properties':{'model':model,'versionUpgradeOption':'NoAutoUpgrade'}})
        receipt['action']='created_pay_per_token_benchmark_deployment'
    else:
        raise SystemExit('Explicit --execute required; no change performed')
    for _ in range(12):
        after,_=az.call(base,api); assert not after.get('nextLink')
        values={x['name']:x for x in after['value']}
        for n,old in existing.items():
            for k in ('sku',):assert values[n][k]==old[k],'existing_deployment_changed'
            assert values[n]['properties']['model']==old['properties']['model'],'existing_model_changed'
        q=values.get(name,{})
        if q.get('properties',{}).get('provisioningState') in ('Succeeded','Failed','Canceled'):break
        time.sleep(5)
    receipt.update(provisioning_state=q.get('properties',{}).get('provisioningState'),sku=q.get('sku'),rate_limits=q.get('properties',{}).get('rateLimits'),old_deployments_unchanged=True)
    Path(a.output).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
    if receipt['provisioning_state']!='Succeeded':raise SystemExit(2)

if __name__=='__main__':
    try:main()
    except urllib.error.HTTPError as e:
        print(json.dumps({'error_type':'HTTPError','http_status':e.code,'credentials_or_response_body_logged':False}));raise SystemExit(2)
