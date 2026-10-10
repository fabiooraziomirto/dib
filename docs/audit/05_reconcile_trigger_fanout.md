# Audit 05 — Trigger di `/reconcile` e fan-out D11

Data: 2026-10-10. Branch `fix-reconcile-trigger-fanout` (da `revision-tnsm`, tag `pre-reconcile-trigger`). DIST = `code/src/dib/registry/distributed/service.py`. Il piano approvato è in `/root/.claude/plans/pasted-content-id-6bde-contesto-leggi-groovy-lemon.md` (copia del contenuto: questa nota riporta decisioni, esiti e scostamenti). Il numero 04 è riservato al piano di misure. Checklist pre-pubblicazione: `docs/work/PRE_PUBLICATION_CHECKLIST.md`.

## 1. Parte 0: branch di integrazione (eseguita)
- Stato iniziale: working tree pulito; `main` f1473d4, `tests-gap-closure` 8c13a42, `fix-d12-ack` c9491a9; tag `baseline-v43`, `d12-confirmed-pre-fix`, `v43-import` (bd3080b).
- `git merge-base --is-ancestor tests-gap-closure fix-d12-ack` → **vero**: un solo merge. `revision-tnsm` da `main`, `git merge --no-ff fix-d12-ack` → `f121777`, nessun conflitto.
- Verifiche dopo il merge: **345 passed**; `verify_artifact.py` **260 passed, 2 failed** (solo i due sha256 di `service.py`); `git diff v43-import --stat -- code/src formal claims.json` = solo `distributed/service.py` (73+/17−); `docs/audit/00..03`, `docs/audit/raw/`, `docs/work/regenerate-results-after-service-changes.md` e i tag presenti; `git status` pulito.
- Commit documentale `a323663` su `revision-tnsm` (copia di `DIB_piano_completo.md` in `docs/work/`, più `PRE_PUBLICATION_CHECKLIST.md`), tag `pre-reconcile-trigger` sulla testa, poi il branch di lavoro.
- Nota: `main` (f1473d4) non coincide con il tag `v43-import` (bd3080b, un commit prima); vale per il codice, non per i file di documentazione.

## 2. Commit
| Commit | Contenuto |
|---|---|
| `9eba278` | solo estensione di `_dist_harness.py` (file esistente di test-support): `FakeClock`, `net.evidence_down`, `net.gate`, helper del trigger, parametro `env`, lock su `calls`/`fail_next`. Suite dopo il commit: **345 passed** (neutra) |
| `5919c6b` | pre-registrazione dei 2 file nuovi, **non eseguiti prima del commit** (solo `py_compile`) |
| `3e61d9e` | correzione di due bug di *misura* nei test pre-registrati (§4) |
| `5e24b57` | implementazione (service.py, `generate_compose.py`, `docker-compose.yml`) |
| (questo) | nota di audit e aggiornamento della voce di rigenerazione |

