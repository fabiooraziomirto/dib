# Audit 129 — Promozione delle nuove evidenze in `results/`, `claims.json`, base del manoscritto

Data 2026-10-13. Autorizzazione dell'utente in sessione: "puoi procedere" sulle richieste aperte dell'audit 128 §7.

## Promozione (niente cancellato)
| Cartella | Ora contiene | Storico conservato in |
|---|---|---|
| `results/restore_ablation/` | `results.json` del rerun su `83d8c99a` + `manifest.json` + README nuovo | `historical_31863043/` (results.json e README originali) |
| `results/offline_veto/` | 30 trial su `83d8c99a` + manifest + README | `historical_31863043/results.json` (10 trial) |
| `results/dispute_flood/` | 5 ripetizioni su `83d8c99a` + manifest (status dai log) + README | `historical_v43_import/` (hash del servizio non registrato) |
| `results/gateway_withdrawal/` (nuova) | riepiloghi, `episodes.csv` e manifest per lan, wan, degraded e smoke | — (dati grezzi in `experiments_tnsm/gateway_withdrawal_20261013/`) |
| `results/site_sweep_management/` (nuova) | celle, per-op, rapporti e manifest per http e mtls | `results/site_count/` e `results/distributed/` restano come storico |

## `claims.json`
- Aggiornate: `restoration_policy_ablation` e `offline_veto_reconciliation` (servizio, numero di trial), `dispute_flood` (valori e file nuovi).
- Marcate `status` historical + `superseded_by`: `distributed_site_count_sweep`, `distributed_throughput`, `openwrt_campaign`.
- Aggiunte: `gateway_withdrawal`, `site_sweep_management`.
- `paper_version` è ancora `v42.0` (campo storico, non toccato).

## Verificatore
`scripts/verify_artifact.py`: **544 passed, 0 failed**. Nessun hash atteso è stato cambiato: i due controlli di provenienza falliti fino all'audit 128 ora passano perché i file in `results/` vengono dal servizio dell'albero. Modifiche motivate:
- il numero di trial dell'offline veto atteso passa da 10 a 30 (evidenza promossa);
- nuovi controlli di uguaglianza con lo storico (ablation: casi identici; offline veto: primi 10 trial identici);
- le soglie storiche del flood restano verificate sul file storico al nuovo percorso.

Suite `code/tests`: 507 passed, 7 skipped, 8 xfailed.

## Manoscritto
`docs/main_10p_rev.tex` diventa la base di lavoro del manoscritto. `main_wip.tex`, `main_10p.tex`, `main.tex` e `main_old.tex` restano invariati (regola dell'utente). Le versioni successive si scrivono su `main_10p_rev.tex`.
