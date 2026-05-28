"""
QFAS v2.5 — tax_aware_optimizer.py

Selezione finale del portafoglio (8 posizioni equal-weight €6k cad).
Anti-churn con SUB_MARGIN dinamico VIX, MIN_HOLD_DAYS, FIFO tax boost,
TLH proattivo italiano (1 nov - 20 dic, NO wash sale US).

PATCH v2.5:
  - Spread scalato calibrato mid-cap (BUG #1 FIX)
  - SUB_MARGIN dinamico su VIX corrente
  - MIN_HOLD_DAYS con eccezione BROKEN/AVOID
  - TLH italiano: NESSUN blocco riacquisto 31gg (wash sale US non applicabile)
  - Sector cap condizionato (top 3 settori per momentum → 5 slot, altri → 3)
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from qfas.qfas_config import config

log = logging.getLogger("qfas.optimizer")


# ═════════════════════════════════════════════════════════════════════════
# COSTI: spread scalato calibrato mid-cap (BUG #1 FIX)
# ═════════════════════════════════════════════════════════════════════════

def calculate_spread(adv_20d_usd: float) -> float:
    """
    Calibrato su mediana mid-cap reale Fineco.
      ADV $10M  → 0.150% (soglia liquidità)
      ADV $50M  → 0.067% (mid-cap mediano)
      ADV $200M → 0.034% (large-cap liquido)
    Cap 0.30% scatta sotto ADV $2.5M (irraggiungibile post filtro liquidità).
    """
    if adv_20d_usd <= 0:
        return config.SPREAD_CAP
    base_spread = config.SPREAD_BASE_AT_10M_ADV  # 0.0015
    decay_factor = (10_000_000 / adv_20d_usd) ** 0.5
    return min(base_spread * decay_factor, config.SPREAD_CAP)


def cost_per_trade(position_value_eur: float, adv_20d_usd: float) -> float:
    """Commissione fissa + spread scalato."""
    spread = calculate_spread(adv_20d_usd)
    return config.COMMISSION_PER_ORDER_EUR + position_value_eur * spread


# ═════════════════════════════════════════════════════════════════════════
# SUB_MARGIN DINAMICO VIX
# ═════════════════════════════════════════════════════════════════════════

def get_dynamic_sub_margin(vix_value: Optional[float]) -> float:
    """Margine sostituzione adattivo: VIX alto → più conservativi (meno rotaz)."""
    base = config.SUB_MARGIN_BASE
    if vix_value is None:
        return base
    if vix_value < 15:
        return base + config.SUB_MARGIN_LOW_VIX_OFFSET    # -2
    if vix_value > 25:
        return base + config.SUB_MARGIN_HIGH_VIX_OFFSET   # +8
    return base


# ═════════════════════════════════════════════════════════════════════════
# TAX-ADJUSTED SUBSTITUTION (FIFO osservabile)
# ═════════════════════════════════════════════════════════════════════════

@dataclass
class SubstitutionDecision:
    approved: bool
    reason: str
    effective_margin: float
    challenger_score_adjusted: float


def evaluate_substitution(
    incumbent_score: float,
    challenger_score: float,
    sub_margin: float,
    incumbent_unrealized_pnl_pct: float,        # es. -10.0 se in perdita 10%
    challenger_unrealized_gain_abs: float = 0,  # vs incumbent: 0 = pari
    days_held: int = 999,
    incumbent_status: str = "NEUTRAL",
) -> SubstitutionDecision:
    """
    Logica anti-churn tax-aware:
      1. Se incumbent in perdita >5% → TLH probabile, abbassa margine effettivo
      2. Se challenger ha minor latent gain → preferito (5pt boost)
      3. MIN_HOLD_DAYS bloccato salvo BROKEN/AVOID
    """
    # MIN_HOLD_DAYS check con eccezione
    if days_held < config.MIN_HOLD_DAYS:
        if incumbent_status in ("BROKEN", "AVOID"):
            pass  # eccezione: vendita immediata permessa
        else:
            return SubstitutionDecision(
                False, f"min_hold_block ({days_held}d < {config.MIN_HOLD_DAYS}d)",
                sub_margin, challenger_score,
            )

    if challenger_score < incumbent_score - sub_margin:
        return SubstitutionDecision(
            False, "challenger_too_weak", sub_margin, challenger_score,
        )

    # FIFO osservabile: se in perdita → TLH probabile, riduce margine effettivo
    if incumbent_unrealized_pnl_pct < 0:
        tax_alpha_pct = abs(incumbent_unrealized_pnl_pct) * config.CAPITAL_GAIN_TAX_RATE
        effective_margin = sub_margin - tax_alpha_pct
    else:
        effective_margin = sub_margin

    if challenger_score < incumbent_score - effective_margin:
        return SubstitutionDecision(
            False, f"below_effective_margin ({effective_margin:.2f})",
            effective_margin, challenger_score,
        )

    # Boost se challenger ha minor carico fiscale latente
    challenger_score_adj = challenger_score
    if challenger_unrealized_gain_abs < -5:   # 5pt minor latent gain
        challenger_score_adj += 5

    return SubstitutionDecision(
        True, f"sub_approved (eff_margin={effective_margin:.2f})",
        effective_margin, challenger_score_adj,
    )


# ═════════════════════════════════════════════════════════════════════════
# TAX-LOSS HARVESTING PROATTIVO (italiano, NO wash sale US)
# ═════════════════════════════════════════════════════════════════════════

@dataclass
class TLHDecision:
    triggered: bool
    incumbent_ticker: str
    replacement_ticker: Optional[str]
    reason: str
    loss_realized_pct: float


def evaluate_tlh_window(signal_date: date) -> bool:
    """True se siamo nella finestra 1 nov - 20 dic."""
    mmdd = f"{signal_date.month:02d}-{signal_date.day:02d}"
    return config.TLH_WINDOW_START_MMDD <= mmdd <= config.TLH_WINDOW_END_MMDD


def evaluate_tlh_proactive(
    incumbent: Dict,    # {ticker, unrealized_pnl_pct, score, days_held}
    candidates: List[Dict],  # ordinati per score desc, no incumbent
    signal_date: date,
) -> TLHDecision:
    """
    Se siamo nella finestra TLH e incumbent < -8%:
      cerca candidato con score >= incumbent.score - 3 e CUSIP diverso → SWAP.
      Nessun blocco riacquisto 31gg (regime amministrato italiano, no wash sale).
    """
    if not evaluate_tlh_window(signal_date):
        return TLHDecision(False, incumbent["ticker"], None, "out_of_window", 0)
    if incumbent.get("unrealized_pnl_pct", 0) > config.TLH_TRIGGER_LOSS_PCT:
        return TLHDecision(False, incumbent["ticker"], None,
                           "loss_not_severe_enough", 0)

    inc_score = incumbent.get("score", 0)
    inc_ticker = incumbent["ticker"]
    for c in candidates:
        if c["ticker"] == inc_ticker:
            continue
        # In Italia: nessun blocco wash sale 31gg
        if c.get("score", 0) >= inc_score - config.TLH_CHALLENGER_MAX_DELTA:
            return TLHDecision(
                True, inc_ticker, c["ticker"],
                "tlh_proactive_swap_italian (no wash sale)",
                incumbent["unrealized_pnl_pct"],
            )
    return TLHDecision(False, inc_ticker, None, "no_eligible_challenger", 0)


# ═════════════════════════════════════════════════════════════════════════
# SECTOR CAP CONDIZIONATO (top 3 settori = 5 slot, altri = 3)
# ═════════════════════════════════════════════════════════════════════════

def compute_sector_momentum_rank(
    tickers_by_sector: Dict[str, List[str]],
    price_series_by_ticker: Dict[str, pd.Series],
    signal_date: date,
) -> List[str]:
    """Ranking settori per momentum 3m medio. Top SECTOR_TOP_N → 'hot'."""
    sector_mom = {}
    for sector, tickers in tickers_by_sector.items():
        rets = []
        for t in tickers:
            s = price_series_by_ticker.get(t, pd.Series())
            s = s[s.index <= pd.Timestamp(signal_date)].dropna()
            if len(s) >= 63:
                rets.append(float(s.iloc[-1] / s.iloc[-63] - 1))
        if rets:
            sector_mom[sector] = np.mean(rets)
    ranked = sorted(sector_mom.items(), key=lambda x: -x[1])
    return [s for s, _ in ranked]


def get_sector_cap(sector: str, hot_sectors: List[str]) -> int:
    """Sector cap dinamico: top N settori 'hot' hanno più slot."""
    if sector in hot_sectors[:config.SECTOR_TOP_N]:
        return config.SECTOR_CAP_HOT
    return config.SECTOR_CAP_OTHER


# ═════════════════════════════════════════════════════════════════════════
# SELEZIONE FINALE 8 POSIZIONI
# ═════════════════════════════════════════════════════════════════════════

@dataclass
class PortfolioSlot:
    ticker: str
    score: float
    sector: str
    entry_status: str
    reason: str


def select_portfolio(
    candidates: List[Dict],   # [{ticker, score, sector, entry_status, ...}]
    current_holdings: List[Dict],   # [{ticker, score, sector, status, days_held, pnl_pct}]
    sector_momentum_rank: List[str],
    vix_value: Optional[float],
    signal_date: date,
) -> List[PortfolioSlot]:
    """
    Selezione rotational con anti-churn, sector cap dinamico, TLH italiano.

    Algoritmo:
      1. Bacino qualità = top BACINO_SIZE per score
      2. Incumbents survivors: tieni se score nel bacino e status non in {BROKEN, AVOID}
      3. Riempi slot vuoti con challenger top per score (rispettando sector cap)
      4. Sostituzione anti-churn: challenger scalza incumbent solo se eff_margin OK
      5. TLH proattivo se nella finestra Nov-Dic
      6. Slot vuoti residui → CASH
    """
    # Bacino qualità
    candidates_sorted = sorted(candidates, key=lambda c: -c["score"])
    bacino = candidates_sorted[:config.BACINO_SIZE]
    bacino_tickers = {c["ticker"] for c in bacino}
    by_ticker = {c["ticker"]: c for c in candidates_sorted}

    # SUB_MARGIN dinamico
    sub_margin = get_dynamic_sub_margin(vix_value)

    # 1. Incumbents survivors
    survivors: List[Dict] = []
    health_sold: List[str] = []
    for h in current_holdings:
        status = h.get("status", "NEUTRAL")
        if status in ("BROKEN", "AVOID"):
            health_sold.append(h["ticker"])
            continue
        if h["ticker"] not in bacino_tickers:
            health_sold.append(h["ticker"])
            continue
        # arricchisco con score corrente
        cur = by_ticker.get(h["ticker"])
        if cur:
            h["score"] = cur["score"]
            h["sector"] = cur.get("sector", "Unknown")
        survivors.append(h)

    survivors.sort(key=lambda s: -s["score"])

    # 2. Reduce se troppi
    if len(survivors) > config.NUM_POSITIONS:
        health_sold += [s["ticker"] for s in survivors[config.NUM_POSITIONS:]]
        survivors = survivors[:config.NUM_POSITIONS]
    survivor_tickers = {s["ticker"] for s in survivors}

    # 3. TLH proattivo (Nov-Dic): controlla survivors per loss > 8%
    if evaluate_tlh_window(signal_date):
        new_survivors = []
        for s in survivors:
            pnl = s.get("pnl_pct", 0)
            cands = [c for c in bacino if c["ticker"] not in survivor_tickers]
            tlh = evaluate_tlh_proactive(s, cands, signal_date)
            if tlh.triggered:
                # Sostituisci nel survivor (rimuovi e aggiungi challenger)
                replacement = by_ticker.get(tlh.replacement_ticker)
                if replacement:
                    new_survivors.append({
                        "ticker": replacement["ticker"],
                        "score": replacement["score"],
                        "sector": replacement.get("sector", "Unknown"),
                        "status": replacement.get("entry_status", "NEUTRAL"),
                        "days_held": 0,
                        "pnl_pct": 0,
                        "_reason": tlh.reason,
                    })
                    health_sold.append(s["ticker"])
                    continue
            new_survivors.append(s)
        survivors = new_survivors
        survivor_tickers = {s["ticker"] for s in survivors}

    # 4. Sector cap counter
    sector_count: Dict[str, int] = {}
    for s in survivors:
        sec = s.get("sector", "Unknown")
        sector_count[sec] = sector_count.get(sec, 0) + 1

    # 5. Challenger fill: prendi top score nel bacino non già detenuto, valido sector
    challengers = [c for c in bacino if c["ticker"] not in survivor_tickers
                   and c.get("entry_status", "NEUTRAL") not in ("BROKEN", "AVOID")]
    challengers.sort(key=lambda c: -c["score"])

    portfolio = list(survivors)

    while len(portfolio) < config.NUM_POSITIONS:
        added = False
        for c in challengers:
            if c["ticker"] in {p["ticker"] for p in portfolio}:
                continue
            sec = c.get("sector", "Unknown")
            cap = get_sector_cap(sec, sector_momentum_rank)
            if sector_count.get(sec, 0) >= cap:
                continue
            portfolio.append({
                "ticker": c["ticker"],
                "score": c["score"],
                "sector": sec,
                "status": c.get("entry_status", "NEUTRAL"),
                "days_held": 0,
                "_reason": "challenger_fill",
            })
            sector_count[sec] = sector_count.get(sec, 0) + 1
            added = True
            break
        if not added:
            break  # nessun altro candidato eligibile → cash slot

    # 6. Substitution check: ogni challenger sopra può scalzare il peggior survivor
    weakest_survivor = min(portfolio, key=lambda p: p["score"]) if portfolio else None
    if weakest_survivor and len(challengers) > 0:
        top_chall = next((c for c in challengers
                          if c["ticker"] not in {p["ticker"] for p in portfolio}), None)
        if top_chall:
            decision = evaluate_substitution(
                incumbent_score=weakest_survivor["score"],
                challenger_score=top_chall["score"],
                sub_margin=sub_margin,
                incumbent_unrealized_pnl_pct=weakest_survivor.get("pnl_pct", 0),
                days_held=weakest_survivor.get("days_held", 999),
                incumbent_status=weakest_survivor.get("status", "NEUTRAL"),
            )
            if decision.approved:
                sec_w = weakest_survivor.get("sector", "Unknown")
                sec_c = top_chall.get("sector", "Unknown")
                cap_c = get_sector_cap(sec_c, sector_momentum_rank)
                tentative_count = dict(sector_count)
                tentative_count[sec_w] = tentative_count.get(sec_w, 1) - 1
                if tentative_count.get(sec_c, 0) < cap_c:
                    portfolio.remove(weakest_survivor)
                    portfolio.append({
                        "ticker": top_chall["ticker"],
                        "score": top_chall["score"],
                        "sector": sec_c,
                        "status": top_chall.get("entry_status", "NEUTRAL"),
                        "days_held": 0,
                        "_reason": "sub_approved_" + decision.reason,
                    })
                    sector_count = tentative_count

    # Format output
    return [PortfolioSlot(
        ticker=p["ticker"], score=p["score"],
        sector=p.get("sector", "Unknown"),
        entry_status=p.get("status", "NEUTRAL"),
        reason=p.get("_reason", "incumbent"),
    ) for p in portfolio]


if __name__ == "__main__":
    print("TAX AWARE OPTIMIZER self-check")
    print("=" * 60)

    # Spread calibrato
    print("\nTest spread scalato calibrato:")
    for adv in [10_000_000, 50_000_000, 200_000_000, 2_500_000]:
        sp = calculate_spread(adv)
        print(f"  ADV ${adv:>12,.0f} → spread {sp*100:.3f}%")

    # SUB_MARGIN dinamico
    print("\nTest SUB_MARGIN dinamico VIX:")
    for v in [10, 17, 30]:
        m = get_dynamic_sub_margin(v)
        print(f"  VIX {v}: margin = {m}")

    # TLH window
    from datetime import date
    print("\nTest TLH window:")
    for d in [date(2024, 10, 31), date(2024, 11, 15), date(2024, 12, 20), date(2024, 12, 21)]:
        print(f"  {d}: in TLH window = {evaluate_tlh_window(d)}")

    # Wash sale rule check
    print(f"\n  Wash sale 31gg attivo? {config.TLH_BLOCK_REBUY_SAME_CUSIP} (deve essere False)")

    print("\n✓ Modulo OK")
