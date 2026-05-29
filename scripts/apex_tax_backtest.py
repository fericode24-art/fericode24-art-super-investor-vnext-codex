from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apex.config import ASSETS
from apex.engine import _as_date, select_weekly_observations
from apex.yahoo import build_proxy_prices
from scripts.apex_deep_research import (
    pct,
    period_return,
    raw_signal_for,
    round_metric,
    stats_for,
    table_md,
    variant_target,
)


CACHE_DIR = ROOT / "data" / "apex"
OUT_DIR = ROOT / "output"
DOC_PATH = ROOT / "docs" / "APEX_TAX_BACKTEST_2026-05-28.md"
TAX_RATE = 0.26
START = "2018-01-01"
END = "2026-05-27"
SWAP_COST_BPS = 30.0


@dataclass
class LossLot:
    amount: float
    expiry_year: int


@dataclass
class TaxState:
    lots: List[LossLot] = field(default_factory=list)
    taxes_paid: float = 0.0
    losses_created: float = 0.0
    losses_used: float = 0.0
    losses_expired: float = 0.0

    def expire(self, d: date) -> None:
        keep: List[LossLot] = []
        for lot in self.lots:
            if d.year > lot.expiry_year:
                self.losses_expired += lot.amount
            else:
                keep.append(lot)
        self.lots = keep

    @property
    def zainetto(self) -> float:
        return sum(l.amount for l in self.lots)

    def add_loss(self, amount: float, d: date) -> None:
        if amount <= 0:
            return
        self.losses_created += amount
        self.lots.append(LossLot(amount=amount, expiry_year=d.year + 4))

    def use_against_gain(self, gain: float, d: date) -> Tuple[float, float]:
        self.expire(d)
        if gain <= 0:
            return 0.0, 0.0
        remaining = gain
        used = 0.0
        self.lots.sort(key=lambda x: x.expiry_year)
        keep: List[LossLot] = []
        for lot in self.lots:
            if remaining <= 0:
                keep.append(lot)
                continue
            take = min(lot.amount, remaining)
            lot.amount -= take
            remaining -= take
            used += take
            if lot.amount > 1e-9:
                keep.append(lot)
        self.lots = keep
        self.losses_used += used
        tax = remaining * TAX_RATE
        self.taxes_paid += tax
        return tax, used


def is_redditi_diversi(asset: str) -> bool:
    return ASSETS[asset].tax_bucket.startswith("redditi_diversi")


def realize_tax(asset: str, sale_value: float, basis: float, d: date, state: TaxState) -> Tuple[float, float, float]:
    """Return tax, realized gain, realized loss added to zainetto."""
    state.expire(d)
    pnl = sale_value - basis
    if pnl <= 0:
        loss = -pnl
        state.add_loss(loss, d)
        return 0.0, pnl, loss
    if is_redditi_diversi(asset):
        tax, _ = state.use_against_gain(pnl, d)
        return tax, pnl, 0.0
    tax = pnl * TAX_RATE
    state.taxes_paid += tax
    return tax, pnl, 0.0


def first_signal_date(rows: List[Dict], lookback: int, start: str, end: str) -> date:
    s, e = _as_date(start), _as_date(end)
    signals = [raw_signal_for(rows, i, lookback) for i in range(lookback, len(rows))]
    in_period = [x for x in signals if s <= x.date <= e]
    if not in_period:
        raise ValueError("no in-period signals")
    return in_period[0].date


def row_by_date(rows: List[Dict]) -> Dict[date, Dict]:
    return {_as_date(r["date"]): r for r in rows}


