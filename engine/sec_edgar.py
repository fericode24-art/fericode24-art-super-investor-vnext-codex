"""
SEC EDGAR fetcher per 13F, Form 4 e 13D/G filings.

L'API EDGAR è gratuita, pubblica, no auth richiesta.
Unico requisito: User-Agent identificativo (regola SEC).

Endpoints utili:
- https://data.sec.gov/submissions/CIK{cik}.json     → lista filings di un CIK
- https://www.sec.gov/cgi-bin/browse-edgar?...        → ricerca via testo
- https://www.sec.gov/Archives/edgar/data/{cik}/...   → documenti grezzi
"""
from __future__ import annotations

import json
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import requests
from bs4 import BeautifulSoup


# SEC richiede uno User-Agent identificativo; cambiare con email reale in produzione
USER_AGENT = "Super Investor Dashboard fedez@example.com"
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}

BASE_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVES = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{filename}"
COMPANY_TICKERS = "https://www.sec.gov/files/company_tickers.json"


# --- Rate limiting (SEC: max 10 req/s) -----------------------------------------
_LAST_CALL_AT = 0.0
_MIN_INTERVAL = 0.12  # 8 req/s, conservativo


def _throttle():
    global _LAST_CALL_AT
    elapsed = time.time() - _LAST_CALL_AT
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _LAST_CALL_AT = time.time()


def _get(url: str) -> requests.Response:
    _throttle()
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r


# --- Ticker / CIK lookup -------------------------------------------------------
_TICKER_MAP: Optional[dict] = None


def load_ticker_map() -> dict:
    """Mappa ticker → CIK pubblicata da SEC."""
    global _TICKER_MAP
    if _TICKER_MAP is None:
        r = _get(COMPANY_TICKERS)
        raw = r.json()
        _TICKER_MAP = {
            entry["ticker"].upper(): {
                "cik": str(entry["cik_str"]).zfill(10),
                "name": entry["title"],
            }
            for entry in raw.values()
        }
    return _TICKER_MAP


def cik_to_ticker(cik: str) -> Optional[str]:
    cik_z = str(int(cik)).zfill(10)
    for t, info in load_ticker_map().items():
        if info["cik"] == cik_z:
            return t
    return None


# --- Submissions ---------------------------------------------------------------
def get_submissions(cik: str) -> dict:
    """Lista tutti i filing recenti di un CIK."""
    cik_z = str(int(cik)).zfill(10)
    r = _get(BASE_SUBMISSIONS.format(cik=cik_z))
    return r.json()


def latest_filings(cik: str, form_types: list[str], limit: int = 5) -> list[dict]:
    """Filtra i filing per tipo (es. '13F-HR', '4', 'SC 13D', 'SC 13G')."""
    sub = get_submissions(cik)
    recent = sub.get("filings", {}).get("recent", {})
    if not recent:
        return []

    forms = recent.get("form", [])
    accs = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])
    primary = recent.get("primaryDocument", [])

    out = []
    for i, form in enumerate(forms):
        if form in form_types:
            out.append({
                "form": form,
                "accession": accs[i],
                "date": dates[i],
                "primary_doc": primary[i],
            })
            if len(out) >= limit:
                break
    return out


# --- 13F parser ----------------------------------------------------------------
def _parse_13f_filing(cik: str, filing: dict) -> Optional[dict]:
    """
    Parsa un singolo 13F-HR. v2.2: estrae anche putCall e sshPrnamtType
    (necessari per il filtro long-only su Situational Awareness/Aschenbrenner).
    """
    cik_z = str(int(cik)).zfill(10)
    accession_nodash = filing["accession"].replace("-", "")
    base_dir = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_nodash}/"
    try:
        index_json = _get(base_dir + "index.json").json()
    except Exception:
        return None

    # NB: l'estensione XML può essere maiuscola o minuscola (es. MSFS13F033126.XML)
    info_table_file = None
    for item in index_json.get("directory", {}).get("item", []):
        name = item.get("name", "")
        nl = name.lower()
        if nl.endswith(".xml") and ("infotable" in nl or "info_table" in nl or "form13finfotable" in nl):
            info_table_file = name
            break
    if not info_table_file:
        for item in index_json.get("directory", {}).get("item", []):
            name = item.get("name", "")
            nl = name.lower()
            if nl.endswith(".xml") and "primary_doc" not in nl:
                info_table_file = name
                break
    if not info_table_file:
        return None

    xml = _get(base_dir + info_table_file).text
    soup = BeautifulSoup(xml, "lxml-xml")

    holdings = []
    total_value = 0
    for entry in soup.find_all("infoTable"):
        try:
            cusip = entry.find("cusip").text.strip()
            value = int(entry.find("value").text.strip())
            shares = int(entry.find("sshPrnamt").text.strip())
            name = entry.find("nameOfIssuer").text.strip()
            # v2.2: putCall + tipo (SH/PRN) per filtro long-only
            put_call_el = entry.find("putCall")
            put_call = put_call_el.text.strip() if put_call_el else ""
            sh_type_el = entry.find("sshPrnamtType")
            sh_type = sh_type_el.text.strip() if sh_type_el else "SH"
            total_value += value
            holdings.append({
                "cusip": cusip,
                "issuer": name,
                "value_usd": value,
                "shares": shares,
                "put_call": put_call,        # "" | "Put" | "Call"
                "sh_prn_type": sh_type,      # "SH" | "PRN"
            })
        except Exception:
            continue

    for h in holdings:
        h["pct_of_portfolio"] = (h["value_usd"] / total_value * 100) if total_value else 0

    return {
        "date": filing["date"],
        "cik": cik_z,
        "total_value_usd": total_value,
        "n_holdings": len(holdings),
        "holdings": holdings,
    }


