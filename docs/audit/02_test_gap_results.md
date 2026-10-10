# Audit 02 — Chiusura dei buchi B4–B9 e verifica di D12 (parte B)

Data: 2026-10-10. Repo `/root/Desktop/DIB_clean`, branch `tests-gap-closure`. Gli ID B*/D* vengono da `/root/Desktop/DIB_reframe/docs/audit/01_tracciabilita.md` (tabelle §2.4 e §4). Python 3.10.13, pytest 9.0.2, `timeout 300` su ogni esecuzione (`pytest-timeout` non installato).

**Esito in una riga:** 53 test aggiunti; suite completa **329 passed, 5 failed** (prima: 281 passed). I 5 fallimenti sono risultati, non errori di harness: 4 confermano D12 (compresa un'esposizione di sicurezza) e 1 mostra che una terza dispute dopo la revoca incrementa `score.version`. Nessuna asserzione è stata indebolita e nessun codice di produzione è stato toccato (`git diff v43-import -- code/src formal claims.json` = 0 righe).

## 0. Metodo e pre-registrazione

- Un commit per file di test, **prima** di eseguirli: `433e27a` (registry), `0e49ae4` (distribuito + `_dist_harness.py`), `1e5d9ec` (D12). Le ipotesi sono nei docstring dei moduli.
- Esecuzione dopo i tre commit, un file alla volta. Nessun file di test è stato modificato dopo l'esecuzione.
- Tre script usa-e-getta nello scratchpad (non nella repo), non ipotesi registrate: uno smoke dell'harness (stage + dispute, eseguito prima di committare il file del distribuito), una sonda di B8 (stampa `score.version` e `negative_attestations` prima/dopo la terza dispute) e una sonda dei controlli negativi (verifica che falliscano per il motivo giusto).
- Harness (`code/tests/tests/_dist_harness.py`): ogni istanza di `distributed/service.py` è caricata con `importlib` sotto nome unico, con env impostato da `monkeypatch` e SQLite in `tmp_path`; `httpx.get`/`httpx.post` (funzioni di modulo, `DIST:137,259,269,362`) sono sostituite da un router che inoltra a `TestClient`. Nessun socket, nessun Docker. Hook one-shot disarmato prima dell'esecuzione; tetto di 400 chiamate per test.
- Controlli negativi: copia del sorgente in `tmp_path` con sostituzione di testo (ogni ancora deve comparire una sola volta, altrimenti il test fallisce).

## 1. Registry — `test_registry_lifecycle_gaps.py` (17 test, 16 passed, 1 failed)

| Buco | Test | Esito |
|---|---|---|
| B5 | `test_query_after_open_dispute_returns_none` | passed (con 1 e 2 voti `query_score` dà `None` e non crea record; dopo `restore_score` crea MonitorOnly) |
| B5 / D15 | `test_query_existing_record_during_dispute_returns_none_characterization` | passed (`services.py:439`: `None` anche con record esistente; il paper dice "returns its existing decision") |
| B6 | `test_commit_from_disputed_raises`, `…_revoked_dispute_raises`, `…_local_revoked_raises` | passed (stato invariato) |
| B6 / D4 | `test_commit_after_rescore_below_threshold_raises_characterization` | passed (commit rifiutato con `accepted=False`, `services.py:471-475`; il modello lo permetterebbe) |
| B7 | `test_export_excludes_disputed_record`, `…_revoked_dispute_record_until_fresh_commit`, `…_local_revoked_record` | passed (0 ACE in ogni stato; dopo restore ancora 0; dopo nuovo commit 1) |
| B7 / controllo negativo | `test_negative_control_export_admitting_disputed` | passed = lo scenario fallisce sulla copia mutata (ammette Disputed). Verificato che fallisca all'asserzione `exported_ace_count == 0` (`test_registry_lifecycle_gaps.py:211`), non per altro |
| B8 | `test_repeated_dispute_from_same_site_after_revoke_is_noop` | passed; `negative_attestations` 2 → 2 |
| **B8** | `test_third_dispute_after_revoke_adds_no_transition` | **FAILED** (vedi §1.1) |
| B9 | `test_local_restore_on_non_revoked_raises` (MonitorOnly e Active), `test_local_restore_without_local_record_returns_none`, `test_query_on_existing_record_is_noop`, `test_restore_after_restore_raises` | passed |
| D5 | `test_restore_score_restores_score_values_characterization` | passed (il rescore durante la dispute viene applicato, poi scartato dal restore; `accepted` torna a True) |

Esclusi perché già coperti: `local_revoke` senza record e doppio `local_revoke` (`test_registry.py:382`), restore su fact Active mai disputato (`test_registry.py:571`).

### 1.1 B8: la terza dispute dopo la revoca (fallimento)

Sonda sullo stesso scenario (site-a committato, dispute da site-b e site-c → Revoked, poi dispute da site-d):

| | prima | dopo |
|---|---|---|
| `score.status`, `disputed_by` | revoked, site-b | revoked, site-b |
| storia dello score | `upsert, dispute, revoke` | identica |
| decisione di site-a | revoked, versione 4, eventi `query, operator_commit, dispute, revoke` | identica |
| `negative_attestations` (registrato, non asserito) | 2 | **3** |
| **`score.version`** | 3 | **4** |

L'unica differenza che fa fallire l'asserzione è `score.version` (indice 2 dello snapshot). Non nasce un evento né uno stato nuovo: l'incremento viene dall'aggiornamento di `negative_attestations` (`SVC:644-646`, `_upsert_attestation` + `_count_attestations`) che modifica la riga `Score` e quindi fa avanzare il token di concorrenza ottimistica (`db.py:117-124`). Conseguenza: `score.version` (4) non coincide più con l'ultima versione in `get_score_history` (3). Una dispute dalla stessa coppia di siti (test passed) non cambia nulla.
Questo non viola l'ipotesi "nessuna transizione" (stato, `disputed_by` e storie sono invariati) ma l'asserzione scritta includeva `version`. Il test resta rosso come registrato; se vuoi, lo si ridefinisce (escludendo `version` e asserendo la discontinuità separatamente) in un commit successivo.

## 2. Distribuito in-process — `test_distributed_service_inproc.py` (22 test, 22 passed)

Copre B4: fan-out (`DIST:356-382,147-170`), retry (3 tentativi), outbox, reconcile, `origin`, comando/commit, export.

| Area | Esito |
|---|---|
| fan-out | dispute su tutti i siti con record, 404 su `/state` dove non c'è riga; seconda segnalazione distinta → `revoked/fanout`; terza → `applied: false`, seq invariato |
| D8 (characterization) | passed. Con `SUSPENSION_QUORUM=2`: 1ª segnalazione no-op, 2ª sospende (`disputed_by = rep-b`), `rep-b` di nuovo no-op, **`rep-a` (già contata) revoca**. Quindi bastano **due** siti distinti: l'affermazione di D8 in `01_tracciabilita.md` ("la revoca richiede un terzo sito distinto") non regge sul codice (`DIST:450`: confronta solo con `disputed_by`) |
| D11 (characterization) | passed: con siti 1 e 2 giù, `/apply_fanout` = 1 chiamata a site0 + 3 a site1 + 3 a site2, in questo ordine; `timeout=1.0` in tutte; nessuna chiamata a `time.sleep`; la risposta di `/dispute` arriva dopo il giro e le righe sono in outbox |
| retry | consegna al 3º tentativo → outbox vuoto; 3 fallimenti → una riga con seq/event/target corretti |
| outbox | per (sito, fatto) una sola riga col seq più alto (`seq=3 restore`); un `_fan_out` con seq inferiore non sovrascrive |
| reconcile | applica e fa ack; senza pendenti nessuna chiamata di ack; con k=1 e k=3 episodi saltati resta **una** riga (`seq=3k`, `restore`) e il sito va a `monitor-only`; un secondo reconcile non fa nulla; seq ≤ `last_applied_seq` è un no-op |
| D6 (`_spec`) | passed: sito Active offline per dispute→restore → `monitor-only` dopo il reconcile, 0 ACE (semantica voluta; il modello TLA+ non la verifica) |
| origin | il veto locale resiste a dispute, revoke e restore globali e a un restore pendente al reconcile (solo `last_applied_seq` avanza); `local_restore` → 409 con episodio aperto e 409 "not locally revoked" su `origin == fanout`; `local_revoke` consentito su `revoked/fanout`; `local_restore` consentito dopo restore globale |
| comando/export | `/commit` 409 senza record, con evidence disputed, con `accepted=0` o se già Active; `/export_mud`: 1 ACE dopo commit, 0 dopo dispute |
| controllo negativo (analogo m6) | passed = lo scenario del veto locale fallisce sulla copia senza le due guardie di origine; fallisce a `c.state(1, sid) == {revoked, local, 3}` |

## 3. D12 — `test_distributed_d12_reproducer.py` (14 test, 10 passed, 4 failed)

**D12 è confermato**: l'ack `DELETE FROM pending_fanout WHERE site_id=?` (`DIST:495`) cancella eventi che arrivano tra `GET /pending` (`DIST:259`) e l'ack (`DIST:269`) quando la loro consegna diretta fallisce. H1 non è falsificata in nessuno dei tre scenari.

### 3.1 Sequenze e stato finale

**Scenario 1 — restore perso** (sito 1, fatto X)
1. Sito 1 giù: dispute(rep-a) seq1, dispute(rep-b) seq2 → outbox `(site-1, X, seq 2, revoke)`.
2. Sito 1 rientra, `POST /reconcile`: `GET /pending` restituisce `[seq 2]`.
3. Hook (tra GET e ack): sito 1 irraggiungibile, `POST /restore` → seq3, 3 tentativi falliti verso site-1 (verificato, 3 chiamate con `seq == 3`) → riga seq3 in outbox.
4. Il sito applica seq2 (`revoked/fanout`), poi l'ack cancella anche la riga seq3.
Stato finale: evidence `active`, `fanout_seq 3`; sito `revoked`, origin `fanout`, `last_applied_seq 2`; outbox vuoto. **Il sito non converge e non ha più nulla in coda.**

**Scenario 2 — dispute persa, fatto singolo** (sito 1 Active, pendente `restore seq2`)
Hook: `dispute(rep-c)` seq3 con consegna fallita. Dopo reconcile: evidence `disputed`, `fanout_seq 3`; sito `monitor-only` (ha applicato il restore, D6), `last_applied_seq 2`, outbox vuoto. Non converge (lo stato locale è meno permissivo di quello globale: non è esportabile).

**Scenario 3 — revoke perso con pendente su un altro fatto** (X, Y; sito 1 Active su X)
1. Sito 1 giù: dispute(Y) → outbox `(site-1, Y, seq 1)`.
2. Sito 1 rientra, `/reconcile`: `GET /pending` = `[Y]`.
3. Hook: sito 1 irraggiungibile, dispute(X, rep-a) e dispute(X, rep-b) → X `revoked`, seq2; 6 tentativi falliti verso site-1 (verificato); righe X in outbox.
4. Il sito applica Y, l'ack cancella **anche le righe di X** (l'ack è per sito, non per fatto).
Stato finale: evidence X `revoked`, `fanout_seq 2`; sito 1 X `active`, `last_applied_seq 0`, outbox vuoto; **`/export_mud` del sito 1 contiene 1 ACE**.

