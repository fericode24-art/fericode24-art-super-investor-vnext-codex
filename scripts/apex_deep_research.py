from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apex.engine import ASSET_ORDER, _as_date, _signal_from_returns, select_weekly_observations
from apex.yahoo import build_proxy_prices


CACHE_DIR = ROOT / "data" / "apex"
OUT_DIR = ROOT / "output"
DOC_PATH = ROOT / "docs" / "APEX_DEEP_BACKTEST_2026-05-28.md"
INITIAL = 10_000.0
PCT_FIELDS = {
    "total_return",
    "cagr",
    "max_drawdown",
    "volatility",
    "downside_volatility",
    "worst_week",
    "best_week",
    "worst_month",
    "best_month",
    "worst_year",
    "best_year",
}


@dataclass(frozen=True)
class SignalInfo:
    idx: int
    date: date
    raw: str
    reason: str
    scores: Dict[str, float]


def pct(x: float, digits: int = 2) -> float:
    return round(float(x) * 100.0, digits)


def round_metric(key: str, value):
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        if key in PCT_FIELDS:
            return pct(float(value))
        return round(float(value), 4)
    return value


def raw_signal_for(rows: List[Dict], i: int, lookback: int, mode: str = "apex") -> SignalInfo:
    cur, prev = rows[i], rows[i - lookback]
    scores = {
        "BTC": float(cur["BTC"]) / float(prev["BTC"]) - 1.0,
        "GOLD": float(cur["GOLD"]) / float(prev["GOLD"]) - 1.0,
        "SP500": float(cur["SP500"]) / float(prev["SP500"]) - 1.0,
        "CASH": 0.0,
    }
    if mode == "pure_relative":
        best = max(("BTC", "GOLD", "SP500"), key=lambda a: scores[a])
        if scores[best] > 0:
            raw, reason = best, f"{best} ha il momentum positivo piu alto"
        else:
            raw, reason = "CASH", "Nessun momentum positivo"
    else:
        raw, reason = _signal_from_returns(scores["BTC"], scores["GOLD"], scores["SP500"])
    return SignalInfo(idx=i, date=_as_date(cur["date"]), raw=raw, reason=reason, scores=scores)


def variant_target(
    info: SignalInfo,
    current: Optional[str],
    state: Dict,
    variant: str,
) -> str:
    raw = info.raw
    if current is None:
        state["pending"] = None
        state["pending_count"] = 0
        return raw
    if variant == "apex_rev2" or variant == "pure_relative":
        return raw
    if variant == "confirm2_buffer2":
        # First require two consecutive raw signals, then a 2pp improvement.
        confirm = variant_target(info, current, state, "confirm2")
        if confirm == current:
            return current
        if info.scores.get(confirm, 0.0) - info.scores.get(current, 0.0) >= 0.02:
            return confirm
        return current
    if variant.startswith("confirm2"):
        if raw == current:
            state["pending"] = None
            state["pending_count"] = 0
            return current
        if state.get("pending") == raw:
            state["pending_count"] = int(state.get("pending_count", 0)) + 1
        else:
            state["pending"] = raw
            state["pending_count"] = 1
        return raw if state["pending_count"] >= 2 else current
    if variant.startswith("buffer"):
        # Example: buffer_2pp -> require new raw signal to beat the current
        # held asset by at least 2 percentage points of 8w momentum.
        pp = float(variant.split("_")[1].replace("pp", "")) / 100.0
        if raw == current:
            return current
        if info.scores.get(raw, 0.0) - info.scores.get(current, 0.0) >= pp:
            return raw
        return current
    raise ValueError(f"unknown variant: {variant}")


def period_return(row: Dict, nxt: Dict, asset: str) -> float:
    if asset == "CASH":
        if "CASH" in row and "CASH" in nxt and float(row["CASH"]) > 0:
            return float(nxt["CASH"]) / float(row["CASH"]) - 1.0
        return 0.0
    return float(nxt[asset]) / float(row[asset]) - 1.0


