"""
Yahoo Finance fetcher per prezzi, fondamentali e momentum.
Usa yfinance (gratuito, no API key).
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Optional
import yfinance as yf
import pandas as pd
import numpy as np


def get_quote(ticker: str) -> dict:
    """Quote + key stats per un ticker. Cache via yfinance interna."""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        return {
            "ticker": ticker,
            "name": info.get("shortName") or info.get("longName") or ticker,
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "price": info.get("regularMarketPrice") or info.get("currentPrice"),
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("marketCap"),
            "pe_forward": info.get("forwardPE"),
            "pe_trailing": info.get("trailingPE"),
            "pb": info.get("priceToBook"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "gross_margin": info.get("grossMargins"),
            "operating_margin": info.get("operatingMargins"),
            "profit_margin": info.get("profitMargins"),
            "debt_to_equity": info.get("debtToEquity"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "beta": info.get("beta"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "avg_volume": info.get("averageVolume"),
            "analyst_target": info.get("targetMeanPrice"),
            "analyst_recommendation": info.get("recommendationKey"),
            "num_analysts": info.get("numberOfAnalystOpinions"),
            "dividend_yield": info.get("dividendYield"),
            # v2.2 — short interest (sostituisce scraping FINRA, stesso dato underlying)
            "short_pct_float": info.get("shortPercentOfFloat"),
            "short_ratio": info.get("shortRatio"),
            "shares_short": info.get("sharesShort"),
            "shares_short_prior": info.get("sharesShortPriorMonth"),
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def get_price_history(ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """OHLCV history. period: 1mo, 3mo, 6mo, 1y, 2y, 5y."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, auto_adjust=True)
        return df if not df.empty else None
    except Exception:
        return None


def compute_momentum(ticker: str) -> dict:
    """Return su 1M, 3M, 6M, 12M + RSI + posizione vs MA50/MA200."""
    df = get_price_history(ticker, period="1y")
    if df is None or len(df) < 30:
        return {"ticker": ticker, "available": False}

    close = df["Close"]
    now = close.iloc[-1]

    def pct_return(days: int) -> Optional[float]:
        if len(close) < days + 1:
            return None
        return float((now / close.iloc[-days - 1] - 1) * 100)

    # RSI 14
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi_val = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None

    # MA50 / MA200
    ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

    # Volume trend (avg ultimo mese vs precedenti 3 mesi)
    vol = df["Volume"]
    vol_recent = float(vol.iloc[-21:].mean()) if len(vol) >= 21 else None
    vol_prior = float(vol.iloc[-84:-21].mean()) if len(vol) >= 84 else None
    vol_ratio = (vol_recent / vol_prior) if (vol_recent and vol_prior) else None

    # v2.2: rilevazione gap recente (open vs close precedente) negli ultimi 15 gg
    gap_recent_pct = 0.0
    days_since_gap = None
    try:
        opens = df["Open"]
        window = min(15, len(close) - 1)
        biggest_gap = 0.0
        gap_idx = None
        for i in range(len(close) - window, len(close)):
            if i < 1:
                continue
            prev_close = close.iloc[i - 1]
            day_open = opens.iloc[i]
            if prev_close > 0:
                g = abs(day_open / prev_close - 1)
                if g > biggest_gap:
                    biggest_gap = g
                    gap_idx = i
        gap_recent_pct = round(biggest_gap, 4)
        if gap_idx is not None:
            days_since_gap = len(close) - 1 - gap_idx
    except Exception:
        pass

    return {
        "ticker": ticker,
        "available": True,
        "price": float(now),
        "ret_1m": pct_return(21),
        "ret_3m": pct_return(63),
        "ret_6m": pct_return(126),
        "ret_12m": pct_return(252),
        "rsi_14": rsi_val,
        "ma50": ma50,
        "ma200": ma200,
        "above_ma50": (ma50 is not None and now > ma50),
        "above_ma200": (ma200 is not None and now > ma200),
        "volume_ratio_recent_vs_prior": vol_ratio,
        "gap_recent_pct": gap_recent_pct,
        "days_since_gap": days_since_gap,
    }


def batch_quotes(tickers: list[str], throttle_sec: float = 0.3) -> dict:
    """Quote per batch di ticker con throttle."""
    out = {}
    for t in tickers:
        out[t] = get_quote(t)
        time.sleep(throttle_sec)
    return out


def batch_momentum(tickers: list[str], throttle_sec: float = 0.3) -> dict:
    out = {}
    for t in tickers:
        out[t] = compute_momentum(t)
        time.sleep(throttle_sec)
    return out


if __name__ == "__main__":
    import sys
    import json
    t = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    print(json.dumps(get_quote(t), indent=2, default=str))
    print("---")
    print(json.dumps(compute_momentum(t), indent=2, default=str))
