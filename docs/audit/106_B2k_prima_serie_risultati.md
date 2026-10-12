# Audit 106 — B2-kill sul codice finale, PRIMA SERIE (10 prove per cella): verdetti dell'audit 99

Pre-registrazione: `docs/audit/99_prereg_B2k_file_finale.md` (con addendum 1-3). Dati: `experiments_tnsm/final_B2k_20261012/` (copiati dal nodo con sha256, 0 differenze, pcap esclusi; 6 directory `b2kill_<profilo>_<braccio>`, calibrazioni L_dns e `seq.log`). Run 2026-10-12T16:43Z → 20:15Z, `deploy_b2k.sh` (applicatore netem in user space, poll 0,1 s), albero `tree-c898ea8`, `service.py` sha256 `3ffa57ee…`. Analisi: `analyze_b2k.py`, soglie dell'audit 45 invariate. **La seconda serie (20 prove per cella, albero `tree-550afed`) è in corso: i verdetti finali saranno sulle due serie unite (n = 30); questo audit riporta la sola prima serie.**

## Regola L_dns e immagine
- L_dns (p95 del sito morto) con applicatore a poll 0,1 s: `lan` 1,4 ms, `degraded` 1,3 ms, `wan` 1,6 ms; tutti ≤ 50 ms ⇒ tutti e tre i profili eseguiti.
- **H-G:** lo sha256 di `/app/service.py` nei container è `3ffa57ee…` in tutti i gruppi (6/6).
- Nessun container rimasto (`containers_left.txt` = 0), rc=0 per ogni bracco.

## Tabella completa (28 celle)
| profile | arm | T | k | n | converged | never | median s [CI] | bound s | (d-kill) | (e) violations | excluded |
| degraded | C | 5 | 1 | 10 | 10 | 0 | 2.72 [2.56; 3.15] (n=10) | 7.60 | not falsified | 0 | 0 |
| degraded | C | 15 | 1 | 10 | 10 | 0 | 3.69 [3.09; 4.60] (n=10) | 8.60 | not falsified | 1 | 0 |
| degraded | C | 5 | 10 | 7 | 7 | 0 | 2.92 [2.55; 4.34] (n=7) | 7.60 | not falsified | 0 | {'setup_failed': 3} |
| degraded | C | 15 | 10 | 8 | 8 | 0 | 4.10 [3.44; 4.54] (n=8) | 8.60 | not falsified | 0 | {'setup_failed': 2} |
| degraded | D | 5 | 1 | 10 | 10 | 0 | 2.15 [1.96; 2.88] (n=10) | 7.00 | not falsified | 0 | 0 |
| degraded | D | 15 | 1 | 10 | 10 | 0 | 3.11 [2.63; 4.03] (n=10) | 8.00 | not falsified | 0 | 0 |
| degraded | D | 5 | 10 | 10 | 10 | 0 | 2.47 [2.23; 3.36] (n=10) | 7.00 | not falsified | 1 | 0 |
| degraded | D | 15 | 10 | 10 | 10 | 0 | 3.07 [2.58; 3.35] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | C | 5 | 1 | 10 | 10 | 0 | 0.60 [0.52; 0.89] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 1 | 10 | 10 | 0 | 1.00 [0.61; 1.44] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | C | 5 | 10 | 10 | 10 | 0 | 0.57 [0.51; 0.66] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 10 | 10 | 10 | 0 | 1.07 [0.72; 1.54] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | C | 5 | 50 | 10 | 10 | 0 | 0.74 [0.61; 0.79] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 50 | 10 | 10 | 0 | 1.10 [0.96; 1.47] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | D | 5 | 1 | 10 | 10 | 0 | 0.67 [0.51; 0.85] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | D | 15 | 1 | 10 | 10 | 0 | 1.27 [0.86; 1.68] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | D | 5 | 10 | 10 | 10 | 0 | 0.80 [0.66; 0.83] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | D | 15 | 10 | 10 | 10 | 0 | 1.20 [0.77; 1.38] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | D | 5 | 50 | 10 | 10 | 0 | 0.63 [0.58; 0.85] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | D | 15 | 50 | 10 | 10 | 0 | 1.66 [0.77; 1.81] (n=10) | 8.00 | not falsified | 0 | 0 |
| wan | C | 5 | 1 | 10 | 10 | 0 | 1.52 [1.38; 1.61] (n=10) | 7.00 | not falsified | 0 | 0 |
| wan | C | 15 | 1 | 10 | 10 | 0 | 1.93 [1.36; 2.42] (n=10) | 8.00 | not falsified | 0 | 0 |
| wan | C | 5 | 10 | 10 | 10 | 0 | 1.50 [1.43; 1.65] (n=10) | 7.00 | not falsified | 0 | 0 |
| wan | C | 15 | 10 | 10 | 10 | 0 | 2.21 [1.83; 2.49] (n=10) | 8.00 | not falsified | 0 | 0 |
| wan | D | 5 | 1 | 10 | 10 | 0 | 1.29 [1.14; 1.46] (n=10) | 7.00 | not falsified | 0 | 0 |
| wan | D | 15 | 1 | 10 | 10 | 0 | 2.10 [1.65; 2.40] (n=10) | 8.00 | not falsified | 0 | 0 |
| wan | D | 5 | 10 | 10 | 10 | 0 | 1.24 [1.17; 1.43] (n=10) | 7.00 | not falsified | 0 | 0 |
| wan | D | 15 | 10 | 10 | 10 | 0 | 1.71 [1.51; 2.37] (n=10) | 8.00 | not falsified | 0 | 0 |

