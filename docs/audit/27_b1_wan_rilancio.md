# Audit 27 — B1 a `wan`, rilancio confermativo (tree `bf272e8`), 2026-10-11

Eseguito dall'utente con `run_wan_block.py` (commit `de342c3`); watcher `wan` attivo nel tmux del nodo (poll 0,5). Dati: `experiments_tnsm/m67_retraction/wan_20261011/` (`b1/`, `calib_wan_b/`, `plog_thresholds_wan.json`); analisi completa `wan_20261011/analysis_wan.md`. Questo è il **rilancio, il confermativo**; i dati della notte (tree `6b8a6fa`) restano "primo run" (audit 21), non mescolati ai conteggi. Mediane con IC bootstrap percentile al 95% sugli episodi (n = 10: grossolani). Nessuna spiegazione oltre i dati.

## 1. Provenienza e verifiche
- Calibrazione `wan` (`calib_wan_b`, 09:01:33-09:06:43 UTC, hold 240 s): il commit con le soglie (`3574d5c`, 09:06:46 UTC) esiste solo dopo la domanda di verifica di `netem_show.sh` e **1 s prima** dell'avvio di B1 (09:06:47,458): le soglie sono quindi committate **prima del primo dato**. La risposta "s" dell'utente non è registrata nei file (inferita dal fatto che lo script è proseguito).
- `rtt_check_ok` vero, RTT evidence→sito **160,3 ms** a tutti e 10 i siti (banda 128-192); `generator_path_ms` riusata 82,77 / nuova 163,27 ms (`reused_ok` e `fresh_ok` veri).
- Copie con **sha256 verificato sui due lati** dallo script (`calib_*`, `b1/cells.jsonl` locale `5782ba80c3a797a8ff71646657b665ccb2574a2872dbf3195fb482af61623c42`, `manifest.json`, `episodes.jsonl`). B1: 09:06:47-09:15:02 UTC, `aborted: false`, `run.py` `022d97a6…`, 4 ricreazioni del cluster, ordine C f10, D f1, C f1, D f10 (seme 20261014).
- **Soglie P-log** (`plog_thresholds_wan.json` sha256 `750de8b90d6a90e7dd52aee89a6fafc2d1487d9b01ef7e80e40078339e65a219`): p95 calibrato **2,43 ms** (evidence in parallelo; singolo 2,21 ms); soglie D/1 320, D/10 32, C/1 480, C/10 48 ms, **uguali a quelle della notte** (controllo di coerenza: dipendono solo da R); tutte e 4 le celle accettabili.
- **L_dns a `wan`** (stessa calibrazione, 50 campioni, `site-3`): sito vivo p50 0,174 / p95 0,234 / max 1,82 ms; **sito morto p50 3,02 / p95 3,33 / max 5,75 ms**, `gaierror(-3, …)`. Valori adiacenti, senza etichette: `lan` 08:45 p95 4,02 ms; `wan` 08:54-08:56 p95 3,46 ms; `wan` 09:01-09:06 p95 3,33 ms. La notte, a `wan`, p95 185-186 ms. Non dichiaro né "proprietà dell'ambiente" né "dipendenza dal profilo".
- Il riferimento `lan` per (a) è la sola sessione "prima" (08:40-08:44 UTC): **la sessione "dopo" non è stata eseguita** (nessun `--lan-dopo`); B1 a `wan` è iniziato 26 minuti dopo, in un nodo con deriva documentata (audit 26 §A.4): limite dichiarato.

## 2. Risultati per cella (10 episodi, ultimo sito = max P-log di 10 siti; tutte `P-log-apply`, P-log accettato)

| Braccio | FANOUT | Ultimo sito P-log ms [IC] | `dispute-rtt` ms [IC] | Rapporto P-log | Gap risposta − P-log (mediana, max) ms | Esclusioni | `other_cores` / `steal_pct` | `generator_path_ms` riusata / nuova (flag) |
|---|---|---|---|---|---|---|---|---|
| D | 1 | 3191,84 [3174,33; 3824,47] | 3355,28 [3338,00; 3987,06] | 0,001 | 162,89, 163,98 | 0 | 0,163 / 0,010 | 82,46 / 163,17 (falso) |
| C | 1 | 4827,72 [4809,59; 5427,32] | 5087,31 [4975,23; 5589,66] | 0,001 | 162,92, 525,40 | 0 | 0,192 / 0,016 | 81,49 / 245,61 (falso) |
| D | 10 | 258,97 [256,55; 591,89] | 521,96 [420,62; 1069,56] | 0,009 | 163,47, 807,32 | 0 | 0,157 / 0,021 | 82,12 / 163,49 (falso) |
| C | 10 | 429,26 [420,20; 1017,98] | 862,66 [586,93; 1260,45] | 0,006 | 167,00, 522,46 | 0 | 0,153 / 0,026 | 82,43 / 246,12 (falso) |

