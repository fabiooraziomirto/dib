# Audit 90 — Handoff: rieseguire gli esperimenti sul codice corretto (`tnsm-fixes`, `dc3dd20`)

Data: 2026-10-12. Autore: la sessione FSM (branch `tnsm-fsm`, worktree `/root/Desktop/DIB_tnsm_fsm`).
Destinatario: la sessione esperimenti (worktree `/root/Desktop/DIB_tnsm` / `DIB_tnsm_fixes`). Questo file basta da
solo: non serve rileggere gli audit 63-68.

**Convenzioni.**
- **"Eseguito"** = l'ho lanciato io e ho letto l'output. **"Letto"** = l'ho solo letto nel codice,
  non eseguito.
- Abbreviazioni dei file:
  - **S** = `code/src/dib/registry/distributed/service.py` a `dc3dd20`
    (sha256 `5599f53b486c838a6866f5cd8b5037da4ad5cdec779dc6d68d354f1a9ea129be`; sha256 controllato da me, eseguito);
  - **S0** = lo stesso file a `6e6d352` (`0501b383…3d42a64`), quello su cui ho trovato i difetti;
  - **M** = `experiments_tnsm/tla_fsm/v6/DIB_AE_NA.tla` (modello finale, sha256 prefisso
    `dce224c9cbd14acb`, 849 righe);
  - **R** = `experiments_tnsm/m67_retraction/run.py` (versione di `tnsm-fixes`, 991 righe, sha256 prefisso
    `9040c807e11e801c`).
- Il diff di `dc3dd20` è stato letto con `git -C /root/Desktop/DIB_tnsm_fixes show dc3dd20 -- code/src`.

## 1. Stato del modello a stati finiti

**Ultima versione: v6** (`experiments_tnsm/tla_fsm/v6/`). È `formal/distributed_ae/DIB_AE.tla` più:
- Query/Commit/LocalRestore divisi in lettura e scrittura per i siti in `SplitSites`;
- la correzione (riserva `Staging` sotto il lock di reconcile, commit in due fasi, guardie di seq,
  applicazione della lettura alla chiusura della query);
- il quorum 2.

Ogni run con TLC 2026.05.26 (rev 4ba7d88), jar sha256 `237332bd…`, Java 17.0.19. Gli esiti sotto
sono **eseguiti**.

**Limiti comuni** (salvo dove indicato; cfg `v6/v6_f2_fix_all.cfg`):
- **2 siti** (`s1`, `s2`), **1 fatto**, `PartitionableSites = {s1}`;
- **MaxEvents = 2** (al più due eventi dell'evidence per comportamento);
- MaxLoss = 0 (nessuna consegna persa senza outbox), MaxRounds = 2, MaxToggles = 3, Reporters
  `{r1, r2}`;
- non modellati:
  - evidence irraggiungibile dal sito (MAE:53 del modello pubblicato);
  - crash di processo, tempo, mTLS;
  - più di un'operazione pendente per sito (vincolo del modello: un operatore fa una richiesta
    alla volta);
  - consegne perse (MaxLoss 0 nei run della correzione).

| # | Risultato | Configurazione | Log:riga |
|---|---|---|---|
| 1 | Il modello esteso riproduce il modello pubblicato con operazioni atomiche: **14.947.820** stati, nessuna violazione | `logs/r0_regress.cfg` (v1) | `experiments_tnsm/tla_fsm/logs/r0_regress.log:34` (profondità :35) |
| 2 | Codice vecchio (S0) — commit letto prima di una dispute diventa Active dopo | `logs/n1_commit_race.cfg` | `logs/n1_commit_race.log:25` (violazione), :312 (3.005 stati) |
| 3 | Codice vecchio — local restore in corsa: MonitorOnly con seq allineato durante l'episodio | `logs/n2_lrestore_race.cfg` | `logs/n2_lrestore_race.log:25`, :407 |
| 4 | Codice vecchio — query in corsa: viola l'invariante pubblicato `DisputeSuspendsAtReachableSites` | `logs/n4_rest.cfg` | `logs/n4_rest.log:25`, :253 |
| 5 | Codice vecchio — commit letto prima di un intero episodio dispute+restore diventa Active dopo il restore (I3) | `v3/v3_n5_export_nofix.cfg` | `v3/logs/v3_n5_export_nofix.log:25`, :414 |
| 6 | Codice vecchio — l'ack cancella un evento mai applicato (proprietà D12 pubblicata); l'anti-entropia lo ripara | `v4/v4_n6_export_nofix.cfg` | `v4/logs/v4_n6_export_nofix.log:25`, :431 |
| 7 | Codice vecchio — **l'export resta sicuro**: nessuna violazione di ExportSafe, I1, I2, I3_ConservativeRestore, I3_VetoPreserved su **55.063.707** stati | `v4/v4_n7_export_nofix.cfg` | `v4/logs/v4_n7_export_nofix.log:43` (profondità :44) |
| 8 | Codice vecchio, quorum 2 — un votante della sospensione conferma la revoca | `logs/q1_code_rule.cfg` (3 reporter) | `logs/q1_code_rule.log:25`, :223 |
| 9 | Quorum 2 con regola outsider: nessuna violazione su **64.458.470** stati (3 reporter, operazioni **atomiche**, `SplitSites = {}`) | `logs/q2_outsider_rule.cfg` | `logs/q2_outsider_rule.log:47` (profondità :48) |
| 10 | **Correzione v6, s1 diviso: nessuna violazione di nessuna proprietà su 100.746.547 stati** | `v6/v6_f2_fix_all.cfg` | `v6/logs/v6_f2_fix_all.log:57` (profondità 43, :58) |
| 11 | **Correzione v6, entrambi i siti divisi** (MaxToggles 2): nessuna violazione su **476.759.280** stati | `v6/v6_f3_two_split.cfg` | `v6/logs/v6_f3_two_split.log:174` (profondità 53, :175) |
| 12 | Ogni parte è necessaria: senza applicazione della lettura alla chiusura (con MaxEvents 3) | `v6/v6_m5_nofinishapply.cfg` | `v6/logs/v6_m5_nofinishapply.log:26`, :534 |
| 13 | … senza guardia in LRWrite | `v6m/v6m_m2_nolrguard.cfg` | `v6m/logs/v6m_m2_nolrguard.log:25`, :460 |
| 14 | … senza seconda lettura del commit | `v6m/v6m_m3_noverify.cfg` | `v6m/logs/v6m_m3_noverify.log:25`, :365 |
| 15 | … senza riserva della query | `v6m/v6m_m4_noqueryfix.cfg` | `v6m/logs/v6m_m4_noqueryfix.log:25`, :253 |
| 16 | … senza lock di reconcile sulla riserva | `v6m/v6m_m6_nolock.cfg` | `v6m/logs/v6m_m6_nolock.log:26`, :575 |
| 17 | Perché v6 e non v5: con **MaxEvents 3** la v5 è violata (un restore più vecchio consegnato fuori ordine sulla riserva dopo una dispute arrivata a riga assente) | `v5/v5_f4_e3.cfg` | `v5/logs/v5_f4_e3.log:25`, :432 |

