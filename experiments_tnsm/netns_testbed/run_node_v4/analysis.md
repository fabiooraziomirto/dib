# Banco netns: validazione confermativa del modello v4 (audit 80)

## T-W0 (validità, P0 a p = 0)

| d ms | mediana per sito ms | nominale ms | in ritardo | n | valido |
|---|---|---|---|---|---|
| 60 | 187 | 180 | 0 | 200 | True |
| 120 | 367 | 360 | 0 | 200 | True |
| 180 | 548 | 540 | 0 | 200 | True |

**T-W0: SUPERATO**

## P0: misura (previsione v4) e confronto con v3

| d ms | perdita | validi | in ritardo per sito | slow episodes | pending | mediana ultimo ms | p95 ms | v3 in ritardo |
|---|---|---|---|---|---|---|---|---|
| 60 | 4% | 60 | 0.147 (0.150) | 0.767 (0.801) | 0.000 (0) | 1187 (1180) | 2186 (1540) | 0.114 |
| 60 | 8% | 60 | 0.298 (0.282) | 1.000 (0.966) | 0.000 (0) | 1191 (1180) | 2551 (2300) | 0.220 |
| 120 | 4% | 60 | 0.152 (0.149) | 0.817 (0.800) | 0.000 (0) | 1365 (1360) | 1377 (2080) | 0.113 |
| 120 | 8% | 60 | 0.248 (0.281) | 0.917 (0.963) | 0.000 (0) | 1373 (1360) | 2608 (2600) | 0.218 |
| 180 | 4% | 60 | 0.147 (0.147) | 0.783 (0.796) | 0.000 (0) | 1549 (1764) | 2546 (2900) | 0.113 |
| 180 | 8% | 60 | 0.258 (0.277) | 0.917 (0.962) | 0.000 (0) | 1634 (1900) | 2642 (4977) | 0.217 |

## Verdetti

- **T-W1 (modello v4):** 5/6 celle entro ±3 punti (in ritardo), ±10 (slow) e pending ≤ 2 %; celle oltre il doppio: 0 -> **MODELLO v4 VALIDATO** (regola: ≥ 5/6 e nessuna oltre il doppio).
- **T-W2 (descrittivo):** v3 avrebbe superato 1/6 celle con le stesse tolleranze.
