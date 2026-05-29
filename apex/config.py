from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class ApexAsset:
    code: str
    label: str
    product: str
    isin: str
    fineco_hint: str
    yahoo_live: Tuple[str, ...]
    yahoo_proxy: str | None
    tax_bucket: str
    ter: float | None


ASSETS: Dict[str, ApexAsset] = {
    "BTC": ApexAsset(
        code="BTC",
        label="Bitcoin",
        product="WisdomTree Physical Bitcoin",
        isin="GB00BJYDH287",
        fineco_hint="WBTC su Borsa Italiana / WBIT su Xetra; Yahoo usa WBTC.PA come proxy EUR dello stesso ISIN",
        yahoo_live=("WBTC.PA", "BTC-USD"),
        yahoo_proxy="BTC-USD",
        tax_bucket="redditi_diversi_etp",
        ter=0.0015,
    ),
    "GOLD": ApexAsset(
        code="GOLD",
        label="Oro",
        product="iShares Physical Gold ETC",
        isin="IE00B4ND3602",
        fineco_hint="SGLN.MI su Borsa Italiana / PPFB.DE su Xetra",
        yahoo_live=("SGLN.MI", "PPFB.DE", "GC=F"),
        yahoo_proxy="GC=F",
        tax_bucket="redditi_diversi_etc",
        ter=0.0012,
    ),
    "SP500": ApexAsset(
        code="SP500",
        label="S&P 500",
        product="iShares Core S&P 500 UCITS ETF USD (Acc)",
        isin="IE00B5BMR087",
        fineco_hint="CSSPX.MI su Borsa Italiana / SXR8.DE su Xetra",
        yahoo_live=("CSSPX.MI", "SXR8.DE", "^GSPC"),
        yahoo_proxy="^GSPC",
        tax_bucket="redditi_capitale_ucits",
        ter=0.0007,
    ),
    "CASH": ApexAsset(
        code="CASH",
        label="Cash",
        product="Xtrackers II EUR Overnight Rate Swap UCITS ETF 1C",
        isin="LU0290358497",
        fineco_hint="XEON.MI su Borsa Italiana / XEON.DE su Xetra",
        yahoo_live=("XEON.MI", "XEON.DE"),
        yahoo_proxy=None,
        tax_bucket="redditi_capitale_ucits",
        ter=0.0010,
    ),
}


LOOKBACK_WEEKS = 8
DEFAULT_SWAP_COST_BPS = 30.0
SIGNAL_WEEKDAY = 2  # Python: Monday=0, Wednesday=2.
LIVE_RUN_TIME_ROME = "09:45"

