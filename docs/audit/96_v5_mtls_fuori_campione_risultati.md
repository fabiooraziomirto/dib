# Audit 96 — Validazione fuori campione del modello v5 (mTLS) nel banco locale: verdetti dell'audit 95

Pre-registrazione: `docs/audit/95_prereg_v5_mtls_fuori_campione.md` (458e872) con l'addendum sul criterio di macchina quieta (469e6df, committato prima di ogni dato). Dati: `experiments_tnsm/mtls_model/val_final_20261012/{eq_C,eq_D,oos_C,oos_D}` (manifest con sha256, seme, versione di Python, CPU inattiva all'avvio e assenza di TLC). Analisi: `experiments_tnsm/netns_testbed/analyze_mtls.py` (6 test, scritti prima), soglie e previsioni non cambiate dopo i dati.
Condizioni di esecuzione: macchina locale (16 core) senza TLC (l'altra sessione l'aveva fermato), CPU inattiva all'avvio ≈ 0,89 (regola dell'addendum), `service.py` `3ffa57ee…`, Python 3.10.13, 4 worker per lancio, avvio 16:58:50Z, fine 19:21:11Z, rc=0 per tutti e quattro i lanci.

## Tabella (analyze_mtls.py)
| prova | braccio | R (s) | episodi validi | quota in ritardo | IC 95 % | previsione | |
|---|---|---|---|---|---|---|---|
| EQ | D | 0,4 | 100 | 0.172 | [0.151; 0.194] | 0.176 | H-V3a regge |
| EQ | C | 0,4 | 100 | 0.249 | [0.224; 0.273] | 0.309 | H-V3b CADE |
| X1 | C | 0.12 | 200 | 0.325 | [0.306; 0.344] | v4 0.307, v5 0.348 | |
| X1 | D | 0.12 | 200 | 0.212 | [0.194; 0.230] | 0.217 | |
| X2 | C | 0.2 | 200 | 0.219 | [0.202; 0.235] | v4 0.217, v5 0.248 | |
| X2 | D | 0.2 | 200 | 0.153 | [0.138; 0.168] | 0.15 | |
| X3 | C | 0.3 | 200 | 0.318 | [0.296; 0.339] | v4 0.288, v5 0.319 | |
| X3 | D | 0.3 | 200 | 0.191 | [0.173; 0.209] | 0.21 | |
| X4 | C | 0.3 | 200 | 0.402 | [0.381; 0.422] | v4 0.353, v5 0.388 | |
| X4 | D | 0.3 | 200 | 0.264 | [0.244; 0.283] | 0.265 | |


T-0 (senza perdita) valido in tutti i ritardi e in tutti e due i bracci. C/1 e D/1 (descrittivi, 60 episodi per X1 e X2): C 4 794 e 5 205 ms contro previsioni v4/v5 5 900/5 980 e 7 700/8 100; D 3 787 e 4 292 ms contro 4 060 e 5 100.

## Verdetti come pre-registrati
- **H-V3a (equivalenza D, `degraded`):** REGGE. 0,172 contro 0,176 ±0,04.
- **H-V3b (equivalenza C, `degraded`):** **CADE.** 0,249 [0,224; 0,273] contro 0,309 ±0,05 (scarto −0,060). → H-V3 cade: **il banco con mTLS non riproduce il nodo**.
- **H-V0 (controllo D nelle quattro condizioni):** REGGE (scarti da −0,018 a +0,003, soglia ±0,04).
- **H-V1 (|C − v5| ≤ 0,04 in ogni condizione):** REGGE. Scarti −0,023 (X1), −0,029 (X2), −0,002 (X3), +0,014 (X4).
- **H-V2 (|ε5| ≤ 0,02 e ε4 > 0,02):** REGGE. ε5 = −0,010, ε4 = +0,0245.
- **Esito pre-registrato per il paper: `not_confirmed`** (la riga della tabella dell'audit 95: "H-V1 cade, oppure H-V3 cade ⇒ il limite con mTLS resta"). **Il paper non cambia.**

## Lettura (dichiarata come tale: non cambia l'esito)
- Nel banco, in quattro condizioni mai usate, il v5 prevede la quota in ritardo con mTLS entro 2,9 punti e il v4 sottostima in 3 condizioni su 4 (fino a 4,9 punti in X4). Il v5 è quindi **coerente col banco**.
- L'equivalenza col nodo cade proprio con mTLS: a `degraded` il banco dà 0,249 (≈ v4, 0,251) mentre il nodo dà 0,282-0,335 (R1e 0,314). Il braccio D combacia (banco 0,172, nodo 0,176-0,189), quindi la differenza è specifica di mTLS. Le cause candidate non verificate sono la CPU di TLS sul nodo (QEMU senza AVX2), le versioni (Python 3.12 e OpenSSL del container contro 3.10 del banco) e la topologia di rete (netem sull'uscita di ogni container, bridge e DNS di Docker contro un solo netem su `lo`). Il banco non permette di separarle.
- Nel banco il v5 non è nemmeno nettamente migliore del v4 a `degraded` (0,249 misurato contro 0,251 e 0,280); lo è nelle altre condizioni.

## Cosa NON si può dire
- Che il v5 sia validato sul nodo: nessun dato del nodo in queste condizioni; le tre repliche del nodo (0,282-0,335 e R1e) sono in campione.
- Che il banco con mTLS sia equivalente al nodo.

## Opzioni (decisione dell'utente)
1. Chiudere qui: il v5 vale solo per il banco, il paper tiene il limite (costo zero).
2. Il banco eseguito sul nodo, 20-30 min: separa la macchina dalle versioni e dalla topologia.
3. Le condizioni X1-X4 sul deployment vero (profili nuovi in `run.py` e nell'applicatore, ~1-2 h di preparazione e 2-3 h di nodo): l'unica che valida sul sistema di riferimento.
