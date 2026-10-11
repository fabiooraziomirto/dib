# Audit 52 — Risultati di audit 51: (A) sweep di m e (B) dipendenza da ρ

Data: 2026-10-11. Codice: `analysis_fs/m_rho_tables.py`, test `analysis_fs/test_m_rho.py` (rossi per modulo mancante nel commit successivo a `e8f408f`; poi implementazione). Comando test: `PYTHONPATH=code/src PYTHONDONTWRITEBYTECODE=1 python3 -m pytest analysis_fs/test_m_rho.py -q -p no:cacheprovider` → **20 passed** (17 s). Tabelle: `PYTHONPATH=code/src python3 analysis_fs/m_rho_tables.py`. Python 3.10.13. Ipotesi e criteri: audit 51 (committato prima dello script).

## Esito dei test
- **H-A1 (m ∈ {1, 2, 3}, 4 coppie (α, θ), 2 costruzioni, K = 1..8, h = 0..20): non falsificata** su tutte le celle: il `DIBScorer` ammette ⇔ K > r·h ∧ K ≥ m, anche per m = 3 (estensione di audit 11, che copriva m ∈ {1, 2}).
- **H-B1 (ρ ∈ {1, 2, 5, 10, 100, 1000}, h = 1..20, K = 1..8): non falsificata**: decisione del `DIBScorer` = `score_exact ≥ θ` fuori dalla zona di pareggio. Margine a ρ = 100: β·0,3/101 = 0,00119 (riproduce audit 11:32).
- **Saturazione di C_t:** C_t ≤ 1 su tutta la griglia d, f ∈ {0, 1/20, …, 1} e = 1 solo per d = f = 1.
- **Mutazioni:** floor al posto di ceil, `≥` al posto di `>` in `binds`, `>` al posto di `≥` in `types_able`, margine 0,3β/ρ: catturate. **Sopravvissute, dichiarate:** (i) n_a = ρ·h al posto di K·⌈ρh/K⌉ (la differenza non cambia nessuna decisione sulla griglia); (ii) rimozione del `min(1, ·)` di C_t (equivalente: non vincola mai, è proprio la saturazione verificata sopra). Non sono lacune dei test ma equivalenze sulla griglia.

## A. Quorum effettivo k_eff(N, m) = max(m, ⌈5N/12⌉); * = m vincola
| N | m = 1 | m = 2 | m = 3 |
|---|---|---|---|
| 1 | 1 | 2* | 3* |
| 2 | 1 | 2* | 3* |
| 3 | 2 | 2 | 3* |
| 4 | 2 | 2 | 3* |
| 5 | 3 | 3 | 3 |
| 6 | 3 | 3 | 3 |
| 7 | 3 | 3 | 3 |
| 8 | 4 | 4 | 4 |
| 9 | 4 | 4 | 4 |
| 10 | 5 | 5 | 5 |
| 11 | 5 | 5 | 5 |
| 12 | 5 | 5 | 5 |

m binds for N in: m = 1: none; m = 2: [1, 2]; m = 3: [1, 2, 3, 4]

## Device types able to have an admitted fact (h >= m), by h_d histogram variant

| variant | types | m = 1 | m = 2 | m = 3 |
|---|---|---|---|---|
| base_4_sites | 119 | 119 | 32 | 4 |
| with_ncsu_strict | 119 | 119 | 32 | 4 |
| with_ncsu_family | 119 | 119 | 36 | 5 |

## B. Smallest K admitted by the score alone (m = 1), K_min(h, rho); r = 5/7

| h | rho = 1 | rho = 2 | rho = 5 | rho = 10 | rho = 100 | rho = 1000 | rho = 1000000 | 5h/7 |
|---|---|---|---|---|---|---|---|---|
| 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 0.71 |
| 2 | 3 | 2 | 2 | 2 | 2 | 2 | 2 | 1.43 |
| 3 | 4 | 3 | 3 | 3 | 3 | 3 | 3 | 2.14 |
| 5 | 6 | 5 | 5 | 4 | 4 | 4 | 4 | 3.57 |
| 7 | 8 | 7 | 6 | 6 | 6 | 6 | 6 | 5.00 |
| 10 | 11 | 9 | 9 | 8 | 8 | 8 | 8 | 7.14 |
| 14 | 15 | 13 | 12 | 11 | 11 | 11 | 11 | 10.00 |
| 20 | 19 | 18 | 17 | 16 | 15 | 15 | 15 | 14.29 |


## Lettura (descrittiva)
- **m = 2 vincola solo per N ≤ 2; m = 3 solo per N ≤ 4.** Per N ≥ 5 il bound frazionario ⌈5N/12⌉ ≥ 3 domina e m è irrilevante: il quorum non è il meccanismo di protezione a federazioni grandi, ma solo a quelle molto piccole (cold start a 2-3 laboratori).
- **Costo di m sui tipi reali** (istogramma aggregato `anchor_hd.json`: conteggi, nessuna etichetta): i tipi con almeno un fatto ammissibile (h ≥ m) passano da 119 (m = 1) a 36 (m = 2) e a 5 (m = 3) nella variante `with_ncsu_family` (32 e 4 nelle altre). m = 3 azzererebbe l'ammissibilità di 31 dei 36 tipi che m = 2 lascia ammissibili. **Limite:** h = siti indipendenti (audit 11 §2.3), non |ES_d|; non è un recall e non dice quanti fatti benigni si perdono.
- **Quello che si può dire:** m = 2 è la scelta minima che impedisce l'auto-ammissione di un sito singolo (N = 1: C_s = 1, score alto se persistente) e che rifiuta K = 1 a N = 2; m = 3 costa 31 tipi su 36. **Non si dice che m = 2 sia ottimale**, solo che m = 1 è inaccettabile a N ≤ 2 e m = 3 è molto costoso sui dati reali.

## B. K minimo ammesso dal solo punteggio (m = 1), K_min(h, ρ); r = 5/7
Margin to the supremum, beta*0.3/(1 + rho): rho = 1: 0.06000; rho = 2: 0.04000; rho = 5: 0.02000; rho = 10: 0.01091; rho = 100: 0.00119; rho = 1000: 0.00012; rho = 1000000: 0.00000

## Lettura (descrittiva)
- A ρ = 1 l'avversario ha poco volume e serve quasi K ≈ h (K_min = h + 1 per h ≤ 14); con ρ ≥ 10 la soglia si stabilizza e a ρ = 100 coincide con ρ = 10⁶ in tutte le righe della tabella: **ρ = 100 è già indistinguibile dal limite** sulla griglia di h mostrata, quindi la scelta ρ = 100 non pesa sui risultati del Criterion, ma non è una stima di volume avversario realistico (non lo dice).
- Il margine al supremo scende come 0,3·β/(1 + ρ): 0,06 (ρ = 1), 0,0109 (ρ = 10), 0,00119 (ρ = 100).
- Nota di costruzione: `bound_grid.population` dà a ogni avversario almeno ⌈ρh/K⌉ osservazioni, quindi n_a = K·⌈ρh/K⌉ ≥ ρh; per K vicino a h il volume effettivo supera ρh (per questo K_min(20, 1) = 19 < h).
- Il termine di volume non è mai saturato: C_t ≤ 1 per costruzione (0,7·d + 0,3·f ≤ 1), quindi `min(1, ·)` (`dib.py:279`) non ha effetto.
