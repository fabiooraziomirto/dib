# Audit 49 — A4: tabella di robustezza (α, θ) (descrittiva; definizione in audit 42)

Data: 2026-10-11. Script `analysis_fs/alpha_theta_table.py` (test `analysis_fs/test_alpha_theta_table.py`: 5 passed; mutazioni: f* con formula sbagliata catturata (2 falliti), f_s = 1/3 catturata (1), copertura troppo larga catturata (3), `>=` al posto di `>` sul margine **non catturata** perché nessuna coppia ha margine esattamente 0). Comando: `python3 analysis_fs/alpha_theta_table.py`. Dati: `results/sensitivity/*.csv` letti, non ricalcolati; raw per costruzione dello script (`code/scripts/parameter_sensitivity_external.py:44`, default `trust_weighted=False`, `dib.py:66`), ma senza manifest che provi la versione (audit 42 §4). Natura: **descrittiva, nessun criterio**. Recall = macro semantico contro ground truth UNSW, non il recall per ricevente di 5.3b.

| corpus | alpha | theta | f* | r | f*-0.30 | Criterion f_s=0.30 | sweep | admitted | precision | recall | f1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| moniotr | 0.6 | 0.65 | 5/12 | 5/7 | 7/60 | si | alpha_sweep | 26 | 0.125 | 0.034524 | 0.053799 |
| moniotr | 0.6 | 0.65 | 5/12 | 5/7 | 7/60 | si | theta_sweep | 26 | 0.125 | 0.034524 | 0.053799 |
| moniotr | 0.7 | 0.65 | 1/2 | 1 | 1/5 | si | alpha_sweep | 38 | 0.138095 | 0.043452 | 0.064992 |
| moniotr | 0.6 | 0.7 | 1/2 | 1 | 1/5 | si | theta_sweep | 24 | 0.130357 | 0.030952 | 0.049484 |
| moniotr | 0.55 | 0.6 | 3/11 | 3/8 | -3/110 | NO | - | non disponibile | non disponibile | non disponibile | non disponibile |
| yourthings | 0.6 | 0.65 | 5/12 | 5/7 | 7/60 | si | alpha_sweep | 67 | 0.127938 | 0.027897 | 0.043684 |
| yourthings | 0.6 | 0.65 | 5/12 | 5/7 | 7/60 | si | theta_sweep | 67 | 0.127938 | 0.027897 | 0.043684 |
| yourthings | 0.7 | 0.65 | 1/2 | 1 | 1/5 | si | alpha_sweep | 67 | 0.127938 | 0.027897 | 0.043684 |
| yourthings | 0.6 | 0.7 | 1/2 | 1 | 1/5 | si | theta_sweep | 67 | 0.127938 | 0.027897 | 0.043684 |
| yourthings | 0.55 | 0.6 | 3/11 | 3/8 | -3/110 | NO | - | non disponibile | non disponibile | non disponibile | non disponibile |

## Lettura (descrittiva)
- **Colonne analitiche** = valori attesi di audit 42 §3 (f* = 5/12, 1/2, 1/2, 3/11; r = 5/7, 1, 1, 3/8; margini 7/60, 1/5, 1/5, −3/110).
- **(0,55; 0,6) non soddisfa il Criterion con f_s = 0,30** (margine −3/110); recall e precisione "non disponibili" (nessuno dei due sweep la copre): nessuna simulazione nuova senza OK.
- **(0,6; 0,65) è identica nei due sweep** (stesso conteggio ammessi, precisione, recall), come atteso (stessa configurazione).
- **Mon(IoT)r:** il recall passa da 0,0345 (0,6; 0,65) a 0,0435 (0,7; 0,65) e a 0,0310 (0,6; 0,7); i conteggi ammessi 26, 38, 24. **YourThings:** conteggio ammessi 67 e metriche **identici** nelle tre coppie coperte: su questo corpus (α, θ) non cambia nulla in queste coppie. Non si attribuisce una causa (non verificata qui; coerente con la lettura di audit 47 che sui reali conta il quorum, ma è un'ipotesi non testata).
- Valori assoluti bassi (recall ≤ 0,044) perché il ground truth UNSW è in gran parte non osservabile nei dati (nota del paper su 55/564 ACE osservabili, `docs/main_tnsm.tex`).
- **Per `tab:params`:** riportare f*, r, margine e il flag Criterion; il recall solo per le coppie coperte, con l'etichetta "raw, macro semantico, UNSW", e "n/d" per (0,55; 0,6).
