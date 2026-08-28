"""Resumable private W4 capture primitives with hard, atomic cost control."""

from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping

from .contract import ContractError, metered_cost_usd, sha256_bytes


RETRYABLE_HTTP = {408, 409, 429, 500, 502, 503, 504}
LINEAGE_FIELDS = (
    "task_id",
    "event_id",
    "event_date",
    "source_model_id",
    "measurement_model_id",
    "measurement_route",
    "perturbation_id",
    "pi_variant",
    "repetition_id",
    "mapping_commit",
    "mapping_receipt_sha256",
    "price_lineage_version",
    "price_lineage_sha256",
)


class HarnessError(RuntimeError):
    pass


class BudgetExceeded(HarnessError):
    pass


def _lineage(item: Mapping[str, object]) -> dict[str, object]:
    """Copy only public identifiers/hashes needed to trace a terminal row."""

    return {key: item[key] for key in LINEAGE_FIELDS if key in item}


def _not_estimable_fields() -> dict[str, object]:
    """Canonical measurement fields for a blocked or failed item."""

    return {
        "model_returned": None,
        "success": False,
        "pi_successes": 0,
        "pi_trials": 0,
        "pi": None,
        "pi_ci_lower": None,
        "pi_ci_upper": None,
        "pi_uncertainty_method": "not_estimable",
    }


class EncryptedStore:
    """Authenticated encrypted object store. Plaintext exists only in memory."""

    def __init__(self, root: pathlib.Path, key: bytes):
        try:
            from cryptography.fernet import Fernet
        except ImportError as error:
            raise HarnessError("cryptography is required for private prompt storage") from error
        if not root.is_absolute():
            raise HarnessError("private encrypted store path must be absolute")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        root.chmod(0o700)
        self.root = root
        try:
            self._fernet = Fernet(key)
        except (TypeError, ValueError) as error:
            raise HarnessError("invalid DAX_W4_ENCRYPTION_KEY") from error

    @staticmethod
    def key_from_env(variable: str = "DAX_W4_ENCRYPTION_KEY") -> bytes:
        value = os.environ.get(variable)
        if not value:
            raise HarnessError(f"missing private encryption variable {variable}")
        return value.encode("ascii")

    def _path(self, object_id: str) -> pathlib.Path:
        safe = sha256_bytes(object_id.encode("utf-8"))
        return self.root / f"{safe}.fernet"

    def put_json(self, object_id: str, payload: Mapping[str, object]) -> str:
        plaintext = json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
        ciphertext = self._fernet.encrypt(plaintext)
        path = self._path(object_id)
        temporary = path.with_suffix(".tmp")
        with temporary.open("wb") as handle:
            handle.write(ciphertext)
        temporary.chmod(0o600)
        os.replace(temporary, path)
        return sha256_bytes(ciphertext)

    def get_json(self, object_id: str) -> dict[str, object]:
        ciphertext = self._path(object_id).read_bytes()
        try:
            plaintext = self._fernet.decrypt(ciphertext)
        except Exception as error:
            raise HarnessError("encrypted private object failed authentication") from error
        payload = json.loads(plaintext)
        if not isinstance(payload, dict):
            raise HarnessError("encrypted private object must be a JSON object")
        return payload


