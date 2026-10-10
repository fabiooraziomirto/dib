# Audit 20 — Nota di stato (da leggere in un minuto dopo una ripartenza)

Ultimo aggiornamento: 2026-10-10 (notte). Branch `revision-tnsm`, worktree `/root/Desktop/DIB_tnsm`. **Più sessioni scrivono su questo worktree**: `git add` solo con percorsi espliciti, `git status` prima di ogni commit, scrittura + `python -m py_compile` + commit concatenati con `&&`. Nessuna modifica a `code/src`, `service.py` (sha256 `3186304363ed…`), `results/` senza l'OK dell'utente; **nessun comando sudo** da questa sessione (netem, tcpdump li lancia l'utente a mano).

## Dove siamo

| Passo | Stato | Dove |
|---|---|---|
| 0-2 (M1 fermato, audit 14, G0b) | fatto, copiato in `results/` (262 → 266 controlli, `verify_artifact` verde) | audit 14, 15 |
| 6, 6a (sicurezza: H6-1a/b/c, H6-2, D0') | fatto | audit 16 |
| 3 (M3/M4 + diagnosi dell'anomalia) | **chiuso**: causa = contesto SSL httpx costruito a ogni chiamata nel braccio senza mTLS (6,15 ms); braccio D la rimuove; rilancio M4 C contro D fatto (H-M4a/b non falsificate: C/D 0,60 e 0,79; 50 e 100 writer esplorativi 0,60 e 0,54) | audit 18 §1.1-1.7.1 |
| Diagnostica CPU a 100 writer | **fatta, quadro misto**: generatore a ~1,1 core in tutte le celle, evidence 0,84-1,02, nodo ~20% | audit 18 §1.8 | `experiments_tnsm/m3_distributed/diag_cpu100_20261010/` |
| Calibrazioni a `lan` (log con due container, L_dns) | **fatte**: log p95 ~2-2,5 ms, scarto relativo ~0, L_dns 2,6 ms (errore di risoluzione); nessuna soglia dichiarata | audit 18 §1.9 | `experiments_tnsm/m67_retraction/calib_lan_20261010/` |
| Passi 4-5 (M6/M7, rete emulata) | **driver pronto, non integrato dal vivo**; trovato che il netem si perde a ogni ricreazione del cluster (risolto con grouping + `netem_watch.sh`, da decidere D1); attende il via dell'utente | `experiments_tnsm/m67_retraction/run.py`, audit 18 §2.4 |

## Decisioni dell'utente che valgono ora

- Braccio senza mTLS in M6/M7 = **D** (contesto SSL precostruito, lanciatore di B); braccio mTLS = **C**. Il "default come spedito" solo in poche celle di riferimento B1 a `lan`.
- Primo giro: **B1 e B2-kill**, profili `lan`, `wan`, `degraded` (`regional` ed `extreme` solo se avanza tempo). **B2-partition non è nel primo giro** (serve un helper con sudo, decisione dell'utente dopo il 16).
- Predizione (a) per `lan` ricongelata e committata (`6c11e48`): **non modificarla**. Predizioni (c) e (d) invariate finché la cattura `tcpdump` non dice altro.
- Soglie P-log per profilo: p95 della latenza dei log < 10% della mediana del ritiro diretto del profilo, altrimenti ripiego `dispute-rtt`; la soglia numerica si dichiara dopo la calibrazione di ciascun profilo e prima del lancio. Non dichiarare ancora né le soglie né la variante di B2 (dipendono da `wan` e `degraded`).
- Nessun numero di costo di mTLS nel paper se non il rapporto C/D, per questo prototipo (nessun pool fra servizi); non commentare la forma 0,60 → 0,79 → 0,60 → 0,54 oltre i dati (il generatore non era misurato).
- Il paper vecchio non si modifica; le correzioni sono proposte (audit 18 §1.5).

## Cosa aspetto dall'utente

1. **Decisione D1** (come tenere il netem fra le ricreazioni: watcher `netem_watch.sh`, raccomandato) e l'OK alla cella di fumo a `lan`; poi applica i profili con sudo (ordine dei blocchi `wan`, `lan`, `degraded`) e mi avvisa; lista esatta dei comandi con i `--dry-run` in audit 18 §2.4.
2. Conferma di B2-partition fuori dal primo giro (posizione già espressa) e, dopo il 16, la decisione sull'helper con sudo.
3. Il via ai lanci di B1/B2-kill dopo la calibrazione `wan` e `degraded` e le soglie committate.

## Come riprendere (comandi)

- Stato del nodo: `ssh -i ~/.ssh/id_ed25519_lab ubuntu@192.168.100.57 'docker ps -a | grep dibtnsm; df -h /'` (nessun container `dibtnsm` deve restare; ≥ 2 GB liberi).
- Alberi pinnati sul nodo: `~/dib_tnsm/tree-<commit>` (creati con `git archive` del commit); ogni misura registra gli hash nel manifest.
- Controllo di un processo: file con il PID (`/tmp/claude-0/pids/*.pid`) o `pgrep -f '[d]river'`: **mai** `pgrep -f` con un pattern che compare nella propria riga di comando.
- Test offline: `PYTHONDONTWRITEBYTECODE=1 /opt/conda/envs/dib312/bin/python -m pytest experiments_tnsm/common experiments_tnsm/m67_retraction -q -p no:cacheprovider`.
- Dry-run del driver: `python3 experiments_tnsm/m67_retraction/run.py --block b1,b2kill --profile wan --tree <albero> --out /tmp/x --dry-run`.

## Commit rilevanti (più recenti in basso)

`3186304`-hash di `service.py` congelato (G0) · `b29bade` G0b in `results/` · `4bb230c`/`19e2d9b` diagnosi A/B/C/D · `62aaca8`/`8fbe400` M4 rilancio · `6c11e48` predizione (a) · `7e75676` correzioni §1.7.1 · `c1cb846`/`afc415d` CPU a 100 writer · `a834834` driver M6/M7 · `3c7e12f` grouping, watcher, handshake tcpdump · `331c381` dry-run del watcher.
