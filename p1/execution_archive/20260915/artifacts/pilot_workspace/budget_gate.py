#!/usr/bin/env python3
"""Offline bundle selection from genuine saved quotes. No API/data calls.

Input JSON: remaining_credits_usd, cost_usd_by_bundle mapping with keys
core32, core16, validation_mbp1, validation_arcx, extra_etfs.
Every listed cost is the actual gross summed quote of its exact manifest.
Optional missing/unavailable costs may be null; core costs cannot be guessed.
This is a procurement calculation, NOT permission or enforcement at the vendor.
"""
import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

def money(x):
    if x is None or isinstance(x,bool):
        return None
    try:
        d=Decimal(str(x))
    except (InvalidOperation,ValueError):
        return None
    return d if d.is_finite() and d>=0 else None

def select(d):
    credits=money(d.get('remaining_credits_usd'))
    costs=d.get('cost_usd_by_bundle',{})
    if credits is None or not isinstance(costs,dict):
        return {'status':'STOP_MISSING_CREDIT_OR_QUOTES'}
    hard=min(Decimal('125'),credits)
    # Preserve 20% of a smaller actual credit balance, and $25 of $125.
    cap=min(Decimal('100'),hard*Decimal('0.8'))
    v=money(costs.get('validation_mbp1'))
    if v is None:
        return {'status':'STOP_MBP1_VALIDATION_UNQUOTED'}
    selection=[]; total=Decimal('0')
    for core in ['core32','core16']:
        c=money(costs.get(core))
        if c is not None and c+v<=cap:
            selection=[core,'validation_mbp1'];total=c+v;break
    if not selection:
        return {'status':'STOP_NO_COMPLETE_BASE_WITHIN_CAP','planning_cap_usd':str(cap)}
    for optional in ['validation_arcx','extra_etfs']:
        # Extras are currently priced for the full32 package; don't select them for core16.
        if selection[0]=='core16' and optional=='extra_etfs':
            continue
        c=money(costs.get(optional))
        if c is not None and total+c<=cap:
            selection.append(optional);total+=c
    return dict(status='QUOTED_BUNDLE_SELECTED_NOT_PURCHASED',selected=selection,
                gross_quoted_usd=str(total),planning_cap_usd=str(cap),
                hard_ceiling_usd=str(hard),uncommitted_reserve_usd=str(hard-total),
                vendor_charge_enforced=False,owner_purchase_permission_required=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('saved_quotes',type=Path)
    a=p.parse_args()
    print(json.dumps(select(json.loads(a.saved_quotes.read_text())),indent=2))
