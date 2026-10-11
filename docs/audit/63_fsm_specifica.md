# Audit 63 — Specifica della macchina a stati del lifecycle (evidence, sito, monolite)

Data: 2026-10-12. Branch `tnsm-fsm`, worktree separata `/root/Desktop/DIB_tnsm_fsm`, base
`6e6d352` (punta di `tnsm-driver-retry` al momento della creazione). Obiettivo 1 del prompt
dell'audit 61. Nessun codice, modello o paper modificato.

Abbreviazioni e versioni lette (tutte le righe sotto sono state rilette in questa sessione, salvo
quelle nella sezione "NON VERIFICATO"):
- **S** = `code/src/dib/registry/distributed/service.py` a `6e6d352`
  (sha256 `0501b383043a44d4be2f9e0ac2dd9ce2db6ae585b04838a0f54bb1fba3d42a64`). I commit `3a8543b`
  (keepalive opt-in) e `16a6db0` (default `FANOUT_CONCURRENCY = min(N_SITES, 16)`, S:147) dell'altra
  sessione hanno spostato di circa +80 righe tutto ciò che segue S:148: le righe del prompt
  dell'audit 61 si riferiscono alla versione `8505333` e non coincidono con quelle qui.
- **SV** = `code/src/dib/registry/services.py` (monolite).
- **P** = `docs/main_wip.tex` (tabella delle transizioni P:313-329, testo P:334, invarianti P:338-340).
- **M0** = `formal/base/DIB.tla`, **MAE** = `formal/distributed_ae/DIB_AE.tla`.

## 1. Evidence (S, ruolo `evidence`)

Stato per fatto: `status ∈ {active, disputed, revoked}`, `disputed_by`, `fanout_seq`, `accepted`
(S:743-746); voti `suspension_reports(score_id, site_id)` (S:749-750); outbox
`pending_fanout(site_id, score_id)` con chiave primaria per coppia (S:747-748).

| Stato | Evento | Guardia | Effetto | Fan-out |
|---|---|---|---|---|
| — | `/seed` (consortium_admin) | — | nuovo fatto `active`, `accepted=1` (S:839) | no |
| qualunque | `/attest` | fatto esistente | `positive_attestations+1`; nessun cambio di stato | no |
| active | `/dispute(r)`, Q=1 | `site_id` presente (S:899-900) | `disputed`, `disputed_by=r`, seq+1 (S:912-917) | `dispute` → `disputed` |
| active | `/dispute(r)`, Q=2 | voti distinti < 2 dopo `INSERT OR IGNORE` (S:908-911) | solo voto registrato | no |
| active | `/dispute(r)`, Q=2 | voti ≥ 2 | come Q=1, `disputed_by=r` = **il secondo votante** (S:914-915) | `dispute` |
| disputed | `/dispute(r)` | `r ≠ disputed_by` (S:918) | `revoked`, seq+1 (S:919-921) | `revoke` → `revoked` |
| disputed | `/dispute(disputed_by)` | — | nessuno (S:922) | no |
| revoked | `/dispute(r)` | — | nessuno (S:922) | no |
| disputed/revoked | `/restore` (consortium_admin) | stato ∈ {disputed, revoked} (S:937) | `active`, `disputed_by=NULL`, seq+1, **voti cancellati** (S:939-944) | `restore` → `monitor-only` (S:948) |
| active | `/restore` | — | 409 (S:938) | no |

Fan-out (S:781-832): per ogni sito fino a 3 tentativi; se falliscono, upsert nell'outbox con
"vince il seq maggiore" (S:808-810). Il fan-out avviene **dopo** il commit della transazione
(S:924-926, S:947-948). `/pending` restituisce outbox e `current` (stato attuale di ogni fatto con
`fanout_seq > 0`, S:959-979) nella stessa transazione.

## 2. Sito (S, ruolo `site`)

Stato per fatto: riga di `local_decisions(score_id, state, origin, last_applied_seq)` (S:440-442).
"Absent" = nessuna riga (il nome non esiste nel codice, d3). `origin ∈ {NULL, local, fanout}`;
`fanout` solo su `revoked` (S:491).

