# Audit 21 — Rapporto della notte 2026-10-10/11 (blocco `wan`)

Scritto la mattina dell'11 ottobre alla ripresa della sessione. Solo fatti e regole pre-registrate; nessuna interpretazione oltre queste. Dati copiati in `experiments_tnsm/m67_retraction/night_wan_20261011/` (stato, manifest, `cells.jsonl`, soglie, calibrazioni, log del watcher, eventi di profilo); gli output pesanti di M1/M2 restano sul nodo in `~/dib_tnsm/out/night_20261011/run/{m1,m2}/`.

## 1. Cosa è stato eseguito (`night.py`, PID 878739, avviato 22:38:34 UTC, finito 02:50:12 UTC, `DONE`)
Tree congelato `~/dib_tnsm/tree-6b8a6fa` (18 hash verificati all'avvio), watcher `--poll 0.5 wan` in tmux dalle 22:36 (profilo applicato 22:36:04,854; verificato dall'utente con `netem_show.sh`: 11 namespace `delay 80ms loss 1%`).

| Fase | Esito |
|---|---|
| Calibrazione a `wan` (22:38-22:40) | ok, RTT confermato |
| Soglia P-log | `plog_thresholds_wan.json`, sha256 `aa3e03585cb7294f2f052cc5848801c0708353373690c09c9cddf2f468eb291d`; **identico alla copia committata ora** (la soglia non è stata committata prima di B1: la sessione non era viva, flag non creato, attesa di 600 s poi B1; per la tua regola la pre-registrazione vale perché l'hash coincide) |
| B1 `b1_C_f10` | **fallito** (22:50-22:51), nessun dato |
| B1 `b1_D_f1` | completato, 10 episodi |
| B1 `b1_C_f1` | completato, 10 episodi |
| B1 `b1_D_f10` | **fallito** (22:57-22:58), nessun dato |
| B2-kill | **non eseguito** (regola: L_dns p95 186,0 ms > 50 ms; inoltre watcher a 0,5 s) |
| M1 (due bracci) | ritorno 0, **100 celle**, 22:58-01:25, non analizzato |
| M2 (braccio `deploy`) | ritorno 0, **90 celle**, 01:25-02:50, non analizzato |
| Smontaggio | 0 container `dibtnsm` residui; disco 3,8 GB liberi |

Non eseguiti: k = 50, B2-partition, A2 grezza (vedi §6). I gruppi falliti non hanno fermato la coda (nessun tre consecutivi).

## 2. Difetto trovato: i due gruppi FANOUT 10 sono caduti per un errore del driver
Entrambi, con la stessa traceback: `httpx.RemoteProtocolError: Server disconnected without sending a response`, in `setup_fact` (`run.py:574`, chiamate di preparazione non cronometrate di `/seed`, `/query`, `/commit`), non catturata perché l'episodio cattura solo `ClientTimeout`: l'eccezione ha ucciso l'intera invocazione e `cells.jsonl` è rimasto vuoto (le celle si scrivono a fine cella). **Ipotesi, non verificata:** riuso di una connessione keep-alive che il server aveva già chiuso (timeout keep-alive di uvicorn ~5 s) con il FIN ancora in volo a causa di d = 80 ms; con FANOUT 10 la cadenza degli episodi (setup ~1 s, `/dispute`, letture, pausa) è vicina ai 5 s, con FANOUT 1 è oltre 10 s. Nessuna correzione applicata (regola della notte). Proposta per domani: non riusare connessioni nelle chiamate di preparazione (client nuovo per episodio o `max_keepalive_connections=0` sul client di setup, mantenendo il warm prima di t0) e catturare gli errori di trasporto per episodio come esclusione con causa, non come uscita del driver; poi rilanciare i due gruppi FANOUT 10, con nuova conferma degli hash.

## 3. B1 a `wan`: dati dei due gruppi completati (FANOUT 1, T = 5 s, 10 episodi per cella)
| | D (senza mTLS) | C (mTLS) |
|---|---|---|
| Episodi / esclusi / `client_timeout` / `queues_not_empty_at_start` | 10 / 0 / 0 / 0 | 10 / 0 / 0 / 0 |
| Mediana `dispute-rtt` | 3,367 s | 5,650 s |
| Mediana ritiro diretto, ultimo sito (P-log, `P-log-apply`), n episodi | 3,204 s (10) | 5,471 s (9) |
| Scarto risposta − ultimo P-log (mediana, max) | 163,0 ms, 163,5 ms | 163,2 ms, 164,2 ms |
| Accordo P-log/`dispute-rtt` entro 3 ms | no (per costruzione, vedi scarto) | no |
| Rapporto di accettazione P-log (p95 calibrato 3,596 ms) | 0,0011 (< 10%: accettato) | 0,00066 (accettato) |
| Soglia dichiarata (10% del ritiro previsto, (a)) | 320 ms | 480 ms |
| Siti in pending dal log di evidence / righe di ack | 0 / 0 | 1 / 1 |
| Letture di pending (controllo incrociato) | 0 | 1 (stessa) |
| `read_undercount_sites`, non misurati, non drenati | 0, 0, 0 | 0, 0, 0 |
| `other_cores` / `steal_pct` del fondo (soglie 1,0 / 2,0) | 0,202 / 0,99, non scartata | 0,178 / 0,59, non scartata |
| Carico del generatore (processo, host) | 0,016 core (max 0,07), host 5,7% | 0,019 core (max 0,23), host 5,1% |
| `generator_path_ms` riusata / nuova, flag | 83,3 / 163,9 ms, `reused_ok` `fresh_ok` veri, flag falso | 83,4 / 247,8 ms, nuova senza aspettativa (TLS), flag falso |
| Creazione cluster → profilo confermato | 5,07 s, 1 tentativo, già a ~160 ms alla prima sonda (la durata include la sonda: 10 siti × 3 connessioni × 0,16 s) | 6,14 s, 1 tentativo, idem |
| Tipi di misura | `P-log-apply` per i diretti, `P-log-ack` per il caso in pending | idem |

Per episodio (s), D ultimo sito P-log: 3,223 3,385 3,194 3,200 3,191 4,190 3,198 3,219 3,208 3,181; C: 5,874 5,471 4,855 5,860 7,837 5,502 5,217 4,840 4,839 (il decimo episodio è quello con consegna in pending; il suo `dispute-rtt` è 10,209 s). Ritardo delle letture del pending dopo la risposta: D 0,09-0,46 s, C 0,27-0,69 s.

## 4. Esito delle predizioni, secondo le regole pre-registrate
- **(a) ritiro ≈ n_RTT·R + servizio:** **non valutabile**. La regola confronta la mediana con `n_RTT·R + 3 × (mediana a lan dello stesso braccio, stessa sessione)`: stanotte non c'è alcuna misura a `lan`, mancano i due gruppi FANOUT 10, e la regola scritta non dice se per FANOUT 1 il termine `n_RTT·R` vada letto per consegna o come somma lungo il fan-out sequenziale (10 consegne): serve la tua lettura prima di valutarla. Dati grezzi in §3 e nei `cells.jsonl`.
- **(b):** il docstring di `run.py` non definisce una predizione (b); nessun esito.
- **(c) quota in pending a `wan`:** il criterio è "≥ 2 consegne in pending nel blocco B1 del profilo" (falsifica). Osservata **1** (braccio C, FANOUT 1) su 200 consegne eseguite di 400 previste dal blocco: **non falsificata, blocco incompleto** (mancano i due gruppi FANOUT 10, 200 consegne). Osservabile per sito ed episodio con k = 1 (`prediction_c_observable.md`); nessun collasso (1 riga di ack).
- **(d) convergenza B2-kill:** **non eseguita** (B2-kill escluso).
- **(e) correttezza:** nessuna violazione è emersa nei gruppi completati; il controllo di I1-I3 non è una verifica dedicata di B1 e non la riporto come esito.

## 5. Calibrazioni a `wan` (`night_wan_20261011/calib/`, `verify/`)
- **`generator_path_ms`:** riusata 82,3-83,3 ms, nuova 163,9-164,2 ms (braccio D); l'ipotesi "connessione nuova ≈ 2d, riusata ≈ d" è confermata dai dati di tre misure.
- **L_dns** (sito morto, visto dal container evidence sotto netem; 50 campioni): p50 179,8 ms, p95 185,2 ms (calibrazione di prova) e p95 186,0 ms (calibrazione della notte), massimo 4,0 s, errore `gaierror(-3, 'Temporary failure in name resolution')`; sito vivo p50 0,27 ms. Non è stata fatta la misura di controllo con netem rimosso dal solo container che risolve. A `lan` lo stesso valore è risultato 2,6 ms in una misura e 176-186 ms in due altre.
- **Latenza dei log** con evidence e site-0: p95 massimo 3,596 ms (soglia accettata per tutte e quattro le celle: D/1 320 ms, D/10 32 ms, C/1 480 ms, C/10 48 ms).
- **Watcher:** 62 rilevamenti di cambio, 61 applicazioni (0,07-0,71 s), 8 tentativi falliti transitori (un'applicazione mentre il cluster si smontava); `error: no such object` nel log dallo smontaggio dei container; nessun fermo. Ancora attivo alle 07:33, si ferma da solo alle ~07:36. Log copiato in `night_wan_20261011/watch_wan.log` (sha256 `80133d737112dc1c917177a648d5a3491819ea03edad68fcdc45777cedfdc11d`).

## 6. A2 grezza (non eseguita; solo identificazione)
I valori 0,562 (a `f_s` = 0,30, 120 giorni) e 0,663 (a 0,50, 30 giorni) vengono dall'esperimento 22 (`results/masquerade/README.md:52-55,67`; dati `results/masquerade/service_masquerade.csv`), script `code/scripts/service_masquerade_probe.py`; nel paper `docs/main_tnsm.tex:656` dichiara che usa la configurazione selezionata con trust weighting (seme 42, dieci pseudo-siti). Il bound 0,58 e il caso peggiore 0,579 sono con breadth grezza. Non ho letto lo script né rilanciato nulla: il rilancio con breadth grezza e gli stessi seed richiede ipotesi e regola di falsificazione committate prima dei dati.

## 7. Altre note
- **M1/M2 hanno girato con il watcher attivo** (sondaggio ogni 0,5 s, stimato ~0,07 core): il fondo è un'altra attività del nodo; il campione di fondo di ogni cella ne tiene conto in `other_cores`. Non analizzati.
- La nota di stato (audit 20) non è stata aggiornata durante la notte (sessione non attiva).

## 8. Decisioni che servono
1. Correzione del driver per le connessioni stale (§2) e rilancio dei due gruppi FANOUT 10 a `wan` (watcher e profilo vanno riattivati dall'utente).
2. Lettura di (a) per FANOUT 1 e misura di `lan` nella stessa sessione.
3. Se rilanciare B1 `wan` per intero dopo la correzione, per avere i quattro gruppi dallo stesso tree.
4. A2 grezza (§6).
