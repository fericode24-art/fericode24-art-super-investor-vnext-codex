"""Test Stage 2 — entry score, filtri 'treno partito' rafforzati, entry status."""
from scoring import stage2_entry


def test_quality_raw_higher_for_better_fundamentals():
    """ROE/margini più alti → quality raw più alto."""
    good = stage2_entry._quality_raw(roe=0.30, roa=0.15, gm=0.50, om=0.30, de=40)
    poor = stage2_entry._quality_raw(roe=0.02, roa=0.01, gm=0.10, om=0.03, de=300)
    assert good > poor


def test_entry_multiplier_treno_partito_aggressivo():
    """ret_1m >35% e RSI>72 → multiplier pesante (score crolla)."""
    quote = {"price": 100}
    hot = {"ret_1m": 50, "ret_3m": 30, "ret_6m": 40, "rsi_14": 80,
           "price": 100, "ma50": 80, "ma200": 70}
    score, notes = stage2_entry.apply_entry_multipliers("X", 100.0, quote, hot)
    assert score < 40             # fortemente penalizzato
    assert "treno_partito_aggr" in notes


def test_entry_multiplier_ret6m_extended():
    """ret_6m > 80% deve attivare la penalità v2.2."""
    quote = {"price": 100}
    mom = {"ret_1m": 5, "ret_3m": 10, "ret_6m": 95, "rsi_14": 55,
           "price": 100, "ma50": 95, "ma200": 90}
    score, notes = stage2_entry.apply_entry_multipliers("X", 100.0, quote, mom)
    assert "ret6m_extended" in notes


def test_entry_multiplier_far_from_ma200():
    """Prezzo >30% sopra MA200 → penalità."""
    quote = {"price": 100}
    mom = {"ret_1m": 3, "ret_3m": 8, "ret_6m": 15, "rsi_14": 55,
           "price": 140, "ma50": 120, "ma200": 100}
    score, notes = stage2_entry.apply_entry_multipliers("X", 100.0, quote, mom)
    assert "far_from_ma200" in notes


def test_classify_entry_status():
    """Le etichette di entry status devono riflettere la situazione tecnica."""
    fresh = stage2_entry.classify_entry_status(
        {"price": 100}, {"price": 100, "ma50": 90, "ma200": 80, "rsi_14": 55,
                          "ret_3m": 10, "ret_6m": 20})
    extended = stage2_entry.classify_entry_status(
        {"price": 100}, {"price": 100, "ma50": 90, "ma200": 80, "rsi_14": 55,
                         "ret_3m": 55, "ret_6m": 90})
    assert fresh.startswith("Fresh")
    assert extended.startswith("Extended")
