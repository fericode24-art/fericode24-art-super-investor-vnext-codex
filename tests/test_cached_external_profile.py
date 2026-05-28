from __future__ import annotations

from datetime import date

import pandas as pd

from qfas import qfas_runner as runner


def test_cached_insider_score_uses_neutral_when_no_transactions():
    cache = {
        "ABC": {
            "net_value_usd": 0,
            "net_shares": 0,
            "n_transactions": 0,
        }
    }

    assert runner._cached_insider_score("ABC", cache) == 50.0


def test_cached_insider_score_rewards_buying_and_penalizes_selling():
    cache = {
        "BUY": {"net_value_usd": 2_000_000, "n_transactions": 4},
        "SELL": {"net_value_usd": -2_000_000, "n_transactions": 4},
    }

    assert runner._cached_insider_score("BUY", cache) > 50.0
    assert runner._cached_insider_score("SELL", cache) < 50.0


def test_cached_entry_score_is_bounded_and_uses_cached_inputs(monkeypatch):
    monkeypatch.setattr(runner, "_cached_analyst_score", lambda ticker, signal_date: 82.0)
    idx = pd.date_range("2026-05-18", periods=8, freq="B")
    prices = pd.Series([100, 101, 102, 104, 106, 108, 109, 110], index=idx)
    earnings = {"ABC": {"earnings_dates": ["2026-05-20"]}}
    insider = {"ABC": {"net_value_usd": 3_000_000, "n_transactions": 5}}

    res = runner._cached_entry_score(
        ticker="ABC",
        signal_date=date(2026, 5, 27),
        momentum_pct=88.0,
        price_series=prices,
        insider_cache=insider,
        earnings_cache=earnings,
    )

    assert res.analyst_score == 82.0
    assert res.insider_score and res.insider_score > 50.0
    assert abs(res.entry_score_final - 88.0) <= 12.0
    assert res.squeeze_applied is False


def test_cached_market_shadow_reports_diagnostic_delta_only():
    cache = {
        "as_of": "2026-05-27",
        "tickers": {
            "ABC": {
                "congressional_score": 80.0,
                "congressional_trades": 2,
                "congressional_net": 2,
                "short_interest_pct": 30.0,
                "short_interest_raw": 30.0,
            }
        },
    }

    audit = runner._cached_market_shadow(
        ticker="ABC",
        current_entry_score=64.0,
        momentum_pct=70.0,
        analyst_score=60.0,
        insider_score=80.0,
        pead_boost=0.0,
        market_cache=cache,
    )

    assert audit["market_shadow_cached"] is True
    assert audit["congressional_shadow"] == 80.0
    assert audit["squeeze_shadow"] == "bullish"
    assert audit["market_shadow_entry"] > 64.0
    assert audit["market_shadow_delta"] > 0


def test_cached_market_shadow_ignores_missing_cache_rows():
    assert runner._cached_market_shadow(
        ticker="MISS",
        current_entry_score=50.0,
        momentum_pct=50.0,
        analyst_score=None,
        insider_score=None,
        pead_boost=0.0,
        market_cache={"tickers": {}},
    ) == {}
