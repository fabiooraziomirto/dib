# Audit 99 — Pre-registrazione: B2-kill sul `service.py` finale (`tree-54521aa`) con l'applicatore netem in user space

Scritta e committata PRIMA del lancio (2026-10-12). Ipotesi, configurazione e regola di stop su L_dns: **invariate rispetto all'audit 45** (`docs/audit/45_prereg_B2k.md`, sez. 2-6); qui si dichiarano solo le differenze.

## Cosa cambia rispetto all'audit 45
- Codice: `tree-54521aa` (`service.py` sha256 `f7987d95…`, correzioni FSM + D1 + D2; `run.py` con D5 e manifest esteso). Orchestratore: `experiments_tnsm/node_session_20261011/deploy_b2k.sh` (commit c2aa142, non ancora provato sul nodo) invece di `auto_b2k.py`, perché il watcher root è scaduto.
- Netem: applicatore in user space con `--poll 0.1` (stessa soglia della regola L_dns; audit 85/86 per l'equivalenza con il watcher sul braccio D/10, che regge; non è dimostrata l'equivalenza per il kill/restart: **un sito riavviato riceve il netem entro 0,1 s dal polling, non dal watcher**: se questo cambia i numeri di (d-kill) lo si riporta come limite).
- DNS: `DIB_M67_DNS_NOSEARCH=1` (audit 72/73, già parte dei blocchi lan validi).
- Il driver controlla il setup (D5): prove con `/query` o `/commit` rifiutati sono escluse come `setup_failed` e contate per cella.

## Ipotesi (da audit 45, soglie invariate)
- **(d-kill):** convergenza dopo `start` ≈ 0,45 s + U(0; 0,1·T) + D_run, bound 1,5 s + 0,1·T + max(5 s, D_run_max). Falsificata se l'estremo inferiore dell'IC bootstrap 95 % della mediana di una cella supera il bound della cella.
- **(e) correttezza:** nessuna violazione di I1-I3 e nessuna regola disputata esportabile oltre il bound. Falsificata da una sola violazione.
- **T15 − T5:** descrittiva, nessun criterio.
- **(f) nuova, da D1:** negli `final_states` di ogni prova non compaiono righe `staging` o `committing` (D1 le ripulisce all'avvio del sito riavviato). Falsificata da una sola riga transitoria. (Il driver non ne produce: il kill avviene dopo il setup completato e controllato.)

## Regola L_dns (come audit 45 sez. 5)
Per ogni profilo: p95 della latenza del sito morto ≤ 50 ms con applicatore a poll 0,1 s ⇒ si esegue; altrimenti il profilo NON si esegue, si registra la decisione (`ldns_decision_<profilo>.txt`) e nessuna soglia cambia. Il tentativo di oggi conta come uno; un fallimento non si ritenta lo stesso giorno.

## Limiti dichiarati prima
Una macchina, 10 prove per cella (n = vincolo di tempo), nodo con CPU QEMU senza AVX2; il numero di mTLS non si ricava da questi dati (audit 45 sez. 6); `deploy_b2k.sh` non provato prima di questo blocco: un fallimento dell'orchestratore (non del servizio) si riporta come tale e non conta come falsificazione di (d-kill) o (e).
Esecuzione sul nodo dopo R1 (audit 97), un blocco alla volta. Risultati: audit 100.

## Addendum (2026-10-12, 16:50Z, prima del lancio): albero e verifica dell'immagine
Albero `tree-c898ea8` (`service.py` sha256 `3ffa57ee…`; `run.py` con `up -d --build` e `verify_service_image`, audit 104). **Precondizione H-G:** per ogni gruppo di run.py `b2kill` lo sha256 di `/app/service.py` dentro gli 11 container deve essere `3ffa57ee…` (il run si ferma con `ImageMismatch` altrimenti). Il resto della pre-registrazione (ipotesi (d-kill), (e), (f), T15 − T5 descrittiva, regola L_dns, limiti) è invariato. Ricordo che le correzioni di D1 sono nell'immagine solo da R1e in poi: (f) "nessuna riga `staging`/`committing` negli `final_states`" vale ora per la prima volta sul codice vero. R1e (audit 105) ha dato `setup_failed` = 0, quindi il setup di B2k (un sito, k fatti) usa lo stesso retry.

## Addendum 2 (2026-10-12, 17:50Z, prima dei dati della seconda serie): disegno a 30 prove per cella
Il vincolo di tempo della pre-registrazione (10 prove per cella, audit 45 sez. 4) lascia intervalli larghi e rende la differenza T15 − T5 (circa 0,5 s) indistinguibile dal rumore U(0; 0,1·T). Per decisione dell'utente (tutte le prove, di notte) si aggiunge una **seconda serie di 20 prove per cella**: stesso blocco `b2kill`, stessi profili (lan, degraded, wan), stesse celle (T ∈ {5, 15}, k come prima, bracci D e C), `--trials 20`, **seme 20261016** (la prima serie: 20261014), albero `tree-2a40fa4` (`service.py` sha256 `3ffa57ee…` identico; cambia solo `run.py`: parametro `--trials`, default 10 invariato, e nient'altro). Stessa precondizione H-G e stessa regola L_dns per ogni profilo.
- **Analisi:** le due serie sono unite per cella (profilo, braccio, k, T) concatenando le prove (`analyze_b2k.py`, `pool_cells`, test scritto prima): n = 10 + 20 = 30 per cella. La prima serie, analizzata da sola, resta valida e riportata.
- **Ipotesi e soglie invariate:** (d-kill), (e), (f) come nell'addendum precedente; T15 − T5 resta **descrittiva** (decisione Q9) con intervallo più stretto. Se per una cella le prove escluse portano n sotto 20, si riporta.
- **Limite:** le due serie sono eseguite a ore diverse sullo stesso nodo; non si assume che siano indipendenti da condizioni della macchina oltre ai semi.
- Dopo la seconda serie, in coda, **R1f** (replica di R1e, audit 104, stesse ipotesi) su `tree-2a40fa4`.
