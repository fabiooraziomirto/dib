# Audit 126 — Correzione del difetto G3 (`target_state` applicato senza controllo): decisione, verifica, rerun

Data 2026-10-13. Decisione dell'utente (risposta in sessione, 2026-10-13 ~09:27 UTC): **applicare la patch** di audit 124 §1.

## Modifica (unica modifica a `code/src` di questo lavoro)
`code/src/dib/registry/distributed/service.py`: in `_apply_fanout_row` un evento il cui `target_state` non è quello del suo tipo (dispute→disputed, revoke→revoked, restore→monitor-only, Tabella II) viene ignorato. 7 righe; nessun endpoint, nessun cambiamento di architettura o dei percorsi validi. sha256 `3ffa57ee…` → **`83d8c99a063656904d227030f28e4b207a2f56939c424b17a21d866c62e0e0ab`**.
Motivo: senza la guardia, un'identità `evidence` (o chiunque senza mTLS) può portare un record ad Active con un `restore`/`active`, contro G3 (`docs/main_10p.tex:411`); dimostrato da `experiments_tnsm/evidence_trust_20261013/test_target_state_trust.py`.

## Verifica (worktree `tnsm-g3fix`, 09:27–09:29 UTC, con `nice -n 19` durante la campagna gateway LAN, episodi ~48–50: la finestra è registrata per eventuali anomalie di tempo)
- Suite `code/tests`: 507 passed, 7 skipped, 8 xfailed (identica alla baseline di audit 119).
- `test_target_state_trust.py`: 2 passed sul nuovo hash; sul vecchio hash resta 1 passed + 1 xfailed (strict, condizionato all'hash).
- Test esperimenti legati a `service.py`: `m67_retraction/test_night.py` 11, `test_run_image_check.py` 3, `netns_testbed/test_mtls_mode.py` 5, `node_session_20261011/test_diag_setup500.py` 4: tutti passed.

## Effetto sulle evidenze
Sugli input validi il comportamento è identico (la guardia scatta solo per coppie incoerenti, che né il servizio né i harness inviano). Comunque, per la regola di provenienza (audit 119 §2):
| Evidenza | Servizio | Azione |
|---|---|---|
| Campagne gateway LAN/WAN/degraded (audit 121) | `3ffa57ee` (in corso, non interrotte) | restano evidenza di `3ffa57ee`; **smoke** di 5 episodi per profilo su `83d8c99a` dopo il merge |
| Rerun ablation/offline veto (audit 120) | `3ffa57ee` | **rieseguire** su `83d8c99a` (secondi) |
| Sweep di scalabilità (audit 123) | — | parte direttamente su `83d8c99a` |
| B2k, R1e, R1f, banco netns | `3ffa57ee` o precedenti | non rieseguiti: il paper dichiara la versione misurata e che la guardia non tocca i percorsi validi |
Il merge in `tnsm-final-campaigns` avviene solo a campagne gateway finite (il loro harness ricostruisce le immagini dall'albero e ne verifica l'hash alla fine).

## Addendum 1 — pre-registrazione dello smoke gateway su `83d8c99a` (prima del lancio)
`gateway_bench.py` invariato, 5 episodi standard per profilo (lan, wan, degraded), finestra 15 s, mTLS, cartelle `experiments_tnsm/gateway_withdrawal_20261013/smoke_83d8c99a_{lan,wan,degraded}`. Criteri: hash `83d8c99a` negli 11 container all'inizio e alla fine; H-G1, H-G3, H-G4 e H-G5 valgono in 5/5 per profilo. Le mediane di t1 e t2 sono esplorative: la previsione è che stiano entro ±10 % dalle mediane di audit 122, perché la guardia non tocca i percorsi validi. Con 5 episodi non si stima nessuna coda. Subito dopo, in sequenza, parte lo sweep di audit 123 (`http`, poi `mtls`) su `83d8c99a`.
