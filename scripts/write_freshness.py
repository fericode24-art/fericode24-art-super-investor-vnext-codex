from __future__ import annotations
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard"
HOLIDAYS = {
    "2026-01-01","2026-01-19","2026-02-16","2026-04-03","2026-05-25","2026-06-19","2026-07-03","2026-09-07","2026-11-26","2026-12-25",
    "2027-01-01","2027-01-18","2027-02-15","2027-03-26","2027-05-31","2027-06-18","2027-07-05","2027-09-06","2027-11-25","2027-12-24",
    "2028-01-17","2028-02-21","2028-04-14","2028-05-29","2028-06-19","2028-07-04","2028-09-04","2028-11-23","2028-12-25",
    "2029-01-01","2029-01-15","2029-02-19","2029-03-30","2029-05-28","2029-06-19","2029-07-04","2029-09-03","2029-11-22","2029-12-25",
    "2030-01-01","2030-01-21","2030-02-18","2030-04-19","2030-05-27","2030-06-19","2030-07-04","2030-09-02","2030-11-28","2030-12-25",
}

def is_trading_day(d):
    return d.weekday() < 5 and d.isoformat() not in HOLIDAYS

def previous_trading_day(d):
    x = d
    while True:
        x = x - timedelta(days=1)
        if is_trading_day(x):
            return x

def expected_signal_date(now=None):
    now = now or datetime.now(ZoneInfo("Europe/Rome"))
    d = now.date()
    if is_trading_day(d) and (now.hour * 60 + now.minute) >= 9 * 60 + 15:
        return d
    return previous_trading_day(d)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    src = DASH / "data-octa.json"
    data = json.loads(src.read_text(encoding="utf-8")) if src.exists() else {}
    sig = data.get("signal_date") or data.get("last_success_run")
    exp = expected_signal_date()
    fresh = bool(sig and sig >= exp.isoformat() and not data.get("engine_error"))
    out = {
        "generated_at": datetime.now(ZoneInfo("Europe/Rome")).isoformat(timespec="seconds"),
        "signal_date": sig,
        "expected_signal_date": exp.isoformat(),
        "fresh": fresh,
        "engine_error": bool(data.get("engine_error")),
        "updated": data.get("updated"),
        "signals": len(data.get("signals", [])),
        "message": "fresh" if fresh else "stale_or_error",
    }
    (DASH / "freshness.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(out, indent=2))
    if args.strict and not fresh:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