### 3.2 Gravità

| Evento perso | Scenario | Effetto osservato | Classe |
|---|---|---|---|
| `restore` | 1 | sito bloccato in `revoked/fanout` con evidence Active; `/local_restore` dà **409 "not locally revoked"** (`DIST:239-240`, test passed) | **disponibilità** |
| `dispute` | 2 | sito `monitor-only`; `/commit` → **409** (`DIST:196-197`) e 0 ACE (test `…_no_exposure` passed) | nessuna esposizione (disponibilità/consistenza) |
| `revoke` | 3 | sito Active su X con evidence Revoked, **1 ACE esportato** (test `…_no_exposure` failed) | **sicurezza** (viola l'intento di `DisputeSuspendsEverywhere`) |

La finestra dura fino al prossimo evento globale su quel fatto (test `test_d12_recovers_on_next_global_event` passed: una nuova dispute seq4 consegnata riporta il sito a `last_applied_seq 4`, `disputed`). Non ho testato altri rimedi dell'operatore; dalla lettura del codice un `local_revoke` seguito da `local_restore` sarebbe possibile (`DIST:216-219`, `229-247`) ma non l'ho verificato.

### 3.3 Controlli

| Test | Esito | Significato |
|---|---|---|
| `test_d12_control_direct_delivery_converges` | passed | se la consegna diretta nella finestra riesce, nessuna perdita (H2): il sito arriva a `last_applied_seq 3` |
| `test_d12_stale_pending_seq2_after_direct_seq3_does_not_regress` (B3) | passed | l'item seq2 applicato dopo seq3 non regredisce lo stato (`monitor-only`, seq 3), guardia `DIST:155-156` |
| `test_d12_control_no_interleaving_converges` | passed | senza evento nella finestra il reconcile converge e svuota l'outbox |
| `test_negative_control_ack_with_seq_bound_converges` | passed | sulla **copia** con ack `seq <= max seq letto` la riga seq3 sopravvive (`pending == [3]`) e un secondo reconcile porta il sito a `monitor-only`, seq 3. Il bug è quindi causato dall'ack senza filtro. Limite: il vincolo è sul massimo seq dell'intero elenco, non per fatto; basta per questo reproducer, ma un item di un altro fatto con seq inferiore potrebbe ancora essere cancellato |

Nessuna correzione è stata applicata. Il fix da discutere (non toccato): ack con filtro per `(score_id, seq letto)` oppure per `seq <= max letto`.

## 4. Controlli sulla coerenza con il piano e scostamenti

- Il piano prevedeva per D12 una "variante non sicura" a fatto singolo; l'ho verificata (Scenario 2) e **non** produce esposizione. L'esposizione compare solo con l'item pendente di un altro fatto (Scenario 3), previsto dal piano come variante B1 estesa.
- Il piano riportava D8 come "terzo sito distinto": il test lo ha smentito (§2). D8 in `01_tracciabilita.md` va corretto.
- Il test `test_third_dispute_after_revoke_adds_no_transition` fallisce per un campo (`version`) che includevo nello snapshot ma che non era nell'ipotesi scritta in prosa; non l'ho modificato.

## 5. Mappa buchi → esito

| Buco | Stato dopo questo lavoro |
|---|---|
| B4 | coperto da 22 test in-process senza Docker; D8 corretto, D11 e D6 caratterizzati |
| B5 | coperto (2 test) |
| B6 | coperto (4 test); D4 caratterizzato |
| B7 | coperto (3 test + controllo negativo) |
| B8 | coperto con **1 test rosso** (`score.version`, §1.1) e 1 verde |
| B9 | coperto (4 test, esclusi i duplicati) |
| D12 | **confermato**, gravità: restore perso = disponibilità, revoke perso con pendente su altro fatto = sicurezza |
| B10 (mutation testing sul codice) | non chiuso; aggiunti 2 controlli negativi sul codice (export con Disputed, guardie di origine) e 1 sull'ack (D12) |

## 6. Decisioni per te

1. D12: correggere l'ack? (richiede di toccare `distributed/service.py`; non fatto).
2. B8: ridefinire il test della terza dispute (escludere `score.version`, documentare la discontinuità versione/storia) o lasciarlo rosso come segnalazione.
3. Correggere D8 in `01_tracciabilita.md` (copia in `DIB_reframe`, non toccata da me).
4. Se vuoi che l'ack per sito sia descritto nel paper tra i limiti del prototipo distribuito.
