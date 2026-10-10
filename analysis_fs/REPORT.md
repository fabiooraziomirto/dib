# Analisi dell'assunzione f_s = 0,30 (Criterion 1)

Versione 2, 2026-10-10. Repo `DIB_clean`, branch `analysis-fs` (da `formal-ae` @ `cd3b5fa`). Sola analisi: nessun file di produzione, nessuna delle due versioni di `main.tex`, `formal/`, `claims.json`, `results/` o `configs/` è stato modificato. Tutti i file nuovi stanno in `analysis_fs/`.

**Paper di riferimento.** "paper:N" significa `/root/Desktop/DIB_reframe/docs/main.tex` (853 righe). L'altra versione, `DIB_reframe/main.tex` (771 righe), è indicata come "old:N"; le differenze sono in §9.

**Notazione.** [C] = trovato nel codice o nei dati (file:riga). [D] = mia deduzione. [?] = incerto.

**Nota su CLAUDE.md.** Il CLAUDE.md del progetto chiede di scrivere i risultati in `docs/audit/`. Su tua indicazione ho scritto solo in `analysis_fs/`. Proposta, non eseguita: copiare questo file in `docs/audit/07_assunzione_fs.md` (gli audit esistenti arrivano a 06).

## Riprodurre (dalla root della repo)

| Comando | Tempo | Note |
|---|---|---|
| `PYTHONPATH=code/src python3 -m pytest analysis_fs -q -p no:cacheprovider` | ~1 s | 32 passed |
| `PYTHONPATH=code/src python3 analysis_fs/bound_grid.py` | ~13 s | |
| `PYTHONPATH=code/src python3 analysis_fs/hd_heterogeneity.py` | ~3,5 min | dati in `/root/Desktop/DIB/data/processed` (fuori repo) |
| `python3 analysis_fs/hd_coverage.py` | <1 s | legge `out/hd_by_device.csv` |
| `python3 analysis_fs/finite_n.py` | <1 s | |
| `PYTHONPATH=code/src python3 analysis_fs/a2_raw_k.py` | ~3 min | 5 processi, ~26 GB RAM |
| `PYTHONPATH=code/src python3 analysis_fs/worst_case_real.py` | ~2,5 min | |
| `PYTHONPATH=code/src python3 analysis_fs/mitigations.py` | ~2,5 min | |

Calcolo totale speso in questa sessione: circa 22 min. La cifra comprende due run interrotti e rilanciati: il worst-case con ρ=1000 era troppo lento, e le mitigazioni sono state rifatte per le date spurie (§7).

---

## 0. Correzioni rispetto alla versione 1

1. **Errore numerico nella riformulazione (segnalato da te).** La v1 diceva "with h_d=3, two colluders exceed 5/12". È falso: 2/5 = 0,40 < 5/12. Con h_d=3 si tollerano 2 colluder al limite 5/12 e 1 a f_s=0,30; il limite viene superato solo con k=3 (quota 1/2). Corretto in `reformulation_fs.md`.

   Ho ricontrollato con Fraction ogni numero del file (`test_p0_1`, `test_p0_3`). La tabella sotto usa k_tol(5/12) = max k con k/(k+h) < 5/12 e k_tol(f_s) = max k con k/(k+h) ≤ 0,30:

   | h_d | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
   |---|---|---|---|---|---|---|---|---|
   | k_tol 5/12 | 0 | 1 | 2 | 2 | 3 | 4 | 4 | 5 |
   | k_tol f_s=0,30 | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |

   Quote k/(k+h) per k=0..5: h=3: 0, 1/4, 2/5, 1/2, 4/7, 5/8. h=7: …, 5/12 (pareggio, escluso con la disuguaglianza stretta). Le quote per tutti gli h sono in `test_followup.py`.

