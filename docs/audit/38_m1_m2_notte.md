# Audit 38 — M1/M2 della notte 2026-10-10/11: esiti dei criteri pre-registrati (audit 37)

Dati: `experiments_tnsm/m1_single_node/night_20261011/` (100 celle) e `experiments_tnsm/m2_p99_tail/night_20261011/` (90 celle), copiati con sha256 identici sui due lati e committati prima dell'analisi (`cea63ed`); mai in `results/`. Ipotesi, regola di scarto e codice di analisi: quelli committati prima della notte (audit 37 §1). Tutte le uscite sotto sono copie esatte dell'output degli script. Nessuna spiegazione delle cause; nessun confronto con altre macchine.

## 0. Difetto dichiarato dell'analisi e come è stato trattato
- `experiments_tnsm/common/analyze.py` cerca `mode == "threads"` per il verdetto di H-M1; le celle M1 della notte hanno `mode` = braccio (`default`/`deploy`), perciò **`analyze.py m1` non ha stampato alcun verdetto** (uscita vuota) e H-M1b/H-M1c non sono implementati lì. Ho scritto `experiments_tnsm/common/analyze_m1_arms.py` (commit `e98234c`, test `bde4d08`; 7 test sintetici, rossi prima del codice, 3 mutazioni rilevate) che applica **alla lettera** i criteri di `m1_single_node/run.py:12-30`, con lo stesso schema di seme e bootstrap sulle celle di `analyze.py`, e lo ho committato **prima** di eseguirlo sui dati.
- Correzione di processo: il messaggio del commit `e98234c` diceva che 3 mutazioni erano rilevate, ma 2 sopravvivevano; `bde4d08` aggiunge i test che le uccidono (il codice di analisi non è cambiato fra i due commit).
- `analyze.py m2` ha funzionato come registrato (modi `threads`, `null`, `processes`).

## 1. M1 (`analyze_m1_arms.py`, `verdicts_by_arm.md`, copia integrale)

# M1 per-arm verdicts (criteria of m1_single_node/run.py:12-30, verbatim)

- H-M1 [default, all, cells 30]: throughput (all ops) at 50 = 153.5 [140.4, 163.2], at 100 = 118.1 [111.9, 124.0] ops/s -> not falsified (falsified iff CI100 lower > CI50 upper)
- H-M1 [deploy, all, cells 30]: throughput (all ops) at 50 = 205.8 [193.0, 217.7], at 100 = 134.1 [127.5, 140.6] ops/s -> not falsified (falsified iff CI100 lower > CI50 upper)
- H-M1b [all, deploy cells 50]: deploy cells with unexpected errors = 27 -> FALSIFIED
- H-M1c [all, cells 40]: completed-ops throughput at 100: deploy 133.9 [127.2, 140.4] vs default 115.3 [109.0, 121.3] ops/s -> not falsified (falsified iff deploy CI upper < default CI lower)
- H-M1 [default, filtered, cells 30]: throughput (all ops) at 50 = 153.5 [140.2, 163.3], at 100 = 118.1 [111.9, 123.9] ops/s -> not falsified (falsified iff CI100 lower > CI50 upper)
- H-M1 [deploy, filtered, cells 29]: throughput (all ops) at 50 = 205.8 [193.0, 217.3], at 100 = 135.3 [128.9, 141.8] ops/s -> not falsified (falsified iff CI100 lower > CI50 upper)
- H-M1b [filtered, deploy cells 49]: deploy cells with unexpected errors = 26 -> FALSIFIED
- H-M1c [filtered, cells 39]: completed-ops throughput at 100: deploy 135.1 [128.4, 141.6] vs default 115.3 [109.2, 121.4] ops/s -> not falsified (falsified iff deploy CI upper < default CI lower)

# Pool-checkout censoring, reported separately (p99 >= 29.9 s with unexpected errors = ceiling of the 30 s checkout timeout, not a latency)

| arm | writers | cells | censored (p99 at the ceiling) | cells with unexpected errors | cells with a usable p99 |
|---|---|---|---|---|---|
| default | 1 | 10 | 0 | 0 | 10 |
| default | 10 | 10 | 0 | 1 | 10 |
| default | 50 | 10 | 1 | 10 | 9 |
| default | 100 | 20 | 20 | 20 | 0 |
| deploy | 1 | 10 | 0 | 0 | 10 |
| deploy | 10 | 10 | 0 | 0 | 10 |
| deploy | 50 | 10 | 0 | 7 | 10 |
| deploy | 100 | 20 | 0 | 20 | 20 |

`analyze.py m1` (verdetti integrati): uscita vuota (vedi §0). Statistiche per cella e braccio in `experiments_tnsm/m1_single_node/night_20261011/summary.csv` e `summary.md`; colonne principali, insieme "all" (media sulle celle; IC nel CSV):

