# Audit 42 — PRE-REGISTRAZIONE — A4: tabella di robustezza (α, θ), definizione scritta PRIMA di qualunque calcolo

Data: 2026-10-11. **Nulla è stato calcolato.** Pre-registrazione committata prima dello script (via dell'utente, 2026-10-11). Fonte: `docs/audit/43_piano_esperimenti_DRAFT.md` A4; a36:59 (voce 5.3b(a), "resta da definire"); a11:11. Natura: **tabella DESCRITTIVA, nessuna ipotesi, nessun criterio di falsificazione, nessuna soglia.** Offline: nessun ssh, nessun sudo; nessuna modifica a `code/src`, `formal/`, `claims.json`, `results/`.

## 1. Domanda
Perché (α, θ) = (0,6; 0,65) e non le coppie già provate (0,7; 0,65), (0,6; 0,7), (0,55; 0,6) (a11:11)? Serve a `tab:params` e a `sec:sensitivity-results` (obiettivo 5 di CLAUDE.md). Priorità condizionata a Q13 (a43 §7).

## 2. Coppie (fissate ora)
Le 4 coppie di a11:11, con β = 1 − α e γ = 0. Nessuna coppia aggiunta dopo aver visto i dati; una griglia più fine è un'estensione dichiarata a parte (candidato: `analysis_fs/bound_grid.py` con (α, θ) variabile, a09:60).

## 3. Colonne (tutte calcolate con `fractions.Fraction`, mai float)
1. f* = (θ − β)/α;  2. r = (θ + α − 1)/(1 − θ) (forma K < r·h, a36:59);  3. margine f* − 3/10 (f_s = 0,30);  4. recall e precisione sui dati reali da `results/sensitivity/{moniotr,yourthings}_{alpha_sweep,theta_sweep}.csv` (colonne `admitted_endpoint_count`, `precision`, `recall`, `f1`) e margine analitico da `*_alpha_margin.csv` (`theoretical_bound`, `margin`, `provably_safe`).

**Valori attesi dall'aritmetica (controllo, non ipotesi; verificati a mano, da confermare col codice):**

| (α, θ) | f* | r | f* − 3/10 |
|---|---|---|---|
| (0,6; 0,65) | 5/12 | 5/7 | 7/60 |
| (0,7; 0,65) | 1/2 | 1 | 1/5 |
| (0,6; 0,7) | 1/2 | 1 | 1/5 |
| (0,55; 0,6) | 3/11 | 3/8 | −3/110 (negativo: nessuna protezione a f_s = 0,30) |

r = 5/7, 1, 1, 3/8 coincide con a11:11. I margini minimi già noti (a11:36-41) si riproducono come controllo aritmetico.

## 4. Regole di lettura e stop (fissate ora)
- **Se una coppia non è coperta dai CSV:** si scrive "non disponibile"; **nessuna simulazione nuova senza OK** (a43 A4, voce 8).
- **Verifica di copertura fatta (2026-10-11, solo intestazioni e colonne della griglia α, β, θ dei sei CSV; nessun valore di recall letto):** `*_alpha_sweep.csv` ha θ = 0,65 fisso e α = 0,40…0,90 passo 0,05 (11 righe); `*_theta_sweep.csv` ha α = 0,6 fisso e θ = 0,50…0,80 passo 0,025 (13 righe); `*_alpha_margin.csv` ha la stessa griglia di α di `alpha_sweep` con due frazioni avversarie (22 righe). Quindi: (0,6; 0,65) coperta (entrambi gli sweep); (0,7; 0,65) coperta da `alpha_sweep`; (0,6; 0,7) coperta da `theta_sweep`; **(0,55; 0,6) NON coperta** (richiede α = 0,55 e θ = 0,6 insieme, nessuno dei due sweep li varia insieme) ⇒ per questa coppia recall e precisione sono "non disponibili" e restano solo le colonne analitiche (f*, r, margine). Il margine −3/110 va segnato nella tabella e in `tab:params`: **la coppia non soddisfa il Criterion con f_s = 0,30.**
- **Pesato o raw (verifica fatta sul codice, non sui valori):** lo script che produce i CSV costruisce `ScoringConfig(alpha, beta, gamma=0.0, theta, graph_enabled=False)` senza altri argomenti (`code/scripts/parameter_sensitivity_external.py:44`) e il default è `trust_weighted: bool = False`, `independence_aware: bool = False` (`code/src/dib/evaluation/dib.py:66, 71`): **le colonne sono raw per costruzione dello script**. **Limite:** i CSV in `results/sensitivity/` non portano un manifest con commit e config; che siano stati generati da questa versione dello script è un'inferenza dal README (`results/sensitivity/README.md:8-14`), non una verifica. Si riporta così nella tabella. Recall = macro semantico per dispositivo contro il ground truth UNSW (`semantic_match_metrics`, script `:46-60`), non il recall per ricevente di 5.3b: le due quantità non si confrontano.
- **Nota di lettura (da a43 A4):** a parità di conteggio di candidati, B(2, τ_match) dà le stesse metriche di DIB in 3/3 riceventi (H-B1 falsificata, a41 / `aggregates.json:347-386`); se A2 passo 1 dà Δ = 0, sui laboratori reali (α, θ) non cambia l'esito osservato e la tabella va letta nel regime a N siti (f*, K < r·h; a11:9-31), cioè nel simulatore sintetico. La tabella non dice quale sia migliore.
- Dati Mon(IoT)r/YourThings: solo aggregati già presenti in `results/sensitivity/`; nessun dato per dispositivo.

## 5. Output
Tabella aggregata in `docs/audit/` (audit di risultato successivo), script in `analysis_fs/`; test sullo script: l'algebra della §3 contro `DIBScorer` sulla griglia di a11 (mutazioni: α e β scambiati, `>` al posto di `≥`, f_s ≠ 3/10).
