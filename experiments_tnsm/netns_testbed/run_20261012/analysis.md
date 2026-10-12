# Banco netns: verdetti T-0..T-3 (audit 75)

## T-0 (validità, p = 0)

| d ms | politica | mediana per sito ms | nominale ms | in ritardo | n | valido |
|---|---|---|---|---|---|---|
| 50 | P0 | 155 | 150 | 0 | 200 | True |
| 50 | P1 | 57 | 50 | 8 | 200 | False |
| 100 | P0 | 307 | 300 | 0 | 200 | True |
| 100 | P1 | 104 | 100 | 3 | 200 | False |
| 200 | P0 | 605 | 600 | 0 | 200 | True |
| 200 | P1 | 204 | 200 | 18 | 200 | False |

**T-0: FALLITO: il banco non è valido, nulla di ciò che segue si riporta**

## Celle (60 episodi; previsione del modello v2 tra parentesi)

| d ms | perdita | politica | validi | in ritardo per sito | slow episodes | pending episodi | mediana ultimo ms | p95 ultimo ms |
|---|---|---|---|---|---|---|---|---|
| 50 | 2% | P0 | 60 | 0.065 (0.059) | 0.467 (0.454) | 0.000 (0.001) | 167 (150) | 1161 (1150) |
| 50 | 2% | P1 | 60 | 0.127 (0.020) | 0.617 (0.184) | 0.000 (0.000) | 156 (50) | 515 (350) |
| 50 | 5% | P0 | 60 | 0.168 (0.142) | 0.783 (0.786) | 0.000 (0.010) | 784 (1150) | 2162 (2150) |
| 50 | 5% | P1 | 60 | 0.175 (0.050) | 0.867 (0.400) | 0.000 (0.000) | 183 (50) | 817 (350) |
| 50 | 10% | P0 | 60 | 0.322 (0.266) | 0.983 (0.954) | 0.000 (0.082) | 1161 (1150) | 2169 (2150) |
| 50 | 10% | P1 | 60 | 0.278 (0.100) | 0.967 (0.650) | 0.000 (0.009) | 506 (350) | 1555 (950) |
| 100 | 2% | P0 | 60 | 0.090 (0.059) | 0.617 (0.455) | 0.000 (0.001) | 565 (300) | 1323 (1300) |
| 100 | 2% | P1 | 60 | 0.133 (0.020) | 0.667 (0.181) | 0.000 (0.000) | 307 (100) | 903 (700) |
| 100 | 5% | P0 | 60 | 0.207 (0.142) | 0.867 (0.787) | 0.000 (0.011) | 1308 (1300) | 2514 (2300) |
| 100 | 5% | P1 | 60 | 0.225 (0.050) | 0.933 (0.402) | 0.000 (0.001) | 710 (100) | 1507 (700) |
| 100 | 10% | P0 | 60 | 0.337 (0.265) | 1.000 (0.955) | 0.000 (0.092) | 1440 (1300) | 2567 (2300) |
| 100 | 10% | P1 | 60 | 0.345 (0.100) | 1.000 (0.648) | 0.000 (0.013) | 921 (700) | 2123 (1300) |
| 200 | 2% | P0 | 60 | 0.068 (0.059) | 0.483 (0.453) | 0.000 (0.005) | 639 (600) | 2017 (2000) |
| 200 | 2% | P1 | 60 | 0.247 (0.020) | 0.950 (0.186) | 0.000 (0.002) | 611 (200) | 1609 (1600) |
| 200 | 5% | P0 | 60 | 0.172 (0.139) | 0.850 (0.774) | 0.000 (0.061) | 1612 (1600) | 3014 (3000) |
| 200 | 5% | P1 | 60 | 0.340 (0.049) | 0.983 (0.392) | 0.000 (0.034) | 1119 (200) | 2118 (2600) |
| 200 | 10% | P0 | 60 | 0.302 (0.256) | 0.967 (0.943) | 0.000 (0.340) | 2013 (2000) | 4438 (3000) |
| 200 | 10% | P1 | 60 | 0.533 (0.094) | 1.000 (0.612) | 0.000 (0.204) | 1611 (1600) | 3293 (3000) |

## Dettaglio

- (50 ms, 2%): |Δ late| = 0.006, |Δ slow| = 0.013 -> ok
- T-2 (50 ms, 2%): late(P1) - late(P0) IC95 [0.022; 0.103], mediana per sito P1 55 contro P0 156 ms -> NON ridotto
- (50 ms, 5%): |Δ late| = 0.027, |Δ slow| = 0.003 -> ok
- T-2 (50 ms, 5%): late(P1) - late(P0) IC95 [-0.043; 0.058], mediana per sito P1 57 contro P0 157 ms -> NON ridotto
- (50 ms, 10%): |Δ late| = 0.056, |Δ slow| = 0.029 -> FUORI
- T-2 (50 ms, 10%): late(P1) - late(P0) IC95 [-0.093; 0.008], mediana per sito P1 58 contro P0 158 ms -> NON ridotto
- (100 ms, 2%): |Δ late| = 0.031, |Δ slow| = 0.161 -> FUORI
- T-2 (100 ms, 2%): late(P1) - late(P0) IC95 [0.003; 0.087], mediana per sito P1 106 contro P0 307 ms -> NON ridotto
- (100 ms, 5%): |Δ late| = 0.065, |Δ slow| = 0.080 -> FUORI
- T-2 (100 ms, 5%): late(P1) - late(P0) IC95 [-0.028; 0.067], mediana per sito P1 107 contro P0 308 ms -> NON ridotto
- (100 ms, 10%): |Δ late| = 0.072, |Δ slow| = 0.045 -> FUORI
- T-2 (100 ms, 10%): late(P1) - late(P0) IC95 [-0.038; 0.053], mediana per sito P1 109 contro P0 310 ms -> NON ridotto
- (200 ms, 2%): |Δ late| = 0.010, |Δ slow| = 0.030 -> ok
- T-2 (200 ms, 2%): late(P1) - late(P0) IC95 [0.138; 0.218], mediana per sito P1 207 contro P0 607 ms -> NON ridotto
- (200 ms, 5%): |Δ late| = 0.033, |Δ slow| = 0.076 -> ok
- T-2 (200 ms, 5%): late(P1) - late(P0) IC95 [0.122; 0.215], mediana per sito P1 209 contro P0 608 ms -> NON ridotto
- (200 ms, 10%): |Δ late| = 0.046, |Δ slow| = 0.024 -> FUORI
- T-2 (200 ms, 10%): late(P1) - late(P0) IC95 [0.180; 0.285], mediana per sito P1 602 contro P0 610 ms -> NON ridotto

## Verdetti

- **T-1 (modello fuori campione, P0):** 4/9 celle entro i criteri (late ±0.04, slow ±0.12); celle oltre il doppio: 0. **MODELLO NON VALIDATO** (regola: ≥ 7/9 e nessuna oltre il doppio).
- **T-2 (effetto di P1):** P1 riduce le consegne in ritardo in 0/9 condizioni. **FALSIFICATA** (falsificata se non riduce in ≥ 3).
- **T-3 (sicurezza):** pending(P1) − pending(P0) > 3 punti in: nessuna condizione. **non falsificata**.
