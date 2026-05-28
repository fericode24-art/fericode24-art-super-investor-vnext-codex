"""
QFAS v2.5 — qfas_export_octa.py

Genera dashboard/data-octa.json a partire dal decision cycle corrente del
motore QFAS. Output consumato dalla sezione OCTA dell'app.

Schema output:
{
  "updated": "2026-05-24T18:30:00",
  "regime": {"status": "NORMAL", "vix": 14.2, "sub_margin": 12},
  "tlh_active": false,
  "engine_error": false,
  "signals": [
    {
      "id": "sell_NVDA_20260524",
      "ticker": "NVDA",
      "action": "SELL",
      "entry_status": "BROKEN",
      "score": 42,
      "reason": "Status BROKEN (sotto SMA200, 3gg consecutivi)",
      "current_price": 428.50,
      "replacement_id": "buy_AVGO_20260524"
    },
    {
      "id": "buy_AVGO_20260524",
      "ticker": "AVGO",
      "action": "BUY",
      "entry_status": "FRESH_BREAKOUT",
      "score": 78,
      "delta_vs_incumbent": 36,
      "n_funds_holding": 9,
      "sector": "Technology",
      "value_target": 6000,
      "current_price": 429.30,
      "reason": "Score 78 > NVDA 42 + margin 12. Detenuto da 9 fondi pool."
    }
  ],
  "candidates": [...top 40 con score/status/sector...],
  "live_prices": {"AAPL": 195.40, "NVDA": 428.50, ...}
}
"""
from __future__ import annotations
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = Path(__file__).parent.parent.absolute()
DASH_DIR = ROOT / "dashboard"


def export_bootstrap_minimal():
    """
    Bootstrap minimo: genera un data-octa.json placeholder pre-deploy.
    Quando il runner reale (qfas_runner) sarà schedulato giornalmente,
    questo file verrà sovrascritto con segnali veri.
    """
    out = {
        "updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "version": "2.5.0-bootstrap",
        "regime": {
            "status": "NORMAL",
            "vix": None,
            "sub_margin": 12,
        },
        "tlh_active": False,
        "engine_error": False,
        "last_success_run": None,
        "signals": [],
        "candidates": [],
        "live_prices": {},
        "_message": (
            "Bootstrap iniziale OCTA. Il motore QFAS v2.5 è installato in qfas/. "
            "Il runner di scoring giornaliero produrrà segnali veri quando "
            "schedulato. Per ora la sezione mostra l'empty state (nessun segnale)."
        ),
    }
    out_path = DASH_DIR / "data-octa.json"
    out_path.write_text(json.dumps(out, separators=(",", ":"), default=str),
                        encoding="utf-8")
    print(f"[OCTA] bootstrap salvato in {out_path}")
    return out


