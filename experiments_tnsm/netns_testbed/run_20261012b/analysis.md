# Banco netns: verdetti T-0..T-3 (audit 75)

## T-0 (validità, p = 0)

| d ms | politica | mediana per sito ms | nominale ms | in ritardo | n | valido |
|---|---|---|---|---|---|---|
| 50 | P0 | 156 | 150 | 0 | 200 | True |
| 50 | P1 | 55 | 50 | 6 | 200 | False |
| 100 | P0 | 304 | 300 | 0 | 200 | True |
| 100 | P1 | 104 | 100 | 2 | 200 | False |
| 200 | P0 | 607 | 600 | 0 | 200 | True |
| 200 | P1 | 207 | 200 | 12 | 200 | False |

**T-0: FALLITO: il banco non è valido, nulla di ciò che segue si riporta**

## Celle (60 episodi; previsione del modello v2 tra parentesi)

| d ms | perdita | politica | validi | in ritardo per sito | slow episodes | pending episodi | mediana ultimo ms | p95 ultimo ms |
|---|---|---|---|---|---|---|---|---|
| 50 | 2% | P0 | 60 | 0.088 (0.059) | 0.583 (0.454) | 0.000 (0.001) | 285 (150) | 1163 (1150) |
| 50 | 2% | P1 | 60 | 0.070 (0.020) | 0.533 (0.184) | 0.000 (0.000) | 154 (50) | 509 (350) |
| 50 | 5% | P0 | 60 | 0.193 (0.142) | 0.817 (0.786) | 0.000 (0.010) | 1157 (1150) | 2157 (2150) |
| 50 | 5% | P1 | 60 | 0.147 (0.050) | 0.750 (0.400) | 0.000 (0.000) | 187 (50) | 672 (350) |
| 50 | 10% | P0 | 60 | 0.367 (0.266) | 0.983 (0.954) | 0.000 (0.082) | 1264 (1150) | 2816 (2150) |
| 50 | 10% | P1 | 60 | 0.277 (0.100) | 0.933 (0.650) | 0.000 (0.009) | 512 (350) | 1361 (950) |
| 100 | 2% | P0 | 60 | 0.073 (0.059) | 0.550 (0.455) | 0.000 (0.001) | 556 (300) | 1312 (1300) |
| 100 | 2% | P1 | 60 | 0.093 (0.020) | 0.633 (0.181) | 0.000 (0.000) | 309 (100) | 772 (700) |
| 100 | 5% | P0 | 60 | 0.173 (0.142) | 0.833 (0.787) | 0.000 (0.011) | 1303 (1300) | 2302 (2300) |
| 100 | 5% | P1 | 60 | 0.172 (0.050) | 0.850 (0.402) | 0.000 (0.001) | 359 (100) | 1309 (700) |
| 100 | 10% | P0 | 60 | 0.315 (0.265) | 0.967 (0.955) | 0.000 (0.092) | 1312 (1300) | 2521 (2300) |
| 100 | 10% | P1 | 60 | 0.282 (0.100) | 1.000 (0.648) | 0.000 (0.013) | 775 (700) | 2233 (1300) |
| 200 | 2% | P0 | 60 | 0.075 (0.059) | 0.550 (0.453) | 0.000 (0.005) | 1109 (600) | 2015 (2000) |
| 200 | 2% | P1 | 60 | 0.155 (0.020) | 0.783 (0.186) | 0.000 (0.002) | 608 (200) | 1615 (1600) |
| 200 | 5% | P0 | 60 | 0.152 (0.139) | 0.833 (0.774) | 0.000 (0.061) | 1616 (1600) | 2608 (3000) |
| 200 | 5% | P1 | 60 | 0.227 (0.049) | 0.900 (0.392) | 0.000 (0.034) | 1053 (200) | 2113 (2600) |
| 200 | 10% | P0 | 60 | 0.343 (0.256) | 1.000 (0.943) | 0.000 (0.340) | 2117 (2000) | 4603 (3000) |
| 200 | 10% | P1 | 60 | 0.407 (0.094) | 1.000 (0.612) | 0.000 (0.204) | 1608 (1600) | 2611 (3000) |

## Dettaglio

- (50 ms, 2%): |Δ late| = 0.029, |Δ slow| = 0.129 -> FUORI
- T-2 (50 ms, 2%): late(P1) - late(P0) IC95 [-0.048; 0.013], mediana per sito P1 57 contro P0 157 ms -> NON ridotto
- (50 ms, 5%): |Δ late| = 0.052, |Δ slow| = 0.030 -> FUORI
- T-2 (50 ms, 5%): late(P1) - late(P0) IC95 [-0.090; -0.003], mediana per sito P1 56 contro P0 159 ms -> ridotto
- (50 ms, 10%): |Δ late| = 0.101, |Δ slow| = 0.029 -> FUORI
- T-2 (50 ms, 10%): late(P1) - late(P0) IC95 [-0.140; -0.038], mediana per sito P1 58 contro P0 161 ms -> ridotto
- (100 ms, 2%): |Δ late| = 0.014, |Δ slow| = 0.095 -> ok
- T-2 (100 ms, 2%): late(P1) - late(P0) IC95 [-0.010; 0.050], mediana per sito P1 106 contro P0 305 ms -> NON ridotto
- (100 ms, 5%): |Δ late| = 0.032, |Δ slow| = 0.047 -> ok
- T-2 (100 ms, 5%): late(P1) - late(P0) IC95 [-0.045; 0.038], mediana per sito P1 107 contro P0 307 ms -> NON ridotto
- (100 ms, 10%): |Δ late| = 0.050, |Δ slow| = 0.012 -> FUORI
- T-2 (100 ms, 10%): late(P1) - late(P0) IC95 [-0.077; 0.015], mediana per sito P1 109 contro P0 308 ms -> NON ridotto
- (200 ms, 2%): |Δ late| = 0.016, |Δ slow| = 0.097 -> ok
- T-2 (200 ms, 2%): late(P1) - late(P0) IC95 [0.043; 0.117], mediana per sito P1 207 contro P0 605 ms -> NON ridotto
- (200 ms, 5%): |Δ late| = 0.013, |Δ slow| = 0.060 -> ok
- T-2 (200 ms, 5%): late(P1) - late(P0) IC95 [0.030; 0.122], mediana per sito P1 207 contro P0 609 ms -> NON ridotto
- (200 ms, 10%): |Δ late| = 0.087, |Δ slow| = 0.057 -> FUORI
- T-2 (200 ms, 10%): late(P1) - late(P0) IC95 [0.017; 0.110], mediana per sito P1 212 contro P0 611 ms -> NON ridotto

## Verdetti

- **T-1 (modello fuori campione, P0):** 4/9 celle entro i criteri (late ±0.04, slow ±0.12); celle oltre il doppio: 2. **MODELLO NON VALIDATO** (regola: ≥ 7/9 e nessuna oltre il doppio).
- **T-2 (effetto di P1):** P1 riduce le consegne in ritardo in 2/9 condizioni. **FALSIFICATA** (falsificata se non riduce in ≥ 3).
- **T-3 (sicurezza):** pending(P1) − pending(P0) > 3 punti in: nessuna condizione. **non falsificata**.
