"""Static guard: no local name is read before it is ever assigned.

Why this exists. `p1/t2_free/build_nport_convexp.py` carried a leftover inline
copy of its per-cell loop that appended to `rows` and `nh_stocks`. Further down,
`rows, nh_stocks = _cell_rows(...)` made both names function-local for the whole
of `main()`, so those earlier appends raised UnboundLocalError on the very first
aggregated cell — *after* hours of rate-limited EDGAR fetching had been paid for.

Nothing caught it. The unit tests call `_cell_rows` directly with synthetic
cells; no test calls `main()`, because `main()` needs the network. So a green
suite said nothing about the one command the whole task depends on.

That is the gap this file closes. It needs no network, no fixtures and no data —
it reads the source. `symtable` tells us which names are genuinely function-local
(so module-level names and builtins are not false positives), and the AST gives
first-read/first-write line numbers.

The rule: a local is flagged when some read of it appears BEFORE its first
binding. Not "every read before every write" — the real defect read `rows` both
before the tuple-assignment and after it, so that stricter rule missed the very
bug this file was written for.

A name written at the bottom of a loop and read at the top on the next pass is
not flagged, because its binding still appears textually before some read of it
(`prev = None` above the loop). A name whose only binding is inside a loop it is
also read at the top of IS flagged, correctly — that fails on iteration one.
"""
import ast
import pathlib
import symtable

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
P1 = ROOT / "p1"

SKIP_DIRS = {"__pycache__", "cache", "raw", ".pytest_cache"}


def _py_files():
    return sorted(p for p in P1.rglob("*.py")
                  if not any(part in SKIP_DIRS for part in p.parts))


def _local_names(st):
    """Names symtable says are local to this scope AND bound in it.

    Using symtable rather than a hand-rolled scope model is what keeps module
    globals and builtins from showing up as false positives.
    """
    return {sym.get_name() for sym in st.get_symbols()
            if sym.is_local() and sym.is_assigned() and not sym.is_parameter()}


def _function_scopes(st, out=None):
    """(name, lineno) -> symtable scope, for every function scope in the file.

    Comprehensions are their own scopes in Python 3 and are deliberately not
    collected: they are matched out of the AST side instead.
    """
    if out is None:
        out = {}
    for child in st.get_children():
        if child.get_type() == "function":
            out[(child.get_name(), child.get_lineno())] = child
        _function_scopes(child, out)
    return out


# Nodes that open a scope of their own, so names inside them belong to that
# scope rather than to the enclosing function.
NESTED = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
          ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def _own_nodes(fn):
    """Nodes belonging to `fn` itself, excluding every nested scope."""
    skip = set()
    for n in ast.walk(fn):
        if n is fn:
            continue
        if isinstance(n, NESTED):
            for sub in ast.walk(n):
                skip.add(id(sub))
    return [n for n in ast.walk(fn) if id(n) not in skip]


def _offences_in(path):
    src = path.read_text()
    tree = ast.parse(src)
    scopes = _function_scopes(symtable.symtable(src, str(path), "exec"))
    bad = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        st = scopes.get((fn.name, fn.lineno))
        if st is None:
            continue
        locals_here = _local_names(st)
        declared = {n for node in ast.walk(fn)
                    if isinstance(node, (ast.Global, ast.Nonlocal))
                    for n in node.names}
        stores, loads = {}, {}
        for n in _own_nodes(fn):
            if isinstance(n, ast.Name) and n.id in locals_here:
                (stores if isinstance(n.ctx, ast.Store) else loads) \
                    .setdefault(n.id, []).append(n.lineno)
        for name in sorted(locals_here - declared):
            s, l = stores.get(name), loads.get(name)
            if not s or not l:
                continue
            if min(l) < min(s):        # a read exists before the first binding
                bad.append((path, fn.name, name, min(l), min(s)))
    return bad


@pytest.mark.parametrize("path", _py_files(), ids=lambda p: str(p.relative_to(P1)))
def test_no_local_is_read_before_it_is_ever_assigned(path):
    bad = _offences_in(path)
    assert not bad, "\n".join(
        f"{f}:{fn}() reads `{name}` at line {ld} but its first binding is line "
        f"{sd} — UnboundLocalError at runtime. If the earlier block is dead "
        f"code, delete it; do not paper over it by pre-seeding the name."
        for f, fn, name, ld, sd in bad)


def test_the_lint_catches_the_bug_it_was_written_for(tmp_path):
    """The exact shape of the build_nport_convexp defect."""
    p = tmp_path / "regression.py"
    p.write_text(
        "def main():\n"
        "    agg = [1, 2]\n"
        "    for x in agg:\n"
        "        rows.append(x)\n"
        "    rows, other = ([], [])\n"
        "    return rows, other\n")
    bad = _offences_in(p)
    assert [b[2] for b in bad] == ["rows"], bad


def test_the_lint_does_not_flag_a_legal_loop_carry(tmp_path):
    """Written at the bottom of a loop, read at the top next pass — legal."""
    p = tmp_path / "legal.py"
    p.write_text(
        "def f(items):\n"
        "    prev = None\n"
        "    for x in items:\n"
        "        if prev is not None:\n"
        "            print(prev)\n"
        "        prev = x\n"
        "    return prev\n")
    assert _offences_in(p) == []


def test_the_lint_does_not_flag_closures_over_module_globals(tmp_path):
    p = tmp_path / "closure.py"
    p.write_text(
        "CONST = 3\n"
        "def f():\n"
        "    def inner():\n"
        "        return CONST + total\n"
        "    total = 1\n"
        "    return inner()\n")
    assert _offences_in(p) == []
