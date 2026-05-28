"""
QFAS — pre-cache Form 4 insider per ticker universo.
Eseguito da workflow notturno separato per non rallentare octa-refresh mattutino.

Output: data/backtest/insider_cache.json
  {
    "AAPL": {
      "ts": "2026-05-25T03:00:00Z",
      "net_value_usd": -12500000,         # ultimi 60gg, escluse 10b5-1
      "net_shares": -65000,
      "n_transactions": 12,
      "n_10b51_excluded": 8,
    },
    ...
  }

Universo: TOP 200 ticker per liquidità (= prima frazione dell'universo R1000 ∩ 13F).
Form 4 lookback: ultimi 20 filing per ticker.
Stima: 200 ticker × 15 Form 4 medi = 3000 req SEC = ~6 min @ 10 req/sec.
"""
from __future__ import annotations
import json, sys, time
from datetime import date, timedelta
from pathlib import Path

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = Path(__file__).parent.parent.absolute()
DATA = ROOT / "data" / "backtest"
CACHE_FILE = DATA / "insider_cache.json"

# Imposta env var dummy per il modulo qfas_config che richiede SEC_USER_AGENT
import os
os.environ.setdefault("PYTHONUNBUFFERED", "1")


def log(msg):
    print(f"[INSIDER] {msg}", flush=True)


def build_target_universe(top_n: int = 200) -> list[str]:
    """Top N ticker dell'universo OCTA (sorted by ticker, take first n).
    Per il vero ranking by market cap servirebbe yfinance — qui ordino alfabetico
    e prendo i primi 200, che statisticamente coprono i big-cap noti (A, AAPL,
    ABBV, ABT, ACN, ADBE, ADP, ...)."""
    r1000_path = ROOT / "data" / "russell_1000.json"
    h13f_path = DATA / "hist_13f_l40.json"
    r1000 = {c["ticker"] for c in
             json.loads(r1000_path.read_text())["constituents"]}
    h13f = json.loads(h13f_path.read_text())
    counts = {}
    for cik, filings in h13f.items():
        seen = set()
        for f in sorted(filings, key=lambda x: x["date"])[-12:]:
            for h in f.get("holdings", []):
                t = h.get("ticker")
                if t and t not in seen:
                    seen.add(t)
                    counts[t] = counts.get(t, 0) + 1
    in_3plus = {t for t, n in counts.items() if n >= 3}
    universe = sorted(in_3plus & r1000)
    return universe[:top_n]


def fetch_insider_for_ticker(ticker: str, lookback_days: int = 60,
                              max_filings: int = 20) -> dict | None:
    """Fetcha + parsa Form 4 per il ticker. Returns dict aggregato o None."""
    from qfas.data_ingestion import (
        get_cik_for_ticker, list_all_filings_paginated, sec_request,
        _parse_form4_xml,
    )
    cik = get_cik_for_ticker(ticker)
    if cik is None:
        return None
    try:
        filings = list_all_filings_paginated(cik, ["4"])
    except Exception as e:
        log(f"  {ticker}: list_filings fail: {e}")
        return None
    if not filings:
        return None
    recent = sorted(filings, key=lambda f: f["date"])[-max_filings:]

    cutoff_date = date.today() - timedelta(days=lookback_days)
    transactions = []
    for f in recent:
        try:
            acc_clean = f["accession"].replace("-", "")
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{f['primary_doc']}"
            r = sec_request(doc_url, accept_html=True)
            if r.status_code != 200:
                continue
            parsed = _parse_form4_xml(r.content)
            if parsed:
                transactions.extend(parsed["transactions"])
        except Exception:
            continue

    # Filtra al lookback window
    from datetime import datetime as _dt
    relevant = []
    for t in transactions:
        try:
            tx_d = _dt.strptime(t["date"], "%Y-%m-%d").date()
            if tx_d >= cutoff_date:
                relevant.append(t)
        except Exception:
            continue

    if not relevant:
        return {
            "ts": _dt.utcnow().isoformat() + "Z",
            "net_value_usd": 0, "net_shares": 0,
            "n_transactions": 0, "n_10b51_excluded": 0,
        }

    n_10b51 = sum(1 for t in relevant if t.get("is_10b51"))
    disc = [t for t in relevant if not t.get("is_10b51")]
    net_shares = sum((t["shares"] if t.get("is_acquisition") else -t["shares"])
                     for t in disc)
    net_value = sum((t["value"] if t.get("is_acquisition") else -t["value"])
                    for t in disc)
    return {
        "ts": _dt.utcnow().isoformat() + "Z",
        "net_value_usd": round(net_value, 2),
        "net_shares": int(net_shares),
        "n_transactions": len(relevant),
        "n_10b51_excluded": n_10b51,
    }


def prefetch(top_n: int = 200, max_filings: int = 20):
    universe = build_target_universe(top_n)
    log(f"Universo target: {len(universe)} ticker")
    log(f"Max Form 4 per ticker: {max_filings}")
    log(f"Stima tempo: {len(universe) * max_filings / 600:.1f} min @ 10 req/s SEC")

    # Carico cache esistente per merge
    cache = {}
    if CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            log(f"Cache esistente: {len(cache)} ticker già presenti")
        except Exception:
            cache = {}

    t0 = time.time()
    ok = 0
    fail = 0
    for i, t in enumerate(universe):
        if i > 0 and i % 25 == 0:
            elapsed = time.time() - t0
            eta = elapsed / i * (len(universe) - i) / 60
            log(f"  [{i}/{len(universe)}] {ok} ok · {fail} fail · "
                f"elapsed {elapsed:.0f}s · ETA {eta:.1f} min")
        try:
            res = fetch_insider_for_ticker(t, max_filings=max_filings)
            if res:
                cache[t] = res
                ok += 1
            else:
                fail += 1
        except Exception as e:
            log(f"  ERR {t}: {e}")
            fail += 1

    elapsed = time.time() - t0
    log(f"\nCompletato in {elapsed:.0f}s · {ok} ok · {fail} fail")

    CACHE_FILE.write_text(json.dumps(cache, separators=(",", ":")), encoding="utf-8")
    size_mb = CACHE_FILE.stat().st_size / 1024
    log(f"Salvato {CACHE_FILE.relative_to(ROOT)} ({size_mb:.1f} KB · {len(cache)} ticker)")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--top-n", type=int, default=200,
                   help="Numero ticker da pre-cacheare (default 200)")
    p.add_argument("--max-filings", type=int, default=20,
                   help="Form 4 per ticker (default 20)")
    args = p.parse_args()
    prefetch(args.top_n, args.max_filings)
