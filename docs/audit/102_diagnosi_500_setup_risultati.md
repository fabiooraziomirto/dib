# Audit 102 — Diagnosi dei 500 nel setup: risultati (pre-registrazione: audit 101)

Run: 2026-10-12T13:18:34Z → 13:26:51Z, `deploy_diag.sh`, `tree-3cc41c5` (`service.py` sha256 `f7987d95…`), arm C (mTLS), `degraded`, applicatore in user space, 50 fatti. Dati: `experiments_tnsm/diag500_20261012/diag.json` (copiati con sha256, 0 differenze).

## Osservato
- Risposte non-200 nel setup: **7 su 50 fatti** (7 fatti diversi: 12, 13, 27, 28, 36, 40, 43), **tutte HTTP 500**, su siti 0, 3, 4, 6, 7, 8; 2 su `/query`, 5 su `/commit`.
- Ultima eccezione visibile nel log del container del sito (ultimi 1500 caratteri del log, `diag.json` campo `log_tail`): **`httpx.ConnectTimeout: _ssl.c:993: The handshake operation timed out` in 5 casi** (handshake TLS dell'mTLS verso l'evidence scaduto) e **`httpx.ReadTimeout: The read operation timed out` in 2 casi**.

## Verdetti come pre-registrati
- **H-500a (causa: errori httpx non gestiti nella chiamata all'evidence): CONFERMATA NEL TIPO DI ECCEZIONE, NON NEL FRAME.** Sette 500 osservate (≥ 3), tutte e sette con un'eccezione `httpx.*` come ultima riga del log; nessuna con un'altra eccezione (quindi non falsificata). Il criterio chiedeva anche il frame di `service.py` in `_evidence_get_score` o nei chiamanti diretti: **non è osservabile dai dati salvati**, perché il log è stato troncato agli ultimi 1500 caratteri e l'intestazione del traceback e i frame di `service.py` ne restano fuori (limite dello strumento, dichiarato). Il frame si ricostruisce **dalla lettura del codice**, non dall'osservazione: le sole chiamate HTTP di `/query` e `/commit` sono `_evidence_get_score` (`service.py:467-476`, `httpx.get(..., timeout=5.0)`), chiamata senza guardia a `service.py:506` (`/query`, prima lettura), `:563` (`/commit`, prima lettura) e `:622`; a `:531` (`/query`, seconda lettura) l'eccezione viene rilanciata dopo aver cancellato la riserva (e quindi esce come 500); solo `:578` (`/commit`, seconda lettura) è protetta.
- **H-500b (frequenza ≥ 4 fatti su 50 con almeno un sito fallito): REGGE** (7/50 = 14 %, contro 8/50 in R1b C/10).
- Consistenza con la causa: la probabilità che una chiamata mTLS all'evidence con RTT 0,4 s e perdita 5 % superi 5 s (timeout di `httpx.get`) è piccola ma non nulla per ciascuna delle 20 chiamate di un fatto, e l'handshake TLS è il punto più esposto (5 ConnectTimeout su 7).

## Strumento
`classify_log` non ha trovato nulla sui log reali per due ragioni: `docker logs -t` aggiunge un timestamp a ogni riga (corretto, test aggiunto) e i log salvati non contengono l'intestazione del traceback (troncati). La lettura delle righe `httpx.*` è stata fatta direttamente sul campo `log_tail`; il dato grezzo è in repo e chiunque può rifarla.

## Cosa significa per le misure
- Il servizio risponde **500 (errore del server)** a un guasto di rete verso l'evidence invece di un errore gestito (503): per il client è indistinguibile da un bug. Succede a un setup su ~7 fatti su 50 in mTLS e sotto perdita (contro 1 su 50 senza mTLS in R1b).
- Nelle repliche precedenti (audit 86, 89) il driver ignorava queste risposte: episodi con siti non Active possono esserci stati senza che si vedesse (non verificabile a posteriori).
- Non è un difetto di D1/D2. È un comportamento del codice presente da prima delle correzioni, rivelato da D5.

## Decisione presa (utente: "non vorrei dichiarare il limite")
Correggere. Proposta di correzione in due parti (nuovo hash, R1b da rifare): servizio, errore httpx verso l'evidence nelle tre letture non protette → 503 "evidence unreachable" (nessun altro cambio di semantica); driver, ritentare il setup di un sito su 503 (come il testbed, `testbed.py:run_episode`) fino a 3 volte e registrare i tentativi.
