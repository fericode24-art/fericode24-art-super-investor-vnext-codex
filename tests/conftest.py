"""Fixture condivise per la test suite v2.2."""
import sys
from pathlib import Path

# rende importabili i package del progetto
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


@pytest.fixture
def funds():
    """3 fondi di test di tipo diverso."""
    return [
        {"cik": "0000000001", "name": "Legend Fund", "type": "value_legend", "base_weight": 1.0},
        {"cik": "0000000002", "name": "Picker Fund", "type": "concentrated_picker", "base_weight": 0.8},
        {"cik": "0000000003", "name": "New Fund", "type": "tiger_cub", "base_weight": 0.7},
    ]


def _holding(ticker, shares, pct):
    return {"ticker": ticker, "shares": shares, "value_usd": shares * 10,
            "pct_of_portfolio": pct, "cusip": ticker + "000", "issuer": ticker}


@pytest.fixture
def holdings_by_fund():
    """
    holdings_by_fund di test:
      - AAA: tenuto da fondo 1 e 2 come high conviction, in accumulo
      - BBB: tenuto da fondo 1 e 3, posizione stabile
      - CCC: tenuto solo dal fondo 1 (sotto soglia 2 high-conv)
    """
    return {
        "0000000001": {
            "current": {"date": "2026-03-31", "cik": "0000000001", "holdings": [
                _holding("AAA", 2000, 8.0), _holding("BBB", 1000, 5.0), _holding("CCC", 500, 4.0)]},
            "previous": {"date": "2025-12-31", "cik": "0000000001", "holdings": [
                _holding("AAA", 1000, 5.0), _holding("BBB", 1000, 5.0)]},
            "quarters_available": 2,
        },
        "0000000002": {
            "current": {"date": "2026-03-31", "cik": "0000000002", "holdings": [
                _holding("AAA", 3000, 12.0)]},
            "previous": {"date": "2025-12-31", "cik": "0000000002", "holdings": [
                _holding("AAA", 2000, 9.0)]},
            "quarters_available": 2,
        },
        "0000000003": {
            "current": {"date": "2026-03-31", "cik": "0000000003", "holdings": [
                _holding("BBB", 800, 6.0)]},
            "previous": None,                 # fondo nuovo: 1 solo quarter
            "quarters_available": 1,
        },
    }


@pytest.fixture
def momentum():
    return {
        "AAA": {"available": True, "ret_1m": 5, "ret_3m": 25, "ret_6m": 40, "ret_12m": 60,
                "rsi_14": 58, "ma50": 90, "ma200": 80, "above_ma50": True, "above_ma200": True,
                "price": 100, "volume_ratio_recent_vs_prior": 1.4, "gap_recent_pct": 0.02,
                "days_since_gap": 30},
        "BBB": {"available": True, "ret_1m": 1, "ret_3m": 4, "ret_6m": 8, "ret_12m": 12,
                "rsi_14": 50, "ma50": 49, "ma200": 48, "above_ma50": True, "above_ma200": True,
                "price": 50, "volume_ratio_recent_vs_prior": 1.0, "gap_recent_pct": 0.0,
                "days_since_gap": None},
    }
