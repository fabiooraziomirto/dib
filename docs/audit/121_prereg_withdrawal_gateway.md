# Audit 121 — Pre-registrazione: withdrawal end-to-end fino al gateway OpenWrt/osMUD (t0–t3)

Data 2026-10-13, prima della campagna. Harness: `experiments_tnsm/gateway_withdrawal_20261013/` (`gateway_bench.py`, `probe.py`, `echo_stream.py`, `analyze.py`). Servizio di riferimento: audit 119 (`service.py` `3ffa57ee…`).

## 1. Domanda
Dopo che il servizio condiviso accetta un dispute su un fatto Active, quanto tempo passa prima che (t1) l'autorizzazione locale del sito che applica la policy sia invalidata, (t2) il gateway applichi la policy aggiornata, (t3) la comunicazione prima consentita sia effettivamente bloccata — per connessioni nuove e per connessioni già stabilite? E il recovery rispetta le regole di DIB sul gateway reale (restore da solo non riabilita; serve un fresh local commit; il veto locale sopravvive al restore)?

## 2. Testbed (esistente, non riprogettato)
- Servizio distribuito: 1 evidence + 10 siti (`generate_compose.py`, N=10 come il compose canonico), immagini costruite dal Dockerfile dell'albero; **mTLS attivo** (`DIB_DIST_MTLS=1`, PKI di `code/scripts/make_dist_pki.py`, chiavi fuori dalla repo). Quorum di sospensione 1 (default), reconcile trigger T = 5 s, J = 0,5 s, fan-out concurrency 10 (valori del compose).
- Gateway: `openwrt/docker-compose.yml` invariato (OpenWrt 23.05.5 per digest, osMUD `852918e` compilato dal Dockerfile, `router-entrypoint.sh` invariato), veth come `openwrt/run_distributed.sh`.
- **Firma MUD**: il file MUD esportato è **unsigned**; osMUD gira con `-i` (bypass della validazione della firma, `openwrt/README.md`; il log di osMUD registra il fallimento di `openssl cms -verify`). mTLS protegge solo le chiamate tra servizi DIB e del harness verso i servizi; non c'è firma CMS integrata nel percorso del gateway (la firma CMS è misurata separatamente, `experiments_tnsm/m8_mud_sig`).
- Fatti: un device type `camera`, un file MUD. **Soggetto** `allowed.test tcp/8080` (disputato). **Controllo** `allowed.test tcp/9090` (mai disputato, stesso file MUD, stessa destinazione). Echo server persistente (`echo_stream.py`) nel container allowed-service.
- Sito che applica: site-0 (lab-a). Il dispute è riportato da site-1 (certificato operatore di site-1).

