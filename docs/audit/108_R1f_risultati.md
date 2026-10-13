# Audit 108 — R1f: replica di R1e sul codice finale (deployment completo, `degraded`): verdetti degli audit 97/104

Pre-registrazione: audit 104 (R1e) e audit 97 (addendum 2-3), invariate: R1f è la replica di R1e. Dati: `experiments_tnsm/final_R1f_20261012/` (sha256, 0 differenze, pcap esclusi). Run 2026-10-13T03:33:20Z → 05:11:21Z, rc=0, 200 episodi, 0 container rimasti, via `night_queue.sh` (albero `tree-550afed`, `service.py` sha256 `3ffa57ee…`). Analisi: `analyze_deploy.py`, `compare_deploy.py`; nessuna soglia cambiata.

## Tabella (analyze_deploy.py)
| arm | FANOUT | episodi | esclusi | quota in ritardo per sito (previsione v4) | mediana ultimo sito ms [n] (previsione v4) |
|---|---|---|---|---|---|
| D | 10 | 50 | 0 | 0.204 (0.179) | 2012 [47] (—) |
| D | 1 | 50 | 0 | — | 10774 [45] (10600.0) |
| C | 10 | 50 | 0 | 0.340 (0.251) | 2821 [43] (—) |
| C | 1 | 50 | 0 | — | 16701 [35] (16400.0) |


## Verdetti come pre-registrati
- **H-G (immagine): REGGE.** `image_service_sha256` = `3ffa57ee549512e4…` per 11 container in tutte e 4 le celle.
- **H-F1 (D e mediane): REGGE.** D/10 0,204 contro 0,176 ±0,04 (+0,028); mediana dell'ultimo sito a FANOUT 1: D 10 774 ms (10 600 ±25 %: +1,6 %), C 16 701 ms (16 400 ±25 %: +1,8 %).
- **H-F2 (C/10): REGGE.** 0,340 contro 0,309 ±0,06 (+0,031).
- **H-F3 (nessun `setup_failed` con stato 500; residui ≤ 2 per cella): REGGE.** `setup_failed` = 0 in tutte le celle, nessuna esclusione di alcun tipo.
- **H-F5 (descrittivo): `setup_retries`:** C/1 10 (in 10 episodi), D/10 0, **C/10 16 (in 15 episodi su 50)**, D/1 0. Sono i rifiuti puliti dell'evidence sotto mTLS (503) o il 409 del commit con seconda lettura fallita, tutti recuperati entro 3 tentativi.

## Confronto con la replica R1e (stesso codice) e con le repliche del servizio originale (compare_deploy.py, H-R1b)
- **R1f contro R1e** (le due repliche del codice finale): D/10 +0,015, C/10 +0,026, mediane a FANOUT 1 −6,4 % (D) e −3,0 % (C): tutte entro ±0,04 e ±15 %. **Le due repliche sono coerenti fra loro.**
- Contro le quattro repliche del servizio ORIGINALE (audit 86, 89, R1b, R1d; audit 104): mediane a FANOUT 1 entro ±7 % ovunque; quote in ritardo entro ±0,04 in 6 confronti su 8, con due scarti più larghi: D/10 +0,047 contro R1b e C/10 +0,058 contro audit 86. Non sono criteri pre-registrati per R1f (i criteri di R1f sono H-G, H-F1-F3), e le due quote estreme sono i valori più bassi delle repliche originali (D/10 0,157; C/10 0,282): nel complesso C/10 sul nodo, sulle sette repliche, varia da 0,282 a 0,340.

## Le due repliche del codice finale (R1e + R1f) per il paper
D/10: 0,189 e 0,204 (media 0,197; v4 0,179). C/10: 0,314 e 0,340 (media 0,327; v4 0,251, v5 0,280). Il modello senza mTLS sovrastima di meno di 2 punti; con mTLS il v4 sottostima di 7,6 punti e il v5 di 4,7 punti (la prova 3, audit 107, dirà se il v5 regge in condizioni nuove). Mediane dell'ultimo sito a FANOUT 1: D 10 774-11 517 ms, C 16 701-17 215 ms contro previsioni 10 600 e 16 400.

## Limiti
Una macchina; 50 episodi per cella; due repliche; `degraded` soltanto; il numero di ritentativi mescola le due cause del retry (audit 102).
