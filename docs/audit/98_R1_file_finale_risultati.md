# Audit 98 — R1b: deployment completo sul `service.py` finale (`tree-3cc41c5`): verdetti dell'audit 97

Pre-registrazione: `docs/audit/97_prereg_R1_file_finale.md` (con l'addendum sul primo tentativo, fallito per un errore del mio driver). Dati: `experiments_tnsm/final_R1b_20261012/` (copiati con sha256, 0 differenze, pcap esclusi). Run 2026-10-12T11:55:30Z → 13:15:51Z, rc=0, 200 episodi, 0 container rimasti. Codice: `tree-3cc41c5`, `service.py` sha256 `f7987d95…` (correzioni FSM + D1 + D2), `run.py` con D5 corretto (commit 3cc41c5). Analisi: `analyze_deploy.py`, `compare_deploy.py`; nessuna soglia cambiata dopo i dati.

## Tabella (analyze_deploy.py)
| arm | FANOUT | episodi | esclusi | quota in ritardo per sito (previsione v4) | mediana ultimo sito ms [n] (previsione v4) |
|---|---|---|---|---|---|
| D | 10 | 50 | 1 | 0.157 (0.179) | 1621 [48] (—) |
| D | 1 | 50 | 1 | — | 10677 [43] (10600.0) |
| C | 10 | 50 | 8 | 0.304 (0.251) | 2677 [32] (—) |
| C | 1 | 50 | 3 | — | 16818 [34] (16400.0) |


## Verdetti come pre-registrati (audit 97)
- **H-F1 (D e mediane): REGGE.** D/10 0,157 (previsto 0,176 ±0,04: scarto −0,019); mediana ultimo sito a FANOUT 1: D 10 677 ms (10 600 ±25 %), C 16 818 ms (16 400 ±25 %).
- **H-F2 (C/10 non regredisce): REGGE.** C/10 0,304 contro 0,309 ±0,06 (scarto −0,005). Confronto con le repliche precedenti: audit 86 0,282 (+0,023), audit 89 0,335 (−0,031), entrambi entro ±0,04 (`compare_deploy.py`: H-R1b regge in entrambi i confronti).
- **H-F3 (D5, D1, D2 non cambiano il percorso misurato; ≤ 2 `setup_failed` per cella): FALSIFICATA.** `setup_failed`: **C/10 = 8**, C/1 = 3, D/10 = 1, D/1 = 1. Nessun episodio escluso per `queues_not_empty_at_start` né per timeout di client. Soglia ≤ 2: superata in C/10 e in C/1.

## Cosa sono i `setup_failed` (letto dalle righe)
Tutti e 13 sono **HTTP 500 "Internal Server Error"** su `/query` o su `/commit` di un singolo sito durante il setup (per esempio `setup commit at site-7: status 500`), distribuiti su siti diversi (0, 1, 2, 3, 4, 6, 7, 8). Nessun 503 (quindi non è il timeout di D2) e nessun 409.
- **Ipotesi (non verificata: i container sono già rimossi e `run.py` non salva i loro log):** il servizio solleva un'eccezione non gestita quando la chiamata all'evidence (`_evidence_get_score`, lettura all'inizio di `/query` e di `/commit`, fuori dal `try`) scade o fallisce sotto perdita di pacchetti; l'eccezione esce come 500. È coerente con la distribuzione (mTLS 8/50 e 3/50, plain 1/50 e 1/50: l'handshake mTLS ha più pacchetti esposti) ma non è dimostrata.
- **Non è un difetto introdotto da D1/D2** (che non toccano quelle righe), ma è il comportamento che D5 rende visibile: nelle repliche precedenti (audit 86, 89) il driver ignorava le risposte del setup, quindi episodi con siti non Active **potevano già esserci senza che nessuno lo vedesse**. Questo è un limite delle misure precedenti, non verificabile a posteriori.
- **Effetto sulle misure:** H-F1 e H-F2 sono calcolati sugli episodi non esclusi. Il P-log misura l'apply del fan-out, che viene registrato anche senza riga locale (audit 90 D5), quindi i numeri non cambiano per questo; cambia il significato di "sito Active al momento della dispute".

## Conclusione
Il modello v4 sul deployment completo continua a reggere senza mTLS e per le mediane; con mTLS C/10 = 0,304, dentro la banda delle repliche (0,282-0,335), con la sottostima nota del v4 (0,251). **L'unica ipotesi falsificata è H-F3**, e riguarda il servizio sotto mTLS e perdita: un 500 invece di un errore gestito quando l'evidence non risponde in tempo. Per audit 97, B2k **non** è stato lanciato.

## Decisioni per l'utente
1. Verificare la causa dei 500 (catturare `docker logs` dei siti su un episodio con setup fallito, o riprodurre nel testbed con mTLS e perdita).
2. Se confermata: il servizio dovrebbe rispondere 503 (evidence irraggiungibile) invece di 500 e il driver potrebbe ritentare il setup (come fa il testbed). Cambierebbe `service.py` (nuovo hash) e `run.py`.
3. Oppure dichiarare il limite e procedere con B2k sul file attuale, sapendo che il setup di B2k (un solo sito, k fatti) ha esposizione minore ma non nulla.
