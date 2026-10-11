# Audit 57 — Risultati di B2-kill (audit 45): convergenza dopo la morte e il riavvio di un sito

Data: 2026-10-11. Dati: `experiments_tnsm/b2k_20261011/` (orchestratore `auto_b2k.py`, sha256 `a60be9aa…be8b`, sul nodo `ubuntu@192.168.100.57`, tree `244f1d0` con hash verificati, PKI 336 h, watcher v2 a **poll 0,1 s** confermato dal record `profile.applied` di ogni blocco (`poll_s` 0,1), `run.py --block b2kill` per braccio, seme 20261014; 18:15:49-21:29:03Z; **DATA.sha256 verificato per i tre blocchi: 0 discordanze**; nessun pcap). Ipotesi e regole: audit 45 (committato prima dei dati). Analisi: `experiments_tnsm/node_session_20261011/analyze_b2k.py` (output `analysis_b2k.md`; 6 test, mutazioni catturate). Statuto: replica su un solo nodo (CPU QEMU generica, k3s e altri carichi di fondo); nessun confronto con altre macchine.

## Esecuzione e regola L_dns
- Calibrazione L_dns (sito morto visto dal container che risolve) **nello stesso blocco di ogni B2k**: `lan` p95 3,59 ms, `degraded` 3,27 ms, `wan` 3,44 ms (n = 50 ciascuna) → tutte ≤ 50 ms e poll 0,1 s ≤ 0,1 s ⇒ la regola dell'audit 45 §5 dà "run" per tutti e tre i profili; un solo tentativo per profilo (registrati in `ldns_attempts.jsonl.txt`). La misura di smoke di `degraded` (5,0 ms, audit 56/sessione) non conta come tentativo.
- Tre blocchi `done`, 28 celle con dati (lan 12, degraded 8, wan 8), `lan` riconfermato alla fine di ciascuno, nessun gruppo rilanciato. **Deviazione dichiarata (audit 43 B2k, dipendenze):** `run.py` non ha uno smoke per b2kill; il blocco `lan` ha fatto da smoke e i suoi dati sono tenuti.
- **280 prove (10 per cella), 212 utilizzabili, 68 escluse:** `queues_not_empty_at_start` 61 (tutte a `lan`), `client_timeout` 5 (4 a `lan`, 1 a `degraded`), `transport_error` 2 (`degraded`).

