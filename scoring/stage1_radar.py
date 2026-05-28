"""
STAGE 1 — RADAR SCORE (dati lenti, cache 7gg)

Radar Score = Conviction 40% + Accumulation Trend 30% + Insider Quality 30%
              + modifier Congressional [0,+5] + modifier Short [-15,+15]
Cap finale [0, 130].

NOTA FASE 1: Insider Quality, Congressional e Short sono PLACEHOLDER.
  - Insider: usa il conteggio Form 4 grezzo da sec_edgar (Fase 2 → scoring qualitativo)
  - Congressional / Short: ritornano 0 (Fase 2 → CapitolTrades / FINRA)
Tutti i punti d'innesto sono marcati con [FASE 2].
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Optional

from .cfg import load_config, clip, normalize_0_100

TYPE_MULT = {
    "value_legend": 1.3,
    "concentrated_picker": 1.25,
    "activist": 1.2,
    "tiger_cub": 1.15,
    "growth_picker": 1.15,
    "generalist": 0.9,
}


# ─────────────────────────── Fund weight & skill ───────────────────────────
def fund_effective_weight(fund: dict) -> float:
    """base_weight × type_multiplier × recent_skill_mult."""
    base = fund.get("base_weight", 0.5)
    tmult = TYPE_MULT.get(fund.get("type", "generalist"), 1.0)
    skill = fund.get("recent_skill_mult", 1.0)
    return base * tmult * skill


def compute_skill_multipliers(funds: list[dict], holdings_by_fund: dict, momentum: dict) -> dict:
    """
    Moltiplicatore "sul pezzo": media ret_3m delle top 10 posizioni del fondo.
    Fondi con < min_quarters_required di storico → 1.0 (neutro).
    Mapping: -20%→0.5, 0%→1.0, +20%→1.5, +40%+→1.8 (cap).
    """
    cfg = load_config()
    min_q = cfg["skill_multiplier"]["min_quarters_required"]
    out = {}
    for f in funds:
        cik = f["cik"]
        fund_data = holdings_by_fund.get(cik, {})
        current = fund_data.get("current")
        # fondi nuovi senza abbastanza storico → neutro
        if not current or fund_data.get("quarters_available", 0) < min_q:
            out[cik] = 1.0
            continue
        hlist = current.get("holdings", [])
        top = sorted(hlist, key=lambda h: -(h.get("pct_of_portfolio", 0) or 0))[:10]
        rets, weights = [], []
        for h in top:
            t = h.get("ticker")
            m = momentum.get(t) if t else None
            if not m or not m.get("available"):
                continue
            r3 = m.get("ret_3m")
            if r3 is None:
                continue
            rets.append(r3)
            weights.append(h.get("pct_of_portfolio", 1) or 1)
        if not rets:
            out[cik] = 1.0
            continue
        wavg = sum(r * w for r, w in zip(rets, weights)) / sum(weights)
        if wavg <= -20:
            mult = 0.5
        elif wavg <= 40:
            mult = clip(1.0 + wavg / 40, 0.5, 1.8)
        else:
            mult = 1.8
        out[cik] = round(mult, 3)
    return out


# ─────────────────────────── Freshness decay ───────────────────────────
def decay_factor(filing_date: str, half_life_days: int) -> float:
    """0.5 ^ (giorni_da_filing / half_life). 13F sempre 45+ gg vecchi."""
    try:
        d = datetime.fromisoformat(filing_date)
        days = (datetime.now() - d).days
        return 0.5 ** (max(0, days) / half_life_days)
    except Exception:
        return 0.6  # fallback ragionevole per un 13F tipico


# ─────────────────────────── Conviction (40%) ───────────────────────────
def compute_conviction(holdings_by_fund: dict, funds: list[dict]) -> dict:
    """
    Conviction: somma pesata dei fondi che tengono il titolo come HIGH conviction
    (>conviction_threshold_pct del loro portafoglio).
    Anti-dominanza: cap singolo fondo 15%, penalità overcrowded >25 fondi.
    """
    cfg = load_config()
    thr = cfg["filters"]["conviction_threshold_pct"]
    cap_pct = cfg["filters"]["fund_dominance_cap_pct"] / 100.0
    half_life = cfg["freshness_decay"]["half_life_days"]
    fund_lookup = {f["cik"]: f for f in funds}

    contribs = defaultdict(list)
    fund_count = defaultdict(int)
    high_conv_count = defaultdict(int)

    for cik, fdata in holdings_by_fund.items():
        fund = fund_lookup.get(cik)
        current = fdata.get("current")
        if not fund or not current:
            continue
        w = fund_effective_weight(fund)
        decay = decay_factor(current.get("date", ""), half_life)
        n_pos = len(current.get("holdings", []))
        conc_mult = 1.5 if n_pos < 30 else (1.2 if n_pos < 50 else 1.0)
        for h in current.get("holdings", []):
            t = h.get("ticker")
            if not t:
                continue
            fund_count[t] += 1
            pct = h.get("pct_of_portfolio", 0) or 0
            if pct >= thr:
                high_conv_count[t] += 1
                emphasis = min(2.5, 1.0 + pct / 10)
                contribs[t].append(w * conc_mult * decay * emphasis)

    raw = {}
    for t, clist in contribs.items():
        if high_conv_count[t] < 2:
            continue
        total = sum(clist)
        # cap singolo fondo
        mx = max(clist)
        cap = total * cap_pct
        if mx > cap:
            total -= (mx - cap)
        # penalità overcrowded
        if fund_count[t] > 25:
            total *= 1.0 - min(0.5, (fund_count[t] - 25) / 50)
        raw[t] = total
    return normalize_0_100(raw)


# ─────────────────────────── Accumulation Trend (30%) ───────────────────────────
def compute_accumulation(holdings_by_fund: dict, funds: list[dict]) -> dict:
    """
    Accumulation Trend: confronta la size delle posizioni current vs previous 13F.
    +2 nuova posizione, +1..+2 incremento, 0 stabile, -1 riduzione.
    Pesato per qualità del fondo. Normalizzato 0-100.
    """
    fund_lookup = {f["cik"]: f for f in funds}
    raw = defaultdict(float)

    for cik, fdata in holdings_by_fund.items():
        fund = fund_lookup.get(cik)
        current = fdata.get("current")
        previous = fdata.get("previous")
        if not fund or not current:
            continue
        w = fund_effective_weight(fund)

        # aggrega shares per ticker (un titolo può avere più CUSIP)
        def shares_by_ticker(parsed):
            agg = defaultdict(int)
            if parsed:
                for h in parsed.get("holdings", []):
                    t = h.get("ticker")
                    if t:
                        agg[t] += h.get("shares", 0) or 0
            return agg

        cur = shares_by_ticker(current)
        prev = shares_by_ticker(previous)

        for t, cur_sh in cur.items():
            if previous is None:
                # nessun quarter precedente disponibile → segnale neutro
                signal = 0.0
            elif t not in prev:
                signal = 2.0   # nuova posizione
            else:
                prev_sh = prev[t]
                if prev_sh <= 0:
                    signal = 1.0
                else:
                    chg = (cur_sh - prev_sh) / prev_sh
                    if chg > 0.10:
                        signal = min(2.0, 1.0 + chg)
                    elif chg < -0.10:
                        signal = -1.0
                    else:
                        signal = 0.0
            raw[t] += w * signal

    return normalize_0_100(dict(raw))


# ─────────────────────────── Radar Score finale ───────────────────────────
def calculate_radar_scores(
    holdings_by_fund: dict,
    funds: list[dict],
    insider_scores: dict,
    modifiers: dict | None = None,
) -> dict:
    """
    Combina i 3 componenti + modifier. Ritorna {ticker: {radar, conviction, accumulation,
    insider, congress_mod, short_mod}}.
    insider_scores: {ticker: 0-100} da scoring/insider_quality (calcolato dal pipeline).
    modifiers: {ticker: {congress: float, short: float}} da data_sources (Fase 2).
    """
    cfg = load_config()
    w = cfg["scoring"]["stage1_base_weights"]
    cap = cfg["scoring"]["stage1_cap"]
    modifiers = modifiers or {}

    conviction = compute_conviction(holdings_by_fund, funds)
    accumulation = compute_accumulation(holdings_by_fund, funds)

    all_tickers = set(conviction) | set(accumulation) | set(insider_scores)
    out = {}
    for t in all_tickers:
        c = conviction.get(t, 0.0)
        a = accumulation.get(t, 0.0)
        i = insider_scores.get(t, 0.0)
        base = w["conviction"] * c + w["accumulation_trend"] * a + w["insider_quality"] * i
        mod = modifiers.get(t, {})
        congress_mod = mod.get("congress", 0.0)
        short_mod = mod.get("short", 0.0)
        activist_mod = mod.get("activist", 0.0)   # v2.3: SC 13D/13G
        radar = clip(base + congress_mod + short_mod + activist_mod, cap[0], cap[1])
        out[t] = {
            "radar": round(radar, 2),
            "conviction": c,
            "accumulation": a,
            "insider": i,
            "congress_mod": congress_mod,
            "short_mod": short_mod,
            "activist_mod": activist_mod,
        }
    return out
