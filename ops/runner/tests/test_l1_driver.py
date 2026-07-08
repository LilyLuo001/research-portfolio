"""L1 driver: dispatches ready L1 tasks that have a spec, skips those without one
or without sentinels, and writes outputs — without marking anything complete."""
import yaml
import runner
import dispatch
import budget
import l1_driver


FAM = {"meta": {"vendor_families": {"kimi": "moonshot", "deepseek": "deepseek"}}, "tasks": []}


def _wire(monkeypatch, tmp_path, ready_tasks):
    monkeypatch.setattr(runner, "load", lambda p: FAM)
    monkeypatch.setattr(runner, "load_state", lambda: {"completed": [], "gates_cleared": []})
    monkeypatch.setattr(runner, "ready_set", lambda q, s: (ready_tasks, [], [], []))
    monkeypatch.setattr(l1_driver, "L1", tmp_path / "l1")
    monkeypatch.setattr(l1_driver, "OUT", tmp_path / "l1" / "out")
    monkeypatch.setattr(budget, "LOG", tmp_path / "spend.jsonl")
    (tmp_path / "l1").mkdir()


def test_dispatches_task_with_spec(monkeypatch, tmp_path, capsys):
    _wire(monkeypatch, tmp_path, [{"id": "E2-T1-facts", "worker": "kimi", "human_gate": False}])
    (tmp_path / "l1" / "E2-T1-facts.yaml").write_text(yaml.dump({
        "worker": "kimi", "est_cost": 0.1,
        "items": [{"id": "i1", "prompt": "verify X"}],
        "sentinels": [{"id": "S1", "prompt": "2+2? number only", "expect": "4"}],
    }))
    seen = {}

    def fake_run_batch(worker, items, sentinels, est_cost=0.0, live=False, _corrupt=False, out=None):
        seen.update(worker=worker, n=len(items), live=live)
        import pathlib
        pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(out).write_text('{"i1": "answer"}')
        return "DONE", f"{worker}: ok", {"i1": "answer"}

    monkeypatch.setattr(dispatch, "run_batch", fake_run_batch)
    assert l1_driver.run(live=True) == 0
    assert seen == {"worker": "kimi", "n": 1, "live": True}
    assert (tmp_path / "l1" / "out" / "E2-T1-facts.json").exists()


def test_task_without_spec_is_skipped_not_failed(monkeypatch, tmp_path, capsys):
    _wire(monkeypatch, tmp_path, [{"id": "DAX-W0.5-legwork", "worker": "kimi", "human_gate": False}])
    called = False

    def fake_run_batch(*a, **k):
        nonlocal called
        called = True
        return "DONE", "", {}

    monkeypatch.setattr(dispatch, "run_batch", fake_run_batch)
    assert l1_driver.run(live=True) == 0
    assert called is False                       # nothing dispatched
    assert "waiting for input" in capsys.readouterr().out


def test_spec_without_sentinels_is_skipped(monkeypatch, tmp_path, capsys):
    _wire(monkeypatch, tmp_path, [{"id": "P1-T1-events", "worker": "kimi", "human_gate": False}])
    (tmp_path / "l1" / "P1-T1-events.yaml").write_text(yaml.dump({
        "items": [{"id": "i1", "prompt": "x"}]}))   # no sentinels

    def fake_run_batch(*a, **k):
        raise AssertionError("must not dispatch a fence-less batch")

    monkeypatch.setattr(dispatch, "run_batch", fake_run_batch)
    assert l1_driver.run(live=True) == 0
    assert "no sentinels" in capsys.readouterr().out
