# Audit 00 — Inventario e creazione della repo pulita (parte A)

Data: 2026-10-10. Sorgente: `/root/Desktop/DIB_reframe/dib-tnsm-artifact-v43` (`SRC`, HEAD `ca9c6a0`). Nuova repo: `/root/Desktop/DIB_clean` (`NEW`, branch `main`, tag `v43-import` e `baseline-v43` sul commit di importazione `bd3080b`). Nessun file di `SRC` né di `DIB_reframe` è stato modificato.

## 1. Inventario di SRC (`du`)

| Voce | Dimensione (du) | Decisione |
|---|---|---|
| `.git` | 11 M | escluso |
| `slides/` (non tracciato) | 1,6 M | escluso |
| `code/` (src 647K, tests 439K, scripts 433K) | 1,6 M | incluso (senza `__pycache__`) |
| `results/` | 1,3 M | incluso (senza i `registry.db`, vedi §3) |
| `paper/` | 359K | escluso |
| `formal/` | 193K | incluso |
| `openwrt/` | 43K | incluso |
| `docs/` | 33K | incluso `data_provenance.md`, `KNOWN_LIMITATIONS.md`, `label_mapping_v16.csv`; esclusi `RELATED_WORK_SCOPE.md`, `REVISION_NOTES_v36.md`, `PAPER_SOURCE_v43.md` |
| `configs/`, `scripts/`, `claims.json`, `README.md`, `LICENSE`, `CITATION.cff`, `.gitignore` | < 60K | inclusi |

Esclusi anche: `__pycache__`, `.pytest_cache`, PDF, `tla2tools.jar` (assente in SRC), dataset di terzi (assenti in SRC). Snapshot v31 e v36 non sono in SRC.

Risultato: 639 file tracciati in NEW. Confronto con `git ls-files` di SRC (esclusi `paper/` e `slides/`, 635 voci): mancano solo i 2 documenti esclusi e `code/configs`, che in `find -type f` non compare perché è un symlink (è comunque tracciato nel commit di importazione).

## 2. Cose trovate in più rispetto al piano (da decidere)

1. **`code/configs` è un symlink assoluto** a `/root/Desktop/DIB/configs` (in SRC e in `bd3080b`). Fuori dalla macchina è un link rotto, quindi la repo non è autosufficiente. Contiene `default_hyperparams.yaml`, `ref_strict_hyperparams.yaml`, `ref_trust_hyperparams.yaml`, `tnsm_graph_free_unweighted.yaml`. Importato com'è, per restare byte-fedele. Proposta: sostituirlo con una cartella vera in un commit separato (scelta tua).
2. **File richiesti da `verify_artifact.py` ma ignorati da `.gitignore` di SRC**: `formal/mutations/m1..m6/result.log` (letti in `scripts/verify_artifact.py:70`) rientrano in `*.log` (`.gitignore:16`) e non sono nell'whitelist (`!formal/logs/*.log`, `!results/**/*.log`). In SRC non sono tracciati: un clone pulito di v43 farebbe fallire quei 6 check. Qui sono stati aggiunti con `git add -f` nel commit di importazione e il `.gitignore` ora ha `!formal/mutations/**/result.log`.
3. **`results/openwrt/**/registry.db`** (11 file, 55K): ignorati da `*.db` in SRC, mai tracciati. **Esclusi** da NEW. I `checksums.sha256` di quelle cartelle ne citano l'hash (righe 1–2), quindi i file non sono verificabili contro i checksum; `verify_artifact.py` non li legge.
4. **README**: «No code or configuration in this repository depends on those paths» non è del tutto vero: vedi §4 (`prepare_rwv_governance_bootstrap.py`, symlink). Non modificato (le affermazioni del README non sono state cambiate).
5. **Script**: 71 file in `code/scripts/`, solo 26 citati da `claims.json`. Inclusi tutti (default confermato).

## 3. Verifiche dopo la creazione (eseguite)

- Hash: 638 file (tutti i tracciati tranne il symlink) identici a SRC, `sha256sum -c` OK. Manifest: `docs/audit/00_manifest.sha256`.
- `cd code && python3 -m pytest tests -q`: **281 passed in 5,20 s** (Python 3.10.13).
- `python3 -I scripts/verify_artifact.py`: **262 checks passed, 0 failed**.
- `git status` pulito dopo l'esecuzione.
- `pyproject.toml` non modificato: `requires-python >=3.12` (`code/pyproject.toml:9`) contro l'ambiente 3.10.13 (D18). Scelta tua.

