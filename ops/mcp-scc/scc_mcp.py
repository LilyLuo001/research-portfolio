#!/usr/bin/env python3
"""
scc_mcp.py — MCP server giving Claude Code hands on the BU SCC + local git.

Runs LOCALLY (your laptop, stdio transport). Exposes:
  git_status / git_stage / git_commit / git_push / git_pull / git_branch
      — local repo management (confined under MCP_GIT_ROOT)
  scc_check / scc_exec / scc_submit_job / scc_job_status
      — remote shell + SGE batch (qsub/qstat) on scc1.bu.edu
  scc_sync
      — rsync a local directory to/from SCC storage

SECURITY MODEL (read before editing):
  * NO passwords, ever. Every ssh/rsync call runs with BatchMode=yes, which
    makes password prompts a hard failure instead of a hang.
  * Auth = your existing SSH ControlMaster socket: you log in ONCE per work
    session (BU password + Duo push) with a plain `ssh scc1.bu.edu`; OpenSSH
    keeps the authenticated connection open (ControlPersist) and every tool
    call here multiplexes over it. When the socket expires, tools return a
    clear "run ssh once" error — they never try to authenticate themselves.
  * scc_exec is arbitrary shell under YOUR account on a shared university
    cluster. Keep this server local-only (stdio; never bind it to a port)
    and treat tool approval prompts in Claude Code as the safety gate.

Config (env vars, all optional):
  SCC_USER          SCC login name (default: local $USER)
  SCC_HOST          default scc1.bu.edu
  SCC_CONTROL_PATH  default ~/.ssh/cm-%r@%h-%p  (must match ~/.ssh/config)
  MCP_GIT_ROOT      directory git tools are confined to (default ~)
"""
import os
import pathlib
import subprocess

from mcp.server.fastmcp import FastMCP

SCC_HOST = os.getenv("SCC_HOST", "scc1.bu.edu")
SCC_USER = os.getenv("SCC_USER") or os.getenv("USER", "")
CONTROL_PATH = os.getenv("SCC_CONTROL_PATH", "~/.ssh/cm-%r@%h-%p")
GIT_ROOT = pathlib.Path(os.path.expanduser(os.getenv("MCP_GIT_ROOT", "~"))).resolve()
MAX_OUT = 24_000          # clip tool output so one huge log can't flood context

TARGET = f"{SCC_USER}@{SCC_HOST}" if SCC_USER else SCC_HOST
SSH_OPTS = ["-o", "BatchMode=yes",                 # never prompt for a password
            "-o", f"ControlPath={CONTROL_PATH}",
            "-o", "ConnectTimeout=10"]

mcp = FastMCP("bu-scc")


# --------------------------------------------------------------- plumbing --

def _clip(s: str) -> str:
    s = s or ""
    if len(s) <= MAX_OUT:
        return s
    return s[:MAX_OUT] + f"\n…[clipped {len(s) - MAX_OUT} chars]"


def _run(cmd, cwd=None, timeout=120, stdin_text=None) -> str:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, input=stdin_text)
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT after {timeout}s] {' '.join(map(str, cmd))}"
    out = p.stdout.rstrip()
    if p.stderr.strip():
        out += ("\n[stderr] " + p.stderr.strip())
    return f"[exit {p.returncode}]\n{_clip(out).strip()}"


def _master_alive() -> bool:
    p = subprocess.run(["ssh", "-O", "check",
                        "-o", f"ControlPath={CONTROL_PATH}", TARGET],
                       capture_output=True, text=True, timeout=15)
    return p.returncode == 0


NEED_LOGIN = (f"No live SSH master connection to {TARGET}.\n"
              f"Open one in YOUR terminal (BU password + Duo, once per session):\n"
              f"    ssh {TARGET} true\n"
              f"then retry this tool. (ControlPersist keeps it alive; see "
              f"ops/mcp-scc/README.md.)")


def _ssh(command: str, timeout: int = 120, stdin_text=None) -> str:
    if not _master_alive():
        return NEED_LOGIN
    return _run(["ssh", *SSH_OPTS, TARGET, command],
                timeout=timeout, stdin_text=stdin_text)


def _repo(repo_path: str) -> pathlib.Path:
    p = pathlib.Path(os.path.expanduser(repo_path)).resolve()
    if not p.is_relative_to(GIT_ROOT):
        raise ValueError(f"{p} is outside MCP_GIT_ROOT ({GIT_ROOT})")
    if not (p / ".git").exists():
        raise ValueError(f"{p} is not a git repository")
    return p


# -------------------------------------------------------------- git tools --

@mcp.tool()
def git_status(repo_path: str) -> str:
    """Working-tree status + current branch + ahead/behind of upstream."""
    p = _repo(repo_path)
    return _run(["git", "status", "--short", "--branch"], cwd=p)


