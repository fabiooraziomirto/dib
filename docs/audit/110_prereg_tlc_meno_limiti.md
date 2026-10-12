# Audit 110 — Pre-registrazione: togliere limiti al modello (letture fallite, crash, quorum 2, perdite, fatti, siti)

Data: 2026-10-12. Branch `tnsm-fsm`. Scritto e committato **prima** di ogni esecuzione.

**Numero:** 110 e non il primo numero libero, che sarebbe 96.
- Il 100 è riservato esplicitamente dall'altra sessione (`99_prereg_B2k_file_finale.md:22`,
  "Risultati: audit 100").
- Il 96 e il 103 seguono il suo schema (pre-registrazione N, risultati N+1: 97→98, 99→100,
  101→102): con ogni probabilità sono i suoi prossimi numeri.

Per evitare collisioni uso un blocco separato. Verificato su tutti i branch e nelle worktree: il 110
non esiste.

**Decisione dell'utente (2026-10-12):** "vorrei avere meno limiti possibili nel paper". Approvate
tutte le estensioni proposte: 1+2 letture fallite e crash, 3 quorum 2 con la correzione, 4+5
MaxLoss 2 e due fatti, 6+7 tre siti e concorrenza. Prima si lascia finire `Lv_e2` (audit 93).

## 1. Codice di riferimento
`service.py` sha256 `3ffa57ee…` (commit `864101f` su `tnsm-fixes`): `dc3dd20` più
- `54521aa` (D1, D2);
- `4be98f4` e `864101f` (letture dell'evidence fallite → 503/502).

Letto da me in sola lettura (audit 90 e risposte in chat del 2026-10-12):
- **D1:** all'avvio del sito `DELETE … WHERE state='staging'` e `committing` → `monitor-only`;
- **D2:** `_reconcile_lock.acquire(timeout=…)`, altrimenti 503 **prima** della riserva;
- **lettura fallita:**
  - prima lettura di `/query`, `/commit`, `/local_restore`: 503/502 senza cambiare lo stato;
  - seconda lettura di `/query`: cancella la riga `staging` e risponde 503 (`except Exception`,
    `service.py:543` a `4be98f4`);
  - seconda lettura di `/commit`: `again = None`, fase 2 → `monitor-only`, 409 (`service.py:590`).

## 2. Modello v8 (`experiments_tnsm/tla_fsm/v8/DIB_AE_NA.tla`)
= `v6m` (v6 con il flag `MutNoLock`) più:
- le definizioni di vivacità v7 (`DecisionRow`, `ConvergedDecisions`, `ConvergedDecisionsEventually`,
  audit 93 sez. 9);
- azioni nuove:
  - `QueryRead2Fail(s)`: con una query pendente in `qreserved`, la seconda lettura fallisce. Se la
    riga è ancora `Staging` diventa `Absent`, altrimenti resta com'è (come
    `DELETE … AND state='staging'`). Fine dell'operazione.
  - `VerifyReadFail(s)`: con un commit in `committing`, la seconda lettura fallisce.
    `Committing` → `MonitorOnly`, altrimenti nulla. Fine dell'operazione.
  - `RcFail(t)`: un giro di reconcile in qualunque fase viene abbandonato (`rc` torna `IdleRc`,
    nessun ack). Le applicazioni già fatte restano; il giro successivo riparte da capo.
  - `Crash(t)`: il processo del sito muore e riparte. Le righe SQLite restano; operazione pendente
    e giro di reconcile si perdono; pulizia D1 (`Staging` → `Absent`, `Committing` →
    `MonitorOnly`). Crash e riavvio sono istantanei: il periodo "giù" è già coperto da
    `SiteDown`/`SiteUp`.
- limiti: `MaxFails`, `MaxCrashes` (contatori `failCount`, `crashCount`, inclusi nella VIEW);
- mutazioni: `MutNoD1` (riavvio senza pulizia), `MutFailNoClean` (lettura fallita che lascia la
  riserva);
- proprietà nuova `CrashConfinement`: un crash cambia solo i record del proprio sito. `Crash` non è
  fra le `LocalOps`, perché pulisce tutti i fatti del sito e `UnrelatedFactIsolation` non gli si
  applica.

**Non modellato, e perché non cambia lo stato:**
- le prime letture fallite e il timeout di D2: nel modello equivalgono a "il passo non avviene";
- i retry del driver: sono del client.

**Verifiche fatte prima di committare (non run TLC):**
- SANY senza errori;
- `diff` contro `v6m`: 102 righe aggiunte; le righe tolte sono solo liste estese con i contatori.

