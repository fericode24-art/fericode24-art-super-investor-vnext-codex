from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apex.config import ASSETS
from apex.yahoo import build_proxy_prices, fetch_chart_cached, latest_intraday_snapshot


CACHE_DIR = ROOT / "data" / "apex"
DASHBOARD_OUT = ROOT / "dashboard" / "apex-data.json"
OUTPUT_OUT = ROOT / "output" / "apex-data.json"
INITIAL = 10_000.0
TAX_RATE = 0.26
SP500_DIV_YIELD = 0.017
BACKTEST_START = "2018-01-01"

DEX_ASSETS = {
    "BTC": {
        "code": "BTC",
        "label": "Bitcoin spot",
        "product": "BTC spot",
        "isin": "",
        "fineco_hint": "Non Fineco: asset spot/on-chain",
        "tax_bucket": "crypto",
        "ter": None,
    },
    "GOLD": {
        "code": "GOLD",
        "label": "PAX Gold",
        "product": "PAXG token",
        "isin": "",
        "fineco_hint": "Non Fineco: token PAXG, oro tokenizzato",
        "tax_bucket": "crypto",
        "ter": None,
    },
    "CASH": {
        "code": "CASH",
        "label": "Stablecoin",
        "product": "Stablecoin USD/EUR",
        "isin": "",
        "fineco_hint": "Non Fineco: stablecoin su wallet/exchange",
        "tax_bucket": "crypto",
        "ter": None,
    },
}

DEGEN_ASSETS = {
    "BTC": {
        "code": "BTC",
        "label": "Bitcoin",
        "product": "WisdomTree Physical Bitcoin",
        "isin": "GB00BJYDH287",
        "fineco_hint": "BTC proxy EUR; esecuzione reale su ETP BTC scelto a broker",
        "tax_bucket": "dichiarativo_etp",
        "ter": 0.0015,
    },
    "GOLD2": {
        "code": "GOLD2",
        "label": "Oro 2x",
        "product": "WisdomTree Gold 2x Daily Leveraged",
        "isin": "JE00B2NFTL95",
        "fineco_hint": "LBUL.MI",
        "tax_bucket": "dichiarativo_etn",
        "ter": 0.0098,
    },
    "CL2": {
        "code": "CL2",
        "label": "USA 2x",
        "product": "Amundi MSCI USA Daily 2x Leveraged",
        "isin": "FR0010755611",
        "fineco_hint": "CL2.MI",
        "tax_bucket": "dichiarativo_ucits",
        "ter": 0.0035,
    },
    "XEON": {
        "code": "XEON",
        "label": "Cash attivo",
        "product": "Xtrackers II EUR Overnight Rate Swap UCITS ETF 1C",
        "isin": "LU0290358497",
        "fineco_hint": "XEON.MI",
        "tax_bucket": "dichiarativo_ucits",
        "ter": 0.0010,
    },
}


@dataclass(frozen=True)
class Strategy:
    key: str
    name: str
    label: str
    weekday: int
    lookback_weeks: int
    buffer_pp: float
    sma_weeks: int
    dual: bool
    apply_tax: bool
    cost_bps: float
    run_time: str
    execution: str
    engine: str = "apex"
    universe: Tuple[str, ...] = ("BTC", "GOLD", "SP500", "CASH")
    filters: Dict[str, int] = field(default_factory=dict)
    tax_mode: str = "admin"


