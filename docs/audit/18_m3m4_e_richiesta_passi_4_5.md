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

#### 1.7.1 Correzioni e cautele (revisione dell'utente dopo i dati grezzi, 2026-10-10)

0. **Verifica.** L'analisi di §1.7 (commit `8fbe400`, `00b2d56`) è stata ricalcolata da zero dai 20 record grezzi (`cells.jsonl`) con `analyze_m4.py` su una copia: l'output è **identico** a `analysis.txt`. Il lancio è finito alle 22:43:57; 644 000 operazioni cronometrate, 20 celle su 20.
1. **Affermazione da qualificare.** Il testo di §1.7 dice che a 50 e 100 writer "il costo di mTLS cresce con il carico". **Non è un risultato:** il rapporto C/D vale 0,603 (1 writer), 0,794 (10), 0,598 (50), 0,543 (100), cioè **non è monotono**, e il generatore (un solo host, thread Python) **non è misurato durante la cella**: se a 100 writer satura, il rapporto è distorto in una direzione non nota. Va letto come ipotesi. Nessun commento sulla forma della curva oltre i dati.
2. **Due rapporti, da riportare entrambi, con la differenza spiegata.**
   - **C/A "come spedito"** (M3, default senza mTLS): 0,83 a 100 writer (438,4 / 528,2, FANOUT 10), 1,01 a 50, 1,47 a 10, 1,84 a 1.
   - **C/D "TLS isolato"** (questo rilancio): 0,54 a 100 writer, 0,60 a 50, 0,79 a 10, 0,60 a 1.
   - La differenza è che il braccio di default paga ~6 ms per chiamata fra servizi (contesto SSL costruito a ogni chiamata) e D no. Confronto A (M3) contro D (M4): 528 → 824 ops/s a 100 writer (**+56%**), ma **fra lanci diversi** (cluster, ora e ordine diversi): è descrittivo, non una misura appaiata.
   - Entrambi valgono per il prototipo senza pool fra i servizi (handshake completo a ogni chiamata), non per un deployment ottimizzato.
3. **Plateau del paper vecchio da rimettere in discussione** (collo di bottiglia in SQLite / evidence service che limita il guadagno, `main_old.tex:503-505`): con D il throughput a 100 writer è circa il 56% sopra il default, quindi parte del plateau veniva dalla spesa per chiamata. **L'uso di CPU del nodo e dei container durante le celle non è stato misurato** (solo il campione di fondo prima di ciascuna cella): con questi dati **non si può dire se a 100 writer il limite sia la CPU o il database.** Non si cambia il testo del paper. Diagnostica proposta, **da autorizzare**: D a 100 writer, 3 celle, campionamento di `/proc/stat` sul nodo e sull'host del generatore e `docker stats` durante la fase cronometrata.
4. **Prossimi driver:** campionamento di `/proc/stat` sull'host del generatore durante la fase cronometrata. In questo rilancio non c'era; è un limite dichiarato.
5. **Errori (7 su 644 000).** Un errore anche nel braccio D (4 a 100 writer) indica che la causa non è mTLS. Sostiene l'ipotesi del keep-alive per `ReadError` e `RemoteProtocolError`, ma non la prova, e non spiega `ConnectError` e `ReadTimeout`, che sono segni tipici di sovraccarico. L'assenza di errori nel braccio senza mTLS di FANOUT 10 in M3 (0 su 322 000) era un caso, non una proprietà.
6. **Igiene.** Nodo a fine run: nessun container `dibtnsm`, 3,6 GB liberi, nessuna directory residua in `/home/ubuntu/snap/docker/3613`.

### 1.8 Diagnostica CPU a 100 writer, a `lan` (`diag_cpu100_20261010/`, 23:05-23:10; albero `~/dib_tnsm/tree-c1cb846`)

**Fissato prima del lancio** (docstring di `diag_cpu100.py`, commit `c1cb846`): saturazione vicina se un processo singolo (servizio o generatore) usa in media ≥ 0,85 core durante la fase cronometrata, o se un host ha una quota occupata ≥ 80% delle sue vCPU. Nodo saturo = host ≥ 80% oppure un container (evidence o sito) ≥ 0,85 core. Generatore saturo = processo ≥ 0,85 core oppure host ≥ 80%. Tabella: nodo saturo e generatore no → limite CPU; generatore saturo → rapporto C/D distorto dal generatore (direzione ignota), con indicazione del nodo; nessuno dei due → database o serializzazione; entrambi → quadro misto.

**Cosa è stato eseguito.** 4 celle a 100 writer (3 D e 1 C, ordine C D D D), 200 operazioni per worker dopo il warm-up; campionamento ogni secondo sul nodo (`/proc/stat` e `cpu.stat` cgroup v2 di ogni container `dibtnsm`) e sull'host del generatore (`/proc/stat` e il processo del generatore stesso), allineati alla finestra cronometrata con l'offset di orologio misurato (85-88 ms); un `docker stats --no-stream` per cella come controllo. Albero pinnato (`service.py` `3186304363ed…`, `launcher_d.py` `1fe42185…`, `cpu_sampler.py` `c154bd78…` nel manifest). Nessun container residuo; nodo a 3,6 GB liberi.

| Cella | Arm | ops/s | p50 / p99 (ms) | Host nodo (core occupati di 16) | Evidence (core) | Sito max (core) | **Processo del generatore (core)** | Host generatore | Errori |
|---|---|---|---|---|---|---|---|---|---|
| 0 | C | 457,9 | 241 / 436 | 22,2% (3,56) | **1,02** | 0,22 | **1,05** | 16,4% | 0 |
| 1 | D | 855,1 | 125 / 265 | 20,5% (3,29) | 0,865 | 0,19 | **1,12** | 16,8% | 1 (`ReadError`) |
| 2 | D | 823,2 | 126 / 292 | 20,3% (3,25) | 0,840 | 0,19 | **1,12** | 17,1% | 0 |
| 3 | D | 821,9 | 127 / 284 | 20,1% (3,22) | 0,839 | 0,18 | **1,13** | 16,9% | 0 |

