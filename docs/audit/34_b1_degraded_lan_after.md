# Audit 34 — B1 `degraded` e `lan` dopo (blocco reale 2026-10-11 13:17-14:43 UTC): esiti di (a) e (c), senza altre interpretazioni

`<blk>` = `experiments_tnsm/m67_retraction/block_degraded_lan_after_20261011`. Tree `244f1d0` (`run.py` sha256 `022d97a6dc76…`), watcher `d1c8f392…`, seed 20261014, una invocazione di `auto_block.py --blocks degraded,lan_after` (pid 3057429; cartella del nodo `~/dib_tnsm/out/block_degraded_lan_after_20261011`). Dati copiati con `copy_block.py` (sha256 sui due lati, 22 e 17 file, nessun pcap: `<blk>/degraded/COPY_VERIFIED.json`, `<blk>/lan_after/COPY_VERIFIED.json`) e committati prima dell'analisi (`c087f70`). Analisi: `<blk>/analysis_degraded.md`, `<blk>/analysis_lan_after.md`, `<blk>/analysis_c_degraded.md` (uscite integrali degli script, mai ritrascritte).

## 1. Esecuzione e pre-registrazione
- Eventi di `state.json` (letti dal nodo il 14:43:22): `degraded` 13:17:07 → 14:39:15 (calibrazione 13:17:07-13:19:19; `C_f10` →13:37:43; `D_f1` →13:56:42; `C_f1` →14:26:39; `D_f10` →14:39:15); `lan_after` 14:39:16 → 14:43:20 (C_f10, D_f1, C_f1, D_f10). Otto gruppi: `returncode 0`, `data_cells 1`, `aborted []`, `stop None`; `lan_confirmed` per entrambi i blocchi; `done`; nessuna riga `transient` in `profile_events.jsonl` (verificato con `grep -c`, `<blk>/degraded/profile_events.jsonl`, `<blk>/lan_after/profile_events.jsonl` non riletto per questo conteggio nel nodo).
- **Soglie P-log (pre-registrazione):** `plog_thresholds_degraded.json` sha256 `8f1bb7bc47c649f7efd0c9b309485d7a8a4f18b5fe6b28958c9e2d2d009e7fef`, registrato in `state.json` (evento `threshold_file`, 13:19:19.864180) **prima** di `b1_start` (13:19:19.865054); lo stesso hash sul nodo (`sha256sum`), nella copia in scratchpad e nella copia in repo (`<blk>/degraded/plog_thresholds_degraded.json`). Soglie D/1 800, D/10 80, C/1 1200, C/10 120 ms, tutte accettate; p95 della calibrazione 1,93 ms.
- **Processi di controllo (sola lettura, ognuno autorizzato):** un solo watcher v2 (catena 2916544…2916556) per tutta la corsa; nessun v1.

## 2. (a) — risultato con il riferimento `lan` adiacente (`<blk>/analysis_degraded.md:64-71`)
Riferimento: mediana più alta fra `lan_before` e `lan_after`, stesso braccio e stesso FANOUT; FANOUT 1: 10 × n_RTT × R più servizio; regola R-gp (`reused_ok` falso ⇒ "not evaluable"): `reused_ok` vero in tutte e 4 le celle (`:57-60`), quindi tutte valutabili.

| cella | mediana P-log-apply ms [IC bootstrap] (n) | predetto ms | riferimento `lan` ms | soglia ms | eccesso ms | esito |
|---|---|---|---|---|---|---|
| C/1 | 17022,36 [15615,42; 19323,99] (31) | 12000 | 80,04 (`lan_after`) | 12240,1 | 4782,3 | **falsified** |
| C/10 | 2824,58 [2422,25; 3418,70] (35) | 1200 | 22,46 (`lan_before`) | 1267,4 | 1557,2 | **falsified** |
| D/1 | 10669,83 [9769,59; 11177,69] (41) | 8000 | 48,76 (`lan_after`) | 8146,3 | 2523,5 | **falsified** |
| D/10 | 2016,77 [1621,25; 2019,21] (46) | 800 | 20,71 (`lan_before`) | 862,1 | 1154,6 | **falsified** |

