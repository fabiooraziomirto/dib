# Analisi dell'assunzione f_s = 0,30 (Criterion 1)

Versione 3, 2026-10-10 (v2: commit `7c056ef`). Repo `DIB_clean`, branch `analysis-fs`, creato da `formal-ae` @ `6ed220e` (la v1/v2 diceva `cd3b5fa`: sbagliato). Attenzione: la working tree è condivisa con un'altra sessione, i cui commit `2f1f2e4` e `52dcff6` (`formal:`/`docs: audit 07`) sono finiti su `analysis-fs` e non su `formal-ae`; non li ho spostati. Sola analisi: nessun file di produzione, nessuna delle due versioni di `main.tex`, `formal/`, `claims.json`, `results/` o `configs/` è stato modificato. Tutti i file nuovi stanno in `analysis_fs/`.

**Paper di riferimento.** "paper:N" significa `/root/Desktop/DIB_reframe/docs/main.tex` (853 righe). L'altra versione, `DIB_reframe/main.tex` (771 righe), è indicata come "old:N"; le differenze sono in §9.

**Notazione.** [C] = trovato nel codice o nei dati (file:riga). [D] = mia deduzione. [?] = incerto.

**Nota su CLAUDE.md.** Il CLAUDE.md del progetto chiede di scrivere i risultati in `docs/audit/`. La copia di questo file è in `docs/audit/08_assunzione_fs.md`, con un commit separato: il numero 07 è già occupato da `07_modello_ae.md` e il 04 è riservato al piano di misure (`05_reconcile_trigger_fanout.md`). Nella copia cambiano solo il titolo e una riga di provenienza (formato `# Audit NN — …`).

## Riprodurre (dalla root della repo)

| Comando | Tempo | Note |
|---|---|---|
| `PYTHONPATH=code/src python3 -m pytest analysis_fs -q -p no:cacheprovider` | ~2 s | 40 passed, 1 xfailed (§11) |
| `PYTHONPATH=code/src python3 analysis_fs/bound_grid.py` | ~13 s | |
| `PYTHONPATH=code/src python3 analysis_fs/hd_heterogeneity.py` | ~3,5 min | dati in `/root/Desktop/DIB/data/processed` (fuori repo) |
| `python3 analysis_fs/hd_coverage.py` | <1 s | legge `out/hd_by_device.csv` |
| `python3 analysis_fs/finite_n.py` | <1 s | |
| `PYTHONPATH=code/src python3 analysis_fs/a2_raw_k.py [--workers 2]` | 353 s | 2,68 GiB (§13) |
| `PYTHONPATH=code/src python3 analysis_fs/worst_case_real.py [--workers 2]` | 106 s | 3,37 GiB (§13) |
| `PYTHONPATH=code/src python3 analysis_fs/mitigations.py [--workers 2]` | 95 s | 3,72 GiB (§13) |
| `PYTHONPATH=code/src python3 analysis_fs/spurious_dates.py [--workers 3]` | 419 s | 7,08 GiB, 3+1 processi (§11) |
| `PYTHONPATH=code/src python3 analysis_fs/spurious_trust_seed42.py` | 56 s | 1,75 GiB (§11) |
| `PYTHONPATH=code/src python3 analysis_fs/netatmo_sampling.py` | 202 s | 1,35 GiB (§12) |
| `python3 analysis_fs/measure.py <label> -- <comando>` | — | misura tempo e picco RSS dell'albero di processi, scrive `out/measurements.csv` |

Calcolo della sessione v2: circa 22 min (v3: §13). La cifra comprende due run interrotti e rilanciati: il worst-case con ρ=1000 era troppo lento, e le mitigazioni sono state rifatte per le date spurie (§7).

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
| 11 | Chiusa (v3) | **Date spurie nei dati UNSW**: 8 righe in 3 tipi. Effetto puro sulle ammissioni nullo (§11). **Correzione della v2:** il passaggio 349 → 354 attribuito alle date dipende dal rimescolamento della partizione (`mitigations.py` filtra prima di `partition_observations`); a parità di partizione la variazione è 0 |
| 12 | Nuova | `docs/main.tex` non contiene più 0,321/0,490/0,534; si trovano solo in old:451-455 |
| 13 | Aperta | Refuso paper:177 |
| 14 | Chiusa | H3: la frase "tie admitted" (old:402) è conservativa, non sbagliata; paper:405 dice già "strictly below θ". Il sup non viene raggiunto |
| 15 | Nuova | Il commento a `dib.py:107-110` dice che la quarantena si basa sulla data di registrazione, ma il codice usa i timestamp dichiarati (`dib.py:166-173`). Segnalato, non corretto (punto C3) |
| 16 | Nuova (v3) | Ipotesi S3 smentita: togliere le 8 righe cambia la breadth di qualche sito in 19 seed su 21 e la breadth di riferimento in 8; in trust weighting si muovono anche altri tipi (seed 42: 3738 score, max 4,9·10⁻⁵, 346 → 346) |

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

