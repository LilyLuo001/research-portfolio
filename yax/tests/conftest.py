"""Put the repository root on sys.path for the yax test suite.

Most dax tests load their target by file path with importlib and need nothing
here. Four tests added with the W4 duration gate import by package instead --
`from dax.capability_panel.task_duration_gate import ...` -- and `dax/` has no
`__init__.py`, so that only resolves when the repository root happens to be on
sys.path.

`python -m pytest` inserts the working directory, so those tests pass locally.
CI runs bare `pytest -q`, which does not, and every one of them failed to
collect there with `No module named 'dax'`. The suite was green for anyone
running it the first way and red in CI, which is the worst version of this
bug.

Every other test directory in the repository already carries a conftest for
the same reason -- p1/tests, e2/tests, refraction/tests, ops/runner/tests and
shared/econlib/tests. This is the missing one, written to match them.
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
