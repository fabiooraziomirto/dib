# Audit 128 — Riepilogo delle campagne finali (13 ottobre 2026)

Branch `tnsm-final-campaigns` (worktree `/root/Desktop/DIB_tnsm_final`), creato da `tnsm-merged` @ `2f58f8f`. Contiene il merge di `tnsm-g3fix`. Nessun push. `tnsm-merged`, `main`, `docs/main_wip.tex`, `docs/main_10p.tex`, `formal/`, `results/` e `claims.json` non sono stati toccati.

## 1. Versione valutata
- `service.py` **`83d8c99a…`** = `3ffa57ee…` + la guardia su `target_state` (audit 126, decisione dell'utente). È l'unica modifica a `code/src`.
- `mtls.py` `4833dae3…`. Dockerfile e compose non cambiati.
- Suite `code/tests`: 507 passed, 7 skipped, 8 xfailed, prima e dopo la guardia.

| Evidenza | Servizio misurato (verificato dove) |
|---|---|
| Restoration ablation + offline veto | `3ffa57ee` (audit 120) e `83d8c99a` (audit 126), sha del modulo effettivamente caricato; trace identiche |
| Gateway t0–t3, 210 episodi | `3ffa57ee`, nei 11 container a inizio e fine di ogni profilo (audit 122) |
| Smoke gateway, 15 episodi | `83d8c99a`, nei container (audit 127 §1) |
| Sweep dei siti http/mtls, dispute flood | `83d8c99a`, nei container a inizio e fine di ogni topologia (audit 127) |
| B2k, R1e, R1f (campagne del nodo, non rieseguite) | `3ffa57ee`, nei container (audit 125) |

## 2. Esiti
| Domanda | Esito |
|---|---|
| A1–A7 lifecycle: nessun export senza fresh commit; veto preservato; Active stantio invalidato; fatto estraneo; idempotenza; replay; commit sopra il veto | **confermati** (casi controllati: 18 + 30 trial, su entrambe le versioni) |
| H-G1 withdrawal effettivo al gateway | **confermato** (210/210) |
| H-G2 fan-out sincrono (t1 prima della risposta al dispute) | **confermato**, in tutti i profili |
| H-G3 connessioni stabilite non interrotte | **confermato** (210/210): è un **limite** del gateway (conntrack) |
| H-G4 il flusso di controllo si ferma solo durante i reload (~5,1 s per reload) | **confermato**: costo collaterale del reload per restart |
| H-G5 recovery: restore da solo non riabilita, fresh commit sì, veto sopravvive | **confermato** (200/200, veto 10/10) |
| H-G6 latenze LAN previste | **confermato** |
| H-G6 degraded: t1 via reconcile | **falsificato** quanto al meccanismo (fan-out sempre consegnato dentro `/dispute`); la soglia numerica regge |
| H-S2 la distribuzione aumenta il throughput tentato (W ≥ 50) | **confermato** (http 1,9–2,5×, mtls 1,5–1,7×, IC > 1) |
| H-S4 attribuzione del collo di bottiglia | **inconclusivo**: le celle più cariche sono limitate dal generatore di carico. Il claim storico "evidence service bottleneck" non è sostenuto |
| H-D1, H-D2 dispute flood | **confermati** (5/5) |
| G3 del paper ("un evidence difettoso non rende esportabile un fatto") | **falso su `3ffa57ee`** (audit 124), **vero su `83d8c99a`** (test dedicato) |
| Pilot gateway, tentativo mtls 1 dello sweep | non conteggiati (esplorativo; guasto del harness prima dei dati), conservati |
| Banco netns, B2k, R1e/R1f, TLC | **non rieseguiti** (validi e tracciabili; cambia solo come vanno descritti) |
| Modello di costo TCP/TLS | **non esteso** (come richiesto). La sottostima con mTLS resta dichiarata |

## 3. Risultati storici sostituiti (i file restano dove sono)
| Storico | Sostituito da | Motivo |
|---|---|---|
| `results/restore_ablation/results.json` | `experiments_tnsm/lifecycle_rerun_20261013_g3fix/restore_ablation.json` | servizio `31863043` |
| `results/offline_veto/results.json` | `…_g3fix/offline_veto.json` (30 trial) | servizio `31863043` |
| `results/openwrt/campaign-10runs` (come evidenza del paper) | `experiments_tnsm/gateway_withdrawal_20261013/` | registro in-process, nessun tempo, nessun hash |
| `results/site_count/*`, `results/distributed/*` | `experiments_tnsm/site_sweep_20261013/` | servizio `54f635cb`, `contribute` no-op, nessuna classificazione delle risposte |
| `results/dispute_flood/` | `experiments_tnsm/dispute_flood_20261013/` | nessun hash, servizio pre-import |
Promuovere i nuovi file in `results/` e aggiornare `claims.json` richiede l'OK dell'utente. Dopo la promozione i 2 controlli storici del verificatore diventano verdi senza cambiare alcun hash atteso.

## 4. Verificatore
`scripts/verify_artifact.py`: **400 passed, 2 failed**. I 2 falliti sono i controlli storici, mantenuti con lo stesso hash atteso ed etichettati "superseded". Blocchi nuovi:
- rerun lifecycle su `83d8c99a` (contro l'albero) e su `3ffa57ee` (solo coerenza interna);
- gateway: provenienza nei container, conteggi delle ipotesi, mediane t1/t2/t3;
- sweep e flood: provenienza, numero di richieste, errori, rapporti, conteggi H-D1.

## 5. Riproduzione (dalla radice del worktree; Python `/opt/conda/envs/dib312/bin/python`)
```sh
PY=/opt/conda/envs/dib312/bin/python
$PY experiments_tnsm/lifecycle_rerun_20261013/run.py --python $PY --out <dir>       # ~1 min
experiments_tnsm/gateway_withdrawal_20261013/run_campaigns.sh <pki_dir_fuori_repo> 50   # ~2 h 35 min, root + Docker
$PY experiments_tnsm/site_sweep_20261013/sweep.py --out <dir> --transport http          # ~13 min
$PY experiments_tnsm/site_sweep_20261013/sweep.py --out <dir> --transport mtls --pki <pki_dir>
(cd experiments_tnsm/dispute_flood_20261013 && $PY flood_run.py 5)                       # ~5 min
python3 experiments_tnsm/gateway_withdrawal_20261013/analyze.py <runs...> --out <dir>
python3 experiments_tnsm/site_sweep_20261013/analyze.py <runs...> --out <dir>
python3 scripts/verify_artifact.py
```
Hardware: LXC su Proxmox, AMD EPYC 7313, 16 core, 64 GiB; Docker 28.2.2. Host condiviso con altri progetti (load average 7–15 registrato per episodio o ripetizione).

## 6. Manoscritto
`docs/main_10p_rev.tex` (nuovo; 10 pagine con pdflatex; diff parola per parola in `docs/work/main_10p_rev.wdiff`). Interviene su metodi, risultati e limiti; l'architettura non è riscritta.
- Righe M3–M6 rinumerate come `formal/mutations`.
- G3 con la guardia.
- Model checking: configurazioni separate e "bounded".
- B2k: definizione di k, recovery dopo restart, esclusioni 5+1, 16 retry.
- Paragrafo gateway e metodo gateway.
- Placeholder del flood riempito con le misure.
- Placeholder del modello di autorizzazione sostituito con il suo perimetro.
- Frase falsa sul local revoke corretta.
- Claim sul collo di bottiglia rimosso.
- Numeri della ranked union.
- Una frase su mTLS nell'implementazione.

Raccomandato ma **non fatto per spazio**: nella didascalia di Tab. `tab:netem`, il numero di episodi senza consegna pendente (35–48 su 50), i massimi per episodio (fino a 28,1 s per C/1) e i retry di setup (R1e 38, R1f 26) (audit 125 §5).
Da correggere fuori dal paper: `docs/work/evidence_map_10p.md:32` (`3ffa57ee` è del commit `864101f`, non `dc3dd20`); il commento `service.py:194`/`:803` su `/health` (codice: serve l'OK); `formal/distributed/DIB_Distributed.cfg:1` (il commento dice 2 fatti, la configurazione ne ha 1).

## 7. Richieste aperte all'utente
1. OK per promuovere le nuove evidenze in `results/` e aggiornare `claims.json`.
2. OK per il merge di `tnsm-final-campaigns` in `tnsm-merged` (nessun conflitto previsto: branch lineare da `2f58f8f`).
3. Decidere se `main_10p_rev.tex` diventa la base del manoscritto (`main_wip (1).tex` non era nel workspace).
4. Eventuale benchmark con un mix di lifecycle per fatto (commit che cambiano stato): non pre-registrato e non eseguito (audit 127 §2).
