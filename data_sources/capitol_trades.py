"""
CapitolTrades — acquisti del Congresso USA (modifier minore, max +5).

Tenta l'API non ufficiale dietro capitoltrades.com (bff.capitoltrades.com).
Segnale storicamente rumoroso → in v2.2 pesa pochissimo. Se la fonte è
irraggiungibile (tipico da IP cloud) → degradazione gentile, modifier 0.
"""
from __future__ import annotations

import time
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}
BFF_URL = "https://bff.capitoltrades.com/trades"

_LAST_CALL = 0.0
_MIN_INTERVAL = 0.3


def _throttle():
    global _LAST_CALL
    elapsed = time.time() - _LAST_CALL
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _LAST_CALL = time.time()


def get_congressional_buys(ticker: str, days: int = 45) -> dict:
    """
    Ritorna {politician_count, total_value_usd_estimated, status}.
    Conta solo acquisti (buy). Graceful: status='degraded' se la fonte non risponde.
    """
    result = {"politician_count": 0, "total_value_usd_estimated": 0, "status": "degraded"}
    try:
        _throttle()
        params = {"assetTicker": ticker.upper(), "txType": "buy",
                  "pageSize": 50, "txDate": f"{days}d"}
        r = requests.get(BFF_URL, headers=HEADERS, params=params, timeout=15)
        if r.status_code != 200:
            return result
        data = r.json()
        trades = data.get("data", []) if isinstance(data, dict) else []
        politicians = set()
        total = 0
        for tr in trades:
            pol = tr.get("politician", {})
            pid = pol.get("_stateId") or pol.get("politicianId") or str(pol)
            politicians.add(pid)
            # value è spesso un range string; stima col mid se disponibile
            sz = tr.get("size") or tr.get("value") or 0
            try:
                total += float(sz)
            except (TypeError, ValueError):
                pass
        result = {
            "politician_count": len(politicians),
            "total_value_usd_estimated": int(total),
            "status": "ok",
        }
    except Exception as e:
        result["status"] = f"degraded: {type(e).__name__}"
    return result


def congressional_modifier(ticker: str, days: int = 45) -> tuple[float, dict]:
    """Modifier [0, +5] per il Radar Score. v2.2: ridotto rispetto a v2.1."""
    buys = get_congressional_buys(ticker, days)
    n = buys.get("politician_count", 0)
    if n >= 2:
        return 5.0, buys
    if n == 1:
        return 3.0, buys
    return 0.0, buys


def source_health_check() -> dict:
    res = get_congressional_buys("NVDA", 90)
    return {"status": res["status"], "sample_count": res["politician_count"]}


if __name__ == "__main__":
    import sys, json
    t = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    print(json.dumps(get_congressional_buys(t), indent=2))
