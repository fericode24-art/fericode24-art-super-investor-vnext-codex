from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apex.engine import select_weekly_observations
from apex.yahoo import build_proxy_prices
from scripts.apex_daily_sweep import daily_rows, stats_for_daily
from scripts.apex_deep_research import pct, run_strategy_period, stats_for, table_md
from scripts.apex_tax_backtest import run_tax_strategy


CACHE_DIR = ROOT / "data" / "apex"
OUT_DIR = ROOT / "output"
DOC_DIR = ROOT / "docs"
GRID_WEEKLY = OUT_DIR / "apex_timing_sweep_grid.csv"
GRID_DAILY = OUT_DIR / "apex_daily_sweep_grid.csv"
REPORT_PATH = DOC_DIR / "APEX_STRESS_SELECTION_2026-05-29.md"
PROMPT_PATH = DOC_DIR / "APEX_STRATEGY_SELECTION_PROMPT_2026-05-29.md"
JSON_PATH = OUT_DIR / "apex_stress_selection_results.json"

START = "2018-01-01"
END = "2026-05-29"
INITIAL = 10_000.0
MAX_SWAPS_PER_YEAR = 15.0

WEEKDAYS = {
    "lunedi": 0,
    "martedi": 1,
    "mercoledi": 2,
    "giovedi": 3,
    "venerdi": 4,
}


