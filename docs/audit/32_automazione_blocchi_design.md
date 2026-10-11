# Audit 32 — Automazione dei blocchi di rete: watcher v2, controllo profilo, orchestratore (FASE 1: costruito e testato, nulla installato né lanciato)

Data: 2026-10-11. Branch `revision-tnsm`, commit `e09b58a` (watcher v2), `4180ec6` (controllo profilo), `75a5da0` (orchestratore). Nessuna modifica a `code/src`, `service.py`, `results/`, `run.py`, `night.py` e agli altri 18 file congelati di `bf272e8` (hash verificati sotto). Nessun sudo, nessun ssh, nulla pubblicato sul nodo.

## 1. Cosa c'è e dove
| Componente | File | Test |
|---|---|---|
| Watcher v2 (gira come root, installato da te) | `experiments_tnsm/m67_retraction/netem_watch2.sh` | `test_netem_watch2.py` (48) |
| Controllo del profilo lato driver | `profile_ctl.py` | `test_profile_ctl.py` (14) |
| Orchestratore di blocco | `auto_block.py`, `launch_auto_block.sh` | `test_auto_block.py` (26), `test_launch_auto_block.py` (1) |
| Hash | `frozen_hashes_75a5da0.txt` (23 righe: i 18 di `bf272e8` invariati + 5 nuovi) | — |

`netem_watch2.sh` riusa **senza modifiche** `netem_common.sh` (guardia: label `dibtnsm` E nome fra gli 11, pid > 1) e `netem_apply.sh` (i comandi `tc` sono gli stessi); `netem_watch.sh` (v1) e `netem_show.sh` restano com'erano.

## 2. Watcher v2: protocollo e garanzie (`netem_watch2.sh`)
**Avvio (tuo, una volta)**, dopo aver confrontato gli hash e copiato `netem_watch2.sh` in `/usr/local/lib/dib-netem/` accanto agli altri tre:
`sudo timeout 9h bash /usr/local/lib/dib-netem/netem_watch2.sh --dir /home/ubuntu/dib_tnsm/m67 --owner ubuntu --poll 0.5 2>&1 | tee -i ~/dib_tnsm/m67/watch2_stdout.log` (in tmux). La cartella deve essere di `ubuntu` e **non scrivibile da gruppo/altri** (`stat -c %a` = 755 o 700), altrimenti il watcher rifiuta di partire. Le righe `netem_watch: containers changed -> applying X` / `applied X (n s)` hanno lo stesso formato di v1 (le legge `run.py parse_watch_log`).

**File nella cartella** (`netem_watch2.sh:3-33` descrive il protocollo):
- `profile.request` (scritto dal driver): UNA riga; massimo 128 byte; solo file regolare (symlink e ogni altro tipo rifiutati), proprietario = `--owner`, un solo hard link; confrontato per **uguaglianza esatta** con la lista chiusa `lan | regional | wan | degraded | restore | partition:site-N` (N una cifra 0..9, validato contro i nomi attesi), con suffisso opzionale `+fast`. Il contenuto non viene mai interpolato in un comando, né usato come percorso, né passato a `eval` (`netem_watch2.sh`, funzione `read_request`, poi `case` su valori letterali). Tutto il resto è rifiutato e registrato (contenuto riportato con `printf %q`, tronco a 64 caratteri, quindi mai byte di controllo grezzi nel log).
- `profile.applied` (scritto dal watcher): richiesta, `trigger` (`request`|`recreate`), ora UTC al millisecondo e `epoch_ms`, base, partizione, poll corrente, numero di container e, per **ogni** container, `== <nome> pid <pid>` seguito dall'output di `tc qdisc show dev eth0` (sola lettura).
- `watch2.log` (ogni richiesta accettata o rifiutata, con ora UTC), `watch2.heartbeat` (ogni ~2 s: pid, `epoch_ms`, stato `running`/`stopped`).
- `STOP` (creato dal driver o da te): il watcher ripulisce ed esce; se `STOP` esiste all'avvio, rifiuta di partire.

