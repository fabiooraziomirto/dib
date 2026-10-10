# fault_injection: riconciliazione dopo un'interruzione di un sito

Dati rigenerati il 2026-10-10 sul `service.py` congelato (sha256 `3186304363ed309241134752689423088dda98b9d8fe3bcdf9669749264398fd`).
Sostituiscono i dati prodotti il 2026-09-05, che non avevano manifest né README e restano nella storia git (commit `bd3080b`, import v43; `git show bd3080b:results/fault_injection/results.csv`). I vecchi valori (evento singolo 0,512 s, episodio intero 0,496 s, riconciliazione max 0,0755 s) non sono confrontabili: cambiano `service.py` (`d09f8db5…` → `3186304363ed…`), host e Python.

- Script: `code/scripts/fault_injection_experiment.py --trials 10`, 4 scenari x 10 prove = 40.
- Host: nodo 192.168.100.57 (Ubuntu 24.04 KVM), Docker Compose (client snap 29.8.0, Compose v5.5.1), progetto `dibtnsm`, 10 siti + evidence, `DIB_DIST_FANOUT_CONCURRENCY=8`, trigger di riconciliazione spento, `/reconcile` chiamato dallo script.
- Codice: albero `~/dib_tnsm/tree-c23d1e3` sul nodo; commit del run `c23d1e34c2dc4c731e49980c743b59760b1f09e0` (`git diff c23d1e3 HEAD -- code` vuoto al momento del run). Python: venv del nodo con le versioni di dib312 (3.12).
- Immagini: ID in `experiments_tnsm/g0b_regen/compose_images.json`. Durata 1m37s. Log: `experiments_tnsm/g0b_regen/fault_injection.log`.
- Origine: `experiments_tnsm/g0b_regen/{fault_injection_results.csv,trials.csv}` (copie byte per byte); descrizione in `docs/audit/15_g0b_rigenerazione.md`.

Valori (media ± sd): evento singolo 0,480 ± 0,017 s (30 prove); episodio intero 0,509 ± 0,034 s (10); riavvio 0,416 s (media 40 prove); riconciliazione media 0,071 s, massimo 0,105 s. Ipotesi e criterio: nessuno pre-registrato per questa rigenerazione (rilancio di verifica); i tempi sono descrittivi.