## 3. Cosa è automatico e cosa è orchestrato
| Passo | Chi lo fa |
|---|---|
| dispute → commit nell'evidence → fan-out a site-0 (t0 → t1) | **sistema** (fan-out sincrono, `service.py:1007-1009`; se fallisce: outbox + reconcile trigger) |
| site-0 → export MUD → file servito dal mud-server | **harness** (l'architettura non prevede un push dal sito al gateway): il harness reagisce all'osservazione di t1 |
| reload del gateway | **harness**: kill di osMUD + `router-entrypoint.sh` (come il prototipo; non esiste un reload nativo) |
| osMUD: fetch del MUD, regole uci, `fw4` | **gateway** (automatico dopo il restart) |
Quindi t2 − t1 contiene una componente di orchestrazione (`d_react`, `d_export`, `d_cmd`) riportata separatamente.

## 4. Osservazione dei timestamp
Un solo clock: `time.monotonic()` = CLOCK_MONOTONIC del kernel dell'host. Harness, poller e prober girano sull'host (il prober è lanciato con `nsenter -n` nel netns del device, con l'interprete dell'host); i container condividono il kernel e nessuno usa un time namespace (verificato a ogni campagna: `/proc/<pid>/ns/time` uguale per host, router, device). Nessuna sincronizzazione fra clock diversi è necessaria.

| Timestamp | Osservazione | Frequenza / risoluzione |
|---|---|---|
| t0s, t0r | invio e risposta di `POST /dispute` | esatti |
| t0 | poller `GET /scores` (admin) mostra `disputed` | ~6–7 ms fra poll (pilot); evento in (invio ultimo poll vecchio, ricezione primo poll nuovo] |
| t1 | poller `GET /state/{id}` di site-0 (operatore site-0) mostra `disputed` | idem |
| export, reload | timestamp del harness prima/dopo | esatti |
| tf | `nft list chain inet fw4 forward_lan` (via `nsenter -m -n` nel router) senza regole MUD accept | ~8–9 ms fra poll |
| t2 | stessa chain = regole accept del MUD esportato (solo 9090) | idem |
| t3 (nuove connessioni) | prober: nuova connessione TCP al soggetto ogni 20 ms (timeout 0,5 s) | 20 ms + durata del probe |
| t3e (connessioni stabilite) | prober: 1 connessione aperta prima del dispute, 1 byte di echo ogni 50 ms (timeout 1 s) | 50 ms |
La risoluzione effettiva di ogni osservazione è registrata per episodio (`res_*`).

Il **controllo** è sondato allo stesso modo (nuove e stabilita). Conntrack: il ruleset fw4 accetta `ct state established,related` prima delle regole MUD (`results/openwrt/single-run-distributed-driven/ruleset_final.txt:12`); il harness non tocca conntrack.

## 5. Episodio
Setup (non misurato; fino a 3 tentativi per richiesta su 5xx/errori di trasporto, poi 1 riparazione per episodio): soggetto e controllo Active a site-0, export con 8080+9090, reload, regole applicate. Misura: prober avviato; precondizione = 5 nuove connessioni consecutive riuscite su entrambe le porte e connessioni stabilite aperte; poller avviati; `POST /dispute` (nessun retry); attesa di t1 (max 90 s); export; reload; attesa di t2 (max 60 s); finestra di osservazione 15 s dopo t2. Recovery: (R1) `POST /restore` (admin) → stato site-0 → export → reload → 3 s di probe sul soggetto; (R2) fresh local commit → export → reload → tempo fino alla prima di 3 nuove connessioni riuscite. Episodi **veto**: dopo la finestra, local revoke a site-0, poi restore, tentativo di commit (atteso 409), export/reload/probe, poi local restore + commit.

## 6. Configurazioni e numerosità
| Configurazione | Episodi |
|---|---|
| LAN, mTLS, standard (principale) | **100** |
| LAN, mTLS, veto | 10 |
| WAN (80 ms, 1 % per direzione sul link dell'evidence), mTLS, standard | 50 |
| degraded (200 ms, 5 % per direzione sul link dell'evidence), mTLS, standard | 50 (30 se il pilot mostra > 120 s per episodio) |
Costo stimato dal pilot (LAN): ~40 s per episodio con finestra 15 s. N = 100 in LAN dà un IC al 95 % per il p95 fra le statistiche d'ordine ~89 e ~100; con 30–50 episodi il p95 è riportato ma con IC che arriva al massimo.
**netem**: profili esistenti (`experiments_tnsm/m67_retraction/profile_ctl.py:22`), applicati al solo link dell'evidence in entrambe le direzioni (eth0 nel container + veth lato host), così l'RTT evidence↔tutti = 2d come fra due container nelle campagne del nodo, mentre site-0, gateway e mud-server restano in LAN fra loro (il servizio condiviso è remoto, il sito e il suo gateway sono locali). Verifica con `tc qdisc show` registrata nel manifest. Profili applicati in blocchi separati, uno alla volta.

## 7. Ipotesi e criteri (prima dei dati della campagna; il pilot è esplorativo, sez. 9)
- **H-G1 (withdrawal effettivo, confermativa).** In ogni episodio misurato: il MUD esportato dopo t1 contiene solo 9090; tutte le nuove connessioni al soggetto dopo t2 fino a fine finestra falliscono; t2 osservato entro 60 s. Falsificata da un episodio che la viola o da un episodio `op_failed`.
- **H-G2 (propagazione sincrona, LAN).** t1 ≤ t0r (tenendo conto della risoluzione) in tutti gli episodi LAN. Previsione dal codice.
- **H-G3 (connessioni stabilite NON interrotte).** La connessione stabilita al soggetto continua a fare echo fino a fine finestra in ≥ 95 % degli episodi misurati di ogni profilo (pilot: 3/3). Falsificata altrimenti. Comunque vada: il ritiro vale per le nuove connessioni; i flussi esistenti restano finché conntrack non scade o non viene svuotato (limite del gateway, non di DIB).
- **H-G4 (interruzione transitoria del controllo).** Le nuove connessioni al controllo falliscono solo dentro gli intervalli di reload [inizio reload, t2 + 0,6 s] (0 fallimenti fuori, in totale) e riprendono dopo t2 in ogni episodio; la connessione stabilita al controllo non si interrompe. Previsione dal pilot: interruzione mediana ~5 s per reload (timeout di 5 s nella lettura dell'evento DHCP di osMUD).
- **H-G5 (recovery).** In ogni episodio misurato: dopo il solo restore il soggetto resta bloccato (0 connessioni riuscite in 3 s dopo t2 del reload) e l'export non contiene 8080; dopo il fresh commit il soggetto torna raggiungibile entro 60 s. Episodi veto: stato `revoked/local` dopo il restore, commit 409, export senza 8080, soggetto bloccato; local restore + commit lo riabilitano (10/10).
- **H-G6 (latenze, descrittiva con previsioni).** LAN: mediana di d_t1 < 0,2 s; mediana di d_t2 fra 4 e 7 s, con d_apply ≥ 80 % di d_t2; t3 < t2 in ≥ 95 % (le nuove connessioni sono bloccate dal flush del restart, prima che osMUD riapplichi). degraded: il fan-out con mTLS a 400 ms di RTT e timeout 1 s per tentativo dovrebbe fallire spesso → t1 via reconcile → mediana di d_t1 > 1 s. WAN: d_t1 fra LAN e degraded. Valori riportati comunque; le previsioni sono esplorative.

Statistiche: mediana e p95 con IC al 95 % non parametrico da statistiche d'ordine binomiali; per la mediana anche bootstrap percentile (10 000 ricampionamenti, seed 20261013). `analyze.py` è fissato con questo audit (sha nel commit).

## 8. Validità, esclusioni, retry
- Episodio **misurato**: stato `complete` oppure `op_failed` (dispute fallito, t1 o t2 non osservati entro il timeout). Gli `op_failed` sono fallimenti dell'operazione misurata: contano contro H-G1 e sono riportati, non esclusi.
- **setup_invalid** (setup o precondizione falliti dopo 1 riparazione): escluso dalle latenze, contato e riportato con la causa. 3 setup_invalid consecutivi fermano la campagna.
- Nessun retry di dispute, export, reload o probe misurati. Nessun episodio rieseguito per cambiare un esito.
- Provenienza: hash di `service.py`/`mtls.py` dentro gli 11 container all'inizio e alla fine (differenza = campagna invalida); hash di entrypoint e script osMUD nel router uguali all'albero; immagini registrate.
- Carico: load average registrato per episodio; l'host esegue ~30 container di altri progetti (non toccati). Nessun confronto con tempi misurati su altre macchine.

## 9. Pilot (esplorativo, non conteggiato)
Prima di questa pre-registrazione: pilot1 (bug di parsing delle porte nel harness: 0 episodi misurati), pilot2 (3 episodi LAN: 2 standard, 1 veto), pilot3 (1 episodio per profilo, harness definitivo). Dati in `experiments_tnsm/gateway_withdrawal_20261013/pilot_exploratory/`. Hanno guidato le previsioni di H-G3, H-G4, H-G6 e la numerosità; non entrano nelle stime.
