"""Outcome-blind finite checks for the P1 review-closure bundle.

These fixtures do not read P1 data and do not validate an inference procedure.
"""
from __future__ import annotations

import numpy as np


def connected_graph_is_not_transitive_covariance() -> dict[str, object]:
    """Prompt-specified A--B--C graph: connected, while Cov(A,C)=0."""
    # U_A=a1+d1, U_B=a2+d1, U_C=a2+d2; all primitive shocks variance one.
    covariance = np.array([[2.0, 1.0, 0.0], [1.0, 2.0, 1.0], [0.0, 1.0, 2.0]])
    edges = [("A", "B", "shared_date"), ("B", "C", "shared_stock")]
    return {
        "covariance": covariance,
        "edges": edges,
        "component_count": 1,
        "covariance_A_C": float(covariance[0, 2]),
        "interpretation": "CONNECTED_GRAPH_DOES_NOT_IMPLY_TRANSITIVE_COVARIANCE",
    }