## 3. Cosa fa il codice (DIST)
- **Parametri** (DIST:122-139, letti all'import): `DIB_DIST_RECONCILE_INTERVAL` T (default 0 = disattivato), `_JITTER` J (default 0,1·T), `_TIMEOUT` (default 5,0; prima hardcoded a 5,0), `_LOCK_TIMEOUT` (default 60), `DIB_DIST_FANOUT_CONCURRENCY` (default 1).
- **Trigger** `_ReconcileTrigger` (DIST:170-241): ritardo iniziale `U(0,J)`; dopo un run riuscito `T + U(0,J)`; con evidence irraggiungibile backoff 1 s, 2 s, … con tetto `min(T, 30 s)`; single flight con `acquire(blocking=False)` e ripianificazione a `min(1 s, T)`. `tick()` senza thread né sleep (clock e rng iniettabili); `start()/stop()` avvolgono `tick()` in un thread daemon. Avvio/arresto nel `lifespan` (DIST:263-272).
- **`/reconcile`**: corpo estratto in `_reconcile_once` (DIST:425); la route (DIST:466-481) ha lo stesso corpo di risposta e lo stesso header, prende la stessa lock con attesa massima `RECONCILE_LOCK_TIMEOUT` e risponde 503 alla scadenza.
- **Fan-out**: `_deliver_to_site` (DIST:577) è il vecchio corpo del giro per un sito (3 tentativi, timeout 1,0 s, outbox invariata); `_fan_out` (DIST:606) con cap 1 ripete il ciclo storico, con cap > 1 sottomette un task per sito a **un solo** `ThreadPoolExecutor` condiviso (`_get_fanout_executor`, DIST:244) e attende **tutti** i future prima di rispondere o rilanciare il primo errore. Il lifespan chiude il pool.
- **Compose**: `generate_compose.py` e `docker-compose.yml` hanno solo le nuove env (siti: T=5, J=0,5, timeout 5,0; evidence: concorrenza 8); il file rigenerato differisce di 31 righe aggiunte.

## 4. Test
**Prima dell'implementazione** (`5919c6b`, esecuzione sul codice di `9eba278`): 36 test nuovi, **31 failed, 5 passed**. I fallimenti erano `AssertionError: site N has no reconcile trigger` (16), `AttributeError` su `RECONCILE_INTERVAL`/`FANOUT_CONCURRENCY`/`_get_fanout_executor`, timeout atteso 7,5 contro 5,0, nessuna sottomissione registrata: tutti dovuti alla funzionalità assente. I 5 passati: `test_f1` (stesse chiamate), `test_f4` (D12 con executor finto: l'executor finto non viene usato dal codice vecchio, quindi non discrimina), `test_f8b` (cap 1: errore interrompe il giro come oggi), `test_t8b` (timeout di default 5,0) e **`test_w_…_characterization`**: sul codice attuale l'ipotesi H-W è **confermata** (l'evento tra il commit di stato e `_fan_out` non finisce in nessuna outbox e `/reconcile` non lo recupera): candidato D-nuovo ora provato in-process, non ancora corretto.
**Dopo** (`5e24b57`): suite completa **381 passed** (345 + 36), 0 failed; i 36 sono stabili su 3 esecuzioni consecutive (4,2–4,4 s). `verify_artifact.py`: **260 passed, 2 failed** (stessi due sha256, non rigenerati). `git diff revision-tnsm` sui file di test esistenti: **vuoto**, salvo `_dist_harness.py` (estensione dichiarata, `9eba278`); nessun test esistente modificato.
**Due correzioni di misura nei test pre-registrati** (`3e61d9e`, comportamento asserito invariato): T5c registrava l'inizio del run *dopo* `tick()` (che avanza il clock di D), T4 contava anche il thread portal di `TestClient`. Trovati alla prima esecuzione sul codice implementato. Le correzioni sono mie: vanno riviste.
**Controlli negativi** (copie in `tmp_path`, ancora con `count == 1`, `pytest.raises(AssertionError)` + messaggio):
- `…without_the_tick_body…`: `self._run()` → `pass`: il sito non converge; il messaggio contiene `'state': 'monitor-only'` e `'event_type': 'dispute'` (evento ancora in outbox).
- `…sequential_submission…`: `; futures[-1].result()` dopo la sottomissione: fallisce con `sites [2, 3] not delivered while site 1 gated`.
Entrambi passano (cioè il bug reintrodotto produce proprio quell'errore e non un altro).
**Mappa T/F → ipotesi:** T1/T1b (avvio con evidence giù poi su, nessuna chiamata a `/reconcile`; ritardo iniziale ≤ J), T2/T2b/T2c (jitter, calendario esatto agli estremi, siti non sincroni), T3/T3b/T3c (single flight, ripianificazione, 503), T4/T6 (default e T=0), T5 (5 fasi, arrivo avverso, lock tenuta da chiamata manuale), T7/T9 (start/stop, lifespan), T8/T8b (timeout), W, F1–F8.
**T5, arrivo avverso:** evento in outbox subito dopo la snapshot del GET di un run con GET di D = 3 s, T = 10, J = 2: ritardo osservato = `T + J + 2D` = 18 s esatti (asserito), sopra `T + J + d_run` (15) e entro `T + J + 2·d_run_max`. Il caso è stretto: il bound dichiarato è raggiunto.

## 5. Quantificazione del fan-out (in-process, solo conteggi e ordine)
Baseline (`measure_baseline.py` in scratchpad, N = 10, siti giù = `FakeNet.down`) e dopo (cap 1 e cap 8 con pool reale, `measure_after.py`):
| siti giù | chiamate `/apply_fanout` | righe outbox | ordine, cap 1 e cap 8 in-process |
|---|---|---|---|
| {3,5,7} | 16 (3 per sito giù, 1 per gli altri) | 3 | `0123334555677789` |
| {1..9} | 28 | 9 | `0111222333444555666777888999` |
Il numero di chiamate e le righe in outbox sono **identici** con cap 1 e cap 8, come previsto. **Attenzione:** l'ordine con il pool reale è identico a quello sequenziale perché in-process ogni task è istantaneo e termina prima che parta il successivo (verificato che 8 thread `dib-fanout_*` eseguono i task): quell'ordine non prova la concorrenza. La concorrenza e le ondate sono provate dai test con executor finto (F2, F3, F1b), non da questa tabella. Tempi non misurati: `ceil(k_giù / cap) × 3 s` nel caso peggiore con host che scarta i pacchetti; con cap 2 e giù {1..5}: 9 unità contro 15 in serie e il sito sano 6 parte a 6 (non a 0: in una coda FIFO con cap < k i sani accodati dopo i giù aspettano). La frase "≤ ~3 s indipendente da k" è falsa per k > cap e non va usata.

## 6. Limite di staleness (per il paper)
Con T > 0, evidence raggiungibile e evento **già in outbox**: `staleness ≤ T + J + 2·d_run`, con `d_run` durata di un `_reconcile_once` (da misurare). Fuori garanzia: eventi mai arrivati in outbox (H-W), servizio avviato con T = 0 (**staleness illimitata**: avvertenza nel docstring di DIST e qui), processo del sito fermo (il bound riparte dal riavvio). Una chiamata manuale che tiene la lock può ritardare il run di `d_run + min(1 s, T)` (T5c). Falsificabile variando T e misurando il massimo. Nessuna modifica al paper.

## 7. Scostamenti dal piano
1. `tick()` cattura `Exception` (non solo `httpx.HTTPError`/`sqlite3.Error`) per non uccidere il thread daemon; l'errore è in `last_error` e nel log. Un bug del codice di riconciliazione diventerebbe un backoff perpetuo, non un crash: da tenere presente.
2. Il giudizio "F4 non discrimina" (sopra) non era previsto: il codice vecchio non usa l'executor finto.
3. Nessun altro scostamento; i default nel codice sono quelli decisi (T = 0, cap 1).

## 8. Non fatto / da fare (richiede il tuo ok)
- Nessun esperimento Docker o su rete reale è stato lanciato. Da rieseguire dopo la modifica (ognuno con il tuo ok): `fault_injection_experiment.py` in **due varianti** (T = 0 con chiamata esplicita, comparabile con il claim 26; T > 0 senza chiamata, tempo fino a `/state`), `reconcile_race_experiment.py`, `dispute_flood.py`, `distributed_concurrency_benchmark.py`, `distributed_site_count_sweep.sh`; con cap = N e cap 8. Con il compose rigenerato (T = 5) la chiamata esplicita di `fault_injection_experiment.py` troverebbe già `reconciled: 0`: per il confronto col claim 26 generare il compose con `DIB_DIST_RECONCILE_INTERVAL=0`.
- Le due rigenerazioni dei risultati con sha256 (`restore_ablation`, `offline_veto`) restano da fare a fine di tutte le modifiche a `service.py`; hash corrente `f6860bea…` (era `ecb06dd3…` dopo il fix D12, `d09f8db5…` registrato nei risultati). Voce aggiornata in `docs/work/regenerate-results-after-service-changes.md`.
- Modello TLA+ (solo elenco, nulla toccato): fairness `WF_vars(Reconcile(t,f))` condizionata a `t \notin unreachable`; proprietà di vivacità `pending[t][f] ~> ~pending[t][f]` (oggi `Spec` a `formal/distributed/DIB_Distributed.tla:267` non ha fairness); un tempo o `Tick` per il bound `T + J + 2·d_run`; GET e ack separati con evento concorrente (audit 03 §8); per l'opzione (b), `Dispute` spezzata in registra/consegna.
- Timestamp per fase (da non implementare ora): evidence, dopo il commit di stato, per sito in `_deliver_to_site`, riga in outbox; sito, inizio/fine di `_reconcile_once` e per round, apply per item, ack. Nuove informazioni in header/log, non nel corpo.
- Estensione futura (non implementata): anti-entropia basata sullo stato (il sito confronta `fanout_seq` di `/scores` con `last_applied_seq`) per chiudere la finestra di H-W senza passare all'outbox-first.
- `docker-compose.yml`: rigenerato con `python3 generate_compose.py`; i fatti con `--workers N` moltiplicherebbero il trigger (un solo worker per sito).

## 9. Ipotesi che potrebbero cadere
- Che `d_run` sia piccolo: il caso peggiore teorico è ~30 s con timeout 5 s; non misurato.
- Che il timeout di guardia 503 (60 s) non scatti mai in esercizio normale.
- Che il carico `GET /pending` (N/T richieste/s sul lock globale dell'evidence) non degradi il p99: da misurare con `dispute_flood.py`.
- Che il costo reale di un sito giù sia vicino a 3 s: con connessione rifiutata può essere molto minore.
- Che il pool condiviso non causi head-of-line sotto dispute concorrenti con molti siti giù (cap < k).
- Che H-W rifletta un crash reale: provato con un'eccezione iniettata, non con un crash di processo.
- Che i test con thread reali di start/stop (T7, T9) restino stabili su macchine lente (attendono solo, `join` con timeout 5 s).