def load_decision_data(signal_date: date,
                        prices_months: int = 15,
                        n_recent_filings: int = 12):
    """
    Loader DEDICATO al decision cycle live (non backtest).
    Carica solo il minimo strettamente necessario:
      - prezzi: ultimi `prices_months` mesi (default 15)
      - 13F: ultimi `n_recent_filings` per fondo (default 12 = 3 anni)
      - universo: intersezione 13F (≥3 fondi) ∩ Russell 1000
      - sectors: snapshot corrente per universo filtrato

    Stima tempo: 5-15 secondi (vs 60+ per load_backtest_data).
    """
    import json
    import time as _t
    t0 = _t.time()
    ROOT_LOCAL = Path(__file__).parent.parent.absolute()
    print(f"[OCTA-FAST] load_decision_data per {signal_date}…")

    # 1. Universo investibile: intersezione 13F + Russell 1000
    r1000 = set()
    r1000_path = ROOT_LOCAL / "data" / "russell_1000.json"
    if r1000_path.exists():
        r1000 = {c["ticker"] for c in
                 json.loads(r1000_path.read_text(encoding="utf-8"))["constituents"]}
    print(f"[OCTA-FAST]   Russell 1000: {len(r1000)} ticker")

    # 13F cache
    h13f_path = ROOT_LOCAL / "data" / "backtest" / "hist_13f_l40.json"
    raw_h13f = json.loads(h13f_path.read_text(encoding="utf-8"))
    print(f"[OCTA-FAST]   13F: {len(raw_h13f)} fondi")

    # Tronco a ultimi N filing per fondo (decay-relevant)
    filings_trimmed = {}
    for cik, filings in raw_h13f.items():
        sorted_f = sorted(filings, key=lambda f: f["date"])
        filings_trimmed[cik] = sorted_f[-n_recent_filings:]
    total_filings = sum(len(f) for f in filings_trimmed.values())
    print(f"[OCTA-FAST]   13F troncati a ultimi {n_recent_filings}: {total_filings} filing totali")

    # Ticker dei 13F (≥3 fondi)
    ticker_fund_count = {}
    for cik, filings in filings_trimmed.items():
        seen_in_fund = set()
        for f in filings:
            for h in f.get("holdings", []):
                t = h.get("ticker")
                if t and t not in seen_in_fund:
                    seen_in_fund.add(t)
                    ticker_fund_count[t] = ticker_fund_count.get(t, 0) + 1
    tickers_3plus = {t for t, n in ticker_fund_count.items() if n >= 3}
    print(f"[OCTA-FAST]   ticker in ≥3 fondi: {len(tickers_3plus)}")

    # Intersezione finale
    universe = sorted(tickers_3plus & r1000) if r1000 else sorted(tickers_3plus)
    print(f"[OCTA-FAST]   universo finale (∩ R1000): {len(universe)} ticker")

    # 2. Carica solo le colonne necessarie dal CSV
    # Preferisco prices_octa.csv (cache piccola dedicata) se esiste,
    # fallback su prices_v25.csv (cache backtest 12 anni)
    prices_octa = ROOT_LOCAL / "data" / "backtest" / "prices_octa.csv"
    prices_v25  = ROOT_LOCAL / "data" / "backtest" / "prices_v25.csv"
    if prices_octa.exists():
        prices_csv = prices_octa
    elif prices_v25.exists():
        prices_csv = prices_v25
    else:
        raise FileNotFoundError(
            "Nessuna cache prezzi trovata. Esegui prima "
            "`python -m qfas.qfas_download_prices` per popolare prices_octa.csv"
        )
    cutoff_date = pd.Timestamp(signal_date) - pd.Timedelta(days=prices_months * 31)
    # Carico tutto (small file ~2.7MB) e poi filtro colonne in-memory
    # (più robusto rispetto a usecols che dipende dal nome dell'index column)
    prices_df = pd.read_csv(prices_csv, index_col=0, parse_dates=True)
    cols_needed = [c for c in (["SPY", "QQQ", "^VIX"] + universe) if c in prices_df.columns]
    prices_df = prices_df[cols_needed]
    # Filtra periodo
    prices_df = prices_df.loc[cutoff_date:].sort_index()
    print(f"[OCTA-FAST]   prezzi: {prices_df.shape[0]} giorni × {prices_df.shape[1]} ticker "
          f"(da {prices_df.index.min().date()})")

    # 3. Sectors (snapshot)
    sectors = {}
    sectors_path = ROOT_LOCAL / "data" / "backtest" / "sectors_full.json"
    if sectors_path.exists():
        all_sectors = json.loads(sectors_path.read_text(encoding="utf-8"))
        sectors = {t: all_sectors.get(t, "Unknown") for t in universe}

    # VIX serie
    vix_series = prices_df["^VIX"] if "^VIX" in prices_df.columns else None

    elapsed = _t.time() - t0
    print(f"[OCTA-FAST]   loader completo in {elapsed:.1f}s")
    return {
        "prices_df": prices_df,
        "filings_by_cik": filings_trimmed,
        "sectors": sectors,
        "vix_series": vix_series,
        "universe": [t for t in universe if t in prices_df.columns],
    }


def fetch_portfolio_from_cloud():
    """
    Fetch portfolio corrente dell'utente da Netlify Blobs.
    Returns dict {ticker: {shares, entry_date, entry_price, ...}} oppure {} se vuoto/errore.
    """
    import urllib.request
    import os
    base = os.environ.get("DASHBOARD_URL") or "http://localhost:5177"
    url = f"{base.rstrip('/')}/.netlify/functions/octa-portfolio"
    # Stato attuale: il default live usa external_mode="cached"; il blocco
    # storico sopra descriveva il bug precedente, ora superato dal confronto
    # off-vs-cached salvato in output/external_profile_compare.json.
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode("utf-8")
        data = json.loads(raw)
        portfolio = data.get("portfolio", {}) or {}
        history = data.get("history", []) or []
        print(f"[OCTA-SYNC] fetched cloud portfolio: {len(portfolio)} posizioni, "
              f"{len(history)} ops")
        return portfolio, history
    except Exception as e:
        print(f"[OCTA-SYNC] fetch fallito: {e} — uso portfolio vuoto")
        return {}, []


