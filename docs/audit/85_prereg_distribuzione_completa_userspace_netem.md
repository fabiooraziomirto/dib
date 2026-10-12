# Audit 85 — Pre-registrazione: validazione del modello v4 sulla distribuzione completa (11 container, bridge Docker, mTLS), con un applicatore netem in user space al posto del watcher

Data: 2026-10-12. Contesto: il hook di fine sessione chiede una validazione sulla distribuzione del paper, non solo sul banco. Il watcher v2 (root) è scaduto, ma Docker è usabile senza sudo: un container con `NET_ADMIN` può applicare `tc netem` alla propria `eth0` (è ciò che `netem_apply.sh` fa dall'esterno con `nsenter`). **Setup:** il vero `run.py --block b1` sul cluster a 11 container (evidence + 10 siti, bridge Docker, arm D plain e arm C mTLS) con un file compose in più (`cap_add: NET_ADMIN`, `tc` e librerie dell'host montati in sola lettura, `DIB_M67_EXTRA_COMPOSE`, commit successivo a `3a45868`, tree `467a711`) e `userspace_netem.py` che applica **le stesse specifiche del watcher** (`delay 200ms loss 5%` a `degraded`) con `docker exec -u 0` entro ~2 s dalla creazione dei container. **Verifica di fumo (3 episodi, arm D, nessun dato analizzato):** tutti e 11 i container configurati, `generator path` 202,6/403,2 ms (atteso 200/400, `reused_ok` e `fresh_ok` veri), run completato.

## Cosa cambia rispetto a B5 (audit 56)
Solo chi applica netem (root dall'esterno contro root dentro il container) e il tree (service.py invariato per il percorso misurato: concorrenza 10 e 1 esplicite dal driver; `run.py` con due opzioni spente di default). Stesse soglie P-log di B5 (`plog_thresholds_degraded.json`, p95 2,59 ms, sha256 `a99773b7…`), stesso seme 20261014, 50 episodi per cella, 4 celle (D e C × FANOUT 10 e 1). Nodo con gli stessi carichi di fondo di B5. **Il P-log conta solo le applicazioni del fan-out**: il modello si confronta quindi senza il ramo della riconciliazione.

## Previsioni v4 (calcolate PRIMA dei dati; 20 000 episodi, seme 20261012, R = 0,4 s, perdita 5 %, riconciliazione spenta, richiesta in due segmenti)
| arm | FANOUT | v4 per-site late share (fan-out only) | v4 median last-site ms |
|---|---|---|---|
| D | 10 | 0.179 | 2000 |
| D | 1 | — | 10600 |
| C | 10 | 0.251 | 2800 |
| C | 1 | — | 16400 |

Quota di consegne in ritardo per sito = frazione dei valori P-log per sito (episodi non esclusi) oltre nominale + 0,3 s (nominale 0,6 s D, 1,0 s C). Valori B5 del nodo per confronto (già visti): D/10 0,178, C/10 0,310; mediane dell'ultimo sito D/10 1 639, C/10 2 826, D/1 10 512, C/1 19 069 ms.

## Criteri (fissati ora)
- **H-N1 (equivalenza dell'applicatore):** quota di consegne in ritardo per sito, D/10 e C/10, entro ±4 punti dai valori B5 (0,178 e 0,310). **Falsificata** se uno dei due esce.
- **H-N2 (modello sulla distribuzione):** D/10: quota in ritardo entro ±4 punti da 0,179; **C/10: entro ±8 punti da 0,251** (la sottostima di C di 6 punti è già nota dal confronto retrospettivo con B5 e dichiarata: la handshake TLS ha segmenti non modellati); mediana dell'ultimo sito a FANOUT 1 entro ±25 % da 10 600 (D) e da 16 400 (C).
- **Il modello v4 è "validato sulla distribuzione completa" solo se H-N1 e H-N2 reggono entrambe.** Altrimenti: elenco di ciò che è fuori. Nessuna modifica di previsioni o criteri dopo i dati. Dati in `experiments_tnsm/deploy_run_20261012/`.
