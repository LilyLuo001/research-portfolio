"""Coordinator checks of saved receipts and synthetic join boundaries only."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pandas as pd
from run_other_wave_join import build_pairs, EXP_COLS, UNI_COLS

root = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
full = json.loads((root / "full_artifacts/receipt.json").read_text())
pilot = json.loads((root / "pilot_artifacts/receipt.json").read_text())
gate = json.loads((root / "OTHER_WAVE_JOIN_PILOT_PASS.json").read_text())
for name, key in [("run_other_wave_join.py", "code_sha256"),
                  ("config.json", "config_sha256"),
                  ("source_manifest.json", "manifest_sha256")]:
    assert sha(root / name) == full[key] == pilot[key] == gate[key], name
assert sha(root / "pilot_artifacts/receipt.json") == gate["pilot_receipt_sha256"]
for name, digest in full["aggregate_hashes"].items():
    assert sha(root / "full_artifacts" / name) == digest, name
assert full["focal_candidate_denominator"] == 99
assert full["candidates_with_any_other_wave_match"] + full["candidates_with_no_other_wave_match"] == 99
assert full["candidate_other_wave_pairs"] == 45
assert full["candidates_with_any_other_wave_match"] == 24
assert full["matched_other_wave_count"] == 4
subprocess.run([sys.executable, "-B", str(root / "test_other_wave_join.py")], check=True)
c = pd.DataFrame([["A", "W1", "high", 1], ["B", "W2", "low", 1]],
                 columns=["candidate_id", "wave_id", "provisional_tier", "permno"])
u = pd.DataFrame(columns=UNI_COLS)
p = build_pairs(c, pd.DataFrame(columns=EXP_COLS), u)
assert len(p) == 2 and p.other_wave_id.eq("NO_OTHER_WAVE_MATCH").all()
e = pd.DataFrame([[1, "W1", "2020-01-01"], [1, "W2", "2021-01-01"]], columns=EXP_COLS)
p = build_pairs(c, e, u)
assert set(zip(p.candidate_id, p.other_wave_id)) == {("A", "W2"), ("B", "W1")}
assert p.public_metadata_relation.eq("OTHER_WAVE_MISSING_FROM_PUBLIC_UNIVERSE_METADATA").all()
print(json.dumps({"status": "PASS", "existing_fixture_assertions": 13,
                  "additional_synthetic_scenarios": 2,
                  "saved_gate_and_output_hashes_match": True,
                  "independent_source_row_reproduction": "NOT_RUN",
                  "scientific_eligibility": "NOT_ASSESSED"}))
