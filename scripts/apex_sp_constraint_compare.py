from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apex.yahoo import build_proxy_prices

CACHE_DIR = ROOT / "data" / "apex"
OUT = ROOT / "output" / "apex_sp_constraint_compare.json"
DOC = ROOT / "docs" / "APEX_SP_CONSTRAINT_COMPARE_2026-05-29.md"
INITIAL = 10_000.0
TAX = 0.26
TER = {"BTC": 0.0015, "GOLD": 0.0012, "SP500": 0.0007, "CASH": 0.0}
SP500_DIV = 0.017


@dataclass(frozen=True)
class Strategy:
    key: str
    label: str
    sp_after_btc_filter: bool
    weekday: int = 1
    lookback: int = 6
    buffer_pp: float = 3.0
    sma_weeks: int = 30
    cost_bps: float = 30.0


STRATS = [
    Strategy("current", "APEX Legit attuale: filtro BTC -> Oro/Cash", False),
    Strategy("sp_free", "APEX Legit senza vincolo SP: filtro BTC -> rivaluta Oro/SP/Cash", True),
]
WINDOWS = [
    ("2018-2020", date(2018, 1, 1), date(2020, 12, 31)),
    ("2021-2022", date(2021, 1, 1), date(2022, 12, 31)),
    ("2023-2026", date(2023, 1, 1), date(2026, 5, 29)),
    ("2019-2021", date(2019, 1, 1), date(2021, 12, 31)),
    ("2020-2022", date(2020, 1, 1), date(2022, 12, 31)),
    ("2021-2023", date(2021, 1, 1), date(2023, 12, 31)),
    ("2022-2024", date(2022, 1, 1), date(2024, 12, 31)),
    ("2023-2025", date(2023, 1, 1), date(2025, 12, 31)),
]


def pct(x: float) -> float:
    return round(x * 100, 2)


def weekly(prices: pd.DataFrame, weekday: int) -> Tuple[List[date], List[Dict[str, float]]]:
    iso = prices.index.isocalendar()
    yw = pd.Series(list(zip(iso.year.values, iso.week.values)), index=prices.index)
    chosen = []
    for _, grp in prices.groupby(yw, sort=False):
        g = grp.sort_index()
        target = [ix for ix in g.index if ix.weekday() <= weekday]
        chosen.append(target[-1] if target else g.index[0])
    chosen = sorted(set(chosen))
    sub = prices.loc[chosen]
    return [ix.date() for ix in sub.index], [
        {c: float(sub.loc[ix, c]) for c in ("BTC", "GOLD", "SP500", "CASH") if c in sub.columns}
        for ix in sub.index
    ]


def raw_apex(rb: float, rg: float, rs: float) -> str:
    if rb > 0 and rb >= rg:
        return "BTC"
    if rg > 0 and rg > rs:
        return "GOLD"
    if rs > 0 and rs > rg:
        return "SP500"
    return "CASH"


def fallback_after_btc_filter(rg: float, rs: float, st: Strategy) -> str:
    if st.sp_after_btc_filter:
        if rg > 0 and rg >= rs:
            return "GOLD"
        if rs > 0 and rs > rg:
            return "SP500"
        return "CASH"
    return "GOLD" if rg > 0 else "CASH"


def signals(dates: List[date], rows: List[Dict[str, float]], st: Strategy) -> List[Dict]:
    out = []
    cur: Optional[str] = None
    for i in range(st.lookback, len(rows)):
        c, p = rows[i], rows[i - st.lookback]
        rb = c["BTC"] / p["BTC"] - 1
        rg = c["GOLD"] / p["GOLD"] - 1
        rs = c["SP500"] / p["SP500"] - 1
        raw = raw_apex(rb, rg, rs)
        moms = {"BTC": rb, "GOLD": rg, "SP500": rs, "CASH": 0.0}
        if cur is None or raw == cur:
            target = raw if cur is None else cur
        else:
            target = raw if moms[raw] - moms.get(cur, 0.0) >= st.buffer_pp / 100 else cur
        sma = None
        filter_hit = False
        if target == "BTC" and i >= st.sma_weeks:
            sma = sum(rows[k]["BTC"] for k in range(i - st.sma_weeks + 1, i + 1)) / st.sma_weeks
            if c["BTC"] < sma:
                target = fallback_after_btc_filter(rg, rs, st)
                filter_hit = True
        out.append({
            "date": dates[i],
            "asset": target,
            "raw": raw,
            "changed": cur is not None and target != cur,
            "previous": cur,
            "filter_hit": filter_hit,
            "ret": {"BTC": rb, "GOLD": rg, "SP500": rs},
            "sma": sma,
        })
        cur = target
    return out


