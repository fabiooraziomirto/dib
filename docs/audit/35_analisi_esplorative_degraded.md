# Audit 35 — Analisi esplorative e di sensibilità su B1 `degraded` (dati già copiati, nessun accesso al nodo)

Dati: `experiments_tnsm/m67_retraction/block_degraded_lan_after_20261011/` (`<blk>`, commit `c087f70`); confronto con `block_lan_before_20261011/` e `wan_20261011/b1/`. **Tutto quanto segue è esplorativo o di sensibilità: non cambia i verdetti registrati di (a) (falsificata in 4/4 celle) e (c) (non falsificata), né criteri, soglie, intervalli.** Nessuna causa è proposta. Le definizioni di §B sono scritte e committate PRIMA di ogni calcolo; i risultati sono in §C (aggiunta successiva, con le uscite integrali degli script).

## A. Controlli già chiusi (nessun nuovo accesso al nodo)
- **Esclusi** (`<blk>/analysis_degraded.md:10-13,19-22`): C 4 (C/1 2, C/10 2), D 4 (D/1 3 = 1 `client_timeout` + 2 `transport_error_setup`; D/10 1); totale 8 su 200 (7 `transport_error_setup`, 1 `client_timeout`). Gli errori di setup avvengono prima di t0 (`run.py:620` fase `setup` fino a t0, `run.py:633` fase `measured`; `excluded_reason` = `transport_error_<fase>` a `run.py:659`): nessuna consegna manca dal denominatore di (c).
- **`state.json` contro le due letture** (eventi: `<blk>/BLOCK.json` non li contiene; li ho letti dal nodo alle 14:43:22 e riportati in audit 34 §1): alle **14:42:17** i `b1_end` con ora ≤ 14:42:17 sono 6 (`degraded` C_f10 13:37:43, D_f1 13:56:42, C_f1 14:26:39, D_f10 14:39:15; `lan_after` C_f10 14:40:27, D_f1 14:41:18): il conteggio 6 **torna**. L'ultimo `b1_start` a quell'ora è `lan_after` **C_f1** alle 14:41:18,141, preceduto da `b1_end` `lan_after` D_f1 (14:41:18,141) e `b1_start` D_f1 (14:40:27,467): l'estratto filtrato (che non stampava il campo `block`) **torna**; il `run.py` di 59 s e i 3 container "Up 54-58 s" della stessa lettura sono coerenti con un avvio alle 14:41:18. Alle **14:43:22**: 8 `b1_end`, `lan_confirmed`, `block_end`, `done` (14:43:20,070), `DONE` presente: **torna**. L'incoerenza che avevo segnalato in audit 34 §9 era una mia lettura errata del filtro (corretta lì).
- **Battito a 3,3 s** (14:42:14,153 contro 14:42:17,502): `netem_watch2.sh:23` dichiara il rinnovo ogni ~2 s ("refreshed every ~2 s"); 3,3 s supera i 2 s nominali di 1,3 s (con un'applicazione in corso, che non verifico) ed è sotto la soglia di stop di 10 s. Nessuna azione (decisione dell'utente).

## B. Definizioni (scritte prima dei calcoli)
Script: `experiments_tnsm/m67_retraction/analyze_exploratory_degraded.py` (da scrivere con test su dati sintetici; stessi `RES = 10000`, `SEED = 20261011` e bootstrap percentile di `analyze_b1.py:64-84`). **Episodio valido** = non escluso e con `dispute_rtt_s` (come in `analyze_c.py`, punto 6). **Sito in pending** = sito con riga di ack dopo t0 (`plog_ack_ts` non nullo) oppure ancora in `pending_left` alla scadenza (`run.py:372-377`; `analyze_c.py:row_pending_sites`).

