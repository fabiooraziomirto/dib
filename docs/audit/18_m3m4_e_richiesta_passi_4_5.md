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

**Applicazione della tabella fissata prima (H-D1):** B − A a 1 writer = −1,8 ops/s [−9,8; 4,5], B − C = −99,4 [−107,8; −92,5]. B coincide con A, non con C: **seconda riga, il lanciatore del server è escluso come causa**; l'anomalia si riproduce (C quasi doppio). Secondo la tabella: **nessun costo di mTLS nel paper**, ipotesi aperta. H-D2 (access log presente): in tutte le 15 celle 351 righe `POST` su site-0 e 378 su evidence, anche in A, B e C; per il mio conteggio ci si attendono ≈ 345 su site-0 (165 + 165 + 15 di seed), quindi ≥ 90% è soddisfatto; la differenza di 6 righe non è spiegata. H-D2 non falsificata: **la sonda P-log è utilizzabile in tutte le modalità**.

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
- Micro-misura (`diag_httpx_client_cost.py`, ipotesi H-X committata prima in `abe6289`): costruire il `Client` costa **6,15 ms** con verifica di default e **0,029 ms** con un contesto pronto, nell'immagine del servizio sul nodo (httpx 0.28.1, Python 3.12.15; locale: 5,9 ms e 0,03 ms). H-X supportata (soglia 2 ms).
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

### 1.2 Controllo dei fan-out nel mix di M3 (decisione utente A, 2026-10-10)

