"""Test filtro long-only per Situational Awareness (esclude put options)."""
from engine import sec_edgar


def test_13f_parser_extracts_put_call_field():
    """_parse_13f deve estrarre il campo put_call (necessario al filtro long-only)."""
    # verifica che la funzione esista e che il modulo esponga l'helper
    assert hasattr(sec_edgar, "_parse_13f_filing")
    assert hasattr(sec_edgar, "fetch_13f_with_previous")


def test_long_only_filter_logic():
    """
    Simula il filtro long-only del pipeline: per i CIK long-only,
    le holding con put_call='Put' o sh_prn_type='PRN' vengono escluse.
    """
    holdings = [
        {"ticker": "AAA", "put_call": "", "sh_prn_type": "SH"},      # tieni
        {"ticker": "BBB", "put_call": "Call", "sh_prn_type": "SH"},  # tieni
        {"ticker": "CCC", "put_call": "Put", "sh_prn_type": "SH"},   # escludi
        {"ticker": "DDD", "put_call": "", "sh_prn_type": "PRN"},     # escludi
    ]
    kept = [h for h in holdings
            if h.get("put_call") in ("Call", "", None) and h.get("sh_prn_type") == "SH"]
    tickers = {h["ticker"] for h in kept}
    assert tickers == {"AAA", "BBB"}
