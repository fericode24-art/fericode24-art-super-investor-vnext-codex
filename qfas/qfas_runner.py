"""
QFAS v2.5 — qfas_runner.py

Orchestratore del decision cycle: per ogni signal_date, prende i dati,
calcola scoring radar+entry, applica tax_aware_optimizer per produrre il
portfolio finale.

Single entry point: run_decision_cycle(signal_date, current_holdings).

Audit trail strutturato per ogni decisione (input scores, weights, reasons).
"""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from qfas.qfas_config import config, signal_is_available, renormalize_weights
from qfas.fund_universe import get_active_funds_at, FUND_ACTIVE_PERIODS
from qfas.signal_decay_scorer import batch_radar_scores, RadarScoreResult
from qfas.realtime_trigger_engine import (
    compute_entry_score, compute_momentum_pct, classify_entry_status,
    EntryScoreResult,
)
from qfas.tax_aware_optimizer import (
    select_portfolio, compute_sector_momentum_rank, PortfolioSlot,
)

log = logging.getLogger("qfas.runner")
log.setLevel(logging.INFO)
ROOT = Path(__file__).parent.parent.absolute()


@dataclass
class CandidateScore:
    ticker: str
    radar_score: float
    entry_score: float
    opportunity_score: float
    momentum_pct: float
    entry_status: str
    sector: str
    audit: Dict = field(default_factory=dict)


@dataclass
class DecisionCycleResult:
    signal_date: date
    portfolio: List[PortfolioSlot]
    n_candidates: int
    n_active_funds: int
    vix_value: Optional[float]
    sub_margin_used: float
    weights_active: Dict[str, float]
    sector_momentum_rank: List[str]
    top10_candidates: List[CandidateScore]   # top 10 per audit
    all_candidates: List[CandidateScore]     # tutti i candidati scoreati (per UI lookup)
    audit_log: Dict


