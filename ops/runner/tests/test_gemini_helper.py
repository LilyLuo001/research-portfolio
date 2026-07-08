"""gemini_helper: the human-run Gemini channel. Prompt carries C0 + every item
and sentinel; a paste only becomes ops/l1/out/<tid>.json if it parses AND the
sentinel fence passes; a tripped fence saves nothing but keeps the raw paste."""
import importlib.util
import json
import pathlib
import sys

import pytest

RUN = pathlib.Path(__file__).resolve().parents[1]
ROOT = RUN.parents[1]

spec = importlib.util.spec_from_file_location(
    "gemini_helper", ROOT / "ops" / "l1" / "gemini_helper.py")
gh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gh)


SPEC = {
    "manual": True,
    "manual_note": "run with grounding on",
    "items": [{"id": "t1a-oracles", "prompt": "which oracle per market?"}],
    "sentinels": [{"id": "S1", "prompt": "In which year-month did Aave Horizon "
                                         "launch? YYYY-MM only.", "expect": "2025-08"}],
}


def _wire(monkeypatch, tmp_path, paste):
    out = tmp_path / "out"
    monkeypatch.setattr(gh, "OUT", out)
    monkeypatch.setattr(gh, "read_paste", lambda: paste)
    return out


def test_prompt_contains_c0_items_sentinels_and_format():
    text = gh.build_prompt("E2-T1-facts-B", SPEC)
    assert "【项目上下文 C0" in text                 # shared context pack
    assert "run with grounding on" in text            # manual_note
    assert "which oracle per market?" in text         # item
    assert "Aave Horizon" in text                     # sentinel is in the batch
    assert "单一 JSON 对象" in text                   # answer-format contract


def test_good_paste_saves_answer_map(monkeypatch, tmp_path):
    paste = ('Here you go:\n```json\n'
             '{"t1a-oracles": "sACRED: NAVLink …", "S1": "2025-08"}\n```')
    out = _wire(monkeypatch, tmp_path, paste)
    assert gh.run_task("E2-T1-facts-B", SPEC) is True
    saved = json.loads((out / "E2-T1-facts-B.json").read_text())
    assert saved["t1a-oracles"].startswith("sACRED")
    assert (out / "E2-T1-facts-B.gemini-raw.txt").exists()


def test_tripped_fence_saves_nothing_but_keeps_raw(monkeypatch, tmp_path):
    paste = '{"t1a-oracles": "made-up answer", "S1": "2024-01"}'   # wrong sentinel
    out = _wire(monkeypatch, tmp_path, paste)
    assert gh.run_task("E2-T1-facts-B", SPEC) is False
    assert not (out / "E2-T1-facts-B.json").exists()
    assert (out / "E2-T1-facts-B.gemini-raw.txt").exists()          # post-mortem


def test_unparseable_paste_saves_nothing(monkeypatch, tmp_path):
    out = _wire(monkeypatch, tmp_path, "I could not find anything, sorry.")
    assert gh.run_task("E2-T1-facts-B", SPEC) is False
    assert not (out / "E2-T1-facts-B.json").exists()


def test_missing_item_requires_confirmation(monkeypatch, tmp_path):
    paste = '{"S1": "2025-08"}'                       # sentinel ok, item missing
    out = _wire(monkeypatch, tmp_path, paste)
    monkeypatch.setattr("builtins.input", lambda *a: "n")
    assert gh.run_task("E2-T1-facts-B", SPEC) is False
    assert not (out / "E2-T1-facts-B.json").exists()
