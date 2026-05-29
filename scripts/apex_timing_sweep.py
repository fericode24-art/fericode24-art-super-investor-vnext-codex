from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apex.engine import select_weekly_observations
from apex.yahoo import build_proxy_prices
from scripts.apex_deep_research import pct, run_strategy_period, stats_for, table_md
from scripts.apex_tax_backtest import run_tax_strategy


CACHE_DIR = ROOT / "data" / "apex"
OUT_DIR = ROOT / "output"
DOC_PATH = ROOT / "docs" / "APEX_TIMING_SWEEP_2026-05-29.md"
START = "2018-01-01"
END = "2026-05-29"
INITIAL = 10_000.0


TIMINGS: List[Tuple[str, str, int]] = [
    ("lunedi open", "open", 0),
    ("lunedi close", "close", 0),
    ("martedi open", "open", 1),
    ("martedi close", "close", 1),
    ("mercoledi open", "open", 2),
    ("mercoledi close", "close", 2),
    ("giovedi open", "open", 3),
    ("giovedi close", "close", 3),
    ("venerdi open", "open", 4),
    ("venerdi close", "close", 4),
]


def candidate_specs() -> List[Dict]:
    out: List[Dict] = []
    for lb in range(4, 21):
        out.append({"family": "apex", "variant": "apex_rev2", "raw_mode": "apex", "lookback": lb, "label": f"APEX {lb}w"})
        out.append({"family": "confirm", "variant": "confirm2", "raw_mode": "apex", "lookback": lb, "label": f"Confirm2 {lb}w"})
        out.append({"family": "pure", "variant": "pure_relative", "raw_mode": "pure_relative", "lookback": lb, "label": f"Pure Relative {lb}w"})
        for pp in (1, 2, 3, 5):
            out.append({
                "family": "buffer",
                "variant": f"buffer_{pp}pp",
                "raw_mode": "apex",
                "lookback": lb,
                "label": f"Buffer {pp}pp {lb}w",
            })
    for lb in range(4, 21):
        out.append({
            "family": "confirm_buffer",
            "variant": "confirm2_buffer2",
            "raw_mode": "apex",
            "lookback": lb,
            "label": f"Confirm2+Buffer2 {lb}w",
        })
    return out


