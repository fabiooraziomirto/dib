# Audit 67 — Modello DIB_AE_NA: operazioni non atomiche, correzione candidata, quorum 2 (pre-registrazione e risultati)

Data: 2026-10-12/13 (notte). Branch `tnsm-fsm`. Obiettivo dato dall'utente per la notte: "un modello
valido per il paper (facendo attenzione a non andare OOM) e che migliori il paper".

## 1. Perché
Il modello pubblicato del protocollo reale, `formal/distributed_ae/DIB_AE.tla`, rende atomiche
Query, OperatorCommit e LocalRestore: legge lo stato dell'evidence e scrive lo stato locale nello
stesso passo (MAE:244-280). Il codice non lo fa (audit 63 D6), e i test dell'audit 64 hanno mostrato
tre finestre reali (b3q, b3c, b3r). Un modello che le esclude per costruzione non è "valido" per il
prototipo: le garanzie che il paper riporta dal modello (main_wip.tex:547, Table tab:tla)
valgono solo per una versione atomica che non esiste.

## 2. Cosa ho fatto (senza toccare `formal/`)
`experiments_tnsm/tla_fsm/DIB_AE_NA.tla` = copia di `DIB_AE.tla` con le aggiunte marcate `[NA]`:
- **E2:** per i siti in `SplitSites`, Query, Commit e LocalRestore sono divisi in Read (GET
  /scores) e Write (transazione locale), come S:500→516, S:522→532, S:560-564→575. Fra i due passi
  possono avvenire eventi dell'evidence, consegne e reconcile. Una sola operazione pendente per sito.
- **FixRace:** correzione candidata.
  - Write di Commit e LocalRestore rifiuta se `last_applied_seq` > seq letto.
  - Il commit è in due fasi: stato `Committing` (non esportabile), seconda lettura dell'evidence,
    promozione ad Active solo se seq invariato e stato Active; altrimenti torna MonitorOnly.
- **E5:** `Quorum = 2` con `votes[f]` (S:908-911) e due regole di conferma: codice (`r # disputed_by`,
  S:918) e regola dell'utente (`r ∉ votes`).
- **Ghost `dirty[s]`:** un evento dell'evidence sul fatto dell'operazione pendente di s è avvenuto
  fra la sua prima lettura e il suo punto di linearizzazione.
- **Proprietà nuove:**
  - `I1_CommitOnUndisputedEvidence` (riga :321 della tabella come linearizzabilità);
  - `NoMonitorOnlyCaughtUpDuringEpisode` (:320, :326);
  - `CommittingIsTransient`;
  - `RevokeConfirmedByOutsider` (a10);
  - testimoni di non vacuità `NeverActiveOnSplitSite` e `NeverRevoked`;
  - diagnostica `LocalRestoreOnClosedEpisode`.
- `I1_NonEscalation`, `I2_SiteConfinement` e `UnrelatedFactIsolation` sono estesi alle nuove azioni:
  I2 controlla anche origin e last_applied dei pari.

## 3. Ipotesi (pre-registrate nelle cfg, prima di ogni esecuzione)
Limiti di tutte le cfg salvo dove indicato: quelli di `formal/distributed_ae/s0_safe_l0r2.cfg`
(2 siti, 1 fatto, MaxEvents 2, MaxLoss 0, MaxRounds 2, MaxToggles 3).