| mode | n_workers | cells | flagged | p99_censored_cells | throughput_mean | throughput_ci_lo | throughput_ci_hi | throughput_completed_mean | error_rate_mean | p50_ms_mean | p95_ms_mean | p99_ms_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| default | 1 | 10 | 0 | 0 | 254.533 | 235.291 | 268.515 | 254.52751 | 0.0 | 4.5919 | 6.8237 | 7.598 |
| default | 10 | 10 | 0 | 0 | 187.269 | 164.812 | 208.269 | 187.23733 | 0.00025 | 6.4758 | 243.9291 | 1044.8591 |
| default | 50 | 10 | 0 | 1 | 153.491 | 140.363 | 163.246 | 152.40695 | 0.00758 | 6.9165 | 707.8353 | 4162.49044 |
| default | 100 | 20 | 0 | 20 | 118.08 | 111.9355 | 123.9785 | 115.31669 | 0.02391 | 7.54435 | 1483.6152 |  |
| deploy | 1 | 10 | 0 | 0 | 372.597 | 365.351 | 379.587 | 372.61243 | 0.0 | 2.8665 | 4.7923 | 5.3691 |
| deploy | 10 | 10 | 0 | 0 | 287.025 | 225.092 | 339.211 | 287.02645 | 0.0 | 5.64 | 124.2348 | 595.098 |
| deploy | 50 | 10 | 0 | 0 | 205.834 | 192.967 | 217.655 | 205.79378 | 0.0002 | 10.7885 | 1461.5535 | 3684.2314 |
| deploy | 100 | 20 | 1 | 0 | 134.067 | 127.4685 | 140.626 | 133.91047 | 0.00127 | 18.5621 | 4199.2887 | 9949.0588 |

Lette dalle tabelle, senza commento: celle segnalate dalla regola di scarto 0 per tutti i gruppi tranne `deploy`/100 writer (1 su 20); a `default`/100 writer tutte le 20 celle hanno il p99 al tetto del timeout di checkout (censurate: la colonna `p99_ms_mean` è vuota); H-M1b è falsificata (27 celle `deploy` su 50 con almeno un errore inatteso: 7 su 10 a 50 writer e 20 su 20 a 100 writer; il tasso di errore medio resta 0,0002 e 0,00127). Il tipo degli errori in M1 non è disponibile (il harness li conta soltanto).

## 2. M2 (braccio `deploy`; `analyze.py m2`, copia integrale)

```
H-M2a/b [all] tail share before lock held = 0.523 [0.510, 0.538] (>= 0.5), commit share = 0.0002 [0.0001, 0.0002] (< 0.01) -> not falsified
H-M2c [all] Gini of per-writer waiting = 0.059 [0.057, 0.061] (<= 0.3 fair serial queue) -> not falsified
H-G1 [all] null-op 37657.6 [34214.6, 41336.7] vs threads completed 152.1 [149.2, 154.7] ops/s: ratio 247.6 (>= 10) -> not falsified
H-G2 [all] processes completed 218.6 [216.1, 221.0] vs threads 152.1 [149.2, 154.7] ops/s: ratio 1.44 (< 2) -> not falsified
H-M2a/b [filtered] tail share before lock held = 0.523 [0.510, 0.538] (>= 0.5), commit share = 0.0002 [0.0001, 0.0002] (< 0.01) -> not falsified
H-M2c [filtered] Gini of per-writer waiting = 0.059 [0.057, 0.061] (<= 0.3 fair serial queue) -> not falsified
H-G1 [filtered] null-op 37657.6 [34269.9, 41477.9] vs threads completed 152.1 [149.2, 154.8] ops/s: ratio 247.6 (>= 10) -> not falsified
H-G2 [filtered] processes completed 218.6 [216.1, 221.0] vs threads 152.1 [149.2, 154.8] ops/s: ratio 1.44 (< 2) -> not falsified
```
Statistiche per cella in `experiments_tnsm/m2_p99_tail/night_20261011/summary.csv` e `summary.md`; insieme "all" (media sulle celle):

| mode | n_workers | cells | flagged | throughput_mean | throughput_completed_mean | throughput_clean_mean | error_rate_mean | timeout_rate_mean | p50_ms_mean | p95_ms_mean | p99_ms_mean | tail_share_to_lock_mean | tail_share_commit_mean | wait_gini_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| null | 100 | 10 | 0 | 37657.593 | 37657.593 |  |  |  |  |  |  |  |  |  |
| processes | 10 | 10 | 0 | 460.6099 | 460.6099 | 429.641 | 0.0 | 0.0 | 3.0034 | 64.6744 | 322.8429 | 0.89487 | 0.00149 | 0.12417 |
| processes | 50 | 10 | 0 | 304.9854 | 304.9121 | 263.0188 | 0.00024 | 0.0 | 3.9217 | 908.3357 | 2392.5853 | 0.6957 | 0.00028 | 0.09003 |
| processes | 100 | 10 | 0 | 218.6365 | 218.5722 | 183.448 | 0.0003 | 0.0 | 4.5505 | 2549.5892 | 5837.4416 | 0.55258 | 0.00014 | 0.08153 |
| threads | 1 | 10 | 0 | 347.5061 | 347.5061 | 342.2937 | 0.0 | 0.0 | 3.0338 | 5.2818 | 6.1622 | 0.20952 | 0.4302 | 0.0 |
| threads | 10 | 10 | 0 | 332.4327 | 332.4327 | 308.2141 | 0.0 | 0.0 | 5.5117 | 114.6329 | 590.9734 | 0.79845 | 0.00097 | 0.06536 |
| threads | 50 | 10 | 0 | 217.9416 | 217.9087 | 189.2056 | 0.00015 | 0.0 | 10.9208 | 1424.8517 | 3293.9093 | 0.65983 | 0.00027 | 0.05634 |
| threads | 100 | 20 | 0 | 152.1783 | 152.10395 | 127.64275 | 0.00049 | 0.0 | 17.67205 | 3801.51125 | 8091.8636 | 0.52311 | 0.00015 | 0.0592 |

