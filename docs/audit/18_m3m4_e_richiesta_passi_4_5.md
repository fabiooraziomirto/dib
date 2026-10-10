# Audit 18 — Passo 3 (M3/M4) e richiesta unica per i Passi 4-5

Data: 2026-10-10. Branch `revision-tnsm`. Decisioni dell'utente: audit 17 (C1-C3, D).

## 1. M3/M4 (lancio 2026-10-10, 20:19-21:27 ora locale)

**Esecuzione.**
- Driver `experiments_tnsm/m3_distributed/run.py`, commit `d19804e` (hypotheses H-M3a, H-M3b e H-M4 nel docstring, committate prima del lancio). Albero sul nodo `~/dib_tnsm/tree-d19804e`; hash di `service.py` sul nodo e in locale `3186304363ed…`.
- 40 celle (4 bracci × 10 ripetizioni, bracci in ordine mescolato per ripetizione), tutte con exit code 0. Wall per cella 76-90 s. Ogni cella ricrea il cluster (`down -v`, `up -d`, database nuovi); pronto in 0,8-1,1 s.
- Generatore su questo host, servizi sul nodo (differenza voluta rispetto a M6/M7, nel manifest); mTLS con certificati che hanno un SAN in più (IP del nodo), `make_dist_pki.py` sha256 nel manifest.
- Regola G: disco del nodo 3,7 GB liberi prima e dopo; `docker compose -p dibtnsm down -v --remove-orphans` a fine lancio, nessun container `dibtnsm` residuo, nessun prune. Le immagini `dibtnsm-*` restano per i Passi 4-5.
- Dati: `experiments_tnsm/m3_distributed/run_20261010/` (`cells.jsonl`, un CSV e un log per cella, `manifest.json`, `summary.csv`, `analysis.txt`); analisi con `analyze.py` (bootstrap sulle celle, 10 000 ricampionamenti, seed 20261010, rapporti appaiati per ripetizione).

**Throughput (ops/s) e latenza, media con IC al 95% sulle 10 celle di ogni braccio.**

| Writer | FANOUT 1, mTLS off | FANOUT 10, mTLS off | FANOUT 1, mTLS on | FANOUT 10, mTLS on |
|---|---|---|---|---|
| 1 | 112,5 [109,3; 115,7] | 116,1 [112,7; 119,4] | 209,5 [205,6; 213,4] | 213,2 [207,6; 218,9] |
| 10 | 289,5 [283,4; 295,0] | 293,0 [283,2; 304,0] | 423,1 [408,0; 437,9] | 430,5 [422,0; 439,2] |
| 50 | 360,3 [354,1; 366,7] | 364,9 [357,4; 374,0] | 375,9 [366,5; 384,1] | 368,9 [359,7; 376,7] |
| 100 | 527,0 [519,8; 535,8] | 528,2 [518,3; 540,8] | 439,1 [433,6; 444,8] | 438,4 [434,1; 442,8] |

p50 e p99 (ms), FANOUT 10: a 1 writer 9,3 / 24,2 (off) e 5,5 / 8,1 (on); a 100 writer 198,9 / 433,2 (off) e 254,4 / 464,7 (on). Tabella completa in `summary.csv`.

**Ipotesi (criteri fissati nel docstring prima del lancio) e classificazione dopo la revisione dell'utente (2026-10-10).**

| Ipotesi | Classificazione | Dato |
|---|---|---|
| **H-M3a** (FANOUT 10 / FANOUT 1 a 100 writer, mTLS off, entro ±10%) | non falsificata | rapporto 1,003 [0,981; 1,029]; con mTLS 0,999 [0,987; 1,010] |
| **H-M3b** (nessun errore inatteso) | **FALSIFICATA**, resta tale | 13 errori su 1 288 000 operazioni (≈ 0,001%) in 8 celle su 40; conservati nei totali |
| **H-M4, 1 writer** (≤ 5 ms di p50) | **NON VALUTABILE** | il "soddisfacimento" (−3,85 ms) deriva da un artefatto: mTLS risulta più veloce, il che un costo di TLS non può spiegare |
| **H-M4, 100 writer** (≤ 20% di throughput) | **non valutabile come stima di costo**; rapporto osservato 0,831 [0,812; 0,849] | il rapporto è un dato descrittivo: vedi sotto |

