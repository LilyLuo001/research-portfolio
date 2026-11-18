"""Synthetic-only tests. No real LinkUp record, cloud connection or API call."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

import export_reuse_review as exporter


def h(value):
    return hashlib.sha256(value.encode()).hexdigest()


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "SYNTHETIC.sqlite"
        self.exclusions = self.root / "SYNTHETIC_EXCLUSIONS.json"
        self.output = self.root / "export"
        db = sqlite3.connect(self.source)
        for table, columns in exporter.EXPECTED_COLUMNS.items():
            definitions = []
            for c in columns:
                primary = (table == "source_document" and c == "d") or (table == "context_state" and c == "h") or (table == "variable_value" and c == "id") or (table == "dictionary_definition" and c == "variable_key")
                integer = c in {"source_ordinal", "original_accepted", "carrier_present", "original_protected", "reuse_excluded", "value_present", "eligible_original_scope", "derived"}
                definitions.append(c + (" INTEGER" if integer else " TEXT") + (" PRIMARY KEY" if primary else ""))
            db.execute("CREATE TABLE " + table + "(" + ",".join(definitions) + ")")
        db.executescript("""CREATE INDEX variable_context ON variable_value(h,variable_key);
            CREATE INDEX bindings_context ON ad_binding(h);
            CREATE INDEX metadata_ad ON metadata_value(k,variable_key);""")
        self.denied = {h("context-0"), h("context-1"), h("context-2")}
        for i in range(70):
            d, context, key = h("doc-" + str(i)), h("context-" + str(i)), "SYNTHETIC_AD_" + str(i)
            db.execute("INSERT INTO source_document VALUES(?,?,?,?,?,?,?,?,?)", (d, context, key, "SYNTHETIC_ASSET_" + str(i % 7), h("source"), i, int(i % 2 == 0), "exact_source_masks", "adapted"))
            db.execute("INSERT INTO context_state VALUES(?,?,?,?,?,?)", (context, "quarantined" if i == 2 else "accepted" if i % 2 == 0 else "saved_unverified", 1, int(i == 1), 0, "retained"))
            db.execute("INSERT INTO ad_binding VALUES(?,?,?,?,?)", (key, context, "SYNTHETIC_BINDING", "2020-01-01", "matched_consistent"))
            for m in range(3):
                db.execute("INSERT INTO metadata_value VALUES(?,?,?,?,?,?,?)", (key, "lk.time.synthetic" + str(m), h("metadata"), i, "SYNTHETIC", '"2020-01-01"', "retained_source_value"))
            for j in range(20):
                value = '{ "synthetic": "</script><img src=x onerror=alert(1)>", "n": null }' if j == 0 else json.dumps({"synthetic": j})
                db.execute("INSERT INTO variable_value VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (h(d + str(j)), d, context, key, "lk.exp.synthetic" + str(j % 4), "synthetic.path." + str(j), '{ "anchor": 1 }', "synthetic", value, 1, "unknown" if j % 2 == 0 else "known", "saved_unverified", "retained", 0, 0, "original_unknown", '{ "keep": true }'))
        db.execute("INSERT INTO dictionary_definition VALUES(?,?)", ("lk.exp.synthetic0", '{ "synthetic_definition": true }'))
        db.commit()
        db.close()
        self.exclusions.write_text(json.dumps({"context_sha256": [h("context-0")]}))
        self.source_hash = exporter.sha(self.source)
        self.args = exporter.parser().parse_args([
            "--database", str(self.source), "--output-dir", str(self.output),
            "--exclusions-file", str(self.exclusions),
            "--expected-source-bytes", str(self.source.stat().st_size),
            "--expected-exclusions-sha", exporter.sha(self.exclusions),
            "--published-source-sha", self.source_hash])

    def tearDown(self):
        self.tmp.cleanup()

    def run_export(self):
        result = exporter.export(self.args)
        private = json.loads((self.output / "REUSE_TABLE_PREVIEW_PRIVATE.json").read_text())
        return result, private

    def test_caps_and_source_balance(self):
        receipt, payload = self.run_export()
        self.assertEqual(receipt["counts"]["source_carriers"], 50)
        self.assertLessEqual(receipt["counts"]["bound_ad_keys"], 50)
        self.assertEqual(receipt["counts"]["combined_atoms"], 500)
        counts = __import__("collections").Counter(p["source_document"]["asset"] for p in payload["previews"])
        self.assertEqual(len(counts), 7)
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)

    def test_protection_before_private_payload(self):
        _, payload = self.run_export()
        for p in payload["previews"]:
            self.assertNotIn(p["source_document"]["h"], self.denied)
            self.assertNotIn(p["context_state"]["original_state"], {"quarantined"})
            self.assertFalse(p["context_state"]["original_protected"])

    def test_raw_values_status_and_all_columns_unchanged(self):
        _, payload = self.run_export()
        db = sqlite3.connect(self.source)
        db.row_factory = sqlite3.Row
        for p in payload["previews"]:
            for atom in p["variable_atoms"]:
                self.assertEqual(atom, dict(db.execute("SELECT * FROM variable_value WHERE id=?", (atom["id"],)).fetchone()))
                self.assertEqual(atom["workflow_state"], "saved_unverified")
                self.assertEqual(atom["eligible_original_scope"], 0)
        db.close()

    def test_source_unchanged_and_output_hashes_real(self):
        receipt, _ = self.run_export()
        self.assertEqual(exporter.sha(self.source), self.source_hash)
        for name, digest in receipt["private_output_sha256"].items():
            self.assertEqual(digest, exporter.sha(self.output / name))
        self.assertEqual((self.output / "REUSE_TABLE_PREVIEW_PRIVATE.json").stat().st_mode & 0o777, 0o600)

    def test_default_never_rehashes_source(self):
        original = exporter.sha
        def safe_sha(path):
            self.assertNotEqual(Path(path), self.source)
            return original(path)
        with mock.patch.object(exporter, "sha", side_effect=safe_sha):
            receipt, _ = self.run_export()
        self.assertFalse(receipt["source_sha_recomputed_this_run"])
        self.assertIsNone(receipt["source_actual_sha256_this_run"])

    def test_optional_source_hash(self):
        self.args.rehash_source = True
        receipt, _ = self.run_export()
        self.assertTrue(receipt["source_sha_recomputed_this_run"])
        self.assertEqual(receipt["source_actual_sha256_this_run"], self.source_hash)

    def test_wrong_optional_source_hash_fails_closed(self):
        self.args.rehash_source = True
        self.args.published_source_sha = "0" * 64
        with self.assertRaisesRegex(exporter.ExportError, "source_sha_mismatch"):
            exporter.export(self.args)
        self.assertFalse(self.output.exists())

    def test_readonly_connection_denies_update_attach(self):
        db = exporter.open_readonly(self.source, lambda **_: 0)
        for statement in ("UPDATE variable_value SET workflow_state='accepted'", "ATTACH DATABASE ':memory:' AS injected"):
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute(statement)
        db.close()

    def test_html_cannot_execute_value_markup(self):
        self.run_export()
        html = (self.output / "REUSE_TABLE_PREVIEW_PRIVATE.html").read_text()
        self.assertNotIn("<script", html.lower())
        self.assertNotIn("<img", html.lower())
        self.assertIn("default-src 'none'", html)
        self.assertIn("&lt;/script&gt;", html)
        self.assertIn("不是待标注的人工语义审核表", html)

    def test_public_receipt_contains_no_record_ids_or_values(self):
        self.run_export()
        public = (self.output / "REVIEW_EXPORT_PUBLIC.json").read_text()
        self.assertNotIn("SYNTHETIC_AD", public)
        self.assertNotIn("alert(1)", public)
        self.assertNotIn(h("doc-3"), public)

    def test_preexisting_output_not_overwritten(self):
        self.output.mkdir()
        with self.assertRaisesRegex(exporter.ExportError, "existing_output_preserved"):
            exporter.export(self.args)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_git_destination_forbidden(self):
        (self.root / ".git").mkdir()
        with self.assertRaisesRegex(exporter.ExportError, "private_output_inside_git_forbidden"):
            exporter.export(self.args)

    def test_wrong_size_or_exclusion_digest_fails_without_output(self):
        self.args.expected_source_bytes += 1
        with self.assertRaisesRegex(exporter.ExportError, "source_size_differs_from_release"):
            exporter.export(self.args)
        self.args.expected_source_bytes -= 1
        self.args.expected_exclusions_sha = "0" * 64
        with self.assertRaisesRegex(exporter.ExportError, "exclusions_sha_mismatch"):
            exporter.export(self.args)
        self.assertFalse(self.output.exists())

    def test_missing_lookup_index_has_no_scan_fallback(self):
        db = sqlite3.connect(self.source)
        db.execute("DROP INDEX variable_context")
        db.commit()
        db.close()
        self.args.expected_source_bytes = self.source.stat().st_size
        with self.assertRaisesRegex(exporter.ExportError, "required_targeted_lookup_index_missing"):
            exporter.export(self.args)

    def test_no_raw_error_details_to_terminal(self):
        stderr = io.StringIO()
        with mock.patch.object(exporter.parser().__class__, "parse_args", return_value=self.args), mock.patch.object(exporter, "export", side_effect=ValueError("PRIVATE_SYNTHETIC_VALUE")), contextlib.redirect_stderr(stderr):
            self.assertEqual(exporter.main(), 1)
        self.assertNotIn("PRIVATE_SYNTHETIC_VALUE", stderr.getvalue())
        self.assertIn("unexpected_error_details_suppressed", stderr.getvalue())

    def test_caps_cannot_be_expanded_and_small_budget_valid(self):
        self.args.max_carriers = 51
        with self.assertRaisesRegex(exporter.ExportError, "invalid_preview_limits"):
            exporter.export(self.args)
        self.args.max_carriers, self.args.max_atoms = 3, 3
        receipt, _ = self.run_export()
        self.assertEqual(receipt["counts"]["combined_atoms"], 3)


if __name__ == "__main__":
    unittest.main()