**Stato = (BASE, partizione).** `lan/regional/wan/degraded` impostano la base e annullano la partizione; `restore` riapplica la **base corrente** (non cancella netem salvo che la base sia `lan`); `partition:site-N` applica perdita 100% in uscita al solo sito N (`netem_apply.sh partition N`) mantenendo gli altri alla base. Sequenza interna: `netem_apply.sh <base>` poi, se serve, `netem_apply.sh partition N`; lo stato viene confermato solo se l'applicazione riesce (altrimenti ritenta a ogni poll, avviso su stderr al 1° e ogni 20° tentativo, nessun `profile.applied`).
**Ricreazione del cluster:** firma = ID, nome, pid come in v1; a ogni cambio riapplica lo stato corrente e riscrive `profile.applied` con `trigger: recreate`. **Finché non è stata accettata alcuna richiesta non applica nulla** (un cluster nuovo non ha qdisc). **Una richiesta senza cluster** è registrata e confermata con `containers: 0`; viene applicata alla comparsa del cluster.
**Poll:** 0,5 s (`--poll`), 0,1 s con `+fast` (`--fast-poll`); torna a 0,5 s alla richiesta successiva senza `+fast`; `profile.applied` riporta `poll_s`.
**Timeout e uscita:** lo script si ri-esegue sempre sotto `timeout --foreground --preserve-status` (`--max-seconds`, default 9 h; anche se lo avvolgi già tu). Su SIGINT/SIGTERM/HUP, scadenza o `STOP`: `netem_apply.sh lan` sui container validati; se fallisce, avviso `ATTENZIONE: pulizia netem NON riuscita, verifica con netem_show.sh` su stderr (e nel log) e uscita 1; senza container non c'è nulla da pulire (uscita 0; in v1 era un falso allarme). Un `profile.request` già presente all'avvio è ignorato (obsoleto) e registrato.
**File scritti da root in una cartella dell'utente:** `mktemp` (O_EXCL) + `mv -fT`, così un symlink messo dall'utente al nome finale viene sostituito, non seguito. Il log è tenuto in memoria e riscritto per intero (massimo 20 000 righe; lo stdout resta completo).
**Limiti dichiarati (non chiusi):** (1) l'utente proprietario della cartella può sostituire il contenuto di `profile.request` fra il controllo e la lettura: l'effetto è solo un confronto con la lista chiusa, ma una FIFO scambiata nell'intervallo blocca la lettura per al massimo 2 s (`timeout 2 head`); (2) un `profile.applied` sostituito da una directory impedisce la scrittura (avvisi, nessun danno); (3) lo script non usa `set -e` (un daemon non deve morire per un comando secondario): gli errori sono gestiti esplicitamente; (4) i test usano `tc`/`nsenter` finti: il **formato reale** di `tc qdisc show` per netem (`delay 200ms loss 5%`) è assunto come in `netem_show.sh`; la prima esecuzione supervisionata lo verifica.

## 3. `profile_ctl.py` (lato driver)
`ProfileCtl(dir).request(valore, timeout_s, allow_no_cluster)` scrive la richiesta in modo atomico (file temporaneo + `os.replace`, mai visibile a metà), dopo aver validato la lista chiusa e che il battito del watcher sia recente, e ritorna solo quando `profile.applied` mostra **la stessa richiesta**, scritta **non prima** dell'istante della richiesta (un record vecchio con la stessa stringa non vale), con **11 container su 11** e, per ognuno, un `tc qdisc show` coerente: `lan` nessun netem; `regional`/`wan`/`degraded` delay e loss del profilo (20 ms/0,1%, 80 ms/1%, 200 ms/5%); partizione = `loss 100%` senza delay sul sito e base sugli altri dieci. `restore` e `partition` richiedono una base nota (altrimenti errore). Errori espliciti: `ProfileTimeout`, `ProfileMismatch` (con nome del container, atteso e trovato), `WatcherDown` (nessun battito, `stopped`, o più vecchio di 15 s), `StaleApplied` (`read_applied(max_age_s)`: `profile.applied` più vecchio del valore dichiarato). Ogni errore allega la coda di `watch2.log`, dove il watcher scrive il motivo di un rifiuto.

