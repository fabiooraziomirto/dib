# Audit 04 — Piano delle misure di prestazione per TNSM (solo piano, nulla eseguito)

Data: 2026-10-10. Branch `revision-tnsm`. Il numero 04 era riservato al piano di misure (`docs/audit/05_reconcile_trigger_fanout.md:3`). **Nessuna misura è stata lanciata.** Le misure partono solo dopo le porte di decisione della sez. 0 e dopo un tuo OK esplicito (`CLAUDE.md`, fase TNSM: "solo dopo il mio OK, esecuzione").

Fonti lette: `results/concurrency/`, `results/distributed/`, `results/architecture/`, `results/site_count/` e i loro manifest; `code/scripts/fsm_concurrency_harness.py`, `distributed_concurrency_benchmark.py`, `p99_tail_breakdown.py`; l'output del p99 fuori repo in `/root/Desktop/DIB_reframe/reproducibility/experiments/40_p99_tail_breakdown/`; `docs/work/DIB_piano_completo.md` §5.4, §7.2, §7.5, §7.6.

## 0. Porte di decisione (prima di qualsiasi misura)

| Porta | Condizione per aprirla | Stato oggi | Chi decide |
|---|---|---|---|
| **G0: service.py definitivo** | mTLS implementato (piano §6) e nessun'altra modifica prevista a `code/src/dib/registry/distributed/service.py`. Hash congelato nel manifest di ogni misura | **chiusa.** sha256 attuale `48415497…`; nessuna riga TLS, SSL o cert nel file (grep); mTLS da fare | utente |
| **G0b: rigenerazione unica** | Dopo G0: rigenerare `results/restore_ablation` e `results/offline_veto` (`docs/work/regenerate-results-after-service-changes.md`, voci 1–4). `verify_artifact.py` deve tornare a 262/0 | chiusa (dipende da G0) | utente |
| **G1: versione di Python** | Scegliere: **(A)** misurare su CPython 3.12, come dichiara `code/pyproject.toml:9` (`requires-python = ">=3.12"`), oppure **(B)** correggere la dichiarazione (D18) e misurare su 3.10.13 | aperta. Sul disco: 3.10.13 (default) e `/usr/bin/python3.11`; **3.12 assente** | utente |
| **G2: secondo host** | Avere un secondo host o VM per separare il generatore di carico dai servizi, oppure accettare un host solo con CPU pinning dichiarato | aperta. Nessun secondo host Linux attivo (sez. 4.1) | utente |
| **G3: netem praticabile** | Verificare che `tc qdisc ... netem` funzioni sulle interfacce dei container dentro l'LXC (serve `sch_netem` nel kernel dell'host Proxmox e la capability `NET_ADMIN`) | non verificato. `tc` c'è (`/usr/sbin/tc`); comando di prova da autorizzare | utente |
| **G4: host quieto** | Fermare, o almeno registrare, gli altri carichi sull'host durante le misure | aperta. All'ispezione girano container di altri progetti (`iotronic-*`, `keystone-domain-c`, `crossbar-domain-c`, …); load average 3,3 / 4,6 / 4,7 | utente |

**Raccomandazione per G1.** (A): il paper dichiara l'ambiente del `pyproject`, e le prestazioni di CPython cambiano fra 3.10 e 3.12. Costo: installare 3.12 in un ambiente separato (conda o venv, fuori dalla repo; **richiede il tuo OK**, regola "non installare dipendenze senza chiedere"), poi rieseguire su 3.12 la suite (412 test) e `verify_artifact.py` prima di qualsiasi misura. Se scegli (B), la modifica a `pyproject.toml` è tua (fuori da `src/`, ma sempre codice).

**Aggiornamento 2026-10-10 (audit 14).**
- G0 chiusa: `service.py` congelato a sha256 `3186304363ed…`.
- M1 (configurazione di default) fermato a 40 celle su 50, che si conservano senza analizzarle (`experiments_tnsm/m1_single_node/aborted_20261010/`).
- Nuovo ordine: G0b, M3/M4, M6/M7 (disegno fattoriale con netem per container), federazione sintetica, M5, M1/M2 ridotti a due bracci. Piano completo e GATE in `14_priorita_esperimenti_tnsm.md`.

## 1. Cosa è stato misurato e con quali limiti (a)

