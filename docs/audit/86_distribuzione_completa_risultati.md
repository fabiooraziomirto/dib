# Audit 86 — Distribuzione completa (11 container, mTLS, netem in user space): risultati

Pre-registrazione: `docs/audit/85_prereg_distribuzione_completa_userspace_netem.md:19-21` (previsioni e criteri fissati prima del run, nessuna modifica dopo i dati).
Dati: `experiments_tnsm/deploy_run_20261012/` (copiati dal nodo con controllo sha256 su tutti i file tranne i pcap, 0 differenze; `b1/cells.jsonl`, `episodes.jsonl`, `manifest.json`). Analisi: `experiments_tnsm/node_session_20261011/analyze_deploy.py` (2 test verdi, commit 4f820ef).
Run: 2026-10-12T05:12:08Z → 06:33:36Z, `run.py b1 degraded`, arms D e C × FANOUT 10 e 1, 50 episodi per cella, seed 20261014, keep-alive spento, `dns_nosearch` spento, applicatore netem in user space (`userspace_netem.py`) invece del watcher root (scaduto). Codice del nodo: albero congelato `467a711`, quindi PRIMA delle correzioni FSM di `tnsm-fixes` (audit 87).

| arm | FANOUT | episodi | esclusi | quota in ritardo per sito (previsione v4) | mediana ultimo sito ms [n] (previsione v4) |
|---|---|---|---|---|---|
| D | 10 | 50 | 0 | 0.186 (0.179) | 1620 [47] (—) |
| D | 1 | 50 | 0 | — | 10670 [46] (10600.0) |
| C | 10 | 50 | 1 | 0.282 (0.251) | 2684 [34] (—) |
| C | 1 | 50 | 1 | — | 16126 [32] (16400.0) |

## Verdetti

- **H-N1 (applicatore equivalente a B5):** regge (D/10 0.186 contro 0,178; C/10 0.282 contro 0,310; tolleranza ±0,04).
- **H-N2 (modello):** regge (D/10 contro 0,179 ±0,04; C/10 contro 0,251 ±0,08; F1 D 10670 contro 10 600, C 16126 contro 16 400, ±25 %).
- **Modello v4 validato sulla distribuzione completa: SÌ.**

## Cosa i criteri non coprivano (stessi dati, nessun criterio nuovo)

- Mediana dell'ultimo sito a FANOUT 10: D 1620 ms (previsione v4 di audit 85: 2000; −19 %), C 2684 ms (previsione 2800; −4 %). La previsione a FANOUT 10 non aveva un criterio e non entra nel verdetto. D è sovrastimata dal modello, quindi il modello è prudente su quel punto.
- Episodi esclusi: 0 in D/10 e D/50-1, 1 in C/10 e 1 in C/1 (criteri di esclusione di `run.py`, non decisi dopo i dati). Le mediane dell'ultimo sito usano solo gli episodi completi (n indicato fra parentesi quadre in tabella: 47, 46, 34, 32). In C il numero di episodi completi è basso (34 e 32 su 49): la mediana è meno solida che in D.
- Scarto di C/10 rispetto al modello: +3,1 punti (0,282 contro 0,251), dentro i ±8 dichiarati; il modello continua a sottostimare C per i segmenti della handshake TLS non modellati, come già noto da B5.

## Limiti

- Una sola macchina (il nodo), nessun confronto fra macchine; 50 episodi per cella; profilo `degraded` soltanto (non `lossy`, non `lan`).
- Il netem è applicato in user space (docker exec) e non dal watcher root: l'equivalenza con B5 è stata verificata da H-N1 solo sulle quote D/10 e C/10.
- Codice pre-correzione FSM; il percorso misurato (POST /dispute + fan-out + P-log) non è toccato dalle correzioni secondo la review (audit 87), ma il rerun sul codice corretto lo conferma o lo smentisce.