def export_from_decision_cycle(signal_date: Optional[date] = None):
    """
    Genera data-octa.json con decision cycle live (fast path, no backtest).
    Universo: intersezione 13F (≥3 fondi) ∩ Russell 1000.
    Prezzi: 15 mesi. 13F: 12 filing per fondo (3 anni).

    PATCH ROTAZIONI POST-DAY-1: fetch portfolio reale utente da Netlify Blobs,
    passa current_holdings al runner per generare SELL/SWAP coerenti.
    """
    from qfas.qfas_runner import run_decision_cycle

    if signal_date is None:
        signal_date = date.today()
    external_mode = os.environ.get("OCTA_EXTERNAL_SIGNAL_MODE", "cached").strip().lower()
    if external_mode not in {"off", "cached", "full"}:
        raise ValueError(f"OCTA_EXTERNAL_SIGNAL_MODE non valido: {external_mode}")
    print(f"[OCTA] external_signal_mode={external_mode}")

    # 1. Fetch portfolio dal cloud (cosa l'utente ha realmente in PF)
    user_portfolio, user_history = fetch_portfolio_from_cloud()

    data = load_decision_data(signal_date)
    prices_df = data["prices_df"]
    universe = data["universe"]
    sectors = data["sectors"]
    vix_series = data["vix_series"]

    prices_by_ticker = {t: prices_df[t].dropna() for t in universe
                        if t in prices_df.columns}
    vix_val = None
    if vix_series is not None and len(vix_series):
        v = vix_series[vix_series.index <= pd.Timestamp(signal_date)].dropna()
        if not v.empty:
            vix_val = float(v.iloc[-1])

    # FIX BUG #R: warning se portfolio finale < 8 slot (universe troppo piccolo)
    # — segnale di degradazione, non crash. Workflow continua, ma viene loggato.

    # 2. Costruisco current_holdings list dal portfolio cloud
    current_holdings_list = []
    for ticker, pos in user_portfolio.items():
        # Calcolo P&L corrente
        cur_p = None
        if ticker in prices_by_ticker:
            s = prices_by_ticker[ticker]
            sub = s[s.index <= pd.Timestamp(signal_date)].dropna()
            if not sub.empty:
                cur_p = float(sub.iloc[-1])
        entry_price = pos.get("entry_price", 0)
        pnl_pct = ((cur_p / entry_price) - 1) * 100 if cur_p and entry_price else 0
        try:
            entry_date = datetime.fromisoformat(pos.get("entry_date", "").replace("Z", "+00:00")).date()
        except Exception:
            entry_date = signal_date
        days_held = (signal_date - entry_date).days
        current_holdings_list.append({
            "ticker": ticker,
            "score": 50,   # placeholder, ricalcolato dopo
            "sector": pos.get("sector", sectors.get(ticker, "Unknown")),
            "status": "NEUTRAL",
            "days_held": max(0, days_held),
            "pnl_pct": pnl_pct,
        })
    print(f"[OCTA-SYNC] decision cycle con {len(current_holdings_list)} posizioni utente")

    # ⚠ DOCUMENTAZIONE BUG #β (round 3, TODO v2.6):
    # skip_external_signals=True attualmente skippa TUTTI i segnali non-radar:
    # analyst (Finnhub, no cache), insider (HA cache prefetch), congressional
    # (scraping), squeeze (FINRA), PEAD (HA cache prefetch).
    # Risultato: il prefetch notturno insider+earnings produce dati MAI
    # consumati dal decision cycle live. Sistema attualmente gira con solo
    # momentum + radar 13F + crowding + accumulation.
    # Fix v2.6: introdurre flag granulare `use_cached_signals_only` che attiva
    # SOLO insider+PEAD (entrambi cached) e tiene skipati analyst/cong/squeeze.
    # Per ora il fast path è scelta conscia: backtest validato con +38% CAGR
    # è stato fatto con questo profilo segnali, e l'attivazione completa
    # richiede ri-backtest + tuning pesi.
    try:
        decision = run_decision_cycle(
            signal_date=signal_date,
            current_holdings=current_holdings_list,   # FIX BUG #1: portfolio reale utente
            universe_tickers=universe,
            all_filings_by_fund=data["filings_by_cik"],
            prices_by_ticker=prices_by_ticker,
            sectors_by_ticker=sectors,
            vix_value=vix_val,
            skip_external_signals=(external_mode == "off"),
            external_signal_mode=external_mode,
        )
        engine_error = False
        err_msg = None
    except Exception as e:
        # FIX BUG #A (round 2): NON sovrascrivere il data-octa.json valido
        # di ieri con un placeholder vuoto. Solleva l'errore così il workflow
        # fallisce visibilmente e l'app continua a leggere l'ultimo file valido.
        print(f"[OCTA] CRASH decision cycle: {e}", file=sys.stderr)
        import traceback; traceback.print_exc()
        raise SystemExit(2)

    # Trasforma in segnali per UI: SOLO i delta rispetto al portfolio attuale.
    # FIX BUG #1+#2: genera SELL per i ticker che escono, BUY solo per i nuovi.
    # Su Day 1 (portfolio utente vuoto): 8 BUY new.
    # Su Day N steady (nessuna rotazione): 0 segnali (silenzio = niente notifica).
    # Su Day N rotazione: 1 SELL + 1 BUY (notifica accurata).
    def _last_price(ticker):
        s = prices_by_ticker.get(ticker)
        if s is None or not len(s): return None
        v = s[s.index <= pd.Timestamp(signal_date)].dropna()
        return float(v.iloc[-1]) if not v.empty else None

    current_tickers = set(user_portfolio.keys())
    target_tickers = {slot.ticker for slot in decision.portfolio}
    dstr = signal_date.strftime('%Y%m%d')
    signals = []

    # Lookup company name + ISIN da SEC company_tickers_exchange.json
    # (cached). ISIN US = "US" + CUSIP padded 9 chars + check digit.
    name_isin_map = _load_company_meta()
    from qfas.fund_universe import get_fund_by_cik

    def _fund_holders(ticker):
        holders = []
        ticker = ticker.upper()
        for cik, filings in data["filings_by_cik"].items():
            latest = None
            for filing in sorted(filings, key=lambda f: f.get("date", ""), reverse=True):
                if filing.get("date", "") <= signal_date.isoformat():
                    latest = filing
                    break
            if not latest:
                continue
            for h in latest.get("holdings", []):
                if str(h.get("ticker", "")).upper() != ticker:
                    continue
                fund = get_fund_by_cik(cik)
                holders.append({
                    "name": fund.fund_name if fund else cik,
                    "cik": cik,
                    "pct": round(float(h.get("pct") or 0), 2),
                    "shares": h.get("shares"),
                })
                break
        holders.sort(key=lambda h: h.get("pct") or 0, reverse=True)
        return holders

    def _score_notes(candidate, holders):
        comp = candidate.audit if candidate else {}
        n_funds = len(holders)
        signal_bits = [f"{n_funds} fondi"]
        accumulation = comp.get("accumulation")
        conviction = comp.get("conviction")
        if accumulation is not None:
            label = "accumulation forte" if float(accumulation) >= 60 else "accumulation"
            signal_bits.append(f"{label} ({round(float(accumulation))}/100)")
        if conviction is not None:
            signal_bits.append(f"conviction {round(float(conviction))}/100")

        risks = []
        if candidate:
            status = candidate.entry_status
            momentum = candidate.momentum_pct
            if status in {"BROKEN", "AVOID"}:
                risks.append("Veto tecnico del motore")
            elif status == "EXTENDED":
                risks.append("Prezzo gia' esteso rispetto al trend")
            elif momentum is not None and momentum >= 90:
                risks.append("Momentum molto alto: evitare inseguimento senza conferma")
            elif momentum is not None and momentum <= 30:
                risks.append("Momentum debole rispetto al paniere")
        crowding = comp.get("crowding")
        if crowding is not None and float(crowding) < 95:
            risks.append("Crowding fondi: score ridotto dal motore")
        mode = comp.get("external_signal_mode") or external_mode
        if mode == "cached":
            external_state = "Segnali esterni cached pesati nello score: insider, analyst e PEAD dove disponibili"
        elif mode == "full":
            external_state = "Segnali esterni full pesati nello score quando disponibili"
        else:
            external_state = "Profilo fast path: segnali esterni in test, non ancora pesati"

        return {
            "main_signal": " · ".join(signal_bits),
            "main_risk": "; ".join(risks) if risks else "Nessun rischio entry rilevante",
            "exit_trigger": "Esce dal target OCTA o rompe il trend tecnico al ciclo successivo",
            "external_signal_state": external_state,
        }

    # Lookup dettagli candidate per arricchimento UI (radar/entry/momentum/etc)
    cands_by_ticker = {c.ticker: c for c in (decision.all_candidates or [])}
    def _enrich(ticker):
        c = cands_by_ticker.get(ticker)
        meta = name_isin_map.get(ticker.upper(), {})
        holders = _fund_holders(ticker)
        base = {
            "name": meta.get("name", ticker),
            "isin": meta.get("isin"),
            "n_funds_holding": len(holders),
            "top_funds": [h["name"] for h in holders[:10]],
            "top_fund_details": holders[:10],
        }
        base.update(_score_notes(c, holders))
        if not c: return base
        base.update({
            "radar_score": round(c.radar_score, 1),
            "entry_score": round(c.entry_score, 1),
            "opportunity_score": round(c.opportunity_score, 1),
            "momentum_pct": round(c.momentum_pct, 1) if c.momentum_pct is not None else None,
            "sector": c.sector,
            "external_signal_mode": c.audit.get("external_signal_mode"),
            "external_delta": round(float(c.audit.get("external_delta") or 0.0), 1),
            "components": c.audit,
        })
        return base

    # SELL: in portfolio attuale ma non più in target
    for ticker in sorted(current_tickers - target_tickers):
        pos = user_portfolio.get(ticker, {})
        cur_p = _last_price(ticker)
        entry_p = pos.get("entry_price", 0)
        pnl_pct = ((cur_p / entry_p) - 1) * 100 if cur_p and entry_p else None
        sig = {
            "id": f"sell_{ticker}_{dstr}",
            "ticker": ticker,
            "action": "SELL",
            "entry_status": "ROTATION_OUT",
            "score": 0,
            "sector": pos.get("sector", sectors.get(ticker, "Unknown")),
            "current_price": cur_p,
            "pnl_pct": round(pnl_pct, 1) if pnl_pct is not None else None,
            "reason": "Sostituito da candidato con score migliore",
        }
        sig.update(_enrich(ticker))
        signals.append(sig)

    # BUY: in target ma non già in portfolio (gli HOLD non generano segnale)
    for slot in decision.portfolio:
        if slot.ticker in current_tickers:
            continue  # HOLD silenzioso
        is_day1 = len(current_tickers) == 0
        sig = {
            "id": f"buy_{slot.ticker}_{dstr}",
            "ticker": slot.ticker,
            "action": "BUY",
            "entry_status": slot.entry_status,
            "score": round(slot.score, 1),
            "sector": slot.sector,
            "value_target": 6000,
            "current_price": _last_price(slot.ticker),
            "reason": (f"Day 1 — {slot.reason}" if is_day1
                       else f"Nuovo ingresso (sostituisce rotazione) — {slot.reason}"),
        }
        sig.update(_enrich(slot.ticker))
        signals.append(sig)
    print(f"[OCTA] signals generati: {sum(1 for s in signals if s['action']=='BUY')} BUY, "
          f"{sum(1 for s in signals if s['action']=='SELL')} SELL")

    # FIX BUG #R: alert se portfolio target < 8 slot
    if len(decision.portfolio) < 8:
        print(f"[OCTA] ⚠ WARNING: portfolio target ha solo {len(decision.portfolio)}/8 slot. "
              f"Universe valido potrebbe essere troppo piccolo. "
              f"n_candidates={decision.n_candidates}, n_active_funds={decision.n_active_funds}",
              file=sys.stderr)

    # Top 40 candidates per Radar 40 view — usa all_candidates (sorted by opp score)
    candidates = []
    source = decision.all_candidates if decision.all_candidates else decision.top10_candidates
    for c in source[:40]:
        extra = _enrich(c.ticker)
        candidates.append({
            "ticker": c.ticker,
            "name": extra.get("name") or c.ticker,
            "isin": extra.get("isin"),
            "score": round(c.opportunity_score, 1),
            "radar_score": round(c.radar_score, 1),
            "entry_score": round(c.entry_score, 1),
            "momentum_pct": round(c.momentum_pct, 1) if c.momentum_pct is not None else None,
            "entry_status": c.entry_status,
            "sector": c.sector,
            "n_funds_holding": extra.get("n_funds_holding"),
            "top_funds": extra.get("top_funds", []),
            "top_fund_details": extra.get("top_fund_details", []),
            "main_signal": extra.get("main_signal"),
            "main_risk": extra.get("main_risk"),
            "exit_trigger": extra.get("exit_trigger"),
            "external_signal_state": extra.get("external_signal_state"),
            "external_signal_mode": c.audit.get("external_signal_mode"),
            "external_delta": round(float(c.audit.get("external_delta") or 0.0), 1),
            "components": c.audit,
        })

    # Live prices: snapshot ultimi prezzi per i ticker in segnali
    live_prices = {}
    for s in signals:
        if s.get("current_price"):
            live_prices[s["ticker"]] = s["current_price"]

    # Regime — soglie esposte nel JSON per evitare duplicazione in JS (FIX BUG #ζ)
    VIX_RELAXED_BELOW = 15.0
    VIX_STRESSED_ABOVE = 25.0
    regime_status = "NORMAL"
    if vix_val is not None:
        if vix_val < VIX_RELAXED_BELOW: regime_status = "RELAXED"
        elif vix_val > VIX_STRESSED_ABOVE: regime_status = "STRESSED"

    out = {
        "updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "version": "2.6.0-cached",
        "signal_date": signal_date.isoformat(),
        "regime": {
            "status": regime_status,
            "vix": round(vix_val, 1) if vix_val else None,
            "sub_margin": decision.sub_margin_used,
            # FIX BUG #ζ: soglie esposte → JS le legge invece di duplicarle
            "vix_relaxed_below": VIX_RELAXED_BELOW,
            "vix_stressed_above": VIX_STRESSED_ABOVE,
        },
        "tlh_active": _is_in_tlh_window(signal_date),
        "engine_error": engine_error,
        "last_success_run": signal_date.isoformat(),
        "external_signal_mode": external_mode,
        "external_signal_status": "active" if external_mode != "off" else "testing",
        "weights_active": decision.weights_active,
        "n_active_funds": decision.n_active_funds,
        "n_candidates": decision.n_candidates,
        "signals": signals,
        "candidates": candidates,
        "live_prices": live_prices,
    }
    out_path = DASH_DIR / "data-octa.json"
    out_path.write_text(json.dumps(out, separators=(",", ":"), default=str),
                        encoding="utf-8")
    print(f"[OCTA] salvato {out_path} · {len(signals)} segnali · regime {regime_status}")
    return out