## 4. Percorsi assoluti e riferimenti personali (file:riga)

Codice vivo:
- `code/scripts/prepare_rwv_governance_bootstrap.py:17` `sys.path.insert(0, "/root/Desktop/DIB/src")`; `:25` default `--input /root/Desktop/DIB/data/processed/observations_enriched.csv`; `:26` default `--output-dir /root/Desktop/DIB_reframe/results/rwv_baseline/governance_bootstrap`. Script non citato da `claims.json`.
- `code/configs` (symlink, vedi §2.1).
- `docs/data_provenance.md:94,98`.

Evidenza storica, non modificata (README la dichiara «deliberately left unedited»): `results/three_lab_loo/manifest.json:6,22,53`; `results/cold_start/manifest.json:4,37,38`; `results/workload/manifest.json:6,22`; `results/sybil/manifest.json:20`; `results/sybil_jaccard/manifest.json:6`; `results/ablation_multiseed/manifest.json:27,28`; `results/sybil/run.log:51`; `results/a1_baselines/run_sweep.log:25`; `results/openwrt/campaign-10runs/run-*/harness.log:85` e `checksums.sha256:1-2`; `results/openwrt/single-run-*/checksums.sha256`; `formal/logs/full_lifecycle.log:3-10` (e altri log TLC) con `/root/Desktop/BioDevOps/formal_artifacts/tools/tla2tools.jar`.

Riferimenti personali (`fabio|mirto|unime`): nessuno nel codice incluso. `LICENSE:3` ha il segnaposto `<AUTHOR NAME — da completare prima della pubblicazione>`; `CITATION.cff` ha `TODO` per cognome, nome, affiliazione (anche nell'autore di `preferred-citation`).

Segreti: nessuna chiave o password (`api_key|secret|password|BEGIN PRIVATE`); i match di «token» sono il token di concorrenza ottimistica (`code/src/dib/registry/db.py:117,124`) e commenti dei `.tla`.

## 5. Licenze

- Codice: MIT (`LICENSE`, `README.md`), titolare mancante.
- osMUD: clonato a build time (`openwrt/Dockerfile.router:2,5`, commit `852918eb33f3e15225da4de21d440b5b9a5d875f`), non ridistribuito. **La sua licenza non è stata verificata** (richiede accesso al repo upstream).
- Dataset UNSW / Mon(IoT)r / YourThings: non inclusi; licenza «da verificare» già in `docs/data_provenance.md:24,32`.
- Immagini Docker (OpenWrt): licenza propria.
- `slides/README.md` cita un template MIT (UniMe nome/stemma esclusi dalla licenza): `slides/` non è nella repo.

## 6. `tla2tools.jar`

Non incluso. Versione dei log TLC: `TLC2 Version 2026.05.26.235334 (rev: 4ba7d88)` (`formal/logs/full_lifecycle.log:1`). Il jar trovato in `/root/Desktop/BioDevOps/formal_methods/` (usato nell'audit 01) ha sha256 `237332bdcc79a35c7d26efa7b82c77c85c2744591c5598673a8a45085ff2a4fb`, MANIFEST senza numero di versione; non ho confermato che sia la stessa release dei log (per farlo bisognerebbe eseguire TLC su un modello, non fatto).

## 7. Commit

1. `bd3080b` Import (copia byte-identica; `.gitignore` di SRC invariato; mutazioni `result.log` aggiunte con `-f`). Tag `v43-import` e `baseline-v43`.
2. Questo commit: `.gitignore` (whitelist mutazioni, `*.jar`, `.claude/`), intestazione README con provenienza e comandi, `CLAUDE.md`, manifest, questo file.

Il tag `baseline-v43` è nella nuova repo (sul commit di importazione), non in `SRC/.git` (default confermato).

## 8. Decisioni aperte per te

1. Titolare di `LICENSE` e autori di `CITATION.cff`.
2. Sostituire il symlink `code/configs` con una cartella vera.
3. Spostare in `archive/` i 45 script non citati (in particolare `prepare_rwv_governance_bootstrap.py`).
4. Includere o no i `registry.db` (richiederebbe `git add -f` o una whitelist).
5. `requires-python` (D18).
6. Verificare la licenza di osMUD e la release di `tla2tools.jar`.
