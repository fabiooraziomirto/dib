# Audit 93 — Pre-registrazione: correzione v6 con consegne perse (MaxLoss 1)

Data: 2026-10-12. Branch `tnsm-fsm`. Scritto e committato **prima** di ogni esecuzione.

**Numero:** 93 è il primo libero. Verificato con `git ls-tree -r --name-only <branch> docs/audit` su tutti
i branch e nelle worktree `/root/Desktop/DIB*`: esistono solo 90, 91, 92, 94, 95.

**Codice di riferimento:** la correzione v6, che coincide alla lettera con `dc3dd20` (`service.py` sha256
`5599f53b…`, audit 90 sez. 2).

**Modelli:**
- `experiments_tnsm/tla_fsm/v6loss/DIB_AE_NA.tla`, identico a `v6/` (`cmp` senza differenze, eseguito);
- `experiments_tnsm/tla_fsm/v6loss_m/DIB_AE_NA.tla`, identico a `v6m/`: v6 più il flag `MutNoLock`, per
  i mutanti.

Nessuna azione nuova, nessuna semantica cambiata.

## 1. Che cosa è una "consegna persa" nel modello, e come si recupera (letto)
- **Perdita.** L'azione `Lose(r)` (`v6/DIB_AE_NA.tla:319-327`) toglie una consegna in volo da `todo`
  **senza** metterla nell'outbox. L'evento è **scartato**: lo stato dell'evidence è già committato,
  il sito non ne sa nulla. È la finestra D19 dell'audit 06: eccezione fra il commit e il fan-out,
  errore non HTTP, INSERT dell'outbox fallito. Al più `MaxLoss` perdite per comportamento (:320).
- **Recupero:**
  - **anti-entropia nel reconcile del sito:** `ReconcileRead` (:555) legge l'outbox e `current`
    (`CurOf`, :547, presente solo con `AntiEntropy = TRUE`); `RepairStart`/`AntiEntropyStep`/
    `RepairFinish` (:606-631) applicano lo stato corrente dell'evidence a ogni fatto il cui seq è più
    nuovo di `last_applied`. **È l'unico meccanismo che recupera un evento perso.**
  - **outbox (`pending_fanout`):** recupera solo le consegne **fallite** verso un sito
    irraggiungibile (`Deliver`, ramo `unreachable`), non quelle perse;
  - nel modello il reconcile non ha un periodo T: è un passo non deterministico, sempre abilitato,
    e con `SpecL` è giusto (`Fairness`, :658-660).
- **Conseguenza dichiarata dal modello stesso.** Il commento ereditato dal modello pubblicato
  (:672-674) dice che `DisputeSuspendsAtReachableSites` vale **solo con MaxLoss = 0**: con un evento
  perso la finestra dura fino alla riparazione successiva, e la sua chiusura è la proprietà di
  vivacità `ExposureEnds` (:845). `ExportSafeAtReachableSites` (:801) ne è la metà sull'export, quindi
  **con MaxLoss 1 è prevista violata per costruzione**: un sito Active riceve una dispute che si perde,
  e resta Active senza nulla in volo finché non si ripara. Lo stesso vale per V2/V3.
- Il modello pubblicato faceva la stessa scelta:
  - `formal/distributed_ae/v2b_loss_safe.cfg`: "safety (without DisputeSuspends/LagCovered)";
  - `v2b_window.cfg`: la violazione della finestra è *attesa*;
  - `v2b_loss_live.cfg`: il recupero come vivacità.
- **Per questo H-L1 non include ExportSafe e V2/V3**: verrebbero falsificate dalla finestra D19 e
  non dalla correzione. La finestra è controllata a parte (H-L1b) e il recupero è verificato come
  vivacità (H-L3). **Questa è una differenza dalla tua formulazione di H-L1: ti chiedo conferma prima
  di lanciare.**

## 2. Configurazioni
Comuni a tutte:
- **2 siti** (`s1`, `s2`), **1 fatto**, `SplitSites = {s1}`;
- correzione accesa (`FixRace`, `FixQuery`, mutazioni spente);
- quorum 1, MaxRounds 2, `AntiEntropy = TRUE`, `PartitionableSites = {s1}`;
- per la safety `VIEW View` (riduzione validata in audit 92: `e3a`, `e3m`).

La vivacità è **senza VIEW**, perché la VIEW non vale per la vivacità (:647-650).

**Insieme di safety S** (H-L1a):
- invarianti: `TypeOK`, `CaughtUpIsCoherent`, `NoStaleActiveAfterEpisode`,
  `NoMonitorOnlyCaughtUpDuringEpisode`, `CommittingIsTransient`, `StagingIsTransient`;
