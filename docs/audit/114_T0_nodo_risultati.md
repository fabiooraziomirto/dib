# Audit 114 — Risultati della misura SENZA perdita sul nodo (pre-registrazione: audit 113)

Eseguita il 2026-10-13 sul nodo, `deploy_run.sh` su `tree-88b86a7` (`service.py` sha256 `3ffa57ee…`, hash congelati: 0 differenze), profili `z1` (d = 60 ms, R = 0,12 s) e `z3` (d = 150 ms, R = 0,30 s), perdita 0, arms D e C, FANOUT 10, 30 episodi per cella (300 siti per cella), seme 20261014. z1: 07:24:52Z → 07:31:45Z, z3: 07:31:47Z → 07:42:42Z, `rc=0`, nessun container residuo (`containers_left.txt` vuoto). **H-G:** `image_service_sha256` = `3ffa57ee…` in tutti i 11 container di tutte le celle (cells.jsonl, entrambi i profili). Dati: `experiments_tnsm/node_t0_20261013/` (copiati dal nodo senza chiavi; `SHA256SUMS`). Comandi sul nodo: `experiments_tnsm/node_session_20261011/node_commands.txt`. Analisi: `experiments_tnsm/node_session_20261011/analyze_lossless.py` (output sotto).

## Risultato
| profilo | R (s) | braccio | episodi | esclusi | quota in ritardo | spostamento mediano rispetto al nominale (ms) | siti |
|---|---|---|---|---|---|---|---|
| z1 | 0,12 | D | 30 | 0 | 0,000 | +18,9 | 300 |
| z1 | 0,12 | C | 30 | 0 | 0,000 | +21,7 | 300 |
| z3 | 0,30 | D | 30 | 0 | 0,000 | +19,4 | 300 |
| z3 | 0,30 | C | 30 | 0 | 0,000 | +23,3 | 300 |

## Verdetto (meccanico, soglia dell'audit 113)
**H-Z1 regge:** la quota in ritardo senza perdita è 0,000 in tutte e quattro le celle (soglia 0,02). Lo spostamento mediano rispetto al nominale è 19-23 ms, e la differenza C − D è 2-4 ms, cioè molto sotto la soglia di "in ritardo" (0,75 R = 90 ms a z1, 225 ms a z3).

## Cosa ne segue (come pre-registrato)
- Un effetto di CPU o di tempi lato mTLS **indipendente dalla perdita non spiega** il pacchetto efficace mancante (≈ 7,6 misurato contro 7 del v5): senza perdita nessuna consegna, né con né senza mTLS, supera la soglia.
- Resta aperta la spiegazione nella struttura dei pacchetti con mTLS. Prossima misura prevista dall'audit 113: cattura dentro i container (da pre-registrare prima di eseguirla).
- Il paper continua a dichiarare il limite (il modello sottostima la quota in ritardo con mTLS di 3-8 punti).

## Limiti
Una macchina (nodo virtuale), 30 episodi per cella, una replica; senza perdita non si misurano gli effetti della ritrasmissione.
