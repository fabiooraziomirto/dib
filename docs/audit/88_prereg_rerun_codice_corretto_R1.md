# Audit 88 — Pre-registrazione R1: deployment completo sul codice corretto (`tnsm-fixes`)

Scritta e committata PRIMA del lancio (2026-10-12, nodo ~06:40Z). Piano: `docs/audit/87_review_service_e_piano_rerun.md` sez. 3-4. Decisione dell'utente: rieseguire i test se le correzioni sono fondamentali, tetto 48 h.

Codice: albero `~/dib_tnsm/tree-dc3dd20` (git archive del commit `dc3dd20` di `tnsm-fixes`), `frozen_hashes_dc3dd20.txt` (24 file, `sha256sum -c` 0 differenze; `service.py` `5599f53b…129be`). Albero precedente `tree-467a711` intatto.
Run: identico a audit 85/86: `deploy_run.sh` (applicatore netem in user space), `run.py b1 degraded`, arms D e C × FANOUT 10 e 1, 50 episodi, seed 20261014, soglie P-log di B5 riusate, keep-alive e DNS-nosearch spenti, quorum default 1. Nessun altro carico sul nodo (auto_degraded_k.py fermato, PID 3793084).

## Ipotesi (criteri e previsioni invariati rispetto ad audit 85, nessuna modifica dopo i dati)
- **H-R1a (modello sul codice corretto):** H-N1 e H-N2 di audit 85:19-20 reggono con `analyze_deploy.py` (stessi codice e soglie: D/10 entro ±4 punti da 0,178/0,179; C/10 entro ±4 da 0,310 per H-N1 e ±8 da 0,251 per H-N2; mediana ultimo sito a FANOUT 1 entro ±25 % da 10 600 e 16 400).
- **H-R1b (nessuna regressione):** per ognuna delle quattro celle la differenza fra codice nuovo (R1) e vecchio (audit 86) è entro 4 punti nella quota in ritardo (D/10, C/10) e entro 15 % nella mediana dell'ultimo sito (D/1, C/1). Scelta prima dei dati: la review non prevede alcun effetto delle correzioni sul percorso misurato (audit 87 sez. 1), quindi la differenza attesa è solo rumore fra repliche.
- **Falsificazione:** H-R1a cade se uno dei criteri esce; H-R1b cade se una cella esce dalla soglia. Se cade H-R1b si riporta la differenza com'è e si indaga prima di proseguire con R2-R6; non si ritoccano soglie né previsioni.

## Limiti dichiarati prima
Una macchina, 50 episodi per cella, `degraded` soltanto; le due repliche (R1 e audit 86) sono sullo stesso nodo e a ore diverse: la differenza fra repliche non è un test indipendente.