2. **Requisito di copertura** (`test_p0_2`). Per tollerare k colluder in un tipo servono h_d > 7k/5 siti onesti al limite 5/12 e h_d ≥ 7k/3 a f_s=0,30.

   | k | 1 | 2 | 3 | 4 | 5 |
   |---|---|---|---|---|---|
   | h_d minimo, 5/12 | 2 | 3 | 5 | 6 | 8 |
   | h_d minimo, f_s | 3 | 5 | 7 | 10 | 12 |

3. **Precisazioni su quorum e N piccolo.**
   - (a) Con h_d=2, k=1 ha quota 1/3, sotto 5/12. Lo score da solo lo respinge (al massimo 0,2+0,4 = 0,6) e il quorum m=2 lo blocca comunque (`test_p0_4`). Il rischio reale parte da k=2, quota 1/2. "f_s=0,30 non realizzabile con h_d=2" riguarda solo l'assunzione dichiarata (la più piccola quota non nulla è 1/3 > 0,30), non la sicurezza.
   - (b) **Cold-start a tre lab: l'unica fonte di rifiuto di un avversario solo-sorgente è il quorum. Determinabile [C].**
     - Il cold-start non usa `DIBScorer`: usa una sua reimplementazione, `code/scripts/moniotr_cross_lab.py:324-373`, richiamata da `v28_matched_ablation.py:37,48`. La regola è `value >= 0.65 and (not gate or portable) and len(supporters) >= 2` (:372). Con il ricevente escluso, le sorgenti sono 2 (`results/three_lab_matched/README.md`).
     - [D] Se una sorgente è avversaria e l'altra osserva il tipo, C_s = 1/2 e score = 0,3+0,4·C_t: con C_t ≥ 0,875 si supera θ. Se il tipo è osservato solo dalla sorgente avversaria, C_s = 1. In entrambi i casi lo score non respinge; respinge solo il quorum (|S_e| ≥ 2). Verificato con `DIBScorer` nella stessa forma (2 siti, 1 avversario che inonda il volume: score ≥ 0,65 ma `accepted=False` per il quorum, `test_p0_5`). [?] Non ho verificato riga per riga che la reimplementazione coincida con DIBScorer; lo script dichiara di riprodurre i conteggi.
     - Con 2 sorgenti, quando il quorum passa vale sempre |S_e| = |ES_d|, cioè C_s = 1, e lo score filtra solo tramite C_t ≥ 0,125.

4. **Tabella h_d ridimensionata (§4).** Nei corpus con 1–3 siti, "k=3 supera 5/12 per il 100% dei tipi" segue da N piccolo, non è un risultato su consorzi reali. Ora riporto il k_tol mediano e la quota di tipi che soddisfano il requisito di copertura per k=1,2,3. Inoltre: lo 0/3807 di `bound_grid.py` è un test codice-contro-formula-chiusa su popolazioni sintetiche, non una misura su dati.

5. **Coerenza su H3.** In tutto il report e nella riformulazione la formulazione è ora uniforme: **il bound è un sup, mai raggiunto finché almeno un sito onesto osserva d**. A f = 5/12 esatto il pareggio non è raggiungibile. Questo corregge l'ipotesi iniziale; per la frase del Criterion vedi §9. C'è anche un esempio su dati reali: in `worst_case_real` (BlipCare, h=7, H2, k=5) la quota è esattamente 5/12, e nessuna ammissione avviene fino a ρ=100 (ρ* = ∞).

6. **Formula sbagliata nella v1 §5.** Avevo scritto "basta k ≥ ⌈5h_d/7⌉". La condizione corretta è **k > 5h_d/7**: con h=7, k=5 è il pareggio, che non viene ammesso.

7. Resta valida la nota della v1: nella prima stesura di `test_h1` il valore atteso era sbagliato per colpa mia (">0,999" invece di 0,99880). Il codice di produzione non c'entra.

## 1. Mappa del codice

