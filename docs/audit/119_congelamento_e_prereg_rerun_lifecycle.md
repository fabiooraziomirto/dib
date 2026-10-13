# Audit 119 — Versione di riferimento congelata e pre-registrazione del rerun di restoration ablation e offline veto

Data 2026-10-13. Branch `tnsm-final-campaigns` (worktree `/root/Desktop/DIB_tnsm_final`), creato da `tnsm-merged` @ `2f58f8f`. Nessun file di `code/src`, `formal/`, `results/`, `claims.json` modificato da questo audit.

## 1. Verifica iniziale (osservazioni del commit `2f58f8f`: ancora attuali)

| Controllo | Esito oggi |
|---|---|
| `git status` | pulito, HEAD `2f58f8f188ec6aad37196f35dde7634ca729dc2d` |
| `python3 scripts/verify_artifact.py` | **264 passed, 2 failed** (uguale a quanto riportato) |
| fallimento 1 | `ablation source matches packaged service`: `results/restore_ablation/results.json` registra `31863043…`, il checkout ha `3ffa57ee…` (`scripts/verify_artifact.py:257`) |
| fallimento 2 | `offline veto: service matches packaged distributed service`: stessa coppia di hash (`scripts/verify_artifact.py:330`) |
| suite (`cd code && pytest tests`, Python 3.10.13) | **507 passed, 7 skipped, 8 xfailed** in 43.8 s |