STRATEGIES = [
    Strategy(
        key="legit",
        name="APEX Legit",
        label="Buffer 3pp 6w + SMA30",
        weekday=1,
        lookback_weeks=6,
        buffer_pp=3.0,
        sma_weeks=30,
        dual=False,
        apply_tax=True,
        cost_bps=30.0,
        run_time="Martedi 15:30 Italia",
        execution="Martedi 15:35-17:20 su Fineco/Xetra",
        engine="apex",
        universe=("BTC", "GOLD", "SP500", "CASH"),
        filters={"BTC": 30},
    ),
    Strategy(
        key="dex",
        name="APEX Dex",
        label="Dual BTC spot/PAXG 6w + buffer 3pp + SMA30",
        weekday=1,
        lookback_weeks=6,
        buffer_pp=3.0,
        sma_weeks=30,
        dual=True,
        apply_tax=False,
        cost_bps=30.0,
        run_time="Martedi 15:30 Italia, insieme ad APEX Legit",
        execution="DEX 24/7: esegui quando confermi, senza deploy separato",
        engine="dual",
        universe=("BTC", "GOLD", "CASH"),
        filters={"BTC": 30},
        tax_mode="gross",
    ),
    Strategy(
        key="degen",
        name="APEX Degen",
        label="Pure 6w + buffer 5pp + BTC SMA30 + CL2 SMA10",
        weekday=1,
        lookback_weeks=6,
        buffer_pp=5.0,
        sma_weeks=0,
        dual=False,
        apply_tax=False,
        cost_bps=30.0,
        run_time="Martedi 15:30 Italia, insieme ad APEX Legit e Dex",
        execution="Regime dichiarativo: esecuzione dopo segnale, finestra 15:35-17:20 se usi strumenti quotati",
        engine="pure",
        universe=("BTC", "GOLD2", "CL2", "XEON"),
        filters={"BTC": 30, "CL2": 10},
        tax_mode="declared_annual",
    ),
]


def _pct(x: float) -> float:
    return round(float(x) * 100, 4)


def clean_number(value, dec: int = 4):
    try:
        x = float(value)
    except Exception:
        return None
    return round(x, dec) if math.isfinite(x) else None


def weekly_observations(prices: pd.DataFrame, weekday: int) -> Tuple[List[str], List[Dict[str, float]]]:
    iso = prices.index.isocalendar()
    yw = pd.Series(list(zip(iso.year.values, iso.week.values)), index=prices.index)
    chosen = []
    for _, grp in prices.groupby(yw, sort=False):
        g = grp.sort_index()
        target = [ix for ix in g.index if ix.weekday() <= weekday]
        chosen.append(target[-1] if target else g.index[0])
    chosen = sorted(set(chosen))
    sub = prices.loc[chosen]
    dates = [ix.date().isoformat() for ix in sub.index]
    rows = []
    for ix in sub.index:
        row = {}
        for c in sub.columns:
            val = sub.loc[ix, c]
            if pd.notna(val):
                row[c] = float(val)
        rows.append(row)
    return dates, rows


def build_dex_prices(cache_dir: Path) -> pd.DataFrame:
    raw: Dict[str, pd.DataFrame] = {}
    for ticker in ("BTC-USD", "PAXG-USD", "EURUSD=X"):
        raw[ticker], _ = fetch_chart_cached(ticker, "1d", "max", cache_dir, max_age_hours=24)
    idx = raw["BTC-USD"].index.union(raw["PAXG-USD"].index).union(raw["EURUSD=X"].index).sort_values()
    aligned = pd.DataFrame(index=idx)
    aligned["BTC"] = raw["BTC-USD"]["close"]
    aligned["GOLD"] = raw["PAXG-USD"]["close"]
    aligned["EURUSD"] = raw["EURUSD=X"]["close"]
    aligned[["BTC", "GOLD", "EURUSD"]] = aligned[["BTC", "GOLD", "EURUSD"]].ffill(limit=3)
    aligned["BTC"] = aligned["BTC"] / aligned["EURUSD"]
    aligned["GOLD"] = aligned["GOLD"] / aligned["EURUSD"]
    aligned["SP500"] = 1.0
    aligned["CASH"] = 1.0
    return aligned[["BTC", "GOLD", "SP500", "CASH"]].dropna(subset=["BTC", "GOLD"])