## 11. Date spurie nei dati UNSW (punto A, `spurious_dates.py`, `spurious_trust_seed42.py`)

**Le righe [C]** (`out/spurious_rows.csv`). Sono identiche nei due file: riga in `observations_enriched.csv` / riga in `observations_enriched_item1fixed.csv`. Tutte hanno `site_id = unsw-iotraffic-2025`.

| Riga enriched / item1fixed | device_type | endpoint (fqdn o IP), proto/porta | timestamp |
|---|---|---|---|
| 137970 / 102970 | AugustDoorBell | doorbells.august.com, tcp/443 | 1981-01-21 |
| 558139 / 431045 | AugustDoorBell | dmsv2.video-cloud.net, tcp/443 | 1982-07-31 |
| 1693545 / 869484 | NestDropCam | 52.87.241.159, syslog/443 | 1970-07-15 |
| 1693546 / 869485 | NestDropCam | 52.87.241.159, tcp/443 | 1990-11-26 |
| 1693562 / 869488 | NestDropCam | 52.87.241.159, tcp/443 | 2010-08-10 |
| 1693808 / 869588 | NestDropCam | 52.87.241.159, tcp/443 | 2011-08-20 |
| 2162894 / 1187986 | WithingsSleepSensor | 89.30.121.22, tcp/5222 | 2012-08-17 |
| 2182503 / 1197642 | WithingsSleepSensor | 89.30.121.26, syslog/5222 | 1970-01-01 |

Il periodo "buono" va dal 2016-09-22 al 2017-04-13 (179 giorni distinti). Effetto su |D_d|:

| Tipo | Righe del tipo | \|D_d\| con le spurie | \|D_d\| senza | Bound sull'aumento di score (0,28·(\|D_d\|/\|D_d'\| − 1)) |
|---|---|---|---|---|
| AugustDoorBell | 642.734 | 110 | 108 | 0,0052 |
| NestDropCam | 926 | 93 | 89 | 0,0126 |
| WithingsSleepSensor | 20.276 | 89 | 87 | 0,0064 |

**Chi usa il file [C].**
- `observations_enriched.csv` è l'input di default di 26 script in `code/scripts/` (grep su `observations_enriched`) e di 9 directory di `results/` per dichiarazione del manifest: a1, a1_baselines, a1_resolvable, ablation_multiseed, cold_start, masquerade, recall, sybil, sybil_jaccard. `results/drift` non ha manifest, ma lo script `nonstationarity_drift_sweep.py:87` legge questo file per default. Per `results/quorum`, `site_quorum_sensitivity.py:49` richiede `--observations` esplicito: `results/quorum/README.md` (come `results/drift/README.md`) cita `observations_enriched.csv`; [?] non verificato per hash.
- `observations_enriched_item1fixed.csv` è l'input del run multiseed A2 (fuori repo) e dei miei script `a2_raw_k.py`, `worst_case_real.py`, `mitigations.py`, `netatmo_sampling.py`.

Frasi del paper che ne dipendono, con l'esposizione:

| Riga | Claim | Esposizione |
|---|---|---|
| 528 | 36/55 ACE, recall 0,079/0,124, F1 0,112/0,022 | tutti i tipi UNSW |
| 530 | 346 fatti | ricalcolato, vedi sotto |
| 627–629 | A1 0/59, 21/150 | da verificare se i cinque tipi A1 includono quelli coinvolti (da calcolare) |
| 631 | 0,354, 0,562, 0,663 | i massimi stanno su HelloBarbie/CanaryCamera |
| 637 | Sybil 45/48, 0,905 | **target AugustDoorBell**, tipo coinvolto |
| 639 | deriva 69/162 | include i tre tipi |

**Metodo.** Pipeline del paper (`read → filter_observations(exclude_non_global_ips) → partition(random, seed) → DIBScorer`), con le 8 righe tolte **dopo** la partizione. Così misuro l'effetto puro delle date; rifare gli script su un file filtrato rimescolerebbe anche la partizione, cioè varianza di seed. Seed 0–19 e 42; config `graph_free_selected` (trust, m=2) e raw. Lo scoring ristretto ai tre tipi è verificato esatto contro lo scoring completo al seed 42 (190/190 chiavi). Copie filtrate: `out/*_nospurious.csv` (8 righe in meno ciascuna, gitignored).

