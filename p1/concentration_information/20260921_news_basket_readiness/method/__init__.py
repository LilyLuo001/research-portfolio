"""Synthetic-only implementation of the proposed news--ETF--actual-basket estimator.

This package deliberately has no readers, network clients, or empirical defaults.
"""

from .estimator import (
    InputRejected,
    fieller_set,
    fixed_common_support_weights,
    paired_response,
    fit_joint_standardized_slopes,
    ratio_contrast_confidence_set,
    composition_decomposition,
)

__all__ = [
    "InputRejected", "fieller_set", "fixed_common_support_weights",
    "paired_response", "fit_joint_standardized_slopes",
    "ratio_contrast_confidence_set", "composition_decomposition",
]