| Misura | Cosa | Ripetizioni | Codice misurato vs codice attuale | Limiti |
|---|---|---|---|---|
| **Concorrenza single-node** (`results/concurrency/`, claim `claims.json:195`) | `services.py` chiamato in-process da thread, SQLAlchemy + un file SQLite, mix uniforme di 6 operazioni, writer 1/10/50/100, 20 operazioni per worker, warm-up 20 | **3** | manifest `services_sha256 = bea8a575…`; attuale e v43 `609b8043…` → **misurato su un `services.py` diverso da quello della repo**. Harness uguale (`37a6ebe9…`) | Niente HTTP. A 1 writer il p99 su 20 campioni è in pratica il massimo. p99 a 100 writer 5895 ± 191 ms con mediana 3,8 ms |
| **Scomposizione del p99** (`40_p99_tail_breakdown`, fuori repo) | Stessa sweep con tempo di commit e tentativi di retry per operazione | **3** | `python_version` 3.10.13; hash dei sorgenti non registrato | A 100 writer: commit pari allo **0,02%** del p99, tentativi medi nella coda 1,08 (massimo 2). La coda è **attesa in serie, non retry né lavoro di commit**. Chi serializza (lock di SQLite o GIL) **non è isolato**: "p99 di 5,9 s dovuto a SQLite" è un'ipotesi, non una misura. Sono registrati 969 `InvalidStateTransition` a 100 writer (attesi dal mix? da verificare) |
| **Distribuito, 10 siti** (`results/distributed/`, claim `:211`) | 1 container evidence + 10 container sito, HTTP via `httpx.Client` (timeout 5 s), mix `_MIX_REALISTIC` (40% query) | **5** (e una corsa da 3) | manifest `service.py = 54f635cb…`, **diverso da ogni versione della repo** (v43 `d09f8db5`, poi `ecb06dd3`, `f6860bea`, `48415497`). Benchmark `80111012…` contro l'attuale `95970767…` | 1 errore inatteso a 50 writer. **Nessuna deviazione standard del throughput nel CSV**, eppure `claims.json:211` riporta "530.3 +/- 7.8 ops/s": **contraddizione** (il README la dichiara non riproducibile). `contribute` è un no-op contato nel throughput (2 operazioni su 20) |
| **Sweep sul numero di siti** (`results/site_count/`) | N = 1, 2, 5, 10; stesso stack | **5** | stessa epoca del precedente, pre-fix D11/D12/D19 | 6 errori su 64.400 operazioni. Tutto il guadagno si ottiene a N = 2; l'evidence service è il collo di bottiglia; a 1 writer 10 siti sono il 20,6% più lenti di 1 |
| **Architettura** (`results/architecture/`) | Thread con sharding e multiprocess ATTACH | **3** (mp: nessuna ripetizione) | **il manifest non ha hardware né hash** | mp: 6 errori su 100 operazioni |

**Limiti comuni.**
- Un solo host: container LXC su Proxmox, 16 vCPU, 64 GiB, generatore di carico e servizi co-locati.
- Python 3.10.13 contro `>=3.12` dichiarato.
- Nessuna WAN e nessuna perdita di pacchetti.
- Nessun mTLS.
- SQLite su ZFS con il pool al **94%**: ZFS rallenta quando è quasi pieno, il che è rilevante per il p99 di SQLite.
- Fan-out sequenziale di default (`DIB_DIST_FANOUT_CONCURRENCY` = 1, `service.py:146`).
- 20 operazioni per worker: troppo poche per un p99 stabile ai carichi bassi.

## 2. Misure da rifare (b) e ipotesi (c)

Regole comuni:
- **Output:** `experiments_tnsm/<nome>/`, mai in `results/`.
- **Manifest:** comando completo; seed; sha256 di `service.py`, `services.py`, harness, Dockerfile, compose e override; `python -VV`; `nproc`, `free -g`, `lscpu`; `docker version`; `uptime` e `docker ps` prima di ogni ripetizione (G4); data e ora UTC.
- **Ripetizioni:** **≥ 10** per ogni punto, ordine dei writer **randomizzato** in ogni ripetizione (seed nel manifest), database nuovo per ogni ripetizione, warm-up scartato. **200 operazioni per worker**, invece di 20: a 1 writer servono almeno 200 campioni perché il p99 sia diverso dal massimo.
- **Statistica:** l'unità è la ripetizione. Media del throughput e p50/p99 per ripetizione, con **IC 95% bootstrap percentile** (10.000 ricampionamenti sulle ripetizioni, seed dichiarato). Come dato secondario, il p99 sull'insieme delle operazioni con bootstrap sulle operazioni. Con 10 ripetizioni l'IC percentile è grezzo: per i punti del paper (100 writer) propongo 20 ripetizioni se il tempo lo permette. **Nessun confronto fra macchine diverse.** Il confronto con i risultati vecchi è solo descrittivo, perché il codice è diverso (sez. 1).
- **Prima di lanciare:** il docstring di ogni script nuovo dichiara ipotesi e criterio di falsificazione.

