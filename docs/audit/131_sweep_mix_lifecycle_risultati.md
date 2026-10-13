# Audit 131 — Sweep con mix di lifecycle: risultati

Data 2026-10-13. Pre-registrazione: audit 130 (commit `8a7987e`, prima del lancio). Dati: `experiments_tnsm/site_sweep_20261013/lifecycle_{http,mtls}/`; analisi `analysis_lifecycle_{http,mtls}/` (`analyze.py` invariato). Due trasporti × 16 celle × 5 ripetizioni = 126 000 richieste per trasporto. Esecuzione 12:37–13:39 UTC, un trasporto alla volta, host condiviso. Nessun retry, nessuna esclusione.

## H-L0 — provenienza: **regge**
`83d8c99a` in ogni container di ogni N, all'inizio e alla fine, per entrambi i trasporti.

## H-L1 — ogni richiesta è un cambio di stato riuscito: **falsificata sotto il carico più alto**
| Trasporto | Celle con fallimenti | Dettaglio |
|---|---|---|
| http | N=1 W=100 | 29 commit in timeout (5 s lato client) |
| | N=2 W=100 | 1 336 commit, 950 restore e 483 dispute in timeout; 385 commit con 409 (2 ripetizioni su 5 degenerano) |
| | N=10 W=100 | 32 commit in timeout |
| mtls | N=1 W=100 | 4 commit in timeout |
Tutte le altre celle: 0 rifiuti, 0 errori; ogni richiesta è un 2xx che cambia stato.
I 409 seguono un timeout del passo precedente dello stesso writer: un restore che scade lato client e non è ancora applicato lascia il fatto Disputed, quindi il commit successivo è rifiutato. Non è una corsa fra writer: il servizio rifiuta correttamente il commit, ed è il harness che non ritenta. Nessun 5xx, nessun errore di trasporto.

## H-L2 — la distribuzione non aumenta il throughput dei cambi di stato: **regge (previsione esplorativa)**
Throughput (richieste = cambi di stato al secondo, media su 5 ripetizioni):
| N | http W=1 | http W=10 | http W=50 | mtls W=1 | mtls W=10 | mtls W=50 |
|---|---|---|---|---|---|---|
| 1 | 78,5 | 193,5 | 246,1 | 137,1 | 307,8 | 289,7 |
| 2 | 65,8 | 109,7 | 105,7 | 119,8 | 207,2 | 201,1 |
| 5 | 45,3 | 76,6 | 66,2 | 85,2 | 137,0 | 134,0 |
| 10 | 25,4 | 37,3 | 38,0 | 56,5 | 75,2 | 75,6 |
- Rapporto contro N=1 a W=50 [IC 95 %]:
  - http: 0,43× [0,42, 0,44] (N=2), 0,27× (N=5), 0,15× [0,15, 0,16] (N=10);
  - mtls: 0,69×, 0,46×, 0,26×.
- A W=100 i rapporti (http 0,44–0,79×, mtls 0,66–1,68×) **non sono interpretabili come guadagno**: a N=1 e W=100 il servizio scade in timeout e il throughput crolla (http 83,1 ± 11,0, mtls 112,9 ± 23,7 richieste/s; p95 3,4–3,5 s), quindi il denominatore è degradato.
- Latenza mediana a W=50: da 190 ms (N=1) a 1,56 s (N=10) in http, da 144 ms a 474 ms in mtls.

## H-L3 — collo di bottiglia, regola di audit 123: **servizio condiviso (evidence)**
In tutte le celle con W=10 e W=50 da N=2 in su, e a N=1 W=50 (http) e N=1 W=10–50 (mtls), valgono le tre condizioni:
- l'evidence usa 1,5–2,9 core;
- il throughput non cresce passando al W successivo;
- il generatore usa ≤ 0,67 core.
La causa coerente con il codice: dispute e restore attendono il fan-out sincrono a tutti gli N siti (`service.py:1007-1009`), e ogni commit legge due volte l'evidence. È **attribuito** alle celle indicate; nelle celle a W=100, o dove la regola non si applica, resta "non attribuibile". Memoria massima dell'evidence: 159 MiB (http), 124 MiB (mtls).

## Lettura (con audit 127)
La distribuzione dei siti aumenta il throughput del **percorso di gestione locale** (letture, rifiuti, commit): 1,9–2,5× in http. Rallenta invece il **percorso dei cambi di lifecycle condivisi**: dispute e restore hanno costo proporzionale al numero di siti e passano tutti dal servizio condiviso, che diventa il collo di bottiglia misurato. Con 100 writer concorrenti senza retry il servizio supera il timeout di 5 s del client. In mTLS a W ≥ 50 il throughput è più alto che in http, ma i due trasporti non sono a parità di stack (audit 127). Un sito, un host, nessun WAN.
