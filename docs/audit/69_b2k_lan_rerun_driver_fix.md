# Audit 69 (già numerato 63 nei messaggi di commit del branch tnsm-driver-retry; rinumerato per non collidere con gli audit 63-68 del branch tnsm-fsm) — B2-kill a `lan` rifatto con la correzione del driver (H-D1 di audit 60 §1)

Data: 2026-10-12 (00:06Z a nodo). Dati: `experiments_tnsm/b2k_fix_20261012/b2k_lan/` (tree `50c4335` = `244f1d0` con `service.py` e `run.py` cambiati, 22 hash su 24 identici, `frozen_hashes_50c4335.txt`; `calib_profile.py` e `run.py --block b2kill --profile lan`, arms D poi C, seme 20261014, L_dns calibrato a `lan` nello stesso blocco: p95 3,13 ms (n = 50) ≤ 50 ms, regola dell'audit 45 §5 soddisfatta; nessun watcher necessario a `lan`; PKI 336 h; `DATA.sha256` verificato dopo la copia: 0 discordanze). Script: `experiments_tnsm/node_session_20261011/lan_b2k_validation.sh`; analisi `analyze_b2k.py` (invariato salvo il caso "lato vuoto" di audit 57). Le ipotesi di B2k sono quelle dell'audit 45; la validazione del driver quella dell'audit 60 §1.

## H-D1: NON falsificata
- **Criterio 1:** nessuna cella k = 10/50 ha più di 3 prove su 10 escluse per `queues_not_empty_at_start`: massimo **1** (prima: fino a 10 su 10, 61 in tutto). La cascata di audit 57 è sparita.
- **Criterio 2:** ogni prova esclusa per timeout ha `site3_restarted_after_exception = true` (12/12).
- **Conseguenza:** il difetto era quello descritto; con la correzione il blocco `lan` produce dati per k = 10 e 50.

## Risultati (mediana della convergenza dopo `start`, IC bootstrap 95%; bound 7,0 s a T = 5 e 8,0 s a T = 15)
| arm | T | k | n | mediana s [IC] | esclusioni |
|---|---|---|---|---|---|
| C | 5 | 1 | 10 | 0,64 [0,56; 0,71] | 0 |
| C | 15 | 1 | 10 | 1,17 [0,55; 1,65] | 0 |
| C | 5 | 10 | 10 | 0,63 [0,50; 0,76] | 0 |
| C | 15 | 10 | 10 | 1,19 [0,75; 1,57] | 0 |
| C | 5 | 50 | 10 | 0,77 [0,57; 0,84] | 0 |
| C | 15 | 50 | 10 | 0,92 [0,72; 1,69] | 0 |
| D | 5 | 1 | 10 | 0,70 [0,55; 0,76] | 0 |
| D | 15 | 1 | 10 | 0,94 [0,75; 1,38] | 0 |
| D | 5 | 10 | 8 | 0,66 [0,58; 0,78] | 2 timeout |
| D | 15 | 10 | 8 | 0,97 [0,70; 1,51] | 1 timeout, 1 coda non vuota |
| D | 5 | 50 | 3 | 0,72 [0,67; 0,91] | 7 timeout |
| D | 15 | 50 | 1 | 1,91 (n = 1) | 2 timeout, 1 coda non vuota, 6 `transport_error` |
**(d-kill) non falsificata in 12/12 celle** (nelle due con n ≤ 3 il risultato è solo puntuale); **(e) non falsificata** su 100 prove utilizzabili (nessuna `violation_over_bound`, nessun `final_all_monitor_only` falso). T15 − T5 resta descrittiva (audit 45, Q9).

## Cosa resta non misurato bene
- **k = 50 con l'arm D (senza mTLS):** 7 timeout su 10 a T = 5 e una sequenza di 6 `transport_error` (connessione resettata da site-3, `POST /query`) a T = 15: il sito riavviato dopo un timeout non era ancora raggiungibile per le prove seguenti. L'arm C, nello stesso blocco, non ha avuto né timeout né esclusioni a nessun k. **Causa del timeout dell'arm D: NON determinata** (non registro la latenza per chiamata); non la attribuisco né a D né a mTLS. Le esclusioni seguono le regole di audit 45 §6 e non si sostituiscono.
- Il blocco `lan` è su un solo nodo e 10 prove per cella; la coda non è stimata.

## Cosa si può dire
Con il driver corretto la convergenza a `lan` è misurabile fino a k = 50 per l'arm C e fino a k = 10 per l'arm D, con mediane di 0,6-1,2 s (bound 7-8 s) e nessuna violazione; k = 50 per D è solo indicativo (n = 1-3). Questi dati sostituiscono il blocco `lan` di audit 57 per k = 10 e 50; k = 1 di audit 57 e di questo audit sono due repliche separate.
