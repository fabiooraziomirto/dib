# Audit 122 — Withdrawal end-to-end fino al gateway OpenWrt/osMUD: risultati

Data 2026-10-13. Pre-registrazione: audit 121 (commit `f949053`, prima del lancio). Dati: `experiments_tnsm/gateway_withdrawal_20261013/{lan,wan,degraded}_mtls/` (manifest, un `episode.json` per episodio, probe e poll compressi), analisi `analysis_{lan,wan,degraded,all}/` (`episodes.csv`, `summary.json`, `table.md`) con `analyze.py` sha `c7646add…`.

## Provenienza ed esecuzione
| Profilo | Periodo (UTC) | Episodi | Hash `service.py` negli 11 container (inizio, fine) | netem verificato | load average (inizio → fine) |
|---|---|---|---|---|---|
| LAN, mTLS | 08:52–10:08 | 100 std + 10 veto | `3ffa57ee…` / `3ffa57ee…` | nessuno | 12,1 → 7,3 |
| WAN, mTLS | 10:08–10:45 | 50 | idem | 80 ms 1 % su eth0 dell'evidence e sulla veth lato host | 7,5 → 9,1 |
| degraded, mTLS | 10:45–11:26 | 50 | idem | 200 ms 5 %, idem | 8,9 → 11,3 |
- Commit `f949053`, albero pulito al lancio di LAN. WAN e degraded registrano come file non tracciati solo dati e audit, nessun file di servizio.
- Router: entrypoint e script osMUD uguali all'albero (verificati all'inizio e alla fine). Stesso time namespace per host, router e device.
- **Tutti i 210 episodi sono `complete`**: 0 `op_failed`, 0 `setup_invalid`, 0 retry di setup, 0 dispute con status ≠ 200.
- Host condiviso con ~30 container di altri progetti (non toccati).
- Durante gli episodi LAN ~48–50 (09:27–09:29 UTC) ho eseguito la suite di test con `nice -n 19` (audit 126). In quegli episodi non c'è nessuna anomalia visibile: i massimi di LAN cadono altrove.

## Ipotesi
| Ipotesi | LAN (100) | WAN (50) | degraded (50) | Esito |
|---|---|---|---|---|
| H-G1: MUD dopo t1 solo controllo; soggetto bloccato dopo t2; t2 < 60 s | 100/100 | 50/50 | 50/50 | **regge** |
| H-G2: t1 ≤ t0r (fan-out sincrono), LAN | 100/100 | (50/50) | (50/50) | **regge** |
| H-G3: connessione stabilita al soggetto non interrotta fino a fine finestra (≥ 95 %) | 100/100 (finestra ≥ 21,0 s) | 50/50 (≥ 21,3 s) | 50/50 (≥ 22,0 s) | **regge**: nessuna interruzione in nessun episodio, nemmeno durante restore e recommit |
| H-G4: controllo in errore solo durante i reload, ok dopo t2; connessione stabilita del controllo mai interrotta | 0 errori fuori dai reload; 100/100 | 0; 50/50 | 0; 50/50 | **regge** |
| H-G5: restore da solo → soggetto bloccato; fresh commit → riabilitato | 100/100, 100/100 | 50/50, 50/50 | 50/50, 50/50 | **regge** |
| H-G5 veto (10): stato `revoked/local` dopo il restore, commit 409, export senza 8080, soggetto bloccato, poi local restore + commit riabilitano | 10/10 | — | — | **regge** |
| H-G6 LAN: mediana t1 < 0,2 s; mediana t2 in [4, 7] s; d_apply ≥ 80 % di t2; t3 < t2 ≥ 95 % | 0,024 s; 5,49 s; 99,4 %; 100 % | — | — | **regge** |
| H-G6 degraded: mediana t1 > 1 s, **perché** il fan-out fallisce e t1 arriva via reconcile | — | — | 1,020 s, ma t1 ≤ t0r in 50/50 | **soglia rispettata, meccanismo falsificato**: il fan-out è sempre arrivato dentro la chiamata `/dispute` (anche con nuovi tentativi), non tramite reconcile |
| H-G6 WAN: t1 fra LAN e degraded | — | 0,418 s | — | **regge** |

