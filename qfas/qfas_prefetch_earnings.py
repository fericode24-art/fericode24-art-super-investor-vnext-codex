"""
QFAS — pre-cache 8-K Item 2.02 earnings dates per ticker universo.
Workflow notturno, salva data/backtest/earnings_cache.json.

Output:
  {
    "AAPL": {
      "ts": "2026-05-25T03:30:00Z",
      "earnings_dates": ["2026-04-30", "2026-01-29", "2025-10-30", "2025-07-31"]
    }, ...
  }
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = Path(__file__).parent.parent.absolute()
CACHE_FILE = ROOT / "data" / "backtest" / "earnings_cache.json"


def log(msg):
    print(f"[EARN] {msg}", flush=True)


def build_target_universe(top_n: int = 200) -> list[str]:
    r1000_path = ROOT / "data" / "russell_1000.json"
    h13f_path = ROOT / "data" / "backtest" / "hist_13f_l40.json"
    r1000 = {c["ticker"] for c in json.loads(r1000_path.read_text())["constituents"]}
    h13f = json.loads(h13f_path.read_text())
    counts = {}
    for cik, filings in h13f.items():
        seen = set()
        for f in sorted(filings, key=lambda x: x["date"])[-12:]:
            for h in f.get("holdings", []):
                t = h.get("ticker")
                if t and t not in seen:
                    seen.add(t)
                    counts[t] = counts.get(t, 0) + 1
    in_3plus = {t for t, n in counts.items() if n >= 3}
    return sorted(in_3plus & r1000)[:top_n]


def prefetch(top_n: int = 200):
    from qfas.data_ingestion import get_earnings_dates_8k
    from datetime import datetime as _dt

    universe = build_target_universe(top_n)
    log(f"Universo: {len(universe)} ticker")

    cache = {}
    if CACHE_FILE.exists():
        try: cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception: pass

    t0 = time.time()
    ok = fail = 0
    for i, t in enumerate(universe):
        if i > 0 and i % 25 == 0:
            elapsed = time.time() - t0
            eta = elapsed / i * (len(universe) - i) / 60
            log(f"  [{i}/{len(universe)}] {ok}ok {fail}fail · ETA {eta:.1f}min")
        try:
            dates = get_earnings_dates_8k(t, lookback_quarters=8)
            if dates:
                cache[t] = {
                    "ts": _dt.utcnow().isoformat() + "Z",
                    "earnings_dates": [d.isoformat() for d in dates],
                }
                ok += 1
            else:
                fail += 1
        except Exception as e:
            log(f"  ERR {t}: {e}")
            fail += 1

    log(f"\nCompletato in {time.time()-t0:.0f}s · {ok}ok {fail}fail")
    CACHE_FILE.write_text(json.dumps(cache, separators=(",", ":")), encoding="utf-8")
    log(f"Salvato {CACHE_FILE.relative_to(ROOT)} ({CACHE_FILE.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--top-n", type=int, default=200)
    args = p.parse_args()
    prefetch(args.top_n)
