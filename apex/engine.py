from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional

import pandas as pd

from apex.config import LOOKBACK_WEEKS, SIGNAL_WEEKDAY


ASSET_ORDER = ("BTC", "GOLD", "SP500")


@dataclass(frozen=True)
class ApexSignal:
    date: date
    signal: str
    ret_btc: float
    ret_gold: float
    ret_sp500: float
    changed: bool
    previous_signal: Optional[str]
    reason: str


def _as_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return datetime.fromisoformat(str(value)[:10]).date()


def _signal_from_returns(ret_btc: float, ret_gold: float, ret_sp500: float) -> tuple[str, str]:
    """Pure APEX-4 Rev2 priority rule.

    BTC competes only against gold in the first branch. SP500 never directly
    beats BTC if BTC is positive and at least as strong as gold.
    """
    if ret_btc > 0 and ret_btc >= ret_gold:
        return "BTC", "BTC positivo e maggiore/uguale a Oro"
    if ret_gold > 0 and ret_gold > ret_sp500:
        return "GOLD", "Oro positivo e migliore di S&P 500"
    if ret_sp500 > 0 and ret_sp500 > ret_gold:
        return "SP500", "S&P 500 positivo e migliore di Oro"
    return "CASH", "Nessun asset qualifica con momentum positivo"


def compute_signal(
    observations: Iterable[Dict],
    lookback_weeks: int = LOOKBACK_WEEKS,
    previous_signal: Optional[str] = None,
) -> ApexSignal:
    rows = sorted(list(observations), key=lambda r: _as_date(r["date"]))
    if len(rows) < lookback_weeks + 1:
        raise ValueError(f"servono almeno {lookback_weeks + 1} osservazioni settimanali")

    cur = rows[-1]
    prev = rows[-1 - lookback_weeks]
    ret_btc = float(cur["BTC"]) / float(prev["BTC"]) - 1.0
    ret_gold = float(cur["GOLD"]) / float(prev["GOLD"]) - 1.0
    ret_sp500 = float(cur["SP500"]) / float(prev["SP500"]) - 1.0
    signal, reason = _signal_from_returns(ret_btc, ret_gold, ret_sp500)
    if previous_signal is None and len(rows) >= lookback_weeks + 2:
        old = compute_signal(rows[:-1], lookback_weeks=lookback_weeks, previous_signal=None)
        previous_signal = old.signal
    return ApexSignal(
        date=_as_date(cur["date"]),
        signal=signal,
        ret_btc=ret_btc,
        ret_gold=ret_gold,
        ret_sp500=ret_sp500,
        changed=(previous_signal is not None and signal != previous_signal),
        previous_signal=previous_signal,
        reason=reason,
    )


def compute_signal_series(observations: Iterable[Dict], lookback_weeks: int = LOOKBACK_WEEKS) -> List[ApexSignal]:
    rows = sorted(list(observations), key=lambda r: _as_date(r["date"]))
    out: List[ApexSignal] = []
    prev_signal: Optional[str] = None
    for i in range(lookback_weeks, len(rows)):
        sig = compute_signal(rows[: i + 1], lookback_weeks=lookback_weeks, previous_signal=prev_signal)
        out.append(sig)
        prev_signal = sig.signal
    return out


def select_weekly_observations(
    prices: pd.DataFrame,
    weekday: int = SIGNAL_WEEKDAY,
) -> List[Dict]:
    """Select one observation per ISO week.

    For the Wednesday-morning version, if Wednesday is missing in a week, use
    the closest available prior trading day in the same week. If the week has
    only later dates, use the first available date and mark the week anyway.
    """
    required = set(ASSET_ORDER)
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"missing price columns: {sorted(missing)}")

    df = prices.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df = df[list(ASSET_ORDER) + (["CASH"] if "CASH" in df.columns else [])].dropna(subset=list(ASSET_ORDER))

    rows: List[Dict] = []
    for _, week in df.groupby([df.index.isocalendar().year, df.index.isocalendar().week]):
        week = week.sort_index()
        target_dates = [idx for idx in week.index if idx.weekday() <= weekday]
        chosen_idx = target_dates[-1] if target_dates else week.index[0]
        row = week.loc[chosen_idx]
        obs = {"date": chosen_idx.date()}
        for col in row.index:
            obs[col] = float(row[col])
        rows.append(obs)
    return rows