def run_tax_strategy(
    rows: List[Dict],
    lookback: int,
    variant: str,
    label: str,
    initial_value: float,
    start: str = START,
    end: str = END,
    raw_mode: str = "apex",
    cost_bps: float = SWAP_COST_BPS,
) -> Tuple[Dict, pd.DataFrame]:
    s, e = _as_date(start), _as_date(end)
    all_signals = [raw_signal_for(rows, i, lookback, mode=raw_mode) for i in range(lookback, len(rows))]
    signals = [info for info in all_signals if s <= info.date <= e]
    if len(signals) < 2:
        raise ValueError("not enough in-period signals")

    value = float(initial_value)
    current: Optional[str] = None
    basis = 0.0
    tax = TaxState()
    state: Dict = {"pending": None, "pending_count": 0}
    entries = 0
    switches_ex_initial = 0
    swap_costs = 0.0
    records = []

    for pos, info in enumerate(signals[:-1]):
        nxt_info = signals[pos + 1]
        d = info.date
        target = variant_target(info, current, state, variant)
        changed = target != current
        tax_paid = 0.0
        realized_pnl = 0.0
        loss_added = 0.0
        cost = 0.0
        if changed:
            if current is not None:
                tax_paid, realized_pnl, loss_added = realize_tax(current, value, basis, d, tax)
                value -= tax_paid
                switches_ex_initial += 1
            else:
                entries += 1
            cost = value * cost_bps / 10000.0
            value -= cost
            swap_costs += cost
            current = target
            basis = value
        row = rows[info.idx]
        nxt = rows[nxt_info.idx]
        ret = period_return(row, nxt, current or target)
        value *= 1.0 + ret
        tax.expire(nxt_info.date)
        records.append({
            "date": d,
            "next_date": nxt_info.date,
            "signal": current,
            "raw_signal": info.raw,
            "changed": changed,
            "tax_paid": tax_paid,
            "realized_pnl": realized_pnl,
            "loss_added": loss_added,
            "swap_cost": cost,
            "cost": cost,
            "zainetto": tax.zainetto,
            "value_before_final_tax": value,
            "basis": basis,
            "period_ret": ret,
        })

    final_date = signals[-1].date
    final_asset = current or signals[-2].raw
    final_tax, final_pnl, final_loss = realize_tax(final_asset, value, basis, final_date, tax)
    final_value = value - final_tax
    records.append({
        "date": final_date,
        "next_date": final_date,
        "signal": final_asset,
        "raw_signal": signals[-1].raw,
        "changed": False,
        "tax_paid": final_tax,
        "realized_pnl": final_pnl,
        "loss_added": final_loss,
        "swap_cost": 0.0,
        "cost": 0.0,
        "zainetto": tax.zainetto,
        "value_before_final_tax": final_value,
        "basis": final_value,
        "period_ret": 0.0,
    })
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    stats = stats_for(df.rename(columns={"value_before_final_tax": "value"}), {
        "label": label,
        "variant": variant,
        "lookback": lookback,
        "raw_mode": raw_mode,
        "entries": entries,
        "switches_ex_initial": switches_ex_initial,
        "taxable_sells": switches_ex_initial + 1,
        "swap_costs": swap_costs,
        "taxes_paid": tax.taxes_paid,
        "zainetto_remaining": tax.zainetto,
        "zainetto_created": tax.losses_created,
        "zainetto_used": tax.losses_used,
        "zainetto_expired": tax.losses_expired,
        "final_net": final_value,
        "final_asset": final_asset,
        "final_liquidation_tax": final_tax,
    })
    return stats, df


def run_tax_benchmark(
    rows: List[Dict],
    dates: List[date],
    asset: str,
    label: str,
    initial_value: float,
) -> Dict:
    selected = [row_by_date(rows)[d] for d in dates]
    tax = TaxState()
    if asset == "EQUAL":
        parts = ["BTC", "GOLD", "SP500"]
        gross_final = 0.0
        taxes = 0.0
        zainetto_created = 0.0
        for part in parts:
            start_price = float(selected[0][part])
            end_price = float(selected[-1][part])
            basis = initial_value / len(parts)
            sale_value = basis * end_price / start_price
            tax_paid, _, loss = realize_tax(part, sale_value, basis, dates[-1], tax)
            gross_final += sale_value
            taxes += tax_paid
            zainetto_created += loss
        final = gross_final - taxes
        series = pd.Series(
            [sum(initial_value / 3.0 * float(r[p]) / float(selected[0][p]) for p in parts) for r in selected],
            index=pd.to_datetime(dates),
            name=label,
        )
    else:
        start_price = float(selected[0][asset])
        end_price = float(selected[-1][asset])
        gross_final = initial_value * end_price / start_price
        tax_paid, _, _ = realize_tax(asset, gross_final, initial_value, dates[-1], tax)
        final = gross_final - tax_paid
        series = pd.Series(
            [initial_value * float(r[asset]) / start_price for r in selected],
            index=pd.to_datetime(dates),
            name=label,
        )
    out = stats_for(series, {
        "label": label,
        "variant": label,
        "lookback": "",
        "entries": 1,
        "switches_ex_initial": 0,
        "taxable_sells": 1,
        "swap_costs": 0.0,
        "taxes_paid": tax.taxes_paid,
        "zainetto_remaining": tax.zainetto,
        "zainetto_created": tax.losses_created,
        "zainetto_used": tax.losses_used,
        "zainetto_expired": tax.losses_expired,
        "final_net": final,
        "final_asset": asset,
        "final_liquidation_tax": tax.taxes_paid,
    })
    # Override final stats to after-tax liquidation value while keeping the
    # path drawdown from mark-to-market buy-and-hold.
    out["final"] = final
    out["total_return"] = final / initial_value - 1.0
    years = (dates[-1] - dates[0]).days / 365.25
    out["cagr"] = (final / initial_value) ** (1 / years) - 1.0
    return out


