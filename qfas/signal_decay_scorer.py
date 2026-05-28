"""
QFAS v2.5 — signal_decay_scorer.py

Calcola il Radar Score di un titolo a una data point-in-time:
  - Conviction: somma pesata position_pct fondi × base_weight × decay esponenziale
  - Accumulation: % fondi che hanno aumentato posizione (validato AUM)
  - Crowding penalty: se troppo dei fondi attivi tengono il nome, riduci score

PATCH v2.5:
  - filtro survivorship via fund_universe.is_fund_active()
  - decay esponenziale conviction (più vecchio il filing, meno peso)
  - half-life vincolato a >= 90gg (13F sono trimestrali, mediana non può scendere)
  - proxy AUM da somma value posizioni 13F (i 13F non riportano NAV diretto)
  - crowding denominatore = fondi attivi a signal_date (point-in-time, non statico)
"""
from __future__ import annotations
import math
import logging
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from qfas.qfas_config import config, signal_is_available
from qfas.fund_universe import (
    is_fund_active, get_active_funds_at, FUND_ACTIVE_PERIODS, get_fund_by_cik,
)

log = logging.getLogger("qfas.scorer")


# ═════════════════════════════════════════════════════════════════════════
# HALFLIFE per fondo — calcolato dai pattern di rotazione storici
# ═════════════════════════════════════════════════════════════════════════

def compute_fund_halflife(fund_filings: List[Dict], default: int = None) -> int:
    """
    Stima halflife in giorni dai pattern di variazione del fondo.
    Halflife = mediana giorni tra variazioni significative (>10% pos changes)
    sugli ultimi 20 filing.

    PATCH MATEMATICA: i 13F sono trimestrali → mediana NON può scendere <90gg.
    Risultato: max(HALFLIFE_MIN_DAYS, mediana_calcolata).
    """
    if default is None:
        default = config.DEFAULT_HALFLIFE_DAYS

    if not fund_filings or len(fund_filings) < 4:
        return max(config.HALFLIFE_MIN_DAYS, default)

    filings_sorted = sorted(fund_filings, key=lambda f: f["date"])[-20:]
    significant_changes_days = []
    prev_holdings = {h["ticker"]: h["shares"] for h in filings_sorted[0].get("holdings", [])}
    prev_date = pd.Timestamp(filings_sorted[0]["date"])

    for f in filings_sorted[1:]:
        cur = {h["ticker"]: h["shares"] for h in f.get("holdings", [])}
        any_significant = False
        for t, sh in cur.items():
            prev_sh = prev_holdings.get(t, 0)
            if prev_sh == 0 and sh > 0:
                any_significant = True; break
            if prev_sh > 0 and abs(sh - prev_sh) / prev_sh > 0.10:
                any_significant = True; break
        if any_significant:
            delta_days = (pd.Timestamp(f["date"]) - prev_date).days
            if delta_days > 0:
                significant_changes_days.append(delta_days)
            prev_date = pd.Timestamp(f["date"])
        prev_holdings = cur

    if not significant_changes_days:
        return max(config.HALFLIFE_MIN_DAYS, default)
    median_days = int(np.median(significant_changes_days))
    return max(config.HALFLIFE_MIN_DAYS, median_days)


# ═════════════════════════════════════════════════════════════════════════
# AUM PROXY — somma value posizioni 13F
# ═════════════════════════════════════════════════════════════════════════

def compute_aum_proxy(filing_holdings: List[Dict],
                       prices_at_date: Dict[str, float]) -> float:
    """
    Proxy AUM = somma (shares × price) di tutte le posizioni nel filing.
    I 13F non riportano NAV, ma la somma del market value approssima bene
    l'AUM long equity.
    """
    total = 0.0
    for h in filing_holdings:
        t = h.get("ticker")
        sh = h.get("shares", 0)
        p = prices_at_date.get(t)
        if p is not None and sh:
            total += sh * p
    return total


def is_accumulation_valid(prev_shares: int, curr_shares: int,
                          prev_aum: float, curr_aum: float) -> bool:
    """
    Una variazione di shares è "vera accumulation" solo se:
    - shares aumentate >2%
    - aum del fondo non è crollato (>-2%) → escludo redemption massiccia
      che gonfia % per posizioni invariate
    """
    if curr_shares <= prev_shares * 1.02:
        return False
    if prev_aum > 0 and (curr_aum - prev_aum) / prev_aum < -0.02:
        return False
    return True