| File | Ruolo |
|---|---|
| `code/src/dib/evaluation/dib.py` | `admit_auto` (:22-47: quorum, `score >= theta`, eligibilità, `open_dispute`); ES_d/S_de (:198-199); C_s (:276); C_t (:277-279); quarantena (:162-185, :195-205); varianti trust/cluster (:257-274) |
| `code/src/dib/evaluation/intent_overlap.py` | `classify_core` (:81-110): eligibilità A(e) |
| `code/src/dib/registry/services.py` | Config del punto operativo (:43-45); ingestione senza controlli (:71-121); ricalcolo dell'ammissione (:247-271); `query_score` richiede ACTIVE (:439); `dispute_score` (:615-667) |
| `code/src/dib/registry/api.py` | Endpoint HTTP; `site_id` nel payload, nessuna autenticazione |
| `code/src/dib/registry/distributed/service.py` | Dispute/fan-out distribuito (:748-770) |
| `code/src/dib/analysis/poison_bound.py` | Bound analitico (:86-118) |
| `code/src/dib/experiments/poisoning.py` | A2 limitato (:10-98), Sybil (:101, :149, :237, :332) |
| `code/src/dib/experiments/compromised_baseline.py`, `code/scripts/a1_*.py` | A1 |
| `code/src/dib/experiments/drift.py`, `code/scripts/nonstationarity_drift_sweep.py` | A3 |
| `code/src/dib/evaluation/trust.py`, `independence.py` | Mitigazioni Sybil |
| `code/scripts/sybil_*.py`, `adaptive_sybil_whole_registry.py` | Sybil e padding |
| `code/scripts/dispute_flood.py` | Flood di dispute |
| `code/scripts/service_masquerade_probe.py` | A2 con porte mascherate, fonte di 0,562 |
| `code/scripts/moniotr_cross_lab.py:324-373`, `v28_matched_ablation.py` | Cold-start a tre lab (scoring reimplementato) |
| *(fuori repo)* `/root/Desktop/DIB/reports/item1_private_ip_filter/poisoning_multiseed_full_coverage.py` | A2 a 20 seed. Copia invariata in `analysis_fs/orig/`, sha256 `824d6b92…b2d7` |

## 2. Verifica delle ipotesi H1–H7 (v1, confermata)

| # | Esito | Evidenza [C] | Test |
|---|---|---|---|
| H1 Nessun cap per sito, bound stretto | Confermata. Il bound è un sup, mai raggiunto con onesti presenti | dib.py:278 (nessuna normalizzazione per sito); D_d è l'unione dei giorni di tutti i siti (:204); gap ≈0,001 a ρ=100 | `test_h1_*` |
| H2 ES_d auto-dichiarato | Confermata, scorer e registry | dib.py:198; services.py:73, :92, :263-266. k=3 nuovi siti contro h=4 vengono ammessi | `test_h2_*` |
| H3 Pareggio a 5/12 | Smentita nella sostanza | In float `0.6*(5/12)+0.4 == 0.65` e il confronto è `>=` (dib.py:47), ma serve C_t = 1, impossibile con onesti presenti | `test_h3_*` |
| H4 Arrotondamento | Confermata | poisoning.py:24, :76 (`int(round())`): f=0,05 dà 0 avversari; avversari estratti da tutti i siti, non da ES_d | `test_h4_*` |
| H5 N=10, k=4 | Confermata. Ora anche nei dati raw, §5 | sup 0,64 | `test_h5_*`, `test_p1_real_*` |
| H6 Superfici fuori da f_s | Confermata | lo scorer non riceve `open_dispute` (dib.py:297-303); bastano 2 dispute senza evidenza (services.py:643-664); eligibilità permissiva (intent_overlap.py:101-109) | `test_h6*` |
| H7 Refuso | Confermato | paper:177 "A1 tests -----." | — |

## 3. Griglia del bound (`bound_grid.py`)

**Cosa misura:** un test codice-contro-formula-chiusa su popolazioni sintetiche (N=4..50, tutti i k, α∈{0,5; 0,6; 0,7}, ρ=100). Non è una misura su dati reali.

