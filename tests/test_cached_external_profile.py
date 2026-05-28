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
