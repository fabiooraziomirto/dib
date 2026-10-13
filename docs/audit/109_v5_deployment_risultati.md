# Audit 109 — Validazione fuori campione del modello v5 (mTLS) sul deployment vero: verdetti dell'audit 107

Pre-registrazione: `docs/audit/107_prereg_v5_mtls_sul_deployment_vero.md` (49df46a), committata prima di ogni dato. Dati: `experiments_tnsm/node_oos_20261013/node_oos_x{1..4}/` (copiati con sha256, 0 differenze, pcap esclusi). Run `deploy_run.sh` (applicatore netem in user space) via `night_queue2.sh` su `tree-550afed` (`service.py` sha256 `3ffa57ee…`), 2026-10-13T05:12Z → 07:16Z, rc=0 per i quattro profili, nessun container rimasto. Analisi: `analyze_node_oos.py` (5 test, scritti prima); soglie e previsioni invariate. **Salute dei run:** nessun profilo interrotto (la verifica della banda RTT con perdita è passata), nessuna esclusione, nessun `setup_failed`; ritentativi del setup recuperati (x1 15, x2 5, x3 e x4 in `cells.jsonl`); `image_service_sha256` = `3ffa57ee…` per 11 container in tutte le celle.

## Tabella (analyze_node_oos.py): quota di consegne in ritardo per sito, FANOUT 10, 50 episodi per cella
| condizione | R (s) | braccio | episodi | esclusi | quota in ritardo [IC 95 %] | previsione | immagine |
|---|---|---|---|---|---|---|---|
| X1 | 0.12 | D | 50 | 0 | 0.216 [0.184; 0.250] | D 0.217 | ['3ffa57ee'] |
| X1 | 0.12 | C | 50 | 0 | 0.384 [0.343; 0.423] | v4 0.307, v5 0.348 | ['3ffa57ee'] |
| X2 | 0.2 | D | 50 | 0 | 0.156 [0.130; 0.182] | D 0.15 | ['3ffa57ee'] |
| X2 | 0.2 | C | 50 | 0 | 0.219 [0.182; 0.259] | v4 0.217, v5 0.248 | ['3ffa57ee'] |
| X3 | 0.3 | D | 50 | 0 | 0.238 [0.207; 0.272] | D 0.21 | ['3ffa57ee'] |
| X3 | 0.3 | C | 50 | 0 | 0.379 [0.344; 0.415] | v4 0.288, v5 0.319 | ['3ffa57ee'] |
| X4 | 0.3 | D | 50 | 0 | 0.299 [0.256; 0.345] | D 0.265 | ['3ffa57ee'] |
| X4 | 0.3 | C | 50 | 0 | 0.458 [0.412; 0.505] | v4 0.353, v5 0.388 | ['3ffa57ee'] |

Scarti (misura − previsione): D contro modello D: X1 −0,001, X2 +0,006, X3 +0,028, X4 +0,034. C contro v5: X1 +0,036, X2 −0,029, **X3 +0,060, X4 +0,070**; C contro v4: +0,077, +0,002, +0,091, +0,105.

## Verdetti come pre-registrati
- **H-N0 (controllo D, ±0,04 da previsione): REGGE** in tutte e quattro le condizioni (scarto massimo +0,034 in X4). Tutte interpretabili.
- **H-N1 (|C − v5| ≤ 0,05 in ogni condizione interpretabile): CADE.** X3 (+0,060) e X4 (+0,070) escono dalla soglia; X1 (+0,036) e X2 (−0,029) dentro.
- **H-N2 (errore assoluto medio v5 < v4 e |ε5| ≤ 0,04): REGGE.** MAE v5 = 0,049, MAE v4 = 0,068; ε5 = +0,034, ε4 = +0,068.
- **Esito per il paper (tabella dell'audit 107): `not_confirmed`.** Il limite con mTLS resta; il paper non cambia.

## Lettura (post-hoc, dichiarata tale: non cambia l'esito)
- **Senza mTLS il modello regge sul nodo** in quattro condizioni nuove (entro 3,4 punti; X3 e X4 con +0,028 e +0,034, cioè una piccola sottostima in condizioni lente) e, a `degraded`, nelle repliche R1e e R1f (0,189 e 0,204 contro 0,179).
- **Con mTLS il v5 è meglio del v4** (MAE 0,049 contro 0,068) **ma non chiude la sottostima**: la quota misurata supera il v5 di 3-7 punti in tre condizioni su quattro, e la differenza cresce con R (X3 e X4, R = 0,30 s). Solo X2 (R = 0,20 s, perdita 4 %) coincide col v4 (0,219 contro 0,217).
- Parte dell'eccesso è **comune ai due bracci** (anche D è sopra la previsione di 3 punti a R = 0,30 s). L'eccesso proprio di mTLS (C − D misurato contro previsto) vale +0,037, −0,035, +0,032, +0,036: circa 3-4 punti in tre condizioni su quattro.
- A `degraded` (R = 0,4 s) le due repliche del codice finale danno C/10 0,314 e 0,340 contro v4 0,251 e v5 0,280: sottostima del v5 di 3,4-6,0 punti, in linea con X3 e X4. **Il v5 coglie parte del costo di mTLS (il volo del client in un lotto di 3 segmenti, audit 94) ma non tutto; non è escluso che manchino altri elementi (audit 94, limiti).**

## Cosa si può dire nel paper
- Il modello di consegna senza mTLS regge in cinque condizioni sul nodo (X1-X4 e `degraded`).
- Con mTLS il modello **sottostima la quota in ritardo di circa 3-8 punti** (v4: fino a 10,5 punti in X4; v5: fino a 7 punti), crescendo con R; il paper dichiara il limite (frase già presente, audit 89).

## Limiti
Una macchina (nodo virtuale); 50 episodi per cella e una replica per condizione; solo FANOUT 10; la soglia H-N1 (±0,05) è stata fissata prima dei dati e non è stata cambiata.
