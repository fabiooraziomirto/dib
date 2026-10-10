# Audit 16 — Federazione sintetica: DIB contro ranked union sotto A2 (Passi 6a e 6)

Data: 2026-10-10. Branch `revision-tnsm`. Piano: `14_priorita_esperimenti_tnsm.md` §4 (rev. 5) e GATE 1 e 4 (§3). Il numero 15 è riservato al diff di G0b (Passo 2). Notazione: [C] verificato nel codice o nei dati; [D] deduzione.

## 1. Passo 6a: istogramma reale di h_d (riuso, nessun download)

Nessun dato nuovo: si riusano i risultati di audit 11 (§2.3 e §2.6). File di ancoraggio per il generatore: `experiments_tnsm/synthetic_federation/anchor_hd.json`. Contiene solo conteggi di tipi, senza etichette di dispositivi, quindi nessun dato derivato da Mon(IoT)r con etichette.

| Variante | h = 1 | 2 | 3 | 4 | 5 | Tipi | Fonte |
|---|---|---|---|---|---|---|---|
| 4 siti indipendenti (UNSW, Mon(IoT)r US, UK, YourThings) | 87 | 28 | 1 | 3 | 0 | 119 | `analysis_fs/out/hd_union_histogram.csv` (sha256 `80333491…`), corpus `union_canonical_h_indep` |
| più NCSU, mapping stretto | 87 | 28 | 1 | 2 | 1 | 119 | audit 11 §2.6: ring-doorbell passa da 4 a 5 |
| **più NCSU, mapping per famiglia (ancora usata)** | 83 | 31 | 2 | 1 | 2 | 119 | audit 11 §2.6: 7 tipi guadagnano un sito |

- Mediana di h_d = 1 in tutte le varianti; al più 5 siti indipendenti.
- Come ancora si usa la variante "per famiglia", la più favorevole alla guardia fra quelle misurate. [D] Con h ≤ 5, K = 2 a f_s = 0,30 è coperto al più su 2 tipi e K = 3 su nessuno (audit 11 §2.6).
- **Dichiarazione (piano, Passo 6a):** il Passo 6 con N ≥ 10 esplora una popolazione **più favorevole alla guardia** di quella reale.
- Estensioni opzionali (PingPong, HomeSnitch): non avviate. Ognuna richiede un OK separato e aggiunge al più un sito.

## 2. GATE 1: definizione di ammissione e regole secondarie (lettura del codice)

**Ammissione [C].** Un fatto e di tipo d è ammesso se e solo se `admit_auto` restituisce vero (`code/src/dib/evaluation/dib.py:22-47`, chiamata a `:286-298`). Servono tutte e quattro le condizioni:
- |S_e| ≥ m (`:44-45`);
- classe ∈ {dns, ntp, update, vendor-cloud} (`:19,47`);
- score ≥ θ;
- nessuna dispute aperta, sempre falso nello scorer (`:25,47`).

Lo score è α·C_s + β·C_t + γ·C_g (`:272-276`), dove:
- C_s = |S_e|/|ES_d| in modalità breadth grezza (`:268`);
- ES_d = tutti i siti con almeno un'osservazione del tipo, avversari compresi (`:195,249`);
- C_t = min(1, 0,7·giorni + 0,3·volume) (`:269-271`).

**Criterion 1** (audit 09 e 11): con γ = 0 e β = 1 − α, l'evidenza solo avversaria è respinta se K < ⌈5N/12⌉ a (0,6; 0,65); il quorum m = 2 respinge anche K = 1.

**Regole secondarie che possono ammettere un fatto A2 con n_avv < ⌈5N/12⌉:**

