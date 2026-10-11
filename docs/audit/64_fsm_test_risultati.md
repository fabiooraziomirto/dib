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

File: `code/tests/tests/test_distributed_fsm_differential.py`. Pre-registrazioni: `968121d` (H-D1..D4,
generatore uniforme, seed 0-39, 25 passi) e `890f4cb` (H-D5..D7, generatore pesato
`WEIGHTS=(3,3,2,1,2,2,1,1,2)`, seed 100-119, 40 passi, scritta dopo l'esito di H-D4 e prima di
eseguire D5-D7). 3 siti, 2 fatti, eventi sequenziali (le finestre b3 della sez. 1 non sono esercitate).
Controlli a ogni passo: I1, I2, I3-d, I3-r, I3-v, EXP (export ⇔ active, per fatto), ORACLE (oracolo
Python delle tabelle di audit 63, quorum 1) e, a fine sequenza, CONV (convergenza dopo up+reconcile).
Mutanti su copie di S: M1 = guardia di provenienza del restore (S:482) → `if False:`; M2 = target del
restore (S:948) → `DECISION_ACTIVE`.

| Ipotesi | Esito | Osservato |
|---|---|---|
| H-D1 codice reale, 40×25: nessuna violazione | confermata | 0 violazioni, 72,7 s |
| H-D2 M1 rilevato da I3-v | confermata, **di misura** | I3-v 1 (un solo seed: 32, passo 22, restore che porta il veto di site-1 a monitor-only), ORACLE 3; 72,5 s |
| H-D3 M2 rilevato da I1 | confermata | I1 9, ORACLE 52; 70,9 s |
| H-D4 non vacuità (≥5 restore con veto, ≥5 dispute con sito down, ≥5 reconcile che cambiano, ≥10 commit) | **falsificata** | restore con veto 1, reconcile che cambiano 3 (dispute con sito down 49, commit 200: 10) |
| H-D5 pesato, codice reale: nessuna violazione e soglie di H-D4 | confermata | 0 violazioni; restore con veto 6, dispute con sito down 50, reconcile che cambiano 10, commit 200: 21; 48,9 s |
| H-D6 pesato, M1 rilevato da I3-v in ≥ 3 seed | confermata | I3-v in 3 seed su 20: 107, 113, 119 (esattamente la soglia); 106,4 s |
| H-D7 pesato, M2 rilevato da I1 in ≥ 3 seed | confermata | I1 in 11 seed su 20: 100-103, 105, 109, 111, 115, 117-119; 170,8 s |

Conseguenze:
- Con il generatore uniforme il percorso "restore con veto locale presente" capitava una volta in
  1.000 passi: H-D1 da sola era quasi vuota per I3-v. D4 resta `xfail(strict=True)`; il risultato
  che conta è H-D5 + H-D6.
- Sulle sequenze sequenziali il codice coincide con l'oracolo a ogni passo: la specifica di audit 63
  sez. 1-2 descrive il comportamento osservato, salvo le finestre concorrenti della sez. 1 (b3), che
  questo generatore non produce.
- Il controllo copre a4 solo per sequenze senza concorrenza, 3 siti, 2 fatti, quorum 1, nessun
  errore dell'evidence. Non copre quorum 2, evidence irraggiungibile, crash.
- M1 resta il mutante rilevato più a fatica (3/20 seed pesati, 1/40 uniformi): il percorso
  "restore su un sito con veto locale" è raro anche con i pesi. Una conferma più robusta
  richiederebbe un generatore guidato (non pre-registrato qui).
- Rilancio di D2, D6, D7 per leggere i seed (stessi seed, stesso esito): 3 passed in 391,5 s.
- Durata: ~5 min per tutto il file (i tempi crescono durante la stessa sessione pytest: D7 170,8 s
  contro 48,9 s di D5 con lo stesso numero di passi; causa non indagata, probabilmente moduli caricati
  che restano in memoria). Per non superare il `timeout 300` della suite documentata il file gira
  solo con `DIB_FSM_DIFF=1`:
  `cd code && DIB_FSM_DIFF=1 python3 -m pytest tests/tests/test_distributed_fsm_differential.py -q`.
  Nella suite standard i 7 test risultano "skipped". Questa scelta è mia, da confermare.
- Primo tentativo di esecuzione dell'intero file con `timeout 300`: interrotto (exit 143), nessun
  esito; poi i test sono stati eseguiti uno alla volta (tempi sopra).

## 3. Correzioni possibili (proposte, non implementate)
- b3q: la transazione di `/query` può rifiutare l'INSERT se, rileggendo l'evidence dopo, il
  `fanout_seq` è cambiato; in alternativa basta l'anti-entropia con `RECONCILE_INTERVAL > 0`
  (H-b3q-2 mostra che ripara).
- b3c: controllare nella transazione il seq locale non basta, perché in b3c il fan-out non arriva mai
  al sito. Una correzione senza coordinamento è una seconda lettura dell'evidence *dopo* la
  transazione locale, che riporta il record a disputed se `fanout_seq` è cambiato rispetto alla
  prima lettura. Costo: un GET in più per commit; la finestra si riduce a quella fra le due
  letture ma non si chiude (resta coperta da I3 "upon reconciliation").
- b3r: nella transazione di `/local_restore`, rifiutare se `last_applied_seq` è cambiato rispetto a
  prima della lettura dell'evidence (il fan-out della dispute lo avanza, S:487-490).
- b4: `local_revoke` non ha bisogno dell'evidence se lo `score_id` è ricavabile localmente dai
  campi `device_type, endpoint, protocol, port` di `local_decisions` (S:440-442).
- a10: in S:918 `req.site_id NOT IN (SELECT site_id FROM suspension_reports WHERE score_id=?)`
  quando Q=2.

## 4. Nota di correzione (2026-10-12, notte): H-b3r-2 era formulata male
H-b3r-2 si aspettava che, dopo la corsa di `/local_restore` e una `/reconcile`, il record fosse
`disputed`. È sbagliato: un record revocato localmente che riceve una dispute resta revoked/local
(la guardia di veto avanza solo `last_applied_seq`, S:487-490). Lo stato corretto atteso è quindi
"revoked/local". La falsificazione osservata (monitor-only, non riparato) resta un difetto: il veto
è stato tolto durante un episodio aperto. Ma il valore atteso del test era sbagliato.
Il test resta com'è (`xfail(strict=True)`), senza modifiche. La forma corretta è H-F2 in
`test_distributed_fsm_fix_copy.py` (audit 67 sez. 7).
