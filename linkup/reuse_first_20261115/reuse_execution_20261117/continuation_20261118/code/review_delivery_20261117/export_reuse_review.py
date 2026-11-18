#!/usr/bin/env python3
"""Cloud-only bounded review export of an existing, read-only LinkUp sidecar.

No inference, original-text access, acceptance changes, production queue work,
or full variable-table scan. stdout/stderr contain only fixed status codes.
The real-data HTML and JSON are PRIVATE and must never enter Git or logs.
"""
import argparse
import collections
import datetime
import hashlib
import html
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

VERSION = "reuse-review-export-v1.0.0"
RELEASE_SHA = "6f77e3ee4e39d9e60e9eec7731c891c632a528440587450105af3ca1580b5b01"
RELEASE_BYTES = 5550370816
EXCLUSIONS_SHA = "05d47c86b030a8f5a4d091b49635b1481d70956d02f2c28501d7b08e668957d7"
MAX_CARRIERS = 50
MAX_ATOMS = 500
MAX_OUTPUT_BYTES = 32 * 1024 * 1024
MAX_SECONDS = 900
EXPECTED_COLUMNS = {
    "source_document": "d h k asset source_sha source_ordinal original_accepted mask_binding_state adaptation_state".split(),
    "context_state": "h original_state carrier_present original_protected reuse_excluded audit_resolution".split(),
    "variable_value": "id d h k variable_key source_path item_anchor_json dimension value_json value_present measurement_state workflow_state engineering_state eligible_original_scope derived original_mask metadata_json".split(),
    "ad_binding": "k h original_source created created_state".split(),
    "metadata_value": "k variable_key source_sha source_ordinal physical_column value_json state".split(),
    "dictionary_definition": "variable_key definition_json".split(),
}
FIELD_NOTES = {
    "d": "原来源载体标识；不是唯一广告数或新生产数。",
    "h": "既有上下文指纹；不单独创建广告到人的匹配。",
    "k": "既有广告身份键，可能为空；没有重算 JOB_HASH 或四键。",
    "asset": "原来源资产。",
    "source_sha": "原来源载体/文件的 SHA；保留来源版本。",
    "source_ordinal": "原来源中的序号。",
    "original_accepted": "原来源验收标志，未经本次导出升级。",
    "mask_binding_state": "原适配过程的 mask 绑定状态。",
    "adaptation_state": "原适配工程状态，不是语义质量认证。",
    "value_json": "数据库中原封不动的 JSON 文本；不将 null/unknown 转为否定。",
    "measurement_state": "原测量状态，与工作流验收状态分开保留。",
    "workflow_state": "原工作流状态；saved_unverified 仍未验收。",
    "engineering_state": "原工程兼容状态，不代表完整覆盖。",
    "eligible_original_scope": "仅原范围内工程可兼容，不是新的准确率认证。",
    "derived": "原有确定性派生标志，本次不新增派生。",
    "original_mask": "保留原状态/mask。",
    "source_path": "原字段路径；不是本次重新抽取。",
    "item_anchor_json": "原同项关系锚点 JSON 文本。",
    "metadata_json": "原版本、依赖 mask、路线和完整性信息 JSON 文本。",
    "created": "CREATED 为首次观察岗位发布时间代理，不证明正文产生时间。",
    "created_state": "既有日期连接状态，缺失/冲突不升级。",
    "original_source": "既有广告绑定的来源；只展示最多一个既有绑定。",
    "state": "元数据原状态；保留冲突和空值。",
}
TABLE_NOTES = {
    "source_document": "来源载体表：fixed10k 可为广告×字段族，其他可为原 review 载体。",
    "context_state": "原上下文状态；先排除保护/隔离，再读取载荷。",
    "variable_value": "长格式变量原子表；不是一行一个广告，不可直接 count 当广告总数。",
    "ad_binding": "已有身份/日期绑定；本次未匹配、未补齐、未消除来源版本差异。",
    "metadata_value": "已有结构化元数据值；与变量原子共同受 500 行上限约束。",
    "dictionary_definition": "已发布变量定义；保留五个研究模块，不把预览当全集字段。",
}