def export_bootstrap_minimal_with_error(err_msg: str):
    out = export_bootstrap_minimal()
    out["engine_error"] = True
    out["error_detail"] = err_msg
    (DASH_DIR / "data-octa.json").write_text(
        json.dumps(out, separators=(",", ":"), default=str), encoding="utf-8")
    return out


def _is_in_tlh_window(d: date) -> bool:
    mmdd = f"{d.month:02d}-{d.day:02d}"
    return "11-01" <= mmdd <= "12-20"


# ═════════════════════════════════════════════════════════════════════════
# COMPANY META (name + ISIN) lookup via SEC company_tickers_exchange.json
# Cache locale ROOT/data/company_meta.json
# ═════════════════════════════════════════════════════════════════════════
def _load_company_meta() -> Dict[str, Dict]:
    """Returns dict ticker → {name, isin}. Cached daily."""
    import time
    cache_path = ROOT / "data" / "company_meta.json"
    if cache_path.exists() and (time.time() - cache_path.stat().st_mtime) < 30 * 86400:
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    print(f"[OCTA-META] fetching company name + CUSIP from SEC…")
    import urllib.request
    try:
        from qfas.qfas_config import get_sec_user_agent
        ua = get_sec_user_agent()
    except Exception:
        ua = "Super Investor Dashboard"
    try:
        req = urllib.request.Request(
            "https://www.sec.gov/files/company_tickers_exchange.json",
            headers={"User-Agent": ua, "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = json.loads(r.read().decode("utf-8"))
        # Schema: {fields: [...], data: [[cik, name, ticker, exchange, ...]]}
        fields = raw.get("fields", [])
        rows = raw.get("data", [])
        try:
            i_cik = fields.index("cik")
            i_name = fields.index("name")
            i_ticker = fields.index("ticker")
        except ValueError:
            i_cik, i_name, i_ticker = 0, 1, 2
        out = {}
        for row in rows:
            try:
                ticker = str(row[i_ticker]).upper()
                name = str(row[i_name])
                cik = str(row[i_cik]).zfill(10)
                # ISIN US: "US" + CUSIP(9 char) + check digit
                # SEC company_tickers_exchange NON include CUSIP, ma possiamo
                # usare CIK come fallback nel campo isin con prefisso "CIK-".
                # Per il vero ISIN US serve OpenFIGI o un'altra fonte.
                # Per ora salvo ticker come "isin" symbolic.
                out[ticker] = {"name": name, "isin": None, "cik": cik}
            except (IndexError, ValueError, TypeError):
                continue
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(out, separators=(",", ":")),
                              encoding="utf-8")
        print(f"[OCTA-META] cached {len(out)} ticker → name in {cache_path.relative_to(ROOT)}")
        # Arricchisco con ISIN US per ticker noti (top liquidi)
        _enrich_isin_via_openfigi(out, cache_path)
        return out
    except Exception as e:
        print(f"[OCTA-META] fetch fallito: {e} — fallback vuoto")
        return {}


def _enrich_isin_via_openfigi(meta: Dict[str, Dict], cache_path: Path):
    """
    Best-effort: arricchisce con ISIN per i ticker che ne hanno bisogno.
    OpenFIGI è gratuito 25/min senza key. Limito a 200 ticker per non
    rallentare il workflow. Se fallisce, isin resta None (UI mostra solo ticker).
    """
    import os
    import urllib.request, urllib.error
    api_key = os.environ.get("OPENFIGI_API_KEY")
    if not api_key and os.environ.get("OCTA_ENABLE_OPENFIGI") != "1":
        print("[OCTA-META] OpenFIGI skip: niente API key e ISIN non richiesto per nomenclatura UI")
        return
    targets = [t for t, m in meta.items() if m.get("isin") is None][:200]
    if not targets:
        return
    print(f"[OCTA-META] arricchimento ISIN via OpenFIGI per {len(targets)} ticker…")
    batch_size = 10  # limite prudente OpenFIGI free
    enriched = 0
    for i in range(0, len(targets), batch_size):
        chunk = targets[i:i + batch_size]
        body = json.dumps([
            {"idType": "TICKER", "idValue": t, "exchCode": "US"}
            for t in chunk
        ]).encode("utf-8")
        try:
            req = urllib.request.Request(
                "https://api.openfigi.com/v3/mapping",
                data=body, method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    **({"X-OPENFIGI-APIKEY": api_key} if api_key else {}),
                }
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                results = json.loads(r.read().decode("utf-8"))
            for t, res in zip(chunk, results):
                arr = res.get("data", []) if isinstance(res, dict) else []
                if arr:
                    isin = arr[0].get("compositeFIGI") or arr[0].get("figi")
                    # OpenFIGI non sempre ritorna ISIN diretto. Saltabile.
                    # Per ora salviamo il ticker, lasciamo isin opzionale.
                    meta[t]["isin"] = None  # placeholder per future
                    enriched += 1
        except Exception as e:
            print(f"[OCTA-META]   batch fail (continua): {e}")
            continue
        import time as _t
        _t.sleep(2.5)  # 25 req/min limit
    print(f"[OCTA-META] ISIN lookup tentato per {enriched}/{len(targets)}")
    cache_path.write_text(json.dumps(meta, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["bootstrap", "decision"], default="bootstrap")
    p.add_argument("--date", default=None, help="YYYY-MM-DD (default oggi)")
    args = p.parse_args()

    if args.mode == "bootstrap":
        export_bootstrap_minimal()
    else:
        sig_date = date.fromisoformat(args.date) if args.date else None
        export_from_decision_cycle(sig_date)
