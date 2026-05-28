"""
CFTC COT (Commitments of Traders) — crowdedness del mercato.

Socrata API ufficiale CFTC, gratuita, affidabile.
Se il net long dei Managed Money su E-MINI S&P 500 è sopra il 90° percentile
degli ultimi 2 anni → mercato "affollato" → portafoglio si riduce 12→8.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
import requests

HEADERS = {"User-Agent": "SuperInvestor Federico fedezebi@gmail.com"}
COT_URL = (
    "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
    "?$where=market_and_exchange_names like '%25E-MINI S%26P 500%25'"
    "&$order=report_date_as_yyyy_mm_dd desc&$limit=104"
)
CACHE = Path(__file__).resolve().parent.parent / "data" / "v2_cot_cache.json"


def get_market_crowdedness() -> dict:
    """
    Ritorna {market_crowded: bool, net_long_latest: int, percentile: float, status: str}.
    Graceful: se la fonte non risponde → market_crowded=False, status='degraded'.
    """
    # cache 7 giorni
    if CACHE.exists():
        age = (time.time() - CACHE.stat().st_mtime) / 86400
        if age < 7:
            try:
                with open(CACHE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    try:
        r = requests.get(COT_URL, headers=HEADERS, timeout=25)
        r.raise_for_status()
        rows = r.json()
        # E-MINI S&P 500 è un future finanziario → report TFF, categoria "Leveraged Funds"
        nets = []
        for row in rows:
            try:
                long_lev = float(row.get("lev_money_positions_long", 0) or 0)
                short_lev = float(row.get("lev_money_positions_short", 0) or 0)
                nets.append(long_lev - short_lev)
            except Exception:
                continue
        if not nets:
            raise ValueError("no COT data parsed")
        latest = nets[0]
        srt = sorted(nets)
        # percentile del valore latest dentro la distribuzione 2 anni
        rank = sum(1 for x in srt if x <= latest)
        percentile = rank / len(srt)
        result = {
            "market_crowded": percentile >= 0.90,
            "net_long_latest": int(latest),
            "percentile": round(percentile, 3),
            "status": "ok",
        }
    except Exception as e:
        result = {"market_crowded": False, "net_long_latest": None,
                  "percentile": None, "status": f"degraded: {e}"}

    try:
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(result, f)
    except Exception:
        pass
    return result


if __name__ == "__main__":
    print(json.dumps(get_market_crowdedness(), indent=2))