def _load_json_cache(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("Cache non leggibile %s: %s", path, e)
    return default


def _clip_score(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _cached_insider_score(ticker: str, insider_cache: Dict) -> Optional[float]:
    row = insider_cache.get(ticker.upper()) if insider_cache else None
    if not isinstance(row, dict):
        return None
    net_value = float(row.get("net_value_usd") or 0.0)
    n_tx = int(row.get("n_transactions") or 0)
    if n_tx == 0 and net_value == 0:
        return 50.0
    directional = max(-35.0, min(35.0, net_value / 2_000_000.0 * 35.0))
    activity = 0.0
    if n_tx >= 3:
        activity = 5.0 if net_value > 0 else -5.0
    return _clip_score(50.0 + directional + activity)


def _cached_analyst_score(ticker: str, signal_date: date) -> Optional[float]:
    path = ROOT / "qfas" / "cache" / f"finn_reco_{ticker.upper()}.json"
    rows = _load_json_cache(path, [])
    if not isinstance(rows, list):
        return None
    valid = []
    for row in rows:
        try:
            period = pd.Timestamp(row.get("period")).date()
        except Exception:
            continue
        if period <= signal_date:
            valid.append(row)
    if not valid:
        return None
    latest = sorted(valid, key=lambda r: str(r.get("period") or ""))[-1]
    weights = {
        "strongBuy": 100.0,
        "buy": 75.0,
        "hold": 50.0,
        "sell": 25.0,
        "strongSell": 0.0,
    }
    total = sum(float(latest.get(k) or 0.0) for k in weights)
    if total <= 0:
        return None
    score = sum(float(latest.get(k) or 0.0) * v for k, v in weights.items()) / total
    return _clip_score(score)


def _cached_pead_boost(
    ticker: str,
    signal_date: date,
    price_series: pd.Series,
    earnings_cache: Dict,
) -> float:
    row = earnings_cache.get(ticker.upper()) if earnings_cache else None
    if not isinstance(row, dict):
        return 0.0
    dates = []
    for raw in row.get("earnings_dates", []) or []:
        try:
            d = date.fromisoformat(str(raw)[:10])
        except Exception:
            continue
        if d <= signal_date:
            dates.append(d)
    if not dates:
        return 0.0
    last_earn = max(dates)
    days_since = (signal_date - last_earn).days
    if not (0 <= days_since <= config.PEAD_WINDOW_DAYS):
        return 0.0
    s = price_series[price_series.index <= pd.Timestamp(signal_date)].dropna()
    before = price_series[price_series.index < pd.Timestamp(last_earn)].dropna()
    if s.empty or before.empty:
        return 0.0
    prev_close = float(before.iloc[-1])
    cur_close = float(s.iloc[-1])
    if prev_close <= 0:
        return 0.0
    reaction_pct = (cur_close / prev_close - 1.0) * 100.0
    return max(-10.0, min(config.PEAD_MAX_BOOST, reaction_pct * 0.8))


def _cached_entry_score(
    ticker: str,
    signal_date: date,
    momentum_pct: Optional[float],
    price_series: pd.Series,
    insider_cache: Dict,
    earnings_cache: Dict,
) -> EntryScoreResult:
    mom = momentum_pct if momentum_pct is not None else 50.0
    analyst_score = _cached_analyst_score(ticker, signal_date)
    insider_score = _cached_insider_score(ticker, insider_cache)
    analyst_used = analyst_score if analyst_score is not None else 50.0
    insider_used = insider_score if insider_score is not None else 50.0

    weights = renormalize_weights({
        "momentum": config.ENTRY_WEIGHT_MOMENTUM,
        "analyst_composite": config.ENTRY_WEIGHT_ANALYST,
        "insider_flow": config.ENTRY_WEIGHT_INSIDER,
        "congressional": 0.0,
    }, signal_date)
    entry_base = (
        weights.get("momentum", 0.0) * mom +
        weights.get("analyst_composite", 0.0) * analyst_used +
        weights.get("insider_flow", 0.0) * insider_used
    )
    pead = _cached_pead_boost(ticker, signal_date, price_series, earnings_cache)
    raw_delta = (entry_base + pead) - mom
    bounded_delta = max(-12.0, min(12.0, raw_delta))
    entry_final = _clip_score(mom + bounded_delta)

    return EntryScoreResult(
        ticker=ticker,
        signal_date=signal_date,
        entry_score_final=entry_final,
        momentum_pct=momentum_pct,
        analyst_score=analyst_score,
        insider_score=insider_score,
        congressional_score=None,
        pead_boost=pead,
        squeeze_applied=False,
        weights_used=weights,
        entry_status="NEUTRAL",
    )


def _cached_market_shadow(
    ticker: str,
    current_entry_score: float,
    momentum_pct: Optional[float],
    analyst_score: Optional[float],
    insider_score: Optional[float],
    pead_boost: float,
    market_cache: Dict,
) -> Dict:
    row = (market_cache.get("tickers") or {}).get(ticker.upper()) if market_cache else None
    if not isinstance(row, dict):
        return {}
    congressional_score = row.get("congressional_score")
    short_interest = row.get("short_interest_pct")
    if congressional_score is None and short_interest is None:
        return {}

    mom = momentum_pct if momentum_pct is not None else 50.0
    analyst_used = analyst_score if analyst_score is not None else 50.0
    insider_used = insider_score if insider_score is not None else 50.0
    try:
        congressional_used = float(congressional_score) if congressional_score is not None else 0.0
    except (TypeError, ValueError):
        congressional_used = 0.0
    try:
        short_interest_used = float(short_interest) if short_interest is not None else None
    except (TypeError, ValueError):
        short_interest_used = None
    raw_as_of = str(market_cache.get("as_of") or date.today())[:10]
    try:
        market_as_of = date.fromisoformat(raw_as_of)
    except ValueError:
        market_as_of = date.today()
    weights = renormalize_weights({
        "momentum": config.ENTRY_WEIGHT_MOMENTUM,
        "analyst_composite": config.ENTRY_WEIGHT_ANALYST,
        "insider_flow": config.ENTRY_WEIGHT_INSIDER,
        "congressional": config.ENTRY_WEIGHT_CONGRESSIONAL,
    }, market_as_of)
    entry_base = (
        weights.get("momentum", 0.0) * mom +
        weights.get("analyst_composite", 0.0) * analyst_used +
        weights.get("insider_flow", 0.0) * insider_used +
        weights.get("congressional", 0.0) * congressional_used
    )
    raw_delta = (entry_base + pead_boost) - mom
    bounded_delta = max(-12.0, min(12.0, raw_delta))
    entry_with_congress = _clip_score(mom + bounded_delta)
    squeeze_state = "none"
    entry_with_squeeze = entry_with_congress
    if short_interest_used is not None and short_interest_used > config.SQUEEZE_SI_THRESHOLD:
        if insider_score is not None and insider_score > config.SQUEEZE_INSIDER_THRESHOLD and mom > config.SQUEEZE_MOMENTUM_THRESHOLD:
            squeeze_state = "bullish"
            entry_with_squeeze = entry_with_congress * config.SQUEEZE_MULTIPLIER_BULLISH
        elif (insider_score is not None and insider_score < 30.0) or mom < 35.0:
            squeeze_state = "bearish"
            entry_with_squeeze = entry_with_congress * config.SQUEEZE_MULTIPLIER_BEARISH
        else:
            squeeze_state = "watch"

    shadow_entry = _clip_score(entry_with_squeeze)
    return {
        "congressional_shadow": congressional_score,
        "congressional_trades": row.get("congressional_trades"),
        "congressional_net": row.get("congressional_net"),
        "short_interest_shadow": short_interest_used,
        "short_interest_raw": row.get("short_interest_raw"),
        "short_interest_state": row.get("short_interest_state"),
        "squeeze_shadow": squeeze_state,
        "market_shadow_entry": float(shadow_entry),
        "market_shadow_delta": float(shadow_entry - current_entry_score),
        "market_shadow_cached": True,
    }


def run_decision_cycle(
    signal_date: date,
    current_holdings: List[Dict],              # [{ticker, score, sector, status, days_held, pnl_pct}]
    universe_tickers: List[str],               # ticker da valutare
    all_filings_by_fund: Dict[str, List[Dict]], # CIK → list filing 13F
    prices_by_ticker: Dict[str, pd.Series],     # ticker → serie prezzi giornalieri
    sectors_by_ticker: Dict[str, str],
    vix_value: Optional[float] = None,
    skip_external_signals: bool = False,        # se True, skip Form4/analyst/Capitol network calls
    external_signal_mode: str = "full",         # off|cached|full
) -> DecisionCycleResult:
    """
    Esegue un ciclo completo di decisione QFAS per signal_date.

    Pipeline:
      1. Filtro universo (rimuovi ticker senza prezzo o sotto-soglia liquidità)
      2. Calcola Radar Score per tutti i ticker (batch)
      3. Calcola Momentum cross-sectional
      4. Per ciascun candidato (top 60 per radar), calcola Entry Score
      5. Combina in Opportunity Score (50/50 radar/entry)
      6. Classifica entry_status (FRESH_BREAKOUT, NEUTRAL, BROKEN, ecc.)
      7. Calcola sector momentum ranking
      8. Chiama select_portfolio con anti-churn, TLH, sector cap
    """
    log.info(f"Decision cycle {signal_date}: universo {len(universe_tickers)} ticker")
    external_signal_mode = (external_signal_mode or "full").lower()
    if skip_external_signals:
        external_signal_mode = "off"
    if external_signal_mode not in {"off", "cached", "full"}:
        raise ValueError(f"external_signal_mode non valido: {external_signal_mode}")

    # ── 1. Filtro universo: ticker con prezzo valido a signal_date
    cutoff_ts = pd.Timestamp(signal_date)
    valid_universe = []
    for t in universe_tickers:
        s = prices_by_ticker.get(t)
        if s is None or s.empty:
            continue
        valid_at_date = s[s.index <= cutoff_ts].dropna()
        if len(valid_at_date) < 200:   # serve almeno 200gg di prezzi per scoring
            continue
        valid_universe.append(t)

    log.info(f"  universo valido (prezzi >=200gg): {len(valid_universe)}")
    if len(valid_universe) < config.NUM_POSITIONS:
        log.warning("Universe troppo piccolo, returning empty portfolio")
        return DecisionCycleResult(
            signal_date, [], 0, 0, vix_value, config.SUB_MARGIN_BASE,
            {}, [], [], {"error": "insufficient_universe"},
        )

    # ── 2. Radar Score batch (13F-based, con decay + crowding PIT)
    # prices_at_date per AUM proxy
    prices_at_date = {}
    for t in valid_universe:
        s = prices_by_ticker[t]
        s_valid = s[s.index <= cutoff_ts].dropna()
        if not s_valid.empty:
            prices_at_date[t] = float(s_valid.iloc[-1])

    radar_results = batch_radar_scores(
        valid_universe, signal_date, all_filings_by_fund, prices_at_date,
    )
    raw_convictions = pd.Series({t: r.raw_conviction for t, r in radar_results.items()})
    if not raw_convictions.empty and raw_convictions.sum() > 0:
        conviction_pct_map = (raw_convictions.rank(pct=True) * 100.0).to_dict()
    else:
        conviction_pct_map = {t: 50.0 for t in radar_results}

    # ── 3. Momentum cross-sectional su tutto l'universo valido
    momentum_pct_map = compute_momentum_pct(
        {t: prices_by_ticker[t] for t in valid_universe},
        signal_date,
    )

    # ── 4-6. Per ogni candidato calcola Entry Score + classifica status
    # Per efficienza: limito a top 80 per radar_score (riduce chiamate API esterne)
    radar_sorted = sorted(radar_results.items(),
                          key=lambda kv: -kv[1].radar_score)
    top_candidates_for_entry = [t for t, _ in radar_sorted[:80]]
    insider_cache = {}
    earnings_cache = {}
    market_cache = {}
    if external_signal_mode == "cached":
        insider_cache = _load_json_cache(ROOT / "data" / "backtest" / "insider_cache.json", {})
        earnings_cache = _load_json_cache(ROOT / "data" / "backtest" / "earnings_cache.json", {})
        market_cache = _load_json_cache(ROOT / "data" / "backtest" / "market_signal_cache.json", {})

    candidates: List[CandidateScore] = []
    for t in valid_universe:
        radar_result = radar_results[t]
        radar = radar_result.radar_score
        mom = momentum_pct_map.get(t, 50.0)
        radar_audit = {
            "momentum": float(mom),
            "conviction": float(conviction_pct_map.get(t, 50.0)),
            "accumulation": float(radar_result.accumulation_pct),
            "crowding": float(radar_result.crowding_factor * 100.0),
            "fund_coverage": float(radar_result.fund_coverage * 100.0),
            "valid_filings": int(radar_result.num_valid_filings),
            "active_funds": int(radar_result.num_active_funds),
        }

        # Per ticker NON in top80 radar OPPURE skip_external_signals → quick path
        if t in top_candidates_for_entry and external_signal_mode == "full":
            entry_res = compute_entry_score(
                ticker=t, signal_date=signal_date,
                momentum_pct=mom,
                insider_score=None,    # calcolato internamente se segnale available
            )
            entry_score = entry_res.entry_score_final
            audit = {
                **radar_audit,
                "weights": entry_res.weights_used,
                "analyst": entry_res.analyst_score,
                "insider": entry_res.insider_score,
                "congressional": entry_res.congressional_score,
                "pead": entry_res.pead_boost,
                "squeeze": entry_res.squeeze_applied,
                "external_signal_mode": "full",
                "external_delta": float(entry_score - mom),
            }
        elif t in top_candidates_for_entry and external_signal_mode == "cached":
            entry_res = _cached_entry_score(
                ticker=t,
                signal_date=signal_date,
                momentum_pct=mom,
                price_series=prices_by_ticker[t],
                insider_cache=insider_cache,
                earnings_cache=earnings_cache,
            )
            entry_score = entry_res.entry_score_final
            audit = {
                **radar_audit,
                "weights": entry_res.weights_used,
                "analyst": entry_res.analyst_score,
                "analyst_cached": entry_res.analyst_score is not None,
                "insider": entry_res.insider_score,
                "insider_cached": entry_res.insider_score is not None,
                "congressional": entry_res.congressional_score,
                "pead": entry_res.pead_boost,
                "pead_cached": entry_res.pead_boost != 0.0,
                "squeeze": entry_res.squeeze_applied,
                "external_signal_mode": "cached",
                "external_delta": float(entry_score - mom),
            }
            audit.update(_cached_market_shadow(
                ticker=t,
                current_entry_score=entry_score,
                momentum_pct=mom,
                analyst_score=entry_res.analyst_score,
                insider_score=entry_res.insider_score,
                pead_boost=entry_res.pead_boost,
                market_cache=market_cache,
            ))
        else:
            # Quick path: solo momentum (segnali esterni a peso 0 implicito,
            # niente network calls)
            entry_score = mom
            audit = {
                **radar_audit,
                "quick_path": True,
                "skip_external": external_signal_mode == "off",
                "external_signal_mode": "off" if external_signal_mode == "off" else "quick",
                "external_delta": 0.0,
            }

        opp_score = (config.OPPORTUNITY_WEIGHT_RADAR * radar +
                     config.OPPORTUNITY_WEIGHT_ENTRY * entry_score)

        status = classify_entry_status(
            t, signal_date, prices_by_ticker[t],
            radar_score=radar,
        )

        candidates.append(CandidateScore(
            ticker=t,
            radar_score=radar,
            entry_score=entry_score,
            opportunity_score=opp_score,
            momentum_pct=mom,
            entry_status=status,
            sector=sectors_by_ticker.get(t, "Unknown"),
            audit=audit,
        ))

    candidates.sort(key=lambda c: -c.opportunity_score)
    top10 = candidates[:10]

    # ── 7. Sector momentum ranking
    tickers_by_sector: Dict[str, List[str]] = {}
    for c in candidates[:200]:   # top 200 per momentum ranking settore
        tickers_by_sector.setdefault(c.sector, []).append(c.ticker)
    sector_rank = compute_sector_momentum_rank(
        tickers_by_sector,
        {t: prices_by_ticker[t] for t in valid_universe},
        signal_date,
    )

    # ── 8. Selezione portfolio finale
    candidates_for_opt = [
        {"ticker": c.ticker, "score": c.opportunity_score,
         "sector": c.sector, "entry_status": c.entry_status}
        for c in candidates
    ]
    portfolio = select_portfolio(
        candidates=candidates_for_opt,
        current_holdings=current_holdings,
        sector_momentum_rank=sector_rank,
        vix_value=vix_value,
        signal_date=signal_date,
    )

    # Weights effettivi a signal_date (per audit)
    base_weights = {
        "momentum": config.ENTRY_WEIGHT_MOMENTUM,
        "analyst_composite": config.ENTRY_WEIGHT_ANALYST,
        "insider_flow": config.ENTRY_WEIGHT_INSIDER,
        "congressional": config.ENTRY_WEIGHT_CONGRESSIONAL,
    }
    if external_signal_mode == "cached":
        audit_weight_basis = {**base_weights, "congressional": 0.0}
    elif skip_external_signals or external_signal_mode in {"off", "quick"}:
        audit_weight_basis = {
            "momentum": 1.0,
            "analyst_composite": 0.0,
            "insider_flow": 0.0,
            "congressional": 0.0,
        }
    else:
        audit_weight_basis = base_weights
    active_weights = renormalize_weights(audit_weight_basis, signal_date)

    from qfas.tax_aware_optimizer import get_dynamic_sub_margin
    sub_margin = get_dynamic_sub_margin(vix_value)

    audit = {
        "n_universe_valid": len(valid_universe),
        "n_radar_scored": len(radar_results),
        "n_top_entry_computed": len(top_candidates_for_entry),
        "n_candidates_total": len(candidates),
        "external_signal_mode": external_signal_mode,
        "external_cache": {
            "insider_rows": len(insider_cache) if isinstance(insider_cache, dict) else 0,
            "earnings_rows": len(earnings_cache) if isinstance(earnings_cache, dict) else 0,
            "market_rows": len(market_cache.get("tickers", {})) if isinstance(market_cache, dict) else 0,
        },
        "top10_by_opp_score": [
            (c.ticker, round(c.opportunity_score, 1),
             c.entry_status, c.sector) for c in top10
        ],
        "selected_portfolio": [
            (s.ticker, round(s.score, 1), s.sector, s.entry_status, s.reason)
            for s in portfolio
        ],
    }

    return DecisionCycleResult(
        signal_date=signal_date,
        portfolio=portfolio,
        n_candidates=len(candidates),
        n_active_funds=len(get_active_funds_at(signal_date)),
        vix_value=vix_value,
        sub_margin_used=sub_margin,
        weights_active=active_weights,
        sector_momentum_rank=sector_rank,
        top10_candidates=top10,
        all_candidates=candidates,
        audit_log=audit,
    )


if __name__ == "__main__":
    import sys
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

    print("QFAS RUNNER self-check")
    print("=" * 60)
    print("  run_decision_cycle() pronto.")
    print("  Input atteso:")
    print("    - signal_date: date")
    print("    - current_holdings: List[{ticker, score, sector, status, days_held, pnl_pct}]")
    print("    - universe_tickers: List[str]")
    print("    - all_filings_by_fund: Dict[CIK, List[filing dict]]")
    print("    - prices_by_ticker: Dict[ticker, pd.Series]")
    print("    - sectors_by_ticker: Dict[ticker, str]")
    print("    - vix_value: Optional[float]")
    print("  Output: DecisionCycleResult con portfolio (8 PortfolioSlot) + audit completo")
    print("✓ OK")
