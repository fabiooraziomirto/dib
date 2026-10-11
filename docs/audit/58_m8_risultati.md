# Audit 58 — Risultati di M8: costo di firma e verifica MUD con `openssl cms` (audit 55)

Data: 2026-10-11. Dati: `experiments_tnsm/m8_mud_sig/run_20261011/result/{aggregates.json,manifest.json}` (misura sul nodo `ubuntu@192.168.100.57`, 21:30:16-21:30:32Z, dopo la fine di B5 e B2k come da audit 55; Python 3.12.3, OpenSSL 3.0.13, CPU `QEMU Virtual CPU version 2.5+`; `run.py` sha256 `8170e461…e7365` identico alla copia in repo; file MUD 5/20/100 ACE da `export_mud_file` con `last-update` fissato, sha256 in `run_20261011/result/manifest.json`; 10 ripetizioni × 20 coppie per cella, 5 di riscaldamento scartate, ordine delle celle mescolato con seme 20261011). Ipotesi e regole: audit 55 (committato prima del codice). Test del codice: `experiments_tnsm/m8_mud_sig/test_run.py` (6 passed, mutazioni catturate).

## Validità
Tutte le 6 celle valide: ogni verify di firma corretta è riuscito e il verify su file alterato di un byte è fallito (controllo negativo, 5 per cella). Carico del nodo: loadavg a 1 min 0,34 prima e 0,48 dopo; steal trascurabile (8 tick su ~24 000 durante la misura). Nodo con altri carichi di fondo (k3s, `wasmbed-registry`): i tempi non sono confrontabili con altre macchine.

## Risultato (sign + verify con spawn, ms; 200 coppie per cella)
| algoritmo | ACE | mediana [IC 95%] | p95 [IC 95%] | sign (mediana) | verify (mediana) | spawn `openssl version` (mediana) | firma (byte) | H-M8 |
|---|---|---|---|---|---|---|---|---|
| ECDSA P-256 | 5 | 6,76 [6,66; 6,85] | 9,52 [8,56; 9,97] | 3,85 | 2,81 | 1,64 | 826 | non falsificata |
| ECDSA P-256 | 20 | 6,78 [6,74; 6,88] | 9,15 [8,66; 9,88] | 3,89 | 2,83 | 1,64 | 826 | non falsificata |
| ECDSA P-256 | 100 | 6,99 [6,93; 7,12] | 10,02 [9,48; 10,66] | 3,98 | 2,96 | 1,65 | 826 | **inconclusiva** (p95 > 10 ma l'IC attraversa) |
| RSA-2048 | 5 | 8,00 [7,89; 8,11] | 11,17 [10,40; 11,86] | 5,15 | 2,78 | 1,68 | 1413 | **falsificata** |
| RSA-2048 | 20 | 8,24 [8,08; 8,47] | 12,01 [11,30; 12,98] | 5,22 | 2,89 | 1,73 | 1413 | **falsificata** |
| RSA-2048 | 100 | 8,10 [8,04; 8,19] | 10,84 [10,22; 11,28] | 5,18 | 2,85 | 1,64 | 1413 | **falsificata** |

**Verdetto globale pre-registrato: H-M8 falsificata, 3/6 celle** (tutte e tre le celle RSA-2048). Con ECDSA P-256: non falsificata a 5 e 20 ACE, inconclusiva a 100.

## Lettura (descrittiva)
- **Il costo è dominato dal processo, non dalla taglia del file:** la mediana varia di pochi decimi di ms passando da 5 a 100 ACE (6,76 → 6,99 ms con ECDSA); il riferimento di spawn (`openssl version`) è 1,6-1,7 ms per processo, cioè circa 3,3 ms dei 7-8 ms sono avvio dei due processi. Tolto lo spawn, sign + verify resta circa 3,5 ms con ECDSA e 5 ms con RSA. **Questo è un'osservazione, non un criterio:** il criterio registrato (10 ms con spawn) vale per il totale.
- **ECDSA è più economico di RSA-2048 di circa 1,2-1,3 ms in mediana e 1,3-2,9 ms al p95**; la firma ECDSA è più piccola (826 contro 1413 byte).
- **Il p95 è vicino al limite anche con ECDSA** (9,2-10,0 ms): il 10 ms di a04:78 è una soglia stretta per la CLI su questo nodo, non un margine largo.
- **Nessuna conclusione sulla sicurezza né sull'integrazione:** le esportazioni del paper restano non firmate (`wip:503`, `wip:782`); M8 dà solo il costo di una firma CMS staccata (SHA-256) sul percorso di export, misurato con la CLI (non in-process: `cryptography` non è installato sul nodo e non l'ho installato).

## Cosa dire nel paper (se serve)
"Firma e verifica di un file MUD con `openssl cms` costano 6,8-7,0 ms (ECDSA P-256) e 8,0-8,2 ms (RSA-2048) in mediana, con p95 9,2-10,0 e 10,8-12,0 ms, su un nodo QEMU condiviso; di questi circa 3,3 ms sono l'avvio dei due processi." L'ipotesi M8 "< 10 ms al p95" è falsificata per RSA-2048.