## 4. Orchestratore `auto_block.py` (gira sul nodo, staccato, senza sudo)
Blocchi nell'ordine registrato: `lan_before` → `degraded` → `lan_after` (+ `wan`/`regional` solo se nominati con `--blocks`; B2-kill mai). Per blocco (dry-run con i comandi esatti: `auto_block.py --dry-run ...`):
0. **Controlli iniziali con stop**: nessun container `dibtnsm`; nessun processo `run.py` (scansione di `/proc`, non `pgrep -f`); `df /` > 2 GB; **ogni** certificato in `~/dib_tnsm/pki` valido almeno fino a `--end-utc` + 2 h (oggi la PKI scade il 2026-10-13 08:22:10Z: `--end-utc` ≤ 06:22Z del 13); sha256 di albero congelato, file nuovi e `service.py`; battito del watcher.
1. Richiesta del profilo (con `allow_no_cluster`: il cluster lo crea il passo 2). La conferma **11 su 11** arriva dal `ProfileMonitor`, che durante calibrazione e B1 registra ogni nuovo `profile.applied` in `profile_events.jsonl` e segnala un record con 11 container non coerente con lo stato atteso.
2. `calib_profile.py --profile P --profile-wait 90` (L_dns nella stessa invocazione, a ogni profilo).
3. Soglie P-log con `night.plog_thresholds` (regola meccanica del 10%, p95 da `make_plog_thresholds.p95_of`); file `plog_thresholds_P.json`, sha256 nello stato (evento `threshold_file`) **prima** di B1; `--commit-wait-min` (default 0) attende il flag `threshold_committed`.
4. B1: **una** invocazione di `run.py --block b1 --profile P --arms D,C --fanouts 1,10 --seed 20261014 --profile-wait 90 --plog-thresholds … --plog-p95-ms …` (episodi per cella dal driver: 50 a `degraded`, 10 a `lan`/`wan`, `run.py:153`). `--smoke`: `--episodes 3 --fanouts 10`.
5. Smontaggio del progetto, `DATA.sha256` (sha256 di ogni file tranne `*.pcap`), richiesta `lan` e verifica di `profile.applied`.
**Stop del blocco** (figlio terminato con SIGINT, poi SIGKILL dopo 120 s; smontaggio; `lan`; manifesto): battito del watcher assente/vecchio; `df` < 2 GB; certificato scaduto; `profile.applied` non coerente con lo stato atteso; RTT non conforme su 3 celle consecutive in `cells.jsonl`; timeout del figlio. **Un solo nuovo tentativo**, solo se il passo non ha prodotto dati (B1: nessuna cella non abortita; calibrazione: nessun risultato con `rtt_check_ok`), con la causa nello stato; mai dopo uno stop; **un passo che ha prodotto dati non si rilancia**. Errori su celle: `run.py` li registra e prosegue; l'orchestratore non cambia soglie, scarti o codice. Uscita 3 se un `lan` finale non è confermato (e `lan_not_confirmed` nello stato), altrimenti 0. A fine corsa: `REPORT_raw.md` (generato dallo stato, **non** un'analisi), `manifest.json` (ordine, seme, hash attesi, Python, host), `DONE`.

## 5. Verifica
- Test scritti **prima** del codice (watcher: tutti rossi senza lo script). Suite `experiments_tnsm/common` + `m67_retraction`: **162 passati** (89 nuovi), ~84 s, comprensiva dei test v1 invariati.
- Controllo di sensibilità dei test con mutazioni: watcher (controllo symlink rimosso, `restore`→`lan`, controlli hardlink/dimensione/proprietario rimossi: ogni mutazione fa fallire il test atteso; la prima mutazione **non** veniva rilevata perché le asserzioni cercavano parole presenti anche nel percorso temporaneo, e le ho rese precise); orchestratore (retry anche con dati, margine PKI, serie RTT, esclusione dei pcap: tutte rilevate).
- Nessun test tocca il sistema reale: `docker`/`nsenter` finti messi per primi nel `PATH` (con forma delle chiamate verificata: solo `ps --filter label=…dibtnsm`, `inspect -f … <nome atteso>`, `nsenter -t <pid> -n tc qdisc (show|replace|del) dev eth0`).