- Fondo prima della cella: `other_cores` 0,096-0,249, `steal_pct` 0,005-0,010: **nessuna cella segnalata dalla regola di scarto**. Steal durante la cella: nodo 0,07-0,12%, generatore 0,000%.
- Per operazione: CPU del generatore **1,30-1,38 ms** in D e **2,29 ms** in C; CPU del container evidence 1,01-1,02 ms in D e 2,23 ms in C (core / throughput).
- `docker stats --no-stream` (un solo campione per cella) non è coerente con i contatori cgroup (mostra, per esempio, 96% su `site-1` e 79% su `site-2` contro ~0,2 core di media): non lo uso; fa fede il cgroup.

**Verdetto secondo la tabella fissata: QUADRO MISTO.**
- **Generatore:** processo a 1,05-1,13 core in **tutte e 4** le celle (sopra 0,85, al tetto di un singolo core: è un processo Python, GIL), mentre l'**host del generatore è occupato solo al 16-17%** (≈ 2,7 core di 16). Il generatore è quindi vicino alla saturazione a 100 writer in entrambi i bracci.
- **Nodo:** host al 20-22% (3,2-3,6 core di 16), siti a ~0,2 core ciascuno: **non saturi**. Il container **evidence** è a 0,84-0,87 core in D (a cavallo della soglia di 0,85: due celle sotto, una sopra) e a **1,02 core in C** (saturo, un servizio con un solo processo). Il flag "nodo saturo" del codice non è quindi consistente fra le celle D (vero, falso, falso) solo perché i valori stanno sulla soglia: il verdetto dello script per D è "mixed picture across cells", per C "both".
- **Non** è il database a dare il limite con questi dati: né il nodo né i siti sono vicini alla saturazione; i limiti osservati sono processi singoli (il generatore in entrambi i bracci, evidence in C e quasi in D).

**Che cosa significa per il rapporto C/D a 100 writer (0,54).** Con il generatore al tetto di un core in entrambi i bracci, il throughput osservato coincide con (core del generatore) / (CPU del generatore per operazione): ≈ 1,12 / 1,33 ms ≈ 840 ops/s in D e ≈ 1,05 / 2,29 ms ≈ 458 ops/s in C. Quindi il rapporto C/D a 100 writer **include il costo di CPU del lato client** (cifratura TLS e gestione dei contesti nel generatore) oltre a quello dei servizi: **non misura soltanto il costo di mTLS dei servizi**. La direzione della distorsione non è determinata da questi dati: in D il container evidence (0,84-0,87 core) è anch'esso vicino alla soglia, quindi D è limitato da due processi contemporaneamente. Il rapporto a 1 e a 10 writer (0,60 e 0,79) è meno esposto, perché lì il generatore non è al tetto (non campionato in M4: non lo escludo).

**Plateau del paper vecchio.** Questi dati **non** supportano "il database limita il guadagno": a 100 writer il tetto osservato è il processo del generatore (sempre) e il processo evidence (in C; quasi in D). Il test non è stato fatto sul braccio di default A. Non si cambia il testo del paper.

**Limiti.** Una sola cella C; soglie euristiche (0,85 core) con evidence esattamente sulla soglia in D; un solo host di generatore; il generatore in M4 era lo stesso processo Python a thread. Causa **del plateau**: determinata solo in parte (tetti di processo singolo del generatore e di evidence; il database non è risultato saturo).

### 1.9 Calibrazioni a `lan` (senza sudo; `calib_lan_20261010/`, 23:11, albero `~/dib_tnsm/tree-d54f3e7`, arm D, FANOUT 10, T = 5)

