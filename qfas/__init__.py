"""
QFAS v2.5 — Quant Fund + Analyst Signal motor
Engine separato dal 13F core esistente.
Capitale €48k / 8 posizioni equal-weight.

Moduli:
  qfas_config           — parametri centralizzati
  fund_universe         — survivorship filter 36 fondi
  dividend_tax_drag     — doppio scenario fiscalità dividendi USA
  data_ingestion        — SEC 13F/Form4/8-K + prezzi + congressional + analyst
  signal_decay_scorer   — Radar Score con decay esponenziale + crowding
  realtime_trigger_engine — Entry score con analyst/insider/PEAD/squeeze
  tax_aware_optimizer   — selezione 8 posizioni + TLH italiano + spread scalato
"""
__version__ = "2.5.0"
