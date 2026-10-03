import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_person_sampling_extracts_every_career_and_counts_missing_keys(tmp_path):
    # Synthetic fixture only: it is a behavior check, not vendor evidence.
    frame = tmp_path / "frame.csv"
    career = tmp_path / "career.csv"
    out = tmp_path / "protected"
    write_csv(frame, ["pid", "eligible"], [
        {"pid": "p1", "eligible": "yes"}, {"pid": "p2", "eligible": "yes"},
        {"pid": "p3", "eligible": "yes"}, {"pid": "", "eligible": "yes"}
    ])
    write_csv(career, ["pid", "job"], [
        {"pid": "p1", "job": "old"}, {"pid": "p1", "job": "new"},
        {"pid": "p2", "job": "only"}, {"pid": "", "job": "missing"}
    ])
    mapping = {"schema_verified": True,
        "person_frame": {"path": str(frame), "format": "csv", "person_id_column": "pid", "eligibility_column": "eligible", "eligible_value": "yes"},
        "career": {"path": str(career), "person_id_column": "pid", "required_columns": {
            "stable_position_id": "job", "raw_employer_id": "job", "raw_title": "job",
            "start_date_or_month": "job", "end_date_or_month": "job",
            "location_at_position": "job", "industry_at_position": "job", "internship_indicator": "job"}, "format": "csv"},
        "output": {"allow_raw_extract": True, "protected_destination": str(out)}}
    mp = tmp_path / "mapping.json"
    mp.write_text(json.dumps(mapping))
    result = subprocess.run([sys.executable, str(ROOT / "revelio_r0_extract.py"), "--mapping", str(mp), "--protected-output", str(out), "--sample-size", "3"], check=True, capture_output=True, text=True)
    receipt = json.loads(result.stdout)
    extracted = list(csv.DictReader((out / "sampled_all_careers.csv").open()))
    sampled = list(csv.DictReader((out / "sampled_person_keys.csv").open()))
    assert receipt["selected_persons"] == 3
    assert receipt["career_rows_extracted"] == 3
    assert receipt["persons_with_zero_career_rows"] == 1
    assert receipt["missing_person_id_in_frame"] == 1
    assert receipt["missing_person_id_in_career"] == 1
    assert sorted((row["pid"], row["job"]) for row in extracted) == [("p1", "new"), ("p1", "old"), ("p2", "only")]
    assert sorted((row["pid"], row["visible_career_row_count"]) for row in sampled) == [("p1", "2"), ("p2", "1"), ("p3", "0")]


def test_rejects_missing_eligibility_column(tmp_path):
    frame, career, out = tmp_path / "f.csv", tmp_path / "c.csv", tmp_path / "out"
    write_csv(frame, ["pid"], [{"pid": "p1"}])
    write_csv(career, ["pid", "job"], [{"pid": "p1", "job": "j"}])
    mapping = {"schema_verified": True, "person_frame": {"path": str(frame), "format": "csv", "person_id_column": "pid", "eligibility_column": "eligible", "eligible_value": "yes"}, "career": {"path": str(career), "format": "csv", "person_id_column": "pid", "required_columns": {"stable_position_id": "job"}}, "output": {"allow_raw_extract": True, "protected_destination": str(out)}}
    mp = tmp_path / "m.json"; mp.write_text(json.dumps(mapping))
    result = subprocess.run([sys.executable, str(ROOT / "revelio_r0_extract.py"), "--mapping", str(mp), "--protected-output", str(out)], capture_output=True, text=True)
    assert result.returncode != 0 and "eligibility_column is absent" in result.stderr


def test_rejects_duplicate_person_ids(tmp_path):
    frame, career, out = tmp_path / "f.csv", tmp_path / "c.csv", tmp_path / "out"
    write_csv(frame, ["pid"], [{"pid": "p1"}, {"pid": "p1"}])
    write_csv(career, ["pid", "job"], [{"pid": "p1", "job": "j"}])
    mapping = {"schema_verified": True, "person_frame": {"path": str(frame), "format": "csv", "person_id_column": "pid"}, "career": {"path": str(career), "format": "csv", "person_id_column": "pid", "required_columns": {"stable_position_id": "job"}}, "output": {"allow_raw_extract": True, "protected_destination": str(out)}}
    mp = tmp_path / "m.json"; mp.write_text(json.dumps(mapping))
    result = subprocess.run([sys.executable, str(ROOT / "revelio_r0_extract.py"), "--mapping", str(mp), "--protected-output", str(out)], capture_output=True, text=True)
    assert result.returncode != 0 and "duplicate stable person-ID" in result.stderr


def test_rejects_git_worktree_destination(tmp_path):
    frame, career = tmp_path / "f.csv", tmp_path / "c.csv"
    git_root = tmp_path / "gitroot"; git_root.mkdir(); (git_root / ".git").mkdir()
    out = git_root / "private"
    write_csv(frame, ["pid"], [{"pid": "p1"}])
    write_csv(career, ["pid", "job"], [{"pid": "p1", "job": "j"}])
    mapping = {"schema_verified": True, "person_frame": {"path": str(frame), "format": "csv", "person_id_column": "pid"}, "career": {"path": str(career), "format": "csv", "person_id_column": "pid", "required_columns": {"stable_position_id": "job"}}, "output": {"allow_raw_extract": True, "protected_destination": str(out)}}
    mp = tmp_path / "m.json"; mp.write_text(json.dumps(mapping))
    result = subprocess.run([sys.executable, str(ROOT / "revelio_r0_extract.py"), "--mapping", str(mp), "--protected-output", str(out)], capture_output=True, text=True)
    assert result.returncode != 0 and "outside every Git worktree" in result.stderr