**Regole di trattamento (decisione utente).**
- H-M3b: nessun test `xfail` da scrivere (è un'ipotesi di un esperimento, non un test della suite); l'asserzione originale non cambia. Un'ipotesi corretta scritta ora, dopo aver visto i dati, sarebbe **esplorativa**, mai confermativa. Causa: non determinata; l'ipotesi del keep-alive resta un'ipotesi non verificata (la verifica costerebbe più di mezz'ora: richiede un'istrumentazione lato server a scala). Il confronto con i 6 su 64 400 (0,0093%) del paper vecchio è solo descrittivo (cambiano macchina e versioni).
- H-M4 a 100 writer: **non chiamarlo "limite superiore"**. Se il lanciatore avvantaggia il braccio mTLS (come a 1 e 10 writer), a 100 writer quel vantaggio può essere nascosto dal collo di bottiglia del database: il costo vero del TLS potrebbe essere **maggiore** del 17%. La direzione del bias non è determinata.
- **Nessun numero di costo di mTLS va nel paper finché la causa dell'anomalia non è isolata** (diagnostica in §1.1).

**H-M3b: errori inattesi.**
- 13 su 1 288 000 operazioni cronometrate (0,001%): `RemoteProtocolError` 9 (commit 6, query 3) e `ReadError` 4 (commit 2, query 2). **Nessun `http.403`.**
- Per braccio: FANOUT 1 off 2; FANOUT 1 on 6; FANOUT 10 off **0**; FANOUT 10 on 5.
- Solo a 50 writer (9) e 100 writer (4); mai a 1 o 10.
- Celle: 14, 19, 20, 24, 26, 27, 28, 34, con 1-4 errori ciascuna.
- Nessuna cella ha errori sistematici e nessuna è stata scartata. Gli errori sono contati nel throughput come da definizione del benchmark.
- [D] Sono errori di connessione sul client persistente, della stessa classe dei 6 su 64 400 richieste (0,0093%, nessun 5xx) del paper vecchio (`main_old.tex:503`). La causa non è stata verificata. Un'ipotesi coerente è la chiusura di una connessione keep-alive inattiva da parte del server mentre il client la riusa; non l'ho verificata. Il tasso è 5-15 volte inferiore a quello del paper vecchio.

**Anomalia a 1 writer (e a 10): con mTLS il throughput è maggiore, non minore.** [C] Con 1 writer mTLS dà 209-213 ops/s contro 112-116 senza (ratio 1,47 a 10 writer; 1,01 a 50; 0,83 a 100). Un handshake di cifratura non può rendere il sistema più veloce: la differenza fra bracci non è solo mTLS.
- Verificato nel codice che **non** spiega la differenza:
  - il client è persistente in entrambi i modi (`httpx.Client`, `distributed_concurrency_benchmark.py:79,110`; `_client_for`, `:100-105`);
  - mix di operazioni, instradamento worker→sito e numero di operazioni sono identici (`do_op`, `:128-153`);
  - TCP_NODELAY è impostato dal client (`httpcore/_backends/sync.py:215`);
  - il server usa h11 in entrambi i casi (uvicorn 0.51.0 senza extra, `Dockerfile:4`; sottoclasse h11 in `mtls.py:91-95`).
- Differenze non escluse: il server senza mTLS parte con il CLI di uvicorn (`Dockerfile:20`), con mTLS con `uvicorn.Server(config)` e un protocollo sottoclasse (`mtls.py:158`), con parametri di default diversi; in mTLS il traffico passa su TLS, con record e scritture diverse. **Causa non identificata.**
- Conseguenza: il confronto mTLS contro plain **non misura il costo di mTLS** a nessun numero di writer; il −17% a 100 writer è un rapporto descrittivo con direzione del bias non determinata (correzione utente). Il 5 ms di p50 non è valutabile.
- Diagnostica proposta (richiede un OK, dopo la richiesta unica): una misura aggiuntiva a 1 writer che riporti la latenza **per tipo di operazione** nei due modi (il benchmark la calcola ma non la salva), per sapere se il divario sta nelle operazioni sul sito (commit con scrittura SQLite) o anche in quelle su evidence.

### 1.1 Diagnostica dell'anomalia: lettura fissata PRIMA dei risultati (decisione utente, 2026-10-10)

Scritta e committata mentre la diagnostica (`diag_1writer.py`, commit `b18fd1e`, 15 celle) era in corso; **prima di questa scrittura avevo visto due celle** (C a 1 writer 207,9 ops/s e A a 107,0 ops/s, entrambe coincidenti con i valori di M3, quindi senza informazione sulla configurazione B, che è quella che discrimina le righe della tabella). Configurazioni: A = senza mTLS con il lanciatore di default; B = senza mTLS con lo stesso lanciatore del braccio mTLS; C = mTLS.

| Esito a 1 writer | Interpretazione | Azione |
|---|---|---|
| **B ≈ C, entrambi molto sopra A** | il lanciatore del server spiega il divario | rilanciare i bracci senza mTLS con la configurazione B (circa 20 celle) come addendum etichettato; il costo di mTLS si misura fra C e B |
| **A ≈ B, C sopra** | il divario non dipende da quel lanciatore | l'ipotesi resta aperta: nessun costo di mTLS nel paper, causa dichiarata non determinata |
| **A, B e C simili** | l'anomalia non si riproduce | cercare un fattore di ordine o di stato del nodo nei dati originali di M3 (ad esempio l'alternanza dei bracci) |