def run_strategy(
    rows: List[Dict],
    lookback: int,
    variant: str,
    cost_bps: float,
    raw_mode: str = "apex",
) -> pd.DataFrame:
    if len(rows) < lookback + 2:
        raise ValueError("not enough observations")
    signals = [raw_signal_for(rows, i, lookback, mode=raw_mode) for i in range(lookback, len(rows))]
    value = INITIAL
    current: Optional[str] = None
    state: Dict = {"pending": None, "pending_count": 0}
    start_date = signals[0].date
    records = [{
        "date": start_date,
        "value": value,
        "signal": "START",
        "raw_signal": signals[0].raw,
        "changed": False,
        "cost": 0.0,
        "period_ret": 0.0,
        "ret_btc": signals[0].scores["BTC"],
        "ret_gold": signals[0].scores["GOLD"],
        "ret_sp500": signals[0].scores["SP500"],
    }]
    for pos, info in enumerate(signals[:-1]):
        nxt_info = signals[pos + 1]
        target = variant_target(info, current, state, variant)
        before_cost = value
        changed = target != current
        cost = 0.0
        if changed:
            cost = before_cost * cost_bps / 10000.0
            value = before_cost - cost
            current = target
        row = rows[info.idx]
        nxt = rows[nxt_info.idx]
        ret = period_return(row, nxt, current or target)
        value *= 1.0 + ret
        records.append({
            "date": nxt_info.date,
            "value": value,
            "signal": current or target,
            "raw_signal": nxt_info.raw,
            "changed": changed,
            "cost": cost,
            "period_ret": ret,
            "ret_btc": nxt_info.scores["BTC"],
            "ret_gold": nxt_info.scores["GOLD"],
            "ret_sp500": nxt_info.scores["SP500"],
        })
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")


def run_strategy_period(
    rows: List[Dict],
    lookback: int,
    variant: str,
    cost_bps: float,
    start: str | date,
    end: str | date,
    raw_mode: str = "apex",
) -> pd.DataFrame:
    """Run a period with pre-period lookback context but fresh starting capital.

    This is the right mode for "start 2018" comparisons: the first 2018 signal
    can use Nov/Dec 2017 data, but performance starts from the first signal
    inside 2018 with a fresh initial allocation.
    """
    s, e = _as_date(start), _as_date(end)
    all_signals = [raw_signal_for(rows, i, lookback, mode=raw_mode) for i in range(lookback, len(rows))]
    signals = [info for info in all_signals if s <= info.date <= e]
    if len(signals) < 2:
        raise ValueError("not enough in-period signals")
    value = INITIAL
    current: Optional[str] = None
    state: Dict = {"pending": None, "pending_count": 0}
    records = [{
        "date": signals[0].date,
        "value": value,
        "signal": "START",
        "raw_signal": signals[0].raw,
        "changed": False,
        "cost": 0.0,
        "period_ret": 0.0,
        "ret_btc": signals[0].scores["BTC"],
        "ret_gold": signals[0].scores["GOLD"],
        "ret_sp500": signals[0].scores["SP500"],
    }]
    for pos, info in enumerate(signals[:-1]):
        nxt_info = signals[pos + 1]
        target = variant_target(info, current, state, variant)
        before_cost = value
        changed = target != current
        cost = 0.0
        if changed:
            cost = before_cost * cost_bps / 10000.0
            value = before_cost - cost
            current = target
        row = rows[info.idx]
        nxt = rows[nxt_info.idx]
        ret = period_return(row, nxt, current or target)
        value *= 1.0 + ret
        records.append({
            "date": nxt_info.date,
            "value": value,
            "signal": current or target,
            "raw_signal": nxt_info.raw,
            "changed": changed,
            "cost": cost,
            "period_ret": ret,
            "ret_btc": nxt_info.scores["BTC"],
            "ret_gold": nxt_info.scores["GOLD"],
            "ret_sp500": nxt_info.scores["SP500"],
        })
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")


def aligned_benchmark(rows: List[Dict], start_i: int, end_i: int, asset: str) -> pd.Series:
    subset = rows[start_i : end_i + 1]
    if asset == "EQUAL":
        parts = []
        for a in ASSET_ORDER:
            base = float(subset[0][a])
            parts.append(pd.Series(
                [INITIAL / 3.0 * float(r[a]) / base for r in subset],
                index=pd.to_datetime([_as_date(r["date"]) for r in subset]),
            ))
        out = sum(parts)
        out.name = "EQUAL"
        return out
    base = float(subset[0][asset])
    return pd.Series(
        [INITIAL * float(r[asset]) / base for r in subset],
        index=pd.to_datetime([_as_date(r["date"]) for r in subset]),
        name=asset,
    )