def build_degen_prices(cache_dir: Path) -> pd.DataFrame:
    raw: Dict[str, pd.DataFrame] = {}
    for ticker in ("BTC-USD", "EURUSD=X", "LBUL.MI", "CL2.MI", "XEON.MI"):
        raw[ticker], _ = fetch_chart_cached(ticker, "1d", "max", cache_dir, max_age_hours=24)
    idx = raw["BTC-USD"].index
    for ticker in ("EURUSD=X", "LBUL.MI", "CL2.MI", "XEON.MI"):
        idx = idx.union(raw[ticker].index)
    aligned = pd.DataFrame(index=idx.sort_values())
    aligned["BTC"] = raw["BTC-USD"]["close"]
    aligned["EURUSD"] = raw["EURUSD=X"]["close"]
    aligned[["BTC", "EURUSD"]] = aligned[["BTC", "EURUSD"]].ffill(limit=3)
    aligned["BTC"] = aligned["BTC"] / aligned["EURUSD"]
    aligned["GOLD2"] = raw["LBUL.MI"]["close"].reindex(aligned.index).ffill(limit=5)
    aligned["CL2"] = raw["CL2.MI"]["close"].reindex(aligned.index).ffill(limit=5)
    aligned["XEON"] = raw["XEON.MI"]["close"].reindex(aligned.index).ffill(limit=5)
    return aligned[["BTC", "GOLD2", "CL2", "XEON"]].dropna(subset=["BTC", "GOLD2", "CL2"])


def apex_raw(rb: float, rg: float, rs: float) -> Tuple[str, str]:
    if rb > 0 and rb >= rg:
        return "BTC", "BTC positivo e almeno forte quanto Oro"
    if rg > 0 and rg > rs:
        return "GOLD", "Oro positivo e migliore di S&P 500"
    if rs > 0 and rs > rg:
        return "SP500", "S&P 500 positivo e migliore di Oro"
    return "CASH", "Nessun asset con momentum sufficiente"


def dual_raw(rb: float, rg: float) -> Tuple[str, str]:
    if rb > 0 and rb >= rg:
        return "BTC", "BTC positivo e almeno forte quanto Oro"
    if rg > 0:
        return "GOLD", "Oro positivo e BTC non qualifica"
    return "CASH", "BTC e Oro non qualificano"


def pure_raw(momentum: Dict[str, float], risky: Tuple[str, ...]) -> Tuple[str, str]:
    ranked = sorted(((k, momentum.get(k, 0.0)) for k in risky), key=lambda x: x[1], reverse=True)
    best, best_mom = ranked[0]
    if best_mom > 0:
        return best, f"{best} ha il momentum relativo piu forte tra gli asset rischiosi"
    return "XEON", "Nessun asset rischioso ha momentum positivo: fallback difensivo"


def safe_asset(st: Strategy) -> str:
    return "XEON" if st.key == "degen" else "CASH"


def risky_assets(st: Strategy) -> Tuple[str, ...]:
    return tuple(k for k in st.universe if k != safe_asset(st))


def filter_status(rows: List[Dict[str, float]], i: int, st: Strategy) -> Dict[str, Dict]:
    status: Dict[str, Dict] = {}
    for asset, weeks in st.filters.items():
        if i < weeks or asset not in rows[i]:
            continue
        sma = sum(rows[k][asset] for k in range(i - weeks + 1, i + 1)) / weeks
        price = rows[i][asset]
        status[asset] = {
            "weeks": weeks,
            "price": clean_number(price, 4),
            "sma": clean_number(sma, 4),
            "distance_pct": _pct(price / sma - 1.0) if sma else None,
            "passes": price >= sma,
        }
    return status


def apply_filters(target: str, momentum: Dict[str, float], rows: List[Dict[str, float]], i: int, st: Strategy) -> Tuple[str, str, Dict[str, Dict]]:
    status = filter_status(rows, i, st)
    if target in status and not status[target]["passes"]:
        alternatives = []
        for asset in risky_assets(st):
            if asset == target:
                continue
            if asset in status and not status[asset]["passes"]:
                continue
            if momentum.get(asset, 0.0) > 0:
                alternatives.append((asset, momentum.get(asset, 0.0)))
        if alternatives:
            winner = sorted(alternatives, key=lambda x: x[1], reverse=True)[0][0]
            return winner, f"Filtro trend: {target} bocciato, passa a {winner}", status
        return safe_asset(st), f"Filtro trend: {target} bocciato, nessun piano B valido", status
    return target, "", status