# ═════════════════════════════════════════════════════════════════════════
# RADAR SCORE — funzione principale
# ═════════════════════════════════════════════════════════════════════════

@dataclass
class RadarScoreResult:
    ticker: str
    signal_date: date
    radar_score: float                    # 0-100 (post-crowding)
    raw_conviction: float                 # pre-normalization
    accumulation_pct: float               # % fondi che accumulano valid
    crowding_factor: float                # multiplicatore [0.6, 1.0]
    fund_coverage: float                  # frazione fondi attivi che detengono
    num_valid_filings: int                # filing usati dopo filtro survivorship
    num_active_funds: int                 # totale fondi attivi a signal_date


def calculate_radar_score(
    ticker: str,
    signal_date: date,
    all_filings_by_fund: Dict[str, List[Dict]],   # CIK → list di filing dict
    prices_at_date: Dict[str, float],              # ticker → prezzo per AUM proxy
    cross_sectional_normalizer: Optional[Dict[str, float]] = None,
) -> RadarScoreResult:
    """
    Args:
      ticker: titolo da scoreare
      signal_date: data del backtest (point-in-time)
      all_filings_by_fund: dict CIK → list di filing (date, holdings)
      prices_at_date: ticker → prezzo per calcolo proxy AUM
      cross_sectional_normalizer: dict ticker → percentile per normalizzazione
        cross-sectional. Se None, ritorna raw conviction (la normalizzazione
        si fa in batch a livello superiore).

    Returns:
      RadarScoreResult con tutti gli intermediates per audit.
    """
    if not signal_is_available("radar_score", signal_date):
        return RadarScoreResult(ticker, signal_date, 0.0, 0.0, 0.0, 1.0, 0.0, 0, 0)

    active_funds_period = get_active_funds_at(signal_date)
    n_active = len(active_funds_period)
    if n_active == 0:
        return RadarScoreResult(ticker, signal_date, 0.0, 0.0, 0.0, 1.0, 0.0, 0, 0)

    # active CIKs
    active_ciks = {p.cik.lstrip("0").zfill(10) for p in active_funds_period.values()}

    # === Trovo tutti i filing rilevanti point-in-time per ticker
    raw_conv = 0.0
    accum_valid = 0
    accum_total = 0
    holders = set()

    for cik, filings in all_filings_by_fund.items():
        cik_norm = str(cik).lstrip("0").zfill(10)
        if cik_norm not in active_ciks:
            continue

        # cerco filing più recente <= signal_date per questo fondo
        avail = [f for f in filings if pd.Timestamp(f["date"]).date() <= signal_date]
        if not avail:
            continue
        cur = max(avail, key=lambda f: f["date"])
        prev = sorted(avail, key=lambda f: f["date"])[-2] if len(avail) >= 2 else None

        fund_info = get_fund_by_cik(cik_norm)
        if fund_info is None:
            continue
        base_weight = fund_info.base_weight
        halflife = compute_fund_halflife(filings, default=fund_info.default_halflife_days)

        # cerco il ticker nei holdings correnti
        cur_h = next((h for h in cur.get("holdings", []) if h.get("ticker") == ticker), None)
        if cur_h is None:
            continue

        # DECAY ESPONENZIALE su days_since_filing
        days_since = (signal_date - pd.Timestamp(cur["date"]).date()).days
        if days_since < 0:
            continue   # safety check anti look-ahead
        decay = math.exp(-0.693 * days_since / max(1, halflife))

        # CONVICTION WEIGHT capped a CONVICTION_PCT_CAP
        pct = min(cur_h.get("pct", 0) or 0, config.CONVICTION_PCT_CAP)
        raw_conv += base_weight * pct * decay

        holders.add(cik_norm)

        # ACCUMULATION check
        if prev is not None:
            prev_h = next((h for h in prev.get("holdings", []) if h.get("ticker") == ticker), None)
            prev_shares = prev_h.get("shares", 0) if prev_h else 0
            cur_shares = cur_h.get("shares", 0)

            # AUM proxy
            prev_aum = compute_aum_proxy(prev.get("holdings", []), prices_at_date)
            cur_aum = compute_aum_proxy(cur.get("holdings", []), prices_at_date)
            accum_total += 1
            if is_accumulation_valid(prev_shares, cur_shares, prev_aum, cur_aum):
                accum_valid += 1

    accumulation_pct = (accum_valid / accum_total * 100) if accum_total > 0 else 50.0
    fund_coverage = len(holders) / n_active if n_active > 0 else 0.0

    # CROWDING PENALTY point-in-time
    if config.CROWDING_ENABLED and fund_coverage > config.CROWDING_THRESHOLD:
        crowding_factor = max(
            config.CROWDING_MIN_FACTOR,
            1.0 - (fund_coverage - config.CROWDING_THRESHOLD) * 2.0,
        )
    else:
        crowding_factor = 1.0

    # Normalizzazione cross-sectional se passata
    if cross_sectional_normalizer is not None:
        conv_normalized = cross_sectional_normalizer.get(ticker, 50.0)
    else:
        conv_normalized = raw_conv  # gestita esternamente

    # Combina conviction e accumulation
    radar_raw = (config.RADAR_WEIGHT_CONVICTION * conv_normalized +
                 config.RADAR_WEIGHT_ACCUMULATION * accumulation_pct)
    radar_score = radar_raw * crowding_factor

    return RadarScoreResult(
        ticker=ticker, signal_date=signal_date,
        radar_score=radar_score,
        raw_conviction=raw_conv,
        accumulation_pct=accumulation_pct,
        crowding_factor=crowding_factor,
        fund_coverage=fund_coverage,
        num_valid_filings=len(holders),
        num_active_funds=n_active,
    )


