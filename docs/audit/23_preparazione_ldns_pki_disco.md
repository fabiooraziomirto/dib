# Audit 23 — Preparato, NON eseguito: misure di L_dns a `lan`, PKI, disco (2026-10-11)

Nulla di quanto segue è stato eseguito sul nodo. L'accesso al nodo lo gestisce l'utente caso per caso (permessi ssh negati dopo l'avvio di B1 a `lan`).

## 1. Stato che ritengo vero (riletto da audit 20 e 22)
- Driver corretto (`bf272e8`), tree `~/dib_tnsm/tree-bf272e8` con 18/18 hash verificati da me sul nodo alle ~07:50 UTC (cambia solo `run.py`, `022d97a6…`). Dati della notte = "primo run" (audit 21), non mescolati.
- B1 a `lan` (4 gruppi, 10 episodi per cella) avviato da me alle ~07:52 UTC con `nohup`; all'ultimo controllo 3 celle su 4 chiuse, 0 esclusi, nessuna segnalata; poi non ho più potuto leggere il nodo. **Non so se è finito, e non ho analizzato nulla.** Il file `b1.pid` non c'è (errore di redirezione mio). L_dns a `lan`: non misurato. Il mio messaggio precedente si ripeteva, ma lo stato era coerente.

## 2. L_dns a `lan` (tre misure, senza watcher né netem)
`calib_ldns.sh` da solo richiede il cluster già acceso (compose + project-dir + override), cioè più comandi. `calib_profile.py --profile lan` (uno dei 18 file hashati) fa in un solo comando: accende il cluster D, misura RTT, `calib_logs` (100 richieste), poi `calib_ldns.sh` (50 campioni con sito vivo e dopo `kill site-3`, 50 + 50) e spegne il cluster in un `finally`. Output `calib_ldns_lan.txt` con `alive` e `killed` (p50, p95, max, esiti). Comando esatto proposto, una volta per misura (N = 1, 2, 3, a distanza di qualche minuto l'una dall'altra), da autorizzare ogni volta:
```
ssh -i ~/.ssh/id_ed25519_lab ubuntu@192.168.100.57 'T=$HOME/dib_tnsm/tree-bf272e8; timeout 600 $HOME/dib_tnsm/venv/bin/python $T/experiments_tnsm/m67_retraction/calib_profile.py --tree $T --out $HOME/dib_tnsm/out/lan_20261011/ldns_N'
```
Condizioni: B1 finito, nessun container `dibtnsm`, nessun `netem_watch`. Se preferisci solo `calib_ldns.sh`, servono tre comandi per misura (up, script, down): dimmelo.

## 3. PKI (preparato, non eseguito)
Scadenza attuale: 2026-10-11 18:00:00 UTC (`ca.crt`, `admin.crt`, `op-site-1.crt`, `site-0.crt`). La PKI sta **fuori dal tree** (`~/dib_tnsm/pki`, `run.py:929` default `--pki`; `DIB_DIST_PKI_DIR` in `Env.compose`), la CA in `~/dib_tnsm/pki.ca` (`make_dist_pki.py:7-9`).
Comando proposto (dal tree, dopo aver spostato la PKI scaduta, senza cancellare; `--not-before` = ora UTC al momento del lancio; 48 h è una proposta, il default è 24 h):
```
cd ~/dib_tnsm/tree-bf272e8/code && mv ~/dib_tnsm/pki ~/dib_tnsm/pki_scaduta_20261011 && mv ~/dib_tnsm/pki.ca ~/dib_tnsm/pki_scaduta_20261011.ca \
 && ~/dib_tnsm/venv/bin/python scripts/make_dist_pki.py --out ~/dib_tnsm/pki --n-sites 10 --not-before "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --valid-hours 48 --extra-san-ip 192.168.100.57 \
 && sha256sum ~/dib_tnsm/pki/pki_manifest.json ~/dib_tnsm/pki/ca.crt
```
(SAN: `localhost` e `127.0.0.1` ci sono già, `make_dist_pki.py:102-104`; il generatore di M6/M7 è sul nodo, l'IP extra non serve a M6/M7 ma allinea la PKI a M3/M4, come da tua indicazione.)
**File del tree che cambierebbero: nessuno** (né `make_dist_pki.py` né i 18 hash: la PKI è fuori dal tree). Cambia il contenuto di `~/dib_tnsm/pki` (nuovi certificati, nuovo `pki_manifest.json`); propongo di registrarne lo sha256 in audit. Tu hai scritto che una nuova PKI richiede un nuovo tree: per quanto leggo io no, ma la decisione resta tua. Con la nuova PKI il braccio C va ricontrollato con una cella di fumo prima dei blocchi `wan`/`degraded`.

## 4. Disco (3,6 GB liberi, 97%): da misurare, nulla da cancellare
Dimensioni già note: ogni `tree-*` pinnato pesa ~21 MB (`du -sh tree-6b8a6fa`), i vecchi alberi sono 11 (`0610b73 06d4819 1d4e18b 3b61bd8 3c7e12f 62aaca8 65b0160 6af39a2 8345849 a7b53af b18fd1e`) ≈ 0,23 GB in tutto: **non bastano a liberare spazio significativo**, e `6b8a6fa`, `a7b53af`, `bf272e8` sono provenienza di dati già prodotti. Il grosso sta altrove (90 GB usati): serve la misura. Comando di sola lettura da autorizzare:
```
ssh -i ~/.ssh/id_ed25519_lab ubuntu@192.168.100.57 'du -sh ~/dib_tnsm/* 2>/dev/null | sort -h | tail -20; df -h /; PATH=/snap/bin:$PATH docker system df'
```
Candidati da valutare dopo la misura, **solo con il tuo OK e dopo una copia fuori dal nodo**: output pesanti di M1 e M2 della notte (`~/dib_tnsm/out/night_20261011/run/`), vecchi output M3/M4 già copiati in repo, immagini Docker vecchie (`docker image ls`, nessun `docker system prune`).
