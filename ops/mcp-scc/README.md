# bu-scc MCP server — Claude Code hands on the SCC, no copy-paste relay

Runs **on your laptop** (stdio). Gives a local Claude Code session tools for
local git management, remote shell + SGE batch jobs on `scc1.bu.edu`, and
rsync file sync — all over ONE SSH connection you authenticate yourself.

**What this does and does not do about Duo:** BU SCC requires password + Duo
on login. This server never handles either. You log in once per work session
in your own terminal; OpenSSH ControlMaster keeps that authenticated
connection open, and every tool call multiplexes over it (an officially
supported OpenSSH feature). When it expires you just log in again — the tools
tell you so instead of hanging (`BatchMode=yes` forbids password prompts).

## 1. One-time SSH setup (your laptop)

Append to `~/.ssh/config`:

```
Host scc scc1.bu.edu
    HostName scc1.bu.edu
    User qluo
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h-%p
    ControlPersist 8h
    ServerAliveInterval 60
```

`ControlPersist 8h` keeps the authenticated connection alive for 8 hours
after your last use of it. Then, **once per work session**:

```bash
ssh scc1.bu.edu true      # BU password + Duo push, once
ssh -O check scc1.bu.edu  # "Master running" = every tool now works silently
```

If your account has SSH keys enrolled on SCC, `ssh-add` your key too — the
master login then only needs Duo. Optional, not required.

## 2. Install

```bash
cd ~/portfolio/ops/mcp-scc          # or wherever this repo is cloned
python3 -m pip install -r requirements.txt
```

## 3. Register with Claude Code

Claude Code CLI — add to `~/.claude.json` (or a project `.mcp.json`);
Claude Desktop — same block under `mcpServers` in
`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bu-scc": {
      "command": "python3",
      "args": ["/ABSOLUTE/PATH/TO/portfolio/ops/mcp-scc/scc_mcp.py"],
      "env": {
        "SCC_USER": "qluo",
        "SCC_HOST": "scc1.bu.edu",
        "MCP_GIT_ROOT": "/ABSOLUTE/PATH/TO/your/code"
      }
    }
  }
}
```

Restart Claude Code / Desktop; `/mcp` should list `bu-scc` with 11 tools.

## 4. Tools

| tool | what |
|---|---|
| `git_status/stage/commit/push/pull/branch` | local repos, confined under `MCP_GIT_ROOT` |
| `scc_check` | is the authenticated connection alive? |
| `scc_exec` | shell on the SCC login node (10-min cap) |
| `scc_submit_job` / `scc_job_status` | `qsub` (inline script or remote path) / `qstat` |
| `scc_sync` | rsync push/pull, `--delete` only with explicit flag, `dry_run` supported |

## 5. Security notes

- No credential is ever stored, passed, or prompted for by this server.
- `scc_exec` is arbitrary shell under your SCC account: leave the server on
  stdio (never expose it on a network port) and treat Claude Code's
  tool-approval prompts as your gate.
- SCC login nodes are for light work; anything heavy goes through
  `scc_submit_job` (that's what the batch system is for).
- This composes with `ops/box/inbox.sh` (the 24/7 git-driven channel): MCP is
  the interactive hands, the inbox is the autonomous loop.
