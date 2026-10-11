# Audit 62 — Modello del costo di consegna sotto perdita: coerenza con B5 e previsioni da testare (audit 60 §3-5)

Data: 2026-10-12. Codice: `experiments_tnsm/retry_model/model.py` (8 test, 6/6 mutazioni catturate), `python3 experiments_tnsm/retry_model/model.py`; 20 000 episodi per configurazione, seme 20261012, Python 3.10.13. Parametri **non adattati** (R = 0,4 s, perdita 5 % per pacchetto, timeout httpx 1,0 s per fase, 3 tentativi, nuova connessione per tentativo: `service.py:120-121, 708-712`). Struttura del modello scelta **dopo** aver visto i dati di B5: la coerenza sotto è un controllo descrittivo, non una conferma indipendente.

## Coerenza con B5 (criteri fissati in audit 60 §3)
| grandezza | simulata | osservata (B5, audit 56 e analisi esplorativa) | criterio | esito |
|---|---|---|---|---|
| consegne in ritardo, FANOUT 10, D | 13,9 % | 13,6 % (68/499) | ± 4 punti | coerente |
| consegne in ritardo, FANOUT 10, C | 21,6 % | 25,1 % (114/455) | ± 4 punti | coerente (−3,5) |
| mediana ultimo sito, FANOUT 10, D | 1 600 ms | 1 639 ms | ± 25 % | coerente (−2 %) |
| mediana ultimo sito, FANOUT 10, C | 2 800 ms | 2 826 ms | ± 25 % | coerente (−1 %) |
| mediana ultimo sito, FANOUT 1, D | 10 200 ms | 10 316 ms | ± 25 % | coerente (−1 %) |
| mediana ultimo sito, FANOUT 1, C | 15 600 ms | 18 516 ms | ± 25 % | coerente (−16 %) |
Descrittivo (non nei criteri): consegne in pending per consegna ≈ 0,6 % (D) e 1,7 % (C) nel modello contro 0,5 % (5/1000) e 2,2 % (21/960) osservati.
**Perché (a′) falsificava:** un tentativo fallito costa 1,0 s (perdita in connect) ma 1,4-1,8 s se la perdita avviene nelle fasi successive (si somma il tempo già speso nelle fasi precedenti) e la probabilità di fallimento è per **pacchetti** (D 4 critici, C 6), non il valore di profilo f usato in (a′). Il termine E[F]·1 s di (a′) sottostimava entrambe le cose.

## Politiche (solo nel modello; mediana e p95 dell'ultimo sito, episodi completi; pending = quota di episodi con almeno un sito in pending)
| policy | arm | FANOUT | median ms | p95 ms | pending | late share |
|---|---|---|---|---|---|---|
| P0 current | D | 10 | 1600 | 3000 | 0.0618 | 0.139 |
| P0 current | D | 1 | 10200 | 13400 | 0.0618 | 0.000 |
| P0 current | C | 10 | 2800 | 4200 | 0.1721 | 0.216 |
| P0 current | C | 1 | 15600 | 20200 | 0.1721 | 0.000 |
| P1 warm connection | D | 10 | 200 | 2600 | 0.0345 | 0.049 |
| P1 warm connection | D | 1 | 5200 | 8000 | 0.0345 | 0.000 |
| P1 warm connection | C | 10 | 200 | 3000 | 0.0685 | 0.048 |
| P1 warm connection | C | 1 | 5600 | 9200 | 0.0685 | 0.000 |
| P2 phase timeout 0.6 s | D | 10 | 1200 | 2200 | 0.0618 | 0.139 |
| P2 phase timeout 0.6 s | D | 1 | 9400 | 11600 | 0.0618 | 0.000 |
| P2 phase timeout 0.6 s | C | 10 | 2200 | 3400 | 0.1721 | 0.216 |
| P2 phase timeout 0.6 s | C | 1 | 14400 | 18000 | 0.1721 | 0.000 |
| P3 hedged connect 0.5 s | D | 10 | 1100 | 2500 | 0.0109 | 0.141 |
| P3 hedged connect 0.5 s | D | 1 | 9700 | 13000 | 0.0109 | 0.000 |
| P3 hedged connect 0.5 s | C | 10 | 2800 | 4300 | 0.0722 | 0.222 |
| P3 hedged connect 0.5 s | C | 1 | 15500 | 20200 | 0.0722 | 0.000 |

## Lettura
- **Il fattore dominante è la sequenzialità** (FANOUT 1: ~10 consegne in fila): D 10,2 s contro 1,6 s con FANOUT 10 (modello, e 10,3 contro 1,6 s misurati). Cambiare il default `DIB_DIST_FANOUT_CONCURRENCY` (1 → 10, `service.py:146`) è la leva di gran lunga più grande (~6×); **decisione dell'utente, non presa**.
- **P1 connessione riusata e calda**: mediana 200 ms per D **e** C (l'handshake e il costo di mTLS spariscono), ma p95 2,6-3,0 s e pending 3,5 %/6,9 % degli episodi: la perdita sulla richiesta resta. **Vale solo se la connessione è calda**: nel deployment le dispute sono rare, quindi serve un mantenimento della connessione (ping periodico), non modellato.
- **P2 timeout 0,6 s**: −25 % (D) e −21 % (C) sulla mediana, pending invariato; **non modellato**: timeout spuri con RTT variabile.
- **P3 connect hedged a 0,5 s**: D mediana 1,1 s e pending 1,1 % (−82 %); **nessun effetto su C** (le perdite stanno nella fase TLS e nella richiesta, non nel connect).
- **Limiti:** nessun jitter né perdita correlata, nessun costo CPU, RTT fisso; l'applicazione "a metà RTT" e la fase TLS a 1 RTT sono assunzioni di struttura.

## Previsioni registrate per la misura sul nodo (PRIMA di implementare o misurare)
Blocco `degraded`, solo FANOUT 10, D e C, 50 episodi per cella, stesso nodo; configurazione **P1 implementata come opt-in** (connessioni persistenti per sito + ping di mantenimento; default del servizio invariato).
- **H-K1:** la mediana dell'ultimo sito (episodi completi, P-log) è **≤ 600 ms in entrambi i bracci** (il modello dice 200 ms; la soglia è lasca perché il modello ignora il carico). **Falsificata** se l'estremo inferiore dell'IC 95% della mediana supera 600 ms in D o in C.
- **H-K2:** la differenza C − D delle mediane è piccola: **|C − D| ≤ 300 ms** (oggi +1 186 ms). **Falsificata** se l'IC della differenza sta interamente fuori da [−300; +300] ms.
- **H-K3 (sicurezza):** nessuna regressione di consegna: la quota di consegne in pending per consegna non supera quella del blocco B5 (D 0,5 %, C 2,2 %) in modo significativo (IC di Clopper-Pearson di P1 non interamente sopra quello di B5). **Falsificata** se l'IC di P1 sta interamente sopra.
- **H-K4 (connessione stantia dopo riavvio):** B2k `degraded` con P1: mediana della convergenza sotto il bound e 0 violazioni di (e) (stesse regole dell'audit 45). Falsificata come in audit 45.
Se H-K1 o H-K2 sono falsificate, P1 non si propone per il paper e si riporta il modello come spiegazione di (a′).

## Cosa non si fa
Nessuna modifica del default; nessun uso del modello per scegliere parametri oltre P1; nessun dato nuovo nel paper prima delle misure.