def money(x: float) -> str:
    return f"{float(x):,.0f}".replace(",", ".")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prices = build_proxy_prices(CACHE_DIR, price_col="open", range_="max")
    rows = select_weekly_observations(prices)
    rbd = row_by_date(rows)

    start_date = first_signal_date(rows, 8, START, END)
    end_date = _as_date(END)
    all_dates = [d for d in sorted(rbd) if start_date <= d <= end_date]
    initial_value = float(rbd[start_date]["BTC"])
    final_btc_price = float(rbd[end_date]["BTC"])

    candidates = [
        ("buffer_2pp", "apex", 6, "Buffer 2pp 6w"),
        ("confirm2", "apex", 6, "Confirm2 6w"),
        ("confirm2_buffer2", "apex", 6, "Confirm2+buffer 6w"),
        ("pure_relative", "pure_relative", 8, "Pure-relative 8w"),
        ("apex_rev2", "apex", 6, "APEX Rev2 6w"),
        ("buffer_5pp", "apex", 8, "Buffer 5pp 8w"),
        ("confirm2", "apex", 10, "Confirm2 10w"),
        ("apex_rev2", "apex", 8, "APEX Rev2 8w originale"),
        ("buffer_5pp", "apex", 16, "Buffer 5pp 16w"),
        ("apex_rev2", "apex", 17, "APEX Rev2 17w"),
    ]
    stats_rows = []
    frames = {}
    for variant, raw_mode, lb, label in candidates:
        st, frame = run_tax_strategy(
            rows,
            lookback=lb,
            variant=variant,
            label=label,
            initial_value=initial_value,
            start=START,
            end=END,
            raw_mode=raw_mode,
        )
        stats_rows.append(st)
        frames[label] = frame

    benchmark_dates = all_dates
    stats_rows.append(run_tax_benchmark(rows, benchmark_dates, "BTC", "BTC buy&hold", initial_value))
    stats_rows.append(run_tax_benchmark(rows, benchmark_dates, "EQUAL", "Equal BTC/Oro/SP500", initial_value))

    results = pd.DataFrame(stats_rows)
    results["final_btc_equiv_net"] = results["final_net"] / final_btc_price
    results["net_gain_vs_1btc_eur"] = results["final_net"] - final_btc_price
    results = results.sort_values("final_net", ascending=False)
    results.to_csv(OUT_DIR / "apex_tax_results_2018_1btc.csv", index=False)

    detail_rows = []
    for _, r in results.iterrows():
        detail_rows.append({
            "rank": len(detail_rows) + 1,
            "strategia": r["label"],
            "netto EUR": money(r["final_net"]),
            "BTC eq netto": round(float(r["final_btc_equiv_net"]), 3),
            "CAGR netto": f"{pct(r['cagr'])}%",
            "Max DD": f"{pct(r['max_drawdown'])}%",
            "swap": int(r["switches_ex_initial"]),
            "vendite fiscali": int(r["taxable_sells"]),
            "tasse pagate": money(r["taxes_paid"]),
            "zainetto creato": money(r["zainetto_created"]),
            "zainetto usato": money(r["zainetto_used"]),
            "zainetto finale": money(r["zainetto_remaining"]),
        })

    compact_payload = [
        {k: round_metric(k, v) for k, v in row.items()}
        for row in results.to_dict(orient="records")
    ]
    (OUT_DIR / "apex_tax_results_2018_1btc.json").write_text(
        json.dumps({
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "initial_btc_eur": initial_value,
            "final_btc_eur": final_btc_price,
            "tax_rate": TAX_RATE,
            "swap_cost_bps": SWAP_COST_BPS,
            "results": compact_payload,
        }, indent=2, default=str),
        encoding="utf-8",
    )

    report = f"""# APEX tax backtest 1 BTC - 2026-05-28

Stato: simulazione fiscale, nessun deploy.

## Ipotesi

- Periodo: {start_date.isoformat()} -> {end_date.isoformat()}.
- Capitale iniziale: valore EUR di 1 BTC al primo mercoledi utile = {money(initial_value)} EUR.
- Valore finale lordo di 1 BTC al {end_date.isoformat()}: {money(final_btc_price)} EUR.
- Regime simulato: amministrato Italia.
- Aliquota: 26%.
- BTC ETP e Oro ETC: redditi diversi, quindi plus compensabili con zainetto disponibile.
- SP500 ETF UCITS e XEON ETF UCITS: plus come redditi di capitale, tassate senza usare zainetto; minus aggiunte allo zainetto.
- Zainetto: scadenza modellata al 31 dicembre del quarto anno successivo alla minus.
- Costi: 30 bps su ingresso iniziale e ogni cambio posizione, come nel backtest precedente.
- Valore finale: posizione finale liquidata fiscalmente. Non e' consulenza fiscale.

## Classifica Netta

{table_md(detail_rows, ["rank", "strategia", "netto EUR", "BTC eq netto", "CAGR netto", "Max DD", "swap", "vendite fiscali", "tasse pagate", "zainetto creato", "zainetto usato", "zainetto finale"])}

## Lettura Rapida

1. `Buffer 2pp 6w` resta primo anche dopo tasse e zainetto.
2. `Confirm2 6w` e `Confirm2+buffer 6w` sono identici in questa simulazione.
3. `APEX 8w originale` batte nettamente BTC buy&hold netto tasse, ma scende dietro le varianti 6w filtrate.
4. `Pure-relative 8w` va forte, ma cambia filosofia perche lascia SP500 battere direttamente BTC.
5. La colonna `BTC eq netto` dice quanti BTC finali equivalenti avresti dopo tasse se riconvertissi il valore netto finale al prezzo BTC finale.

## File Generati

- `output/apex_tax_results_2018_1btc.csv`
- `output/apex_tax_results_2018_1btc.json`
"""
    DOC_PATH.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