Tempi stimati dai tassi misurati in `results/` (ops/s) × 200 operazioni per worker, sommando i writer 1/10/50/100. Memoria stimata, da misurare con `docker stats` alla prima ripetizione.

| ID | Misura | Comando (bozza) | Ripetizioni | Tempo stimato | Memoria stimata | Output |
|---|---|---|---|---|---|---|
| **M1** | Concorrenza single-node (in-process) | `PYTHONPATH=code/src python3 code/scripts/fsm_concurrency_harness.py --skip-invariants --worker-counts 1,10,50,100 --repeats 10 --ops-per-worker 200 --warmup-ops 20 --output-dir experiments_tnsm/m1_single_node --label m1` | 10 | ~2 min per ripetizione (100 writer: 20.000 operazioni a ~320 ops/s ≈ 63 s), **~20 min** | < 1 GB | `experiments_tnsm/m1_single_node/` |
| **M2** | Scomposizione del p99 | `PYTHONPATH=code/src python3 code/scripts/p99_tail_breakdown.py --worker-counts 1,10,50,100 --ops-per-worker 200 --repeats 10 --output-dir experiments_tnsm/m2_p99_tail --label m2` | 10 | **~20–25 min** | < 1 GB | `experiments_tnsm/m2_p99_tail/` |
| **M2b** (opzionale) | Stesso harness con un database a scritture concorrenti (PostgreSQL) per isolare SQLite dal GIL (piano §7.6) | richiede un engine nuovo e una dipendenza (`psycopg`), più un container Postgres: **codice e dipendenza nuovi, da autorizzare** | 10 | ~25 min + setup | ~1 GB | `experiments_tnsm/m2b_postgres/` |
| **M3** | Distribuito, 10 siti, `service.py` definitivo | `docker compose -f code/src/dib/registry/distributed/docker-compose.yml [-f experiments_tnsm/m3/cpuset.override.yml] up -d --build`, poi `python3 code/scripts/distributed_concurrency_benchmark.py --worker-counts 1,10,50,100 --ops-per-worker 200 --warmup-ops 20 --repeats 10 --output experiments_tnsm/m3_distributed/throughput.csv`; due bracci: `DIB_DIST_FANOUT_CONCURRENCY` = 1 e = 10 | 10 per braccio | ~65 s per ripetizione (100 writer: 20.000 operazioni a ~530 ops/s ≈ 38 s) → ~11 min per braccio, più 3–5 min di build: **~30 min** | 11 container, stimati 1–2 GB | `experiments_tnsm/m3_distributed/` |
| **M4** | Costo di mTLS | M3 con mTLS attivo e spento, stessa immagine, stessi parametri | 10 per braccio | **~25 min** | come M3 | `experiments_tnsm/m4_mtls/` |
| **M5** | Numero di siti | `bash code/scripts/distributed_site_count_sweep.sh` esteso a N ∈ {1, 2, 5, 10, 20, 50} (richiede passare le ripetizioni e la directory di output: script nuovo in `experiments_tnsm/`, non quello in `code/scripts`) | 10 | ~11 min per N, più il rebuild: **~1,5 h** | N = 50: 51 container, stimati 3–5 GB | `experiments_tnsm/m5_site_count/` |
| **M6** | Tempo di ritiro e di riconciliazione (piano §5.4): dall'apertura della dispute alla rimozione della regola in ogni sito; riconciliazione dopo k episodi saltati, k ∈ {1, 2, 5, 10, 50} | script nuovo `experiments_tnsm/m6_retraction/run.py`: polling di `/state` con timestamp monotoni, oracolo I1–I3 (piano §7.2) | 10 per k | **~30–45 min** | come M3 | `experiments_tnsm/m6_retraction/` |
| **M7** | Rete degradata (S7): profili netem LAN; regionale 20 ms / 0,1%; WAN 80 ms / 1%; degradata 200 ms / 5%; partizione asimmetrica, durante S1 e S2 | M6 con `tc qdisc add dev <veth> root netem delay … loss …` per container (dopo G3) | 10 per profilo | **~1–1,5 h** | come M3 | `experiments_tnsm/m7_netem/` |
| **M8** | Firma MUD (piano §7.4): costo di sign e verify sul percorso di export | `openssl cms -sign/-verify` su N file esportati | 10 | minuti | trascurabile | `experiments_tnsm/m8_mud_sig/` |

