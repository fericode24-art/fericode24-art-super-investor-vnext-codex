from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qfas.qfas_export_octa import load_decision_data
from qfas.qfas_runner import run_decision_cycle


def _dashboard_signal_date() -> date:
    path = ROOT / "dashboard" / "data-octa.json"
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if raw.get("signal_date"):
                return date.fromisoformat(str(raw["signal_date"])[:10])
        except Exception:
            pass
    return date.today()


def _previous_trading_days(start: date, count: int) -> List[date]:
    out = []
    d = start
    while len(out) < count:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return out


def _vix_value(vix_series, signal_date: date):
    if vix_series is None or not len(vix_series):
        return None
    v = vix_series[vix_series.index <= pd.Timestamp(signal_date)].dropna()
    return float(v.iloc[-1]) if not v.empty else None


def _run(signal_date: date, mode: str):
    data = load_decision_data(signal_date)
    prices_df = data["prices_df"]
    universe = data["universe"]
    prices_by_ticker = {
        t: prices_df[t].dropna()
        for t in universe
        if t in prices_df.columns
    }
    return run_decision_cycle(
        signal_date=signal_date,
        current_holdings=[],
        universe_tickers=universe,
        all_filings_by_fund=data["filings_by_cik"],
        prices_by_ticker=prices_by_ticker,
        sectors_by_ticker=data["sectors"],
        vix_value=_vix_value(data["vix_series"], signal_date),
        skip_external_signals=(mode == "off"),
        external_signal_mode=mode,
    )


def _top(cycle, n: int) -> List[str]:
    return [c.ticker for c in cycle.all_candidates[:n]]


def _candidate_map(cycle) -> Dict[str, object]:
    return {c.ticker: c for c in cycle.all_candidates}


def _market_shadow_summary(cycle) -> Dict:
    rows = []
    for c in cycle.all_candidates[:80]:
        audit = c.audit or {}
        if not audit.get("market_shadow_cached"):
            continue
        rows.append({
            "ticker": c.ticker,
            "score": round(float(c.opportunity_score), 2),
            "entry": round(float(c.entry_score), 2),
            "shadow_entry": round(float(audit.get("market_shadow_entry") or c.entry_score), 2),
            "shadow_delta": round(float(audit.get("market_shadow_delta") or 0.0), 2),
            "congressional": audit.get("congressional_shadow"),
            "congressional_trades": audit.get("congressional_trades"),
            "congressional_net": audit.get("congressional_net"),
            "short_interest": audit.get("short_interest_shadow"),
            "short_interest_state": audit.get("short_interest_state"),
            "squeeze": audit.get("squeeze_shadow"),
        })
    deltas = [float(r["shadow_delta"]) for r in rows]
    return {
        "status": "cache_present" if rows else "missing_cache",
        "cached_rows_top80": len(rows),
        "congressional_nonzero_top80": sum(1 for r in rows if float(r.get("congressional") or 0.0) > 0),
        "short_interest_rows_top80": sum(1 for r in rows if r.get("short_interest") is not None),
        "squeeze_watch_top80": sum(1 for r in rows if r.get("squeeze") not in (None, "none")),
        "max_abs_shadow_delta": round(max([abs(d) for d in deltas] or [0.0]), 2),
        "largest_shadow_impacts": sorted(rows, key=lambda r: abs(float(r["shadow_delta"])), reverse=True)[:12],
    }


def compare_date(signal_date: date) -> Dict:
    off = _run(signal_date, "off")
    cached = _run(signal_date, "cached")
    off_rank = {t: i + 1 for i, t in enumerate(_top(off, 80))}
    cached_rank = {t: i + 1 for i, t in enumerate(_top(cached, 80))}
    cached_by_ticker = _candidate_map(cached)
    common = [t for t in cached_rank if t in off_rank]
    moves = sorted(
        (
            {
                "ticker": t,
                "off_rank": off_rank[t],
                "cached_rank": cached_rank[t],
                "rank_move": off_rank[t] - cached_rank[t],
                "external_delta": round(float(cached_by_ticker[t].audit.get("external_delta") or 0), 2),
                "score": round(float(cached_by_ticker[t].opportunity_score), 2),
            }
            for t in common
        ),
        key=lambda r: abs(r["rank_move"]),
        reverse=True,
    )
    top10_overlap = len(set(_top(off, 10)) & set(_top(cached, 10)))
    top8_overlap = len(set(_top(off, 8)) & set(_top(cached, 8)))
    deltas = [
        float(c.audit.get("external_delta") or 0.0)
        for c in cached.all_candidates[:80]
    ]
    top40 = cached.all_candidates[:40]
    coverage = {
        "with_external_delta": sum(1 for d in deltas if abs(d) > 0.05),
        "insider_cached_top40": sum(1 for c in top40 if c.audit.get("insider_cached")),
        "analyst_cached_top40": sum(1 for c in top40 if c.audit.get("analyst_cached")),
        "pead_active_top40": sum(1 for c in top40 if c.audit.get("pead_cached")),
    }
    checks = {
        "same_candidate_count": off.n_candidates == cached.n_candidates and cached.n_candidates > 0,
        "cached_has_portfolio": len(cached.portfolio) == 8,
        "external_delta_bounded": max([abs(d) for d in deltas] or [0.0]) <= 12.01,
        "external_affects_ranking": coverage["with_external_delta"] > 0,
        "top10_not_destroyed": top10_overlap >= 5,
    }
    return {
        "date": signal_date.isoformat(),
        "checks": checks,
        "passed": all(checks.values()),
        "off_top10": _top(off, 10),
        "cached_top10": _top(cached, 10),
        "off_portfolio": [p.ticker for p in off.portfolio],
        "cached_portfolio": [p.ticker for p in cached.portfolio],
        "top10_overlap": top10_overlap,
        "top8_overlap": top8_overlap,
        "coverage": coverage,
        "market_shadow": _market_shadow_summary(cached),
        "largest_rank_moves": moves[:12],
        "external_cache": cached.audit_log.get("external_cache", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--date", default=None)
    args = parser.parse_args()
    first = date.fromisoformat(args.date) if args.date else _dashboard_signal_date()
    dates = _previous_trading_days(first, max(1, args.days))
    results = [compare_date(d) for d in dates]
    report = {
        "generated_at": pd.Timestamp.now("UTC").isoformat(),
        "profile": "cached",
        "passed": all(r["passed"] for r in results),
        "results": results,
    }
    out_path = ROOT / "output" / "external_profile_compare.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(
            f"{status} {r['date']} top10_overlap={r['top10_overlap']} "
            f"delta_rows={r['coverage']['with_external_delta']} "
            f"market_shadow_rows={r['market_shadow']['cached_rows_top80']} "
            f"max_shadow={r['market_shadow']['max_abs_shadow_delta']} "
            f"portfolio={','.join(r['cached_portfolio'])}"
        )
    print(f"report={out_path}")
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
