# Audit 64 — Risultati dei test del FSM (race, evidence irraggiungibile, ≥ 3 siti; controllo differenziale)

Data: 2026-10-12. Branch `tnsm-fsm` (worktree `/root/Desktop/DIB_tnsm_fsm`). Specifica: audit 63.
S = `service.py` a `6e6d352` (sha256 `0501b383…3d42a64`), non modificato.
Ambiente: Python 3.10.13 (interprete di default), stessa macchina, pytest in-process (`_dist_harness.py`,
rete finta, `DIB_DIST_FANOUT_CONCURRENCY=1` fissato dal harness).

## 1. Test pre-registrati (obiettivo 2)

File: `code/tests/tests/test_distributed_fsm_races.py`. Pre-registrazione: commit `03986d4` (ipotesi
e previsioni nel docstring, nessuna esecuzione prima). Prima esecuzione: 6 failed, 8 passed in 2,17 s.

| Ipotesi | Previsione | Esito | Osservato |
|---|---|---|---|
| H-b3q-1 `/query` in corsa con una dispute non crea un MO durante l'episodio | rosso | **falsificata** | 200, `monitor-only`, `last_applied_seq=0`, evidence `fanout_seq=1` |
| H-b3q-2 una `/reconcile` ripara (disputed, seq = 1, commit 409, 0 ACE) | verde | confermata | |
| H-b3c-1 `/commit` in corsa con una dispute il cui fan-out non arriva non crea active | rosso | **falsificata** | 200, `active`, 1 ACE esportato, outbox con la dispute seq 1 |
| H-b3c-2 una `/reconcile` porta a disputed e 0 ACE | verde | confermata | |
| H-b3c-3 se il fan-out arriva prima, `/commit` è 409 | verde | confermata | |
| H-b3r-1 `/local_restore` in corsa con una dispute è rifiutato | rosso | **falsificata** | 200, `monitor-only`, `last_applied_seq=1` con evidence `disputed` |
| H-b3r-2 una `/reconcile` porta a disputed | rosso | **falsificata** | resta `monitor-only`, seq 1 (non riparato) |
| H-b3r-3 dopo la corsa commit 409 e 0 ACE | verde | confermata | |
| H-b4-1 `/local_revoke` riesce con l'evidence irraggiungibile | rosso | **falsificata** | `httpx.ConnectError` non gestita; record ancora `active`, 1 ACE |
| H-b4-2 `/local_restore` con evidence giù non si applica | verde | confermata | |
| H-b4-3 `/export_mud` con evidence giù esporta | verde | confermata | |
| H-b6-1 restore e dispute concorrenti su 3 siti convergono (disputed, seq 3, outbox vuote) | verde | confermata | 10/10 esecuzioni ripetute verdi (0,57-0,68 s ciascuna) |
| H-b6-2 (caratterizzazione) quorum 2: voto isolato persiste, restore 409 | verde | confermata | |
| H-a10 quorum 2: un votante della sospensione non conferma la revoca | rosso | **falsificata** | `site-0` conferma: `applied True`, `revoked` |

Tutte e sei le previsioni "rosso" e tutte e otto le previsioni "verde" si sono avverate.

Dopo l'esecuzione (regola Fase 2): i sei test falsificati restano con l'asserzione originale e sono
marcati `xfail(strict=True)` con il motivo; cinque test `*_characterization` fissano il comportamento
osservato (b3r-1 e b3r-2 condividono un test). File: 13 passed, 6 xfailed in 2,65 s. Suite intera
(`cd code && python3 -m pytest tests -q`): **476 passed, 6 xfailed in 35,0 s**.

### Lettura dei risultati
- **b3c è il più grave.** Con un sito che serve il proprio operatore ma non riceve il fan-out
  (partizione asimmetrica, a6), un commit che legge l'evidence prima della dispute e scrive dopo crea
  un'approvazione nuova *dopo* che la dispute è stata committata, ed esporta l'ACE finché il sito non
  riconcilia. È la precondizione di main_wip.tex:321 ("no dispute") violata. Con la formulazione di
  I3 (main_wip.tex:340, "at other sites upon reconciliation") l'esito è formalmente coperto, perché
  la /reconcile lo ritira (H-b3c-2), ma con `RECONCILE_INTERVAL=0` di default (S:143) la finestra non
  ha limite. Né M0 né MAE la rappresentano (audit 63 M-a, M-b).
- **b3r** lascia uno stato permanente fino al prossimo evento: il record è monitor-only per tutto
  l'episodio e l'anti-entropia non lo vede. Nessun export (H-b3r-3), quindi niente violazione di
  I1-I3 sull'export, ma la regola "local restore blocked while a dispute is open"
  (main_wip.tex:334) non vale sotto concorrenza.
- **b3q** è transitorio e riparabile (H-b3q-2), ma solo se una /reconcile parte.
- **b4**: il veto locale dipende dalla raggiungibilità dell'evidence. Divergenza codice-modello
  (MAE:264-271) e codice-paper (main_wip.tex:547).
- **a10**: con la tua decisione, il codice è da correggere (S:918 dovrebbe escludere tutti i
  votanti di `suspension_reports`, non solo `disputed_by`). Non corretto: serve il tuo OK e
  `service.py` è congelato per hash.

Le correzioni possibili (non applicate) sono in §3.

## 2. Controllo differenziale (obiettivo 3)

(compilato al passo P4)

## 3. Correzioni possibili (proposte, non implementate)
- b3q/b3c: nella transazione locale rileggere il seq: `/query` e `/commit` passano alla transazione
  il `fanout_seq` letto e la transazione rifiuta se un fan-out con seq maggiore è già stato
  applicato... ma nel caso b3c il fan-out non è mai arrivato al sito. L'unica correzione che chiude
  b3c senza coordinamento è una seconda lettura dell'evidence *dopo* il commit locale, con
  rollback (o stato disputed) se `fanout_seq` è cambiato: costo, un GET in più per commit.
- b3r: nella transazione di `/local_restore`, rifiutare se `last_applied_seq` è cambiato rispetto a
  prima della lettura dell'evidence (il fan-out della dispute lo avanza, S:487-490).
- b4: `local_revoke` non ha bisogno dell'evidence se lo `score_id` è ricavabile localmente dai
  campi `device_type, endpoint, protocol, port` di `local_decisions` (S:440-442).
- a10: in S:918 `req.site_id NOT IN (SELECT site_id FROM suspension_reports WHERE score_id=?)`
  quando Q=2.
