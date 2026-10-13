# Audit 112 — Risultati: modello TLA+ dell'autorizzazione mTLS (pre-registrazione: audit 111)

Data: 2026-10-12. Branch `tnsm-authz`. Modello `experiments_tnsm/tla_authz/AuthZ.tla` + `Rules.tla` (generato dal codice, `service.py` sha256 `0501b383…`).
Run: `run_tlc.sh <cfg> 2 2` (heap 2 GB, 2 worker, `nice 19`, in parallelo alla v8), TLC jar sha256 `237332bd…`, OpenJDK 17.0.19. Log in `logs/`, manifest `logs/manifest.tsv`
(orari in UTC). Tutti i run completati; nessun watchdog né OOM.

## 1. Esiti (tutti come pre-registrati, audit 111 sez. 3-5 e addendum sez. 8)
| cfg | Previsione | Esito | Stati distinti | Prof. | Durata |
|---|---|---|---|---|---|
| `b_P1L` | regge | **confermata** | 53.535 | 7 | 1 min 30 s |
| `b_P1L_r2` (2 revoche) | regge | **confermata** | 1.750.055 | 8 | 47 min |
| `b_P1S_single` | regge | **confermata** | 53.535 | 7 | 1 min 35 s |
| `b_P1G_atomic` | regge | **confermata** | 3.735 | 3 | 10 s |
| `b_P2` `b_P3` `b_P4` `b_P5` `b_P5b` `b_P6` | reggono | **confermate** (6 run) | 53.535 ciascuna | 7 | ~1 min 30 s ciascuna |
| `x_P1G_async` | violata | **violata** (come previsto) | 452 | 3 | 5 s |
| `x_P1S_multisan` | violata | **violata** (come previsto) | 5.002 | 3 | 5 s |
| `x_PD_design` | violata | **violata** (come previsto) | 63 | 3 | 5 s |
| `m1_nodeny` → P1_Local | violata | **violata** | 1.733 | 4 | 5 s |
| `m2_noownsite` → P2 | violata | **violata** | 293 | 3 | 5 s |
| `m3_memberrestore` → P4 | violata | **violata** | 91 | 3 | 5 s |
| `m4_payloadsite` → P5 | violata | **violata** | 79 | 3 | 5 s |
| `m5_fanoutany` → P3 | violata | **violata** | 39 | 3 | 5 s |
| `m6_openseed` → P6 | violata | **violata** | 805 | 3 | 5 s |
Gli stati dei mutanti e delle esplorative sono quelli al momento della violazione. Righe `No error has been found` / `is violated` / `distinct states found` / `depth`: vedere `logs/<cfg>.log`
(es. `b_P1L.log:30`, `m2_noownsite.log:28`). Il primo tentativo di `b_P1L` a `MaxRevokes=2`, fermato senza esito, è in `logs/b_P1L_r2_ABORTED_partial.log` (addendum 111 sez. 8).

**Non vacuità:** tutti e 6 i mutanti violano la proprietà corrispondente, quindi P1_Local, P2, P3, P4, P5, P6 non sono vacue nel modello.
**Esito per il paper:** nessun controesempio al design sulle proprietà base. Frase possibile: "le regole di autorizzazione (confinamento al proprio sito, fan-out solo dall'evidence, restore e seed solo
dall'amministratore, sito del certificato nelle dispute, nessun accesso senza identità mappata, denylist rispettata) sono verificate su un modello a stati finiti con 3 siti, con 6 mutanti
che le violano".

## 2. Controesempi attesi (cosa dicono davvero)
- **Revoca non immediata (`x_P1G_async`, 3 stati):** `Revoke(m1)` poi `Call(<<m1>>, site.health, s1)` accettata, perché la copia della denylist di `s1` non è stata ancora riletta. Vale per `master` ≠ copia del servizio. Con la
  denylist condivisa (`b_P1G_atomic`) regge. Quindi: la revoca ha effetto **alla prossima richiesta del servizio che ha riletto il file**; verso un servizio con file non ancora aggiornato resta valida fino alla scadenza del certificato
  (design 9.1 punto 5). Il modello non dice nulla sul tempo.
