# Audit 110 — B2-kill sul codice finale, DUE SERIE UNITE (30 prove per cella): verdetti dell'audit 99

Pre-registrazione: `docs/audit/99_prereg_B2k_file_finale.md` (addendum 1-3). Prima serie: audit 106 (10 prove per cella, `tree-c898ea8`, seme 20261014, 16:43Z-20:15Z). **Seconda serie** (20 prove per cella, `tree-550afed`: `run.py` con retry del setup di B2k e traccia dei giri di riconciliazione; `service.py` identico `3ffa57ee…`), seme 20261016, 20:16Z → 03:33Z del 13 ottobre, `deploy_b2k_v2.sh`, rc=0, nessun container rimasto. Dati: `experiments_tnsm/final_B2k_b_20261012/` (sha256, 0 differenze, pcap esclusi). Analisi: `analyze_b2k.py` con `pool_cells` (n = 10 + 20), soglie dell'audit 45 invariate.

## Regola L_dns e immagine
L_dns seconda serie: `lan` 2,8 ms, `degraded` 1,3 ms, `wan` 1,5 ms (tutti ≤ 50 ms, poll 0,1 s): tre profili eseguiti. **H-G:** `3ffa57ee…` nei container di tutti i 6 gruppi della seconda serie (e della prima).

## Tabella a 30 prove per cella (28 celle)
| profile | arm | T | k | n | converged | never | median s [CI] | bound s | (d-kill) | (e) violations | excluded |
| degraded | C | 5 | 1 | 30 | 30 | 0 | 2.79 [2.61; 3.17] (n=30) | 7.60 | not falsified | 0 | 0 |
| degraded | C | 15 | 1 | 30 | 30 | 0 | 3.79 [3.64; 4.24] (n=30) | 8.60 | not falsified | 1 | 0 |
| degraded | C | 5 | 10 | 27 | 27 | 0 | 3.27 [2.96; 4.19] (n=27) | 7.60 | not falsified | 1 | {'setup_failed': 3} |
| degraded | C | 15 | 10 | 27 | 27 | 0 | 4.09 [3.64; 4.54] (n=27) | 8.60 | not falsified | 0 | {'setup_failed': 2, 'queues_not_empty_at_start': 1} |
| degraded | D | 5 | 1 | 30 | 30 | 0 | 2.40 [2.15; 3.04] (n=30) | 7.00 | not falsified | 0 | 0 |
| degraded | D | 15 | 1 | 30 | 30 | 0 | 3.10 [2.88; 3.30] (n=30) | 8.00 | not falsified | 0 | 0 |
| degraded | D | 5 | 10 | 30 | 30 | 0 | 2.49 [2.32; 2.81] (n=30) | 7.00 | not falsified | 1 | 0 |
| degraded | D | 15 | 10 | 30 | 30 | 0 | 3.20 [2.69; 3.67] (n=30) | 8.00 | not falsified | 0 | 0 |
| lan | C | 5 | 1 | 30 | 30 | 0 | 0.62 [0.58; 0.76] (n=30) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 1 | 30 | 30 | 0 | 1.18 [0.89; 1.54] (n=30) | 8.00 | not falsified | 0 | 0 |
| lan | C | 5 | 10 | 30 | 30 | 0 | 0.63 [0.59; 0.71] (n=30) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 10 | 30 | 30 | 0 | 1.17 [0.90; 1.46] (n=30) | 8.00 | not falsified | 0 | 0 |
| lan | C | 5 | 50 | 30 | 30 | 0 | 0.69 [0.62; 0.76] (n=30) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 50 | 30 | 30 | 0 | 1.22 [0.99; 1.42] (n=30) | 8.00 | not falsified | 0 | 0 |
| lan | D | 5 | 1 | 30 | 30 | 0 | 0.67 [0.61; 0.80] (n=30) | 7.00 | not falsified | 0 | 0 |
| lan | D | 15 | 1 | 30 | 30 | 0 | 1.24 [0.85; 1.43] (n=30) | 8.00 | not falsified | 0 | 0 |
| lan | D | 5 | 10 | 30 | 30 | 0 | 0.75 [0.66; 0.83] (n=30) | 7.00 | not falsified | 0 | 0 |
| lan | D | 15 | 10 | 30 | 30 | 0 | 1.22 [1.06; 1.52] (n=30) | 8.00 | not falsified | 0 | 0 |
| lan | D | 5 | 50 | 30 | 30 | 0 | 0.69 [0.62; 0.82] (n=30) | 7.00 | not falsified | 0 | 0 |
| lan | D | 15 | 50 | 30 | 30 | 0 | 1.39 [1.03; 1.59] (n=30) | 8.00 | not falsified | 0 | 0 |
| wan | C | 5 | 1 | 30 | 30 | 0 | 1.50 [1.38; 1.56] (n=30) | 7.00 | not falsified | 0 | 0 |
| wan | C | 15 | 1 | 30 | 30 | 0 | 1.91 [1.68; 2.21] (n=30) | 8.00 | not falsified | 0 | 0 |
| wan | C | 5 | 10 | 30 | 30 | 0 | 1.54 [1.47; 1.65] (n=30) | 7.00 | not falsified | 0 | 0 |
| wan | C | 15 | 10 | 30 | 30 | 0 | 2.06 [1.84; 2.28] (n=30) | 8.00 | not falsified | 0 | 0 |
| wan | D | 5 | 1 | 30 | 30 | 0 | 1.35 [1.26; 1.46] (n=30) | 7.00 | not falsified | 0 | 0 |
| wan | D | 15 | 1 | 30 | 30 | 0 | 1.86 [1.52; 2.17] (n=30) | 8.00 | not falsified | 0 | 0 |
| wan | D | 5 | 10 | 30 | 30 | 0 | 1.38 [1.29; 1.49] (n=30) | 7.00 | not falsified | 0 | 0 |
| wan | D | 15 | 10 | 30 | 30 | 0 | 1.85 [1.57; 2.21] (n=30) | 8.00 | not falsified | 0 | 0 |