- Tipo di misura: P-log-apply in tutte e 4 le celle; P-log accettato (rapporto 0,000-0,001, soglia 10%) in tutte e 4 (`:10-13`). L'n della misura P-log è il numero di episodi non esclusi **senza** consegne in pending (es. C/1: 48 validi − 17 con pending = 31, `<blk>/degraded/b1_C_f1/cells.jsonl`, `summary.n_direct`, `n_pending_episodes`).
- Mediane di dispute-rtt (n validi): C/1 19574,41 (48), C/10 4327,94 (48), D/1 11468,47 (47), D/10 2829,26 (49) (`:10-13`).
- Differenze C−D, solo descrittive (`:73-78`): FANOUT 1 last-site P-log 6352,54 [4856,69; 8852,73] ms, dispute-rtt 8105,93 [5762,65; 9097,56]; FANOUT 10 last-site P-log 807,81 [406,13; 1402,90], dispute-rtt 1498,67 [902,86; 2163,20]. P-a4 è registrato solo per `lan`; il braccio `default` non è nel blocco (P-a1/P-a2 "not evaluable").
- Non commento la forma dei valori né spiego l'eccesso.

## 3. Esclusioni e stato dell'ambiente (`<blk>/analysis_degraded.md:10-51`)
- Esclusi (causa): C/1 2 (`transport_error_setup`: episodi 9 e 25, righe senza `t0`), C/10 2 (`transport_error_setup`), D/1 3 (1 `client_timeout`, 2 `transport_error_setup`), D/10 1 (`transport_error_setup`). `transport_error_measured` 0, `queues_not_empty_at_start` 0, "flagged by discard rule" falso ovunque. Non rilanciati né sostituiti. Non ho letto i testi delle eccezioni (`exception`, `excluded_reason`): non analizzati qui.
- **Esclusione per sovrapposizione con profilo non assestato: 0 episodi per cella**; 13 intervalli del watcher letti da `watch2.log` che toccano l'intervallo del blocco (`:24-42`), tutti fra un gruppo e il successivo. Controllo diretto con `awk` su `watch2.log` copiato in tempo reale (nodo, sola lettura): 0 righe fra primo t0 e fine ultimo episodio per `C_f10` (13:20:24,353 → 13:37:15,245), `D_f1` (13:38:34,756 → 13:56:26,118, episodi con `t0`) e `C_f1` (13:57:50,275 → 14:26:12,803). `D_f10` non ricontrollato con `awk`: vale solo l'uscita di `analyze_b1.py` (0 sovrapposizioni).
- `other_cores` 0,1624-0,1741, `steal_pct` 0,010-0,026, nessuna cella segnalata, nessuna "near saturation" (`:48-51`).
- `generator_path_ms` riusata 202,93-203,66 ms (`reused_ok` vero, flag falso ovunque); fresca 607,57 e 607,81 (C, `fresh_ok` None) e 404,32 e 403,78 (D, `fresh_ok` vero) (`:57-60`). Non spiegato il 607 di C.
- `watch2.log` (191 righe, sha256 `8b9fd291517b8ee498b933def05c7e3c85637dae1c0c9dd559183a0ec8a7d212`, `<blk>/watch2.log`): 22 righe `applied degraded (… s)` fra 0,022 e 1,41 s (la distribuzione completa non analizzata); polling configurato `--poll 0.5` (`watch2.heartbeat`); **polling effettivo non misurato**.
- **Battito osservato una volta a 3,3 s** (14:42:14,153 contro 14:42:17,502 del nodo; sotto la soglia di 10 s; nelle altre letture 0,4-1,6 s). Non spiegato.

## 4. Tempo per sito (`withdrawn_plog_s`, siti degli episodi non esclusi; `<blk>/degraded/b1_*/cells.jsonl`, `rows[].withdrawn_plog_s`)
| cella | siti con valore | siti `None` | min / mediana / p95 / max (s) |
|---|---|---|---|
| C/1 | 472 | 8 | 1,012 / 9,866 / 20,383 / 29,964 |
| C/10 | 474 | 6 | 1,013 / 1,021 / 3,131 / 4,634 |
| D/1 | 467 | 3 | 0,609 / 5,734 / 11,916 / 17,784 |
| D/10 | 490 | 0 | 0,611 / 0,617 / 2,019 / 3,421 |
A `lan_after` (100 siti per cella, nessun `None`): mediana 45,8 (C/1), 18,8 (C/10), 29,0 (D/1), 16,4 (D/10) ms. I siti `None` non sono analizzati né spiegati.