**Risultati.**

| Misura | Risultato |
|---|---|
| Fatti ammessi dei tre tipi, trust e raw, 21 seed (`spurious_dates_summary.csv`) | 15 → 15 in ogni seed; **0 nuove ammissioni, 0 nuovi rifiuti** |
| Endpoint eleggibili dei tre tipi in [θ − bound, θ) prima della rimozione | **0** in tutti i seed |
| Variazioni di score (raw), endpoint non proprietari delle righe | da 0 a +0,0051 (dentro il bound) |
| Endpoint proprietari delle righe | **in calo**: dmsv2.video-cloud.net 0,6993 → 0,6985 (resta ammesso); 52.87.241.159 tcp/443 0,622 → 0,556 (classe `other`, non eleggibile); 89.30.121.26 syslog 0,253 → 0,190; 89.30.121.22 0,186 → 0,183 |
| Trust weighting, popolazione completa, seed 42 (`spurious_dates_trust_seed42.csv`) | **346 → 346 fatti**; 3738 score di altri tipi si muovono, al massimo di 4,9·10⁻⁵ |
| A2 raw a k=3 e k=5, tipi coinvolti, 20 seed (`spurious_dates_a2.csv`) | variazione del massimo da +0,00005 a +0,0007; 0 cambi di ammissione; i valori "prima" coincidono con `a2_raw_k.csv` (120/120) |
| Celle dei tipi coinvolti in `results/*.csv` con score in [θ − bound, θ) (`spurious_dates_results_scan.csv`) | **nessuna**, Sybil e deriva inclusi |

**Esito delle ipotesi.**
- S1 confermata.
- **S2 smentita in parte:** gli endpoint che possiedono le righe perdono giorni propri e scendono fino a −0,066. Il test A.3 resta con l'asserzione originale ed è marcato `xfail(strict=True)`; il test post-hoc ristretto ai non proprietari passa.
- **S3 smentita:** la breadth di qualche sito cambia in 19 seed su 21 e quella di riferimento in 8.
- S4 confermata con 0 cambi; S5 confermata.

**Conclusione [D].** Nessun numero del paper cambia per effetto delle date: nessuna ammissione attraversa θ=0,65 nelle configurazioni ricalcolate, e la scansione dei risultati salvati non trova celle che il bound possa spostare oltre θ. Restano da calcolare:
- l'effetto del rimescolamento, se gli script vengono rifatti su un file filtrato (varianza di seed, ad esempio 344,55 ± 5,03);
- il trust completo sugli altri 20 seed (solo il seed 42 è stato rifatto);
- la sovrapposizione tra i tipi A1 e quelli coinvolti.

## 12. Campionamento di Netatmo e BlipCare: due modelli (punto B, `netatmo_sampling.py`)

Modelli:
- **uniforme:** k siti tra tutti i 10, con la stessa chiamata RNG dello script originale. K_d segue una ipergeometrica (10, k, |ES_d|).
- **ES_d:** k siti dentro ES_d (`a2_raw_k.py`), quindi K_d = min(k, |ES_d|).

"Attesa" è P(K_d ≥ 2 e K_d/|ES_d| > 5/12), cioè il fatto è ammissibile in linea di principio; per BlipCare è mediata su |ES_d| per seed (4–8). Single-shot, raw breadth, 20 seed (`out/netatmo_sampling_table.csv`).

| Tipo | Modello | k=1 | k=2 | k=3 | k=4 | k=5 |
|---|---|---|---|---|---|---|
| Netatmo (\|ES_d\|=2) | uniforme: attesa / osservata ammessi | 0 / 0 | 0,022 / 0 | 0,067 / **3** (seed 1, 6, 13) | 0,133 / 4 | 0,222 / 8 |
| Netatmo | ES_d: attesa / osservata | 0 / 0 | 1 / **20** | 1 / 20 | 1 / 20 | 1 / 20 |
| BlipCare (\|ES_d\| 4–8) | uniforme: attesa ammissibile / ammessi | 0 / 0 | 0,007 / 0 | 0,190 / 0 (3 ammissibili) | 0,492 / 0 (8) | 0,769 / 0 (15) |
| BlipCare | ES_d: attesa ammissibile / ammessi | 0 / 0 | 0,05 / 0 | 0,90 / 0 | 1 / 2 | 1 / 11 |