Le azioni dell'operatore leggono prima l'evidence con `GET /scores` (S:461-470) e **poi** aprono una
transazione locale separata: lettura e scrittura non sono atomiche (a8, b3).

| Stato locale | Evento | Guardia (lettura evidence → transazione locale) | Nuovo stato | Note |
|---|---|---|---|---|
| Absent | `/query` | evidence `accepted ∧ status=active` (S:500-502) → nessuna riga (S:505-507) | monitor-only, `last_applied_seq = fanout_seq letto` (S:508-514) | seq letto PRIMA della transazione |
| esistente | `/query` | — | invariato (S:506-507) | |
| monitor-only | `/commit` | evidence `accepted ∧ active` (S:522-524) → stato = monitor-only (S:528) | active (S:530) | unico ingresso in Active |
| MO/active/disputed/revoked(fanout) | `/local_revoke` | evidence: fatto esistente (S:538-540) → guardia S:544-547 | revoked, origin=local (S:549-552) | dipende dalla raggiungibilità dell'evidence (b4) |
| revoked(local) | `/local_restore` | evidence `status ∉ {disputed, revoked}` (S:563-564) → revoked ∧ origin=local (S:568) | monitor-only, origin NULL (S:570-573) | |
| Absent | fan-out / reconcile | — | invariato (S:476-478) | nessuna riga creata |
| qualunque | fan-out con `seq ≤ last_applied_seq` | — | invariato (S:480-481) | idempotenza |
| revoked(local) | fan-out `restore`/`dispute`/`revoke` | — | invariato, `last_applied_seq=seq` (S:482-490) | veto locale |
| qualunque altro (MO, active, disputed, revoked(fanout)) | fan-out `dispute` | seq nuovo | disputed, origin NULL | |
| idem | fan-out `revoke` | seq nuovo | revoked, origin fanout | anche da MO/active (episodio perso) |
| idem | fan-out `restore` | seq nuovo | **monitor-only** (S:491-495) | anche da **active** e monitor-only (a2) |
| — | `/reconcile` | outbox, poi `current` (S:603-654) | come fan-out | ripara solo se `seq_current > last_applied_seq` (S:584-601) |
| active | `/export_mud` | — | esporta tutti gli active (S:682-709) | nessun controllo di freschezza (a5) |

## 3. Monolite (SV)

Stato: `Score.status`, `LocalDecision.state`; nessun `origin`: la provenienza della revoca è letta
dalla storia `LocalDecisionVersion` (SV:516-521, SV:743-757). Nessun seq per fatto, nessun ruolo
(SV:676 `actor_site_id: str | None = None`), nessun quorum configurabile. Tutto in una transazione
SQLAlchemy con retry ottimistico (`_retry_on_conflict`).

| Stato | Evento | Guardia | Effetto |
|---|---|---|---|
| Absent | `query_score` | `accepted ∧ status=active` (SV:439) | monitor-only (SV:445) |
| monitor-only | `operator_commit` | `accepted ∧ active` (SV:471), stato MO (SV:476) | active (SV:481) |
| MO/active/disputed; revoked con ultimo evento `revoke` | `local_revoke` | SV:515-528; **nessuna** guardia sullo stato globale | revoked (SV:529) |
| revoked (qualunque origine) | `local_restore` | `status ∉ {disputed, revoked}` (SV:565), stato revoked (SV:570) | monitor-only (SV:575); **nessun controllo di provenienza** |
| status active | `dispute_score(s)` | SV:648 | status disputed; decisioni in {MO, active, disputed} → disputed (SV:649-654) |
| status disputed | `dispute_score(s)` | `s ≠ disputed_by` (SV:657) | status revoked; decisioni in {MO, active, disputed} → revoked, evento `revoke` (SV:658-662) |
| status disputed/revoked | `restore_score` | SV:689-693 | status active; solo decisioni disputed, o revoked con ultimo evento `revoke`, → monitor-only (SV:708-711, SV:740-757) |
| qualunque | `upsert_score` (rescore) | — | aggiorna `accepted`; non cambia mai lo stato; segna "flagged" gli active non più ammessi (SV:344-353) |
| active | `export_active_mud` | — | esporta anche gli active "flagged" (SV:769-772, SV:776) |

