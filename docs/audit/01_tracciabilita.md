# Audit 01 — Tracciabilità modello ↔ codice ↔ test (piano §7.1)

Data audit: 2026-10-10. Solo lettura: nessun file della repo è stato modificato (unico file creato: questo).

## 0. Convenzioni e perimetro

**Cosa ho auditato.**
- Codice e modelli: `dib-tnsm-artifact-v43/` (nel seguito `V/`). È l'ultimo snapshot; v31 e v36 sono snapshot precedenti, non letti.
- Paper: `docs/main.tex`. È la copia di lavoro con le tue annotazioni `\del/\add` e i commenti `%`. Le tabelle `tab:transitions` e `tab:tla` sono **identiche** a quelle di `V/paper/main.tex` (confrontate programmaticamente).
- Numerazione: nel PDF compilato di v43 (`V/paper/main.aux:39,55,68`) la tabella delle transizioni è **Table III** (`tab:transitions`). La **Table II** è `tab:record-example` (esempio della telecamera). Qui "Table II" = `tab:transitions` (`docs/main.tex:303-324`), perché è l'unica con transizioni e guardie. Le mutazioni M1–M6 sono `tab:tla` = Table V (`docs/main.tex:453-467`).
- `CLAUDE.md` cita `docs/paper_attuale.tex`, che **non esiste**; ho usato `docs/main.tex`.

**Abbreviazioni** (tutti i percorsi sono sotto `V/` salvo diversa indicazione):

| Sigla | File |
|---|---|
| `SVC` | `code/src/dib/registry/services.py` (registry centralizzato) |
| `DB` | `code/src/dib/registry/db.py` |
| `API` | `code/src/dib/registry/api.py` |
| `DIST` | `code/src/dib/registry/distributed/service.py` (prototipo distribuito) |
| `EXP` | `code/src/dib/evaluation/mud_export.py` |
| `TLA` | `formal/base/DIB.tla` |
| `TLAD` | `formal/distributed/DIB_Distributed.tla` |
| `T` | `code/tests/tests/test_registry.py` |
| `OSM` | sorgente osMUD al commit 852918e, letto in un layer Docker locale: `/var/lib/docker/overlay2/aefb57fb88c585eaaf9cfefbc8ff75899caa2d02acd54e349a2ebd016ffd62de/diff/src/osmud/src/` (`.git/HEAD` = `852918eb…`, lo stesso pin di `openwrt/Dockerfile.router:2`) |

**Cosa ho eseguito** (tutto senza scrivere nella repo):
- `pytest` sull'intera suite: **281 passed in 5,74 s** (Python 3.10.13, pytest 9.0.2). Con `-p no:cacheprovider` e `PYTHONDONTWRITEBYTECODE=1`; `git status` di `V/` identico a prima.
- Le 6 mutazioni TLC (`scripts/run_formal.py --mutations-only`), output nello scratchpad. Tutte e 6 hanno dato la violazione attesa. Ho usato un `tla2tools.jar` trovato in un altro progetto (`/root/Desktop/BioDevOps/formal_methods/`); la repo non ne contiene uno.
- Due `docker run --network none` sull'immagine `18_openwrt_enforcement-router` (cerca `openssl`, stampa `osmud -h`).

**Cosa NON ho eseguito:** modelli TLC completi (130 M stati, diversi minuti), `verify_artifact.py`, campagna OpenWrt, cluster Docker distribuito, regressione numeri vs `claims.json` (§7.1 punto 1, fuori dalla richiesta). Non ho verificato che il codice nel layer Docker sia byte-identico alla build usata per `results/openwrt/`; so solo che il commit è lo stesso.

---

## 1. Struttura della repo e come si eseguono test ed esperimenti

### 1.1 Struttura

`/root/Desktop/DIB_reframe` **non è un repo git**. Contiene:
- tre snapshot dell'artifact (`dib-tnsm-artifact-v31`, `-v36`, `-v43`), ciascuno con un proprio `.git`;
- molte versioni del paper (`main*.tex`, `ready/`, `reproducibility/main_v*.tex`);
- `scripts/` e `results/` a livello radice, relativi agli esperimenti RWV/TNSM-extra. Non li ho auditati: non riguardano il lifecycle;
- `docs/DIB_piano_completo.md` e `docs/main.tex`.

`V/` ha git con 3 commit (HEAD `ca9c6a0`, "first commit"). Ha modifiche non committate: `paper/main.tex`, `paper/main.pdf`, `docs/PAPER_SOURCE_v43.md`, `slides/`. Il "commit di riferimento" del piano §7.1.1 non è ancora etichettato.

