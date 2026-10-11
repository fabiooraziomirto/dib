# Audit 37 — Pre-registrazione dell'analisi di M1/M2 della notte 2026-10-10/11 (scritta PRIMA di copiare o leggere un solo dato)

Data: 2026-10-11 sera. Dati: 100 celle M1 (22:58-01:25 UTC) e 90 celle M2 (01:25-02:50 UTC), `ritorno 0`, **non analizzati** (`docs/audit/21_rapporto_notte.md` §1; `experiments_tnsm/m67_retraction/night_wan_20261011/m1_STATE.md`, `m2_STATE.md`); gli output pesanti sono sul nodo in `~/dib_tnsm/out/night_20261011/run/{m1,m2}/` (audit 21 intro). Nessun file di M1/M2 della notte è stato copiato o aperto da questa sessione prima di questo commit. Questo documento **non cambia** ipotesi, criteri, regola di scarto né codice di analisi: li cita dove sono già stati committati prima delle misure.

## 1. Cosa è già registrato (committato prima della notte)
| Elemento | Dove | Commit (prima del lancio, 2026-10-10 +0200) |
|---|---|---|
| H-M1, H-M1b, H-M1c e falsificazioni | `experiments_tnsm/m1_single_node/run.py:9-31` | `c23d1e3` 18:14, braccio `deploy` aggiunto in `a90b27a` 19:22 |
| H-M2a, H-M2b, H-M2c, H-G1, H-G2, celle e controlli GIL | `experiments_tnsm/m2_p99_tail/run.py:1-49` e oltre (strumentazione `instrument.py`) | `f6d1c28` 18:30 (riformulazione), `a90b27a` 19:22 |
| Regola di scarto (other_cores > 1,0 core o steal_pct > 2%) e baseline senza DIB | `experiments_tnsm/common/discard_rule.json` (60 campioni, other_cores max 0,280, steal max 0,038) | `c23d1e3`, "fissata prima di ogni cella" |
| Codice di analisi: unità = cella, bootstrap percentile 95% sulle celle, 10 000 ricampionamenti, seme 20261010; "all" e "filtered"; censura p99 ≥ 29,9 s con errori inattesi (`p99_censored_cells`) | `experiments_tnsm/common/analyze.py:1-32` (`CENSOR_MS = 29_900.0`) | `c23d1e3`/`f6d1c28` |
| Tre definizioni di throughput (`throughput`, `throughput_completed`, `throughput_clean` solo M2) | `analyze.py:16-22`, audit 04 §7.4 | idem |
Il processo notturno (`night.py`, avviato 2026-10-10 22:38:34 UTC, tree `6b8a6fa`, 2026-10-11 00:12 +0200) è **posteriore** a tutti questi commit.

## 2. Esiti da riportare, nell'ordine fisso (nessun criterio nuovo)
1. **M1, per braccio (`default`, `deploy`):** H-M1 (IC bootstrap della media del throughput a 50 e a 100 writer sovrapposti; falsificata se l'IC a 100 sta interamente sopra quello a 50), sui due insiemi "all" e "filtered"; H-M1b (nessuna cella `deploy` con `unexpected_errors > 0`); H-M1c (a 100 writer il `throughput_completed` di `deploy` non è inferiore a quello di `default`; falsificata se l'IC di `deploy` sta interamente sotto). Riportati senza soglia: p50/p95/p99 per numero di writer e errori inattesi.
2. **M2 (braccio `deploy`):** H-M2a (media su celle della quota di coda `to_lock_s/total_s` ≥ 0,5 a 100 writer, thread), H-M2b (quota di commit < 1%), H-M2c (Gini dell'attesa per writer ≤ 0,3), H-G1 (throughput dell'operazione nulla a 100 thread ≥ 10× quello completato), H-G2 (throughput a processi a 100 writer < 2× quello a thread).
3. **Censura del pool riportata a parte** (decisione dell'utente, audit 14:405; audit 04 §7.4): una sezione separata con, per braccio e numero di writer, quante celle hanno p99 ≥ 29,9 s con errori inattesi (`p99_censored_cells`), quante ripetizioni totali, e le statistiche di latenza **solo sulle celle non censurate**; per le censurate si riporta soltanto "tetto del timeout di checkout (30 s), non una latenza". Mai un p99 di 30 s nella tabella delle latenze. Throughput e tasso di errore/timeout si riportano su tutte le celle, in colonne separate dalle latenze.
4. **Numero di celle segnalate dalla regola di scarto**, sempre; nessuna cella scartata in silenzio; risultati su "all" e "filtered".

## 3. Limiti e deviazioni da dichiarare nel rapporto (già noti prima dei dati)
- **Fondo del watcher:** M1/M2 sono girate con il watcher `netem_watch.sh … wan` attivo (~0,07 core di fondo, audit 20:20, 21); non cambia la regola di scarto ma è un processo di fondo che la regola non esclude per nome.
- **G4 non soddisfatta** sul nodo (k3s e altre sessioni; audit 04 §7.3); CPU QEMU generica senza AVX2: i tempi **non sono confrontabili con altre macchine**; nessun confronto con `results/concurrency` (altro host, altro `services.py`, audit 04 §1).
- Python del nodo 3.12.3 contro 3.12.15 dell'ambiente locale (audit 04 §7.2); `sum()` può differire all'ultima cifra fra versioni (audit 04 §7.1).
- M1 con 20 ripetizioni a 100 writer e 10 altrove; i controlli di M2 hanno 10 ripetizioni anche a 100 (audit 04 §7.4: limite dichiarato).
- Il primo M1 (solo `default`, 40/50 celle, `experiments_tnsm/m1_single_node/aborted_20261010/`, commit `51ad9db`) resta non analizzato e **non viene mescolato** ai dati della notte.
- Il manifest di M1 non contiene le impostazioni di SQLite per il primo run; per la notte, `node_env.json` va letto prima di riportare la configurazione (audit 04 §7.4 ultima riga).
- L'analisi è calcolata sui dati della notte, che non sono mai stati aperti prima: non c'è informazione preliminare da dichiarare (a differenza di (c) a `degraded`).

## 4. Procedura (ogni ssh autorizzato dall'utente, uno per volta; sola lettura sul nodo)
1. Elenco e dimensioni dei file di `~/dib_tnsm/out/night_20261011/run/{m1,m2}/` (`ls -l`, `du -sh`, `sha256sum`), per decidere la copia e verificare lo spazio locale.
2. Copia con `tar` su ssh in cartelle **nuove** `experiments_tnsm/m1_single_node/night_20261011/` e `experiments_tnsm/m2_p99_tail/night_20261011/` (mai `results/`, mai sovrascrivere), sha256 verificati sui due lati.
3. Commit dei dati (se la licenza/dimensione lo permette) **prima** dell'analisi.
4. `python3 experiments_tnsm/common/analyze.py m1|m2 <dir>` (nessuna modifica al codice di analisi; se serve, prima il test e un commit separato) e rapporto in `docs/audit/38_m1_m2_notte.md`.
