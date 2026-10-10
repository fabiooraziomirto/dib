# Audit 14 — Priorità degli esperimenti TNSM e piano di esecuzione (rev. 5)

Data: 2026-10-10. Branch `revision-tnsm`. Il documento registra il confronto con la versione precedente del paper, le decisioni dell'utente e il piano approvato (rev. 5, dopo quattro revisioni dell'utente), con le condizioni aggiuntive (GATE). Nessuna misura è stata lanciata per questo documento. Notazione: [C] verificato nel codice o nei dati; [D] deduzione.

## 1. Confronto con la versione precedente del paper (`docs/main_old.tex`, Evaluation, righe 437-660)

**Cosa migliora.**
1. **Le misure di prestazione vecchie non erano difendibili.**
   - Sono state fatte su `service.py` e `services.py` diversi da ogni versione della repo, con 3 ripetizioni e 20 operazioni per worker (audit 04 §1, §6).
   - Il "530.3 ± 7.8" non è riproducibile.
   - La frase "Instrumentation attributes this tail to SQLite's single serialized writer" (`main_old.tex:497`) era un'ipotesi, non una misura: il tetto di 30 s viene dal timeout di checkout del pool (audit 04 §7.4).
2. **f_s = 0,30:** si passa dal commento `% attacco 30%` (`main_old.tex:393`) a f*, alla forma in conteggi K < 5h/7, alla coda binomiale e alla letteratura (audit 09, 11).
3. **Metodo:** ipotesi registrate prima del lancio, bootstrap sulle ripetizioni, manifest, regola di scarto fissata prima.

**Critiche che guidano le priorità.**
1. M1/M2 caratterizzano soprattutto un artefatto di configurazione (pool di 15 connessioni con 100 thread): si riducono a un paragrafo con due bracci (Passo 7).
2. Il risultato nuovo per TNSM è M6/M7, cioè ritiro e riconciliazione con rete emulata. Il paper vecchio lo dichiara fuori ambito (`main_old.tex:505`, "WAN latency, packet loss, and asymmetric partitions remain outside this evaluation") e ammette "no established withdrawal deadline" (`main_old.tex:650`).
3. La scalabilità resta debole per costruzione: nodo con 15 GiB, 4 GB di disco liberi, CPU QEMU generica; l'evidence service è il collo di bottiglia (`main_old.tex:652`). M5 la caratterizza, non la prova.
4. Il punto più debole del paper vecchio, cioè la ranked union che recupera quasi lo stesso rendimento di DIB (`main_old.tex:617`), non era affrontato. Il Passo 6 confronta DIB e ranked union sotto A2 a scala.
5. I dati reali danno una mediana di h_d = 1 (audit 11): con le federazioni osservabili oggi protegge il quorum, non lo score.
6. Anche i numeri di outage e veto del paper vecchio vanno rigenerati dopo D11, D12, D19 e mTLS (G0b, Passo 2).

## 2. Decisioni dell'utente (2026-10-10)

- Priorità: G0, G0b, M3/M4, **M6/M7**, **federazione sintetica DIB contro ranked union sotto A2**, M5, M1/M2 ridotti; IoT-23 se avanza tempo; GothX fuori.
- M1 in corso: fermato e conservato senza analisi (`experiments_tnsm/m1_single_node/aborted_20261010/`, commit `51ad9db`).
- M1/M2: due bracci, `default` e `deploy`.
- M7: netem per container.
- **G0 chiusa: `service.py` congelato** a sha256 `3186304363ed309241134752689423088dda98b9d8fe3bcdf9669749264398fd` (mTLS completato, audit 13 §9). Ogni modifica successiva passa per la regola E (§4, "Se M6/M7 espongono un bug").
- **C8: si adotta la regola per profilo** (decisione con i GATE): `dispute-rtt` a `lan`; P-log nei profili dove il p95 della latenza dei log è < 10% della mediana del ritiro diretto del profilo. La soglia numerica si committa dopo la calibrazione e prima del lancio.

## 3. GATE (condizioni dell'utente, prevalgono sul piano)

Se un GATE fallisce: stop e report con file:riga, nessuna modifica automatica.
1. **Prima del Passo 6 (D0):** definizione esatta di ammissione e di Criterion 1 in `code/src/dib/evaluation/dib.py`, con file:riga, nel docstring di H6-1a. Si verifica che DIB non possa ammettere un fatto A2 con n_avv < ⌈5N/12⌉ per una regola secondaria; se può, D0 si ridefinisce su quella regola e si chiede conferma prima del lancio.
2. **Prima del Passo 4-5 (P-log):** calibrazione di `docker logs -t` anche con due container in parallelo (un sito ed evidence), per verificare ordine e scarto relativo, con la distribuzione riportata; regola per profilo (C8).
3. **Prima di B2-kill e `kill-min`:** potenza di (d-kill). Se con 10 ripetizioni per braccio la differenza attesa (≈ 0,5 s) non si distingue dal jitter U(0, 0,1·T): ~30 ripetizioni con il costo ricalcolato, oppure (d-kill) solo descrittiva. Decide l'utente.
4. **Prima di H6-2:** eccesso atteso con ρ_corr = 0,3 calcolato con la beta-binomiale sui 9 punti con potenza; si verifica che sia rilevabile con 20 000 prove a α = 0,05/59. I punti non rilevabili si escludono dalla famiglia, dichiarandolo.

**Orchestrazione.**
- All'inizio del Passo 3, un'unica richiesta con tutti i comandi sudo, i comandi Docker e le calibrazioni dei Passi 4-5, con l'elenco di quelli che lancia l'utente.
- I passi senza punti di stop (0, 1, 6a, codice dei Passi 6 e 7 fino al pre-lancio) si eseguono di seguito.

## 4. Piano approvato (rev. 5)

### Premesse verificate nel codice (lettura, nulla eseguito)
- **V1. Timeout del fan-out.**
  - Ogni tentativo è `httpx.post(..., timeout=_FANOUT_TIMEOUT_S)` (`code/src/dib/registry/distributed/service.py:707-711`), con `_FANOUT_RETRIES = 3` e `_FANOUT_TIMEOUT_S = 1.0` (`:120-121`), senza pausa fra i tentativi (`:701`). Se tutti falliscono, l'evento va in `pending_fanout` (`:717-726`).
  - Il timeout vale 1 s **per fase** (connect, read, write, pool); non c'è un tetto totale.
  - httpcore 1.0.9 applica il timeout di connect separatamente a TCP e TLS (`httpcore/_sync/connection.py:108,118-129,147-154`); il read timeout vale per ogni lettura (`httpcore/_sync/http11.py:174,200`).
  - Ne segue un **limite rigido per tentativo**, cioè la somma dei timeout di fase: 3 s senza mTLS (connect, write, read) e 4 s con mTLS (più TLS). È il limite per una risposta letta in una sola operazione, come le risposte JSON brevi del servizio.
