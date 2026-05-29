from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apex.yahoo import build_proxy_prices
from scripts.apex_deep_research import table_md


CACHE_DIR = ROOT / "data" / "apex"
DOC_DIR = ROOT / "docs"
OUT_DIR = ROOT / "output"
START = date(2018, 1, 1)
END = date(2026, 5, 29)
INITIAL = 10_000.0
TAX_RATE = 0.26
SP500_DIV_YIELD = 0.017

REPORT = DOC_DIR / "APEX_HYBRID_WALKFORWARD_2026-05-29.md"
REPORT_TXT = DOC_DIR / "APEX_HYBRID_WALKFORWARD_2026-05-29.txt"
REPORT_HTML = DOC_DIR / "APEX_HYBRID_WALKFORWARD_2026-05-29.html"
JSON_OUT = OUT_DIR / "apex_hybrid_walkforward_results.json"


@dataclass(frozen=True)
class Strategy:
    name: str
    weekday: int
    price_col: str
    lookback_weeks: int
    buffer_pp: float
    sma_weeks: int
    dual: bool = False
    apply_tax: bool = True
    cost_bps: float = 30.0


@dataclass(frozen=True)
class AssetTax:
    ter: float
    redditi_diversi: bool
    ucits: bool = False


ASSET_TAX = {
    "BTC": AssetTax(0.0015, True),
    "GOLD": AssetTax(0.0012, True),
    "SP500": AssetTax(0.0007, False, True),
    "CASH": AssetTax(0.0, False, True),
}

STRATEGIES = [
    Strategy("APEX R 8w + SMA30", 2, "close", 8, 0.0, 30),
    Strategy("Buffer 5pp 5w", 4, "open", 5, 5.0, 0),
    Strategy("Buffer 5pp 5w + SMA30", 4, "open", 5, 5.0, 30),
    Strategy("Buffer 5pp 6w + SMA30", 4, "open", 6, 5.0, 30),
    Strategy("Buffer 5pp 8w + SMA30", 4, "open", 8, 5.0, 30),
    Strategy("Buffer 3pp 6w + SMA30", 1, "close", 6, 3.0, 30),
]

WINDOWS = [
    ("2018-2020", date(2018, 1, 1), date(2020, 12, 31)),
    ("2021-2022", date(2021, 1, 1), date(2022, 12, 31)),
    ("2023-2026", date(2023, 1, 1), END),
    ("2019-2021", date(2019, 1, 1), date(2021, 12, 31)),
    ("2020-2022", date(2020, 1, 1), date(2022, 12, 31)),
    ("2021-2023", date(2021, 1, 1), date(2023, 12, 31)),
    ("2022-2024", date(2022, 1, 1), date(2024, 12, 31)),
    ("2023-2025", date(2023, 1, 1), date(2025, 12, 31)),
]


@dataclass
class TaxState:
    lots: List[Tuple[float, int]] = field(default_factory=list)
    paid: float = 0.0
    created: float = 0.0
    used: float = 0.0

    def expire(self, d: date) -> None:
        self.lots = [(a, y) for a, y in self.lots if d.year <= y]

    def add_loss(self, amount: float, d: date) -> None:
        if amount > 0:
            self.created += amount
            self.lots.append((amount, d.year + 4))

    def use_against_gain(self, gain: float, d: date) -> float:
        self.expire(d)
        remaining = gain
        keep: List[Tuple[float, int]] = []
        for amount, expiry in sorted(self.lots, key=lambda x: x[1]):
            if remaining <= 0:
                keep.append((amount, expiry))
                continue
            take = min(amount, remaining)
            remaining -= take
            self.used += take
            if amount - take > 1e-9:
                keep.append((amount - take, expiry))
        self.lots = keep
        tax = remaining * TAX_RATE
        self.paid += tax
        return tax


