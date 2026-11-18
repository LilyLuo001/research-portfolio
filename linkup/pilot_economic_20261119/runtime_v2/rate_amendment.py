"""Additive, quiescent rate-only amendment. Never contacts Azure or resets a run."""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import time
import types

VERSION = "economic-scheduler-rate-amendment-v2"
OLD_TPM, NEW_TPM, VERIFIED_TPM = 80000, 200000, 250000
CLOUD_RUN = Path("/home/linkup/migration/pilot_economic_20261119/run01")
AMENDMENT_KEY = "scheduler_rate_amendment_v2"
V2_FILES = ("rate_amendment.py", "pilot_worker_v2.py")
APPROVED_BASE_CODE = {
    "pilot_common.py": "b98f6da6e313035f2673810f0fb5a9f6a67f9a4e8a906e610f7f272cb33df77f",
    "pilot_worker.py": "2cb02e880b6fd33636e19d31776ac6f44d6cbde53a466d395d554458e2a13e3c",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def base_runtime(directory):
    directory = Path(directory).resolve()
    policy_path = directory / "policy.json"
    policy = json.loads(policy_path.read_text())
    if policy.get("code_sha256") != APPROVED_BASE_CODE:
        raise RuntimeError("exact_original_runtime_required")
    for name in ("pilot_common.py", "pilot_worker.py"):
        if sha(directory / "runtime" / name) != policy["code_sha256"][name]:
            raise RuntimeError("original_runtime_pin_mismatch")
    common = module("economic_rate_base_common", directory / "runtime/pilot_common.py")
    common.validate_policy(policy)
    return common, policy, sha(policy_path)


@contextlib.contextmanager
def quiescent_locks(common, directory):
    with contextlib.ExitStack() as stack:
        for leg in sorted(common.MODELS):
            stack.enter_context(common.process_lock(directory, leg))
        yield


def readonly_db(directory):
    db = sqlite3.connect((Path(directory) / "ADMISSION_PRIVATE.sqlite3").as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def assert_identity(common, db, policy_sha):
    row = db.execute("SELECT value FROM meta WHERE key='identity'").fetchone()
    expected = {"policy_sha256": policy_sha, "version": common.VERSION, "models": common.MODELS}
    if not row or common.parse_json(row[0]) != expected:
        raise RuntimeError("original_ledger_identity_mismatch")


def assert_quiescent(db):
    if db.execute("SELECT 1 FROM meta WHERE key='global_hold'").fetchone():
        raise RuntimeError("existing_hold_must_not_be_cleared")
    if db.execute("SELECT 1 FROM attempts WHERE state IN ('forwarding_uncertain','transport_uncertain_no_retry')").fetchone():
        raise RuntimeError("active_or_uncertain_request_forbids_amendment")


def snapshot(common, db, directory):
    """Hash private row identities and content without exporting either."""
    tables = {}
    for name, order in (("attempts", "id"), ("claims", "leg,context"), ("batches", "id"), ("quarantine", "context")):
        rows = [dict(row) for row in db.execute("SELECT * FROM " + name + " ORDER BY " + order)]
        tables[name] = {"count": len(rows), "sha256": hashlib.sha256(common.encoded(rows)).hexdigest()}
    meta = [dict(row) for row in db.execute("SELECT * FROM meta WHERE key NOT IN (?,?) ORDER BY key", ("Luna:tpm", AMENDMENT_KEY))]
    tables["unchanged_meta"] = {"count": len(meta), "sha256": hashlib.sha256(common.encoded(meta)).hexdigest()}
    outputs, raw = {}, {}
    for row in db.execute("SELECT * FROM attempts ORDER BY id"):
        detail = common.parse_json(row["detail"])
        if row["result_path"]:
            path = common.safe_file(directory, row["result_path"])
            if sha(path) != row["result_sha"]:
                raise RuntimeError("existing_output_sha_mismatch")
            outputs[row["result_path"]] = row["result_sha"]
        if detail.get("raw_sha256"):
            relative = "results/%s/%s/HTTP_%06d_PRIVATE.bin" % (row["leg"], row["context"], row["id"])
            path = common.safe_file(directory, relative)
            if sha(path) != detail["raw_sha256"]:
                raise RuntimeError("saved_header_evidence_raw_sha_mismatch")
            raw[relative] = detail["raw_sha256"]
    aggregate = db.execute("SELECT COUNT(*),COALESCE(SUM(dollars_nano),0),COALESCE(MAX(forwarded),0) FROM attempts").fetchone()
    return {"tables": tables, "physical_attempts": aggregate[0], "reserved_nano": aggregate[1],
        "last_forward_epoch": aggregate[2], "saved_results": len(outputs), "saved_http_responses": len(raw),
        "saved_result_manifest_sha256": hashlib.sha256(common.encoded(outputs)).hexdigest(),
        "saved_http_manifest_sha256": hashlib.sha256(common.encoded(raw)).hexdigest()}


def quota_evidence(common, db):
    evidence = []
    for row in db.execute("SELECT * FROM attempts WHERE leg='Luna' ORDER BY id"):
        detail = common.parse_json(row["detail"])
        header = detail.get("rate_headers", {}).get("x-ratelimit-limit-tokens")
        if header is None:
            continue
        if str(header) != str(VERIFIED_TPM):
            raise RuntimeError("Luna_quota_evidence_is_not_uniform_exact_250000")
        if (detail.get("http_status") == 200 and detail.get("returned_model") in common.MODELS["Luna"]["returned_models"]
            and detail.get("raw_sha256")):
            evidence.append({"attempt_id": row["id"], "http_status": 200,
                "x_ratelimit_limit_tokens": VERIFIED_TPM, "raw_sha256": detail["raw_sha256"],
                "detail_sha256": hashlib.sha256(row["detail"].encode()).hexdigest()})
    if len(evidence) < 2:
        raise RuntimeError("two_saved_exact_quota_responses_required")
    return evidence


def v2_pins():
    return {name: sha(Path(__file__).parent / name) for name in V2_FILES}


def prepare(directory, output):
    common, policy, policy_sha = base_runtime(directory)
    with quiescent_locks(common, directory), contextlib.closing(readonly_db(directory)) as db:
        assert_identity(common, db, policy_sha)
        assert_quiescent(db)
        if db.execute("SELECT 1 FROM meta WHERE key=?", (AMENDMENT_KEY,)).fetchone():
            raise RuntimeError("rate_amendment_already_registered")
        old = db.execute("SELECT value FROM meta WHERE key='Luna:tpm'").fetchone()
        if not old or int(old[0]) != OLD_TPM:
            raise RuntimeError("only_original_artificial_80000_clamp_may_change")
        amendment = {"version": VERSION, "scope": "scheduler_only",
            "original_policy_sha256": policy_sha, "original_runtime_sha256": policy["code_sha256"],
            "runtime_v2_sha256": v2_pins(), "leg": "Luna", "old_scheduler_tpm": OLD_TPM,
            "effective_scheduler_tpm": NEW_TPM, "verified_provider_limit_tpm": VERIFIED_TPM,
            "global_tpm_unchanged": common.AGGREGATE_TPM,
            "quota_evidence": quota_evidence(common, db), "closed_checkpoint": snapshot(common, db, directory),
            "scientific_settings_unchanged": True, "financial_caps_unchanged": True,
            "timestamps_cooldowns_token_windows_unchanged": True,
            "original_policy_and_carrier_policy_sha_unchanged": True,
            "no_budget_reset_no_replay": True}
        common.immutable(output, common.encoded(amendment) + b"\n")
    return {"status": "rate_amendment_prepared_not_applied", "amendment_sha256": sha(output),
            "physical_attempts": amendment["closed_checkpoint"]["physical_attempts"], "new_model_calls": 0}


def verify_document(common, policy, policy_sha, amendment, directory):
    exact = {"version": VERSION, "scope": "scheduler_only", "original_policy_sha256": policy_sha,
        "original_runtime_sha256": policy["code_sha256"], "runtime_v2_sha256": v2_pins(),
        "leg": "Luna", "old_scheduler_tpm": OLD_TPM, "effective_scheduler_tpm": NEW_TPM,
        "verified_provider_limit_tpm": VERIFIED_TPM, "global_tpm_unchanged": common.AGGREGATE_TPM}
    if any(amendment.get(key) != value for key, value in exact.items()):
        raise RuntimeError("rate_amendment_scope_or_code_pin_mismatch")
    if any(amendment.get(key) is not True for key in ("scientific_settings_unchanged", "financial_caps_unchanged",
        "timestamps_cooldowns_token_windows_unchanged", "original_policy_and_carrier_policy_sha_unchanged", "no_budget_reset_no_replay")):
        raise RuntimeError("rate_amendment_preservation_contract_required")


def read_amendment(common, path, digest):
    if sha(path) != digest:
        raise RuntimeError("explicit_amendment_sha_mismatch")
    return common.read(path)


def applied_receipt(amendment, amendment_sha):
    return {"status": "scheduler_only_amendment_registered", "version": VERSION,
        "amendment_sha256": amendment_sha, "original_policy_sha256": amendment["original_policy_sha256"],
        "old_tpm": OLD_TPM, "new_tpm": NEW_TPM, "verified_provider_tpm": VERIFIED_TPM,
        "preserved_checkpoint": amendment["closed_checkpoint"], "all_non_rate_ledger_state_unchanged": True,
        "new_model_calls": 0, "scientific_contract_unchanged": True, "financial_caps_unchanged": True}


def apply(directory, amendment_path, amendment_sha):
    common, policy, policy_sha = base_runtime(directory)
    amendment = read_amendment(common, amendment_path, amendment_sha)
    verify_document(common, policy, policy_sha, amendment, directory)
    with quiescent_locks(common, directory):
        # Existing file is required; this command never creates a fresh ledger.
        db = sqlite3.connect((Path(directory) / "ADMISSION_PRIVATE.sqlite3").as_uri() + "?mode=rw", uri=True)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            assert_identity(common, db, policy_sha)
            assert_quiescent(db)
            registered = db.execute("SELECT value FROM meta WHERE key=?", (AMENDMENT_KEY,)).fetchone()
            if registered:
                existing = common.parse_json(registered[0])
                if (existing["amendment_sha256"] != amendment_sha or existing["original_policy_sha256"] != policy_sha
                    or existing["runtime_v2_sha256"] != amendment["runtime_v2_sha256"]
                    or existing["closed_checkpoint"] != amendment["closed_checkpoint"]
                    or existing["effective_scheduler_tpm"] != NEW_TPM or existing["verified_provider_limit_tpm"] != VERIFIED_TPM):
                    raise RuntimeError("different_rate_amendment_already_registered")
                # Never raise a subsequently lowered quota on repeat application.
                db.rollback()
                common.immutable(Path(directory) / "RATE_AMENDMENT_APPLIED_PUBLIC.json",
                    common.encoded(applied_receipt(amendment, amendment_sha)) + b"\n")
                return {"status": "same_amendment_already_registered_no_mutation", "amendment_sha256": amendment_sha, "new_model_calls": 0}
            before = snapshot(common, db, directory)
            if before != amendment["closed_checkpoint"] or quota_evidence(common, db) != amendment["quota_evidence"]:
                raise RuntimeError("closed_checkpoint_changed_prepare_again")
            old = db.execute("SELECT value FROM meta WHERE key='Luna:tpm'").fetchone()
            if not old or int(old[0]) != OLD_TPM:
                raise RuntimeError("old_scheduler_clamp_changed")
            registration = {"amendment_sha256": amendment_sha, "original_policy_sha256": policy_sha,
                "runtime_v2_sha256": amendment["runtime_v2_sha256"], "effective_scheduler_tpm": NEW_TPM,
                "verified_provider_limit_tpm": VERIFIED_TPM, "closed_checkpoint": before}
            db.execute("INSERT INTO meta VALUES(?,?)", (AMENDMENT_KEY, common.encoded(registration).decode()))
            db.execute("UPDATE meta SET value=? WHERE key='Luna:tpm'", (str(NEW_TPM),))
            after = snapshot(common, db, directory)
            if after != before:
                raise RuntimeError("non_rate_state_changed")
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
    receipt = applied_receipt(amendment, amendment_sha)
    common.immutable(Path(directory) / "RATE_AMENDMENT_APPLIED_PUBLIC.json", common.encoded(receipt) + b"\n")
    return receipt


def install_rate_ledger(common, policy, policy_sha, directory, amendment, amendment_sha):
    """Reuse original method bytecode; only its private read-only TPM view differs."""
    verify_document(common, policy, policy_sha, amendment, directory)
    original = common.Ledger
    rate_models = json.loads(json.dumps(common.MODELS))
    rate_models["Luna"]["tpm"] = NEW_TPM
    for leg in common.MODELS:
        for key in common.MODELS[leg]:
            if (leg, key) != ("Luna", "tpm") and rate_models[leg][key] != common.MODELS[leg][key]:
                raise RuntimeError("non_scheduler_model_change")

    def method(function):
        namespace = dict(function.__globals__)
        namespace["MODELS"] = rate_models
        result = types.FunctionType(function.__code__, namespace, function.__name__, function.__defaults__, function.__closure__)
        result.__kwdefaults__ = function.__kwdefaults__
        return result

    class RateLedger(original):
        def __init__(self, path, original_policy, original_policy_sha):
            super().__init__(path, original_policy, original_policy_sha)
            if Path(path).resolve() != Path(directory).resolve() or original_policy_sha != policy_sha:
                raise RuntimeError("rate_override_bound_to_original_run_only")
            with self.db() as db:
                registered = db.execute("SELECT value FROM meta WHERE key=?", (AMENDMENT_KEY,)).fetchone()
                if not registered:
                    raise RuntimeError("quiescent_migration_required_before_v2")
                value = common.parse_json(registered[0])
                if (value["amendment_sha256"] != amendment_sha or value["original_policy_sha256"] != policy_sha
                    or value["runtime_v2_sha256"] != v2_pins() or value["effective_scheduler_tpm"] != NEW_TPM):
                    raise RuntimeError("registered_rate_amendment_mismatch")

        reserve = method(original.reserve)
        finish = method(original.finish)

        def summary(self):
            result = super().summary()
            with self.db() as db:
                row = db.execute("SELECT value FROM meta WHERE key='Luna:tpm'").fetchone()
            result.update(scheduler_version=VERSION, rate_amendment_sha256=amendment_sha,
                original_policy_sha256=policy_sha, configured_Luna_scheduler_tpm=NEW_TPM,
                effective_Luna_scheduler_tpm=min(NEW_TPM, int(row[0]) if row else NEW_TPM),
                verified_Luna_provider_tpm=VERIFIED_TPM, original_carrier_policy_sha_preserved=True)
            return result

    common.Ledger = RateLedger
    return RateLedger


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "apply"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--amendment", type=Path)
    parser.add_argument("--amendment-sha256")
    args = parser.parse_args()
    if args.directory.resolve() != CLOUD_RUN:
        raise SystemExit("new_pilot_run_only")
    try:
        if args.action == "prepare":
            if args.output is None:
                raise RuntimeError("output_required")
            result = prepare(args.directory, args.output)
        else:
            if args.amendment is None or not args.amendment_sha256:
                raise RuntimeError("amendment_and_explicit_sha_required")
            result = apply(args.directory, args.amendment, args.amendment_sha256)
        print(json.dumps(result), flush=True)
    except Exception as exc:
        print(json.dumps({"fatal_error_type": type(exc).__name__, "raw_exception_not_logged": True}), flush=True)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
