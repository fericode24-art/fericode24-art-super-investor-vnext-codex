"""
OpenInsider — transazioni insider dettagliate (per Insider Quality Score).

openinsider.com aggrega i Form 4 SEC in tabelle leggibili. Nessuna API ufficiale
→ scraping HTML. FRAGILE: da IP cloud (GitHub Actions) può essere bloccato.
Tutte le funzioni degradano con grazia: ritornano [] in caso di errore.

get_insider_transactions(ticker, days) ritorna lista di dict dettagliati,
input per scoring/insider_quality.py.
"""
from __future__ import annotations

import time
import re
from typing import Optional
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}
# screener filtrato per ticker; il filtro tipo transazione lo facciamo noi
SCREENER_URL = "http://openinsider.com/screener?s={ticker}&cnt=100"

_LAST_CALL = 0.0
_MIN_INTERVAL = 0.4


def _throttle():
    global _LAST_CALL
    elapsed = time.time() - _LAST_CALL
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _LAST_CALL = time.time()


def _parse_money(txt: str) -> float:
    """'+$1,234,567' -> 1234567.0 ; '-$1,000' -> -1000.0"""
    if not txt:
        return 0.0
    neg = "-" in txt
    digits = re.sub(r"[^0-9.]", "", txt)
    if not digits:
        return 0.0
    try:
        v = float(digits)
        return -v if neg else v
    except ValueError:
        return 0.0


def _parse_int(txt: str) -> int:
    digits = re.sub(r"[^0-9]", "", txt or "")
    return int(digits) if digits else 0


def get_insider_transactions(ticker: str, days: int = 90) -> list[dict]:
    """
    Ritorna lista transazioni insider recenti per il ticker.
    Ogni dict: filing_date, trade_date, insider_name, title, transaction_type,
               price, quantity, value_usd, shares_held_after.
    Lista vuota = nessun dato o fonte degradata (graceful).
    """
    try:
        _throttle()
        r = requests.get(SCREENER_URL.format(ticker=ticker.upper()),
                          headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "lxml")
        table = soup.find("table", class_="tinytable")
        if not table:
            return []
        tbody = table.find("tbody") or table
        out = []
        for tr in tbody.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 12:
                continue
            txt = [c.get_text(strip=True) for c in cells]
            # layout screener per-ticker:
            # 0=X 1=FilingDate 2=TradeDate 3=Ticker 4=Insider 5=Title
            # 6=TradeType 7=Price 8=Qty 9=Owned 10=dOwn 11=Value
            ttype = txt[6].replace(" - ", "-").replace(" ", "")
            out.append({
                "filing_date": txt[1],
                "trade_date": txt[2],
                "insider_name": txt[4],
                "title": txt[5],
                "transaction_type": ttype,       # es. "P-Purchase", "S-Sale"
                "price": _parse_money(txt[7]),
                "quantity": _parse_int(txt[8]),
                "shares_held_after": _parse_int(txt[9]),
                "value_usd": abs(_parse_money(txt[11])),
            })
        return out
    except Exception:
        return []


def batch_insider(tickers: list[str], days: int = 90) -> dict:
    """Transazioni insider per una lista di ticker. {ticker: [transazioni]}."""
    out = {}
    degraded = 0
    for t in tickers:
        txns = get_insider_transactions(t, days)
        out[t] = txns
    return out


def source_health_check() -> dict:
    """Test rapido: la fonte risponde? Usato per diagnosticare blocco da cloud."""
    txns = get_insider_transactions("AAPL", 365)
    return {"reachable": True if txns is not None else False,
            "sample_count": len(txns),
            "status": "ok" if txns else "no_data_or_blocked"}


if __name__ == "__main__":
    import sys, json
    t = sys.argv[1] if len(sys.argv) > 1 else "OXY"
    txns = get_insider_transactions(t)
    print(f"{t}: {len(txns)} transazioni")
    print(json.dumps(txns[:5], indent=2))
