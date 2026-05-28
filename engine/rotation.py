"""
Tracker rotazioni: confronta top 12 attuale vs precedente,
genera segnali BUY/SELL/HOLD e mantiene storico.
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Optional


def load_previous_top(history_path: Path) -> Optional[dict]:
    if not history_path.exists():
        return None
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        snapshots = data.get("snapshots", [])
        return snapshots[-1] if snapshots else None
    except Exception:
        return None


def append_snapshot(history_path: Path, snapshot: dict) -> None:
    """Appende una snapshot al file di storia."""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    if history_path.exists():
        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"snapshots": [], "rotations": []}

    data["snapshots"].append(snapshot)

    # Mantieni solo le ultime 24 snapshot (2 anni se mensile)
    if len(data["snapshots"]) > 24:
        data["snapshots"] = data["snapshots"][-24:]

    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def compute_rotation_signals(new_top: list[dict], prev_top: Optional[dict]) -> dict:
    """
    Ritorna:
      {
        "entries": [...],      # nuovi BUY
        "exits": [...],        # SELL (uscivano dalla top 12)
        "holds": [...],        # confermati
        "movements": {...},    # rank delta per i confermati
      }
    """
    new_tickers = {h["ticker"] for h in new_top}
    new_lookup = {h["ticker"]: i for i, h in enumerate(new_top)}

    if not prev_top:
        return {
            "entries": list(new_tickers),
            "exits": [],
            "holds": [],
            "movements": {},
        }

    prev_holdings = prev_top.get("top12", [])
    prev_tickers = {h["ticker"] for h in prev_holdings}
    prev_lookup = {h["ticker"]: i for i, h in enumerate(prev_holdings)}

    entries = sorted(new_tickers - prev_tickers)
    exits = sorted(prev_tickers - new_tickers)
    holds = sorted(new_tickers & prev_tickers)

    movements = {}
    for t in holds:
        delta = prev_lookup[t] - new_lookup[t]  # positivo = salito di rank
        movements[t] = delta

    return {
        "entries": entries,
        "exits": exits,
        "holds": holds,
        "movements": movements,
    }


def build_snapshot(
    top_12: list[dict],
    quotes: dict,
    momentum: dict,
    rotation: dict,
    prev_top: Optional[dict] = None,
) -> dict:
    """
    Costruisce la snapshot completa che andrà su data/current.json.
    Aggiunge entry_price e entry_date per ogni titolo: prezzo a cui è entrato in top 12.
    """
    now = datetime.now().isoformat()
    prev_entry_meta = {}
    if prev_top:
        for h in prev_top.get("top12", []):
            prev_entry_meta[h["ticker"]] = {
                "entry_price": h.get("entry_price"),
                "entry_date": h.get("entry_date"),
            }

    enriched = []
    for i, item in enumerate(top_12):
        t = item["ticker"]
        q = quotes.get(t, {})
        m = momentum.get(t, {})
        price = q.get("price") or m.get("price")

        # status BUY se nuovo entrante, HOLD altrimenti
        if t in rotation["entries"]:
            status = "BUY"
            entry_price = price
            entry_date = now
        else:
            status = "HOLD"
            entry_price = prev_entry_meta.get(t, {}).get("entry_price") or price
            entry_date = prev_entry_meta.get(t, {}).get("entry_date") or now

        # performance da entry
        perf_since_entry = None
        if entry_price and price:
            try:
                perf_since_entry = round((price / entry_price - 1) * 100, 2)
            except Exception:
                perf_since_entry = None

        enriched.append({
            "rank": i + 1,
            "ticker": t,
            "name": q.get("name", t),
            "sector": q.get("sector", "Unknown"),
            "status": status,
            "composite_score": item["composite_score"],
            "breakdown": item["breakdown"],
            "price": price,
            "currency": q.get("currency", "USD"),
            "market_cap": q.get("market_cap"),
            "pe_forward": q.get("pe_forward"),
            "analyst_target": q.get("analyst_target"),
            "analyst_recommendation": q.get("analyst_recommendation"),
            "ret_1m": m.get("ret_1m"),
            "ret_3m": m.get("ret_3m"),
            "ret_6m": m.get("ret_6m"),
            "ret_12m": m.get("ret_12m"),
            "rsi_14": m.get("rsi_14"),
            "entry_price": entry_price,
            "entry_date": entry_date,
            "perf_since_entry": perf_since_entry,
        })

    # SELL signals: titoli usciti dalla top 12
    sells = []
    if prev_top:
        for h in prev_top.get("top12", []):
            if h["ticker"] in rotation["exits"]:
                t = h["ticker"]
                cur_price = (quotes.get(t, {}) or {}).get("price")
                entry_price = h.get("entry_price")
                final_perf = None
                if cur_price and entry_price:
                    try:
                        final_perf = round((cur_price / entry_price - 1) * 100, 2)
                    except Exception:
                        final_perf = None
                sells.append({
                    "ticker": t,
                    "name": h.get("name", t),
                    "status": "SELL",
                    "exit_price": cur_price,
                    "entry_price": entry_price,
                    "entry_date": h.get("entry_date"),
                    "exit_date": now,
                    "final_perf": final_perf,
                })

    return {
        "generated_at": now,
        "top12": enriched,
        "sells": sells,
        "rotation": rotation,
        "summary": {
            "n_entries": len(rotation["entries"]),
            "n_exits": len(rotation["exits"]),
            "n_holds": len(rotation["holds"]),
        },
    }
