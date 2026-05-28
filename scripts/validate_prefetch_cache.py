from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"{path.as_posix()} non generato")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path.as_posix()} non e' JSON valido: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{path.as_posix()} deve essere un oggetto ticker -> dati")
    return data


def _validate_insider(data: dict[str, Any]) -> list[str]:
    required = {"ts", "net_value_usd", "net_shares", "n_transactions", "n_10b51_excluded"}
    issues: list[str] = []
    for ticker, row in list(data.items())[:500]:
        if not isinstance(row, dict):
            issues.append(f"{ticker}: record non oggetto")
            continue
        missing = required - set(row)
        if missing:
            issues.append(f"{ticker}: campi mancanti {sorted(missing)}")
    return issues


def _validate_earnings(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for ticker, row in list(data.items())[:500]:
        if not isinstance(row, dict):
            issues.append(f"{ticker}: record non oggetto")
            continue
        if not isinstance(row.get("earnings_dates"), list):
            issues.append(f"{ticker}: earnings_dates mancante o non lista")
    return issues


def _validate_market(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    tickers = data.get("tickers")
    if not isinstance(tickers, dict):
        return ["tickers mancante o non oggetto"]
    for ticker, row in list(tickers.items())[:500]:
        if not isinstance(row, dict):
            issues.append(f"{ticker}: record non oggetto")
            continue
        if "congressional_score" not in row:
            issues.append(f"{ticker}: congressional_score mancante")
        if "short_interest_pct" not in row:
            issues.append(f"{ticker}: short_interest_pct mancante")
    return issues


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["insider", "earnings", "market"])
    parser.add_argument("--min-items", type=int, default=1)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    filename = "market_signal_cache.json" if args.kind == "market" else f"{args.kind}_cache.json"
    cache_path = ROOT / "data" / "backtest" / filename
    data = _load_json(cache_path)
    count = len(data.get("tickers", {})) if args.kind == "market" else len(data)
    if count < args.min_items:
        raise SystemExit(
            f"{cache_path.as_posix()} contiene {count} ticker, minimo atteso {args.min_items}"
        )

    if args.kind == "insider":
        issues = _validate_insider(data)
    elif args.kind == "earnings":
        issues = _validate_earnings(data)
    else:
        issues = _validate_market(data)
    if issues:
        raise SystemExit("Cache non valida:\n" + "\n".join(issues[:20]))

    keys = list(data.get("tickers", data))[:8]
    sample = ", ".join(keys)
    print(f"OK {args.kind} cache: {count} ticker")
    if args.summary:
        title = {
            "insider": "Insider Form 4",
            "earnings": "Earnings 8-K",
            "market": "Market shadow",
        }[args.kind]
        print(f"## OCTA vNext {title} prefetch")
        print(f"- Ticker in cache: {count}")
        print(f"- Sample: {sample or 'n/d'}")


if __name__ == "__main__":
    main()
