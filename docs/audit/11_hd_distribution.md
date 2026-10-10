# Audit 11 — Forma in conteggi di Criterion 1 sul DIBScorer e distribuzione di h_d

Data: 2026-10-10. Branch `revision-tnsm`, worktree `/root/Desktop/DIB_tnsm`. Nessun file di produzione modificato. Notazione: [C] = verificato nel codice o nei dati (file:riga); [D] = deduzione.

## 1. Forma in conteggi sul DIBScorer reale (Fase 2)

Test: `analysis_fs/test_fstar_scorer.py`. Ipotesi, previsione e criterio di falsificazione sono nel docstring, scritti prima dell'esecuzione.

**Ipotesi H (utente).** Con (α, θ) = (0.6, 0.65), un fatto riportato solo da K siti avversari e mai dagli h siti onesti che osservano il tipo è ammesso se e solo se K > 5h/7 (pareggio escluso), anche con volume avversario ρ = 100. Per altre coppie il rapporto 5/7 diventa r = (θ+α−1)/(1−θ).

**Griglia.** K = 1..8, h = 0..20. Quattro coppie (α, θ): (0.6, 0.65) con r = 5/7, (0.7, 0.65) con r = 1, (0.6, 0.7) con r = 1, (0.55, 0.6) con r = 3/8. Due costruzioni, entrambe riusate:
- `bound_grid.population`: un giorno, volume avversario di almeno 100 volte quello onesto;
- `test_followup._flood`: tre giorni, l'avversario copre ogni giorno con `ceil(100h/K)` report per sito.

**Codice [C].** C_s = |S_e|/|ES_d| (`code/src/dib/evaluation/dib.py:276`). C_t = min(1, 0.7·giorni + 0.3·volume) (`:277-279`). score = α·C_s + β·C_t (`:281-285`). Ammissione in `admit_auto` (`:22-47`), con il quorum `min_reporting_sites` a `:45-46`.

**Esito.** 18 test: 10 passed, 8 failed. I fallimenti erano previsti e l'asserzione non è stata indebolita.

| Test | Esito | Contraddizioni di H |
|---|---|---|
| `test_h_score_only_m1` (quorum m = 1, solo score), 4 coppie × 2 costruzioni | 8 passed | nessuna su 168 celle per combinazione |
| `test_supremum_never_attained` (h ≥ 1: score < αK/(K+h)+β; volume avversario ≥ 100× onesto), 2 costruzioni | 2 passed | — |
| `test_h_operating_quorum_m2` (quorum operativo m = 2), 4 coppie × 2 costruzioni | **8 failed** | solo celle con K = 1, uguali nelle due costruzioni: |
| — (0.6, 0.65) | | (K,h) = (1,0) score 1.0; (1,1) score 0.6988 |
| — (0.7, 0.65) e (0.6, 0.7) | | (1,0) score 1.0 |
| — (0.55, 0.6) | | (1,0) 1.0; (1,1) 0.7237; (1,2) 0.6320 |

In tutte le contraddizioni lo score supera θ, |S_e| = 1, e il fatto è rifiutato dal quorum m = 2 (`dib.py:45-46`), non dallo score. Le celle coincidono con la previsione calcolata prima in aritmetica esatta. Coerente con `analysis_fs/test_followup.py::test_p0_5` (con due fonti, solo il quorum rifiuta).

**Lettura [D].**
1. Il solo score realizza esattamente "ammesso ⇔ K > r·h" sulla griglia, per tutte e quattro le coppie. H vale come proprietà dello score. Con il quorum operativo, la condizione corretta è "ammesso ⇔ K > r·h e K ≥ m". Per K ≥ 2 il quorum non cambia nulla nella griglia.
2. **Pareggio (0.6, 0.65), K = 5, h = 7: rifiutato con margine 0.00119 = 0.3β/101.** È lo scarto dovuto al volume finito (ρ = 100). Per ρ → ∞ lo score tende a θ dal basso: il supremum non è raggiunto e il fatto resta rifiutato, ma con un margine che tende a 0. [?] In virgola mobile, con ρ molto grande, l'arrotondamento potrebbe portare lo score a ≥ θ. Non testato.
3. **La direzione "se" dipende da ρ.** Il caso ammesso più vicino alla soglia, a (0.6, 0.65), è K = 8, h = 11 (share 0.421), con margine 0.00145. In aritmetica esatta servono ρ ≳ 45 perché sia ammesso. Con ρ più piccolo, K > 5h/7 non basta. La direzione "solo se" (K ≤ r·h ⇒ rifiutato) non dipende da ρ: è il Criterion 1.
4. Margini minimi dalla soglia nella griglia (costruzione a un giorno, K ≥ 2):

| (α, θ) | r | ammesso più vicino (score−θ; K, h) | rifiutato più vicino (θ−score; K, h) |
|---|---|---|---|
| (0.6, 0.65) | 5/7 | 0.00145; 8, 11 | 0.00119; 5, 7 |
| (0.7, 0.65) | 1 | 0.02245; 8, 7 | 0.00089; 2, 2 |
| (0.6, 0.7) | 1 | 0.01882; 8, 7 | 0.00119; 8, 8 |
| (0.55, 0.6) | 3/8 | 0.00144; 5, 13 | 0.00133; 3, 8 |

**Aggiornamento (decisione utente).** `test_h_operating_quorum_m2` è invariato e marcato `xfail(strict=True)` con motivazione "ipotesi H falsificata: il quorum respinge K = 1". Nuovo test `test_h_prime_with_quorum`, sulla stessa griglia e sul DIBScorer reale, con H' = "ammesso ⇔ K > r·h e K ≥ m" per m ∈ {1, 2}: **16 passed**. Stato del file: 26 passed, 8 xfailed. Formulazione corretta riportata in `docs/audit/09_f_s_derivazione_e_letteratura.md` (punto 4).

Riprodurre: `PYTHONPATH=code/src PYTHONDONTWRITEBYTECODE=1 timeout 300 python3 -m pytest analysis_fs/test_fstar_scorer.py -q -p no:cacheprovider` (~10 s).

## 2. Distribuzione di h_d (Fase 3)

Da completare.
