# Audit 101 — Pre-registrazione: diagnosi dei 500 nel setup (arm C, `degraded`)

Scritta e committata PRIMA del lancio (2026-10-12). Origine: audit 98 (13 `setup_failed`, tutti HTTP 500 "Internal Server Error" su `/query` o `/commit`, 8 su 50 episodi in C/10). Codice: `tree-3cc41c5`, `service.py` sha256 `f7987d95…`. Strumento: `experiments_tnsm/node_session_20261011/diag_setup500.py` + `deploy_diag.sh` (applicatore in user space, `degraded`, 11 container, arm C): 50 fatti, setup di `run.py` ripetuto (seed, `/query` + `/commit` sui 10 siti in parallelo con identità op-site-<i>), **senza dispute**; per ogni risposta non-200 si registra stato, corpo e il log del container del sito degli ultimi 20 s, classificando l'ultima eccezione del traceback.

## Ipotesi
- **H-500a (causa):** i 500 sono errori httpx (timeout, connessione, lettura) non gestiti nella chiamata del servizio all'evidence (`_evidence_get_score`, lettura all'inizio di `/query` e `/commit`). **Confermata** se almeno 3 risposte 500 sono osservate e **tutte** hanno nel log del sito un traceback la cui ultima eccezione è `httpx.*` o `httpcore.*` con il frame di `service.py` in `_evidence_get_score` o nei suoi chiamanti diretti. **Falsificata** se anche una sola 500 ha un'altra eccezione (nel qual caso il servizio ha un altro difetto) o se un 500 non ha traceback.
- **H-500b (frequenza):** almeno 4 dei 50 fatti hanno almeno un sito con setup non-200 (in R1b C/10: 8/50). **Inconcludente** se si osservano meno di 3 risposte 500 in totale: la diagnosi non si può trarre e non si dichiara nulla.
- Nessuna correzione al servizio prima di conoscere l'esito.

## Cosa si fa per ogni esito
- H-500a confermata: si propone (non si applica senza OK) di mappare il fallimento dell'evidence a 503 nel servizio e di far ritentare il setup al driver; nuovo hash, R1b da rifare.
- H-500a falsificata: si riporta l'eccezione vera, si indaga prima di altro.
- Inconcludente: si ripete con più fatti (stesso protocollo) o si cattura direttamente dentro un run B1.

## Limiti
Un solo run, 50 fatti, applicatore in user space; non riproduce la concorrenza di un episodio con dispute; i log dei container sono finiti per `docker logs --since` (se la rotazione li ha persi, il 500 resta senza traceback e conta come falsificazione della sola classificazione, non della causa).
