# Audit 24 — B1 a `lan` (rilancio, tree `bf272e8`): risultati (2026-10-11)

Dati: `experiments_tnsm/m67_retraction/lan_20261011/b1/` (copia dal nodo con `scp`; sha256 di `cells.jsonl` `2b8de326d579a18578723bc9e54697ff2c1e3c0177eb9d238e8354e99730b98b` identico sui due lati; commit `744e1ff`). Run del 2026-10-11 07:51:49-07:56:29 UTC, `run.py` sha256 `022d97a6…`, seme 20261014, 4 gruppi (C f10, D f1, C f1, D f10), 10 episodi per cella, `aborted: false`. Analisi: `analyze_b1.py` (ipotesi dichiarate nel docstring e committate prima di eseguirlo), uscita completa in `lan_20261011/analysis_b1.md`. Mediane con IC bootstrap percentile al 95% **sugli episodi** (10000 ricampionamenti, seme 20261011): con n = 10 gli IC sono grossolani. Nessuna interpretazione oltre i dati. Questo è il rilancio, separato dal primo run della notte (audit 21).

Nota: il manifest registra `measure_rule: dispute-rtt (no P-log calibration applied)` (nessun file di soglie a `lan`, `--plog-p95-ms` non passato: il riepilogo usa il default 2,5 ms, `run.py:330`). A `lan` il bias di `dispute-rtt` è 0. Sotto, il tipo di misura è quello della regola per cella (P-log se p95/mediana < 10%); `dispute-rtt` è riportato accanto.

## Per cell

| arm | FANOUT | n | excl. | dispute-rtt ms | last-site P-log ms | gap rtt - P-log ms (med, max) | P-log ratio | measure | pending sites (log/read/undercount) | ack lines (tot/max) |
|---|---|---|---|---|---|---|---|---|---|---|
| C | 1 | 10 | 0  | 109.72 [101.75; 120.40] (n=10) | 105.96 [98.69; 117.54] (n=10) | 3.06, 4.70 | 0.024 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| C | 10 | 10 | 0  | 36.44 [35.23; 50.70] (n=10) | 30.61 [29.27; 43.71] (n=10) | 6.29, 8.62 | 0.082 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| D | 1 | 10 | 0  | 70.51 [64.64; 84.49] (n=10) | 67.31 [62.78; 82.06] (n=10) | 2.47, 4.08 | 0.037 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| D | 10 | 10 | 0  | 29.91 [28.21; 35.12] (n=10) | 25.91 [23.85; 30.32] (n=10) | 4.72, 6.04 | 0.096 (accepted) | P-log-apply | 0/0/0 | 0/0 |

## Exclusions by cause (all cells)

| arm | FANOUT | client_timeout | queues_not_empty_at_start | transport_error_setup | transport_error_measured | flagged by discard rule |
|---|---|---|---|---|---|---|
| C | 1 | 0 | 0 | 0 | 0 | False |
| C | 10 | 0 | 0 | 0 | 0 | False |
| D | 1 | 0 | 0 | 0 | 0 | False |
| D | 10 | 0 | 0 | 0 | 0 | False |

## Background and discard rule (other_cores > 1.0 or steal_pct > 2.0 flags a cell)

| arm | FANOUT | other_cores | steal_pct | flagged | generator proc cores mean/max | host busy % mean | near saturation |
|---|---|---|---|---|---|---|---|
| C | 1 | 0.2164 | 0.401 | False | 0.064/0.318 | 9.6 | False |
| C | 10 | 0.169 | 0.229 | False | 0.064/0.298 | 9.4 | False |
| D | 1 | 0.2739 | 0.313 | False | 0.047/0.150 | 8.9 | False |
| D | 10 | 0.1482 | 0.359 | False | 0.049/0.160 | 9.3 | False |

## generator_path_ms (reused / fresh, ms) and flags