- **V1b. Nessun riuso delle connessioni.** `httpx.post` apre un `Client` nuovo a ogni chiamata (`httpx/_api.py:102`). Vale anche per la riconciliazione (`service.py:542,563-565`; `RECONCILE_TIMEOUT` = 5 s per fase, `:138`).
- **V2. Round trip per tentativo.** 2 RTT senza mTLS; 3 RTT con mTLS (TLS 1.3).
  - Server: uvicorn `PROTOCOL_TLS_SERVER` (`uvicorn/config.py:77,126`). Client: `create_default_context` (`mtls.py:100`). OpenSSL 3.5.9.
  - Chiavi EC P-256 (`code/scripts/make_dist_pki.py:72,95`).
- **V3. Ranked union.** `code/scripts/union_ranked_budget.py:50-73` ordina per il solo score, senza supporto minimo. `budget_yield` (`:76-100`) è riusabile.
- **V4. Simulatore contro binomiale.** Nessun modello di avversario in `dib.simulator.sites` (`sites.py:19-36,103`). Il generatore con ρ_corr = 0 condivide H1 di `analysis_fs/fs_binomial.py:5-7`.
- **V5. Arresto di un sito.**
  - Il precedente è `docker compose kill` e poi `start` (`code/scripts/fault_injection_experiment.py:61-63,91,113`).
  - I siti sono indirizzati per nome (`service.py:192-194`; `docker-compose.yml:11-20`).
  - La `getaddrinfo` dentro `socket.create_connection` non è limitata dal timeout (`httpcore/_backends/sync.py:208-212`).
  - Con il container ucciso, l'esito è un errore DNS di durata L_dns [D, comportamento di Docker].
- **V6. Concorrenza del fan-out.** Con `FANOUT_CONCURRENCY` = 1 è sequenziale sui siti (`service.py:728-732`); con 10 i siti vanno in parallelo (`:324,736-745`). I 3 tentativi per sito sono sempre sequenziali (`:705`).
- **V7. Trigger.** Primo run dopo U(0, J), con J = 0,1·T (`service.py:57-58,143,241`). Poi T + U(0, J) (`:270`). Se un run fallisce, backoff 1, 2, 4, … s con tetto min(T, 30 s) (`:59-61,262-263`). Ogni episodio fa 3 fan-out (`:808-870`).
- **V8. Bound binomiale.**
  - `p_violate(N, q) = P(Binomial(N, q) ≥ ⌈5N/12⌉)` (`analysis_fs/fs_binomial.py:28-34`), su N ∈ {5, 10, 20, 50, 100} × q ∈ {0,01; 0,05; 0,1; 0,2; 0,3} (`:38-43`).
  - 9 punti ≥ 7,2·10⁻³; 3 intermedi (1,6·10⁻³; 1,2·10⁻³; 3,2·10⁻⁴); 13 < 1,5·10⁻⁴.
  - N è N_d.
- **V9. Timestamp interni.**
  - Nessun campo temporale nelle tabelle (`service.py:359-361,662-669`).
  - Nessun log applicativo per `/dispute` o `/apply_fanout`: l'unico logger (`:189`) scrive solo i fallimenti del trigger (`:260,266`).
  - L'unico tempo esposto è quello monotono del trigger in `/health` (`:234-235,252,269,282`).
  - L'access log di uvicorn è attivo di default (`Dockerfile:20`; `mtls.py:91,158`).
- **V10. Sonda P-log.**
  - `docker logs -t` sulla riga `POST /apply_fanout 200` del sito: l'applicazione avviene prima della risposta (`service.py:498`).
  - `docker logs -t` sulla riga `POST /pending/<site>/ack 200` di evidence: l'ack segue l'applicazione (`service.py:559-566,895-910`).
  - Limiti: (i) latenza della pipeline dei log; (ii) associazione degli eventi per ordine; (iii) la riparazione da snapshot (`:567-572`) non lascia log; (iv) il driver di log; (v) l'access log in mTLS da confermare.
- **V11. Sweep di H6-1b.** 4 N × 4 presenze × 5 q × 2 ρ_corr = 160 punti, più il punto ancorato × 5 q × 2 ρ_corr = 10: **170 punti**.
- **V12. Timeout dei client del generatore** (verifica 1).
  - `code/scripts/distributed_concurrency_benchmark.py` usa `httpx.Client(timeout=5.0)` (`:79` con mTLS, `:110` senza): 5 s per fase, compresa l'attesa della risposta di `/dispute` (una sola lettura).
  - Gli altri script: `fault_injection_experiment.py` chiama `/dispute` con il default di httpx, 5 s per fase (`:80-104`, nessun timeout esplicito), poi `/pending` con 5 s (`:110`) e `/state` con 3 s (`:122`); `dispute_flood.py` usa 10 s (`:72,95`).
  - Lo script di M6/M7 non esiste ancora.
  - **5 s è più corto della durata attesa di `/dispute`** a `degraded` con concorrenza 1 (≈ 11-20 s) e a `extreme` (≈ 30 s con concorrenza 1): vedi la tabella al Passo 4-5. Per M3/M4, che girano a `lan`, non è un problema.
