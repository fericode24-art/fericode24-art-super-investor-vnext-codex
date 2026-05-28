"""
QFAS v2.5 — dividend_tax_drag.py

Calcola il drag fiscale annuale sui dividendi USA per residente fiscale
italiano in regime amministrato Fineco. Doppio scenario configurabile.

═══════════════════════════════════════════════════════════════════════════
SCENARIO A — assume_recovery=True (default per imprenditore con dichiarazione)
═══════════════════════════════════════════════════════════════════════════
  Procedura fiscale:
  1) Broker USA applica ritenuta alla fonte 15% (US-IT tax treaty con W-8BEN)
  2) Fineco applica imposta sostitutiva 26% sul GROSS, scalando i 15% USA
  3) → 11% netto pagato in più
  4) In dichiarazione (Quadro CE/RM), credito d'imposta recupera i 15% USA
  Tax rate effettiva netta: 26% (uguale a imposta sostitutiva pura).

═══════════════════════════════════════════════════════════════════════════
SCENARIO B — assume_recovery=False (conservativo)
═══════════════════════════════════════════════════════════════════════════
  Procedura fiscale (chi NON fa dichiarazione articolata):
  1) Broker USA applica ritenuta 15% alla fonte
  2) Fineco applica imposta sostitutiva 26% sul NETTO frontiera (85%)
  3) Nessun recupero credito
  Tax rate effettiva: 15% + 26% × 85% = 36,1%

Riferimenti:
- Convenzione US-IT tax treaty: ritenuta agevolata 15%
- Art. 27 DPR 600/73 + art. 18 DPR 917/86 per credito imposta
- Regime amministrato Fineco: applica imposta sostitutiva 26% automaticamente
"""
from __future__ import annotations
from typing import Tuple
from qfas.qfas_config import config


def calculate_effective_dividend_tax_rate(assume_recovery: bool = None) -> float:
    """
    Restituisce l'aliquota effettiva totale sui dividendi USA.
    Se assume_recovery è None, usa il default da config.
    """
    if assume_recovery is None:
        assume_recovery = config.ASSUME_FOREIGN_TAX_CREDIT_RECOVERY

    if assume_recovery:
        # Scenario A: 26% effettivo (= imposta sostitutiva pura)
        return config.CAPITAL_GAIN_TAX_RATE

    # Scenario B: 15% withholding USA + 26% × 85% Fineco
    withholding_usa = config.DIV_WITHHOLDING_USA              # 0.15
    sostitutiva_on_net = config.CAPITAL_GAIN_TAX_RATE * (1.0 - withholding_usa)
    return withholding_usa + sostitutiva_on_net               # 0.15 + 0.221 = 0.371


def calculate_dividend_drag(gross_yield: float,
                            assume_recovery: bool = None) -> Tuple[float, float]:
    """
    Calcola il drag annuale e il yield netto.

    Args:
        gross_yield: rendimento da dividendi annuo lordo (es. 0.025 = 2.5%)
        assume_recovery: True/False per Scenario A/B. None = default config.

    Returns:
        (annual_drag, net_yield):
          annual_drag = % di portafoglio persa in tasse dividendi/anno
          net_yield = % di dividendi netti incassati/anno
    """
    tax_rate = calculate_effective_dividend_tax_rate(assume_recovery)
    annual_drag = gross_yield * tax_rate
    net_yield = gross_yield - annual_drag
    return annual_drag, net_yield


def apply_dividend_drag_to_cagr(cagr_gross: float, dividend_yield_avg: float,
                                assume_recovery: bool = None) -> float:
    """
    Sottrae il drag dividendi annuo dal CAGR lordo.
    Usare per onestà nel confronto strategia vs SPY.

    Args:
        cagr_gross: CAGR lordo dividendi (es. 0.20 = 20%/anno)
        dividend_yield_avg: yield medio dividendi del portafoglio (es. 0.018)
        assume_recovery: scenario fiscale

    Returns:
        CAGR netto dividendi
    """
    drag, _ = calculate_dividend_drag(dividend_yield_avg, assume_recovery)
    return cagr_gross - drag


def report_scenario_comparison() -> str:
    """Diagnostico: stampa side-by-side i due scenari per typical yields."""
    L = []
    L.append("=" * 72)
    L.append(" DIVIDEND TAX DRAG — Doppio Scenario Regime Amministrato Fineco")
    L.append("=" * 72)
    L.append("")
    L.append(f" Scenario A (recovery=True):  {calculate_effective_dividend_tax_rate(True)*100:.1f}%")
    L.append(f" Scenario B (recovery=False): {calculate_effective_dividend_tax_rate(False)*100:.1f}%")
    L.append("")
    L.append(" Drag annuo su portafoglio per yield tipici:")
    L.append(f"  {'Yield lordo':>12} | {'Scenario A':>12} | {'Scenario B':>12}")
    L.append(f"  {'-'*12} | {'-'*12} | {'-'*12}")
    for y in [0.005, 0.010, 0.015, 0.020, 0.025, 0.030, 0.040, 0.050]:
        drag_a, _ = calculate_dividend_drag(y, assume_recovery=True)
        drag_b, _ = calculate_dividend_drag(y, assume_recovery=False)
        L.append(f"  {y*100:>11.1f}% | {drag_a*100:>11.3f}% | {drag_b*100:>11.3f}%")
    L.append("")
    L.append(" Per portafoglio strategia QFAS (yield medio stimato ~1.5%):")
    drag_a, _ = calculate_dividend_drag(0.015, assume_recovery=True)
    drag_b, _ = calculate_dividend_drag(0.015, assume_recovery=False)
    L.append(f"   Scenario A: -{drag_a*100:.2f}% CAGR/anno")
    L.append(f"   Scenario B: -{drag_b*100:.2f}% CAGR/anno")
    L.append("=" * 72)
    return "\n".join(L)


if __name__ == "__main__":
    print(report_scenario_comparison())