def realize(asset: str, sale: float, basis: float, d: date, tax: TaxState) -> float:
    pnl = sale - basis
    info = ASSET_TAX[asset]
    if pnl <= 0:
        if info.redditi_diversi or info.ucits:
            tax.add_loss(-pnl, d)
        return 0.0
    if info.redditi_diversi:
        return tax.use_against_gain(pnl, d)
    t = pnl * TAX_RATE
    tax.paid += t
    return t


def weekly_observations(prices: pd.DataFrame, weekday: int) -> Tuple[List[date], List[Dict[str, float]]]:
    iso = prices.index.isocalendar()
    yw = pd.Series(list(zip(iso.year.values, iso.week.values)), index=prices.index)
    chosen = []
    for _, grp in prices.groupby(yw, sort=False):
        g = grp.sort_index()
        target = [ix for ix in g.index if ix.weekday() <= weekday]
        chosen.append(target[-1] if target else g.index[0])
    chosen = sorted(set(chosen))
    sub = prices.loc[chosen]
    dates = [ix.date() for ix in sub.index]
    rows = [{c: float(sub.loc[ix, c]) for c in ("BTC", "GOLD", "SP500", "CASH") if c in sub.columns} for ix in sub.index]
    return dates, rows


def apex_signal(rb: float, rg: float, rs: float) -> str:
    if rb > 0 and rb >= rg:
        return "BTC"
    if rg > 0 and rg > rs:
        return "GOLD"
    if rs > 0 and rs > rg:
        return "SP500"
    return "CASH"


def target_series(dates: List[date], rows: List[Dict[str, float]], st: Strategy) -> Dict[int, str]:
    out = {}
    cur: Optional[str] = None
    for i in range(st.lookback_weeks, len(dates)):
        c = rows[i]
        p = rows[i - st.lookback_weeks]
        rb = c["BTC"] / p["BTC"] - 1.0
        rg = c["GOLD"] / p["GOLD"] - 1.0
        rs = c["SP500"] / p["SP500"] - 1.0
        candidate = apex_signal(rb, rg, rs)
        moms = {"BTC": rb, "GOLD": rg, "SP500": rs, "CASH": 0.0}
        if cur is None or candidate == cur:
            target = candidate if cur is None else cur
        else:
            target = candidate if moms.get(candidate, 0.0) - moms.get(cur, 0.0) >= st.buffer_pp / 100.0 else cur
        if st.sma_weeks and target == "BTC" and i >= st.sma_weeks:
            sma = sum(rows[k]["BTC"] for k in range(i - st.sma_weeks + 1, i + 1)) / st.sma_weeks
            if rows[i]["BTC"] < sma:
                # Conservative version of the pasted APEX R filter.
                target = "GOLD" if rg > 0 else "CASH"
        out[i] = target
        cur = target
    return out


def backtest(prices: pd.DataFrame, st: Strategy, start: date, end: date) -> Tuple[pd.DataFrame, Dict]:
    dates, rows = weekly_observations(prices, st.weekday)
    targets = target_series(dates, rows, st)
    sim_i = [i for i in range(st.lookback_weeks, len(dates)) if start <= dates[i] <= end]
    if len(sim_i) < 4:
        raise ValueError("not enough observations")
    value = INITIAL
    basis = INITIAL
    current: Optional[str] = None
    tax = TaxState()
    switches = 0
    records = []
    for pos in range(len(sim_i) - 1):
        i = sim_i[pos]
        j = sim_i[pos] + 1
        d = dates[i]
        target = targets[i]
        if target != current:
            if current is not None:
                value -= realize(current, value, basis, d, tax)
                switches += 1
            value -= value * st.cost_bps / 10000.0
            current = target
            basis = value
        asset = current or target
        dt = (dates[j] - dates[i]).days / 365.25
        if asset == "CASH":
            period_ret = 0.0
        else:
            period_ret = rows[j][asset] / rows[i][asset] - 1.0
            if asset == "SP500":
                period_ret += SP500_DIV_YIELD * dt
            period_ret -= ASSET_TAX[asset].ter * dt
        value *= 1.0 + period_ret
        tax.expire(dates[j])
        records.append({"date": dates[j], "value": value, "signal": asset})
    final_asset = current or "CASH"
    value -= realize(final_asset, value, basis, dates[sim_i[-1]], tax)
    if records:
        records[-1]["value"] = value
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    m = metrics(df["value"], value)
    m.update({
        "label": st.name,
        "timing": f"{weekday_name(st.weekday)} {st.price_col}",
        "lookback": st.lookback_weeks,
        "buffer": st.buffer_pp,
        "sma": st.sma_weeks,
        "final": value,
        "switches": switches,
        "switches_per_year": switches / m["years"],
        "taxes_paid": tax.paid,
        "start": start.isoformat(),
        "end": end.isoformat(),
    })
    return df, m


