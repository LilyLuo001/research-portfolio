import importlib.util
from pathlib import Path

import numpy as np


MODULE = Path(__file__).parents[1] / "code" / "closure_checks.py"
SPEC = importlib.util.spec_from_file_location("closure_checks", MODULE)
closure_checks = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(closure_checks)


def test_connected_graph_is_not_transitive_covariance():
    r = closure_checks.connected_graph_is_not_transitive_covariance()
    assert r["component_count"] == 1
    assert r["edges"] == [("A", "B", "shared_date"), ("B", "C", "shared_stock")]
    assert np.allclose(r["covariance"], [[2, 1, 0], [1, 2, 1], [0, 1, 2]])
    assert r["covariance_A_C"] == 0.0
    assert r["interpretation"] == "CONNECTED_GRAPH_DOES_NOT_IMPLY_TRANSITIVE_COVARIANCE"
