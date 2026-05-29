from __future__ import annotations

import csv
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
OUT_DIR = ROOT / "output"
DOC_DIR = ROOT / "docs"
START = date(2018, 1, 1)
END = date(2026, 5, 29)
INITIAL = 10_000.0
TAX_RATE = 0.26
SP500_DIV_YIELD = 0.017

REPORT = DOC_DIR / "APEX_DEFINITIVE_COMPARE_2026-05-29.md"
REPORT_TXT = DOC_DIR / "APEX_DEFINITIVE_COMPARE_2026-05-29.txt"
REPORT_HTML = DOC_DIR / "APEX_DEFINITIVE_COMPARE_2026-05-29.html"
JSON_OUT = OUT_DIR / "apex_definitive_compare_results.json"


@dataclass(frozen=True)
class Strategy:
    name: str
    weekday: int
    lookback_weeks: int
    buffer_pp: float
    confirm_k: int
    regime_sma_weeks: int
    dual: bool
    apply_tax: bool
    cost_bps: float
    price_col: str
    run_time_it: str


@dataclass(frozen=True)
class AssetTax:
    ter: float
    redditi_diversi: bool
    ucits: bool = False


ASSET_TAX = {
    "BTC": AssetTax(ter=0.0015, redditi_diversi=True),
    "GOLD": AssetTax(ter=0.0012, redditi_diversi=True),
    "SP500": AssetTax(ter=0.0007, redditi_diversi=False, ucits=True),
    "CASH": AssetTax(ter=0.0, redditi_diversi=False, ucits=True),
}


APEX_R = Strategy(
    name="APEX R Fineco proposta",
    weekday=2,
    lookback_weeks=8,
    buffer_pp=0.0,
    confirm_k=1,
    regime_sma_weeks=30,
    dual=False,
    apply_tax=True,
    cost_bps=30.0,
    price_col="close",
    run_time_it="mercoledi 15:00",
)

APEX_ALFA_DEX = Strategy(
    name="APEX ALFA DEX proposta",
    weekday=1,
    lookback_weeks=6,
    buffer_pp=3.0,
    confirm_k=1,
    regime_sma_weeks=30,
    dual=True,
    apply_tax=False,
    cost_bps=30.0,
    price_col="close",
    run_time_it="martedi 20:00",
)


@dataclass
class TaxState:
    lots: List[Tuple[float, int]] = field(default_factory=list)
    paid: float = 0.0
    created: float = 0.0
    used: float = 0.0
    expired: float = 0.0

    def expire(self, d: date) -> None:
        keep: List[Tuple[float, int]] = []
        for amount, expiry in self.lots:
            if d.year <= expiry:
                keep.append((amount, expiry))
            else:
                self.expired += amount
        self.lots = keep

    def add_loss(self, amount: float, d: date) -> None:
        if amount > 0:
            self.created += amount
            self.lots.append((amount, d.year + 4))

    def use_against_gain(self, gain: float, d: date) -> float:
        self.expire(d)
        if gain <= 0:
            return 0.0
        remaining = gain
        used = 0.0
        keep: List[Tuple[float, int]] = []
        for amount, expiry in sorted(self.lots, key=lambda x: x[1]):
            if remaining <= 0:
                keep.append((amount, expiry))
                continue
            take = min(amount, remaining)
            remaining -= take
            used += take
            if amount - take > 1e-9:
                keep.append((amount - take, expiry))
        self.lots = keep
        self.used += used
        tax = remaining * TAX_RATE
        self.paid += tax
        return tax

    @property
    def zainetto(self) -> float:
        return sum(a for a, _ in self.lots)


def realize_tax(asset: str, sale_value: float, basis: float, d: date, state: TaxState, ucits_losses_to_zainetto: bool) -> float:
    pnl = sale_value - basis
    info = ASSET_TAX[asset]
    if pnl <= 0:
        if info.redditi_diversi or (info.ucits and ucits_losses_to_zainetto):
            state.add_loss(-pnl, d)
        return 0.0
    if info.redditi_diversi:
        return state.use_against_gain(pnl, d)
    tax = pnl * TAX_RATE
    state.paid += tax
    return tax


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


def dual_signal(rb: float, rg: float) -> str:
    if rb > 0 and rb >= rg:
        return "BTC"
    if rg > 0:
        return "GOLD"
    return "CASH"


