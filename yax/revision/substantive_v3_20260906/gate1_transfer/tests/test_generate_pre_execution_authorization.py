from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys

import pytest


HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[3]
SCRIPT = HERE / "generate_pre_execution_authorization.py"
LOADER = importlib.util.spec_from_file_location("yax_gate1_authorization_generator", SCRIPT)
assert LOADER is not None and LOADER.loader is not None
GENERATOR = importlib.util.module_from_spec(LOADER)
sys.modules[LOADER.name] = GENERATOR
LOADER.loader.exec_module(GENERATOR)


def test_generated_document_binds_current_specs_code_and_source_registry():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    document = GENERATOR.build_document(
        REPO,
        "a" * 40,
        now.isoformat().replace("+00:00", "Z"),
        (now + timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
        (now + timedelta(hours=23)).isoformat().replace("+00:00", "Z"),
    )
    assert document["authorization_id"] == GENERATOR.expected_identifier(document)
    assert document["status"] == GENERATOR.STATUS
    for key, relative in {
        "cells": GENERATOR.CELL_CODE_REL,
        "target": GENERATOR.TARGET_CODE_REL,
        "numerical": GENERATOR.NUMERICAL_CODE_REL,
    }.items():
        assert document["modules"][key]["code_sha256"] == hashlib.sha256(
            (REPO / relative).read_bytes()
        ).hexdigest()


@pytest.mark.parametrize(
    "values",
    [
        ("2099-01-01T00:00:00+00:00", "2099-01-01T00:00:01Z", "2099-01-02T00:00:00Z"),
        ("2099-01-02T00:00:00Z", "2099-01-01T00:00:01Z", "2099-01-03T00:00:00Z"),
        ("2020-01-01T00:00:00Z", "2020-01-01T00:00:01Z", "2020-01-02T00:00:00Z"),
        ("2099-01-01T00:00:00Z", "2099-01-01T00:00:01Z", "2099-01-01T01:00:00Z"),
    ],
)
def test_noncanonical_unordered_or_expired_windows_fail_closed(values):
    with pytest.raises(GENERATOR.AuthorizationGenerationError):
        GENERATOR.build_document(REPO, "a" * 40, *values)


def test_overlong_authorization_window_fails_closed():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    values = (
        now.isoformat().replace("+00:00", "Z"),
        now.isoformat().replace("+00:00", "Z"),
        (now + timedelta(hours=24, seconds=1)).isoformat().replace("+00:00", "Z"),
    )
    with pytest.raises(GENERATOR.AuthorizationGenerationError, match="twenty-four"):
        GENERATOR.build_document(REPO, "a" * 40, *values)


def test_template_is_explicitly_unstamped_and_generator_never_overwrites(tmp_path: Path):
    template = json.loads((HERE / "PRE_EXECUTION_AUTHORIZATION.template.json").read_text())
    assert template["status"] == "UNSTAMPED_FAIL_CLOSED"
    target = tmp_path / "authorization.json"
    GENERATOR.publish_new_file(target, b'{"safe":true}\n')
    assert target.read_bytes() == b'{"safe":true}\n'
    with pytest.raises(GENERATOR.AuthorizationGenerationError, match="already exists"):
        GENERATOR.publish_new_file(target, b'{"safe":false}\n')
    assert target.read_bytes() == b'{"safe":true}\n'


def test_git_queries_ignore_caller_path(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["/usr/bin/git", "init", "-q"], cwd=repo, check=True)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text("#!/bin/sh\necho fabricated\n", encoding="utf-8")
    fake_git.chmod(0o755)
    monkeypatch.setenv("PATH", str(fake_bin))
    assert GENERATOR.git_output(repo, "rev-parse", "--show-toplevel") == str(
        repo.resolve()
    )
