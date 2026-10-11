# Audit 53 — Pre-registrazione: ablation C_s-only / C_t-only e sweep dello split 0,7/0,3 di C_t sui tre laboratori reali (voce 5.3 di audit 36)

Data: 2026-10-11. Offline, nessun nodo. Dati letti **in place** da `/root/Desktop/DIB/data/processed/{moniotr_full_observations,yourthings_observations}.csv` e `docs/label_mapping_v16.csv` (stessi ingressi, stessi sha256 di a41:13/`run_secondary_20261011/manifest.json`); nella repo solo aggregati per ricevente (conteggi, precisione, recall, F1) e sha256 degli ingressi; **nessun valore per dispositivo** (licenza Mon(IoT)r/YourThings, CLAUDE.md). Nessuna modifica a `code/src`, `code/scripts`, `formal/`, `claims.json`, `results/`. Codice: `experiments_tnsm/split_ablation/analyze_split.py` (copia parametrica di `moniotr_cross_lab.score_keys`, come `pareto_frontier.score_keys_param`), test `test_analyze_split.py` (scritti prima).

## Cosa c'è oggi
Il testo del paper dice solo che lo split non entra nel bound (audit 36 voce 5.3; audit 09:49, 16:31); un'ablation non esiste. Sui tre laboratori con due sorgenti per ricevente C_s non varia (a43 A5 punto 1; audit 47: DIB e B(2, τ_match) selezionano gli stessi fatti): l'ablation dice quanto conta **C_t** e come, non il breadth.

## Disegno
Leave-one-out a tre laboratori come 5.3b: ricevente ∈ {US, UK, YT}, sorgenti = gli altri due; 6 dispositivi bersaglio per ricevente (`per_device_metrics`). Punteggio = α_eff·C_s + β_eff·C_t con C_t = min(1, w·d + (1 − w)·f), d = `active_day_ratio`, f = `frequency_ratio` (`dib.py:277-279`; `moniotr_cross_lab.py:360-367`); ammissione: valore ≥ θ, classe eleggibile (gate = vero, come `per_device_metrics`) e |S_e| ≥ m.
| Variante | w | α_eff, β_eff | θ | m |
|---|---|---|---|---|
| **V0 (DIB)** | 0,7 | 0,6; 0,4 | 0,65 | 2 |
| split | 0; 0,5; 0,6; 0,8; 0,9; 1 | 0,6; 0,4 | 0,65 | 2 |
| **Cs-only** | — | 1; 0 | 0,65 | 2 |
| **Ct-only** | 0,7 | 0; 1 | 0,65 | 2 |
Nessuna soglia ri-calibrata per variante (θ = 0,65 fisso: l'ablation toglie un termine, non riottimizza).

## Validità (asserzione, prima di qualunque numero)
V0 deve riprodurre **esattamente** l'insieme `locked` di `per_device_metrics` per ciascun ricevente (stessa asserzione di analyze_baseline.py:211-216); la copia parametrica deve inoltre coincidere con `score_keys` reale su un `Aggregate` sintetico (test). Se la riproduzione fallisce non si riporta nulla.

## Ipotesi (scritte prima dei dati)
- **H-S1 (lo split non conta nel range 0,6-0,9):** l'**insieme** dei candidati per w ∈ {0,6; 0,8; 0,9} coincide con quello di V0 in tutti e tre i riceventi. **Falsificata** se almeno un ricevente ha un insieme diverso per almeno un w del range. Se non falsificata: "nessuna differenza osservata a questi tre riceventi", non "lo split è irrilevante in generale".
- **H-S2 (identità dell'ablation Cs-only):** con due sorgenti C_s = 1 per ogni chiave che supera il quorum, quindi **Cs-only = {chiavi con |S_e| ≥ 2 e classe eleggibile}** (calcolato indipendentemente da `key_table`, `analyze_baseline.py:50-64`, con τ = 0). **Falsificata** da un insieme diverso in un ricevente.
- **H-S3 (Ct-only ⊆ V0):** poiché a C_s = 1 la soglia di DIB su C_t è 1/8 < 0,65, ogni chiave di Ct-only (quorum e classe inclusi) sta in V0. **Falsificata** da una chiave di Ct-only fuori da V0 in un ricevente.
- **Descrittivo, nessun criterio:** candidati, copertura, precisione, recall, F1 per ricevente e variante; per ogni w, differenza simmetrica con V0 (solo conteggio).

## Cosa non si fa / limiti
Nessun ottimo di w; nessun bootstrap (nessuna unità di campionamento sensata: n = 3 riceventi, deterministico); nessuna generalizzazione oltre i tre laboratori (con 2 sorgenti C_s è costante: il peso del breadth non è sollecitato). Se H-S1 è falsificata, si riporta quale ricevente e quanti fatti cambiano, senza interpretare. Output: `experiments_tnsm/split_ablation/run_20261011/aggregates.json` (+ manifest con sha256), solo aggregati.
