"""Test Confidence Score — affidabilità dati separata dall'Opportunity."""
from scoring import confidence


def test_high_confidence_full_coverage(holdings_by_fund, momentum):
    """Titolo con XBRL, momentum, 3+ fondi, analisti → confidence alta."""
    xbrl = {"years_available": 20}
    quote = {"num_analysts": 25}
    # AAA è tenuto da 2 fondi nel fixture; aggiungiamo copertura piena
    c = confidence.compute_confidence("AAA", holdings_by_fund, momentum, xbrl, quote)
    assert c >= 60


def test_low_confidence_new_fund_no_xbrl(holdings_by_fund, momentum):
    """Titolo senza XBRL e con storia 13F corta → confidence bassa."""
    c = confidence.compute_confidence("BBB", holdings_by_fund, momentum,
                                      None, {"num_analysts": 1})
    assert c < 70


def test_confidence_in_range(holdings_by_fund, momentum):
    """Confidence sempre in [0, 100]."""
    c = confidence.compute_confidence("AAA", holdings_by_fund, momentum, None, None)
    assert 0 <= c <= 100


def test_xbrl_absence_penalizes(holdings_by_fund, momentum):
    """A parità di tutto, l'assenza di XBRL deve abbassare la confidence."""
    quote = {"num_analysts": 25}
    with_xbrl = confidence.compute_confidence("AAA", holdings_by_fund, momentum,
                                              {"years_available": 20}, quote)
    without = confidence.compute_confidence("AAA", holdings_by_fund, momentum, None, quote)
    assert with_xbrl > without