Risultati: 0/3807 violazioni e 3807/3807 coincidenze con la formula; il gap minimo è ≈0,001, quindi il bound è un sup mai raggiunto.

| N | 4 | 5 | 6 | 7 | 10 | 12 | 20 | 24 | 30 | 50 |
|---|---|---|---|---|---|---|---|---|---|---|
| k_max dal bound | 1 | 2 | 2 | 2 | 4 | 4 | 8 | 9 | 12 | 20 |
| k_max con DIBScorer, ρ=100 | 1 | 2 | 2 | 2 | 4 | 5 | 8 | 10 | 12 | 20 |
| ⌊0,30·N⌋ | 1 | 1 | 1 | 2 | 3 | 3 | 6 | 7 | 9 | 15 |

Le differenze a N=12 e N=24 sono celle di pareggio: il bound non garantisce nulla, ma il sup non viene raggiunto.

## 4. Eterogeneità di h_d (`hd_heterogeneity.py`, `out/hd_coverage_requirement.csv`)

k_tol è calcolato contando h_d onesti più k colluder aggiunti. La colonna "cov k" riporta la quota di tipi che soddisfano il requisito di copertura (h_d > 7k/5 per 5/12, h_d ≥ 7k/3 per f_s).

| Corpus | Tipi | h_d med | k_tol 5/12 med | k_tol f_s med | cov k=1 (5/12 / f_s) | cov k=2 | cov k=3 |
|---|---|---|---|---|---|---|---|
| Mon(IoT)r, US/UK unificati | 59 | 1 | 0 | 0 | .44 / 0 | 0 / 0 | 0 / 0 |
| Mon(IoT)r, 4 capture tree | 59 | 2 | 1 | 0 | 1 / .44 | .44 / 0 | 0 / 0 |
| YourThings | 46 | 1 | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Tre lab US/UK/YT | 6 | 3 | 2 | 1 | 1 / 1 | 1 / 0 | 0 / 0 |
| Real federation, 6 etichette | 10 | 2,5 | 1,5 | 0,5 | 1 / .5 | .5 / .4 | .4 / 0 |
| Real federation, org indipendenti | 10 | 2 | 1 | 0 | 1 / .4 | .4 / 0 | 0 / 0 |
| UNSW 10 pseudo-siti, seed 0–19 | 540 | 10 | 7 | 4 | 1 / .96 | .96 / .96 | .96 / .94 |

[D] Lettura corretta:
- I corpus con 1–3 siti non sono consorzi: dicono solo che con N così piccolo il "k tollerato" è 0–2 per costruzione.
- L'unico corpus con N=10 è la partizione UNSW, IID per costruzione. Lì il requisito per k=3 è soddisfatto dal 96% delle coppie tipo×seed; mancano NetatmoWeatherStation (h=2) e in parte BlipCareBPMeter (h=4–8).
- Nessun corpus rappresenta un consorzio reale con N ≥ 10 organizzazioni indipendenti per tipo.

## 5. Sensibilità con N finito (`finite_n.py`)

Invariata rispetto alla v1, con una correzione: con H2 l'ammissione è possibile se e solo se **k > 5h_d/7** (con k ≥ 2). Valori principali:
- n = |ES_d| = 4, p = 0,3 → P_admissible ≈ 0,35 per ogni N;
- n = N = 100, p = 0,3 → P_unsafe binomiale 0,007, ipergeometrica 0;
- N=10, k=3, n=2 → 8/120 = 0,067 (il caso Netatmo).

Il rischio dipende da |ES_d|, non da N.

## 6. A2 in raw breadth con k espliciti (`a2_raw_k.py`)

**Setup.** Copia modificata dello script multiseed: raw breadth, θ=0,65, m=2, successo = `accepted` di DIBScorer (≥). Seed 0–19, partizione random su 10 pseudo-siti, fabbricazione single-shot. Gli avversari sono k=0..5 estratti **dall'ES_d del tipo**, con k_d = min(k, |ES_d|). Nessun tipo è escluso.

