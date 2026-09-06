# NEED_HUMAN: this seat cannot reach the WRDS mirror

**Raised** 2026-09-06 · **Task** no-purchase ETF/stock price-discovery feasibility
· **Session** Claude Code on the web (remote cloud container), branch
`claude/terminal-access-setup-xw4qf7`

The instruction is executable. This *seat* cannot execute it. Every module of
the bounded package (§1–§5) reads either the SCC-mirrored WRDS archive or the
FRBSF public page, and this container reaches neither. That is a routing fact,
not a permissions one — the owner granted full permission, and permission is not
what is missing.

## What was tested, and what came back

| # | Check | Result |
|---|---|---|
| 1 | `ls /projectnb` | `No such file or directory` — the SCC filesystem is not mounted here |
| 2 | `ls ~/.ssh` | empty; no key, no `known_hosts`, no ControlMaster socket |
| 3 | `nc -vz scc1.bu.edu 22` | timeout after 20s (DNS resolves to 192.12.187.130; the port does not open) |
| 4 | `curl --proxytunnel telnet://scc1.bu.edu:22` | terminated — the egress proxy tunnels HTTPS only |
| 5 | `curl https://scc-ondemand2.bu.edu/` | `CONNECT tunnel failed, 403` — `connect_rejected (organization policy)` |
| 6 | `curl https://www.frbsf.org/...usmpd...` | same 403 — so the §4 public macro supplement is blocked too |
| 7 | `curl https://api.github.com` | `200` — egress works; the allowlist simply excludes these hosts |
| 8 | `ListAgents` | no other Claude session reachable — nothing to delegate to |

## Why "SCC is logged in on the Mac terminal" does not carry over

It does — to a session running **on that Mac**. The repo's own bridge says so in
`ops/mcp-scc/README.md`: `bu-scc` is a **stdio** MCP server that "runs on your
laptop", multiplexing over an OpenSSH **ControlMaster socket** created by the
Duo login in the owner's terminal. Three consequences:

- The authenticated socket is a file on the Mac (`~/.ssh/cm-%r@%h-%p`). A cloud
  container has no path to it.
- `bu-scc` is not registered in this session — the tool list here carries only
  `github` and `claude-code-remote`.
- `ops/box` is not an alternative: per its README it is a VPS running cheap
  model APIs, holding no SCC credential.

So the SCC login is real and usable; it is reachable from a **local** Claude Code
session on that Mac, and from this one it is not.

## What is NOT the blocker

Worth stating, because each would otherwise look like a candidate:

- Not authorisation. No purchase was needed and none was contemplated.
- Not the archive. `_migration_meta/FINAL_VERIFY_REPORT.txt` is unread here, so
  its integrity is simply **unknown from this seat** — not suspected bad.
- Not the instruction, which is internally consistent and executable as written.

## Unblocking, cheapest first

1. **Run stage 0 where the data is** — a Claude Code session on the Mac (which
   already has `bu-scc`), or `ssh scc1.bu.edu` directly, in a clone of this repo:

   ```bash
   python news_price_discovery/prepurchase_wrds/stage0_discover.py \
       --out news_price_discovery/prepurchase_wrds/out
   ```

   It reads footers only, writes `source_catalog.tsv` + `stage0_report.json`,
   and prints which capability gates the real schemas satisfy. Full brief:
   `ops/briefs/opus/OPUS-NPD-prepurchase.md`.

2. **Or paste back two artefacts** and this seat can carry stages 1–5 forward as
   far as schema-level work allows: `stage0_report.json`, plus the head of
   `FINAL_VERIFY_REPORT.txt`. Note this still cannot produce empirical results —
   those need the data, not its schema.

3. **Or add `*.bu.edu` to the environment's egress allowlist** — this only opens
   HTTPS, which does not by itself give the archive; it would unblock the §4
   FRBSF macro supplement.

Under CLAUDE.md meta-rule 1 no row count, coverage figure, or coefficient may be
written from the manual or from memory, so no stage past 0 is startable here.
Stage 0's code is committed, tested (13 tests, no WRDS access required) and ready
to run the moment it is pointed at the archive.