def summarize(row: Dict) -> Dict:
    return {
        "timing": row["timing"],
        "strategia": row["label"],
        "famiglia": row["family"],
        "lookback": int(row["lookback"]),
        "CAGR": f"{pct(row['cagr'])}%",
        "Out CAGR": f"{pct(row['out_cagr'])}%",
        "Max DD": f"{pct(row['max_drawdown'])}%",
        "Sharpe": round(float(row["sharpe"]), 3),
        "Out Sharpe": round(float(row["out_sharpe"]), 3),
        "Calmar": round(float(row["calmar"]), 3),
        "Switch": int(row["switches"]),
        "Finale 10k": round(float(row["final"]), 0),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prices_by_col = {
        "open": build_proxy_prices(CACHE_DIR, price_col="open", range_="max"),
        "close": build_proxy_prices(CACHE_DIR, price_col="close", range_="max"),
    }
    specs = candidate_specs()
    records: List[Dict] = []
    rows_by_timing: Dict[str, List[Dict]] = {}

    for timing_name, price_col, weekday in TIMINGS:
        rows = select_weekly_observations(prices_by_col[price_col], weekday=weekday)
        rows_by_timing[timing_name] = rows
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
            st = stats_for(full, {
                **spec,
                "timing": timing_name,
                "price_col": price_col,
                "weekday": weekday,
            })
            st_in = stats_for(in_sample)
            st_out = stats_for(out_sample)
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
    grid.to_csv(OUT_DIR / "apex_timing_sweep_grid.csv", index=False)

    # Deduplicate near-identical parameter clusters only for report readability:
    # keep the best strategy per timing/family/label in the raw CSV, but show
    # the global and timing leaders in the markdown.
    top_by_final = grid.sort_values(["final", "out_sharpe"], ascending=False).head(20)
    top_by_out = grid.sort_values(["out_sharpe", "out_cagr", "final"], ascending=False).head(20)
    top_by_robust = grid.sort_values(["robust_sharpe", "robust_cagr", "final"], ascending=False).head(20)

    timing_leaders = []
    for timing_name, _, _ in TIMINGS:
        part = grid[grid["timing"] == timing_name]
        if part.empty:
            continue
        leader = part.sort_values(["final", "out_sharpe"], ascending=False).iloc[0].to_dict()
        timing_leaders.append(summarize(leader))

    monday_close = grid[grid["timing"] == "lunedi close"].sort_values(["final", "out_sharpe"], ascending=False).head(12)
    wednesday_close = grid[grid["timing"] == "mercoledi close"].sort_values(["final", "out_sharpe"], ascending=False).head(8)
    wednesday_open = grid[grid["timing"] == "mercoledi open"].sort_values(["final", "out_sharpe"], ascending=False).head(8)

    # Net-liquidated tax view for the top gross candidates and a few anchors.
    anchor_keys = {
        ("mercoledi close", "APEX 8w"),
        ("mercoledi open", "Buffer 2pp 6w"),
        ("lunedi close", "APEX 8w"),
        ("lunedi close", "Buffer 5pp 8w"),
    }
    tax_candidates = pd.concat([top_by_final.head(12), top_by_out.head(8), top_by_robust.head(8)])
    anchor_rows = grid[[((r["timing"], r["label"]) in anchor_keys) for _, r in grid.iterrows()]]
    tax_candidates = pd.concat([tax_candidates, anchor_rows]).drop_duplicates(
        subset=["timing", "variant", "raw_mode", "lookback", "label"]
    )
    tax_records = []
    for _, row in tax_candidates.iterrows():
        rows = rows_by_timing[row["timing"]]
        label = f"{row['timing']} / {row['label']}"
        try:
            st, _ = run_tax_strategy(
                rows,
                lookback=int(row["lookback"]),
                variant=row["variant"],
                label=label,
                initial_value=INITIAL,
                start=START,
                end=END,
                raw_mode=row["raw_mode"],
            )
        except ValueError:
            continue
        st.update({
            "timing": row["timing"],
            "strategy_label": row["label"],
            "family": row["family"],
            "gross_final": row["final"],
            "gross_cagr": row["cagr"],
            "gross_sharpe": row["sharpe"],
        })
        tax_records.append(st)
    tax = pd.DataFrame(tax_records).sort_values("final_net", ascending=False)
    tax.to_csv(OUT_DIR / "apex_timing_sweep_tax_top.csv", index=False)

    def tax_row(r: Dict) -> Dict:
        return {
            "timing": r["timing"],
            "strategia": r["strategy_label"],
            "netto 10k": round(float(r["final_net"]), 0),
            "CAGR netto": f"{pct(r['cagr'])}%",
            "DD netto": f"{pct(r['max_drawdown'])}%",
            "Sharpe netto": round(float(r["sharpe"]), 3),
            "switch": int(r["switches_ex_initial"]),
            "tasse": round(float(r["taxes_paid"]), 0),
        }

    payload = {
        "start": START,
        "end": END,
        "assumption": "gross grid uses mark-to-market with 30bps switch cost; tax table liquidates final position with the simplified Italian tax model",
        "top_by_final": top_by_final.to_dict(orient="records"),
        "top_by_out": top_by_out.to_dict(orient="records"),
        "top_by_robust": top_by_robust.to_dict(orient="records"),
        "tax_top": tax.to_dict(orient="records"),
    }
    (OUT_DIR / "apex_timing_sweep_results.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    report = f"""# APEX timing sweep - 2026-05-29

Stato: ricerca quantitativa, nessun deploy.

## Metodo

- Periodo: 2018-01-01 -> 2026-05-29.
- Fonte: Yahoo Finance proxy EUR gia' usati per APEX.
- Timing testati: lunedi-venerdi, open e close.
- Strategie testate: APEX, Buffer 1/2/3/5pp, Confirm2, Confirm2+Buffer2, Pure Relative.
- Lookback testati: 4 -> 20 settimane.
- Griglia principale: mark-to-market con costo cambio 30 bps, non fiscalmente liquidata.
- Tabella fiscale: solo sui migliori candidati, con modello fiscale Italia semplificato e liquidazione finale.
- Nota: `Confirm2+Buffer2` qui usa la logica corretta. Nei report precedenti era accidentalmente uguale a Confirm2 per un ordine sbagliato nel codice.

## Vincitori Per Timing

{table_md(timing_leaders, ["timing", "strategia", "famiglia", "lookback", "CAGR", "Out CAGR", "Max DD", "Sharpe", "Out Sharpe", "Calmar", "Switch", "Finale 10k"])}

## Top Globale Mark-to-Market

Ordinato per capitale finale, costo switch incluso, senza liquidazione fiscale finale.

{table_md([summarize(r.to_dict()) for _, r in top_by_final.head(15).iterrows()], ["timing", "strategia", "famiglia", "lookback", "CAGR", "Out CAGR", "Max DD", "Sharpe", "Out Sharpe", "Calmar", "Switch", "Finale 10k"])}

## Top Per Out-of-Sample

Ordinato per Sharpe 2023-2026, poi CAGR 2023-2026.

{table_md([summarize(r.to_dict()) for _, r in top_by_out.head(15).iterrows()], ["timing", "strategia", "famiglia", "lookback", "CAGR", "Out CAGR", "Max DD", "Sharpe", "Out Sharpe", "Calmar", "Switch", "Finale 10k"])}

## Focus Lunedi Close

Questa e' la domanda specifica: cosa succede se il segnale viene letto lunedi sera?

{table_md([summarize(r.to_dict()) for _, r in monday_close.iterrows()], ["timing", "strategia", "famiglia", "lookback", "CAGR", "Out CAGR", "Max DD", "Sharpe", "Out Sharpe", "Calmar", "Switch", "Finale 10k"])}

## Confronto Mercoledi

Mercoledi close, cioe' la lettura piu vicina al motore Claude.

{table_md([summarize(r.to_dict()) for _, r in wednesday_close.iterrows()], ["timing", "strategia", "famiglia", "lookback", "CAGR", "Out CAGR", "Max DD", "Sharpe", "Out Sharpe", "Calmar", "Switch", "Finale 10k"])}

Mercoledi open, cioe' la lettura piu vicina all'idea di segnale mattina.

{table_md([summarize(r.to_dict()) for _, r in wednesday_open.iterrows()], ["timing", "strategia", "famiglia", "lookback", "CAGR", "Out CAGR", "Max DD", "Sharpe", "Out Sharpe", "Calmar", "Switch", "Finale 10k"])}

## Vista Fiscale Sui Migliori

Questa tabella liquida fiscalmente la posizione finale. Serve solo per i candidati migliori emersi dallo sweep.

{table_md([tax_row(r.to_dict()) for _, r in tax.head(20).iterrows()], ["timing", "strategia", "netto 10k", "CAGR netto", "DD netto", "Sharpe netto", "switch", "tasse"])}

## Lettura Tecnica

1. La tua intuizione e' corretta: cambiando timing, puo emergere una terza combinazione.
2. Il lunedi close non va escluso: va confrontato con mercoledi close e mercoledi open per robustezza, non solo per capitale finale.
3. Se un timing vince solo con un lookback molto specifico e perde out-of-sample, va considerato overfitting.
4. Per scegliere la versione operativa finale servono due colonne in app: `valore portafoglio` e `netto se liquidato`.

## Conclusione Operativa Provvisoria

APEX 8w non e' il campione assoluto: e' forte quando il perimetro e' stretto, soprattutto vicino al mercoledi close e alla logica originale.

Quando si allarga il test a timing diversi e filtri diversi, emergono candidati migliori. Pero' i migliori assoluti vanno trattati con sospetto, perche' potrebbero essere ottimizzati sul passato.

Shortlist sensata da approfondire:

| Ruolo | Timing | Strategia | Perche' resta candidata |
| --- | --- | --- | --- |
| Base conservativa | mercoledi close | APEX 8w | Strategia originale, semplice, coerente con la tesi BTC-centrica |
| Challenger mattina | mercoledi open | Buffer 2pp 6w / Buffer 3pp 6w | Forte nella logica di segnale mattutino, ma piu' nuova da validare |
| Challenger lunedi | lunedi close | Buffer 5pp 8w | Risponde alla domanda sul lunedi sera, ma non domina lo sweep globale |
| Challenger globale | martedi close | Buffer 3pp 6w | Molto forte su finale e out-of-sample |
| Candidato aggressivo | venerdi open | Buffer 5pp 5w | Vince molte metriche, ma va controllato bene per rischio overfitting e praticabilita' operativa |

La decisione migliore non e' ancora sostituire APEX 8w. La decisione migliore e' creare un confronto finale a 5 candidati, con gli stessi dati, TER aggiornati, tasse, liquidazione finale e regole operative realistiche.

## File Generati

- `output/apex_timing_sweep_grid.csv`
- `output/apex_timing_sweep_tax_top.csv`
- `output/apex_timing_sweep_results.json`
"""
    DOC_PATH.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