Vincoli: 5 ripetizioni in ordine mescolato, potenza limitata per differenze piccole ma una differenza vicina al doppio è visibile. Se i risultati sono ambigui: nessuna configurazione aggiuntiva oltre il limite di un'ora (iniziato alle 21:32), documentare e proseguire. "Simili" e "≈" si leggono con gli IC al 95% sulla differenza delle medie per ripetizione (H-D1 del docstring è la regola operativa).

**Provenienza.** I servizi girano dalla copia `~/dib_tnsm/tree-b18fd1e` sul nodo, creata con `git archive` del commit; il generatore gira in locale importando i moduli una sola volta all'avvio. Gli hash dei file di input si registrano nel manifest della diagnostica.

#### Esito della diagnostica (`diag_20261010/`, 15 celle, 21:32-21:44; manifest scritto a posteriori dal commit `b18fd1e`)

Servizi dalla copia `~/dib_tnsm/tree-b18fd1e` del nodo; hash degli input in `manifest.json`. Ordine di esecuzione (per cella): C A B B A C A B C A C B A C B.

**Throughput (ops/s), media con IC al 95% sulle 5 ripetizioni.**

| Writer | A: plain, CLI | B: plain, lanciatore mTLS | C: mTLS |
|---|---|---|---|
| 1 | 115,5 [108,4; 123,8] | 113,6 [110,9; 116,9] | **213,0** [208,4; 219,4] |
| 10 | 282,9 [277,9; 288,3] | 283,5 [269,1; 300,7] | **429,5** [409,7; 447,7] |

**Applicazione della tabella fissata prima (H-D1):** B − A a 1 writer = −1,8 ops/s [−9,8; 4,5], B − C = −99,4 [−107,8; −92,5]. B coincide con A, non con C: **seconda riga, il lanciatore del server è escluso come causa**; l'anomalia si riproduce (C quasi doppio). Secondo la tabella: **nessun costo di mTLS nel paper**, ipotesi aperta. H-D2 (access log presente): in tutte le 15 celle 351 righe `POST` su site-0 e 378 su evidence, anche in A, B e C; per il mio conteggio ne ci si attende ≈ 345 su site-0 (165 + 165 + 15 di seed), quindi ≥ 90% è soddisfatto; la differenza di 6 righe non è spiegata. H-D2 non falsificata: **la sonda P-log è utilizzabile in tutte le modalità**.

**Latenza p50 per tipo di operazione (ms, media sulle ripetizioni).**

| Operazione | A w1 | B w1 | C w1 | A w10 | B w10 | C w10 |
|---|---|---|---|---|---|---|
| query (sito) | 9,64 | 9,55 | **5,68** | 45,94 | 46,16 | **28,80** |
| commit (sito) | 9,38 | 9,39 | **5,65** | 45,19 | 45,28 | **28,46** |
| attest (evidence) | 3,93 | 3,86 | 3,53 | 4,89 | 4,94 | **8,72** |
| dispute (evidence) | 1,38 | 1,39 | 1,41 | 2,65 | 2,64 | **6,34** |
| restore (evidence) | 1,39 | 1,37 | 1,38 | 2,58 | 2,78 | **6,48** |

**Il divario sta nelle operazioni sul sito** (query e commit, −3,9 ms a 1 writer e −17 ms a 10), **non in quelle su evidence**, che a 1 writer sono uguali e a 10 writer sono **più lente** con mTLS (+3,7 ms circa), come ci si aspetta da un costo di TLS.