def run(prices: pd.DataFrame, st: Strategy, start: date, end: date) -> Dict:
    dates, rows = weekly(prices, st.weekday)
    sigs = signals(dates, rows, st)
    by_date = {s["date"]: s for s in sigs}
    row_by_date = dict(zip(dates, rows))
    sim = [s["date"] for s in sigs if start <= s["date"] <= end]
    value = INITIAL
    basis = INITIAL
    current: Optional[str] = None
    switches = 0
    taxes = 0.0
    equity = []
    for i, d in enumerate(sim[:-1]):
        sig = by_date[d]
        nxt = sim[i + 1]
        if sig["asset"] != current:
            if current is not None:
                gain = value - basis
                if gain > 0:
                    tax = gain * TAX
                    value -= tax
                    taxes += tax
                switches += 1
            value *= 1 - st.cost_bps / 10000
            current = sig["asset"]
            basis = value
        row = row_by_date[d]
        nr = row_by_date[nxt]
        if current == "CASH":
            r = 0.0
        else:
            r = nr[current] / row[current] - 1
            if current == "SP500":
                r += SP500_DIV * 7 / 365.25
            r -= TER[current] * 7 / 365.25
        value *= 1 + r
        equity.append((nxt, value, current))
    if current and value > basis:
        tax = (value - basis) * TAX
        value -= tax
        taxes += tax
        if equity:
            equity[-1] = (equity[-1][0], value, equity[-1][2])
    s = pd.Series([x[1] for x in equity], index=pd.to_datetime([x[0] for x in equity]))
    dd = s / s.cummax() - 1
    years = max((sim[-1] - sim[0]).days / 365.25, 1 / 52)
    cagr = (value / INITIAL) ** (1 / years) - 1
    ulcer = math.sqrt(float((dd ** 2).mean()))
    alloc = {a: 0 for a in ("BTC", "GOLD", "SP500", "CASH")}
    blocks = []
    cur_asset = None
    count = 0
    start_block = None
    prev_d = None
    for d, _, a in equity:
        alloc[a] += 1
        if a != cur_asset:
            if cur_asset:
                blocks.append((cur_asset, start_block, prev_d, count))
            cur_asset = a
            start_block = d
            count = 1
        else:
            count += 1
        prev_d = d
    if cur_asset:
        blocks.append((cur_asset, start_block, prev_d, count))
    total = sum(alloc.values()) or 1
    return {
        "key": st.key,
        "label": st.label,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "final": round(value, 2),
        "cagr": pct(cagr),
        "maxdd": pct(float(dd.min())),
        "calmar": round(cagr / abs(float(dd.min())), 3),
        "ulcer": pct(ulcer),
        "switches": switches,
        "switches_per_year": round(switches / years, 2),
        "taxes": round(taxes, 2),
        "alloc_weeks": alloc,
        "alloc_pct": {k: round(v / total * 100, 1) for k, v in alloc.items()},
        "blocks": [{"asset": a, "start": s.isoformat(), "end": e.isoformat(), "weeks": n} for a, s, e, n in blocks],
        "recent_blocks": [{"asset": a, "start": s.isoformat(), "end": e.isoformat(), "weeks": n} for a, s, e, n in blocks[-12:]],
        "filter_to_cash": sum(1 for x in sigs if x["filter_hit"] and x["asset"] == "CASH" and start <= x["date"] <= end),
        "filter_to_sp500": sum(1 for x in sigs if x["filter_hit"] and x["asset"] == "SP500" and start <= x["date"] <= end),
    }


def md_table(rows: List[List[str]]) -> str:
    head, *body = rows
    out = ["| " + " | ".join(head) + " |", "| " + " | ".join(["---"] * len(head)) + " |"]
    out += ["| " + " | ".join(map(str, row)) + " |" for row in body]
    return "\n".join(out)


def main() -> int:
    prices = build_proxy_prices(CACHE_DIR, price_col="close", range_="max")
    full = [run(prices, st, date(2018, 1, 1), date(2026, 5, 29)) for st in STRATS]
    rolling = []
    for name, start, end in WINDOWS:
        for st in STRATS:
            r = run(prices, st, start, end)
            r["window"] = name
            rolling.append(r)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"full": full, "rolling": rolling}, indent=2), encoding="utf-8")

    rows = [["Strategia", "Finale 10k", "CAGR", "MaxDD", "Calmar", "Ulcer", "Swap/anno", "Cash weeks", "SP500 weeks", "Filtro->Cash", "Filtro->SP500"]]
    for r in full:
        rows.append([
            r["label"],
            f"{r['final']:,.0f}".replace(",", "."),
            f"{r['cagr']:.2f}%",
            f"{r['maxdd']:.2f}%",
            r["calmar"],
            f"{r['ulcer']:.2f}%",
            r["switches_per_year"],
            r["alloc_weeks"]["CASH"],
            r["alloc_weeks"]["SP500"],
            r["filter_to_cash"],
            r["filter_to_sp500"],
        ])
    roll_rows = [["Periodo", "Strategia", "CAGR", "MaxDD", "Calmar", "Swap/anno"]]
    for r in rolling:
        roll_rows.append([r["window"], r["key"], f"{r['cagr']:.1f}%", f"{r['maxdd']:.1f}%", r["calmar"], r["switches_per_year"]])
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(
        "# APEX Legit: vincolo S&P dopo filtro BTC\n\n"
        "Confronto fra strategia attuale e variante che, quando BTC vince ma viene bocciato dalla SMA30, rivaluta anche S&P 500 invece di andare solo Oro/Cash.\n\n"
        "## Full period netto fiscale\n\n"
        + md_table(rows)
        + "\n\n## Rolling windows\n\n"
        + md_table(roll_rows)
        + "\n",
        encoding="utf-8",
    )
    print(DOC)
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