def benchmark_on_dates(rows: List[Dict], dates: Iterable[pd.Timestamp], asset: str) -> pd.Series:
    date_to_row = {_as_date(r["date"]): r for r in rows}
    selected = [date_to_row[d.date() if hasattr(d, "date") else _as_date(d)] for d in dates
                if (d.date() if hasattr(d, "date") else _as_date(d)) in date_to_row]
    if len(selected) < 2:
        return pd.Series(dtype=float)
    if asset == "EQUAL":
        parts = []
        for a in ASSET_ORDER:
            base = float(selected[0][a])
            parts.append(pd.Series(
                [INITIAL / 3.0 * float(r[a]) / base for r in selected],
                index=pd.to_datetime([_as_date(r["date"]) for r in selected]),
            ))
        out = sum(parts)
        out.name = "EQUAL"
        return out
    base = float(selected[0][asset])
    return pd.Series(
        [INITIAL * float(r[asset]) / base for r in selected],
        index=pd.to_datetime([_as_date(r["date"]) for r in selected]),
        name=asset,
    )


def max_drawdown_duration(equity: pd.Series) -> int:
    peak = equity.iloc[0]
    current = 0
    worst = 0
    for v in equity:
        if v >= peak:
            peak = v
            current = 0
        else:
            current += 1
            worst = max(worst, current)
    return worst


def return_by_period(equity: pd.Series, rule: str) -> pd.Series:
    last = equity.resample(rule).last().dropna()
    first = equity.resample(rule).first().dropna()
    # Include return from first point of period to last point of period.
    aligned = pd.concat([first, last], axis=1, keys=["first", "last"]).dropna()
    return aligned["last"] / aligned["first"] - 1.0


def stats_for(df_or_series, extra: Optional[Dict] = None) -> Dict:
    if isinstance(df_or_series, pd.DataFrame):
        equity = df_or_series["value"].dropna()
        frame = df_or_series
    else:
        equity = df_or_series.dropna()
        frame = None
    weekly = equity.pct_change().dropna()
    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1 / 52)
    total = equity.iloc[-1] / equity.iloc[0] - 1.0
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0
    dd = equity / equity.cummax() - 1.0
    vol = weekly.std() * math.sqrt(52) if len(weekly) else 0.0
    downside = weekly[weekly < 0].std() * math.sqrt(52) if (weekly < 0).any() else 0.0
    sharpe = (weekly.mean() * 52) / vol if vol else 0.0
    sortino = (weekly.mean() * 52) / downside if downside else 0.0
    monthly = return_by_period(equity, "ME") if len(equity) else pd.Series(dtype=float)
    yearly = return_by_period(equity, "YE") if len(equity) else pd.Series(dtype=float)
    out = {
        "start": equity.index[0].date().isoformat(),
        "end": equity.index[-1].date().isoformat(),
        "years": years,
        "final": float(equity.iloc[-1]),
        "total_return": total,
        "cagr": cagr,
        "max_drawdown": float(dd.min()),
        "drawdown_duration_weeks": max_drawdown_duration(equity),
        "volatility": vol,
        "downside_volatility": downside,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": cagr / abs(float(dd.min())) if dd.min() < 0 else 0.0,
        "worst_week": float(weekly.min()) if len(weekly) else 0.0,
        "best_week": float(weekly.max()) if len(weekly) else 0.0,
        "worst_month": float(monthly.min()) if len(monthly) else 0.0,
        "best_month": float(monthly.max()) if len(monthly) else 0.0,
        "worst_year": float(yearly.min()) if len(yearly) else 0.0,
        "best_year": float(yearly.max()) if len(yearly) else 0.0,
    }
    if frame is not None:
        switches = int(frame["changed"].sum())
        exposure = frame.loc[frame["signal"] != "START", "signal"].value_counts(normalize=True).to_dict()
        out.update({
            "switches": switches,
            "switches_per_year": switches / years,
            "total_cost": float(frame["cost"].sum()),
            "exposure_btc": exposure.get("BTC", 0.0),
            "exposure_gold": exposure.get("GOLD", 0.0),
            "exposure_sp500": exposure.get("SP500", 0.0),
            "exposure_cash": exposure.get("CASH", 0.0),
        })
    if extra:
        out.update(extra)
    return out


def summarize_stats(stats: Dict) -> Dict:
    return {k: round_metric(k, v) for k, v in stats.items()}


def subperiod_slice(rows: List[Dict], start: str, end: str) -> List[Dict]:
    s, e = _as_date(start), _as_date(end)
    return [r for r in rows if s <= _as_date(r["date"]) <= e]