## Verdetti come pre-registrati
- **(d-kill) mediana contro il limite: NON falsificata in 0 celle su 28.** Mediane di convergenza: `lan` 0,57-1,66 s, `wan` 1,24-2,21 s, `degraded` 2,15-4,10 s, contro limiti di 7,0-8,6 s.
- **(e) correttezza: FALSIFICATA da due prove** (regola dell'audit 45: "da una sola violazione"; nessuna violazione di stato: tutti gli `final_states` sono `monitor-only`, 3 450 righe, nessuna `staging` o `committing`; la violazione è sul TEMPO oltre il limite):
  - `degraded`, D, T = 5, k = 10, prova 4: 7,097 s contro 7,0 s (+0,097 s);
  - `degraded`, C, T = 15, k = 1, prova 3: **11,605 s contro 8,6 s (+3,0 s)**; sito risalito a +1,34 s, primo `GET /pending/site-3` visibile nel log dell'evidence a +10,07 s, ritiro a +11,61 s.
  Nessuna violazione a `lan` né a `wan`.
- **(f) (nuova, da D1): REGGE.** Nessuna riga `staging` o `committing` negli `final_states`.
- **T15 − T5 (descrittiva):** tra −0,61 e +1,94 s, con intervalli molto larghi (n = 10): non distinguibile dal rumore. La seconda serie la riporterà con n = 30.

## Esclusioni (letto dalle righe)
- **5 prove escluse su 40 in `degraded`/C, tutte nelle celle con k = 10:** quattro `503 evidence unreachable` e un `409 the evidence changed during the commit` nel setup del sito 3. In questa serie il setup di B2k **non** ritentava (usava `check_step`, non `setup_step`: il retry era stato collegato solo al setup di B1): errore mio, corretto per la seconda serie (commit 550afed, test rosso prima). Non toccano (d-kill) né (e), ma riducono n a 7-8 in due celle.
- Nessuna esclusione in `lan`, `wan` e `degraded`/D.

## Lettura (post-hoc, dichiarata tale; i verdetti sopra non cambiano)
Le due prove sopra il limite sono entrambe a `degraded` (RTT 0,4 s, perdita 5 %) e entrambe dove il primo giro di riconciliazione risulta tardi nel log dell'evidence. Il limite è 1,5 + 0,1·T + max(5 s, D_run_max): conta un timeout di riconciliazione da 5 s con poco margine. Con mTLS (il caso da +3 s) un giro fallito (handshake scaduto, 5 s) più la pausa e un secondo giro supera il limite di molto. **I giri falliti non compaiono nel log dell'evidence**, quindi questa è una deduzione dai tempi. La seconda serie registra `reconcile_trace` (giri e conferme visibili all'evidence) e `site3_reconcile_log` (righe del log del sito 3 sulla riconciliazione, che mostrano i tentativi falliti): permetterà di leggere la causa dai dati.
Implicazione per il paper (da decidere dopo la serie unita): "la mediana converge in 1-4 s e resta sotto il limite", ma con code oltre il limite a `degraded` con una frequenza di circa 1/40 (D) e 1/40 (C) nei dati di questa serie; non "sempre entro il limite".

## Limiti
n = 10 per cella; una macchina; il setup senza retry in questa serie; le code non spiegate dalla traccia.