### B1. Sensibilità di (c) al `client_timeout` di D/1
L'episodio escluso di D/1 per `client_timeout` non ha `dispute_rtt_s` e conta 0 in x e n nella definizione registrata (D = 9/960). Caso peggiore: lo si aggiunge con 10 consegne in n e x_ep ∈ {0, 10}: S0 registrata 9/960; S_a 9/970; S_b 19/970. Per ciascuno: IC di Clopper-Pearson 95% (`analyze_c.clopper_pearson`), classificazione contro [0,004; 0,015] (`analyze_c.classify`) e seconda clausola (C invariato 32/960, `analyze_c.second_clause`). Si riporta se la classificazione di D cambia rispetto a S0 ("CI crosses a bound: inconclusive"). Gli altri 7 esclusi (`transport_error_setup`) non entrano: avvengono prima di t0.

### B2. Sensibilità di (a) alla selezione
Per ogni episodio valido, per ogni sito: se pending (def. sopra) con ack non nullo: `plog_ack_ts − t0`; altrimenti `plog_apply_ts − t0` (se nullo e il sito non è pending: episodio "non misurabile", contato e fuori dalla mediana); se pending senza ack (solo `pending_left`): episodio "non drenato", contato e fuori. Tempo dell'ultimo sito dell'episodio = max sui 10 siti. Per cella: mediana con IC bootstrap su TUTTI gli episodi validi misurabili e n, accanto alla mediana registrata (`<blk>/analysis_degraded.md:68-71`, episodi senza pending, n = 31/35/41/46) e alla soglia registrata (12240,1 / 1267,4 / 8146,3 / 862,1 ms). Colonna informativa "mediana − soglia registrata": **non è un verdetto** e non sostituisce quello registrato.

### B3. Tempi per sito, solo descrittivo
**FANOUT 1:** popolazione = episodi validi senza siti pending, con i 10 `plog_apply_ts` presenti e non decrescenti nell'ordine degli id dei siti 0…9 (ordine di consegna a FANOUT 1, verificato sui dati: gli episodi che non lo rispettano sono contati e riportati, non scartati in silenzio). Posizione 0: `apply[0] − t0`; posizioni k = 1…9: `apply[k] − apply[k−1]`. Per braccio e posizione: n, min, p25, mediana, p75, p95, max (s); in più istogramma di tutti gli scarti delle posizioni 1…9 per braccio con classi di 0,25 s. **FANOUT 10:** popolazione = episodi validi senza siti pending con i 10 `plog_apply_ts` presenti: tempo massimo per episodio (n, min, p25, mediana, p75, p95, max; istogramma con classi di 0,5 s). "Piano di base" della cella = mediana di `withdrawn_plog_s` su tutti i siti con valore degli episodi non esclusi (valore fissato ora, prima del calcolo); un sito è "sopra il piano di base" se `withdrawn_plog_s` > piano + 0,25 s (soglia fissata ora). Si riportano: siti totali, siti sopra il piano, distribuzione per episodio del numero di siti sopra il piano (tutti gli episodi validi, siti con valore), istogramma di (valore − piano) in classi di 0,5 s.

