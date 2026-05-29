from __future__ import annotations

from datetime import date, timedelta

import pytest

from apex.engine import compute_signal


def _obs(values):
    start = date(2026, 1, 7)
    return [
        {"date": start + timedelta(days=7 * i), "BTC": b, "GOLD": g, "SP500": s}
        for i, (b, g, s) in enumerate(values)
    ]


def test_btc_wins_without_sp500_direct_comparison():
    rows = _obs([
        (100, 100, 100),
        (101, 101, 101),
        (102, 102, 102),
        (103, 103, 103),
        (104, 104, 104),
        (105, 105, 105),
        (106, 106, 106),
        (107, 107, 107),
        (110, 105, 160),
    ])
    sig = compute_signal(rows, lookback_weeks=8)
    assert sig.signal == "BTC"


def test_gold_branch_when_btc_fails_and_gold_beats_sp500():
    rows = _obs([
        (100, 100, 100),
        (101, 101, 101),
        (102, 102, 102),
        (103, 103, 103),
        (104, 104, 104),
        (105, 105, 105),
        (106, 106, 106),
        (107, 107, 107),
        (98, 115, 110),
    ])
    sig = compute_signal(rows, lookback_weeks=8)
    assert sig.signal == "GOLD"


def test_sp500_branch_when_btc_fails_and_sp500_beats_gold():
    rows = _obs([
        (100, 100, 100),
        (101, 101, 101),
        (102, 102, 102),
        (103, 103, 103),
        (104, 104, 104),
        (105, 105, 105),
        (106, 106, 106),
        (107, 107, 107),
        (98, 104, 115),
    ])
    sig = compute_signal(rows, lookback_weeks=8)
    assert sig.signal == "SP500"


def test_cash_when_no_positive_asset_qualifies():
    rows = _obs([
        (100, 100, 100),
        (101, 101, 101),
        (102, 102, 102),
        (103, 103, 103),
        (104, 104, 104),
        (105, 105, 105),
        (106, 106, 106),
        (107, 107, 107),
        (98, 99, 99),
    ])
    sig = compute_signal(rows, lookback_weeks=8)
    assert sig.signal == "CASH"


def test_requires_enough_weeks():
    with pytest.raises(ValueError):
        compute_signal(_obs([(100, 100, 100)] * 8), lookback_weeks=8)