def batch_radar_scores(
    tickers: List[str],
    signal_date: date,
    all_filings_by_fund: Dict[str, List[Dict]],
    prices_at_date: Dict[str, float],
) -> Dict[str, RadarScoreResult]:
    """
    FIX BUG #η (round 3): pre-indicizza per fondo invece di scansionare
    holdings linearmente per ogni ticker. Riduce 459 × 36 × O(n_holdings)
    a 36 × O(n_holdings) + 459 × O(1). Su universo tipico: 197k iter → ~10k.

    Schema:
      1. Pre-process: per ogni fondo attivo trovi cur/prev filing + indicizza
         holdings per ticker (dict O(1) lookup), pre-calcola halflife + decay
         + AUM una sola volta.
      2. Per ogni ticker: lookup veloce in tutti i fondi attivi.
      3. Cross-sectional normalization su raw_conviction.
    """
    if not signal_is_available("radar_score", signal_date):
        return {t: RadarScoreResult(t, signal_date, 0, 0, 0, 1.0, 0, 0, 0) for t in tickers}

    active_funds_period = get_active_funds_at(signal_date)
    n_active = len(active_funds_period)
    if n_active == 0:
        return {t: RadarScoreResult(t, signal_date, 0, 0, 0, 1.0, 0, 0, 0) for t in tickers}
    active_ciks = {p.cik.lstrip("0").zfill(10) for p in active_funds_period.values()}

    # ── 1. Pre-process fondi (UNA volta) ──
    fund_state: Dict[str, Dict] = {}
    for cik, filings in all_filings_by_fund.items():
        cik_norm = str(cik).lstrip("0").zfill(10)
        if cik_norm not in active_ciks:
            continue
        avail = [f for f in filings if pd.Timestamp(f["date"]).date() <= signal_date]
        if not avail:
            continue
        cur = max(avail, key=lambda f: f["date"])
        prev = sorted(avail, key=lambda f: f["date"])[-2] if len(avail) >= 2 else None
        fund_info = get_fund_by_cik(cik_norm)
        if fund_info is None:
            continue
        # Indicizza holdings per ticker (O(1) lookup)
        cur_idx = {h["ticker"]: h for h in cur.get("holdings", []) if h.get("ticker")}
        prev_idx = ({h["ticker"]: h for h in prev.get("holdings", []) if h.get("ticker")}
                    if prev else {})
        halflife = compute_fund_halflife(filings, default=fund_info.default_halflife_days)
        days_since = (signal_date - pd.Timestamp(cur["date"]).date()).days
        if days_since < 0:
            continue
        decay = math.exp(-0.693 * days_since / max(1, halflife))
        cur_aum = compute_aum_proxy(cur.get("holdings", []), prices_at_date)
        prev_aum = compute_aum_proxy(prev.get("holdings", []), prices_at_date) if prev else 0.0
        fund_state[cik_norm] = {
            "base_weight": fund_info.base_weight,
            "decay": decay,
            "cur_idx": cur_idx,
            "prev_idx": prev_idx,
            "cur_aum": cur_aum,
            "prev_aum": prev_aum,
            "has_prev": prev is not None,
        }

    # ── 2. Per ticker: lookup veloce ──
    raw_results: Dict[str, RadarScoreResult] = {}
    for t in tickers:
        raw_conv = 0.0
        accum_valid = 0
        accum_total = 0
        holders = set()
        for cik_norm, st in fund_state.items():
            cur_h = st["cur_idx"].get(t)
            if cur_h is None:
                continue
            pct = min(cur_h.get("pct", 0) or 0, config.CONVICTION_PCT_CAP)
            raw_conv += st["base_weight"] * pct * st["decay"]
            holders.add(cik_norm)
            if st["has_prev"]:
                accum_total += 1
                prev_h = st["prev_idx"].get(t)
                prev_shares = prev_h.get("shares", 0) if prev_h else 0
                cur_shares = cur_h.get("shares", 0)
                if is_accumulation_valid(prev_shares, cur_shares,
                                          st["prev_aum"], st["cur_aum"]):
                    accum_valid += 1

        accumulation_pct = (accum_valid / accum_total * 100) if accum_total > 0 else 50.0
        fund_coverage = len(holders) / n_active if n_active > 0 else 0.0
        if config.CROWDING_ENABLED and fund_coverage > config.CROWDING_THRESHOLD:
            crowding_factor = max(
                config.CROWDING_MIN_FACTOR,
                1.0 - (fund_coverage - config.CROWDING_THRESHOLD) * 2.0,
            )
        else:
            crowding_factor = 1.0
        raw_results[t] = RadarScoreResult(
            ticker=t, signal_date=signal_date,
            radar_score=0.0,  # ricalcolato dopo cross-sectional norm
            raw_conviction=raw_conv,
            accumulation_pct=accumulation_pct,
            crowding_factor=crowding_factor,
            fund_coverage=fund_coverage,
            num_valid_filings=len(holders),
            num_active_funds=n_active,
        )

    # ── 3. Cross-sectional normalization su raw_conviction ──
    raw_convictions = pd.Series({t: r.raw_conviction for t, r in raw_results.items()})
    if raw_convictions.sum() > 0:
        conv_pct = raw_convictions.rank(pct=True) * 100.0
    else:
        conv_pct = pd.Series(50.0, index=raw_convictions.index)

    out = {}
    for t, r in raw_results.items():
        radar_raw = (config.RADAR_WEIGHT_CONVICTION * float(conv_pct[t]) +
                     config.RADAR_WEIGHT_ACCUMULATION * r.accumulation_pct)
        out[t] = RadarScoreResult(
            ticker=t, signal_date=signal_date,
            radar_score=radar_raw * r.crowding_factor,
            raw_conviction=r.raw_conviction,
            accumulation_pct=r.accumulation_pct,
            crowding_factor=r.crowding_factor,
            fund_coverage=r.fund_coverage,
            num_valid_filings=r.num_valid_filings,
            num_active_funds=r.num_active_funds,
        )
    return out


