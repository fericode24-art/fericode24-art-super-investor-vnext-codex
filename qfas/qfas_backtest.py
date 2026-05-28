"""
QFAS v2.5 — qfas_backtest.py

Backtest del motore QFAS in NATURAL COMPOUND dal 2015-01 al 2026-05.

MODELLO REALE DI INVESTIMENTO:
  - €48.000 iniettati UNA SOLA VOLTA il 2 gennaio 2015
  - 8 posizioni equal-weight €6.000 ciascuna iniziale
  - Le rotazioni usano cash interno (vendi A, compri B con i soldi di A)
  - Profitti restano dentro, compoundano nelle posizioni successive
  - Tasse 26% pagate a fine anno SOLO sul realizzato (zainetto 4y)
  - Posizioni aperte a fine anno NON tassate (mark-to-market non tassato in IT)

DECISION FREQUENCY: mensile (primo trading day del mese)

CONFRONTO: SPY buy & hold dal 2015-01, tassa SOLO al riscatto finale 2026-05

NOTA: il backtest gira con i segnali backtestabili (radar 13F + momentum + VIX).
I segnali real-time (analyst, PEAD, short squeeze, insider Form 4) sono
disponibili da date diverse via SIGNAL_AVAILABLE_FROM e contribuiscono peso 0
prima della loro disponibilità (rinormalizzazione automatica).
"""
from __future__ import annotations
import json
import logging
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

from qfas.qfas_config import config, CACHE_DIR
from qfas.fund_universe import FUND_ACTIVE_PERIODS, get_active_funds_at
from qfas.qfas_runner import run_decision_cycle, DecisionCycleResult
from qfas.tax_aware_optimizer import cost_per_trade
from qfas.dividend_tax_drag import calculate_dividend_drag

ROOT = Path(__file__).parent.parent.absolute()
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(exist_ok=True)

log = logging.getLogger("qfas.backtest")
log.setLevel(logging.INFO)
if not log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[QFAS-BT %(levelname)s] %(message)s"))
    log.addHandler(h)


# ═════════════════════════════════════════════════════════════════════════
# COSTANTI BACKTEST
# ═════════════════════════════════════════════════════════════════════════
BACKTEST_START = date(2015, 1, 2)
BACKTEST_END = date(2026, 5, 21)
DEFAULT_ADV = 50_000_000      # ADV usato se non disponibile, mediano mid-cap


# ═════════════════════════════════════════════════════════════════════════
# DATI: carico cache esistenti
# ═════════════════════════════════════════════════════════════════════════

def load_backtest_data() -> Dict:
    """Carica prezzi, 13F filings, settori dalle cache esistenti del progetto."""
    log.info("Carico dati per backtest…")
    # Prezzi
    prices_csv = ROOT / "data" / "backtest" / "prices_v25.csv"
    if not prices_csv.exists():
        raise FileNotFoundError(f"Cache prezzi non trovata: {prices_csv}")
    prices_df = pd.read_csv(prices_csv, index_col=0, parse_dates=True).sort_index()
    log.info(f"  prezzi: {prices_df.shape[0]} giorni × {prices_df.shape[1]} ticker "
             f"({prices_df.index.min().date()} → {prices_df.index.max().date()})")

    # 13F filings (riusa cache esistente)
    h13f_path = ROOT / "data" / "backtest" / "hist_13f_l40.json"
    if not h13f_path.exists():
        raise FileNotFoundError(f"Cache 13F non trovata: {h13f_path}")
    raw_h13f = json.loads(h13f_path.read_text(encoding="utf-8"))
    # struttura: {cik: [{date, holdings: [{ticker, shares, pct}]}, ...]}
    log.info(f"  13F: {len(raw_h13f)} fondi nel pool")

    # Sectors
    sectors_path = ROOT / "data" / "backtest" / "sectors_full.json"
    sectors = {}
    if sectors_path.exists():
        sectors = json.loads(sectors_path.read_text(encoding="utf-8"))
    log.info(f"  settori GICS: {len(sectors)} ticker")

    # SPY per benchmark
    if "SPY" not in prices_df.columns:
        raise RuntimeError("SPY mancante in cache prezzi")

    # VIX
    vix_series = prices_df["^VIX"] if "^VIX" in prices_df.columns else None

    # Universo: tutti i ticker presenti nei 13F (con prezzo)
    all_tickers_in_13f = set()
    for filings in raw_h13f.values():
        for f in filings:
            for h in f.get("holdings", []):
                all_tickers_in_13f.add(h.get("ticker"))
    universe = sorted(t for t in all_tickers_in_13f if t in prices_df.columns)
    log.info(f"  universe investibile: {len(universe)} ticker")

    return {
        "prices_df": prices_df,
        "filings_by_cik": raw_h13f,
        "sectors": sectors,
        "vix_series": vix_series,
        "universe": universe,
    }


