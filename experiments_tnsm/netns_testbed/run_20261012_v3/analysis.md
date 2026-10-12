# Banco netns: validazione confermativa del modello v3 (audit 78)

## T-V0 (validità, P0 a p = 0)

| d ms | mediana per sito ms | nominale ms | in ritardo | n | valido |
|---|---|---|---|---|---|
| 75 | 229 | 225 | 0 | 200 | True |
| 150 | 458 | 450 | 0 | 200 | True |

**T-V0: SUPERATO**

## Parallelo (P0): misura (previsione v3)

| d ms | perdita | validi | in ritardo per sito | slow episodes | pending | mediana ultimo ms | p95 ms |
|---|---|---|---|---|---|---|---|
| 75 | 3% | 60 | 0.108 (0.087) | 0.683 (0.597) | 0.000 (0) | 841 (675) | 1284 (1225) |
| 75 | 7% | 60 | 0.250 (0.194) | 0.900 (0.884) | 0.000 (0) | 1235 (1225) | 2242 (2225) |
| 150 | 3% | 60 | 0.100 (0.086) | 0.683 (0.592) | 0.000 (0) | 1443 (1450) | 2452 (2270) |
| 150 | 7% | 60 | 0.242 (0.192) | 0.950 (0.883) | 0.000 (0) | 1640 (1750) | 2461 (3050) |

## Sequenziale (S1): misura (previsione v3)

| d ms | perdita | validi | mediana ultimo ms [IC] | p95 ms | errore relativo |
|---|---|---|---|---|---|
| 75 | 3% | 40/40 | 3408 [3056; 3674] (3325) | 4690 (4775) | 0.02 |
| 75 | 7% | 40/40 | 4373 [4135; 4602] (4025) | 6313 (5475) | 0.09 |
| 150 | 3% | 40/40 | 5260 [4802; 5431] (5050) | 6023 (5954) | 0.04 |
| 150 | 7% | 40/40 | 5538 [5344; 5697] (5281) | 6653 (6022) | 0.05 |

## Verdetti

- **T-V1 (parallelo):** 2/4 celle entro i criteri -> **NON regge** (regola: ≥ 3/4).
- **T-V2 (sequenziale):** 4/4 celle entro ±25 % -> **regge** (regola: ≥ 3/4).
- **Modello v3 fuori campione: NON VALIDATO** (richiede T-V0, T-V1 e T-V2).
