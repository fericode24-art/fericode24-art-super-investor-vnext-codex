"""
QFAS — script per warm-cache prezzi 15 mesi.

Scarica via yfinance solo i prezzi necessari per il decision cycle:
  - 459 ticker universo (R1000 ∩ 13F ≥3 fondi)
  - + SPY, QQQ, ^VIX
  - 15 mesi di storia

Output: data/backtest/prices_octa.csv (~1.5 MB)
Idempotente: skip download se cache <24h vecchia.
"""
from __future__ import annotations
import json, sys, time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = Path(__file__).parent.parent.absolute()
DATA_DIR = ROOT / "data" / "backtest"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_OCTA = DATA_DIR / "prices_octa.csv"


def build_octa_universe() -> list[str]:
    """Calcola universo OCTA: R1000 ∩ 13F (≥3 fondi)."""
    r1000 = {c["ticker"] for c in
             json.loads((ROOT / "data" / "russell_1000.json").read_text())["constituents"]}
    h13f = json.loads((DATA_DIR / "hist_13f_l40.json").read_text())
    counts = {}
    for cik, filings in h13f.items():
        seen = set()
        # solo ultimi 12 filing per fondo
        for f in sorted(filings, key=lambda x: x["date"])[-12:]:
            for h in f.get("holdings", []):
                t = h.get("ticker")
                if t and t not in seen:
                    seen.add(t)
                    counts[t] = counts.get(t, 0) + 1
    in_3plus = {t for t, n in counts.items() if n >= 3}
    return sorted(in_3plus & r1000)


def download_prices(force: bool = False):
    """Scarica/aggiorna prices_octa.csv.

    FIX BUG #B (round 2): check freshness basato sulla data più recente DENTRO
    il CSV, non sul mtime del file. Quando GitHub Actions restore-keys una cache
    di ieri, l'mtime è "ora" ma i dati sono di ieri → controllo l'ultima riga
    del CSV per capire l'effettiva freshness.
    """
    import yfinance as yf
    if not force and CACHE_OCTA.exists():
        # Leggi solo l'index (data) per controllare freshness
        try:
            last_date = pd.read_csv(CACHE_OCTA, index_col=0, parse_dates=True,
                                    usecols=[0]).index.max()
            today = pd.Timestamp(date.today())
            # Mercati USA: ultima data utile = oggi se trading aperto, altrimenti
            # ultimo giorno lavorativo. Tollero fino a 4 giorni (weekend + holiday)
            staleness_days = (today - last_date).days
            if staleness_days <= 4:
                print(f"[QFAS-DL] cache prices_octa.csv contiene dati fino a "
                      f"{last_date.date()} ({staleness_days}gg fa), skip")
                return
            else:
                print(f"[QFAS-DL] cache prices_octa.csv stale ({staleness_days}gg, "
                      f"ultimo dato {last_date.date()}) → forza redownload")
        except Exception as e:
            print(f"[QFAS-DL] cache check fallito ({e}) → redownload")

    universe = build_octa_universe()
    tickers = universe + ["SPY", "QQQ", "^VIX"]
    print(f"[QFAS-DL] universo: {len(universe)} ticker + SPY/QQQ/^VIX")

    end_date = date.today() + timedelta(days=2)
    start_date = end_date - timedelta(days=15 * 31 + 30)   # 15 mesi + buffer
    print(f"[QFAS-DL] periodo: {start_date} → {end_date}")

    # Yahoo replace dot con dash
    def y(t): return t.replace(".", "-") if not t.startswith("^") else t
    syms = [y(t) for t in tickers]

    # FIX BUG #γ: retry su Yahoo 429/empty con backoff exponential.
    # yfinance è notoriamente flaky → senza retry il workflow crasha 1-2 volte/sett.
    t0 = time.time()
    data = None
    last_err = None
    for attempt in range(3):
        try:
            data = yf.download(syms, start=start_date, end=end_date,
                               auto_adjust=True, progress=False, threads=True,
                               group_by="ticker")
            if data is not None and not data.empty:
                break
            last_err = "empty result"
        except Exception as e:
            last_err = str(e)
        wait = 30 * (attempt + 1)
        print(f"[QFAS-DL] yfinance attempt {attempt+1}/3 failed ({last_err}), wait {wait}s")
        time.sleep(wait)
    if data is None or data.empty:
        raise RuntimeError(f"yfinance returned empty data after 3 attempts: {last_err}")

    # Estrai Close per tutti
    out = pd.DataFrame()
    failed = []
    for orig, ysym in zip(tickers, syms):
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if ysym in data.columns.get_level_values(0):
                    sub = data[ysym]
                else:
                    failed.append(orig); continue
            else:
                sub = data
            if "Close" not in sub.columns:
                failed.append(orig); continue
            s = sub["Close"].dropna()
            if len(s) < 30:
                failed.append(orig); continue
            out[orig] = s
        except Exception:
            failed.append(orig)

    elapsed = time.time() - t0
    print(f"[QFAS-DL] scaricato in {elapsed:.0f}s · {out.shape[1]}/{len(tickers)} ticker "
          f"× {out.shape[0]} giorni · failed: {len(failed)}")

    # FIX BUG #δ: sanity check sui prezzi (Yahoo bad data: split errati,
    # valori azzerati, jump >10x giornalieri). Sostituisce outlier con NaN
    # → niente segnali falsi per momentum/SMA bagliato.
    n_outliers = 0
    for col in out.columns:
        s = out[col]
        # Calcola rapporto giorno-su-giorno
        ratio = s / s.shift(1)
        # Outlier: salto >10x o <0.1x (split mal calibrato, errori dati)
        mask = (ratio > 10) | (ratio < 0.1)
        if mask.any():
            n_local = int(mask.sum())
            n_outliers += n_local
            # Marca outlier come NaN (forward fill consigliata in consumer)
            out.loc[mask, col] = pd.NA
    if n_outliers > 0:
        print(f"[QFAS-DL] ⚠ sanity check: rimossi {n_outliers} outlier (jump >10x o <0.1x)")
    # Sanity check #2: ticker con < 30 valid prices ultimi 60gg → escludi
    recent_60d = out.tail(60)
    bad_tickers = [c for c in out.columns
                   if recent_60d[c].notna().sum() < 30]
    if bad_tickers:
        print(f"[QFAS-DL] ⚠ {len(bad_tickers)} ticker con dati recenti scarsi: "
              f"{bad_tickers[:10]}{'…' if len(bad_tickers) > 10 else ''}")
        out = out.drop(columns=bad_tickers)

    out.to_csv(CACHE_OCTA)
    size_mb = CACHE_OCTA.stat().st_size / 1024 / 1024
    print(f"[QFAS-DL] salvato {CACHE_OCTA.relative_to(ROOT)} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="forza download anche se cache <24h")
    args = p.parse_args()
    download_prices(force=args.force)
