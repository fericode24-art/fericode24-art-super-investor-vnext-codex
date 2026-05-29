from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apex.engine import (
    backtest_rotation,
    buy_and_hold,
    compute_signal_series,
    equal_weight_bh,
    performance_stats,
    select_weekly_observations,
)
from apex.yahoo import build_listed_prices, build_proxy_prices, latest_intraday_snapshot


CACHE_DIR = ROOT / "data" / "apex"
OUT_DIR = ROOT / "output"


def _fmt_pct(x):
    return round(float(x) * 100, 2)


PCT_FIELDS = {"total_return", "cagr", "max_drawdown", "volatility"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["proxy", "listed"], default="proxy")
    ap.add_argument("--price", choices=["open", "close"], default="close")
    ap.add_argument("--cost-bps", type=float, default=30.0)
    ap.add_argument("--lookbacks", default="4,6,8,10,12,16")
    ap.add_argument("--range", default="max")
    ap.add_argument("--intraday", action="store_true")
    args = ap.parse_args()

    if args.profile == "listed":
        prices = build_listed_prices(CACHE_DIR, price_col=args.price, range_=args.range)
    else:
        prices = build_proxy_prices(CACHE_DIR, price_col=args.price, range_=args.range)

    observations = select_weekly_observations(prices)
    lookbacks = [int(x.strip()) for x in args.lookbacks.split(",") if x.strip()]
    results = []
    for lb in lookbacks:
        if len(observations) < lb + 2:
            continue
        bt = backtest_rotation(observations, cost_bps=args.cost_bps, lookback_weeks=lb)
        stats = performance_stats(bt)
        sigs = compute_signal_series(observations, lookback_weeks=lb)
        results.append({
            "lookback": lb,
            "signal_count": len(sigs),
            "changes": int(sum(1 for s in sigs if s.changed)),
            "apex": {k: (_fmt_pct(v) if k in PCT_FIELDS else round(float(v), 3) if k == "sharpe" else v)
                     for k, v in stats.items()},
        })

    bh = {
        "BTC": performance_stats(buy_and_hold(observations, "BTC")),
        "GOLD": performance_stats(buy_and_hold(observations, "GOLD")),
        "SP500": performance_stats(buy_and_hold(observations, "SP500")),
        "EQUAL_BTC_GOLD_SP500": performance_stats(equal_weight_bh(observations)),
    }
    bh_fmt = {
        name: {k: (_fmt_pct(v) if k in PCT_FIELDS else round(float(v), 3) if k == "sharpe" else v)
               for k, v in stats.items()}
        for name, stats in bh.items()
    }
    payload = {
        "profile": args.profile,
        "price": args.price,
        "cost_bps": args.cost_bps,
        "n_weekly_observations": len(observations),
        "first_week": observations[0]["date"].isoformat() if observations else None,
        "last_week": observations[-1]["date"].isoformat() if observations else None,
        "lookback_results": results,
        "benchmarks": bh_fmt,
    }
    if args.intraday:
        payload["intraday_snapshot"] = latest_intraday_snapshot(CACHE_DIR)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cost_tag = str(args.cost_bps).replace(".", "p")
    lookback_tag = args.lookbacks.replace(",", "-")
    out_path = OUT_DIR / f"apex_backtest_{args.profile}_{args.price}_lb{lookback_tag}_cost{cost_tag}.json"
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str))
    print(f"\nSaved {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