def table_md(rows: List[Dict], columns: List[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prices_open = build_proxy_prices(CACHE_DIR, price_col="open", range_="max")
    prices_close = build_proxy_prices(CACHE_DIR, price_col="close", range_="max")
    rows_open = select_weekly_observations(prices_open)
    rows_close = select_weekly_observations(prices_close)

    lookbacks = list(range(2, 27))
    costs = [0, 10, 30, 60, 100]
    grid_records = []
    for price_name, rows in (("open", rows_open), ("close", rows_close)):
        for cost in costs:
            for lb in lookbacks:
                if len(rows) < lb + 2:
                    continue
                df = run_strategy(rows, lb, "apex_rev2", cost_bps=cost)
                grid_records.append(stats_for(df, {
                    "profile": "proxy",
                    "price": price_name,
                    "variant": "apex_rev2",
                    "lookback": lb,
                    "cost_bps": cost,
                }))
    grid = pd.DataFrame(grid_records)
    grid.to_csv(OUT_DIR / "apex_deep_grid.csv", index=False)

    variant_specs = [
        ("apex_rev2", "apex"),
        ("pure_relative", "pure_relative"),
        ("confirm2", "apex"),
        ("buffer_2pp", "apex"),
        ("buffer_5pp", "apex"),
        ("confirm2_buffer2", "apex"),
    ]
    variant_records = []
    for variant, raw_mode in variant_specs:
        for lb in [6, 8, 10, 12, 16]:
            df = run_strategy(rows_open, lb, variant, cost_bps=30, raw_mode=raw_mode)
            variant_records.append(stats_for(df, {
                "profile": "proxy",
                "price": "open",
                "variant": variant,
                "lookback": lb,
                "cost_bps": 30,
            }))
    variants = pd.DataFrame(variant_records)
    variants.to_csv(OUT_DIR / "apex_deep_variants.csv", index=False)

    # Main aligned benchmarks for 8w/open.
    lb = 8
    base_df = run_strategy(rows_open, lb, "apex_rev2", cost_bps=30)
    start_i, end_i = lb, len(rows_open) - 1
    benchmark_records = []
    for asset in ["BTC", "GOLD", "SP500", "EQUAL"]:
        s = aligned_benchmark(rows_open, start_i, end_i, asset)
        benchmark_records.append(stats_for(s, {
            "profile": "proxy",
            "price": "open",
            "variant": asset if asset != "EQUAL" else "EQUAL_BTC_GOLD_SP500",
            "lookback": lb,
            "cost_bps": 0,
        }))
    benchmark_df = pd.DataFrame(benchmark_records)
    benchmark_df.to_csv(OUT_DIR / "apex_deep_benchmarks.csv", index=False)

    periods = [
        ("full", "2014-09-17", "2026-05-27"),
        ("claude_comparable_2018_now", "2018-01-01", "2026-05-27"),
        ("cycle_2014_2017", "2014-09-17", "2017-12-31"),
        ("bear_recovery_2018_2020", "2018-01-01", "2020-12-31"),
        ("mania_bear_2021_2023", "2021-01-01", "2023-12-31"),
        ("recent_2024_2026", "2024-01-01", "2026-05-27"),
    ]
    sub_records = []
    for name, start, end in periods:
        try:
            df = run_strategy_period(rows_open, lb, "apex_rev2", cost_bps=30, start=start, end=end)
        except ValueError:
            continue
        sub_records.append(stats_for(df, {"period": name, "variant": "APEX_8w_open"}))
        for asset in ["BTC", "EQUAL"]:
            s = benchmark_on_dates(rows_open, df.index, asset)
            sub_records.append(stats_for(s, {
                "period": name,
                "variant": "BTC_BH" if asset == "BTC" else "EQUAL_BH",
            }))
    subperiods = pd.DataFrame(sub_records)
    subperiods.to_csv(OUT_DIR / "apex_deep_subperiods.csv", index=False)

    # Claude-comparable 2018 start: fresh capital starts in 2018, but the
    # first signal can use pre-2018 lookback context.
    claude_start, claude_end = "2018-01-01", "2026-05-27"
    claude_candidate_specs = [
        ("apex_rev2", "apex", 6, "APEX Rev2 6w"),
        ("apex_rev2", "apex", 8, "APEX Rev2 8w originale"),
        ("apex_rev2", "apex", 17, "APEX Rev2 17w best full"),
        ("pure_relative", "pure_relative", 8, "Pure-relative 8w"),
        ("confirm2", "apex", 6, "Confirm2 6w"),
        ("confirm2", "apex", 10, "Confirm2 10w"),
        ("buffer_2pp", "apex", 6, "Buffer 2pp 6w"),
        ("buffer_5pp", "apex", 8, "Buffer 5pp 8w"),
        ("buffer_5pp", "apex", 16, "Buffer 5pp 16w"),
        ("confirm2_buffer2", "apex", 6, "Confirm2+buffer 6w"),
    ]
    claude_variant_records = []
    for variant, raw_mode, lbx, label in claude_candidate_specs:
        try:
            df = run_strategy_period(
                rows_open,
                lbx,
                variant,
                cost_bps=30,
                start=claude_start,
                end=claude_end,
                raw_mode=raw_mode,
            )
        except ValueError:
            continue
        claude_variant_records.append(stats_for(df, {
            "period": "claude_comparable_2018_now",
            "label": label,
            "variant": variant,
            "lookback": lbx,
            "cost_bps": 30,
        }))
    claude_variants = pd.DataFrame(claude_variant_records)
    claude_variants.to_csv(OUT_DIR / "apex_deep_claude2018_variants.csv", index=False)

    # Lookback robustness by regime.
    lb_sub_records = []
    for name, start, end in [p for p in periods if p[0] != "full"]:
        for lbx in lookbacks:
            try:
                df = run_strategy_period(rows_open, lbx, "apex_rev2", cost_bps=30, start=start, end=end)
            except ValueError:
                continue
            lb_sub_records.append(stats_for(df, {
                "period": name,
                "variant": "apex_rev2",
                "lookback": lbx,
                "cost_bps": 30,
            }))
    lb_sub = pd.DataFrame(lb_sub_records)
    lb_sub.to_csv(OUT_DIR / "apex_deep_lookback_subperiods.csv", index=False)

    # Expanding walk-forward: choose lookback on data available up to the
    # previous year, then evaluate the next calendar year.
    walk_records = []
    all_dates = [_as_date(r["date"]) for r in rows_open]
    for year in range(2018, 2027):
        train_end = date(year - 1, 12, 31)
        test_start = date(year, 1, 1)
        test_end = date(year, 12, 31)
        train = [r for r in rows_open if _as_date(r["date"]) <= train_end]
        if len(train) < max(lookbacks) + 52:
            continue
        train_scores = []
        for lbx in lookbacks:
            if len(train) < lbx + 2:
                continue
            df_train = run_strategy(train, lbx, "apex_rev2", cost_bps=30)
            st = stats_for(df_train)
            train_scores.append({"lookback": lbx, "train_sharpe": st["sharpe"], "train_cagr": st["cagr"]})
        if not train_scores:
            continue
        chosen = sorted(train_scores, key=lambda x: (x["train_sharpe"], x["train_cagr"]), reverse=True)[0]
        context = [r for r in rows_open if _as_date(r["date"]) <= test_end]
        df_chosen = run_strategy(context, int(chosen["lookback"]), "apex_rev2", cost_bps=30)
        df_static8 = run_strategy(context, 8, "apex_rev2", cost_bps=30)

        def slice_and_norm(frame: pd.DataFrame) -> pd.Series:
            s = frame["value"][(frame.index.date >= test_start) & (frame.index.date <= test_end)].copy()
            if len(s) < 2:
                return pd.Series(dtype=float)
            return s / s.iloc[0] * INITIAL

        wf = slice_and_norm(df_chosen)
        st8 = slice_and_norm(df_static8)
        if len(wf) < 2 or len(st8) < 2:
            continue
        # BTC benchmark with same weekly dates as static strategy slice.
        idx_dates = [d.date() for d in st8.index]
        date_to_row = {_as_date(r["date"]): r for r in rows_open}
        bench_rows = [date_to_row[d] for d in idx_dates if d in date_to_row]
        btc = aligned_benchmark(bench_rows, 0, len(bench_rows) - 1, "BTC") if len(bench_rows) >= 2 else pd.Series(dtype=float)
        walk_records.append({
            "year": year,
            "chosen_lookback": int(chosen["lookback"]),
            "train_sharpe": chosen["train_sharpe"],
            "train_cagr": chosen["train_cagr"],
            "wf_return": wf.iloc[-1] / wf.iloc[0] - 1.0,
            "static8_return": st8.iloc[-1] / st8.iloc[0] - 1.0,
            "btc_return": (btc.iloc[-1] / btc.iloc[0] - 1.0) if len(btc) >= 2 else None,
            "wf_max_dd": (wf / wf.cummax() - 1.0).min(),
            "static8_max_dd": (st8 / st8.cummax() - 1.0).min(),
        })
    walk = pd.DataFrame(walk_records)
    walk.to_csv(OUT_DIR / "apex_deep_walk_forward.csv", index=False)

    yearly = pd.DataFrame({
        "APEX_8w_open": return_by_period(base_df["value"], "YE"),
        "BTC_BH": return_by_period(aligned_benchmark(rows_open, start_i, end_i, "BTC"), "YE"),
        "EQUAL_BH": return_by_period(aligned_benchmark(rows_open, start_i, end_i, "EQUAL"), "YE"),
    }).dropna()
    yearly.to_csv(OUT_DIR / "apex_deep_yearly.csv")

    signal_tail = base_df.tail(12).copy()
    signal_tail["value"] = signal_tail["value"].round(2)
    signal_tail["period_ret"] = (signal_tail["period_ret"] * 100).round(2)
    signal_tail["ret_btc"] = (signal_tail["ret_btc"] * 100).round(2)
    signal_tail["ret_gold"] = (signal_tail["ret_gold"] * 100).round(2)
    signal_tail["ret_sp500"] = (signal_tail["ret_sp500"] * 100).round(2)
    signal_tail.reset_index().to_csv(OUT_DIR / "apex_deep_last_signals.csv", index=False)

    payload = {
        "data": {
            "source": "Yahoo Finance chart API",
            "profile": "proxy EUR",
            "weekly_observations_open": len(rows_open),
            "weekly_observations_close": len(rows_close),
            "first_open_week": rows_open[0]["date"].isoformat(),
            "last_open_week": rows_open[-1]["date"].isoformat(),
        },
        "best_open_30bps_by_cagr": summarize_stats(
            grid[(grid["price"] == "open") & (grid["cost_bps"] == 30)]
            .sort_values("cagr", ascending=False)
            .iloc[0]
            .to_dict()
        ),
        "base_8w_open": summarize_stats(stats_for(base_df, {
            "profile": "proxy",
            "price": "open",
            "variant": "apex_rev2",
            "lookback": lb,
            "cost_bps": 30,
        })),
        "benchmarks_8w_aligned": [summarize_stats(x) for x in benchmark_records],
        "best_variants": [
            summarize_stats(r.to_dict())
            for _, r in variants.sort_values(["sharpe", "cagr"], ascending=False).head(12).iterrows()
        ],
        "subperiods": [summarize_stats(r.to_dict()) for _, r in subperiods.iterrows()],
        "claude_2018_variants": [
            summarize_stats(r.to_dict())
            for _, r in claude_variants.sort_values(["sharpe", "cagr"], ascending=False).iterrows()
        ],
        "walk_forward": [summarize_stats(r.to_dict()) for _, r in walk.iterrows()],
        "yearly": {
            str(idx.year): {k: pct(v) for k, v in row.dropna().to_dict().items()}
            for idx, row in yearly.iterrows()
        },
    }
    (OUT_DIR / "apex_deep_results.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    open_30 = grid[(grid["price"] == "open") & (grid["cost_bps"] == 30)].copy()
    open_top = open_30.sort_values("cagr", ascending=False).head(10)
    top_rows = [
        {
            "lookback": int(r["lookback"]),
            "CAGR": f"{pct(r['cagr'])}%",
            "Max DD": f"{pct(r['max_drawdown'])}%",
            "Sharpe": round(float(r["sharpe"]), 3),
            "Switch": int(r["switches"]),
            "BTC%": f"{pct(r['exposure_btc'], 1)}%",
            "Cash%": f"{pct(r['exposure_cash'], 1)}%",
        }
        for _, r in open_top.iterrows()
    ]
    variant_rows = [
        {
            "variant": r["variant"],
            "lookback": int(r["lookback"]),
            "CAGR": f"{pct(r['cagr'])}%",
            "Max DD": f"{pct(r['max_drawdown'])}%",
            "Sharpe": round(float(r["sharpe"]), 3),
            "Switch": int(r["switches"]),
            "BTC%": f"{pct(r['exposure_btc'], 1)}%",
            "Cash%": f"{pct(r['exposure_cash'], 1)}%",
        }
        for _, r in variants.sort_values(["sharpe", "cagr"], ascending=False).head(12).iterrows()
    ]
    bench_rows = [
        {
            "strategia": r["variant"] if r["variant"] != "EQUAL" else "EQUAL_BTC_GOLD_SP500",
            "CAGR": f"{pct(r['cagr'])}%",
            "Max DD": f"{pct(r['max_drawdown'])}%",
            "Sharpe": round(float(r["sharpe"]), 3),
            "Finale 10k": round(float(r["final"]), 0),
        }
        for r in [stats_for(base_df, {"variant": "APEX_8w_open_30bps"})] + benchmark_records
    ]
    sub_rows = [
        {
            "periodo": r["period"],
            "strategia": r["variant"],
            "CAGR": f"{pct(r['cagr'])}%",
            "Max DD": f"{pct(r['max_drawdown'])}%",
            "Sharpe": round(float(r["sharpe"]), 3),
        }
        for _, r in subperiods.iterrows()
    ]
    claude_rows = [
        {
            "strategia": r["variant"],
            "inizio": r["start"],
            "fine": r["end"],
            "CAGR": f"{pct(r['cagr'])}%",
            "Max DD": f"{pct(r['max_drawdown'])}%",
            "Sharpe": round(float(r["sharpe"]), 3),
            "Finale 10k": round(float(r["final"]), 0),
        }
        for _, r in subperiods[subperiods["period"] == "claude_comparable_2018_now"].iterrows()
    ]
    claude_variant_rows = [
        {
            "strategia": r["label"],
            "CAGR": f"{pct(r['cagr'])}%",
            "Max DD": f"{pct(r['max_drawdown'])}%",
            "Sharpe": round(float(r["sharpe"]), 3),
            "Switch": int(r["switches"]),
            "Finale 10k": round(float(r["final"]), 0),
            "BTC%": f"{pct(r['exposure_btc'], 1)}%",
            "Cash%": f"{pct(r['exposure_cash'], 1)}%",
        }
        for _, r in claude_variants.sort_values(["sharpe", "cagr"], ascending=False).iterrows()
    ]
    yearly_rows = [
        {
            "anno": idx.year,
            "APEX": f"{pct(row['APEX_8w_open'])}%",
            "BTC": f"{pct(row['BTC_BH'])}%",
            "Equal": f"{pct(row['EQUAL_BH'])}%",
        }
        for idx, row in yearly.iterrows()
    ]
    lb_robust = []
    if not lb_sub.empty:
        grouped = lb_sub.groupby("lookback").agg(
            median_cagr=("cagr", "median"),
            min_cagr=("cagr", "min"),
            median_sharpe=("sharpe", "median"),
            worst_dd=("max_drawdown", "min"),
        ).reset_index()
        for _, r in grouped.sort_values(["median_sharpe", "median_cagr"], ascending=False).head(12).iterrows():
            lb_robust.append({
                "lookback": int(r["lookback"]),
                "median CAGR": f"{pct(r['median_cagr'])}%",
                "min CAGR": f"{pct(r['min_cagr'])}%",
                "median Sharpe": round(float(r["median_sharpe"]), 3),
                "worst DD": f"{pct(r['worst_dd'])}%",
            })
    walk_rows = [
        {
            "anno": int(r["year"]),
            "lb scelto": int(r["chosen_lookback"]),
            "WF": f"{pct(r['wf_return'])}%",
            "Static 8w": f"{pct(r['static8_return'])}%",
            "BTC": f"{pct(r['btc_return'])}%" if pd.notna(r.get("btc_return")) else "n/d",
            "WF DD": f"{pct(r['wf_max_dd'])}%",
        }
        for _, r in walk.iterrows()
    ]
    last_rows = [
        {
            "data": idx.date().isoformat(),
            "signal": row["signal"],
            "raw": row["raw_signal"],
            "BTC 8w": f"{row['ret_btc']:.2f}%",
            "Oro 8w": f"{row['ret_gold']:.2f}%",
            "SP 8w": f"{row['ret_sp500']:.2f}%",
            "cambio": "si" if row["changed"] else "no",
        }
        for idx, row in signal_tail.iterrows()
    ]

    report = f"""# APEX deep backtest - 2026-05-28

Stato: ricerca quantitativa, nessun deploy.

## Dati

- Fonte: Yahoo Finance chart API, profilo proxy EUR.
- BTC: `BTC-USD / EURUSD=X`.
- Oro: `GC=F / EURUSD=X`.
- S&P 500: `^GSPC / EURUSD=X`.
- Cash: `XEON.MI` quando disponibile.
- Osservazioni settimanali open: {len(rows_open)}.
- Periodo: {rows_open[0]["date"]} -> {rows_open[-1]["date"]}.
- Query Yahoo corretta con `period1/period2`; `range=max` puro veniva downsamplato a dati mensili.

Nota importante: per il segnale live Fineco useremo strumenti EUR/intraday. Il backtest lungo usa proxy per avere storia dal 2014; gli strumenti WisdomTree BTC quotati EUR su Yahoo non hanno storia sufficiente.

## Confronto Principale Allineato

Lookback 8 settimane, prezzo open, costo cambio 30 bps, stesso periodo di partenza per benchmark.

{table_md(bench_rows, ["strategia", "CAGR", "Max DD", "Sharpe", "Finale 10k"])}

Nota comparabilita': Claude parte dal 2018. Qui il capitale parte nel 2018, mentre lo storico pre-2018 serve solo a calcolare il primo momentum 8w disponibile.

## Confronto Claude 2018

Periodo richiesto: 2018-01-01 -> 2026-05-27. Benchmark allineati alle stesse date settimanali di APEX 8w/open/30bps.

{table_md(claude_rows, ["strategia", "inizio", "fine", "CAGR", "Max DD", "Sharpe", "Finale 10k"])}

Varianti candidate nello stesso periodo 2018-oggi. Questa tabella serve a capire se cambiare davvero regola o se tenere APEX 8w come base.

{table_md(claude_variant_rows, ["strategia", "CAGR", "Max DD", "Sharpe", "Switch", "Finale 10k", "BTC%", "Cash%"])}

## Scan Lookback

APEX Rev2 originale, prezzo open, costo 30 bps. Top 10 per CAGR.

{table_md(top_rows, ["lookback", "CAGR", "Max DD", "Sharpe", "Switch", "BTC%", "Cash%"])}

## Varianti

Prezzo open, costo 30 bps. Varianti ordinate per Sharpe/CAGR.

{table_md(variant_rows, ["variant", "lookback", "CAGR", "Max DD", "Sharpe", "Switch", "BTC%", "Cash%"])}

## Sottoperiodi

APEX 8w/open/30bps contro BTC buy&hold e paniere equal-weight, benchmark allineati al primo segnale del sottoperiodo.

{table_md(sub_rows, ["periodo", "strategia", "CAGR", "Max DD", "Sharpe"])}

## Robustezza Lookback Per Regime

APEX Rev2 originale, prezzo open, costo 30 bps. Classifica per mediana Sharpe/CAGR sui sottoperiodi, non sul periodo totale.

{table_md(lb_robust, ["lookback", "median CAGR", "min CAGR", "median Sharpe", "worst DD"])}

## Walk-Forward Annuale

Ogni anno sceglie il lookback migliore sui dati disponibili fino all'anno precedente, poi lo applica all'anno successivo. Confronto con 8w fisso e BTC buy&hold nello stesso anno.

{table_md(walk_rows, ["anno", "lb scelto", "WF", "Static 8w", "BTC", "WF DD"])}

## Rendimenti Annuali

{table_md(yearly_rows, ["anno", "APEX", "BTC", "Equal"])}

## Ultimi Segnali

{table_md(last_rows, ["data", "signal", "raw", "BTC 8w", "Oro 8w", "SP 8w", "cambio"])}

## Lettura Tecnica

1. Il lookback 8w resta la base piu pulita e coerente con APEX Rev2, ma non e' il vincitore unico in ogni metrica.
2. Nel confronto 2018 richiesto, `Buffer 2pp 6w` e `Confirm2 6w` battono nettamente l'8w originale; sono candidati veri, non rumore da ignorare.
3. Non li adotterei automaticamente: aggiungono regole, riducono o spostano alcuni drawdown, ma possono essere piu ottimizzati sul periodo 2018-oggi.
4. La versione pure-relative, dove S&P 500 puo battere direttamente BTC, migliora alcune metriche ma cambia l'identita BTC-centrica della strategia. La terrei fuori salvo scelta esplicita.
5. Il lookback 17w e' il migliore sul periodo pieno per CAGR, ma sul confronto 2018 va molto peggio: e' un segnale forte contro l'overfitting.
6. Il drawdown resta enorme: APEX riduce il drawdown rispetto a BTC buy&hold, ma resta una strategia aggressiva.
7. Raccomandazione provvisoria: implementare APEX 8w come versione base verificabile, e affiancare in app una simulazione non-operativa `6w + filtro` per decidere con dati live prima di cambiare regola.

## File Generati

- `output/apex_deep_grid.csv`
- `output/apex_deep_variants.csv`
- `output/apex_deep_claude2018_variants.csv`
- `output/apex_deep_benchmarks.csv`
- `output/apex_deep_subperiods.csv`
- `output/apex_deep_yearly.csv`
- `output/apex_deep_last_signals.csv`
- `output/apex_deep_results.json`
"""
    DOC_PATH.write_text(report, encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str))
    print(f"Saved {DOC_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
