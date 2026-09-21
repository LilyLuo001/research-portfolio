"""Fail-closed validation amendment, reusing unchanged historical projection.

No tolerance repairs are made: PSD means PSD of the represented binary floats,
tested exactly as rational numbers. Slightly asymmetric or indefinite inputs
are rejected, even when numerical rounding could explain them. This is not an
empirical covariance estimator or critical-value calibration.
"""
import importlib.util
import itertools
from fractions import Fraction
from pathlib import Path
import numpy as np

BASE = Path(__file__).resolve().parents[2] / '20260921_ratio_continuation/method/estimator.py'
spec = importlib.util.spec_from_file_location('_preserved_ratio_projection', BASE)
_base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_base)
InputRejected = _base.InputRejected
ORDER = _base.ORDER

def _determinant(matrix):
    if len(matrix) == 1:
        return matrix[0][0]
    return sum(((-1)**j * matrix[0][j] * _determinant(
        [row[:j]+row[j+1:] for row in matrix[1:]])) for j in range(len(matrix)))

def _psd_covariance(value, name='joint_covariance'):
    covariance = _base._finite_array(value, name, 2)
    if covariance.shape != (4,4):
        raise InputRejected(f'{name} must be 4x4')
    if not np.array_equal(covariance, covariance.T):
        raise InputRejected(f'{name} is not exactly symmetric; no implicit repair')
    matrix = [[Fraction.from_float(float(x)) for x in row] for row in covariance]
    # A real symmetric matrix is PSD iff ALL principal minors are nonnegative.
    # There are only 15 for this fixed four-coefficient interface.
    for size in range(1,5):
        for idx in itertools.combinations(range(4), size):
            minor = [[matrix[i][j] for j in idx] for i in idx]
            if _determinant(minor) < 0:
                raise InputRejected(f'{name} is not PSD as represented; negative principal minor {idx}')
    return covariance.copy()

_base._psd_covariance = _psd_covariance
joint_covariance_from_event_score_sums = _base.joint_covariance_from_event_score_sums

def ratio_contrast_outer_bound(*args, **kwargs):
    result = _base.ratio_contrast_outer_bound(*args, **kwargs)
    result['covariance_input_policy'] = 'EXACT_RATIONAL_PRINCIPAL_MINORS_OF_BINARY_FLOATS_NO_REPAIR'
    return result
