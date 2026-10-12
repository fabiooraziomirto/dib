# Banco netns: sequenziale contro parallelo (audit 77)

| d ms | perdita | S1 validi/episodi | S1 mediana ms [IC] | previsione ms | P0 mediana ms | rapporto S1/P0 | gap mediano tra siti s | episodi incompleti S1 |
|---|---|---|---|---|---|---|---|---|
| 50 | 2% | 40/40 | 2020 [2007; 2382] | 2250 | 285 | 7.1 | 0.21 | 0 |
| 50 | 5% | 40/40 | 3564 [2695; 3988] | 3250 | 1157 | 3.1 | 0.21 | 0 |
| 50 | 10% | 40/40 | 4270 [4080; 4635] | 4550 | 1264 | 3.4 | 0.27 | 0 |
| 100 | 2% | 40/40 | 3951 [3789; 4128] | 4500 | 556 | 7.1 | 0.40 | 0 |
| 100 | 5% | 40/40 | 4030 [3663; 4549] | 5500 | 1303 | 3.1 | 0.40 | 0 |
| 100 | 10% | 40/40 | 5435 [5268; 5658] | 7100 | 1312 | 4.1 | 0.40 | 0 |
| 200 | 2% | 40/40 | 5729 [5397; 5817] | 8800 | 1109 | 5.2 | 0.38 | 0 |
| 200 | 5% | 40/40 | 5711 [5074; 5923] | 10200 | 1616 | 3.5 | 0.43 | 0 |
| 200 | 10% | 40/40 | 6519 [6260; 7247] | 12200 | 2117 | 3.1 | 0.49 | 0 |

## Verdetti

- **T-S0 (sequenzialità):** celle con gap mediano < 0,75 R: 0 -> **non falsificata**.
- **T-S1 (modello sequenziale):** 5/9 celle entro ±25 % -> **NON VALIDATO** (regola: ≥ 7/9).
- **T-S2 (default parallelo):** rapporto minimo S1/P0 = 3.08 (soglia 2,0) -> **non falsificata**.