## Tempi (secondi da t0s = invio del dispute; mediana [IC 95 % da statistiche d'ordine], p95, max)
| Grandezza | LAN (n=100) | WAN (n=50) | degraded (n=50) |
|---|---|---|---|
| t0: evidence `disputed` (poll) | 0,016 [0,015, 0,017]; 0,026; 0,031 | 0,296; 0,513; 1,220 | 0,723; 1,989; 2,641 |
| risposta `/dispute` (t0r) | 0,031; 0,038; 0,074 | 0,506; 1,503; 1,605 | 2,426; 4,237; 4,480 |
| **t1: site-0 `disputed`** | **0,024 [0,023, 0,025]; 0,034; 0,068** | **0,418 [0,418, 0,419]; 0,479; 1,437** | **1,020 [1,019, 1,022]; 2,258; 2,504** |
| reazione del harness t1→export (orchestrazione) | 0,001; 0,002; 0,002 | 0,001; 0,002; 0,002 | 0,001; 0,002; 0,002 |
| export (generazione + scrittura) | 0,008; 0,010; 0,012 | 0,007; 0,008; 0,010 | 0,007; 0,009; 0,010 |
| comando di reload (docker exec) | 0,291; 0,326; 0,340 | 0,280; 0,308; 0,326 | 0,297; 0,329; 0,342 |
| reload → flush delle regole MUD | 0,363; 0,402; 0,469 | 0,352; 0,379; 0,396 | 0,371; 0,405; 0,424 |
| reload → t2 (applicazione nel gateway) | 5,460; 5,499; 5,565 | 5,451; 5,484; 5,555 | 5,470; 5,507; 5,530 |
| **t2: policy applicata** | **5,494 [5,489, 5,499]; 5,537 [5,528, 5,586]; 5,597** | **5,875 [5,868, 5,887]; 5,973; 6,914** | **6,504 [6,493, 6,527]; 7,727; 7,977** |
| **t3: nuove connessioni bloccate** | **0,382; 0,422; 0,461** | **0,766; 0,826; 1,815** | **1,398; 2,630; 2,865** |
| t3e: connessioni stabilite | mai interrotte (censurate a ≥ 21 s) | idem | idem |
| interruzione del controllo per reload | 5,076; 5,096; 5,175 | 5,075; 5,095; 5,098 | 5,076; 5,095; 5,099 |
| riabilitazione dopo fresh commit | 5,501; 5,535; 5,556 | 5,981; 7,137; 7,178 | 6,724; 8,552; 8,930 |

Risoluzione mediana delle osservazioni: t1 10 ms, t2 18 ms, t3 20 ms (periodo del probe). t0 a WAN/degraded ha risoluzione 0,17/0,41 s (poll attraverso il link emulato): in quei profili t0 è indicativo. Con n=50 l'IC del p95 arriva al massimo e non è riportato. Episodi veto LAN (10): t1 0,023 s, t2 5,499 s, t3 0,399 s (mediane).

## Lettura
- **Propagazione (t0→t1)**: è automatica e sincrona. In LAN 24 ms. Con il servizio condiviso remoto è dominata dal link: 0,42 s a WAN, 1,02 s a degraded, con code fino a 2,5 s per i nuovi tentativi.
- **Generazione/export**: ~8 ms. È orchestrata dal harness, perché l'architettura non prevede un push dal sito al gateway.
- **Applicazione**: ~5,46 s in ogni profilo. È quasi tutta dovuta al restart di osMUD, che legge l'evento DHCP con un timeout di 5 s (log di osMUD: "No data available within five seconds"). È indipendente da DIB e dalla rete.
- **Nuove connessioni bloccate prima di t2**: il restart svuota le regole MUD prima che osMUD le riapplichi, quindi le nuove connessioni al soggetto sono rifiutate da t0 + 0,38 s (LAN).
- **Costo collaterale del restart**: anche il flusso autorizzato estraneo al dispute è rifiutato per ~5,1 s a **ogni** reload (dispute, restore, recommit). È un costo del meccanismo di reload del prototipo, non della semantica di DIB.
- **Connessioni stabilite**: non vengono mai interrotte. fw4 accetta `ct state established,related` prima delle regole MUD e il percorso non svuota conntrack. Il ritiro vale per le **nuove** connessioni; un flusso aperto prima del dispute continua finché la connessione o la voce conntrack restano vive (default OpenWrt per TCP established: 7440 s). È un limite del gateway da dichiarare. Non è stato provato un rimedio (per esempio `conntrack -D`), che sarebbe un'estensione del percorso di enforcement.
- **Recovery**: le regole di DIB valgono sul gateway reale. Il restore da solo non riabilita; il fresh commit riabilita in ~5,5 s (LAN); il veto locale sopravvive al restore e blocca il commit (409).
- **Firma**: il MUD resta unsigned (osMUD `-i`). mTLS riguarda solo le chiamate fra i servizi DIB e il harness.

## Ambito
Un solo host (container Docker, OpenWrt in container privilegiato, non hardware fisico). Un device, un file MUD, due fatti TCP. Rete emulata solo sul link dell'evidence. Reload orchestrato dal harness. Il servizio misurato è `3ffa57ee…`, cioè prima della guardia di audit 126, che non cambia nessuna transizione valida. Lo smoke su `83d8c99a…` è in audit 127. Questi numeri non vanno confrontati con tempi misurati sul nodo KVM.

## Sostituisce
`results/openwrt/campaign-10runs` (10 run, registro **in-process**, senza tempi) come evidenza del percorso gateway nel paper; la campagna storica resta dov'è.
