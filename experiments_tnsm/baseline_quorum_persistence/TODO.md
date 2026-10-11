# TODO — baseline 5.3b

- `code/scripts/v28_matched_ablation.py` non è eseguibile in questa repo: usa percorsi che qui non esistono
  (righe 19-22: `code/data/processed/moniotr_full_observations.csv`, `code/data/processed/yourthings_observations.csv`,
  `experiments/30_three_lab_loo/label_mapping_v16.csv`, `experiments/33_v28_matched_ablation`; riga 28:
  `experiments/30_three_lab_loo/leave_one_out_three_lab.csv`). L'indicazione «righe 21-24» ricevuta era approssimata:
  i numeri verificati con `grep -n "code/data\|experiments/"` sono questi. Per questo `analyze_baseline.py` ne replica
  la logica invece di importarlo, e la Fase B è stata coperta dalla riproduzione 12/12 contro
  `results/three_lab_matched/matched_ablation.csv` (commit bd3080b). Codice congelato, non modificato.
