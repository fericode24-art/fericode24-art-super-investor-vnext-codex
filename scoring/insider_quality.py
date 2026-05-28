"""
Insider Quality Score (v2.2) — sostituisce il conteggio Form 4 grezzo.

Score 0-100, multidimensionale:
  - 40% role weight   (CEO/CFO/Chairman pesano più di Director generico)
  - 30% size weight   (acquisto grande rispetto allo stipendio stimato)
  - 20% cluster       (acquisti concentrati in pochi giorni = segnale forte)
  - 10% prior bonus   (insider che compra dopo 2+ anni di silenzio)

Input: lista transazioni da data_sources/openinsider.py.
Filtra SOLO P-Purchase (open market); esclude award/gift/automatic plan.
"""
from __future__ import annotations

from datetime import datetime

from .cfg import clip

# OpenInsider abbrevia i ruoli — mappa abbreviazioni → peso
ROLE_WEIGHTS = [
    ("ceo", 1.0), ("chief executive", 1.0),
    ("cfo", 1.0), ("chief financial", 1.0),
    ("chairman", 1.0), ("cob", 1.0),
    ("pres", 0.9), ("president", 0.9),
    ("coo", 0.8), ("chief operating", 0.8),
    ("10%", 0.7),
    ("dir", 0.5), ("director", 0.5),
    ("evp", 0.6), ("svp", 0.5), ("vp", 0.4),
]

SALARY_ESTIMATES = [
    ("ceo", 1_500_000), ("chief executive", 1_500_000),
    ("cfo", 800_000), ("chief financial", 800_000),
    ("chairman", 1_000_000),
    ("pres", 700_000), ("president", 700_000),
    ("coo", 700_000),
    ("dir", 200_000), ("director", 200_000),
]


def _role_weight(title: str) -> float:
    t = (title or "").lower()
    for key, w in ROLE_WEIGHTS:
        if key in t:
            return w
    return 0.4


def _salary_estimate(title: str) -> float:
    t = (title or "").lower()
    for key, s in SALARY_ESTIMATES:
        if key in t:
            return s
    return 500_000


def _parse_date(s: str):
    """Accetta 'YYYY-MM-DD' o 'YYYY-MM-DD HH:MM:SS'."""
    if not s:
        return None
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d")
    except Exception:
        return None


def compute_insider_quality_score(ticker: str, transactions: list[dict]) -> dict:
    """
    Ritorna {score: 0-100, n_purchases, n_insiders, detail: {...}}.
    Score 0 se < 2 insider distinti che hanno comprato sul mercato aperto.
    """
    empty = {"score": 0.0, "n_purchases": 0, "n_insiders": 0, "detail": {}}
    if not transactions:
        return empty

    # FILTRO 1: solo open market purchases
    purchases = [t for t in transactions
                 if t.get("transaction_type", "").startswith("P-")]
    if len(purchases) < 2:
        return empty

    # FILTRO 2: minimo 2 insider distinti
    distinct = set(t.get("insider_name", "") for t in purchases if t.get("insider_name"))
    if len(distinct) < 2:
        return empty

    # finestra recente: ultimi 120 giorni (cluster di interesse)
    now = datetime.now()
    recent = []
    for t in purchases:
        d = _parse_date(t.get("trade_date") or t.get("filing_date"))
        if d and (now - d).days <= 120:
            recent.append((t, d))
    if len(recent) < 2:
        # acquisti esistono ma non recenti → segnale debole
        recent = [(t, _parse_date(t.get("trade_date"))) for t in purchases[:4]]

    # COMPONENTE 1 — Role weight (40%)
    role_sum = sum(_role_weight(t["title"]) for t, _ in recent)
    role_component = clip(role_sum * 25, 0, 100)

    # COMPONENTE 2 — Size relativa allo stipendio (30%)
    size_weights = []
    for t, _ in recent:
        salary = _salary_estimate(t["title"])
        ratio = (t.get("value_usd", 0) or 0) / salary
        if ratio > 1.0:
            size_weights.append(1.0)
        elif ratio > 0.5:
            size_weights.append(0.7)
        elif ratio > 0.2:
            size_weights.append(0.4)
        elif ratio > 0.05:
            size_weights.append(0.2)
        else:
            size_weights.append(0.05)
    size_component = (sum(size_weights) / len(size_weights)) * 100 if size_weights else 0

    # COMPONENTE 3 — Cluster freshness (20%)
    dates = sorted(d for _, d in recent if d)
    if len(dates) >= 2:
        span = (dates[-1] - dates[0]).days
        if span <= 7:
            cluster_component = 100
        elif span <= 14:
            cluster_component = 75
        elif span <= 21:
            cluster_component = 50
        else:
            cluster_component = 25
    else:
        cluster_component = 25

    # COMPONENTE 4 — Prior history bonus (10%)
    # insider che compra dopo lungo silenzio: confronta con le transazioni vecchie
    prior_bonus = 0
    old_buyers = set()
    for t in purchases:
        d = _parse_date(t.get("trade_date"))
        if d and (now - d).days > 365:
            old_buyers.add(t.get("insider_name", ""))
    recent_buyers = set(t.get("insider_name", "") for t, _ in recent)
    fresh_buyers = recent_buyers - old_buyers
    prior_bonus = clip(len(fresh_buyers) * 10, 0, 100)

    score = (0.40 * role_component + 0.30 * size_component +
             0.20 * cluster_component + 0.10 * prior_bonus)

    return {
        "score": round(clip(score, 0, 100), 2),
        "n_purchases": len(purchases),
        "n_insiders": len(distinct),
        "detail": {
            "role": round(role_component, 1),
            "size": round(size_component, 1),
            "cluster": round(cluster_component, 1),
            "prior_bonus": round(prior_bonus, 1),
        },
    }