```
V/
  paper/            main.tex (= "main (43).tex" non modificato, vedi docs/PAPER_SOURCE_v43.md)
  claims.json       claim → file di evidenza → generatore (paper_version "v42.0")
  formal/base/      DIB.tla + DIB.cfg (lifecycle completo) + DIBEvidenceOnly.cfg (Σ_ev, senza commit)
  formal/distributed/  DIB_Distributed.tla (+SiteDown/SiteUp/Reconcile)
  formal/mutations/m1..m6/  DIB.tla mutato + DIB.cfg + result.log (run 2026-09-05 23:37)
  formal/logs/      log completi + mutation_*.log storici (run 15:28, modello precedente)
  code/src/dib/     registry/ (services, api, db, distributed/), evaluation/ (scorer, mud_export), experiments/, adapters/
  code/tests/tests/ 40 file test_*.py (cartella annidata tests/tests)
  code/scripts/     ~70 script di esperimento; osmud_probe/dib_mud_probe.c
  openwrt/          harness Docker OpenWrt 23.05.5 + osMUD 852918e
  results/          evidenza compatta per claim
  scripts/          run_formal.py, verify_artifact.py
```

### 1.2 Come si eseguono (ricostruito; la sezione "Come si esegue" di `CLAUDE.md` è vuota)

| Cosa | Comando | Note |
|---|---|---|
| Test unitari | `cd V/code && python3 -m pytest tests -q` | `code/conftest.py:1-4` aggiunge `src/` al path. `pyproject.toml:9` dichiara `requires-python >=3.12`, ma l'ambiente ha Python 3.10 e la suite passa lo stesso. |
| Verifica numeri indicizzati | `python3 scripts/verify_artifact.py [--with-tests]` | Legge `results/` e `formal/`, secondi. Non rilancia TLC né i gateway (README). |
| TLC | `python3 scripts/run_formal.py --jar <tla2tools.jar> --output <dir>`; `--mutations-only` per le 6 mutazioni | Richiede Java. `formal/base/run_tlc.sh` è solo un wrapper (richiede `TLA_TOOLS`). `run_formal.py:21-26` fissa la proprietà attesa per ogni mutazione. |
| Esperimenti registry senza dati terzi | `PYTHONPATH=code/src python3 code/scripts/{v36_restore_ablation,v35_lifecycle_experiment,v28_lifecycle_trace,offline_veto_reconciliation --trials 10}.py` | Comandi dal README. |
| Esperimenti su dataset | `code/scripts/*.py`, mappati in `claims.json` (campo `generator`) | UNSW / Mon(IoT)r / YourThings vanno procurati a parte (`docs/data_provenance.md`). |
| Cluster distribuito (10 siti + evidence) | `docker compose` in `code/src/dib/registry/distributed/`; poi `fault_injection_experiment.py`, `reconcile_race_experiment.py` | Porte `localhost:18100` (evidence) e `18110+i` (siti), da `reconcile_race_experiment.py:28,33-34`. |
| Gateway OpenWrt+osMUD | `cd openwrt && python3 run_campaign.py --runs 10` (o `./run.sh`, `./run_distributed.sh`) | Docker privilegiato, ≥8 GiB RAM, senza retry (README). **Comando lungo: da chiedere prima.** |

Il piano §7.2 chiede ≥10 ripetizioni e un harness unico. Oggi gli script non hanno un entry point comune.

---

## 2. Mappa di tracciabilità

Legenda esito: ✅ coperto da test pytest · 🟡 coperto solo in parte, o solo da esperimento Docker/script · ❌ buco.

### 2.1 Transizioni di Table II (`tab:transitions`, `docs/main.tex:303-324`)

