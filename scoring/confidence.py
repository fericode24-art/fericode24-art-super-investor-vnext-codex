"""
Confidence Score (v2.2) — quanto sono AFFIDABILI i dati di un titolo,
indipendente dall'Opportunity Score (quanto è interessante).

Esempio: un fondo nuovo (Aschenbrenner, 1 quarter) → Confidence bassa anche se
l'Opportunity è alta. Berkshire con 25 anni di storia → Confidence alta.

compute_confidence(...) ritorna int 0-100.
"""
from __future__ import annotations

from .cfg import clip


def compute_confidence(
    ticker: str,
    holdings_by_fund: dict,
    momentum: dict,
    xbrl_data: dict | None,
    quote: dict | None,
    red_flags: dict | None = None,
) -> int:
    """
    Confidence 0-100. Penalità per dati mancanti / scarsa copertura.
    """
    confidence = 100

    # --- copertura 13F: quanti fondi e con quanta storia ---
    n_funds = 0
    min_quarters = 99
    for fdata in holdings_by_fund.values():
        cur = fdata.get("current")
        if cur and any(h.get("ticker") == ticker for h in cur.get("holdings", [])):
            n_funds += 1
            min_quarters = min(min_quarters, fdata.get("quarters_available", 0))
    if n_funds < 2:
        confidence -= 20          # poco supporto trasversale
    if min_quarters == 99:
        min_quarters = 0
    if min_quarters < 2:
        confidence -= 15          # skill multiplier inaffidabile

    # --- copertura XBRL ---
    if xbrl_data is None:
        confidence -= 25
    else:
        if xbrl_data.get("years_available", 0) < 4:
            confidence -= 10

    # --- copertura momentum / storia prezzi ---
    m = momentum.get(ticker, {})
    if not m or not m.get("available"):
        confidence -= 25
    elif m.get("ret_12m") is None:
        confidence -= 15          # < 1 anno di storia prezzi (possibile IPO recente)

    # --- copertura analisti ---
    q = quote or {}
    n_analysts = q.get("num_analysts") or 0
    if n_analysts < 5:
        confidence -= 10

    # --- warnings da red flags (no veto ma riducono confidence) ---
    if red_flags and red_flags.get("warnings"):
        confidence -= 5 * len(red_flags["warnings"])

    # --- bonus: tutte le fonti robuste presenti ---
    if (xbrl_data is not None and m and m.get("available")
            and n_funds >= 3 and n_analysts >= 5):
        confidence += 5

    return int(clip(confidence, 0, 100))