def target_series(dates: List[date], rows: List[Dict[str, float]], st: Strategy) -> Dict[int, str]:
    out: Dict[int, str] = {}
    cur: Optional[str] = None
    pending: Optional[str] = None
    pending_count = 0
    for i in range(st.lookback_weeks, len(dates)):
        cur_row = rows[i]
        prev = rows[i - st.lookback_weeks]
        rb = cur_row["BTC"] / prev["BTC"] - 1.0
        rg = cur_row["GOLD"] / prev["GOLD"] - 1.0
        rs = cur_row["SP500"] / prev["SP500"] - 1.0
        raw = dual_signal(rb, rg) if st.dual else apex_signal(rb, rg, rs)
        moms = {"BTC": rb, "GOLD": rg, "SP500": rs, "CASH": 0.0}
        if st.confirm_k > 1:
            if raw == pending:
                pending_count += 1
            else:
                pending = raw
                pending_count = 1
            candidate = pending if pending_count >= st.confirm_k else (cur or raw)
        else:
            candidate = raw
        if cur is None or candidate == cur:
            target = candidate if cur is None else cur
        else:
            target = candidate if moms.get(candidate, 0.0) - moms.get(cur, 0.0) >= st.buffer_pp / 100.0 else cur
        if st.regime_sma_weeks and target == "BTC" and i >= st.regime_sma_weeks:
            sma = sum(rows[k]["BTC"] for k in range(i - st.regime_sma_weeks + 1, i + 1)) / st.regime_sma_weeks
            if rows[i]["BTC"] < sma:
                target = "GOLD" if rg > 0 else "CASH"
        out[i] = target
        cur = target
    return out


def backtest_strategy(prices: pd.DataFrame, st: Strategy, ucits_losses_to_zainetto: bool) -> Tuple[pd.DataFrame, Dict]:
    dates, rows = weekly_observations(prices, st.weekday)
    targets = target_series(dates, rows, st)
    sim_i = [i for i in range(st.lookback_weeks, len(dates)) if START <= dates[i] <= END]
    if len(sim_i) < 2:
        raise ValueError("not enough simulation dates")
    value = INITIAL
    current: Optional[str] = None
    basis = INITIAL
    tax = TaxState()
    switches = 0
    records = []
    for pos in range(len(sim_i) - 1):
        i = sim_i[pos]
        j = sim_i[pos] + 1
        d = dates[i]
        target = targets[i]
        changed = target != current
        if changed:
            if current is not None and st.apply_tax:
                value -= realize_tax(current, value, basis, d, tax, ucits_losses_to_zainetto)
                switches += 1
            elif current is not None:
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
            if st.apply_tax:
                period_ret -= ASSET_TAX[asset].ter * dt
        value *= 1.0 + period_ret
        if st.apply_tax:
            tax.expire(dates[j])
        records.append({
            "date": dates[j],
            "value": value,
            "signal": asset,
            "changed": changed,
            "period_ret": period_ret,
        })
    final_asset = current or targets[sim_i[-2]]
    final_pre_tax = value
    final_tax = 0.0
    if st.apply_tax:
        final_tax = realize_tax(final_asset, value, basis, dates[sim_i[-1]], tax, ucits_losses_to_zainetto)
        value -= final_tax
        if records:
            records[-1]["value"] = value
    frame = pd.DataFrame(records)
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.set_index("date")
    st_metrics = metrics(frame["value"], value)
    st_metrics.update({
        "label": st.name,
        "timing": f"{weekday_name(st.weekday)} {st.price_col}",
        "lookback": st.lookback_weeks,
        "buffer_pp": st.buffer_pp,
        "sma_weeks": st.regime_sma_weeks,
        "dual": st.dual,
        "tax_mode": "netto" if st.apply_tax else "lordo",
        "final": value,
        "final_pre_tax": final_pre_tax,
        "final_liquidation_tax": final_tax,
        "taxes_paid": tax.paid,
        "zainetto_created": tax.created,
        "zainetto_used": tax.used,
        "zainetto_remaining": tax.zainetto,
        "switches": switches,
        "switches_per_year": switches / st_metrics["years"],
        "final_asset": final_asset,
        "start": frame.index[0].date().isoformat(),
        "end": frame.index[-1].date().isoformat(),
    })
    return frame, st_metrics


