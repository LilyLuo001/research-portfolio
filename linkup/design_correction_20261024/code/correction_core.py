"""Design weighted generalized difference estimates, with nullable reference labels.

Pure numerical functions: no text, model, or label production. Bounds are missing
reference-label sensitivity bounds for this estimator, never confidence intervals.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

MAJORS = ('11', '13', '15', '17')
GA = 'genai_use_with_or_without_software'
GB = 'traditional_software_use_no_ai'


def truth(value, index):
    if value is None:
        return pd.Series(pd.NA, index=index, dtype='boolean')
    if np.isscalar(value):
        return pd.Series(value, index=index, dtype='boolean')
    return pd.Series(value, index=index).astype('boolean')


def conjunction(*values):
    result = truth(True, values[0].index)
    for value in values:
        result &= value.astype('boolean')
    return result


def expr(frame, expression):
    """Evaluate a deliberately small, explicit, three-valued indicator AST."""
    if isinstance(expression, (bool, int)):
        if expression not in (0, 1):
            raise ValueError('indicator constant must be 0/1')
        return truth(bool(expression), frame.index)
    if expression is None:
        return truth(None, frame.index)
    if isinstance(expression, str):
        if expression not in frame:
            raise KeyError(expression)
        vals = frame[expression]
        if not vals.dropna().isin([0, 1, False, True]).all():
            raise ValueError('not a binary column: ' + expression)
        return truth(vals, frame.index)
    op = expression['op']
    if op in ('and', 'or'):
        result = truth(op == 'and', frame.index)
        for arg in expression['args']:
            val = expr(frame, arg)
            result = result & val if op == 'and' else result | val
        return result
    if op == 'not':
        return ~expr(frame, expression['arg'])
    if op in ('eq', 'in'):
        vals = frame[expression['column']]
        val = vals.eq(expression['value']) if op == 'eq' else vals.isin(expression['values'])
        return val.astype('boolean').mask(vals.isna(), pd.NA)
    raise ValueError('unsupported indicator operator: ' + op)


def needed_columns(expression):
    if isinstance(expression, str):
        return {expression}
    if not isinstance(expression, dict):
        return set()
    if expression['op'] in ('eq', 'in'):
        return {expression['column']}
    if expression['op'] == 'not':
        return needed_columns(expression['arg'])
    return set().union(*(needed_columns(x) for x in expression['args']))


def interval(value):
    return value.fillna(False).to_numpy(dtype=float), value.fillna(True).to_numpy(dtype=float)


def estimate_component(reference, old, weight, old_census, population_n):
    if old.isna().any():
        raise ValueError('working proxy must be fully observed; unavailable != zero')
    lo, hi = interval(reference)
    proxy = old.to_numpy(dtype=float)
    w = np.asarray(weight, dtype=float)
    lower = float(old_census + np.dot(w, lo - proxy))
    upper = float(old_census + np.dot(w, hi - proxy))
    unknown = reference.isna().to_numpy()
    known = ~unknown
    ref = reference.fillna(False).to_numpy(dtype=float)
    return {
        'old_census_total': float(old_census),
        'old_sample_ht_total': float(np.dot(w, proxy)),
        'reference_known_positive_ht_total': float(np.dot(w, ref)),
        'reference_unknown_ht_mass': float(np.dot(w, unknown)),
        'known_residual_ht_total': float(np.dot(w[known], ref[known] - proxy[known])),
        'corrected_total_point': lower if not unknown.any() else None,
        'corrected_total_lower_raw': lower,
        'corrected_total_upper_raw': upper,
        'reference_known_ads': int(known.sum()),
        'reference_unknown_ads': int(unknown.sum()),
        'weighted_false_positive': float(np.dot(w, known & (ref == 0) & (proxy == 1))),
        'weighted_false_negative': float(np.dot(w, known & (ref == 1) & (proxy == 0))),
        'population_n': int(population_n),
    }


def known_domain_components(domain, outcome):
    """Observed-reference domain, with unknown membership/outcome excluded explicitly.

    Filling the JOINT indicators outside this named observed domain is indicator
    arithmetic. The original reference columns and full-target envelopes stay nullable.
    """
    denominator = domain.fillna(False) & outcome.notna()
    numerator = denominator & outcome.fillna(False)
    return numerator.astype('boolean'), denominator.astype('boolean')


def corrected_point(numerator, denominator):
    n = numerator['corrected_total_point']
    d = denominator['corrected_total_point']
    if n is None or d is None or d <= 0 or not 0 <= n <= d <= denominator['population_n']:
        return None, 'unavailable_invalid_corrected_totals'
    return n / d, 'reference_known_domain_only'


def ht_envelope(domain, outcome, weight):
    """Nonnegative HT reference mass envelope; no corrected-total clipping."""
    yl, yu = interval(conjunction(domain, outcome))
    dl, du = interval(domain)
    w = np.asarray(weight, dtype=float)
    nlo, nhi, dlo, dhi = (float(np.dot(w, z)) for z in (yl, yu, dl, du))
    return {'ht_numerator_lower': nlo, 'ht_numerator_upper': nhi,
            'ht_denominator_lower': dlo, 'ht_denominator_upper': dhi,
            'full_target_unknown_lower': nlo / dhi if dhi > 0 else None,
            'full_target_unknown_upper': min(1., nhi / dlo) if dlo > 0 else 1. if dhi > 0 else None,
            'unknown_domain_ads': int(domain.isna().sum()),
            'unknown_outcome_in_possible_domain_ads': int((domain.fillna(True) & outcome.isna()).sum())}



_GROUP_CACHE = {}

def design_variance(influence, cells, population):
    """Stratified SRSWOR variance; all sampled rows enter, including zeros."""
    cache_key = tuple(cells)
    if cache_key not in _GROUP_CACHE:
        unique = sorted(set(cells))
        lookup = {cell: i for i, cell in enumerate(unique)}
        groups = np.array([lookup[cell] for cell in cells], dtype=int)
        counts = np.bincount(groups).astype(float)
        _GROUP_CACHE[cache_key] = (unique, groups, counts)
    unique, groups, n = _GROUP_CACHE[cache_key]
    N = np.array([population[cell] for cell in unique], dtype=float)
    if (N < n - 1e-7).any():
        raise ValueError('population smaller than sample')
    noncensus = ~np.isclose(N, n, atol=1e-7, rtol=0)
    if ((n < 2) & noncensus).any():
        return None
    x = np.asarray(influence, dtype=float)
    sums = np.bincount(groups, weights=x, minlength=len(unique))
    squares = np.bincount(groups, weights=x*x, minlength=len(unique))
    sample_var = np.zeros(len(unique))
    use = n > 1
    sample_var[use] = np.maximum(0., squares[use] - sums[use]**2 / n[use]) / (n[use] - 1)
    return float(np.sum(N*N * (1. - n/N) * sample_var / n))
