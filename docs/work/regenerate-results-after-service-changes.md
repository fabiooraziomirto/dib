# TODO: rigenerare i risultati che registrano lo sha256 di `distributed/service.py`

Stato (branch `fix-d12-ack`, 2026-10-10): `scripts/verify_artifact.py` dà **260 passed, 2 failed**. Fallimenti attesi, non errori:

- `ablation source matches packaged service` (`scripts/verify_artifact.py:250-251`) -> `results/restore_ablation/results.json` (`service_sha256` registrato = `d09f8db5…`, hash del file prima del fix)
- `offline veto: service matches packaged distributed service` (`scripts/verify_artifact.py:323-324`) -> `results/offline_veto/results.json` (`service_sha256` registrato = `d09f8db5…`; il file dopo il fix ha `ecb06dd3…`)

Decisione (utente, 2026-10-10): lasciare i due controlli falliti e documentati e **rigenerare i risultati una sola volta**, alla fine di tutte le modifiche a `service.py` (D11 fan-out, mTLS cambieranno di nuovo il file). Rigenerare ora significherebbe rifarlo.

Da fare a fine modifiche (ognuno richiede l'ok dell'utente; nessuno è stato lanciato):

1. `PYTHONPATH=code/src python3 code/scripts/v36_restore_ablation.py --output results/restore_ablation/results.json` (in-process, secondi)
2. `PYTHONPATH=code/src python3 code/scripts/offline_veto_reconciliation.py --trials 10 --output results/offline_veto/results.json` (processi su loopback, pochi minuti)
3. Opzionali, con Docker (build necessario, `service.py` e' copiato nell'immagine): `reconcile_race_experiment.py --trials 20` (1,6 min misurati su codice pre-fix), `fault_injection_experiment.py --trials 10` (claim 26).
4. `python3 scripts/verify_artifact.py` deve tornare a 262 passed prima di ogni merge.

Regola: **prima di ogni merge controllare `verify_artifact.py`**; non fare merge in `main` con controlli rossi. Integrazione su un branch dedicato (es. `revision-tnsm`); `main` resta la baseline v43.