- proprietà: `I1_NonEscalation`, `I2_SiteConfinement`, `I2_ApplyConfinement`,
  `I3_ConservativeRestore`, `I3_VetoPreserved`, `UnrelatedFactIsolation`, `LastAppliedMonotone`,
  `NoRegression`, `OutboxNeverDropsUnapplied`, `I1_CommitOnUndisputedEvidence`,
  `RevokeConfirmedByOutsider`.

| cfg (cartella) | MaxEvents | MaxLoss | MaxToggles | Spec | Proprietà |
|---|---|---|---|---|---|
| `L1a_e2_np` (v6loss) | 2 | 1 | 0 | Spec + VIEW | S |
| `L1a_e3_np` (v6loss) | 3 | 1 | 0 | Spec + VIEW | S |
| `L1a_e2_p` (v6loss) | 2 | 1 | 2 | Spec + VIEW | S |
| `L1b_window_v6` (v6loss) | 2 | 1 | 0 | Spec + VIEW | `ExportSafeAtReachableSites` |
| `L1b_window_atomic` (v6loss) | 2 | 1 | 0 | Spec + VIEW, **senza correzione, operazioni atomiche** | `ExportSafeAtReachableSites` |
| `L3_live_e1` (v6loss) | 1 | 1 | 0 | SpecL | `ConvergedEventually`, `ExposureEnds` |
| `L3_live_e2` (v6loss) | 2 | 1 | 0 | SpecL | idem |
| `L2_noae_live_e1` (v6loss) | 1 | 1 | 0 | SpecL, `AntiEntropy = FALSE` | `ConvergedEventually` |
| `L2_m2_nolrguard` (v6loss_m) | 2 | 1 | 0 | Spec + VIEW | `NoMonitorOnlyCaughtUpDuringEpisode` |
| `L2_m3_noverify` (v6loss_m) | 2 | 1 | 0 | Spec + VIEW | `I1_CommitOnUndisputedEvidence` |
| `L2_m6_nolock` (v6loss_m) | 2 | 1 | 3 (serve l'outbox) | Spec + VIEW | `OutboxNeverDropsUnapplied` |

## 3. Ipotesi H-L1
- **H-L1a.** Con MaxLoss 1 nessuna violazione dell'insieme S, in `L1a_e2_np`, `L1a_e3_np` e
  `L1a_e2_p`. Falsificata da un qualunque controesempio.
- **H-L1b (finestra D19, violazione attesa).**
  - In `L1b_window_v6` `ExportSafeAtReachableSites` è violata e la traccia contiene un passo `Lose`.
  - In `L1b_window_atomic` è violata anche nel protocollo atomico **senza** correzione: la finestra
    dipende dalla perdita, non dalla correzione.
  - Falsificata se una delle due non dà violazione, o se la traccia di v6 non contiene `Lose`.
- **H-L3 (recupero, vivacità).** In `L3_live_e1` valgono `ConvergedEventually` e `ExposureEnds`.
  Falsificata da un qualunque controesempio. `L3_live_e2` si fa per quanto possibile: incompleta =
  nessuna affermazione.

## 4. Ipotesi H-L2 (non vacuità)
Con MaxLoss 1 i comportamenti includono quelli con MaxLoss 0 (`Lose` è facoltativa). Quindi ogni
controesempio già trovato **esiste ancora**, se la sua proprietà è nell'insieme controllato.
- **Separabili con le perdite**, devono essere ancora trovati:
  - `L2_m2_nolrguard` (guardia di LR);
  - `L2_m3_noverify` (seconda lettura);
  - `L2_m6_nolock` (lock).

  Falsificata se uno non viene trovato.
- **NON separabili con le perdite (lo dico prima):**
  - **m4** (senza riserva della query) e **m5** (senza applicazione della lettura alla chiusura) si
    rivelano solo con `DisputeSuspendsAtReachableSitesV2/V3`, la proprietà della finestra, che con
    MaxLoss 1 è violata anche **senza** mutante;
  - con le perdite non esiste quindi un controllo che li distingua dalla finestra D19;
  - la loro non vacuità resta quella senza perdite: `v6m/logs/v6m_m4_noqueryfix.log:25`,
    `v6/logs/v6_m5_nofinishapply.log:26`, `v6e3/logs/e3m_nofinishapply_noparts.log`;
  - definire una proprietà nuova ("finestra al netto delle perdite") sarebbe un cambio di semantica:
    non lo faccio senza il tuo assenso.
- **Mutante "senza riconciliazione"** `L2_noae_live_e1` (`AntiEntropy = FALSE`): un evento perso non
  si recupera più, quindi `ConvergedEventually` è violata. Falsificata se nessuna violazione.
  - Nota: senza anti-entropia la safety S **non** cambia; la differenza è solo di vivacità.

## 5. Risorse e tempo
- Come in audit 67/92:
  - `run_tlc.sh` con `-Xmx28g` su 64 GB (nessuno swap) e 8 worker;
  - metadir nello scratchpad, cancellata a fine run;
  - watchdog che uccide TLC sotto 8 GB liberi su `/`;
  - un TLC alla volta.
- Prima del lancio: 34 GB liberi, ~54 GB di RAM libera.
- La vivacità di TLC salva il grafo dei comportamenti su disco: è il run più a rischio per il disco.
  Il watchdog resta.
- **Tetto di tempo proposto:**
  - 30 min ciascuno: `L1b_*`, `L2_m2`, `L2_m3`, `L2_noae_live_e1`;
  - 1 h: `L3_live_e1`;
  - 3 h ciascuno: `L1a_e2_np`, `L1a_e3_np`, `L1a_e2_p`, `L3_live_e2`, `L2_m6_nolock`.
- Superato il tetto: incompleto, nessuna affermazione. **Ti chiedo se vuoi togliere il tetto per
  qualche run**, come per e3c in audit 92.
- **Ordine:** L1b (2), L2 rapidi (m2, m3, noae), L3_live_e1, L1a_e2_np, L1a_e3_np, L2_m6, L1a_e2_p,
  L3_live_e2.
- Se H-L1a cade si ferma tutto e si riporta la traccia minima.

## 6. Cosa va nel paper per ciascun esito
- **H-L1a confermata (e H-L3 su e1):** una frase sui limiti del modello. "With at most one lost
  delivery, the corrected design keeps every safety property except the exposure window that a lost
  dispute opens until the next repair; recovery is checked as a liveness property for a single
  event."
  - La finestra D19 è già un limite dichiarato: G3 "upon reconciliation", AS6.
- **Controesempio di H-L1a:** ci si ferma e si riporta la traccia in chiaro. `service.py` dovrebbe
  cambiare: nuova decisione dell'utente, e i blocchi sul nodo vanno rifatti. Nessuna correzione di
  codice proposta senza dirlo.
- **Incompleto:** il paper dice "verified without lost deliveries; with one lost delivery the check
  is incomplete".
- **H-L1b falsificata** (nessuna finestra): andrebbe capito perché, prima di scrivere qualunque cosa
  sulla finestra.
- **H-L2 falsificata** (un mutante separabile non trovato): il controllo con le perdite è vacuo per
  quella parte, e lo si dice.

## 7. Decisioni dell'utente (prima di ogni run, 2026-10-12T10:46:43Z)
- **H-L1 come pre-registrato:** H-L1a senza ExportSafe/V2/V3; H-L1b come violazione attesa con
  controllo atomico; H-L3 vivacità; m4 e m5 dichiarati non separabili.
- **Nessun tetto di tempo per nessun run.** Restano il watchdog del disco (< 8 GB liberi → TLC
  fermato, esito "incompleto") e l'heap limitato a 28 GB. La sez. 5 è superata per la parte sui tetti.
- **Regola di arresto:** se `L1a_*` o `L3_*` trovano un controesempio, la sequenza si ferma e si
  riporta la traccia minima. Gli altri run (`L1b_*`, `L2_*`) prevedono una violazione: la sequenza
  prosegue.
  (Il testo di questa riga è stato ripristinato dopo il commit `25b19b7`: un heredoc senza virgolette
  aveva cancellato i nomi fra backtick. Il contenuto è quello deciso prima del lancio.)

## 8. Risultati (eseguiti, 2026-10-12 ~10:47-10:48Z) e arresto
| cfg | Previsione | Esito | Stati | Traccia / log |
|---|---|---|---|---|
| `L1b_window_v6` | violazione di ExportSafe con un `Lose` | **confermata** | 2.369 | Query(s2), Commit(s2), EvDispute, **Lose** (consegna a s2): s2 Active con evidence Disputed e nulla in volo. Il sito s2 non è diviso: la finestra non dipende dalla correzione. `v6loss/logs/L1b_window_v6.log` |
| `L1b_window_atomic` | violazione anche senza correzione | **confermata** | 1.474 | stessa traccia (Query, Commit, EvDispute, Lose). `v6loss/logs/L1b_window_atomic.log` |
| `L2_m2_nolrguard` | violazione | **confermata** | 45.297 | `v6loss_m/logs/L2_m2_nolrguard.log` |
| `L2_m3_noverify` | violazione | **confermata** | 8.770 | `v6loss_m/logs/L2_m3_noverify.log` |
| `L2_noae_live_e1` | `ConvergedEventually` violata da un evento perso mai recuperato | violata, **ma non per la ragione prevista** | 46.974 | la traccia **non contiene `Lose`** (`lossCount = 0`): ciclo QueryReserve → QueryRead → QueryFinish (abort, perché l'evidence è Disputed) → Absent, ripetuto all'infinito; negli stati `Staging` vale `last_applied 0 ≠ eseq 1` |
| `L3_live_e1` | `ConvergedEventually` e `ExposureEnds` valgono | **FALSIFICATA come scritta** | 27.017 | stesso tipo di ciclo: dopo un `Lose` (s1 ancora senza riga) le riparazioni avvengono mentre s1 è Absent; poi s1 riserva e abortisce all'infinito (ritorno allo stato 8). `v6loss/logs/L3_live_e1.log` |
| `L1a_e2_np` | nessuna violazione | **interrotto** a 163.318 stati, nessuna violazione fino lì: **nessuna affermazione** | — | |

**Errore mio nel lanciatore.** La regola di arresto cercava "Temporal properties were violated",
mentre TLC scrive "Temporal property … was violated". La sequenza non si è fermata dopo
`L3_live_e1`: ha avviato `L1a_e2_np` e l'ho fermata a mano subito dopo (TaskStop, nessun processo
residuo, metadir rimossa). Gli altri run (L1a_e3_np, L2_m6, L1a_e2_p, L3_live_e2) non sono partiti.

**Lettura (mia, da confermare con l'utente).**
- Il controesempio di vivacità è un **artefatto della formulazione**: nessun evento perso resta
  senza recupero.
- `Converged` (`v6/DIB_AE_NA.tla:836-838`) chiede, per ogni riga non Absent, `last_applied = eseq`.
  Le operazioni dell'operatore non hanno vincoli di equità né di numero: un operatore che rilancia
  `/query` all'infinito mentre il fatto è disputato crea infinite volte una riga `Staging` con
  `last_applied 0`, quindi `[]Converged` non vale mai. Questo accade anche **senza** perdite
  (`L2_noae_live_e1`) e quindi anche con l'anti-entropia.
- Il modello pubblicato non aveva questo problema, perché la sua `Query` era atomica: niente stato
  intermedio.
- Correggere la formulazione (ad esempio escludere da `Converged` le righe `Staging`/`Committing`
  con un'operazione pendente, oppure limitare il numero di query) è un **cambio di semantica**: non
  lo faccio senza l'assenso dell'utente.
- Le parti di safety con le perdite (H-L1a) **non sono state verificate**: i run non sono partiti o
  sono stati interrotti.

## 9. Pre-registrazione aggiuntiva (scritta dopo i risultati della sez. 8, prima di ogni nuovo run)
**Decisione dell'utente (2026-10-12):** procedere con entrambe:
1. rilanciare la safety con perdite (H-L1a);
2. riformulare la vivacità sulle sole righe che rappresentano una decisione.

**Modello v7** (`experiments_tnsm/tla_fsm/v7live/DIB_AE_NA.tla`) = v6 più 14 righe di sole definizioni
(`diff` contro v6: 14 righe aggiunte, 0 tolte; SANY senza errori; eseguito):
- `DecisionRow(t, f)`: stato non in {Absent, Staging, Committing};
- `ConvergedDecisions`: per ogni sito raggiungibile e fatto, o non è una riga di decisione, o
  `last_applied = eseq`;
- `ConvergedDecisionsEventually == <>[] ConvergedDecisions`.

`ExposureEnds` resta invariata. **È un cambio di formulazione della proprietà, deciso dopo aver visto
il controesempio, e lo dichiaro come tale.** Motivo:
- `Staging` e `Committing` sono transitori per invariante e non vengono mai esportati;
- la proprietà vecchia falliva per un operatore che rilancia la query all'infinito, senza alcun
  evento perso (sez. 8).

**Limite della nuova proprietà:** non dice nulla su una query o un commit che restano pendenti per
sempre. Nel modello le operazioni dell'operatore non hanno equità: è un'assunzione sull'operatore,
non sul protocollo.

| cfg (cartella `v7live/`) | Ipotesi | Falsificata se |
|---|---|---|
| `Lv_e1` (SpecL, MaxEvents 1, MaxLoss 1, MaxToggles 0) | `ConvergedDecisionsEventually` ed `ExposureEnds` valgono | qualunque violazione |
| `Lv_noae_e1` (idem, `AntiEntropy = FALSE`) | `ConvergedDecisionsEventually` violata **e** la traccia contiene `Lose` | nessuna violazione, o traccia senza `Lose` |
| `Lv_e2` (MaxEvents 2) | come `Lv_e1` | qualunque violazione; fermato dal watchdog = incompleto, nessuna affermazione |

## 10. Rilancio di H-L1a e della non vacuità di m6
Si rilanciano le cfg della sez. 2, invariate: `L1a_e2_np`, `L1a_e3_np`, `L2_m6_nolock`, `L1a_e2_p`.
Il log del run interrotto di `L1a_e2_np` resta committato com'è (`177358f`). Il nuovo run lo
sovrascrive nella worktree: la copia vecchia è nella storia git.

Correzioni al lanciatore:
- la regola di arresto cerca "violated", che copre sia "is violated" sia "was violated";
- **nessun tetto di tempo** (decisione dell'utente, sez. 7);
- restano il watchdog del disco e l'heap a 28 GB.

**Ordine:** `Lv_e1`, `Lv_noae_e1`, `L1a_e2_np`, `L1a_e3_np`, `L2_m6_nolock`, `L1a_e2_p`, `Lv_e2`.

**Arresto:** se `Lv_e1`, `Lv_e2` o un `L1a_*` trovano una violazione, ci si ferma e si riporta la
traccia minima.

## 11. Risultati della sez. 9-10 (eseguiti, 2026-10-12 10:54-11:52Z)
| cfg | Previsione | Esito | Stati distinti | Profondità | Durata | Log:riga |
|---|---|---|---|---|---|---|
| `Lv_e1` (v7, SpecL, 1 evento, MaxLoss 1) | `ConvergedDecisionsEventually` ed `ExposureEnds` valgono | **confermata** | 247.317 | 25 | 42 s | `v7live/logs/Lv_e1.log:32,37` |
| `Lv_noae_e1` (`AntiEntropy = FALSE`) | violata, con `Lose` nella traccia | **confermata** | (violazione) | 14 | 3 s | `v7live/logs/Lv_noae_e1.log:27` |
| `L1a_e2_np` (2 eventi, MaxLoss 1, senza partizioni) | nessuna violazione dell'insieme S | **confermata** | 4.831.051 | 39 | 1 min 37 s | `v6loss/logs/L1a_e2_np.log:27,32` |
| `L1a_e3_np` (3 eventi, MaxLoss 1, senza partizioni) | idem | **confermata** | 119.425.107 | 44 | 44 min | `v6loss/logs/L1a_e3_np.log:71,76` |
| `L2_m6_nolock` (MaxLoss 1, MaxToggles 3) | `OutboxNeverDropsUnapplied` violata | **confermata** | 496.278 al momento della violazione | 12 | 5 s | `v6loss_m/logs/L2_m6_nolock.log:26` |
| `L1a_e2_p` (2 eventi, MaxLoss 1, MaxToggles 2) | nessuna violazione dell'insieme S | **confermata** | 32.885.070 | 42 | 9 min 58 s | `v6loss/logs/L1a_e2_p.log:35,40` |
| `Lv_e2` (v7, 2 eventi) | come `Lv_e1` | (in corso) | | | | |

**Traccia di `Lv_noae_e1`** (verificata a mano):
1. Query(s2), EvDispute;
2. Deliver a s1, che è Absent: no-op;
3. **Lose** della consegna a s2;
4. LocalRevoke(s2): Revoked/Local con last_applied 0;
5. ciclo di reconcile senza riparazione: la riga di s2 resta a last_applied 0 contro eseq 1 per
   sempre.

Il mutante è rivelato **per la ragione giusta**, a differenza della formulazione vecchia della
sez. 8.

**H-L1a: CONFERMATA** in tutte e tre le configurazioni pre-registrate (2 eventi senza e con
partizioni, 3 eventi senza partizioni). **H-L2:** i mutanti separabili m2, m3 e m6 sono ancora
trovati con MaxLoss 1; m4 e m5 non sono separabili (sez. 4). **H-L3 (v7, 1 evento): confermata**;
`Lv_e2` in corso.

Risorse: picco di RAM di sistema ~22 GB su 64 nei controlli; disco libero ≥ 33 GB; nessun intervento
del watchdog; nessun OOM.