**Meccanismo candidato [C per il codice, D per la causalità].**
- `query_score` e `operator_commit` del sito chiamano entrambi `_evidence_get_score` (`service.py:380-390`), cioè un `httpx.get` di modulo che costruisce un `Client` nuovo a ogni chiamata.
- Senza mTLS `_HTTP_TLS = {}` (`service.py:161`): httpx usa `verify=True` di default e costruisce un contesto SSL, con caricamento del bundle CA, anche per un URL `http://`. Con mTLS `_HTTP_TLS = {"verify": <contesto già costruito>}` (`:167`), quindi non c'è nulla da costruire a ogni chiamata.
- Micro-misura (`diag_httpx_client_cost.py`, ipotesi H-X committata prima in `abe6289`): costruire il `Client` costa **6,15 ms** con verifica di default e **0,029 ms** con un contesto pronto, nell'immagine del servizio sul nodo (httpx 0,28.1, Python 3.12.15; locale: 5,9 ms e 0,03 ms). H-X supportata (soglia 2 ms).
- Coerenza con i dati: il risparmio atteso per operazione sul sito è circa 6,1 ms; quello osservato a 1 writer è 3,7-3,9 ms. La differenza (~2,2 ms) è compatibile con l'handshake TLS completo che il braccio mTLS paga a ogni chiamata fra servizi (nessun pool, V1b); **non è stata misurata**. A 10 writer l'effetto cresce perché il sito è un processo Python singolo e la costruzione del contesto è tempo CPU.
- Non verificato a livello di sistema: richiederebbe un braccio plain che passi lo stesso contesto precostruito (tramite un wrapper del lanciatore in `experiments_tnsm/`, senza toccare `service.py`, congelato).