def build_signals(dates: List[str], rows: List[Dict[str, float]], st: Strategy) -> List[Dict]:
    out: List[Dict] = []
    current: Optional[str] = None
    for i in range(st.lookback_weeks, len(rows)):
      cur = rows[i]
      prev = rows[i - st.lookback_weeks]
      moms = {asset: (cur[asset] / prev[asset] - 1.0) for asset in st.universe if asset in cur and asset in prev}
      moms[safe_asset(st)] = 0.0
      rb = moms.get("BTC", 0.0)
      rg = moms.get("GOLD", 0.0)
      rs = moms.get("SP500", 0.0)
      if st.engine == "dual":
          raw, reason = dual_raw(rb, rg)
      elif st.engine == "pure":
          raw, reason = pure_raw(moms, risky_assets(st))
      else:
          raw, reason = apex_raw(rb, rg, rs)
      if current is None or raw == current:
          target = raw if current is None else current
      else:
          edge = moms.get(raw, 0.0) - moms.get(current, 0.0)
          target = raw if edge >= st.buffer_pp / 100.0 else current
          if target == current:
              reason = f"{raw} non supera {current} di almeno {st.buffer_pp:.0f} punti"
      filtered, filter_reason, filters = apply_filters(target, moms, rows, i, st)
      if filter_reason:
          target = filtered
          reason = filter_reason
      changed = current is not None and target != current
      current = target
      out.append({
          "date": dates[i],
          "asset": target,
          "raw_asset": raw,
          "changed": changed,
          "previous_asset": out[-1]["asset"] if out else None,
          "reason": reason,
          "momentum": {k: _pct(v) for k, v in moms.items()},
          "filters": filters,
          "prices": {k: clean_number(cur.get(k), 4) for k in st.universe},
      })
    return out


def backtest(dates: List[str], rows: List[Dict[str, float]], signals: List[Dict], st: Strategy) -> Dict:
    by_date = {s["date"]: s for s in signals}
    signal_dates = [s["date"] for s in signals if s["date"] >= BACKTEST_START]
    row_by_date = dict(zip(dates, rows))
    value = INITIAL
    basis = INITIAL
    current: Optional[str] = None
    taxes = 0.0
    declared_pnl = 0.0
    declared_carry = 0.0
    declared_year = datetime.fromisoformat(signal_dates[0]).year
    switches = 0
    equity = [{"d": signal_dates[0], "v": round(INITIAL, 2), "asset": "START"}]
    def settle_declared_year() -> None:
        nonlocal value, taxes, declared_pnl, declared_carry
        net = declared_pnl + declared_carry
        if net > 0:
            tax = net * TAX_RATE
            value -= tax
            taxes += tax
            declared_carry = 0.0
        else:
            declared_carry = net
        declared_pnl = 0.0
    for idx, d in enumerate(signal_dates[:-1]):
        year = datetime.fromisoformat(d).year
        if st.tax_mode == "declared_annual" and year != declared_year:
            settle_declared_year()
            declared_year = year
        sig = by_date[d]
        nxt_d = signal_dates[idx + 1]
        if sig["asset"] != current:
            if current is not None:
                gain = value - basis
                if st.tax_mode == "declared_annual":
                    declared_pnl += gain
                elif st.apply_tax and gain > 0:
                    tax = gain * TAX_RATE
                    value -= tax
                    taxes += tax
                switches += 1
            value *= 1.0 - st.cost_bps / 10000.0
            current = sig["asset"]
            basis = value
        row = row_by_date[d]
        nxt = row_by_date[nxt_d]
        if current == safe_asset(st):
            r = (nxt.get(current, row.get(current, 1.0)) / row.get(current, 1.0) - 1.0) if row.get(current) else 0.0
        else:
            r = nxt[current] / row[current] - 1.0
            if current == "SP500":
                r += SP500_DIV_YIELD * 7 / 365.25
            assets = strategy_assets(st)
            ter = assets.get(current, {}).get("ter")
            if (st.apply_tax or st.tax_mode == "declared_annual") and ter:
                r -= float(ter) * 7 / 365.25
        if not math.isfinite(r):
            r = 0.0
        value *= 1.0 + r
        equity.append({"d": nxt_d, "v": round(value, 2), "asset": current})
    if current is not None:
        if st.tax_mode == "declared_annual":
            declared_pnl += value - basis
            settle_declared_year()
            if equity:
                equity[-1]["v"] = round(value, 2)
        elif st.apply_tax and value > basis:
            tax = (value - basis) * TAX_RATE
            value -= tax
            taxes += tax
            if equity:
                equity[-1]["v"] = round(value, 2)
    years = max((datetime.fromisoformat(signal_dates[-1]) - datetime.fromisoformat(signal_dates[0])).days / 365.25, 1 / 52)
    s = pd.Series([p["v"] for p in equity], index=pd.to_datetime([p["d"] for p in equity]))
    dd = s / s.cummax() - 1 if len(s) else pd.Series(dtype=float)
    cagr = (value / INITIAL) ** (1 / years) - 1
    ulcer = math.sqrt(float((dd ** 2).mean())) if len(dd) else 0.0
    return {
        "initial": INITIAL,
        "final": round(value, 2),
        "cagr": _pct(cagr),
        "max_drawdown": _pct(float(dd.min())) if len(dd) else 0.0,
        "calmar": round(cagr / abs(float(dd.min())), 3) if len(dd) and dd.min() < 0 else 0.0,
        "ulcer": _pct(ulcer),
        "switches": switches,
        "switches_per_year": round(switches / years, 2),
        "taxes_paid": round(taxes, 2),
        "equity": equity,
        "allocation": allocation_from_equity(equity),
        "annual": annual_breakdown(equity),
    }


