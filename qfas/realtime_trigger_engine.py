"""
QFAS v2.5 — realtime_trigger_engine.py

Calcola Entry Score real-time per ogni titolo:
  entry_score = w_mom × momentum + w_an × analyst + w_in × insider + w_cong × congressional
  + PEAD boost (post-earnings drift)
  × Short squeeze conditional multiplier

PATCH v2.5-PRAGMATIC:
  - Ogni segnale ha signal_available_from nel config
  - I pesi vengono RINORMALIZZATI dinamicamente quando alcuni segnali non sono
    ancora disponibili (analyst pre-2021, short squeeze pre-2024)
  - Nel backtest 2015-2020, peso passa a 0 per analyst/PEAD/squeeze,
    momentum + insider + congressional si redistribuiscono i pesi residui.

Classifica entry_status: FRESH_BREAKOUT, PULLBACK_IN_TREND, NEUTRAL,
CONSOLIDATION, BROKEN, AVOID.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from qfas.qfas_config import config, signal_is_available, renormalize_weights
from datetime import timedelta
from qfas.data_ingestion import (
    get_insider_net_flow, fetch_congressional_trades_for_ticker,
    fetch_analyst_grades_fmp, fetch_short_interest_finra,
    get_earnings_dates_8k, get_latest_earnings_surprise_pct,
    fetch_market_cap_adv, InsiderFlowResult,
)

log = logging.getLogger("qfas.trigger")


# ═════════════════════════════════════════════════════════════════════════
# MOMENTUM (sempre disponibile)
# ═════════════════════════════════════════════════════════════════════════

def compute_momentum_pct(price_series_by_ticker: Dict[str, pd.Series],
                          signal_date: date) -> Dict[str, float]:
    """
    momentum_pct = percentile rank cross-sectional di (0.5 × ret_3m + 0.5 × ret_6m).
    Restituisce dict ticker → percentile 0-100.
    """
    raw = {}
    for t, series in price_series_by_ticker.items():
        s = series[series.index <= pd.Timestamp(signal_date)].dropna()
        if len(s) < 130:
            raw[t] = None
            continue
        p_now = float(s.iloc[-1])
        p_3m = float(s.iloc[-63]) if len(s) >= 63 else None
        p_6m = float(s.iloc[-126]) if len(s) >= 126 else None
        if not (p_3m and p_6m):
            raw[t] = None
            continue
        ret3 = p_now / p_3m - 1
        ret6 = p_now / p_6m - 1
        raw[t] = 0.5 * ret3 + 0.5 * ret6
    valid = {t: v for t, v in raw.items() if v is not None}
    if not valid:
        return {t: 50.0 for t in raw}
    series = pd.Series(valid)
    pct = series.rank(pct=True) * 100
    out = {t: float(pct[t]) if t in pct.index else 50.0 for t in raw}
    return out


# ═════════════════════════════════════════════════════════════════════════
# ANALYST COMPOSITE CONTINUO (OPTIMIZATION #3 del prompt)
# ═════════════════════════════════════════════════════════════════════════

def calculate_analyst_composite(net_30d: int, net_90d: int,
                                next_earn_days: Optional[int]) -> float:
    """
    Score continuo 0-100 (50 = neutro).
    Pesa più 30d (0.6) di 90d (0.4) per reattività.
    Catalyst boost se earnings imminenti (entro 30gg) E rating positivo.
    """
    norm_30d = max(-5, min(5, net_30d)) / 5.0
    norm_90d = max(-5, min(5, net_90d)) / 5.0
    raw = 0.6 * norm_30d + 0.4 * norm_90d
    if next_earn_days is not None and 0 <= next_earn_days < 30 and raw > 0:
        catalyst_boost = 0.2 * (1.0 - next_earn_days / 30.0)
        raw = min(1.0, raw + catalyst_boost)
    return (raw + 1.0) * 50.0


def get_analyst_score(ticker: str, signal_date: date) -> Optional[float]:
    """
    Recupera grades FMP e calcola net upgrade/downgrade su 30d e 90d.
    Returns 0-100 score (50 neutro), o None se segnale non disponibile.
    """
    if not signal_is_available("analyst_composite", signal_date):
        return None

    grades = fetch_analyst_grades_fmp(ticker)
    if not grades:
        return None  # no data, segnale skipped

    # filtra al signal_date
    cutoff = pd.Timestamp(signal_date)
    cutoff_30 = cutoff - pd.Timedelta(days=30)
    cutoff_90 = cutoff - pd.Timedelta(days=90)

    net_30 = 0
    net_90 = 0
    for g in grades:
        try:
            d = pd.Timestamp(g.get("date", g.get("publishedDate", "")))
        except Exception:
            continue
        if d > cutoff:
            continue
        action = (g.get("action") or "").lower()
        delta = 0
        if "upgrade" in action: delta = 1
        elif "downgrade" in action: delta = -1
        if d >= cutoff_30:
            net_30 += delta
        if d >= cutoff_90:
            net_90 += delta

    # Earnings date check via 8-K Item 2.02 (con fallback yfinance)
    earn_dates = get_earnings_dates_8k(ticker)
    next_earn_days = None
    if earn_dates:
        future = [d for d in earn_dates if d > signal_date]
        if future:
            next_earn_days = (min(future) - signal_date).days

    return calculate_analyst_composite(net_30, net_90, next_earn_days)


# ═════════════════════════════════════════════════════════════════════════
# INSIDER FLOW (Form 4, escluse 10b5-1)
# ═════════════════════════════════════════════════════════════════════════

def get_insider_score(ticker: str, signal_date: date,
                      universe_flows: Dict[str, float] = None) -> Optional[float]:
    """
    Percentile rank cross-sectional del net insider flow %float ultimi 60gg.
    SOLO transazioni discrezionali (10b5-1 escluse via OR logic).
    Returns 0-100 o None se segnale non disponibile.
    """
    if not signal_is_available("insider_flow", signal_date):
        return None
    result = get_insider_net_flow(ticker, signal_date, lookback_days=60)
    if result is None:
        return None
    # Calcolo % di float: serve market cap come proxy
    # net_value_usd / market_cap = approssimazione %float
    mc_adv = fetch_market_cap_adv(ticker)
    if mc_adv is None or mc_adv[0] is None or mc_adv[0] == 0:
        # Fallback: ranking diretto cross-sectional sul net_value
        if universe_flows:
            values = pd.Series(universe_flows)
            return float((values.rank(pct=True) * 100).get(ticker, 50.0))
        # Singolo titolo: normalizza con sigmoid del net_value
        v = result.net_value_usd
        return max(0.0, min(100.0, 50.0 + (v / 1_000_000)))
    pct_float = result.net_value_usd / mc_adv[0] * 100
    if universe_flows:
        # universe_flows = dict ticker → pct_float
        universe_flows[ticker] = pct_float
        values = pd.Series(universe_flows)
        return float((values.rank(pct=True) * 100).get(ticker, 50.0))
    # singolo titolo: normalizza con sigmoid (5% float = score 95)
    return max(0.0, min(100.0, 50.0 + pct_float * 10))


# ═════════════════════════════════════════════════════════════════════════
# CONGRESSIONAL OVERLAP (binario o weighted)
# ═════════════════════════════════════════════════════════════════════════

def get_congressional_score(ticker: str, signal_date: date) -> Optional[float]:
    """
    Score basato sui trade congressionali ultimi 90gg:
      - 0 se nessun trade
      - 60 se 1 trade
      - 80 se 2-3 trades
      - 100 se 4+ trades
    Considera anche il sign (buy → boost, sell → riduce).
    """
    if not signal_is_available("congressional", signal_date):
        return None
    since = signal_date - timedelta(days=90)
    trades = fetch_congressional_trades_for_ticker(ticker, since)
    if not trades:
        return 0.0
    buys = sum(1 for t in trades if t.get("transaction_type") == "buy")
    sells = sum(1 for t in trades if t.get("transaction_type") == "sell")
    net = buys - sells
    if net <= 0:
        return 0.0
    if net == 1:
        return 60.0
    if net <= 3:
        return 80.0
    return 100.0


# ═════════════════════════════════════════════════════════════════════════
# PEAD BOOST (Post-Earnings Announcement Drift)
# ═════════════════════════════════════════════════════════════════════════

def calc_pead_boost(ticker: str, signal_date: date,
                    earnings_surprise_pct: Optional[float] = None) -> float:
    """
    Boost (in punti) se siamo entro PEAD_WINDOW_DAYS da un earnings con surprise
    significativa. Production: usa FMP per surprise, fallback su param caller.
    """
    if not signal_is_available("pead_surprise", signal_date):
        return 0.0
    # Recupera surprise via FMP se non passata
    surprise = earnings_surprise_pct
    if surprise is None:
        surprise = get_latest_earnings_surprise_pct(ticker, signal_date)
    if surprise is None:
        return 0.0
    # Trova ultimo earnings via 8-K Item 2.02
    earn_dates = get_earnings_dates_8k(ticker)
    if not earn_dates:
        return 0.0
    past = [d for d in earn_dates if d <= signal_date]
    if not past:
        return 0.0
    last_earn = max(past)
    days_since = (signal_date - last_earn).days
    if not (0 <= days_since <= config.PEAD_WINDOW_DAYS):
        return 0.0
    if surprise > config.PEAD_SURPRISE_THRESHOLD_POS:
        return min(config.PEAD_MAX_BOOST, surprise * 2.0)
    elif surprise < config.PEAD_SURPRISE_THRESHOLD_NEG:
        return -10.0
    return 0.0


# ═════════════════════════════════════════════════════════════════════════
# SHORT SQUEEZE CONDITIONAL
# ═════════════════════════════════════════════════════════════════════════

def apply_squeeze_multiplier(entry_score: float, ticker: str,
                              signal_date: date,
                              insider_score: Optional[float] = None,
                              momentum_pct: Optional[float] = None) -> float:
    """
    Se short_interest > 25%:
      - bullish set (insider>70 + mom>55) → score × 1.4
      - bearish set (insider<30 OR mom<35) → score × 0.5
      - neutral → invariato
    Se short_interest <= 25% → invariato.
    """
    if not signal_is_available("short_squeeze", signal_date):
        return entry_score
    si = fetch_short_interest_finra(ticker, signal_date)
    if si is None or si <= config.SQUEEZE_SI_THRESHOLD:
        return entry_score
    # condizioni bullish
    if (insider_score is not None and insider_score > config.SQUEEZE_INSIDER_THRESHOLD
        and momentum_pct is not None and momentum_pct > config.SQUEEZE_MOMENTUM_THRESHOLD):
        return entry_score * config.SQUEEZE_MULTIPLIER_BULLISH
    # condizioni bearish
    if (insider_score is not None and insider_score < 30) or \
       (momentum_pct is not None and momentum_pct < 35):
        return entry_score * config.SQUEEZE_MULTIPLIER_BEARISH
    return entry_score


# ═════════════════════════════════════════════════════════════════════════
# ENTRY SCORE COMPOSITO con rinormalizzazione anti-look-ahead
# ═════════════════════════════════════════════════════════════════════════

@dataclass
class EntryScoreResult:
    ticker: str
    signal_date: date
    entry_score_final: float
    momentum_pct: Optional[float]
    analyst_score: Optional[float]
    insider_score: Optional[float]
    congressional_score: Optional[float]
    pead_boost: float
    squeeze_applied: bool
    weights_used: Dict[str, float]
    entry_status: str


def compute_entry_score(
    ticker: str,
    signal_date: date,
    momentum_pct: Optional[float],
    insider_score: Optional[float] = None,
    universe_flows: Dict[str, float] = None,
    earnings_surprise_pct: Optional[float] = None,
) -> EntryScoreResult:
    """
    Calcola entry_score finale con rinormalizzazione dinamica dei pesi
    in base ai segnali disponibili a signal_date.
    """
    # Pesi originali
    base_weights = {
        "momentum": config.ENTRY_WEIGHT_MOMENTUM,
        "analyst_composite": config.ENTRY_WEIGHT_ANALYST,
        "insider_flow": config.ENTRY_WEIGHT_INSIDER,
        "congressional": config.ENTRY_WEIGHT_CONGRESSIONAL,
    }
    weights = renormalize_weights(base_weights, signal_date)

    # Raccolgo score per ogni segnale
    analyst_score = get_analyst_score(ticker, signal_date) if weights.get("analyst_composite", 0) > 0 else None
    congressional_score = get_congressional_score(ticker, signal_date) if weights.get("congressional", 0) > 0 else None
    if insider_score is None and weights.get("insider_flow", 0) > 0:
        insider_score = get_insider_score(ticker, signal_date, universe_flows)

    # Default 50 (neutral) per segnali disponibili ma data mancante
    mom = momentum_pct if momentum_pct is not None else 50.0
    an = analyst_score if analyst_score is not None else 50.0
    ins = insider_score if insider_score is not None else 50.0
    cong = congressional_score if congressional_score is not None else 0.0

    # Compositive linear (pesi già rinormalizzati)
    entry_base = (weights.get("momentum", 0) * mom +
                  weights.get("analyst_composite", 0) * an +
                  weights.get("insider_flow", 0) * ins +
                  weights.get("congressional", 0) * cong)

    # PEAD
    pead = calc_pead_boost(ticker, signal_date, earnings_surprise_pct)
    entry_with_pead = entry_base + pead

    # Squeeze multiplier
    entry_with_squeeze = apply_squeeze_multiplier(
        entry_with_pead, ticker, signal_date, insider_score, momentum_pct
    )
    squeeze_applied = entry_with_squeeze != entry_with_pead

    # Cap a [0, 100]
    entry_final = max(0.0, min(100.0, entry_with_squeeze))

    return EntryScoreResult(
        ticker=ticker, signal_date=signal_date,
        entry_score_final=entry_final,
        momentum_pct=momentum_pct,
        analyst_score=analyst_score,
        insider_score=insider_score,
        congressional_score=congressional_score,
        pead_boost=pead,
        squeeze_applied=squeeze_applied,
        weights_used=weights,
        entry_status="NEUTRAL",  # da classificare dopo via classify_entry_status
    )


# ═════════════════════════════════════════════════════════════════════════
# ENTRY STATUS CLASSIFICATION
# ═════════════════════════════════════════════════════════════════════════

def classify_entry_status(
    ticker: str, signal_date: date,
    price_series: pd.Series,
    radar_score: float,
    insider_score: Optional[float] = None,
    short_interest: Optional[float] = None,
) -> str:
    """
    Classifica il titolo in uno degli stati:
      - FRESH_BREAKOUT: max 60gg + volume>1.5x avg + radar>50°pctl
      - PULLBACK_IN_TREND: trend OK + correction 5-15%
      - NEUTRAL: niente di particolare
      - CONSOLIDATION: range ±5% da SMA50 ultimi 20gg
      - BROKEN: price < SMA200 e momentum debole
      - AVOID: short_interest > 40 e insider negativo
    """
    s = price_series[price_series.index <= pd.Timestamp(signal_date)].dropna()
    if len(s) < 200:
        return "NEUTRAL"
    p = float(s.iloc[-1])
    sma50 = float(s.tail(50).mean())
    sma200 = float(s.tail(200).mean())
    high60 = float(s.tail(60).max())
    momentum_ok = (p > sma200) and (sma50 > sma200)

    # AVOID
    if short_interest is not None and short_interest > 40 \
       and insider_score is not None and insider_score < 20:
        return "AVOID"

    # BROKEN
    if p < sma200:
        # check momentum_pct se disponibile
        return "BROKEN"

    # FRESH_BREAKOUT
    if abs(p - high60) / high60 < 0.005 and radar_score > 50:
        return "FRESH_BREAKOUT"

    # PULLBACK_IN_TREND
    if momentum_ok and -0.15 <= (p - high60) / high60 <= -0.05 and radar_score > 60:
        return "PULLBACK_IN_TREND"

    # CONSOLIDATION
    last_20 = s.tail(20)
    if not last_20.empty:
        last_20_dev = (last_20.max() - last_20.min()) / sma50
        if last_20_dev < 0.10:
            return "CONSOLIDATION"

    return "NEUTRAL"


if __name__ == "__main__":
    print("REALTIME TRIGGER ENGINE self-check")
    print("=" * 60)

    # Test analyst composite continuo
    print("\nTest analyst composite (deve essere continuo 0-100):")
    for net_30, net_90, earn_days in [(0, 0, None), (3, 5, None), (-2, 1, None),
                                       (5, 5, 10), (-5, -5, None)]:
        score = calculate_analyst_composite(net_30, net_90, earn_days)
        print(f"  net30={net_30:+d}  net90={net_90:+d}  earn={earn_days}  → {score:.1f}")
    assert 0 <= calculate_analyst_composite(5, 5, 5) <= 100

    # Test rinormalizzazione pesi via entry score
    print("\nTest entry score 2018 (analyst disabled) vs 2024 (full):")
    res_2018 = compute_entry_score("AAPL", date(2018, 6, 1), momentum_pct=70.0)
    res_2024 = compute_entry_score("AAPL", date(2024, 6, 1), momentum_pct=70.0)
    print(f"  2018: weights={res_2018.weights_used}  score={res_2018.entry_score_final:.1f}")
    print(f"  2024: weights={res_2024.weights_used}  score={res_2024.entry_score_final:.1f}")

    print("\n✓ Modulo OK")