Massimo per seed sui 25 tipi a copertura piena (|ES_d| = 10), statistiche su 20 seed (`out/a2_raw_k_summary.csv`):

| k (f=k/10) | media ± sd | max | ammissioni | Paper/log, trust-weighted [C] | Differenza |
|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | f=0,05: 0,000 (=0 avversari) | coincide: f=0,05 era k=0 |
| 1 | 0,1177 ± 0 | 0,1177 | 0 | 0,118 / max 0,118 (log) | ≈ |
| 2 | 0,2255 ± 0,011 | 0,2354 | 0 | 0,227 / 0,236 (log) | −0,002 / −0,001 |
| 3 | 0,3174 ± 0,022 | 0,3531 | 0 | **0,321 ± 0,026 / 0,354** (old:451-455) | −0,004 / −0,001 |
| 4 | 0,4033 ± 0,020 | 0,4267 | 0 | 0,409 / 0,472 (log) | −0,006 / **−0,045** |
| 5 | 0,4742 ± 0,034 | 0,5322 | 0 | **0,490 ± 0,019 / 0,534** (old:451-455) | −0,016 / −0,002 |

Note:
- I numeri 0,321/0,490/0,534 compaiono solo in old:451-455. In `docs/main.tex` restano 0,354 (paper:631, "one-day horizon") e 0,562.
- Con raw breadth i valori cambiano poco, sempre al ribasso. Il massimo a k=4 scende di 0,045.
- In raw breadth C_s = k/10 esatto per tutti i tipi a copertura piena (`test_p1_real_k0_and_k_le4…`).

Tipi a bassa copertura (`out/a2_raw_k_low_coverage.csv`), riportati a parte e non esclusi:

| Tipo | \|ES_d\| per seed | k | Quota k_d/\|ES_d\| | Max score | Ammessi / 20 |
|---|---|---|---|---|---|
| NetatmoWeatherStation | 2 (tutti i seed) | 1 | 0,5 | 0,48 | 0 (quorum) |
| NetatmoWeatherStation | 2 | 2–5 | 1,0 | 0,94 | **20** |
| BlipCareBPMeter | 4–8 | 2 | 0,25–0,5 | 0,39 | 0 |
| BlipCareBPMeter | 4–8 | 3 | 0,375–0,75 | 0,583 | 0 |
| BlipCareBPMeter | 4–8 | 4 | 0,5–1,0 | 0,774 | 2 |
| BlipCareBPMeter | 4–8 | 5 | 0,625–1,0 | 0,815 | 11 |

[D] Nello script originale Netatmo era coperto in 3/20 seed perché gli avversari erano estratti da tutti i 10 siti. Qui è coperto 20/20 per costruzione, perché gli avversari sono estratti da ES_d. Le due frequenze non sono confrontabili: misurano cose diverse. Tutte le ammissioni hanno quota ≥ 0,8, quindi sono fuori dall'assunzione; nessuna viola l'algebra.

**Controlli (Passo 1.4):**
- k=0 → 0 avversari ✔;
- k=4 con |ES_d|=10 → 0 ammissioni ✔;
- k=5 single-shot → 0 ammissioni ✔, ipotesi H-A2.3 confermata;
- k=5 viene ammesso con persistenza e flood sufficienti: 125/125 celle già con ρ ≤ 2 (§7).

## 7. Worst-case su dati reali (`worst_case_real.py`)

**Setup.**
- UNSW, seed 0–4, 27 tipi. I tre lab (N=3) sono riportati solo per k_tol (§4).
- Strategia: i k avversari riportano il fatto falso in ogni giorno di D_d, con volume ρ·n_d e ρ ∈ {1, 2, 5, 10, 20, 50, 100}. Scoring con `DIBScorer` reale.
- [D] Per stare nei tempi ho usato una popolazione ridotta: una riga onesta per coppia (sito, giorno), che conserva esattamente ES_d, D_d e il rapporto di volume. L'equivalenza è verificata con DIBScorer sulla popolazione **completa** a ρ=1: 27/27 tipi. Inoltre ogni score coincide con la formula chiusa al ρ realizzato (assert per tutte le 5565 righe). 0/795 celle sono incoerenti con ρ*.

