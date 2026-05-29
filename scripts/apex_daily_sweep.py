from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apex.engine import _as_date
from apex.yahoo import build_proxy_prices
from scripts.apex_deep_research import pct, run_strategy_period, stats_for, table_md
from scripts.apex_tax_backtest import run_tax_strategy


CACHE_DIR = ROOT / "data" / "apex"
OUT_DIR = ROOT / "output"
DOC_PATH = ROOT / "docs" / "APEX_DAILY_SWEEP_2026-05-29.md"
START = "2018-01-01"
END = "2026-05-29"
INITIAL = 10_000.0
DAILY_PERIODS = 252


def daily_rows(prices: pd.DataFrame) -> List[Dict]:
    df = prices.copy().sort_index()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    # Realistic execution: Fineco instruments cannot be traded over the weekend.
    df = df[df.index.weekday < 5]
    df = df.dropna(subset=["BTC", "GOLD", "SP500"])
    out: List[Dict] = []
    for idx, row in df.iterrows():
        obs = {"date": idx.date()}
        for col in ("BTC", "GOLD", "SP500", "CASH"):
            if col in row and pd.notna(row[col]):
                obs[col] = float(row[col])
        out.append(obs)
    return out


def stats_for_daily(equity: pd.Series | pd.DataFrame, extra: Dict | None = None) -> Dict:
    frame = equity if isinstance(equity, pd.DataFrame) else None
    if isinstance(equity, pd.DataFrame):
        s = equity["value"] if "value" in equity.columns else equity.iloc[:, 0]
    else:
        s = equity
    s = s.dropna()
    if len(s) < 2:
        return {}
    rets = s.pct_change().dropna()
    years = max((s.index[-1] - s.index[0]).days / 365.25, 1 / DAILY_PERIODS)
    cagr = (s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1.0
    drawdown = s / s.cummax() - 1.0
    vol = rets.std() * (DAILY_PERIODS ** 0.5) if len(rets) else 0.0
    down = rets[rets < 0].std() * (DAILY_PERIODS ** 0.5) if len(rets[rets < 0]) else 0.0
    out = {
        "start": s.index[0].date().isoformat(),
        "end": s.index[-1].date().isoformat(),
        "years": years,
        "final": float(s.iloc[-1]),
        "total_return": float(s.iloc[-1] / s.iloc[0] - 1.0),
        "cagr": float(cagr),
        "max_drawdown": float(drawdown.min()),
        "volatility": float(vol),
        "downside_volatility": float(down),
        "sharpe": float(cagr / vol) if vol else 0.0,
        "sortino": float(cagr / down) if down else 0.0,
        "calmar": float(cagr / abs(drawdown.min())) if drawdown.min() else 0.0,
    }
    if frame is not None and "changed" in frame.columns:
        switches = int(frame["changed"].sum())
        out["switches"] = switches
        out["switches_per_year"] = switches / years
        if "cost" in frame.columns:
            out["total_cost"] = float(frame["cost"].sum())
        if "signal" in frame.columns:
            exposure = frame.loc[frame["signal"] != "START", "signal"].value_counts(normalize=True).to_dict()
            out["exposure_btc"] = exposure.get("BTC", 0.0)
            out["exposure_gold"] = exposure.get("GOLD", 0.0)
            out["exposure_sp500"] = exposure.get("SP500", 0.0)
            out["exposure_cash"] = exposure.get("CASH", 0.0)
    if extra:
        out.update(extra)
    return out


def candidate_specs() -> List[Dict]:
    out: List[Dict] = []
    # Trading-day lookbacks. Roughly: 20=4w, 40=8w, 60=12w.
    for lb in range(10, 101, 5):
        out.append({"family": "apex", "variant": "apex_rev2", "raw_mode": "apex", "lookback": lb, "label": f"APEX {lb}d"})
        out.append({"family": "confirm", "variant": "confirm2", "raw_mode": "apex", "lookback": lb, "label": f"Confirm2 {lb}d"})
        out.append({"family": "pure", "variant": "pure_relative", "raw_mode": "pure_relative", "lookback": lb, "label": f"Pure Relative {lb}d"})
        for pp in (1, 2, 3, 5):
            out.append({
                "family": "buffer",
                "variant": f"buffer_{pp}pp",
                "raw_mode": "apex",
                "lookback": lb,
                "label": f"Buffer {pp}pp {lb}d",
            })
        out.append({
            "family": "confirm_buffer",
            "variant": "confirm2_buffer2",
            "raw_mode": "apex",
            "lookback": lb,
            "label": f"Confirm2+Buffer2 {lb}d",
        })
    return out


def summarize(row: Dict) -> Dict:
    years = max(float(row.get("years", 1.0)), 1.0)
    switches = int(row["switches"])
    return {
        "frequenza": row["frequency"],
        "prezzo": row["price_col"],
        "strategia": row["label"],
        "famiglia": row["family"],
        "lookback": int(row["lookback"]),
        "CAGR": f"{pct(row['cagr'])}%",
        "Out CAGR": f"{pct(row['out_cagr'])}%",
        "Max DD": f"{pct(row['max_drawdown'])}%",
        "Sharpe": round(float(row["sharpe"]), 3),
        "Out Sharpe": round(float(row["out_sharpe"]), 3),
        "Switch": switches,
        "Sw/anno": round(switches / years, 1),
        "Finale 10k": round(float(row["final"]), 0),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    specs = candidate_specs()
    records: List[Dict] = []
    rows_by_price: Dict[str, List[Dict]] = {}

    for price_col in ("open", "close"):
        prices = build_proxy_prices(CACHE_DIR, price_col=price_col, range_="max")
        rows = daily_rows(prices)
        rows_by_price[price_col] = rows
        for spec in specs:
            try:
                full = run_strategy_period(
                    rows,
                    spec["lookback"],
                    spec["variant"],
                    cost_bps=30,
                    start=START,
                    end=END,
                    raw_mode=spec["raw_mode"],
                )
                in_sample = run_strategy_period(
                    rows,
                    spec["lookback"],
                    spec["variant"],
                    cost_bps=30,
                    start="2018-01-01",
                    end="2022-12-31",
                    raw_mode=spec["raw_mode"],
                )
                out_sample = run_strategy_period(
                    rows,
                    spec["lookback"],
                    spec["variant"],
                    cost_bps=30,
                    start="2023-01-01",
                    end=END,
                    raw_mode=spec["raw_mode"],
                )
            except ValueError:
                continue
            st = stats_for_daily(full, {
                **spec,
                "frequency": "daily",
                "price_col": price_col,
            })
            st_in = stats_for_daily(in_sample)
            st_out = stats_for_daily(out_sample)
            st.update({
                "in_cagr": st_in["cagr"],
                "in_sharpe": st_in["sharpe"],
                "in_max_drawdown": st_in["max_drawdown"],
                "out_cagr": st_out["cagr"],
                "out_sharpe": st_out["sharpe"],
                "out_max_drawdown": st_out["max_drawdown"],
                "robust_cagr": min(st_in["cagr"], st_out["cagr"]),
                "robust_sharpe": min(st_in["sharpe"], st_out["sharpe"]),
            })
            records.append(st)

    grid = pd.DataFrame(records)
    grid.to_csv(OUT_DIR / "apex_daily_sweep_grid.csv", index=False)

    top_final = grid.sort_values(["final", "out_sharpe"], ascending=False).head(25)
    top_out = grid.sort_values(["out_sharpe", "out_cagr", "final"], ascending=False).head(25)
    top_robust = grid.sort_values(["robust_sharpe", "robust_cagr", "final"], ascending=False).head(25)

    daily_leaders = []
    for price_col in ("open", "close"):
        part = grid[grid["price_col"] == price_col]
        if not part.empty:
            daily_leaders.append(summarize(part.sort_values(["final", "out_sharpe"], ascending=False).iloc[0].to_dict()))

    # Weekly anchors from the already produced timing sweep, if available.
    timing_grid_path = OUT_DIR / "apex_timing_sweep_grid.csv"
    weekly_anchors = []
    if timing_grid_path.exists():
        weekly = pd.read_csv(timing_grid_path)
        for timing, label in [
            ("mercoledi close", "APEX 8w"),
            ("mercoledi open", "Buffer 2pp 6w"),
            ("martedi close", "Buffer 3pp 6w"),
            ("venerdi open", "Buffer 5pp 5w"),
        ]:
            subset = weekly[(weekly["timing"] == timing) & (weekly["label"] == label)]
            if not subset.empty:
                r = subset.sort_values("final", ascending=False).iloc[0]
                years = max(float(r.get("years", 1.0)), 1.0)
                weekly_anchors.append({
                    "frequenza": "weekly",
                    "timing": timing,
                    "strategia": label,
                    "CAGR": f"{pct(r['cagr'])}%",
                    "Max DD": f"{pct(r['max_drawdown'])}%",
                    "Sharpe": round(float(r["sharpe"]), 3),
                    "Switch": int(r["switches"]),
                    "Sw/anno": round(float(r["switches"]) / years, 1),
                    "Finale 10k": round(float(r["final"]), 0),
                })

    tax_candidates = pd.concat([top_final.head(10), top_out.head(8), top_robust.head(8)]).drop_duplicates(
        subset=["price_col", "variant", "raw_mode", "lookback", "label"]
    )
    tax_records = []
    for _, row in tax_candidates.iterrows():
        rows = rows_by_price[row["price_col"]]
        try:
            st_raw, frame = run_tax_strategy(
                rows,
                lookback=int(row["lookback"]),
                variant=row["variant"],
                label=f"daily {row['price_col']} / {row['label']}",
                initial_value=INITIAL,
                start=START,
                end=END,
                raw_mode=row["raw_mode"],
            )
            st = stats_for_daily(frame.rename(columns={"value_before_final_tax": "value"}), {
                k: st_raw[k]
                for k in [
                    "label",
                    "variant",
                    "lookback",
                    "raw_mode",
                    "entries",
                    "switches_ex_initial",
                    "taxable_sells",
                    "swap_costs",
                    "taxes_paid",
                    "zainetto_remaining",
                    "zainetto_created",
                    "zainetto_used",
                    "zainetto_expired",
                    "final_net",
                    "final_asset",
                    "final_liquidation_tax",
                ]
                if k in st_raw
            })
        except ValueError:
            continue
        st.update({
            "frequency": "daily",
            "price_col": row["price_col"],
            "strategy_label": row["label"],
            "gross_final": row["final"],
            "gross_cagr": row["cagr"],
            "gross_sharpe": row["sharpe"],
        })
        tax_records.append(st)
    tax = pd.DataFrame(tax_records).sort_values("final_net", ascending=False)
    tax.to_csv(OUT_DIR / "apex_daily_sweep_tax_top.csv", index=False)

    def tax_row(row: Dict) -> Dict:
        years = max(float(row.get("years", 1.0)), 1.0)
        switches = int(row["switches_ex_initial"])
        return {
            "prezzo": row["price_col"],
            "strategia": row["strategy_label"],
            "netto 10k": round(float(row["final_net"]), 0),
            "CAGR netto": f"{pct(row['cagr'])}%",
            "Max DD": f"{pct(row['max_drawdown'])}%",
            "Sharpe": round(float(row["sharpe"]), 3),
            "Switch": switches,
            "Sw/anno": round(switches / years, 1),
            "tasse": round(float(row["taxes_paid"]), 0),
        }

    payload = {
        "start": START,
        "end": END,
        "assumption": "daily signals use Monday-Friday observations only; lookback is trading-day count",
        "top_final": top_final.to_dict(orient="records"),
        "top_out": top_out.to_dict(orient="records"),
        "top_robust": top_robust.to_dict(orient="records"),
        "tax_top": tax.to_dict(orient="records"),
    }
    (OUT_DIR / "apex_daily_sweep_results.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    report = f"""# APEX daily sweep - 2026-05-29

Stato: ricerca quantitativa, nessun deploy.

## Metodo

- Periodo: 2018-01-01 -> 2026-05-29.
- Frequenza: daily, solo giorni lunedi-venerdi.
- Prezzi testati: open e close.
- Lookback: 10 -> 100 sedute, passo 5.
- Varianti: APEX, Buffer 1/2/3/5pp, Confirm2, Confirm2+Buffer2, Pure Relative.
- Griglia principale: mark-to-market con costo cambio 30 bps.
- Tabella fiscale: solo candidati migliori, con liquidazione finale.
- Nota: daily e' molto piu' esposto a rumore, quindi la classifica assoluta va trattata con piu' sospetto rispetto al weekly.

## Vincitori Daily

{table_md(daily_leaders, ["frequenza", "prezzo", "strategia", "famiglia", "lookback", "CAGR", "Out CAGR", "Max DD", "Sharpe", "Out Sharpe", "Switch", "Sw/anno", "Finale 10k"])}

## Top Daily Mark-to-Market

{table_md([summarize(r.to_dict()) for _, r in top_final.head(15).iterrows()], ["frequenza", "prezzo", "strategia", "famiglia", "lookback", "CAGR", "Out CAGR", "Max DD", "Sharpe", "Out Sharpe", "Switch", "Sw/anno", "Finale 10k"])}

## Top Daily Out-of-Sample

{table_md([summarize(r.to_dict()) for _, r in top_out.head(15).iterrows()], ["frequenza", "prezzo", "strategia", "famiglia", "lookback", "CAGR", "Out CAGR", "Max DD", "Sharpe", "Out Sharpe", "Switch", "Sw/anno", "Finale 10k"])}

## Vista Fiscale Daily

{table_md([tax_row(r.to_dict()) for _, r in tax.head(15).iterrows()], ["prezzo", "strategia", "netto 10k", "CAGR netto", "Max DD", "Sharpe", "Switch", "Sw/anno", "tasse"])}

## Confronto Con Weekly

Ancora mark-to-market, costo switch incluso.

{table_md(weekly_anchors, ["frequenza", "timing", "strategia", "CAGR", "Max DD", "Sharpe", "Switch", "Sw/anno", "Finale 10k"])}

## Lettura Tecnica

1. Daily puo' trovare vincitori molto forti, ma aumenta il rischio di data mining.
2. Gli swap non crescono in modo lineare solo perche' controlli ogni giorno: i buffer frenano molto. Senza buffer, le versioni pure o APEX corte possono superare facilmente 20-30 cambi/anno.
3. Se una daily vince con lookback corto e tanti switch, va considerata fragile finche' non passa test piu severi.
4. Per una strategia reale su Fineco, weekly resta piu pulita operativamente. Daily ha senso solo se il vantaggio netto resta forte dopo tasse, spread, ritardi e stress test.

## File Generati

- `output/apex_daily_sweep_grid.csv`
- `output/apex_daily_sweep_tax_top.csv`
- `output/apex_daily_sweep_results.json`
"""
    DOC_PATH.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
