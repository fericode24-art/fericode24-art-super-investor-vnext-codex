"""
v2.4 — Scoring composito ROTATION_BETA.

Combina i componenti nel punteggio finale secondo i pesi v2.4:
  Radar (50%)  = Conviction 35 + Accumulation 30 + Insider 25 + Fund Skill 10
  Entry (50%)  = Momentum 30 + Beta 25 + Freshness 15 + Quality 15 + Value 15
  Composite    = 0.50 Radar + 0.50 Entry + Modifiers

I componenti arrivano già normalizzati 0-100 dal pipeline.
"""
from __future__ import annotations

from .cfg import load_config, clip


def fund_skill_score(ticker: str, holdings_by_fund: dict, funds: list[dict]) -> float:
    """
    Score 0-100 = skill medio (recent_skill_mult) dei fondi che tengono il titolo.
    skill_mult va 0.5–1.8 → mappato su 0–100 (1.0 neutro → 50).
    """
    fund_lookup = {f["cik"]: f for f in funds}
    mults = []
    for cik, fdata in holdings_by_fund.items():
        cur = fdata.get("current")
        fund = fund_lookup.get(cik)
        if not cur or not fund:
            continue
        if any(h.get("ticker") == ticker for h in cur.get("holdings", [])):
            mults.append(fund.get("recent_skill_mult", 1.0))
    if not mults:
        return 50.0
    avg = sum(mults) / len(mults)
    # 0.5→0, 1.0→50, 1.8→100
    return clip((avg - 0.5) / 1.3 * 100, 0, 100)


def calculate_rotation_beta_scores(radar_components: dict, entry_components: dict,
                                   modifiers: dict | None = None) -> dict:
    """
    radar_components: {ticker: {conviction, accumulation, insider, fund_skill}}
    entry_components: {ticker: {momentum, beta, freshness, quality, value}}
    modifiers:        {ticker: {short, congress}}
    Ritorna {ticker: {composite, radar, entry, ...componenti}}.
    """
    cfg = load_config()["rotation_beta"]
    rw = cfg["radar_weights"]
    ew = cfg["entry_weights"]
    cw = cfg["composite"]
    modifiers = modifiers or {}

    out = {}
    tickers = set(radar_components) & set(entry_components)
    for t in tickers:
        rc = radar_components[t]
        ec = entry_components[t]
        radar = (rw["conviction"] * rc.get("conviction", 0)
                 + rw["accumulation"] * rc.get("accumulation", 0)
                 + rw["insider"] * rc.get("insider", 0)
                 + rw["fund_skill"] * rc.get("fund_skill", 50))
        entry = (ew["momentum_rs"] * ec.get("momentum", 0)
                 + ew["beta"] * ec.get("beta", 0)
                 + ew["freshness"] * ec.get("freshness", 0)
                 + ew["quality"] * ec.get("quality", 0)
                 + ew["value"] * ec.get("value", 0))
        mod = modifiers.get(t, {})
        mod_total = mod.get("short", 0) + mod.get("congress", 0)
        composite = clip(cw["radar_weight"] * radar
                         + cw["entry_weight"] * entry + mod_total, 0, 130)
        out[t] = {
            "composite": round(composite, 2),
            "radar": round(radar, 2),
            "entry": round(entry, 2),
            "conviction": rc.get("conviction", 0),
            "accumulation": rc.get("accumulation", 0),
            "insider": rc.get("insider", 0),
            "fund_skill": round(rc.get("fund_skill", 50), 1),
            "momentum": ec.get("momentum", 0),
            "beta": ec.get("beta", 0),
            "freshness": ec.get("freshness", 0),
            "quality": ec.get("quality", 0),
            "value": ec.get("value", 0),
        }
    return out


def equal_weight_sizing(n_holdings: int, confidence: float) -> float:
    """
    Sizing equal-weight con cap per confidence.
    base = 1/n_holdings; cap 5% (conf<60) / 8% (conf<80) / 11% (conf>=80).
    Il peso residuo va a cash.
    """
    cfg = load_config()["rotation_beta"]["sizing"]
    base = 1.0 / max(1, n_holdings)
    if confidence < 60:
        cap = cfg["confidence_cap_low"]
    elif confidence < 80:
        cap = cfg["confidence_cap_mid"]
    else:
        cap = cfg["confidence_cap_high"]
    return round(min(base, cap) * 100, 2)
