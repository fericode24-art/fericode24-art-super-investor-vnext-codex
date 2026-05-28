"""
Quality Red Flags (v2.2) — veto qualitativo basato su segnali specifici,
non su una soglia numerica generica.

check_quality_red_flags(xbrl_data) ritorna:
  {has_hard_veto: bool, reasons: [str], warnings: [str]}

Se XBRL non è disponibile → nessun veto (solo warning, penalità su Confidence).
Red flag = esclusione dura dal portafoglio. Warning = solo riduzione confidence.
"""
from __future__ import annotations

from .cfg import load_config


def check_quality_red_flags(ticker: str, xbrl_data: dict | None) -> dict:
    """Veto qualitativo. xbrl_data da data_sources/edgar_xbrl.get_fundamentals."""
    cfg = load_config()["quality_red_flags"]
    flags = {"has_hard_veto": False, "reasons": [], "warnings": []}

    if xbrl_data is None:
        # dati insufficienti → niente veto, solo penalità confidence
        flags["warnings"].append("xbrl_data_unavailable")
        return flags

    # RED FLAG 1 — Going concern warning
    if xbrl_data.get("going_concern_flag"):
        flags["has_hard_veto"] = True
        flags["reasons"].append("going_concern_warning")

    # RED FLAG 2 — FCF cronicamente negativo
    # approssimazione documentata: 'N anni fiscali negativi' invece di '4 quarter'
    # (i cash-flow XBRL nei 10-Q sono YTD cumulativi e non affidabili come quarterly)
    fcf_neg = xbrl_data.get("fcf_negative_years", 0)
    if fcf_neg >= 2:
        flags["has_hard_veto"] = True
        flags["reasons"].append(f"fcf_negative_{fcf_neg}y_consecutive")

    # RED FLAG 3 — Diluizione azionaria > soglia in 12 mesi
    sn = xbrl_data.get("shares_outstanding")
    so = xbrl_data.get("shares_outstanding_12m_ago")
    if sn and so and so > 0:
        dilution = (sn - so) / so
        if dilution > cfg["share_dilution_max_pct"]:
            flags["has_hard_veto"] = True
            flags["reasons"].append(f"share_dilution_{dilution*100:.0f}pct")

    # RED FLAG 4 — Revenue collapse YoY
    rev_yoy = xbrl_data.get("revenue_growth_yoy")
    if rev_yoy is not None and rev_yoy < cfg["revenue_collapse_yoy_min"]:
        flags["has_hard_veto"] = True
        flags["reasons"].append(f"revenue_collapse_{rev_yoy*100:.0f}pct")

    # RED FLAG 5 — Leva eccessiva
    de = xbrl_data.get("debt_to_ebitda")
    if de is not None and de > cfg["debt_ebitda_max"]:
        flags["has_hard_veto"] = True
        flags["reasons"].append(f"excessive_leverage_{de:.1f}x")

    # WARNINGS (no veto)
    if xbrl_data.get("roe_trend_4y") == "declining":
        flags["warnings"].append("roe_declining")
    ic = xbrl_data.get("interest_coverage")
    if ic is not None and ic < 2.0:
        flags["warnings"].append("low_interest_coverage")

    return flags