Origine dei due hash (storia di `code/src/dib/registry/distributed/service.py`, `git log`):
- `31863043…` = commit `9413c20` (2026-10-10, mTLS step 2). I due `results.json` sono stati rigenerati su questo file dal commit `b29bade` ("regenerated on the frozen service.py").
- `3ffa57ee…` = commit `864101f` (2026-10-12, ultimo cambiamento: 4xx dell'evidence → 502). Fra i due ci sono 6 versioni intermedie (`05427d0f`, `0501b383`, `a6bb1d22`, `5599f53b`, `f7987d95`, `425f5966`), fra cui l'integrazione della FSM corretta (`dc3dd20`: `/query` con staging, `/commit` in due fasi, guardie di `/local_restore`).

Quindi i due fallimenti sono reali: **le evidenze impacchettate non sono state prodotte dal servizio corrente**. Non è un problema dell'hash atteso.

Altre provenienze verificate:
- `results/site_count/manifest.json` registra `service.py` `54f635cb…` (anteriore all'import v43, `d09f8db…`) e `distributed_concurrency_benchmark.py` `074455a0…` (oggi `035ab45e…`): lo sweep storico è di un altro servizio **e** di un altro benchmark.
- Le campagne del nodo fino a R1d hanno eseguito `31863043…` dentro i container (audit 104); R1e, R1f, B2k-finale verificano lo sha dentro gli 11 container (`run.py` `verify_service_image`, commit `c898ea8`).
- Il testbed OpenWrt locale: l'immagine `18_openwrt_enforcement-router` (2026-08-08) è di un altro progetto compose; il compose di `openwrt/` costruisce `openwrt-router`. Nessuna immagine `dibtnsm-*` è presente su questo host: ogni campagna Docker qui costruisce le immagini e verifica gli hash dentro i container (sez. 3).

## 2. Versione di riferimento (congelata)

| Oggetto | sha256 |
|---|---|
| commit | `2f58f8f188ec6aad37196f35dde7634ca729dc2d` (nessun diff) |
| `code/src/dib/registry/distributed/service.py` | `3ffa57ee549512e4d3341738c8ec052a86a3c11f4a05f37f82614868fc822af8` |
| `code/src/dib/registry/distributed/mtls.py` | `4833dae39a4a592cda82b7dc1a22663d5b2c1f2ade58014d1c1fe0060812b7c9` |
| `code/src/dib/registry/distributed/Dockerfile` | `50adfd9dd41d4a7a9d19a992684bd7d108973318979b0ec7749671b327a8a5a9` |
| `code/src/dib/registry/distributed/generate_compose.py` | `22c5be5ab390c17c1b38d77bf20c9e3cd4138e44c5d8b41bdbb1ecdcf64c4541` |
| `code/scripts/v36_restore_ablation.py` | `8387487e799871a4a5ba1bdc1dfbfbe494d4922cba428afeeff83f8ddff51266` (= storico) |
| `code/scripts/offline_veto_reconciliation.py` | `ae9fc1431bf98f410b1c521bd48825386146f04a3ad06186d1807f1fcd006cf8` (= storico) |
| `code/scripts/v35_lifecycle_experiment.py` | `b00e87e6f0636f8d45b39a369895134aebf6ffc3940d4fcf4a07867b21b5cd73` |
| `openwrt/Dockerfile.router` | `029f6b7dc321aeb2627de79a206b6f8b0719da4963d6034993589ee0c56309c3` |
| `openwrt/router-entrypoint.sh` | `31ef6803967c8e6eb0f278a841daba41063be60edf5e03cfc0c65ae02907659a` |

Ambiente: host LXC su Proxmox (kernel 6.8.12-18-pve), AMD EPYC 7313, 16 core assegnati (`nproc`), 64 GiB; Docker 28.2.2, Compose 2.40.3. Python delle misure: `/opt/conda/envs/dib312/bin/python` 3.12.15 (fastapi 0.128.8, uvicorn 0.51.0, httpx 0.28.1, starlette 0.52.1, pydantic 2.12.5). **Carico concorrente**: l'host esegue ~30 container di altri progetti (Stack4Things/IoTronic, Open WebUI); load average 8–10 all'avvio. Non vanno toccati; il carico è registrato in ogni manifest e le misure di tempo non vanno confrontate con quelle del nodo.

Regola: se `service.py`, `mtls.py` o il Dockerfile cambiano durante il lavoro, ogni risultato di questo branch prodotto prima del cambiamento va rigenerato (elenco in audit finale). Obiettivo: nessun cambiamento.

## 3. Regola di provenienza per le campagne di questo branch

- In-process (TestClient): hash del file caricato (`spec_from_file_location` sullo stesso path di cui si calcola lo sha).
- Processi uvicorn: `importlib.util.find_spec("dib.registry.distributed.service").origin` con lo stesso `PYTHONPATH` del sottoprocesso, e sha di quel file.
- Container: `docker exec <c> sha256sum /app/service.py /app/dib/registry/distributed/mtls.py` per **ogni** container dopo l'avvio e alla fine; una differenza dall'albero ferma la campagna (nessun dato conteggiato).
- I risultati storici restano dove sono; ogni nuova campagna va in `experiments_tnsm/<nome>_20261013/`. Niente scritture in `results/`.

## 4. Pre-registrazione A — rerun di restoration ablation e offline veto (confermativo)

**Domanda.** Le proprietà di lifecycle verificate dalle campagne v36 (ablation) e v42 (offline veto) valgono sul servizio di riferimento `3ffa57ee…`, che ha cambiato `/query`, `/commit` e `/local_restore` dopo `31863043…`?

**Configurazione.** Generatori invariati (sha sopra, uguali a quelli storici). Ablation: 3 politiche (`persistent_approval`, `review_reset`, `dib`) × 3 tempi del veto (`before`, `during`, `confirmed`) × {consegna completa, site-2 perde l'intero episodio} = 18 casi deterministici, TestClient + SQLite reale + serializzatore MUD. Offline veto: 3 processi sito + 1 evidence uvicorn su loopback, kill/restart del sito con il veto, SQLite persistente; **30 trial** (originale: 10; il costo è di secondi). Python 3.12.15. Wrapper: `experiments_tnsm/lifecycle_rerun_20261013/run.py` (scrive manifest e provenienza; non modifica i generatori).

**Metriche e criteri (tutti devono valere; nessun adattamento dopo):**
- A1 (nessun export senza fresh commit): ablation, export del soggetto dopo restore/reconcile prima di un nuovo commit = 12/18 per `persistent_approval`, **0/18** per `review_reset`, **0/18** per `dib` (valori storici, `results/restore_ablation/README.md`).
- A2 (veto locale preservato): 6/6 `persistent_approval` (stessa protezione per costruzione), **0/6** `review_reset`, **6/6** `dib`; offline veto: veto con `origin=local` dopo il restart in 30/30.
- A3 (Active stantio invalidato dopo un episodio interamente perso): offline veto, il fatto Active torna `monitor-only` e non esporta in 30/30; ablation, site-2 disconnesso non esporta in tutti i casi `dib`.
- A4 (fatto estraneo esportabile): `control_aces == [1,1,1]` in ogni passo di ogni caso; offline veto `unrelated == [1,1,1]` 30/30.
- A5 (idempotenza): secondo `/reconcile` = 0 elementi (ablation casi disconnessi, offline veto 30/30).
- A6 (replay obsoleto senza effetto): `/apply_fanout` con seq 1 non cambia stati né export (tutti i casi, 30/30).
- A7 (veto non aggirabile con commit diretto): `/commit` sul fatto vetato → 409 in 30/30 (offline veto); `/local_restore` durante l'episodio → 409 in 18/18 (ablation).
- Provenienza: `service_sha256` = `3ffa57ee…` nei due JSON **e** origine del modulo dei sottoprocessi = `code/src/.../service.py` con lo stesso sha.

**Esclusioni e retry.** Nessuna esclusione. Nessun retry: un'eccezione o un assert fallito in un caso è un fallimento della proprietà (o del harness) e si riporta come tale, con traceback; la campagna non si rilancia per ottenere un esito diverso. Unica eccezione ammessa: impossibilità di avviare i processi (porta occupata) **prima** del primo trial, documentata.

**Natura.** Sono casi controllati, deterministici o quasi (processi reali, ordine sequenziale): i conteggi sono **esiti di casi**, non stime di affidabilità né tassi di errore.

**Verificatore.** Si aggiunge un blocco che controlla le nuove evidenze (hash del servizio, dei generatori, del JSON, conteggi A1–A7). I due controlli storici che oggi falliscono **restano** e continuano a fallire: dicono il vero (le evidenze in `results/` vengono da `31863043…`). Il verificatore li riporta in una sezione separata "evidenza storica sostituita" con il puntatore alla nuova campagna, senza cambiare l'hash atteso e senza contarli come passati.