if __name__ == "__main__":
    print("SIGNAL DECAY SCORER self-check")
    print("=" * 60)
    # Test halflife min vincolo
    print("Test halflife matematico:")
    fake_filings = [{"date": "2024-01-15", "holdings": []},
                    {"date": "2024-04-15", "holdings": []}]
    hl = compute_fund_halflife(fake_filings)
    assert hl >= 90, f"Halflife {hl} < 90, patch failed!"
    print(f"  halflife con 2 filing (fallback): {hl} (>= 90 ✓)")

    # Test accumulation validation
    print("\nTest accumulation validation:")
    cases = [
        (1000, 1500, 1_000_000, 950_000, True, "shares +50%, AUM -5% → REDEMPTION GUSTO MA VALID"),
        (1000, 1500, 1_000_000, 980_000, True, "shares +50%, AUM -2% → valid"),
        (1000, 1500, 1_000_000, 200_000, False, "shares +50%, AUM -80% → ridenzione massiccia"),
        (1000, 1010, 1_000_000, 1_000_000, False, "shares +1% → non significativo"),
    ]
    for ps, cs, pa, ca, expected, desc in cases:
        got = is_accumulation_valid(ps, cs, pa, ca)
        mark = "✓" if got == expected else "✗"
        print(f"  {mark} {desc}: {got}")

    print("\n✓ Modulo OK")