def metrics(s: pd.Series, final_value: float) -> Dict:
    s = s.dropna()
    years = (s.index[-1].date() - s.index[0].date()).days / 365.25
    cagr = (final_value / INITIAL) ** (1.0 / years) - 1.0
    drawdown = s / s.cummax() - 1.0
    rets = s.pct_change().dropna()
    vol = rets.std() * math.sqrt(52) if len(rets) else 0.0
    sharpe = (rets.mean() * 52) / vol if vol else 0.0
    y = np.log(s.to_numpy(dtype=float))
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    pred = intercept + slope * x
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot else 1.0
    annual = annual_returns(s)
    return {
        "years": years,
        "cagr": cagr,
        "max_drawdown": float(drawdown.min()),
        "calmar": cagr / abs(float(drawdown.min())) if drawdown.min() < 0 else 0.0,
        "ulcer": math.sqrt(float((drawdown ** 2).mean())),
        "sharpe": sharpe,
        "r2": r2,
        "time_below_20": float((drawdown < -0.20).mean()),
        "time_below_40": float((drawdown < -0.40).mean()),
        "worst_year": min(annual.values()) if annual else 0.0,
        "best_year": max(annual.values()) if annual else 0.0,
        "positive_years": sum(1 for v in annual.values() if v > 0),
        "negative_years": sum(1 for v in annual.values() if v < 0),
    }


def annual_returns(s: pd.Series) -> Dict[int, float]:
    out: Dict[int, float] = {}
    for year in sorted(set(s.index.year)):
        sub = s[s.index.year == year]
        if len(sub) < 2:
            continue
        before = s[s.index < sub.index[0]]
        base = before.iloc[-1] if len(before) else sub.iloc[0]
        out[year] = float(sub.iloc[-1] / base - 1.0)
    return out


def weekday_name(weekday: int) -> str:
    return ["lunedi", "martedi", "mercoledi", "giovedi", "venerdi"][weekday]


def pct(x: float, d: int = 2) -> str:
    return f"{x * 100:.{d}f}%"