- **V13. Riconciliazione: fasi e durata** (verifica 2).
  - `_reconcile_once` fa fino a `_RECONCILE_MAX_ROUNDS` = 3 round (`service.py:122,540`). In ogni round: `GET /pending` (`:542`), poi, se ci sono eventi, applicazione locale e `POST /ack` (`:552-566`). Dopo i round, la riparazione da snapshot è solo locale (`:567-572`, nessuna chiamata HTTP).
  - Caso tipico (eventi presenti al primo pull): GET, ACK, GET vuoto = **3 chiamate** HTTP. Caso massimo: 3 × (GET + ACK) = **6 chiamate**.
  - Senza perdite: D_run = 3 × n_RTT × R, con n_RTT = 2 o 3 (V2):
    - `lan` ≈ 0,06 s (misurato, `results/fault_injection/results.csv`, `reconcile_s_mean`);
    - `wan` (R = 0,16 s): 0,96 / 1,44 s;
    - `degraded` (R = 0,4 s): 2,4 / 3,6 s;
    - `extreme` (R = 1,1 s): 6,6 / 9,9 s.
  - Con perdite, una ritrasmissione del SYN costa 1 s, e altre ritrasmissioni stanno nei 5 s per fase. Si assume un margine di 2 s: **D_run_max = 3·n_RTT·R + 2 s**.
  - Il limite rigido teorico (6 chiamate × somma dei timeout di fase di 5 s) è di decine di secondi e non è usato come bound.
  - **Il bound "1,1·T + 5 s" non regge** a T = 5 s: a `extreme` vale 1,1·5 + 8,6 = 14,1 s senza mTLS e 1,1·5 + 11,9 = 17,4 s con mTLS, contro 10,5 s; a `degraded` con mTLS 1,1·5 + 5,6 = 11,1 s, contro 10,5 s. Correzione sotto, al Passo 4-5.
- **V14. Dove si contano avversari e accordo** (verifica 3).
  - `analysis_fs/bound_grid.population(n, k, rho)` (`bound_grid.py:73-85`) riceve k = numero di siti avversari come **argomento**: n_avv = k per costruzione. Tutti i k avversari riportano lo **stesso unico fatto** (`"fake.example"`), quindi l'accordo è totale per costruzione.
  - `empirical()` conta solo le osservazioni avversarie (`n_adv`, `:94`), non i siti.
  - Lo stesso vale per `analysis_fs/test_followup._flood` (`:85-88`, lista `adv` esplicita).
  - Il generatore del Passo 6 non esiste: deve **registrare per ogni prova, prima dello scoring**, n_avv (siti avversari per il tipo), l'insieme dei fatti A2 e, per ogni fatto A2, il supporto avversario |S_e ∩ Avv|. Così il controllo del generatore non dipende dall'esito di DIB.

### Premesse contraddette (dette esplicitamente)
- **C1-C4** (rev. 2-3): timeout per fase; campione NCSU già analizzato; `compose kill` non dà un RST garantito; convergenza dopo il riavvio indipendente da T.
- **C5** (rev. 4): kill e partition coincidono solo nel costo, non nella convergenza.
- **C6** (rev. 4): `mixed`, RTT = d e perdita ≈ p (confermato).
- **C7 (correzione 3 di queste istruzioni).** "Per i punti con p* < 3,3·10⁻⁴ un solo fallimento di DIB in 20 000 prove falsifica comunque H6-1a" è **vero solo in parte**. Al livello della famiglia ridefinita (α = 0,05/59, vedi Passo 6), con un fallimento il limite CP inferiore vale 4,2·10⁻⁸. Supera p* solo per gli **8 punti con p* ≤ 2,4·10⁻⁸**. Per gli altri servono:
  - 2 fallimenti per p* = 4,5·10⁻⁷ e 2,0·10⁻⁷;
  - 4 per 9,9·10⁻⁶;
  - 7 per 6,4·10⁻⁵ e 6,0·10⁻⁵;
  - 17 per 3,2·10⁻⁴.

  Il test sensibile a un solo fallimento a ogni punto è invece il **test deterministico condizionato** D0 (Passo 6): qualsiasi ammissione con n_avv < ⌈5N/12⌉ falsifica, qualunque sia p*.
- **C8 (latenza dei log; **adottata la regola per profilo**, §2).** La regola richiesta ("P-log utilizzabile se il p95 della latenza è < 10% della mediana del ritiro diretto a `lan`") si applica come scritta. Va però segnalato che a `lan` d = 0, quindi il ripiego `dispute-rtt` ha bias nullo dove la regola è più severa. Inoltre il ritiro diretto a `lan` vale pochi ms (≈ 5 ms con concorrenza 10), quindi la soglia sarà ≈ 0,5-2,5 ms e potrebbe escludere P-log anche dove servirebbe (d > 0). Propongo un'alternativa, **da confermare**: la regola si valuta per profilo, `dispute-rtt` a `lan` e P-log dove il p95 della latenza è < 10% della mediana del profilo.

### Passo 0: fermare M1 (subito dopo l'approvazione)
0. Disco: `df -h /` sul nodo e su questo host; stop se < 2 GB (regola G).
1. Sul nodo: `ps -o pid,pgid,ppid,cmd -p 22376`. Si procede solo se il comando è ancora `../venv/bin/python experiments_tnsm/m1_single_node/run.py … --commit c23d1e3`. Poi `kill -TERM 22376`, **solo il PID, mai il gruppo 22368**.
2. Controllare con `ps` che il processo sia uscito (M1 non crea sottoprocessi oltre al `pip freeze` iniziale, `experiments_tnsm/common/cells.py:83`). Se dopo 30 s è ancora vivo, chiedere prima di usare `-KILL`.
3. Validare l'ultima riga di `~/dib_tnsm/out/m1_single_node/cells.jsonl` con `json.loads`. Se è troncata, annotarlo nel README e non correggere il file.
4. Copiare `cells.jsonl` e `m1.log` in `experiments_tnsm/m1_single_node/aborted_20261010/`, con un `README.md`: motivo, commit `c23d1e3`, N celle su 50, ora UTC dello stop, esito della validazione, "non usare in statistiche".
5. Lasciare sul nodo `venv/` e `tree-c23d1e3/`. Commit: `experiments: stop M1 (default config), keep partial cells unanalyzed`.

### Passo 1: audit 14 (documento)
`docs/audit/14_priorita_esperimenti_tnsm.md`: confronto con `main_old.tex`, decisioni, freeze di G0, premesse V1-V14 e C1-C8 di questo piano, regola E. Una riga in `04_piano_misure_tnsm.md` §0 e in `13_mtls_design.md` §9. Commit.

### Passo 2: G0b, rigenerazione unica
Disco all'inizio. Voci 1-4 di `docs/work/regenerate-results-after-service-changes.md`, con l'output in `experiments_tnsm/g0b_regen/`. Le voci 3-4 usano Docker sul nodo, dopo OK. Diff con i numeri del paper vecchio nell'audit 15. Copia in `results/` e ritorno di `verify_artifact.py` a 262/0 solo con OK esplicito, in un commit separato. Cleanup Docker mirato (regola G).