### B4. Percorso via pending contro B_online
Popolazione = tutti i siti in pending degli episodi validi (attesi 41: 18+14+6+3). B_online = 10,5 s (D) e 11,1 s (C) (`docs/audit/14_priorita_esperimenti_tnsm.md:94,204-207`, T = 5, mTLS per C), definito dall'inserimento in coda. Per sito: (i) `u = plog_ack_ts − t0`, limite superiore del tempo dall'inserimento; (ii) solo a FANOUT 1 e solo se stimabile: `e = plog_ack_ts − apply_prev` con `apply_prev` = `plog_apply_ts` del sito con id precedente (per il sito 0: t0); non stimabile se il precedente ha `plog_apply_ts` nullo (è anch'esso pending/senza apply). A FANOUT 10 (consegne concorrenti da t0) la stima (ii) non è definita. Per braccio e FANOUT: n siti, n con stima (ii), quanti superano B_online con (i) e con (ii), massimo e mediana di ciascuna, `n_pending_undrained` e `n_pending_unmeasured` dai riepiloghi di cella, e quanti siti in `pending_left` (nessun ack) esistono.

### B5. Nota aritmetica POST-HOC (calcolata sugli stessi dati che hanno falsificato (a))
Ipotesi del calcolo (dichiarate, non verificate): una consegna va in pending dopo `_FANOUT_RETRIES = 3` tentativi falliti di 1 s (`service.py:120-121`, `_deliver_to_site` a `:700-720`); tentativi indipendenti con probabilità di fallimento p; frequenza di pending q = x/n ⇒ p = q^(1/3). Per braccio (pooled e per FANOUT; anche agli estremi dell'IC di Clopper-Pearson di (c)): F = numero di tentativi falliti di una consegna ∈ {0,1,2,3} con P(F=0) = 1−p, P(F=k) = p^k(1−p) (k = 1,2), P(F=3) = p³; E[F] = p + p² + p³. **FANOUT 1:** tentativi falliti attesi per episodio = 10·E[F]; tempo extra atteso = 1 s × quel numero. **FANOUT 10:** massimo atteso E[max_{10 siti} F_i] (calcolo esatto) e tempo extra = 1 s × quel valore. Controllo con simulazione Monte Carlo (seme 20261011, 200 000 episodi). Confronto con l'eccesso osservato: (mediana registrata − predizione di (a)) e (eccesso sulla soglia registrata) per cella, da `<blk>/analysis_degraded.md:68-71`. Nessuna affermazione che il calcolo spieghi o confermi l'eccesso. Limiti da riportare: le mediane registrate sono su episodi senza pending, il calcolo no; il costo di un tentativo è assunto 1 s.

### B6. Tabella riassuntiva per il paper
Righe: `lan` prima (`block_lan_before_20261011/lan_before`), `lan` dopo (`<blk>/lan_after`), `wan` rilancio (`wan_20261011/b1`), `degraded` (`<blk>/degraded`); per braccio e FANOUT: mediana dell'ultimo sito (P-log-apply, **solo episodi senza pending**, `analyze_b1.last_site`) in ms con IC bootstrap e n; se il P-log è accettato (`plog_acceptable_rule_10pct`) — se no, la cella è marcata "P-log non accettato"; quota di consegne in pending x/n (`analyze_c.counts_from_cells`); esclusi per cella. Le altre sessioni `lan` (audit 24-26, 28) non sono incluse.

## C. Risultati

Esecuzione: `analyze_exploratory_degraded.py` (commit `2243865`, scritto dopo le definizioni di `55b29a3`; 9 test sintetici scritti prima del codice, rossi per modulo mancante, 3 mutazioni rilevate: ultimo sito con ack, violazioni dell'ordine, predecessore). Suite completa `experiments_tnsm/common experiments_tnsm/m67_retraction`: **215 passati** (101,9 s). Uscita integrale (copia esatta di `experiments_tnsm/m67_retraction/block_degraded_lan_after_20261011/analysis_exploratory_degraded.md`, 128 righe) in §C.1; letture dei numeri in §C.2 (solo confronti con i valori registrati, nessuna causa).

### C.1 Uscita integrale

# Exploratory / sensitivity analyses, B1 `degraded` (definitions: docs/audit/35 section B, committed 55b29a3 before any computation)

## B1. Sensitivity of (c) to the `client_timeout` episode of D/1 (registered D = 9/960, C = 32/960)
Episodes excluded for `client_timeout` in D cells: 1 (counted as 10 deliveries in n in the worst cases).

| scenario | x/n | share | CP 95% CI | classification vs D [0.004, 0.015] | changed vs S0 | second clause |
|---|---|---|---|---|---|---|
| S0 | 9/960 | 0.00937 | [0.00430; 0.01772] | CI crosses a bound: inconclusive | False | satisfied: the CI of C lies entirely above the CI of D (point estimates C 0.03333, D 0.00937) |
| S_a | 9/970 | 0.00928 | [0.00425; 0.01754] | CI crosses a bound: inconclusive | False | satisfied: the CI of C lies entirely above the CI of D (point estimates C 0.03333, D 0.00928) |
| S_b | 19/970 | 0.01959 | [0.01183; 0.03042] | CI crosses a bound: inconclusive | False | inconclusive for this clause: the CIs overlap (point estimates C 0.03333, D 0.01959; point estimate of C above D, information only) |

## B2. Sensitivity of (a) to the selection: last site over ALL valid episodes (pending sites by their ack time)
No verdict: the registered one is in analysis_degraded.md:68-71. 'registered' = episodes without pending (analyze_b1.last_site).

| cell | all valid, median ms [CI] (n) | unmeasurable / undrained | registered, median ms [CI] (n) | registered threshold ms | all-valid median − threshold ms (information) | all-valid median − registered median ms |
|---|---|---|---|---|---|---|
| C/1 | 19322.36 [16964.61; 20584.00] (48) | 0 / 0 | 17022.36 [15615.42; 19323.99] (31) | 12240.1 | 7082.3 | 2300.0 |
| C/10 | 3420.38 [2733.97; 3825.86] (48) | 0 / 0 | 2824.58 [2422.25; 3418.70] (35) | 1267.4 | 2153.0 | 595.8 |
| D/1 | 10783.83 [10164.55; 11672.11] (47) | 0 / 0 | 10669.83 [9769.59; 11177.69] (41) | 8146.3 | 2637.5 | 114.0 |
| D/10 | 2016.93 [1621.59; 2020.18] (49) | 0 / 0 | 2016.77 [1621.25; 2019.21] (46) | 862.1 | 1154.8 | 0.2 |

## B3. Per-site times (descriptive)

### FANOUT 1: delivery cost = gap between consecutive `plog_apply_ts` in id order (position 0: apply[0] − t0), seconds; episodes without pending, id order monotone

**D/1**: episodes used 41, with pending (left out) 6, order violations 0

| position | stats (s) |
|---|---|
| 0 | n=41 min 0.609 p25 0.611 med 0.613 p75 0.618 p95 1.613 max 2.617 |
| 1 | n=41 min 0.804 p25 0.807 med 0.807 p75 0.808 p95 2.613 max 3.119 |
| 2 | n=41 min 0.803 p25 0.806 med 0.807 p75 0.809 p95 2.208 max 2.611 |
| 3 | n=41 min 0.803 p25 0.804 med 0.805 p75 0.809 p95 2.210 max 4.011 |
| 4 | n=41 min 0.804 p25 0.805 med 0.807 p75 1.310 p95 2.171 max 2.210 |
| 5 | n=41 min 0.804 p25 0.805 med 0.805 p75 1.807 p95 2.610 max 4.014 |
| 6 | n=41 min 0.803 p25 0.804 med 0.805 p75 0.806 p95 2.207 max 2.609 |
| 7 | n=41 min 0.803 p25 0.804 med 0.805 p75 0.808 p95 3.118 max 4.014 |
| 8 | n=41 min 0.803 p25 0.804 med 0.805 p75 0.806 p95 1.807 max 3.715 |
| 9 | n=41 min 0.804 p25 0.804 med 0.805 p75 0.805 p95 2.208 max 4.925 |

histogram of gaps at positions 1-9 (class width 0.25 s, left edge: count): {0.75: 285, 1.25: 18, 1.5: 2, 1.75: 26, 2.0: 13, 2.25: 2, 2.5: 10, 2.75: 1, 3.0: 6, 3.5: 1, 4.0: 4, 4.75: 1}

**C/1**: episodes used 31, with pending (left out) 17, order violations 0

| position | stats (s) |
|---|---|
| 0 | n=31 min 1.012 p25 1.015 med 1.017 p75 1.022 p95 2.421 max 2.927 |
| 1 | n=31 min 1.207 p25 1.209 med 1.211 p75 3.014 p95 5.526 max 7.229 |
| 2 | n=31 min 1.207 p25 1.210 med 1.212 p75 2.413 p95 3.419 max 3.422 |
| 3 | n=31 min 1.207 p25 1.208 med 1.210 p75 2.211 p95 3.768 max 4.821 |
| 4 | n=31 min 1.208 p25 1.208 med 1.210 p75 2.411 p95 3.419 max 3.520 |
| 5 | n=31 min 1.207 p25 1.209 med 1.209 p75 1.716 p95 3.771 max 4.418 |
| 6 | n=31 min 1.207 p25 1.209 med 1.210 p75 1.913 p95 3.014 max 6.228 |
| 7 | n=31 min 1.208 p25 1.209 med 1.715 p75 2.611 p95 3.568 max 4.027 |
| 8 | n=31 min 1.207 p25 1.209 med 1.209 p75 1.891 p95 3.868 max 5.731 |
| 9 | n=31 min 1.207 p25 1.208 med 1.209 p75 1.710 p95 3.089 max 3.419 |

histogram of gaps at positions 1-9 (class width 0.25 s, left edge: count): {1.0: 175, 1.5: 22, 2.0: 20, 2.5: 16, 3.0: 19, 3.25: 7, 3.5: 7, 3.75: 1, 4.0: 3, 4.25: 3, 4.75: 2, 5.5: 1, 6.0: 2, 7.0: 1}

### FANOUT 10: maximum per episode (episodes without pending), base plane and sites above it (base + 0.25 s)

**D/10**: max per episode n=46 min 0.615 p25 1.618 med 2.017 p75 2.101 p95 3.018 max 3.421; histogram (0.5 s): {0.5: 1, 1.0: 6, 1.5: 13, 2.0: 16, 2.5: 6, 3.0: 4}
base plane (median of withdrawn_plog_s, all non-excluded sites with a value) 0.617 s; sites total 490, above the base 101; number of sites above per valid episode {k: episodes} {0: 1, 1: 18, 2: 12, 3: 13, 4: 5}; histogram of (value − base) in 0.5 s classes {-0.5: 245, 0.0: 145, 0.5: 38, 1.0: 50, 1.5: 5, 2.0: 6, 2.5: 1}

**C/10**: max per episode n=35 min 1.023 p25 2.421 med 2.825 p75 3.624 p95 4.266 max 4.634; histogram (0.5 s): {1.0: 1, 1.5: 1, 2.0: 13, 2.5: 5, 3.0: 6, 3.5: 6, 4.0: 2, 4.5: 1}
base plane (median of withdrawn_plog_s, all non-excluded sites with a value) 1.021 s; sites total 474, above the base 127; number of sites above per valid episode {k: episodes} {0: 3, 1: 8, 2: 14, 3: 12, 4: 5, 5: 5, 10: 1}; histogram of (value − base) in 0.5 s classes {-0.5: 237, 0.0: 119, 0.5: 32, 1.0: 41, 1.5: 18, 2.0: 15, 2.5: 7, 3.0: 4, 3.5: 1}

## B4. Pending path against B_online (D 10.5 s, C 11.1 s): u = ack − t0 (upper bound); e = ack − apply of the previous site (FANOUT 1 only)

| cell | pending sites (with ack) | in pending_left without ack | n_pending_undrained / unmeasured (cell summary) | exceed B_online with u | estimable e | exceed with e | max u | median u | max e | median e |
|---|---|---|---|---|---|---|---|---|---|---|
| C/1 | 18 | 0 | 0 / 0 | 15 | 18 | 5 | 31.46 | 18.43 | 17.78 | 9.32 |
| C/10 | 14 | 0 | 0 / 0 | 6 | 0 | n/a | 16.00 | 10.49 | n/a | n/a |
| D/1 | 6 | 0 | 0 / 0 | 4 | 6 | 0 | 17.96 | 11.61 | 8.89 | 8.01 |
| D/10 | 3 | 0 | 0 / 0 | 0 | 0 | n/a | 9.67 | 8.82 | n/a | n/a |

Per-site list (cell, episode order not kept: site id, u s, e s):
- C/1: s6 u=31.46 e=17.78; s6 u=19.60 e=8.30; s1 u=9.64 e=8.62; s9 u=23.25 e=8.24; s9 u=30.42 e=9.60; s3 u=16.52 e=6.97; s0 u=15.37 e=15.37; s0 u=5.36 e=5.36; s2 u=11.30 e=8.67; s4 u=17.25 e=9.20; s7 u=23.63 e=9.34; s8 u=25.28 e=10.57; s1 u=13.75 e=12.23; s9 u=23.93 e=10.02; s8 u=23.63 e=12.25; s0 u=9.23 e=9.23; s4 u=16.01 e=11.36; s6 u=20.56 e=9.29
- C/10: s0 u=15.93; s6 u=9.97; s6 u=9.97; s4 u=12.60; s2 u=7.89; s2 u=11.59; s4 u=16.00; s2 u=13.09; s1 u=9.70; s1 u=11.01; s8 u=9.19; s9 u=13.09; s2 u=6.24; s6 u=8.04
- D/1: s2 u=12.12 e=8.89; s8 u=17.96 e=8.49; s2 u=7.32 e=5.91; s1 u=8.22 e=7.61; s5 u=11.10 e=6.46; s8 u=16.96 e=8.40
- D/10: s7 u=9.67; s9 u=8.44; s0 u=8.82

## B5. POST-HOC arithmetic (computed on the same data that falsified (a); independence of attempts assumed; 3 attempts of 1 s, service.py:120-121)

| arm | pending share q (x/n) | p = q^(1/3) | E[failed attempts] per delivery | expected failed attempts per episode FANOUT 1 (10 deliveries) | E[max over 10 sites] failed attempts FANOUT 10 | MC check (seed 20261011, 200000) F1 / F10 |
|---|---|---|---|---|---|---|
| D (point) | 0.00937 | 0.2109 | 0.2647 | 2.647 | 1.362 | 2.651 / 1.365 |
| D (CI low) | 0.00430 | 0.1626 | 0.1933 | 1.933 | 1.107 | 1.936 / 1.111 |
| D (CI high) | 0.01772 | 0.2607 | 0.3464 | 3.464 | 1.620 | 3.469 / 1.622 |
| D FANOUT 1 only | 6/470 = 0.01277 | 0.2337 | 0.3011 | 3.011 | 1.481 | — |
| D FANOUT 10 only | 3/490 = 0.00612 | 0.1829 | 0.2225 | 2.225 | 1.215 | — |
| C (point) | 0.03333 | 0.3218 | 0.4587 | 4.587 | 1.932 | 4.593 / 1.931 |
| C (CI low) | 0.02291 | 0.2840 | 0.3876 | 3.876 | 1.740 | 3.881 / 1.742 |
| C (CI high) | 0.04673 | 0.3602 | 0.5367 | 5.367 | 2.120 | 5.370 / 2.120 |
| C FANOUT 1 only | 18/480 = 0.03750 | 0.3347 | 0.4843 | 4.843 | 1.996 | — |
| C FANOUT 10 only | 14/480 = 0.02917 | 0.3078 | 0.4317 | 4.317 | 1.861 | — |

Comparison with the observed excess (a), seconds; expected extra time = 1 s × expected failed attempts (point estimate of the pooled q):

| cell | observed median − predicted (s) | registered excess over threshold (s) | expected extra time from the arithmetic (s) |
|---|---|---|---|
| C/1 | 5.02 | 4.78 | 4.59 |
| C/10 | 1.62 | 1.56 | 1.93 |
| D/1 | 2.67 | 2.52 | 2.65 |
| D/10 | 1.22 | 1.15 | 1.36 |

Limits: the observed medians are over episodes WITHOUT pending, the arithmetic is not; the cost of a failed attempt is assumed 1 s; no statement that the arithmetic explains or confirms the excess.

## B6. Summary table (last-site P-log-apply, ONLY episodes without pending; pending share over all valid episodes; excluded per cell)

| profile | arm | FANOUT | median last site ms [95% CI] | n (episodes without pending) | P-log accepted | pending x/n | excluded |
|---|---|---|---|---|---|---|---|
| lan (before) | C | 1 | 74.14 [70.90; 82.07] | 10 | yes | 0/100 | 0 |
| lan (before) | C | 10 | 22.46 [20.29; 23.59] | 10 | NO (not accepted) | 0/100 | 0 |
| lan (before) | D | 1 | 45.71 [43.11; 54.78] | 10 | yes | 0/100 | 0 |
| lan (before) | D | 10 | 20.71 [18.86; 22.63] | 10 | NO (not accepted) | 0/100 | 0 |
| lan (after) | C | 1 | 80.04 [75.56; 86.62] | 10 | yes | 0/100 | 0 |
| lan (after) | C | 10 | 19.65 [19.20; 22.05] | 10 | NO (not accepted) | 0/100 | 0 |
| lan (after) | D | 1 | 48.76 [43.80; 55.76] | 10 | yes | 0/100 | 0 |
| lan (after) | D | 10 | 18.86 [17.63; 22.12] | 10 | NO (not accepted) | 0/100 | 0 |
| wan (rilancio) | C | 1 | 4827.72 [4809.59; 5427.32] | 10 | yes | 0/100 | 0 |
| wan (rilancio) | C | 10 | 429.26 [420.20; 1017.98] | 10 | yes | 0/100 | 0 |
| wan (rilancio) | D | 1 | 3191.84 [3174.33; 3824.47] | 10 | yes | 0/100 | 0 |
| wan (rilancio) | D | 10 | 258.97 [256.75; 591.89] | 10 | yes | 0/100 | 0 |
| degraded | C | 1 | 17022.36 [15615.42; 19323.99] | 31 | yes | 18/480 | 2 |
| degraded | C | 10 | 2824.58 [2422.25; 3418.70] | 35 | yes | 14/480 | 2 |
| degraded | D | 1 | 10669.83 [9769.59; 11177.69] | 41 | yes | 6/470 | 3 |
| degraded | D | 10 | 2016.77 [1621.25; 2019.21] | 46 | yes | 3/490 | 1 |

### C.2 Cosa mostrano i numeri (solo fatti; nessuna causa, nessun cambio di verdetto)
- **B1.** La classificazione di D non cambia in nessuno dei tre scenari ("CI crosses a bound: inconclusive": S0 9/960, S_a 9/970, S_b 19/970 con IC [0,01183; 0,03042]). Cambia la seconda clausola in S_b: da "satisfied" (S0, S_a) a "inconclusive for this clause: the CIs overlap" (non falsificata). Per (c) quindi: nel caso peggiore S_b nessun braccio è falsificato.
- **B2.** Su tutti gli episodi validi misurabili (0 non misurabili, 0 non drenati) le mediane sono ≥ quelle registrate: C/1 19322,36 contro 17022,36 ms (+2300,0), C/10 3420,38 contro 2824,58 (+595,8), D/1 10783,83 contro 10669,83 (+114,0), D/10 2016,93 contro 2016,77 (+0,2). Le differenze dalla soglia registrata (colonna informativa, non un verdetto) restano positive in tutte le celle (7082,3, 2153,0, 2637,5, 1154,8 ms). Il verdetto registrato non è modificato.
- **B3.** FANOUT 1: gli scarti mediani fra consegne consecutive sono 0,805-0,807 s (D) e 1,209-1,212 s (C) in 8 posizioni su 9 per D e in 8 su 9 per C (C posizione 7: mediana 1,715); le code (p95) arrivano a 2,2-3,1 s (D) e 3,0-5,5 s (C) con massimi 4,9 s (D, posizione 9) e 7,2 s (C, posizione 1); la posizione 0 ha mediana 0,613 s (D) e 1,017 s (C). Istogrammi nell'uscita. FANOUT 10: massimo per episodio mediana 2,017 s (D, n = 46) e 2,825 s (C, n = 35); piano di base 0,617 s (D) e 1,021 s (C); siti sopra il piano (> piano + 0,25 s): D 101 su 490, C 127 su 474; il numero di siti sopra il piano per episodio va da 0 a 4 per D e da 0 a 5 per C, con **un episodio di C con 10 siti sopra il piano**.
- **B4.** I siti in pending con ack sono 41 (C/1 18, C/10 14, D/1 6, D/10 3); nessuno resta in `pending_left` senza ack (0); `n_pending_undrained` e `unmeasured` 0 in tutte le celle. Con `u` (ack − t0) superano B_online: C/1 15 su 18, C/10 6 su 14, D/1 4 su 6, D/10 0 su 3; massimo `u` 31,46 s (C/1). Con `e` (a FANOUT 1, tutti stimabili: 18 e 6): C/1 5 su 18 superano 11,1 s (massimo 17,78 s, mediana 9,32 s), D/1 0 su 6 superano 10,5 s (massimo 8,89 s, mediana 8,01 s). **Nota di lettura del codice (non dei dati):** `e` è misurato dal momento in cui la sequenza ha raggiunto il sito, mentre l'inserimento in coda avviene dopo i tentativi diretti falliti (`service.py:700-722`, `INSERT INTO pending_fanout` a `:719-720`, dopo il ciclo di `_FANOUT_RETRIES` = 3 tentativi da 1 s, `:120-121`): il tempo dall'inserimento è quindi ≤ `e`, e `e` è anch'esso un limite superiore, più stretto di `u`.
- **B5 (POST-HOC, stessi dati che hanno falsificato (a); indipendenza assunta, 1 s per tentativo).** Stima puntuale pooled: D q = 0,00937 ⇒ p = 0,2109, 2,647 tentativi falliti attesi per episodio a FANOUT 1 e 1,362 come massimo atteso a FANOUT 10; C q = 0,03333 ⇒ p = 0,3218, 4,587 e 1,932 (simulazione Monte Carlo concorde: 2,651/1,365 e 4,593/1,931). Confronto per cella (s): osservato mediana − predizione / eccesso registrato sulla soglia / extra atteso dall'aritmetica: C/1 5,02 / 4,78 / 4,59; C/10 1,62 / 1,56 / 1,93; D/1 2,67 / 2,52 / 2,65; D/10 1,22 / 1,15 / 1,36. Limiti: le mediane osservate sono su episodi senza pending, l'aritmetica no; 1 s per tentativo assunto; **non dico che l'aritmetica spieghi né confermi l'eccesso**.
- **B6.** Tabella in §C.1. P-log non accettato nelle quattro celle FANOUT 10 delle due sessioni `lan` (la misura registrata lì è dispute-rtt: `analysis_lan_before.md`, `analysis_lan_after.md`); accettato in tutte le altre. Le quote di pending sono 0/100 per ogni cella `lan` e `wan`, e 18/480, 14/480, 6/470, 3/490 a `degraded`. **Differenza di forma da segnalare:** gli IC bootstrap delle righe `lan` della tabella differiscono di 0,05-0,16 ms da quelli di `analysis_lan_*.md` (es. D/10 `lan` prima [18,86; 22,63] contro [18,92; 22,63]; C/10 `lan` dopo [19,20; 22,05] contro [19,20; 22,01]) perché `summary_row` inizializza un nuovo `random.Random(SEED)` per cella mentre `analyze_b1.py` condivide un solo generatore fra le celle; le mediane coincidono e gli IC registrati restano quelli delle analisi originali. A `degraded` gli IC coincidono con quelli registrati.

## D. Stato
Eseguito solo §B su dati già copiati; nessun accesso al nodo, nessun nuovo blocco di rete, nessuna modifica a `code/src`, `service.py`, `results/`, ai file congelati; nessun sudo. Verdetti registrati di (a) (falsificata 4/4) e (c) (non falsificata) invariati. In attesa delle decisioni dell'utente.