def metrics(s: pd.Series, final_value: float) -> Dict:
    years = (s.index[-1].date() - s.index[0].date()).days / 365.25
    cagr = (final_value / INITIAL) ** (1 / years) - 1
    dd = s / s.cummax() - 1
    rets = s.pct_change().dropna()
    vol = rets.std() * math.sqrt(52) if len(rets) else 0.0
    sharpe = (rets.mean() * 52) / vol if vol else 0.0
    y = np.log(s.to_numpy(dtype=float))
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    pred = intercept + slope * x
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
    return {
        "years": years,
        "cagr": cagr,
        "max_drawdown": float(dd.min()),
        "calmar": cagr / abs(float(dd.min())) if dd.min() < 0 else 0.0,
        "ulcer": math.sqrt(float((dd ** 2).mean())),
        "sharpe": sharpe,
        "r2": r2,
        "time_below_20": float((dd < -0.20).mean()),
        "time_below_40": float((dd < -0.40).mean()),
    }


def weekday_name(i: int) -> str:
    return ["lunedi", "martedi", "mercoledi", "giovedi", "venerdi"][i]


def pct(x: float, d: int = 2) -> str:
    return f"{x * 100:.{d}f}%"


def money(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def row_display(m: Dict) -> Dict:
    return {
        "Strategia": m["label"],
        "Timing": m["timing"],
        "CAGR": pct(m["cagr"]),
        "Finale 10k": money(m["final"]),
        "MaxDD": pct(m["max_drawdown"]),
        "Calmar": round(m["calmar"], 3),
        "R2": round(m["r2"], 3),
        "Ulcer": pct(m["ulcer"]),
        "Sw/anno": round(m["switches_per_year"], 1),
    }


def window_display(m: Dict, window: str) -> Dict:
    return {
        "Periodo": window,
        "Strategia": m["label"],
        "CAGR": pct(m["cagr"]),
        "MaxDD": pct(m["max_drawdown"]),
        "Calmar": round(m["calmar"], 3),
        "R2": round(m["r2"], 3),
        "Sw/anno": round(m["switches_per_year"], 1),
    }


def aggregate_window(records: List[Dict]) -> List[Dict]:
    out = []
    for name in sorted({r["label"] for r in records}):
        vals = [r for r in records if r["label"] == name]
        out.append({
            "Strategia": name,
            "CAGR medio": pct(sum(v["cagr"] for v in vals) / len(vals)),
            "CAGR min": pct(min(v["cagr"] for v in vals)),
            "DD peggiore": pct(min(v["max_drawdown"] for v in vals)),
            "Calmar medio": round(sum(v["calmar"] for v in vals) / len(vals), 3),
            "R2 medio": round(sum(v["r2"] for v in vals) / len(vals), 3),
            "Periodi >0": f"{sum(1 for v in vals if v['cagr'] > 0)}/{len(vals)}",
        })
    return sorted(out, key=lambda x: (float(x["CAGR min"].replace("%", "")), float(x["CAGR medio"].replace("%", ""))), reverse=True)


def main() -> int:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prices_cache = {
        "open": build_proxy_prices(CACHE_DIR, price_col="open", range_="max"),
        "close": build_proxy_prices(CACHE_DIR, price_col="close", range_="max"),
    }
    full = []
    frames = {}
    for st in STRATEGIES:
        frame, m = backtest(prices_cache[st.price_col], st, START, END)
        full.append(m)
        frames[st.name] = frame
    window_records = []
    for win_name, start, end in WINDOWS:
        for st in STRATEGIES:
            try:
                _, m = backtest(prices_cache[st.price_col], st, start, end)
                m["window"] = win_name
                window_records.append(m)
            except ValueError:
                continue

    payload = {"full": full, "windows": window_records}
    JSON_OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    report = make_report(full, window_records)
    REPORT.write_text(report, encoding="utf-8")
    REPORT_TXT.write_text(report, encoding="utf-8")
    html = "<!doctype html><html lang='it'><meta charset='utf-8'><title>APEX hybrid walk-forward</title><style>body{font-family:Segoe UI,Arial,sans-serif;max-width:1180px;margin:24px auto;padding:0 16px;background:#f8fafc;color:#111827;line-height:1.45}pre{white-space:pre-wrap;background:white;border:1px solid #ddd;border-radius:10px;padding:18px}</style><pre>" + report.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "</pre></html>"
    REPORT_HTML.write_text(html, encoding="utf-8")
    print(REPORT)
    print(JSON_OUT)
    return 0


def make_report(full: List[Dict], window_records: List[Dict]) -> str:
    full_table = table_md([row_display(m) for m in sorted(full, key=lambda x: x["final"], reverse=True)], ["Strategia", "Timing", "CAGR", "Finale 10k", "MaxDD", "Calmar", "R2", "Ulcer", "Sw/anno"])
    agg_table = table_md(aggregate_window(window_records), ["Strategia", "CAGR medio", "CAGR min", "DD peggiore", "Calmar medio", "R2 medio", "Periodi >0"])
    window_top = sorted(window_records, key=lambda x: (x["window"], -x["cagr"]))
    window_rows = [window_display(m, m["window"]) for m in window_top]
    return f"""# APEX hybrid + walk-forward - 2026-05-29

Stato: test locale, nessun deploy.

## Cosa stiamo testando

La critica a `Buffer 5pp 5w` e' corretta: potrebbe essere un parametro fortunato sul passato. Qui quindi non guardo solo il full-period 2018-2026, ma anche finestre rolling / out-of-sample. Ho aggiunto il filtro anti-crash SMA30 di APEX R alla nostra vincitrice e ad alcune varianti vicine.

## Full Period Netto Fiscale

{full_table}

## Rolling / Walk-Forward Aggregato

Questa e' la tabella piu importante per il dubbio overfitting. `CAGR min` e `DD peggiore` contano piu del CAGR massimo.

{agg_table}

## Dettaglio Finestre

{table_md(window_rows, ["Periodo", "Strategia", "CAGR", "MaxDD", "Calmar", "R2", "Sw/anno"])}

## Lettura

- APEX R e' piu difensiva: il filtro SMA30 abbassa il drawdown e rende la logica piu facile da giustificare.
- Buffer 5pp 5w puro resta fortissimo sul full-period, ma la critica dell'overfitting non e' assurda: il parametro 5w era gia' risultato fragile nel plateau.
- L'ibrido `Buffer 5pp 5w + SMA30` e' il test chiave: se mantiene rendimento accettabile e migliora le finestre peggiori, diventa candidato serio.
- Se l'ibrido sacrifica troppo CAGR o non migliora le finestre rolling, allora APEX R resta la scelta conservativa e Buffer 5pp 5w resta la scelta aggressiva ma sospetta.
"""


if __name__ == "__main__":
    raise SystemExit(main())
