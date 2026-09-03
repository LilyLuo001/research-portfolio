"""Tests for the W2 two-channel price harvester.

These pin the properties that make the panel trustworthy rather than merely
populated: unit-drift tolerance, no fabricated dates, no single-channel row
ever reaching `verified`, and locality of price matching.
"""

import pathlib
import sys

import pytest

PRICES = pathlib.Path(__file__).resolve().parents[1] / "w2" / "prices"
sys.path.insert(0, str(PRICES))

import channel_git            # noqa: E402
import channel_wayback as cw  # noqa: E402


# --- Channel A: corroboration semantics -------------------------------------

def test_price_tokens_cover_per_1k_and_per_1m_quoting():
    """GPT-4 launched quoted per-1K; the same price is $30/1M or $0.03/1K.

    Missing this turns every pre-2024 row into a false contradiction.
    """
    tokens = cw.price_tokens(30.0)
    assert "30" in tokens and "30.00" in tokens
    assert "0.03" in tokens


def test_corroborated_when_price_appears_near_model():
    text = "Our models. gpt-4o Input $5.00 per 1M tokens Output $15.00 per 1M tokens"
    status, _ = cw.corroborate_in_text(text, "gpt-4o-2024-05-13", 5.0)
    assert status == cw.CORROBORATED, "dated snapshot id should fall back to its alias"


def test_preview_id_falls_back_to_family_label():
    text = (
        "gpt-4.5-preview metadata " + ("filler " * 100) +
        "GPT-4.5 Price Input: $75.00 Cached input: $37.50 Output: $150.00"
    )
    status, _ = cw.corroborate_in_text(text, "gpt-4.5-preview", 37.5)
    assert status == cw.CORROBORATED


def test_not_found_when_model_absent():
    status, _ = cw.corroborate_in_text("Pricing for gpt-3.5-turbo $0.50", "gpt-5-2025-08-07", 1.25)
    assert status == cw.NOT_FOUND


def test_contradicted_when_model_present_but_price_differs():
    text = "gpt-4o Input $2.50 per 1M tokens"
    status, _ = cw.corroborate_in_text(text, "gpt-4o", 5.0)
    assert status == cw.CONTRADICTED


def test_distant_price_does_not_corroborate():
    """A price 2kB away on the page must not be credited to this model."""
    text = "gpt-4o Input " + ("filler " * 200) + "$5.00"
    status, _ = cw.corroborate_in_text(text, "gpt-4o", 5.0)
    assert status == cw.CONTRADICTED


def test_unreachable_archive_is_a_status_not_an_exception():
    result = cw.corroborate("gpt-4o", "input", 5.0, [], "2024-05-13")
    assert result.status == cw.NO_SNAPSHOT
    assert result.locator is None


# --- Channel B: interval construction ---------------------------------------

def _obs(model, kind, value, date):
    return channel_git.GitPriceObservation(
        model_id=model, price_kind=kind, usd_per_1m=value,
        observed_on=date, locator=f"repo@{date}:file.json",
    )


def test_intervals_bound_the_change_and_never_invent_a_date():
    from build_price_panel import to_intervals
    rows = to_intervals([
        _obs("gpt-4o", "input", 5.0, "2024-06-30"),
        _obs("gpt-4o", "input", 2.5, "2024-08-31"),
    ])
    assert rows[0]["effective_date_earliest"] == "", "first observation has no lower bound"
    assert rows[0]["effective_date_latest"] == "2024-06-30"
    # The cut happened after the old price was last seen and by the new date.
    assert rows[1]["effective_date_earliest"] == "2024-06-30"
    assert rows[1]["effective_date_latest"] == "2024-08-31"


def test_single_channel_rows_are_never_verified():
    from build_price_panel import to_intervals, VERIFIED
    rows = to_intervals([_obs("gpt-5-2025-08-07", "output", 10.0, "2025-09-30")])
    assert all(row["price_status"] != VERIFIED for row in rows), \
        "meta-rule 2: one channel can never certify a price"


def test_unchanged_months_are_not_re_emitted():
    """The panel is a price history, not a monthly repetition."""
    from build_price_panel import to_intervals
    rows = to_intervals([_obs("o3", "input", 2.0, "2025-05-31")])
    assert len(rows) == 1


def test_monthly_commits_use_committer_not_author_date(monkeypatch, tmp_path):
    seen = {}

    def fake_run(args, cwd, timeout=300):
        seen["args"] = args
        return "abc123 2026-03-11\n"

    monkeypatch.setattr(channel_git, "_run", fake_run)
    assert channel_git.monthly_commits(tmp_path) == [("abc123", "2026-03-11")]
    assert "--format=%H %cd" in seen["args"]


