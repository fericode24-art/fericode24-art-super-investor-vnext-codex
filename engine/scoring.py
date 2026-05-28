"""
Motore di scoring composito a 6 fattori.

Per ogni titolo (ticker) calcola:
  composite = 0.30*conviction + 0.15*insider + 0.15*quality
            + 0.10*value     + 0.15*momentum + 0.15*emerging_trend

Tutti i singoli score sono normalizzati 0-100 nell'universo analizzato.
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict
from typing import Optional
import numpy as np


WEIGHTS = {
    "conviction": 0.15,   # ridotto: non vogliamo che "tutti tengono X" domini
    "insider": 0.20,      # alzato: segnale forte di chi sta DENTRO l'azienda
    "quality": 0.15,
    "value": 0.05,
    "momentum": 0.20,     # alzato: cattura trend reali
    "emerging": 0.25,     # alzato: cuore dei picks "che spuntano dal nulla"
}

# Soglie per evitare dominanza singolo fondo / overcrowded names
MAX_SINGLE_FUND_CONTRIBUTION = 0.15   # un fondo solo non pesa > 15% dello score conviction
CROWDED_PENALTY_THRESHOLD = 25         # se più di N fondi tengono il titolo, scala (è benchmark, non signal)
MIN_HIGH_CONVICTION_PCT = 3.0          # un titolo "conta" come high conviction solo se pesa > 3% del portafoglio del fondo


def fund_effective_weight(fund: dict) -> float:
    """Peso effettivo di un fondo (base × type × recent_skill_multiplier)."""
    base = fund.get("base_weight", 0.5)
    fund_type = fund.get("type", "generalist")
    type_mult = {
        "value_legend": 1.3,
        "concentrated_picker": 1.25,
        "activist": 1.2,
        "growth_picker": 1.15,
        "tiger_cub": 1.15,
        "macro_quant": 1.1,
        "generalist": 0.9,
    }.get(fund_type, 1.0)
    # recent_skill_multiplier: settato dal main.py dopo aver letto Yahoo,
    # range 0.5-1.8 in base al return medio delle top 10 posizioni 3-6M
    skill_mult = fund.get("recent_skill_mult", 1.0)
    return base * type_mult * skill_mult


def compute_recent_skill_multipliers(funds: list[dict], holdings_by_fund: dict, momentum: dict) -> dict:
    """
    Per ogni fondo, calcola moltiplicatore "sul pezzo o no":
      - prende top 10 posizioni del fondo
      - per quelle con momentum disponibile, media il ret_3m
      - mappa: ret_3m medio → moltiplicatore 0.5..1.8
        ret_3m  =  -20% → 0.5  (sta sbagliando)
        ret_3m  =    0% → 1.0  (neutro)
        ret_3m  =  +20% → 1.5  (sul pezzo)
        ret_3m  =  +40% → 1.8  (caldissimo)
    """
    out = {}
    for f in funds:
        cik = f["cik"]
        hlist = holdings_by_fund.get(cik, [])
        if not hlist:
            out[cik] = 1.0
            continue
        # top 10 per pct_of_portfolio
        top = sorted(hlist, key=lambda h: -(h.get("pct_of_portfolio", 0) or 0))[:10]
        rets = []
        weights = []
        for h in top:
            t = h.get("ticker")
            if not t or t not in momentum:
                continue
            m = momentum[t]
            if not m.get("available"):
                continue
            r3 = m.get("ret_3m")
            if r3 is None:
                continue
            rets.append(r3)
            weights.append(h.get("pct_of_portfolio", 1) or 1)
        if not rets:
            out[cik] = 1.0
            continue
        # weighted avg ret_3m
        wavg = sum(r * w for r, w in zip(rets, weights)) / sum(weights)
        # mapping lineare: -20% → 0.5, 0% → 1.0, +20% → 1.5, +40% → 1.8
        if wavg <= -20:
            mult = 0.5
        elif wavg <= 0:
            mult = 1.0 + wavg / 40  # 0%→1.0, -20%→0.5
        elif wavg <= 40:
            mult = 1.0 + wavg / 40  # +20%→1.5, +40%→2.0
            mult = min(mult, 1.8)
        else:
            mult = 1.8
        out[cik] = round(mult, 3)
    return out


def conviction_score(holdings_by_fund: dict, funds: list[dict], all_tickers: list[str]) -> dict:
    """
    Conviction RIDISEGNATA per evitare dominanza:
    - Conta SOLO posizioni "high conviction" del fondo (>3% del portafoglio)
    - Cap contributo singolo fondo (anche Buffett non domina)
    - Penalità per titoli "overcrowded" (tenuti da troppi fondi = benchmark, non signal)
    """
    fund_lookup = {f["cik"]: f for f in funds}
    # per ogni ticker, lista (fund_cik, fund_weight, position_emphasis)
    ticker_contribs = defaultdict(list)
    fund_count = defaultdict(int)
    high_conv_count = defaultdict(int)

    for cik, hlist in holdings_by_fund.items():
        if cik not in fund_lookup:
            continue
        w = fund_effective_weight(fund_lookup[cik])
        n_pos = len(hlist)
        conc_mult = 1.5 if n_pos < 30 else (1.2 if n_pos < 50 else 1.0)
        for h in hlist:
            t = h.get("ticker")
            if not t:
                continue
            pct = h.get("pct_of_portfolio", 0) or 0
            fund_count[t] += 1
            # contributo SOLO se è high conviction per il fondo
            if pct >= MIN_HIGH_CONVICTION_PCT:
                high_conv_count[t] += 1
                # position emphasis basato sul peso reale (più importante è la posizione, più conta)
                position_emphasis = min(2.5, 1.0 + pct / 10)
                contrib = w * conc_mult * position_emphasis
                ticker_contribs[t].append(contrib)

    # Filtra: titoli con almeno 2 fondi che lo tengono come high conviction
    raw = {}
    total_contributions = {}
    for t, contribs in ticker_contribs.items():
        if high_conv_count[t] < 2:
            continue
        total = sum(contribs)
        # Cap contributo del singolo fondo top: nessuno deve dominare
        if contribs:
            max_contrib = max(contribs)
            cap = total * MAX_SINGLE_FUND_CONTRIBUTION
            if max_contrib > cap:
                # ridistribuiamo l'eccedenza riducendo solo il max
                excess = max_contrib - cap
                total -= excess
        # Penalità "overcrowded": se troppi fondi lo tengono, è benchmark
        n_funds = fund_count[t]
        if n_funds > CROWDED_PENALTY_THRESHOLD:
            penalty = 1.0 - min(0.5, (n_funds - CROWDED_PENALTY_THRESHOLD) / 50)
            total *= penalty
        raw[t] = total
        total_contributions[t] = total

    if not raw:
        return {}

    # Normalizza 0-100
    values = list(raw.values())
    mx = max(values)
    mn = min(values)
    rng = (mx - mn) or 1
    return {t: round((v - mn) / rng * 100, 2) for t, v in raw.items()}


def insider_score_from_signals(insider_signals: dict) -> dict:
    """insider_signals: { ticker: {n_recent_form4, score} }"""
    if not insider_signals:
        return {}
    scores = {t: s.get("score", 0) for t, s in insider_signals.items()}
    # già 0-100, ma re-normalize all'universo
    if not scores:
        return {}
    mx = max(scores.values()) or 1
    return {t: round(v / mx * 100, 2) for t, v in scores.items()}


def quality_score(quotes: dict) -> dict:
    """
    Fattori quality: ROE, ROA, gross/op margin, debt_to_equity (inverso).
    quotes: { ticker: {...} }
    """
    metrics = {}
    for t, q in quotes.items():
        if q.get("error"):
            continue
        roe = q.get("roe") or 0
        roa = q.get("roa") or 0
        gm = q.get("gross_margin") or 0
        om = q.get("operating_margin") or 0
        de = q.get("debt_to_equity")
        de_score = 0
        if de is not None:
            # debt_to_equity: <50 ottimo, >200 male
            de_score = max(0, 1 - (de / 200))
        composite = (
            (roe or 0) * 100 * 0.30 +  # ROE è frazionale
            (roa or 0) * 100 * 0.20 +
            (gm or 0) * 100 * 0.20 +
            (om or 0) * 100 * 0.20 +
            de_score * 10
        )
        metrics[t] = composite

    if not metrics:
        return {}
    vals = list(metrics.values())
    mx = max(vals) or 1
    mn = min(vals)
    rng = (mx - mn) or 1
    return {t: round((v - mn) / rng * 100, 2) for t, v in metrics.items()}


def value_score(quotes: dict) -> dict:
    """Value: inverso di PE forward + EV/EBITDA. Più basso = più value."""
    metrics = {}
    for t, q in quotes.items():
        if q.get("error"):
            continue
        pe = q.get("pe_forward") or q.get("pe_trailing")
        ev_ebitda = q.get("ev_ebitda")
        if not pe and not ev_ebitda:
            continue
        # invertiamo: più basso il multiplo, più alto lo score
        pe_score = 0
        if pe and pe > 0:
            pe_score = max(0, 50 - pe)  # PE 0 → 50, PE 50 → 0
        ev_score = 0
        if ev_ebitda and ev_ebitda > 0:
            ev_score = max(0, 30 - ev_ebitda)
        metrics[t] = pe_score + ev_score

    if not metrics:
        return {}
    vals = list(metrics.values())
    mx = max(vals) or 1
    mn = min(vals)
    rng = (mx - mn) or 1
    return {t: round((v - mn) / rng * 100, 2) for t, v in metrics.items()}


def momentum_score(momentum_data: dict) -> dict:
    """
    Score: 0.4*ret_3m + 0.3*ret_6m + 0.2*ret_12m + 0.1*above_ma50
    Penalità se RSI > 80 (overbought) o < 30 (downtrend forte).
    """
    metrics = {}
    for t, m in momentum_data.items():
        if not m.get("available"):
            continue
        r1 = m.get("ret_1m") or 0
        r3 = m.get("ret_3m") or 0
        r6 = m.get("ret_6m") or 0
        r12 = m.get("ret_12m") or 0
        above50 = 10 if m.get("above_ma50") else 0
        above200 = 10 if m.get("above_ma200") else 0
        rsi = m.get("rsi_14") or 50
        penalty = 0
        if rsi > 80:
            penalty = (rsi - 80) * 2  # overbought
        elif rsi < 30:
            penalty = (30 - rsi) * 2  # forte downtrend
        composite = r3 * 0.4 + r6 * 0.3 + r12 * 0.2 + r1 * 0.1 + above50 + above200 - penalty
        metrics[t] = composite

    if not metrics:
        return {}
    vals = list(metrics.values())
    mx = max(vals)
    mn = min(vals)
    rng = (mx - mn) or 1
    return {t: round((v - mn) / rng * 100, 2) for t, v in metrics.items()}


def emerging_trend_score(
    holdings_by_fund: dict,
    momentum_data: dict,
    prev_top_set: Optional[set] = None,
) -> dict:
    """
    Cattura "titoli che spuntano dal nulla":
      - alto volume_ratio (volumi recenti > medi)
      - momentum 1M elevato MA non ancora 12M (titoli nuovi sul radar)
      - già 2+ fondi entrati ultimo trimestre (proxy: presenti nei 13F)
    """
    metrics = {}
    prev_top_set = prev_top_set or set()
    for t, m in momentum_data.items():
        if not m.get("available"):
            continue
        vol_ratio = m.get("volume_ratio_recent_vs_prior") or 1
        r1 = m.get("ret_1m") or 0
        r12 = m.get("ret_12m") or 0
        # boost: r1m positivo forte, r12m moderato (nuovo trend)
        new_trend = max(0, r1) - max(0, r12 / 6)  # incentiva accelerazione
        vol_boost = max(0, (vol_ratio - 1) * 50)  # vol_ratio 2 → +50
        novelty_boost = 20 if t not in prev_top_set else 0
        composite = new_trend + vol_boost + novelty_boost
        metrics[t] = composite

    if not metrics:
        return {}
    vals = list(metrics.values())
    mx = max(vals) or 1
    mn = min(vals)
    rng = (mx - mn) or 1
    return {t: round((v - mn) / rng * 100, 2) for t, v in metrics.items()}


def composite_rank(
    conviction: dict,
    insider: dict,
    quality: dict,
    value: dict,
    momentum: dict,
    emerging: dict,
    top_n: int = 12,
) -> list[dict]:
    """Combina i 6 fattori, ritorna i top N ordinati."""
    all_tickers = set(conviction) | set(insider) | set(quality) | set(value) | set(momentum) | set(emerging)
    ranked = []
    for t in all_tickers:
        c = conviction.get(t, 0)
        i = insider.get(t, 0)
        q = quality.get(t, 0)
        v = value.get(t, 0)
        m = momentum.get(t, 0)
        e = emerging.get(t, 0)
        composite = (
            WEIGHTS["conviction"] * c
            + WEIGHTS["insider"] * i
            + WEIGHTS["quality"] * q
            + WEIGHTS["value"] * v
            + WEIGHTS["momentum"] * m
            + WEIGHTS["emerging"] * e
        )
        ranked.append({
            "ticker": t,
            "composite_score": round(composite, 2),
            "breakdown": {
                "conviction": c,
                "insider": i,
                "quality": q,
                "value": v,
                "momentum": m,
                "emerging": e,
            },
        })
    ranked.sort(key=lambda x: -x["composite_score"])
    return ranked[:top_n]