### Passo 3: M3/M4 (distribuito e costo di mTLS), dopo OK al lancio
- Servizi: Docker sul nodo, progetto compose a nome fisso `dibtnsm`, override in `experiments_tnsm/m3_distributed/`. Porte già pubblicate: 18100 e 18110+ (`generate_compose.py:48,63`).
- Generatore: su questo host, con `distributed_concurrency_benchmark.py --evidence-url/--site-urls [--pki]` (righe 190-200).
  - **Differenza voluta rispetto a M6/M7:** in M3/M4 il generatore sta su un altro host per non sottrarre CPU ai servizi durante il carico; in M6/M7 sta sul nodo per la sonda P-log (Passo 4-5).
  - Le latenze assolute di M3/M4 e di M6/M7 **non si confrontano**, perché M3/M4 hanno in più l'hop LAN (≈ 0,17 ms, audit 04 §7.2) e il generatore è in una posizione diversa.
- Bracci alternati per ripetizione: `FANOUT_CONCURRENCY` ∈ {1, 10} × mTLS ∈ {off, on}. 10 ripetizioni, 200 operazioni per worker.
- Riuso di `experiments_tnsm/common/` (`cells.py`, `node_monitor.py`, `discard_rule.json`, `analyze.py`). M4 è un limite superiore (nessun pool, V1b).
- **In parallelo, mentre gira M3/M4:** preparo e provo con `--dry-run` gli script netem del Passo 4-5. Raccolgo in un'unica richiesta tutti i comandi sudo e gli OK del Passo 4-5, comprese la cattura `tcpdump`, la calibrazione di L_dns (V5) e quella della pipeline dei log (V10).

### Passo 4-5: M6×M7, disegno fattoriale (ritiro e riconciliazione sotto rete emulata)
Script `experiments_tnsm/m67_retraction/run.py` più `netem_apply.sh` e `netem_clear.sh` riscritti. Il vecchio `m7_netem/README.md` resta, con una nota di supersessione.

**Generatore e oracolo sul nodo: requisito, non preferenza.**
- Generatore di eventi e oracolo di M6/M7 girano **sul nodo 192.168.100.57, nel namespace di rete radice**, nello stesso processo `run.py`.
- t0 (invio di `/dispute`) si registra con `time.time()` (`CLOCK_REALTIME` del nodo). È lo stesso orologio con cui il demone Docker del nodo marca le righe di `docker logs -t`: la sonda P-log richiede un unico orologio per t0 e per i timestamp dei log, e un generatore su un altro host introdurrebbe lo scarto fra gli orologi dei due host.
- `time.monotonic()` si registra accanto, per le durate interne al generatore.
- Si differenzia volutamente dal Passo 3 (vedi lì).
- **Manifest:** host del generatore (hostname, IP, namespace = radice) e sorgente dell'orologio.

**Netem per container.**
- Per ogni container del progetto `dibtnsm` (guardia sulla label `com.docker.compose.project=dibtnsm`) si ricava il PID con `docker inspect`, poi `nsenter -t <pid> -n tc qdisc replace dev eth0 root netem delay <d> loss <p>`.
- Li lanci tu con sudo; io verifico con `tc qdisc show`.
- Un pacchetto da X a Y attraversa solo il qdisc in uscita di X.

| Profilo | d per lato | p per lato | RTT evidence↔sito (R) | perdita sul round trip |
|---|---|---|---|---|
| `lan` (baseline) | 0 | 0 | ~0,1 ms | 0 |
| `regional` | 20 ms | 0,1% | 2d = 40 ms | ≈ 2p = 0,2% |
| `wan` | 80 ms | 1% | 2d = 160 ms | ≈ 2p = 2% |
| `degraded` | 200 ms | 5% | 2d = 400 ms | ≈ 2p = 10% |
| `extreme` (da confermare) | 550 ms | 0 | 2d = 1100 ms | 0 |
| `mixed` | evidence 0; metà dei siti 80 ms / 1% | | d = 80 ms verso i siti `wan` | ≈ p = 1% |
| `partition` (B2-partition) | perdita 100% in uscita da un solo sito | | — | — |

**Timeout del client del generatore (V12).**
- Lo script nuovo imposta timeout espliciti, senza toccare `service.py` né `distributed_concurrency_benchmark.py`:
  - `/dispute` e `/restore`: read timeout = 2 × il limite rigido H del fan-out (tabella sotto);
  - `/state`, `/export_mud`, `/pending`: 5 s per fase, perché la chiamata dura ≤ 3·d ≤ 1,65 s anche a `extreme` con mTLS;
  - connect, write e pool: 5 s.
- Una cella in cui scade un timeout del client si registra come **`client_timeout`** ed è **esclusa**. Non si conta mai come fallimento del servizio: si riporta il numero per profilo.