I percorsi in tabella sono relativi a `experiments_tnsm/tla_fsm/`.

**Incompleto (nessuna affermazione):** la correzione v6 con **MaxEvents 3** (`v6/v6_f4_e3.cfg`). L'ho
fermato io a 202.510.519 stati, profondità 18, perché la proiezione superava il limite di 3 h e la
soglia del disco (`v6/logs/v6_f4_e3.log:69`, riga "STOPPED BY OPERATOR"). Nella parte esplorata non
c'è violazione, ma questo **non** verifica la correzione con 3 eventi.

**Non verificato nel modello:**
- la correzione con quorum 2 **insieme** alle operazioni divise (la riga 9 è con operazioni
  atomiche);
- la correzione con consegne perse (MaxLoss > 0);
- più di un fatto;
- più di 2 siti.

## 2. Corrispondenza fra il modello e `dc3dd20`

**Eseguito:** applicando le mie sostituzioni `FIXES` (`code/tests/tests/test_distributed_fsm_fix_copy.py`,
costanti `FQ`, `FC`, `FR`, `FV`, `FQ2`) al genitore di `dc3dd20` (`dc3dd20^`, sha256 `a6bb1d22…`) si
ottiene **esattamente** S, salvo un'unica differenza: le 3 righe aggiunte del retry keep-alive
(S:852-854, `except RuntimeError` → `httpx.TransportError`), che non sono nella mia copia.

Ogni testo nuovo compare una sola volta in S (contato con `str.count`, eseguito). Comprese le parti
in commento: S contiene i miei commenti `# v5:` (S:517) e `# v6:` (S:535-536).

| Correzione | Riga in S | Punto del modello che la giustifica | Controesempio senza di essa |
|---|---|---|---|
| **FQ** `/query`: 1ª lettura (S:501-503), riserva `staging` sotto `_reconcile_lock` (S:506-518), 2ª lettura (S:521-527), chiusura (S:529-548) che applica la lettura se la riga è già stata spostata (S:534-541) | S:499-549 | M:415-423 `QueryReserve` (guardia `rc[s].ph = "idle"` a M:418 = il lock), M:425 `QueryRead2`, M:431-449 `QueryFinish` (applicazione a M:445) | righe 15, 16, 12 della tabella sez. 1 |
| **FC** `/commit` in due fasi: fase 1 `monitor-only`→`committing` solo se `last_applied_seq ≤ seq letto` (S:560-567), 2ª lettura (S:568-573), fase 2: `active` solo se seq invariato e Active, altrimenti `monitor-only` e 409 (S:575-584) | S:552-585 | M:451 `CommitRead`, M:459-474 `CommitWrite` (guardia a M:462, `Committing` a M:465), M:476 `VerifyRead`, M:482-492 `Promote` (condizione a M:486) | righe 14 e 5 |
| **FR** `/local_restore`: 409 se `last_applied_seq > fanout_seq` letto | S:620-625 | M:504-515 `LRWrite` (guardia a M:508) | riga 13 |
| **FV** `/local_revoke` senza evidence: lookup per (device_type, endpoint, protocol, port) nella tabella locale; ammesso anche da `committing` | S:587-608 (lookup S:591-594, stati ammessi S:597-601) | M:356 `LocalRevoke` non legge l'evidence (come il modello pubblicato, MAE:264-271): la correzione allinea il codice al modello. Non c'è un controesempio TLC per FV: il difetto era di disponibilità (b4), mostrato dal test `test_b4_1_*` | — |
| **FQ2** quorum 2: conferma solo da un segnalante fuori da `suspension_reports` | S:977-980 | M:287 `Confirms` con `ConfirmOutsideVoters = TRUE` (`r ∉ votes[f]`) | riga 8; verificato con la riga 9 |

**Differenze fra modello e codice (letto), da tenere presenti:**
1. Il codice fa una **prima lettura prima della riserva** (S:501-503) e non riserva se l'evidence
   non è Active. Il modello riserva senza leggere: copre un sovrainsieme dei comportamenti, quindi
   i risultati di sicurezza valgono anche per il codice.