def allocation_from_equity(equity: List[Dict]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for p in equity:
        asset = p.get("asset")
        if not asset or asset == "START":
            continue
        counts[asset] = counts.get(asset, 0) + 1
    return counts


def annual_breakdown(equity: List[Dict]) -> List[Dict]:
    if len(equity) < 2:
        return []
    frame = pd.DataFrame(equity)
    frame["date"] = pd.to_datetime(frame["d"])
    frame["year"] = frame["date"].dt.year
    out = []
    prev_last = None
    for year, grp in frame.groupby("year"):
        vals = grp["v"].astype(float)
        start = float(prev_last if prev_last is not None else vals.iloc[0])
        end = float(vals.iloc[-1])
        curve = pd.concat([pd.Series([start]), vals], ignore_index=True)
        dd = curve / curve.cummax() - 1.0
        out.append({
            "year": int(year),
            "return": _pct(end / start - 1.0) if start else 0.0,
            "drawdown": _pct(float(dd.min())) if len(dd) else 0.0,
            "ending": round(end, 2),
        })
        prev_last = end
    return out


def asset_payload(code: str) -> Dict:
    a = ASSETS[code]
    return {
        "code": a.code,
        "label": a.label,
        "product": a.product,
        "isin": a.isin,
        "fineco_hint": a.fineco_hint,
        "tax_bucket": a.tax_bucket,
        "ter": a.ter,
    }


def strategy_assets(st: Strategy) -> Dict[str, Dict]:
    if st.key == "dex":
        return DEX_ASSETS
    if st.key == "degen":
        return DEGEN_ASSETS
    return {k: asset_payload(k) for k in ("BTC", "GOLD", "SP500", "CASH")}


def daily_radar(dates: List[str], rows: List[Dict[str, float]], signals: List[Dict], st: Strategy) -> Dict:
    if not signals:
        return {"level": "warn", "title": "Radar non disponibile", "body": "Mancano dati sufficienti."}
    cur_signal = signals[-1]
    i = len(rows) - 1
    if i < st.lookback_weeks:
        return {"level": "warn", "title": "Radar non disponibile", "body": "Mancano dati sufficienti."}
    row = rows[i]
    prev = rows[i - st.lookback_weeks]
    moms = {asset: (row[asset] / prev[asset] - 1.0) for asset in st.universe if asset in row and asset in prev}
    moms[safe_asset(st)] = 0.0
    if st.engine == "dual":
        raw, reason = dual_raw(moms.get("BTC", 0.0), moms.get("GOLD", 0.0))
    elif st.engine == "pure":
        raw, reason = pure_raw(moms, risky_assets(st))
    else:
        raw, reason = apex_raw(moms.get("BTC", 0.0), moms.get("GOLD", 0.0), moms.get("SP500", 0.0))
    candidate, filter_reason, filters = apply_filters(raw, moms, rows, i, st)
    official = cur_signal.get("asset")
    edge = moms.get(candidate, 0.0) - moms.get(official, 0.0)
    threshold = st.buffer_pp / 100.0
    losing_filter = official in filters and not filters[official]["passes"]
    if candidate != official and (edge >= threshold or losing_filter):
        level = "alert"
        title = "Radar: possibile cambio in formazione"
    elif candidate != official:
        level = "watch"
        title = "Radar: alternativa da osservare"
    else:
        level = "ok"
        title = "Radar coerente col segnale"
    body = filter_reason or reason
    return {
        "as_of": dates[i],
        "official_asset": official,
        "radar_asset": candidate,
        "raw_asset": raw,
        "level": level,
        "title": title,
        "body": body,
        "edge_pp": _pct(edge),
        "buffer_pp": st.buffer_pp,
        "momentum": {k: _pct(v) for k, v in moms.items()},
        "filters": filters,
        "is_operational": False,
    }


def main() -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    legit_prices = build_proxy_prices(CACHE_DIR, price_col="close", range_="max")
    dex_prices = build_dex_prices(CACHE_DIR)
    degen_prices = build_degen_prices(CACHE_DIR)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
        "base_currency": "EUR",
        "note": "Backtest su proxy Yahoo daily in EUR; run APEX unico martedi 15:30 Italia per Legit, Dex e Degen.",
        "assets": {
            **{k: asset_payload(k) for k in ("BTC", "GOLD", "SP500", "CASH")},
            **DEGEN_ASSETS,
        },
        "strategies": {},
    }
    try:
        payload["intraday"] = latest_intraday_snapshot(CACHE_DIR)
    except Exception as exc:
        payload["intraday_error"] = str(exc)

    for st in STRATEGIES:
        prices = dex_prices if st.key == "dex" else degen_prices if st.key == "degen" else legit_prices
        dates, rows = weekly_observations(prices, st.weekday)
        signals = build_signals(dates, rows, st)
        bt = backtest(dates, rows, signals, st)
        current = signals[-1] if signals else None
        changes = [s for s in signals if s.get("changed") and s.get("date", "") >= BACKTEST_START]
        if signals and (not changes or changes[-1]["date"] != signals[-1]["date"]):
            changes.append({ **signals[-1], "current_marker": True })
        payload["strategies"][st.key] = {
            "key": st.key,
            "name": st.name,
            "label": st.label,
            "primary": st.key == "legit",
            "run_time": st.run_time,
            "execution": st.execution,
            "weekday": st.weekday,
            "lookback_weeks": st.lookback_weeks,
            "buffer_pp": st.buffer_pp,
            "sma_weeks": st.sma_weeks,
            "filters": st.filters,
            "dual": st.dual,
            "engine": st.engine,
            "apply_tax": st.apply_tax,
            "tax_mode": st.tax_mode,
            "cost_bps": st.cost_bps,
            "assets": strategy_assets(st),
            "universe": list(st.universe),
            "chart_explainer": "Simulazione su capitale iniziale 10.000 EUR, costi inclusi; non e' il tuo saldo reale.",
            "current": current,
            "history": signals[-16:],
            "changes": changes,
            "radar": daily_radar(dates, rows, signals, st),
            "backtest": bt,
        }

    DASHBOARD_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    OUTPUT_OUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(DASHBOARD_OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
