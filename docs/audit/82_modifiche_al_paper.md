# Audit 82 — Modifiche a `docs/main_wip.tex` (copia canonica di lavoro, CLAUDE.md): cosa è stato aggiunto, con la fonte di ogni numero

Data: 2026-10-12. Commit: vedi `git log docs/main_wip.tex`. Il paper compila (`latexmk -pdf`, 13 pagine come prima, nessun errore né riferimento indefinito, compilazione in una copia temporanea). **Solo risultati validati o dichiarati come limiti**; nessuna modifica a `main.tex`, `main_old.tex`, `formal/`, `claims.json`, `results/`. Il branch `tnsm-fsm-paper` dell'altra sessione modifica lo stesso file: al merge possono esserci conflitti nelle sezioni di valutazione (le mie modifiche sono in tre punti, righe 610, 642, 784 del file dopo la modifica).

| Punto (riga) | Affermazione aggiunta | Fonte (audit, file) |
|---|---|---|
| 642 (Sec. `sec:netem-results`, al posto del calcolo post-hoc "1 s per tentativo fallito") | replica del blocco `degraded`: (a) falsificata di nuovo in 4/4 celle con eccessi di 0,8-6,3 s; (c) inconclusa (D 5/1 000, C 21/960) | audit 56 (`analysis_b1_degraded.md`, `analysis_c.md`) |
| 642 | modello di costo di consegna senza parametri adattati (handshake, TLS, richiesta in due segmenti, RTO R + max(2R; 0,2) s, riconciliazione ogni 5 s); due versioni precedenti non validate; la finale entro 1,7 punti sulle consegne in ritardo in 6 condizioni nuove (RTT 120-360 ms, perdita 4-8 %) e nessun sito non riconciliato; sovrastima del p95 fino al 60 % a RTT alto; due segmenti inferiti, non catturati | audit 62, 75, 76, 78, 79, 80, 81 (`run_20261012_v4/analysis.md`); replica sul nodo: audit 83-84 (`run_node_v4/analysis.md`, 5/6 celle entro 3 punti) |
| 642 | fan-out sequenziale 3,1-7,1× più lento del parallelo in 9 condizioni (RTT 100-400 ms, perdita 2-10 %); in 3 280 episodi con perdita ogni sito ha raggiunto `disputed` (fan-out o riconciliazione); default parallelo | audit 77, 79 (`run_20261012_s1/analysis.md`); 3 280 = conteggio su 5 run (audit 81) |
| 610 (paragrafo dei trial di interruzione) | kill-and-restart con k = 1, 10, 50: a `lan` mediane 0,6-1,7 s contro bound 7-8 s in 12/12 celle, 0 violazioni in 120 prove; a `degraded` e `wan` (k ≤ 10) mediane 1,0-4,3 s, la più lenta di 157 prove utilizzabili al 98,6 % del bound; resolver senza domini di ricerca solo per `lan` | audit 73 (`b2k_dnsfix_20261012`), 57 (`b2k_20261011`), 72 |
| 784 (Discussione) | nessuna scadenza di ritiro finché il gateway è irraggiungibile; dopo la riconnessione la convergenza è rimasta entro il bound in ogni cella misurata | audit 57, 73 |

## Cosa NON è stato modificato e perché
- Il numero di 530,3 operazioni/s, lo sweep su N e il "20,6 % più lento" (righe 604-606) restano: sono numeri vecchi già segnalati nell'audit 43 per riscrittura, decisione dell'autore (Q6-Q8, Q10).
- Le affermazioni su G3 ("imposes no deadline") restano: il paper continua a non promettere un limite per siti irraggiungibili; il limite dopo la riconnessione è misurato, non dichiarato come garanzia.
- Le connessioni persistenti non compaiono (falsificate, audit 76); `degraded` sul nodo con il watcher non è misurato (audit 74).
## Rischi di lettura da conoscere
La frase sul modello cita un banco di prova che non è il nodo: stessa macchina per tutti i processi, HTTP semplice (arm D), nessun mTLS né Docker. Il paper non lo chiama "validato" in generale ma riporta gli scarti. Il termine "reconciliation every 5 s" è la configurazione di `docker-compose.yml`/`generate_compose.py`, non il default del servizio (T = 0).

## Verifica di merge con `tnsm-fsm-paper` (2026-10-12)
Prova in un worktree temporaneo (branch `tnsm-merge-preview`, nessun branch altrui modificato): un solo conflitto, nel paragrafo della Discussione (la mia frase sul limite dopo la riconnessione contro la frase dell'altra sessione sul veto locale che dipende dall'evidence), risolto tenendo entrambe le frasi; il paper unito compila (14 pagine), la suite `code/tests` passa (491 passed, 7 skipped, 7 xfailed). Con `tnsm-fsm` (senza paper) il merge è pulito. Il preview è nel branch `tnsm-merge-preview` (commit `94ea825`) per chi voglia adottarlo.

## Aggiunta 2026-10-12 (audit 86)

Una frase aggiunta in `docs/main_wip.tex` nel paragrafo del modello di consegna (dopo "inferred, not captured"): sul deployment completo il modello prevede la quota di consegne in ritardo entro 0,7 punti senza mTLS e 3,1 con mTLS, e la mediana dell'ultimo sito a fan-out sequenziale entro il 2 %. Numeri da `docs/audit/86_distribuzione_completa_risultati.md` (D/10 0,186 contro 0,179; C/10 0,282 contro 0,251; F1 10 670 contro 10 600 ms e 16 126 contro 16 400 ms). Una prima formulazione più lunga portava il paper a 14 pagine: accorciata, compila a 13 pagine. La frase riguarda codice PRE-correzione (albero `467a711`); va riconfermata dopo il rerun sul codice di `tnsm-fixes` (audit 87).

## Correzione 2026-10-12 (audit 89)

La frase descritta sopra (0,7 e 3,1 punti, "entro il 2 %") è stata SOSTITUITA in `docs/main_wip.tex` dopo il rerun sul codice corretto (commit ab23ea3): ora dice che su due repliche il modello prevede la quota in ritardo entro 1,5 punti senza mTLS, la sottostima con mTLS di 3,1 e 8,4 punti e la mediana a fan-out sequenziale entro il 9 %. Numeri: `docs/audit/89_rerun_R1_risultati.md`. L'"entro 8 punti" non regge (H-N2 falsificata su C/10).