2. **Seconda lettura che fallisce** (eccezione):
   - `/query` cancella la riga `staging` e rilancia (S:523-526);
   - `/commit` tratta il fallimento come "evidence cambiata" e torna `monitor-only` (S:568-571).

   Nessuno dei due casi è nel modello (l'evidence irraggiungibile non è modellata).
3. **FQ2** nel codice tiene anche `req.site_id != disputed_by` (S:977). Con quorum 2 `disputed_by`
   è sempre fra i votanti, quindi la condizione è ridondante ed equivalente a M:287 (letto).
   Con quorum 1 il codice è invariato (`SUSPENSION_QUORUM == 1 or …`, S:978).
4. **FV** cerca la riga per tupla; il modello per identificatore di fatto. Il codice presuppone che
   la tupla sia unica in `local_decisions`, ma lo schema non lo garantisce (sez. 3, D4).
5. **Concorrenza nello stesso sito.** Il modello ammette una sola operazione pendente per sito; il
   codice accetta richieste concorrenti dello stesso operatore (thread FastAPI). Ad esempio, due
   `/commit` concorrenti sullo stesso fatto: il secondo trova `committing` e risponde 409 (S:563,
   letto). Le combinazioni di operazioni concorrenti diverse sullo stesso fatto **non** sono
   verificate.
6. **Retry keep-alive** (S:852-854): fuori dal modello, perché le consegne sono astratte. È coperto
   dal test K-11 dell'altra sessione (non eseguito da me).
7. **Test eseguiti da me sulla copia** (non sul file di `dc3dd20`):
   - `test_distributed_fsm_fix_copy.py` + `test_distributed_fsm_stale_commit.py`: 13 passed, 1 xfailed;
   - regressione di tutti i test distribuiti sulla copia v6: 127 passed, 15 failed, 1 xfailed. I
     fallimenti sono tutti caratterizzazioni del vecchio comportamento, xfail strict che sulla
     copia passano, un'ancora non più presente e `test_b3q_2` (dopo la correzione non c'è più un
     record da riparare).

   Sul codice integrato l'altra sessione riporta 491 passed, 7 skipped, 8 xfailed (non rieseguito
   da me).

## 3. Difetti ancora aperti dopo `dc3dd20`

"Tocca le misure di ritiro" significa: cambia il percorso POST /dispute → `_fan_out` →
`/apply_fanout` → P-log (accesso `/apply_fanout` nei log del sito, R:675) o il conteggio di chi è
Active al momento della dispute.

**D1 — righe `staging` / `committing` lasciate da un crash.** Gravità **media** (disponibilità, non
sicurezza).
- **Scenario (letto).** Il processo del sito muore:
  - fra la riserva (S:518) e la chiusura (S:548) di `/query`;
  - oppure fra la fase 1 (S:567) e la fase 2 (S:583) di `/commit`.

  La riga resta `staging` o `committing`. Non è esportabile (l'export seleziona solo `active`,
  S:752), quindi la sicurezza non è toccata.
- **Riparazione.**
  - Una riga `staging` ha `last_applied_seq = 0` (S:512). Se il fatto ha `fanout_seq == 0`, nessun
    fan-out e nessuna anti-entropia la toccano mai: `current` contiene solo i fatti con
    `fanout_seq > 0` (S:1028) e la riparazione richiede `seq > last` (S:649). **La riga è
    permanente.**
  - Un nuovo `/query` trova la riga e risponde `applied: True` senza cambiarla (S:507-508,
    519-520). Un `/commit` risponde 409 (S:563). Il fatto è bloccato per quel sito.
  - Una riga `committing` ha `last_applied_seq` uguale al seq corrente (la fase 1 lo richiede,
    S:563): l'anti-entropia non la vede finché non arriva **un nuovo** evento per quel fatto, anche
    con `fanout_seq > 0`.
- **Tocca le misure?** No sul ritiro: `/apply_fanout` sposta comunque la riga, S:473-496. Sì su
  B2k se un `client_timeout` lascia un `/commit` in volo prima del `kill site-3` (R:712-714):
  `final_states` (R:757-758) potrebbe contenere `committing`.