Esclusioni: 0 per ogni causa (`client_timeout`, `queues_not_empty_at_start`, `transport_error_setup`, `transport_error_measured`), nessuna cella segnalata dalla regola di scarto, nessuna saturazione del generatore (processo 0,013-0,032 core). Nessuna consegna in pending, 0 righe di ack, `read_undercount_sites` 0.
**Valori per episodio (ms, ultimo sito P-log):** D/1 3202 3824 4182 4182 3174 3174 3182 3388 3174 3179; C/1 4833 5815 5017 5427 4807 4812 4809 4810 4823 5501; D/10 276 254 255 457 259 1257 259 257 258 908; C/10 437 419 420 620 1416 422 1419 420 624 420. I valori hanno un piano di base ben definito (D/1 ~3174, C/1 ~4807, D/10 ~255, C/10 ~420) e, in alcuni episodi, eccessi discreti sopra quel piano (da circa +0,2 s fino a +1,0 s); non li spiego.

## 3. Esito di (a), regola di audit 26 §A (riferimento = `lan` adiacente "prima", stesso braccio e FANOUT, mediana della stessa misura; soglia = n_RTT·R·(10 se FANOUT 1) + 3 × riferimento; falsificata se l'IC inferiore è sopra la soglia)

| Braccio | FANOUT | Mediana ms | 10·n_RTT·R / n_RTT·R ms | Riferimento `lan` ms | Soglia ms | Eccesso sulla soglia ms | Esito |
|---|---|---|---|---|---|---|---|
| D | 1 | 3191,8 | 3200 | 45,85 | 3337,5 | −145,7 | **non falsificata** |
| C | 1 | 4827,7 | 4800 | 73,31 | 5019,9 | −192,2 | **non falsificata** |
| D | 10 | 259,0 | 320 | 17,82 | 373,5 | −114,5 | **non falsificata** |
| C | 10 | 429,3 | 480 | 20,88 | 542,6 | −113,4 | **non falsificata** |

Per FANOUT 1 la lettura è 10 × n_RTT × R più il servizio. **Predizione (a) non falsificata in nessuna delle quattro celle.** Scarti rispetto al solo termine di rete: D/1 −8,2 ms, C/1 +27,7 ms, D/10 −61,0 ms, C/10 −50,7 ms. L'aspettativa dell'utente per il braccio C FANOUT 1 (5,12 s di soglia contro 5,47 s del primo run) **non si è ripresentata**: nel rilancio la mediana è 4,828 s (CI superiore 5,427 s, sopra la soglia di 5,020 s, ma la mediana è sotto: regola = "non falsificata"). Primo run della notte, per confronto, **non mescolato** (audit 21 §3): D/1 3,204 s (n = 10), C/1 5,471 s (n = 9).

## 4. Esito di (c) (criterio: ≥ 2 consegne in pending nel blocco B1 del profilo falsifica)
Consegne eseguite nel rilancio: 4 celle × 10 episodi × 10 siti = **400**; consegne in pending dal log di evidence: **0**; righe di ack 0; letture dirette 0. **(c) non falsificata** (0 < 2), compatibile con la previsione `wan` ~8-9·10⁻⁶ (0 osservati). Il primo run (1 consegna in pending su 200 eseguite, braccio C FANOUT 1) non è sommato. Nessun'altra interpretazione.

## 5. Differenze fra bracci (descrittive; P-a4 è registrata per `lan`, non applicabile a `wan`)
C − D, ultimo sito, FANOUT 1: **1635,88 ms [998,43; 2235,48]**; `dispute-rtt` 1732,03 [1008,30; 2234,39]. FANOUT 10: 170,29 ms [−152,10; 662,28] (P-log), 340,70 [−302,90; 548,01] (`dispute-rtt`). Le due previsioni di (a) differiscono di 10·(3−2)·0,16 = 1600 ms a FANOUT 1.
**Correzione di analisi (etichetta, non di dati):** `analyze_b1.py` stampava il verdetto di P-a4 anche a `wan` ("falsified under the strict reading"); P-a4 è registrata per `lan` e l'applicazione era un errore di etichetta. Ora il verdetto compare solo a `lan`; `analysis_wan.md` è rigenerato (stessi numeri). Il verdetto di P-a4 a `lan` è invariato (né falsificata né confermata, non conclusivo).

## 6. Limiti dichiarati
n = 10 per cella (IC grossolani, con code a destra per alcuni episodi); riferimento `lan` solo "prima" e a 26 minuti dal blocco (deriva); un solo blocco di rilancio a `wan`; nessuna analisi di M1 e M2; nessuna spiegazione di code e scarti.