class ExportError(Exception):
    """A fixed public error code, never an original value or identifier."""


def require(condition, code):
    if not condition:
        raise ExportError(code)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_stat(path):
    s = Path(path).stat()
    return {"bytes": s.st_size, "mtime_ns": s.st_mtime_ns,
            "inode": s.st_ino, "device": s.st_dev}


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)


def safe_write(path, value):
    """Exclusive creation, mode 0600; no existing artifact is overwritten."""
    data = value.encode("utf-8")
    require(len(data) <= MAX_OUTPUT_BYTES, "output_size_cap_exceeded")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def open_readonly(path, checkpoint):
    db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    db.execute("PRAGMA trusted_schema=OFF")
    db.execute("PRAGMA temp_store=MEMORY")
    db.execute("PRAGMA cache_size=-16384")
    # One consistent read snapshot for all previews; never commit source changes.
    db.execute("BEGIN")
    db.set_progress_handler(lambda: checkpoint(sqlite_callback=True), 10000)
    # Deny mutation/ATTACH even if this script is later accidentally extended.
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
    if hasattr(sqlite3, "SQLITE_RECURSIVE"):
        allowed.add(sqlite3.SQLITE_RECURSIVE)
    def authorize(action, arg1, arg2, database, trigger):
        if action in allowed:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_PRAGMA and arg1 == "table_info" and arg2 in EXPECTED_COLUMNS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    db.set_authorizer(authorize)
    return db


def inspect_schema(db):
    schema = []
    for table, columns in EXPECTED_COLUMNS.items():
        info = [dict(row) for row in db.execute('PRAGMA table_info("' + table + '")')]
        require([row["name"] for row in info] == columns, "schema_mismatch")
        schema.append({"table": table, "description_zh": TABLE_NOTES[table], "columns": info})
    # Required keyed access path; do not fall back to a full atom-table scan.
    indexes = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    require({"variable_context", "bindings_context", "metadata_ad"} <= indexes,
            "required_targeted_lookup_index_missing")
    return schema


def select_carriers(db, denied, limit):
    """Only source metadata are scanned; no variable payloads are selected.

    Retain at most limit metadata rows per asset, then round-robin assets.
    This is a deterministic layout preview, not an accuracy/representative sample.
    """
    buckets = collections.defaultdict(list)
    rows = db.execute("""SELECT s.* FROM source_document s
        JOIN context_state c ON c.h=s.h
        WHERE c.reuse_excluded=0 AND c.original_protected=0
          AND c.original_state!='quarantined' ORDER BY s.d""")
    for row in rows:
        if row["h"] not in denied and len(buckets[row["asset"]]) < limit:
            buckets[row["asset"]].append(dict(row))
    result = []
    for index in range(limit):
        for asset in sorted(buckets):
            if index < len(buckets[asset]):
                result.append(buckets[asset][index])
                if len(result) == limit:
                    return result
    return result


def atom_ids(db, document, limit):
    # Group only a selected context's identifiers, not the whole atom table.
    rows = db.execute("""SELECT variable_key, MIN(id) AS first_id
        FROM variable_value INDEXED BY variable_context
        WHERE h=? AND d=? GROUP BY variable_key ORDER BY variable_key LIMIT ?""",
        (document["h"], document["d"], limit))
    ids = [r["first_id"] for r in rows]
    if len(ids) < limit:
        for row in db.execute("""SELECT id FROM variable_value INDEXED BY variable_context
                WHERE h=? AND d=? ORDER BY variable_key,source_path,id LIMIT ?""",
                (document["h"], document["d"], limit * 2)):
            if row["id"] not in ids:
                ids.append(row["id"])
                if len(ids) == limit:
                    break
    return ids


