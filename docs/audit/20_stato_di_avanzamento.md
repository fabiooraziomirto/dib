# Audit 20 — Nota di stato (da leggere in un minuto dopo una ripartenza)

Ultimo aggiornamento: 2026-10-11 mattina, dopo le correzioni del driver (audit 22; notte finita, rapporto in audit 21). Branch `revision-tnsm`, worktree `/root/Desktop/DIB_tnsm`. **Più sessioni scrivono su questo worktree**: `git add` solo con percorsi espliciti, `git status` prima di ogni commit, scrittura + `python -m py_compile` + commit concatenati con `&&`. Nessuna modifica a `code/src`, `service.py` (sha256 `3186304363ed…`), `results/` senza l'OK dell'utente; **nessun comando sudo** da questa sessione (netem, tcpdump li lancia l'utente a mano).

## Dove siamo

| Passo | Stato | Dove |
|---|---|---|
| 0-2 (M1 fermato, audit 14, G0b) | fatto, copiato in `results/` (262 → 266 controlli, `verify_artifact` verde) | audit 14, 15 |
| 6, 6a (sicurezza: H6-1a/b/c, H6-2, D0') | fatto | audit 16 |
| 3 (M3/M4 + diagnosi dell'anomalia) | **chiuso**: causa = contesto SSL httpx costruito a ogni chiamata nel braccio senza mTLS (6,15 ms); braccio D la rimuove; rilancio M4 C contro D fatto (H-M4a/b non falsificate: C/D 0,60 e 0,79; 50 e 100 writer esplorativi 0,60 e 0,54) | audit 18 §1.1-1.7.1 |
| Diagnostica CPU a 100 writer | **fatta, quadro misto**: generatore a ~1,1 core in tutte le celle, evidence 0,84-1,02, nodo ~20% | audit 18 §1.8 | `experiments_tnsm/m3_distributed/diag_cpu100_20261010/` |
| Calibrazioni a `lan` (log con due container, L_dns) | **fatte**: log p95 ~2-2,5 ms, scarto relativo ~0, L_dns 2,6 ms (errore di risoluzione); nessuna soglia dichiarata | audit 18 §1.9 | `experiments_tnsm/m67_retraction/calib_lan_20261010/` |
| Passi 4-5 (M6/M7, rete emulata) | **D1 approvata (watcher)**; script netem rinforzati e provati con test (8 test); B1 provato dal vivo a `lan` (3 e 2×20 episodi, nessun `client_timeout`); B2-kill non provato e non parte senza decisione su L_dns; trovato che il netem si perde a ogni ricreazione del cluster (risolto con grouping + `netem_watch.sh`, da decidere D1); script netem corretti (retry, pulizia rumorosa, pid nella firma, `--poll`), albero pinnato `tree-6b8a6fa`; percorso generatore→container (d, non 2d) reso esplicito: warm-up prima di t0, log a connessione persistente, `generator_path_ms`; conta del pending dal log (letture del generatore solo controllo incrociato); albero `06d4819`; attende la conferma degli hash di `06d4819` e il via per le sole calibrazioni di `wan`; prima di B1: un ultimo rifacimento del tree (code vuote a inizio episodio, `queues_not_empty_at_start`; osservabile di (c) per sito, `prediction_c_observable.md`) e nuova conferma degli hash | `experiments_tnsm/m67_retraction/run.py`, audit 18 §2.5 |

## AGGIORNAMENTO 2026-10-11 mattina: correzioni prima del rilancio (dettagli e hash in `docs/audit/22_correzioni_driver_e_stato_pre_rilancio.md`)

- **Fatto:** driver corretto (commit `bf272e8`): `keepalive_expiry` 2 s contro i 5 s di uvicorn (stesso valore in plain e mTLS), errori di trasporto esclusi per episodio con causa e tipo (`transport_error_setup/measured`), `episodes.jsonl` per episodio e record parziale di cella, `dispute_rtt_bias_s` = uscita sito + uscita evidence (160 ms a `wan`), lettura di (a) per FANOUT 1 nel docstring con la nota "letta dopo aver visto i dati della notte". Test: 52 passati in `experiments_tnsm` (7 nuovi). **Tree `~/dib_tnsm/tree-bf272e8`, 18/18 hash verificati da me sul nodo; cambia solo `run.py` (`022d97a6…`).**
- **Fatto:** tabella dei costi di B2-kill con L_dns = 186 ms (3,06 h; non eseguito); A2 grezza eseguita: 0,5609, non falsificata (audit 22 §4-5).
- **I dati della notte restano "primo run" (audit 21):** non mescolati con il rilancio; nessun episodio aggiunto alle celle ambigue. M1/M2 della notte (100 e 90 celle, girate con il watcher `wan` attivo, ~0,07 core di fondo) **non analizzati** finché i blocchi non sono chiusi.
- **B1 a `lan` finito 07:56:29 UTC (4/4 celle, 0 esclusi), copiato in locale con sha256 verificato e analizzato: `docs/audit/24_b1_lan_rilancio.md`** (commit dati `744e1ff`). (a) degenere a `lan`; P-a4: C−D 38,65 ms [22,85; 49,69], né falsificata né confermata; P-a1/P-a2 non valutabili. Preparati: PKI e disco (`docs/audit/23_*.md`); L_dns a `lan` ×3 fatto (08:03-08:14, `site-3`, p95 3,9/7,5/9,9 ms, vivo 0,3-0,6 ms; non spiega i 176-186 ms del fumo di `night.py` a `lan` né quelli di `wan`: audit 24); tabella dei costi 2,37 h con L a `lan`, 3,06 h con 186 ms a `wan`.
- **In attesa dell'utente:** (1) conferma degli hash di `tree-bf272e8` sul nodo, poi blocco `lan` (B1 a `lan` 4 gruppi, 10 episodi per cella; L_dns a `lan` tre volte senza watcher); (2) "wan attivo" dopo il riavvio del watcher, poi B1 `wan` dal tree finale; (3) `degraded` con l'utente per tcpdump; (4) decisione su B2-kill (L_dns p95 186 ms, zona intermedia, watcher a `--poll 0,1`); (5) **PKI del nodo scade oggi 18:00 UTC**: decidere se rigenerarla prima dei blocchi con il braccio C dopo quell'ora; (6) disco del nodo al 97% (3,6 GB liberi).

## NOTTE FINITA (avviata 2026-10-10 22:38:34 UTC, `DONE` 2026-10-11 02:50 UTC): vedi `docs/audit/21_rapporto_notte.md`

Esito in una riga: B1 `wan` completato solo per i due gruppi FANOUT 1 (D e C); i due FANOUT 10 sono caduti per `httpx.RemoteProtocolError` in `setup_fact` (connessione keep-alive stale, ipotesi); B2-kill non eseguito (L_dns p95 186 ms); M1 (100 celle) e M2 (90 celle) eseguiti, non analizzati. Sotto, il testo scritto all'avvio.

- Processo: `night.py` staccato sul nodo, PID `878739`, file `~/dib_tnsm/out/night_20261011/run/night.pid`; stato in `run/state.json`, uscita in `run/night.stdout`, un log per gruppo `run/b1_<arm>_f<fanout>.log`, dati in `run/b1_*/`. Si controlla con `kill -0 $(cat …/night.pid)`, `tail run/night.stdout` e `run/state.json`; a fine corsa compare `run/DONE`.
- Tree congelato `~/dib_tnsm/tree-6b8a6fa` (18 hash controllati dallo script all'avvio). Watcher `netem_watch.sh --poll 0.5 wan` in tmux (`timeout 9h`, parte 22:36 UTC, si ferma ~07:36), log `~/dib_tnsm/m67/watch_wan.log`; `netem_show.sh` verificato dall'utente (11 namespace, `delay 80ms loss 1%`).
- Eventi di profilo in `~/dib_tnsm/out/night_20261011/profile_events.jsonl` (il primo "applied" 22:34:36 era prematuro; watcher applicato 22:36:04,854).
- Calibrazione di prova prima della notte (`night_20261011/verify/`): `generator_path_ms` riusata 83,1 ms / nuova 164,0 ms (attesi ~80 / ~160, ipotesi del proxy confermata); L_dns del sito morto p50 179,8 ms, p95 185,2 ms (errore `Temporary failure in name resolution`, massimo 4,0 s). La regola esclude B2-kill (> 50 ms, e watcher a 0,5 s).
- Previsto: calibrazione `wan`, soglia, B1 (4 gruppi), smontaggio, M1/M2 solo se restano ≥ 3 h (cioè prima delle 04:00 UTC). Nessun intervento sul nodo, sul netem o sul watcher fino al rapporto del mattino (`docs/audit/21_rapporto_notte.md`).

## Decisioni dell'utente che valgono ora

- Braccio senza mTLS in M6/M7 = **D** (contesto SSL precostruito, lanciatore di B); braccio mTLS = **C**. Il "default come spedito" solo in poche celle di riferimento B1 a `lan`.
- Primo giro: **B1 e B2-kill**, profili `lan`, `wan`, `degraded` (`regional` ed `extreme` solo se avanza tempo). **B2-partition non è nel primo giro** (serve un helper con sudo, decisione dell'utente dopo il 16).
- Predizione (a) per `lan` ricongelata e committata (`6c11e48`): **non modificarla**. Predizioni (c) e (d) invariate finché la cattura `tcpdump` non dice altro.
- Soglie P-log per profilo: p95 della latenza dei log < 10% della mediana del ritiro diretto del profilo, altrimenti ripiego `dispute-rtt`; la soglia numerica si dichiara dopo la calibrazione di ciascun profilo e prima del lancio. Non dichiarare ancora né le soglie né la variante di B2 (dipendono da `wan` e `degraded`).
- Nessun numero di costo di mTLS nel paper se non il rapporto C/D, per questo prototipo (nessun pool fra servizi); non commentare la forma 0,60 → 0,79 → 0,60 → 0,54 oltre i dati (il generatore non era misurato).
- Il paper vecchio non si modifica; le correzioni sono proposte (audit 18 §1.5).

## Cosa aspetto dall'utente

1. Il "via" dell'utente: applica `sudo netem_watch.sh <profilo>` per un blocco alla volta (ordine `wan`, `lan`, `degraded`, seme 20261014) e mi avvisa; hash degli script, correzioni e anteprime in audit 18 §2.5 (albero `~/dib_tnsm/tree-6b8a6fa`; elenco comandi in §2.4 con le variazioni di §2.5: `--poll`, `tee -i`, due tcpdump).
2. Dopo la calibrazione di L_dns a `wan`/`degraded`: la sua decisione sulla variante di B2 (B2-kill non parte prima).
2. Conferma di B2-partition fuori dal primo giro (posizione già espressa) e, dopo il 16, la decisione sull'helper con sudo.
3. Il via ai lanci di B1/B2-kill dopo la calibrazione `wan` e `degraded` e le soglie committate.

## Come riprendere (comandi)

- Stato del nodo: `ssh -i ~/.ssh/id_ed25519_lab ubuntu@192.168.100.57 'docker ps -a | grep dibtnsm; df -h /'` (nessun container `dibtnsm` deve restare; ≥ 2 GB liberi).
- Alberi pinnati sul nodo: `~/dib_tnsm/tree-<commit>` (creati con `git archive` del commit); ogni misura registra gli hash nel manifest.
- Controllo di un processo: file con il PID (`/tmp/claude-0/pids/*.pid`) o `pgrep -f '[d]river'`: **mai** `pgrep -f` con un pattern che compare nella propria riga di comando.
- Test offline: `PYTHONDONTWRITEBYTECODE=1 /opt/conda/envs/dib312/bin/python -m pytest experiments_tnsm/common experiments_tnsm/m67_retraction -q -p no:cacheprovider`.
- Dry-run del driver: `python3 experiments_tnsm/m67_retraction/run.py --block b1,b2kill --profile wan --tree <albero> --out /tmp/x --dry-run`.

## Commit rilevanti (più recenti in basso)

`3186304`-hash di `service.py` congelato (G0) · `b29bade` G0b in `results/` · `4bb230c`/`19e2d9b` diagnosi A/B/C/D · `62aaca8`/`8fbe400` M4 rilancio · `6c11e48` predizione (a) · `7e75676` correzioni §1.7.1 · `c1cb846`/`afc415d` CPU a 100 writer · `a834834` driver M6/M7 · `3c7e12f` grouping, watcher, handshake tcpdump · `0610b73` script netem rinforzati + test · `f8c358a`/`e093063`/`9e8f2ac`/`54f7741` (verifica RTT dei due percorsi) · `06d4819` (conta del pending dal log, letture concorrenti) · `19ba814` (code vuote, osservabile di (c) per sito) · `a7b53af` (`night.py`, `launch_night.sh`) · `6b8a6fa` (launcher con argomenti extra; fumo di `run.py` e di `night.py` a `lan` riusciti) correzioni A1-A4, tolleranza RTT ±20%, `--dry-runs-only`, dry-run senza duplicati · `1d4e18b`/`6af39a2`/`65b0160` fumo a `lan`, `calib_profile.py`, `--hold`.