class BudgetLedger:
    """SQLite reservation ledger; reservations prevent concurrent overspend."""

    def __init__(self, path: pathlib.Path, ceiling_usd: float):
        if ceiling_usd <= 0:
            raise HarnessError("budget ceiling must be positive")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.parent.chmod(0o700)
        self.path = path
        self.ceiling_usd = float(ceiling_usd)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS items ("
                "item_id TEXT PRIMARY KEY, reserved_usd REAL NOT NULL, "
                "realized_usd REAL, status TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=30, isolation_level=None)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def reserve(self, item_id: str, estimated_usd: float) -> bool:
        if estimated_usd < 0:
            raise HarnessError("estimated cost cannot be negative")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT status FROM items WHERE item_id=?", (item_id,)
            ).fetchone()
            if existing:
                connection.execute("COMMIT")
                return False
            committed, reserved = connection.execute(
                "SELECT "
                "COALESCE(SUM(CASE WHEN status IN ('settled','settled_partial') THEN realized_usd ELSE 0 END),0),"
                "COALESCE(SUM(CASE WHEN status IN ('reserved','retained','settled_partial') THEN reserved_usd ELSE 0 END),0) "
                "FROM items"
            ).fetchone()
            if committed + reserved + estimated_usd > self.ceiling_usd + 1e-12:
                connection.execute("ROLLBACK")
                raise BudgetExceeded("next item would exceed the frozen W4 ceiling")
            connection.execute(
                "INSERT INTO items VALUES (?,?,NULL,'reserved')",
                (item_id, float(estimated_usd)),
            )
            connection.execute("COMMIT")
            return True

    def settle(self, item_id: str, realized_usd: float, *, retain_usd: float = 0.0) -> None:
        if realized_usd < 0:
            raise HarnessError("realized cost cannot be negative")
        if retain_usd < 0:
            raise HarnessError("retained unknown cost cannot be negative")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT reserved_usd,status FROM items WHERE item_id=?", (item_id,)
            ).fetchone()
            if not row:
                connection.execute("ROLLBACK")
                raise HarnessError("cannot settle an unreserved item")
            if row[1] in {"settled", "settled_partial"}:
                connection.execute("COMMIT")
                return
            committed, other_reserved = connection.execute(
                "SELECT "
                "COALESCE(SUM(CASE WHEN status IN ('settled','settled_partial') THEN realized_usd ELSE 0 END),0),"
                "COALESCE(SUM(CASE WHEN status IN ('reserved','retained','settled_partial') AND item_id<>? "
                "THEN reserved_usd ELSE 0 END),0) FROM items",
                (item_id,),
            ).fetchone()
            if committed + other_reserved + realized_usd + retain_usd > self.ceiling_usd + 1e-12:
                connection.execute("ROLLBACK")
                raise BudgetExceeded("realized cost would exceed the frozen W4 ceiling")
            connection.execute(
                "UPDATE items SET realized_usd=?,reserved_usd=?,status=? WHERE item_id=?",
                (
                    float(realized_usd),
                    float(retain_usd),
                    "settled_partial" if retain_usd else "settled",
                    item_id,
                ),
            )
            connection.execute("COMMIT")

    def retain_unknown(self, item_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE items SET status='retained' WHERE item_id=? AND status='reserved'",
                (item_id,),
            )

    def item_state(self, item_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT reserved_usd,realized_usd,status FROM items WHERE item_id=?",
                (item_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "reserved_usd": float(row[0]),
            "realized_usd": None if row[1] is None else float(row[1]),
            "status": str(row[2]),
        }

    def summary(self) -> dict[str, float]:
        with self._connect() as connection:
            committed, reserved = connection.execute(
                "SELECT "
                "COALESCE(SUM(CASE WHEN status IN ('settled','settled_partial') THEN realized_usd ELSE 0 END),0),"
                "COALESCE(SUM(CASE WHEN status IN ('reserved','retained','settled_partial') THEN reserved_usd ELSE 0 END),0) "
                "FROM items"
            ).fetchone()
        return {
            "ceiling_usd": self.ceiling_usd,
            "realized_usd": float(committed),
            "reserved_or_retained_usd": float(reserved),
            "remaining_usd": max(0.0, self.ceiling_usd - committed - reserved),
        }


class Checkpoint:
    """Append-only sanitized checkpoint keyed by stable item ID."""

    def __init__(self, path: pathlib.Path):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.parent.chmod(0o700)
        self.path = path
        self.completed: set[str] = set()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    if row.get("terminal"):
                        self.completed.add(str(row["item_id"]))

    def append(self, row: Mapping[str, object]) -> None:
        forbidden = {"prompt", "task_text", "response", "raw_response"}.intersection(row)
        if forbidden:
            raise HarnessError(f"checkpoint contains private fields: {sorted(forbidden)}")
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(row), sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.path.chmod(0o600)
        if row.get("terminal"):
            self.completed.add(str(row["item_id"]))


class RateLimiter:
    def __init__(self, requests_per_minute: float, *, clock: Callable[[], float] = time.monotonic, sleeper: Callable[[float], None] = time.sleep):
        if requests_per_minute <= 0:
            raise HarnessError("requests_per_minute must be positive")
        self.interval = 60.0 / requests_per_minute
        self.clock = clock
        self.sleeper = sleeper
        self.next_allowed = 0.0

    def wait(self) -> None:
        now = self.clock()
        if now < self.next_allowed:
            self.sleeper(self.next_allowed - now)
            now = self.clock()
        self.next_allowed = max(now, self.next_allowed) + self.interval


class HttpTransport:
    """Minimal JSON transport. Keys stay in memory and never enter argv."""

    def __init__(self, api_key: str, *, base_url: str = "https://api.openai.com/v1", timeout_seconds: float = 120.0):
        if not api_key:
            raise HarnessError("missing API key")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def __call__(self, endpoint_kind: str, body: Mapping[str, object]) -> dict[str, object]:
        endpoint = "/responses" if endpoint_kind == "responses" else "/chat/completions"
        request = urllib.request.Request(
            self.base_url + endpoint,
            data=json.dumps(dict(body), separators=(",", ":")).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.load(response)
        if not isinstance(payload, dict):
            raise HarnessError("provider response is not a JSON object")
        return payload


def request_body(item: Mapping[str, object], prompt: str, *, max_output_tokens: int) -> dict[str, object]:
    model = item.get("measurement_model_id")
    if not model:
        raise HarnessError("blocked item has no measurement model")
    if item.get("endpoint_kind") == "responses":
        body: dict[str, object] = {
            "model": model,
            "input": prompt,
            "max_output_tokens": max_output_tokens,
            "store": False,
        }
    else:
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "store": False,
        }
        output_parameter = str(item.get("max_output_parameter", "max_tokens"))
        if output_parameter not in {"max_tokens", "max_completion_tokens"}:
            raise HarnessError("unsupported chat output-token parameter")
        body[output_parameter] = max_output_tokens
        if item.get("supports_temperature", True):
            body["temperature"] = 0
        if item.get("supports_seed"):
            body["seed"] = int(item["deterministic_seed"])
    return body


def usage_from_response(payload: Mapping[str, object]) -> dict[str, int]:
    usage = payload.get("usage")
    if not isinstance(usage, Mapping):
        raise HarnessError("provider response lacks final usage")
    input_tokens = int(usage.get("input_tokens", usage.get("prompt_tokens", 0)))
    output_tokens = int(usage.get("output_tokens", usage.get("completion_tokens", 0)))
    input_details = usage.get("input_tokens_details", usage.get("prompt_tokens_details", {}))
    output_details = usage.get("output_tokens_details", usage.get("completion_tokens_details", {}))
    cached = int(input_details.get("cached_tokens", 0)) if isinstance(input_details, Mapping) else 0
    reasoning = int(output_details.get("reasoning_tokens", 0)) if isinstance(output_details, Mapping) else 0
    if min(input_tokens, output_tokens, cached, reasoning) < 0:
        raise HarnessError("provider returned negative token usage")
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning,
    }


