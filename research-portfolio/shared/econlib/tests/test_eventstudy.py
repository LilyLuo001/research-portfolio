"""Event study recovers a flat pre-trend and the known dynamic path, and
normalizes the reference period to zero."""
from econlib.eventstudy import event_study
from toydata import single_cohort_panel


def test_event_study_dynamics():
    df = single_cohort_panel(n_units=60, T=8, g=4, tau=1.0, seed=2, dynamic=True)
    es = event_study(df, window=(-3, 3), ref=-1)

    # reference period normalized to exactly zero
    assert es.loc[-1, "coef"] == 0.0

    # flat pre-trend (leads ~ 0)
    for k in (-3, -2):
        assert abs(es.loc[k, "coef"]) < 0.4

    # dynamic path: effect at event time k is tau*(k+1) = 1, 2, 3, 4
    assert abs(es.loc[0, "coef"] - 1.0) < 0.4
    assert abs(es.loc[1, "coef"] - 2.0) < 0.5
    assert abs(es.loc[2, "coef"] - 3.0) < 0.6
    assert es.loc[2, "coef"] > es.loc[0, "coef"]   # monotone growth


def test_event_study_has_all_periods():
    df = single_cohort_panel(seed=2)
    es = event_study(df, window=(-3, 3), ref=-1)
    assert list(es.index) == [-3, -2, -1, 0, 1, 2, 3]