| # | Transizione (paper) | Azione TLA+ | Codice centralizzato | Codice distribuito | Test | Esito |
|---|---|---|---|---|---|---|
| R1 | Absent —query/stage→ MonitorOnly; precond. *admitted, no open dispute*; grant no | `Query` `TLA:88-94` (`state=Absent ∧ admissible ∧ ¬OpenDispute`) | `SVC:427-451`. Guard admitted+status Active a `:439`; crea la riga a `:445` | `DIST:172-191` (guard a `:175`) | `T:593` (stage), `T:607` (non ammesso) | 🟡 Il guard "no open dispute" (`SVC:439`, `status != ACTIVE`) non ha un test sul registry: nessun test chiama `query_score` dopo `dispute_score` (scansione di tutti i test). Esiste solo `test_admit_auto.py:19`, a livello di scorer. Il distribuito non ha pytest. |
| R2 | MonitorOnly —local commit→ Active; precond. *local operator, no dispute*; grant **yes, new**; exportable yes | `OperatorCommit` `TLA:100-107` (imposta `grantValid`, azzera `revokeReason`) | `SVC:454-487`. Guard stato `:476`, guard evidenza `:471`. `flagged_for_review=False` a `:482` | `DIST:193-206` | `T:740`, `T:772` (re-commit su Active → eccezione), `T:475` (restore+commit), `T:302` | 🟡 (a) Nessun test di commit da Disputed/Revoked. (b) Il codice richiede anche `score.accepted` (`SVC:471`), mentre TLA e paper no: vedi D4. (c) Nel codice non esiste `grantValid` (D2): "yes, new" non è verificabile. (d) "local operator": `site_id` è un parametro fidato (`API:200-215`), nessun controllo di ruolo. |
| R3 | MonitorOnly/Active —first dispute→ Disputed; precond. *valid dispute*; grant no | `Dispute` `TLA:122-139` con `votes=1` | `dispute_score` `SVC:615-667`, ramo `:648-656`. Fan-out `_transition_all_decisions` `:719-761`, `from_states={MonitorOnly,Active,Disputed}` | `DIST:438-449` → `_fan_out` `:356-382` → `_apply_fanout_row` `:147-170` | `T:146`, `T:159` (Active e MonitorOnly → Disputed) | 🟡 Centralizzato ✅. "Valid dispute" non è verificata: qualunque stringa `site_id` basta, anche di un sito senza record (`API:184-197`, `DIST:431-432`). Il distribuito è coperto solo da script Docker. |
| R4 | Disputed —second dispute→ Revoked(Dispute); precond. *distinct reporting site* | `Dispute` con `votes≥2` `TLA:126` | `SVC:657-664` (`site_id != score.disputed_by`) | `DIST:450-453` | `T:198` (secondo sito → Revoked), `T:185` (stesso sito: nessun voto) | ✅ centralizzato. 🟡 distribuito. Nel distribuito con `DIB_DIST_SUSPENSION_QUORUM=2` (`DIST:69-71,439-443`) bastano comunque due siti distinti per revocare (la prima segnalazione non sospende, ma conta in `suspension_reports`): D8 (corretto il 2026-10-10, vedi `docs/audit/02_test_gap_results.md` §2). |
| R5 | Disputed/Revoked(Dispute) —global restore→ MonitorOnly; precond. *authorized restore*; grant no | `Restore` `TLA:145-159` | `restore_score` `SVC:670-716`. Reset a MonitorOnly `:708-711`, filtro provenienza `:743-757` | `DIST:461-480` + `_apply_fanout_row` `:157-161` | `T:225`, `T:262`, `T:401`, `T:435`, `T:503`, `T:571` (restore su fact Active → eccezione) | ✅ centralizzato. "Authorized" non è implementato né testato (`API:271-287`: `actor_site_id` opzionale). Il distribuito è 🟡. Il codice ripristina anche il punteggio: D5. |
| R6 | Active/MonitorOnly/Disputed/Revoked(Dispute) —local revoke→ Revoked(Local); precond. *local operator*; grant no | `LocalRevoke` `TLA:170-179` | `local_revoke` `SVC:490-535`. Provenienza dedotta dalla storia `:515-523` | `DIST:208-227` (colonna `origin`) | Active `T:302`; MonitorOnly `T:382`; Disputed e Revoked(Dispute) `T:435` (loop `dispute_count` 1 e 2) | ✅ tutte e 4 le sorgenti. Il distribuito è 🟡. |
| R7 | Revoked(Local) —local restore→ MonitorOnly; precond. *no open dispute*; grant no | `LocalRestore` `TLA:181-188` | `local_restore` `SVC:538-580`. Guard dispute `:565-569`, guard stato `:570-574` | `DIST:229-247` | `T:329`, `T:354` (bloccato con dispute aperta), `T:435` | ✅ centralizzato; 🟡 distribuito. Il centralizzato non controlla la provenienza "Local" (TLA `:183` sì, `DIST:239` sì): non è raggiungibile in pratica, vedi D3. |
| R8 | MonitorOnly —retention expiry→ Absent; precond. *sotto soglia per la finestra W, nessuna decisione locale* | **assente** (il paper dice "outside the verified configuration") | **assente**: nessun `retention`/`expiry`/`window` in `code/src/dib/registry` (grep). Il README v43 lo ammette | **assente** | nessuno | ❌ Buco dichiarato. Nessuna azione TLA+, nessun codice, nessun test, nessun claim in `claims.json`. |
| R9 | Revoked(Local) —global restore→ Revoked(Local) (invariato) | `Restore` non include Revoked(Local) in `TLA:148-149`; proprietà `I3_GlobalRestorePreservesLocalRevoke` `TLA:298-304` | `SVC:743-757` (`continue` se la provenienza non è "revoke") | `DIST:157-161` | `T:401`, `T:435` | ✅ centralizzato; 🟡 distribuito (script `offline_veto_reconciliation.py:115`). È l'unica mutazione con back-test sul codice: vedi §2.3. |
| R10 | Absent —dispute→ Absent | `Dispute` `TLA:127-130` (stato non-extant invariato; `disputers` sì → blocca `Query`) | `SVC:648-656`: lo stato globale cambia, nessuna riga locale creata (`_transition_all_decisions` itera solo i record esistenti) | `DIST:150-153`, `_apply_fanout_row` `:151-153` (return se non c'è riga) | `T:503` (due dispute + restore senza decisioni locali: `local_decisions == []`) | ✅ centralizzato |

### 2.2 Guardie e frasi della didascalia / del testo di Table II

| Guardia / affermazione | TLA+ | Codice | Test | Esito |
|---|---|---|---|---|
| Admitted (`A=1 ∧ |S|≥m ∧ score≥θ ∧ ¬openDispute`, eq. `admitauto`) | astratto in `admissible[f]` (`TLA:14-16`) | `admit_auto` `code/src/dib/evaluation/dib.py:22-47`. **`open_dispute` ha default False e nessun chiamante lo passa** (`:33-34`, i chiamanti sono a `dib.py:297` e negli esperimenti). Il blocco reale è `query_score` (`SVC:439`). Parametri registry: `SVC:43-44` (α=.6, β=.4, γ=0, θ=.65, m=2) = paper `tab:symbols` ✅ | `test_admit_auto.py:6-19`, `test_registry_admission_trust.py:55-150` | 🟡 La parte `¬openDispute` dell'ammissione non è collegata al registry (D7). |
| Grant valid? (colonna) | variabile `grantValid` + `AuthorizationStateCoherence` `TLA:220` | **non esiste**: `LocalDecision` (`DB:180-198`) ha solo `state`, `flagged_for_review`, `version`. Si assume `grantValid ⇔ state==Active` | indiretto: `T:225` (restore → MonitorOnly, non Active), `T:475` | ❌ non rappresentato (D2). M1 non ha controparte. |
| Exportable? = Active ∧ grantValid (eq. `exportable`) | `Export` `TLA:109-113`, `ExportRequiresActive` `:209`, `ExportRequiresFreshAuthorization` `:216` | `export_active_mud` `SVC:764-813`: filtra `state==ACTIVE` (`:776`) poi `export_mud_file` scarta IP-literal e protocolli non mappabili (`EXP:94-98`) | `T:807`, `T:463-470`, `test_mud_export.py:40`, `test_rescoring_non_destructive.py:56,116` | 🟡 Nessun test registry di export con record Disputed o Revoked(Dispute): il test `T:463` esporta dopo il restore (M3, vedi §2.3). Un fact Active ma non rappresentabile (IP literal) non produce ACE senza alcun avviso (D9). |
| Provenienza della revoca ("separately stored revocation origin") | `revokeReason` `TLA:35` | centralizzato: **non memorizzata**, dedotta da `LocalDecisionVersion.event` (`SVC:515-523`, `:744-757`). Distribuito: colonna `origin` (`DIST:116`, `:166`, `:218`) | `T:401`, `T:435` | 🟡 Il paper dice "separately stored"; vero solo nel distribuito (D3). |
| "Repeated reports from the same site … add no transition" | `Dispute` `s ∉ disputers` `TLA:123` | `SVC:657` | `T:185` | ✅ |
| "Reports after confirmed revocation add no transition" | `Dispute` su Revoked: stato invariato | `SVC:648-664`: nessun ramo per `status==REVOKED`; ma `_upsert_attestation` viene comunque eseguito (`:644`) | nessun test con un terzo dispute dopo la revoca (i test fermano a 2 voti) | ❌ |
| "Other undefined transitions are rejected or leave the record unchanged" | `Next` (azioni con guard) | commit `SVC:476-480`, local_revoke `:515-528`, local_restore `:565-574`, restore `:689-693` | commit su Active `T:772`; restore su Active `T:571`; local_revoke su Revoked `T:382` | 🟡 Non testati: `local_restore` su stato ≠ Revoked, commit da Disputed/Revoked, `query` su record già esistente in altro stato. |
| Idempotenza e ordine del fan-out (non in Table II, ma sostiene I3) | `Reconcile` `TLAD:227-250` | `DIST:155-156` (scarta `seq ≤ last_seq`); outbox `:372-382` (`ON CONFLICT … WHERE excluded.seq > pending_fanout.seq`) | nessun pytest; script `fault_injection_experiment.py`, `reconcile_race_experiment.py`, `offline_veto_reconciliation.py` (asserzioni `:94-132`) | 🟡 Solo esperimenti Docker, non in `pytest`. |
| I1 (`NoActiveWithoutCommit`, `I1_NonEscalation`) | `TLA:232`, `:242`; cfg `DIBEvidenceOnly.cfg` | `operator_commit` è l'unico punto che scrive `DECISION_ACTIVE` (`SVC:481`; `DIST:203`) | `T:593` (query non dà Active), `T:225`, `test_rescoring_non_destructive.py:162` | ✅ |
| I2 (`I2_SiteConfinement`, `I2_LocalRevokeConfinement`) | `TLA:258`, `:288` | commit e local_revoke toccano solo la riga `(score, site_id)` (`SVC:468`, `:512`) | `T:302` (peer invariato), `T:807`, `T:824` | ✅ |
| I3 (`I3_ConservativeRestore`, `…LocalRestoreConservative`, `…GlobalRestorePreservesLocalRevoke`, `…DisputeClears…`) | `TLA:265-304` | `SVC:708-711`, `:565-569`, `:743-757` | `T:225`, `T:354`, `T:401`, `T:435` | ✅ centralizzato. Per i siti offline vedi D6. |

### 2.3 Mutazioni M1–M6

**Attenzione: la numerazione del paper (`docs/main.tex:459-464`) è una permutazione di quella dei file** (`formal/mutations/m*`, `claims.json:20`, `run_formal.py:21-26`). Ho rieseguito le 6 mutazioni: la proprietà violata coincide con `run_formal.py`.

| Paper | Descrizione paper | Cartella repo | Modifica reale (diff vs `DIB.tla`) | Proprietà violata (TLC rieseguito) | Corrisponde al paper? |
|---|---|---|---|---|---|
| M1 | Grant coherence; restore recreates grant | `m1` | `Restore` aggiunge `grantValid'=TRUE` (`m1/DIB.tla:158`) | `AuthorizationStateCoherence` | ✅ |
| M2 | I2 site confinement; cross-site commit | `m2` | `OperatorCommit` modifica altri siti (`m2/DIB.tla:103`) | `I2_SiteConfinement` | ✅ |
| M3 | I2 local-revoke confinement; local-revoke fans out | **`m5`** | `LocalRevoke` ha effetto su tutti i siti (`m5/DIB.tla:174`) | `I2_LocalRevokeConfinement` | ✅ proprietà; ⚠ cartella diversa |
| M4 | I3 global restore preserves local revoke; restore ignores origin | **`m6`** | `Restore` ripristina ogni `Revoked` (`m6/DIB.tla:149`) | `I3_GlobalRestorePreservesLocalRevoke` | ✅ proprietà; ⚠ cartella diversa |
| M5 | **I3 local-restore conservative**; local-restore ignores open dispute | **`m4`** | `LocalRestore` senza `¬OpenDispute` (riga 184 rimossa) | **`DisputeSuspendsEverywhere`** | ❌ La proprietà in tabella non coincide: `I3_LocalRestoreConservative` resta vera nella mutazione (il record torna comunque a MonitorOnly). La violata è `DisputeSuspendsEverywhere` (`TLA:225`). |
| M6 | Export requires Active; disputed export | **`m3`** | `Export` ammette `Disputed` (`m3/DIB.tla:110`) | `ExportRequiresActive` | ✅ proprietà; ⚠ cartella diversa |

Altre osservazioni sulle mutazioni:
- `claims.json:19` e l'abstract dicono "six guard-removal mutations". Solo `m4` (guard rimosso), `m3` (insieme di stati allargato) e `m6` (predicato allargato) sono rimozioni/allargamenti di guard. `m1`, `m2` e `m5` aggiungono o cambiano un effetto.
- Le mutazioni sono applicate solo a `DIB.tla` (base). Nessuna sul modello distribuito e nessuna su `Reconcile`.
- `formal/logs/mutation_m*.log` sono di un run precedente (2026-09-05 15:28, conteggi di stati diversi: m1 405 vs 285). `claims.json` punta ai `result.log` più recenti. Il README li dichiara "historical".

**Controparte nel codice, test e back-test delle mutazioni** (numerazione repo):

| Mutazione | Dove il codice impedisce il difetto | Test che lo cattura | Back-test sul codice? |
|---|---|---|---|
| m1 restore ricrea il grant | `SVC:708-711` (target MonitorOnly, mai Active) | `T:225` (`state == MONITOR_ONLY`), `T:475` | ❌ (nessun `grantValid` nel codice) |
| m2 commit esce dal sito | `SVC:468,481` (una sola riga) | `T:807`, `T:824` (commit concorrenti) | ❌ |
| m3 export da Disputed | `SVC:776` (`state==ACTIVE`) | **nessun test** con record Disputed/Revoked(Dispute) prima del restore | ❌ ma a livello gateway c'è `results/openwrt/*/ruleset_after_dispute1.txt` |
| m4 local-restore ignora dispute | `SVC:565-569` | `T:354`, `T:435` | ❌ |
| m5 local-revoke fa fan-out | `SVC:508-533` | `T:302` | ❌ |
| m6 restore ignora provenienza | `SVC:743-757` | `T:401`, `T:435` | ✅ `formal/logs/regression_before.log` mostra `T:401` che fallisce sulla versione sbagliata (`'monitor-only' == 'revoked'`); `regression_after.log`: 33 passed |

### 2.4 Elenco dei buchi (da chiudere prima di dichiarare "verificato")

| ID | Buco | Gravità |
|---|---|---|
| B1 | Retention expiry (R8): né modello, né codice, né test. Table II lo include. | Alta (la riga esiste nel paper) |
| B2 | `grantValid` non esiste nel codice (R2, M1, colonna "Grant valid?"). | Media |
| B3 | Il modello distribuito con `Reconcile` lascia Active un sito rimasto offline per un intero episodio, mentre il codice lo porta a MonitorOnly (D6). L'affermazione I3 del paper su "siti che hanno perso l'intero episodio" non è model-checked. | **Alta** |
| B4 | Nessun test pytest su `distributed/service.py` (fan-out, retry, outbox, reconcile, `origin`). Solo script che richiedono Docker/processi. | Alta |
| B5 | `query_score` durante dispute aperta: nessun test (R1). | Media |
| B6 | `operator_commit` da Disputed/Revoked e dopo un rescore sotto soglia: nessun test (R2, D4). | Media |
| B7 | Export con record Disputed/Revoked(Dispute) prima del restore: nessun test registry (M3/m3). | Media |
| B8 | Dispute successive alla revoca (terzo voto): nessun test (R4). | Bassa |
| B9 | Rifiuto delle transizioni non definite: coperto solo in parte. | Bassa |
| B10 | Nessun mutation testing sul codice tranne m6. | Media |
| B11 | Autorizzazioni ("local operator", "authorized restore", "valid dispute"): non implementate né testate. Il paper lo dichiara fuori scope (`docs/main.tex:172`); la tabella però le usa come precondizioni. | Dichiarata |
| B12 | Controlli negativi del modello distribuito (`DisputeSuspendsEverywhere` che *deve* fallire, `I3_ConservativeRestore` non ristretta che fallisce: `TLAD:22-31,283-304,331-343`) senza log salvato né voce in cfg. Non sono verificabili dall'artifact. | Media |
| B13 | Scala dei modelli: 3 siti × 2 fatti (base), 3 siti × **1** fatto con `ToggleBound ≤ 4` e un solo sito partizionabile (`DIB_Distributed.cfg:6-11`). Il commento in testa a `DIB_Distributed.cfg:1-2` dice "3 sites, 2 facts", ma `:7` ha `Facts = {f1}`. | Bassa |

---

## 3. Dove osMUD valida la firma e quale opzione il testbed disattiva

Sorgente letto: `OSM` (commit 852918e). Nei punti qui sotto `OSM/` è la cartella `src/`.

### 3.1 Percorso di validazione (osMUD)

1. Il nome del file di firma si ottiene sostituendo l'estensione dell'URL del MUD con `p7s`: `MUD_FILE_SIGNATURE_EXTENSION "p7s"` (`OSM/mud_manager.h:26`), `createSigUrlFromMudUrl` (`OSM/dhcp_event.c:64-71`).
2. `executeNewDhcpAction` (`OSM/mud_manager.c:258-315`) scarica il MUD (`:273`) e poi la firma (`:279`).
3. `validateMudFileWithSig` (`OSM/dhcp_event.c:78-87`) chiama `verifyCmsSignature` (dichiarata in `OSM/mud_manager.h:51`).
4. `verifyCmsSignature` (`OSM/openwrt/openwrt.c:231-262`) esegue con `system()`:
   `openssl cms -verify -in <p7s> -inform DER -content <mud.json> -purpose any`. Un codice di ritorno ≠ 0 vale `INVALID_MUD_FILE_SIG`.
   - Non c'è `-CAfile` né `-CApath`: la fiducia dipende dallo store di default di OpenSSL.
   - Non c'è alcun pinning del firmatario o del certificato.
5. Solo se il risultato è `VALID_MUD_FILE_SIG` si chiama `executeMudWithDhcpContext` (`OSM/mud_manager.c:285-295`); altrimenti si registra "BAD SIGNATURE" (`:298`). Se la firma non si scarica: "NO SIG FILE RETRIEVED" (`:303`).

Nel repo DIB non c'è nessun codice di firma: `grep -E "p7s|pkcs7|cms|signature"` su `code/src`, `code/scripts/*.py`, `openwrt/*.py` non dà risultati. `EXP:139-156` produce solo il documento JSON. L'esportatore non produce un file `.p7s`.

### 3.2 L'opzione disattivata: `-i`

`router-entrypoint.sh:40` avvia `osmud -d -i -m DEBUG …`. L'opzione `-i` imposta `noFailOnMudValidation = 1` (`OSM/osmud.c:271,275`) e l'help dice: "Do not fail processing when the MUD file p7s file does not validate" (`OSM/osmud.c:196`, confermato con `docker run … osmud -h`). Il README di `openwrt/` (righe 87-91) lo riconosce.

**`-i` fa tre cose, non una** (il README e il paper ne citano una):
1. Rende irrilevante il fallimento del *download* della firma: `|| (noFailOnMudValidation)` in `OSM/mud_manager.c:279-280`.
2. Rende irrilevante l'*esito* della verifica: `|| (noFailOnMudValidation)` in `OSM/mud_manager.c:285-286`.
3. **Disattiva la verifica del certificato TLS del server MUD**: `CURLOPT_SSL_VERIFYPEER = 0` in `OSM/comms.c:66-67` (con `-i` spento è `1`, `:69`). Nel testbed non pesa, perché il MUD server è su `http://mud-server:8000/camera.json` (`run.sh:35`), ma il paper non lo dice.

**Prova empirica** (`results/openwrt/single-run-lifecycle/osmud.log`, righe 18-22; il file contiene byte non testuali, serve `grep -a`):
- r.18 "MUD and SIG FILE RETRIEVED"
- r.19 `validateMudFileWithSig()`
- r.20 comando `openssl cms -verify … camera.p7s … camera.json -purpose any`
- r.21 `ERROR::DEVICE_INTERFACE::` (verifica fallita)
- r.22 `executeMudWithDhcpContext()` → le regole vengono installate lo stesso.

La verifica viene quindi eseguita, fallisce, e viene ignorata.

**Aggravante verificata:** nell'immagine del router `openssl` **non esiste** (`docker run … sh -c 'command -v openssl'` → `openssl: NOT FOUND`; `Dockerfile.router:12-13` installa solo `firewall4 nftables-json uci curl ca-bundle`). Quindi, anche togliendo `-i` e fornendo una firma valida, la verifica fallirebbe sempre. L'errore alla r.21 è con ogni probabilità "comando non trovato", non "firma non valida". Questo non l'ho riprodotto togliendo `-i`.

**Il probe di interoperabilità non tocca questo percorso.** `reproduce_mud_export.sh:44-46` compila solo `mudparser.c`, `oms_utils.c`, `oms_logging.c`. `mud_manager.c` e `openwrt.c` (dove sta la verifica) non sono inclusi.

Nota a margine: `verifyCmsSignature` costruisce una riga di comando per `system()` con percorsi derivati dall'URL (`OSM/openwrt/openwrt.c:238`). È codice osMUD upstream, fuori dal perimetro del paper.

### 3.3 Cosa dice il paper

- `docs/main.tex:174`: "the receiving site's MUD manager signs these exports, and the gateway trusts that site's policy-signing authority". **Nel codice non c'è alcun firmatario** (§3.1).
- `docs/main.tex:175` (tuo commento): "The enforcement testbed uses unsigned exports with signature validation disabled. - to do".
- `docs/main.tex:422` lo dichiara già nella sezione sperimentale: "Exports are unsigned and signature validation is disabled."
- Il paper non menziona che `openssl` manca nel router né che `-i` disattiva anche la verifica TLS.

---

## 4. Differenze tra ciò che fa il codice e ciò che dice il paper

Legenda: **C→P** il codice fa qualcosa che il paper non dice · **P→C** il paper dice qualcosa che il codice non fa · **M↔C** divergenza tra modello TLA+ e codice.

| ID | Tipo | Differenza | Evidenza |
|---|---|---|---|
| D1 | P→C | **Retention expiry** (riga 8 di Table II e il paragrafo sulla finestra W) non è implementata. | `docs/main.tex:326` (paragrafo) e didascalia `:305`; README v43; assenza di codice (grep in `code/src/dib/registry`). |
| D2 | P→C | Il paper introduce `grantValid[s][f]` e "creates a fresh grant". Il codice non ha una variabile di grant: `grantValid` è implicito in `state==Active`. | `docs/main.tex:291`; `DB:180-198`; `TLA:34,220`. |
| D3 | P→C | "Differ in the separately stored revocation origin": nel registry centralizzato l'origine **non è memorizzata**, è dedotta dalla storia degli eventi (l'ultimo tra `local_revoke` e `revoke`). Solo il distribuito ha la colonna `origin`. Se la storia manca, il caso è trattato come locale (conservativo). In più `local_restore` non controlla la provenienza (il modello sì). | `docs/main.tex:290`; `SVC:515-523,744-757`; `DIST:116,166`; `TLA:183`. |
| D4 | M↔C | `operator_commit` richiede `score.accepted` (evidenza ancora ammissibile) oltre allo stato MonitorOnly. Il modello e Table II ("local operator; no dispute") no. Se un rescore porta un fact in MonitorOnly sotto soglia, per il codice il commit fallisce, per il modello è possibile. Nessun test. | `SVC:471-475`; `TLA:100-107`. |
| D5 | C→P / M↔C | `restore_score` non fa solo cambiare stato: **ripristina anche i valori del punteggio** (score, confidenze, `accepted`, tier) all'ultima versione con status Active. Un rescore avvenuto durante la disputa viene scartato e un fact non più ammissibile può tornare `accepted=True`. Il modello lascia `admissible` invariato nel `Restore` (`UNCHANGED admissible`). | `SVC:694-706`; `TLA:158`. `T:546` esercita questo comportamento come voluto (restituisce 0.92, il punteggio dell'ultima versione Active), ma il paper non lo descrive. |
| D6 | M↔C | **Siti offline e Reconcile.** Nel codice distribuito, il target `restore` si applica a qualunque stato non "Local-revoked", quindi un sito rimasto **Active** per un intero episodio torna a MonitorOnly (asserito in `offline_veto_reconciliation.py:116`). Nel modello `Reconcile` con `¬OpenDispute` porta a MonitorOnly solo Disputed/Revoked(Dispute) e lascia Active il resto (`TLAD:242-248`). Inoltre `I3_ConservativeRestore` nel modello distribuito è ristretta ai siti raggiungibili e non pendenti (`TLAD:344-348`), e non c'è proprietà sull'esito di `Reconcile`. Il paper afferma in I3 che la restaurazione richiede approvazione fresca "including … sites that missed the entire dispute/restore episode" (`docs/main.tex:332`). Questa frase regge sul codice e su un esperimento, non sul modello. | `DIST:147-170`; `TLAD:227-250,344-348`; `offline_veto_reconciliation.py:112-123`. |
| D7 | P→C | L'eq. `admitauto` include `¬openDispute(d,e)`. In `admit_auto` il parametro `open_dispute` esiste ma nessun chiamante lo valorizza (il suo docstring dice "not yet built"). Il blocco effettivo avviene al momento della query (`status != ACTIVE`). | `dib.py:22-47`; `SVC:439`. |
| D8 | C→P | `DIB_DIST_SUSPENSION_QUORUM=2` (non in paper né in TLA+): la prima segnalazione non sospende; con quorum 2 la seconda segnalazione di un sito distinto sospende (`disputed_by` = quel sito) e una successiva segnalazione del sito già contato, che è diverso da `disputed_by`, revoca: bastano due siti distinti, non tre (`DIST:450`, test `test_suspension_quorum_2_two_distinct_sites_suffice_characterization`). Correzione del 2026-10-10: la versione precedente di questa riga diceva «un terzo sito distinto». Il default è 1. | `DIST:69-71,439-453`. |
| D9 | C→P | Un fact Active il cui endpoint è IP-literal o con protocollo non mappabile non genera ACE: nessun errore, solo `skipped_endpoints`. `Exportable` nel paper è `Active ∧ grantValid`, senza questa restrizione. | `EXP:94-98`; `SVC:776`. |
| D10 | C→P | `export_active_mud` forza `accepted=True` per i fact Active: un fact con punteggio sceso sotto soglia resta esportato, solo marcato `flagged_for_review`. Coerente con la regola "i punteggi non cambiano permessi", ma va detto in modo esplicito. | `SVC:764-791`, `:344-353`; test `T:646`, `test_rescoring_non_destructive.py:116`. |
| D11 | C→P | **Fan-out reale**: 3 tentativi per sito con timeout 1,0 s, **senza pausa** tra i tentativi, **in sequenza** su tutti gli N siti; un sito giù costa fino a ~3 s e la risposta HTTP di `/dispute` e `/restore` attende il fan-out. Il paper dice solo "up to three attempts of 1 s each" (`docs/main.tex:501`): coerente con il codice. Non dice che non c'è pausa tra i tentativi, che il giro è sequenziale e che la risposta HTTP attende il fan-out. Anche i "ten retries" del registry centralizzato (`docs/main.tex:420`) corrispondono a `SVC:183`. | `DIST:64-65,356-382,456-459,478-479`. |
| D12 | C→P | Outbox e riconciliazione: chiave `(site, score)` con "latest wins", `ack` cancella **tutte** le righe del sito (`DELETE … WHERE site_id=?`), anche quelle arrivate dopo il `GET`. La finestra è stretta (un evento nuovo viene consegnato direttamente se il sito è su), non ho un reproducer. `reconcile_race_experiment.py` testa una corsa diversa (evento B concorrente a `/reconcile`). | `DIST:372-382,482-496`. |
| D13 | C→P | `/dispute`, `/restore`, `/commit`, `/local-*`: nessuna autenticazione né verifica di appartenenza del sito; `site_id` è una stringa fidata. Il paper lo dichiara ("trusted caller identities", `docs/main.tex:172`). | `API:184-287`; `DIST:429-432`. |
| D14 | P→C | Policy authority: "the receiving site's MUD manager signs these exports". Non esiste firmatario; il testbed usa osMUD con `-i`, con verifica TLS disattivata e senza `openssl` nell'immagine. | §3. |
| D15 | C→P | `query_score` restituisce `None` se la prova globale non è ammissibile **anche** quando il sito ha già un record. Il paper dice "or returns its existing decision". | `SVC:439-444`; `docs/main.tex:233` ("A query stages … or returns its existing decision"). |
| D16 | Numerazione | Table II del piano = `tab:transitions` che nel PDF è Table III. Le mutazioni del paper (M3–M6) non coincidono con `m3–m6` dei file e la proprietà di M5 è sbagliata (§2.3). | `V/paper/main.aux:39,55,68`. |
| D17 | Riferimenti stantii | Le intestazioni dei `.tla` citano "Sec. IV-B" e "Table IV" (le mutazioni sono Table V nel PDF). Il commento di `DIB_Distributed.cfg:1-2` dice "3 sites, 2 facts" ma `:7` ha `Facts={f1}`. `formal/distributed/DIB.cfg` è una copia non usata di quello base. `README.md` dice paper v42.0 mentre `paper/main.tex` è la revisione stilistica "(43)". | `TLA:3`; `TLAD:31`; cfg. |
| D18 | Ambiente | `pyproject.toml` richiede Python ≥3.12; la suite è stata eseguita (e le cache sono state generate) con 3.10. | `code/pyproject.toml:9`; `code/**/__pycache__/*cpython-310*`. |