# ═════════════════════════════════════════════════════════════════════════
# DATE DI REBALANCE: primo trading day del mese
# ═════════════════════════════════════════════════════════════════════════

def month_start_trading_days(start: date, end: date,
                              trading_index: pd.DatetimeIndex) -> List[date]:
    """Primo trading day di ogni mese tra start e end."""
    out = []
    cur = date(start.year, start.month, 1)
    while cur <= end:
        # Trova primo trading day >= cur
        future = trading_index[trading_index >= pd.Timestamp(cur)]
        if len(future):
            d = future[0].date()
            if d >= start and d <= end:
                out.append(d)
        # Next month
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return out


# ═════════════════════════════════════════════════════════════════════════
# SIMULATORE PORTAFOGLIO (natural compound)
# ═════════════════════════════════════════════════════════════════════════

def run_qfas_backtest(skip_external_signals: bool = True) -> Dict:
    """
    Esegue il backtest QFAS dal 2015 a maggio 2026.

    Args:
        skip_external_signals: se True, segnali Form 4 / 8-K / FMP / FINRA
            non vengono chiamati per velocità. La logica di rinormalizzazione
            li tratta come unavailable (peso 0). Sui dati storici è equivalente
            perché tali API non hanno dati storici 2015 comunque.

    Returns:
        dict con continuous, yearly, summary, rotations
    """
    data = load_backtest_data()
    prices_df = data["prices_df"]
    filings_by_cik = data["filings_by_cik"]
    sectors = data["sectors"]
    vix_series = data["vix_series"]
    universe = data["universe"]

    # Pre-build prices dict ticker→Series per efficienza
    prices_by_ticker: Dict[str, pd.Series] = {
        t: prices_df[t].dropna() for t in universe if t in prices_df.columns
    }
    spy = prices_df["SPY"].ffill()
    spy0 = float(spy.loc[pd.Timestamp(BACKTEST_START):
                          pd.Timestamp(BACKTEST_START) + pd.Timedelta(days=10)].iloc[0])

    # Decision dates
    decision_dates = month_start_trading_days(
        BACKTEST_START, BACKTEST_END, prices_df.index,
    )
    log.info(f"\nDate decisionali: {len(decision_dates)} (mensile)")
    log.info(f"Periodo: {decision_dates[0]} → {decision_dates[-1]}")

    # ── STATO PORTAFOGLIO (natural compound) ──
    cash = config.INITIAL_CAPITAL_EUR
    holdings: Dict[str, Dict] = {}    # ticker → {shares, entry_date, entry_price, sector, status, score}
    realized_pnl_year = 0.0
    carried_losses: List[tuple] = []   # (year, amount)
    tax_paid_total = 0.0
    rotations_log: List[Dict] = []
    continuous: List[Dict] = []
    yearly: List[Dict] = []
    current_year: Optional[int] = None
    year_start_wealth = config.INITIAL_CAPITAL_EUR

    def total_wealth(d: date) -> float:
        h = 0.0
        ts = pd.Timestamp(d)
        for t, pos in holdings.items():
            s = prices_by_ticker.get(t)
            if s is None: continue
            p = s[s.index <= ts].dropna()
            if not p.empty:
                h += pos["shares"] * float(p.iloc[-1])
        return cash + h

    def get_price(t: str, d: date) -> Optional[float]:
        s = prices_by_ticker.get(t)
        if s is None: return None
        p = s[s.index <= pd.Timestamp(d)].dropna()
        return float(p.iloc[-1]) if not p.empty else None

    # === LOOP MENSILE ===
    log.info("\nInizio simulazione…")
    t0 = time.time()
    for i, signal_date in enumerate(decision_dates):
        # Cambio anno fiscale
        if current_year is None:
            current_year = signal_date.year
            year_start_wealth = total_wealth(signal_date)
        elif signal_date.year != current_year:
            # Fine anno fiscale precedente: paga tasse con zainetto
            carried_losses = [(oy, a) for oy, a in carried_losses
                              if oy + config.LOSS_CARRYFORWARD_YEARS >= current_year]
            tax_y = 0.0
            if realized_pnl_year > 0:
                avail = sum(a for _, a in carried_losses)
                used = min(realized_pnl_year, avail)
                rem = used
                nc = []
                for oy, a in carried_losses:
                    if rem <= 0: nc.append((oy, a))
                    elif a <= rem: rem -= a
                    else: nc.append((oy, a - rem)); rem = 0
                carried_losses = nc
                tax_y = config.CAPITAL_GAIN_TAX_RATE * (realized_pnl_year - used)
            elif realized_pnl_year < 0:
                carried_losses.append((current_year, -realized_pnl_year))
            cash -= tax_y
            tax_paid_total += tax_y
            yend_wealth = total_wealth(signal_date)
            yearly.append({
                "year": current_year,
                "wealth_start": round(year_start_wealth, 2),
                "wealth_end": round(yend_wealth, 2),
                "realized_pnl": round(realized_pnl_year, 2),
                "tax_paid": round(tax_y, 2),
                "s_net_pct": round((yend_wealth / year_start_wealth - 1) * 100, 2)
                              if year_start_wealth else 0,
            })
            log.info(f"  {current_year} END: wealth €{yend_wealth:,.0f}  "
                     f"({(yend_wealth/year_start_wealth-1)*100:+.1f}%) "
                     f"realized €{realized_pnl_year:+,.0f} tax €{tax_y:,.0f}")
            realized_pnl_year = 0.0
            current_year = signal_date.year
            year_start_wealth = yend_wealth

        # VIX corrente
        vix_val = None
        if vix_series is not None:
            v = vix_series[vix_series.index <= pd.Timestamp(signal_date)].dropna()
            if not v.empty:
                vix_val = float(v.iloc[-1])

        # Costruisco current_holdings per il runner
        current_holdings_list = []
        for t, pos in holdings.items():
            cur_p = get_price(t, signal_date)
            pnl_pct = ((cur_p / pos["entry_price"]) - 1) * 100 if cur_p else 0
            days_held = (signal_date - pos["entry_date"]).days
            current_holdings_list.append({
                "ticker": t, "score": pos.get("score", 50),
                "sector": pos.get("sector", "Unknown"),
                "status": pos.get("status", "NEUTRAL"),
                "days_held": days_held,
                "pnl_pct": pnl_pct,
            })

        # === DECISION CYCLE ===
        try:
            decision = run_decision_cycle(
                signal_date=signal_date,
                current_holdings=current_holdings_list,
                universe_tickers=universe,
                all_filings_by_fund=filings_by_cik,
                prices_by_ticker=prices_by_ticker,
                sectors_by_ticker=sectors,
                vix_value=vix_val,
            )
        except Exception as e:
            log.error(f"Decision cycle failed at {signal_date}: {e}")
            continue

        new_portfolio_tickers = {s.ticker for s in decision.portfolio}
        new_portfolio_map = {s.ticker: s for s in decision.portfolio}

        # === ESEGUI VENDITE (incumbents not in new portfolio)
        to_sell = [t for t in holdings if t not in new_portfolio_tickers]
        for t in to_sell:
            pos = holdings[t]
            p = get_price(t, signal_date)
            if p is None: continue
            gross = pos["shares"] * p
            # ADV proxy: lo skipperiamo per backtest (usiamo DEFAULT_ADV)
            cost = cost_per_trade(gross, DEFAULT_ADV)
            cash += (gross - cost)
            realized = (gross - cost) - (pos["shares"] * pos["entry_price"])
            realized_pnl_year += realized
            rotations_log.append({
                "date": signal_date.isoformat(),
                "action": "SELL", "ticker": t,
                "shares": round(pos["shares"], 4),
                "price": round(p, 4),
                "value": round(gross, 2),
                "realized_pnl": round(realized, 2),
                "gain_pct": round((p / pos["entry_price"] - 1) * 100, 2),
                "days_held": (signal_date - pos["entry_date"]).days,
            })
            del holdings[t]

        # === ESEGUI ACQUISTI (new tickers not in holdings)
        to_buy = [s for s in decision.portfolio if s.ticker not in holdings]
        if to_buy and cash > 100:
            per_entry = cash / len(to_buy) if to_buy else 0
            for slot in to_buy:
                t = slot.ticker
                p = get_price(t, signal_date)
                if p is None or per_entry <= 100: continue
                cost = cost_per_trade(per_entry, DEFAULT_ADV)
                invested = per_entry - cost
                shares = invested / p
                if shares <= 0: continue
                holdings[t] = {
                    "shares": shares,
                    "entry_date": signal_date,
                    "entry_price": p,
                    "sector": slot.sector,
                    "status": slot.entry_status,
                    "score": slot.score,
                }
                cash -= per_entry
                rotations_log.append({
                    "date": signal_date.isoformat(),
                    "action": "BUY", "ticker": t,
                    "shares": round(shares, 4),
                    "price": round(p, 4),
                    "value": round(per_entry, 2),
                    "sector": slot.sector,
                    "status": slot.entry_status,
                    "reason": slot.reason,
                })

        # Aggiorno status/score per i sopravvissuti dal portfolio decision
        for t, pos in holdings.items():
            if t in new_portfolio_map:
                pos["score"] = new_portfolio_map[t].score
                pos["status"] = new_portfolio_map[t].entry_status

        # SNAPSHOT giornaliero (in realtà mensile in questo loop)
        w = total_wealth(signal_date)
        sp = config.INITIAL_CAPITAL_EUR * float(spy.loc[pd.Timestamp(signal_date)]) / spy0
        continuous.append({
            "d": signal_date.isoformat(),
            "s": round(w, 2),
            "b": round(sp, 2),
            "n_held": len(holdings),
            "vix": round(vix_val, 2) if vix_val else None,
        })

        # Progress log every 12 months
        if i % 12 == 0:
            elapsed = time.time() - t0
            log.info(f"  [{i+1}/{len(decision_dates)}] {signal_date}: "
                     f"wealth €{w:,.0f} · holdings {len(holdings)} "
                     f"· elapsed {elapsed:.0f}s")

    # FINE simulazione: calcola summary
    end_day = decision_dates[-1]
    final_strat_open = total_wealth(end_day)
    spy_end = float(spy.loc[pd.Timestamp(end_day)])
    sp_gross_final = config.INITIAL_CAPITAL_EUR * spy_end / spy0
    sp_tax_final = config.CAPITAL_GAIN_TAX_RATE * max(0.0, sp_gross_final - config.INITIAL_CAPITAL_EUR)
    sp_net_final = sp_gross_final - sp_tax_final

    # Latent gain strategia (se chiudessi tutto oggi)
    latent_pnl = 0.0
    for t, pos in holdings.items():
        p = get_price(t, end_day)
        if p is not None:
            latent_pnl += pos["shares"] * p - pos["shares"] * pos["entry_price"]
    strat_if_closed = final_strat_open - config.CAPITAL_GAIN_TAX_RATE * max(0.0, latent_pnl)

    n_years = (end_day - BACKTEST_START).days / 365.25
    cagr_strat_closed = (strat_if_closed / config.INITIAL_CAPITAL_EUR) ** (1/n_years) - 1
    cagr_sp_net = (sp_net_final / config.INITIAL_CAPITAL_EUR) ** (1/n_years) - 1

    # Dividend drag (per onestà nel confronto)
    div_drag_strat, _ = calculate_dividend_drag(0.015, assume_recovery=config.ASSUME_FOREIGN_TAX_CREDIT_RECOVERY)
    div_drag_sp, _ = calculate_dividend_drag(0.013, assume_recovery=config.ASSUME_FOREIGN_TAX_CREDIT_RECOVERY)
    cagr_strat_net = cagr_strat_closed - div_drag_strat
    cagr_sp_truly_net = cagr_sp_net - div_drag_sp

    summary = {
        "start": BACKTEST_START.isoformat(),
        "end": end_day.isoformat(),
        "n_years": round(n_years, 2),
        "initial_capital_eur": config.INITIAL_CAPITAL_EUR,
        "num_positions": config.NUM_POSITIONS,
        # Strategia
        "strategy_final_open": round(final_strat_open, 2),
        "strategy_latent_pnl": round(latent_pnl, 2),
        "strategy_final_closed_today": round(strat_if_closed, 2),
        "strategy_tax_paid_annual": round(tax_paid_total, 2),
        "strategy_tax_if_closed_now": round(config.CAPITAL_GAIN_TAX_RATE * max(0, latent_pnl), 2),
        "cagr_strategy_closed_today": round(cagr_strat_closed * 100, 2),
        "cagr_strategy_net_dividends": round(cagr_strat_net * 100, 2),
        # SPY
        "sp_gross_final": round(sp_gross_final, 2),
        "sp_tax_final": round(sp_tax_final, 2),
        "sp_net_final": round(sp_net_final, 2),
        "cagr_sp_net": round(cagr_sp_net * 100, 2),
        "cagr_sp_truly_net": round(cagr_sp_truly_net * 100, 2),
        # Alpha
        "alpha_eur_closed": round(strat_if_closed - sp_net_final, 2),
        "alpha_pct_closed": round((strat_if_closed / sp_net_final - 1) * 100, 2),
        "alpha_cagr_pp": round((cagr_strat_closed - cagr_sp_net) * 100, 2),
        "alpha_cagr_truly_net_pp": round((cagr_strat_net - cagr_sp_truly_net) * 100, 2),
        # Ops
        "n_rotations": sum(1 for r in rotations_log if r["action"] == "SELL"),
        "dividend_drag_scenario_A": config.ASSUME_FOREIGN_TAX_CREDIT_RECOVERY,
    }

    return {
        "continuous": continuous,
        "yearly": yearly,
        "summary": summary,
        "rotations": rotations_log,
    }


