"""
STAGE 2 — ENTRY FILTER SCORE (dati live, cache 24h)

Entry Score = Quality 35% + Value 25% + Momentum 40%
Poi applica i moltiplicatori "treno partito" (v2.2 rafforzati).
Filtro liquidità HARD: ADV < $5M → score 0.
Cap finale [0, 130].

NOTA FASE 1: Quality usa yfinance (Fase 2 → EDGAR XBRL).
  Quality Red Flags (veto qualitativo) sono [FASE 3].
"""
from __future__ import annotations

from .cfg import load_config, clip, normalize_0_100


# ─────────────────────────── Quality (35%) ──────────────
def _quality_raw(roe, roa, gm, om, de) -> float:
    """Formula quality comune. Tutti i ratio frazionali (0.25 = 25%)."""
    roe = roe or 0
    roa = roa or 0
    gm = gm or 0
    om = om or 0
    de_score = max(0, 1 - (de / 200)) if de is not None else 0.3
    return (roe * 100 * 0.30 + roa * 100 * 0.20 +
            gm * 100 * 0.20 + om * 100 * 0.20 + de_score * 10)


def compute_quality(quotes: dict, xbrl_map: dict | None = None) -> dict:
    """
    Quality v2.2: usa EDGAR XBRL se disponibile (dato ufficiale), fallback yfinance.
    xbrl_map: {ticker: fundamentals_dict | None} da data_sources/edgar_xbrl.
    """
    xbrl_map = xbrl_map or {}
    raw = {}
    for t, q in quotes.items():
        if not q or q.get("error"):
            continue
        xb = xbrl_map.get(t)
        if xb:  # XBRL preferito
            raw[t] = _quality_raw(xb.get("roe"), xb.get("roa"),
                                  xb.get("gross_margin"), xb.get("operating_margin"),
                                  xb.get("debt_to_equity"))
        else:   # fallback yfinance
            raw[t] = _quality_raw(q.get("roe"), q.get("roa"),
                                  q.get("gross_margin"), q.get("operating_margin"),
                                  q.get("debt_to_equity"))
    return normalize_0_100(raw)


def compute_quality_yf(quotes: dict) -> dict:
    """Backward-compat: quality solo yfinance."""
    return compute_quality(quotes, None)


# ─────────────────────────── Value (25%) ───────────────────────────
def compute_value(quotes: dict) -> dict:
    """Value: inverso di P/E forward + EV/EBITDA. Più basso il multiplo, più alto lo score."""
    raw = {}
    for t, q in quotes.items():
        if not q or q.get("error"):
            continue
        pe = q.get("pe_forward") or q.get("pe_trailing")
        ev = q.get("ev_ebitda")
        if not pe and not ev:
            continue
        pe_score = max(0, 50 - pe) if (pe and pe > 0) else 0
        ev_score = max(0, 30 - ev) if (ev and ev > 0) else 0
        raw[t] = pe_score + ev_score
    return normalize_0_100(raw)


# ─────────────────────────── Momentum (40%) ───────────────────────────
def compute_momentum_score(momentum: dict) -> dict:
    """Momentum: combo ret 3M/6M/12M/1M + bonus MA - penalità RSI estremo."""
    raw = {}
    for t, m in momentum.items():
        if not m or not m.get("available"):
            continue
        r1 = m.get("ret_1m") or 0
        r3 = m.get("ret_3m") or 0
        r6 = m.get("ret_6m") or 0
        r12 = m.get("ret_12m") or 0
        above50 = 10 if m.get("above_ma50") else 0
        above200 = 10 if m.get("above_ma200") else 0
        rsi = m.get("rsi_14") or 50
        penalty = (rsi - 80) * 2 if rsi > 80 else ((30 - rsi) * 2 if rsi < 30 else 0)
        raw[t] = r3 * 0.4 + r6 * 0.3 + r12 * 0.2 + r1 * 0.1 + above50 + above200 - penalty
    return normalize_0_100(raw)


