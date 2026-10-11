# Audit 56 — Risultati di B5: (a') a `degraded`, replica con i tentativi falliti (audit 46, regole di analisi audit 50)

Data: 2026-10-11. Dati: `experiments_tnsm/b5_20261011/` (blocco `auto_block.py` lan_before → degraded → lan_after, nodo `ubuntu@192.168.100.57`, tree `244f1d0` con hash verificati, PKI 336 h, watcher v2 a poll 0,5 s, Python 3.12.3, 16:43-18:15:24Z; **DATA.sha256 verificato dopo la copia: 0 discordanze**; nessun pcap; soglie P-log: file `degraded/plog_thresholds_degraded.json` sha256 `a99773b7…ee405`, p95 calibrato 2,59 ms, scritto prima di B1). Ipotesi e regole: audit 46 e 50 (committati prima dei dati). Analisi: `experiments_tnsm/node_session_20261011/analyze_b5.py` (output `analysis_b5_aprime.md`), `analyze_c.py` e `analyze_b1.py` invariati (`analysis_c.md`, `analysis_b1_degraded.md`). Statuto (46 §1): **replica sullo stesso nodo e profilo** del blocco che ha falsificato (a), non un test indipendente. **Limite di cecità (audit 50, addendum):** l'analista aveva visto l'esito del codice sui dati vecchi prima di questo blocco.

## Esecuzione
Tutti e tre i blocchi `done`, 4 gruppi con dati ciascuno, nessun gruppo rilanciato, `lan` riconfermato alla fine. Esclusi: 4 episodi di C/FANOUT 10 per `transport_error_setup` (46/50 → n = 46 per dispute-rtt); nessuna esclusione per sovrapposizione con profilo non assestato (151 intervalli letti, 0 episodi toccati); nessuna cella segnalata dalla regola di scarto del fondo; regola R-gp: nessuna cella non valutabile (`reused_ok` vero ovunque; `generator_path` fresca C 607-608 ms, `fresh_ok` non definito per il braccio C, come nel blocco precedente).

## (a′): verdetti per cella (p all'estremo superiore: D 0,226; C 0,401)
| arm | FANOUT | n completi | mediana ms [IC 95%] | limite fisico n_RTT·R(×10) ms | soglia (a′) ms | verdetto 1 | verdetto 2 |
|---|---|---|---|---|---|---|---|
| C | 1 | 40 | 18 516 [16 817; 19 703] | 12 000 | 12 872 | **falsificata** | ok |
| C | 10 | 38 | 2 826 [2 820; 2 982] | 1 200 | 1 888 | **falsificata** | ok |
| D | 1 | 46 | 10 316 [9 872; 11 174] | 8 000 | 8 423 | **falsificata** | ok |
| D | 10 | 49 | 1 639 [1 618; 2 020] | 800 | 1 148 | **falsificata** | ok |

**Globale:** (a′) **falsificata, 4/4 celle**; "modello di base falsificato" 0/4 (nessun IC sotto il limite fisico). La falsificazione regge anche con p all'estremo inferiore (soglie 12 666 / 1 683 / 8 360 / 1 085 ms, nessuna sotto l'estremo inferiore dell'IC). Con la soglia di (a) (senza il termine dei tentativi, riferimento `lan` adiacente più alto) le stesse celle sono falsificate con eccessi di 6 270, 1 564, 2 182 e 780 ms (`analysis_b1_degraded.md`). **Lettura:** la mediana osservata supera sempre di più di quanto (a′) concede (da +0,5 a +5,6 s); l'eccesso di (a′) è minore di quello di (a) ma non si annulla. Una possibile causa (non testata qui, ipotesi): il costo di un tentativo fallito sta vicino al limite per tentativo di `run.py` (`ATTEMPT_HARD_S` D 3 s, C 4 s), non a 1 s. Non si propone nessuna correzione del modello in questo audit.

## (c) replica, per consegna (analysis_c.md)
| arm | pending / consegne | quota | IC Clopper-Pearson 95% | intervallo registrato | classificazione |
|---|---|---|---|---|---|
| D | 5 / 1000 | 0,0050 | [0,0016; 0,0116] | (0,004; 0,015) | l'IC attraversa un estremo: **inconclusiva** |
| C | 21 / 960 | 0,0219 | [0,0136; 0,0332] | (0,025; 0,08) | l'IC attraversa un estremo: **inconclusiva** |
Seconda clausola (C sopra D, forma non ambigua): **soddisfatta** (IC di C interamente sopra quello di D). Nel blocco precedente: D 9/960, C 32/960 (paper `wip:640`). Frazione di *episodi* con almeno un pending (descrittiva, non primaria, 46 §3): **non calcolata in questo audit** (i conteggi sopra sono per consegna); resta da produrre se serve al paper.

## Descrittivo (nessun criterio)
C − D a FANOUT 1: +8 200 ms [6 339; 9 265] (P-log); a FANOUT 10: +1 186 ms [804; 1 313]. Mediane di dispute-rtt: C/1 19 578, C/10 4 284, D/1 11 117 ms.

## Cosa si può dire e cosa no
- (a′) non sostituisce (a) come modello predittivo del tempo di ritiro a `degraded` in questo nodo: falsificata 4/4 anche con la lettura più permissiva di p. Il paper può riportare (a) falsificata e (a′) falsificata nella replica, con lo statuto di replica non indipendente.
- (c) **non è né confermata né falsificata**: due IC che attraversano gli estremi registrati.
- Nessun confronto con altre macchine; tempi su CPU QEMU generica con k3s e altri carichi di fondo (a04:154, 164-167).