def fetch_13f_holdings(cik: str) -> Optional[dict]:
    """Scarica e parsa l'ULTIMO 13F-HR di un fondo (backward compatible)."""
    filings = latest_filings(cik, ["13F-HR", "13F-HR/A"], limit=1)
    if not filings:
        return None
    return _parse_13f_filing(cik, filings[0])


def fetch_13f_with_previous(cik: str) -> dict:
    """
    v2.2 — Scarica gli ULTIMI DUE 13F-HR di un fondo (corrente + precedente).
    Necessario per l'Accumulation Trend (confronto size posizioni QoQ).
    Ritorna: {'current': {...} | None, 'previous': {...} | None}
    Salta i 13F-HR/A (amendment) per evitare doppioni dello stesso quarter.
    """
    filings = latest_filings(cik, ["13F-HR"], limit=3)
    out = {"current": None, "previous": None}
    if not filings:
        # fallback: includi anche gli amendment se non ci sono HR puri
        filings = latest_filings(cik, ["13F-HR", "13F-HR/A"], limit=3)
    if not filings:
        return out
    out["current"] = _parse_13f_filing(cik, filings[0])
    if len(filings) >= 2:
        out["previous"] = _parse_13f_filing(cik, filings[1])
    return out


# --- Form 4 (insider buying) ---------------------------------------------------
def fetch_recent_form4(ticker: str, days_back: int = 60) -> list[dict]:
    """
    Form 4 di un'azienda (insider transactions).
    Cerca via CIK dell'emittente.
    """
    tmap = load_ticker_map()
    if ticker.upper() not in tmap:
        return []
    cik = tmap[ticker.upper()]["cik"]
    filings = latest_filings(cik, ["4"], limit=30)
    cutoff = datetime.now() - timedelta(days=days_back)
    out = []
    for f in filings:
        try:
            fdate = datetime.fromisoformat(f["date"])
        except Exception:
            continue
        if fdate < cutoff:
            continue
        # NB: parsing dettagliato del Form 4 XML è complesso; qui contiamo solo
        # numero di filing recenti come proxy di attività insider
        out.append(f)
    return out


def insider_signal(ticker: str) -> dict:
    """
    Ritorna un signal score 0-100 basato sulla frequenza di Form 4 recenti.
    Una versione più sofisticata parserebbe gli XML per separare BUY da SELL.
    """
    recent = fetch_recent_form4(ticker, days_back=60)
    n = len(recent)
    # threshold semplice; sopra 10 filings = forte attività
    score = min(100, n * 10)
    return {"n_recent_form4": n, "score": score}


# --- 13D / 13G (>5% stakes) ----------------------------------------------------
def fetch_recent_13dg(cik: str, days_back: int = 90) -> list[dict]:
    """Filing SC 13D/13G recenti indicizzati su un CIK (filer o subject company)."""
    filings = latest_filings(cik, ["SC 13D", "SC 13G", "SC 13D/A", "SC 13G/A"], limit=20)
    cutoff = datetime.now() - timedelta(days=days_back)
    out = []
    for f in filings:
        try:
            fdate = datetime.fromisoformat(f["date"])
        except Exception:
            continue
        if fdate >= cutoff:
            out.append(f)
    return out


# NOTA v2.3: un modifier "attivista 13D/13G" è stato valutato ma NON integrato.
# Gli attivisti depositano i 13D sotto entità/CIK diversi dal filer 13F
# (frammentazione per campagna) → un tracking affidabile richiede un database
# multi-entità dedicato, fuori scope. fetch_recent_13dg resta disponibile come
# fetcher base. Lo scoring (stage1) mantiene il MECCANISMO del modifier attivista,
# semplicemente non alimentato.


# --- CUSIP → Ticker mapping (best effort) --------------------------------------
def cusip_to_ticker_best_effort(cusip: str, issuer_name: str) -> Optional[str]:
    """
    Non esiste un endpoint pubblico SEC per CUSIP→ticker.
    Strategia: fuzzy match del nome emittente contro company_tickers.
    """
    tmap = load_ticker_map()
    issuer_norm = re.sub(r"[^A-Z ]", "", issuer_name.upper()).strip()
    # match esatto
    for t, info in tmap.items():
        if info["name"].upper() == issuer_norm:
            return t
    # match prefisso (primo word)
    first_word = issuer_norm.split(" ")[0] if issuer_norm else ""
    if len(first_word) >= 4:
        for t, info in tmap.items():
            if info["name"].upper().startswith(first_word):
                return t
    return None


# --- CLI debug ----------------------------------------------------------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python sec_edgar.py <CIK or ticker>")
        sys.exit(1)
    arg = sys.argv[1]
    if arg.isdigit() or arg.startswith("000"):
        result = fetch_13f_holdings(arg)
        print(json.dumps(result, indent=2)[:2000] if result else "No 13F found")
    else:
        tmap = load_ticker_map()
        print(tmap.get(arg.upper(), "Not found"))
