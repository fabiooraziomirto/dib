# Audit 127 — Sweep dei siti (management path), dispute flood e smoke gateway sul servizio `83d8c99a`: risultati

Data 2026-10-13. Pre-registrazioni: audit 123 (sweep), 123 addendum 1 (flood), 126 addendum 1 (smoke). Servizio misurato `83d8c99a…` (`service.py` con la guardia di audit 126), verificato **dentro ogni container** all'inizio e alla fine di ogni topologia e ripetizione. Host condiviso (load average 10–15 durante lo sweep; frazione di CPU dell'host occupata 0,22–0,63), una campagna alla volta.

## 1. Smoke gateway (5 episodi per profilo)
15/15 episodi completi. Hash `83d8c99a` negli 11 container all'inizio e alla fine. H-G1, H-G3, H-G4 e H-G5 valgono in 5/5 per profilo. Mediane di t2: 5,498 / 5,899 / 6,533 s, contro 5,494 / 5,875 / 6,504 s su `3ffa57ee` (audit 122): la previsione ±10 % regge (differenze < 1 %). Dati: `experiments_tnsm/gateway_withdrawal_20261013/smoke_83d8c99a_*`, `analysis_smoke_83d8c99a/`.

## 2. Sweep dei siti (`experiments_tnsm/site_sweep_20261013/{http,mtls}`, analisi `analysis_{http,mtls}/`)
Esecuzione:
- `http`: 16 celle × 5 ripetizioni, 100 000 richieste misurate (commit `e1ad277`).
- `mtls`: il primo tentativo si è fermato **prima di qualsiasi cella**. Era un errore del mio harness: `code/src` mancava dal path in `sweep.up`. È conservato in `mtls_attempt1_failed/` e il trasporto è stato rilanciato una volta, come ammesso dalla regola pre-registrata (commit `a126a15`). Il rilancio è completo: 100 000 richieste.
- **H-S0 regge**: `83d8c99a` in ogni container di ogni N, all'inizio e alla fine.

### Throughput tentato (richieste/s, media ± sd su 5 ripetizioni) e p50/p99 (ms, tutte le richieste della cella)
| N | W | http | http p50/p99 | mtls | mtls p50/p99 |
|---|---|---|---|---|---|
| 1 | 1 | 109,7 ± 6,6 | 8,2 / 23,0 | 200,9 ± 6,2 | 4,7 / 9,1 |
| 1 | 10 | 248,6 ± 13,3 | 40,0 / 92,2 | 409,9 ± 12,0 | 23,8 / 50,9 |
| 1 | 50 | 272,9 ± 6,5 | 202,5 / 285,9 | 335,0 ± 6,6 | 164,2 / 233,0 |
| 1 | 100 | 271,8 ± 9,6 | 412,6 / 545,3 | 315,6 ± 5,6 | 352,7 / 461,5 |
| 2 | 50 | 517,3 ± 14,8 | 90,7 / 204,6 | 499,2 ± 12,0 | 98,8 / 161,1 |
| 2 | 100 | 522,5 ± 6,2 | 164,4 / 409,3 | 486,6 ± 12,0 | 204,2 / 307,8 |
| 5 | 50 | 656,7 ± 14,4 | 76,1 / 124,5 | 511,1 ± 5,9 | 98,9 / 146,5 |
| 5 | 100 | 682,7 ± 8,6 | 129,5 / 314,0 | 501,2 ± 9,5 | 199,8 / 283,3 |
| 10 | 1 | 67,4 ± 0,8 | 9,6 / 62,0 | 137,1 ± 1,9 | 5,4 / 24,8 |
| 10 | 50 | 680,2 ± 23,4 | 73,3 / 124,5 | 525,0 ± 17,1 | 95,9 / 144,8 |
| 10 | 100 | 670,2 ± 9,6 | 133,4 / 321,0 | 533,7 ± 3,7 | 191,2 / 263,5 |
Tabelle complete, con `ok`/s, cambi di stato/s, 409, errori, core di client/evidence/sito e memoria: `analysis_{http,mtls}/table.md`, `cells.csv`; latenze per tipo di operazione in `per_op.csv`.

