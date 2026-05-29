from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, Tuple
from urllib.parse import quote

import pandas as pd
import requests


YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"


def fetch_chart(ticker: str, interval: str = "1d", range_: str = "max", timeout: int = 25) -> tuple[pd.DataFrame, Dict]:
    url = YAHOO_CHART.format(ticker=quote(ticker, safe=""))
    params = {"interval": interval, "includePrePost": "false"}
    # Yahoo often down-samples range=max daily charts to monthly bars. Explicit
    # period bounds keeps true daily bars for backtests.
    if interval == "1d" and range_ == "max":
        period1 = int(datetime(1980, 1, 1, tzinfo=timezone.utc).timestamp())
        period2 = int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp())
        params.update({"period1": period1, "period2": period2})
    else:
        params["range"] = range_
    r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    payload = r.json()
    result = (payload.get("chart", {}).get("result") or [None])[0]
    if not result:
        err = payload.get("chart", {}).get("error")
        raise RuntimeError(f"Yahoo returned no result for {ticker}: {err}")
    ts = result.get("timestamp") or []
    quote_data = (result.get("indicators", {}).get("quote") or [{}])[0]
    meta = result.get("meta") or {}
    if not ts:
        raise RuntimeError(f"Yahoo returned no timestamps for {ticker}")
    df = pd.DataFrame({
        "open": quote_data.get("open"),
        "high": quote_data.get("high"),
        "low": quote_data.get("low"),
        "close": quote_data.get("close"),
        "volume": quote_data.get("volume"),
    }, index=pd.to_datetime(ts, unit="s", utc=True))
    gmtoffset = int(meta.get("gmtoffset") or 0)
    df.index = (df.index + pd.to_timedelta(gmtoffset, unit="s")).tz_localize(None)
    df = df.dropna(subset=["close"])
    return df, meta


def _cache_path(cache_dir: Path, ticker: str, interval: str, range_: str) -> Path:
    safe = ticker.replace("^", "_").replace("=", "_").replace(".", "_").replace("/", "_")
    if interval == "1d" and range_ == "max":
        range_ = "max_daily"
    return cache_dir / f"{safe}_{interval}_{range_}.json"


def fetch_chart_cached(
    ticker: str,
    interval: str,
    range_: str,
    cache_dir: Path,
    max_age_hours: float = 12.0,
) -> tuple[pd.DataFrame, Dict]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache_dir, ticker, interval, range_)
    if path.exists() and (time.time() - path.stat().st_mtime) < max_age_hours * 3600:
        raw = json.loads(path.read_text(encoding="utf-8"))
        df = pd.DataFrame(raw["rows"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        return df, raw.get("meta", {})
    df, meta = fetch_chart(ticker, interval=interval, range_=range_)
    rows = df.reset_index(names="date").copy()
    rows["date"] = rows["date"].astype(str)
    path.write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "ticker": ticker,
        "interval": interval,
        "range": range_,
        "meta": meta,
        "rows": rows.to_dict(orient="records"),
    }, separators=(",", ":"), default=str), encoding="utf-8")
    return df, meta


def build_proxy_prices(cache_dir: Path, price_col: str = "close", range_: str = "max") -> pd.DataFrame:
    """Build long EUR proxy series from Yahoo public data.

    BTC, gold and S&P 500 are USD series converted with EURUSD. XEON is used as
    real EUR cash proxy when available.
    """
    raw: Dict[str, pd.DataFrame] = {}
    meta: Dict[str, Dict] = {}
    for ticker in ("BTC-USD", "GC=F", "^GSPC", "EURUSD=X", "XEON.MI"):
        raw[ticker], meta[ticker] = fetch_chart_cached(ticker, "1d", range_, cache_dir, max_age_hours=24)

    idx = raw["BTC-USD"].index
    for ticker in ("GC=F", "^GSPC", "EURUSD=X"):
        idx = idx.union(raw[ticker].index)
    aligned = pd.DataFrame(index=idx.sort_values())
    for ticker, name in (("BTC-USD", "BTC"), ("GC=F", "GOLD"), ("^GSPC", "SP500")):
        aligned[name] = raw[ticker][price_col]
    aligned["EURUSD"] = raw["EURUSD=X"][price_col]
    aligned[["BTC", "GOLD", "SP500", "EURUSD"]] = aligned[["BTC", "GOLD", "SP500", "EURUSD"]].ffill(limit=3)
    for col in ("BTC", "GOLD", "SP500"):
        aligned[col] = aligned[col] / aligned["EURUSD"]
    cash = raw["XEON.MI"][price_col].reindex(aligned.index).ffill(limit=5)
    aligned["CASH"] = cash
    return aligned[["BTC", "GOLD", "SP500", "CASH"]].dropna(subset=["BTC", "GOLD", "SP500"])


def build_listed_prices(cache_dir: Path, price_col: str = "open", range_: str = "max") -> pd.DataFrame:
    """Build listed EUR instrument series for realistic execution tests.

    Yahoo currently does not serve WBTC.MI/WBITG.DE, so WBTC.PA is the live EUR
    proxy for the same WisdomTree Physical Bitcoin ISIN.
    """
    mapping = {
        "BTC": "WBTC.PA",
        "GOLD": "SGLN.MI",
        "SP500": "CSSPX.MI",
        "CASH": "XEON.MI",
    }
    frames = {}
    for asset, ticker in mapping.items():
        df, _ = fetch_chart_cached(ticker, "1d", range_, cache_dir, max_age_hours=24)
        frames[asset] = df[price_col if price_col in df.columns else "close"]
    out = pd.DataFrame(frames).sort_index()
    return out.ffill(limit=3).dropna(subset=["BTC", "GOLD", "SP500"])


def latest_intraday_snapshot(cache_dir: Path, tickers: Iterable[str] = ("WBTC.PA", "SGLN.MI", "CSSPX.MI", "XEON.MI")) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for ticker in tickers:
        df, meta = fetch_chart_cached(ticker, "5m", "1d", cache_dir, max_age_hours=0.05)
        last = df.dropna(subset=["close"]).iloc[-1]
        out[ticker] = {
            "price": float(last["close"]),
            "as_of": df.dropna(subset=["close"]).index[-1].isoformat(),
            "currency": meta.get("currency"),
            "regular_market_price": meta.get("regularMarketPrice"),
        }
    return out
