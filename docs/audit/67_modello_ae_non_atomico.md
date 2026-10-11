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
| `q2_outsider_rule` | nessuna violazione | (in corso) | | |

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
