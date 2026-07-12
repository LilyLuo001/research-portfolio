"""Synthetic fixtures for the Refraction guard + assertion tests (no real data;
per iron rule the tests exercise the machinery, never assert about the world).

World: one wave W1 effective 2023-01-02; four permnos (1001/1002 treated with
ConvExp .02/.01; 2001/2002 controls); six scheduled announcements, three pre /
three post; internally consistent betas, weights, LOO basket responses."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

WAVE_EFF = {"W1": date(2023, 1, 2)}
PERMNOS = [1001, 1002, 2001, 2002]
TREATED = {1001, 1002}
CONVEXP = {1001: 0.02, 1002: 0.01, 2001: 0.0, 2002: 0.0}
BETA = {1001: 0.8, 1002: 1.3, 2001: 1.0, 2002: 0.6}
WEIGHT = {1001: 0.55, 1002: 0.45}  # converting-fund portfolio holds the treated pair
ANNS = [  # announcement_id, type, date, time
    ("FOMC-2022-06-15", "FOMC", "2022-06-15", "14:00"),
    ("CPI-2022-09-13", "CPI", "2022-09-13", "08:30"),
    ("NFP-2022-12-02", "NFP", "2022-12-02", "08:30"),
    ("FOMC-2023-03-22", "FOMC", "2023-03-22", "14:00"),
    ("CPI-2023-06-13", "CPI", "2023-06-13", "08:30"),
    ("NFP-2023-09-01", "NFP", "2023-09-01", "08:30"),
]


@pytest.fixture
def wave_effective():
    return pd.Series({w: pd.Timestamp(d) for w, d in WAVE_EFF.items()})


@pytest.fixture
def calendar():
    return pd.DataFrame(
        [{"announcement_id": a, "type": t, "date_ET": d} for a, t, d, _ in ANNS])


@pytest.fixture
def betas():
    beta_b_full = sum(WEIGHT[p] * BETA[p] for p in WEIGHT)
    rows = []
    for p in PERMNOS:
        loo = ((beta_b_full - WEIGHT.get(p, 0.0) * BETA[p]) / (1 - WEIGHT.get(p, 0.0))
               if p in WEIGHT else beta_b_full)
        rows.append({"permno": p, "wave": "W1", "beta_i": BETA[p], "se_beta": 0.05,
                     "n_pre_announcements": 40, "max_est_date": "2022-12-30",
                     "beta_b_loo": loo})
    return pd.DataFrame(rows)


@pytest.fixture
def weights():
    return pd.DataFrame([{"wave": "W1", "permno": p, "weight": w}
                         for p, w in WEIGHT.items()])


@pytest.fixture
def basket():
    return pd.DataFrame([{"wave": "W1",
                          "beta_b_full": sum(WEIGHT[p] * BETA[p] for p in WEIGHT)}])


@pytest.fixture
def convexp():
    return pd.DataFrame([{"permno": p, "wave": "W1", "conv_exp": CONVEXP[p],
                          "effective_date": "2023-01-02"}
                         for p in PERMNOS if p in TREATED])


@pytest.fixture
def panel(betas):
    loo = betas.set_index("permno")["beta_b_loo"]
    rng = np.random.default_rng(7)
    rows = []
    for a, t, d, tm in ANNS:
        post = pd.Timestamp(d).date() >= WAVE_EFF["W1"]
        for p in PERMNOS:
            r1, r2 = rng.normal(0, 0.01, 2)
            L = loo[p] - BETA[p]
            rows.append({
                "permno": p, "announcement_id": a, "type": t, "date_ET": d,
                "time_ET": tm, "wave": "W1", "is_treated": p in TREATED,
                "Post": post, "ConvExp": CONVEXP[p], "S_std": rng.normal(),
                "r_c2o": r1, "r_o2c": r2, "r_total": r1 + r2,
                "beta_i": BETA[p], "beta_b_loo": loo[p],
                "L": L, "L_mkt": 1 - BETA[p], "L_tilt": loo[p] - 1,
            })
    return pd.DataFrame(rows)


@pytest.fixture
def config():
    import yaml
    from pathlib import Path
    return yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "frozen_config.yaml").read_text())
