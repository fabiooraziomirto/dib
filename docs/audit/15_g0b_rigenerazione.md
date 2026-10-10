# Audit 15 — G0b: rigenerazione unica dopo il freeze di `service.py` (Passo 2)

Data: 2026-10-10. Branch `revision-tnsm`. `service.py` congelato a sha256 `3186304363ed…` (audit 14 §2).

Le voci 1-4 di `docs/work/regenerate-results-after-service-changes.md` sono state eseguite con l'output in `experiments_tnsm/g0b_regen/`. **`results/` non è stato toccato.** La copia attende il tuo OK. `verify_artifact.py` resta a **260 passed e 2 failed**: sono i due controlli sull'hash di `service.py` (`scripts/verify_artifact.py:250,323`), che passeranno solo dopo la copia.

## 1. Esecuzione

| Voce | Comando | Dove | Durata | File |
|---|---|---|---|---|
| 1 | `code/scripts/v36_restore_ablation.py --output …` | questo host, in-process, Python 3.12.15 | 7,5 s | `restore_ablation_results.json` |
| 2 | `code/scripts/offline_veto_reconciliation.py --trials 10 --output …` | questo host, processi su loopback | 26 s | `offline_veto_results.json` |
| 3 | `code/scripts/reconcile_race_experiment.py --trials 20` | nodo 192.168.100.57, Docker | 47 s | `reconcile_race.log` |
| 4 | `code/scripts/fault_injection_experiment.py --trials 10 --output …` | nodo, Docker | 98 s | `fault_injection_results.csv`, `trials.csv`, `fault_injection.log` |

**Voci 3-4, regola G e dettagli.**
- Prima del passo: `df -h /` sul nodo = 3,9 GB liberi (3,7 GB dopo il build).
- Progetto compose `dibtnsm` (`COMPOSE_PROJECT_NAME`), con il compose committato (`DIB_DIST_FANOUT_CONCURRENCY=8`, trigger di riconciliazione spento, `/reconcile` chiamato dagli script).
- Albero sul nodo: `~/dib_tnsm/tree-c23d1e3`. `git diff c23d1e3 HEAD -- code` è vuoto e `service.py` ha l'hash congelato (verificato sul nodo). Python: venv del nodo con le versioni di dib312.
- Fine passo: `docker compose down -v --remove-orphans`, nessun container `dibtnsm` residuo. Nessun prune. Le 11 immagini `dibtnsm-*` (layer condivisi, ~145 MB nominali ciascuna, ID in `compose_images.json`) restano perché il Passo 3 le riusa.
- **Nota d'ambiente:** sul nodo `/usr/bin/docker` (client 29.1.3) non ha il plugin compose. Il client snap `/snap/bin/docker` 29.8.0 sì (Compose v5.5.1). Gli script sono stati lanciati con `PATH=/snap/bin:$PATH`: nessuna installazione e nessuna modifica alla configurazione di Docker.

Sha256 dei file prodotti (`experiments_tnsm/g0b_regen/`):
- `restore_ablation_results.json` `2820bc4c…`
- `offline_veto_results.json` `4b7ceb04…`
- `trials.csv` `c7d60c00…`
- `fault_injection_results.csv` `92684dfc…`
- `reconcile_race.log` `0f8c88d5…`
- `fault_injection.log` `c0c09b6c…`

## 2. Confronto con il paper vecchio e con `results/`

Il confronto dei tempi è **solo descrittivo**: `service.py` è diverso (`d09f8db5…` → `3186304363ed…`) e cambiano host e versione di Python.

