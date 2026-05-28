"""Loader centralizzato per config.yaml."""
from __future__ import annotations

import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_CONFIG = None


def load_config() -> dict:
    """Carica (e memoizza) config.yaml."""
    global _CONFIG
    if _CONFIG is None:
        with open(ROOT / "config.yaml", "r", encoding="utf-8") as f:
            _CONFIG = yaml.safe_load(f)
    return _CONFIG


def clip(x: float, lo: float, hi: float) -> float:
    """Helper: limita x in [lo, hi]."""
    return max(lo, min(hi, x))


def normalize_0_100(values: dict) -> dict:
    """Min-max normalization di un dict {key: value} su scala 0-100."""
    if not values:
        return {}
    vals = list(values.values())
    mx, mn = max(vals), min(vals)
    rng = (mx - mn) or 1.0
    return {k: round((v - mn) / rng * 100, 2) for k, v in values.items()}