| arm | FANOUT | reused | fresh | reused_ok | fresh_ok | generator_path_flag |
|---|---|---|---|---|---|---|
| C | 1 | 2.37 | 5.63 | True | None | False |
| C | 10 | 2.29 | 5.58 | True | None | False |
| D | 1 | 1.57 | 6.31 | True | False | True |
| D | 10 | 1.66 | 4.25 | True | False | True |

(at `lan` d = 0: the +-20% band is replaced by 0-3 ms; `fresh_ok` False/None carries no meaning here, audit 22.)

## Prediction (a) at `lan` (rule: falsified if median > n_RTT*R*(10 if FANOUT 1) + 3 x median `lan` of the same arm, beyond the CI)

| arm | FANOUT | measure | median ms [CI] | n_RTT*R*(x10) ms | 3 x lan median ms (same arm, same FANOUT) | threshold ms | CI lower > threshold? |
|---|---|---|---|---|---|---|---|
| C | 1 | P-log-apply | 105.96 [98.69; 117.54] (n=10) | 3.00 | 317.88 | 320.88 | False |
| C | 10 | P-log-apply | 30.61 [29.27; 43.71] (n=10) | 0.30 | 91.83 | 92.13 | False |
| D | 1 | P-log-apply | 67.31 [62.78; 82.06] (n=10) | 2.00 | 201.92 | 203.92 | False |
| D | 10 | P-log-apply | 25.91 [23.85; 30.32] (n=10) | 0.20 | 77.72 | 77.92 | False |

**Degenerate at `lan`**: the reference is the cell itself, so the threshold always exceeds the median; the verdict is False by construction and carries no information. Lan medians for both FANOUT values of each arm are in the table above, so the wan rule can be evaluated with either reading of 'same arm' (same FANOUT, or any FANOUT): the choice is open and must be declared before the wan block is analysed.

## Differences between arms (median difference, bootstrap CI over episodes)

- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), last-site P-log: C - D = 38.65 ms [22.85; 49.69] -> CI NOT inside [15, 32]: CI straddles a bound: not falsified, not confirmed
- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), dispute-rtt: C - D = 39.21 ms [22.81; 50.03]
- FANOUT 10 (no registered interval; descriptive), last-site P-log: C - D = 4.70 ms [0.02; 15.52]
- FANOUT 10 (no registered interval; descriptive), dispute-rtt: C - D = 6.53 ms [1.64; 18.55]
- default - D (P-a1 +61.5 ms at FANOUT 1; P-a2 between +6 and +62 ms at FANOUT 10): **not evaluable**, no `default` cells in this run.

