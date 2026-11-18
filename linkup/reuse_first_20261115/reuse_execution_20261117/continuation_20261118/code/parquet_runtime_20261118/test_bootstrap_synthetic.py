"""Pure synthetic tests. No PyArrow import, network, Azure, or real wheel."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import unittest
from unittest import mock
import urllib.request
import warnings
import zipfile

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("bootstrap", HERE / "bootstrap_pyarrow_no_pip.py")
b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(b)


def wheel_entry(tag="manylinux_2_28_x86_64", **updates):
    name = "pyarrow-19.0.1-cp312-cp312-" + tag + ".whl"
    result = {"filename": name, "size": 100, "url": "https://files.pythonhosted.org/packages/test/" + name,
              "packagetype": "bdist_wheel", "yanked": False, "digests": {"sha256": "a" * 64}}
    result.update(updates)
    return result


def metadata(*entries):
    return {"info": {"name": "pyarrow", "version": "19.0.1"}, "urls": list(entries)}


def zip_bytes(entries):
    buffer = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, value in entries:
                archive.writestr(name, value)
    return buffer.getvalue()


class BootstrapTests(unittest.TestCase):
    def error(self, code, function, *args, **kwargs):
        with self.assertRaises(b.BootstrapError) as raised:
            function(*args, **kwargs)
        self.assertEqual(raised.exception.code, code)

    def inspect(self, data):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return b.inspect_members(archive)

    def test_select_highest_compatible(self):
        old = wheel_entry("manylinux_2_17_x86_64.manylinux2014_x86_64")
        new = wheel_entry()
        self.assertEqual(b.select_wheel(metadata(old, new), (2, 39))["filename"], new["filename"])
        self.assertEqual(b.select_wheel(metadata(old, new), (2, 27))["filename"], old["filename"])

    def test_reject_unsupported_glibc(self):
        self.error("no_compatible_cp312_manylinux_wheel", b.select_wheel, metadata(wheel_entry()), (2, 17))

    def test_reject_wrong_abi_arch_os_version(self):
        for change in [("cp312-cp312", "cp311-cp311"), ("x86_64", "aarch64"),
                       ("manylinux_2_28_x86_64", "musllinux_1_2_x86_64"),
                       ("19.0.1", "19.0.0")]:
            entry = wheel_entry()
            entry["filename"] = entry["filename"].replace(*change)
            with self.subTest(change=change):
                self.error("no_compatible_cp312_manylinux_wheel", b.select_wheel, metadata(entry), (2, 39))

    def test_reject_wrong_metadata(self):
        value = metadata(wheel_entry())
        value["info"]["version"] = "20.0.0"
        self.error("wrong_package_or_version_metadata", b.select_wheel, value, (2, 39))

    def test_reject_yanked(self):
        self.error("no_compatible_cp312_manylinux_wheel", b.select_wheel,
                   metadata(wheel_entry(yanked=True)), (2, 39))

    def test_reject_ambiguous_selection(self):
        entry = wheel_entry()
        self.error("ambiguous_compatible_wheel", b.select_wheel, metadata(entry, entry), (2, 39))

    def test_reject_bad_metadata_size_and_hash(self):
        for size in [0, -1, True, b.MAX_WHEEL + 1]:
            self.error("wheel_metadata_size_exceeds_cap", b.select_wheel,
                       metadata(wheel_entry(size=size)), (2, 39))
        self.error("missing_official_SHA256", b.select_wheel,
                   metadata(wheel_entry(digests={"sha256": ""})), (2, 39))

    def test_reject_url_filename_mismatch(self):
        self.error("wheel_URL_filename_mismatch", b.select_wheel,
                   metadata(wheel_entry(url="https://files.pythonhosted.org/other.whl")), (2, 39))

    def test_url_allowlist(self):
        self.assertEqual(b.verified_url(b.METADATA_URL, "pypi.org"), b.METADATA_URL)
        for url in ["http://pypi.org/x", "https://evil.example/x", "https://pypi.org.evil/x",
                    "https://user:password@pypi.org/x", "https://pypi.org/x?token=secret",
                    "https://pypi.org/x#fragment", "https://pypi.org:444/x", "https://pypi.org/\\x",
                    "https://pypi.org/\nx"]:
            with self.subTest(url=url):
                self.error("untrusted_URL", b.verified_url, url, "pypi.org")

    def test_redirect_host_restriction(self):
        handler = b.RestrictedRedirect("pypi.org")
        request = urllib.request.Request(b.METADATA_URL)
        self.error("untrusted_URL", handler.redirect_request, request, None, 302, "", {},
                   "https://files.pythonhosted.org/redirect")
        result = handler.redirect_request(request, None, 302, "", {}, "https://pypi.org/allowed")
        self.assertEqual(result.full_url, "https://pypi.org/allowed")

    def test_checksum_and_size_mismatch(self):
        expected = {"advertised_bytes": 3, "advertised_sha256": "a" * 64}
        b.verify_download({"bytes": 3, "sha256": "a" * 64}, expected)
        self.error("wheel_SHA256_mismatch", b.verify_download, {"bytes": 3, "sha256": "b" * 64}, expected)
        self.error("wheel_size_mismatch", b.verify_download, {"bytes": 4, "sha256": "a" * 64}, expected)

    def test_zip_traversal_absolute_backslash_drive(self):
        for name in ["../outside", "a/../../outside", "/absolute", "a/./file", "a//file",
                     "C:/drive", "a\\..\\outside"]:
            with self.subTest(name=name), self.assertRaises(b.BootstrapError):
                self.inspect(zip_bytes([(name, b"bad")]))

    def test_zip_symlink_and_special_file(self):
        for kind in [stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR, stat.S_IFSOCK]:
            info = zipfile.ZipInfo("evil")
            info.create_system = 3
            info.external_attr = (kind | 0o777) << 16
            self.error("ZIP_symlink_or_special_file", self.inspect, zip_bytes([(info, b"target")]))

    def test_zip_duplicate_and_directory_collision(self):
        self.error("duplicate_ZIP_member", self.inspect, zip_bytes([("a", b"1"), ("a", b"2")]))
        self.error("duplicate_ZIP_member", self.inspect, zip_bytes([("a/", b""), ("a", b"2")]))
        for entries in [[("a", b"1"), ("a/b", b"2")], [("a/b", b"2"), ("a", b"1")]]:
            self.error("ZIP_file_directory_conflict", self.inspect, zip_bytes(entries))

    def test_zip_directory_with_data(self):
        self.error("ZIP_directory_with_data", self.inspect, zip_bytes([("a/", b"bad")]))

    def test_zip_encryption_null_and_expanded_limits(self):
        good = zip_bytes([("a", b"123456789")])
        with mock.patch.object(b, "MAX_EXPANDED", 8):
            self.error("ZIP_expanded_size_exceeds_cap", self.inspect, good)
        with zipfile.ZipFile(io.BytesIO(good)) as archive:
            archive.infolist()[0].flag_bits |= 1
            self.error("encrypted_ZIP_member", b.inspect_members, archive)
        with zipfile.ZipFile(io.BytesIO(good)) as archive:
            archive.infolist()[0].orig_filename = "a\x00hidden"
            self.error("unsafe_ZIP_name", b.inspect_members, archive)

    def test_zip_member_count_limit(self):
        with mock.patch.object(b, "MAX_MEMBERS", 1):
            self.error("ZIP_member_count_exceeds_cap", self.inspect,
                       zip_bytes([("a", b"1"), ("b", b"2")]))

    def test_safe_extract_and_exclusive_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / "synthetic.zip"
            wheel.write_bytes(zip_bytes([("package/", b""), ("package/a.py", b"value=1\n")]))
            target = root / "libraries"
            manifest, size = b.safe_extract(wheel, target, time.monotonic() + 10)
            self.assertEqual(size, 8)
            self.assertEqual((target / "package/a.py").read_bytes(), b"value=1\n")
            self.assertEqual(manifest[0]["sha256"], b.sha256(b"value=1\n"))
            self.error("library_directory_exists", b.safe_extract, wheel, target, time.monotonic() + 10)
            self.assertEqual((target / "package/a.py").read_bytes(), b"value=1\n")

    def test_bad_zip_does_not_create_libraries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / "synthetic.zip"
            wheel.write_bytes(zip_bytes([("../outside", b"bad")]))
            with self.assertRaises(b.BootstrapError):
                b.safe_extract(wheel, root / "libraries", time.monotonic() + 10)
            self.assertFalse((root / "libraries").exists())

    def test_compressed_size_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / "synthetic.zip"
            wheel.write_bytes(zip_bytes([("a", b"1")]))
            with mock.patch.object(b, "MAX_WHEEL", 1):
                self.error("wheel_file_exceeds_cap", b.safe_extract, wheel, root / "lib", time.monotonic() + 10)

    def test_exclusive_output_and_symlink_ancestor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            output = b.claim_new_output(root / "new")
            self.assertTrue(output.is_dir())
            self.error("output_already_exists_no_retry", b.claim_new_output, output)
            link = root / "alias"
            link.symlink_to(output, target_is_directory=True)
            self.error("output_ancestor_symlink_or_dot_path", b.claim_new_output, link / "child")

    def test_deadline(self):
        self.error("overall_180_second_deadline", b.remaining, time.monotonic() - 1)

    def test_network_error_is_not_retried_and_partial_is_preserved(self):
        opener = mock.Mock()
        opener.open.side_effect = OSError("private error text")
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(b.urllib.request, "build_opener", return_value=opener):
            target = Path(tmp) / "partial"
            with self.assertRaises(OSError):
                b.fetch(b.METADATA_URL, "pypi.org", target, 100, time.monotonic() + 10)
            opener.open.assert_called_once()
            self.assertTrue(target.exists())
            with self.assertRaises(FileExistsError):
                b.fetch(b.METADATA_URL, "pypi.org", target, 100, time.monotonic() + 10)
            opener.open.assert_called_once()

    def test_streaming_download_enforces_cap(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.headers = {}
        response.geturl.return_value = b.METADATA_URL
        response.read.side_effect = [b"1234", b""]
        opener = mock.Mock()
        opener.open.return_value = response
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(b.urllib.request, "build_opener", return_value=opener):
            self.error("download_exceeds_cap", b.fetch, b.METADATA_URL, "pypi.org", Path(tmp) / "x", 3, time.monotonic() + 10)

    def test_main_sanitized_failure_no_retry_no_global_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / "run"
            stream = io.StringIO()
            before = list(b.sys.path)
            old_umask = os.umask(0o077)
            try:
                with contextlib.redirect_stdout(stream), mock.patch.object(b, "host_compatibility", return_value=(2, 39)), mock.patch.object(b, "fetch", side_effect=OSError("do-not-leak-secret")) as fetch:
                    code = b.main(["--output", str(output)])
            finally:
                os.umask(old_umask)
            self.assertEqual(code, 1)
            fetch.assert_called_once()
            self.assertNotIn("do-not-leak-secret", stream.getvalue())
            receipt = json.loads(stream.getvalue())
            self.assertFalse(receipt["global_python_environment_modified"])
            self.assertEqual(before, b.sys.path)
            self.assertEqual(receipt["status"], "isolated_runtime_setup_failed_no_automatic_retry")
            self.assertTrue((output / "SETUP_ERROR_PRIVATE.json").is_file())
            self.assertTrue((output / "BOOTSTRAP_PUBLIC.json").is_file())
            self.assertFalse((output / "libraries").exists())

    def test_synthetic_import_program_compiles_without_execution(self):
        compile(b.IMPORT_TEST, "synthetic_import_test", "exec")
        self.assertIn('"-I", "-S", "-B"', (HERE / "bootstrap_pyarrow_no_pip.py").read_text())

    def test_verified_official_metadata_candidates_if_present(self):
        path = HERE / "PYPI_METADATA_CHECK_PUBLIC.json"
        if not path.exists():
            self.skipTest("optional official metadata receipt absent")
        check = json.loads(path.read_text())
        candidates = copy.deepcopy(check["cp312_linux_candidates"])
        for entry in candidates:
            entry["packagetype"] = "bdist_wheel"
        selected = b.select_wheel(metadata(*candidates), (2, 39))
        self.assertEqual(selected["filename"], "pyarrow-19.0.1-cp312-cp312-manylinux_2_28_x86_64.whl")
        self.assertEqual(selected["advertised_bytes"], 42087026)
        self.assertEqual(selected["advertised_sha256"], "b4c4156a625f1e35d6c0b2132635a237708944eb41df5fbe7d50f20d20c17832")


if __name__ == "__main__":
    unittest.main(verbosity=2)