| cfg | Ipotesi | Falsificata se |
|---|---|---|
| `r0_regress` | estensione conservativa: con `SplitSites={}` e Quorum 1 nessuna violazione e **esattamente 14.947.820** stati distinti (`s0_safe_l0r2_run1.log:34`) | violazione o conteggio diverso |
| `n1_commit_race` | senza FixRace `I1_CommitOnUndisputedEvidence` è violata (b3c) | nessuna violazione |
| `n2_lrestore_race` | senza FixRace `NoMonitorOnlyCaughtUpDuringEpisode` è violata (b3r) | nessuna violazione |
| `n3_caughtup` | senza FixRace l'invariante ORIGINALE `CaughtUpIsCoherent` è violato | nessuna violazione |
| `n4_rest` | senza FixRace tutte le ALTRE proprietà originali reggono (le finestre rompono le precondizioni della tabella, non la sicurezza dell'export) | qualunque violazione |
| `f1_fix` | con FixRace nessuna violazione di alcuna proprietà originale o nuova | qualunque violazione |
| `f1_witness` | con FixRace un commit diviso può arrivare ad Active | nessuna violazione |
| `f1_lrestore_strict` | anche con FixRace la forma stretta di LocalRestoreOnClosedEpisode è violata (dispute committata e non ancora consegnata: la stessa finestra di ogni fan-out) | nessuna violazione |
| `q1_code_rule` | quorum 2, regola del codice: `RevokeConfirmedByOutsider` violata | nessuna violazione |
| `q2_outsider_rule` | quorum 2, regola dell'utente: nessuna violazione | qualunque violazione |
| `q2_witness` | quorum 2, regola dell'utente, 3 reporter: la revoca è raggiungibile | nessuna violazione |

## 4. Protezioni (OOM, disco)
`experiments_tnsm/tla_fsm/run_tlc.sh`:
- heap JVM limitato (`-Xmx`, default 20 GB su 64 GB, nessuno swap);
- un run alla volta;
- watchdog che uccide TLC se lo spazio libero su `/` scende sotto 8 GB: il disco è al 94%, con
  34 GB liberi all'inizio;
- metadir nello scratchpad della sessione, cancellata a fine run;
- jar verificato per sha256 (`237332bd…`, lo stesso degli audit 01 e 07, fuori dal perimetro DIB,
  usato in sola lettura come in quegli audit);
- manifest in `experiments_tnsm/tla_fsm/logs/manifest.tsv`.

## 5. Risultati del batch 1 (modello a `ba68604`, 2026-10-11 23:33-23:40Z)
Ogni run: heap 16-24 GB, 8 worker, jar `237332bd…`, Java 17.0.19. Log in
`experiments_tnsm/tla_fsm/logs/<cfg>.log`, una riga per run in `logs/manifest.tsv`.

| cfg | Previsione | Esito | Stati distinti | Traccia |
|---|---|---|---|---|
| `n1_commit_race` | violazione | **confermata** | 3.005 | QueryRead, QueryWrite, CommitRead, Dispute, CommitWrite → Active con evidence Disputed (= b3c senza partizione: la consegna è ancora in volo) |
| `n2_lrestore_race` | violazione | **confermata** | 48.173 | QueryRead/Write, LocalRevoke, LRRead, Dispute, Deliver (veto: solo last_applied → 1), LRWrite → MonitorOnly con last_applied = eseq = 1 (= b3r) |
| `n3_caughtup` | violazione dell'invariante ORIGINALE CaughtUpIsCoherent | **confermata** | 57.934 | stessa finestra b3r |
| `q1_code_rule` | violazione | **confermata** | 185 | Vote(r1), Dispute(r2) → disputed_by = r2, Dispute(r1) → Revoked (= a10) |
| `f1_witness` | violazione (non vacuità) | **confermata** | 13.859 | con FixRace un commit diviso arriva ad Active |
| `q2_witness` | violazione (non vacuità) | **confermata** | 196 | con la regola outsider e 3 reporter la revoca è raggiungibile |
| `f1_lrestore_strict` | violazione (diagnostica) | **confermata** | 15.224 | dispute committata ma ancora in `todo` quando LRWrite scrive: la finestra di qualunque fan-out |
| `r0_regress` | nessuna violazione, esattamente 14.947.820 stati | **confermata** | **14.947.820**, profondità 32, 3 min 48 s | — |
| `n4_rest` | nessuna violazione delle altre proprietà originali | **FALSIFICATA** | 509 | QueryRead (Active), Dispute, Deliver a s1 (riga assente: no-op), QueryWrite → MonitorOnly su un sito raggiungibile senza nulla in volo: viola l'invariante ORIGINALE `DisputeSuspendsAtReachableSites` (= b3q) |
| `f1_fix` | nessuna violazione | **FALSIFICATA** | 498 | stessa traccia di n4: FixRace non copre la query (errore di progetto mio: avevo ritenuto b3q coperto dall'anti-entropia, che però interviene solo alla reconcile successiva) |
| `q2_outsider_rule` | nessuna violazione | **confermata** | **64.458.470**, profondità 34, 16 min 58 s (3 reporter, quorum 2) | — |

Lettura:
- Il modello esteso riproduce esattamente il modello pubblicato quando le operazioni sono atomiche
  (r0). Quindi le violazioni dipendono solo dalla divisione lettura/scrittura, non da errori
  dell'estensione.
- Con la semantica del prototipo, **due invarianti del modello pubblicato non valgono**
  (`CaughtUpIsCoherent`, `DisputeSuspendsAtReachableSites`) e la precondizione della tabella per il
  commit (main_wip.tex:321) è violabile. Le tre finestre coincidono con i test rossi dell'audit 64.
- n4 non dice ancora se **l'export** (stato Active) resta sicuro: la prima violazione trovata
  riguarda un MonitorOnly, che non è esportabile, e TLC si ferma alla prima. Serve una proprietà
  separata (batch 2).

## 6. Batch 2 — pre-registrazione (scritta dopo il batch 1, prima di eseguire il batch 2)
Modello v2 in `experiments_tnsm/tla_fsm/v2/DIB_AE_NA.tla`: il batch 1 resta legato a `ba68604`.
Aggiunte rispetto a v1:
- **FixQuery** (riserva-poi-leggi): la query divisa inserisce prima una riga `Staging` (non
  esportabile, non è una decisione), poi legge l'evidence, poi chiude: Staging → MonitorOnly se ha
  letto Active, altrimenti torna Absent. Un fan-out arrivato dopo la riserva trova la riga e si
  applica.
- **Mutazioni:**
  - `MutNoLRGuard`: FixRace senza la guardia su last_applied in LRWrite;
  - `MutNoVerify`: commit Active alla scrittura, con la guardia ma senza la seconda lettura.
- **Proprietà:**
  - `ExportSafeAtReachableSites`: la metà "export" di DisputeSuspendsAtReachableSites, cioè nessun
    Active su un sito raggiungibile senza nulla in volo mentre l'evidence ha il fatto
    disputed/revoked;
  - `DisputeSuspendsAtReachableSitesV2`: come l'originale, ma ammette `Staging` mentre la query del
    sito su quel fatto è pendente;
  - `StagingIsTransient`;
  - testimone `NeverMonitorOnlyOnSplitSite`.

| cfg | Ipotesi | Falsificata se |
|---|---|---|
| `r1_regress_v2` | v2 conservativa: SplitSites={} → nessuna violazione, esattamente 14.947.820 stati | violazione o altro conteggio |
| `n5_export_nofix` | semantica del PROTOTIPO (s1 diviso, nessuna correzione): ExportSafe, NoStaleActiveAfterEpisode e tutte le proprietà d'azione originali reggono | qualunque violazione |
| `f2_fix_all` | FixRace + FixQuery: nessuna violazione di nessuna proprietà | qualunque violazione |
| `f2_orig_strict` | con le correzioni l'originale DisputeSuspends è violato SOLO da una riserva Staging | nessuna violazione, o record non Staging |
| `f2_witness_mo`, `f2_witness_active` | con le correzioni query e commit divisi arrivano a MonitorOnly e ad Active | nessuna violazione del testimone |
| `m2_nolrguard` | senza la guardia di LRWrite: NoMonitorOnlyCaughtUpDuringEpisode violato | nessuna violazione |
| `m3_noverify` | senza seconda lettura: I1_CommitOnUndisputedEvidence violato | nessuna violazione |
| `m4_noqueryfix` | senza FixQuery: DisputeSuspendsAtReachableSitesV2 violato | nessuna violazione |
| `f3_two_split` | correzioni su ENTRAMBI i siti, MaxToggles 2: nessuna violazione | qualunque violazione (incompleto oltre 3 h = riportato come tale) |

## 7. Patch candidata su COPIA di service.py — pre-registrazione
`code/tests/tests/test_distributed_fsm_fix_copy.py`: la correzione verificata nel modello v2 è
tradotta in sostituzioni di testo applicate a una copia di service.py (`make_source_copy`). Il file
reale non è toccato: è congelato per hash e serve il tuo OK.
- **FQ:** riserva `staging`, poi seconda lettura e chiusura.
- **FC:** commit in due fasi `committing`.
- **FR:** guardia `last_applied_seq` in local restore.
- **FV:** local revoke senza evidence (b4).
- **FQ2:** conferma con quorum 2 da un segnalante fuori dai voti (a10).

Ipotesi H-F1..H-F4 nel docstring del file (le ipotesi originali dei test rossi valgono sulla copia;
H-b3r-2 corretta in H-F2; i test verdi restano verdi; ciclo base invariato). Ogni ancora compare
una sola volta nel service.py reale (controllato prima di eseguire).

Esito (2026-10-12, notte): **11 passed in 1,75 s**. H-F1..H-F4 confermate.

### 7.1 Regressione della copia corretta su tutti i test distribuiti — pre-registrazione
Comando: i file `code/tests/tests/test_distributed_*.py` eseguiti con un plugin pytest (nello
scratchpad, non nella repo) che punta `_dist_harness.DIST_SOURCE` alla copia corretta. Così ogni
`Cluster` senza `source` esplicito, e ogni mutante costruito da `make_source_copy`, parte dalla copia.
**Ipotesi:** ogni fallimento appartiene a una di queste classi, previste:
(i) test `*_characterization` che fissano i comportamenti corretti dalla patch (b3, b4, a10:
`test_distributed_fsm_races.py` e `test_distributed_service_inproc.py:108`);
(ii) test `xfail(strict=True)` del file delle race, che sulla copia passano (XPASS strict = failed);
(iii) controlli negativi la cui ancora di testo cade in una regione riscritta ("anchor not found").
Falsificata da un fallimento fuori da queste classi.

Esito 7.1: **127 passed, 12 failed, 1 xfailed in 24,0 s.**
- 6 fallimenti di classe (i): `test_suspension_quorum_2_two_distinct_sites_suffice_characterization` e
  le 5 caratterizzazioni `*_observed_*` del file delle race.
- 5 di classe (ii): gli xfail strict b3q-1, b3c-1, b3r-1, b4-1, a10, che passano sulla copia.
- Nessuno di classe (iii): nessun controllo negativo ha perso la sua ancora.
- **1 fuori dalle classi dichiarate: l'ipotesi 7.1 è FALSIFICATA come scritta.**
  `test_b3q_2_reconcile_repairs_query_race` fallisce perché sulla copia la corsa non crea più alcun
  record (H-b3q-1 vale), quindi non c'è niente che una reconcile possa portare a disputed. Il
  fallimento è la conseguenza attesa della correzione, ma non era nell'elenco pre-registrato.
- L'unico xfail rimasto è b3r-2: sulla copia il record resta revoked/local, come dice la nota
  dell'audit 64.
- Tutti gli altri 127 test (D12, D19, trigger, fan-out parallelo, keep-alive, ack, inproc) passano
  sulla copia corretta.

## 8. Risultati del batch 2 (modello v2, 2026-10-11 23:57Z - 2026-10-12 00:03Z)
| cfg | Previsione | Esito | Stati distinti | Nota |
|---|---|---|---|---|
| `f2_witness_mo` | violazione | **confermata** | 435 | con FixQuery la query divisa arriva a MonitorOnly |
| `f2_witness_active` | violazione | **confermata** | 54.231 | con le correzioni il commit diviso arriva ad Active |
| `m2_nolrguard` | violazione | **confermata** | 143.253 | senza guardia in LRWrite torna b3r |
| `m3_noverify` | violazione | **confermata** | 16.735 | senza seconda lettura torna b3c |
| `m4_noqueryfix` | violazione | **confermata** | 857 | senza FixQuery torna b3q |
| `f2_orig_strict` | violazione SOLO da Staging | **confermata** | 425 | ultimo stato: s1 `Staging` dopo QueryReserve con la dispute già consegnata (Absent → no-op) |
| `r1_regress_v2` | nessuna violazione, 14.947.820 | **confermata** | **14.947.820**, profondità 32, 3 min 48 s | |
| `n5_export_nofix` | nessuna violazione | **FALSIFICATA (errore mio nella proprietà)** | 2.946 | `I3_VetoPreserved` esentava solo `LocalRestore`; la traccia è una local restore legittima del sito (LRRead, LRWrite, nessuna dispute) |
| `f2_fix_all` | nessuna violazione | **FALSIFICATA (stessa causa)** | 18.022 | idem |
| `f3_two_split` | nessuna violazione | **FALSIFICATA (stessa causa)** | 18.504 | idem; il run è finito in 1 s, prima che lo fermassi |

Le tre falsificazioni non dicono nulla sul sistema: dicono che la proprietà non era stata estesa
all'azione divisa (ho esteso I1, I2 e l'isolamento, ma non I3_VetoPreserved). Restano registrate così.
Il batch 3 ripete i tre run con la proprietà corretta.

## 9. Batch 3 — pre-registrazione (modello v3 = v2 + `I3_VetoPreserved` che esenta anche `LRWrite`)
`experiments_tnsm/tla_fsm/v3/`. Corpo delle cfg identico a quello di v2, salvo `v3_mut_veto`.
| cfg | Ipotesi | Falsificata se |
|---|---|---|
| `v3_mut_veto` | la proprietà corretta non è vuota: con le correzioni e `MutIgnoreOrigin` è violata | nessuna violazione |
| `v3_n5_export_nofix` | come H-n5 (semantica del prototipo, export sicuro, proprietà d'azione originali) | qualunque violazione |
| `v3_f2_fix_all` | come H-f2 (correzioni: nessuna violazione) | qualunque violazione |
| `v3_r1_regress_v2` | nessuna violazione, 14.947.820 stati | violazione o altro conteggio |
| `v3_f3_two_split` | come H-f3 (correzioni su entrambi i siti, MaxToggles 2) | qualunque violazione; incompleto oltre 3 h = riportato come tale |

## 10. Risultati del batch 3 (modello v3) e verifica sul codice reale
| cfg | Previsione | Esito | Stati distinti | Nota |
|---|---|---|---|---|
| `v3_mut_veto` | violazione | **confermata** | 1.004 | la proprietà corretta non è vuota |
| `v3_n5_export_nofix` | nessuna violazione | **FALSIFICATA (reale)** | 44.783 | `NoStaleActiveAfterEpisode` (invariante del modello pubblicato) |
| `v3_f2_fix_all` | nessuna violazione | **FALSIFICATA (proprietà da adattare)** | 82.851 | `OutboxNeverDropsUnapplied`, vedi sez. 11 |

**Traccia di v3_n5, un difetto reale del prototipo.**
1. CommitRead legge Active a seq 0.
2. Dispute (seq 1) e Restore (seq 2) completano l'episodio.
3. Il restore arriva a s1: monitor-only, last_applied 2.
4. CommitWrite → **Active**.
5. La consegna della dispute (seq 1) è scartata perché 1 ≤ 2.

Un'approvazione decisa su evidenza precedente all'episodio diventa Active dopo il restore, aggiornata
ed esportabile, senza un commit successivo al restore. Viola I3 ("Restoration requires fresh local
approval", main_wip.tex:340). L'export-safety "durante la dispute" non la vede, perché quando il
record diventa Active l'evidence è di nuovo Active.

**Sul codice reale:** `code/tests/tests/test_distributed_fsm_stale_commit.py` (pre-registrato in un
commit separato prima dell'esecuzione):
- **H-S1 falsificata come previsto:** il record è `active` dopo il commit con la lettura prima
  dell'episodio;
- **H-S2 confermata:** la copia corretta risponde 409 e lascia monitor-only;
- 1 failed, 1 passed in 0,71 s.

H-S1 resta rossa nel commit di pre-registrazione; nel commit dei risultati è marcata
`xfail(strict=True)` con un test di caratterizzazione, come gli altri.

## 11. Batch 4 — pre-registrazione (v4 = v3 + OutboxNeverDropsUnapplied con Staging come Absent)
**Seconda correzione di una proprietà dopo un risultato: la dichiaro come tale.** Nella traccia di
v3_f2:
1. una dispute è messa in outbox mentre s1 è Absent;
2. la reconcile la applica come no-op;
3. QueryReserve crea Staging;
4. l'ack cancella la riga, e la proprietà guarda lo stato all'ack (Staging) invece che
   all'applicazione (Absent).

Argomento per cui nessun evento si perde: un fan-out applicato a una riga Staging la sposta sempre
(il suo last_applied è 0 e ogni seq è ≥ 1), quindi Staging all'ack implica che l'applicazione è
avvenuta su Absent. In più la riserva precede la seconda lettura, che vede l'evento.

Controllo di non vacuità: `v4_mut_ack` (ack "cancella tutto", D12) deve violare la proprietà v4.

| cfg | Ipotesi | Falsificata se |
|---|---|---|
| `v4_mut_ack` | la proprietà v4 non è vuota | nessuna violazione |
| `v4_n6_export_nofix` | semantica del PROTOTIPO, senza NoStaleActiveAfterEpisode: export sicuro ai siti raggiungibili e tutte le proprietà d'azione originali | qualunque violazione |
| `v4_f2_fix_all` | correzioni su s1: nessuna violazione di nessuna proprietà | qualunque violazione |
| `v4_f3_two_split` | correzioni su entrambi i siti, MaxToggles 2: nessuna violazione | qualunque violazione; incompleto oltre 3 h = riportato come tale |

## 12. Risultati del batch 4 e pre-registrazione del batch 5
| cfg | Previsione | Esito | Stati distinti | Nota |
|---|---|---|---|---|
| `v4_mut_ack` | violazione | **confermata** | 94.381 | la proprietà v4 non è vuota |
| `v4_n6_export_nofix` | nessuna violazione | **FALSIFICATA (reale)** | 83.959 | `OutboxNeverDropsUnapplied` (vedi sotto) |
| `v4_f2_fix_all` | nessuna violazione | **FALSIFICATA (reale, nel progetto della correzione)** | 543.257 | stessa proprietà (vedi sotto) |
| `v4_f3_two_split` | nessuna violazione | **FALSIFICATA (stessa causa)** | 814.195 | |

**Traccia di v4_n6, prototipo (b3q × outbox):**
1. la dispute (seq 1) è messa in outbox mentre s1 è Absent;
2. la reconcile la applica come no-op;
3. un QueryWrite in sospeso crea un MonitorOnly con last_applied 0;
4. l'ack cancella la riga della dispute.

Il record non ha ricevuto l'evento. L'anti-entropia lo recupera nello stesso giro di reconcile
(RepairStart legge last_applied dopo l'ack) o in quello successivo, ma la proprietà D12 del modello
pubblicato non vale per il prototipo.

**Traccia di v4_f2, correzione v4:**
1. s1 è irraggiungibile; l'outbox contiene la revoke (seq 2);
2. la reconcile la applica come no-op su Absent;
3. QueryReserve crea Staging nel mezzo del giro;
4. arriva in ritardo la consegna diretta della dispute (seq 1): Staging → Disputed, last_applied 1;
5. l'ack cancella la revoke.

L'argomento della sez. 11 non copriva una consegna *diversa* arrivata dopo la riserva: era incompleto.

**Batch 5 (v5 = v4 + `QueryReserve` solo con il giro di reconcile del sito fermo).** Nel codice
questo significa prendere `_reconcile_lock` attorno alla transazione di riserva. Così una riserva
non può cadere fra un'applicazione no-op e il suo ack. La patch su copia è aggiornata allo stesso
modo (H-F5, pre-registrata nel docstring prima di rieseguire).

| cfg | Ipotesi | Falsificata se |
|---|---|---|
| `v4_n7_export_nofix` (modello v4) | semantica del PROTOTIPO senza le due proprietà già violate (NoStaleActiveAfterEpisode, OutboxNeverDropsUnapplied): ExportSafeAtReachableSites e le altre proprietà d'azione originali reggono | qualunque violazione |
| `v5_witness_mo` | la query divisa raggiunge ancora MonitorOnly | nessuna violazione |
| `v5_f2_fix_all` | correzioni con riserva serializzata: nessuna violazione di nessuna proprietà | qualunque violazione |
| `v5_f3_two_split` | idem su entrambi i siti, MaxToggles 2 | qualunque violazione; incompleto oltre 3 h = riportato come tale |

## 13. Risultati del batch 5
| cfg | Previsione | Esito | Stati distinti | Nota |
|---|---|---|---|---|
| `v4_n7_export_nofix` | nessuna violazione | **confermata** | **55.063.707**, profondità 38, 12 min 56 s | semantica del PROTOTIPO: export sicuro ai siti raggiungibili, I1, I2, I3_ConservativeRestore, I3_VetoPreserved, isolamento, monotonia, nessuna regressione |
| `v5_witness_mo` | violazione | **confermata** | 324 | la riserva serializzata non blocca la query |
| `v5_f2_fix_all` | nessuna violazione | (in corso) | | |
| `v5_f3_two_split` | nessuna violazione | (in coda) | | |

Patch su copia con la riserva sotto `_reconcile_lock` (H-F5): `test_distributed_fsm_fix_copy.py` +
`test_distributed_fsm_stale_commit.py`, **13 passed, 1 xfailed** (l'xfail è H-S1 sul prototipo);
**H-F5 confermata**.

Regressione della copia v5 (riserva sotto lock) su tutti i test distribuiti più `test_distributed_fsm_stale_commit.py`:
**127 passed, 15 failed, 1 xfailed in 32,0 s**.
- I 12 fallimenti della sez. 7.1 si ripetono identici: 11 nelle classi dichiarate, b3q-2 fuori classe
  come prima.
- 3 nuovi, tutti in classe:
  - `s1` passa sulla copia (XPASS strict, ii);
  - `s1_observed` caratterizza il vecchio comportamento (riceve 409 invece di 200, i);
  - `s2` riapplica le FIXES a una sorgente già corretta: "anchor not found", iii.

**`v5_f2_fix_all`: CONFERMATA.** Nessuna violazione di nessuna proprietà, invarianti e proprietà
d'azione originali e nuove, `OutboxNeverDropsUnapplied` compresa: **98.945.568** stati distinti,
profondità 43, 25 min 21 s.

### 13.1 Batch 5b — pre-registrazione: necessità di ogni parte sulla v5
I mutanti m2-m4 erano stati eseguiti sulla v2. La guardia aggiunta in v5 restringe i comportamenti,
quindi la necessità di ogni parte va rivista sulla v5. La necessità del lock è già mostrata da
v4_f2 (stesso modello senza la guardia).

| cfg | Ipotesi | Falsificata se |
|---|---|---|
| `v5_m2_nolrguard` | senza guardia in LRWrite: NoMonitorOnlyCaughtUpDuringEpisode violato | nessuna violazione |
| `v5_m3_noverify` | senza seconda lettura: I1_CommitOnUndisputedEvidence violato | nessuna violazione |
| `v5_m4_noqueryfix` | senza riserva: DisputeSuspendsAtReachableSitesV2 violato | nessuna violazione |

Esito 13.1 (heap 4 GB, 4 worker, in parallelo con v5_f3): **tutte e tre confermate**.
- `v5_m2_nolrguard`: violato a 144.842 stati;
- `v5_m3_noverify`: violato a 9.668 stati;
- `v5_m4_noqueryfix`: violato a 3.108 stati.

Con v4_f2 (senza lock: OutboxNeverDropsUnapplied violata a 543.257 stati), **ognuna delle quattro
parti della correzione è necessaria** nella configurazione verificata.

### 13.2 Batch 5c — pre-registrazione
`v5_f4_e3`: correzione su s1, **MaxEvents 3** (una seconda dispute dopo un restore è raggiungibile),
MaxToggles 2. Ipotesi: nessuna violazione di nessuna proprietà. Falsificata da qualunque violazione.
Se lo fermano il limite di 3 h o il watchdog del disco: incompleto, nessuna affermazione. Parte
dopo `v5_f3_two_split`, un TLC alla volta.