**Non dichiaro soglie né la variante di B2** (dipendono anche da `wan` e `degraded`, che richiedono i comandi sudo dell'utente).

**Pipeline dei log, latenza di `docker logs -t` (ms; `t_log − t_send`, che include i ~1 ms di gestione di `/health`), 100 campioni.**

| Condizione | p50 | p95 | max | min |
|---|---|---|---|---|
| evidence da sola | 1,35 | 1,99 | 22,7 | 1,02 |
| **in parallelo**, evidence | 1,44 | 2,47 | 3,08 | 0,99 |
| **in parallelo**, site-0 | 1,43 | 2,14 | 2,56 | 1,08 |

- Scarto relativo fra i due container (p50 site-0 − evidence): **−0,015 ms**: nessun offset sistematico.
- Ordine relativo: 22 posizioni su 200 hanno un ordine dei log diverso da quello di invio quando i due container ricevono richieste quasi simultanee; è compatibile con la risoluzione della sonda (~1-2,5 ms: jitter di invio fra due thread più jitter dei log). **Il confronto di istanti fra container diversi è affidabile a circa 2-3 ms**, non meglio.
- La latenza include la gestione dell'operazione, quindi la sonda è un limite superiore.
- Per il braccio mTLS la latenza dei log si assume uguale (la pipeline non dipende da TLS): è un'assunzione; l'access log in mTLS è già verificato.
- La regola di accettazione di P-log (p95 < 10% della mediana del ritiro diretto del profilo) si applica quando saranno note le mediane del ritiro diretto: a `lan` il ritiro diretto vale pochi ms (p95 della sonda 2-2,5 ms), quindi la sonda potrebbe non soddisfare la regola a `lan`; **da decidere dopo B1, non ora**.

**L_dns a `lan` (`getaddrinfo('site-3')` da dentro evidence, 50 campioni).**

| Stato di site-3 | p50 | p95 | max | esito |
|---|---|---|---|---|
| vivo (controllo) | 0,14 ms | 0,18 ms | 1,65 ms | risolto |
| fermato con `compose kill` | **2,63 ms** | 2,92 ms | 5,21 ms | `gaierror(-3, 'Temporary failure in name resolution')` |

A `lan` un tentativo verso un sito fermato fallisce in ~2,6 ms, con errore di risoluzione (non RST). Il fatto che sia 18 volte più lento del controllo suggerisce che il resolver incorporato di Docker inoltri la richiesta all'esterno attraverso `eth0`; **se è così, con netem sull'uscita di `eth0` L_dns crescerebbe di almeno `d` per tentativo.** È un'ipotesi: va misurata a `wan` e `degraded` dopo l'applicazione dei profili.

**Altre verifiche della parte live del driver, fatte a `lan` (non è un'integrazione completa):** `Env.up()`, `Env.healthy()` (0,82 s) e la sonda RTT (0,05-0,09 ms, `rtt_matches('lan')` vero) funzionano sul nodo; i dry-run di `netem_apply.sh` per tutti i profili elencano solo gli 11 container del progetto (nessuna traccia di k3s o wasmbed); nessun container residuo, nodo a 3,6 GB liberi. Gli episodi B1/B2, la P-log e il campionamento non sono ancora stati eseguiti dal vivo.

### 1.10 Cella di fumo a `lan` (decisione utente B; `smoke_lan_20261010/` 3 episodi, `smoke20_lan_20261010/` 20 episodi × 2 FANOUT; arm D, albero pinnato, nessun sudo)

**Esito.** Nessun `client_timeout` (0 su 43 episodi), nessuna cella segnalata dalla regola di scarto, carico del generatore (= il nodo) trascurabile (processo 0,02 core, host 7-9%), cluster ricreato una sola volta per cella, profilo `lan` confermato dopo 0,21 s (un solo tentativo di sonda RTT; prima misura 0,05-0,09 ms), nessun container residuo. Il riepilogo di cella calcolato sul nodo coincide con il ricalcolo locale (stesso codice dei test offline: `summarize_rows`, `generator_load`, `client_timeout_s`, `rtt_matches`); il budget del manifest per FANOUT 10 a `lan` (timeout 18 s, H 9 s, B_online 10,5 s) coincide con la tabella dell'audit 18 §1.4. Il manifest contiene ora anche `cells_summary` (tempo di conferma del profilo, riepilogo e carico del generatore per cella).

**Concordanza P-log / `dispute-rtt` (gap = risposta di `/dispute` meno l'istante del log dell'ultimo sito, 20 episodi per FANOUT).**

| | FANOUT 1 (siti in sequenza) | FANOUT 10 (in parallelo) |
|---|---|---|
| `dispute-rtt` mediano | 41,3 ms | 17,6 ms |
| ultimo sito, P-log, mediano | 40,0 ms | 15,2 ms |
| gap min / mediana / p90 / max | 1,01 / 1,46 / 2,06 / 2,30 ms | 1,51 / 2,72 / 3,81 / 4,38 ms |
| episodi con gap > 3 ms | **0 / 20** | **9 / 20** |
| gap negativi | 0 | 0 |
| rapporto di accettazione (p95 log 2,5 ms / ritiro diretto mediano) | **6,3%** (< 10%: P-log accettabile) | **16,4%** (> 10%: P-log non accettabile secondo la regola) |

- Con FANOUT 1 le due misure concordano **entro la calibrazione** (massimo 2,3 ms, p95 della calibrazione dei log 2,0-2,5 ms).
- **Con FANOUT 10 non concordano entro 3 ms in 9 episodi su 20** (massimo 4,4 ms). Il gap non è un errore di misura puro: contiene tempo reale (la risposta di evidence parte dopo che ha atteso tutti i thread del fan-out) più la latenza dei log (~1,4 ms). Le due misure sono un **intervallo**: P-log ≤ ritiro vero ≤ `dispute-rtt`; l'ampiezza mediana a `lan` è 1,5 ms (FANOUT 1) e 2,7 ms (FANOUT 10). Non ho spostato la tolleranza di 3 ms per rientrarci.
- A `lan` d = 0, quindi `dispute-rtt` non ha bias di percorso: per FANOUT 10 a `lan` vale il ripiego `dispute-rtt` previsto dalla regola. La regola va valutata **per cella** (profilo e FANOUT), come fa già `summarize_rows`.
- τ_D per tentativo a `lan` con FANOUT 1: 3,6-4,7 ms fra siti consecutivi (mediana della dispersione prima-ultimo 33,6 ms su 10 siti); è il valore di base per P-a1.
- Primo episodio di una cella: più lento (37 ms contro 15-16 ms nel campione da 3): effetto di avvio; con 10 o più episodi per cella pesa meno.
- Rischio noto, non ancora osservato: a `degraded` (perdita ~10% sul round trip) la sonda RTT (mediana di 3 connessioni per sito) può incappare in una ritrasmissione del SYN da 1 s e far fallire un controllo del profilo; il driver ripete la sonda ogni secondo fino a `--profile-wait` (90 s) prima di abortire.

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

### 2.4 Richiesta unica per i Passi 4-5 (versione della notte del 2026-10-10; SUPERATA da §2.5 per albero, hash e uso del watcher; nulla lanciato con sudo)

`T=~/dib_tnsm/tree-65b0160` (albero pinnato sul nodo; `service.py` `3186304363ed…`; script in `$T/experiments_tnsm/m67_retraction/`).

**Decisione D1: approvata la (a), `netem_watch.sh`.** Lo lanci tu, con sudo, in un terminale visibile, per il solo blocco, e lo termini a fine blocco. Nessuna regola sudoers, nessun demone.

**Script da rivedere (il codice è in questo repository, invariato nell'albero del nodo: gli sha256 coincidono):**

| Script | sha256 |
|---|---|
| `netem_common.sh` (guardia, sorgente degli altri) | `bfce039a5fb5c313b4b63543ae90382a2678b0df8aaa6969ffcd85f5b363d707` |
| `netem_apply.sh` | `f07dfb3677534af84f9454adf7efecb5c87342e5fd11e64ec10626a605f38a25` |
| `netem_watch.sh` | `7ec731d6b01f80323e7c0cf70b831453ad2987b1c61424db30d03f297960ee83` |
| `netem_show.sh` (sola lettura) | `8a0e8ce5533804bae903734456751ab94ff8a02d4b730fc7807591eab95ee2c5` |

Prima di lanciarli: `sha256sum $T/experiments_tnsm/m67_retraction/netem_*.sh` e confronta.

**Cosa garantiscono (verificato da 8 test con `docker` e `nsenter` finti messi per primi nel `PATH`, `test_netem_scripts.py`, 10 esecuzioni su 10 passate):**
1. **Filtro doppio.** Selezione con `docker ps --filter label=com.docker.compose.project=dibtnsm` (l'unica forma di `docker ps` usata); poi, per ogni container, la label deve valere esattamente `dibtnsm` **e** il nome deve essere uno degli 11 attesi (`dibtnsm-evidence-1`, `dibtnsm-site-0-1` … `dibtnsm-site-9-1`), con pid numerico > 1. Container senza label, k3s, wasmbed e qualunque sosia non vengono mai ispezionati né toccati (N-5).
2. **Validazione prima dell'applicazione.** Qualunque anomalia (nome inatteso, label diversa, pid non valido, profilo sconosciuto) abortisce **l'intero script prima di toccare un solo namespace** (N-3). Un difetto della versione precedente, in cui un container sospetto fermava solo un sottoprocesso e il ciclo continuava, è stato corretto e coperto da un test.
3. **Solo `docker ps --filter` e `docker inspect -f <label|pid> <nome atteso>`.** Nessun `docker network`, `exec`, `run`, `rm`, `kill` (N-5). Il ciclo del watcher interroga **solo** `docker ps --filter … --format '{{.ID}} {{.Names}}'` (gli ID cambiano a ogni ricreazione) e, quando la lista cambia, chiama `netem_apply.sh`.
4. **Solo `tc qdisc replace`** dentro il namespace dei container validati, via `nsenter -t <pid> -n tc qdisc replace dev eth0 root netem …` (N-2). L'unica cancellazione è `tc qdisc del dev eth0 root`, usata dal profilo `lan` e dalla pulizia.
5. **Ctrl-C ripulisce solo i container validati (test N-4):** il test avvia il watcher con un cluster finto, simula una ricreazione (nuovi ID e pid) e verifica la riapplicazione sui nuovi pid; poi invia SIGINT e verifica che i `tc qdisc del` vadano **esattamente** ai pid del cluster corrente validato, nessun altro pid, e che il watcher esca con codice 0. `nsenter` compare solo con `tc qdisc`.
6. **Finestra di riapplicazione.** Dopo una ricreazione il cluster gira senza netem fino a ~1 s (polling a 0,5 s più l'applicazione). Il driver non cronometra finché la connessione TCP evidence → sito (misurata con timer, senza sudo) non corrisponde al profilo dichiarato, ripetendo la sonda ogni secondo per `--profile-wait` (90 s), e **abortisce il blocco** altrimenti; per ogni cella il manifest registra `t_created`, `t_profile_confirmed`, `profile_apply_delay_s`, i tentativi e la prima misura (a `lan` 0,21 s). I tempi di applicazione e rimozione che mi comunichi vanno nel manifest con `run.py --record-event applied|removed --profile P --out <dir>` (registrati alla ricezione: un limite superiore del ritardo reale; il watcher stampa anche le ore UTC nel tuo terminale).

**Ordine randomizzato dei blocchi (seme 20261014): `wan`, `lan`, `degraded`.** Nel manifest: seme, `group_order`, `cell_order` e `cluster_recreations` (6 creazioni per profilo per B1 + B2-kill; celle con la stessa chiave (arm, FANOUT, T) condividono un cluster).

**Comandi che lanci tu, in ordine.** Prima di tutto, una volta: `sudo modprobe sch_netem && lsmod | grep sch_netem` (G3).

*Blocco `wan`*
1. Anteprima, senza sudo (output sotto): `bash $T/experiments_tnsm/m67_retraction/netem_watch.sh --dry-run wan`.
2. `sudo bash $T/experiments_tnsm/m67_retraction/netem_watch.sh wan` (terminale visibile; lascialo in esecuzione; stampa l'ora UTC a ogni riapplicazione).
3. Scrivimi "wan attivo". Io registro l'evento e lancio, nell'ordine: (i) `calib_profile.py --profile wan --hold 60`, che crea il cluster D, aspetta che l'RTT confermi il profilo, stampa `VERIFY_NOW` e tiene il cluster 60 s; in quel momento tu esegui **`sudo bash $T/experiments_tnsm/m67_retraction/netem_show.sh`** (sola lettura: una riga `tc qdisc show dev eth0` per container, tutte con `netem … delay 80ms … loss 1%`); poi misura L_dns (`calib_ldns.sh`, con netem sul container che risolve, evidence) e la latenza dei log con due container; (ii) **mi fermo e ti riporto L_dns e le soglie P-log di `wan`**; B2-kill non parte finché non decidi su L_dns; (iii) dopo il tuo via, B1 con `run.py --block b1 --profile wan` (solo B1 se L_dns non è deciso).
4. A blocco finito ti avviso: Ctrl-C nel terminale del watcher (ripulisce) e mi scrivi "wan rimosso".

*Blocco `lan`* (nessun netem; serve anche da prova di pulizia dopo `wan`)
5. Io lancio `calib_profile.py --profile lan --hold 60`; durante `VERIFY_NOW` tu esegui `sudo bash $T/experiments_tnsm/m67_retraction/netem_show.sh`: **nessuna riga deve contenere `netem`**. Poi B1 (e il riferimento "default come spedito", poche celle B1 a `lan`).

*Blocco `degraded`*
6. `bash $T/experiments_tnsm/m67_retraction/netem_watch.sh --dry-run degraded`, poi `sudo bash $T/experiments_tnsm/m67_retraction/netem_watch.sh degraded`; scrivimi "degraded attivo".
7. Come al punto 3 (`--hold 60` con la verifica `netem_show.sh`, che deve mostrare `delay 200ms … loss 5%`; calibrazioni; stop su L_dns e soglie; poi B1).
8. **tcpdump nel namespace con `nsenter`**, per i bracci D e C (il cluster è ricreato fra i due), 20 tentativi per braccio (`run.py --block tcpdump --profile degraded`). Per ogni braccio il driver stampa `TCPDUMP_WAIT arm=<D|C> evidence_pid=<pid>` e aspetta; tu, con la riga stampata:
   - `mkdir -p ~/dib_pcap` (fuori dal repository);
   - `sudo nsenter -t <pid> -n timeout 600 tcpdump -i eth0 -w ~/dib_pcap/dib_degraded_<D|C>.pcap 'tcp port 8000'` (terminale visibile);
   - `touch ~/dib_tnsm/m67/tcpdump_ready_<D|C>` e annota `date -u +%FT%TZ`; il driver stampa `CAPTURE_WINDOW_START`/`END` con l'epoch del nodo;
   - a fine cattura `sudo chown ubuntu ~/dib_pcap/*.pcap`.
9. A blocco finito: Ctrl-C del watcher; mi scrivi "degraded rimosso".

*Pulizia finale e verifica*
10. Io lancio un ultimo `calib_profile.py --profile lan --hold 60`; tu esegui `sudo bash $T/experiments_tnsm/m67_retraction/netem_show.sh` durante il `VERIFY_NOW`: nessuna riga con `netem` in nessun namespace del progetto. Dopo il teardown `docker ps -a --filter label=com.docker.compose.project=dibtnsm` deve essere vuoto. Un residuo contaminerebbe le misure successive.

**Anteprime (`--dry-run`) con gli script definitivi, cluster D acceso a `lan`; i pid cambiano a ogni creazione e vengono sempre riletti; tutti e soli gli 11 container del progetto, per nome:**

`netem_watch.sh --dry-run wan` (include il dry-run di `netem_apply.sh wan`):
```
netem_watch (dry run): profile=wan; containers of project dibtnsm right now (by name):
  dibtnsm-evidence-1
  dibtnsm-site-0-1
  dibtnsm-site-1-1
  dibtnsm-site-2-1
  dibtnsm-site-3-1
  dibtnsm-site-4-1
  dibtnsm-site-5-1
  dibtnsm-site-6-1
  dibtnsm-site-7-1
  dibtnsm-site-8-1
  dibtnsm-site-9-1
netem_apply: profile=wan, 11 of 11 expected containers of project dibtnsm
dibtnsm-evidence-1 (pid 690552): delay 80ms loss 1%
+ nsenter -t 690552 -n tc qdisc replace dev eth0 root netem delay 80ms loss 1%
dibtnsm-site-0-1 (pid 691994): delay 80ms loss 1%
+ nsenter -t 691994 -n tc qdisc replace dev eth0 root netem delay 80ms loss 1%
dibtnsm-site-1-1 (pid 691757): delay 80ms loss 1%
+ nsenter -t 691757 -n tc qdisc replace dev eth0 root netem delay 80ms loss 1%
dibtnsm-site-2-1 (pid 692939): delay 80ms loss 1%
+ nsenter -t 692939 -n tc qdisc replace dev eth0 root netem delay 80ms loss 1%
dibtnsm-site-3-1 (pid 690815): delay 80ms loss 1%
+ nsenter -t 690815 -n tc qdisc replace dev eth0 root netem delay 80ms loss 1%
dibtnsm-site-4-1 (pid 692469): delay 80ms loss 1%
+ nsenter -t 692469 -n tc qdisc replace dev eth0 root netem delay 80ms loss 1%
dibtnsm-site-5-1 (pid 691050): delay 80ms loss 1%
+ nsenter -t 691050 -n tc qdisc replace dev eth0 root netem delay 80ms loss 1%
dibtnsm-site-6-1 (pid 691521): delay 80ms loss 1%
+ nsenter -t 691521 -n tc qdisc replace dev eth0 root netem delay 80ms loss 1%
dibtnsm-site-7-1 (pid 692232): delay 80ms loss 1%
+ nsenter -t 692232 -n tc qdisc replace dev eth0 root netem delay 80ms loss 1%
dibtnsm-site-8-1 (pid 691285): delay 80ms loss 1%
+ nsenter -t 691285 -n tc qdisc replace dev eth0 root netem delay 80ms loss 1%
dibtnsm-site-9-1 (pid 692705): delay 80ms loss 1%
+ nsenter -t 692705 -n tc qdisc replace dev eth0 root netem delay 80ms loss 1%
```

`netem_watch.sh --dry-run degraded`:
```
netem_watch (dry run): profile=degraded; containers of project dibtnsm right now (by name):
  dibtnsm-evidence-1
  dibtnsm-site-0-1
  dibtnsm-site-1-1
  dibtnsm-site-2-1
  dibtnsm-site-3-1
  dibtnsm-site-4-1
  dibtnsm-site-5-1
  dibtnsm-site-6-1
  dibtnsm-site-7-1
  dibtnsm-site-8-1
  dibtnsm-site-9-1
netem_apply: profile=degraded, 11 of 11 expected containers of project dibtnsm
dibtnsm-evidence-1 (pid 690552): delay 200ms loss 5%
+ nsenter -t 690552 -n tc qdisc replace dev eth0 root netem delay 200ms loss 5%
dibtnsm-site-0-1 (pid 691994): delay 200ms loss 5%
+ nsenter -t 691994 -n tc qdisc replace dev eth0 root netem delay 200ms loss 5%
dibtnsm-site-1-1 (pid 691757): delay 200ms loss 5%
+ nsenter -t 691757 -n tc qdisc replace dev eth0 root netem delay 200ms loss 5%
dibtnsm-site-2-1 (pid 692939): delay 200ms loss 5%
+ nsenter -t 692939 -n tc qdisc replace dev eth0 root netem delay 200ms loss 5%
dibtnsm-site-3-1 (pid 690815): delay 200ms loss 5%
+ nsenter -t 690815 -n tc qdisc replace dev eth0 root netem delay 200ms loss 5%
dibtnsm-site-4-1 (pid 692469): delay 200ms loss 5%
+ nsenter -t 692469 -n tc qdisc replace dev eth0 root netem delay 200ms loss 5%
dibtnsm-site-5-1 (pid 691050): delay 200ms loss 5%
+ nsenter -t 691050 -n tc qdisc replace dev eth0 root netem delay 200ms loss 5%
dibtnsm-site-6-1 (pid 691521): delay 200ms loss 5%
+ nsenter -t 691521 -n tc qdisc replace dev eth0 root netem delay 200ms loss 5%
dibtnsm-site-7-1 (pid 692232): delay 200ms loss 5%
+ nsenter -t 692232 -n tc qdisc replace dev eth0 root netem delay 200ms loss 5%
dibtnsm-site-8-1 (pid 691285): delay 200ms loss 5%
+ nsenter -t 691285 -n tc qdisc replace dev eth0 root netem delay 200ms loss 5%
dibtnsm-site-9-1 (pid 692705): delay 200ms loss 5%
+ nsenter -t 692705 -n tc qdisc replace dev eth0 root netem delay 200ms loss 5%
```

`netem_apply.sh --dry-run lan` (la rimozione che fa la pulizia):
```
netem_apply: profile=lan, 11 of 11 expected containers of project dibtnsm
dibtnsm-evidence-1 (pid 690552): no qdisc
+ nsenter -t 690552 -n tc qdisc del dev eth0 root
dibtnsm-site-0-1 (pid 691994): no qdisc
+ nsenter -t 691994 -n tc qdisc del dev eth0 root
dibtnsm-site-1-1 (pid 691757): no qdisc
+ nsenter -t 691757 -n tc qdisc del dev eth0 root
dibtnsm-site-2-1 (pid 692939): no qdisc
+ nsenter -t 692939 -n tc qdisc del dev eth0 root
dibtnsm-site-3-1 (pid 690815): no qdisc
+ nsenter -t 690815 -n tc qdisc del dev eth0 root
dibtnsm-site-4-1 (pid 692469): no qdisc
+ nsenter -t 692469 -n tc qdisc del dev eth0 root
dibtnsm-site-5-1 (pid 691050): no qdisc
+ nsenter -t 691050 -n tc qdisc del dev eth0 root
dibtnsm-site-6-1 (pid 691521): no qdisc
+ nsenter -t 691521 -n tc qdisc del dev eth0 root
dibtnsm-site-7-1 (pid 692232): no qdisc
+ nsenter -t 692232 -n tc qdisc del dev eth0 root
dibtnsm-site-8-1 (pid 691285): no qdisc
+ nsenter -t 691285 -n tc qdisc del dev eth0 root
dibtnsm-site-9-1 (pid 692705): no qdisc
+ nsenter -t 692705 -n tc qdisc del dev eth0 root
```

**Calibrazioni che lancio io, senza sudo** (dopo il tuo "profilo attivo"): L_dns con netem sul container che risolve confrontato con la baseline a `lan` (2,63 ms, `gaierror(-3)`) e la distribuzione della latenza dei log con due container; nessuna soglia né variante di B2 prima della tua decisione su L_dns (regola: ≤ 50 ms per tentativo, entrambe le varianti; ≥ 0,5 s, solo B2-partition più `kill-min`; nel mezzo ricalcolo la tabella dei costi e decidi tu).

**Stato di B1 e B2-kill.** Pronti; B1 provato dal vivo a `lan` (§1.10). B2-kill non è stato provato dal vivo e non parte senza la tua decisione su L_dns; B2-partition non è nel primo giro.

### 2.5 Correzioni agli script netem prima del blocco `wan` (revisione dell'utente, 2026-10-10; nulla lanciato con sudo)

**Albero pinnato: `T=~/dib_tnsm/tree-9e8f2ac`** (`git archive` del commit `9e8f2ac`; `service.py` `3186304363ed…` verificato sul nodo; i commit successivi toccano solo documenti e dati, non gli script). Il vecchio `tree-65b0160` è superato: non usarlo.

**Hash definitivi** (identici in questo repository e nell'albero del nodo, verificati con `sha256sum`; `dryrun_corrected_20261010/sha256_netem_scripts.txt`):

| Script | sha256 |
|---|---|
| `netem_common.sh` (invariato) | `bfce039a5fb5c313b4b63543ae90382a2678b0df8aaa6969ffcd85f5b363d707` |
| `netem_apply.sh` | `d0d9496c22c35a0672434954426ca349c9ec756506b8d435e302dc27f776b0bd` |
| `netem_watch.sh` | `49249c63a6a431f7f7ae94dca795d0f1b92653c4ecb2f5223aae7821e6e62009` |
| `netem_show.sh` (invariato) | `8a0e8ce5533804bae903734456751ab94ff8a02d4b730fc7807591eab95ee2c5` |

**Correzioni A1-A4** (test scritti prima del codice, stessi `docker`/`nsenter` finti; `test_netem_scripts.py` 12 passati su 12, più 11 test di `test_run_helpers.py` e la suite comune, 31 in tutto):
1. **Nuovo tentativo.** `last=$cur` si imposta solo se `netem_apply.sh` riesce; se fallisce il ciclo riprova al giro dopo senza attendere un cambio di lista (N-6: il primo `tc qdisc replace` fallisce una volta, poi 11 riuscite). I messaggi di errore escono al primo fallimento e poi ogni 20 tentativi.
2. **Pulizia rumorosa.** Se `netem_apply.sh lan` fallisce, il trap stampa su stderr `ATTENZIONE: pulizia netem NON riuscita, verifica con netem_show.sh` ed esce con 1 (N-7a: un container con label diversa compare un attimo prima del Ctrl-C). In più, `tc qdisc del` che fallisce non è più ignorato alla cieca: se fallisce si legge `tc qdisc show dev eth0` (sola lettura) e si segnala errore solo se compare `netem` o se la lettura stessa non riesce (N-7b: `del` fallisce e netem resta, errore; N-7c: `del` fallisce perché non c'era nulla, nessun errore).
3. **Firma con il pid.** La firma è `<ID> <nome>` più `pid <nome> <pid>`; i pid si leggono con **una** `docker inspect -f '{{.State.Pid}}' <nomi attesi>` e solo per nomi che corrispondono al pattern atteso (un nome inatteso in `docker ps` non viene mai ispezionato e blocca l'applicazione: N-8b). Stesso ID e stesso nome con pid diverso (compose kill/start) → riapplicazione sui nuovi pid (N-8a). Costo misurato sul nodo: ~17 ms di CPU per chiamata, quindi ~0,07 core a 0,5 s e ~0,35 core a 0,1 s; è un processo "altro" per il nodo e compare nel campione di fondo di ogni cella (`other_cores`, soglia di scarto 1,0, che lo contiene).
4. **Polling e bias del riavvio.** `--poll S` (validato, ≥ 0,05; default 0,5): **0,5 nei blocchi B1, 0,1 nei blocchi B2-kill**. Dato che B1 e B2-kill sono due invocazioni separate di `run.py`, il watcher si riavvia con `--poll 0,1` fra le due (Ctrl-C e nuovo avvio con il driver fermo). Il watcher stampa le ore UTC al millisecondo di "containers changed" e "applied <profilo> (X s)". Per ogni riavvio di sito il driver registra `t_start` (ritorno di `compose start`), `t_first_reconcile_pull` (prima riga `GET /pending/site-3 200` nel log di accesso di evidence dopo `t_start`, stesso orologio) e `site3_started_at`; con `--watch-log <file>` il manifest contiene `site_restarts`: `netem_applied_after_start_s`, `first_reconcile_after_start_s` e `first_reconcile_before_netem`. **Bias dichiarato:** la prima riconciliazione del sito, entro `U(0, 0,1·T)` più ~0,45 s dall'avvio, può partire prima che il watcher riapplichi netem; le righe con `first_reconcile_before_netem=true` ne sono affette e si riportano a parte; senza `--watch-log` il manifest dice che il ritardo **non è misurato**. Il log del watcher si salva con `… 2>&1 | tee -i ~/dib_tnsm/m67/watch_<profilo>.log` (`-i` perché Ctrl-C non fermi `tee` prima della pulizia del watcher: con una pipe rotta la pulizia verrebbe interrotta da SIGPIPE).
5. Un difetto trovato nella lettura del dry-run vivo (ogni nome compariva due volte per la firma nuova) è stato corretto e il test N-1 ora controlla che ogni nome compaia una volta.

**B1 (da dichiarare prima di `wan`): P-log contro `dispute-rtt`.** Il gap risposta − ultimo P-log a `lan` (mediana 1,5 ms con FANOUT 1, 2,7 ms con FANOUT 10; 9 episodi su 20 oltre 3 ms con FANOUT 10) è un risultato: con FANOUT 10 la risposta parte dopo aver atteso tutti i thread del fan-out. P-log e `dispute-rtt` sono un intervallo, P-log ≤ ritiro vero ≤ `dispute-rtt`. A `lan` vale `dispute-rtt` (d = 0, nessun bias di percorso). La regola di accettazione (p95 della latenza dei log < 10% della mediana del ritiro diretto) si valuta **per cella** (profilo e FANOUT). A `wan` e `degraded` P-log **non è dato per accettato**: la soglia numerica si dichiara dopo la calibrazione di ciascun profilo e prima del lancio.

**B2: sonda RTT, tolleranza dichiarata prima di `wan`.** Profilo accettato se, per tutti i 10 siti, la **mediana di 3 connessioni TCP** evidence → sito sta in **±20% dell'RTT atteso R = 2d** (R = 40, 160, 400, 1100 ms per `regional`, `wan`, `degraded`, `extreme`; sito di `mixed` con netem: 80 ms; `lan`: 0-3 ms). Le bande dei profili vicini sono lontane, e ±20% non li confonde (test R-12). Rischio noto a `degraded`: un SYN o SYN-ACK perso viene ritrasmesso dopo 1 s (RTO iniziale), quindi quella connessione dura ~1,4 s; la mediana di 3 regge a un solo campione colpito, fallisce con almeno 2 su 3 (~2,8% per sito, ~25% delle sonde a 10 siti a `degraded`, ~1% a `wan`). Una sonda fallita **non è un errore**: il driver ripete ogni secondo fino a `--profile-wait` (90 s) e solo allora abortisce il blocco (probabilità di 90 s di fallimenti consecutivi a `degraded` ~0,25^45).

**B3: tcpdump.**
- **Lato del tap, da CONFERMARE (non è dato per vero).** Dai sorgenti del kernel, la cattura in uscita su `eth0` avviene dopo il dequeue del qdisc (`dev_hard_start_xmit` → `xmit_one` → `dev_queue_xmit_nit`), quindi dovrebbe vedere i pacchetti dopo netem, senza quelli scartati da netem; il ritardo comparirebbe come tempo di uscita ritardato. Questa è una lettura del codice, non una misura.
- **Prova nella prima cattura a `degraded`:** si confrontano i pacchetti visti dal mittente e dal destinatario. Pacchetti visti dal mittente e mai dal destinatario significano tap prima del qdisc; nessuna differenza in nessuna direzione, su migliaia di pacchetti con 5% di perdita, significa tap dopo il qdisc. Se il tap è dopo il qdisc, un SYN perso è invisibile al mittente: l'RTO di 1 s (a1) si legge dal tempo di connect nelle righe del driver e dal SYN ritrasmesso visto dal destinatario, non dalla cattura del mittente.
- **Due namespace in parallelo** in almeno una cattura (evidence e site-0): il driver ora stampa `TCPDUMP_WAIT arm=<D|C> evidence_pid=<pid> site0_pid=<pid>` e registra `capture_pids`. Comandi per braccio: `sudo nsenter -t <evidence_pid> -n timeout 600 tcpdump -i eth0 -w ~/dib_pcap/dib_degraded_<D|C>_evidence.pcap 'tcp port 8000'` e lo stesso con `<site0_pid>` e `…_site0.pcap`, in due terminali; poi `touch ~/dib_tnsm/m67/tcpdump_ready_<D|C>`; annota l'orologio di inizio e fine (`date -u +%FT%T.%3NZ`) accanto alla finestra stampata dal driver (`CAPTURE_WINDOW_START/END`).
- **I pcap restano fuori dal repository** (`~/dib_pcap`): il braccio D contiene payload in chiaro.

**Anteprime (`--dry-run`) con gli script definitivi, cluster D acceso a `lan`, tutti e soli gli 11 container per nome, ciascuno una volta:** `dryrun_corrected_20261010/` (`watch_wan_poll0.5.txt`, `watch_degraded_poll0.5.txt`, `watch_degraded_poll0.1.txt`, `apply_<profilo>.txt`).

**Procedura del blocco `wan`:** invariata rispetto a §2.4 con questo albero, `--poll 0.5` per B1 (e `tee -i` verso `watch_wan.log`), `--poll 0.1` per B2-kill dopo la decisione su L_dns. Fino al tuo "via" non parte nulla; B2-kill non parte prima della tua decisione su L_dns (regola invariata: ≤ 50 ms entrambe le varianti; ≥ 0,5 s solo B2-partition più `kill-min`; nel mezzo ricalcolo e decidi tu).

**Verifica A del 2026-10-10 (RTT dei due percorsi) — esito: serviva una correzione, in parte.**
- **Sonda del profilo (`VERIFY_NOW`, `calib_profile.py`, `wait_profile`): era già corretta.** Gira da dentro il container evidence (`Env.measure_rtt_ms`, `run.py`) e misura la connessione TCP evidence → sito, con netem sull'uscita di entrambi: RTT = 2d. Le bande ±20% (`RTT_EXPECT_MS`) sono su 2d per **questo** percorso e solo per questo; la sonda non misura il percorso del generatore, quindi il blocco non può abortire né accettare un profilo sbagliato per quel motivo. Ho aggiunto un commento che lo dichiara accanto alle bande.
- **Percorso generatore → container: non era misurato né modellato.** Il generatore è nel namespace radice senza qdisc in uscita: solo la risposta attraversa il netem del container, quindi RTT = d su una connessione riusata. **Ipotesi, da misurare e non ancora verificata sotto netem:** su una connessione nuova il docker-proxy (userland-proxy attivo sul nodo: `docker info` → `EnableUserlandProxy: true`; `docker-proxy` in esecuzione) apre la connessione verso il container all'accept, e il SYN-ACK è ritardato di d, quindi la prima richiesta costa ~2d e la richiesta arriva al servizio con d di ritardo.
- **Conseguenze trovate e corrette (test R-13 scritto prima):**
  1. *Bias di t0.* Il client del generatore è per identità nel braccio C (e il keep-alive scade a ~5 s): un `/dispute` su connessione nuova avrebbe avuto d in più prima di arrivare al servizio, e i timestamp P-log (applicazione − t0) lo avrebbero ereditato, in modo variabile. Ora `Env.warm` fa una `GET /health` non misurata sulla stessa connessione subito prima di t0 (B1) e prima di ogni `/dispute` e `/restore` (B2-kill): le chiamate misurate girano su connessione riusata, bias del generatore ~d, uguale in ogni episodio.
  2. *Calibrazione dei log.* `calib_logs.py` apriva una connessione nuova per ogni richiesta (`urllib`): sotto netem la latenza dei log sarebbe risultata gonfiata di ~d (80 ms a `wan`). Ora usa connessioni persistenti con warm-up e riporta a parte, come diagnostica, la latenza con connessioni nuove (`fresh_connection_diagnostic`, 30 richieste), che mostra l'effetto.
  3. *Bias di `dispute-rtt`.* `dispute_rtt_bias_ratio` usa ora d del percorso del generatore (`gen_path_d`: d del profilo, 0 a `mixed` perché evidence non ha netem), non il d evidence↔sito.
  4. *Misura del percorso.* Per ogni cluster il manifest registra `generator_path_ms` (mediana di 5 `GET /health` su connessione riusata e di 5 su connessione nuova, con `reused_ok`/`fresh_ok` a ±20% di d e 2d; nessun controllo per mTLS con connessione nuova, dove l'handshake aggiunge round trip). **Informativo, non abortisce**: se `reused_ms` non è ≈ d, o `fresh_ms` non è ≈ 2d, lo riporto senza correggere.
- **Residuo dichiarato (B2-kill):** la convergenza dopo `start` si legge dal polling di `/export_mud` sul sito: connessioni nuove verso un sito appena riavviato, bias ≤ 2d sul tempo di rilevazione (d per il dial del proxy, d per la risposta). Va nel bias dichiarato di B2-kill.
- **Hash:** i quattro script netem sono **invariati** (tabella di §2.5 valida). Cambiano `run.py`, `calib_logs.py` e `calib_profile.py`; i loro sha256 e il nuovo albero pinnato sono riportati qui sotto e nel manifest di ogni lancio.

**Albero pinnato aggiornato: `T=~/dib_tnsm/tree-54f7741`** (`git archive` del commit `54f7741`; `tree-9e8f2ac` rimosso dal nodo, era una copia mia). `service.py` `3186304363ed…`. Script netem **invariati**, stessi sha256 della tabella di §2.5 (verificati sul nodo). Altri file:

| File | sha256 |
|---|---|
| `run.py` | `fceee42680b77945e74b89ef32c239af4f297109cb6897fd2dee8be907e3cda4` |
| `calib_logs.py` | `c221ca812c6c8d6065d07641cdac38364a8f4dd3f2aa168022e105f1c7b76a93` |
| `calib_profile.py` | `f045d0fdcfd543f8d3a98a6de739ec488290cf430d269eda5e595bb6676c1c38` |
| `calib_ldns.sh` | `0191b1fafc52dc05a69f198390d1029467b4273b04fed9b3ddc771d989a28ba7` |

Nel blocco, sostituire `tree-9e8f2ac` con `tree-54f7741` in tutti i comandi di §2.4-§2.5.

**Chiamate del generatore con connessioni nuove dentro intervalli cronometrati (lettura di `run.py` albero `54f7741`, nessuna esecuzione).** Righe di `run.py` del commit `54f7741`.
- **B1.**
  - L'unico intervallo cronometrato dal generatore è `[t0, t_resp]` del `/dispute` (`run.py:517`), preceduto da `Env.warm`: connessione riusata, bias ~d.
  - I tempi di ritiro sono P-log, cioè timestamp dei log dei container meno t0 (`:530-535`): non dipendono dai percorsi delle altre chiamate. `setup_fact` (`:493-499`) e `/seed` non sono cronometrati.
  - Le `GET /pending/site-i` dopo la risposta (`:522`, `:529`) **non producono tempi**: stabiliscono *se* c'è una consegna in pending e fanno da condizione di attesa. Nel braccio C usano il client per identità `site-i` e possono girare su connessione nuova (prima volta nella cella o keep-alive scaduto, ~5 s): la lettura può essere in ritardo fino a ~2d, quindi uno stato drenato nei 2d precedenti potrebbe contarsi come "non pending". Con T = 5 s il primo drenaggio avviene dopo ≥ ~0,5 s, quindi il caso è marginale ma **non escluso a `degraded` (2d = 0,4 s)**: lo dichiaro come bias possibile della conta delle consegne in pending (predizione (c)), da guardare nel confronto con la tcpdump.
  - Il tempo di ritiro via pending è `POST /pending/site-i/ack` nel log di evidence: nessun polling del generatore. La misura "poll" del piano (riparazione da snapshot) **non è implementata** in B1: i tipi di misura nelle righe sono solo `P-log-apply`, `P-log-ack` e `dispute-rtt`.
- **B2-kill.** Sono cronometrati `t_kill` e `t_start` (ritorno dei comandi `compose`, non percorso di rete) e il **polling di `/export_mud` sul sito riavviato** (`:575`, P = 50 ms, timeout 2 s), da cui `t_up` e `t_withdrawn`: la prima risposta dopo `start` arriva su connessione nuova (bias ≤ 2d: d per il dial del proxy, d per la risposta); le successive su connessione riusata (bias ≤ d più 50 ms di periodo). È il bias di B2-kill già dichiarato sopra; si aggiunge al ritardo di riapplicazione di netem. I `/dispute` e `/restore` della prova sono preceduti da `Env.warm`; `/pending` (`:566`) e `/state` (`:597`) non sono cronometrati.
- **Flag di `generator_path_ms`.** Il valore con `reused_ok`/`fresh_ok` è già in `cells_summary[*].profile_timing.generator_path_ms` del manifest e nel record di ogni cella, e stampato a console al momento della misura; fuori dal ±20% lo segnala senza abortire e senza correggere nulla. Se vuoi un campo di primo livello nel riepilogo di cella lo aggiungo dopo il confronto degli hash (cambia `run.py` e quindi il suo sha256), non prima.

