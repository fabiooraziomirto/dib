# Audit 00 — Baseline per la revisione TNSM (due riferimenti)

Data: 2026-10-10. Branch `revision-tnsm` (portato in fast-forward su `analysis-fs` @ `d22652e`, nessun commit proprio prima), worktree `/root/Desktop/DIB_tnsm`. Nessun file di `code/src`, `formal/`, `claims.json` o `results/` è stato modificato. Numerato 00 perché è un riferimento di partenza come `00_inventario_repo_pulita.md`; le numerazioni 11, 12, 13 restano a h_d, piano misure e test realistici.

## Ambiente

| Voce | Valore |
|---|---|
| Python | 3.10.13 (`pyproject.toml` dichiara >=3.12, D18) |
| OS | Ubuntu 22.04.3 LTS, kernel 6.8.12-18-pve (container Proxmox) |
| CPU | 2 × AMD EPYC 7313 16-Core; `nproc` = 16 nel container |
| RAM | 64 GiB, nessuno swap (`free -g`) |
| Disco | `/` al 94% (35 GB liberi): scaricare solo campioni e fuori dalla repo |

## Due baseline

Le due righe sono entrambe attese. I numeri attesi in `CLAUDE.md` (281/262) non cambiano: valgono per il tag.

| Riferimento | `service.py` sha256 | `pytest code/tests` | `verify_artifact.py` | Come |
|---|---|---|---|---|
| `v43-import` (`bd3080b`) | `d09f8db5…` | **281 passed** (5,4 s) | **262 passed, 0 failed** | worktree temporaneo detached sul tag, rimosso dopo l'uso |
| HEAD `revision-tnsm` (`d22652e` + integrazione file nuovi) | `48415497…` | **412 passed** (23 s) | **260 passed, 2 failed** | worktree `DIB_tnsm` |

I 2 fallimenti di HEAD sono quelli attesi e documentati in `docs/work/regenerate-results-after-service-changes.md`:

- `scripts/verify_artifact.py:250` `ablation source matches packaged service`: `results/restore_ablation/results.json:3` registra `d09f8db5…`;
- `scripts/verify_artifact.py:323` `offline veto: service matches packaged distributed service`: `results/offline_veto/results.json:4` registra `d09f8db5…`.

Il file attuale è `48415497…`: i fix D12, D11 e D19 (`eaea3ea`, `5e24b57`, `b17cbab`) cambiano `code/src/dib/registry/distributed/service.py`. Decisione: niente rigenerazione di `results/` adesso; si rigenera una volta sola, a fine modifiche a `service.py` (mTLS incluso).

I 131 test in più rispetto al tag vengono dai 36 commit `v43-import..analysis-fs` (`test_registry_lifecycle_gaps.py`, `test_distributed_service_inproc.py` e harness, audit 02–06).

### Test di `analysis_fs/`

| Dove | Esito |
|---|---|
| `DIB_clean` (working tree condivisa) | 47 passed, 1 xfailed |
| `DIB_tnsm` (worktree pulito) | 45 passed, 2 skipped, 1 xfailed |

I 2 skip sono `analysis_fs/test_spurious_sampling.py:58` ("data or filtered copy missing"): le copie filtrate `analysis_fs/out/observations_enriched*_nospurious.csv` sono in `.gitignore` ed esistono solo in `DIB_clean`. Non le ho copiate.

## Discrepanza con la documentazione: `main` non è più la baseline v43

`docs/work/regenerate-results-after-service-changes.md` dice che `main` resta la baseline v43. Non è così: `v43-import..main` contiene il merge `280ddfa` di `integration/2026-10-10`, che integra `tests-gap-closure`, `fix-d12-ack`, `revision-tnsm`, `fix-reconcile-trigger-fanout`, `fix-d19`, `formal-ae` e `analysis-fs`. `main` ha `service.py` = `48415497…`, quindi `verify_artifact.py` su `main` dà gli stessi 2 fallimenti. Questo contraddice anche la regola "non fare merge in main con controlli rossi" dello stesso documento. Rispetto ad `analysis-fs`, `main` ha in più 5 commit di `formal-ae` (`bdc3c38`, `2d6b315`, `0751cc1`, `a6f8060`, `8223480`: audit 07 e cfg/TLA+ in `formal/distributed_ae/`) più i merge. La baseline v43 resta il tag `v43-import`.

## Dati fuori repo

Presenti in `/root/Desktop/DIB/data`: `processed/` (`observations_enriched*.csv`, `moniotr_full_observations.csv`, `real_federation_observations.csv`, `yourthings_observations.csv`, …), `unsw/profiles/{normalized,ground_truth}`, `unsw_attack_2018/annotations`, `testbed/`. Presenti anche `/root/Desktop/DIB/src`, `/root/Desktop/DIB/reports/item1_private_ip_filter/` e `/root/Desktop/DIB_reframe/results/rwv_baseline/governance_bootstrap`.

Mancante: `data/unsw_iotraffic_2025/{flows_extracted/flows,protocols_extracted/protocols}`, letto da `code/scripts/build_dataset_inventory.py`, `fingerprint_classifier_experiment.py`, `fingerprint_classifier_strong.py` e `prepare_unsw_iotraffic.py`.

## Verifica dell'integrazione (Fase 1)

File copiati senza sovrascrivere (`cp -n`, verificati con `cmp`) da `DIB_clean`: `analysis_fs/fs_binomial.py` (sha256 `981681c8…`), `analysis_fs/out/fs_binomial.csv` (`ba6ad79c…`), `analysis_fs/test_fstar_math.py` (`5ac6d62e…`), `docs/audit/09_…`, `docs/audit/10_…`. `CLAUDE.md`: diff rispetto a HEAD = 19 righe aggiunte in fondo, nessuna rimossa.

- `PYTHONPATH=code/src python3 -m pytest analysis_fs/test_fstar_math.py`: **7 passed**.
- `python3 analysis_fs/fs_binomial.py <tmp> && diff <tmp> analysis_fs/out/fs_binomial.csv`: **diff non vuoto**. Differiscono 8 righe su 25, solo nella colonna `p_violation`, ciascuna di esattamente 1 ulp (errore relativo massimo 2,1e-16). Le colonne `N`, `q`, `kmin` e `f_star` sono identiche. La causa più probabile è l'arrotondamento di `q**k * (1-q)**(N-k)` in `analysis_fs/fs_binomial.py:34` (potenze in floating point, `pow` della libm), diverso tra la macchina che ha prodotto il CSV e questa. [?] Non ho la versione di Python o la piattaforma di origine. Nessun valore cambia a più di 15 cifre significative. Il CSV è stato committato così come fornito.

## Note per la pubblicazione

- `analysis_fs/out/hd_by_device.csv` (già committato, 730 righe) contiene solo aggregati: `corpus, device_type, h_d, sites, k_tol_5_12, k_tol_fs030, k3_share, k3_exceeds_5_12, k3_exceeds_fs030`. Le etichette di sito sono `US`, `UK`, `YT` o vuote, e non ci sono IP, MAC, flussi o timestamp. Contiene però i nomi dei dispositivi Mon(IoT)r (corpora `moniotr_*`), cioè l'inventario dei laboratori. La voce corrispondente è in `docs/work/PRE_PUBLICATION_CHECKLIST.md`.
- `docs/main.tex` (866 righe) e i 7 `.cfg` in stage in `formal/distributed_ae/` sono nella working tree di `DIB_clean` e restano fuori dai commit di questo branch.
