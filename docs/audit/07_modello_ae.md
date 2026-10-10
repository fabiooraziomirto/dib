# Audit 07 — Modello TLA+ del protocollo di riconciliazione (con e senza anti-entropia)

Stato: **piano e modello scritti, nulla eseguito** (né SANY né TLC). Branch `formal-ae` da `fix-d19` (`bcc9efb`). Commit (a): modello, cfg, README, questa nota. Il piano qui sotto è quello approvato; la sezione «Raffinamenti prima dell'esecuzione» elenca ciò che è cambiato scrivendo il modello. Gli esiti andranno nel commit (b) (log) e nel commit (c) (aggiornamento di questa nota).

## Raffinamenti prima dell'esecuzione (rispetto al piano approvato)
1. **`SiteDown` non azzera più la macchina di riconciliazione `rc[t]`** (piano §2). Con il reset D12 sarebbe stato irrappresentabile: nel D12 reale il sito sta riconciliando mentre la consegna *verso* di lui fallisce (`c.net.down.add(1)` dentro l'hook, `test_distributed_d12_reproducer.py`). `unreachable` significa ora «l'evidence non riesce a consegnare al sito» (partizione asimmetrica o sito fermo); il giro del sito prosegue (sito → evidence assunto raggiungibile).
2. **Fairness condizionata**: `WF_vars(RcStep(t) /\ t \notin unreachable)` (come chiesto: solo per siti non irraggiungibili), più `WF` su ogni consegna in volo. Di conseguenza `Converged` ed `ExposureEnds` riguardano i siti raggiungibili (per `ExposureEnds`: eventualmente raggiungibili per sempre).
3. **`LoseEvent` è per record** (una consegna), non per evento: la perdita di un evento intero = N perdite; `MaxLoss=1` perde una consegna (un sito), sufficiente per D19.
4. **`DisputeSuspendsAtReachableSites` in V2**: con un evento perso (D19) esiste per costruzione una finestra tra la perdita e la riparazione, in cui nulla è «in volo» ma il sito è ancora Active: l'invariante vale in V2a (senza perdita) ed è **attesa violata** in V2b (`v2b_window`); in V2b si chiede la forma di sicurezza `CaughtUpIsCoherent` e la vivacità `ExposureEnds`. Nel piano V2 diceva «tutte le proprietà tengono (finestre dichiarate)»: questa è la dichiarazione precisa, scritta prima del run.
5. **Mutazioni come flag** nello stesso modulo (raccomandazione del piano, nessuna obiezione). **E1 (surrogato dei 2 giri) fuori dal primo ciclo.** Aggiunte rispetto al piano: `v0_lag`, `v1_lag`, `v1_noloss`, `v2b_window`, `neg_nofairness` (controllo negativo della vivacità), `v0_2facts_outbox`, `v2a_2facts`.
6. `M-AE5` (`MutRestoreKeepsActive`) viola probabilmente anche `I3_ConservativeRestore`; nel cfg è elencata la sola `NoStaleActiveAfterEpisode` (una proprietà per run, per leggere quale viola).
7. Bound nelle guardie (`MaxEvents`, `MaxLoss`, `MaxToggles`), nessun `CONSTRAINT`, come previsto. D12 minimo richiede `MaxEvents=2`, `MaxToggles=3` (giù, su, giù); il caso «altro fatto» richiede 2 fatti e `MaxEvents=3`.

## Rischi di correttezza del modello già individuati (da verificare con SANY/TLC)
- Sintassi: modulo mai passato da SANY; possibili errori (es. `IF` annidati dentro `EXCEPT`, `LET` in congiunzione). Si correggono solo errori sintattici, e ogni correzione è riportata.
- `todo` ammette qualunque ordine di consegna (con `FANOUT_CONCURRENCY>1` è reale, con cap 1 il codice è sequenziale): sovra-approssima il cap 1.
- Nessun test dedicato per: caduta del sito a metà giro, atomicità righe+`current` (il mutante M-AE4 la esplora), staging `last_applied_seq` (da cercare in implementazione).

---

Branch proposto: `formal-ae` da `fix-d19` (nessun push/force/cancellazione, nessun Docker). Tutto in `formal/distributed_ae/` (nuova). Non si toccano `formal/` esistente, `scripts/run_formal.py`, `scripts/verify_artifact.py`, `claims.json`, `results/`, paper, `code/src`. Nulla scritto né eseguito in plan mode.
**Nota sul vincolo di plan mode:** il piano vive qui; `docs/audit/07_modello_ae.md` (da te richiesto come sede del piano) lo creo **dopo l'approvazione**, nel commit (a), poi esteso nel commit (c).

## 0. TLC
- Jar trovato (4 copie identiche): `/root/Desktop/BioDevOps/formal_methods/tla2tools.jar` (anche `…/formal_artifacts/tools/`, `…/reproducibility_repository/formal_models/formal_artifacts/tools/`, `…/zenodo_2026-08-07/…`). **sha256 = `237332bd…a2fb` (coincide con l'atteso)**; manifest `Build-TimeStamp 2026-05-26T23:53:34Z` = TLC2 `2026.05.26.235334` dei log esistenti (`formal/logs/distributed_extension.log:2`). Non copiato nella repo. Java: OpenJDK 17.0.19; 16 core, 64 GB.
- Invocazione (identica a `scripts/run_formal.py:46-49`, per confrontabilità): in una cartella temporanea con copia di modulo+cfg, `java -Xmx4g -cp <jar> tlc2.TLC -workers 4 -metadir <tmp>/states -config X.cfg X.tla`. Aggiungo solo `-metadir` fuori dalla repo. Per le esecuzioni lunghe chiederò `-workers 8 -Xmx8g`. Nessuna esecuzione senza tuo ok esplicito, con stima prima.

## 1. Letture (vocabolario da riusare e codice rappresentato)

### 1a. Modello esistente
| Elemento | Dove | Cosa ne faccio |
|---|---|---|
| `Sites, Facts, AllowCommit, NoSite, NoFact` | `DIB.tla:22-27`, `DIB_Distributed.tla:36-47` | riuso |
| `PartitionableSites`, `ToggleBound`, `toggleCount` | `DIB_Distributed.tla:38-59,87` | riuso (bound sui toggle); per le prove di vivacità il bound passa **nelle guardie**, non in `CONSTRAINT` (vedi §2) |
| `States`, `RevokeReasons`, `Ops`, `OpRecord`, `Note`, `lastOp` | `DIB.tla:40-45,58`, `Dist.tla:63-68,89` | riuso `States`, `Note`, `lastOp`; `Ops` esteso |
| Azioni `Query, OperatorCommit, LocalRevoke, LocalRestore, SiteDown, SiteUp` | `Dist.tla:113,121,181,192,212,220` | riuse **con guardie allineate al codice** (vedi discrepanze) |
| `Dispute, Restore` atomici con fan-out | `Dist.tla:143-179` | **sostituite** da commit di stato + consegna separati |
| `Reconcile(t,f)` atomico | `Dist.tla:227-250` | **sostituita** dalla macchina GET/apply/ack/ri-pull/riparazione |
| Invarianti di stato | `ExportRequiresActive…`, `DisputeSuspendsAtReachableSites` (`Dist.tla:272-307`) | `exported/grantValid` **eliminate**: il codice non le ha (export = `state=Active`, `service.py:559-587`); restano `TypeOK` e la versione con finestra esplicita |
| Proprietà d'azione | `I1_NonEscalation` (`DIB.tla:242`, `Dist.tla:312`), `I2_SiteConfinement` (`:326`), `I3_ConservativeRestore` (`:344`), `I3_GlobalRestorePreservesLocalRevoke` (`:376`), `UnrelatedFactIsolation` (`:358`), `I2_ReconcileConfinement` (`:392`) | riuso i nomi e il pattern `[][… lastOp' …]_vars`; riscritte per le nuove azioni |
| Dimensione baseline | `formal/logs/distributed_extension.log`: 3 siti, 1 fatto, 48.960 stati distinti, 815.335 generati, 4 s | riferimento per le stime |
| cfg | `DIB_Distributed.cfg:1-35`: `SPECIFICATION Spec`, `CONSTRAINT ToggleBound`, nessuna fairness | stesso formato |

### 1b. Discrepanze modello esistente ↔ codice (da trattare nel nuovo modello e da dichiarare)
1. **Restore su sito Active:** il vecchio `Reconcile`/`Restore` non tocca uno stato `Active` (`Dist.tla:167,242`); il codice applica `restore → monitor-only` a qualunque stato tranne il veto locale (`service.py:337-341`, `_apply_fanout_row` `:356-379`). È D6/B3: il nuovo modello segue il codice e lo verifica con `NoStaleActiveAfterEpisode` (§2).
2. **Origin:** il vecchio modello mette `revokeReason="Dispute"` anche su `Disputed` (`Dist.tla:152-154`); il codice mette `origin=fanout` solo su `Revoked`, `NULL` altrimenti (`service.py:337`). Il nuovo modello usa `origin ∈ {None, Local, Fanout}` come il codice.
3. **`LocalRevoke` da `Revoked`:** vecchio: `reason=Dispute`; codice: `origin=fanout` (`service.py:417-436`). Equivalenti dopo la mappa.
4. **`OperatorCommit`:** il vecchio modello non guarda lo stato globale; il codice richiede evidence `Active` e locale `monitor-only` (`:402-415`). Allineato.
5. **Fan-out:** vecchio atomico con il commit (nessuna finestra, quindi niente D19); codice: commit (`:763-768`, `:786-794`) poi `_fan_out` (`:685`, 3 tentativi, upsert latest-wins `:665-672`).
6. **Dispute su sito `Revoked/fanout`:** il codice lo porta a `Disputed` (`:337-341`; guardia solo sul veto locale), il vecchio modello lo lascia `Revoked` (`Dist.tla:150`). Differenza semantica reale (stato meno restrittivo ma comunque sospeso): il nuovo modello segue il codice.
7. `SUSPENSION_QUORUM` = 1 per default (`:126`); il modello assume 1 (2 fuori scopo).

### 1c. Azione nuova ↔ codice (`service.py` a `HEAD`, `b17cbab`)
| Azione del modello | Codice |
|---|---|
| `CommitDispute(s,f)` / `CommitRevoke(s,f)` (stato e `fanout_seq` per fatto) | `dispute` `:747-779`: txn `:753-775` (Active→Disputed `:763-768`; Disputed e altro sito→Revoked `:771-773`; altrimenti noop); `fanout_seq+1` per fatto |
| `CommitRestore(f)` | `restore` `:781-801`: txn `:783-796`, 409 se status Active `:790-791`; `disputed_by=NULL`, seq+1 |
| `DeliverDirect(t, rec)` | `_deliver_to_site` `:656-683`: POST `/apply_fanout` `:663-669` → `apply_fanout` `:458-461` → `_apply_fanout_row` |
| `EnqueueOnFailure` | `:670-683` (upsert, `WHERE excluded.seq > pending_fanout.seq`) dopo i 3 tentativi; solo `httpx.HTTPError` `:675-676` |
| `LoseEvent` (D19) | eccezione fra commit (`:778`) e `_fan_out` (`:779`/`:800`), o non-HTTP in `_deliver_to_site` `:675`, o INSERT outbox fallita |
| `ReconcileRead(t)` | `get_pending` `:810-829` (righe outbox + `current` nella stessa txn `:813-818`) chiamata da `_reconcile_once` `:482-533` (GET `:507-511`) |
| `ReconcileApply(t,item)` | ciclo `:520-528` → `_apply_fanout_row` `:356-379` (guardie: seq `:365-366`, veto restore `:367-371`, veto dispute/revoke `:372-376`, origin `:377-379`; nessun record `:360-363`) |
| `ReconcileAck(t)` per coppia / cancella-tutto | `ack_pending` `:831-846` (`req is None` → `DELETE … WHERE site_id` `:836-838`; coppia `seq<=` `:839-845`); chiamata del sito `:529-533` nel `finally` |
| ri-pull | `for _round in range(_RECONCILE_MAX_ROUNDS)` `:505` (=3) |
| `AntiEntropy(t,f)` = passo di `_repair_from_snapshot` | `:463-480`, chiamata `:532`; `applied_seqs` letto una volta `:528-531`; mappa stato→evento `_STATUS_EVENT` `:803-808` |
| `SiteDown/SiteUp` | `FakeNet.down` (test); in produzione partizione/arresto |
| `LocalRevoke/LocalRestore/OperatorCommit/Query` | `:417-436`, `:438-456`, `:402-415`, `:381-400` (`Query` stagia con `last_applied_seq = fanout_seq` `:393-396`, solo se status Active `:383`) |
| single flight del trigger | `_reconcile_lock` `:535`, route `:537-556`: **una sola esecuzione di riconciliazione per sito** → una macchina `rc[t]` |

## 2. Specifica proposta (scheletro) — modulo `DIB_AE.tla`
**Variabili.** Evidence: `estatus[f] ∈ {Active, Disputed, Revoked}`, `eseq[f] ∈ 0..MaxSeq`, `disputedBy[f] ∈ Sites ∪ {NoSite}`; `outbox[t][f] ∈ {NoRow} ∪ [seq, ev]` (una riga per coppia, latest-wins); `todo` = insieme di consegne dirette in volo `[site, fact, seq, ev]` (aggiunto dal commit di stato, consumato da `DeliverDirect`/`LoseEvent`: qui vive la finestra D19 e l'ordine arbitrario delle consegne, cioè la concorrenza). Sito: `sstate[t][f] ∈ States`, `sorigin[t][f] ∈ {None,Local,Fanout}`, `lastApplied[t][f] ∈ 0..MaxSeq`. Macchina di riconciliazione `rc[t] = [phase ∈ {idle, applying, acking, repairing}, snapRows, snapCur, applied, round]`. Rete: `unreachable`, `toggleCount`. Fantasma: `gen[f]` (episodi aperti, per D6/B3), `commitGen[t][f]`, contatori `evCount`, `lossCount`. `lastOp` come nell'esistente.
**Azioni:** `CommitDispute/CommitRevoke/CommitRestore` (stato+seq+`todo`, atomiche come la txn SQLite); `DeliverDirect(t,rec)` (se `t` raggiungibile → `ApplyRow`; se no → `EnqueueOnFailure` con upsert latest-wins); `LoseEvent(f,seq)` (toglie dal `todo` i record del commit senza accodare; ≤ `MaxLoss`); `ReconcileStart/Read(t)` (snapshot atomico di righe outbox del sito e, se `AntiEntropy`, di `current` dei fatti con `eseq>0` mappati da `estatus`); `ReconcileApply(t)` (un item per passo, ordine arbitrario → ammette eventi concorrenti fra gli apply); `ReconcileAck(t)` (`AckPerPair`: `DELETE seq<=` per coppia applicata; altrimenti cancella tutte le righe del sito); passo `ReRead` se `ReRead ∧ round<MaxRounds ∧ qualcosa applicato`; **`AntiEntropy(t,f)`** = passo di riparazione sull'**ultimo** snapshot (anche con outbox vuota), via `ApplyRow`, senza ack; `SiteDown/SiteUp` (il `SiteDown` azzera `rc[t]`: arresto/partizione che interrompe il giro — dichiarato); `Query, OperatorCommit, LocalRevoke, LocalRestore` allineate al codice (vedi 1b). `ApplyRow(t,f,seq,ev)` è **una sola definizione** (copia fedele di `:356-379`) usata da consegna, riconciliazione e riparazione: le guardie (seq, veto, origin, mai `Active`) sono quindi le stesse per costruzione.
**Costanti-flag:** `AntiEntropy`, `AckPerPair`, `ReRead`, `MaxLoss` (0 = `LoseEvent` spento), `MaxRounds` (3 come `:505`), `MaxEvents`, più i flag di mutazione (default FALSE) `MutIgnoreOrigin`, `MutWriteActive`, `MutNoSeqGuard`, `MutNonAtomicSnapshot`, `MutRestoreKeepsActive`. Scelta: **flag nello stesso modulo**, non copie testuali come `formal/mutations/m1..m6` (meno deriva fra le copie; ogni mutante differisce da `Spec` di una sola riga controllabile). Da te se preferisci le copie.
**Sicurezza (invarianti e proprietà d'azione):**
- `TypeOK`; `I1_NonEscalation` (Active solo da `Commit` locale da `monitor-only`); `I2_SiteConfinement`, `I2_ApplyConfinement` (consegna/riconciliazione/riparazione toccano solo `(t,f)`); `I3_ConservativeRestore` (un `restore` approda a `monitor-only`, mai `Active`); `I3_VetoPreserved` (`(Revoked,Local)` cambia solo per `LocalRestore`); `UnrelatedFactIsolation`; `LastAppliedMonotone` e `NoRegression` (snapshot vecchio non regredisce).
- `CaughtUpIsCoherent`: se `lastApplied[t][f]=eseq[f]` e il record esiste, lo stato è coerente con `estatus` (stato ≠ Active ⇒ sito ∈ {Disputed, Revoked}); è la forma "sicurezza" della finestra: l'esposizione è possibile **solo** con `lastApplied<eseq`. `DisputeSuspendsAtReachableSites` con finestra esplicita = stessa cosa più `t` raggiungibile e nessun `todo`/riga in volo per `(t,f)`.
- `OutboxNeverDropsUnapplied` (proprietà d'azione su `ReconcileAck`): ogni riga cancellata ha `seq ≤ lastApplied[t][f]` (o sito senza record, che il codice acka come no-op `:360-363`); copre "righe con seq maggiore delle lette o di altri fatti" (D12, serve 2 fatti per il caso "altro fatto").
- `LagCoveredByQueue` (solo diagnostica per V0/V1): `lastApplied<eseq` ⇒ esiste `todo` o riga con `seq>lastApplied`. Atteso violato da D12 (V0) e D19 (V1); **non** è richiesto a V2/V3, dove l'AE copre per costruzione (lo dichiaro: con AE è tautologico).
- **D6/B3 `NoStaleActiveAfterEpisode`**: sito `Active` con `lastApplied=eseq` ⇒ `commitGen[t][f]=gen[f]` (un sito rimasto Active per un intero episodio dispute+restore finisce in `monitor-only`). Mutante `MutRestoreKeepsActive` (restore non tocca Active = comportamento del vecchio `Reconcile`) deve violarlo.
**Vivacità:** con `MaxEvents`, `MaxLoss`, toggle finiti **fra le guardie** (non `CONSTRAINT`: un vincolo di stato tronca i comportamenti e rende i controlli temporali non affidabili): `Spec_L == Init /\ [][Next]_vars /\ WF(ReconcileStep(t)) /\ WF(AntiEntropyStep(t,f)) /\ WF(DeliverDirect)`, con le azioni di sito abilitate solo con `t ∉ unreachable`. Con i toggle finiti `t` diventa prima o poi raggiungibile per sempre → `WF` basta (niente `SF`).
- `ConvergedEventually == <>[] Converged`, `Converged = ∀ t raggiungibile, f con record: lastApplied[t][f] = eseq[f]`.
- `ExposureEnds == ∀t,f: ActiveWhileDisputedOrRevoked(t,f) ~> ¬ActiveWhileDisputedOrRevoked(t,f)`.
- Opzionale E1 (dopo il nucleo, stima separata): surrogato logico del bound `T+J+2·d_run`: contatore fantasma di **giri completi** per sito; "ogni evento è applicato entro 2 giri completi del sito" (il giro in corso allo scatto dell'evento + il successivo = il `2·d_run` del caso avverso T5, audit 05 §4).
**Il tempo resta fuori.** La fairness sostituisce `T`, `J`, `d_run`: dice che il giro **prima o poi** parte e termina (vivacità), non **quando**. Si può concludere: sotto le ipotesi di fairness e raggiungibilità, l'evento è applicato; non si può concludere nulla su `T+J+2·d_run` in secondi. Un `Tick` discreto è realizzabile (orologio 0..K per sito + deadline) ma moltiplica lo spazio per K^N e aggiunge solo una scala arbitraria: **rimandato**; E1 è la forma logica del bound a costo molto minore. Misure di tempo restano ai test (T5) e agli esperimenti.

## 3. Matrice delle esecuzioni (ipotesi PRIMA di lanciare)
Configurazione base: 2 siti, 1 fatto (poi 2 fatti per D12 "altro fatto"). `AllowCommit=TRUE`.
| Run | Flag | Ipotesi (attesa) | Cosa falsificherebbe |
|---|---|---|---|
| **V0** | AE off, `AckPerPair` off, ReRead off/on, `MaxLoss=0` | `ConvergedEventually` **violata** (D12: evento accodato fra GET e ack, ack cancella-tutto); `OutboxNeverDropsUnapplied` e `LagCoveredByQueue` violate; traccia = `_lost_restore` | Il modello converge: allora il modello non rappresenta D12 (sbagliato) o `ReRead` lo maschera: va indagato, non assolto |
| **V1** | AE off, `AckPerPair` on, ReRead on, `MaxLoss=1` | D12 chiuso (`OutboxNeverDropsUnapplied` vale); **D19 violato**: `ConvergedEventually` e `LagCoveredByQueue` violate con `LoseEvent`; con `MaxLoss=0` converge | Converge anche con `LoseEvent`: la perdita non è modellata bene |
| **V1b** | come V1, `MaxLoss=0`, ReRead off | converge ma `ExposureEnds` può avere finestra residua (T5-like); nessuna perdita | — (esplorativa) |
| **V2** | AE on, `AckPerPair` on, ReRead on, `MaxLoss≥1` | tutte le proprietà di sicurezza e vivacità tengono; `NoStaleActiveAfterEpisode` tiene; finestre dichiarate: sito irraggiungibile, evento dopo l'ultimo snapshot (rientra nella vivacità) | Una violazione di `I3_VetoPreserved`/`CaughtUpIsCoherent`: bug reale nella riparazione o nel modello, da riportare come trovato |
| **V3** | AE on, `AckPerPair` off | **converge** (mascheramento, come i test) ma `OutboxNeverDropsUnapplied` violata | Converge e l'invariante tiene: l'ack cancella-tutto non è modellato; oppure l'invariante è mal formulata |
| M-AE1 | V2 + `MutIgnoreOrigin` | viola `I3_VetoPreserved` (veto locale sovrascritto da un `revoke/restore` riparato) | nessuna violazione: l'AE non è esposta al veto (improbabile) o il veto non è raggiungibile nel bound |
| M-AE2 | V2 + `MutWriteActive` (restore → Active) | viola `I1_NonEscalation` e `I3_ConservativeRestore` | nessuna violazione ⇒ bound troppo piccolo |
| M-AE3 | V2 + `MutNoSeqGuard` | viola `NoRegression`/`LastAppliedMonotone` con snapshot vecchio (evento più nuovo consegnato fra lettura e riparazione) | nessuna violazione ⇒ snapshot vecchio non raggiungibile nel modello |
| M-AE4 | V2 + `MutNonAtomicSnapshot` (righe e `current` letti in passi separati, in entrambi gli ordini) | **previsione: nessuna violazione** (la riparazione non fa ack e i seq filtrano); se TLC non trova nulla, l'atomicità nella stessa txn non è necessaria per la sicurezza, solo prudenziale: lo riporto come tale | una violazione = l'atomicità è necessaria, e la traccia dice perché |
| M-AE5 | V2 + `MutRestoreKeepsActive` | viola `NoStaleActiveAfterEpisode` (D6/B3 riprodotto) | nessuna violazione ⇒ la proprietà è vuota |
Per ogni run: log in `formal/distributed_ae/logs/` con nome nuovo (`ae_v0.log` …); l'esito si riporta **così com'è**, comprese le ipotesi che cadono.

## 4. Dimensione, rischi, copertura
- **Fasi.** S0: 2 siti, 1 fatto, `MaxEvents=2`, toggle ≤ 2 (solo controllo semantica, V2): stima ≲ 10^5–10^6 stati, secondi–1 min. S1: `MaxEvents=3` (episodio dispute+restore+dispute/revoke), stima 10^6–10^7, qualche minuto. S2: 2 siti, **2 fatti** (necessari per D12 "altro fatto"), `MaxEvents=3`: 10^7–10^8, da stimare con S1 (±10× di incertezza: le stime sono da misurare, non garantite). Baseline: 49k stati, 4 s per il vecchio modello (log). Per ogni esecuzione ti dò prima la stima aggiornata e chiedo il permesso.
- **Riduzioni.** `Sites` simmetrici solo se `PartitionableSites=Sites` (nel vecchio cfg `{s1}` rompe la simmetria); la simmetria è **non affidabile con le proprietà temporali**, quindi solo per le sole safety. Vista (`VIEW`) per escludere i fantasmi (`evCount`, `lossCount`, contatori E1) dal confronto fra stati. `MaxSeq=MaxEvents`. `todo` limitato dai bound; `rc` con un solo giro attivo per sito.
- **Fuori modello (dichiarato):** tempo (T/J/d_run), crash di processo a metà transazione, durabilità/WAL di SQLite, errori di apply per item (testato: `test_item_whose_apply_raises…`; modellabile come flag opzionale), evidence irraggiungibile (i giri del sito non partono: in modello è stutter), retry 3× (astratti: la consegna fallisce se il sito è irraggiungibile), mTLS/autenticazione, `SUSPENSION_QUORUM=2`, admissibilità/score (`admissible` astratta a TRUE), più di 3 siti.
- **Cosa resta fuori per dimensione:** 3+ siti, 3+ fatti, E1 con tre eventi concorrenti, combinazione di tutti i flag di mutazione.
- **Rischi.** (1) Un'errata astrazione di `todo` che sovra-approssima l'ordine delle consegne (ammette ordini che il codice sequenziale non produce; con cap>1 sono reali); (2) fairness mal posta rende la vivacità vuota: la verifico con un controllo negativo (togliere la `WF` ⇒ la proprietà deve cadere); (3) `<>[]` con `CONSTRAINT` non affidabile: bound nelle guardie; (4) i bound dei test (`MaxEvents=3`) non provano nulla oltre: non scrivo "verificato" oltre i bound usati.

## 5. Tracciabilità: azione ↔ codice ↔ test
| Azione | Codice | Test che la esercita |
|---|---|---|
| CommitDispute/Revoke/Restore | `:747-801` | `test_distributed_service_inproc.py:73,84,96,108`; `test_d12_…` (setup) |
| DeliverDirect + EnqueueOnFailure | `:656-683` | `inproc:147,157,169` (3 tentativi, outbox, latest-wins); `test_distributed_fanout_parallel.py` (F*) |
| LoseEvent | `:778-779,800` | `d19_spec`: `test_w_spec_…` (S1), S2 (cap 1/8), S10 |
| ReconcileRead (`current` nella stessa txn) | `:810-829` | S6 (snapshot vecchio), S8; **atomicità riga/`current` nessun test dedicato** → M-AE4 la esplora |
| ReconcileApply/ApplyRow (guardie) | `:356-379` | `inproc:221` (seq stale), `:268-313` (veto, origin), S3, S4, S5; `test_negative_control_apply_fanout_ignoring_origin` (`inproc:356`) |
| ReconcileAck per coppia / cancella-tutto | `:831-846`, `:529-533` | `test_distributed_ack_fix.py` (H-compat, H-body, controlli riscritti `1f3f19f`) |
| ReRead (ri-pull) | `:505` | `ack_fix: test_repull…`, `test_residual_window…`, controllo (b) |
| AntiEntropy / repair | `:463-480,532` | S1–S8, S9 (controllo), `d19_controls` |
| SiteDown/SiteUp | `FakeNet.down` | `inproc:125-169`; **nessun test di caduta a metà giro** (il modello lo esplora) |
| Query (staging `last_applied=fanout_seq`) | `:381-400` | da cercare i test che ne verificano `last_applied_seq` (probabile solo indiretto: **da confermare in implementazione**) |
| LocalRevoke/Restore/Commit | `:402-456` | `inproc:268-327` |
| Single flight del giro | `:535-556` | T3/T3b/T3c (`test_distributed_reconcile_trigger.py`) |
**Azioni senza test dedicato:** caduta del sito a metà giro; atomicità `pending`+`current`; staging `last_applied_seq`; errore di apply per item combinato con AE. **Discrepanze** già in §1b (1–6); altre che il modello potrebbe rivelare vanno in `07` senza correzione del codice.

## 6. Output e ordine di lavoro (dopo il tuo ok)
0. `git switch -c formal-ae` da `fix-d19`; nessun push.
1. **Commit (a):** `formal/distributed_ae/DIB_AE.tla`, cfg `ae_s0…`, `v0…v3`, `mut_ae1…5` (`.cfg`), `README`, ipotesi in commenti del modulo e nelle cfg; `docs/audit/07_modello_ae.md` con questo piano. Nessuna esecuzione; controllo di sintassi: `java -cp <jar> tla2sany.SANY` è **già** un'esecuzione di uno strumento TLA+: la lancio solo con tuo permesso (non è TLC ma lo tratto come tale).
2. **Commit (b):** per ogni run, stima → tuo ok → esecuzione → log `formal/distributed_ae/logs/*.log` e **esito riportato come sta** (ipotesi cadute incluse). Controlli negativi del modello: V2 senza `WF` (la vivacità deve cadere), mutanti M-AE1..5.
3. **Commit (c):** nota di audit `docs/audit/07_modello_ae.md` (esiti, discrepanze, tracciabilità, bound dichiarati). Nessun aggiornamento di `claims.json`/`verify_artifact.py`/paper: li decidi tu dopo.
4. Verifiche a ogni commit: `git diff fix-d19 --stat -- formal/base formal/distributed formal/logs formal/mutations scripts claims.json results code` **vuoto**; suite e `verify_artifact.py` invariati (260/2).

## 7. Da te
1. Ok al piano, al branch `formal-ae`, alla sede `docs/audit/07_modello_ae.md` (creata dopo l'ok).
2. Mutazioni come **flag** nello stesso modulo (consigliato) o come copie?
3. E1 (surrogato "2 giri completi") dentro o fuori dal primo ciclo? (consiglio: dopo V0–V3)
4. Permesso per SANY (sintassi) e per ogni esecuzione TLC, una per una, dopo la stima.
5. Se vuoi tre siti per V2, dimmelo: costerà almeno un ordine di grandezza.

## 8. Ipotesi che potrebbero cadere
- Che `todo` (consegne in volo con ordine arbitrario) non sovra-approssimi in modo da generare falsi positivi in V2.
- Che la fairness `WF` basti (toggle finiti) e non serva `SF`.
- Che 2 siti / 1–2 fatti / `MaxEvents=3` contengano gli interleaving di D12 (1 fatto) e dell'"altro fatto" (2 fatti).
- Che la stima degli stati regga: potrebbe superare di 10× o più; in tal caso riduco `MaxEvents` o i toggle e lo dichiaro.
- Che il mascheramento V3 sia riprodotto: se non lo è, o il modello o i test sbagliano, e va indagato.

---

## Chiarimenti di modellazione (lettura di `DIB_AE.tla` al commit `cd3b5fa`, prima di eseguire)
**a. Direzioni di rete.** `unreachable` indica **solo evidence → sito**: è usata in `Deliver` (la consegna fallisce e accoda se `r.site \in unreachable`, `DIB_AE.tla` azione `Deliver`), in `DisputeSuspendsAtReachableSites`, `Converged`, `ExposureEnds` e nella fairness. I passi di `RcStep(t)` (Read, Apply, Ack, RepairStart, AntiEntropy, Finish) **non** hanno guardia su `unreachable`: il pull sito → evidence prosegue durante la partizione (come nel D12 reale, dove il sito riconcilia mentre `c.net.down` blocca la consegna). La fairness è condizionata: `WF_vars(RcStep(t) /\ t \notin unreachable)`.
- (i) **Fedele al codice** per il comportamento (giro attivo con consegna fallita). (ii) **Conservativa** per la vivacità: nel codice un sito partizionato lato evidence→sito ma con processo e trigger vivi continua a riconciliare, quindi il modello garantisce *meno* (nessuna fairness finché `t ∈ unreachable`; `Converged` esclude i siti irraggiungibili; `ExposureEnds` richiede «eventualmente raggiungibile per sempre»).
- **Partizione contro processo fermo:** il modello non li distingue (un solo insieme). «Processo fermo, senza trigger» è fuori garanzia (audit 05 §6) e in modello coincide con `t ∈ unreachable` per sempre, che il modello esclude dalle conclusioni.
- **Due flag** (`unreachable` per la consegna, `stopped` per il processo/pull): la fairness dei passi del sito dipenderebbe solo da `stopped`; `Converged`/`ExposureEnds` coprirebbero anche i siti partizionati ma vivi (vivacità più forte e più vicina al codice); un sito fermo resta fuori garanzia. Costo: una variabile e un insieme di toggle in più, stati ×2–4 (da misurare). **Non implementato** (cambia la semantica): decisione tua.
**b. Riportatori e siti.** In `DIB_AE.tla` `Dispute(s,f)` ha `s \in Sites` e `edisp[f] \in Sites \cup {NoSite}`: i riportatori **sono i siti**. Nel codice `disputed_by` è l'identificatore `req.site_id` dato dall'harness (`service.py:747-751`, nei test `rep-a`, `rep-b`), non necessariamente un sito. Con 2 siti il D12 minimo (dispute, restore con consegna fallita) **è rappresentabile anche con il sito in ritardo non riportatore** (riporta l'altro sito; il riportatore non è accoppiato alla destinazione della consegna). Lo scenario con **revoke** (due voti distinti) e sito in ritardo **non riportatore** richiede 3 identità: 3 siti (costo stimato ≥ un ordine di grandezza in stati, `rc` per sito) oppure **identificatori di riportatore astratti** separati dai siti (modifica semantica, una costante `Reporters` e `edisp \in Reporters`; costo stimato ≈ ×1,5 stati). Raccomandazione: riportatori astratti, 2 siti. **Non modificato.**

## Esecuzioni
**Ambiente.** Jar `/root/Desktop/BioDevOps/formal_methods/tla2tools.jar`, sha256 `237332bdcc79a35c7d26efa7b82c77c85c2744591c5598673a8a45085ff2a4fb` (**coincide**). Java OpenJDK 17.0.19. TLC `2026.05.26.235334 (rev: 4ba7d88)` (**coincide** con i log esistenti). 16 core, 64 GB totali, 55 GB liberi.
**SANY** (`java -cp <jar> tla2sany.SANY DIB_AE.tla`, copia in `/tmp/dib_ae_tlc/sany`): **nessun errore** (SANY2 2.2): `Semantic processing of module DIB_AE`, `Linting of module DIB_AE`, uscita 0. Nessuna correzione sintattica necessaria. **Le 21 cfg**, controllo per lettura (script di verifica nomi, non TLC): ogni `INVARIANT`/`PROPERTY` esiste nel modulo, ogni costante del modulo è assegnata, `SPECIFICATION` ∈ {`Spec`,`SpecL`}: nessun rifiuto atteso (non eseguite, tranne s0).
**s0_smoke** (un solo run; `SpecL`, 2 siti, 1 fatto, `MaxEvents=2`, `MaxLoss=1`, `MaxToggles=3`; tutte le proprietà). Invocazione: `java -Xmx16g -cp <jar> tlc2.TLC -workers 8 -metadir /tmp/dib_ae_tlc/s0/states -config s0_smoke.cfg DIB_AE.tla`, `timeout 900`; deadlock: controllo di default di TLC acceso (il modello ha sempre un passo abilitato, `ReconcileRead` da `idle`; nessuna `CONSTRAINT`, nessuna simmetria). Log: `formal/distributed_ae/logs/s0_smoke_run1.log`.
**Esito: l'ipotesi della cfg è caduta.** TLC si è fermato al primo errore: `Error: Action property I3_ConservativeRestore is violated.` dopo **4.528 stati generati, 2.912 distinti, 2.363 in coda, profondità 6, 1 s** (esaurimento non raggiunto: **nessun'altra proprietà è stata verificata in questo run**; invarianti e vivacità non sono state né confermate né smentite). Memoria massima: **non misurata in modo affidabile** (campionato il processo `timeout`, non la JVM); lo spazio esplorato è minuscolo.
**Controesempio, in linguaggio naturale** (6 stati): iniziale tutto Absent/Active; (2) `EvDispute` di `s1` (seq 1, due consegne in volo, per `s1` e `s2`); (3) `EvRestore` (seq 2, altre due consegne in volo; evidence di nuovo Active); (4) `Query(s1)`: `s1` stagia `MonitorOnly` con `lastApplied = 2`; (5) `OperatorCommit(s1)`: `s1` Active; (6) `Deliver` della consegna **in ritardo** `restore seq 2` verso `s1`: `ApplyResult` ha `seq <= lastApplied` → no-op, `s1` resta Active; `lastOp = {Deliver, restore}`.
**Natura del difetto:** è un difetto della **formulazione della proprietà**, non del codice né dell'azione. `I3_ConservativeRestore` (`DIB_AE.tla`) richiede `sstate' # "Active"` per ogni `Deliver/Apply/AntiEntropy` di un `restore`, senza escludere i no-op guardati dal seq; il codice, sul no-op, esce prima (`service.py:365-366`, `return` con `seq <= last_seq`) e lascia lo stato com'è. Per costruzione il vecchio test nel modello esistente (`Dist.tla:344-348`) lo evitava perché i `restore` non erano consegne in ritardo. Il modello dunque è fedele al codice qui; la proprietà è mal posta. **Correzione proposta (NON applicata, sarebbe un ritocco del modello per far tornare l'ipotesi: decisione tua):** aggiungere nell'antecedente `lastOp'.seq > lastApplied[lastOp'.site][lastOp'.fact]`, cioè «un restore *applicato* (non un duplicato/stale) non produce Active». Scenario collaterale utile: la consegna in volo di un evento vecchio verso un sito appena staggiato è reale (`/query` stagia con `last_applied_seq = fanout_seq`, `service.py:393-396`).
**Stima per i run successivi.** Non estrapolabile dal solo s0: TLC si è fermato a profondità 6 con 2,9k stati distinti, prima di qualunque saturazione, quindi nessuna curva di crescita osservata. Per ora restano le stime del piano (§4: S0 ≲ 10^5–10^6 stati; `MaxEvents=3` 10^6–10^7; 2 fatti 10^7–10^8), che **non sono confermate**. Velocità osservata: ~4,5k stati generati/s su 8 worker, ma con il solo avvio della ricerca (non rappresentativa). Per misurare la crescita serve un run di s0 che esaurisca lo spazio: richiede la correzione della proprietà (o un tuo ok a un run senza `I3_ConservativeRestore`).