## 3. Configurazioni e ipotesi
Comune: 1 operazione pendente per sito, `VIEW View` per la safety, quorum 1 salvo Q*. Con
`MaxFails = MaxCrashes = 0` il modello si comporta come la v6.

**Insiemi di proprietà:**
- **S:** `TypeOK`, `CaughtUpIsCoherent`, `NoStaleActiveAfterEpisode`,
  `NoMonitorOnlyCaughtUpDuringEpisode`, `CommittingIsTransient`, `StagingIsTransient`;
  `I1_NonEscalation`, `I2_SiteConfinement`, `I2_ApplyConfinement`, `I3_ConservativeRestore`,
  `I3_VetoPreserved`, `UnrelatedFactIsolation`, `LastAppliedMonotone`, `NoRegression`,
  `OutboxNeverDropsUnapplied`, `I1_CommitOnUndisputedEvidence`, `RevokeConfirmedByOutsider`,
  `CrashConfinement`;
- **ALL2** = S + `DisputeSuspendsAtReachableSitesV2` + `ExportSafeAtReachableSites`;
- **ALL3** = S + `V3` + `ExportSafe`. Con 3 eventi si usa V3, come in audit 92: la chiusura della
  query applica la lettura e il record può essere `MonitorOnly` durante la query pendente;
- **SLOSS** = S. Con le perdite ExportSafe e V2/V3 sono violate per costruzione (audit 93 sez. 1).

| cfg | Ipotesi | Falsificata se |
|---|---|---|
| `H0_regress` (e2, MaxToggles 3, F0 C0) | conservativa: nessuna violazione di ALL2 e **esattamente 19.415.620** stati (`v6e3/logs/e3a_view_check.log:36`) | violazione o altro conteggio |
| `Xm1_noD1` (C1, `MutNoD1`) | `StagingIsTransient` o `CommittingIsTransient` violato | nessuna violazione |
| `Xm2_failnoclean` (F1, `MutFailNoClean`) | `StagingIsTransient` violato | nessuna violazione |
| `X1_e2_fc` (e2, T0, L0, F1, C1) | nessuna violazione di ALL2 | qualunque violazione |
| `X5_live_e1` (SpecL, e1, L1, F1, C1, T0) | `ConvergedDecisionsEventually` ed `ExposureEnds` valgono | qualunque violazione |
| `X3_e2_loss_fc` (e2, T0, L1, F1, C1) | nessuna violazione di SLOSS | qualunque violazione |
| `X2_e2_p_fc` (e2, T2, L0, F1, C1) | nessuna violazione di ALL2 | qualunque violazione |
| `X4_e3_fc` (e3, T0, L0, F1, C1) | nessuna violazione di ALL3 | qualunque violazione |
| `Q1_quorum2_e3` (quorum 2 outsider, 3 reporter, e3, T0) | nessuna violazione di ALL3 | qualunque violazione |
| `Q2_quorum2_e2_p` (quorum 2, e2, T2) | nessuna violazione di ALL2 | qualunque violazione |
| `L2a_loss2` (e2, T0, MaxLoss 2) | nessuna violazione di SLOSS | qualunque violazione |
| `L2b_loss2_p` (e2, T2, MaxLoss 2) | nessuna violazione di SLOSS | qualunque violazione |
| `F2_two_facts` (2 fatti, e2 in totale, T0) | nessuna violazione di ALL2 | qualunque violazione |
| `S3_three_sites` (3 siti, s1 diviso, e2, T0) | nessuna violazione di ALL2 | qualunque violazione |
| `S2e3_both_split` (s1 e s2 divisi, e3, T0) | nessuna violazione di ALL3 | qualunque violazione |

Legenda: eN = MaxEvents N; TN = MaxToggles N; LN = MaxLoss N; F/C = MaxFails/MaxCrashes.

**Non vacuità delle parti già note:** i mutanti di audit 67/92/93 restano validi, perché con
`MaxFails = MaxCrashes = 0` v8 coincide con v6m (H0). Non li ripeto.

## 4. Concorrenza (estensione 7): pre-registrazione separata
Due richieste pendenti per sito richiedono di cambiare la struttura di `op`: da una per sito a più
"slot" per sito. È un intervento più grande, che faccio **dopo** questi run, con una pre-registrazione
aggiuntiva committata prima del suo lancio.

## 5. Risorse, ordine, arresto
- Come in audit 67/92/93: `-Xmx28g` su 64 GB, 8 worker, metadir nello scratchpad, watchdog del
  disco sotto 8 GB, un TLC alla volta.