| Risultato | Paper vecchio (`main_old.tex`) | `results/` (vecchio) | G0b (nuovo) | Esito |
|---|---|---|---|---|
| `tab:comparison`, *reuse approval; preserve veto* | ACE senza nuovo commit 12/18; veti 6/6 (`:480`) | 12/18; 6/6 | **12/18; 6/6** | identico |
| `tab:comparison`, *reset every record to review* | 0/18; 0/6 (`:481`) | 0/18; 0/6 | **0/18; 0/6** | identico |
| `tab:comparison`, *provenance-aware review (DIB)* | 0/18; 6/6 (`:482`) | 0/18; 6/6 | **0/18; 6/6** | identico |
| Restore ablation, file completo | — | — | stesso contenuto; cambiano solo `service_sha256` e `script_sha256` dove applicabile | identico salvo gli hash |
| Veto offline, 10 prove (`:509`) | veto preservato e approvazione obsoleta riportata a MonitorOnly in ogni prova | 10/10 su tutti e quattro i controlli | **10/10 su tutti e quattro** (veti preservati, approvazioni obsolete annullate, fatti non correlati preservati, recuperi espliciti) | identico; cambiano solo `service_sha256` e `python` (3.10.13 → 3.12.15) |
| Outage: prove convergenti (`:507`) | 40 su 40 | 40/40 | **40/40** | identico |
| Un solo tipo di evento perso, 30 prove (`:507`) | 0,51 ± 0,03 s | 0,512 ± 0,029 s | **0,480 ± 0,017 s** | stesso ordine di grandezza |
| Episodio intero perso, 10 prove (`:507`) | 0,50 ± 0,04 s | 0,496 ± 0,039 s | **0,509 ± 0,034 s** | stesso ordine di grandezza |
| Riavvio del processo (`:507`) | ~0,45 s | 0,446 s (media) | 0,416 s (media) | stesso ordine di grandezza |
| Logica di riconciliazione (`:507`) | < 0,1 s | massimo 0,075 s | **massimo 0,105 s** | **la frase "< 0,1 s" non vale più per il massimo** (0,105 s in una prova); la media resta ≈ 0,07 s |
| Race con fan-out nuovi (`:507`, "another 20 trials") | 20 prove, numero d'ordine preservato | (nessun file in `results/`) | **20/20 consistenti** | identico |

**Lettura [D].**
- I risultati di correttezza dopo D11, D12, D19 e mTLS sono identici a quelli del paper.
- I tempi di convergenza restano dominati dal riavvio del processo (~0,42 s).
- Una sola cosa va corretta nel testo: "reconciliation logic takes less than 0.1 s" va riformulata come media (≈ 0,07 s) oppure come "about 0.1 s", perché il massimo nuovo è 0,105 s.

## 3. Cosa serve dall'utente

- OK alla copia in `results/` dei due file che fanno fallire `verify_artifact.py` (`restore_ablation/results.json`, `offline_veto/results.json`) e, se vuoi, di `fault_injection/{results,trials}.csv`, in un commit separato; poi `verify_artifact.py` deve tornare a 262/0.
- Decisione sulla frase "< 0,1 s" del paper.


## 4. Decisioni dell'utente (2026-10-10) e copia in `results/`

**Correzione per il paper** (`main_old.tex` non è stato modificato).
- "reconciliation logic takes less than 0.1 s" va sostituita con il valore misurato: **massimo 0,105 s, media 0,071 s** (40 prove, `experiments_tnsm/g0b_regen/trials.csv`, colonna `reconcile_call_s`).
- Nota: la formulazione dell'utente indicava "media ≈ 0,06 s"; il dato misurato è 0,071 s. 0,06 s era la media del vecchio `results/` (0,064 / 0,061 nei primi due scenari).
- Convergenza, da riportare separatamente: un solo tipo di evento perso **0,48 ± 0,02 s** (30 prove); episodio intero perso **0,51 ± 0,03 s** (10 prove).

**Copia.**
- In `results/` si copiano solo i due file che fanno fallire `verify_artifact.py`: `restore_ablation/results.json` e `offline_veto/results.json`.
- `fault_injection/{results,trials}.csv` **non** si copia. `scripts/verify_artifact.py:215-220` controlla la convergenza a evento singolo contro **0,51 ± 0,005 s**, il numero del paper; il nuovo valore 0,48 s farebbe fallire il controllo. Copiarlo richiederebbe di cambiare insieme il numero atteso e il paper: va deciso dall'utente.
- Se la regola E portasse a correggere `service.py`, la copia si rifà con il nuovo hash.

## 5. Aggiornamento (2026-10-10, sera): copia di `fault_injection` fatta da un altro commit

La sezione 4 dice che `fault_injection` non si copia. **Superata:** i commit `062b417` (dati, `README.md` e `verify_artifact.py` aggiornato: 262 → 266 controlli, con atteso 0,48 per l'evento singolo e 0,51 per l'episodio intero e nuovi controlli su `trials.csv`) e `52888bd` (`claims.json`), non scritti da questa sessione ma presenti su `revision-tnsm`, hanno già copiato i file e riallineato verificatore e claim. Verifica al momento della lettura: `verify_artifact.py` dà **266 passed, 0 failed**, `service.py` è invariato (`3186304363ed…`). Resta da aggiornare il testo del paper (`docs/main_tnsm.tex`, l'unico file di paper modificabile secondo `CLAUDE.md`): mancano la frase "< 0,1 s" (massimo 0,105 s, media 0,071 s) e le due convergenze 0,48 ± 0,02 e 0,51 ± 0,03 s.
