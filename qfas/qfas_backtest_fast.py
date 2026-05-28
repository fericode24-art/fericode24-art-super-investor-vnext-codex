"""
Backtest QFAS 2015-2026 — versione FAST per validare strategia vs SPY.

Differenze dal qfas_backtest.py originale:
  - skip_external_signals=True (no network calls Form4/FMP/Capitol)
  - usa universo R1000 ∩ 13F (459 ticker invece di 1325) — più veloce
  - 12 filing 13F per fondo (3 anni decay-relevant)
  - prezzi cache prices_v25.csv (12 anni completi)
  - decision cycle MENSILE (primo trading day)

Stima tempo: ~20-30 min in background.
Output: output/qfas_backtest_result.json + report .txt
"""
from __future__ import annotations
import json, sys, time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = Path(__file__).parent.parent.absolute()
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(exist_ok=True)

from qfas.qfas_config import config
from qfas.qfas_runner import run_decision_cycle
from qfas.tax_aware_optimizer import cost_per_trade

BACKTEST_START = date(2015, 1, 2)
BACKTEST_END = date(2026, 5, 21)
INITIAL_CAPITAL = 48000.0
NUM_POS = 8
TAX = 0.26


def log(msg):
    print(f"[BT-FAST] {msg}", flush=True)


def load_backtest_data_fast():
    """Carica cache 12 anni + universo R1000 ∩ 13F (~459 ticker)."""
    t0 = time.time()
    log("Carico dati backtest…")

    # 13F
    h13f_path = ROOT / "data" / "backtest" / "hist_13f_l40.json"
    raw_h13f = json.loads(h13f_path.read_text())
    filings_trimmed = {}
    for cik, filings in raw_h13f.items():
        sorted_f = sorted(filings, key=lambda f: f["date"])
        filings_trimmed[cik] = sorted_f[-12:]   # ultimi 12 filing per fondo
    log(f"  13F: {len(filings_trimmed)} fondi × max 12 filing")

    # Russell 1000
    r1000_path = ROOT / "data" / "russell_1000.json"
    r1000 = {c["ticker"] for c in json.loads(r1000_path.read_text())["constituents"]}

    # Universo intersezione
    ticker_count = {}
    for cik, filings in filings_trimmed.items():
        seen = set()
        for f in filings:
            for h in f.get("holdings", []):
                t = h.get("ticker")
                if t and t not in seen:
                    seen.add(t)
                    ticker_count[t] = ticker_count.get(t, 0) + 1
    in_3plus = {t for t, n in ticker_count.items() if n >= 3}
    universe = sorted(in_3plus & r1000)
    log(f"  universe (13F ≥3 ∩ R1000): {len(universe)} ticker")

    # Prezzi 12 anni (file pesante ma una lettura)
    prices_csv = ROOT / "data" / "backtest" / "prices_v25.csv"
    log(f"  caricamento prezzi 12 anni da {prices_csv.name}…")
    prices_df = pd.read_csv(prices_csv, index_col=0, parse_dates=True)
    # Filtro solo colonne universo + benchmark
    cols = [c for c in (["SPY", "QQQ", "^VIX"] + universe) if c in prices_df.columns]
    prices_df = prices_df[cols]
    log(f"  prezzi: {prices_df.shape[0]} giorni × {prices_df.shape[1]} ticker "
        f"({prices_df.index.min().date()} → {prices_df.index.max().date()})")

    # Sectors
    sectors_path = ROOT / "data" / "backtest" / "sectors_full.json"
    sectors = {}
    if sectors_path.exists():
        all_sec = json.loads(sectors_path.read_text())
        sectors = {t: all_sec.get(t, "Unknown") for t in universe}

    vix_series = prices_df["^VIX"] if "^VIX" in prices_df.columns else None
    log(f"  loader totale: {time.time()-t0:.1f}s")
    return {
        "prices_df": prices_df,
        "filings_by_cik": filings_trimmed,
        "sectors": sectors,
        "vix_series": vix_series,
        "universe": universe,
    }


def month_starts(prices_index, start: date, end: date) -> List[date]:
    """Primo trading day di ogni mese."""
    out = []
    cur = date(start.year, start.month, 1)
    while cur <= end:
        future = prices_index[prices_index >= pd.Timestamp(cur)]
        if len(future):
            d = future[0].date()
            if start <= d <= end:
                out.append(d)
        cur = date(cur.year + (1 if cur.month == 12 else 0),
                   1 if cur.month == 12 else cur.month + 1, 1)
    return out


