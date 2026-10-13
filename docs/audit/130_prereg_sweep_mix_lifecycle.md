# Audit 130 — Pre-registrazione: sweep dei siti con mix di lifecycle (ogni richiesta cambia stato)

Data 2026-10-13, prima del lancio. Motivazione: nello sweep di audit 127 il mix ereditato produce il 99 % di commit rifiutati con 409, quindi il throughput misura soprattutto letture e rifiuti. Autorizzazione: "puoi procedere" (audit 128 §7, punto 4).

## Configurazione
`experiments_tnsm/site_sweep_20261013/lifecycle_bench.py` (test: `test_lifecycle_bench.py`, 2 passed).
- Ogni writer w possiede un fatto (seed + query alla sua sede w % N, fuori dal tempo misurato) ed esegue **in sequenza** il ciclo commit → dispute → restore. Ogni richiesta è un cambio di stato; dispute e restore fanno fan-out a tutti i siti.
- Cella: `ops_per_worker = 3·max(10, 300 // W)`, cioè 900 richieste per ripetizione a W=1 e W=10, 1 500 a W=50, 3 000 a W=100. 5 ripetizioni, fatti nuovi per ripetizione. Warm-up: un ciclo per writer su fatti separati, scartato.
- Restano uguali allo sweep di audit 123: N ∈ {1, 2, 5, 10}, W ∈ {1, 10, 50, 100}; trasporto (`http`, poi `mtls`); identità; topologia generata nella cartella del run; hash di `service.py` dentro ogni container a inizio e fine (`83d8c99a`); campionamento di CPU e memoria; nessun retry.
- Pilot esplorativo (N=1, W=10, 1 ripetizione, non conteggiato): 900/900 con esito 200 e cambio di stato, 202 richieste/s.

## Ipotesi e criteri
- **H-L0**: hash `83d8c99a` in ogni container.
- **H-L1 (correttezza sotto carico)**: in ogni cella ogni richiesta è un 2xx che cambia stato. Un 409 conta come errore **inatteso** (corsa nel servizio o nel harness) e falsifica H-L1 per quella cella; lo stesso vale per un 5xx, un timeout o un errore di trasporto. Previsione: 0.
- **H-L2 (effetto della distribuzione)**: rapporto del throughput a N=2, 5, 10 contro N=1, a W=50 e 100, con IC bootstrap al 95 % come in audit 123. Previsione esplorativa: **nessun guadagno o una perdita**, perché due richieste su tre (dispute e restore) passano dal servizio condiviso e fanno fan-out sincrono a tutti gli N siti.
- **H-L3**: si applica la regola H-S4 di audit 123 per attribuire il collo di bottiglia.
- **Descrittive**: latenza per operazione (p50/p95/p99), CPU e memoria.
Analisi: `analyze.py` invariato (stesso schema del manifest). Nessuna esclusione.
