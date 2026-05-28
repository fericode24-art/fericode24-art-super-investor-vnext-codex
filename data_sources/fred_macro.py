"""
FRED (Federal Reserve Economic Data) — regime macro.

Endpoint CSV keyless: https://fred.stlouisfed.org/graph/fredgraph.csv?id=SERIE
Nessuna API key richiesta. Fonte ufficiale Federal Reserve di St. Louis.

Indica un regime "risk-off" quando lo spread High Yield si allarga oltre soglia
(stress creditizio) → il pipeline riduce il portafoglio 12 → 8 (difensivo).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
import requests

from scoring.cfg import load_config

HEADERS = {"User-Agent": "SuperInvestor Federico fedezebi@gmail.com"}
CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
CACHE = Path(__file__).resolve().parent.parent / "data" / "v2_macro_cache.json"


def _latest_value(series: str):
    """Ultimo valore numerico di una serie FRED (ignora i '.' = dati mancanti)."""
    try:
        r = requests.get(CSV_URL.format(series=series), headers=HEADERS, timeout=20)
        r.raise_for_status()
        lines = [l for l in r.text.strip().splitlines() if l]
        for line in reversed(lines[1:]):       # salta header
            parts = line.split(",")
            if len(parts) >= 2 and parts[-1].strip() not in (".", ""):
                try:
                    return float(parts[-1])
                except ValueError:
                    continue
        return None
    except Exception:
        return None


def get_macro_regime() -> dict:
    """
    Ritorna {risk_off, hy_spread, yield_curve_2_10, status}.
    Graceful: se FRED non risponde → risk_off=False, status='degraded'.
    """
    cfg = load_config()["macro"]
    ttl = load_config()["cache_ttl_days"]["macro_fred"]

    if CACHE.exists():
        age = (time.time() - CACHE.stat().st_mtime) / 86400
        if age < ttl:
            try:
                with open(CACHE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    hy = _latest_value(cfg["hy_spread_series"])
    curve = _latest_value(cfg["yield_curve_series"])

    if hy is None:
        result = {"risk_off": False, "hy_spread": None, "yield_curve_2_10": curve,
                  "status": "degraded"}
    else:
        risk_off = hy > cfg["hy_spread_risk_threshold"]
        result = {
            "risk_off": risk_off,
            "hy_spread": round(hy, 2),
            "yield_curve_2_10": round(curve, 2) if curve is not None else None,
            "status": "ok",
        }

    try:
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(result, f)
    except Exception:
        pass
    return result


if __name__ == "__main__":
    print(json.dumps(get_macro_regime(), indent=2))