| Regola | Dove | Effetto su D0 | Trattamento |
|---|---|---|---|
| R1 termine di grafo (γ > 0) | `configs/graph_augmented.yaml` (γ = 0,2, grafo attivo) | il bound non vale più | esclusa: γ = 0 e grafo spento |
| **R2 trust weighting** | **la configurazione selezionata del paper**, `configs/graph_free_selected.yaml` (`trust_weighted: true`, `LOCKED_CONFIGS.md:12`); C_s pesato (`dib.py:256-259`), con w = min(1, breadth/riferimento) (`trust.py:86-104`) | **sì**: avversari con peso pieno e siti onesti con peso ridotto superano 5/12 con K/N < 5/12 | **D0 ridefinito** (sotto) |
| R3 denominatore | ES_d conta solo i siti con osservazioni del tipo (`dib.py:195`) | un sito onesto senza osservazioni riduce N | ogni sito onesto ha un'osservazione; N si prende da `eligible_sites` di DIB e si verifica con `assert` |
| R4 supporto onesto del fatto | |S_e| include i siti onesti | K/N sottostimato | esclusa: endpoint A2 nuovi, `assert supporting_sites == K` |
| R5 gate di classe | `classify_core` | protegge solo se A2 non è eleggibile | caso peggiore: A2 = vendor-cloud (verificato) |

**Esito del GATE 1: D0 così come scritto nel piano non vale per la configurazione selezionata del paper (R2).** Come richiesto dal GATE:
- **D0** (piano) si applica alla configurazione a breadth grezza (`configs/graph_free_unweighted_federation.yaml`), cioè quella per cui il paper enuncia Criterion 1 ("raw-breadth shares below 5/12").
- **D0'** (ridefinito) si applica alla configurazione con trust weighting: nessuna ammissione quando la quota **pesata** degli avversari, Σ_avv w / Σ_ES_d w, è < 5/12.
- **D0' attende la tua conferma prima di qualsiasi lancio.** [D] Nella costruzione di `bound_grid.population` tutti i siti hanno breadth 1, quindi i pesi sono tutti 1 e D0' coincide con D0: per esercitare R2 serve una costruzione con breadth eterogenee, che non è ancora scritta.

Il docstring di `experiments_tnsm/synthetic_federation/h61a.py` riporta tutto questo con file:riga.

## 3. GATE 4: eccesso atteso con ρ_corr = 0,3 (H6-2), calcolo analitico

- Modello: beta-binomiale con media q e correlazione intra-classe 0,3, cioè a = q(1/ρ − 1) e b = (1 − q)(1/ρ − 1).
- p_BB = P(K ≥ ⌈5N/12⌉), contro p* binomiale. Potenza = P(il limite CP inferiore supera p*) con n = 20 000 e α = 0,05/59 (scipy, calcolo esatto sulla binomiale del conteggio).

| N | q | p* | p_BB | p_BB/p* | Conteggio minimo per rifiutare | Potenza |
|---|---|---|---|---|---|---|
| 5 | 0,3 | 0,163 | 0,256 | 1,6 | 3428 | ≈ 1 |
| 10 | 0,3 | 0,150 | 0,283 | 1,9 | 3166 | ≈ 1 |
| 20 | 0,3 | 0,113 | 0,298 | 2,6 | 2409 | ≈ 1 |
| 5 | 0,2 | 0,0579 | 0,150 | 2,6 | 1264 | ≈ 1 |
| 50 | 0,3 | 0,0478 | 0,309 | 6,5 | 1052 | ≈ 1 |
| 10 | 0,2 | 0,0328 | 0,165 | 5,0 | 737 | ≈ 1 |
| 20 | 0,2 | 0,00998 | 0,173 | 17,3 | 246 | ≈ 1 |
| 5 | 0,1 | 0,00856 | 0,0636 | 7,4 | 215 | ≈ 1 |
| 100 | 0,3 | 0,00717 | 0,303 | 42,2 | 183 | ≈ 1 |

**Esito: tutti e 9 i punti sono rilevabili; nessun punto è escluso dalla famiglia H6-2.** [D] La potenza dipende dal modello di correlazione (latente condivisa per tipo); con correlazioni minori l'eccesso si riduce.

## 4. Pre-lancio: pilote (nessun lancio completo)