- **Proposta:** correggere prima del rerun di B2k. Una pulizia all'avvio del sito: `DELETE` delle
  righe `staging` e `committing` → `monitor-only`, nel blocco `if ROLE == "site"` dopo S:445.
  Nessun'altra operazione è in volo all'avvio, quindi è sicuro (argomento letto, non verificato
  nel modello, dove il crash non c'è). Alternativa senza toccare S: il driver controlla a inizio
  prova che non esistano righe `staging`/`committing` e altrimenti esclude la prova.

**D2 — `/query` aspetta il lock di reconcile senza timeout.** Gravità **media** (latenza e
disponibilità).
- **Scenario (letto).** `with _reconcile_lock:` (S:517) blocca finché un `_reconcile_once` in corso
  finisce. Il reconcile tiene il lock mentre fa HTTP verso l'evidence: fino a
  `_RECONCILE_MAX_ROUNDS = 3` giri (S:123) con timeout `RECONCILE_TIMEOUT = 5 s` (S:145), più la
  riparazione. Il `/reconcile` manuale invece usa `acquire(timeout=RECONCILE_LOCK_TIMEOUT)` e
  risponde 503 (S:724, S:146). Con l'evidence lenta (`degraded`) una `/query` può attendere
  secondi; molte `/query` concorrenti occupano i thread del server.
- **Tocca le misure?** Non il ritiro: `/apply_fanout` non prende quel lock, S:634-638. Tocca il
  **setup** (R:632, R:712) e ogni benchmark con `/query`: possibili `ClientTimeout` di setup in più
  (timeout di setup 30 s / 90 s a R:652, 30 s a R:712).
- **Proposta:** correggere, con poco codice. Usare `acquire(timeout=…)` e rispondere 503 come
  `/reconcile`, e far ritentare il driver. Se non si corregge: dichiararlo e riportare nel manifest
  il numero di esclusioni di setup per cella.

**D3 — `/local_revoke` su fatto sconosciuto: 409 invece di 404.** Gravità **bassa** (contratto
dell'API).
- **Scenario (letto).** Prima un fatto sconosciuto all'evidence dava 404 (S0:538-540). Ora il sito
  non chiede all'evidence e senza riga locale risponde 409 (S:597-601). Un fatto noto all'evidence
  ma mai interrogato in quel sito dava 409 già prima.
- **Tocca le misure?** No. `offline_veto_reconciliation.py:95` fa `local_revoke` su un fatto con
  riga locale.
- **Proposta:** dichiarare (documentazione dell'API). Distinguere i due casi richiederebbe di nuovo
  l'evidence, cioè il problema b4.

**D4 — Nessun vincolo UNIQUE (né indice) su (device_type, endpoint, protocol, port) in
`local_decisions`.** Gravità **bassa**, ma di sicurezza nello scenario raro.
- **Scenario (letto).** Lo schema ha solo `score_id INTEGER PRIMARY KEY` (S:441-443). Il lookup di
  `/local_revoke` (S:591-594) prende la prima riga che trova, senza `ORDER BY`. Si hanno due righe
  per la stessa tupla solo se l'evidence riassegna gli id, cioè se il suo database viene perso e
  ricreato (caso già escluso dal bound, S:82-83). In quel caso il veto può finire sulla riga
  vecchia e non su quella viva. In più ogni `/local_revoke` è una scansione completa della tabella.
- **Tocca le misure?** No (nessun esperimento ricrea il DB dell'evidence).
- **Proposta:** dichiarare ora. Aggiungere l'indice UNIQUE insieme all'epoch del seq (progetto in
  audit 65): si ricreano gli stessi DB.

**D5 — Nuove risposte che i driver non controllano.** Gravità **media per le misure**.
- **Scenario (letto).**
  - `/query` ora può rispondere `{"applied": false}` quando la seconda lettura non è Active, e
    cancella la riga (S:545-549).
  - `/commit` ora può rispondere 409 "the evidence changed during the commit" (S:583-584), anche
    quando la seconda lettura **fallisce per la rete** (S:568-573): sotto perdita di pacchetti il
    commit fallisce più spesso.
  - `Env.req` di R non controlla né lo stato né il corpo (R:574-581); `setup_fact` (R:630-633) e
    B2k (R:712-713) ignorano la risposta. `testbed.py:145-148` controlla lo stato 200 ma non
    `applied`.
- **Tocca le misure?** Sì nell'interpretazione: un episodio può partire con alcuni siti non Active.
  Il P-log B1 non cambia, perché `/apply_fanout` risponde 200 e viene loggato anche senza riga
  (S:477-479, S:634-638). Cambia invece il significato di "sito Active al momento della dispute"
  e di `final_all_monitor_only` in B2k (R:759).
- **Proposta:** correggere **nel driver** prima del rerun:
  - controllare `status_code == 200` e `applied` per `/query`, `200` per `/commit`;
  - altrimenti escludere con `excluded_reason="setup_failed"` e contare le esclusioni per cella.

  Non tocca S. R è congelato per hash: nuovo hash da dichiarare.

**D6 — Stati transitori visibili.** Gravità **bassa**.
- **Scenario (letto).** `GET /state` (S:767-777) può restituire `staging` o `committing` durante
  una richiesta in volo.
- **Tocca le misure?** Solo l'analisi: chi confronta con un insieme fisso di stati
  (R:757-759 conta solo `monitor-only`) li conta come anomalie.
- **Proposta:** dichiarare; negli `analyze_*` trattarli come "in volo" (sez. 5,
  `no_transient_left`).

**D7 — `/local_restore` richiede ancora l'evidence** (S:613-617). Gravità **bassa**; scelta
fail-closed: senza evidence non si sa se l'episodio è aperto.
- **Tocca le misure?** No.
- **Proposta:** dichiarare.

**D8 — Limiti del modello che valgono per il codice corretto** (vedi sez. 1): al più 2 eventi,
MaxLoss 0, 1 fatto, 2 siti, operazioni concorrenti nello stesso sito non modellate. Gravità:
**limite di validità**.
- **Proposta:** dichiarare nel paper (lo fa già il branch `tnsm-fsm-paper`: "up to two evidence
  events"). Eventualmente un run TLC con MaxLoss 1 sulla v6 (costo non stimato, NON VERIFICATO).

**D9 — Ancora aperti dalla lista dell'audit 61, non toccati da `dc3dd20`:**
- default `DIB_DIST_RECONCILE_INTERVAL = 0` (S:143): staleness illimitata senza configurazione;
- nessun lease (a5);
- nessun epoch del seq (b8);
- `site_id` dal payload senza mTLS (b7).

Gravità secondo l'audit 65. Proposta: le regole della sez. 4 coprono T; il resto va dichiarato.

## 4. Regole per leggere (e lanciare) gli esperimenti

1. **T.** Ogni blocco deve girare con `DIB_DIST_RECONCILE_INTERVAL = T > 0` e riportare T e il jitter
   nel manifest.
   - Il default del servizio è 0 (S:143): senza trigger, una dispute persa o arrivata a riga
     assente si ripara solo con un `/reconcile` esterno.
   - R lo imposta per ogni cella (R:482-483: `DIB_DIST_RECONCILE_INTERVAL={self.T}`; T=5 per B1,
     R:307; `B2_TS` per B2k, R:310).
   - Per gli script fuori da R va controllato:
     - `testbed.py:72` usa T=5;
     - `offline_veto_reconciliation.py` **non** imposta T (righe 48-54, letto): usa `/reconcile`
       esplicito, va bene così ma va scritto.
2. **Quorum e regola di conferma.** Riportare `DIB_DIST_SUSPENSION_QUORUM` nel manifest.
   - Né R né `generate_compose.py` lo impostano (grep, 0 occorrenze in `generate_compose.py`), quindi
     vale il default 1 (S:127): la regola di conferma
     corretta (FQ2, S:977-980) **non entra in gioco**.
   - Ogni esperimento con quorum 2 su `dc3dd20` richiede **tre** segnalanti distinti per arrivare a
     revocato (due votanti più un esterno).
   - La campagna di sospensione del paper (main_wip.tex:646) va rifatta o riletta con questa
     regola.
3. **Evidence irraggiungibile.** Con l'evidence giù dal sito:
   - `/query`, `/commit`, `/local_restore` falliscono (S:501, S:554, S:613);
   - `/local_revoke` ora funziona (FV);
   - `/export_mud` continua a servire gli `active` senza controllo di freschezza (S:738-765).

   Non si può quindi misurare commit né restore locale durante un guasto dell'evidence, e il ritiro
   ai siti che non ricevono il fan-out è illimitato finché non si riconnettono.
4. **Limite dei due eventi.** Le garanzie del modello sulla correzione valgono con al più due
   eventi dell'evidence per fatto (sez. 1).
   - Gli esperimenti con episodi più lunghi sullo stesso fatto escono da ciò che il modello copre.
   - B2k fa dispute, dispute e restore = **3 eventi** per fatto (R:720-724), sopra il limite.
   - B1 fa 1 evento per fatto (R:658).
   - Per B2k la lettura è quindi empirica, non garantita dal modello.
5. **Commit concorrenti con episodi.**
   - Sul codice vecchio un commit letto prima di un episodio poteva diventare Active dopo (sez. 1,
     riga 5).
   - Su `dc3dd20` la seconda lettura lo impedisce (FC), ma **conviene registrarlo comunque**: per
     ogni commit il driver salva l'istante e la risposta, e a fine prova il `fanout_seq`
     dell'evidence.
   - Oppure si serializza: nessun `/commit` mentre una dispute o un restore sullo stesso fatto è in
     corso. R oggi serializza: il setup precede la dispute, R:652-658 e R:712-722.

## 5. Invarianti controllabili a fine prova

Dati richiesti, tutti esposti dal servizio:
- `GET /state/{score_id}` di ogni sito → `state`, `origin`, `last_applied_seq` (S:767-777), che sono
  i campi di `local_decisions`;
- `GET /scores` dell'evidence → `status`, `fanout_seq` (S:906-ff), campi di `scores`;
- `GET /pending/site-i` → righe in coda;
- il log del driver (istante, operazione, sito, fatto, codice HTTP).

Oggi R legge solo `state` in B2k (R:757). Per questi controlli va letto l'intero `/state` più
`/scores`.

| Invariante | Formula sui campi (r = riga di `local_decisions` del sito per il fatto; sc = riga di `scores`) | Origine |
|---|---|---|
| CaughtUpIsCoherent | `r.last_applied_seq == sc.fanout_seq ⇒ sc.status == 'active' ∨ r.state ∈ {disputed, revoked}` | M:681 |
| Nessun transitorio rimasto | `r.state ∉ {staging, committing}` a fine prova | M:824 `StagingIsTransient`, M:789 `CommittingIsTransient` |
| ExportSafe | `sc.status ≠ 'active' ∧ pending(sito, fatto) = 0 ⇒ r.state ≠ 'active'` | M:801 |
| I1 + "nessun Active senza commit dopo il restore" (I3, `NoStaleActiveAfterEpisode`) | `r.state = 'active' ⇒ ∃ commit 200 del sito sul fatto, e t(ultimo commit 200) > t(ultimo restore 200 del fatto)` | M:696, M:703 |
| I3 veto preservato | `∃ local_revoke 200 al sito ∧ nessun local_restore 200 successivo ⇒ (r.state, r.origin) = ('revoked', 'local')` | M:736 |
| I2 confinamento | `r.origin = 'local' ⇒ ∃ local_revoke 200 di quel sito su quel fatto` | M:710 |

Codice da incollare (funzioni pure; **eseguito**: i 4 test sotto passano, `4 passed in 0.10s`,
Python 3.10.13, file nello scratchpad della sessione FSM):

```python
TRANSIENT = {"staging", "committing"}

def caught_up_is_coherent(rows, scores):
    bad = []
    for (site, sid), r in rows.items():
        sc = scores[sid]
        if r["last_applied_seq"] == sc["fanout_seq"]:
            if not (sc["status"] == "active" or r["state"] in ("disputed", "revoked")):
                bad.append(("CaughtUpIsCoherent", site, sid, r["state"], sc["status"]))
    return bad

def no_transient_left(rows):
    return [("TransientLeft", site, sid, r["state"]) for (site, sid), r in rows.items() if r["state"] in TRANSIENT]

def export_safe(rows, scores, pending):
    return [("ExportSafe", site, sid) for (site, sid), r in rows.items()
            if scores[sid]["status"] != "active" and pending.get((site, sid), 0) == 0 and r["state"] == "active"]

def _last(events, op, sid, site=None, ok=True):
    ts = [e["t"] for e in events if e["op"] == op and e["score_id"] == sid
          and (site is None or e["site"] == site) and (not ok or e["status"] == 200)]
    return max(ts) if ts else None

def no_active_without_commit_after_restore(rows, events):
    bad = []
    for (site, sid), r in rows.items():
        if r["state"] != "active":
            continue
        t_commit, t_restore = _last(events, "commit", sid, site), _last(events, "restore", sid)
        if t_commit is None:
            bad.append(("I1_ActiveWithoutCommit", site, sid))
        elif t_restore is not None and t_commit < t_restore:
            bad.append(("I3_StaleActiveAfterRestore", site, sid, t_commit, t_restore))
    return bad

def veto_preserved(rows, events):
    bad = []
    for (site, sid), r in rows.items():
        t_rv = _last(events, "local_revoke", sid, site)
        if t_rv is None:
            continue
        t_rs = _last(events, "local_restore", sid, site)
        if (t_rs is None or t_rs < t_rv) and (r["state"], r["origin"]) != ("revoked", "local"):
            bad.append(("I3_VetoLost", site, sid, r["state"], r["origin"]))
    return bad

def confinement(rows, events):
    return [("I2_LocalOriginWithoutLocalRevoke", site, sid) for (site, sid), r in rows.items()
            if r["origin"] == "local" and _last(events, "local_revoke", sid, site) is None]

def all_checks(rows, scores, pending, events):
    return (caught_up_is_coherent(rows, scores) + no_transient_left(rows) + export_safe(rows, scores, pending)
            + no_active_without_commit_after_restore(rows, events) + veto_preserved(rows, events)
            + confinement(rows, events))
```

Formati:
- `rows = {(site, score_id): {"state", "origin", "last_applied_seq"}}` (chiave assente = 404);
- `scores = {score_id: {"status", "fanout_seq"}}`;
- `pending = {(site, score_id): n}`;
- `events = [{"t", "op", "site", "score_id", "status"}]`, con `op ∈ {commit, local_revoke,
  local_restore, dispute, restore}`.

Test minimo (eseguito):

```python
S = {7: {"status": "active", "fanout_seq": 2}}
def row(state, la=2, origin=None): return {"state": state, "origin": origin, "last_applied_seq": la}

def test_clean_trial_has_no_violation():
    rows = {(0, 7): row("active"), (1, 7): row("monitor-only"), (3, 7): row("revoked", origin="local")}
    ev = [{"t": 1, "op": "dispute", "site": None, "score_id": 7, "status": 200},
          {"t": 2, "op": "restore", "site": None, "score_id": 7, "status": 200},
          {"t": 3, "op": "commit", "site": 0, "score_id": 7, "status": 200},
          {"t": 0.5, "op": "local_revoke", "site": 3, "score_id": 7, "status": 200}]
    assert all_checks(rows, S, {}, ev) == []

def test_stale_commit_is_caught():          # commit before the restore, Active after it (sez. 1, riga 5)
    ev = [{"t": 1, "op": "commit", "site": 0, "score_id": 7, "status": 200},
          {"t": 2, "op": "restore", "site": None, "score_id": 7, "status": 200}]
    assert no_active_without_commit_after_restore({(0, 7): row("active")}, ev)[0][0] == "I3_StaleActiveAfterRestore"

def test_monitor_only_caught_up_during_episode_is_caught():   # sez. 1, riga 3
    assert caught_up_is_coherent({(0, 7): row("monitor-only", la=3)},
                                 {7: {"status": "disputed", "fanout_seq": 3}})[0][0] == "CaughtUpIsCoherent"

def test_other_checks():
    sc = {7: {"status": "disputed", "fanout_seq": 1}}
    assert export_safe({(0, 7): row("active", la=0)}, sc, {(0, 7): 0}) == [("ExportSafe", 0, 7)]
    assert export_safe({(0, 7): row("active", la=0)}, sc, {(0, 7): 1}) == []
    assert no_transient_left({(0, 7): row("committing")}) == [("TransientLeft", 0, 7, "committing")]
    ev = [{"t": 1, "op": "local_revoke", "site": 0, "score_id": 7, "status": 200}]
    assert veto_preserved({(0, 7): row("monitor-only")}, ev)[0][0] == "I3_VetoLost"
    assert confinement({(1, 7): row("revoked", origin="local")}, ev)[0][0] == "I2_LocalOriginWithoutLocalRevoke"
```

**Limiti (letto):**
- I1 e I2 sono controllati solo **a fine prova**, non a ogni passo.
- La versione "a ogni passo" esiste solo in-process, nel test differenziale (sez. 7).
- ExportSafe vale solo se, al momento della lettura, il sito è raggiungibile e la sua coda è vuota.
- Gli istanti di commit e restore vengono da clock diversi se il driver e l'evidence non condividono
  l'orologio. Usare il clock del driver per entrambi: il driver registra quando riceve il 200.

## 6. Proposta di blocco "costo della correzione" (non eseguito)

**Scopo:** misurare quanto costano a `/query` e `/commit` le due letture e il lock della
correzione.

**Arm (codice).**
- **A** = S0 (`0501b383…`).
- **B** = S (`5599f53b…`).
- Fra A e B, oltre alle correzioni, ci sono solo:
  - `75836c8`: pool keep-alive e timeout del ping, solo con `DIB_DIST_FANOUT_KEEPALIVE=1`
    (letto con `git show 75836c8`);
  - il retry keep-alive (S:852-854).

  Con il keep-alive **spento** il percorso di `/query` e `/commit` differisce solo per FQ e FC.
- Raccomando come arm A più pulito **`dc3dd20^`** (`a6bb1d22…`): differisce da B solo per le
  correzioni e per le 3 righe keep-alive (eseguito: confronto testuale, sez. 2).

**Ipotesi** (da scrivere in un audit di pre-registrazione **prima** del lancio). Sia R_se l'RTT
sito→evidence misurato nello stesso blocco:
- **H-C1 (`/query`, fatto nuovo, nessun reconcile in corso):** la mediana di B − A è
  ≈ 1 · R_se + Δ_db, con Δ_db = due transazioni SQLite in più.
  - **Falsificata se** l'IC bootstrap 95 % della differenza delle mediane è sotto 0,5 · R_se o
    sopra 1,5 · R_se + 5 ms.
  - Per `lan`, dove R_se < 1 ms: falsificata se il limite superiore dell'IC supera 10 ms.
- **H-C2 (`/commit`):** la mediana di B − A è ≈ 1 · R_se + Δ_db. Stesso criterio di falsificazione.
- **H-C3 (ritiro invariato):** la latenza `/dispute` → P-log non cambia fra A e B (quorum 1,
  keep-alive spento): l'IC della differenza della mediana dell'ultimo sito include 0 o è entro
  ±15 %.
  - È lo stesso criterio di H-R1b dell'audit 88: si può **riusare R1** invece di rimisurarlo.
- **H-C4 (descrittivo, D2):** latenza di `/query` mentre il trigger di reconcile è attivo (T = 5)
  contro trigger spento, solo arm B. Si riporta la coda (p95, p99), senza soglia.

**Profili:** `lan`, `wan`, `degraded`, gli stessi di R e del watcher/applicatore netem dei blocchi
B1. Si misura R_se nello stesso blocco con `measure_rtt_ms` (R:615-622).

**Disegno.**
- **Stesso nodo, stessa sessione.** A e B sono due alberi `git archive` con `sha256sum -c` (come
  `tree-dc3dd20` dell'audit 88), lanciati **in alternanza** A B A B …, per non confondere la
  deriva del nodo con l'effetto.
- Nessun confronto con misure di altre macchine o giorni.
- Per profilo:
  - **≥ 10 ripetizioni** per arm (regola CLAUDE.md);
  - ogni ripetizione: 200 coppie `/query` + `/commit` su fatti nuovi, un fatto per coppia, dal
    driver nel namespace root come in R;
  - intervalli bootstrap (10 000 ricampionamenti) della differenza di mediana e p95, ricampionando
    **le ripetizioni**, non le singole operazioni.
- Seed, versione di Python, hardware, hash degli alberi e T nel manifest.
- **Esclusioni** pre-dichiarate: risposta ≠ 200, oppure `applied` falso, oppure `ClientTimeout`.
  Si contano per arm: un tasso più alto in B è esso stesso un risultato (D5).

**Stima di durata (NON VERIFICATA):** 3 profili × 2 arm × 10 ripetizioni × 200 coppie, con
`degraded` a ~1-2 s per coppia nell'arm B, è dell'ordine di 3-5 h di nodo, più il setup.

## 7. Workload ai bordi: il generatore del test differenziale

**Dove (letto):** `code/tests/tests/test_distributed_fsm_differential.py`.
- Eventi a :77: `stage, commit, local_revoke, local_restore, dispute, restore, down, up, reconcile`.
- Generatore uniforme: seed 0-39 (:75), 25 passi (:76).
- Generatore pesato: pesi `(3, 3, 2, 1, 2, 2, 1, 1, 2)` nello stesso ordine (:79), seed 100-119
  (:80), 40 passi (:81).
- Scelta dell'evento a :219: `rng.choice(EVENTS)` oppure `rng.choices(EVENTS, weights=WEIGHTS)[0]`,
  poi `s = rng.randrange(3)`, `f = rng.choice(FACTS)`, `r = rng.randrange(3)`, con
  `rng = random.Random(seed)`.
- 3 siti (:73), 2 fatti (:74).
- Il file gira solo con `DIB_FSM_DIFF=1` (:83-85), circa 5 min.
- In-process controlla I1, I2, I3, export e convergenza **a ogni passo**, più un oracolo.

**Esiti eseguiti** (in-process, su S0, audit 64 sez. 2):
- uniforme: nessuna violazione;
- pesato: nessuna violazione, con restore applicati mentre un sito aveva un veto locale 6,
  dispute con un sito giù 50, reconcile che cambiano un record 10, commit riusciti 21.

Con il generatore uniforme il caso "restore con veto locale" capitava 1 volta su 1.000 passi:
**usare i pesi**.

**Non eseguito su `dc3dd20`.** La suite dell'altra sessione ha 7 skipped, cioè questo file non è
girato. Prima di riusarlo, lanciare
`cd code && DIB_FSM_DIFF=1 python3 -m pytest tests/tests/test_distributed_fsm_differential.py -q`
sul codice corretto. L'oracolo modella la semantica sequenziale vecchia di `/query` e `/commit`; con
eventi sequenziali dovrebbe coincidere, ma NON VERIFICATO.

**Come riusarlo in un driver reale (proposta).**
- Copiare solo la scelta degli eventi (:219 più le tre `randrange`/`choice`), con gli stessi seed e
  pesi, e mappare ogni evento su una chiamata HTTP:
  - `stage` → `POST /query`;
  - `commit` → `POST /commit`;
  - `local_revoke`, `local_restore` → le rotte omonime;
  - `dispute` → `POST /dispute` con `site_id = site-r`;
  - `restore` → `POST /restore`;
  - `reconcile` → `POST /reconcile`;
  - `down`/`up` → netem 100 % loss verso il sito, oppure `docker kill`/`start`, da dichiarare.
- A fine sequenza: up di tutti, `/reconcile` di tutti, poi `all_checks` della sez. 5.
- **Limite:** il generatore è **sequenziale**. Non esercita le finestre fra lettura e scrittura
  (b3, sez. 1 righe 2-5), che richiedono richieste concorrenti. Per esercitarle servono due flussi
  concorrenti sullo stesso fatto (ad esempio `/commit` e un episodio dispute+restore lanciati
  insieme). L'esito non è più deterministico: va letto con gli invarianti della sez. 5, non con un
  oracolo.

## 8. Decisioni che spettano all'utente

| # | Decisione | Raccomandazione | Costo stimato (ore, NON VERIFICATO) |
|---|---|---|---|
| 1 | D1: pulizia `staging`/`committing` all'avvio del sito | **Sì, prima del rerun di B2k** (B2k uccide un sito). Per R1 (B1 degraded, nessun kill) non serve | 1,5 (codice + test + nuovo hash) |
| 2 | D2: lock di `/query` con timeout e 503 | **Sì**, prima di benchmark che usano `/query`; per R1 basta contare le esclusioni di setup | 1 |
| 3 | D5: controllo di stato e `applied` nel setup dei driver (R, testbed) | **Sì, prima di R2 e successivi**: senza, un episodio può partire con siti non Active senza che lo si sappia | 0,5-1 (più il nuovo hash di R) |
| 4 | D3: 404 contro 409 su `/local_revoke` | Dichiarare | 0,2 |
| 5 | D4: indice UNIQUE sulla tupla | Dichiarare ora; implementare con l'epoch (audit 65) | 0,2 ora; ~3 con l'epoch |
| 6 | Run TLC v6 con MaxLoss 1 (consegne perse) | Utile per il paper, ma solo se c'è tempo di nodo libero; costo ignoto | 1-4 (stima molto incerta) |
| 7 | Blocco "costo della correzione" (sez. 6) | **Sì**: senza, il paper non può dire quanto costa la correzione | 3-5 di nodo + 1 di analisi |
| 8 | Invarianti di fine prova negli `analyze_*` (sez. 5) | **Sì**: rende B2k e i rerun controllabili oltre lo stato finale `monitor-only` | 1 |
| 9 | Pagine del paper (14 contro 13, branch `tnsm-fsm-paper`) | Decidere con il supervisor; la versione corta è nell'audit 68 | 0,5 |
| 10 | Rinumerare i miei audit 63-68 (collidono con 63-64 dell'altra sessione) al merge | Sì, in un solo commit | 0,5 |

## 9. Esperimento → cosa va riletto dopo le correzioni

Percorsi cambiati da `dc3dd20` (letto):
- `/query` (S:499-549), `/commit` (S:552-585), `/local_revoke` (S:587-608), `/local_restore`
  (S:620-625);
- `/dispute` solo con quorum 2 (S:977-980);
- consegna del fan-out solo con keep-alive (S:852-854).

**Non** cambiati: `_apply_fanout_row` (S:473-496), `_fan_out`/outbox, `/restore`, `/pending`,
`/reconcile`, `/export_mud`.

| Esperimento | Toccato? | Perché | Riga che lo esercita |
|---|---|---|---|
| **B1** (`run.py b1`, `episode_b1`) | **Setup sì, misura no** (con quorum 1 e keep-alive spento) | Il setup chiama `/query` e `/commit` (doppia lettura, lock, nuove risposte non controllate: D2, D5). La misura è POST `/dispute` → fan-out → P-log, percorso invariato. **Con keep-alive acceso la misura è toccata** dal retry S:852-854: le consegne perse per `RuntimeError` ora ritentano | setup R:632-633 (da R:652); misura R:658, P-log R:673-679 |
| **B5** (audit 56: B1 a `lan`/`degraded`, albero `244f1d0`) | Come B1 | Stesso codice di driver. Attenzione: B5 girava su `244f1d0`, **precedente** a `6e6d352` (default `FANOUT_CONCURRENCY` e altro diversi) | R:632-633, :658 |
| **B2k** (`trial_b2kill`) | **Sì** | Setup `/query` + `/commit` (R:712-713) con D2 e D5; D1 se un setup resta in volo al `kill` (R:714); 3 eventi per fatto (R:720-724), sopra il limite di 2 del modello. La lettura di `final_states` (R:757-759) va estesa agli stati transitori e agli invarianti della sez. 5 | R:712-714, :720-724, :757-759 |
| **M8** (firma MUD con `openssl cms`, audit 58) | **No** | Non usa il servizio: firma e verifica di documenti MUD. `/export_mud` non è cambiato | — |
| **Testbed** (`experiments_tnsm/netns_testbed/testbed.py`, audit 75/81) | **Setup sì, misura no** | Setup `/query` + `/commit` con 4 tentativi e controllo dello stato 200, ma non di `applied` (`testbed.py:142-151`). La misura (istante `disputed` nei DB, letto in polling) passa da `/dispute` (`testbed.py:186`) e `/apply_fanout`, invariati con quorum 1 | `testbed.py:145-146`, :186 |
| **Replica nei container** (audit 84 `run_node_v4` = testbed in Docker; audit 86 `deploy_run` = R `b1 degraded`) | Come testbed (84) e come B1 (86) | Stessi percorsi. Il rerun R1 (audit 88) è proprio il B1 dell'audit 86 sul codice corretto | come sopra |
| **Offline** (`code/scripts/offline_veto_reconciliation.py`) | **Sì** | Usa tutte le rotte cambiate: `/query` + `/commit` (:92-93), `/local_revoke` (:95, ora senza evidence), `/local_restore` (:127, ora con guardia di seq), `/commit` bloccato (:125) e di nuovo `/commit` (:131); dispute e restore con quorum 1 (:103-105); asserzioni sul numero di eventi riconciliati (:113, :120). Per lettura del codice l'esito atteso è invariato, ma **NON eseguito da me**: va rieseguito (è locale, pochi secondi, scrive solo `--output`, :159, :165) | :92-131 |

## Cose che ho dovuto supporre
- Che "testbed" sia `experiments_tnsm/netns_testbed/testbed.py` e "replica nei container" siano
  gli audit 84 (`run_node_v4`) e 86 (`deploy_run`). L'ho dedotto dalle intestazioni degli audit;
  non ho letto i loro manifest.
- Che R su `tnsm-fixes` sia quella usata per il rerun. Ho letto la versione della worktree
  `DIB_tnsm_fixes` (sha256 prefisso `9040c807e11e801c`).
- Che nei blocchi di R il quorum sia 1. Né R né `generate_compose.py` impostano
  `DIB_DIST_SUSPENSION_QUORUM` (grep); il default è 1 (S:127). Non ho letto i manifest dei run per
  confermarlo sul nodo.
- Che il keep-alive sia spento nei blocchi R1 come dichiara l'audit 88:6 (branch
  `tnsm-driver-retry`). Non ho letto i manifest di R1.
- Le stime in ore e la durata del blocco della sez. 6 non sono misurate.