Tutte le misure M3–M7 usano Docker e sono **comandi lunghi**: ognuna parte solo dopo il tuo OK, dopo G0, G1 e G4, e M7 anche dopo G3.

**Ipotesi e criteri di falsificazione** (da riportare nei docstring):
- **M1.** Il throughput single-node satura fra 50 e 100 writer: IC 95% sovrapposti a 50 e 100. *Falsificata se* il throughput a 100 supera quello a 50 oltre gli IC.
- **M2.** La coda p99 a 100 writer è attesa, non retry né commit: tentativi medi nella coda ≤ 1,5 e quota di commit nel p99 < 1%. *Falsificata se* una delle due soglie è superata.
- **M2b.** Con un database a scritture concorrenti il p99 a 100 writer scende di almeno 10 volte. *Falsificata se* la riduzione è < 10× (allora domina il GIL o il retry, non SQLite).
- **M3.** Con il fan-out parallelo (D11), il costo a 1 writer di N = 10 rispetto a N = 1 scende sotto il 10% (oggi è il 20,6%, misurato con codice vecchio). *Falsificata se* resta ≥ 10% con `FANOUT_CONCURRENCY` = 10.
- **M4.** Con connessioni riusate (`httpx.Client`), mTLS costa ≤ 20% di throughput a 100 writer e ≤ 5 ms di p50 a 1 writer. *Falsificata se* una delle due soglie è superata. Se il harness apre una connessione per richiesta, l'ipotesi va riscritta prima di lanciare.
- **M5.** Il guadagno si ferma a N = 2 perché l'evidence service è il collo di bottiglia: il throughput a N = 20 e N = 50 non supera N = 2 oltre gli IC. *Falsificata se* N ≥ 20 supera N = 2.
- **M6.** Il ritiro converge in tutti i siti online entro un fan-out (≤ 3 tentativi × 1 s, `service.py:120-121`). I siti offline convergono entro T + jitter dopo il ritorno (`service.py:142-143`), senza violazioni di I1–I3. Il costo di riconciliazione è circa costante in k. *Falsificata se* un sito online non converge entro 3 s, se un sito tornato online non converge entro 3T, se l'oracolo vede una violazione, o se il costo cresce in k oltre gli IC.
- **M7.** Con perdita fino al 5% e ritardo fino a 200 ms, ritiro e riconciliazione restano corretti (nessuna violazione). Il tempo di ritiro cresce di circa RTT × tentativi, senza perdita di regole. *Falsificata se* l'oracolo registra una violazione, o se una regola disputata resta esportabile dopo 3T.
- **M8.** Sign + verify costa < 10 ms per file MUD. *Falsificata se* il p95 supera 10 ms.

## 3. Rischi di validità (d)

1. **Co-locazione.** Generatore di carico, evidence e siti sullo stesso host da 16 vCPU. Il generatore usa thread Python: con 100 thread e TLS può essere il generatore stesso il collo di bottiglia, non il sistema. Mitigazioni:
   - registrare la CPU del processo generatore (`resource.getrusage`, `psutil` se presente);
   - CPU pinning con un **file di override del compose dentro `experiments_tnsm/`** (`cpuset`: generatore su 0–3, evidence su 4–5, siti sul resto), senza toccare `generate_compose.py` in `code/src`;
   - dichiarare il bias.
