# DAX-W4-availability-probe — brief

**Owner:** any seat with SCC access to `/usr3/graduate/qluo/dax-private/w4/`.
**Runs on:** the SCC, in a terminal. Not runnable from a cloud session.
**Cost:** USD 0. **Expected wall time:** under five minutes.
**Blocking:** yes — it is the input to a signature decision under a 61-day
irreversible deadline.

## Why this exists

`dax/capability_panel/vintage_registry.json` holds 22 rows. Fourteen are
`measurement_route: direct` — dated OpenAI snapshots that must be measured
before they retire on **2026-10-23** and **2026-12-11**. All fourteen currently
sit at `status: account_probe_required`: **nobody has ever checked whether this
account can still reach them.**

The committed receipt at `dax/data_raw/w4_availability_audit_receipt.json` is a
**no-key** run — `account_probe_performed: false`, all fourteen at
`unprobed_missing_key`. It looks like a result and is not one.

The answer decides whether the pending amendment in
`dax/memo/AMENDMENT_DRAFT_w4_capture_scoring_split.md` is worth its cost. That
amendment trades a fail-closed contract invariant, so it should not be signed
without knowing how many vintages are actually still there to save.

## Scope — read before running

This task probes **availability metadata only**. It calls the account-scoped
models list endpoint. It does not perform inference, does not spend money, and
does not begin capture.

**Do not**, under any circumstance in this task:

- run `dax.capability_panel.harness` or any capture, smoke or otherwise;
- edit `vintage_registry.json`, `contract.py`, `plan.py`, or `preflight.py`;
- create or touch anything under `dax/analysis/outcomes/` (sealed until the
  `v1.0-preregistered` tag);
- infer, constant-fill, or otherwise invent task duration — it is 0/220 and
  must stay honestly missing (portfolio meta-rule 1);
- print, echo, log, or commit the API key, or pass it as a command argument;
- commit anything from `/usr3/graduate/qluo/dax-private/`.

If anything is ambiguous, emit `NEED_HUMAN: <reason>` and stop. Do not guess.

## Preconditions

```bash
cd ~/research-portfolio          # adjust if your checkout lives elsewhere
git pull origin claude/dax-research-direction-1ohi97

# the reader refuses a loose mode; 600 or stricter is required
stat -c 'env mode: %a (want 600)' /usr3/graduate/qluo/dax-private/w4/.env
# if it is not 600:  chmod 600 /usr3/graduate/qluo/dax-private/w4/.env

# confirm outbound HTTPS without putting the key anywhere
curl -sS -o /dev/null -w 'egress check: %{http_code}\n' https://api.openai.com/v1/models
```

`401` from that curl is a **pass** — it proves egress works and that no key was
sent. A hang or proxy error means you are on a node without outbound access:
move to a login node, or export `HTTPS_PROXY` (urllib honours it; `ssh` does
not).

The probe does not import `cryptography`, so a broken crypto stack in the venv
will not stop it. That matters only for the later capture run.

## Run

```bash
python -m dax.capability_panel.availability \
  --registry dax/capability_panel/vintage_registry.json \
  --env-file /usr3/graduate/qluo/dax-private/w4/.env \
  --output dax/data_raw/w4_availability_audit_receipt.json
```

The tool reads `OPENAI_API_KEY` from inside the file, inside the process, so it
never enters argv or shell history. Keep it that way.

## Read the result

```bash
python -c "
import json;d=json.load(open('dax/data_raw/w4_availability_audit_receipt.json'))
print('probe_performed:',d['account_probe_performed'],'at',d['probed_at_utc'])
print('counts:',json.dumps(d['status_counts']))
for r in d['matrix']:
    if r['availability_status'] in ('account_unavailable','account_available'):
        print(('LOST   ' if r['availability_status']=='account_unavailable' else 'REACHED'),r['event_date'],r['source_model_id'])
"
```

Only the fourteen `direct` rows can move. The 2 open-weight stand-ins, 5 blocked
aliases, and 1 binding exclusion keep their status by construction — that is
correct, not a partial failure.

`shutdown_date` stays `null` in every row even on success: the models-list
endpoint returns `id`/`object`/`created`/`owned_by` and carries no retirement
field. Retirement dates are pinned in the registry from the deprecations page.
**This is not a probe failure — do not "fix" it.**

## Interpreting it

| Outcome | Meaning | Consequence |
|---|---|---|
| `account_available: 14` | every deadline-bound snapshot still reachable | nothing lost yet; the amendment is worth its cost; maximum urgency |
| mixed | some vintages already gone | capture the survivors; lost rows need approved open-weight stand-ins filed under the W0.5 rule, or become `measurement_failed` per design memo §1.2 |
| `account_unavailable: 14` | **suspect the key, not the world** | fourteen simultaneous retirements is far less likely than a key scoped to the wrong project. Verify scoping before recording any row as lost. Do not file stand-ins on this basis. |

That third row matters: recording fourteen false losses would trigger a large
and unnecessary stand-in filing effort, and would misinform the signature
decision. When in doubt, `NEED_HUMAN:`.

## Done means

1. `dax/data_raw/w4_availability_audit_receipt.json` shows
   `account_probe_performed: true` with a non-null `probed_at_utc`.
2. The receipt is committed and pushed to
   `claude/dax-research-direction-1ohi97`. It carries no key, no task text, and
   no prompts — only event IDs, model IDs, statuses, and counts, so it is safe
   to commit. Verify that by eye before committing.
3. The `counts:` line and any `LOST` lines are reported back to the owner.

```bash
git add dax/data_raw/w4_availability_audit_receipt.json
git commit -m "dax: record W4 account availability probe result"
git push -u origin claude/dax-research-direction-1ohi97
```

## Explicitly not in scope

Capture, the amendment itself, duration work, S3 design, and anything under
`dax/analysis/outcomes/`. `full_capture_allowed` remains gated on the signed
budget ceiling and, until the amendment is signed, on complete task duration.
This task establishes **what is still reachable**, nothing more.
