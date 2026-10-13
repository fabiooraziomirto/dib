# Audit 120 — Rerun di restoration ablation e offline veto sul servizio di riferimento: risultati

Data 2026-10-13. Pre-registrazione: audit 119 sez. 4 (commit `2db1904`, prima del lancio). Dati: `experiments_tnsm/lifecycle_rerun_20261013/` (`manifest.json`, `restore_ablation.json`, `offline_veto.json`, log, `summary.json`, `table.md`).

## Provenienza
- Commit al lancio `2db1904` (albero pulito). `service.py` `3ffa57ee…` sia nel file caricato da TestClient (ablation) sia nell'origine del modulo dei sottoprocessi uvicorn (`find_spec` = `code/src/dib/registry/distributed/service.py`, stesso sha) — `manifest.json`.
- Generatori invariati: `v36_restore_ablation.py` `8387487e…`, `offline_veto_reconciliation.py` `ae9fc143…` (= storici).
- Python 3.12.15; host con load average ~10 (altri progetti). Nessuna misura di tempo è usata.
- sha256 dei risultati: `restore_ablation.json` `8fa17cba5a8d2044b149137829b15b1178365419ca9d497bb5f1daa8f87477cb`; `offline_veto.json` `42e8f29a8239451483c723292b2e5a8f229f05235c17786e50a7736fcc15b678`.
- Esecuzione: 1 tentativo per generatore, entrambi rc 0 (ablation 8.2 s, offline veto 45.0 s). Nessuna esclusione, nessun retry.

## Esiti (casi controllati, non stime)

| Politica | ACE del soggetto senza fresh commit (18 opportunità sito-caso) | Veti preservati (6) | Fatto di controllo |
|---|---|---|---|
| Persistent approval | 12/18 | 6/6 | esportato in ogni passo |
| Blanket review reset | 0/18 | **0/6** | esportato in ogni passo |
| DIB | **0/18** | **6/6** | esportato in ogni passo |

Offline veto, 30 trial con kill/restart del sito che detiene il veto e due episodi completi persi: veto `revoked/local` dopo il restart 30/30; Active stantio → `monitor-only` 30/30; né il fatto vetato né quello stantio esportano 30/30; fatto estraneo esportato da tutti i siti 30/30; secondo `/reconcile` = 0 elementi 30/30; replay di un evento con seq 1 senza effetto 30/30; `/commit` sul fatto vetato → 409 30/30; recovery esplicita (local restore + commit) 30/30.

| Criterio (audit 119) | Esito |
|---|---|
| A1 nessun export dopo dispute/restore senza fresh commit (DIB) | **regge** (0/18) |
| A2 veto locale preservato | **regge** (DIB 6/6; offline 30/30); review reset lo perde (0/6), come atteso |
| A3 Active invalidato dopo episodio interamente perso | **regge** (offline 30/30; site-2 disconnesso esporta 0 in tutti i casi DIB) |
| A4 fatto estraneo esportabile | **regge** (ogni passo, 30/30) |
| A5 reconcile idempotente | **regge** |
| A6 replay obsoleto senza effetto | **regge** |
| A7 veto non aggirabile con commit diretto | **regge** (409 30/30; `/local_restore` durante l'episodio 409 in 18/18) |
| Provenienza | **regge** |

**Confronto con le evidenze storiche.** I 18 casi dell'ablation sono identici campo per campo a `results/restore_ablation/results.json`; i primi 10 trial dell'offline veto sono identici a `results/offline_veto/results.json`. Cambiano solo `service_sha256` e `python`. Quindi le modifiche FSM a `/query`, `/commit` e `/local_restore` (dopo `31863043…`) non cambiano nessuna traccia di questi casi.

## Verificatore
`scripts/verify_artifact.py`: nuovo blocco `check_lifecycle_rerun_20261013` (30 controlli: hash del servizio nel JSON e nel modulo caricato, hash dei generatori e dei risultati, conteggi ricalcolati dalle trace). Esito: **292 passed, 2 failed**. I due falliti sono i controlli storici (`results/` prodotto da `31863043…`), **mantenuti con lo stesso hash atteso**; ora il verificatore stampa accanto a ciascuno il puntatore all'evidenza che lo sostituisce. Diventano verdi solo promuovendo i nuovi file in `results/` (operazione che richiede l'OK dell'utente; proposta in audit finale).

Test dell'analisi: `experiments_tnsm/lifecycle_rerun_20261013/test_analyze.py`, 5 passed (inclusi 4 casi mutati che devono fallire).

## Testo per il paper
"On the evaluated service version (sha256 `3ffa57ee…`), the 18 controlled restoration cases and 30 offline-veto trials reproduce the earlier traces exactly: under DIB no subject ACE is exported after restore before a fresh local commit (0/18 site-case opportunities, against 12/18 for persistent approval), every local veto survives (6/6, and 30/30 after a process restart), and the unrelated fact remains exported throughout." Sono conteggi di casi controllati, da non presentare come affidabilità.