def backtest_rotation(
    observations: Iterable[Dict],
    cost_bps: float = 30.0,
    initial_value: float = 10000.0,
    lookback_weeks: int = LOOKBACK_WEEKS,
) -> pd.DataFrame:
    rows = sorted(list(observations), key=lambda r: _as_date(r["date"]))
    if len(rows) < lookback_weeks + 2:
        raise ValueError("dati insufficienti per backtest")

    signals = compute_signal_series(rows, lookback_weeks=lookback_weeks)
    by_date = {_as_date(r["date"]): r for r in rows}
    value = initial_value
    current: Optional[str] = None
    records = []
    sig_by_date = {s.date: s for s in signals}
    signal_dates = [s.date for s in signals]

    for idx, d in enumerate(signal_dates[:-1]):
        sig = sig_by_date[d]
        next_d = signal_dates[idx + 1]
        row = by_date[d]
        nxt = by_date[next_d]
        if current != sig.signal:
            value *= 1.0 - cost_bps / 10000.0
            current = sig.signal
        if current == "CASH":
            if "CASH" in row and "CASH" in nxt and row["CASH"] > 0:
                period_ret = float(nxt["CASH"]) / float(row["CASH"]) - 1.0
            else:
                period_ret = 0.0
        else:
            period_ret = float(nxt[current]) / float(row[current]) - 1.0
        value *= 1.0 + period_ret
        records.append({
            "date": d,
            "next_date": next_d,
            "signal": sig.signal,
            "changed": sig.changed,
            "value": value,
            "period_ret": period_ret,
            "ret_btc": sig.ret_btc,
            "ret_gold": sig.ret_gold,
            "ret_sp500": sig.ret_sp500,
        })
    return pd.DataFrame(records).set_index("date")


def buy_and_hold(observations: Iterable[Dict], asset: str, initial_value: float = 10000.0) -> pd.Series:
    rows = sorted(list(observations), key=lambda r: _as_date(r["date"]))
    base = float(rows[0][asset])
    return pd.Series(
        [initial_value * float(r[asset]) / base for r in rows],
        index=pd.to_datetime([_as_date(r["date"]) for r in rows]),
        name=asset,
    )


def equal_weight_bh(
    observations: Iterable[Dict],
    assets: Iterable[str] = ASSET_ORDER,
    initial_value: float = 10000.0,
) -> pd.Series:
    parts = [buy_and_hold(observations, a, initial_value / len(tuple(assets))) for a in assets]
    out = sum(parts)
    out.name = "EQUAL"
    return out


def performance_stats(equity: pd.Series | pd.DataFrame) -> Dict[str, float]:
    if isinstance(equity, pd.DataFrame):
        if "value" in equity.columns:
            s = equity["value"]
        else:
            s = equity.iloc[:, 0]
    else:
        s = equity
    s = s.dropna()
    if len(s) < 2:
        return {}
    weekly = s.pct_change().dropna()
    years = max((s.index[-1] - s.index[0]).days / 365.25, 1 / 52)
    cagr = (s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1
    drawdown = s / s.cummax() - 1
    vol = weekly.std() * (52 ** 0.5) if len(weekly) else 0.0
    sharpe = (weekly.mean() * 52) / vol if vol else 0.0
    start = _as_date(s.index[0]).isoformat()
    end = _as_date(s.index[-1]).isoformat()
    return {
        "start": start,
        "end": end,
        "final": float(s.iloc[-1]),
        "total_return": float(s.iloc[-1] / s.iloc[0] - 1),
        "cagr": float(cagr),
        "max_drawdown": float(drawdown.min()),
        "volatility": float(vol),
        "sharpe": float(sharpe),
    }