@mcp.tool()
def git_stage(repo_path: str, paths: str = "-A") -> str:
    """Stage files. `paths` is space-separated pathspecs, default -A (all)."""
    p = _repo(repo_path)
    return _run(["git", "add", *paths.split()], cwd=p)


@mcp.tool()
def git_commit(repo_path: str, message: str) -> str:
    """Commit whatever is staged."""
    p = _repo(repo_path)
    return _run(["git", "commit", "-m", message], cwd=p)


@mcp.tool()
def git_push(repo_path: str, remote: str = "origin", branch: str = "",
             set_upstream: bool = False) -> str:
    """Push. Empty branch = current. Uses your local git credentials/agent."""
    p = _repo(repo_path)
    cmd = ["git", "push"]
    if set_upstream:
        cmd.append("-u")
    cmd.append(remote)
    if branch:
        cmd.append(branch)
    return _run(cmd, cwd=p, timeout=180)


@mcp.tool()
def git_pull(repo_path: str, remote: str = "origin", branch: str = "",
             ff_only: bool = True) -> str:
    """Pull (fast-forward only by default — refuses to create merge knots)."""
    p = _repo(repo_path)
    cmd = ["git", "pull"] + (["--ff-only"] if ff_only else ["--no-rebase"])
    cmd.append(remote)
    if branch:
        cmd.append(branch)
    return _run(cmd, cwd=p, timeout=180)


@mcp.tool()
def git_branch(repo_path: str, action: str = "list", name: str = "") -> str:
    """Branch management. action ∈ list | create | switch | delete."""
    p = _repo(repo_path)
    if action == "list":
        return _run(["git", "branch", "-vv", "--all"], cwd=p)
    if not name:
        return "[exit 2]\nbranch name required for " + action
    cmd = {"create": ["git", "switch", "-c", name],
           "switch": ["git", "switch", name],
           "delete": ["git", "branch", "-d", name]}.get(action)
    if not cmd:
        return f"[exit 2]\nunknown action: {action}"
    return _run(cmd, cwd=p)


# -------------------------------------------------------------- SCC tools --

@mcp.tool()
def scc_check() -> str:
    """Is the authenticated SSH master connection to the SCC alive?"""
    if _master_alive():
        return f"OK — live multiplexed connection to {TARGET}."
    return NEED_LOGIN


@mcp.tool()
def scc_exec(command: str, timeout_s: int = 120) -> str:
    """Run a shell command on the SCC login node over the existing
    authenticated connection. Never prompts; fails cleanly if no session."""
    return _ssh(command, timeout=min(timeout_s, 600))


@mcp.tool()
def scc_submit_job(script_text: str = "", remote_script_path: str = "",
                   qsub_args: str = "") -> str:
    """Submit an SGE batch job (BU SCC uses qsub). Provide either script_text
    (submitted via stdin) or remote_script_path (a file already on the SCC).
    Returns qsub's output (contains the job id)."""
    if bool(script_text) == bool(remote_script_path):
        return "[exit 2]\nprovide exactly one of script_text / remote_script_path"
    if remote_script_path:
        return _ssh(f"qsub {qsub_args} {remote_script_path}")
    return _ssh(f"qsub {qsub_args}", stdin_text=script_text)


@mcp.tool()
def scc_job_status(job_id: str = "") -> str:
    """qstat for your jobs; pass a job_id for the detailed view."""
    if job_id:
        return _ssh(f"qstat -j {job_id} 2>&1 | head -60")
    return _ssh(f"qstat -u {SCC_USER or '$USER'}")


@mcp.tool()
def scc_sync(local_dir: str, remote_dir: str, direction: str = "push",
             delete: bool = False, dry_run: bool = False) -> str:
    """rsync a directory between this machine and SCC storage over the
    multiplexed connection. direction: push (local→SCC) or pull (SCC→local).
    delete=True mirrors deletions — use with dry_run=True first."""
    if not _master_alive():
        return NEED_LOGIN
    local = str(pathlib.Path(os.path.expanduser(local_dir)).resolve()) + "/"
    remote = f"{TARGET}:{remote_dir.rstrip('/')}/"
    src, dst = (local, remote) if direction == "push" else (remote, local)
    cmd = ["rsync", "-az", "--info=stats1",
           "-e", f"ssh -o BatchMode=yes -o ControlPath={CONTROL_PATH}"]
    if delete:
        cmd.append("--delete")
    if dry_run:
        cmd.append("--dry-run")
    cmd += [src, dst]
    return _run(cmd, timeout=600)


if __name__ == "__main__":
    mcp.run()
