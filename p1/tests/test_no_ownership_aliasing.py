"""`pre_etf_ownership` must never be an alias for `conv_exp`.

The field name means TOTAL pre-conversion ETF ownership — the GNZ-style control
variable. `conv_exp` is the CONVERTING FUNDS' ownership only. They are different
quantities, and the second is a strict subset of the first.

The free path used to write `conv_exp` into it. Nothing raised: the column was
populated, the contract passed, and the number was plausible. Any regression
using it as an ownership control would have been silently misspecified —
mechanically, the "control" would have been collinear with the treatment.

The WRDS twin (holdings_pipeline.py) always wrote None and has had a test since
its introduction. This file extends the same guard to the free path and to the
committed artifact, so the two paths cannot drift apart again.
"""
import ast
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
FREE = ROOT / "p1" / "t2_free" / "build_nport_convexp.py"
PARQUET = ROOT / "p1" / "conv_exposure_free.parquet"


def test_free_path_writes_none_not_conv_exp():
    """Read the emitted dict literal out of the source, not a string grep."""
    tree = ast.parse(FREE.read_text())
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for k, v in zip(node.keys, node.values):
            if isinstance(k, ast.Constant) and k.value == "pre_etf_ownership":
                found.append(v)
    assert found, "pre_etf_ownership vanished from the free path entirely"
    for v in found:
        assert isinstance(v, ast.Constant) and v.value is None, (
            "pre_etf_ownership must be written as None. Assigning conv_exp (or "
            "anything derived from it) puts the converting funds' ownership "
            "under a name that reads as total ETF ownership — see this file's "
            "docstring.")


def test_committed_parquet_is_flagged_if_still_aliased():
    """The committed artifact predates the fix, so it IS still aliased.

    Pinned deliberately rather than ignored: it documents that the current file
    must not be used for an ownership control, and it will fail the moment the
    rebuilt parquet lands — at which point flip the expectation to all-null.
    """
    pytest.importorskip("pandas")
    import pandas as pd
    df = pd.read_parquet(PARQUET)
    aliased = df["pre_etf_ownership"].equals(df["conv_exp"])
    assert aliased, (
        "conv_exposure_free.parquet no longer aliases pre_etf_ownership — the "
        "rebuild has landed. Update this test to assert the column is all-null, "
        "and re-check anything that consumed it.")


def test_no_p1_code_uses_it_as_a_regression_control():
    """Nothing in p1/ may feed this column into a control set."""
    hits = []
    for path in (ROOT / "p1").rglob("*.py"):
        if "__pycache__" in path.parts or path.name == "test_no_ownership_aliasing.py":
            continue
        for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if "pre_etf_ownership" not in line:
                continue
            low = line.lower()
            if any(w in low for w in ("control", "covariate", "rhs", "regress", "match_on")):
                hits.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
    assert not hits, (
        "pre_etf_ownership appears in a controls/covariates context:\n"
        + "\n".join(hits)
        + "\nIt is NULL by construction until a 13F/ETF-holdings join exists.")