def run_backtest():
    data = load_backtest_data_fast()
    prices_df = data["prices_df"]
    universe = data["universe"]
    sectors = data["sectors"]
    vix_series = data["vix_series"]
    spy = prices_df["SPY"].ffill()

    decision_dates = month_starts(prices_df.index, BACKTEST_START, BACKTEST_END)
    log(f"\nDecision dates: {len(decision_dates)} mesi")

    spy0 = float(spy.loc[pd.Timestamp(decision_dates[0])
                          + pd.Timedelta(days=0):
                          pd.Timestamp(decision_dates[0])
                          + pd.Timedelta(days=10)].iloc[0])

    # Pre-buildo dict prezzi
    log("Pre-build dict prezzi…")
    prices_by_ticker = {t: prices_df[t].dropna() for t in universe}

    # Stato natural-compound
    cash = INITIAL_CAPITAL
    holdings: Dict[str, Dict] = {}
    realized_year = 0.0
    carried_losses = []
    tax_total = 0.0
    rotations = []
    continuous = []
    yearly = []
    current_year = None
    year_start_w = INITIAL_CAPITAL

    def total_wealth(d):
        h = 0.0
        ts = pd.Timestamp(d)
        for t, pos in holdings.items():
            s = prices_by_ticker.get(t)
            if s is None:
                continue
            p = s[s.index <= ts].dropna()
            if not p.empty:
                h += pos["shares"] * float(p.iloc[-1])
        return cash + h

    def get_px(t, d):
        s = prices_by_ticker.get(t)
        if s is None: return None
        p = s[s.index <= pd.Timestamp(d)].dropna()
        return float(p.iloc[-1]) if not p.empty else None

    t_start = time.time()
    log(f"\nInizio simulazione {len(decision_dates)} cicli decisionali…")

    for i, sig_date in enumerate(decision_dates):
        # Cambio anno fiscale
        if current_year is None:
            current_year = sig_date.year
            year_start_w = total_wealth(sig_date)
        elif sig_date.year != current_year:
            carried_losses = [(oy, a) for oy, a in carried_losses
                              if oy + 4 >= current_year]
            tax_y = 0.0
            if realized_year > 0:
                avail = sum(a for _, a in carried_losses)
                used = min(realized_year, avail)
                rem = used
                nc = []
                for oy, a in carried_losses:
                    if rem <= 0: nc.append((oy, a))
                    elif a <= rem: rem -= a
                    else: nc.append((oy, a - rem)); rem = 0
                carried_losses = nc
                tax_y = TAX * (realized_year - used)
            elif realized_year < 0:
                carried_losses.append((current_year, -realized_year))
            cash -= tax_y
            tax_total += tax_y
            ye_w = total_wealth(sig_date)
            yearly.append({
                "year": current_year,
                "wealth_start": round(year_start_w, 2),
                "wealth_end": round(ye_w, 2),
                "realized": round(realized_year, 2),
                "tax": round(tax_y, 2),
                "pct": round((ye_w / year_start_w - 1) * 100, 2) if year_start_w else 0,
            })
            elapsed = time.time() - t_start
            log(f"  {current_year}: wealth €{ye_w:,.0f} ({(ye_w/year_start_w-1)*100:+.1f}%) "
                f"tax €{tax_y:.0f} · elapsed {elapsed:.0f}s")
            realized_year = 0.0
            current_year = sig_date.year
            year_start_w = ye_w

        # VIX
        vix_val = None
        if vix_series is not None:
            v = vix_series[vix_series.index <= pd.Timestamp(sig_date)].dropna()
            if not v.empty: vix_val = float(v.iloc[-1])

        # Current holdings list
        cur_holdings = []
        for t, pos in holdings.items():
            p = get_px(t, sig_date)
            pnl_pct = ((p / pos["entry_price"]) - 1) * 100 if p else 0
            cur_holdings.append({
                "ticker": t, "score": pos.get("score", 50),
                "sector": pos.get("sector", "Unknown"),
                "status": pos.get("status", "NEUTRAL"),
                "days_held": (sig_date - pos["entry_date"]).days,
                "pnl_pct": pnl_pct,
            })

        # Decision cycle FAST
        try:
            dec = run_decision_cycle(
                signal_date=sig_date,
                current_holdings=cur_holdings,
                universe_tickers=universe,
                all_filings_by_fund=data["filings_by_cik"],
                prices_by_ticker=prices_by_ticker,
                sectors_by_ticker=sectors,
                vix_value=vix_val,
                skip_external_signals=True,
            )
        except Exception as e:
            log(f"  ERR {sig_date}: {e}")
            continue

        new_tickers = {s.ticker for s in dec.portfolio}
        new_map = {s.ticker: s for s in dec.portfolio}

        # SELL incumbents fuori
        for t in [t for t in holdings if t not in new_tickers]:
            pos = holdings[t]
            p = get_px(t, sig_date)
            if p is None: continue
            gross = pos["shares"] * p
            c = cost_per_trade(gross, 50_000_000)
            cash += (gross - c)
            realized = (gross - c) - (pos["shares"] * pos["entry_price"])
            realized_year += realized
            rotations.append({"date": sig_date.isoformat(), "action": "SELL",
                              "ticker": t, "shares": pos["shares"], "price": p,
                              "realized": realized})
            del holdings[t]

        # BUY new
        to_buy = [s for s in dec.portfolio if s.ticker not in holdings]
        if to_buy and cash > 100:
            per = cash / len(to_buy)
            for slot in to_buy:
                p = get_px(slot.ticker, sig_date)
                if p is None or per <= 100: continue
                c = cost_per_trade(per, 50_000_000)
                inv = per - c
                sh = inv / p
                if sh <= 0: continue
                holdings[slot.ticker] = {
                    "shares": sh, "entry_date": sig_date, "entry_price": p,
                    "sector": slot.sector, "status": slot.entry_status,
                    "score": slot.score,
                }
                cash -= per
                rotations.append({"date": sig_date.isoformat(), "action": "BUY",
                                  "ticker": slot.ticker, "shares": sh, "price": p})

        # Update score/status for survivors
        for t, pos in holdings.items():
            if t in new_map:
                pos["score"] = new_map[t].score
                pos["status"] = new_map[t].entry_status

        # Snapshot
        w = total_wealth(sig_date)
        sp = INITIAL_CAPITAL * float(spy.loc[pd.Timestamp(sig_date)]) / spy0
        continuous.append({
            "d": sig_date.isoformat(), "s": round(w, 2), "b": round(sp, 2),
            "n_held": len(holdings),
        })

    # Risultato finale
    end_d = decision_dates[-1]
    final_w_open = total_wealth(end_d)
    spy_end = float(spy.loc[pd.Timestamp(end_d)])
    sp_gross = INITIAL_CAPITAL * spy_end / spy0
    sp_tax = TAX * max(0, sp_gross - INITIAL_CAPITAL)
    sp_net = sp_gross - sp_tax

    # Latent gain strategia
    latent = 0
    for t, pos in holdings.items():
        p = get_px(t, end_d)
        if p: latent += pos["shares"] * p - pos["shares"] * pos["entry_price"]
    final_w_closed = final_w_open - TAX * max(0, latent)

    n_years = (end_d - BACKTEST_START).days / 365.25
    cagr_strat = (final_w_closed / INITIAL_CAPITAL) ** (1/n_years) - 1
    cagr_sp = (sp_net / INITIAL_CAPITAL) ** (1/n_years) - 1

    summary = {
        "start": BACKTEST_START.isoformat(),
        "end": end_d.isoformat(),
        "years": round(n_years, 2),
        "initial": INITIAL_CAPITAL,
        "n_positions": NUM_POS,
        "strategy_final_open": round(final_w_open, 2),
        "strategy_final_closed": round(final_w_closed, 2),
        "strategy_latent": round(latent, 2),
        "tax_paid_annual": round(tax_total, 2),
        "tax_if_closed": round(TAX * max(0, latent), 2),
        "sp_gross": round(sp_gross, 2),
        "sp_tax_final": round(sp_tax, 2),
        "sp_net": round(sp_net, 2),
        "cagr_strategy_pct": round(cagr_strat * 100, 2),
        "cagr_sp_pct": round(cagr_sp * 100, 2),
        "alpha_cagr_pp": round((cagr_strat - cagr_sp) * 100, 2),
        "alpha_eur": round(final_w_closed - sp_net, 2),
        "n_rotations": sum(1 for r in rotations if r["action"] == "SELL"),
    }

    log("\n" + "=" * 60)
    log(f"BACKTEST QFAS COMPLETATO in {time.time()-t_start:.0f}s")
    log(f"  Strategia (chiuso oggi): €{final_w_closed:,.0f}")
    log(f"  SPY netto:               €{sp_net:,.0f}")
    log(f"  Alpha € assoluto:        €{summary['alpha_eur']:+,.0f}")
    log(f"  CAGR strategia:          {cagr_strat*100:+.2f}%/anno")
    log(f"  CAGR SPY netto:          {cagr_sp*100:+.2f}%/anno")
    log(f"  Alpha CAGR:              {summary['alpha_cagr_pp']:+.2f}pp/anno")
    log(f"  Rotazioni totali:        {summary['n_rotations']}")

    out = {
        "summary": summary, "yearly": yearly,
        "continuous": continuous, "rotations": rotations[:200],
    }
    out_path = OUT_DIR / "qfas_backtest_result.json"
    out_path.write_text(json.dumps(out, separators=(",", ":"), default=str), encoding="utf-8")
    log(f"\nSalvato {out_path}")
    return out


if __name__ == "__main__":
    run_backtest()