## Lettura (solo dati)
- **0 esclusioni** in tutte le celle, per ogni causa; nessuna cella segnalata dalla regola di scarto (`other_cores` 0,15-0,27 contro soglia 1,0; `steal_pct` 0,23-0,40 contro 2,0); nessuna consegna in pending, 0 righe di ack, `read_undercount_sites` 0.
- **P-log accettato in tutte e 4 le celle**; D FANOUT 10 è al limite (0,096 contro 0,10).
- `generator_path_flag` vero per il braccio D (fresh 4,3-6,3 ms contro banda 0-3 ms, `fresh_ok` False): flag informativo senza significato a `lan` (audit 22); la connessione riusata è 1,6-2,4 ms in tutte le celle.
- **(a) a `lan` è degenere**: il riferimento è la cella stessa, la soglia (n_RTT·R·k + 3 × mediana) supera sempre la mediana; l'esito "non falsificata" vale per costruzione e non dice nulla, né sul CPU né sul setup. Non è stata tarata. Le mediane `lan` per entrambi i FANOUT di ogni braccio sono in tabella: per valutare `wan` va dichiarato prima se "stesso braccio" significa anche stesso FANOUT (lettura più naturale, non scritta).
- **P-a4 (C − D, ultimo sito, FANOUT 1, +23,5 ms; falsificata se l'IC è fuori da [15, 32])**: C − D = **38,65 ms** [22,85; 49,69]. La stima puntuale è oltre l'estremo superiore 32, l'IC lo attraversa e contiene 23,5: **né falsificata (IC non interamente fuori) né confermata**; letta come "stima puntuale fuori dall'intervallo" sarebbe fuori. Il braccio C è oltre D di più di quanto previsto in stima puntuale. Non spiego.
- C − D a FANOUT 10 (nessun intervallo registrato): 4,70 ms [0,02; 15,52] (ultimo sito), 6,53 ms [1,64; 18,55] (`dispute-rtt`).
- **P-a1 (default − D, +61,5 ms) e P-a2 (FANOUT 10, +6…+62 ms): non valutabili**, nessuna cella `default` in questo run.

## L_dns a `lan`, tre misure, senza watcher né netem (2026-10-11)
Comando: `calib_profile.py --tree ~/dib_tnsm/tree-bf272e8 --profile lan` (script hashato `f045d0fd…`, esso lancia `calib_ldns.sh` `0191b1fa…`, uguale alla notte), un comando per volta, intervallo ~5 min. **Sito ucciso: `site-3`** (`calib_ldns.sh`: `kill site-3`, sonda `getaddrinfo("site-3", 8000)` dal container evidence), lo stesso della notte. Cluster D. Nessun container né watcher prima di ciascuna. Dati: `experiments_tnsm/m67_retraction/lan_20261011/ldns_{1,2,3}/calib_ldns_lan.txt`.

| Misura | Ora UTC (inizio-fine) | Controllo sito vivo p50 / p95 / max (ms) | Sito morto p50 / p95 / max (ms) | Errore |
|---|---|---|---|---|
| 1 | 08:03:00-08:03:36 | 0,208 / 0,296 / 2,90 | 3,08 / 3,87 / 6,09 | `gaierror(-3, 'Temporary failure in name resolution')` |
| 2 | 08:08:20-08:08:59 | 0,283 / 0,491 / 2,31 | 3,71 / 7,53 / 26,9 | idem |
| 3 | 08:13:57-08:14:35 | 0,318 / 0,594 / 2,87 | 4,24 / 9,87 / 13,7 | idem |

Per confronto (da audit 18:708 e 21 §5, stessi script): `lan` 2026-10-10 23:11: 2,6 ms; **`lan` fumo di `night.py` (sera 2026-10-10): p50 176 / p95 186 / max 5,3 s**; `wan` (prova e notte): p50 179,8 / p95 185,2-186,0 / max 4,0 s, controllo vivo p50 0,27 ms.
**Conclusione, solo dai dati:** a `lan` senza netem oggi 3 misure su 3 danno p95 di 3,9-9,9 ms, quindi lontane dai ~180 ms di `wan`; **ma** un'altra misura etichettata `lan` (fumo di `night.py`) aveva dato 176/186 ms. Perciò **non posso dichiarare i ~180 ms né una proprietà dell'ambiente né una dipendenza dal profilo**: dipende da cosa era attivo durante quel fumo (netem/watcher `wan`?), che nei file che ho letto non è registrato. Lo sai tu; senza quel dato la dichiarazione "proprietà dell'ambiente" non è sostenuta (il caso 176 ms a `lan` oggi non si riproduce). Nota solo descrittiva: il p95 del sito morto sale 3,9 → 7,5 → 9,9 ms nelle tre misure consecutive.

### Tabella dei costi di B2-kill con L_dns (modello di audit 22 §4, non eseguito)
Con il valore di `lan` (p95 massimo 9,9 ms): episodio 0,59 s a `lan`, 1,70 s a `wan`, 8,75 s a `degraded`; totale 2,37 h (2,36 h con 2,6 ms). Con 186 ms (misurato a `wan`, unico valore sotto netem): 3,06 h (audit 22 §4). **Il valore da usare per `wan` è quello misurato a `wan` (186 ms)**; a `degraded` L_dns non è stato misurato (a `degraded` l'episodio resta 8,75 s per ogni L ≤ 0,92 s). Riga "lento" a `degraded` (11,0 contro 9,5 s): non rientra nei calcoli. La decisione su B2-kill (zona intermedia 50 ms-0,5 s a `wan`, watcher a `--poll 0,1`) resta tua.