### Ipotesi
- **H-S2 (la distribuzione aumenta il throughput tentato), regge in entrambi i trasporti.** Rapporto contro N=1 [IC bootstrap 95 %]:
  - http, W=50: N=2 1,90× [1,84, 1,95], N=5 2,41×, N=10 2,49×;
  - http, W=100: N=2 1,92×, N=5 2,51×, N=10 2,47×;
  - mtls: da 1,49× [1,46, 1,53] (N=2, W=50) a 1,69× [1,67, 1,71] (N=10, W=100).
  
  Tutti i limiti inferiori sono > 1. A W=1 la distribuzione **costa**: http da 109,7 (N=1) a 67,4 richieste/s (N=10), perché dispute e restore aspettano il fan-out a ogni sito.
- **H-S3 (errori inattesi).**
  - http: 2 su 100 000, entrambi `ReadError` di trasporto su una richiesta a un sito, a W=100 (uno a N=5, uno a N=10). Causa non diagnosticata.
  - mtls: 0 su 100 000.
  - Nessun timeout. Nessun 5xx. Nessun 403.
- **H-S4 (attribuzione del collo di bottiglia).**
  - Nelle celle più cariche il generatore di carico usa ≥ 0,85 core: http, N ≥ 5 con W ≥ 50 e N=2 con W=100; mtls, quasi tutte le celle con W ≥ 50, fino a 1,5 core. Per la regola pre-registrata **queste celle non si attribuiscono al servizio**.
  - La regola assegna "evidence service" solo a tre celle mtls (N=1 W=10; N=5 e N=10 con W=50: evidence ≥ 1,04 core e throughput fermo). La cella successiva (W=100) di queste è però limitata dal client.
  - **L'affermazione storica "the shared evidence service is the remaining bottleneck" (`results/site_count/README.md`) non è sostenuta da queste misure.**
- **Memoria massima**: evidence 88 MiB (http) / 93 MiB (mtls); sito 150 / 113 MiB.

### Limiti scoperti dall'analisi (da riportare)
- **Composizione effettiva del carico.** Il mix ereditato accoppia per indice operazione ed endpoint: il dispute cade sempre su `ep-4`, il restore sempre su `ep-2`. Dopo il warm-up quasi nessun commit cambia stato. Su 39 580 commit per trasporto ne riescono 245 (http) e 335 (mtls); il resto è 409. I restore riescono nel 40 % dei casi (2 048 su 5 100). Il benchmark misura quindi letture, attest, dispute e soprattutto i **percorsi di rifiuto** di commit e restore; i cambi di stato sono 11–67/s. Il benchmark storico contava tutti questi 409 come successi.
- **http e mtls non sono a parità di stack.** Con mTLS il servizio parte con `python -m dib.registry.distributed.mtls` (protocollo h11 di uvicorn); in http con `uvicorn service:app`. A basso carico mtls risulta più veloce (W=1: 201 contro 110 richieste/s). Per la regola già in vigore nessun "costo di mTLS" va nel paper. I due trasporti si riportano separatamente.
- **Un solo host, nessun WAN.** È separazione di processi, non distribuzione geografica. Il generatore di carico (un processo Python) limita le celle alte.
- Nessun confronto con lo sweep storico (`54f635cb`, mix con `contribute`, nessuna classificazione) né con benchmark in-process.

## 3. Dispute flood (`experiments_tnsm/dispute_flood_20261013/`, 5 topologie nuove, http, generatore invariato)
- **H-D1 regge 5/5**: 100/100 dispute applicate; export da 100 a 0 ACE in tutti i 10 siti; dopo il recovery di nuovo 100; 11 richieste per fatto.
- **H-D2 regge**: nei log di accesso di tutti gli 11 container compaiono solo status 200.

| Grandezza (5 ripetizioni) | mediana | intervallo |
|---|---|---|
| 100 dispute di una identità, un thread (1 000 record sospesi) | 5,16 s | 4,77–5,63 s |
| letture legittime a riposo | 662 op/s, p99 29,4 ms | 612–685 op/s; p99 25,8–30,8 ms |
| letture legittime durante il flood | 228 op/s, p99 74,5 ms | 212–259 op/s; p99 71,3–89,9 ms |
| recovery (100 restore + 1 000 commit) | 23,9 s | 23,4–24,1 s |

Il generatore non ha mTLS: è una misura senza autenticazione. Non va confrontata con `results/dispute_flood` (11,3 s), che ha un servizio diverso e senza hash.

## 4. Evidenze sostituite
`results/site_count/*` e `results/distributed/*` (servizio `54f635cb`) sono sostituiti da §2 per il servizio valutato. `results/dispute_flood/` è sostituito da §3. I file storici restano dove sono.
