# APEX Legit: vincolo S&P dopo filtro BTC

Confronto fra strategia attuale e variante che, quando BTC vince ma viene bocciato dalla SMA30, rivaluta anche S&P 500 invece di andare solo Oro/Cash.

## Full period netto fiscale

| Strategia | Finale 10k | CAGR | MaxDD | Calmar | Ulcer | Swap/anno | Cash weeks | SP500 weeks | Filtro->Cash | Filtro->SP500 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| APEX Legit attuale: filtro BTC -> Oro/Cash | 144.246 | 37.43% | -40.82% | 0.917 | 21.26% | 8.1 | 41 | 85 | 17 | 0 |
| APEX Legit senza vincolo SP: filtro BTC -> rivaluta Oro/SP/Cash | 157.262 | 38.85% | -37.87% | 1.026 | 21.04% | 7.51 | 25 | 118 | 5 | 23 |

## Rolling windows

| Periodo | Strategia | CAGR | MaxDD | Calmar | Swap/anno |
| --- | --- | --- | --- | --- | --- |
| 2018-2020 | current | 41.1% | -31.7% | 1.295 | 8.7 |
| 2018-2020 | sp_free | 43.2% | -31.7% | 1.363 | 8.03 |
| 2021-2022 | current | 18.4% | -33.5% | 0.547 | 9.12 |
| 2021-2022 | sp_free | 17.5% | -30.2% | 0.578 | 8.11 |
| 2023-2026 | current | 35.9% | -27.4% | 1.313 | 7.08 |
| 2023-2026 | sp_free | 38.2% | -27.4% | 1.396 | 6.78 |
| 2019-2021 | current | 92.5% | -40.8% | 2.265 | 8.36 |
| 2019-2021 | sp_free | 97.4% | -37.9% | 2.573 | 8.36 |
| 2020-2022 | current | 47.4% | -40.8% | 1.162 | 8.75 |
| 2020-2022 | sp_free | 46.4% | -37.9% | 1.224 | 9.09 |
| 2021-2023 | current | 28.6% | -33.5% | 0.854 | 8.75 |
| 2021-2023 | sp_free | 28.0% | -30.2% | 0.926 | 8.08 |
| 2022-2024 | current | 30.8% | -27.4% | 1.127 | 8.36 |
| 2022-2024 | sp_free | 28.1% | -27.4% | 1.027 | 8.03 |
| 2023-2025 | current | 40.7% | -27.4% | 1.487 | 7.02 |
| 2023-2025 | sp_free | 40.7% | -27.4% | 1.487 | 7.02 |