def test_exact_dated_official_evidence_can_corroborate_channel_b():
    from build_price_panel import apply_official_evidence, VERIFIED
    rows = [{
        "model_id": "gpt-4-0314", "price_kind": "input", "usd_per_1m": "30",
        "effective_date_latest": "2023-09-30", "price_status": "single_channel",
        "channel_web_status": "unreachable", "channel_web_snapshot": "",
        "channel_web_locator": "", "notes": "",
    }]
    evidence = [{
        "model_id": "gpt-4-0314", "price_kind": "input", "usd_per_1m": "30",
        "source_date": "2023-03-14", "source_url": "https://openai.com/example",
        "archived_url": "https://web.archive.org/example", "archived_sha256": "a" * 64,
    }]
    assert apply_official_evidence(rows, evidence) == 1
    assert rows[0]["price_status"] == VERIFIED
    assert rows[0]["effective_date_latest"] == "2023-03-14"
    assert rows[0]["channel_web_locator"] == evidence[0]["archived_url"]


def test_git_observation_before_dated_model_fails_closed():
    from build_price_panel import apply_temporal_sanity, CONFLICT, VERIFIED
    rows = [{
        "model_id": "gpt-5.4-2026-03-05",
        "channel_git_observed": "2026-01-14",
        "price_status": VERIFIED,
        "notes": "",
    }]
    assert apply_temporal_sanity(rows) == 1
    assert rows[0]["price_status"] == CONFLICT
    assert "cannot serve as an upper bound" in rows[0]["notes"]


def test_git_observation_on_model_date_is_allowed():
    from build_price_panel import apply_temporal_sanity, VERIFIED
    rows = [{
        "model_id": "gpt-5.4-2026-03-05",
        "channel_git_observed": "2026-03-05",
        "price_status": VERIFIED,
        "notes": "",
    }]
    assert apply_temporal_sanity(rows) == 0
    assert rows[0]["price_status"] == VERIFIED


# --- Contract shape ---------------------------------------------------------

def test_emitted_fields_match_the_frozen_contract():
    import yaml
    from build_price_panel import FIELDS
    contract = yaml.safe_load(
        (pathlib.Path(__file__).resolve().parents[2]
         / "ops" / "contracts" / "price_histories.yaml").read_text()
    )
    assert set(FIELDS) == set(contract["columns"]), "meta-rule 3: schema is frozen"
    for key in contract["primary_key"]:
        assert key in FIELDS


# --- date coherence against the registry (found after Channel A ran) ---------

def _price_row(model, latest, status="verified"):
    return {"model_id": model, "price_kind": "input", "usd_per_1m": "5",
            "effective_date_earliest": "", "effective_date_latest": latest,
            "price_status": status, "channel_git_observed": latest,
            "channel_git_locator": "repo@x:f.json", "channel_web_status": "corroborated",
            "channel_web_snapshot": latest, "channel_web_locator": "https://x",
            "date_coherence": "", "notes": ""}


def _event(model, date):
    return {"model_ids": model, "api_effective_date": date}


def test_price_before_the_models_launch_cannot_stay_verified():
    """A corroboration dated before the model existed is not evidence.

    Real case: Channel A returned `corroborated` for gpt-5.6-* at 2026-06-30
    against a registry launch of 2026-07-09.
    """
    from build_price_panel import apply_date_coherence, COHERENCE_EARLY

    rows = [_price_row("gpt-5.6-luna", "2026-06-30")]
    counts = apply_date_coherence(rows, [_event("gpt-5.6-luna", "2026-07-09")])
    assert counts[COHERENCE_EARLY] == 1
    assert rows[0]["date_coherence"] == COHERENCE_EARLY
    assert rows[0]["price_status"] == "conflict", \
        "an impossible corroboration must be demoted, not left reading as clean"
    assert "registry dates this model to 2026-07-09" in rows[0]["notes"]


def test_coherence_uses_the_earliest_registry_date_not_the_last():
    """A model appearing in several events is anchored to its FIRST one.

    Anchoring to the last row makes a price look early whenever the model has a
    later price-cut event — which produced a false positive on first run.
    """
    from build_price_panel import apply_date_coherence, COHERENCE_OK

    rows = [_price_row("o3-2025-04-16", "2025-04-30")]
    events = [_event("o3-2025-04-16", "2025-04-16"),
              _event("o3-2025-04-16", "2025-06-10")]   # later price-cut event
    apply_date_coherence(rows, events)
    assert rows[0]["date_coherence"] == COHERENCE_OK


def test_coherence_leaves_untracked_models_explicit():
    from build_price_panel import apply_date_coherence, COHERENCE_UNKNOWN

    rows = [_price_row("not-in-registry", "2025-01-01")]
    apply_date_coherence(rows, [_event("something-else", "2025-01-01")])
    assert rows[0]["date_coherence"] == COHERENCE_UNKNOWN
