# Audit 104 — SCOPERTA: i container del nodo non hanno mai eseguito il `service.py` degli alberi dopo il 10 ottobre; ambito e pre-registrazione di R1e

Data 2026-10-12. **Errore mio di procedura, scoperto da R1d** (17 `setup_failed`, tutti HTTP 500, con la correzione 503 già nell'albero).

## Cosa è successo
- `run.py` portava su il cluster con `docker compose up -d` (`run.py` prima di c898ea8, riga `up -d` in `Env.up`), **senza `--build`**. Compose costruisce l'immagine solo se manca: le immagini `dibtnsm-*:latest` esistono dal **2026-10-10 17:30:46 UTC** (`docker images`) e sono state riusate da ogni run successivo.
- Dentro l'immagine, `/app/service.py` ha sha256 `31863043…` (`docker run --rm --entrypoint sha256sum dibtnsm-site-3:latest /app/service.py`, e lo stesso per `dibtnsm-evidence`), cioè il file originale (`tree-244f1d0` e tutti gli alberi fino al 10-11 ottobre).
- Il manifest registrava `node_service_sha256` = sha256 del file nell'ALBERO, non quello dentro i container: la discrepanza non era visibile.

## Ambito (dai manifest committati, `node_tree` e `node_service_sha256`)
- **Non toccati** (albero con `service.py` `31863043…` = immagine): tutti i blocchi fino al 2026-10-11T21:05Z compreso, cioè **B5** (`b5_20261011`), **B2k originale** (`b2k_20261011`, lan/degraded/wan), i blocchi B1 lan/wan/degraded dell'11 ottobre, le diagnosi M3 del 10 ottobre. Il loro codice è quello dichiarato.
- **Toccati** (albero con `service.py` diverso dall'immagine): `b2k_fix_20261012` e `keepalive_lan_20261012` (albero `0501b383…`), `b2k_dnsfix_20261012` (`0501b383…`), `deploy_run_20261012` = audit 86 (`a6bb1d22…`), `rerun_R1_20261012` = audit 89 (`5599f53b…`), `final_R1b_20261012` (`f7987d95…`), `final_R1d_20261012` (`3ffa57ee…`). **In tutti questi i container eseguivano l'originale `31863043…`**, non il codice dell'albero.
- Che cosa cambia, per audit:
  - **Audit 71 / keep-alive sul nodo (`keepalive_lan_20261012`):** la misura "falsificata" sul nodo NON provava nulla (il codice del keep-alive non era nei container). La falsificazione resta valida **solo** per il banco locale (audit 76, codice vero).
  - **B2k lan "pulito" con driver fix e DNS fix (audit 69, 73):** le correzioni erano nel DRIVER e nel compose (DNS), non in `service.py`: i risultati restano validi, ma descrivono il servizio ORIGINALE.
  - **Audit 86, 89, R1b, R1d:** misure del servizio ORIGINALE (`31863043…`). I confronti "vecchio contro nuovo codice" (audit 89 H-R1b, audit 98 H-F3) sono **privi di senso come confronti di codice**: confrontano repliche dello stesso codice. Restano valide come repliche del modello di consegna con il servizio originale. In particolare **i 500 e i `setup_failed` di audit 98 e della presente R1d sono del servizio originale**, e la diagnosi dei 500 (audit 102: errori httpx non gestiti, 7/50) vale per il servizio originale; la correzione 503 NON è stata ancora provata sul nodo.
  - **Paper (`main_wip.tex`):** le frasi sul nodo (replica di B5, convergenza dopo il riavvio fino a k = 50 a lan, validazione del modello di consegna sul deployment con due repliche) descrivono misure del servizio originale: restano vere, ma il paper deve dichiarare quale servizio è stato misurato. Il banco locale (concorrenza fan-out, modello v4) e la replica nei container del nodo usano il codice vero.
- **Cosa NON cambia:** i test sul codice (507 passed), i banchi locali (codice vero, sha nel manifest), le verifiche TLC.

## Correzione (commit `c898ea8`)
`run.py`: `up -d --build` e `verify_service_image()`, che esegue `docker exec <container> sha256sum /app/service.py` sugli 11 container e solleva `ImageMismatch` (il run si ferma) se differisce dal `service.py` dell'albero; lo sha dei container è registrato in ogni cella (`image_service_sha256`). 4 test rossi prima. Le immagini vecchie non vengono cancellate.

## Pre-registrazione R1e (prima del lancio)
Albero `tree-c898ea8` (`service.py` sha256 `3ffa57ee…`), run identico ad audit 97 (`deploy_run.sh`, `run.py b1 degraded`, D,C × 10,1, 50 episodi, seed 20261014, applicatore in user space, quorum 1, T = 5, invarianti OFF, soglie P-log di B5). **Ipotesi e soglie dell'audit 97 (addendum 2 e 3):**
- **H-G (nuova, precondizione):** in ogni cella `image_service_sha256` = `3ffa57ee…` per tutti gli 11 container. Se no, il run si ferma (ImageMismatch) e non conta.
- **H-F1:** D/10 entro ±0,04 da 0,176; mediana ultimo sito a FANOUT 1 entro ±25 % da 10 600 (D) e 16 400 (C).
- **H-F2:** C/10 entro ±0,06 da 0,309.
- **H-F3:** nessun `setup_failed` con stato 500; `setup_failed` residui (503/409-retry esauriti) ≤ 2 per cella.
- **H-F5:** `setup_retries` per cella (descrittivo). Atteso > 0 in C se la causa è l'evidence lenta.
Se H-G passa e H-F3 regge, la correzione 503 + retry è provata sul nodo e **B2k** parte sull'albero finale; altrimenti B2k non parte.