**Dati disponibili.** I log di accesso dei container di M3 **non esistono**: il cluster è ricreato con `down -v` a ogni cella e il driver non li salvava (`cell_NNN.log` contiene l'output del benchmark, non i log dei container). I conteggi di `POST /apply_fanout` e di `pending_fanout` per cella e per braccio di M3 non sono quindi ricostruibili. Si usano il codice e i conteggi diretti raccolti da D (e dai conteggi totali della prima diagnostica).

**Mix e transizioni [C].**
- Il mix ha 20 posizioni (`_MIX_REALISTIC`, `distributed_concurrency_benchmark.py:106-109`): `dispute` alla posizione 14, `restore` alla 17, `attest` alla 9. L'endpoint è `ep-{op_index % 5}` (`:132`), il tipo di dispositivo è `worker_id % 3` (`:131`), il sito è `worker_id % N_SITES` (`:130`).
- Quindi **`dispute` cade sempre su `ep-4` e `restore` sempre su `ep-2`**.
- `/restore` su `ep-2`, mai disputato (stato attivo), risponde **409 senza fan-out** (`service.py:851-852`).
- `/dispute` su `ep-4` fa fan-out solo nelle transizioni attiva → disputata (`:820-831`) e disputata → revocata da un secondo sito (`:832-835`). Dopo la revoca non fa più nulla.
- In tutto: al più 2 transizioni per tipo di dispositivo, cioè **6 fan-out per cluster**, e ognuno raggiunge ogni sito una volta.

**Conteggio diretto (D, 15 celle: 5 × A, C, D; `apply_fanout_site0` in `cells.jsonl`).** `POST /apply_fanout` ricevuti da site-0, cumulativi:

| Punto | dopo il seed | dopo warm-up 1 writer | dopo fase cronometrata 1 writer | dopo warm-up 10 writer | dopo fase cronometrata 10 writer |
|---|---|---|---|---|---|
| tutte le 15 celle (A, C e D) | 0 | 1 | 1 | 6 | 6 |

- **Tutti i 6 fan-out avvengono nei batch di warm-up, che sono scartati. Nelle fasi cronometrate i fan-out sono zero**, identici in tutte le celle e i bracci.
- Coerente con la prima diagnostica: 351 righe `POST` su site-0 contro le 345 attese da query, commit e seed (eccesso 6), e 378 su evidence, uguale a seed + attest + dispute + restore.
- `pending_fanout`: **non misurato** (non è nelle metriche del driver). Per costruzione è 0 (tutti i siti sono raggiungibili e il fan-out riesce al primo tentativo); non verificato direttamente.
- Per M3 con altri ordini di writer vale la stessa logica (ogni coppia tipo-sito è incontrata per la prima volta in un warm-up, che precede la fase cronometrata corrispondente); non è stato contato direttamente.

**Dispute e restore a ~1,4 ms (a 1 writer)** sono spiegati: sono una no-op o un 409, non un fan-out sincrono verso 10 siti.

**Riclassificazione di H-M3a** (il testo dell'ipotesi in `run.py` non è cambiato): **non falsificata ma non informativa.** Il rapporto FANOUT 10 / FANOUT 1 = 1,003 [0,981; 1,029] non dice nulla sul fan-out, perché nelle fasi cronometrate non ce n'è.

**Contraddizione con il paper vecchio (inferenza, non misura).** `main_old.tex:503` attribuisce al fan-out il calo da 125,7 a 99,8 ops/s a 1 writer con 10 siti rispetto a 1 sito (20,6%). Con questo benchmark e questo mix (lo sweep usa lo stesso script e gli stessi warm-up, `results/site_count/README.md`), il fan-out non può avvenire nella fase cronometrata. Il calo a 1 writer ha quindi un'altra causa, non determinata. L'esecuzione vecchia usava un `service.py` diverso e non è stata rimisurata. La frase va rivista nel paper (`docs/main_tnsm.tex`).

### 1.3 Configurazione D: esito (`diag_d_20261010/`, 15 celle, 21:54-22:04; albero `~/dib_tnsm/tree-3b61bd8`)

**Provenienza.** `service.py` sul nodo `3186304363ed…`; `launcher_d.py` sul nodo e in locale `1fe42185…` (stesso hash), montato in sola lettura; nota nel manifest: `_HTTP_TLS` è valorizzato dall'esterno (`service._HTTP_TLS = {"verify": <contesto precostruito>}`) prima di servire; `service.py` non modificato. Il log di ogni container D riporta la riga del lanciatore (5 su 5 celle D). Ordine di esecuzione: A D C A D C D A C D C A D A C. Un primo tentativo era fallito alla cella 2 per un errore di percorso (vedi commit `3b61bd8`); il run abortito è conservato.

**Throughput (ops/s), media con IC al 95% sulle 5 ripetizioni.**

| Writer | A: plain di default | C: mTLS | D: plain con contesto precostruito |
|---|---|---|---|
| 1 | 115,1 [112,6; 117,5] | 214,6 [206,5; 222,7] | **351,6** [345,4; 358,3] |
| 10 | 297,2 [286,3; 306,3] | 444,0 [440,8; 446,1] | **579,2** [566,9; 588,7] |

**p50 per tipo di operazione (ms), media con IC al 95% (`per_op_p50_ci.json`).**

| Operazione | A, 1 w | C, 1 w | D, 1 w | A, 10 w | C, 10 w | D, 10 w |
|---|---|---|---|---|---|---|
| query (sito) | 9,67 [9,45; 9,90] | 5,60 [5,47; 5,74] | 3,25 [3,17; 3,32] | 43,7 [42,2; 45,6] | 27,6 [27,3; 27,9] | 22,4 [22,0; 23,0] |
| commit (sito) | 9,39 [9,26; 9,57] | 5,51 [5,40; 5,61] | 3,15 [3,07; 3,20] | 43,4 [41,9; 45,2] | 27,3 [27,1; 27,6] | 21,4 [21,2; 21,8] |
| attest (evidence) | 3,80 [3,68; 3,90] | 3,64 [3,30; 3,88] | 3,36 [3,24; 3,44] | 4,52 [4,41; 4,66] | **8,71** [8,13; 9,41] | 4,79 [4,52; 5,14] |
| dispute (evidence) | 1,41 [1,37; 1,46] | 1,31 [1,27; 1,33] | 1,33 [1,30; 1,36] | 2,41 [2,33; 2,48] | **6,78** [6,31; 7,25] | 2,79 [2,64; 2,92] |
| restore (evidence) | 1,36 [1,32; 1,40] | 1,31 [1,25; 1,36] | 1,31 [1,28; 1,33] | 2,49 [2,38; 2,60] | **6,63** [6,28; 7,01] | 2,72 [2,55; 2,90] |

**Esito dell'interpretazione fissata prima del lancio:** D ha CI interamente sopra quello di C e di A a 1 writer → **"D ≥ C: meccanismo confermato"**.

**Risparmio atteso contro osservato (a 1 writer, media di query e commit):**

| | Valore |
|---|---|
| atteso (micro-misura, costruzione del `Client` con verifica di default, nell'immagine) | 6,15 ms |
| **osservato A − D** | **6,33 ms** [6,12; 6,53] |
| osservato A − C | 3,98 ms |
| C − D (resta a mTLS) | 2,35 ms [2,22; 2,44] |

L'osservato A − D coincide con l'atteso (entro il 3%, con 6,15 dentro l'IC): il meccanismo non è solo plausibile, è quantitativamente allineato. A 10 writer il risparmio è maggiore (A − D = 21,7 ms [20,1; 23,1]) perché i siti sono processi Python singoli e la costruzione del contesto è tempo CPU che si accumula.

**Costo di mTLS, misurato fra C e D (solo diagnostico, 5 ripetizioni).** Per questo prototipo (nessun pool fra servizi, handshake completo a ogni chiamata, `service.py` congelato):
- operazioni su evidence, a 10 writer: +3,9 ms (attest), +4,0 (dispute), +3,8 (restore), cioè 2-3 volte la latenza di D;
- operazioni sul sito: +2,35 ms a 1 writer e +5,5 ms a 10;
- throughput C/D: 0,61 a 1 writer, 0,77 a 10 (rapporti sulle medie).

**Non sono numeri da paper:** servono il rilancio di C con 10 ripetizioni a 1, 10, 50 e 100 writer (decisione utente C.1) e la verifica che D non introduca altre differenze.

**Altri dati.**
- Errori inattesi: 0 in tutte le 15 celle (non confrontabile con M3: qui ≤ 10 writer).
- **Regola di scarto** (soglie invariate: `other_cores` > 1,0 o `steal_pct` > 2%): `other_cores` 0,098-0,211 (massimo in cella 6, D rep 2), `steal_pct` 0,005-0,042. **Nessuna cella segnalata su 15.** Il campione è quello prima della cella (12 s a sistema idle, container `dibtnsm` esclusi).
- Pulizia: nessun container `dibtnsm` residuo; le directory create da Docker nel primo tentativo sono state rimosse (0 file).

### 1.4 Proposte per il punto C (NON applicate: attendono le decisioni dell'utente)

1. **M4:** rilanciare solo le celle senza mTLS con D, a 1, 10, 50 e 100 writer, 10 ripetizioni (~20 celle, 30-40 minuti), ordine mescolato con i bracci mTLS già misurati se possibile; i dati originali restano come "configurazione di default" con una nota. Costo di mTLS = C contro D. A 50 e 100 writer la presenza di un collo di bottiglia al database può nascondere parte dell'effetto: i rapporti vanno letti con quella cautela.
2. **M6/M7 [C, verificato nel codice]:** il fan-out (`service.py:710`), la lettura dei pending (`:542`) e l'ack (`:565`) passano tutti da `**_HTTP_TLS`, quindi nei bracci senza mTLS **ogni tentativo e ogni chiamata di riconciliazione paga ~6,15 ms** di contesto SSL; in mTLS non li paga ma paga l'handshake (2,35 ms per chiamata a 1 writer).
   - Proposta: usare D come braccio senza mTLS in tutto M6/M7.
   - Predizione (a) corretta: ritiro diretto ≈ n_RTT·R + servizio, dove in default il servizio include +6,15 ms per tentativo (con FANOUT 1: ≈ +61,5 ms per fan-out a 10 siti, a `lan`) e in D no; a `wan` e oltre il termine è < 4% di R.
   - Da riportare nell'audit **prima del lancio**.
3. **Regola E:** caso (ii), prestazione con invarianti intatte, nessuna modifica al servizio.

### 1.5 Decisione sul punto C (utente, 2026-10-10) e verifiche collegate

**Decisione.** Rilancio di M4 approvato: bracci C (mTLS) e D (senza mTLS, contesto SSL precostruito, lanciatore di B) nello stesso blocco, ordine mescolato, 1/10/50/100 writer, 10 ripetizioni (20 celle in tutto, 10 per braccio), FANOUT fisso a 10 (il mix non lo esercita). Predizioni scritte prima del lancio nel docstring di `run_m4.py` (commit `62aaca8`): C/D ≈ 0,61 a 1 writer (falsificata se l'IC del rapporto appaiato è interamente fuori da [0,50; 0,72]) e ≈ 0,77 a 10 writer (fuori da [0,68; 0,86]); 50 e 100 writer esplorativi. I dati originali di M4 restano come "configurazione di default". Il costo di mTLS riportabile è il solo rapporto C/D, per questo prototipo (nessun pool fra servizi), a 100 writer esplorativo. M5 esce dalla sequenza (stesso mix: non misurerebbe il fan-out).
Il lancio parte da `~/dib_tnsm/tree-62aaca8` (hash di `service.py` `3186304363ed…`); PKI valida fino al 2026-10-11 18:00 UTC contro una durata stimata di circa 45 minuti.

**B1. Tutte le chiamate httpx di `service.py` (grep).** Non ci sono `httpx.Client(` né altre chiamate `httpx.*` oltre queste quattro, e **tutte e quattro passano da `**_HTTP_TLS`**; nessuna ne è esclusa:

| Riga | Chiamata | Chi la usa |
|---|---|---|
| `service.py:381-384` | `httpx.get(.../scores)` in `_evidence_get_score` | `/query` e `/commit` del sito (1 chiamata per operazione) |
| `:542` | `httpx.get(.../pending/<sito>)` | `_reconcile_once` (route `/reconcile` e trigger, `:255,590`) |
| `:563-565` | `httpx.post(.../pending/<sito>/ack)` | `_reconcile_once` |
| `:707-710` | `httpx.post(.../apply_fanout)` | `_deliver_to_site`, una per tentativo (fino a 3 per sito) |

`:715` è solo un `except httpx.HTTPError`. Il trigger (`_ReconcileTrigger`) non chiama httpx da sé: esegue `_reconcile_once`. Nessun altro file del servizio (`mtls.py`) usa httpx. Ne segue che in un braccio senza D ogni chiamata fra servizi costruisce un `Client` con il contesto SSL di default (6,15 ms nell'immagine).

**B2.** D è il braccio senza mTLS in tutto M6/M7 (manifest: hash di `launcher_d.py`, nota che `_HTTP_TLS` è valorizzato dall'esterno, hash di `service.py`, host del generatore, come in `run_m4.py`).

**B3. Predizione (a) per `lan`, ricongelata con D (scritta prima di qualsiasi lancio di M6/M7).** Predizioni (c) e (d) invariate finché la cattura `tcpdump` non dice altro.
- Grandezza: ritiro diretto per sito = timestamp `POST /apply_fanout 200` del sito (sonda P-log) meno t0; ripiego `dispute-rtt`. Il valore assoluto a `lan` in D (τ_D per tentativo: connessione, richiesta, scrittura SQLite del sito) non si predice: si calibra nella prova pilota.
- **P-a1 (FANOUT 1, 10 siti in sequenza).** Differenza fra braccio di default e braccio D per l'**ultimo** sito: **+61,5 ms** (10 tentativi × 6,15 ms). Falsificata se l'IC al 95% della differenza delle mediane cade interamente fuori da [46; 77] ms (±25%). Per la media sui 10 siti il valore previsto è +33,8 ms (6,15 × 5,5).
- **P-a2 (FANOUT 10).** Differenza default − D per il sito che completa per ultimo: fra +6 ms (costruzioni dei contesti in parallelo) e +62 ms (costruzioni serializzate dal GIL, perché sono tempo CPU di un solo processo). Falsificata se l'IC cade interamente fuori da [3; 75] ms. L'estremo effettivo è un risultato, non un'assunzione.
- **P-a3 (profili con ritardo).** Ritiro diretto in D ≈ n_RTT·R + τ_D, con il criterio invariato: falsificata se la mediana a `regional`, `wan` o `mixed` supera n_RTT·R + 3 × (mediana `lan`) **dello stesso braccio** oltre l'IC (il bias per chiamata si cancella nel confronto con `lan` dello stesso braccio). A `wan` e oltre i 6,15 ms sono meno del 4% di R.
- **P-a4 (mTLS contro D a `lan`).** Per l'ultimo sito con FANOUT 1: +23,5 ms (10 × 2,35 ms, C − D misurato a 1 writer per chiamata sul sito). Falsificata se l'IC cade fuori da [15; 32] ms.
- **Celle di riferimento B1 a `lan` (k = 0), configurazione di default "come spedito"** (nessuna modifica): poche celle (10 episodi, FANOUT 1 e 10, senza mTLS) etichettate come riferimento e non come braccio del disegno; servono a verificare P-a1 e P-a2.
- Il D_run di `lan` (0,06-0,07 s, misurato in G0b con il default) è nel bound `max(5 s, D_run_max)`: sotto D la stima è ~18 ms in meno (vedi audit 15 §6), irrilevante per il bound.

**D. Verifiche sul vecchio run (senza il nodo).**
- Storia del benchmark nel repo: due sole versioni (`bd3080b` import v43, hash `95970767`; `0ac6a51` mTLS, hash `035ab45e`). Fra le due, **mix, warm-up, instradamento dei worker e scelta dell'endpoint sono invariati** (il diff riguarda solo le identità mTLS).
- **I vecchi run non usavano nessuna delle due:** `results/site_count/manifest.json` registra il benchmark `074455a0…` e `results/distributed/manifest.json` `80111012…`, assenti dalla storia; anche il vecchio `service.py` (`54f635cb…`) è assente. Non si può diffare il benchmark e il servizio realmente usati.
- Quello che i manifest dicono: stesso mix (`_MIX_REALISTIC`, query ×8, commit ×7, contribute ×2, attest ×1, dispute ×1, restore ×1), `ops_per_worker` 20, 5 ripetizioni. **Nessun manifest né CSV registra contatori di fan-out** (grep su `results/site_count`, `results/distributed`, `results/concurrency`).
- **Proposta per il paper vecchio, NON applicata:** togliere l'attribuzione del calo da 125,7 a 99,8 ops/s al fan-out (`main_old.tex:503`): "ten sites are 20.6% slower than one" resta come osservazione, la causa non è isolata. Frase suggerita: *With one writer, ten sites are 20.6% slower than one (125.7 vs 99.8 operations/s); the cause was not isolated.*
- **Proposta di frase per il paper (caso (ii) della regola E):** *In the prototype, every inter-service call creates an HTTP client and, without a shared context, builds a default SSL context (about 6 ms); reusing a context or a client removes it.*

### 1.7 Rilancio di M4: C (mTLS) contro D (plain, contesto precostruito) (`run_m4_20261010/`, 22:10-22:44)

**Provenienza.** `run_m4.py` commit `62aaca8` (predizioni nel docstring prima del lancio), servizi da `~/dib_tnsm/tree-62aaca8` (`service.py` `3186304363ed…`, `launcher_d.py` `1fe42185…`, entrambi nel manifest), generatore su questo host, PKI con un SAN in più (IP del nodo), FANOUT fisso a 10, 20 celle (10 blocchi, C e D nello stesso blocco, ordine mescolato: C D D C C D C D D C C D D C D C D C D C), writer 1/10/50/100 in ordine mescolato per cella, 200 operazioni per worker (322 000 cronometrate per braccio) dopo un warm-up di 20. Disco del nodo 3,6 GB prima e dopo, nessun container `dibtnsm` residuo, directory dello snap pulita. Analisi: `analyze_m4.py` (bootstrap sulle celle, 10 000 ricampionamenti, rapporti appaiati per blocco).

**Throughput (ops/s), media con IC al 95% sulle 10 celle di ogni braccio, e rapporto appaiato C/D.**

| Writer | D | C | C/D (10 blocchi) | Predizione | Esito |
|---|---|---|---|---|---|
| 1 | 353,2 [339,3; 368,0] | 212,1 [208,9; 214,9] | **0,603** [0,575; 0,629] | ≈ 0,61, falsificata se IC fuori da [0,50; 0,72] | **H-M4a non falsificata** |
| 10 | 567,3 [550,4; 584,3] | 449,3 [438,2; 460,1] | **0,794** [0,761; 0,828] | ≈ 0,77, falsificata se IC fuori da [0,68; 0,86] | **H-M4b non falsificata** |
| 50 | 648,4 [640,0; 656,5] | 387,8 [382,6; 393,0] | 0,598 [0,588; 0,611] | esplorativo | — |
| 100 | 824,4 [819,1; 829,5] | 448,0 [444,1; 452,1] | 0,543 [0,540; 0,547] | esplorativo | — |

Le predizioni cadono dentro gli IC osservati. **A 50 e 100 writer il rapporto è più basso (0,60 e 0,54), non più alto**: il costo di mTLS non è nascosto dal collo di bottiglia del database, come temuto, ma cresce con il carico; il 0,83 del vecchio M4 a 100 writer era un rapporto contro il braccio di default e sottostimava il costo, come l'utente aveva indicato. A 50 e 100 writer i valori restano **esplorativi** per decisione presa nel docstring.

**Latenza complessiva (ms, media sulle celle): p50 / p95 / p99.**

| Writer | D | C |
|---|---|---|
| 1 | 3,15 / 3,98 / 4,75 | 5,56 / 6,66 / 7,99 |
| 10 | 19,7 / 31,9 / 42,7 | 25,3 / 37,4 / 44,0 |
| 50 | 89,4 / 144,6 / 165,7 | 137,4 / 234,4 / 260,1 |
| 100 | 128,5 / 234,8 / 285,6 | 248,3 / 406,2 / 454,8 |

**p50 per tipo di operazione (ms), media con IC al 95%; differenza C − D.**

| Operazione | 1 w: D | 1 w: C | C−D | 10 w: D | 10 w: C | C−D | 100 w: D | 100 w: C | C−D |
|---|---|---|---|---|---|---|---|---|---|
| query (sito) | 3,32 [3,18; 3,45] | 5,75 [5,67; 5,85] | +2,43 | 22,8 [22,0; 23,6] | 27,4 [26,7; 28,2] | +4,7 | 150,7 [149,0; 152,4] | 273,6 [270,1; 277,3] | +122,9 |
| commit (sito) | 3,18 [3,06; 3,29] | 5,69 [5,60; 5,81] | +2,51 | 21,7 [21,0; 22,5] | 27,1 [26,5; 27,8] | +5,4 | 148,2 [146,7; 149,6] | 272,4 [268,9; 276,2] | +124,3 |
| attest (evidence) | 3,03 [2,74; 3,28] | 2,89 [2,55; 3,30] | −0,13 | 4,69 [4,26; 5,11] | 8,56 [7,75; 9,32] | +3,9 | 42,4 [40,2; 44,7] | 117,3 [115,5; 119,2] | +74,9 |
| dispute (evidence) | 1,36 [1,31; 1,42] | 1,48 [1,42; 1,54] | +0,12 | 2,80 [2,71; 2,91] | 6,79 [6,12; 7,44] | +4,0 | 41,6 [39,5; 43,7] | 117,5 [115,7; 119,5] | +75,9 |
| restore (evidence) | 1,37 [1,32; 1,41] | 1,41 [1,38; 1,44] | +0,04 | 2,91 [2,75; 3,10] | 6,72 [6,07; 7,27] | +3,8 | 41,6 [39,5; 43,7] | 72,0 [70,6; 73,4] | +30,5 |

A 1 writer la differenza sulle operazioni sul sito (+2,4-2,5 ms) coincide con quella della diagnostica (+2,35 ms): è l'handshake TLS completo a ogni chiamata sito → evidence (nessun pool). Le operazioni su evidence sono invariate a 1 writer e pagano ≈ +3,9 ms a 10 writer, perché evidence serve gli handshake dei dieci siti. A 50 e 100 writer il costo si amplifica (code su evidence, un processo Python singolo). Tabelle complete in `analysis.txt` e `summary.json`.

**Errori inattesi: 7 su 644 000 operazioni cronometrate (0,0011%), in 7 celle diverse.**
- Tipi: `ReadTimeout` 2 (commit), `ConnectError` 2 (query, commit), `ReadError` 2 (query, commit), `RemoteProtocolError` 1 (query).
- Per braccio e writer: D a 100 writer 4 (su 200 000 operazioni, 0,002%); C a 10 writer 1, a 50 writer 1, a 100 writer 1. Nessun 403.
- Rispetto a M3: ricompaiono `ReadError` e `RemoteProtocolError`, e per la prima volta `ConnectError` e `ReadTimeout` (timeout del client a 5 s). Causa non determinata; l'ipotesi del keep-alive resta non verificata e non spiega i `ConnectError`. Conservati nei totali.

**Regola di scarto** (soglie invariate): `other_cores` 0,096-0,182, `steal_pct` 0,005-0,021 nel campione pre-cella (12 s a sistema idle, container `dibtnsm` esclusi). **Nessuna cella segnalata su 20**; risultati su tutte le celle. La finestra durante la cella non è misurata (generatore su un altro host).

**Cosa si può riportare.** Il rapporto C/D a 1 e 10 writer (0,60 e 0,79) come costo di mTLS **per questo prototipo, che non ha un pool fra i servizi** (handshake completo a ogni chiamata fra servizi): è un limite superiore del costo di un'implementazione con connessioni riusate, per decisione dell'utente. A 50 e 100 writer (0,60 e 0,54) solo come esplorativo. I dati del vecchio M4 restano come "configurazione di default", con la nota in `run_20261010/README.md`.

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

### 2.4 Aggiornamento dopo le decisioni del 2026-10-10 (sera): richiesta unica per i Passi 4-5

Questa sezione sostituisce §2.0-2.3 dove li contraddice. **Nulla è stato lanciato con sudo.**

**Posizione dell'utente su B2-partition (da confermare):** per il 16 solo **B1 e B2-kill**, con la variante decisa dalla calibrazione di L_dns; l'helper con sudo per B2-partition dopo. Il braccio senza mTLS in M6/M7 è **D** (non il default); il braccio mTLS è C.

**1. Comandi che lanci tu, con sudo sul nodo** (`T=~/dib_tnsm/tree-<commit>`; script in `$T/experiments_tnsm/m67_retraction/`):
1. `sudo modprobe sch_netem && lsmod | grep sch_netem` (G3).
2. Rivedere prima l'output di `netem_apply.sh --dry-run <profilo>` (il filtro è sul progetto `dibtnsm`; sul nodo girano anche k3s e wasmbed, che non vanno toccati).
3. `sudo $T/.../netem_apply.sh wan`, poi `sudo $T/.../netem_show.sh` (verifica del `tc qdisc` in ogni namespace del progetto); poi io lancio L_dns e la calibrazione dei log; lo stesso con `degraded`.
4. **tcpdump dentro il namespace del container**, con `degraded` applicato, mentre io invio 20 tentativi per braccio (D, poi C; il cluster va ricreato fra i due), annotando l'orologio di inizio:
   `sudo nsenter -t $(docker inspect -f '{{.State.Pid}}' dibtnsm-evidence-1) -n timeout 300 tcpdump -i eth0 -w /tmp/dib_degraded_<D|C>.pcap 'tcp port 8000'`, poi `sudo chown ubuntu /tmp/dib_degraded_*.pcap`.
5. **Pulizia finale:** `sudo $T/.../netem_apply.sh lan`, poi `sudo $T/.../netem_show.sh`: **nessun netem deve restare in nessun namespace** (un residuo contaminerebbe le misure successive). Verifica che l'output mostri solo il qdisc di default (`noqueue` o `fq_codel`) per ogni container.

**2. Calibrazioni che lancio io, senza sudo.** Cluster D (plain, il braccio di M6/M7), tutte da `~/dib_tnsm/tree-<commit>`:
1. **Pipeline dei log con due container in parallelo** (`calib_logs.py --n 100`): evidence da sola e poi evidence con `site-0`, ordine e scarto relativo; a `lan`. Per il braccio mTLS la latenza dei log si assume uguale (la pipeline Docker non dipende da TLS); **è un'assunzione**, e il presenza dell'access log in mTLS è già verificata (diagnostica del 2026-10-10).
2. **L_dns** (`calib_ldns.sh`): a `lan` subito; a `wan` e `degraded` **solo dopo che avrai applicato i profili** (punto 1.3). Da questo valore si decide la variante di B2 (≤ 50 ms: entrambe; ≥ 0,5 s: solo B2-partition più `kill-min`; nel mezzo ricalcolo e decidi tu).
3. Dalle calibrazioni: soglie per profilo (P-log usabile se il p95 della latenza è < 10% della mediana del ritiro diretto del profilo, altrimenti ripiego `dispute-rtt`), committate prima del lancio.

**3. Cosa resta da scrivere io prima del lancio di M6/M7:** driver `m67_retraction/run.py` con le ipotesi e la predizione (a) ricongelata (§1.5 B3), GATE 3 (10 ripetizioni, test sui due bracci mTLS **uniti**, verifica preliminare che i bracci non differiscano a T fisso; qui i bracci sono D e C, quindi la verifica va fatta fra D e C: **se differiscono, il test unito perde validità e mi fermo**), ordine dei blocchi di profilo randomizzato e registrato nel manifest.

**4. Decisione che ti chiedo.** Conferma della posizione su B2-partition (solo B1 e B2-kill per il 16, helper dopo). Con le tue decisioni sul sudo (punti 1.1-1.5 li lanci tu) posso procedere con le calibrazioni senza sudo (2.1 e 2.2 a `lan`) appena dai l'OK a partire.
