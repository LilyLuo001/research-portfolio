#!/usr/bin/env python3
"""Publish sealed regional shards from a login node without holding compute."""
import argparse, fcntl, json, os, subprocess, sys, time
from pathlib import Path


def atomic_json(path, value):
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def sealed_outputs(buffer_root, subdirs):
    roots = [buffer_root / name for name in subdirs] if subdirs else [buffer_root]
    found = {}
    for root in roots:
        root.mkdir(parents=True, exist_ok=True)
        for path in root.iterdir():
            if (path.is_dir() and not path.name.endswith(".work")
                    and (path / "SHARD_COMPLETE.json").is_file()):
                if path.name in found:
                    raise RuntimeError("duplicate sealed shard across buffer partitions: " + path.name)
                found[path.name] = path
    return [found[key] for key in sorted(found)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--buffer-root", type=Path, required=True); p.add_argument("--checkpoint-root", type=Path, required=True)
    p.add_argument("--buffer-subdirs", nargs="*", default=[])
    p.add_argument("--lock-name", default="login-transfer.lock")
    p.add_argument("--status-name", default="TRANSFER_WORKER_STATUS.json")
    p.add_argument("--compute-complete-name", default="REGION_QUEUE_COMPLETE.json")
    p.add_argument("--published-complete-name", default="REGION_PUBLISHED_COMPLETE.json")
    p.add_argument("--transfer", type=Path, required=True); p.add_argument("--host", required=True)
    p.add_argument("--port", required=True); p.add_argument("--user", required=True)
    p.add_argument("--key", required=True); p.add_argument("--known-hosts", required=True)
    p.add_argument("--control-path", required=True); p.add_argument("--remote-root", required=True)
    p.add_argument("--remote-cap-bytes", type=int, default=420_000_000_000)
    p.add_argument("--poll-seconds", type=int, default=20); p.add_argument("--max-runtime-seconds", type=int, default=180_000)
    args = p.parse_args(); args.buffer_root.mkdir(parents=True, exist_ok=True); args.checkpoint_root.mkdir(parents=True, exist_ok=True)
    if any(not name or name in (".", "..") or "/" in name for name in args.buffer_subdirs):
        raise ValueError("buffer subdirs must be simple names")
    if any("/" in name for name in (args.lock_name, args.status_name,
                                      args.compute_complete_name, args.published_complete_name)):
        raise ValueError("marker/lock/status names must be simple filenames")
    lock = (args.checkpoint_root / args.lock_name).open("a+")
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: raise SystemExit("login transfer worker already active")
    started = time.time(); failures = 0
    while time.time() - started < args.max_runtime_seconds:
        sealed = sealed_outputs(args.buffer_root, args.buffer_subdirs)
        if not sealed:
            compute_complete = args.checkpoint_root / args.compute_complete_name
            if compute_complete.is_file():
                expected = json.loads(compute_complete.read_text())["planned_shards"]
                published = len(list(args.checkpoint_root.glob("*.published.json")))
                if published == expected:
                    atomic_json(args.checkpoint_root / args.published_complete_name,
                                {"status": "complete", "planned_shards": expected,
                                 "published_receipts": published,
                                 "finished_at": time.time()})
                    return
                atomic_json(args.checkpoint_root / args.status_name,
                            {"status": "awaiting_missing_sealed_outputs", "planned_shards": expected,
                             "published_receipts": published, "at": time.time()})
            time.sleep(args.poll_seconds); continue
        source = sealed[0]; receipt = args.checkpoint_root / (source.name + ".published.json")
        command = [sys.executable, str(args.transfer), "--source", str(source),
                   "--allowed-source-root", str(args.buffer_root), "--local-receipt", str(receipt),
                   "--host", args.host, "--port", args.port, "--user", args.user,
                   "--key", args.key, "--known-hosts", args.known_hosts,
                   "--control-path", args.control_path, "--remote-root", args.remote_root,
                   "--shard-id", source.name, "--remote-cap-bytes", str(args.remote_cap_bytes),
                   "--command-timeout-seconds", "75"]
        try:
            subprocess.run(command, check=True, timeout=90)
            failures = 0
            atomic_json(args.checkpoint_root / args.status_name,
                        {"status": "running", "last_published": source.name, "at": time.time()})
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            failures += 1
            atomic_json(args.checkpoint_root / args.status_name,
                        {"status": "backoff", "shard_id": source.name, "failures": failures,
                         "error_type": type(exc).__name__, "source_retained": source.exists(), "at": time.time()})
            time.sleep(min(300, 15 * (2 ** min(failures - 1, 4))))
    atomic_json(args.checkpoint_root / args.status_name,
                {"status": "runtime_limit", "restart_safe": True, "at": time.time()})
    raise SystemExit(75)


if __name__ == "__main__": main()