# ═════════════════════════════════════════════════════════════════════════
# REPORT
# ═════════════════════════════════════════════════════════════════════════

def write_report(out: Dict) -> str:
    s = out["summary"]
    L = []
    L.append("=" * 84)
    L.append(" QFAS v2.5 BACKTEST · NATURAL COMPOUND · 2015 → maggio 2026")
    L.append("=" * 84)
    L.append("")
    L.append(f" Periodo: {s['start']} → {s['end']} ({s['n_years']} anni)")
    L.append(f" Capitale: €{s['initial_capital_eur']:,.0f} · {s['num_positions']} posizioni equal-weight")
    L.append(f" Modello: natural compound (single injection, no aggiunte)")
    L.append(f" Costi: €{config.COMMISSION_PER_ORDER_EUR}/ordine + spread calibrato mid-cap")
    L.append(f" Tasse: {config.CAPITAL_GAIN_TAX_RATE*100:.0f}% IT + zainetto 4y")
    L.append(f" Dividend drag scenario A (recovery): {s['dividend_drag_scenario_A']}")
    L.append("")
    L.append("─" * 84)
    L.append(" ANNO PER ANNO")
    L.append("─" * 84)
    L.append(f" {'Anno':>5}  {'Wealth Start':>14}  {'Wealth End':>13}  {'Strat %':>9}  "
             f"{'Realized':>11}  {'Tax':>8}")
    for y in out["yearly"]:
        L.append(f" {y['year']:>5}  €{y['wealth_start']:>12,.0f}   €{y['wealth_end']:>11,.0f}   "
                 f"{y['s_net_pct']:+8.1f}%  €{y['realized_pnl']:+9,.0f}  €{y['tax_paid']:>6,.0f}")
    L.append("")
    L.append("─" * 84)
    L.append(" RISULTATO FINALE")
    L.append("─" * 84)
    L.append("")
    L.append(f" STRATEGIA (natural compound):")
    L.append(f"   Valore mark-to-market:                €{s['strategy_final_open']:>11,.0f}")
    L.append(f"   Plus latenti (non realizzate):        €{s['strategy_latent_pnl']:>11,.0f}")
    L.append(f"   Se chiudessi tutto OGGI:              €{s['strategy_final_closed_today']:>11,.0f}")
    L.append(f"   Tasse cumulate (annuali):             €{s['strategy_tax_paid_annual']:>11,.0f}")
    L.append(f"   Tasse aggiuntive se chiudo:           €{s['strategy_tax_if_closed_now']:>11,.0f}")
    L.append(f"   CAGR chiuso oggi:                      {s['cagr_strategy_closed_today']:>+10,.2f}%/anno")
    L.append(f"   CAGR netto dividend drag:              {s['cagr_strategy_net_dividends']:>+10,.2f}%/anno")
    L.append("")
    L.append(f" SP500 (buy & hold):")
    L.append(f"   Valore lordo:                         €{s['sp_gross_final']:>11,.0f}")
    L.append(f"   Tassa al riscatto:                    €{s['sp_tax_final']:>11,.0f}")
    L.append(f"   Valore NETTO al riscatto:             €{s['sp_net_final']:>11,.0f}")
    L.append(f"   CAGR netto cap gain:                   {s['cagr_sp_net']:>+10,.2f}%/anno")
    L.append(f"   CAGR netto + dividend drag:            {s['cagr_sp_truly_net']:>+10,.2f}%/anno")
    L.append("")
    L.append("=" * 84)
    L.append(" ALPHA STRATEGIA vs SP500")
    L.append("─" * 84)
    L.append(f"   Differenza € (chiuso oggi):            €{s['alpha_eur_closed']:>+11,.0f}")
    L.append(f"   Differenza % sul SP500 netto:           {s['alpha_pct_closed']:>+10,.1f}%")
    L.append(f"   Alpha CAGR:                             {s['alpha_cagr_pp']:>+10,.2f}pp/anno")
    L.append(f"   Alpha CAGR (netto dividend drag):       {s['alpha_cagr_truly_net_pp']:>+10,.2f}pp/anno")
    L.append("")
    L.append(f"   Rotazioni totali:                      {s['n_rotations']}")
    L.append(f"   Rotazioni/anno medie:                  {s['n_rotations']/s['n_years']:.0f}")
    L.append("=" * 84)
    L.append("")
    L.append(" SEGNALI USATI NEL BACKTEST:")
    L.append("   ✓ Radar 13F (decay esponenziale + crowding PIT, dal 2010)")
    L.append("   ✓ Momentum cross-sectional (3m+6m, dal 2010)")
    L.append("   ✓ VIX regime margin dinamico")
    L.append("   ✓ TLH proattivo Nov-Dic (italiano, no wash sale US)")
    L.append("   ✓ Sector cap condizionato (top 3 settori per momentum)")
    L.append("   ⊘ Analyst composite (disponibile da 2021 via FMP, peso 0 prima)")
    L.append("   ⊘ PEAD surprise (disponibile da 2021)")
    L.append("   ⊘ Short squeeze conditional (disponibile da 2024)")
    L.append("   ⊘ Form 4 insider (richiede pipeline download massivo, skip in backtest)")
    L.append("   ⊘ Congressional trades (skip in backtest)")
    L.append("")
    L.append(" CAVEAT:")
    L.append("   - Survivorship bias fondi (i 36 sono quelli vivi nel 2026)")
    L.append("   - Survivorship bias ticker (universo derivato dai 13F attuali)")
    L.append("   - Dividend drag stimato a posteriori (yield medio 1.5%)")
    L.append("   - Costi Fineco €5 + spread scalato calibrato mid-cap")
    L.append("=" * 84)
    return "\n".join(L)


# ═════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    log.info("Avvio QFAS v2.5 backtest…")
    result = run_qfas_backtest(skip_external_signals=True)

    rep = write_report(result)
    print(rep)

    # Salva output
    (OUT_DIR / "qfas_backtest_report.txt").write_text(rep, encoding="utf-8")
    (OUT_DIR / "qfas_backtest.json").write_text(
        json.dumps({k: v for k, v in result.items() if k != "rotations"},
                   separators=(",", ":"), default=str),
        encoding="utf-8",
    )
    (OUT_DIR / "qfas_rotations.json").write_text(
        json.dumps(result["rotations"], indent=2), encoding="utf-8",
    )
    log.info("Output salvato in output/qfas_backtest_*.{txt,json}")