Provenienza dei log OpenWrt: `results/openwrt/single-run-lifecycle/osmud.log` porta data 2026-08-03 12:24, mentre il README di `openwrt/` elenca run completi dall'8 agosto in poi. Il contenuto è coerente con un singolo evento NEW (49 righe). Va controllato a quale run appartiene prima di citarlo come evidenza.

---

## 5. Prossimi passi suggeriti (non eseguiti)

Ordine di dipendenza per chiudere i buchi, senza toccare modelli, paper o risultati senza la tua conferma (regole di `CLAUDE.md`):

1. **Decidere con te**: B1/D1 (implementare la retention o togliere la riga dal paper), B3/D6 (estendere `Reconcile` nel modello o ridimensionare l'affermazione), D5 (restore del punteggio).
2. **Test mancanti sul registry** (nessuna modifica al codice): B5, B6, B7, B8, B9, più un `pytest` che esercita `distributed/service.py` in-process (B4).
3. **Allineare la numerazione M1–M6** tra paper, `claims.json` e cartelle (D16), e la proprietà di M5.
4. Per il testbed: tre domande aperte, da decidere prima del §6 del piano: aggiungere `openssl-util` all'immagine; firmare davvero i MUD; dire nel paper che `-i` disattiva anche la verifica TLS.
5. Etichettare un commit di riferimento di `V/` (piano §7.1.1).