Durata di `/dispute` (fan-out sincrono, V6), per profilo e concorrenza:
- attesa E = consegne riuscite (n_RTT·R) più i tentativi falliti attesi (f/(1 − f) per sito, ≈ 1,4 s l'uno);
- limite rigido H = 10 siti × 3 tentativi × 3 s / 4 s (V1) con concorrenza 1, oppure 3 tentativi × 3 s / 4 s con concorrenza 10;
- più ≤ 3·d per il percorso generatore↔evidence.

| Profilo | Conc. | E senza mTLS / mTLS (s) | H senza mTLS / mTLS (s) | Timeout del client = 2H (s) |
|---|---|---|---|---|
| `lan` | 1 | 0,05 / 0,05 | 90 / 120 | 180 / 240 |
| `lan` | 10 | 0,01 / 0,01 | 9 / 12 | 18 / 24 |
| `regional` | 1 | 0,8 / 1,2 | 90 / 120 | 180 / 240 |
| `regional` | 10 | 0,08 / 0,12 | 9 / 12 | 18 / 24 |
| `wan` | 1 | 3,4 / 5,0 | 90 / 120 | 180 / 240 |
| `wan` | 10 | 0,4 / 0,6 | 9 / 12 | 18 / 24 |
| `mixed` | 1 | 0,9 / 1,3 | 90 / 120 | 180 / 240 |
| `mixed` | 10 | 0,2 / 0,3 | 9 / 12 | 18 / 24 |
| `degraded` | 1 | ≈ 11 / ≈ 20 | 90 / 120 | 180 / 240 |
| `degraded` | 10 | ≈ 2,5 / ≈ 4 | 9 / 12 | 18 / 24 |
| `extreme` | 1 | 30 / 30 (ogni tentativo scade al connect, 1 s) | 30 / 30 | 60 / 60 |
| `extreme` | 10 | 3 / 3 | 3 / 3 | 6 / 6 |
| B2-kill (conc. 10, sito morto) | 10 | max(E del profilo, 3·L_dns) | max(H, 3·L_dns) | 2 × max(H, 3·L_dns), con L_dns dalla calibrazione |

Con il timeout di 5 s del benchmark esistente, `degraded` e `extreme` con concorrenza 1 andrebbero in `client_timeout`: per questo M6/M7 usano lo script nuovo.

**Misura del ritiro (V10, sonda P-log).**
- Ritiro diretto: `docker logs -t` sulla riga `POST /apply_fanout 200` del sito, meno t0.
- Ritiro via pending: riga `POST /pending/<site>/ack 200` nel log di evidence, meno t0, con bias ≤ d. Per la riparazione da snapshot: polling con P = 50 ms, bias ≤ d + P.
- **Regola di accettazione della sonda** (sostituisce la soglia fissa di 5 ms):
  - calibrazione a `lan` con ~100 richieste `/health` a tempi noti;
  - P-log è **utilizzabile se il p95 della latenza dei log è < 10% della mediana del ritiro diretto a `lan`**, altrimenti ripiego `dispute-rtt` (limite superiore, stima puntuale = mediana − d, senza flag);
  - la soglia numerica si dichiara e si committa dopo la calibrazione e prima del lancio;
  - alternativa per profilo da confermare (C8).
- Flag del 10% solo per il ritiro via pending.
- **Manifest, per cella:** d, P, latenza dei log calibrata, tipo di misura, host del generatore, timeout del client e numero di `client_timeout`.

**Bound di convergenza, corretti (V13).**
- B_online(profilo, braccio, T) = 1,1·T + max(5 s, D_run_max). È il tempo entro cui un evento in pending di un sito raggiungibile è applicato, misurato dall'inserimento in coda.
- D_run_max = 3·n_RTT·R + 2 s:

| Profilo | D_run_max senza mTLS / mTLS (s) | B_online a T = 5 (s) | B_online a T = 15 (s) |
|---|---|---|---|
| `lan`, `regional`, `wan`, `mixed` | ≤ 3,44 → si usa 5 | 10,5 | 21,5 |
| `degraded` | 4,4 → 5 / **5,6** | 10,5 / **11,1** | 21,5 / **22,1** |
| `extreme` | **8,6 / 11,9** | **14,1 / 17,4** | (solo T = 5 in B1) |

**Predizione (c), scomposta per fase.**

| Fase | Senza mTLS | Con mTLS |
|---|---|---|
| connect | SYN, SYN-ACK (2) | SYN, SYN-ACK (2) |
| TLS | — | ClientHello, volo del server (1-2): 2-3 |
| richiesta e risposta | richiesta (1-2), risposta (1): 2-3 | volo client (1), richiesta (1), NewSessionTicket (1), risposta (1): 3-5 |
| **totale n_c** | **4-5** | **7-10** |

Meccanismo per fase:
- **connect, deterministico:** un SYN o SYN-ACK perso si ritrasmette con l'RTO iniziale di 1 s, che è ≥ il timeout di 1 s, quindi la fase scade sempre. P ≈ 2p (≈ p in `mixed`).
- **TLS e richiesta/risposta:** dopo il primo campione R, RTO = R + max(200 ms, 2R) e PTO del TLP ≈ max(2R, 1,5R + 200 ms); l'attesa dopo una perdita singola è ≈ PTO + R.
  - `regional` ≈ 0,30 s e `wan` ≈ 0,60 s: si recupera; con due perdite nella stessa fase a `wan` la fase scade, con probabilità O(p²);
  - `degraded` ≈ 1,2 s: la fase scade;
  - `extreme`: f = 1.

**Tabella degli intervalli: CONDIZIONATA ALLA CALIBRAZIONE `tcpdump`** (a1 RTO iniziale 1 s; a2 RTO minimo 200 ms e TLP attivo; a3 PTO ≈ 2R, attesa ≈ 1,2 s a `degraded`, vicina alla soglia di 1 s; a4 n_c).

| Profilo | Braccio | f | f³ previsto | Intervallo per la falsificazione |
|---|---|---|---|---|
| `regional` | entrambi | 0,002 | 8·10⁻⁹ | 0 osservati |
| `wan` | entrambi | 0,020-0,021 | 8-9·10⁻⁶ | 0 osservati |
| `mixed` (siti `wan`) | entrambi | 0,010 | 1·10⁻⁶ | 0 osservati |
| `degraded` | senza mTLS | 0,185-0,226 | 0,0063-0,0115 | [0,004; 0,015] |
| `degraded` | mTLS | 0,302-0,401 | 0,028-0,064 | [0,025; 0,08] |
| `degraded`, sensibilità (a3 falsa) | entrambi | 0,0975 | 9,3·10⁻⁴, uguale nei bracci | — |
| `extreme` | entrambi | 1 | 1 | tutte le consegne in pending, applicate entro B_online(`extreme`) |

Osservabile: dopo la risposta di `/dispute`, `GET /pending/site-<i>` su evidence (`service.py:873`).

**Criteri:**
- `degraded`: l'IC Clopper-Pearson al 95% è interamente fuori dall'intervallo del braccio, oppure il braccio mTLS non supera quello senza mTLS;
- `wan`, `regional`, `mixed`: ≥ 2 consegne in pending nel blocco B1 del profilo;
- `extreme`: almeno una consegna diretta riuscita, oppure una consegna non applicata entro B_online(`extreme`);
- intervalli congelati (commit) solo dopo la cattura, e nessun criterio modificato dopo il lancio.

**B1: siti tutti online (k = 0).**
- Fattori: profilo ∈ {lan, regional, wan, degraded, extreme, mixed} × mTLS × `FANOUT_CONCURRENCY` ∈ {1, 10}, con T = 5 s. 10 episodi per cella, 50 a `degraded` (3000 consegne per braccio).
- Predizione (a): ritiro diretto ≈ n_RTT·R + servizio, con R = 2d, e R = d per i siti `wan` di `mixed`. *Falsificata se* la mediana a `regional`, `wan` o `mixed` supera n_RTT·R + 3 × (mediana `lan`) oltre l'IC.

**B2: un sito irraggiungibile durante k episodi** (`FANOUT_CONCURRENCY` = 10).
- **B2-kill:**
  - (d-kill): convergenza dopo `start` ≈ 0,45 + U(0, 0,1·T) + D_run;
  - bound: **1,5 + 0,1·T + max(5 s, D_run_max)**;
  - differenza delle mediane fra T = 15 e T = 5 in [0; 1,5] s.
- **B2-partition:**
  - (d-part): convergenza dopo la rimozione della perdita ≤ **5 + 1,1·T + max(5 s, D_run_max)**; i primi 5 s sono il tentativo in corso al momento della rimozione;
  - differenza delle mediane fra T = 15 e T = 5 in [3; 8] s.
- **Correttezza (e):** nessuna violazione di I1-I3; nessuna regola disputata esportabile oltre il bound della variante e del profilo.

**Regola sulla variante, invariata:** si decide subito dopo la calibrazione di L_dns. Con ≤ 50 ms si tengono entrambe; con ≥ 0,5 s solo B2-partition più `kill-min`; nel mezzo si ricalcola e decidi tu.

**Tabella dei costi, disegno ridotto, ricalcolata con la convergenza corretta.**

Base di stima:
- durata per prova = costi fissi (5 / 10 / 15 s) + convergenza + k × episodio;
- convergenza:
  - kill = 0,45 + 0,05·T + D_run;
  - partition = (5 + 1,05·T)/2 + D_run;
  - D_run mediano: `lan` 0,06 s; `wan` 0,96 / 1,44 s; `degraded` 2,4 / 3,6 s;
- episodio: kill veloce 0,56 / 1,7 / 8,75 s; kill lento e partition 9,5 / 9,5 / 11,0 s.

Ogni riga ha 10 ripetizioni per braccio mTLS; la durata è riportata per i due bracci.

*B2-kill, L_dns veloce*

| k | Profilo | T (s) | Prove | Durata per prova senza mTLS / mTLS (s) | Ore |
|---|---|---|---|---|---|
| 1 | lan | 5 / 15 | 20 + 20 | 6,3 / 6,3 ; 6,8 / 6,8 | 0,035 + 0,038 |
| 1 | wan | 5 / 15 | 20 + 20 | 13,4 / 13,8 ; 13,9 / 14,3 | 0,076 + 0,078 |
| 1 | degraded | 5 / 15 | 20 + 20 | 26,9 / 28,1 ; 27,4 / 28,6 | 0,152 + 0,155 |
| 10 | lan | 5 / 15 | 20 + 20 | 11,4 ; 11,9 | 0,063 + 0,066 |
| 10 | wan | 5 / 15 | 20 + 20 | 28,7 / 29,1 ; 29,2 / 29,6 | 0,161 + 0,163 |
| 10 | degraded | 5 / 15 | 20 + 20 | 105,6 / 106,8 ; 106,1 / 107,3 | 0,590 + 0,593 |
| 50 | lan | 5 | 20 | 33,8 | 0,188 |
| **Totale** | | | **260** | | **2,36** |

*B2-kill, L_dns lento*

| k | Profilo | T (s) | Prove | Durata per prova (s) | Ore |
|---|---|---|---|---|---|
| 1 | lan | 5 / 15 | 20 + 20 | 15,3 ; 15,8 | 0,085 + 0,088 |
| 1 | wan | 5 / 15 | 20 + 20 | 21,2 / 21,6 ; 21,7 / 22,1 | 0,119 + 0,122 |
| 1 | degraded | 5 / 15 | 20 + 20 | 29,1 / 30,3 ; 29,6 / 30,8 | 0,165 + 0,168 |
| 10 | lan | 5 / 15 | 20 + 20 | 100,8 ; 101,3 | 0,560 + 0,563 |
| 10 | wan | 5 / 15 | 20 + 20 | 106,7 / 107,1 ; 107,2 / 107,6 | 0,594 + 0,597 |
| 10 | degraded | 5 / 15 | 20 + 20 | 128,1 / 129,3 ; 128,6 / 129,8 | 0,715 + 0,718 |
| 50 | lan | 5 | 20 | 480,8 | 2,671 |
| **Totale** | | | **260** | | **7,16** |

*B2-partition*

| k | Profilo | T (s) | Prove | Durata per prova (s) | Ore |
|---|---|---|---|---|---|
| 1 | lan | 5 / 15 | 20 + 20 | 19,7 ; 24,9 | 0,109 + 0,139 |
| 1 | wan | 5 / 15 | 20 + 20 | 25,6 / 26,1 ; 30,8 / 31,3 | 0,143 + 0,173 |
| 1 | degraded | 5 / 15 | 20 + 20 | 33,5 / 34,7 ; 38,8 / 40,0 | 0,190 + 0,219 |
| 10 | lan | 5 / 15 | 20 + 20 | 105,2 ; 110,4 | 0,584 + 0,614 |
| 10 | wan | 5 / 15 | 20 + 20 | 111,1 / 111,6 ; 116,3 / 116,8 | 0,618 + 0,648 |
| 10 | degraded | 5 / 15 | 20 + 20 | 132,5 / 133,7 ; 137,8 / 139,0 | 0,740 + 0,769 |
| 50 | lan | 5 | 20 | 485,2 | 2,695 |
| **Totale** | | | **260** | | **7,64** |

*`kill-min`* (k = 1, `lan`, T ∈ {5, 15}, 2 bracci, 10 ripetizioni = 40 prove, L_dns lento): 15,3 / 15,8 s per prova, **0,17 h**.

*B1*: stessa base della rev. 4, ma per `extreme` l'attesa di convergenza per episodio vale 1,05·T/2 + D_run (2,6 + 6,6 / 9,9 s) invece di 10,25 s: **1,87 h**.

**Totali:**

| Scenario | B2-kill | B2-partition | B1 | Totale |
|---|---|---|---|---|
| L_dns veloce | 2,36 | 7,64 | 1,87 | **11,87 h** |
| L_dns lento, entrambe le varianti | 7,16 | 7,64 | 1,87 | 16,67 h |
| L_dns lento, regola applicata (`kill-min` più B2-partition) | 0,17 | 7,64 | 1,87 | **9,68 h** |

Disegno completo, per riferimento: kill veloce 8,70 h; kill lento 21,57 h; partition 22,25 h.

### Se M6/M7 espongono un bug in `service.py` (regola E, da confermare)
- **(i) Correggere, rigenerare G0b e ricongelare l'hash**, se:
  - c'è una violazione di I1-I3;
  - una regola disputata resta esportabile da un sito raggiungibile oltre il **bound del profilo**: B_online, (d-kill) o (d-part) come definiti sopra, non più 1,1·T + 5 s;
  - un sito non converge mai;
  - un **evento è perso**: oltre il bound del profilo dal ritorno, il seq del sito è inferiore a quello dell'evento **e** in `pending_fanout` non c'è una riga (sito, score) con seq ≥ quello dell'evento. Un evento *in coda* non fa scattare il criterio.

  Procedura: test di riproduzione rosso, fix su un branch dedicato, suite verde, G0b rifatta, nuovo hash, rilancio delle celle già misurate.
- **(ii) Dichiarare come limite nel paper**, se è solo prestazione o disponibilità con le invarianti rispettate (pending sotto perdita, fan-out sequenziale lento, handshake per ogni tentativo, L_dns non limitato, D_run che a `extreme` supera 5 s).
- In entrambi i casi: stop, report con file:riga, e decisione tua.
- Una cella con `client_timeout` non è mai un bug del servizio (vedi timeout del client).

### Passo 6a: istogramma di h_d (riuso, nessun download obbligatorio)
- Base: audit 11 (UNSW, Mon(IoT)r, YourThings più NCSU). Mediana di h_d = 1, 0 tipi con h ≥ 5, al più 5 siti indipendenti (`11_hd_distribution.md:79,164`).
- Estensioni opzionali con OK separati: PingPong (dopo la licenza, nulla nella repo) e HomeSnitch (su richiesta).
- **Dichiarazione:** il Passo 6 con N ≥ 10 esplora una popolazione più favorevole alla guardia di quella reale.

### Passo 6: federazione sintetica, DIB contro ranked union sotto A2
`experiments_tnsm/synthetic_federation/`. Riusa `partition_observations` e `apply_synthetic_site_overlap` (`sites.py:19,103`), il DIBScorer (`code/src/dib/evaluation/dib.py`), `budget_yield` (`union_ranked_budget.py:76`), lo stile di `analysis_fs/bound_grid.population` (flood con ρ ≥ 100) e `fs_binomial.p_violate`.

**Riga per l'abstract del risultato (da riportare tale e quale):** *"La federazione sintetica (N ≥ 10 siti per tipo) è più favorevole alla guardia della popolazione reale osservabile (più siti per tipo rendono più facile soddisfare Criterion 1), in cui la mediana di h_d è 1 e i siti indipendenti sono al più 5 (audit 11); i risultati mostrano il comportamento del meccanismo a scala, non quello atteso nelle federazioni misurate oggi."*

- **Avversario:** Bernoulli(q) per ogni sito che ha il tipo; ρ_corr > 0 con una latente condivisa per vendor.
- **Strategia A2:**
  - principale, *collusione totale*: tutti gli avversari del tipo riportano lo stesso insieme di fatti A2, come in `bound_grid.population`;
  - secondaria e descrittiva, *accordo parziale*: ogni avversario riporta un sottoinsieme casuale.
- **Registro per prova, scritto prima dello scoring (V14):** n_avv, l'insieme dei fatti A2, |S_e ∩ Avv| per ogni fatto, N_d e il seed.
- **Baseline:** `ranked-score` (V3), `ranked-support-2` e `ranked-support-3`.

**H6-1a: unità = prova (tipo, estrazione), N_d fisso, 20 000 prove per punto, strategia di collusione totale.**

Tre componenti separate:
- **G (controllo del generatore, senza usare DIB).** Per ogni punto, X_gen = numero di prove con n_avv ≥ ⌈5N/12⌉. Si confronta con p* = `p_violate(N, q)`.
  - *Eccesso*, 25 test: c'è un difetto se il limite CP inferiore supera p*.
  - *Difetto*, 9 test, solo sui punti con potenza: c'è un difetto se il limite CP superiore è sotto p*.
- **D0 (test deterministico su DIB, fuori dalla famiglia statistica).** Nelle prove con n_avv < ⌈5N/12⌉ (Criterion 1 soddisfatto) DIB non deve ammettere **alcun** fatto A2. **Una sola ammissione falsifica H6-1a**, a qualsiasi punto (C7). Non ha errore di tipo I, perché è un controllo esatto, non una stima.
- **D1 (tasso complessivo di DIB contro p*).** X_dib = numero di prove con almeno un fatto A2 ammesso. *Falsificata se* il limite CP inferiore di X_dib/n supera p*. 25 test.
- **Descrittivo, senza test:** tasso di ammissione condizionato a n_avv ≥ ⌈5N/12⌉, con IC CP.
  - Con la collusione totale e ρ ≥ 100 è atteso vicino a 1 lontano dal margine, e minore di 1 vicino al margine (direzione "se", audit 11 punto 3).
  - Con l'accordo parziale è minore: **un DIB più conservativo del bound non è un difetto del generatore**. Il generatore si giudica solo con G, che non guarda DIB. D1 sotto p* è quindi atteso e non è un controllo del codice.

**Famiglia e livello:** **59 test unilaterali** (G-eccesso 25, G-difetto 9, D1 25), Bonferroni, α per test = 0,05/59 ≈ 8,5·10⁻⁴, limiti CP unilaterali al 99,915%, **uguali per tutti**. Errore complessivo ≤ 5%.
- Potenza di G-difetto (rilevare p*/2 con potenza 80%): n ≈ 55,8/p*, quindi con 20 000 prove p* ≥ 2,8·10⁻³. Sono i 9 punti (il successivo vale 1,6·10⁻³).
- Potenza di G-eccesso e D1 contro 0: n ≥ ln(1/α)/p* = 7,07/p*, quindi p* ≥ 3,5·10⁻⁴. Coprono 11 punti; per gli altri l'esito è "nessun fallimento in 20 000 prove" (C7).

**Esiti discordanti:**
- G fallisce (eccesso o difetto): il generatore non riproduce H1. **H6-1a è nulla** finché non è corretto, perché D0 e D1 dipendono dalla distribuzione di n_avv; si rilancia tutta la famiglia.
- D0 fallisce: DIB viola Criterion 1. È il risultato più forte; stop e report con file:riga su `code/src/dib/evaluation/dib.py` (nessuna correzione senza di te).
- D1 rifiuta con G e D0 superati: è **logicamente impossibile**. Con D0 superato, X_dib ≤ X_gen; il limite CP inferiore cresce con X, quindi se D1 rifiuta rifiuta anche G-eccesso. Se succede, è un errore dello script di analisi.
- D1 sotto p* (DIB più conservativo): non è un difetto (vedi sopra); si riporta il tasso condizionato.

**Durata stimata:** 500 000 prove × 1-10 ms ≈ 0,14-1,4 h in serie, da misurare su 1000 prove pilota.

**H6-1b: unità = replica di federazione, 170 punti (V11) × 200 repliche = 34 000 repliche, 3 baseline appaiate = 510 confronti.**
- Metrica: a budget pari alla coda DIB, quota di fatti A2 nel prefisso (baseline − DIB).
- **Punti testabili:** almeno 50 repliche su 200 con almeno un fatto A2 nella coda DIB o nel prefisso della baseline. Gli altri (atteso: q = 0,01 con N_d piccolo) sono "non testabili": si riportano in modo descrittivo, non entrano nella famiglia e non falsificano.
- **Test:** Wilcoxon dei ranghi con segno, unilaterale, sulle 200 differenze appaiate (H0: mediana della differenza ≤ 0). Il bootstrap (IC al 95%) serve solo per riportare l'effetto. Il bootstrap non basta per i p-value: con 510 test la soglia più piccola di Holm vale ≈ 10⁻⁴, alla scala della risoluzione di 10 000 ricampionamenti.
- **Molteplicità: Holm** sui test dei punti testabili (≤ 510), con FWER 5%.
  - Motivo: H6-1b è un'affermazione universale ("per ogni punto e per ogni baseline"); Holm controlla l'errore complessivo senza assumere l'indipendenza ed è uniformemente più potente di Bonferroni.
  - Una regola a quota richiederebbe una soglia arbitraria e sosterrebbe solo un'affermazione "nella maggior parte dei casi".
- **Falsificazione:** H6-1b è falsificata se Holm **non rifiuta** H0 per almeno una coppia (punto, baseline) testabile.
- **Esiti parziali**, riportati per fattore (baseline, ρ_corr, N, presenza, q):
  - *solo con ρ_corr > 0*: il vantaggio dell'ammissione vale con siti indipendenti ma non con siti correlati; l'affermazione del paper si restringe a quella condizione e il limite si dichiara;
  - *solo con `ranked-support-3`*: un filtro di supporto ≥ 3 toglie già gran parte dei fatti A2 a quei q; l'affermazione diventa "l'ammissione aggiunge protezione rispetto al ranking per score e al supporto ≥ 2, non rispetto a un ranking con supporto ≥ 3";
  - *solo con q alto*: il vantaggio esiste solo quando gli avversari sono abbastanza da superare i filtri deboli; si riporta la soglia di q.
- La regola (test, molteplicità, soglia di testabilità, lettura degli esiti parziali) è **scritta nel docstring prima del lancio e non cambia dopo**.
- **Durata stimata:** 0,2-2 s per replica, cioè 1,9-19 h in serie o 0,2-1,6 h con 12 processi; da confermare con 50 repliche pilota a N = 100. Oltre 8 h si propone di scendere a 100 repliche.

**H6-2:** con ρ_corr = 0,3, X_gen supera il valore binomiale p* (questa volta l'eccesso è atteso). Famiglia separata di 9 test unilaterali sui punti con potenza, con lo stesso α per test della famiglia H6-1a (8,5·10⁻⁴). *Falsificata se* il limite CP inferiore non supera p* in nessuno dei 9 punti.

**Cosa valida cosa (V4):** l'accordo di G con `fs_binomial.csv` a ρ_corr = 0 valida il codice, non il modello. I casi decisivi sono ρ_corr > 0 e il punto ancorato.

### Passo 7: M1/M2 ridotti (due bracci)
- Si riusa `m1_single_node/run.py` e `m2_p99_tail/run.py`, aggiungendo `--arm {default,deploy}`. `deploy` imposta solo `DIB_SQLITE_WAL=1` e `DIB_SQLITE_POOL_SIZE` ≥ writer (`code/src/dib/registry/db.py:244-262`). Nessuna modifica a `code/src`.
- Bracci mescolati. 10 ripetizioni, 20 a 100 writer. M2 solo sul braccio `deploy`. Niente M2b.
- Censura del timeout del pool riportata a parte (audit 04 §7.4).

### Regola G: disco e pulizia, a ogni passo
- All'inizio di ogni passo: `df -h /` sul nodo e su questo host (`/root/Desktop`). **Stop se < 2 GB liberi** sul filesystem usato dal passo. Il valore va nel manifest.
- Dopo ogni passo con Docker:
  - `docker compose -p dibtnsm down -v --remove-orphans`;
  - rimozione delle sole immagini con label `com.docker.compose.project=dibtnsm`, solo se il passo successivo non le riusa;
  - l'immagine base `python:3.12-slim@sha256:a6e3…` si tiene.

  **Mai `docker system prune` né `docker builder prune` globali.** Prima di ogni rimozione: `docker ps -a` e `docker image ls` filtrati per progetto, controllati a vista.

### Fuori dalla sequenza
- M5 (numero di siti): dopo M3, se la RAM del nodo lo permette.
- M8 (firma MUD): in qualsiasi momento.
- IoT-23: se avanza tempo.
- GothX, S3, S4, S5: fuori.

### Verifica, a ogni passo
- `cd code && /opt/conda/envs/dib312/bin/python -m pytest tests -q -p no:cacheprovider`: 448 passed, invariato.
- `python3 scripts/verify_artifact.py`: 260/2 fino a G0b, 262/0 dopo la copia autorizzata.
- Dry-run o prova pilota prima di ogni lancio completo. Il manifest contiene seed, `python -VV`, hardware, sha256 di `service.py`, dell'immagine e dei dati, disco, P, T, profilo, L_dns, latenza dei log, tipo di misura, host del generatore e timeout del client.
- Alla fine di ogni passo: riepilogo e l'audit corrispondente (15, 16, …).
