"""
v2.4 — Entry Status Classifier (modalità ROTATION_BETA).

Classifica il "momento tecnico" di un titolo in uno stato operativo.
Ritorna (status, freshness_score 0-100).

Stati:
  PULLBACK_IN_TREND (100) — ritracciamento dentro trend → miglior entry
  FRESH_BREAKOUT    (90)  — breakout giovane → buon entry
  CONSOLIDATION     (60)  — accumulo laterale → watch
  NEUTRAL           (50)  — nessun segnale
  EXTENDED          (40)  — corsa lunga → no nuovo entry, hold ok
  BROKEN            (0)   — trend rotto → vendi se detenuto
  AVOID             (0)   — red flag / illiquido / dati insufficienti
"""
from __future__ import annotations

import pandas as pd


def _ma(close: pd.Series, n: int):
    return float(close.rolling(n).mean().iloc[-1]) if len(close) >= n else None


def _rsi14(close: pd.Series):
    if len(close) < 15:
        return None
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    val = (100 - 100 / (1 + rs)).iloc[-1]
    return None if pd.isna(val) else float(val)


def _consecutive_below(series_a: pd.Series, series_b, n: int) -> bool:
    """True se series_a < series_b per almeno n sessioni consecutive (in coda)."""
    if len(series_a) < n:
        return False
    tail_a = series_a.tail(n)
    if isinstance(series_b, pd.Series):
        tail_b = series_b.tail(n)
        return bool((tail_a.to_numpy() < tail_b.to_numpy()).all())
    return bool((tail_a < series_b).all())


def classify_entry_status(
    stock_df: pd.DataFrame,
    spy_df: pd.DataFrame | None,
    has_red_flag: bool = False,
    is_illiquid: bool = False,
    data_confidence: float = 100,
) -> tuple[str, int]:
    """
    stock_df / spy_df: DataFrame OHLC con colonna 'Close'.
    Ritorna (status, freshness_score).
    """
    if has_red_flag or is_illiquid or data_confidence < 40:
        return ("AVOID", 0)
    if stock_df is None or "Close" not in stock_df or len(stock_df) < 60:
        return ("NEUTRAL", 50)

    close = stock_df["Close"].dropna()
    price = float(close.iloc[-1])
    ma20 = _ma(close, 20)
    ma50 = _ma(close, 50)
    ma200 = _ma(close, 200)
    rsi = _rsi14(close) or 50

    # rendimento 3 mesi (~63 sedute)
    ret_3m = float(price / close.iloc[-64] - 1) if len(close) >= 64 else 0.0
    # distanza dal massimo 52 settimane
    high_52w = float(close.tail(252).max())
    dist_52w = (high_52w - price) / high_52w if high_52w else 0.0

    # forza relativa vs SPY su 90 giorni
    rs_vs_spy = 0.0
    rs_series = None
    if spy_df is not None and "Close" in spy_df:
        spy_close = spy_df["Close"].dropna()
        joined = pd.DataFrame({"s": close, "m": spy_close}).dropna()
        if len(joined) >= 90:
            stock_ret_90 = joined["s"].iloc[-1] / joined["s"].iloc[-90] - 1
            spy_ret_90 = joined["m"].iloc[-1] / joined["m"].iloc[-90] - 1
            rs_vs_spy = (stock_ret_90 - spy_ret_90) * 100
            # serie RS giornaliera (rapporto normalizzato) per i check consecutivi
            rs_series = (joined["s"] / joined["s"].iloc[0]) - (joined["m"] / joined["m"].iloc[0])

    # ── BROKEN: trend rotto ──
    if ma200 and _consecutive_below(close, close * 0 + ma200, 5) and price < ma200:
        return ("BROKEN", 0)
    if rs_series is not None and len(rs_series) >= 10:
        if bool((rs_series.tail(10).to_numpy() < -0.05).all()):
            return ("BROKEN", 0)

    # ── EXTENDED: corsa troppo lunga ──
    if rsi > 75 or ret_3m > 0.40 or (ma200 and price > ma200 * 1.25):
        return ("EXTENDED", 40)

    # ── PULLBACK_IN_TREND: miglior entry ──
    if (ma200 and ma20 and price > ma200 and price < ma20
            and 35 <= rsi <= 55 and ret_3m > 0):
        return ("PULLBACK_IN_TREND", 100)

    # ── FRESH_BREAKOUT ──
    if (ma50 and ma200 and price > ma50 and price > ma200
            and rs_vs_spy > 0 and dist_52w < 0.30 and 0 <= ret_3m <= 0.35):
        return ("FRESH_BREAKOUT", 90)

    # ── CONSOLIDATION: laterale stretto sopra MA50 ──
    if ma50 and price > ma50:
        range_20 = close.tail(20)
        if len(range_20) >= 20:
            width = (range_20.max() - range_20.min()) / range_20.mean()
            if width < 0.05:
                return ("CONSOLIDATION", 60)

    return ("NEUTRAL", 50)