Risultati per i tipi con |ES_d| = 10 (125 celle tipo×seed per riga):

| Variante | Livello | k | Quota | Max score | Bound | Ammesse | ρ min di ammissione (ρ* analitico) |
|---|---|---|---|---|---|---|---|
| insider | k_fs | 3 | 0,300 | **0,5788** | 0,58 | 0 | — (∞) |
| insider | k_tol | 4 | 0,400 | 0,6388 | 0,64 | 0 | — (∞) |
| insider | k_tol+1 | 5 | 0,500 | 0,6989 | 0,70 | **125** | 1–2 (1,40) |
| H2 (nuovi id) | k_fs | 4 | 0,286 | 0,5703 | 0,571 | 0 | — |
| H2 | k_tol | 7 | 0,412 | 0,6459 | 0,647 | 0 | — |
| H2 | k_tol+1 | 8 | 0,444 | 0,6655 | 0,667 | **125** | 5–10 (6,20) |

Tipi con |ES_d| < 10:
- insider k_tol+1: 5/10 celle ammesse; le altre 5 sono Netatmo con k=1, bloccate dal quorum. ρ ≤ 20, ρ* fino a 15,8.
- H2 k_tol+1: 8/10 ammesse. Le 2 non ammesse sono BlipCare con h=7 e k=5, quota **esattamente 5/12**: ρ* = ∞, il sup non viene raggiunto (H3 su dati reali).

Esito delle ipotesi W1–W4:
- **W1 confermata:** a k_tol nessuna ammissione, per ogni ρ e in entrambe le varianti.
- **W2 confermata:** a k_tol+1 l'ammissione avviene da ρ ≥ ρ*.
- **W3 confermata:** H2 lascia invariata l'aritmetica delle quote, ma rende l'attacco possibile senza possedere il tipo; è riuscito su tutti i 25 tipi a copertura piena con k=8.
- **W4 confermata. "0,562 è il massimo a f_s=0,30" (paper:631) va corretto.** Il massimo osservato con k=3 di 10 è **0,5788** (0,5439 a ρ=1, 0,5705 a ρ=10), a 0,0012 dal bound 0,58. Lo 0,562 è il massimo della strategia testata (120 giorni, 1 riga al giorno, trust-weighted), non del modello di minaccia.

## 8. Opzioni di mitigazione, solo valutazione (`mitigations.py`)

**Setup.** Reimplementazione dello scoring con due varianti opzionali. La versione base coincide con DIBScorer su 4504/4504 chiavi (UNSW, seed 42; `test_p3_base…`). Dati: tolte 5 righe datate 1970–1990 (artefatto, §9). La base risultante ammette 354 fatti, contro 349 con quelle righe.

