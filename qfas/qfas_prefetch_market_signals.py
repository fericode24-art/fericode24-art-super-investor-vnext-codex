"""
Prefetch shadow market signals for OCTA.

Output: data/backtest/market_signal_cache.json

This cache is diagnostic by design: congressional and squeeze are measured in
shadow mode first, then activated only if the comparison report shows value.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent.parent.absolute()
DATA = ROOT / "data" / "backtest"
CACHE_FILE = DATA / "market_signal_cache.json"


def log(msg: str) -> None:
    print(f"[MARKET-SHADOW] {msg}", flush=True)


def _dashboard_tickers(top_n: int) -> list[str]:
    path = ROOT / "dashboard" / "data-octa.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    tickers: list[str] = []
    for key in ("signals", "candidates"):
        for row in data.get(key, []) or []:
            ticker = str(row.get("ticker") or "").upper()
            if ticker and ticker not in tickers:
                tickers.append(ticker)
            if len(tickers) >= top_n:
                return tickers
    return tickers


def _fallback_universe(top_n: int) -> list[str]:
    r1000_path = ROOT / "data" / "russell_1000.json"
    h13f_path = DATA / "hist_13f_l40.json"
    r1000 = {c["ticker"] for c in json.loads(r1000_path.read_text())["constituents"]}
    h13f = json.loads(h13f_path.read_text())
    counts: dict[str, int] = {}
    for filings in h13f.values():
        seen = set()
        for filing in sorted(filings, key=lambda x: x["date"])[-12:]:
            for holding in filing.get("holdings", []):
                ticker = holding.get("ticker")
                if ticker and ticker not in seen:
                    seen.add(ticker)
                    counts[ticker] = counts.get(ticker, 0) + 1
    return sorted({ticker for ticker, n in counts.items() if n >= 3} & r1000)[:top_n]


def build_target_universe(top_n: int) -> list[str]:
    tickers = _dashboard_tickers(top_n)
    if len(tickers) >= min(20, top_n):
        return tickers[:top_n]
    return _fallback_universe(top_n)


def _congressional_summary(ticker: str, as_of: date, lookback_days: int) -> dict:
    from qfas.data_ingestion import fetch_congressional_trades_for_ticker

    since = as_of - timedelta(days=lookback_days)
    trades = fetch_congressional_trades_for_ticker(ticker, since)
    buys = sum(1 for row in trades if row.get("transaction_type") == "buy")
    sells = sum(1 for row in trades if row.get("transaction_type") == "sell")
    net = buys - sells
    if net <= 0:
        score = 0.0
    elif net == 1:
        score = 60.0
    elif net <= 3:
        score = 80.0
    else:
        score = 100.0
    return {
        "congressional_score": score,
        "congressional_trades": len(trades),
        "congressional_buys": buys,
        "congressional_sells": sells,
        "congressional_net": net,
    }


def _short_interest_summary(ticker: str, as_of: date) -> dict:
    from qfas.data_ingestion import fetch_short_interest_finra

    raw = fetch_short_interest_finra(ticker, as_of)
    if raw is None:
        return {"short_interest_pct": None, "short_interest_raw": None, "short_interest_state": "missing"}
    # FINRA raw files can expose shares instead of percentage depending on schema.
    # Only allow it to influence shadow squeeze when it is plausibly a percent.
    if 0.0 <= float(raw) <= 100.0:
        return {"short_interest_pct": float(raw), "short_interest_raw": float(raw), "short_interest_state": "pct"}
    return {"short_interest_pct": None, "short_interest_raw": float(raw), "short_interest_state": "raw_not_pct"}


def prefetch(top_n: int = 80, lookback_days: int = 90, include_short: bool = True) -> dict:
    as_of = date.today()
    universe = build_target_universe(top_n)
    log(f"Universo target: {len(universe)} ticker")
    cache = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "as_of": as_of.isoformat(),
        "lookback_days": lookback_days,
        "source": "capitoltrades+finra",
        "tickers": {},
    }
    t0 = time.time()
    for i, ticker in enumerate(universe, start=1):
        if i == 1 or i % 10 == 0:
            log(f"  [{i}/{len(universe)}] {ticker}")
        row: dict = {}
        try:
            row.update(_congressional_summary(ticker, as_of, lookback_days))
        except Exception as exc:
            row.update({
                "congressional_score": None,
                "congressional_error": str(exc),
            })
        if include_short:
            try:
                row.update(_short_interest_summary(ticker, as_of))
            except Exception as exc:
                row.update({
                    "short_interest_pct": None,
                    "short_interest_raw": None,
                    "short_interest_state": "error",
                    "short_interest_error": str(exc),
                })
        else:
            row.update({
                "short_interest_pct": None,
                "short_interest_raw": None,
                "short_interest_state": "skipped",
            })
        cache["tickers"][ticker] = row
    DATA.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, separators=(",", ":"), default=str), encoding="utf-8")
    log(f"Salvato {CACHE_FILE.relative_to(ROOT)} in {time.time() - t0:.0f}s")
    return cache


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--top-n", type=int, default=80)
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--skip-short", action="store_true")
    args = parser.parse_args()
    prefetch(args.top_n, args.lookback_days, include_short=not args.skip_short)
