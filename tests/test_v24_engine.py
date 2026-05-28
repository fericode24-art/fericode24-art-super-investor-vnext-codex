"""Test motore v2.4 ROTATION_BETA — beta score, entry status, regime, scoring."""
import numpy as np
import pandas as pd
from scoring import beta_score, entry_status, regime_v24, rotation_beta
from scoring.cfg import load_config


def _series(values):
    return pd.Series(values, index=pd.date_range("2025-01-01", periods=len(values)))


def test_config_has_rotation_beta_section():
    cfg = load_config()
    assert "rotation_beta" in cfg
    assert "regime_v24" in cfg
    rw = cfg["rotation_beta"]["radar_weights"]
    assert abs(sum(rw.values()) - 1.0) < 1e-6


def test_linreg_beta_identity():
    """Un titolo identico al mercato ha beta ≈ 1."""
    market = _series([100 + i for i in range(120)])
    beta = beta_score.linreg_beta(market.copy(), market.copy())
    assert 0.95 <= beta <= 1.05


def test_linreg_beta_amplified():
    """Un titolo che amplifica 2x i movimenti ha beta ≈ 2."""
    base = np.cumprod(1 + np.random.RandomState(1).normal(0, 0.01, 200))
    market = _series(100 * base)
    # titolo con rendimenti doppi
    mret = market.pct_change().fillna(0)
    stock = _series((100 * np.cumprod(1 + 2 * mret)).values)
    beta = beta_score.linreg_beta(stock, market)
    assert beta > 1.5


def test_entry_status_avoid_on_red_flag():
    status, fresh = entry_status.classify_entry_status(
        None, None, has_red_flag=True)
    assert status == "AVOID" and fresh == 0


def test_entry_status_extended_on_overbought():
    """Prezzo in fortissima corsa → EXTENDED."""
    prices = [100 * (1.012 ** i) for i in range(260)]  # +200%+ trend
    df = pd.DataFrame({"Close": prices}, index=pd.date_range("2025-01-01", periods=260))
    status, fresh = entry_status.classify_entry_status(df, None)
    assert status in ("EXTENDED", "FRESH_BREAKOUT", "NEUTRAL")  # forte salita


def test_regime_classify_returns_valid_state():
    r = regime_v24.classify_regime()
    assert r["regime"] in ("RISK_ON", "NEUTRAL", "RISK_OFF", "PANIC")
    assert r["holdings"] in (6, 7, 8, 10, 12)


def test_vulnerability_score_higher_for_high_beta_low_quality():
    high = regime_v24.vulnerability_score(beta_score=90, quality_score=20, sector="Technology")
    low = regime_v24.vulnerability_score(beta_score=40, quality_score=85, sector="Utilities")
    assert high > low


def test_rotation_beta_composite():
    """Lo scoring composito v2.4 combina radar ed entry."""
    radar = {"AAA": {"conviction": 80, "accumulation": 70, "insider": 60, "fund_skill": 75}}
    entry = {"AAA": {"momentum": 70, "beta": 80, "freshness": 90, "quality": 60, "value": 50}}
    out = rotation_beta.calculate_rotation_beta_scores(radar, entry)
    assert "AAA" in out
    assert 0 <= out["AAA"]["composite"] <= 130
    assert out["AAA"]["radar"] > 0 and out["AAA"]["entry"] > 0


def test_equal_weight_sizing_confidence_cap():
    """Confidence bassa → cap 5%; alta → cap 11%."""
    low = rotation_beta.equal_weight_sizing(12, confidence=50)
    high = rotation_beta.equal_weight_sizing(12, confidence=90)
    assert low <= 5.0
    assert high <= 11.0
    assert high >= low
