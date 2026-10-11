# Audit 28 — Sensibilità di (a) alle tre sessioni `lan` e dati per sito (2026-10-11)

Complementare ad audit 27. Il verdetto pre-registrato di (a) a `wan` (riferimento = sessione `lan` adiacente "prima", 08:40 UTC) **resta il risultato**; qui solo la sensibilità, descrittiva (`a_sensitivity.py`, ipotesi dichiarate nel docstring e committate prima di eseguirlo).

## 1. Sensibilità di (a) al riferimento `lan`
Misura: ultimo sito P-log (le quattro celle `wan` sono `P-log-apply`). Sessioni `lan` del giorno: 07:52 (`b1`), 08:27 (`b1_default`), 08:40 (`before`). **D è in tutte e tre; C solo in `b1` e in `before`** (la sessione 08:27 era `default` contro D), quindi per C le sessioni sono due.
| arm | FANOUT | wan median ms [CI] | 10xn_RTTxR or n_RTTxR ms | reference | lan median ms | threshold ms | excess ms | verdict |
|---|---|---|---|---|---|---|---|---|
| C | 1 | 4827.7 [4809.6; 5427.3] | 4800 | 07:52 (b1) | 105.96 | 5117.9 | -290.2 | not falsified |
| C | 1 | 4827.7 [4809.6; 5427.3] | 4800 | 08:40 (before, adjacent) | 73.31 | 5019.9 | -192.2 | not falsified |
| C | 1 | 4827.7 [4809.6; 5427.3] | 4800 | max of sessions | 105.96 | 5117.9 | -290.2 | not falsified |
| C | 10 | 429.3 [420.2; 1018.0] | 480 | 07:52 (b1) | 30.61 | 571.8 | -142.6 | not falsified |
| C | 10 | 429.3 [420.2; 1018.0] | 480 | 08:40 (before, adjacent) | 20.88 | 542.6 | -113.4 | not falsified |
| C | 10 | 429.3 [420.2; 1018.0] | 480 | max of sessions | 30.61 | 571.8 | -142.6 | not falsified |
| D | 1 | 3191.8 [3174.3; 3824.5] | 3200 | 07:52 (b1) | 67.31 | 3401.9 | -210.1 | not falsified |
| D | 1 | 3191.8 [3174.3; 3824.5] | 3200 | 08:27 (b1_default) | 48.41 | 3345.2 | -153.4 | not falsified |
| D | 1 | 3191.8 [3174.3; 3824.5] | 3200 | 08:40 (before, adjacent) | 45.85 | 3337.5 | -145.7 | not falsified |
| D | 1 | 3191.8 [3174.3; 3824.5] | 3200 | max of sessions | 67.31 | 3401.9 | -210.1 | not falsified |
| D | 10 | 259.0 [256.6; 591.9] | 320 | 07:52 (b1) | 25.91 | 397.7 | -138.8 | not falsified |
| D | 10 | 259.0 [256.6; 591.9] | 320 | 08:27 (b1_default) | 21.99 | 386.0 | -127.0 | not falsified |
| D | 10 | 259.0 [256.6; 591.9] | 320 | 08:40 (before, adjacent) | 17.82 | 373.5 | -114.5 | not falsified |
| D | 10 | 259.0 [256.6; 591.9] | 320 | max of sessions | 25.91 | 397.7 | -138.8 | not falsified |

- C FANOUT 1: median 4827.7 vs pred 4800 (diff +27.7 ms): verdict would become 'inconclusive' only for a lan reference below 9.24 ms and 'falsified' below 3.20 ms (lan medians of the day: 73.3-106.0 ms)
- C FANOUT 10: median 429.3 vs pred 480 (diff -50.7 ms): the median is below the network term alone: no non-negative reference can make it exceed the threshold
- D FANOUT 1: median 3191.8 vs pred 3200 (diff -8.2 ms): the median is below the network term alone: no non-negative reference can make it exceed the threshold
- D FANOUT 10: median 259.0 vs pred 320 (diff -61.0 ms): the median is below the network term alone: no non-negative reference can make it exceed the threshold

**Lettura (solo dati).** Il verdetto "non falsificata" **non cambia** con nessuna delle sessioni né con il massimo (ipotesi di robustezza non falsificata). Margini minimi sotto la soglia: D/1 −145,7, C/1 −192,2, D/10 −114,5, C/10 −113,4 ms (riferimento adiacente); con il riferimento `lan` più alto del giorno i margini sono più ampi. **Solo C FANOUT 1 può essere sensibile in principio:** la sua mediana (4827,7 ms) supera il solo termine di rete (4800 ms) di 27,7 ms, quindi il verdetto diventerebbe "inconclusivo" solo con un riferimento `lan` sotto 9,24 ms e "falsificato" sotto 3,20 ms; i riferimenti reali del giorno sono 73,3-106,0 ms. Per D/1, C/10 e D/10 la mediana è sotto il termine di rete: nessun riferimento non negativo può farle superare la soglia.

## 2. Dati per sito in `cells.jsonl`: presenti e completi
Ogni riga di episodio ha, per **tutti i 10 siti**, i campi `withdrawn_plog_s` (ritiro P-log da t0), `plog_apply_ts` (ora di `POST /apply_fanout 200` del sito), `plog_ack_ts`, `plog_ack_count`, `pending_after_response`, `pending_left` (6/6 campi con 10 siti in ogni episodio di ogni cella), più `t0`, `t_resp`, `dispute_rtt_s`, `status`. `episodes.jsonl` (40 righe) contiene gli stessi campi per episodio. **Mancanti: 0** su 400 sito-episodi (100/100 per cella). Script `per_site_check.py`, uscita `wan_20261011/per_site_check.md`. Mediane per sito (ms, siti 0..9):

