"""
Short Interest — modifier al Radar Score.

DEVIAZIONE DALLA SPEC (documentata): la spec indicava scraping FINRA.
Usiamo invece i campi short di Yahoo Finance (shortPercentOfFloat, shortRatio,
sharesShort, sharesShortPriorMonth): è lo STESSO dato sottostante pubblicato da
FINRA/exchange, ma già strutturato, affidabile e a costo zero di richieste extra
(le quote Yahoo le scarichiamo comunque). Niente scraper fragile.

Modifier (applicato al Radar Score, vedi stage1_radar):
  +15  se short_pct > 8%  AND conviction > 70   (squeeze candidate)
  -15  se short_pct > 15% AND quality < 50      (deterioramento)
"""
from __future__ import annotations


def get_short_data(quote: dict) -> dict:
    """Estrae i dati short da una quote Yahoo già scaricata."""
    if not quote or quote.get("error"):
        return {"short_pct": None, "days_to_cover": None,
                "change_vs_prev": None, "status": "unavailable"}
    spf = quote.get("short_pct_float")
    short_pct = (spf * 100) if spf is not None else None
    shares_short = quote.get("shares_short")
    shares_prior = quote.get("shares_short_prior")
    change = None
    if shares_short and shares_prior and shares_prior > 0:
        change = (shares_short - shares_prior) / shares_prior
    return {
        "short_pct": short_pct,
        "days_to_cover": quote.get("short_ratio"),
        "change_vs_prev": change,
        "status": "ok" if short_pct is not None else "unavailable",
    }


def short_modifier(quote: dict, conviction: float, quality: float) -> float:
    """
    Modifier [-15, +15] per il Radar Score.
    Doppiamente condizionale: serve sia il livello di short sia la condizione
    conviction/quality, così non distorce titoli normali.
    """
    sd = get_short_data(quote)
    sp = sd.get("short_pct")
    if sp is None:
        return 0.0
    if sp > 8 and conviction > 70:
        return 15.0   # short squeeze candidate
    if sp > 15 and quality < 50:
        return -15.0  # short alto su titolo debole
    return 0.0
