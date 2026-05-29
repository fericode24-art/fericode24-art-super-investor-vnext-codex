from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
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
    rows = [{c: float(sub.loc[ix, c]) for c in ("BTC", "GOLD", "SP500", "CASH") if c in sub.columns} for ix in sub.index]
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


def build_signals(dates: List[str], rows: List[Dict[str, float]], st: Strategy) -> List[Dict]:
    out: List[Dict] = []
    current: Optional[str] = None
    for i in range(st.lookback_weeks, len(rows)):
      cur = rows[i]
      prev = rows[i - st.lookback_weeks]
      rb = cur["BTC"] / prev["BTC"] - 1.0
      rg = cur["GOLD"] / prev["GOLD"] - 1.0
      rs = cur.get("SP500", 1.0) / prev.get("SP500", 1.0) - 1.0
      raw, reason = dual_raw(rb, rg) if st.dual else apex_raw(rb, rg, rs)
      moms = {"BTC": rb, "GOLD": rg, "SP500": rs, "CASH": 0.0}
      if current is None or raw == current:
          target = raw if current is None else current
      else:
          edge = moms.get(raw, 0.0) - moms.get(current, 0.0)
          target = raw if edge >= st.buffer_pp / 100.0 else current
          if target == current:
              reason = f"{raw} non supera {current} di almeno {st.buffer_pp:.0f} punti"
      sma = None
      if st.sma_weeks and target == "BTC" and i >= st.sma_weeks:
          sma = sum(rows[k]["BTC"] for k in range(i - st.sma_weeks + 1, i + 1)) / st.sma_weeks
          if cur["BTC"] < sma:
              if st.dual:
                  target = "GOLD" if rg > 0 else "CASH"
              elif rg > 0 and rg >= rs:
                  target = "GOLD"
              elif rs > 0 and rs > rg:
                  target = "SP500"
              else:
                  target = "CASH"
              reason = "Filtro anti-crash: BTC sotto media 30 settimane, rivalutato piano B"
      changed = current is not None and target != current
      current = target
      out.append({
          "date": dates[i],
          "asset": target,
          "raw_asset": raw,
          "changed": changed,
          "previous_asset": out[-1]["asset"] if out else None,
          "reason": reason,
          "momentum": {"BTC": _pct(rb), "GOLD": _pct(rg), "SP500": _pct(rs)},
          "sma30_btc": round(sma, 2) if sma else None,
          "prices": {k: clean_number(cur.get(k), 4) for k in ("BTC", "GOLD", "SP500", "CASH")},
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
    switches = 0
    equity = [{"d": signal_dates[0], "v": round(INITIAL, 2), "asset": "START"}]
    for idx, d in enumerate(signal_dates[:-1]):
        sig = by_date[d]
        nxt_d = signal_dates[idx + 1]
        if sig["asset"] != current:
            if current is not None:
                gain = value - basis
                if st.apply_tax and gain > 0:
                    tax = gain * TAX_RATE
                    value -= tax
                    taxes += tax
                switches += 1
            value *= 1.0 - st.cost_bps / 10000.0
            current = sig["asset"]
            basis = value
        row = row_by_date[d]
        nxt = row_by_date[nxt_d]
        if current == "CASH":
            r = (nxt.get("CASH", row.get("CASH", 1.0)) / row.get("CASH", 1.0) - 1.0) if row.get("CASH") else 0.0
        else:
            r = nxt[current] / row[current] - 1.0
            if current == "SP500":
                r += SP500_DIV_YIELD * 7 / 365.25
            if st.apply_tax and ASSETS[current].ter:
                r -= float(ASSETS[current].ter) * 7 / 365.25
        if not math.isfinite(r):
            r = 0.0
        value *= 1.0 + r
        equity.append({"d": nxt_d, "v": round(value, 2), "asset": current})
    if st.apply_tax and current is not None and value > basis:
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
    }


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
    return {k: asset_payload(k) for k in ("BTC", "GOLD", "SP500", "CASH")}


def main() -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    legit_prices = build_proxy_prices(CACHE_DIR, price_col="close", range_="max")
    dex_prices = build_dex_prices(CACHE_DIR)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
        "base_currency": "EUR",
        "note": "Backtest su proxy Yahoo daily in EUR; operativita live APEX Legit fissata a martedi 15:30 Italia.",
        "assets": {k: asset_payload(k) for k in ("BTC", "GOLD", "SP500", "CASH")},
        "strategies": {},
    }
    try:
        payload["intraday"] = latest_intraday_snapshot(CACHE_DIR)
    except Exception as exc:
        payload["intraday_error"] = str(exc)

    for st in STRATEGIES:
        prices = dex_prices if st.key == "dex" else legit_prices
        dates, rows = weekly_observations(prices, st.weekday)
        signals = build_signals(dates, rows, st)
        bt = backtest(dates, rows, signals, st)
        current = signals[-1] if signals else None
        changes = [s for s in signals if s.get("changed")]
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
            "dual": st.dual,
            "apply_tax": st.apply_tax,
            "cost_bps": st.cost_bps,
            "assets": strategy_assets(st),
            "universe": ["BTC", "GOLD", "CASH"] if st.dual else ["BTC", "GOLD", "SP500", "CASH"],
            "chart_explainer": "Simulazione su capitale iniziale 10.000 EUR, costi inclusi; non e' il tuo saldo reale.",
            "current": current,
            "history": signals[-16:],
            "changes": changes,
            "backtest": bt,
        }

    DASHBOARD_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    OUTPUT_OUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(DASHBOARD_OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
