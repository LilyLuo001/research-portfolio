# The always-on box (L0 + L1, 24/7)

This is the half of the architecture that actually runs round the clock. It holds
**no Claude credential** and never drives a Pro subscription — it runs your own
scripts and the cheap non-Anthropic APIs under their commercial terms (see
`ops/COMPLIANCE.md`). The Pro seats are separate, human-driven, daytime bandwidth.

What the box does, and nothing else:
1. **reap** stale leases so an abandoned task re-queues (`runner.py --reap`).
2. **dispatch** the overnight cheap-model batches, sentinel-fenced, under the
   budget cap (`dispatch.py`).
3. **digest** the day for your ~30 human minutes (`runner.py --digest`), and push
   briefs + digest back to GitHub so the seats read them.

The seats never read the box directly — everything rendezvous through the repo.

## One-time setup

Any always-on Linux machine (a ¥ / $5 VPS is plenty; the box does no heavy compute —
the model APIs do). Then:

```bash
git clone <your repo url> ~/portfolio
cd ~/portfolio/research-portfolio

python3 -m venv .venv && . .venv/bin/activate
pip install pyyaml pandas pyarrow requests

# L1 API keys live ONLY on this box, never in the repo:
cp ops/box/env.example ops/box/.env
$EDITOR ops/box/.env          # fill in the keys you have; leave the rest blank
# ops/box/.env is git-ignored — confirm: git check-ignore ops/box/.env

git config user.email "you@example.com"     # the box commits briefs/digest as you
git config user.name  "portfolio-box"
```

## Prove the cheap layer before trusting it

```bash
set -a; . ops/box/.env; set +a
python ops/runner/dispatch.py --workers      # shows which keys are live
python ops/runner/dispatch.py --smoke        # SH-l1-smoke: sentinel-fenced dry-run
```

`--smoke` needs no keys: it exercises the dispatch path for every worker and
proves the sentinel fence voids a bad batch. Once your keys are in and a worker
shows `LIVE`, wire the real POST in `models.py` (`dispatch(..., dry_run=False)`)
and re-run one live batch before putting it on cron.

## Cron

Install the schedule in `ops/box/crontab` (edit the repo path first):

```bash
crontab ops/box/crontab
crontab -l          # verify
```

That runs the reaper every 30 min, dispatches the overnight L1 batch nightly,
writes the evening digest, and pushes briefs + digest to GitHub. Your morning
starts at `make plan`; your evening is the digest and the gate decisions in
`ops/decisions.md`.

## What stays off the box

- **No Claude token.** L2 (Claude Code / claude.ai) is you, in the official apps.
- **No NDA data, no DAX outcomes** before the `v1.0-preregistered` tag — CI blocks
  both, but the box shouldn't stage them either.
- **DAX-W4 capability-panel spend** is project *data* cost on its own budget line,
  NOT the ¥300–500 L1 envelope in `budget.py`.