- **Certificato multi-SAN (`x_P1S_multisan`):** il certificato `[m2, m1]` con `m1` revocato è accettato come `m2` (`Identities.resolve`, `mtls.py:134-142`, torna il primo SAN mappato e non revocato). Rilevante solo se la CA
  emette certificati con più SAN; il design 3.1 ne prevede uno. Decisione per l'utente: dichiararlo come ipotesi (un SAN per certificato) o far fallire `resolve` se un SAN presentato è in denylist.
- **Codice più permissivo del design (`x_PD_design`, traccia: `m1` chiama `site.health` su `s1`):** confronto tabella-codice (`Rules.tla`) contro tabella-design 3.3 con Q1 (nessun caso in cui il codice ammetta meno):
  - D-b `/scores`, `/scores/by_id` (`service.py:849, 857`): il codice ammette anche `operator`; il design `member` e `consortium_admin`;
  - D-c `/attest`, `/dispute` (`_reporter`, `:871`): `member` e `operator`; il design `member`;
  - D-d `/health` del sito (`:725`): qualunque identità mappata (anche `member` di un altro sito o `evidence`); il design "proprio sito, `consortium_admin`". La risposta (`:731-735`) include `site_id` e `reconcile.last_error`.
  Nessuna delle tre viola le proprietà P1-P6: sono differenze di larghezza della regola, non di confinamento delle operazioni.

## 3. Cosa è verificato / cosa no
**Verificato (modello):** le 18 route hanno `_authorize` o `_reporter` come prima istruzione (`gen_rules.py`, 18/18); data la regola estratta dal codice, P1_Local, P2-P6 valgono per ogni certificato mono-SAN, ogni
endpoint, ogni servizio bersaglio, ogni argomento, con fino a 1 revoca (2 per P1_Local) e copie della denylist asincrone.
**Non verificato:** TLS (handshake, scadenza, CA: fuori ambito, design sez. 2); corpo degli handler oltre alla riga di autorizzazione (letto a mano); che `PeerCertH11Protocol` esponga davvero i SAN del
certificato verificato (coperto dai test di `test_mtls_peer_identity.py`, non dal modello); mtime con granularità insufficiente; tempo di propagazione della denylist; operatore umano e governance della CA;
registry single-node (fuori ambito, design 9 Q4); revoca come rimozione dalla denylist.

## 4. Decisioni per l'utente
1. Frase per il paper sulla revoca: "effetto alla prima richiesta dopo la rilettura del file; altrimenti entro la scadenza del certificato".
2. Multi-SAN: ipotesi dichiarata oppure modifica a `resolve` (non proposta qui; `code/src` non toccato).
3. D-b, D-c, D-d: allineare il design al codice (documentare `operator`) o stringere il codice. Non toccato.

## 5. Decisioni dell'utente (2026-10-13)
1. **Revoca:** il paper scrive il limite così com'è: la revoca ha effetto alla prima richiesta dopo la rilettura del file di identità da parte del servizio; verso un servizio con file non aggiornato vale fino alla scadenza del certificato. Non si scrive "revoca immediata".
2. **Multi-SAN:** si dichiara l'ipotesi "un SAN per certificato" (design 3.1, garantita dall'emissione della CA). `resolve` (`mtls.py:134-142`) non cambia; `code/src` non è toccato.
3. **D-b, D-c, D-d:** si aggiorna il design (tabella 3.3) per documentare il ruolo `operator` su `/scores`, `/scores/by_id`, `/attest`, `/dispute` e l'accesso di qualunque identità mappata a `/health` del sito; `service.py` non cambia. Resta aperta, se lo si ritiene sensibile, la sola `/health` del sito (espone `site_id` e `reconcile.last_error`, `service.py:731-735`): non decisa.
Nessuna modifica a `code/src`, `formal/`, `claims.json`, `results/`. L'aggiornamento della tabella di `13_mtls_design.md` non è ancora fatto (file di design: da fare su richiesta).