# ─────────────────────────── Entry multipliers (v2.2 rafforzati) ──────────
def apply_entry_multipliers(ticker: str, base_score: float, quote: dict, mom: dict) -> tuple[float, str]:
    """
    Applica i moltiplicatori "treno partito". Ritorna (score_finale, nota_diagnostica).
    NB: i ret_* da market_data sono in PERCENTUALE (es. 35.0 = +35%); le soglie
    config sono in RATIO (0.35) → confronto * 100.
    """
    cfg = load_config()
    em = cfg["entry_multipliers"]
    score = base_score
    notes = []

    ret_1m = mom.get("ret_1m") or 0
    ret_3m = mom.get("ret_3m") or 0
    ret_6m = mom.get("ret_6m") or 0
    rsi = mom.get("rsi_14") or 50
    price = mom.get("price") or quote.get("price") or 0
    ma50 = mom.get("ma50")
    ma200 = mom.get("ma200")
    vol_ratio = mom.get("volume_ratio_recent_vs_prior") or 1.0
    gap_pct = mom.get("gap_recent_pct") or 0
    days_since_gap = mom.get("days_since_gap")
    if days_since_gap is None:
        days_since_gap = 999

    # 1. Treno partito aggressivo / mild
    agg = em["treno_partito_aggressive"]
    mild = em["treno_partito_mild"]
    if ret_1m > agg["ret_1m"] * 100 and rsi > agg["rsi"]:
        score *= agg["mult"]; notes.append("treno_partito_aggr")
    elif ret_1m > mild["ret_1m"] * 100 and rsi > mild["rsi"]:
        score *= mild["mult"]; notes.append("treno_partito_mild")

    # 2. Performance estesa 3M / 6M
    if ret_3m > em["ret_3m_over"]["threshold"] * 100:
        score *= em["ret_3m_over"]["mult"]; notes.append("ret3m_extended")
    if ret_6m > em["ret_6m_over"]["threshold"] * 100:
        score *= em["ret_6m_over"]["mult"]; notes.append("ret6m_extended")

    # 3. Distanza da MA200
    if ma200 and price > ma200 * em["far_from_ma200"]["ratio"]:
        score *= em["far_from_ma200"]["mult"]; notes.append("far_from_ma200")

    # 4. Gap recente non consolidato
    rg = em["recent_gap"]
    if gap_pct > rg["gap_pct"] and days_since_gap < rg["days"]:
        score *= rg["mult"]; notes.append("recent_gap")

    # 5. Ritracciamento
    if ma50 and price < ma50 and ret_1m < -5:
        score *= em["ritracciamento"]["mult"]; notes.append("pullback")

    # 6. Setup fresco (bonus) — solo se non troppo esteso
    sf = em["setup_fresco"]
    if (ma50 and ma200 and price > ma50 and price > ma200
            and rsi < sf["rsi"] and vol_ratio > sf["volume_ratio"]
            and price < ma200 * sf["max_ma200_distance"]):
        score *= sf["mult"]; notes.append("setup_fresco")

    return score, ",".join(notes) if notes else "neutral"


def classify_entry_status(quote: dict, mom: dict) -> str:
    """Etichetta interpretabile per la dashboard."""
    ret_3m = mom.get("ret_3m") or 0
    ret_6m = mom.get("ret_6m") or 0
    rsi = mom.get("rsi_14") or 50
    price = mom.get("price") or quote.get("price") or 0
    ma50 = mom.get("ma50")
    ma200 = mom.get("ma200")
    if ret_3m > 40 or ret_6m > 80:
        return "Extended — wait for retracement"
    if ma50 and ma200 and price > ma50 and price > ma200 and rsi < 65:
        return "Fresh — entry favorable"
    if ma50 and price < ma50:
        return "Pullback — monitor"
    return "Neutral"


# ─────────────────────────── Entry Score finale ───────────────────────────
def calculate_entry_scores(candidates: list[str], quotes: dict, momentum: dict,
                           xbrl_map: dict | None = None) -> dict:
    """
    Per ogni candidato Stage 2 calcola l'entry score.
    xbrl_map: {ticker: fundamentals} da EDGAR XBRL (Fase 2) per la Quality.
    Ritorna {ticker: {entry, quality, value, momentum, entry_status, entry_notes}}.
    """
    cfg = load_config()
    w = cfg["scoring"]["stage2_weights"]
    cap = cfg["scoring"]["stage2_cap"]
    min_adv = cfg["filters"]["min_avg_daily_volume_usd"]

    sub_quotes = {t: quotes.get(t, {}) for t in candidates}
    sub_mom = {t: momentum.get(t, {}) for t in candidates}

    quality = compute_quality(sub_quotes, xbrl_map)
    value = compute_value(sub_quotes)
    moment = compute_momentum_score(sub_mom)

    out = {}
    for t in candidates:
        q = sub_quotes.get(t, {})
        m = sub_mom.get(t, {})
        # filtro liquidità HARD
        price = (m.get("price") or q.get("price") or 0)
        avg_vol = q.get("avg_volume") or 0
        adv_usd = price * avg_vol
        if adv_usd < min_adv:
            out[t] = {"entry": 0, "quality": quality.get(t, 0), "value": value.get(t, 0),
                      "momentum": moment.get(t, 0), "entry_status": "Illiquid — excluded",
                      "entry_notes": "below_min_adv", "adv_usd": adv_usd}
            continue
        ql, vl, mo = quality.get(t, 0), value.get(t, 0), moment.get(t, 0)
        base = w["quality"] * ql + w["value"] * vl + w["momentum"] * mo
        final, notes = apply_entry_multipliers(t, base, q, m)
        out[t] = {
            "entry": round(clip(final, cap[0], cap[1]), 2),
            "quality": ql, "value": vl, "momentum": mo,
            "entry_status": classify_entry_status(q, m),
            "entry_notes": notes,
            "adv_usd": adv_usd,
        }
    return out