def execute_item(
    item: Mapping[str, object],
    *,
    prompt_store: EncryptedStore,
    response_store: EncryptedStore,
    transport: Callable[[str, Mapping[str, object]], dict[str, object]],
    score: Callable[[Mapping[str, object]], bool],
    prices: Mapping[str, float],
    ledger: BudgetLedger,
    checkpoint: Checkpoint,
    limiter: RateLimiter,
    max_output_tokens: int,
    max_retries: int = 4,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, object] | None:
    item_id = str(item["item_id"])
    if item_id in checkpoint.completed:
        return None
    if item.get("plan_status") != "eligible":
        record = {
            "item_id": item_id,
            "terminal": True,
            "status": "blocked",
            "failure_status": "blocked",
            "failure_code": "|".join(item.get("blockers", [])),
            "realized_api_cost_usd": 0.0,
            **_not_estimable_fields(),
            **_lineage(item),
        }
        checkpoint.append(record)
        return record

    prompt_object = prompt_store.get_json(item_id)
    prompt = prompt_object.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        raise HarnessError("encrypted prompt object lacks prompt text")
    body = request_body(item, prompt, max_output_tokens=max_output_tokens)
    estimated_per_attempt = (
        max_output_tokens * float(prices["output_usd_per_1m"])
        + len(prompt.encode("utf-8")) * float(prices["input_usd_per_1m"])
    ) / 1_000_000.0
    reserved_upper_bound = estimated_per_attempt * (max_retries + 1)
    if not ledger.reserve(item_id, reserved_upper_bound):
        # The provider may already have received this item before a crash that
        # preceded checkpoint fsync. Never replay an ambiguous paid request.
        state = ledger.item_state(item_id)
        if state is None:
            raise HarnessError("ledger lost an existing item during replay check")
        retained = float(state["reserved_usd"])
        realized = state["realized_usd"]
        record = {
            "item_id": item_id,
            "terminal": True,
            "status": "measurement_failed",
            "failure_status": "measurement_failed",
            "failure_code": "ledger_state_prevents_replay",
            "usage_status": "not_estimable_existing_ledger_state",
            "ledger_status": state["status"],
            "realized_api_cost_usd": realized,
            "retained_unknown_cost_usd": retained,
            "attempts": [],
            **_not_estimable_fields(),
            **_lineage(item),
        }
        checkpoint.append(record)
        return record

    started = time.monotonic()
    attempts: list[dict[str, object]] = []
    payload: dict[str, object] | None = None
    for attempt in range(1, max_retries + 2):
        limiter.wait()
        try:
            payload = transport(str(item["endpoint_kind"]), body)
            attempts.append({"attempt": attempt, "status": "completed"})
            break
        except urllib.error.HTTPError as error:
            retryable = error.code in RETRYABLE_HTTP
            attempts.append({"attempt": attempt, "status": "http_error", "http_status": error.code, "retryable": retryable})
            if not retryable or attempt > max_retries:
                ledger.retain_unknown(item_id)
                record = {
                    "item_id": item_id,
                    "terminal": True,
                    "status": "measurement_failed",
                    "failure_status": "measurement_failed",
                    "failure_code": f"http_{error.code}",
                    "usage_status": "not_estimable_reservation_retained",
                    "realized_api_cost_usd": None,
                    "retained_unknown_cost_usd": reserved_upper_bound,
                    "attempts": attempts,
                    **_not_estimable_fields(),
                    **_lineage(item),
                }
                checkpoint.append(record)
                return record
            sleeper(min(30.0, 2.0 ** (attempt - 1)))
        except (urllib.error.URLError, TimeoutError) as error:
            attempts.append({"attempt": attempt, "status": type(error).__name__, "retryable": True})
            if attempt > max_retries:
                ledger.retain_unknown(item_id)
                record = {
                    "item_id": item_id,
                    "terminal": True,
                    "status": "measurement_failed",
                    "failure_status": "measurement_failed",
                    "failure_code": "transport_exhausted",
                    "usage_status": "not_estimable_reservation_retained",
                    "realized_api_cost_usd": None,
                    "retained_unknown_cost_usd": reserved_upper_bound,
                    "attempts": attempts,
                    **_not_estimable_fields(),
                    **_lineage(item),
                }
                checkpoint.append(record)
                return record
            sleeper(min(30.0, 2.0 ** (attempt - 1)))
    if payload is None:
        raise HarnessError("unreachable: capture loop produced no terminal state")

    latency_ms = (time.monotonic() - started) * 1000.0
    response_hash = response_store.put_json(item_id, payload)
    try:
        usage = usage_from_response(payload)
    except HarnessError:
        ledger.retain_unknown(item_id)
        record = {
            "item_id": item_id,
            "terminal": True,
            "status": "measurement_failed",
            "failure_status": "measurement_failed",
            "failure_code": "missing_or_invalid_final_usage",
            "usage_status": "not_estimable_reservation_retained",
            "realized_api_cost_usd": None,
            "retained_unknown_cost_usd": reserved_upper_bound,
            "response_ciphertext_sha256": response_hash,
            "attempts": attempts,
            **_not_estimable_fields(),
            **_lineage(item),
        }
        checkpoint.append(record)
        return record
    realized = metered_cost_usd(
        **usage,
        input_usd_per_1m=float(prices["input_usd_per_1m"]),
        cached_input_usd_per_1m=float(prices["cached_input_usd_per_1m"]),
        output_usd_per_1m=float(prices["output_usd_per_1m"]),
    )
    ambiguous_failed_attempts = sum(1 for attempt in attempts if attempt["status"] != "completed")
    ledger.settle(
        item_id,
        realized,
        retain_usd=ambiguous_failed_attempts * estimated_per_attempt,
    )
    try:
        success = bool(score(payload))
    except Exception:
        record = {
            "item_id": item_id,
            "terminal": True,
            "status": "measurement_failed",
            "failure_status": "measurement_failed",
            "failure_code": "grader_failed",
            "usage_status": "metered",
            "latency_ms": latency_ms,
            **usage,
            "realized_api_cost_usd": realized,
            "response_ciphertext_sha256": response_hash,
            "attempts": attempts,
            **_not_estimable_fields(),
            **_lineage(item),
        }
        checkpoint.append(record)
        return record
    record = {
        "item_id": item_id,
        "terminal": True,
        "status": "captured",
        "failure_status": "none",
        "failure_code": "none",
        "usage_status": "metered",
        "model_returned": payload.get("model"),
        "success": success,
        "latency_ms": latency_ms,
        **usage,
        "realized_api_cost_usd": realized,
        "retained_unknown_cost_usd": ambiguous_failed_attempts * estimated_per_attempt,
        "response_ciphertext_sha256": response_hash,
        "attempts": attempts,
        **_lineage(item),
    }
    checkpoint.append(record)
    return record
