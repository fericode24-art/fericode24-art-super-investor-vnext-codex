"""Test v2.3 — modifier attivista SC 13D/13G + regime macro FRED."""
from scoring.cfg import load_config
from scoring import stage1_radar


def test_config_has_activist_modifiers():
    """config.yaml deve esporre i pesi del modifier attivista."""
    mods = load_config()["scoring"]["stage1_modifiers"]
    assert mods["activist_13d"] > mods["activist_13g"] > 0


def test_config_has_macro_section():
    """config.yaml deve avere la sezione macro per FRED."""
    macro = load_config()["macro"]
    assert "hy_spread_series" in macro
    assert macro["hy_spread_risk_threshold"] > 0


def test_radar_applies_activist_modifier(holdings_by_fund, funds):
    """Il modifier attivista deve alzare il radar score del titolo."""
    insider = {"AAA": 40.0}
    base = stage1_radar.calculate_radar_scores(holdings_by_fund, funds, insider)
    with_act = stage1_radar.calculate_radar_scores(
        holdings_by_fund, funds, insider, {"AAA": {"activist": 10.0}})
    assert with_act["AAA"]["radar"] > base["AAA"]["radar"]
    assert with_act["AAA"]["activist_mod"] == 10.0


def test_radar_modifiers_independent(holdings_by_fund, funds):
    """short, congress e activist si sommano indipendentemente."""
    insider = {"AAA": 40.0}
    mods = {"AAA": {"short": 15.0, "congress": 5.0, "activist": 10.0}}
    r = stage1_radar.calculate_radar_scores(holdings_by_fund, funds, insider, mods)
    assert r["AAA"]["short_mod"] == 15.0
    assert r["AAA"]["congress_mod"] == 5.0
    assert r["AAA"]["activist_mod"] == 10.0