## 4. Divergenze

### 4.1 S ↔ SV
- **D1 (a2).** Restore: SV tocca solo decisioni disputed o revoked da dispute (SV:710, SV:743-757);
  S porta a monitor-only ogni record non revocato localmente (S:482-495), quindi anche active e
  monitor-only. Sugli stati raggiungibili del monolite la differenza **non si osserva**: in SV il
  fan-out è sincrono e nella stessa transazione (SV:651-654), e durante l'episodio `query` e
  `commit` sono bloccati (SV:439, SV:471), quindi al restore non esistono decisioni active o MO
  del fatto. In S invece un sito che ha perso la dispute (o, vedi D7, un commit in corsa) è active
  al momento del restore: S lo riporta a monitor-only, che è il comportamento che P:606 e P:610
  descrivono e che `test_distributed_service_inproc.py:238` (D6) fissa.
- **D2 (nuova).** `local_restore`: S richiede origin=local (S:568); SV accetta qualunque revoked
  (SV:570). In SV un record revocato da dispute con provenienza mancante (lasciato da SV:754-757) è
  ripristinabile localmente; in S un revoked(fanout) dopo il restore globale non esiste (diventa
  monitor-only).
- **D3 (a10).** Quorum: SV sospende sempre alla prima segnalazione (SV:648); S ha
  `SUSPENSION_QUORUM ∈ {1,2}` (S:127-129). Con Q=2 in S, `disputed_by` è il secondo votante
  (S:914-915), quindi il primo votante può confermare la revoca (S:918): bastano due siti distinti
  (già caratterizzato da `test_distributed_service_inproc.py:108-122`). La tua decisione del
  2026-10-12 è che con Q=2 la revoca richieda un sito distinto da **tutti** i votanti: il codice la
  viola; test pre-registrato in P2.
- **D4.** Ruoli: assenti in SV (SV:676); in S solo con `DIB_DIST_MTLS=1` (S:177-186); senza mTLS
  `site_id` della dispute viene dal payload (S:867-878, b7).
- **D5 (a1).** Ammissione: in SV `accepted` è ricalcolato sul percorso di rete (SV:290-304,
  `api.py:132`) e il rescore non cambia lo stato (SV:344-353); in S `accepted` è scritto a 1 al seed
  (S:839) e nessuna rotta lo modifica (grep di `accepted` in S: solo S:501, :523, :704, :746, :776,
  :839, :853, :905, :936), quindi il ramo `not score["accepted"]` di S:501 e S:523 non può scattare.
- **D6 (a8).** Atomicità: SV legge evidence e decisione nella stessa transazione; S no (S:500→516,
  S:522→532, S:538→554, S:560-564→575).
- **D7 (b3, conseguenza di D6).** Finestre in S non presenti in SV né nei modelli:
  - `/query`: il seq usato per `last_applied_seq` è quello letto (S:512); un fan-out arrivato fra
    lettura e INSERT trova la riga assente e non fa nulla (S:476-478): il record nasce monitor-only
    durante un episodio aperto. Riparabile da `current` (seq maggiore).
  - `/commit`: se il fan-out della dispute non raggiunge il sito prima della transazione, il commit
    crea active dopo che l'evidence ha già committato la dispute.
  - `/local_restore`: un fan-out `dispute` arrivato fra il controllo S:563 e la transazione porta
    solo `last_applied_seq` avanti (S:487-490); poi la transazione scrive monitor-only (S:570-573).
    Lo stato resta monitor-only con seq allineato: `current` non lo ripara (S:593).
  Verifica sperimentale: P2/P3 (audit 64).
- **D8.** Retention expiry: assente in SV e in S (grep `retention|expir` in `code/src/dib/registry`:
  solo un docstring non correlato, SV:192).

### 4.2 Codice ↔ paper (P)
- **P-a (a3).** La tabella P:319-329 non ha la riga "Active/MonitorOnly + restore globale (sito che
  ha perso la dispute) → MonitorOnly", che S implementa (S:491-495) e che il testo descrive
  (P:606, P:610). Proposta, non applicata: aggiungere la riga oppure una nota alla riga P:324.
