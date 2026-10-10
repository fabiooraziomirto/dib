# TODO: rigenerare i risultati che registrano lo sha256 di `distributed/service.py`

Stato (branch `fix-d12-ack`, 2026-10-10): `scripts/verify_artifact.py` dà **260 passed, 2 failed**. Fallimenti attesi, non errori:

- `ablation source matches packaged service` (`scripts/verify_artifact.py:250-251`) -> `results/restore_ablation/results.json` (`service_sha256` registrato = `d09f8db5…`, hash del file prima del fix)
- `offline veto: service matches packaged distributed service` (`scripts/verify_artifact.py:323-324`) -> `results/offline_veto/results.json` (`service_sha256` registrato = `d09f8db5…`; il file dopo il fix ha `ecb06dd3…`)

Decisione (utente, 2026-10-10): lasciare i due controlli falliti e documentati e **rigenerare i risultati una sola volta**, alla fine di tutte le modifiche a `service.py` (D11 fan-out, mTLS cambieranno di nuovo il file). Rigenerare ora significherebbe rifarlo.

Da fare a fine modifiche (ognuno richiede l'ok dell'utente; nessuno è stato lanciato):

1. `PYTHONPATH=code/src python3 code/scripts/v36_restore_ablation.py --output results/restore_ablation/results.json` (in-process, secondi)
2. `PYTHONPATH=code/src python3 code/scripts/offline_veto_reconciliation.py --trials 10 --output results/offline_veto/results.json` (processi su loopback, pochi minuti)
3. Opzionali, con Docker (build necessario, `service.py` e' copiato nell'immagine): `reconcile_race_experiment.py --trials 20` (1,6 min misurati su codice pre-fix), `fault_injection_experiment.py --trials 10` (claim 26).
4. `python3 scripts/verify_artifact.py` deve dare 266 passed (262 al tag `v43-import`, +4 controlli su `fault_injection` dal commit `062b417`) prima di ogni merge.

Regola: **prima di ogni merge controllare `verify_artifact.py`**; non fare merge in `main` con controlli rossi. Integrazione su un branch dedicato (es. `revision-tnsm`); `main` resta la baseline v43.

## Aggiornamento 2026-10-10 (branch `fix-reconcile-trigger-fanout`)
`service.py` e' cambiato di nuovo (trigger di `/reconcile` e fan-out D11, audit 05): sha256 attuale `f6860bea35baf1ac…` (dopo il fix D12 `ecb06dd3…`; nei risultati `d09f8db5…`). `verify_artifact.py` resta a **260 passed, 2 failed** (gli stessi due). Restano da fare, una volta sola e a fine di tutte le modifiche a `service.py` (mTLS ancora da venire), le stesse rigenerazioni delle voci 1-4 sopra. Per il confronto con il claim 26 generare il compose con `DIB_DIST_RECONCILE_INTERVAL=0` (con il default del compose, T=5, la chiamata esplicita trova `reconciled: 0`).

## Aggiornamento 2026-10-10 (branch `fix-d19`)
`service.py` e' cambiato ancora (anti-entropia D19, osservabilita' del trigger, audit 06): sha256 attuale `48415497997fdfcf…`. `verify_artifact.py` resta **260 passed, 2 failed** (gli stessi due sha256). Le rigenerazioni delle voci 1-4 restano da fare una volta sola, a fine di tutte le modifiche (mTLS ancora da venire).