def read_rows(path: Path, freq: str) -> List[Dict]:
    rows: List[Dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row = dict(row)
            row["freq_type"] = freq
            if freq == "weekly":
                row["moment"] = row["timing"]
            else:
                row["moment"] = f"daily {row['price_col']}"
            for col in [
                "final",
                "cagr",
                "max_drawdown",
                "sharpe",
                "calmar",
                "switches",
                "switches_per_year",
                "in_cagr",
                "in_sharpe",
                "in_max_drawdown",
                "out_cagr",
                "out_sharpe",
                "out_max_drawdown",
                "robust_cagr",
                "robust_sharpe",
            ]:
                if col in row:
                    row[col] = float(row[col])
            row["dd_abs"] = abs(row["max_drawdown"])
            rows.append(row)
    return rows


def get_price_col(row: Dict) -> str:
    if row["freq_type"] == "daily":
        return str(row["price_col"])
    return str(row["price_col"])


def get_weekday(row: Dict) -> int:
    timing = str(row["timing"])
    day_name = timing.split()[0]
    return WEEKDAYS[day_name]


def rows_for(row: Dict, cache: Dict) -> List[Dict]:
    price_col = get_price_col(row)
    if row["freq_type"] == "weekly":
        weekday = get_weekday(row)
        key = ("weekly", price_col, weekday)
        if key not in cache:
            prices = build_proxy_prices(CACHE_DIR, price_col=price_col, range_="max")
            cache[key] = select_weekly_observations(prices, weekday=weekday)
        return cache[key]
    key = ("daily", price_col)
    if key not in cache:
        prices = build_proxy_prices(CACHE_DIR, price_col=price_col, range_="max")
        cache[key] = daily_rows(prices)
    return cache[key]


def stats_for_freq(frame: pd.DataFrame, freq_type: str, extra: Dict | None = None) -> Dict:
    return stats_for_daily(frame, extra) if freq_type == "daily" else stats_for(frame, extra)


def equity_for(row: Dict, cache: Dict, cost_bps: float = 30.0) -> pd.DataFrame:
    rows = rows_for(row, cache)
    return run_strategy_period(
        rows,
        int(row["lookback"]),
        str(row["variant"]),
        cost_bps=cost_bps,
        start=START,
        end=END,
        raw_mode=str(row["raw_mode"]),
    )


def r2_log_equity(s: pd.Series) -> float:
    y = np.log(s.dropna().to_numpy(dtype=float))
    if len(y) < 3:
        return float("nan")
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    pred = intercept + slope * x
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return 1.0 - ss_res / ss_tot if ss_tot else 1.0


def max_underwater_run(dd: pd.Series) -> int:
    flags = (dd < 0).astype(int)
    groups = (flags == 0).cumsum()
    return int(flags.groupby(groups).sum().max()) if len(flags) else 0


def annual_returns(s: pd.Series) -> Dict[int, float]:
    out: Dict[int, float] = {}
    years = sorted(set(s.index.year))
    for year in years:
        sub = s[s.index.year == year]
        if len(sub) < 2:
            continue
        before = s[s.index < sub.index[0]]
        start = before.iloc[-1] if len(before) else sub.iloc[0]
        out[year] = float(sub.iloc[-1] / start - 1.0)
    return out


def monthly_returns(s: pd.Series) -> pd.Series:
    last = s.resample("ME").last().dropna()
    first = s.resample("ME").first().dropna()
    both = pd.concat([first, last], axis=1, keys=["first", "last"]).dropna()
    return both["last"] / both["first"] - 1.0


def stress_metrics(row: Dict, cache: Dict) -> Dict:
    frame = equity_for(row, cache, cost_bps=30.0)
    s = frame["value"].dropna()
    dd = s / s.cummax() - 1.0
    years = annual_returns(s)
    months = monthly_returns(s)
    return {
        "freq_type": row["freq_type"],
        "moment": row["moment"],
        "label": row["label"],
        "variant": row["variant"],
        "lookback": int(row["lookback"]),
        "cagr": row["cagr"],
        "final": row["final"],
        "max_drawdown": row["max_drawdown"],
        "sharpe": row["sharpe"],
        "calmar": row["calmar"],
        "out_cagr": row["out_cagr"],
        "out_sharpe": row["out_sharpe"],
        "out_max_drawdown": row["out_max_drawdown"],
        "switches": int(row["switches"]),
        "switches_per_year": row["switches_per_year"],
        "linearity_r2": r2_log_equity(s),
        "ulcer_index": math.sqrt(float((dd ** 2).mean())),
        "time_below_20": float((dd < -0.20).mean()),
        "time_below_40": float((dd < -0.40).mean()),
        "max_underwater_observations": max_underwater_run(dd),
        "positive_years": sum(1 for v in years.values() if v > 0),
        "negative_years": sum(1 for v in years.values() if v < 0),
        "worst_year": min(years.values()) if years else 0.0,
        "best_year": max(years.values()) if years else 0.0,
        "worst_month": float(months.min()) if len(months) else 0.0,
        "best_month": float(months.max()) if len(months) else 0.0,
    }


def cost_sensitivity(row: Dict, cache: Dict) -> List[Dict]:
    out: List[Dict] = []
    for cost in (10, 30, 60, 100):
        frame = equity_for(row, cache, cost_bps=float(cost))
        st = stats_for_freq(frame, row["freq_type"])
        out.append({
            "strategia": f"{row['moment']} / {row['label']}",
            "costo bps": cost,
            "CAGR": st["cagr"],
            "Max DD": st["max_drawdown"],
            "Finale 10k": st["final"],
            "Switch": int(st["switches"]),
        })
    return out


def plateau_rows(row: Dict, all_rows: Iterable[Dict]) -> List[Dict]:
    lb = int(row["lookback"])
    span = 2 if row["freq_type"] == "weekly" else 10
    out = []
    for other in all_rows:
        if other["freq_type"] != row["freq_type"]:
            continue
        if other["moment"] != row["moment"]:
            continue
        if other["variant"] != row["variant"] or other["raw_mode"] != row["raw_mode"]:
            continue
        if abs(int(other["lookback"]) - lb) <= span:
            out.append(other)
    return sorted(out, key=lambda x: int(x["lookback"]))


def stability_summary(row: Dict, all_rows: Iterable[Dict]) -> Dict:
    plateau = plateau_rows(row, all_rows)
    if row["freq_type"] == "weekly":
        timing_peers = [
            x for x in all_rows
            if x["freq_type"] == "weekly"
            and x["variant"] == row["variant"]
            and x["raw_mode"] == row["raw_mode"]
            and int(x["lookback"]) == int(row["lookback"])
        ]
    else:
        timing_peers = [
            x for x in all_rows
            if x["freq_type"] == "daily"
            and x["variant"] == row["variant"]
            and x["raw_mode"] == row["raw_mode"]
            and int(x["lookback"]) == int(row["lookback"])
        ]
    plateau_cagr = [float(x["cagr"]) for x in plateau]
    timing_cagr = [float(x["cagr"]) for x in timing_peers]
    return {
        "Segnale": row["moment"],
        "Strategia": row["label"],
        "CAGR": fmt_pct(row["cagr"]),
        "Plateau medio": fmt_pct(sum(plateau_cagr) / len(plateau_cagr)),
        "Plateau min": fmt_pct(min(plateau_cagr)),
        "Timing medio": fmt_pct(sum(timing_cagr) / len(timing_cagr)),
        "Timing min": fmt_pct(min(timing_cagr)),
        "Nota": "ok" if min(plateau_cagr) > 0.35 and min(timing_cagr) > 0.25 else "fragile",
    }


def tax_for(row: Dict, cache: Dict) -> Dict:
    rows = rows_for(row, cache)
    label = f"{row['moment']} / {row['label']}"
    st, _ = run_tax_strategy(
        rows,
        lookback=int(row["lookback"]),
        variant=str(row["variant"]),
        label=label,
        initial_value=INITIAL,
        start=START,
        end=END,
        raw_mode=str(row["raw_mode"]),
        cost_bps=30.0,
    )
    return st


def fmt_pct(x: float, digits: int = 2) -> str:
    return f"{x * 100:.{digits}f}%"


def money(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def display_candidate(row: Dict) -> Dict:
    return {
        "Segnale": row["moment"],
        "Strategia": row["label"],
        "CAGR": fmt_pct(row["cagr"]),
        "Out CAGR": fmt_pct(row["out_cagr"]),
        "Max DD": fmt_pct(row["max_drawdown"]),
        "Sharpe": round(row["sharpe"], 3),
        "Calmar": round(row["calmar"], 3),
        "Sw/anno": round(row["switches_per_year"], 1),
        "Finale 10k": money(row["final"]),
    }


def display_stress(row: Dict) -> Dict:
    return {
        "Segnale": row["moment"],
        "Strategia": row["label"],
        "CAGR": fmt_pct(row["cagr"]),
        "Max DD": fmt_pct(row["max_drawdown"]),
        "R2 linea": round(row["linearity_r2"], 3),
        "Ulcer": fmt_pct(row["ulcer_index"]),
        "Tempo DD>20": fmt_pct(row["time_below_20"], 1),
        "Tempo DD>40": fmt_pct(row["time_below_40"], 1),
        "Peggior anno": fmt_pct(row["worst_year"], 1),
        "Anni + / -": f"{row['positive_years']} / {row['negative_years']}",
        "Sw/anno": round(row["switches_per_year"], 1),
    }


def display_tax(row: Dict, tax: Dict) -> Dict:
    return {
        "Segnale": row["moment"],
        "Strategia": row["label"],
        "Netto 10k": money(float(tax["final_net"])),
        "CAGR netto": fmt_pct(float(tax["cagr"])),
        "DD netto": fmt_pct(float(tax["max_drawdown"])),
        "Tasse": money(float(tax["taxes_paid"])),
        "Swap": int(tax["switches_ex_initial"]),
    }


def rank_top5(stress: List[Dict]) -> List[Dict]:
    metrics = [
        ("cagr", True),
        ("max_drawdown", True),  # less negative is better
        ("linearity_r2", True),
        ("ulcer_index", False),
        ("time_below_40", False),
        ("out_cagr", True),
        ("out_sharpe", True),
        ("switches_per_year", False),
    ]
    ranked = []
    for row in stress:
        score = 0
        for key, high in metrics:
            order = sorted(stress, key=lambda x: x[key], reverse=high)
            score += order.index(row) + 1
        ranked.append({**row, "robust_score": score})
    return sorted(ranked, key=lambda x: x["robust_score"])


def write_prompt(top5: List[Dict], anchors: List[Dict]) -> None:
    prompt = """# Prompt per scegliere la strategia APEX finale

Obiettivo: decidere quale strategia APEX seguire in produzione, quale timing di segnale usare, e quale candidata e' piu robusta, cioe' piu lineare e con meno drawdown.

Contesto: la strategia nasce dal concetto Dual Momentum BTC/Gold e dalla versione APEX Rev2 BTC-centrica. L'utente accetta fino a 15 swap/anno. Operativita' Fineco, strumenti in EUR quando disponibili, segnale informativo senza ordini automatici.

Universo:
- BTC: WisdomTree Physical Bitcoin o ETP BTC equivalente acquistabile su Fineco.
- GOLD: iShares Physical Gold / ETC oro fisico a basso TER.
- SP500: ETF UCITS S&P 500 basso TER e liquido.
- CASH: XEON / overnight EUR.

Regole comuni:
- 100% del capitale su un solo asset alla volta.
- Momentum = prezzo oggi / prezzo lookback - 1, calcolato in EUR.
- Costo swap nel test base: 0,30% per cambio.
- Vincolo operativo: scartare strategie sopra 15 swap/anno.

Strategie candidate da confrontare:

```python
STRATEGIES = [
    {
        "name": "APEX Rev2 originale 8w",
        "type": "weekly",
        "timing_to_test": ["mercoledi close", "mercoledi open"],
        "lookback": "8 settimane",
        "rule": "BTC vince se ret_BTC > 0 e ret_BTC >= ret_GOLD; altrimenti GOLD se positivo e > SP500; altrimenti SP500 se positivo e > GOLD; altrimenti CASH.",
        "note": "SP500 non compete mai direttamente con BTC. Questa e' la regola originale da usare come benchmark obbligatorio."
    },
    {
        "name": "Buffer 5pp 5w",
        "type": "weekly",
        "timing_to_test": ["venerdi open"],
        "lookback": "5 settimane",
        "rule": "Calcola APEX Rev2; cambia asset solo se il nuovo asset batte quello corrente di almeno 5 punti percentuali di momentum."
    },
    {
        "name": "Buffer 3pp 6w",
        "type": "weekly",
        "timing_to_test": ["martedi close"],
        "lookback": "6 settimane",
        "rule": "Calcola APEX Rev2; cambia asset solo se il nuovo asset batte quello corrente di almeno 3 punti percentuali di momentum."
    },
    {
        "name": "Pure Relative 7w",
        "type": "weekly",
        "timing_to_test": ["martedi close"],
        "lookback": "7 settimane",
        "rule": "Sceglie l'asset con momentum positivo piu alto tra BTC, GOLD e SP500; se nessuno e' positivo va in CASH. Nessuna priorita' BTC."
    },
    {
        "name": "Confirm2+Buffer2 90d",
        "type": "daily",
        "timing_to_test": ["daily open"],
        "lookback": "90 giorni di trading",
        "rule": "Calcola APEX Rev2 ogni giorno; richiede due segnali consecutivi uguali e poi cambia solo se il nuovo asset supera quello corrente di almeno 2 punti percentuali."
    },
    {
        "name": "Buffer 5pp 8w",
        "type": "weekly",
        "timing_to_test": ["lunedi open"],
        "lookback": "8 settimane",
        "rule": "Calcola APEX Rev2; cambia asset solo se il nuovo asset batte quello corrente di almeno 5 punti percentuali."
    },
]
```

Richiesta di valutazione:
1. Filtra tutto con massimo 15 swap/anno.
2. Classifica i migliori per CAGR lordo e poi per CAGR netto fiscale.
3. Tra i migliori, scegli il candidato piu robusto usando: MaxDD, ulcer index, linearita' R2 della curva log, tempo sotto -20% e -40%, peggior anno, Sharpe out-of-sample 2023-2026.
4. Controlla se il timing vincente e' stabile o se sembra overfitting di calendario.
5. Confronta sempre contro APEX Rev2 originale 8w.
6. Restituisci una decisione finale: strategia consigliata, timing segnale consigliato, motivi, rischi residui e cosa monitorare live.
"""
    PROMPT_PATH.write_text(prompt, encoding="utf-8")


def main() -> int:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_rows = read_rows(GRID_WEEKLY, "weekly") + read_rows(GRID_DAILY, "daily")
    eligible = [r for r in all_rows if r["switches_per_year"] <= MAX_SWAPS_PER_YEAR]
    top5 = sorted(eligible, key=lambda r: r["cagr"], reverse=True)[:5]

    anchors = []
    anchor_keys = {
        ("weekly", "mercoledi close", "APEX 8w"),
        ("weekly", "mercoledi open", "APEX 8w"),
    }
    for row in all_rows:
        if (row["freq_type"], row["moment"], row["label"]) in anchor_keys:
            anchors.append(row)

    selected = top5 + [a for a in anchors if a not in top5]
    cache: Dict = {}
    stress = [stress_metrics(r, cache) for r in selected]
    top5_stress = stress[: len(top5)]
    robust_rank = rank_top5(top5_stress)
    taxes = {f"{r['moment']} / {r['label']}": tax_for(r, cache) for r in selected}

    costs = []
    for row in top5:
        costs.extend(cost_sensitivity(row, cache))

    plateau = []
    for row in top5:
        rows = plateau_rows(row, eligible)
        for p in rows:
            plateau.append({
                "Base": f"{row['moment']} / {row['label']}",
                "Lookback": int(p["lookback"]),
                "CAGR": p["cagr"],
                "Max DD": p["max_drawdown"],
                "Sw/anno": p["switches_per_year"],
                "Finale 10k": p["final"],
            })

    write_prompt(top5, anchors)

    payload = {
        "start": START,
        "end": END,
        "max_swaps_per_year": MAX_SWAPS_PER_YEAR,
        "top5_by_cagr": top5,
        "anchors": anchors,
        "stress": stress,
        "robust_rank": robust_rank,
        "tax": taxes,
        "cost_sensitivity": costs,
        "plateau": plateau,
    }
    JSON_PATH.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    stability = [stability_summary(r, eligible) for r in top5]

    report = f"""# APEX stress selection - 2026-05-29

Stato: ricerca quantitativa. Nessun deploy.

## Sintesi decisionale

Filtro applicato: massimo {MAX_SWAPS_PER_YEAR:.0f} swap/anno.

Il miglior candidato grezzo resta `Buffer 5pp 5w` con segnale `venerdi open`: e' primo per CAGR lordo, primo per netto fiscale tra i candidati stressati, ha il drawdown massimo piu basso tra i top 5 e pochi swap/anno.

La seconda lettura e' piu prudente: `Pure Relative 7w` e' la curva piu lineare, ma fa piu swap e perde la tesi BTC-centrica originale. `Confirm2+Buffer2 90d` e' interessante come daily ed e' piu stabile sul lookback, ma non batte il miglior weekly e ha drawdown/ulcer piu pesanti.

Avviso importante: il test di plateau segnala che molti vincitori hanno un picco molto preciso sul lookback. Quindi la scelta finale non deve essere fatta solo sul CAGR. APEX Rev2 8w originale resta un benchmark obbligatorio, ma nei test non e' il miglior candidato.

## Top 5 Per CAGR Con Vincolo Swap

{table_md([display_candidate(r) for r in top5], ["Segnale", "Strategia", "CAGR", "Out CAGR", "Max DD", "Sharpe", "Calmar", "Sw/anno", "Finale 10k"])}

## APEX Rev2 Originale Come Ancora

{table_md([display_candidate(r) for r in anchors], ["Segnale", "Strategia", "CAGR", "Out CAGR", "Max DD", "Sharpe", "Calmar", "Sw/anno", "Finale 10k"])}

## Stress Robustezza Dei Candidati

{table_md([display_stress(r) for r in stress], ["Segnale", "Strategia", "CAGR", "Max DD", "R2 linea", "Ulcer", "Tempo DD>20", "Tempo DD>40", "Peggior anno", "Anni + / -", "Sw/anno"])}

## Ranking Robustezza Tra I Top 5

Punteggio piu basso = migliore. Il ranking combina CAGR, drawdown, linearita', ulcer index, tempo sotto -40%, out-of-sample e numero swap.

{table_md([{
    "Rank": i + 1,
    "Segnale": r["moment"],
    "Strategia": r["label"],
    "Score": r["robust_score"],
    "CAGR": fmt_pct(r["cagr"]),
    "Max DD": fmt_pct(r["max_drawdown"]),
    "R2 linea": round(r["linearity_r2"], 3),
    "Ulcer": fmt_pct(r["ulcer_index"]),
    "Out CAGR": fmt_pct(r["out_cagr"]),
    "Sw/anno": round(r["switches_per_year"], 1),
} for i, r in enumerate(robust_rank)], ["Rank", "Segnale", "Strategia", "Score", "CAGR", "Max DD", "R2 linea", "Ulcer", "Out CAGR", "Sw/anno"])}

## Stabilita' Parametro E Timing

`Plateau` = media/min dei lookback vicini allo stesso timing. `Timing` = media/min della stessa strategia/lookback su altri momenti di lettura. Se qui il numero crolla, il candidato puo essere overfit.

{table_md(stability, ["Segnale", "Strategia", "CAGR", "Plateau medio", "Plateau min", "Timing medio", "Timing min", "Nota"])}

## Netto Fiscale Stimato

Modello fiscale semplificato Italia con liquidazione finale, costo swap 0,30%. Serve per confronto, non per dichiarazione fiscale.

{table_md([display_tax(r, taxes[f"{r['moment']} / {r['label']}"]) for r in selected], ["Segnale", "Strategia", "Netto 10k", "CAGR netto", "DD netto", "Tasse", "Swap"])}

## Sensibilita' Ai Costi

{table_md([{
    "Strategia": r["strategia"],
    "Costo bps": r["costo bps"],
    "CAGR": fmt_pct(r["CAGR"]),
    "Max DD": fmt_pct(r["Max DD"]),
    "Finale 10k": money(float(r["Finale 10k"])),
    "Switch": r["Switch"],
} for r in costs], ["Strategia", "Costo bps", "CAGR", "Max DD", "Finale 10k", "Switch"])}

## Plateau Lookback Vicino Ai Vincitori

Questa tabella serve a capire se il risultato dipende da un singolo parametro fortunato.

{table_md([{
    "Base": r["Base"],
    "Lookback": r["Lookback"],
    "CAGR": fmt_pct(float(r["CAGR"])),
    "Max DD": fmt_pct(float(r["Max DD"])),
    "Sw/anno": round(float(r["Sw/anno"]), 1),
    "Finale 10k": money(float(r["Finale 10k"])),
} for r in plateau], ["Base", "Lookback", "CAGR", "Max DD", "Sw/anno", "Finale 10k"])}

## Decisione Provvisoria

1. Miglior rendimento/rischio operativo: `Buffer 5pp 5w`, segnale `venerdi open`, ma con flag di overfit sul lookback.
2. Miglior robustezza tra i top 5: `Pure Relative 7w`, segnale `martedi close`, soprattutto per linearita' curva.
3. Miglior stabilita' daily: `Confirm2+Buffer2 90d daily open`, ma paga drawdown piu profondo e complessita' maggiore.
4. Candidato operativo piu calmo: `Buffer 5pp 8w`, segnale `lunedi open`, ma il plateau e' fragile.
5. APEX Rev2 originale 8w: da tenere come benchmark obbligatorio, non come scelta finale automatica.

Conclusione prudente: non promuoverei ancora nessuna strategia senza walk-forward/rolling validation finale. Se devo scegliere un candidato da portare al prossimo step, porto `Buffer 5pp 5w venerdi open`; se devo scegliere la piu lineare/robusta, porto `Pure Relative 7w martedi close`.

## File Collegati

- Prompt pronto per confronto esterno: `{PROMPT_PATH.relative_to(ROOT)}`.
- Dati macchina: `{JSON_PATH.relative_to(ROOT)}`.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(REPORT_PATH)
    print(PROMPT_PATH)
    print(JSON_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
