# Audit 123 — Pre-registrazione: sweep del numero di siti sul servizio finale (management-path benchmark)

Data 2026-10-13, prima dello sweep. Harness: `experiments_tnsm/site_sweep_20261013/` (`mgmt_bench.py`, `sweep.py`, `test_mgmt_bench.py`: 10 passed). Servizio: audit 119 (`service.py` `3ffa57ee…`). Lo sweep parte solo dopo la fine delle campagne gateway (audit 121): una campagna temporizzata alla volta su questo host.

## 1. Perché rifarlo
Lo sweep storico (`results/site_count/`) ha tre problemi che impediscono di usarlo per il servizio finale:
1. servizio diverso: `service.py` `54f635cb…` (precedente all'import v43), benchmark `074455a0…` (`results/site_count/manifest.json`);
2. `contribute` è un no-op lato client contato al denominatore (2 operazioni su 20; `code/scripts/distributed_concurrency_benchmark.py:14-15`, `:142-143`);
3. ogni risposta diversa da 403 conta come successo (`distributed_concurrency_benchmark.py:154-156`): i 409 di `/commit` su un fatto già Active e di `/restore` su un fatto non disputato contano come operazioni riuscite e veloci.
Inoltre le percentili sono medie per ripetizione di percentili da 20·W richieste, e non ci sono misure per tipo di operazione, CPU o memoria.

## 2. Correzioni (solo harness; il servizio non cambia, nessun endpoint aggiunto)
- Mix = `_MIX_REALISTIC` senza `contribute` (18 voci: query 8, commit 7, attest 1, dispute 1, restore 1). Il prototipo distribuito non ha un endpoint di osservazione: questo è un **management-path benchmark**.
- Classificazione: `ok` (2xx), `rejected` (409, conflitto di lifecycle previsto dall'API), `error` (altro status, compresi 403 e 5xx), `timeout`, `transport`. `applied` registrato quando presente.
- Throughput riportati: richieste tentate/s (tutte le richieste arrivate in rete), `ok`/s, cambi di stato/s (commit 200, restore 200, attest 200, dispute 200 con `applied=true`).
- Record grezzi per richiesta → p50/p95/p99 per cella (5 ripetizioni unite) e per tipo di operazione.
- Numerosità per cella: `ops_per_worker = max(20, 1000 // W)` (W=1: 1000; W=10: 100; W=50, 100: 20 come lo storico), così ogni cella ha ≥ 5000 richieste misurate e il p99 è stimabile.
- Invariati rispetto allo storico: stack (FastAPI/uvicorn 1 worker per container, SQLite), trasporto (httpx, client condiviso, timeout 5 s), seeding, warm-up 20 operazioni per worker scartato, 5 ripetizioni, routing `worker % N`, nessun retry.
- Topologie: compose generato da `generate_compose.py` per N nella cartella del run (progetto `dibsweep`; il compose versionato in `code/src` non viene toccato), volumi rimossi fra topologie. Hash di `service.py`/`mtls.py` dentro **ogni** container all'avvio e alla fine di ogni N (differenza = stop).
- Risorse per ripetizione: CPU-secondi di ogni container (cgroup v2 `cpu.stat`), `memory.current` massimo (campionato ogni 0,5 s) e `memory.peak`, CPU-secondi del processo generatore di carico, frazione di CPU dell'host occupata, load average.

## 3. Celle e ordine
Trasporto `http` (stesso trasporto dello storico), poi `mtls` (PKI di `make_dist_pki.py`, identità per sito e admin). N ∈ {1, 2, 5, 10} × W ∈ {1, 10, 50, 100} × 5 ripetizioni. N = 1 è una baseline di processo: un consortium di un sito non soddisfa il quorum di due siti.

## 4. Domande e criteri
- **H-S0 (provenienza).** Ogni container esegue `3ffa57ee…`. Altrimenti lo sweep non conta.
- **H-S1 (descrittiva).** Throughput tentato, `ok`, cambi di stato; latenza per tipo e aggregata (p50/p95/p99); rifiuti attesi; errori inattesi, timeout.
- **H-S2 (effetto della distribuzione, confermativa).** Lo storico affermava un guadagno 1,63–1,75× a 50 e 100 writer, realizzato già a N = 2. Qui: rapporto fra throughput tentato a N = 2 e N = 1, a W = 50 e W = 100, con IC al 95 % bootstrap sulle 5 ripetizioni per lato (10 000 ricampionamenti, seed 20261013). "La distribuzione aumenta il throughput" si afferma solo se il limite inferiore dell'IC > 1. Stesso calcolo per N = 5 e N = 10 contro N = 1. Previsione (esplorativa): guadagno minore dello storico, perché `/commit` ora fa due letture dell'evidence (`service.py:574` e `:589`), il servizio condiviso.
- **H-S3 (errori).** Errori inattesi (error + timeout + transport) per cella, con tipo. Nessuna soglia: si riportano tutti; un errore in una cella impedisce di descriverla come "error-free".
- **H-S4 (attribuzione del collo di bottiglia, regola fissata ora).** Un componente si può chiamare collo di bottiglia di una cella solo se (a) il suo uso di CPU è ≥ 0,85 core in media sulla ripetizione (un processo uvicorn con un worker è legato al GIL), (b) il throughput non cresce più di 10 % passando a W più alto, e (c) il generatore di carico usa < 0,85 core. Se (c) non vale, la cella è limitata (anche) dal client e nessun componente del servizio viene indicato. Se nessun componente soddisfa (a), si scrive "non attribuibile".
- **Confronti vietati.** Nessun confronto diretto con benchmark in-process (stack e mix diversi), né con lo sweep storico come "prima/dopo" del codice (cambiano servizio, mix e classificazione insieme): lo storico si cita solo come evidenza sostituita.

## 5. Validità, esclusioni, retry
Nessuna esclusione di richieste o ripetizioni. Un fallimento infrastrutturale (compose up, health, hash) prima di registrare celle di un N ferma lo sweep di quel trasporto; si rilancia una sola volta l'intero trasporto, documentandolo. Carico concorrente: l'host esegue altri progetti (load average ~10 su 16 core); è registrato per ripetizione e limita la generalità dei numeri assoluti (un solo host, nessun WAN: separazione di processi, non distribuzione geografica).

## Addendum 1 — dispute flood sul servizio valutato (prima del lancio; dopo lo sweep)
Scopo: sostituire il placeholder di `main_10p.tex:499` ("withdrawal-time and read-throughput figures") con una misura sul servizio `83d8c99a`. L'evidenza storica `results/dispute_flood` non registra alcun hash.
Generatore `code/scripts/dispute_flood.py` invariato: 100 fatti, 10 siti, HTTP; il generatore non supporta mTLS. 5 ripetizioni, ognuna su una topologia nuova; hash verificato nei container prima e dopo (`experiments_tnsm/dispute_flood_20261013/flood_run.py`). Il wrapper conta gli status HTTP dai log di accesso dei container, perché il generatore non classifica le letture legittime.
Criteri:
- H-D1, blast radius: 100/100 dispute applicate; export da 100 a 0 ACE in tutti i 10 siti; dopo il recovery di nuovo 100; recovery = 11 richieste per fatto (1 restore + 10 commit). Deve valere in 5/5.
- H-D2: nessuno status 5xx in nessun container.
- Descrittive: tempo del flood (100 dispute, una identità, un thread), throughput e p50/p99 delle letture legittime a riposo e durante il flood, tempo di recovery. Riportate come mediana e intervallo fra le 5 ripetizioni.
Nessun retry; nessuna esclusione.
