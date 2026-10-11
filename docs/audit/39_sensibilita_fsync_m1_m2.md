# Audit 39 — Sensibilità di M1/M2 allo stallo di `fsync` iniziale (definizioni committate PRIMA di calcolare)

Motivo: la micro-misura di `fsync` fatta **prima di M1** (500 scritture da 4 KiB) ha p99 2024,4 ms e massimo 2059,4 ms, mentre la stessa misura dopo M1 ha p99 15,3 ms, prima di M2 15,2 ms, dopo M2 2,2 ms (`experiments_tnsm/m1_single_node/night_20261011/manifest.json`, chiavi `fsync_bench_before`/`fsync_bench_after`; `m2_p99_tail/night_20261011/manifest.json`; audit 38 §4). La causa dello stallo non è nota e non viene cercata qui. **Questa è un'analisi di sensibilità: i verdetti registrati di audit 38 non cambiano e non si sostituiscono**; si riporta soltanto se ricalcolandoli senza le celle più vicine allo stallo cambiano. Nessun nuovo dato, nessun accesso al nodo. M2 è il controllo (nessuno stallo prima di M2).

## Definizioni
- **Posizione** di una cella = il campo `cell` (0, 1, 2, …), che coincide con l'ordine cronologico di `t_start_unix` (verificato sui dati: monotono in M1 e in M2) e con `cell_order` del manifest. **Tempo dall'avvio** = `t_start_unix` − `started_utc` del manifest.
- **Insiemi di celle escluse (fissati ora):** E5 = le prime 5 celle di M1; E10 = le prime 10; E20 = le prime 20; ET = le celle con tempo dall'avvio < 600 s. (Nessuna durata dello stallo è nota: sono quattro finestre arbitrarie dichiarate prima del calcolo.)
- **Ordine:** tabella delle prime 20 celle di M1 (braccio, writer, ripetizione, throughput, errori inattesi) e, per ogni gruppo (braccio, writer), la posizione media delle sue celle (per vedere se la randomizzazione ha concentrato un gruppo all'inizio).
- **Andamento:** per ogni gruppo (braccio, writer) di M1 con ≥ 8 celle, correlazione di Spearman (ranghi medi per i pareggi) fra posizione e `throughput`, e fra posizione e `unexpected_errors`; per ogni gruppo, throughput medio delle celle del gruppo che cadono in E10 contro le altre (descrittivo, con i due n). Stesse correlazioni per M2 (gruppo = modo, writer; `throughput` solo: M2 non ha `unexpected_errors` nello stesso campo).
- **Errori:** per M1, per braccio: numero di celle con `unexpected_errors > 0` fra le prime 10 e fra le altre, e le posizioni di tutte le celle con errori nel braccio `deploy` (H-M1b).
- **Verdetti ricalcolati:** con `analyze_m1_arms.verdicts` (criteri verbatim di `m1_single_node/run.py:12-30`, seme e ricampionamenti di audit 38) sulle celle di M1 **meno** ciascun insieme escluso (E5, E10, E20, ET): H-M1 per braccio, H-M1b, H-M1c, nei due sottoinsiemi "all"/"filtered" della regola di scarto; si riporta per ogni (insieme, ipotesi) "invariato" o "cambia" rispetto al verdetto registrato (audit 38 §3). Per M2: i verdetti di `analyze.py m2` sono già senza stallo precedente; si riporta soltanto l'andamento.
- **Limiti:** un'esclusione di celle iniziali riduce l'n dei gruppi (es. 50 e 100 writer); le correlazioni di Spearman con n = 10-20 sono grossolane e **non si leggono come prova di assenza di effetto**; nessuna soglia di "effetto" è definita: l'analisi riporta i numeri.
- **Non si fa:** nessuna causa dello stallo, nessuna modifica dei verdetti registrati, nessuna esclusione di celle dai risultati ufficiali.

## Codice
`experiments_tnsm/common/analyze_fsync_sensitivity.py` con 5 test su righe sintetiche (scritti prima, rossi per modulo mancante; 4 mutazioni rilevate, una quinta non si applicava), committato (`cfa9e76`) prima di eseguirlo sui dati.

## Risultati (uscita integrale dello script: `experiments_tnsm/m1_single_node/night_20261011/fsync_sensitivity.md`)

# Sensitivity of M1/M2 to the initial fsync stall (definitions: docs/audit/39, c3e3777)

## M1, order: first 20 cells (position: arm, writers, rep, throughput ops/s, unexpected errors)
- 0: default, 1, rep 1, 181.8, 0
- 1: deploy, 10, rep 3, 244.4, 0
- 2: deploy, 10, rep 8, 236.7, 0
- 3: default, 10, rep 2, 140.2, 0
- 4: default, 10, rep 4, 120.6, 5
- 5: deploy, 100, rep 12, 117.2, 10
- 6: default, 100, rep 13, 89.4, 615
- 7: default, 10, rep 8, 147.3, 0
- 8: deploy, 50, rep 9, 168.6, 2
- 9: deploy, 100, rep 10, 110.5, 13
- 10: deploy, 100, rep 17, 116.4, 10
- 11: default, 100, rep 16, 97.3, 527
- 12: default, 1, rep 9, 281.7, 0
- 13: default, 1, rep 3, 273.7, 0
- 14: deploy, 100, rep 7, 124.7, 105
- 15: default, 50, rep 8, 167.0, 35
- 16: default, 10, rep 5, 207.7, 0
- 17: deploy, 10, rep 1, 345.9, 0
- 18: default, 100, rep 0, 105.5, 605
- 19: default, 100, rep 18, 124.2, 444

## M1, trend per group (cells >= 8): Spearman of position with throughput / unexpected errors; throughput of cells at positions < 10 against the rest

| arm | writers | cells | mean position | rho(position, throughput) | rho(position, errors) | early n / mean | rest n / mean |
|---|---|---|---|---|---|---|---|
| default | 1 | 10 | 47.0 | 0.236 | n/a | 1 / 181.8 | 9 / 262.6 |
| default | 10 | 10 | 33.6 | 0.503 | -0.406 | 3 / 136.0 | 7 / 209.2 |
| default | 50 | 10 | 56.9 | -0.079 | 0.061 | 0 / n/a | 10 / 153.5 |
| default | 100 | 20 | 54.0 | 0.723 | -0.690 | 1 / 89.4 | 19 / 119.6 |
| deploy | 1 | 10 | 58.8 | 0.430 | n/a | 0 / n/a | 10 / 372.6 |
| deploy | 10 | 10 | 33.7 | 0.418 | n/a | 2 / 240.5 | 8 / 298.6 |
| deploy | 50 | 10 | 52.7 | -0.285 | 0.123 | 1 / 168.6 | 9 / 210.0 |
| deploy | 100 | 20 | 52.2 | 0.442 | -0.116 | 2 / 113.8 | 18 / 136.3 |

## M1, errors by arm: cells with unexpected errors among the first 10 cells and the rest; positions of all cells with errors

- default: first 10 cells 2/5 with errors; rest 29/45; positions with errors: [4, 6, 11, 15, 18, 19, 20, 28, 29, 32, 34, 36, 39, 40, 52, 56, 57, 58, 66, 67, 72, 75, 80, 86, 87, 90, 91, 93, 94, 98, 99]
- deploy: first 10 cells 3/5 with errors; rest 24/45; positions with errors: [5, 8, 9, 10, 14, 24, 26, 31, 33, 44, 46, 47, 49, 50, 61, 62, 64, 65, 73, 74, 76, 79, 82, 88, 89, 95, 97]

## M1, registered verdicts recomputed without the excluded cells (same criteria, seed and resamples as audit 38)

### E5: 5 cells excluded, 95 left

| hypothesis | arm | subset | registered | without the set | changes |
|---|---|---|---|---|---|
| H-M1 | default | all | not falsified | not falsified | unchanged |
| H-M1 | default | filtered | not falsified | not falsified | unchanged |
| H-M1 | deploy | all | not falsified | not falsified | unchanged |
| H-M1 | deploy | filtered | not falsified | not falsified | unchanged |
| H-M1b | deploy | all | FALSIFIED | FALSIFIED | unchanged |
| H-M1b | deploy | filtered | FALSIFIED | FALSIFIED | unchanged |
| H-M1c | deploy vs default | all | not falsified | not falsified | unchanged |
| H-M1c | deploy vs default | filtered | not falsified | not falsified | unchanged |

### E10: 10 cells excluded, 90 left

| hypothesis | arm | subset | registered | without the set | changes |
|---|---|---|---|---|---|
| H-M1 | default | all | not falsified | not falsified | unchanged |
| H-M1 | default | filtered | not falsified | not falsified | unchanged |
| H-M1 | deploy | all | not falsified | not falsified | unchanged |
| H-M1 | deploy | filtered | not falsified | not falsified | unchanged |
| H-M1b | deploy | all | FALSIFIED | FALSIFIED | unchanged |
| H-M1b | deploy | filtered | FALSIFIED | FALSIFIED | unchanged |
| H-M1c | deploy vs default | all | not falsified | not falsified | unchanged |
| H-M1c | deploy vs default | filtered | not falsified | not falsified | unchanged |

### E20: 20 cells excluded, 80 left

| hypothesis | arm | subset | registered | without the set | changes |
|---|---|---|---|---|---|
| H-M1 | default | all | not falsified | not falsified | unchanged |
| H-M1 | default | filtered | not falsified | not falsified | unchanged |
| H-M1 | deploy | all | not falsified | not falsified | unchanged |
| H-M1 | deploy | filtered | not falsified | not falsified | unchanged |
| H-M1b | deploy | all | FALSIFIED | FALSIFIED | unchanged |
| H-M1b | deploy | filtered | FALSIFIED | FALSIFIED | unchanged |
| H-M1c | deploy vs default | all | not falsified | not falsified | unchanged |
| H-M1c | deploy vs default | filtered | not falsified | not falsified | unchanged |

### ET: 9 cells excluded, 91 left

| hypothesis | arm | subset | registered | without the set | changes |
|---|---|---|---|---|---|
| H-M1 | default | all | not falsified | not falsified | unchanged |
| H-M1 | default | filtered | not falsified | not falsified | unchanged |
| H-M1 | deploy | all | not falsified | not falsified | unchanged |
| H-M1 | deploy | filtered | not falsified | not falsified | unchanged |
| H-M1b | deploy | all | FALSIFIED | FALSIFIED | unchanged |
| H-M1b | deploy | filtered | FALSIFIED | FALSIFIED | unchanged |
| H-M1c | deploy vs default | all | not falsified | not falsified | unchanged |
| H-M1c | deploy vs default | filtered | not falsified | not falsified | unchanged |

## M2 (control: no stall before M2), trend per group (cells >= 8): Spearman of position with throughput; throughput at positions < 10 against the rest

| mode | writers | cells | mean position | rho(position, throughput) | early n / mean | rest n / mean |
|---|---|---|---|---|---|---|
| null | 100 | 10 | 49.5 | -0.552 | 1 / 40327.0 | 9 / 37361.0 |
| processes | 10 | 10 | 39.4 | 0.139 | 0 / n/a | 10 / 460.6 |
| processes | 50 | 10 | 37.4 | -0.176 | 1 / 303.0 | 9 / 305.2 |
| processes | 100 | 10 | 53.2 | 0.309 | 1 / 219.2 | 9 / 218.6 |
| threads | 1 | 10 | 38.8 | -0.188 | 2 / 349.8 | 8 / 346.9 |
| threads | 10 | 10 | 34.9 | -0.091 | 2 / 322.9 | 8 / 334.8 |
| threads | 50 | 10 | 51.6 | -0.067 | 1 / 215.5 | 9 / 218.2 |
| threads | 100 | 20 | 47.9 | 0.511 | 2 / 142.5 | 18 / 153.2 |

## Letture dei numeri (solo fatti; nessuna causa; nessuna soglia di effetto, vedi Limiti)
- **Verdetti:** invariati in tutti i 32 confronti (4 insiemi × 8 righe: H-M1 per braccio, H-M1b, H-M1c, nei sottoinsiemi "all" e "filtered"): E5 (95 celle rimaste), E10 (90), E20 (80), ET (91; 9 celle nei primi 600 s). H-M1b resta falsificata; H-M1 e H-M1c restano non falsificate.
- **Ordine:** le prime 20 celle mescolano bracci e writer (7 gruppi presenti su 8); la posizione media dei gruppi va da 33,6 (`default` 10 e `deploy` 10 writer) a 58,8 (`deploy` 1 writer): `default`/10 e `deploy`/10 sono i due gruppi più anticipati.
- **Andamento (Spearman posizione-throughput, n = 10-20):** positivo in 6 gruppi su 8 (massimo 0,723 a `default`/100 writer, n = 20; 0,503 a `default`/10), negativo in 2 (`default`/50 −0,079; `deploy`/50 −0,285). In tutti i 6 gruppi che hanno celle fra le prime 10 posizioni, il throughput medio di quelle celle è inferiore a quello delle altre (es. `default`/1: 181,8 con n = 1 contro 262,6; `default`/10: 136,0 (3) contro 209,2; `default`/100: 89,4 (1) contro 119,6; `deploy`/10: 240,5 (2) contro 298,6; `deploy`/50: 168,6 (1) contro 210,0; `deploy`/100: 113,8 (2) contro 136,3), con n = 1-3 per le celle iniziali.
- **Errori inattesi:** correlazione posizione-errori −0,690 a `default`/100 (n = 20), −0,406 a `default`/10, vicina a 0 o debole negli altri gruppi con varianza (0,061, 0,123, −0,116). Celle con errori fra le prime 10: `default` 2 su 5, `deploy` 3 su 5; fra le altre 29 su 45 e 24 su 45. Le celle `deploy` con errori sono sparse su tutte le posizioni (da 5 a 97).
- **M2 (controllo, nessuno stallo prima):** correlazioni fra −0,552 (`null`/100) e +0,511 (`threads`/100, n = 20); le prime celle sono sotto la media del resto in 4 gruppi su 7 che ne hanno e sopra in 3: nessun andamento coerente.
- **Cosa non so dire:** se l'andamento di M1 dipenda dallo stallo iniziale, da un transitorio del nodo o dal caso (n piccoli, nessun modello nullo); non è stata fatta alcuna correzione dei dati e nessun verdetto cambia.