## 6. Hash (sha256, working tree = commit `75a5da0`)
I 18 di `bf272e8` sono **invariati** (audit 22 §3 = `git show bf272e8:` = working tree, verificato file per file). Nuovi:
| File | sha256 |
|---|---|
| `experiments_tnsm/m67_retraction/netem_watch2.sh` | `8010b14d2446c57bdd9dfea62e0384bb66326244bc7911b436c393f5f3c9a05e` |
| `experiments_tnsm/m67_retraction/profile_ctl.py` | `d3a245e6ebb16074895e1448878a5bb4d3fa85dab211744a67576eca1aae289c` |
| `experiments_tnsm/m67_retraction/auto_block.py` | `615d6ba346b86a02c2f0bbed59be3b6d654ddd8704c29774c2421063c20b087f` |
| `experiments_tnsm/m67_retraction/make_plog_thresholds.py` (già nel repo, importato dall'orchestratore) | `9a97cb5e465be7b2175f1534d910d5d1f846967fe3aa78959cf163d334974d97` |
| `experiments_tnsm/m67_retraction/launch_auto_block.sh` | `ad117a522449704a4491447b01a7455148f1cb0985693399efbfe8ddaf9f93b0` |
Test: `test_netem_watch2.py` `16ff413d…`, `test_profile_ctl.py` `f66cb38f…`, `test_auto_block.py` `464dc095…`, `test_launch_auto_block.py` `11e4952f…` (non servono sul nodo).
L'elenco completo, nel formato di `launch_auto_block.sh` / `sha256sum -c`, è `experiments_tnsm/m67_retraction/frozen_hashes_75a5da0.txt`.

## 7. Scelte mie da confermare o correggere
1. **L'orchestratore gira sul nodo** (come `night.py`), non sulla workstation: ore di blocco non devono dipendere dalla sessione ssh. Di conseguenza il passo "copia con sha256 sui due lati" non è nell'orchestratore: sul nodo scrive `DATA.sha256`; la copia (scp senza pcap + `sha256sum -c` in locale) la faccio io dopo, con il tuo OK all'ssh.
2. **Calibrazione e soglie anche nei blocchi `lan`**, come da testo ("ogni blocco"). Le sessioni `lan` precedenti (`lan_before` del 09:30) sono girate **senza** `--plog-thresholds` (manifest: `dispute-rtt`): i `lan` nuovi avrebbero una regola di misura diversa nel manifest. Se vuoi la stessa regola di prima, il blocco `lan` deve saltare passi 2-3; dimmelo prima della FASE 3.
3. **B1 in una sola invocazione**: se `run.py` abortisce un gruppo per RTT non conforme, interrompe l'invocazione (`run.py:813-817`) e i gruppi rimanenti non girano; se almeno un gruppo ha prodotto dati non si rilancia (regola tua), quindi i gruppi mancanti sono riportati come non eseguiti. Rilanciare solo i mancanti richiederebbe un'invocazione per gruppo (cambia l'ordine casuale registrato) o una modifica di `run.py`: non fatto.
4. `--commit-wait-min` default 0 (sul nodo non c'è git; senza la mia sessione che crea il flag, attendere sarebbe tempo perso). Con la sessione viva: lo passo a 10 e committo prima.
5. `--smoke` non è nella sequenza ma è la cella di fumo che chiedi (3 episodi, FANOUT 10, stesso percorso); `--blocks degraded --smoke` è il primo lancio supervisionato.
6. Battito vecchio > 15 s = watcher fermo; `profile.applied` non ha una scadenza (si riscrive solo a richiesta o ricreazione): la scadenza dichiarata vale per `read_applied(max_age_s)`, non per il monitor.
7. Il watcher non applica nulla prima della prima richiesta e ignora una richiesta presente all'avvio.

## 8. Resta fuori dall'automazione
- **Sudo e installazione**: confronto hash, copia in `/usr/local/lib/dib-netem/`, avvio del watcher v2 in tmux (e `STOP`/Ctrl-C a fine giornata); tcpdump.
- **Pubblicazione sul nodo** dell'albero `tree-75a5da0` (`git archive`) e di `frozen_hashes_75a5da0.txt`, con ogni ssh autorizzato da te.
- **Prima esecuzione supervisionata** (un blocco `degraded`, ~30 min, con te presente) e, prima, la cella di fumo (`--smoke`): FASE 3 non parte senza.
- **B2-kill** (decisione tua; richiederebbe `+fast`, L_dns nello stesso blocco ≤ 50 ms p95 e la sua cella di fumo) e B2-partition.
- Copia dei dati sulla workstation con sha256, analisi, commit, aggiornamento orario di `docs/audit/20_stato_di_avanzamento.md` e rapporto finale: li fa la sessione.
- Decisione sulla PKI (scade il 2026-10-13 08:22:10Z) se la sequenza supera quell'ora.
