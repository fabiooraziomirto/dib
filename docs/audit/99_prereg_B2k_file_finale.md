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
