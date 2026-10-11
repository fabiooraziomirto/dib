# Audit 47 — A2 passo 1: differenza simmetrica C_DIB Δ C_B(2, τ_match) per ricevente (POST-HOC, a41 §1-§3)

Data: 2026-10-11. Fonti: `experiments_tnsm/baseline_quorum_persistence/run_secondary_20261011/{secondary.json,manifest.json}` (aggregati; valori per dispositivo fuori repo, `/root/Desktop/DIB/outputs/tnsm_baseline_53b/per_device_53b.csv`, sha256 `e8893a09…0484b`, `manifest.json`); codice `analyze_secondary.py` (commit `5aede6e`, sha256 `d2104d39…efbb`); confermativo `run_20261012/real/aggregates.json` (sha256 `15cd3be1…a9a560`, coincide con a41:13). Etichetta: **POST-HOC**; nessuna ipotesi nuova. Esecuzione: seed 20261012, B = 10 000, Python 3.10.13, Linux 6.8.12-18-pve (`manifest.json`). Test del modulo: 14 passed (`pytest experiments_tnsm/baseline_quorum_persistence`, riletti 2026-10-11).

## Risultato
| Ricevente | τ_match | \|C_DIB\| | \|C_B(2,τ_match)\| | intersezione | \|Δ\| | n unità | unità con d ≠ 0 |
|---|---|---|---|---|---|---|---|
| US | 0,17 | 36 | 36 | 36 | **0** | 6 | 0 |
| UK | 0,0 | 43 | 43 | 43 | **0** | 6 | 0 |
| YT | 0,17 | 107 | 107 | 107 | **0** | 6 | 0 |
Pooled: n = 18, 0 unità con d ≠ 0, media d = 0, IC95 [0, 0] ⇒ "non falsificata; nessuna differenza osservata, nessun potere" (`secondary.json`, chiave `pooled.verdict`; regola a41:34). Per ricevente n = 6 < 10 ⇒ solo descrittivo, nessun verdetto.

## Lettura
- **Gli insiemi coincidono** nei tre riceventi (non solo i conteggi): sui laboratori reali, a candidati pari, DIB e quorum + classe + persistenza B(2, τ_match) selezionano gli **stessi** fatti (`secondary.json`, `sets`). Quindi (α, θ) non cambia l'esito osservato sui reali (a43 A4, nota) e il passo 2 di A2 (bootstrap come test) **non si esegue**: sarebbe degenere. **A3 decade** (a43: condizionata a Δ > 0).
- **Cosa non si conclude:** non dice che i due criteri siano equivalenti in generale. Con 2 sorgenti per ricevente C_s non varia (a43 A5 punto 1); il termine di breadth non è sollecitato. Vale per questi dati e per τ_match scelto a candidati pari. Il bootstrap con IC [0, 0] non è conferma di equivalenza, è assenza di potere (a41:34).
- Nessun dato per dispositivo da Mon(IoT)r/YourThings nella repo.
