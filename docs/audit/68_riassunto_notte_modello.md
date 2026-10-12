# Audit 68 — Riassunto della notte 12-13/10/2026: modello del prototipo, difetti trovati, correzione verificata

Obiettivo dato: "un modello valido per il paper (facendo attenzione a non andare OOM) e che migliori il
paper". Dettagli, ipotesi pre-registrate ed esiti in audit 63 (FSM), 64 (test), 67 (modello).
Branch:
- `tnsm-fsm` (worktree `/root/Desktop/DIB_tnsm_fsm`): audit, test, modelli;
- `tnsm-fsm-paper` (worktree `/root/Desktop/DIB_tnsm_paper`): le modifiche a `docs/main_wip.tex`.

Nessuna modifica a `code/src`, `formal/`, `results/`, `claims.json`.

## 1. Il modello
- `experiments_tnsm/tla_fsm/v5/DIB_AE_NA.tla` = `formal/distributed_ae/DIB_AE.tla` più:
  - le operazioni del sito non atomiche, come nel codice (lettura dell'evidence, poi transazione
    locale);
  - la correzione;
  - il quorum 2.
- **Fedeltà:** con le operazioni atomiche riproduce esattamente il modello pubblicato,
  14.947.820 stati (3 run di regressione, v1/v2/v3).
- **Protezioni:**
  - un TLC alla volta, heap ≤ 24 GB su 64;
  - watchdog sul disco (< 8 GB liberi → kill), metadir nello scratchpad;
  - nessun OOM, nessun intervento del watchdog;
  - heap disponibile riportato da TLC: 21,8 GB (non il picco misurato); metadir osservata fino a ~1,1 GB;
  - memoria di sistema usata fino a ~20 GB su 64 nei controlli con `free`.

## 2. Cosa ha trovato (ognuno riprodotto da un test sul prototipo)
| # | Difetto | Proprietà violata | Test |
|---|---|---|---|
| i | query in corsa con una dispute: MonitorOnly durante l'episodio (fino alla reconcile) | `DisputeSuspendsAtReachableSites` (pubblicata); ack D12 | `test_distributed_fsm_races.py` b3q |
| ii | commit letto prima di una dispute diventa Active dopo | precondizione tab:transitions :321 | b3c |
| iii | local restore in corsa con una dispute: MonitorOnly per tutto l'episodio, non riparato | `CaughtUpIsCoherent` (pubblicata) | b3r |
| iv | commit letto prima di un **intero** episodio dispute+restore diventa Active **dopo il restore, senza nuova approvazione**, esportabile | `NoStaleActiveAfterEpisode` (pubblicata) = **I3** | `test_distributed_fsm_stale_commit.py` |
| v | quorum 2: un votante della sospensione conferma la revoca | regola decisa da te (a10) | a10 |
| vi | local revoke impossibile con l'evidence irraggiungibile | (disponibilità, non modellata) | b4 |

**Che cosa regge nel prototipo** (`v4_n7`, 55.063.707 stati): l'export durante una dispute aperta ai
siti raggiungibili senza nulla in volo, I1, I2, la conservazione del veto, il restore conservativo.

## 3. La correzione (verificata nel modello, provata su una COPIA del servizio)
- **Parti:**
  - query: riserva di una riga `staging` sotto `_reconcile_lock`, poi lettura, poi chiusura;
  - local restore: guardia `last_applied_seq ≤ seq letto`;
  - commit in due fasi (`committing`, seconda lettura, promozione solo a seq invariato);
  - in più, nella copia: local revoke senza evidence; conferma con quorum 2 da un segnalante
    esterno ai voti.
- **Nel modello:**
  - progetto finale **v6**: alla chiusura la query applica anche la propria lettura se un fan-out
    ha già spostato la riserva. Serve con 3 eventi: `v5_f4_e3` ha trovato una dispute persa e un
    restore più vecchio consegnato fuori ordine sulla riserva;
  - `v6_f2_fix_all`: nessuna violazione di alcuna proprietà su 100.746.547 stati (MaxEvents 2);
  - ognuna delle cinque parti è necessaria (5 mutanti v6, tutti rilevati);
  - versione v5 su entrambi i siti: 466.601.973 stati senza violazioni, ma è la v5;
    `v6_f3_two_split` è in corso;
  - con MaxEvents 3 la v6 è **incompleta** (fermata da me a 202 M stati: nessuna affermazione);
  - quorum 2 con la regola outsider: 64.458.470 stati, nessuna violazione.
- **Sulla copia:**
  - test delle race e del commit stantio verdi;
  - 127 test distribuiti esistenti verdi;
  - falliscono solo i test che fissano i vecchi comportamenti e b3q-2 (non c'è più niente da
    riparare).