def money(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def load_current_winner() -> Dict:
    tax_row = None
    with (OUT_DIR / "apex_timing_sweep_tax_top.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["timing"] == "venerdi open" and row["strategy_label"] == "Buffer 5pp 5w":
                tax_row = row
                break
    gross_row = None
    with (OUT_DIR / "apex_timing_sweep_grid.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["timing"] == "venerdi open" and row["label"] == "Buffer 5pp 5w":
                gross_row = row
                break
    if not tax_row or not gross_row:
        raise RuntimeError("current winner rows not found")
    return {
        "label": "Vincitrice attuale - Buffer 5pp 5w",
        "timing": "venerdi open",
        "tax_mode": "netto",
        "lookback": 5,
        "buffer_pp": 5.0,
        "sma_weeks": 0,
        "dual": False,
        "final": float(tax_row["final_net"]),
        "gross_final": float(gross_row["final"]),
        "cagr": float(tax_row["cagr"]),
        "gross_cagr": float(gross_row["cagr"]),
        "max_drawdown": float(tax_row["max_drawdown"]),
        "gross_max_drawdown": float(gross_row["max_drawdown"]),
        "calmar": float(tax_row["calmar"]),
        "sharpe": float(tax_row["sharpe"]),
        "switches": int(tax_row["switches_ex_initial"]),
        "switches_per_year": float(tax_row["switches_per_year"]),
        "taxes_paid": float(tax_row["taxes_paid"]),
        "r2": None,
        "ulcer": None,
        "time_below_20": None,
        "time_below_40": None,
        "worst_year": None,
        "positive_years": None,
        "negative_years": None,
    }


def display(row: Dict) -> Dict:
    return {
        "Strategia": row["label"],
        "Timing": row["timing"],
        "Tipo": row["tax_mode"],
        "CAGR": pct(row["cagr"]),
        "Finale 10k": money(row["final"]),
        "MaxDD": pct(row["max_drawdown"]),
        "Calmar": round(row["calmar"], 3),
        "Sharpe": round(row["sharpe"], 3),
        "R2": "" if row.get("r2") is None else round(row["r2"], 3),
        "Ulcer": "" if row.get("ulcer") is None else pct(row["ulcer"]),
        "Sw/anno": round(row["switches_per_year"], 1),
    }


def main() -> int:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prices_close = build_proxy_prices(CACHE_DIR, price_col="close", range_="max")
    rows = []
    _, apex_r_as_written = backtest_strategy(prices_close, APEX_R, ucits_losses_to_zainetto=False)
    _, apex_r_corrected = backtest_strategy(prices_close, APEX_R, ucits_losses_to_zainetto=True)
    _, alfa = backtest_strategy(prices_close, APEX_ALFA_DEX, ucits_losses_to_zainetto=False)
    apex_r_as_written["label"] = "APEX R Fineco proposta (as-written)"
    apex_r_corrected["label"] = "APEX R Fineco proposta (fisco corretto)"
    winner = load_current_winner()
    rows.extend([apex_r_as_written, apex_r_corrected, alfa, winner])

    payload = {
        "start": START.isoformat(),
        "end": END.isoformat(),
        "rows": rows,
        "audit_findings": audit_findings(),
    }
    JSON_OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    report = make_report(rows)
    REPORT.write_text(report, encoding="utf-8")
    REPORT_TXT.write_text(report, encoding="utf-8")
    html = "<!doctype html><html lang='it'><meta charset='utf-8'><title>APEX definitive compare</title><style>body{font-family:Segoe UI,Arial,sans-serif;max-width:1080px;margin:24px auto;padding:0 16px;line-height:1.45;background:#f8fafc;color:#111827}pre{white-space:pre-wrap;background:white;border:1px solid #ddd;border-radius:10px;padding:18px}</style><pre>" + report.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "</pre></html>"
    REPORT_HTML.write_text(html, encoding="utf-8")
    print(REPORT)
    print(JSON_OUT)
    return 0


def audit_findings() -> List[str]:
    return [
        "APEX R dichiara prezzi intraday mercoledi 15:00, ma il codice usa solo barre daily Yahoo e nel main usa close.",
        "APEX R aggiunge filtro SMA30 che cambia la filosofia Rev2: se BTC e' sotto SMA, SP500 viene ignorato come fallback anche quando positivo.",
        "APEX R usa buffer 0pp: e' piu esposta a micro-cambi rispetto alle varianti buffer.",
        "APEX ALFA DEX e' lordo imposte: non e' confrontabile col netto Fineco senza modello fiscale cripto.",
        "APEX ALFA DEX usa GC=F come proxy Oro/PAXG: utile per serie lunga, ma non replica spread, liquidita' e tracking PAXG on-chain.",
        "Il cash e' modellato a rendimento zero: per Fineco sottostima XEON, per DEX sottostima eventuale stable yield ma evita ipotesi rischiose.",
        "Il codice as-written tratta le perdite UCITS SP500 come perse; Fineco indica che il capital gain/loss da compravendita quote ha componente redditi diversi, mentre i proventi periodici ETF restano redditi di capitale.",
    ]


def make_report(rows: List[Dict]) -> str:
    table = table_md([display(r) for r in rows], ["Strategia", "Timing", "Tipo", "CAGR", "Finale 10k", "MaxDD", "Calmar", "Sharpe", "R2", "Ulcer", "Sw/anno"])
    audit = "\n".join(f"- {x}" for x in audit_findings())
    return f"""# APEX R / ALFA DEX - revisione e confronto 2026-05-29

Stato: confronto quantitativo locale, nessun deploy.

## Metodo

- Periodo: {START.isoformat()} -> {END.isoformat()}.
- Dati: stessi proxy EUR Yahoo usati nei test APEX precedenti.
- Costo swap: 0,30%.
- APEX R e APEX ALFA DEX sono implementate seguendo il codice incollato.
- APEX R viene mostrata in due modi:
  - `as-written`: perdite UCITS SP500 considerate perse, come nel codice incollato.
  - `fisco corretto`: perdite UCITS considerate minus nello zainetto, ma plus ETF tassate come redditi di capitale. La differenza qui e' piccola.
- La vincitrice attuale e' presa dal report precedente: `Buffer 5pp 5w venerdi open`.

## Risultati

{table}

## Lettura

1. `APEX R Fineco proposta` migliora molto la vecchia APEX Rev2 sul drawdown, grazie al filtro SMA30, ma resta sotto la nostra vincitrice su CAGR, capitale finale e Calmar.
2. `APEX ALFA DEX proposta` e' molto forte come lordo e ha drawdown molto piu basso, ma non e' una risposta Fineco: niente SP500, niente tassazione cripto, uso PAXG/proxy oro, operativita' DEX.
3. La vincitrice attuale `Buffer 5pp 5w venerdi open` resta davanti nel confronto netto Fineco: CAGR netto 42,47% e finale netto 169.308 su 10k.
4. Se guardiamo solo robustezza/drawdown, ALFA DEX e' la piu pulita, ma e' un'altra categoria di rischio e fiscalita'.

## Audit tecnico della strategia incollata

{audit}

## Decisione provvisoria

- Per Fineco/regime amministrato: APEX R e' sensata come versione difensiva, ma non batte ancora `Buffer 5pp 5w venerdi open`.
- Per DEX: APEX ALFA DEX merita un filone separato, perche' il profilo e' interessante ma non confrontabile al netto fiscale italiano.
- Prossimo test necessario: walk-forward/rolling validation tra `Buffer 5pp 5w`, `APEX R + SMA30`, e una variante ibrida `Buffer 5pp 5w + SMA30` per capire se il filtro anti-crash migliora la nostra vincitrice senza uccidere il CAGR.
"""


if __name__ == "__main__":
    raise SystemExit(main())