**Implicazioni (da leggere con la cautela che il meccanismo non è confermato a livello di sistema).**
1. Il confronto mTLS contro plain **non** isola il costo di TLS: il braccio plain paga in più la costruzione del contesto a ogni chiamata fra servizi. Nessun numero di costo di mTLS va nel paper.
2. Il bias va nella direzione che l'utente aveva indicato: a 100 writer il rapporto 0,83 sottostima verosimilmente il costo di TLS, perché il braccio plain è rallentato da una spesa che il braccio mTLS non ha. È coerente con i dati, ma non quantificato.
3. I numeri del prototipo plain (anche quelli del paper vecchio, 530 ops/s a 100 writer) descrivono il prototipo così com'è, inclusa questa spesa per chiamata: restano veri per quel codice, ma non rappresentano un deployment ottimizzato.
4. Proposta (richiede OK, entro il limite di un'ora che scade alle 22:32): una configurazione D, cioè plain con il lanciatore B più un wrapper che passa a httpx un contesto precostruito. Circa 5 celle (6 minuti). Se D si allinea a C a 1 writer, il meccanismo è confermato e il costo di mTLS si misura fra C e D; se D resta come A, il meccanismo non spiega il divario.

**Regola di scarto, ora applicabile (pre-campione di fondo, 12 s a sistema idle, container `dibtnsm` esclusi).** Soglie invariate (`discard_rule.json`: `other_cores` > 1,0 o `steal_pct` > 2%).
- `other_cores` 0,096-0,157 (massimo in cella 8, C rep 2: k3s-server 0,137); `steal_pct` 0,005-0,021; `busy_pct` 0,75-1,16. **Nessuna cella segnalata su 15.** Processo principale di fondo: `k3s-server` (~0,09 core), poi `containerd`.
- Limite: è il campione **prima** della cella. La finestra durante la cella non è misurata (il generatore sta su un altro host), quindi la regola, che per definizione guarda la finestra della cella, è applicata solo al fondo.

**Limiti e cautele.**
- **Regola di scarto non applicata.** Il driver di M3/M4 registra per cella il carico medio e i primi processi per CPU del nodo (`node_load()`), non `other_cores` né `steal_pct` come `experiments_tnsm/common/node_monitor.py`: non si può quindi applicare `discard_rule.json`, e nessuna cella è stata scartata. G4 (nodo a riposo) resta non soddisfatta.
- Load average a 1 minuto prima di ogni cella: 0,78-6,5; media per braccio 3,5-4,4 (FANOUT 1 off 3,46; FANOUT 1 on 3,62; FANOUT 10 off 4,03; FANOUT 10 on 4,42). Il valore è contaminato dalla cella precedente e dal riavvio del cluster, quindi **non è una misura pulita del carico di fondo**.
- Fra i servizi non c'è un pool (audit 13 §9.1): il costo di mTLS fra servizi è l'handshake completo a ogni chiamata. **Non si usa la formula "limite superiore"** per M4 (vedi sopra).
- Il confronto con i risultati del paper vecchio è solo descrittivo (codice, host e Python diversi): lì il throughput a 100 writer era 530 ops/s (10 siti, FANOUT 1, senza mTLS, in locale), qui 527 senza mTLS; è un'analogia, non un confronto.

## 2. Richiesta unica per i Passi 4-5 (nulla lanciato)

### 2.0 Nuovo vincolo: B2-partition con netem a mano

**Decisione utente C2:** netem si lancia a mano, a blocchi per profilo, senza regola sudoers. **B2-partition** però applica e toglie la perdita al 100% su un sito **a ogni prova** (260 prove nel disegno ridotto, audit 14 §4), mentre le prove di un blocco durano decine di secondi: farlo a mano non è praticabile.

Senza root non c'è un modo equivalente [C/D]:
- `docker network disconnect` toglie IP e record DNS, quindi equivale a B2-kill (V5);
- `docker pause` congela il processo: il kernel completa ancora il SYN (timeout di read, non di connect), e il trigger del sito si ferma invece di andare in backoff (V7). È un'altra semantica.

Opzioni (decidi tu):
- **(a)** un helper che **lanci tu con sudo all'inizio di ogni blocco B2-partition**, `experiments_tnsm/m67_retraction/partition_helper.sh` (da scrivere). Resta in ascolto su una FIFO aperta da `run.py` e accetta solo due comandi, `cut site-<i>` e `heal site-<i>`, sui container del progetto `dibtnsm` (stessa guardia di `netem_apply.sh`). Si chiude a fine blocco. Nessuna regola sudoers: il privilegio vale solo per la durata del blocco e lo concedi tu a mano;
- **(b)** B2-partition sostituita da una variante `pause`, dichiarata con la sua semantica (sito vivo ma congelato), senza sudo;
- **(c)** solo B2-kill più `kill-min`. Le predizioni (d-part) cadono e la partizione di rete resta fuori da M6/M7.

### 2.1 Comandi che lancio io, senza sudo (cluster `dibtnsm`, profilo `lan`, mTLS spento)

1. Pipeline dei log (GATE 2): `~/dib_tnsm/venv/bin/python experiments_tnsm/m67_retraction/calib_logs.py --n 100 --out ~/dib_tnsm/out/calib_logs_lan.json`. Misura evidence da sola, poi evidence e `site-0` in parallelo, con ordine e scarto relativo.
2. L_dns a `lan`: `experiments_tnsm/m67_retraction/calib_ldns.sh <compose> <project-dir> lan`, che misura `getaddrinfo('site-3')` dentro evidence con il sito vivo e poi ucciso.
3. Dopo i passi 2.2.2-2.2.3: L_dns a `wan` e `degraded` (stesso script, con l'etichetta del profilo).
4. Dai risultati: la soglia P-log per profilo (C8) e la variante di B2 (≤ 50 ms / ≥ 0,5 s), committate **prima** del lancio. Poi GATE 3 con la dispersione misurata.

### 2.2 Comandi che lanci tu, con sudo sul nodo

Albero: `T=~/dib_tnsm/tree-<commit>`; script in `$T/experiments_tnsm/m67_retraction/`.
1. `sudo modprobe sch_netem && lsmod | grep sch_netem` (G3).
2. `sudo $T/experiments_tnsm/m67_retraction/netem_apply.sh wan`, poi `sudo $T/experiments_tnsm/m67_retraction/netem_show.sh` per la verifica, mentre io ripeto 2.1.2.
3. Lo stesso con `degraded`.
4. **Cattura `tcpdump`** con `degraded` applicato, mentre invio 20 tentativi di fan-out per braccio (mTLS off, poi on; il cluster va riavviato con mTLS fra le due catture):
   `sudo nsenter -t $(docker inspect -f '{{.State.Pid}}' dibtnsm-evidence-1) -n timeout 300 tcpdump -i eth0 -w /tmp/dib_degraded_<off|on>.pcap 'tcp port 8000'`
   poi `sudo chown ubuntu /tmp/dib_degraded_*.pcap`.
5. `sudo $T/experiments_tnsm/m67_retraction/netem_apply.sh lan` (pulizia), poi `netem_show.sh`.

### 2.3 Cosa resta da scrivere prima del lancio di M6/M7

- Driver `experiments_tnsm/m67_retraction/run.py` con le ipotesi del piano.
- GATE 3 (decisione utente C3): 10 ripetizioni per braccio e test (d-kill) sui due bracci mTLS **uniti**, con nel docstring l'assunzione che mTLS non cambi la convergenza; prima del test unito, un confronto fra i bracci mTLS a T fisso. Se differiscono, il test unito decade: stop e domanda.
- L'ordine dei blocchi di profilo è randomizzato con seed e registrato nel manifest (C2).