- **Nessun tetto di tempo** (decisione dell'utente, audit 93 sez. 7).
- **Ordine** (dai più leggeri ai più pesanti): H0, Xm1, Xm2, X1, X5, X3, X2, X4, Q1, Q2, L2a, L2b,
  F2, S3, S2e3. Parte quando `Lv_e2` ha finito.
- **Arresto:** se un run che deve reggere (tutti tranne Xm1 e Xm2) trova una violazione, o H0 dà un
  altro conteggio, la sequenza si ferma e si riporta la traccia minima, senza proporre codice.
- I run fermati dal watchdog sono incompleti: nessuna affermazione.

## 6. Cosa va nel paper
- **Tutto confermato:** la frase sul modello elenca la configurazione verificata, cioè letture
  dell'evidence fallite, crash e riavvio, una o due consegne perse, partizioni, quorum 2, 2 fatti,
  3 siti, fino a 3 eventi, e i limiti restanti (la finestra D19; la concorrenza solo se verificata
  in sez. 4).
- **Controesempio:** ci si ferma. Se riguarda il codice, `service.py` cambia e i blocchi sul nodo
  vanno rifatti (decisione dell'utente).
- **Incompleti:** si dichiarano tali, e la configurazione verificata nel paper si ferma all'ultimo
  run completo.

## 7. Risultati (eseguiti)

Esecuzione del 2026-10-12, 14:02-14:42 UTC (i `Progress` nei log sono in ora locale, CEST = UTC+2), worktree `DIB_tnsm_v8`
(branch `tnsm-fsm-v8`, da 7a4a9d5), `run_tlc.sh <cfg> 28 8`, un TLC alla volta, jar sha256 `237332bd…`, Java OpenJDK 17.0.19.
Log in `experiments_tnsm/tla_fsm/v8/logs/<cfg>.log`, riga per run in `logs_v8.out`, manifest (hash di modello e cfg) in `logs/manifest.tsv`.
Righe citate: "r. A/B/C" = riga di `No error has been found` / `distinct states found` / `depth` (o `is violated`) del log.

| cfg | Previsione | Esito | Stati distinti | Profondità | Durata | Log (righe) |
|---|---|---|---|---|---|---|
| `H0_regress` | nessuna violazione, esattamente 19.415.620 stati | **confermata** | 19.415.620 | 42 | 6 min 00 s | r. 31, 36, 37 |
| `Xm1_noD1` | `StagingIsTransient` violato | **confermata** (violazione prevista) | 179 (al momento della violazione) | 6 | 15 s | r. 25, 177, 178 |
| `Xm2_failnoclean` | `StagingIsTransient` violato | **confermata** (violazione prevista) | 229 | 7 | 15 s | r. 25, 287, 288 |
| `X1_e2_fc` | nessuna violazione di ALL2 | **confermata** | 7.370.542 | 38 | 3 min 00 s | r. 28, 33, 34 |
| `X5_live_e1` | `ConvergedDecisionsEventually` ed `ExposureEnds` valgono | **confermata** | 1.087.027 | 25 | 3 min 45 s | r. 36, 41, 42 |
| `X3_e2_loss_fc` | nessuna violazione di SLOSS | **confermata** | 19.485.890 | 39 | 7 min 15 s | r. 32, 37, 38 |
| `X2_e2_p_fc` | nessuna violazione di ALL2 | **confermata** | 54.623.202 | 42 | 19 min 31 s | r. 45, 50, 51 |
| `X4_e3_fc` | nessuna violazione di ALL3 | **FALSIFICATA** | 88.535 (al momento della violazione) | 10 | 15 s | r. 25 (`DisputeSuspendsAtReachableSitesV3 is violated`), 500, 501 |
| `Q1_quorum2_e3`, `Q2_quorum2_e2_p`, `L2a_loss2`, `L2b_loss2_p`, `F2_two_facts`, `S3_three_sites`, `S2e3_both_split` | — | **NON ESEGUITE**: regola di arresto (sez. 5), la sequenza si è fermata a `X4_e3_fc` | — | — | — | `logs_v8.out`: `STOP: X4_e3_fc found a counterexample` |

Risorse: picco di RAM usata a livello di sistema 24,6 GB (campionata ogni 60 s, include altri processi; heap TLC 28 GB su 64 GB, mai OOM);
disco libero minimo osservato 33 GB (soglia del watchdog 8 GB, mai scattato). Nessun run incompleto: tutti terminati con `exit=0` o `exit=12` (violazione).

### 7.1 Violazioni previste (non vacuità delle due mutazioni)
- **`Xm1_noD1`** (riavvio senza pulizia D1), `StagingIsTransient`: (1) `QueryReserve(s1,f1)` → `sstate[s1][f1]="Staging"` con operazione pendente; (2) `Crash(s1)` →
  l'operazione pendente si perde, la riga resta `Staging`. Violato: `Staging` senza query pendente (r. 98-169).
- **`Xm2_failnoclean`** (lettura fallita che lascia la riserva), `StagingIsTransient`: (1) `Dispute(r1,f1)`; (2) `Dispute(r2,f1)` (revoca, `EvRevoke`);
  (3) `QueryReserve(s1,f1)` → `Staging`; (4) `QueryRead2Fail(s1)` senza pulizia → la riga resta `Staging`, operazione terminata (r. 77-276).
Le due mutazioni sono quindi non vacue: i due rami di D1 (`Crash`) e della pulizia nella lettura fallita (`QueryRead2Fail`) sono necessari a `StagingIsTransient`.

### 7.2 Falsificazione: `X4_e3_fc` (3 eventi, letture fallite e crash, nessuna perdita né partizione, ALL3)
Proprietà violata: `DisputeSuspendsAtReachableSitesV3` (`DIB_AE_NA.tla:894-898`: con stato dell'evidence ≠ Active e nessuna operazione in volo, un sito
raggiungibile deve essere `Absent`/`Disputed`/`Revoked`, oppure `Staging`/`MonitorOnly` **con una query pendente**). Traccia minima (9 stati, `lastOp` fra parentesi):

| # | Azione | Evidence | Sito s1 per f1 | `lastApplied[s1]` |
|---|---|---|---|---|
| 1 | Init | Active, seq 0 | Absent | 0 |
| 2 | `Dispute(r1,f1)` (`EvDispute`, seq 1) | Disputed | Absent | 0 |
| 3 | `Restore(f1)` (`EvRestore`, seq 2) | Active | Absent | 0 |
| 4 | `Dispute(r1,f1)` (`EvDispute`, seq 3) | Disputed | Absent | 0 |
| 5 | `Deliver` a s1 del seq 1 dispute (`Deliver`) | Disputed | Absent | 0 |
| 6 | `Deliver` a s1 del seq 3 dispute (`Deliver`) | Disputed | Absent | 0 |
| 7 | `QueryReserve(s1,f1)` (`QueryReserve`) | Disputed | **Staging**, query pendente `qreserved` | 0 |
| 8 | `Deliver` a s1 del **seq 2 restore** (`Deliver`), arrivato dopo il seq 3 | Disputed | **MonitorOnly**, query ancora pendente | **2** |
| 9 | `QueryRead2Fail(s1)` (`QueryFail`, `failCount=1`) | Disputed | **MonitorOnly**, **nessuna query pendente** | 2 |

Lettura: i due `dispute` (seq 1 e 3) consegnati a un sito dove il fatto è `Absent` non cambiano lo stato né `lastApplied` (resta 0); il `restore` (seq 2),
vecchio rispetto al seq 3, viene consegnato dopo e, con la query in corso, porta la riga a `MonitorOnly` con `lastApplied=2`. Il fallimento della seconda lettura chiude
l'operazione ma, avendo la riga già lasciato `Staging`, non la cancella: resta un `MonitorOnly` con l'evidence `Disputed`, senza query che lo giustifichi.
`MonitorOnly` non è esportabile (commento a `DIB_AE_NA.tla:893`): il controesempio è a `V3` e **non** dice che un fatto disputato venga esportato; non ho verificato
(non è nel modello) come il codice si comporti nello stesso scenario e non propongo correzioni.
Con 3 eventi senza fallimenti né crash `V3` regge (audit 92), quindi il controesempio dipende dalla sola azione `QueryRead2Fail` di v8 (`F1`).
Decisione per l'utente: se `V3` va letta come invariante da correggere (modello o codice) oppure ridotta (ammettere `MonitorOnly` anche dopo una lettura fallita), e se
`lastApplied` non avanzato per un `dispute` su fatto `Absent` sia voluto. Nessuna correzione proposta in questa sede.

### 7.3 NON VERIFICATO
- Le 7 configurazioni non eseguite (quorum 2 con 3 eventi e con partizioni; `MaxLoss 2` senza e con partizioni; due fatti; tre siti; due siti divisi con 3 eventi): fermate dalla regola di arresto. Nessuna affermazione su di esse.
- Tutto ciò che richiede 3 eventi con letture fallite e crash: il controesempio di `X4` vale per ALL3 (V3); `X1`, `X2`, `X3`, `X5` reggono solo con **2 eventi** (X5: 1 evento).
- Estensione 7 (richieste pendenti multiple per sito): non iniziata.
- Lettura del controesempio sul codice (`service.py`): non fatta.