## 5. Consegne in pending (`summary` di ogni cella)
| cella | episodi con pending | siti con pending (log / lettura / undercount) | righe di ack (tot / max per sito-episodio) | non misurati / non drenati |
|---|---|---|---|---|
| C/1 | 17 | 18 / 7 / 11 | 18 / 1 | 0 / 0 |
| C/10 | 13 | 14 / 14 / 0 | 14 / 1 | 0 / 0 |
| D/1 | 6 | 6 / 2 / 4 | 6 / 1 | 0 / 0 |
| D/10 | 3 | 3 / 3 / 0 | 3 / 1 | 0 / 0 |
`lan_after`: 0 episodi con pending in tutte e 4 le celle. `plog_rtt_agree` (±3 ms) falso in tutte e 4 le celle a `degraded`; bias di pending 0,013-0,028, mai oltre il 10%.

## 6. L_dns a `degraded` (calibrazione 13:19:19, `<blk>/degraded/calib/calib_ldns_degraded.txt`)
Sito morto: n 50, p50 3,08, p95 3,29, max 5,92 ms (`gaierror(-3, 'Temporary failure in name resolution')`); sito vivo: p50 0,21, p95 0,43, max 1,92 ms.

## 7. (c) — consegne in pending (intervalli registrati invariati: D [0,004; 0,015], C [0,025; 0,08]); B1 = test confermativo (`<blk>/analysis_c_degraded.md:5-10`)
| braccio | pending / consegne | quota | IC Clopper-Pearson 95% | per FANOUT | classificazione |
|---|---|---|---|---|---|
| D | 9 / 960 | 0,00937 | [0,00430; 0,01772] | f1 6/470, f10 3/490 | "CI crosses a bound: inconclusive" (supera 0,015) |
| C | 32 / 960 | 0,03333 | [0,02291; 0,04673] | f1 18/480, f10 14/480 | "CI crosses a bound: inconclusive" (sotto 0,025) |
- Episodi non esclusi senza `dispute_rtt_s`: D 0, C 0 (la definizione alternativa non scatta); n = 10 × episodi validi (D 47+49, C 48+48); asserzione dei 10 siti superata; 0 episodi esclusi per sovrapposizione (61 intervalli letti).
- **Esito:** nessuno dei due IC è interamente fuori dal proprio intervallo ⇒ (c) **non falsificata** in nessuno dei due bracci; seconda clausola **soddisfatta** (IC di C interamente sopra l'IC di D: 0,02291 > 0,01772; non è "interamente sotto"). I due bracci restano "inconclusivi" per il criterio per braccio. I dati tcpdump (2/200 D, 6/200 C) erano noti prima: non vengono mescolati.

## 8. `lan` dopo (`<blk>/analysis_lan_after.md`, riferimento per (a))
Mediane (n = 10, 0 esclusi, `other_cores` 0,163-0,176): C/1 dispute-rtt 82,70 [78,14; 89,70] e P-log 80,04 [75,56; 86,62] ms; C/10 25,04 [23,60; 27,19] e 19,65 [19,20; 22,01]; D/1 50,51 [45,55; 58,04] e 48,76 [43,93; 55,76]; D/10 21,65 [20,38; 26,01] e 18,86 [17,53; 22,12]. P-log accettato per C/1 e D/1, non accettato per C/10 (0,127) e D/10 (0,133). P-a4 (C−D, FANOUT 1, last-site P-log) 31,27 [22,79; 40,25] ms: "criterio ambiguo, non conclusivo" (IC attraversa il limite 32 dell'intervallo [15, 32]). (a) a `lan` degenere (riferimento = la cella stessa).

## 9. Incidenti di processo (riportati, non risolti)
- Un estratto filtrato di `state.json` (14:42:17) finiva con `b1_start C_f1` mentre il conteggio dei `b1_end` era 6; la lettura completa delle 14:43:22 è coerente (8 `b1_end`). Il motivo della discrepanza dell'estratto non è accertato.
- Il mio primo calcolo della finestra di `D_f1` fallì (`KeyError: 't0'`, righe escluse senza `t0`); corretto in lettura. Una invocazione `analyze_c.py --help` trattò `--help` come file (traceback, nessuna scrittura).
- Due processi `bash …netem_watch2.sh` effimeri (pid 3175604/3175606) osservati alle 13:37:44, spariti alla lettura successiva; compatibili con subshell del watcher, non verificato con il ppid nel momento.
- Nessuna modifica a `code/src`, `service.py`, `results/`, né ai file congelati; nessun sudo.

## 10. Stato
Blocchi di rete chiusi (`lan` prima, `degraded`, `lan` dopo). Sul nodo: `DONE` presente (14:43); i container residui dopo `DONE` non sono stati riletti. In attesa delle decisioni dell'utente; non analizzo M1/M2 né altro.
