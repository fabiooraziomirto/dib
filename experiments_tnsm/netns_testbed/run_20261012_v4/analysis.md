# Banco netns: validazione confermativa del modello v4 (audit 80)

## T-W0 (validità, P0 a p = 0)

| d ms | mediana per sito ms | nominale ms | in ritardo | n | valido |
|---|---|---|---|---|---|
| 60 | 185 | 180 | 0 | 200 | True |
| 120 | 366 | 360 | 0 | 200 | True |
| 180 | 545 | 540 | 0 | 200 | True |

**T-W0: SUPERATO**

## P0: misura (previsione v4) e confronto con v3

| d ms | perdita | validi | in ritardo per sito | slow episodes | pending | mediana ultimo ms | p95 ms | v3 in ritardo |
|---|---|---|---|---|---|---|---|---|
| 60 | 4% | 60 | 0.143 (0.150) | 0.800 (0.801) | 0.000 (0) | 1119 (1180) | 2160 (1540) | 0.114 |
| 60 | 8% | 60 | 0.290 (0.282) | 0.983 (0.966) | 0.000 (0) | 1193 (1180) | 2669 (2300) | 0.220 |
| 120 | 4% | 60 | 0.157 (0.149) | 0.850 (0.800) | 0.000 (0) | 1364 (1360) | 2363 (2080) | 0.113 |
| 120 | 8% | 60 | 0.268 (0.281) | 0.933 (0.963) | 0.000 (0) | 1367 (1360) | 2432 (2600) | 0.218 |
| 180 | 4% | 60 | 0.130 (0.147) | 0.733 (0.796) | 0.000 (0) | 1547 (1764) | 2007 (2900) | 0.113 |
| 180 | 8% | 60 | 0.275 (0.277) | 0.967 (0.962) | 0.000 (0) | 1556 (1900) | 2997 (4977) | 0.217 |

## Verdetti

- **T-W1 (modello v4):** 6/6 celle entro ±3 punti (in ritardo), ±10 (slow) e pending ≤ 2 %; celle oltre il doppio: 0 -> **MODELLO v4 VALIDATO** (regola: ≥ 5/6 e nessuna oltre il doppio).
- **T-W2 (descrittivo):** v3 avrebbe superato 2/6 celle con le stesse tolleranze.