| Braccio | FANOUT | Mediana per sito |
|---|---|---|
| D | 1 | 249 576 902 1228 1556 1880 2205 2544 2868 3192 |
| C | 1 | 414 902 1391 1881 2371 2860 3347 3841 4339 4828 |
| D | 10 | 255 254 254 256 256 257 256 256 258 258 |
| C | 10 | 418 419 420 419 419 420 420 420 420 420 |

Descrittivo: a FANOUT 1 i siti sono ritirati in sequenza, con incrementi di circa 327 ms (D) e 490 ms (C) per consegna; a FANOUT 10 i siti sono quasi simultanei. Non commento oltre.

## 3. `lan` dopo: preparato, non eseguito (serve l'utente)
Il watcher `wan` è ancora attivo; fermarlo richiede sudo (Ctrl-C nel tmux). Lo script `run_wan_block.py --only-lan-dopo` (nuovo flag, test, 65 in `experiments_tnsm`) chiede conferma "watcher fermato e `netem_show.sh` pulito?", poi lancia le quattro celle `lan` e L_dns a `lan` con il guard "watcher assente" (rifiuta se il watcher gira), copia con sha256, analizza e rifà l'analisi di (a) con riferimento prima+dopo (mediana più alta). Resta a carico dell'utente fermare il watcher.

## 4. `lan` dopo (eseguito dall'utente con `run_wan_block.py --only-lan-dopo`, 2026-10-11 09:21:12-09:25:04 UTC; watcher fermato e `netem_show.sh` pulito confermati dall'utente al prompt; sha256 verificati dallo script; commit `c301754`)
Dati: `experiments_tnsm/m67_retraction/wan_20261011/lan_after/`, `ldns_after/`; analisi `analysis_lan_after.md` e `analysis_wan_before_after.md`. 4 celle, 10 episodi, `aborted: false`, 0 esclusioni per ogni causa, nessuna cella segnalata (`other_cores` 0,09-0,12, `steal_pct` 0,005-0,016), 0 consegne in pending, 0 ack, nessuna saturazione.

| Braccio | FANOUT | Ultimo sito P-log ms [IC] | `dispute-rtt` ms [IC] | Rapporto P-log | Misura |
|---|---|---|---|---|---|
| D | 1 | 47,36 [42,98; 49,25] | 49,07 [44,43; 50,85] | 0,053, accettato | `P-log-apply` |
| C | 1 | 70,03 [64,72; 74,55] | 71,66 [66,60; 77,14] | 0,036, accettato | `P-log-apply` |
| D | 10 | 17,09 [15,64; 20,32] | 19,04 [18,25; 22,85] | 0,146, non accettato | `dispute-rtt` |
| C | 10 | 21,65 [18,43; 22,69] | 26,52 [23,96; 28,48] | 0,115, non accettato | `dispute-rtt` |

**L_dns a `lan` dopo** (50 campioni, `site-3`): sito vivo p50 0,174 / p95 0,217 / max 2,09 ms; **sito morto p50 2,85 / p95 3,04 / max 4,97 ms**, `gaierror(-3, …)`. Serie del giorno (p95 sito morto): `lan` 08:03 3,87; 08:08 7,53; 08:14 9,87; 08:45 4,02; `wan` 08:54-56 3,46; `wan` 09:01-06 3,33; `lan` dopo 09:25 3,04 ms.

**Regola (a) con riferimento prima+dopo (mediana più alta per cella; verdetto pre-registrato in audit 26):** invariato, **non falsificata in tutte e 4 le celle**: C/1 riferimento 73,31 (prima) → soglia 5019,9, eccesso −192,2; D/1 riferimento 47,36 (dopo) → 3342,1, −150,2; C/10 21,65 (dopo) → 545,0, −115,7; D/10 17,82 (prima) → 373,5, −114,5 ms.

**P-a4 (C − D, FANOUT 1, ultimo sito, +23,5 ms, [15, 32]) nelle tre sessioni `lan` con C e D:** 38,65 [22,85; 49,69] (07:52, attraversa il 32: non conclusivo); 27,46 [25,34; 32,38] (08:40, attraversa il 32: non conclusivo); **22,67 [16,92; 29,27] (09:21, IC interamente dentro [15, 32])**. Il criterio registrato è ambiguo (audit 25 §A.2); la classificazione della prima sessione resta "non conclusivo" e le tre misure si riportano **tutte**, senza sceglierne una. C − D a FANOUT 10 (descrittivo): 4,57 ms [0,27; 6,59] (P-log), 7,48 [3,05; 9,55] (`dispute-rtt`).

**Deriva** (D, mediana P-log dell'ultimo sito; descrittivo): FANOUT 1: 67,3 (07:52), 48,4 (08:27), 45,9 (08:40), 47,4 (09:21) ms; FANOUT 10: 25,9, 22,0, 17,8, 17,1 ms. Dopo la prima sessione i valori di D/1 restano fra 45,9 e 48,4 ms; la sequenza non è più decrescente per D/1 (45,9 → 47,4).
