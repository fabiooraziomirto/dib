# Audit 105 — R1e: deployment completo sul codice finale (immagine ricostruita e verificata): verdetti dell'audit 104

Pre-registrazione: `docs/audit/104_immagine_docker_scorretta_e_prereg_R1e.md` (committata prima del lancio, f06cb25). Dati: `experiments_tnsm/final_R1e_20261012/` (copiati con sha256, 0 differenze, pcap esclusi). Run 2026-10-12T15:02:58Z → 16:42:34Z, rc=0, 200 episodi, 0 container rimasti. Albero `tree-c898ea8`, `service.py` sha256 `3ffa57ee…` (correzioni FSM + D1 + D2 + 503/502), `run.py` con `up -d --build` e `verify_service_image`. **È il primo run sul nodo che esegue davvero il codice finale** (audit 104). Soglie non cambiate dopo i dati.

## Tabella (analyze_deploy.py)
| arm | FANOUT | episodi | esclusi | quota in ritardo per sito (previsione v4) | mediana ultimo sito ms [n] (previsione v4) |
|---|---|---|---|---|---|
| D | 10 | 50 | 0 | 0.189 (0.179) | 1621 [45] (—) |
| D | 1 | 50 | 0 | — | 11517 [48] (10600.0) |
| C | 10 | 50 | 0 | 0.314 (0.251) | 2823 [36] (—) |
| C | 1 | 50 | 0 | — | 17215 [35] (16400.0) |


## Verdetti come pre-registrati
- **H-G (precondizione): REGGE.** In tutte e 4 le celle `image_service_sha256` ha 11 container, tutti `3ffa57ee549512e4…` = sha256 del `service.py` dell'albero.
- **H-F1: REGGE.** D/10 0,189 (previsto 0,176 ±0,04: scarto +0,013); mediana dell'ultimo sito a FANOUT 1: D 11 517 ms (10 600 ±25 %: +8,7 %), C 17 215 ms (16 400 ±25 %: +5,0 %).
- **H-F2: REGGE.** C/10 0,314 contro 0,309 ±0,06 (scarto +0,005).
- **H-F3 (nessun `setup_failed` con stato 500; residui ≤ 2 per cella): REGGE.** `setup_failed` = **0 in tutte le celle** (nelle repliche con il servizio originale erano 13 e 17, tutti 500: audit 98 e R1d). Nessuna esclusione di alcun tipo in R1e.
- **H-F5 (descrittivo): `setup_retries`** C/1 = 14 (in 11 episodi), D/10 = 1 (1), **C/10 = 23 (in 19 episodi su 50)**, D/1 = 0. Cioè nel braccio mTLS a FANOUT 10 **più di un episodio su tre ha avuto almeno un passo del setup ritentato**; tutti sono rientrati entro 3 tentativi. Il numero mescola, per audit 102, le due cause del retry (503 dell'evidence non raggiungibile, 409 "evidence changed" per seconda lettura fallita): R1e non distingue le due.

## Primo confronto vero fra servizio originale e codice finale (H-R1b, `compare_deploy.py`)
Le quattro repliche precedenti (audit 86, audit 89, R1b, R1d) eseguivano tutte il servizio ORIGINALE `31863043…` (audit 104). R1e rispetto a ciascuna: D/10 +0,003, +0,023, +0,032, +0,005; C/10 +0,033, −0,021, +0,010, +0,001 (tutti entro ±0,04); mediane a FANOUT 1 entro ±8 % (soglia ±15 %). **Nessuna regressione nella quota in ritardo né nelle mediane**, in tutti e quattro i confronti.

## Cosa si conclude
- Il servizio finale, sul deployment completo con mTLS e perdita 5 %, non cambia il tempo di ritiro rispetto all'originale e **non perde più episodi per errori del setup**: i guasti dell'evidence (con mTLS, RTT 0,4 s) diventano 503 gestiti e il setup li ritenta. Il modello v4 sul braccio senza mTLS regge (D/10 0,189 contro 0,179); con mTLS C/10 = 0,314 contro il v4 0,251 (sottostima di 6,3 punti, dentro la banda 0,282-0,335 delle repliche) e il v5 0,280 (audit 94).
- Le repliche R1e + R1f (da fare) sono quelle da usare nel paper per il deployment completo; le quattro precedenti restano come repliche del servizio originale (non per il paper, per decisione dell'utente).

## Limiti
Una macchina; una replica (R1f segue); `setup_retries` mescola due cause; R1e non esegue gli invarianti di fine prova (flag spento per confrontabilità); un solo profilo (`degraded`).
