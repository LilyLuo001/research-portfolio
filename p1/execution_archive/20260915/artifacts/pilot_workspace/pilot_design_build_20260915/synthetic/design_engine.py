"""Synthetic implementation of the candidate wave fit, not an empirical estimator run.

Rows passed here are generated in tests; this module has no source-data reader.
Derivative standardization requires actual stock x calendar-cell support.
Exact redundant nuisance columns are retained for a row-space contrast test.
"""
from dataclasses import dataclass
import numpy as np


@dataclass
class FitResult:
    contrast: np.ndarray
    influence: np.ndarray
    event_ids: list
    rank: int
    columns: int
    contrast_rowspace_residual: float


def validate_events(rows):
    keys = [(r['wave'], r['event_id']) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('DUPLICATE_ECONOMIC_EVENT_WITHIN_WAVE')
    if len({r['wave'] for r in rows}) != 1:
        raise ValueError('FIT_ONE_WAVE_AT_A_TIME')
    stock_defs = {}
    for r in rows:
        definition = (r['group'], r['industry'])
        if stock_defs.setdefault(r['stock'], definition) != definition:
            raise ValueError('STOCK_DEFINITION_CHANGED')
        if r['group'] not in ('H', 'L') or r['post'] not in (0, 1):
            raise ValueError('INVALID_CANDIDATE_CELL')


def encode(rows, stocks, cells):
    """All low-order H,P,SUE interactions plus stock and industry-cell levels/slopes."""
    names = ['1', 'H', 'P', 'H:P', 'S', 'H:S', 'P:S', 'H:P:S']
    names += [f'stock={s}' for s in stocks]
    names += [f'stock={s}:S' for s in stocks]
    names += [f'ic={i}/{c}' for i, c in cells]
    names += [f'ic={i}/{c}:S' for i, c in cells]
    values = []
    for r in rows:
        h, p, s = float(r['group'] == 'H'), float(r['post']), float(r['sue'])
        stock = [float(r['stock'] == x) for x in stocks]
        ic = [float((r['industry'], r['cell']) == x) for x in cells]
        values.append([1, h, p, h*p, s, h*s, p*s, h*p*s] + stock + [v*s for v in stock] + ic + [v*s for v in ic])
    return np.asarray(values, dtype=float), names


def standardized_contrast(rows, stocks, cells):
    """One wave H/L POST/PRE slope DID; equal PRE stock and common-cell weights."""
    observed = {(r['stock'], r['cell'], r['post']) for r in rows}
    stock_meta = {r['stock']: (r['group'], r['industry']) for r in rows}
    terms = []
    for post in (0, 1):
        group_cells = [{r['cell'] for r in rows if r['post'] == post and r['group'] == g} for g in ('H', 'L')]
        common_cells = sorted(group_cells[0] & group_cells[1])
        if not common_cells:
            raise ValueError(f'NO_COMMON_CALENDAR_CELLS_PERIOD_{post}')
        for group in ('H', 'L'):
            eligible_stocks = sorted({r['stock'] for r in rows if r['post'] == 0 and r['group'] == group})
            if not eligible_stocks:
                raise ValueError(f'NO_FROZEN_PRE_STOCKS_{group}')
            sign = (1 if group == 'H' else -1) * (1 if post else -1)
            for stock in eligible_stocks:
                for cell in common_cells:
                    if (stock, cell, post) not in observed:
                        raise ValueError(f'MISSING_REQUIRED_STOCK_CELL:{stock}:{cell}:{post}')
                    base = dict(stock=stock, group=group, industry=stock_meta[stock][1], cell=cell, post=post)
                    probes = [dict(base, sue=0.), dict(base, sue=1.)]
                    x, _ = encode(probes, stocks, cells)
                    terms.append(sign*(x[1]-x[0])/(len(eligible_stocks)*len(common_cells)))
    return np.sum(terms, axis=0)


def fit_wave(rows, outcomes):
    validate_events(rows)
    stocks = sorted({r['stock'] for r in rows})
    cells = sorted({(r['industry'], r['cell']) for r in rows})
    x, names = encode(rows, stocks, cells)
    q = standardized_contrast(rows, stocks, cells)
    y = np.asarray(outcomes, dtype=float)
    if y.ndim == 1:
        y = y[:, None]
    if len(y) != len(rows) or not np.isfinite(y).all():
        raise ValueError('INVALID_SYNTHETIC_OUTCOME_ARRAY')
    pinv = np.linalg.pinv(x)
    residual = float(np.max(np.abs(q - q @ pinv @ x)))
    if residual > 1e-9:
        raise ValueError('REQUIRED_CONTRAST_NOT_IDENTIFIED')
    beta = pinv @ y
    errors = y - x @ beta
    row_contrast_weights = q @ pinv
    influence = row_contrast_weights[:, None]*errors
    return FitResult(q @ beta, influence, [r['event_id'] for r in rows], int(np.linalg.matrix_rank(x)), len(names), residual)


def unique_event_covariance(fits, wave_weights):
    """Uncorrected event-score meat ONLY. Not approved dependence/inference.

    Sum wave-weighted influences before forming outer products so repeated
    event IDs across stacks retain cross-wave and cross-horizon terms.
    Sponsor/date/serial covariance is NOT supplied by this primitive.
    """
    if len(fits) != len(wave_weights) or not np.isclose(sum(wave_weights), 1.):
        raise ValueError('INVALID_WAVE_WEIGHTS')
    event_scores = {}
    for fit, weight in zip(fits, wave_weights):
        for event, vector in zip(fit.event_ids, fit.influence):
            event_scores[event] = event_scores.get(event, np.zeros_like(vector)) + weight*vector
    scores = np.stack(list(event_scores.values()))
    return scores.T @ scores, len(event_scores)
