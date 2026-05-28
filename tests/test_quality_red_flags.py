"""Test Quality Red Flags — veto qualitativo specifico."""
from scoring import quality_red_flags


def test_no_veto_when_xbrl_missing():
    """XBRL assente → niente veto, solo warning."""
    rf = quality_red_flags.check_quality_red_flags("X", None)
    assert rf["has_hard_veto"] is False
    assert "xbrl_data_unavailable" in rf["warnings"]


def test_veto_on_fcf_chronically_negative():
    """FCF negativo per 2 anni consecutivi → veto."""
    xbrl = {"fcf_negative_years": 2, "shares_outstanding": 100, "shares_outstanding_12m_ago": 100}
    rf = quality_red_flags.check_quality_red_flags("X", xbrl)
    assert rf["has_hard_veto"] is True
    assert any("fcf_negative" in r for r in rf["reasons"])


def test_veto_on_excessive_dilution():
    """Diluizione azioni > 10% in 12 mesi → veto."""
    xbrl = {"fcf_negative_years": 0,
            "shares_outstanding": 130, "shares_outstanding_12m_ago": 100}
    rf = quality_red_flags.check_quality_red_flags("X", xbrl)
    assert rf["has_hard_veto"] is True
    assert any("dilution" in r for r in rf["reasons"])


def test_veto_on_revenue_collapse():
    """Revenue YoY < -20% → veto."""
    xbrl = {"fcf_negative_years": 0, "shares_outstanding": 100,
            "shares_outstanding_12m_ago": 100, "revenue_growth_yoy": -0.35}
    rf = quality_red_flags.check_quality_red_flags("X", xbrl)
    assert rf["has_hard_veto"] is True


def test_veto_on_excessive_leverage():
    """Debt/EBITDA > 6x → veto."""
    xbrl = {"fcf_negative_years": 0, "shares_outstanding": 100,
            "shares_outstanding_12m_ago": 100, "debt_to_ebitda": 8.5}
    rf = quality_red_flags.check_quality_red_flags("X", xbrl)
    assert rf["has_hard_veto"] is True


def test_healthy_company_no_veto():
    """Azienda sana → nessun veto."""
    xbrl = {"fcf_negative_years": 0, "shares_outstanding": 101,
            "shares_outstanding_12m_ago": 100, "revenue_growth_yoy": 0.08,
            "debt_to_ebitda": 1.5, "roe_trend_4y": "rising", "interest_coverage": 12}
    rf = quality_red_flags.check_quality_red_flags("X", xbrl)
    assert rf["has_hard_veto"] is False