## 4. Il paper (branch `tnsm-fsm-paper`, compila, 13 → **14 pagine**)
- Sec. lifecycle-results: nuovo paragrafo sul modello del protocollo, i quattro controesempi, ciò
  che regge e la correzione verificata ("not part of the prototype evaluated in this paper").
- Analisi di G3: una frase sul caso (iv).
- Caption della tabella delle transizioni: restore su un sito che ha perso la dispute; retention
  non implementata.
- Sospensione: la regola di conferma del prototipo e il controllo del modello.
- Limiti: il veto locale richiede l'evidence.
- Conclusione: una frase.
- Ogni numero ha un `% SRC:` che rimanda agli audit.

## 5. Decisioni per te
1. **Integrare la correzione in `service.py`?** Il file è congelato per hash. Integrarla cambia
   l'hash e richiede di rieseguire i blocchi misurati con il nuovo codice (o di dichiarare che le
   misure sono sul codice precedente). Finché non lo fai, il paper dice correttamente che il
   prototipo valutato non la include.
2. **Pagine:** il paragrafo nuovo porta il PDF a 14 pagine. Se TNSM o il supervisor hanno un
   limite, va accorciato (proposta: togliere l'elenco (i)-(iv) e tenere solo il caso (iv)).
3. **Merge:**
   - `tnsm-fsm` è stato creato da `6e6d352`; l'altra sessione ha committato dopo su
     `tnsm-driver-retry`;
   - i file toccati qui non si sovrappongono ai suoi;
   - `docs/audit/62` è suo, 63-68 sono miei;
   - prova di merge in sola lettura (`git merge-tree`, 2026-10-12 ~03:00) contro `tnsm-driver-retry` a `f904de4`: 0 conflitti per `tnsm-fsm` e `tnsm-fsm-paper`; dall`'`altra parte nessuna modifica a `code/`, `formal/`, `main_wip.tex` dalla base `6e6d352`.
2b. **Versione corta (proposta, non applicata), se serve tornare a 13 pagine.** Sostituisce i due
   paragrafi nuovi di Sec. lifecycle-results:
   > A third model follows the prototype's reconciliation protocol (sequence numbers, collapsed
   > pending records, per-pair acknowledgement, anti-entropy, asymmetric partitions) and explores
   > 14,947,820 states without violations when site operations are atomic. In the prototype,
   > query, commit, and local restore read the evidence service before a separate local
   > transaction; modeling this split yields four counterexamples, all reproduced by registry
   > tests, the most severe being a commit read before a dispute and restoration episode that
   > becomes Active afterwards without fresh approval. Export during an open dispute remains safe
   > (55,063,707 states). A corrected design (reservation under the reconciliation lock, sequence
   > checks, and a two-phase commit) removes all four within two evidence events (100,746,547
   > states); it is not part of the evaluated prototype.
3b. **Numerazione degli audit in collisione.** Su `tnsm-driver-retry` l'altra sessione ha creato
   `63_b2k_lan_rerun_driver_fix.md` e `64_prereg_keepalive_lan.md`; qui ci sono `63_fsm_specifica.md`
   e `64_fsm_test_risultati.md`. Nessun conflitto git (nomi diversi), ma "audit 63/64" diventa
   ambiguo nei riferimenti: docstring dei test, `% SRC:` del paper, audit 65-68. Proposta: al merge
   rinumerare i miei 63-68 in un blocco libero e aggiornare i riferimenti con un solo commit. Non
   l'ho fatto ora perché l'altra sessione continua a numerare.
4. **Il differenziale** (`test_distributed_fsm_differential.py`) gira solo con `DIB_FSM_DIFF=1`
   (~5 min): scelta mia, da confermare.
5. **Lease o epoch** (audit 65): da scegliere.

## 6. Errori miei durante la notte (tutti registrati negli audit)
- `git switch -c` nella worktree condivisa ha spostato il branch dell'altra sessione. Riparato
  senza perdite, poi lavoro in worktree separate.
- H-b3r-2 aveva un valore atteso sbagliato ("disputed" invece di revoked/local).
- `FixRace` v1 non copriva la query.
- Due proprietà non adattate alle azioni divise o a `Staging` (`I3_VetoPreserved`,
  `OutboxNeverDropsUnapplied`). Corrette in v3/v4, dichiarando che la correzione veniva dopo il
  risultato.
- L'argomento della v4 sull'ack era incompleto; v5 lo corregge con il lock.
- Stima della durata del differenziale sbagliata (1-2 min contro ~5).