**H6-1a** (`h61a.py`): pilota con 1000 prove su 3 punti (5:0,3; 20:0,2; 100:0,3), configurazione grezza, 0,8 s.
- D0: 0 violazioni.
- Tasso di ammissione condizionato a n_avv ≥ ⌈5N/12⌉ = 1,0, quindi **X_dib = X_gen**: con la collusione totale e ρ = 100, D1 coincide con G-eccesso. [D] D1 non aggiunge informazione oltre a G; il contenuto della prova è D0.
- Stima del lancio completo (25 punti × 20 000 prove): secondi (lo scorer è memoizzato per (N, K), ed è esatto perché la popolazione è deterministica).

**H6-1b** (`h61b.py`): profili per tipo da UNSW (27 tipi, i 30 endpoint più osservati; cache fuori dalla repo in `/root/Desktop/DIB/outputs/tnsm_synth/`, sha256 del CSV nella cache).
- Pilota 1: N = 100, presenza 0,8, q = 0,3, 12 repliche con 12 processi in 10,3 s (~10 s a replica, ~7·10⁵ osservazioni, soprattutto il flood).
- Stima del lancio completo: il costo scala con N × presenza, in media ≈ 0,28 del punto pilota, quindi ≈ 2,8 s a replica × 34 000 / 12 ≈ **2,2 h**.

**Problema di disegno trovato in pilota (blocca il lancio di H6-1b, serve una tua decisione).** Con budget = |coda DIB| e baseline ordinate per **lo stesso score DIB**, il confronto non isola "ammissione contro ranking". Evidenza (replica diagnostica, N = 20, presenza 0,8, q = 0,3, seed 7):
- coda DIB di 13 fatti, di cui 3 A2: è un tipo con K/N > 5/12, ammesso correttamente secondo Criterion 1;
- score accettati fra 0,672 e 0,909; score massimo degli A2 = 0,672;
- i primi 14 fatti per score contengono 9 fatti di classe `other` (score ≈ 0,88), respinti da DIB per il gate di classe;
- **il prefisso di 13 della ranked union contiene 0 A2**, quindi la differenza (baseline − DIB) è **negativa**.

[D] Ordinando per lo stesso score, un fatto A2 entra nel prefisso solo se il suo score è fra i primi B. Ma con la stessa formula un A2 ha uno score alto solo quando K/N > f*, cioè quando anche DIB lo ammette. Le differenze vengono quindi dal gate di classe e dal riempimento del budget, non dall'ammissione. H6-1b come specificato sarà per lo più non testabile o di segno opposto, per costruzione.

Opzioni (nessuna applicata):
- **(a)** stesso gate di classe per tutte le baseline: ranked-score coincide quasi con DIB, la differenza va a ≈ 0 e il risultato mostra la tautologia;
- **(b)** baseline che **non** usano lo score DIB: ranking per volume (osservazioni) o per supporto puro |S_e|, cioè le alternative realistiche che un flood sfrutta; ranked-score resta come controllo. [D] È il confronto che risponde a `main_old.tex:617`;
- **(c)** budget più grandi della coda DIB (c·B, con c ∈ {2, 5}), cioè un operatore che rivede più fatti.

Raccomandazione: (b) + (c) con il gate di classe applicato a tutti; l'ipotesi H6-1b va riscritta nel docstring prima del lancio.

## 5. Decisioni dell'utente (2026-10-10) e lanci di H6-1a, H6-2 e D0'

**Decisioni.**
- D0' confermato. Va esplicitato **nel paper**: Criterion 1 vale per la configurazione non pesata; per quella pesata vale D0', sulla quota pesata.
- Prova vera con pesi eterogenei e controllo con pesi uniformi.
- Se D0' fallisce: stop e report, nessuna modifica a `dib.py`.

**Verifica che D0' misuri il codice e non una definizione mia [C].**
- `d0prime.py` calcola W = Σ_avv w / Σ_ES_d w con gli stessi pesi di DIB (`compute_site_trust_weights` sulle stesse osservazioni, come `dib.py:157-161`).
- A ogni caso fa `assert` che W sia uguale al `site_confidence` restituito da DIB (`dib.py:256-259`), con tolleranza relativa 1e-12.
- Il quorum resta sul conteggio non pesato |S_e| (`dib.py:250,292`), e la soglia è stretta (W·12 < 5).
- Tutte le asserzioni sono passate.

