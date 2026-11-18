"""Original pinned pilot worker plus an explicit, registered rate-only amendment."""
import argparse
import json
from pathlib import Path
import sys
import rate_amendment as amendment_control


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--rate-amendment", type=Path, required=True)
    parser.add_argument("--rate-amendment-sha256", required=True)
    own, forwarded = parser.parse_known_args()
    original = argparse.ArgumentParser(add_help=False)
    original.add_argument("--directory", type=Path, required=True)
    original.add_argument("--policy", type=Path, required=True)
    launch, _ = original.parse_known_args(forwarded)
    directory = launch.directory.resolve()
    if directory != amendment_control.CLOUD_RUN or launch.policy.resolve() != directory / "policy.json":
        raise SystemExit("original_run_and_policy_required")
    common, policy, policy_sha = amendment_control.base_runtime(directory)
    amendment = amendment_control.read_amendment(common, own.rate_amendment, own.rate_amendment_sha256)
    amendment_control.install_rate_ledger(common, policy, policy_sha, directory, amendment, own.rate_amendment_sha256)
    # The unmodified worker imports this verified original module; its ordinary
    # code/policy pins remain intact. Its transport, payload, cache and CLI run verbatim.
    sys.modules["pilot_common"] = common
    worker = amendment_control.module("economic_original_worker_v2_scheduler", directory / "runtime/pilot_worker.py")
    sys.argv = [str(directory / "runtime/pilot_worker.py"), *forwarded]
    worker.main()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"fatal_error_type": type(exc).__name__, "raw_exception_not_logged": True}), flush=True)
        raise SystemExit(2)