| Opzione | Sup avversario (peggior caso) | τ equivalente | Costo sul recall UNSW (354 ammessi) | Tocca la formula del paper? |
|---|---|---|---|---|
| (a) Quarantena per anzianità, first-seen **dai timestamp** (com'è in dib.py:166-173) | invariato: insider k=5 → 0,6998, 19/25 ammessi; H2 k=8 → 0,6666, 11/25 | 5/12 (invariato) | 0 persi con T ≤ 90; 203 persi con T = intero periodo; 354 con T > periodo | Sì: cambia quali righe entrano in D_d e n_d |
| (a') Quarantena, first-seen **dalla registrazione** (ipotetica) | H2 → α·quota = 0,267, 0/25 ammessi; insider invariato (0,6998) | nessuna quota ammissibile per i nuovi arrivati (α=0,6 < θ); 5/12 per gli insider | non misurabile su UNSW: tutti i pseudo-siti hanno la stessa data di ingresso [D] | Sì, come (a) |
| (b) Cap c righe per sito per (d,e) | k=3 (f_s): 0,48 / 0,497 / 0,558 per c = 1 / 10 / 100; k=5: 0,61 / 0,631 / 0,686 (0, 0, 4 ammessi); H2 k=8: 0,588 / 0,612 / 0,657 (0, 0, 2) | peggior caso sui dati: 0,514 (c=1), 0,486 (2), 0,455 (5), 0,439 (10), 0,419 (100), 0,417 (1000) | 0 persi, +1 guadagnato per c ≤ 100; 0 per c = 1000 | Sì: cambia la definizione di n_de e n_d nell'eq. ct |

[C][D] Una scoperta laterale:
- Il commento a dib.py:107-110 dice che la quarantena per anzianità "cannot be forged … the registry knows a site's registration date by construction". Ma il codice calcola la data di primo ingresso dai **timestamp delle osservazioni**, che sono auto-dichiarati (dib.py:166-173).
- Un avversario che copre tutti i giorni di D_d risulta quindi "anziano" e non viene messo in quarantena (`test_p3_tenure_timestamp_forgeable…`).
- In più la variante richiede `trust_weighted` (dib.py:126-130); qui l'ho valutata in raw breadth.

[D] Sintesi delle opzioni: il cap riduce il contributo del flood (al massimo 0,12) con costo di recall nullo su UNSW, ma non tocca la copertura dei giorni (0,7·β = 0,28). La quarantena basata sulla registrazione neutralizza H2 ma non gli insider. Nessuna delle due cambia la natura di "sup" del bound per gli insider.

## 9. Discrepanze (aggiornate)

| # | Stato | Discrepanza |
|---|---|---|
| 1 | Aperta | **Esclusione per copertura non dichiarata in paper.** Il run originale esclude `eligible_sites != 10` (orig:57-59); Netatmo arriva a 0,94 a f nominale 0,30. old:446-449 lo dichiarava, paper non lo menziona. Ora quantificato in §6 |
| 2 | Aperta | **Trust vs raw.** I numeri A2 e lo 0,562 vengono da run trust-weighted (`results/masquerade/manifest.json:45`, C_s = 0,30124), mentre il paper dice che il Criterion si applica alla raw breadth (paper:414). In raw breadth i valori sono leggermente più bassi (§6) |
| 3 | Aperta | **"Largest score 0,562 at f_s=0,30"** (paper:631): il worst-case reale dà 0,5788 (§7) |
| 4 | Aperta | f=0,05 sono 0 avversari (poisoning.py:24), ma paper:627 elenca .05 tra le frazioni testate |
| 5 | Aperta | "Reducing the influence of high traffic volume from a single reporter" (paper, dopo l'eq. ct): nessuna normalizzazione per sito (dib.py:278) |
| 6 | Aperta | ¬openDispute è nella formula di ammissione, ma lo scorer non lo valuta (dib.py:297-303); è applicato tramite lo stato nel registry (services.py:439) |
| 7 | Aperta | ES_d auto-dichiarato (services.py:71-121); paper:172 parla solo di allineamento delle etichette |
| 8 | Aperta | Script multiseed fuori repo, con θ=0, m=1 e `>` (orig:59-60, :86-90). Ora esiste una copia corretta in `analysis_fs/a2_raw_k.py` |
| 9 | Nuova | Il cold-start usa uno scoring reimplementato (`moniotr_cross_lab.py:324-373`), non DIBScorer; lì la protezione da un avversario solo-sorgente è solo il quorum |
| 10 | Nuova | La quarantena per anzianità calcola la data di ingresso dai timestamp (falsificabile), in contrasto con il commento a dib.py:107-110 |
| 11 | Nuova | **Date spurie nei dati UNSW**: 8 righe su 1.268.020 sono anteriori al 2016-09-01, di cui 5 datate 1970–1990 e 3 tra 2010-08 e 2016. Il periodo risultante è 17.269 giorni (2438 senza le righe precedenti al 2000), mentre il periodo principale, 2016-09 → 2017-04-13, è di circa 7 mesi. Allungano D_d per alcuni tipi; togliere solo le 5 righe porta i fatti ammessi da 349 a 354 (raw, seed 42). [?] Effetto sui numeri del paper non quantificato |
| 12 | Nuova | `docs/main.tex` non contiene più 0,321/0,490/0,534; si trovano solo in old:451-455 |
| 13 | Aperta | Refuso paper:177 |
| 14 | Chiusa | H3: la frase "tie admitted" (old:402) è conservativa, non sbagliata; paper:405 dice già "strictly below θ". Il sup non viene raggiunto |

**Le due versioni di main.tex sulle stesse affermazioni:**

| Affermazione | `docs/main.tex` | `DIB_reframe/main.tex` (old) |
|---|---|---|
| Definizione di f | "fraction f_s of the eligible reporting population for a device type" (172) | "at most 30% of authorized sites for a device" (abstract, old:39); "eligible contributor … authorized and included" (old:107) |
| Pareggio | "fall strictly below θ" (405) | "an exact tie is admitted and therefore unprotected" (old:402) |
| Esclusione per copertura | assente | dichiarata, con il caso 3/20 (old:446-449) |
| Numeri A2 | 0,354 e 0,562 (631) | 0,289/0,315 graph, 0,321/0,490/0,354/0,534 (old:451-455) |
| Raw breadth | "registry and independent-deployment experiments use raw breadth" (414) | non specificato per A2 |

## 10. Piano (aggiornato)

| # | Azione | Stato |
|---|---|---|
| 1 | Riformulazione per tipo, con requisito di copertura e quorum | Testo pronto (`reformulation_fs.md`) |
| 2 | Dichiarare l'esclusione per copertura e passare ai numeri raw | Numeri pronti (§6). Decisione editoriale tua |
| 3 | k espliciti invece delle frazioni | Fatto (§6) |
| 4 | Worst-case su dati reali | Fatto (§7). Correggere lo 0,562 |
| 5 | Mitigazioni | Solo valutate (§8), senza raccomandazione |
| 6 | Indagare le date spurie e rifare i numeri sensibili a D_d | Da fare: rischio basso, costo medio |
| 7 | Portare in repo lo script e i dati del run multiseed | `analysis_fs/orig/` contiene la copia; gli output originali restano fuori repo |

## Riassunto

1. L'algebra del Criterion 1 regge sia su dati sintetici (0/3807) sia su dati reali (0/795 celle incoerenti). Il bound è un sup mai raggiunto e il pareggio a 5/12 non viene ammesso; c'è anche un caso reale (BlipCare, H2).
2. Correggere "0,562 è il massimo a f_s=0,30": il worst-case reale arriva a 0,5788 (bound 0,58). k=5 di 10 viene ammesso in 125/125 celle già con ρ ≤ 2.
3. Raw breadth contro trust-weighted: k=3 dà 0,317/0,353 (contro 0,321/0,354), k=5 dà 0,474/0,532 (contro 0,490/0,534). Differenze piccole, ma i run del paper non sono in raw breadth.
4. Bassa copertura: Netatmo (|ES_d|=2) ammesso 20/20 con k ≥ 2 (quota 1,0); BlipCare ammesso solo con quota ≥ 0,8. Va dichiarato, non escluso.
5. H2: l'attacco con k=8 nuovi id contro h=10 riesce su 25/25 tipi. Lo neutralizza solo una quarantena basata sulla data di registrazione, che il codice non ha: quella attuale è falsificabile.
6. Cold-start a 2–3 sorgenti: contro l'avversario solo-sorgente protegge il quorum, non lo score.
7. La riformulazione è corretta: tabella con Fraction, requisito h_d > 7k/5 (5/12) e h_d ≥ 7k/3 (f_s).
