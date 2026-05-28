"""
v2.4 — Regime macro a 4 stati (modalità ROTATION_BETA).

RISK_ON / NEUTRAL / RISK_OFF / PANIC da VIX + yield curve + HY spread (FRED).
Determina numero di holdings e % cash. In PANIC, il Vulnerability Score
ordina quali titoli vendere per primi.
"""
from __future__ import annotations

from .cfg import load_config, clip
from data_sources import fred_macro

# vulnerabilità settoriale grezza: settori ciclici/growth crollano di più in panic
SECTOR_VULNERABILITY = {
    "Technology": 85, "Consumer Cyclical": 80, "Communication Services": 70,
    "Financial Services": 65, "Industrials": 60, "Energy": 60,
    "Basic Materials": 55, "Real Estate": 55, "Healthcare": 40,
    "Consumer Defensive": 25, "Utilities": 20,
}


def classify_regime() -> dict:
    """
    Ritorna {regime, vix, yield_curve, hy_spread, holdings, cash_pct, status}.
    Graceful: se FRED non risponde su tutto → NEUTRAL.
    """
    cfg = load_config()
    rc = cfg["regime_v24"]
    macro = fred_macro.get_macro_regime()          # hy_spread + yield_curve
    vix = fred_macro._latest_value(rc["vix_series"])
    hy = macro.get("hy_spread")
    curve = macro.get("yield_curve_2_10")

    regime = "NEUTRAL"
    if vix is not None or hy is not None:
        panic = (vix is not None and vix > rc["panic_vix"]) or \
                (curve is not None and curve < -0.5 and hy is not None and hy > rc["panic_hy_spread"])
        risk_off = (vix is not None and vix > rc["risk_off_vix"]) or \
                   (curve is not None and curve < 0) or \
                   (hy is not None and hy > 5.0)
        risk_on = (vix is not None and vix < rc["risk_on_vix"]) and \
                  (curve is not None and curve > 0.5) and \
                  (hy is not None and hy < 3.5)
        if panic:
            regime = "PANIC"
        elif risk_off:
            regime = "RISK_OFF"
        elif risk_on:
            regime = "RISK_ON"

    alloc = rc["allocation"][regime]
    return {
        "regime": regime,
        "vix": round(vix, 2) if vix is not None else None,
        "yield_curve": curve,
        "hy_spread": hy,
        "holdings": alloc["holdings"],
        "cash_pct": alloc["cash_pct"],
        "status": macro.get("status", "ok"),
    }


def vulnerability_score(beta_score: float, quality_score: float, sector: str) -> float:
    """
    Quanto un titolo è vulnerabile in caso di PANIC (0-100, più alto = vendi prima).
    Combinazione di beta, fragilità di bilancio e vulnerabilità settoriale.
    """
    sector_vuln = SECTOR_VULNERABILITY.get(sector, 60)
    score = (0.40 * (beta_score or 50)
             + 0.40 * (100 - (quality_score or 50))
             + 0.20 * sector_vuln)
    return round(clip(score, 0, 100), 1)
