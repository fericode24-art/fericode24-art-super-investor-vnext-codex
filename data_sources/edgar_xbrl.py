"""
EDGAR XBRL CompanyFacts — fondamentali ufficiali SEC.

Endpoint: https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json
API ufficiale, gratuita, affidabile. User-Agent obbligatorio.

get_fundamentals(ticker) ritorna un dict con i dati per:
  - Quality score (ROE, ROA, margini, debt/equity, ROE trend 4q)
  - Quality Red Flags (FCF, diluizione azioni, revenue collapse, debt/EBITDA)
Ritorna None se il ticker non è mappabile a CIK o XBRL non disponibile.

NOTA: i dati cash-flow XBRL nei 10-Q sono spesso cumulativi YTD. Per i red flag
usiamo serie ANNUALI (10-K) che sono pulite; il flag "FCF cronico" approssima
'4 quarter negativi' con '2 anni fiscali negativi consecutivi' (documentato).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional
import requests

HEADERS = {"User-Agent": "SuperInvestor Federico fedezebi@gmail.com",
           "Accept-Encoding": "gzip, deflate"}
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "xbrl_cache"

_LAST_CALL = 0.0
_MIN_INTERVAL = 0.12


def _throttle():
    global _LAST_CALL
    elapsed = time.time() - _LAST_CALL
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _LAST_CALL = time.time()


def _fetch_companyfacts(cik: str) -> Optional[dict]:
    """Scarica companyfacts XBRL, con cache su disco 7 giorni."""
    cik_z = str(int(cik)).zfill(10)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{cik_z}.json"
    if cache_file.exists():
        age_days = (time.time() - cache_file.stat().st_mtime) / 86400
        if age_days < 7:
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    try:
        _throttle()
        r = requests.get(FACTS_URL.format(cik=cik_z), headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return None
        data = r.json()
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return data
    except Exception:
        return None


# ─────────────────────────── estrazione fatti ───────────────────────────
def _concept(facts: dict, taxonomy: str, name: str) -> Optional[dict]:
    return facts.get(taxonomy, {}).get(name)


def _series(facts: dict, names: list[str], unit_pref: list[str], annual_only: bool = False) -> list[dict]:
    """
    Ritorna la lista di fatti per il primo concept trovato, DEDUPLICATA per periodo.
    Le società ridichiarano lo stesso anno in 10-K successivi (comparativi) → teniamo
    un solo fatto per 'end' date, quello del filing più recente.
    annual_only=True filtra solo i 10-K.
    """
    for tax in ("us-gaap", "ifrs-full"):
        for nm in names:
            c = _concept(facts, tax, nm)
            if not c:
                continue
            units = c.get("units", {})
            for u in unit_pref:
                if u in units:
                    items = [it for it in units[u] if it.get("end")]
                    if annual_only:
                        items = [it for it in items if it.get("form") == "10-K"]
                    if not items:
                        continue
                    # dedup per 'end': tieni il fatto col 'filed' più recente
                    by_end = {}
                    for it in items:
                        end = it["end"]
                        prev = by_end.get(end)
                        if prev is None or (it.get("filed", "") > prev.get("filed", "")):
                            by_end[end] = it
                    deduped = sorted(by_end.values(), key=lambda x: x["end"])
                    if deduped:
                        return deduped
    return []


def _latest(facts: dict, names: list[str], unit_pref: list[str], annual_only: bool = False):
    s = _series(facts, names, unit_pref, annual_only)
    return s[-1]["val"] if s else None


def get_fundamentals(ticker_or_cik, ticker_map: Optional[dict] = None) -> Optional[dict]:
    """
    Ritorna dict fondamentali da XBRL. ticker_map: {ticker: cik} (da sec_edgar.load_ticker_map).
    """
    cik = None
    arg = str(ticker_or_cik)
    if arg.isdigit() or arg.startswith("000"):
        cik = arg
    elif ticker_map:
        info = ticker_map.get(arg.upper())
        if info:
            cik = info.get("cik")
    if not cik:
        return None

    data = _fetch_companyfacts(cik)
    if not data:
        return None
    facts = data.get("facts", {})
    if not facts:
        return None

    USD = ["USD"]
    SHARES = ["shares"]

    # --- valori puntuali / annuali ---
    net_income = _latest(facts, ["NetIncomeLoss", "ProfitLoss"], USD, annual_only=True)
    revenue_series = _series(facts, [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues", "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet"], USD, annual_only=True)
    equity = _latest(facts, ["StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"], USD)
    assets = _latest(facts, ["Assets"], USD)
    gross_profit = _latest(facts, ["GrossProfit"], USD, annual_only=True)
    op_income = _latest(facts, ["OperatingIncomeLoss"], USD, annual_only=True)
    lt_debt = _latest(facts, ["LongTermDebtNoncurrent", "LongTermDebt"], USD)
    interest_exp = _latest(facts, ["InterestExpense",
        "InterestExpenseDebt"], USD, annual_only=True)

    # --- shares outstanding (per diluizione) ---
    shares_series = _series(facts, ["CommonStockSharesOutstanding",
        "EntityCommonStockSharesOutstanding"], SHARES)
    shares_now = shares_series[-1]["val"] if shares_series else None
    shares_12m_ago = None
    if shares_series and shares_now:
        last_end = shares_series[-1]["end"]
        for it in reversed(shares_series[:-1]):
            # cerca un dato ~1 anno prima
            if it["end"][:4] != last_end[:4]:
                shares_12m_ago = it["val"]
                break

    # --- FCF annuale (operating CF - capex) ---
    ocf_series = _series(facts, ["NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
        USD, annual_only=True)
    capex_series = _series(facts, ["PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsForCapitalImprovements"], USD, annual_only=True)
    fcf_annual = []
    capex_by_year = {it["end"][:4]: it["val"] for it in capex_series}
    for it in ocf_series:
        yr = it["end"][:4]
        capex = capex_by_year.get(yr, 0)
        fcf_annual.append({"year": yr, "fcf": it["val"] - capex})

    # --- revenue YoY ---
    revenue_yoy = None
    if len(revenue_series) >= 2:
        cur, prev = revenue_series[-1]["val"], revenue_series[-2]["val"]
        if prev and prev != 0:
            revenue_yoy = (cur - prev) / abs(prev)

    # --- ROE / ROA ---
    roe = (net_income / equity) if (net_income and equity and equity != 0) else None
    roa = (net_income / assets) if (net_income and assets and assets != 0) else None

    # --- margini ---
    rev_latest = revenue_series[-1]["val"] if revenue_series else None
    gross_margin = (gross_profit / rev_latest) if (gross_profit and rev_latest) else None
    op_margin = (op_income / rev_latest) if (op_income and rev_latest) else None
    net_margin = (net_income / rev_latest) if (net_income and rev_latest) else None

    # --- debt/equity, debt/EBITDA ---
    debt_to_equity = (lt_debt / equity * 100) if (lt_debt and equity and equity > 0) else None
    ebitda_approx = None
    if op_income is not None:
        dep = _latest(facts, ["DepreciationDepletionAndAmortization",
            "DepreciationAmortizationAndAccretionNet", "DepreciationAndAmortization"],
            USD, annual_only=True) or 0
        ebitda_approx = op_income + dep
    debt_to_ebitda = (lt_debt / ebitda_approx) if (lt_debt and ebitda_approx and ebitda_approx > 0) else None

    # --- interest coverage ---
    interest_coverage = None
    if op_income is not None and interest_exp and interest_exp > 0:
        interest_coverage = op_income / interest_exp

    # --- ROE trend 4 periodi (annuali) ---
    roe_trend = None
    eq_series = _series(facts, ["StockholdersEquity"], USD)
    ni_series = _series(facts, ["NetIncomeLoss"], USD, annual_only=True)
    if len(ni_series) >= 4 and eq_series:
        # roe per ognuno degli ultimi 4 anni (approssima equity con il più vicino)
        roes = []
        for ni in ni_series[-4:]:
            yr = ni["end"][:4]
            eq = next((e["val"] for e in reversed(eq_series) if e["end"][:4] == yr), None)
            if eq and eq != 0:
                roes.append(ni["val"] / eq)
        if len(roes) >= 3:
            roe_trend = "rising" if roes[-1] > roes[0] else ("declining" if roes[-1] < roes[0] else "flat")

    return {
        "cik": str(int(cik)).zfill(10),
        "source": "edgar_xbrl",
        "roe": roe, "roa": roa,
        "gross_margin": gross_margin, "operating_margin": op_margin, "net_margin": net_margin,
        "debt_to_equity": debt_to_equity,
        "debt_to_ebitda": debt_to_ebitda,
        "interest_coverage": interest_coverage,
        "revenue_growth_yoy": revenue_yoy,
        "shares_outstanding": shares_now,
        "shares_outstanding_12m_ago": shares_12m_ago,
        "fcf_annual": fcf_annual,            # [{year, fcf}]
        "fcf_negative_years": sum(1 for x in fcf_annual[-2:] if x["fcf"] < 0),
        "roe_trend_4y": roe_trend,
        "years_available": len(revenue_series),
        "going_concern_flag": False,         # raramente taggato in XBRL; veto da text 10-K [non implementato]
    }


def batch_fundamentals(tickers: list[str], ticker_map: dict, throttle: float = 0.12) -> dict:
    """Fondamentali XBRL per una lista di ticker."""
    out = {}
    for t in tickers:
        out[t] = get_fundamentals(t, ticker_map)
        time.sleep(throttle)
    return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from engine import sec_edgar
    tmap = sec_edgar.load_ticker_map()
    t = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    print(json.dumps(get_fundamentals(t, tmap), indent=2, default=str))