## Verdetti pre-registrati
- **(d-kill): non falsificata in nessuna delle 24 celle valutabili** (estremo inferiore dell'IC della mediana mai sopra il bound; 4 celle non valutabili per n = 0, vedi sotto; 2 celle con n = 1 sono solo puntuali).
- **(e): non falsificata:** nessuna prova con `violation_over_bound` o `final_all_monitor_only` falso su 212. **Limite:** I1-I3 sono verificati solo attraverso lo stato finale `monitor-only`; nessun altro invariante è controllato qui.
- **T15 − T5: descrittiva** (decisione Q9): `analysis_b2k.md`; differenze da −0,08 s a +1,69 s, IC larghi con 9-10 prove (es. degraded/D/k=10 +1,62 s [0,45; 2,48], wan/C/k=10 +0,66 s [0,14; 0,99]); l'intervallo di riferimento [0; 1,5] s non è un criterio.

## Tabella (mediana della convergenza dopo `start`, IC bootstrap 95%, bound)
| profile | arm | T | k | n | converged | never | median s [CI] | bound s | (d-kill) | (e) violations | excluded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| degraded | C | 5 | 1 | 10 | 10 | 0 | 2.64 [2.33; 4.71] (n=10) | 7.60 | not falsified | 0 | 0 |
| degraded | C | 15 | 1 | 10 | 10 | 0 | 4.33 [3.30; 5.37] (n=10) | 8.60 | not falsified | 0 | 0 |
| degraded | C | 5 | 10 | 9 | 9 | 0 | 2.81 [2.04; 4.16] (n=9) | 7.60 | not falsified | 0 | {'transport_error': 1} |
| degraded | C | 15 | 10 | 9 | 9 | 0 | 3.26 [2.49; 3.59] (n=9) | 8.60 | not falsified | 0 | {'transport_error': 1} |
| degraded | D | 5 | 1 | 9 | 9 | 0 | 1.98 [1.57; 3.32] (n=9) | 7.00 | not falsified | 0 | {'client_timeout': 1} |
| degraded | D | 15 | 1 | 10 | 10 | 0 | 2.62 [1.64; 3.96] (n=10) | 8.00 | not falsified | 0 | 0 |
| degraded | D | 5 | 10 | 10 | 10 | 0 | 2.04 [1.49; 2.82] (n=10) | 7.00 | not falsified | 0 | 0 |
| degraded | D | 15 | 10 | 10 | 10 | 0 | 3.66 [2.79; 4.32] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | C | 5 | 1 | 10 | 10 | 0 | 0.71 [0.62; 0.79] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 1 | 10 | 10 | 0 | 1.01 [0.57; 1.34] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | C | 5 | 10 | 0 | 0 | 0 | — | 7.00 | not evaluable | 0 | {'queues_not_empty_at_start': 10} |
| lan | C | 15 | 10 | 7 | 7 | 0 | 0.98 [0.88; 1.38] (n=7) | 8.00 | not falsified | 0 | {'client_timeout': 1, 'queues_not_empty_at_start': 2} |
| lan | C | 5 | 50 | 1 | 1 | 0 | 0.69 [0.69; 0.69] (n=1) | 7.00 | not falsified | 0 | {'client_timeout': 1, 'queues_not_empty_at_start': 8} |
| lan | C | 15 | 50 | 0 | 0 | 0 | — | 8.00 | not evaluable | 0 | {'queues_not_empty_at_start': 10} |
| lan | D | 5 | 1 | 10 | 10 | 0 | 0.71 [0.56; 0.82] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | D | 15 | 1 | 10 | 10 | 0 | 1.20 [0.93; 1.78] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | D | 5 | 10 | 0 | 0 | 0 | — | 7.00 | not evaluable | 0 | {'queues_not_empty_at_start': 10} |
| lan | D | 15 | 10 | 6 | 6 | 0 | 0.91 [0.61; 1.59] (n=6) | 8.00 | not falsified | 0 | {'client_timeout': 1, 'queues_not_empty_at_start': 3} |
| lan | D | 5 | 50 | 1 | 1 | 0 | 0.64 [0.64; 0.64] (n=1) | 7.00 | not falsified | 0 | {'client_timeout': 1, 'queues_not_empty_at_start': 8} |
| lan | D | 15 | 50 | 0 | 0 | 0 | — | 8.00 | not evaluable | 0 | {'queues_not_empty_at_start': 10} |
| wan | C | 5 | 1 | 10 | 10 | 0 | 1.43 [1.24; 1.56] (n=10) | 7.00 | not falsified | 0 | 0 |
| wan | C | 15 | 1 | 10 | 10 | 0 | 1.35 [0.90; 2.29] (n=10) | 8.00 | not falsified | 0 | 0 |
| wan | C | 5 | 10 | 10 | 10 | 0 | 1.36 [1.22; 1.56] (n=10) | 7.00 | not falsified | 0 | 0 |
| wan | C | 15 | 10 | 10 | 10 | 0 | 2.01 [1.48; 2.34] (n=10) | 8.00 | not falsified | 0 | 0 |
| wan | D | 5 | 1 | 10 | 10 | 0 | 1.00 [0.82; 1.26] (n=10) | 7.00 | not falsified | 0 | 0 |
| wan | D | 15 | 1 | 10 | 10 | 0 | 2.06 [1.28; 2.25] (n=10) | 8.00 | not falsified | 0 | 0 |
| wan | D | 5 | 10 | 10 | 10 | 0 | 1.12 [0.90; 1.31] (n=10) | 7.00 | not falsified | 0 | 0 |
| wan | D | 15 | 10 | 10 | 10 | 0 | 1.50 [0.85; 1.78] (n=10) | 8.00 | not falsified | 0 | 0 |


## Cosa NON è stato misurato (limite grosso)
- **`lan` con k = 10 e k = 50 è quasi interamente escluso:** 4 celle su 4 per k = 50 e per k = 10 a T = 5 hanno n = 0-1; k = 10 a T = 15 ha n = 6-7. **Quindi la dipendenza da k a `lan` non è misurata** (solo k = 1 a `lan`; k = 1 e 10 a `degraded` e `wan`; k = 50 mai).
- **Causa (verificata sul codice e coerente con i dati, non ipotesi):** in `trial_b2kill` (`run.py`, ramo `except ClientTimeout`) una prova con timeout del client restituisce la riga esclusa **senza** il `start site-3`: il sito resta morto per il resto del cluster. Ogni prova successiva trova la coda di site-3 non vuota e viene esclusa (`queues_not_empty_at_start`, attesa 10-11 s senza svuotarsi). Il motivo si legge nelle sequenze per cella, identiche nei due bracci: `......Tqqq` (D, k = 10, T = 15), `.Tqqqqqqqq` (k = 50, T = 5) e poi interi cell successive nello stesso gruppo `qqqqqqqqqq`; il gruppo T = 5 (nuovo cluster) riparte pulito per k = 1. Il codice `run.py` è congelato (hash): **non l'ho modificato**.
- **Perché non è stato rilanciato:** la regola pre-registrata (audit 45 §6, a33:19-20) ammette un solo nuovo tentativo e solo per un gruppo **senza dati**; qui i gruppi hanno dati. Rifare `lan` k = 10/50 è una nuova decisione (richiede una correzione del driver, quindi un tree nuovo e nuovi hash, oppure una pre-registrazione che accetti l'ordine k crescente per limitare la cascata): non l'ho presa.

## Coda della distribuzione (descrittivo, nessun criterio)
Nessuna prova ha superato il bound, ma a `degraded` il braccio C si avvicina: massimo 7,49 s su 7,60 (98,6 %, k = 10, T = 5) e 8,29 s su 8,60 (96,4 %, k = 10, T = 15); in 9 celle su 24 il massimo supera metà del bound. **Il criterio pre-registrato usa la mediana** (che sta a 2,6-4,3 s, ben sotto): con 9-10 prove per cella la coda non è stimata e il bound potrebbe essere superato in condizioni non campionate.

## Cosa si può dire
- A `lan` (k = 1), `degraded` (k = 1, 10) e `wan` (k = 1, 10) la convergenza dopo la riconnessione ha mediana sotto il bound in tutte le celle valutabili, senza violazioni di (e) su 212 prove; è un risultato **misurato su un solo nodo**, con IC larghi e senza dipendenza da k a `lan` e a k = 50.
- Non si può dire: nulla su k = 50; nessuna garanzia di coda; nessun confronto fra T = 5 e T = 15 (Q9, descrittivo).