def collect_preview(db, denied, max_carriers, max_atoms):
    carriers = select_carriers(db, denied, max_carriers)
    require(bool(carriers), "no_unprotected_source_carrier")
    per_carrier = max_atoms // len(carriers)
    previews, used_keys = [], set()
    for document in carriers:
        require(document["h"] not in denied, "denied_context_before_payload")
        state = dict(db.execute("SELECT * FROM context_state WHERE h=?", (document["h"],)).fetchone())
        require(not state["reuse_excluded"] and not state["original_protected"]
                and state["original_state"] != "quarantined", "context_protection_changed")
        binding = db.execute("""SELECT * FROM ad_binding INDEXED BY bindings_context
            WHERE h=? AND (?='' OR k=?) ORDER BY k,original_source LIMIT 1""",
            (document["h"], document["k"], document["k"])).fetchone()
        binding = dict(binding) if binding else None
        # At most one existing bound ad per carrier; no new cross-context join.
        meta = []
        if binding:
            used_keys.add(binding["k"])
            meta = [dict(r) for r in db.execute("""SELECT * FROM metadata_value INDEXED BY metadata_ad
                WHERE k=? ORDER BY variable_key,source_sha,source_ordinal,physical_column LIMIT ?""",
                (binding["k"], min(2, per_carrier)))]
        ids = atom_ids(db, document, per_carrier - len(meta))
        atoms = []
        for identifier in ids:
            atom = dict(db.execute("SELECT * FROM variable_value WHERE id=?", (identifier,)).fetchone())
            require(atom["h"] == document["h"] and atom["d"] == document["d"], "atom_binding_mismatch")
            atoms.append(atom)
        previews.append({"source_document": document, "context_state": state,
                         "one_existing_ad_binding": binding, "metadata_atoms": meta,
                         "variable_atoms": atoms,
                         "partial_carrier_preview": True,
                         "all_atoms_or_all_bindings_included": False})
    count = sum(len(p["variable_atoms"]) + len(p["metadata_atoms"]) for p in previews)
    require(len(previews) <= MAX_CARRIERS and len(used_keys) <= MAX_CARRIERS and count <= MAX_ATOMS,
            "preview_cap_exceeded")
    return previews, {"source_carriers": len(previews), "bound_ad_keys": len(used_keys),
                      "variable_atoms": sum(len(p["variable_atoms"]) for p in previews),
                      "metadata_atoms": sum(len(p["metadata_atoms"]) for p in previews),
                      "combined_atoms": count}


def render_html(payload):
    esc = lambda value: html.escape(str(value), quote=True)
    pre = lambda value: "<pre>" + esc(json_text(value)) + "</pre>"
    items = []
    for number, p in enumerate(payload["previews"], 1):
        doc = p["source_document"]
        rows = []
        for atom in p["variable_atoms"]:
            rows.append("<tr><td>" + esc(atom["variable_key"]) + "</td><td><pre>" + esc(atom["value_json"])
                + "</pre></td><td>" + esc(atom["measurement_state"]) + "<br>" + esc(atom["workflow_state"])
                + "<br>" + esc(atom["engineering_state"]) + "</td><td>" + esc(atom["source_path"])
                + "<details><summary>全部原始列及溯源</summary>" + pre(atom) + "</details></td></tr>")
        items.append("<section><h2>预览 " + str(number) + " · " + esc(doc["asset"]) + "</h2>"
            + "<p>仅该载体的一部分变量；空白不表示无要求。原验收标志：" + esc(doc["original_accepted"]) + "。</p>"
            + "<details><summary>来源、上下文状态、一个既有广告/日期绑定</summary>"
            + pre({k: p[k] for k in ("source_document", "context_state", "one_existing_ad_binding")}) + "</details>"
            + "<table><thead><tr><th>变量</th><th>原 value_json</th><th>原状态</th><th>字段路径与完整溯源</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>"
            + "<details><summary>附带的原结构化元数据值（最多两行）</summary>" + pre(p["metadata_atoms"]) + "</details></section>")
    return """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; base-uri 'none'; form-action 'none'">
<title>LinkUp 旧成果复用表第一版 · 私有小型预览</title><style>
body{font-family:system-ui,sans-serif;max-width:1240px;margin:28px auto;padding:0 20px;line-height:1.65;color:#183044;background:#f7fafc}
h1,h2{line-height:1.3}section,.notice{background:white;border:1px solid #ccd8e1;border-radius:10px;padding:18px;margin:18px 0}
.notice{border-left:6px solid #b46900}table{width:100%;border-collapse:collapse;table-layout:fixed}th,td{border:1px solid #d4dce3;padding:9px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#eaf0f6}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;max-height:32em;overflow:auto}summary{cursor:pointer;font-weight:600}details{margin:10px 0}code{overflow-wrap:anywhere}
</style></head><body><h1>LinkUp 旧成果复用表第一版</h1><p>私有、仅供成果结构审阅；不是待标注的人工语义审核表。</p>
<div class="notice"><strong>这只是小型结构预览，不是全表、全五亿条或准确率验证集。</strong>
<p>原表有 108,292 条来源载体、45,710 个上下文、2,963,270 条变量原子。来源载体/变量原子不能当成唯一广告数。这里按来源资产做确定性预览，最多 50 个载体、50 个既有广告绑定、500 条变量与元数据原子。</p>
<p>原值、原状态和溯源未改。saved_unverified、unknown、冲突均保留；eligible_original_scope 不是新语义验收。你可以看表的结构、范围和字段组织，不需要逐条判断原文或再次人工打标签。</p>
<p>五大研究模块和约五亿全范围仍保留。本表只衔接已有细语义成果；Revelio 结果尚未产生。CREATED 是首次观察岗位发布时间代理，前后变化不自动等于 AI 因果效应。</p></div>""" + "<details><summary>本次导出范围与来源核对方式</summary>" + pre(payload["receipt"]) + "</details>" \
        + "<details><summary>字段阅读说明</summary>" + pre(FIELD_NOTES) + "</details>" \
        + "<details><summary>数据表结构</summary>" + pre(payload["schema"]) + "</details>" \
        + "<details><summary>保留的变量定义（仅定义，不含新语义判断）</summary>" + pre(payload["dictionary_definitions"]) + "</details>" \
        + "".join(items) + "</body></html>\n"