### 5.1 D0' (`d0prime.py`, commit `06182ce`; dati in `runs/d0prime/`)

- Griglia: N ∈ {5, 10, 20, 50, 100}, ogni K = 1..N, 20 estrazioni di breadth onesta per caso.
- Pesi: REF = 10, breadth onesta uniforme su [1, 19]; due bracci avversari più il controllo uniforme. Durata 220 s.

| Braccio | Casi | Ammessi (pesato) | **Violazioni D0'** | Decisioni pesate ≠ grezze | Ammessi con quota **grezza** < 5/12 | Quota grezza minima ammessa |
|---|---|---|---|---|---|---|
| uniforme (controllo, pesi = 1) | 185 | 110 | **0** | 0 | 0 | 0,42 |
| adv-low (avversari b = 1, w = 0,1) | 3700 | 628 | **0** | 1572 | 0 | 0,60 |
| adv-high (avversari con breadth gonfiata, w = 1) | 3700 | 2445 | **0** | 245 | **245** (N = 5: 15; 10: 18; 20: 30; 50: 62; 100: 120) | **0,30** |

**Esito:**
- H-D0'u non falsificata: nel controllo la decisione pesata è identica a quella grezza.
- **H-D0'h non falsificata:** nessuna ammissione con quota pesata < 5/12 né con |S_e| < 2.

**Risultato sul meccanismo [D], da riportare nel paper.**
- Il trust weighting protegge dai Sybil a breadth bassa: in adv-low la quota grezza minima ammessa sale a 0,60.
- Lo stesso pesatura **apre** però una superficie di attacco: un avversario che gonfia la propria breadth fino al riferimento (peso 1), contro siti onesti di cui circa metà ha peso < 1, fa ammettere fatti con quota grezza fino a **0,30 < 5/12**.
- Il Criterion 1 grezzo **non** protegge quindi la configurazione selezionata. La garanzia vale nella forma D0', sulla quota pesata, ed è tanto buona quanto la stima dei pesi.
- Che un avversario possa guadagnare peso è un'ipotesi di attacco da dichiarare nel threat model.

### 5.2 H6-1a, ρ_corr = 0 (`h61a.py --trials 20000`, configurazione grezza, seed 20261010; `runs/h61a_rho0/`)

- 25 punti in 1,7 s.
- G-eccesso: 0 difetti su 25. G-difetto: 0 su 9. Il generatore riproduce la binomiale; per esempio N = 5, q = 0,3: X_gen = 3261 su 20 000, CP [0,155; 0,171] contro p* = 0,163.
- **D0: 0 violazioni.**
- D1: 0 falsificazioni. X_dib = X_gen in tutti i punti: con la collusione totale e ρ = 100, DIB ammette **esattamente** quando n_avv ≥ ⌈5N/12⌉.
- **H6-1a non falsificata.**

### 5.3 H6-2, ρ_corr = 0,3 (seed 20261011; `runs/h62_rho03/`)

- Eccesso rilevato in **9 punti su 9** (e anche nei restanti 16): ad esempio N = 100, q = 0,3 dà X_gen/n = 0,304 contro p* = 0,0072 (42×), N = 20, q = 0,2 dà 0,173 contro 0,0100.
- **H6-2 non falsificata.** D0 resta a 0 violazioni: anche con correlazione DIB ammette solo sopra la soglia.
- Il bound binomiale sottostima invece di uno a due ordini di grandezza la frequenza con cui la soglia è superata quando i siti sono correlati (firmware o cloud condiviso).
- Nota: il flag "D1_falsified" in `runs/h62_rho03/points.csv` è calcolato rispetto al p* binomiale. Lì **non** è una falsificazione di H6-1a, che è definita a ρ_corr = 0, ma la misura dell'eccesso dovuto alla correlazione.

## 6. H6-1b riprogettata: esito (`h61b.py`, ipotesi committata in `07fb841` prima del lancio)