## Verdetti come pre-registrati
- **(d-kill) mediana contro il limite: NON falsificata in 0 celle su 28.** Mediane di convergenza dopo il riavvio: `lan` 0,62-1,39 s, `wan` 1,35-2,06 s, `degraded` 2,40-4,09 s, contro limiti di 7,0-8,6 s. Con n = 30 gli intervalli sono stretti (per esempio `lan` C T 15 k 50: 1,22 s [0,99; 1,42]; `lan` D k 50 T 5: 0,69 s [0,62; 0,82]). **Il caso più forte è k = 50 a `lan`:** convergenza mediana 0,69-1,39 s per 50 fatti, 6 celle × 30 prove, nessuna violazione.
- **(e) correttezza: FALSIFICATA da 3 prove su 840**, tutte a `degraded` e solo sul TEMPO (stati finali tutti `monitor-only`, 8 590 righe, nessuna violazione di stato):
  - D, T 5, k 10, prova 4 (prima serie): 7,097 s contro 7,0 s (+0,097 s);
  - C, T 15, k 1, prova 3 (prima serie): 11,605 s contro 8,6 s (+3,0 s); primo giro visibile a +10,07 s;
  - C, T 5, k 10, prova 0 (seconda serie): 11,555 s contro 7,6 s (+3,95 s); **il log del sito 3 riporta `reconcile attempt 1 failed: ConnectTimeout('_ssl.c:993: The handshake operation timed out')` a `service.py:699`** (`httpx.get` di `/pending` con `RECONCILE_TIMEOUT` 5 s) e il primo giro che l'evidence vede è a +10,71 s: **meccanismo osservato nei dati, non dedotto**, per la sola prova della seconda serie. Le due della prima serie non avevano la traccia: stessa forma, non verificata.
  - Frequenza a `degraded`: D 1/120 (0,8 %), C 2/120 (1,7 %). Nessuna a `lan` (240 prove) né a `wan` (240 prove).
- **(f) (da D1): REGGE.** Nessuna riga `staging` o `committing` negli stati finali.
- **T15 − T5 (descrittiva, n = 30):** da 0,41 s a 0,99 s a `wan` e `degraded` (esempi: `degraded` C k 1 0,99 s [0,58; 1,46]; `wan` C k 10 0,52 s [0,24; 0,77]; `lan` k 50 0,53-0,70 s), dentro il riferimento [0; 1,5] s di audit 45 e con intervalli molto più stretti di n = 10; nessun criterio (decisione Q9).

## Esclusioni e setup
- Prima serie: 5 prove escluse in `degraded`/C (k = 10) per setup senza retry (audit 106). Seconda serie: **0 `setup_failed`**, 16 ritentativi del setup recuperati (`degraded` D 1, `degraded` C 15), e 1 prova esclusa per `queues_not_empty_at_start` (`degraded` C). Per questo due celle hanno n = 27 (`degraded` C, k = 10).

## Cosa si può dire e cosa no
- Si può dire: dopo la morte e il riavvio di un sito, **la convergenza mediana è di 0,6-4,1 s nei tre profili, fino a k = 50 fatti a `lan`**, con un limite superiore di 7-8,6 s non superato dalla mediana in nessuna delle 28 celle.
- Non si può dire che nessuna prova superi il limite: a `degraded` lo supera lo 0,8 % (D) e l'1,7 % (C) delle prove; con mTLS la causa osservata è un timeout di handshake nel primo tentativo di riconciliazione (5 s) seguito da un secondo tentativo.

## Limiti
Due serie a orari diversi sullo stesso nodo (CPU QEMU senza AVX2); la prima senza retry nel setup e senza traccia; la causa delle due code della prima serie non è osservata; una macchina.