- **P-b (a3).** "Retention expiry" (P:327, P:334, P:778) non è implementata (D8); la caption P:313
  dice già "specified here but lies outside the verified configuration", ma non dice che manca
  anche nel codice. Proposta: "not implemented in the prototype".
- **P-c (a10).** P:323 "second dispute — distinct reporting site" e P:646 ("Under two-reporter
  suspension the first report is retained and the second opens the dispute") non dicono chi può
  confermare con Q=2. Con la tua decisione, il codice (D3) è il punto da correggere, non il paper.
- **P-d (b4).** P:547 descrive il modello distribuito "with … local revoke and restore enabled while
  the site is unreachable"; in S il sito irraggiungibile dalla rete non può nemmeno chiedere
  `GET /scores`, e local_revoke fallisce (S:538, S:461-470, nessun try). In MAE, `LocalRevoke` non
  legge lo stato dell'evidence (MAE:264-271) e "evidence unreachable from the site" non è modellato
  (MAE:53). Test in P2.
- **P-e (D7).** P:320-321 richiedono "no open dispute" per query/stage e local commit; S non lo
  garantisce sotto concorrenza (D7). P:338 (I1) non è violato da `/query` (non crea active), ma la
  finestra `/commit` di D7 crea un active dopo la dispute: è I1 "fresh local authorization" o I3
  "dispute invalidates grants"? Il commit è dell'operatore (I1 rispettato alla lettera); I3 vale
  solo "upon reconciliation" per un sito non raggiunto dal fan-out (P:340). Lo classifico come
  violazione della precondizione di P:321, non di I1-I3: da confermare con l'esito di P3.

### 4.3 Codice ↔ modelli
- **M-a (a1).** M0 modella l'ammissione come Booleano con `Rescore` non deterministico (M0:14-16,
  :63, :79-82): il prompt dell'audit 61 dice "Rescore non è modellato", ma in M0 lo è; manca in MAE
  (MAE:56). M0 `OperatorCommit` non controlla `admissible` né `OpenDispute` (M0:100-107): nel
  modello la guardia è superflua perché un MonitorOnly non coesiste con una dispute aperta (Query
  bloccata M0:91, Dispute sposta MO in Disputed M0:128, LocalRestore bloccato M0:184). D7 mostra che
  nel codice quella coesistenza è possibile.
- **M-b (a8).** MAE legge `estatus` e scrive lo stato locale nello stesso passo (Query MAE:244-252,
  OperatorCommit MAE:254-262, LocalRestore MAE:273-280): le finestre D7 non sono rappresentabili.
- **M-c (a10).** M0 conta i votanti come insieme e revoca con ≥ 2 distinti (M0:123-126): con quorum
  di sospensione 1 coincide con S Q=1. Q=2 non è modellato (MAE:55, MAE:207).

## 5. Chiusura dei punti del prompt
- **a1** chiuso come descrizione (D5, M-a). Nessuna decisione richiesta: in S l'ammissione è
  fuori ambito (il distribuito eredita `accepted` costante); da dichiarare nel paper se P:320
  "admitted" viene riferito al prototipo distribuito.
- **a2** chiuso (D1): divergenza reale solo in S, ed è il comportamento voluto da P:606/P:610.
- **a3** chiuso con due proposte di testo (P-a, P-b), non applicate.
- **a10** decisione presa (D3): test rosso atteso in P2.
- **d2** (fuori dagli obiettivi 1-5, solo nota): il default `FANOUT_CONCURRENCY` è già cambiato in
  `16a6db0` (S:147, `min(N_SITES, 16)`); `RECONCILE_INTERVAL` resta 0 (S:143). Il harness fissa
  `DIB_DIST_FANOUT_CONCURRENCY=1` per i test esistenti (`_dist_harness.py`, diff di `16a6db0`).

## NON VERIFICATO
- Righe di MAE oltre 40-60 e 195-300, e di `formal/distributed/DIB_Distributed.tla`: lette
  dall'agente, non da me.
- P:547, P:646, P:778: citate dall'output di `grep`, non rilette nel contesto del paragrafo.
- Che nessun chiamante esterno al servizio modifichi `scores.accepted` nel DB evidence (verificato
  solo dentro S).