Quota effettiva per Netatmo: 0, 0,5 o 1,0 nel modello uniforme; 0,5 (k=1) o 1,0 (k ≥ 2) nel modello ES_d. Per BlipCare l'intervallo per k è in `netatmo_sampling_table.csv` (`share_range`).

Ipotesi N1–N3 confermate: con k=3 il modello uniforme riproduce esattamente i seed 1, 6, 13 del run originale, e Netatmo è ammesso se e solo se K_d = 2. Per BlipCare l'ammissibilità è necessaria ma non sufficiente: con single-shot, C_t resta basso.

**Quale modello citare (senza scegliere per te).**
- Il modello **uniforme** descrive un consorzio in cui la compromissione colpisce i siti indipendentemente dai tipi che osservano. È quello dello script originale, quindi il 3/20 si cita con questo modello.
- Il modello **ES_d** descrive un avversario che sceglie di colpire proprio i siti che osservano il tipo bersaglio. È il caso peggiore per un dato k, e tiene la quota per tipo pari a k/|ES_d|, cioè la quantità definita dal Criterion.
- Il paper deve dire quale dei due usa: il 3/20 e il 20/20 non sono due misure dello stesso evento.

## 13. RAM, parallelismo e riproducibilità (punto C2)

`--workers N` (default 2) in `a2_raw_k.py` (processi sui seed, ciascuno carica i dati), `worst_case_real.py` e `mitigations.py` (fork, dati condivisi copy-on-write). Misure con `analysis_fs/measure.py`, che campiona ogni 0,5 s l'RSS sommato sull'albero dei processi, quindi il picco è un limite inferiore (`out/measurements.csv`).

| Script, N=2 | Tempo | Picco RSS | Output identici a `7c056ef` (sha256) |
|---|---|---|---|
| `a2_raw_k.py --workers 2` | 353 s | 2,68 GiB | sì: `a2_raw_k.csv`, `a2_raw_k_summary.csv`, `a2_raw_k_low_coverage.csv` |
| `worst_case_real.py --workers 2` | 106 s | 3,37 GiB | sì: `worst_case_real.csv`, `worst_case_real_summary.csv` |
| `mitigations.py --workers 2` | 95 s | 3,72 GiB | sì: `mitigation_recall_cost.csv`, `mitigation_adversary_sup.csv`, `mitigation_tau.csv` |

**Correzione della v2:** i "~26 GB" della v2 venivano da `free -g` sull'intera macchina, con altri run in parallelo; non erano una misura del solo `a2_raw_k.py` con 5 processi. [?] Il picco con 5 processi non è stato rimisurato.

Tempo di calcolo di questa sessione: **somma dei run misurati 1231 s ≈ 20,5 min (`measurements.csv`), più circa 4 min di un primo `spurious_dates.py --workers 2` interrotto perché troppo lento, più circa 1 min di controlli con pandas: in tutto circa 26 min, entro i 30. Molti run sono andati in parallelo, quindi il tempo di orologio è stato minore**.

## Riassunto

1. **Date spurie (A):** 8 righe in 3 tipi (AugustDoorBell, NestDropCam, WithingsSleepSensor; |D_d| −2/−4/−2). A parità di partizione nessuna ammissione cambia in 21 seed (trust e raw), il 346 del paper resta 346 al seed 42, e nessuna cella salvata in `results/` è entro il bound da θ. **Nessun numero del paper cambia.** Le ipotesi S2 e S3 sono smentite in parte (endpoint proprietari in calo; breadth dei siti modificata). La v2 attribuiva alle date il 349 → 354, che era un rimescolamento della partizione.
2. **Campionamento (B):** Netatmo con modello uniforme 0/0/3/4/8 su 20 (attese 0/0,022/0,067/0,133/0,222); con modello ES_d 0/20/20/20/20. Il 3/20 originale è riprodotto esattamente. Sono due eventi diversi, e il paper deve dichiarare il modello.
3. **RAM (C2):** con N=2, worst-case 106 s / 3,37 GiB, mitigazioni 95 s / 3,72 GiB, A2 353 s / 2,68 GiB; output identici byte per byte alla v2.
4. Restano valide le conclusioni di v1/v2 su bound, worst-case e H2 (§3, §7).
5. Diff proposto per il paper: `paper_edits_proposed.md`. Le frasi che dipendono dai dati UNSW (§0 del file) vanno toccate solo dopo aver deciso se rigenerare i risultati su dati filtrati.