def export(args):
    os.umask(0o077)
    started = time.monotonic()
    def checkpoint(sqlite_callback=False):
        expired = time.monotonic() - started > MAX_SECONDS
        if sqlite_callback:
            return int(expired)
        require(not expired, "wall_time_cap_exceeded")
    source, exclusions = Path(args.database).resolve(), Path(args.exclusions_file).resolve()
    output = Path(args.output_dir).resolve()
    require(not any((p / ".git").exists() for p in (output, *output.parents)), "private_output_inside_git_forbidden")
    require(not output.exists(), "existing_output_preserved")
    require(1 <= args.max_carriers <= MAX_CARRIERS and args.max_carriers <= args.max_atoms <= MAX_ATOMS,
            "invalid_preview_limits")
    require(source.is_file() and exclusions.is_file(), "required_input_missing")
    before = file_stat(source)
    require(before["bytes"] == args.expected_source_bytes, "source_size_differs_from_release")
    require(all(not Path(str(source) + suffix).exists() for suffix in ("-wal", "-journal")),
            "source_has_live_or_unresolved_journal")
    require(sha(exclusions) == args.expected_exclusions_sha, "exclusions_sha_mismatch")
    exclusion_data = json.loads(exclusions.read_text())
    require(isinstance(exclusion_data, dict) and isinstance(exclusion_data.get("context_sha256"), list),
            "invalid_exclusions_structure")
    denied = set(exclusion_data["context_sha256"])
    require(all(isinstance(v, str) and len(v) == 64 for v in denied), "invalid_exclusion_identity")
    actual_sha = sha(source) if args.rehash_source else None
    if args.rehash_source:
        require(actual_sha == args.published_source_sha, "source_sha_mismatch")
    checkpoint()
    db = open_readonly(source, checkpoint)
    try:
        schema = inspect_schema(db)
        previews, counts = collect_preview(db, denied, args.max_carriers, args.max_atoms)
        definitions = [dict(r) for r in db.execute("SELECT * FROM dictionary_definition ORDER BY variable_key")]
    finally:
        db.close()
    checkpoint()
    after = file_stat(source)
    require(before == after, "source_stat_changed_during_export")
    require(all(not Path(str(source) + suffix).exists() for suffix in ("-wal", "-journal")),
            "source_journal_appeared_during_export")
    require(sha(exclusions) == args.expected_exclusions_sha, "exclusions_changed_during_export")
    receipt = {
        "status": "bounded_private_preview_exported", "version": VERSION,
        "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_published_sha256": args.published_source_sha,
        "source_sha_basis": "published_materialization_and_independent_QA",
        "source_sha_recomputed_this_run": bool(args.rehash_source),
        "source_actual_sha256_this_run": actual_sha,
        "source_stat_before": before, "source_stat_after": after,
        "source_stat_unchanged": True, "source_sqlite_mode": "ro_and_query_only_and_read_authorizer",
        "runtime_exclusions_sha256": args.expected_exclusions_sha,
        "protection_checked_before_payload": True,
        "selection": "deterministic_round_robin_by_source_asset_not_representative_or_accuracy_sample",
        "counts": counts, "variable_definitions": len(definitions),
        "limits": {"source_carriers": args.max_carriers, "combined_atoms": args.max_atoms},
        "full_variable_table_scanned": False, "source_document_metadata_scanned": True,
        "source_or_acceptance_modified": False, "new_semantic_judgments": 0,
        "new_model_calls": 0, "human_semantic_acceptance_required": False,
        "preview_not_full_table": True, "source_sha_not_rechecked_by_default": True,
        "elapsed_seconds_before_serialization": round(time.monotonic() - started, 3),
    }
    payload = {"receipt": receipt, "field_notes_zh": FIELD_NOTES, "schema": schema,
               "dictionary_definitions": definitions, "previews": previews}
    # Serialize before creating a directory; invalid data fail without partial payloads.
    private_json, private_html = json_text(payload) + "\n", render_html(payload)
    require(len(private_json.encode()) + len(private_html.encode()) <= MAX_OUTPUT_BYTES,
            "combined_output_size_cap_exceeded")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    safe_write(output / "REUSE_TABLE_PREVIEW_PRIVATE.json", private_json)
    safe_write(output / "REUSE_TABLE_PREVIEW_PRIVATE.html", private_html)
    hashes = {name: sha(output / name) for name in ("REUSE_TABLE_PREVIEW_PRIVATE.json", "REUSE_TABLE_PREVIEW_PRIVATE.html")}
    public = {**receipt, "private_output_sha256": hashes,
              "private_records_excluded_from_public_receipt": True,
              "private_outputs_must_not_enter_git_or_terminal": True,
              "elapsed_seconds": round(time.monotonic() - started, 3)}
    safe_write(output / "REVIEW_EXPORT_PUBLIC.json", json_text(public) + "\n")
    safe_write(output / "REVIEW_SCHEMA_PUBLIC.json", json_text({"schema": schema, "field_notes_zh": FIELD_NOTES}) + "\n")
    return public


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--database", default=str(Path.home() / "migration/reuse_execution_20261117/run001/LINKUP_REUSED_VARIABLES_V1_PRIVATE.sqlite"))
    p.add_argument("--output-dir", required=True)
    p.add_argument("--exclusions-file", required=True)
    p.add_argument("--published-source-sha", default=RELEASE_SHA)
    p.add_argument("--expected-source-bytes", type=int, default=RELEASE_BYTES)
    p.add_argument("--expected-exclusions-sha", default=EXCLUSIONS_SHA)
    p.add_argument("--max-carriers", type=int, default=MAX_CARRIERS)
    p.add_argument("--max-atoms", type=int, default=MAX_ATOMS)
    p.add_argument("--rehash-source", action="store_true", help="Optional whole-source hash, not default; never a variable-table scan.")
    return p


def main():
    args = parser().parse_args()
    try:
        export(args)
    except ExportError as error:
        print("REVIEW_EXPORT_FAILED:" + str(error), file=sys.stderr)
        return 1
    except Exception:
        # SQLite/JSON/OSError messages may contain private values/paths; suppress them.
        print("REVIEW_EXPORT_FAILED:unexpected_error_details_suppressed", file=sys.stderr)
        return 1
    print("REVIEW_EXPORT_OK:private_files_written_public_receipt_available")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