2. **Bias dell'host.** Container LXC dentro Proxmox, Docker annidato, altri progetti attivi (G4), ZFS al 94%. Mitigazioni: G4 (fermare o registrare i carichi), `uptime` e `docker ps` nel manifest per ogni ripetizione, scartare le ripetizioni con load average > 2 prima dell'avvio (regola da fissare prima).
3. **Deriva nel tempo.** Ordine dei writer randomizzato e bracci alternati (mTLS on/off, `FANOUT_CONCURRENCY` 1/10) per ripetizione, non in blocchi.
4. **Codice diverso dai risultati vecchi.** Nessun rapporto vecchio/nuovo nel paper (sez. 1).
5. **Mix di operazioni e `contribute` no-op.** Dichiararli. Riportare il throughput anche escludendo le operazioni no-op.
6. **Errori inattesi.** Classificarli per tipo (c'è già `41_distributed_error_classification` fuori repo) e non escludere le ripetizioni che ne hanno.
7. **Validità esterna.** Una macchina sola non dice nulla sulla scalabilità multi-organizzazione. M7 emula la rete, non l'eterogeneità degli host.

## 4. Infrastruttura disponibile

### 4.1 Secondo host o VM

- Tailscale: `mirto-llm-vnet170` (questo host); `arancino` (Linux, **offline da 125 giorni**); `controller` (Linux, **offline da 347 giorni**); `fab` (Windows, attivo); un iPhone. **Nessun secondo host Linux disponibile oggi.**
- Questo host: LXC (`systemd-detect-virt` = `lxc`), `cpu.max` = `max` (nessun limite), Docker 28.2.2 con cgroup v2.

Opzioni, da decidere tu:
- **(i)** un secondo LXC o VM sullo stesso nodo Proxmox: separa i processi, non l'hardware;
- **(ii)** un nodo fisico diverso, se esiste nel cluster Proxmox, come host del generatore e per le prove WAN reali;
- **(iii)** un host solo con pinning (sez. 3.1), dichiarato come limite.

Raccomandazione: (iii) subito; (ii) solo per M7 se è disponibile.

### 4.2 Versione di Python

Vedi G1: sul disco ci sono 3.10.13 e 3.11, non 3.12.

## 5. Ordine proposto (dopo le porte)

G0 → G0b (rigenerazione, `verify_artifact` 262/0) → G1 (suite su 3.12 se scelta A) → G4 → M1, M2 (in-process, nessun Docker) → M3, M4 → M5 → G3 → M6, M7 → M8. Un commit per misura, con docstring delle ipotesi prima del lancio e manifest dopo.

## 6. Contraddizioni trovate leggendo (vale il codice)

- `claims.json:211` "530.3 +/- 7.8 ops/s": il CSV citato (`results/distributed/throughput_distributed_5rep.csv`) non contiene la deviazione standard del throughput, e il README e il manifest dicono che il ± non è riproducibile.
- `results/distributed/README.md` cita `throughput_distributed_3rep.csv`; nella cartella il file si chiama `throughput_distributed.csv`. L'hash `c458a3eb…` coincide con la voce `_3rep` del manifest.
- `results/distributed/manifest.json`: `service.py = 54f635cb…`, che non corrisponde a nessuna versione nella storia della repo. `results/concurrency/manifest_v28_performance.json`: `services_sha256 = bea8a575…`, diverso dal file attuale `609b8043…` (identico a v43).
- Docstring di `fsm_concurrency_harness.py` (riga 20): "the minimal fix is applied to services.py" durante le prove. Le misure del piano **non** devono correggere nulla: se un invariante cade, si riporta (regola della repo).

## 7. Esiti delle porte (aggiornamento 2026-10-10)

### 7.1 G1: Python 3.12 (opzione A, decisione utente)

**Ambiente.** `/opt/conda/envs/dib312`, fuori dalla repo, creato con `conda create -p /opt/conda/envs/dib312 python=3.12`. Interprete: `Python 3.12.15 | packaged by Anaconda, Inc. | (main, Oct 1 2026) [GCC 14.3.0]`. Ho installato con pip le **stesse versioni** dell'ambiente 3.10 per i pacchetti diretti: pandas 2.3.3, numpy 2.2.6, networkx 3.4.2, scipy 1.15.3, matplotlib 3.10.1, scikit-learn 1.7.2, fastapi 0.128.8, starlette 0.52.1, pydantic 2.12.5, uvicorn 0.51.0, SQLAlchemy 2.0.51, psycopg 3.3.4, PyYAML 6.0.3, httpx 0.28.1, pytest 9.0.2, tldextract 5.3.1, openpyxl 3.1.5.

Le dipendenze transitive sono state risolte da pip. Fra i 50 pacchetti in comune, 24 hanno versioni diverse, fra cui anyio 4.12.1 → 4.15.1, pyparsing 2.4.7 → 3.3.3, urllib3 2.6.3 → 2.8.0, typing_extensions 4.15.0 → 4.16.0, idna 3.11 → 3.20 e certifi 2026.1.4 → 2026.7.22. Il `pip freeze` completo delle due versioni va nel manifest di ogni misura.

| Controllo | 3.10.13 | 3.12.15 |
|---|---|---|
| `pytest code/tests` | 412 passed (~22 s) | **412 passed** (18,8 s), **1 warning**: `DeprecationWarning` di `starlette/testclient.py:45` (`anyio.abc.BlockingPortal` deprecato in anyio 4.15) |
| `verify_artifact.py` | 260 passed, 2 failed | **identico byte per byte** (`diff` vuoto): 260 passed, gli stessi 2 failed (hash di `service.py`) |
| `verify_artifact.py --with-tests` | — | 261 passed, 2 failed (gli stessi) |
| `pytest analysis_fs` | 72 passed, 2 skipped, 9 xfailed | 72 passed, 2 skipped, 9 xfailed |
| `fs_binomial.py` rigenerato vs CSV committato | 8 righe diverse di 1 ulp | **identico** |

**Differenze trovate.**
1. Il warning di anyio (nessun effetto sui risultati).
2. La somma `sum()` sui float. Da 3.12 è compensata (Neumaier), e questo spiega lo scarto di 1 ulp di `fs_binomial.csv`: con `math.fsum` su 3.10 le righe diverse sono 0 su 25. Correzione della causa in `00_baseline_tnsm.md`. **Conseguenza per le misure:** qualsiasi aggregato calcolato con `sum()` (statistiche di throughput, medie) può differire all'ultima cifra fra 3.10 e 3.12. Va confrontato con una tolleranza, mai con l'uguaglianza.

**G1 aperta per le misure.** Le misure si eseguono con `/opt/conda/envs/dib312/bin/python`.

### 7.2 G2: secondo nodo 192.168.100.57

- Raggiungibile: `ping -c 5` RTT min/avg/max/mdev = 0,135/0,251/0,448/0,113 ms, 0% perdita; porta 22 aperta.
- **Accesso SSH non disponibile da questo host.** Con chiave (`id_ed25519_lab`, `BatchMode`): `Permission denied (publickey,password)`. Il nodo accetta password, ma qui mancano `sshpass`, `expect` e `paramiko` per usarla in modo non interattivo.
- ~~La caratterizzazione non è stata fatta.~~ **Aggiornamento:** l'utente ha installato la chiave `id_ed25519_lab` con `ssh-copy-id`; `ssh -i ~/.ssh/id_ed25519_lab ubuntu@192.168.100.57 hostname` → `ubuntu`. Caratterizzazione in sola lettura (2026-10-10, ~15:41 ora del nodo):

| Voce | Nodo 192.168.100.57 | Questo host (generatore) |
|---|---|---|
| Virtualizzazione | **KVM** (`systemd-detect-virt`) | LXC |
| OS e kernel | Ubuntu 24.04.3 LTS, 6.8.0-146-generic | Ubuntu 22.04.3, 6.8.12-18-pve |
| CPU | 16 vCPU "QEMU Virtual CPU version 2.5+" (2 socket × 8 core, 1 thread per core); flag: `aes`, `sse4_2`, **niente AVX2** (modello di CPU generico) | 16 vCPU AMD EPYC 7313 |
| RAM | **15 GiB** (+3 GiB swap); all'ispezione 3 usati, 12 disponibili | 64 GiB |
| Disco | ext4 su LVM, 98 GB, **96% occupato, 4,4 GB liberi** | ZFS, 94%, 35 GB liberi |
| Python | 3.12.3 di sistema (`python3`, `python3.12`) | 3.12.15 in `/opt/conda/envs/dib312` |
| Docker | 29.8.0 (snap), overlay2, cgroup v2 (systemd); l'utente `ubuntu` è nel gruppo `docker` | 28.2.2 |
| netem | `sch_netem.ko.zst` presente per il kernel in uso; `tc` presente; **`sudo` richiede la password** (`sudo -n true` fallisce) | — |
| iperf3 | assente | — |
| Carico | load average 0,09 / 0,18 / 0,23 | 3,3 / 4,6 / 4,7 |
| Rete | `ping -c 50 -i 0.2` da questo host: RTT min/avg/max/mdev = 0,077/0,173/0,338/0,057 ms, 0% perdita | — |

**Il nodo non è a riposo.** Ci girano:
- `k3s server` (~11% CPU) con coredns e metrics-server (interfacce `flannel.1` e `cni0`);
- il container `wasmbed-registry` (Up), più `wasmbed-renode-device-gateway-1`, `nervous_poincare` e `keep-renode` fermi;
- sessioni utente attive (VS Code server, `claude`, `codex`, processi `MainThread`), `tailscale0`, un VPN `tun0`, snap di lxd e mosquitto.

Nessuno di questi è stato toccato.

**Conseguenze per le misure [D].**
1. **Spazio:** 4,4 GB bastano per un'immagine Python dei servizi (stima ~1 GB) e un venv con le dipendenze (~0,5–1 GB), non per dataset. Niente IoT-23 o GothX sul nodo.
2. **RAM:** 15 GiB. M5 con N = 50 (51 container) è da verificare. GothX (~20 GB) **non ci sta**.
3. **Rumore:** k3s e le altre sessioni sono un carico di fondo. Il manifest di ogni ripetizione registra `uptime` e i primi processi per CPU del nodo, e servono una regola di scarto concordata e possibilmente una finestra in cui le altre sessioni sono ferme.
4. **CPU:** il modello QEMU generico (senza AVX2) rende i tempi **non confrontabili** con quelli di questo host o di macchine con passthrough della CPU. Va dichiarato.
5. **netem (G3):** il modulo c'è, ma la prova richiede `sudo` con password, quindi o la lanci tu o mi dai un modo non interattivo. Resta aperta.
6. **Python sul nodo:** 3.12.3 contro 3.12.15 qui (stessa minor, patch diversa). Per M1/M2 sul nodo serve un venv con le stesse versioni dei pacchetti (`pip install`): richiede il tuo OK al momento di M1/M2.

### 7.3 G4 non soddisfatta: baseline del nodo e regola di scarto (fissata prima di M1/M2)

**G4 (host a riposo) non è soddisfatta** sul nodo 192.168.100.57: ci girano k3s, un container registry e altre sessioni utente, che per decisione dell'utente non si toccano. È dichiarato anche nel manifest di ogni misura (`g4_host_quiet`).

**Baseline senza DIB.** 2026-10-10 dalle 16:08:46 UTC, 300 s, un campione ogni 5 s (60 campioni). Script `experiments_tnsm/common/node_monitor.py baseline`, dati in `experiments_tnsm/node_baseline/baseline_noDIB.json`.

| Grandezza | mediana | p95 | max |
|---|---|---|---|
| `other_cores` (CPU dei processi utente, in core) | 0,123 | 0,230 | 0,280 |
| `steal_pct` | 0,013 | 0,013 | 0,038 |
| `busy_pct` (tutte le vCPU) | 0,73 | 1,48 | 1,79 |
| `load1` | 0,145 | 0,24 | 0,26 |

Processo principale: `k3s-server`, ~0,10 core in media, poi containerd e metrics-server.

**Regola (`experiments_tnsm/common/discard_rule.json`, committata prima della prima cella).** Una cella è *disturbata* se nella sua finestra (dall'inizio del warm-up alla fine) `other_cores` > **1,0 core** oppure `steal_pct` > **2%**:
- 1,0 core vale 3,6 volte il massimo della baseline e 8 volte la mediana, cioè un altro tenant che occupa un'intera vCPU;
- 2% di steal vale 50 volte il massimo della baseline.

`other_cores` esclude i thread del kernel, che durante una cella fanno soprattutto I/O causato da DIB; sono registrati a parte come `kernel_cores`.

Per ogni cella si registrano prima (2 s), durante e dopo (2 s): load, steal, `busy_pct`, `other_cores`, `kernel_cores` e i 5 processi non DIB con più CPU, oltre allo spazio libero su disco. **Nessuna cella viene scartata in silenzio:** i risultati si riportano su tutte le celle e su quelle non segnalate, con il numero delle segnalate.

### 7.4 Correzioni e decisioni prima di M2 (2026-10-10)

**Il tetto di 30 s non è il `busy_timeout` di SQLite (correzione).** Avevo attribuito il p99 di 30.001 ms delle celle M1 a 100 writer al `PRAGMA busy_timeout=30000` di `code/src/dib/registry/db.py:276`. Quel pragma si applica solo con `DIB_SQLITE_WAL=1` (`db.py:244-249`, `:269`). Nella configurazione predefinita, misurata su un'engine creata dal harness:
- SQLite: `journal_mode=delete`, `synchronous=2` (FULL), `busy_timeout=5000` (default di pysqlite);
- pool di SQLAlchemy: `QueuePool`, 5 connessioni più 10 di overflow, **timeout di checkout 30 s**.

Con 100 thread e 15 connessioni, i 30 s sono il timeout di attesa di una connessione dal pool, cioè un **tetto, non una latenza**. Non va mai riportato come latenza. Il `docstring` di `db.py` (`DIB_SQLITE_POOL_SIZE`, `:252-262`) prevedeva già questa ipotesi.

**Analisi (decisione utente):**
- si riportano sempre separati tasso di errore e di timeout, throughput e p99 delle sole operazioni completate;
- **il bootstrap ricampiona le celle (ripetizioni), mai le singole operazioni**. Era già così in `experiments_tnsm/common/analyze.py`: le metriche si calcolano per cella e il bootstrap si fa su quei valori;
- throughput, tre definizioni:
  - `throughput` = tutte le operazioni misurate / tempo (il numero del harness, fallimenti inclusi);
  - `throughput_completed` = operazioni senza errore / tempo, con `InvalidStateTransition` (rifiuto di business) contato come completato;
  - `throughput_clean` = operazioni senza alcuna eccezione / tempo (solo M2);
- **M1:** il harness dà solo aggregati su tutte le operazioni. Il p99 delle celle con errori e p99 ≥ 29,9 s è troncato al timeout del pool ed è escluso dalle statistiche di latenza (`p99_censored_cells`). Il p99 delle sole riuscite non è disponibile per M1 (nessun dato per operazione); lo dà M2.

**M2 riformulata prima del lancio.** Ipotesi e criteri sono in `experiments_tnsm/m2_p99_tail/run.py`; la strumentazione è in `instrument.py`. Per ogni operazione si misurano:
- il tempo fino al primo statement (sessione più attesa del pool);
- la durata della prima scrittura (lock RESERVED, con il busy handler di SQLite fino a 5 s);
- il tempo fino a quando si tiene il lock di scrittura;
- il commit (lock EXCLUSIVE più fsync);
- la distribuzione dell'attesa fra writer.

Ipotesi:
- **H-M2a:** la quota della coda prima di tenere il lock è ≥ 0,5.
- **H-M2b:** la quota di commit è < 1%.
- **H-M2c:** Gini dell'attesa per writer ≤ 0,3, cioè coda equa; oltre, starvation.
- **Controllo GIL (a), H-G1:** operazione nulla a 100 thread, con throughput ≥ 10 volte quello delle operazioni completate.
- **Controllo GIL (b), H-G2:** un processo per writer a 10, 50 e 100 (ognuno con la propria engine e il proprio pool), con throughput < 2 volte quello a thread.

Celle mescolate in un unico ordine casuale: thread 1/10/50 × 10 e 100 × 20; nulla 100 × 10; processi 10/50/100 × 10. **Le varianti di controllo hanno 10 ripetizioni anche a 100 writer**, invece di 20: limite dichiarato.

**Manifest.** M2 registra `journal_mode`, `synchronous`, `busy_timeout`, i parametri del pool, il filesystem delle basi dati (da `/proc/self/mountinfo`) e una micro-misura di fsync prima e dopo (500 × write 4 KiB + fsync). Per M1, già in corso con il manifest precedente, le stesse voci si raccolgono subito dopo la fine, sullo stesso albero (`node_env.json`).

**Limiti dichiarati:**
- database nuovo a ogni cella, quindi niente stato accumulato;
- M1 e M2 non confrontabili sul throughput assoluto (la strumentazione di M2 aggiunge overhead);
- G4 (host a riposo) non soddisfatta (sez. 7.3);
- M1 è stato lanciato prima di queste decisioni: il suo p99 a 100 writer è troncato e il suo manifest non contiene le impostazioni di SQLite.