**Lancio.**
- 170 punti × 200 repliche = 34 000 repliche, 12 processi, 954 s. Pilota a N = 100: 50 repliche in 16,9 s.
- Dati in `runs/h61b/`: `replicas.jsonl.gz`, con lo sha256 del file non compresso in `replicas.jsonl.sha256`; `h61b_tests.csv`; `manifest.json`.

**Famiglia.**
- 1020 test (2 baseline × 3 budget × 170 punti), di cui **892 testabili**; Holm con FWER 5%.
- I 128 non testabili sono soprattutto a q = 0,01 (62), dove gli avversari sono rari.
- **Holm rifiuta H0 in 802 test su 892. H6-1b è FALSIFICATA.**

| Baseline | c | Testabili (ρ_corr 0 / 0,3) | H0 non rifiutata | Lettura |
|---|---|---|---|---|
| ranked-volume | 1, 2, 5 | 85 / 85 per c | **0** | il ranking per volume mette sempre in coda più fatti A2 di DIB, a ogni budget |
| ranked-sites | 2, 5 | 54-85 per cella | **0** | con budget 2× e 5× il ranking per supporto presenta più fatti A2 di DIB |
| **ranked-sites** | **1** | 23 / 67 | **90 su 90** | **a budget uguale alla coda DIB il ranking per supporto presenta MENO fatti A2 di DIB** |

**Dettaglio di ranked-sites a 1×.**
- 90 test: IC bootstrap interamente < 0 in 79, che include 0 in 8, > 0 in 3.
- Media di A2 nella coda DIB = 6,3; differenza media (baseline − DIB) = −0,48.
- Ricorre a ogni q ≥ 0,05 (16 / 20 / 25 / 29 test per q = 0,05 / 0,1 / 0,2 / 0,3) ed è più frequente con ρ_corr = 0,3 (67 su 90).

**Curva (media sui 170 punti della differenza in numero di fatti A2, baseline − DIB).**

| c | 1 | 1,5 | 2 | 3 | 5 | 10 |
|---|---|---|---|---|---|---|
| ranked-volume | 8,8 | 14,1 | 18,6 | 24,9 | 31,5 | 37,2 |
| ranked-sites | **−0,26** | 1,8 | 4,0 | 7,8 | 14,1 | 24,7 |

Il vantaggio di DIB **non sparisce** a budget grandi: cresce, perché il ranking presenta sempre più fatti inventati. Contro il ranking per supporto, però, il vantaggio **non c'è** a budget pari alla coda DIB, e compare da circa 1,5× in su.

**Riferimenti (fuori dalla famiglia).**
- `ranked-score`: ≈ DIB a 1× (+0,17 in media), poi +5,8 / +19,9 / +31,6 a 2×, 5× e 10×.
- `ranked-support-2`: identico a DIB a 1× (0,000 in tutti i punti), come atteso, perché il ranking per score con quorum 2 a budget B coincide con la coda.
- `ranked-support-3`: **meno A2 di DIB** in 40 punti a 1× (media −0,31) e ancora in 31 punti a c ≥ 2.

**Lettura [D].** Quando la soglia di Criterion 1 è superata (q alto, oppure siti correlati: vedi H6-2), DIB **ammette** i fatti A2 di quel tipo, perché la loro quota supera 5/12. Un ranking per numero di siti a budget uguale li mette dietro i fatti benigni più diffusi, e li esclude. In quei punti DIB non è più protettivo di un filtro di supporto: l'ammissione a quorum 2 con soglia di score non aggiunge protezione rispetto a ordinare per supporto (o a richiedere supporto ≥ 3) a budget uguale. Il vantaggio dell'ammissione è netto solo contro le baseline che il flood sfrutta (volume, ranking per score) e contro qualsiasi ranking quando l'operatore rivede più della coda DIB (c ≥ 1,5-2).

**Da dire nel paper:**
1. L'ammissione protegge dal flood (volume) e da budget di revisione più grandi della coda.
2. A budget uguale, ordinare per supporto è altrettanto o più protettivo di DIB quando gli avversari superano la soglia.
3. La riga per l'abstract (§1, "più favorevole alla guardia") vale anche qui.

Il filtro di classe è applicato a tutte le baseline e non è un contributo dell'ammissione (docstring).