Lette dalle tabelle, senza commento: celle segnalate 0 in tutti i gruppi; `timeout_rate_mean` 0,0 in tutti i gruppi con errori misurati (nessun timeout di checkout del pool nel braccio `deploy`); `error_rate_mean` fino a 0,0005 a 100 thread; la quota di coda prima del lock (H-M2a) è 0,523 [0,510; 0,538], vicina alla soglia 0,5 e con IC che non la attraversa.

## 3. Riassunto degli esiti rispetto ai criteri registrati
| Ipotesi | Esito |
|---|---|
| H-M1, braccio `default` (all e filtered) | non falsificata (nessun IC a 100 writer sopra quello a 50) |
| H-M1, braccio `deploy` (all e filtered) | non falsificata |
| H-M1b | **falsificata** (27 su 50 celle `deploy` con errori inattesi; 26 su 49 nel filtrato) |
| H-M1c | non falsificata (deploy 133,9 [127,2; 140,4] contro default 115,3 [109,0; 121,3] ops/s) |
| H-M2a/b | non falsificata (quota 0,523; commit 0,0002) |
| H-M2c | non falsificata (Gini 0,059) |
| H-G1 | non falsificata (rapporto 247,6) |
| H-G2 | non falsificata (rapporto 1,44) |
Censura del pool (M1, tetto a 30 s, riportata a parte): `default` 100 writer 20 su 20 celle censurate, 50 writer 1 su 10; `deploy` 0 celle censurate. Il p99 delle celle censurate non compare in nessuna tabella di latenza.

## 4. Limiti (audit 37 §3, invariati)
Watcher `wan` attivo durante la notte (~0,07 core), G4 non soddisfatta, CPU QEMU generica senza AVX2, Python 3.12.3 sul nodo, primo M1 abortito non mescolato, 20 ripetizioni a 100 writer e 10 altrove. `node_env.json` **non esiste più** sul nodo (ssh di sola lettura autorizzato, `find … -name "node_env*"` su `~/dib_tnsm/out/night_20261011`, profondità 4: nessun risultato). **La mia frase precedente, che diceva la configurazione SQLite non riportabile, era sbagliata:** i `manifest.json` già copiati la contengono (`experiments_tnsm/m1_single_node/night_20261011/manifest.json`, `…/m2_p99_tail/night_20261011/manifest.json`, chiavi `sqlite`, `filesystem`, `fsync_bench_*`, `python_vv`, `g4_host_quiet`):
- Python 3.12.3 (GCC 13.3.0), SQLite 3.45.1; database in `/tmp/dib_tnsm_db`, ext4 su LVM (`/dev/mapper/ubuntu--vg-ubuntu--lv`), 91,2-91,3% usato (3,5-3,7 GB liberi).
- Braccio `default`: `journal_mode` delete, `synchronous` 2, `busy_timeout` 5000, `QueuePool` con `pool_size` 5, `max_overflow` 10, `pool_timeout` 30 s. Braccio `deploy` (M1 e M2): `journal_mode` wal, `synchronous` 2, `busy_timeout` 30000, `pool_size` 100, `max_overflow` 100, `pool_timeout` 30 s, `DIB_SQLITE_WAL=1`, `DIB_SQLITE_POOL_SIZE=100` (valore nel manifest; nelle celle con meno writer la dimensione è `max(writers, 5)` per il docstring di `m1_single_node/run.py`).
- Micro-misura di `fsync` (500 scritture da 4 KiB): prima di M1 p50 2,13 ms, **p99 2024,4 ms, massimo 2059,4 ms**; dopo M1 p99 15,3 ms; prima di M2 p99 15,2 ms; dopo M2 p99 2,2 ms. Riportato come dato, senza spiegazione (non so a cosa sia dovuto lo scarto del p99 prima di M1).
- `g4_host_quiet`: "NOT satisfied" (k3s, un container registry e altre sessioni utente sul nodo). M1 22:58:02-01:25:25 UTC, M2 01:25:26-02:50:10 UTC, `stopped_reason` nullo in entrambi.
