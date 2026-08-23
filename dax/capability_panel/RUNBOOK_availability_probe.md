# Runbook — W4 account availability probe

Run this **on the SCC**, from the repository root, on a node with outbound
HTTPS. Costs USD 0: it calls the account-scoped models *metadata* endpoint, not
any inference endpoint. It reads no duration receipt and is unaffected by the
0/220 duration blocker.

Prepared 2026-08-23. Validated against `dax/tests/test_w4_availability.py`,
`test_w4_plan.py`, `test_w4_preflight.py` (12 passed).

## Current state

`dax/data_raw/w4_availability_audit_receipt.json` as committed is a **no-key**
run: `account_probe_performed: false`, and all 14 `direct` rows at
`unprobed_missing_key`. The probe has never been performed against the account.
Running this overwrites that receipt with real data.

## Step 0 — preconditions

```bash
cd <repo root>
git pull origin claude/dax-research-direction-1ohi97

# the env file must be 0600 or stricter or the tool refuses to read it
stat -c '%a %n' /usr3/graduate/qluo/dax-private/w4/.env     # want: 600
# if it is not:  chmod 600 /usr3/graduate/qluo/dax-private/w4/.env

# confirm the node has outbound HTTPS (login nodes usually do, compute nodes often do not)
curl -sS -o /dev/null -w '%{http_code}\n' https://api.openai.com/v1/models   # 401 is a PASS here
```

A `401` from that curl is the correct result — it proves egress works without
putting the key on the command line. A hang or a proxy error means run it on a
login node, or export `HTTPS_PROXY` (urllib honours it).

The probe does **not** import `cryptography`, so it runs even if the venv's
crypto stack is broken. That matters only for the later capture run.

## Step 1 — run the probe

```bash
python -m dax.capability_panel.availability \
  --registry dax/capability_panel/vintage_registry.json \
  --env-file /usr3/graduate/qluo/dax-private/w4/.env \
  --output dax/data_raw/w4_availability_audit_receipt.json
```

Never pass the key as an argument. The tool reads `OPENAI_API_KEY` from inside
the file, inside the process, so it never enters argv or the shell history.

## Step 2 — read the result

```bash
python -c "
import json;d=json.load(open('dax/data_raw/w4_availability_audit_receipt.json'))
print('probe_performed:',d['account_probe_performed'],'at',d['probed_at_utc'])
print('counts:',json.dumps(d['status_counts'],indent=1))
print()
for r in d['matrix']:
    if r['availability_status']=='account_unavailable':
        print('LOST   ',r['event_date'],r['source_model_id'])
for r in d['matrix']:
    if r['availability_status']=='account_available':
        print('REACHED',r['event_date'],r['source_model_id'])
"
```

**Expected shapes.** The 2 open-weight stand-ins, 5 blocked aliases, and 1
binding exclusion never change status — only the 14 `direct` rows move.

| Outcome | Meaning | Next action |
|---|---|---|
| `account_available: 14` | every deadline-bound snapshot still reachable | maximum urgency on the capture amendment; nothing lost yet |
| mixed available/unavailable | some vintages already gone | capture the survivors; the lost rows need approved open-weight stand-ins filed under the W0.5 rule, or they become `measurement_failed` per design memo §1.2 |
| `account_unavailable: 14` | account cannot see dated snapshots at all | check the key's project scope before concluding the vintages are gone — this is more likely an account-scoping problem than 14 simultaneous retirements |

`shutdown_date` stays `null` in every row even on success: the models-list
endpoint returns `id`/`object`/`created`/`owned_by` and carries no retirement
field. Retirement dates are pinned in the registry from the deprecations page.
This is not a probe failure.

## Step 3 — commit the receipt

```bash
git add dax/data_raw/w4_availability_audit_receipt.json
git commit -m "dax: record W4 account availability probe result"
git push -u origin claude/dax-research-direction-1ohi97
```

The receipt carries no key, no task text, and no prompts — only event IDs,
model IDs, statuses, and counts. It is safe to commit.

## What this does not do

It does not authorize or perform any capture. `full_capture_allowed` still
requires the signed budget ceiling and, until the amendment in
`dax/memo/AMENDMENT_DRAFT_w4_capture_scoring_split.md` is signed, complete task
duration. The probe only establishes **what is still reachable**, which is the
input that makes the amendment decision concrete.
