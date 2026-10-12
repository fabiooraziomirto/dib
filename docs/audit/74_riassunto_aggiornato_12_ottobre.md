# Audit 74 — Riassunto aggiornato (notte 11→12 ottobre): cosa cambia rispetto all'audit 59

Scritto per: l'autore e il supervisore. Data: 2026-10-12, ore 02:10Z. Branch `tnsm-driver-retry`. Tutto su un solo nodo (CPU QEMU generica, altri carichi di fondo). Nulla è stato scritto nel paper né in `results/`.

## Nuovi risultati misurati
| Voce | Esito | Audit |
|---|---|---|
| **B2k a `lan`, correzione driver + DNS corretto** (tree `3a45868`) | **120/120 prove utilizzabili**, (d-kill) non falsificata in 12/12 celle fino a **k = 50, entrambi i bracci**, mediana ≤ 1,7 s contro bound 7-8 s, 0 violazioni di (e). Sostituisce i blocchi `lan` di audit 57 per k = 10 e 50 | 73 |
| **Causa dei timeout a k ≥ 10 in B2k** | non erano di DIB né di mTLS né del keep-alive: il DNS del nodo (`search tail18eba5.ts.net proxmox`) rallentava a raffiche la risoluzione del nome del sito ucciso (2 000 risoluzioni: 401,5 s; con `dns_search: .`: 1,7 s) | 72 |
| **Controllo funzionale del keep-alive a `lan`** (opt-in) | H-L1..L4 non falsificate: 0 violazioni su 101 prove dopo riavvio di un sito, nessun costo di latenza (C: 23 ms contro 30 ms senza), 0 errori del warmer | 71 |
| **Modello del costo di consegna sotto perdita** | coerente con B5 secondo i criteri fissati prima (consegne in ritardo D 13,9 % contro 13,6 %; mediane a FANOUT 10 entro ±2 %); spiega perché (a′) falsificava (un tentativo fallito costa 1,0-1,8 s, la probabilità è per pacchetti). Struttura scelta dopo aver visto B5: non è una conferma indipendente | 62 |

## Modifiche al codice (branch `tnsm-driver-retry`, un commit per passo, suite `code/tests` 463 passati, `m67`+`common` 246)
1. `run.py`: riavvia site-3 dopo una prova esclusa (audit 60); opzioni spente di default `DIB_M67_KEEPALIVE` e `DIB_M67_DNS_NOSEARCH`.
2. `service.py`: **default** della concorrenza del fan-out `min(N_SITES, 16)` (era 1; la compose spediva 8: con 10 siti due siti aspettavano uno slot) e **opt-in** connessioni persistenti per sito con warmer (`DIB_DIST_FANOUT_KEEPALIVE`, default 0). `generate_compose.py` e `docker-compose.yml` allineati. Tree congelati sul nodo: `50c4335` (service + run) e `3a45868` (+ opzione DNS).

## Cosa NON è stato misurato e perché
**L'effetto del keep-alive sotto perdita (H-K1..K4, audit 62) non è misurato**: serve il watcher v2 (netem), scaduto alle 21:48Z (`timeout 9h`), e riavviarlo richiede sudo con password. La coda `auto_degraded_k.py` è **già in attesa** sul nodo e parte da sola al ritorno del watcher (non oltre le 07:00Z).

## Cosa fare tu, in una riga
Sul nodo, in tmux: `sudo timeout 9h bash /usr/local/lib/dib-netem/netem_watch2.sh --dir /home/ubuntu/dib_tnsm/m67 --owner ubuntu --poll 0.5 2>&1 | tee -ia ~/dib_tnsm/m67/watch2_stdout.log` (`-a` per non perdere lo storico). Entro 30 s la coda parte: B1 FANOUT 10 con keep-alive acceso, controllo spento nella stessa sessione, B2k con keep-alive (circa 3 h, `~/dib_tnsm/out/degraded_k2_20261012/`). Poi chiedimi l'analisi.

## Decisioni per il supervisore / per te
- Il default di concorrenza `min(N_SITES, 16)` va bene per il paper? (è il fattore dominante: ~6× a `degraded`).
- Le connessioni persistenti diventano default solo se H-K1..K4 reggono; oggi sono opt-in.
- Il modello di guasto dei test B2k è "sito ucciso con nome non risolvibile"; un sito "muto" (silenzio di rete) non è misurato.
- Q14 e Q2/Q4+Q5 dell'audit 59 restano aperte.

## Addendum (04:50Z): il modello di consegna è validato fuori campione; il resto resta com'è
- **Modello v4 validato** (audit 80-81): 6/6 condizioni nuove, consegne in ritardo entro 1,7 punti, 0 siti non aggiornati; è la sintesi di quattro iterazioni (v2 4/9 e 5/9, v3 2/4, v4 6/6) con criteri e previsioni sempre scritti prima dei dati (audit 75, 77, 78, 80). Limite: mediana e p95 a RTT alto sovrastimati; ipotesi dei due segmenti non verificata con una cattura.
- **Fan-out parallelo ≥ 3× più veloce del sequenziale** su 9 condizioni (audit 79); riconciliazione: 0 episodi incompleti su 3 280.
- **Connessioni persistenti: non proposte** (audit 76, due run falsificati). Il codice resta opt-in spento.
- **Invariato:** `degraded` sul nodo (watcher scaduto) non è misurato; la coda `auto_degraded_k.py` resta in attesa (fino alle 07:00Z) e misurerebbe un'opzione che il banco ha già falsificato: **conviene fermarla** (`kill $(cat ~/dib_tnsm/out/degraded_k2_20261012/auto_degraded_k.pid)`), e riavviare il watcher solo se si vuole misurare qualcos'altro sul nodo (per esempio B1 `degraded` con il default parallelo contro B5, per confermare sul nodo i risultati del banco).
