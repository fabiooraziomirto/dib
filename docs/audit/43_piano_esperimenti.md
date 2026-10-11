# Audit 43 — Piano degli esperimenti mancanti per il paper DIB (IEEE TNSM) — piano da discutere col supervisore il 16 ottobre

Data: 2026-10-11. Stato: **bozza non tracciata, nulla eseguito**. **Rev. 2026-10-11 (sera):** aggiunta la colonna "Quando" in §1 (*prima del 16* / *dopo il 16* / *condizionato a Qn*), B1 diviso in B1a/B1b (§1, §3), calendario di §4 sostituito, Q12 in §7b diventata decisione presa; l'esecuzione prima del 16 riguarda solo ciò che resta valido qualunque cosa risponda il supervisore (A2 passo 1, A4, B0, B1a, B2k completo, B5, A5 parametrico); ciò che dipende da Q2, Q4+Q5, Q13, Q14 si prepara ma non si esegue. **Rev. 2 (2026-10-11, risposta dell'utente):** A5 ritirata come test, opzione (c) (audit 44); D-B5-1 chiusa (audit 46); PKI 336 h confermata; `docs/main_wip.tex` canonica. Nulla di quanto sopra è autorizzato: ogni ssh/sudo e ogni lancio lungo resta da chiedere (CLAUDE.md). Non è una pre-registrazione: ogni ipotesi qui è una bozza da registrare in un audit separato (44, 45, …) e committare prima dei dati.
Convenzioni: `aNN:r` = `docs/audit/NN_*.md` riga r; `wip:r` = `docs/main_wip.tex` riga r (copia di lavoro del paper usata dagli ultimi commit `75d1b19`, `7091f37`); `M67/` = `experiments_tnsm/m67_retraction/`. **[SSH-U]** = ssh che l'utente autorizza/lancia, uno per volta; **[SUDO-U]** = comando sudo che lancia l'utente. "da verificare" = numero senza fonte certa.

## 0. Contributo candidato e goal
- Contributo candidato (dal prompt dell'utente): ritiro limitato nel tempo e coerente dopo disputa, anche sotto rete degradata. Goal proposti: **G1** protezione condizionata dell'ammissione, **G2** autorizzazione locale, **G3** ritiro limitato e coerente.
- **Disallineamento con il paper:** in `wip:153-159` G1 = "Evidence-based proposals", G2 = "Conditional admission protection", G3 = "Local authorization with conservative withdrawal"; `wip:164` dice che G3 "imposes no deadline on withdrawal". La numerazione proposta (G1 = ammissione, G3 = ritiro *limitato*) cambia due goal: va decisa (domanda Q1). In questo piano uso la numerazione proposta.
- **Cosa il paper misura oggi per G3:** solo siti raggiungibili (`wip:606`, `wip:640` ultima frase); siti irraggiungibili restano "without a time bound (AS6)" (`wip:179`, `wip:487`); "no established withdrawal deadline … rule leases could bound stale permissions" (`wip:780`); future work "mechanisms to bound gateway withdrawal time" (`wip:792`). Quindi "limitato" oggi vale solo (i) per siti raggiungibili (B1) e (ii) *dopo la riconnessione* (B2, mai eseguito). Un limite durante la disconnessione richiede il lease (Q2).

## 1. Tabella riassuntiva

| ID | Esperimento | Priorità | Goal | Dipendenze | Durata nodo | Disco nodo | Sezione del paper | Quando |
|---|---|---|---|---|---|---|---|---|
| A1 | 5.3b Fase B: riproduzione di `matched_ablation.csv` | COPERTA dal run confermativo (12/12); attesi = CSV committato (`bd3080b`, sha256 `f04866a9…`) | G1 | nessuna (offline) | 0 | 0 | `tab:threelab` (`wip:678`), `wip:778` | fatto (run confermativo) |
| A2 | 5.3b Fase C: calcolo 5.3b (card(C_DIB Δ C_B) per ricevente, poi recall per dispositivo con bootstrap appaiato) | UTILE | G1 | A1; codice+test committati prima | 0 | 0 | idem | **prima del 16** (passo 1, Δ); passo 2 solo se Δ > 0 |
| A3 | 5.3b Fase C, parte secondaria POST-HOC (a41 §3-§6) | UTILE (bassa) | G1 | A2 | 0 | 0 | idem (solo come POST-HOC) | dopo il 16; condizionato a Δ > 0 (A2) |
| A4 | 5.3b Fase D: tabella (α, θ) con `Fraction`, descrittiva (audit 42: definizione prima del calcolo) | INDISPENSABILE (obiettivo 5) | G1 | audit 42 da scrivere (NON TROVATO) | 0 | 0 | `tab:params` (`wip:444`), `sec:sensitivity-results` (`wip:764`) | **prima del 16** (audit 42, poi calcolo) |
| A5 | 5.3b Fase C bis: riedizione di S2 (simulazione benigna), quorum frazionario + persistenza contro punteggio (domanda sul breadth) | UTILE, INDISPENSABILE se Q13 = "quorum + classe + persistenza" | G1 | A1; Q14b; audit 44 committato prima, codice e test prima dell'esecuzione | 0 | 0 | `wip:413-424` (Criterion), `wip:778` | **RITIRATA come test (opzione (c), audit 44)**: degenere per costruzione a q = 0 e candidati pari; resta la caratterizzazione analitica (audit 44 §3) per Q14; macro (a) solo descrittivo, facoltativo |
| B0 | Rigenerazione PKI | INDISPENSABILE (prerequisito) | — | disco, tree | minuti (a20:22) | trascurabile, da verificare | — | **prima del 16** (lun 12) |
| B1a | Cella di fumo (`lan`, `degraded`) + calibrazione L_dns | INDISPENSABILE (prerequisito) | G3 | B0, watcher v2 | ~0,5 h, stima non fondata (parti: a32:173-186, a26:58) | trascurabile | — | **prima del 16** (lun 12; tentativo 2 di L_dns mar 13 se serve) |
| B1b | Test partition+restore con il vero watcher (B1(ii)) | serve solo a B2p | G3 | B1a, codice di test | stima non fondata | trascurabile | — | dopo il 16; condizionato a Q4+Q5 |
| B2k | B2-kill | INDISPENSABILE | G3 | B1, L_dns ≤ 50 ms | 1,69 h (minimo) / 2,36 h (completo) (a14:281-288) | MB, da verificare | `wip:606`, `wip:640`, `wip:780` | **prima del 16** (versione completa) |
| B2p | B2-partition | UTILE (decisione Q4+Q5) | G3 | B1, codice in `run.py` + helper sudo | 7,64 h (a14:314) | MB, da verificare | `wip:606` ("asymmetric partitions") | codice, helper e test preparati prima del 16, **non lanciato**; condizionato a Q4+Q5 |
| B3 | Profili `regional` / `mixed` / `extreme` | FUTURE WORK (`regional`, `extreme`), UTILE (`mixed`) | G3 | B1; `mixed`/`extreme` richiedono modifica del watcher | ~0,5 h per profilo, stima da a27:6,8 | MB | `tab:netem` (`wip:622`) | `mixed` solo se resta tempo giovedì 15 (richiede modifica del watcher); `regional`/`extreme` dopo il 16 |
| B4 | Braccio `default` a `degraded` (P-a1, P-a2) | TAGLIO proposto (Q8, §7b) | — | B1, B0 | ~0,6 h, stima non fondata | MB | nessuna | non si lancia (taglio) |
| B5 | (a') pre-registrata con i tentativi falliti, SOLO dati nuovi `degraded` | INDISPENSABILE se G3 = "limitato sotto rete degradata" (Q4+Q5) | G3 | B1, B0; audit di pre-registrazione | ~1,4 h (a34:6) | ~4 MB in copia locale | `wip:640` (calcolo post-hoc "not tested") | **prima del 16**, accettando che i dati restino in `experiments_tnsm/` se Q4+Q5 dice di non rifare (a') |
| B6 | M5 (numero di siti) | TAGLIO proposto (Q6, §7b); era UTILE per obiettivo 3, nessun goal | — | B0; disco | ~1,5 h (a04:62) | 3-5 GB a N = 50 (a04:62) | `wip:604` (oggi numeri vecchi) | non si lancia (taglio) |
| B7 | M8 (firma MUD) | FUTURE WORK / UTILE (basso costo) | G2 (deployment) | nessuna | minuti (a04:65) | trascurabile | `wip:503`, `wip:782` | facoltativo giovedì 15; altrimenti dopo il 16 |
| B8 | M3 con un mix che eserciti il fan-out | TAGLIO proposto (Q7, §7b); era UTILE | G3 (percorso di gestione) | B0 | ~1,1 h (a18:5) | MB | `wip:602` | non si lancia (taglio) |
| C | Promozione in `results/` | dopo il paper | — | analisi chiuse | 0 | 0 | tutte | dopo il paper |

## 2. Prima del 16: solo offline (nessun nodo)

### A1 — 5.3b Fase B: riproduzione di `results/three_lab_matched/matched_ablation.csv`
1. **Domanda / paper:** il codice della baseline riproduce esattamente le righe `union`, `quorum`, `quorum_score`, `DIB` già pubblicate? Serve a `tab:threelab` (`wip:678`) e alla frase "Quorum accounts for most queue reduction" (`wip:778`).
2. **Goal / priorità:** G1. **COPERTA dal run confermativo:** l'asserzione di riproduzione di `real()` (`analyze_baseline.py:211-216`: candidati esatti, metriche entro 1e-12, 4 stadi per ricevente) è passata per 12/12 righe (3 riceventi × 4 stadi), altrimenti `aggregates.json` non sarebbe stato scritto. Fonte: `experiments_tnsm/baseline_quorum_persistence/run_20261012/real/aggregates.json` (sha256 `15cd3be186b01654cd1d41b6ef6133b44473460630483122a7304ba6d5a9a560`, coincide con a41:13; righe `DIB` a :27, :141, :255). Gli attesi sono `REFERENCE = results/three_lab_matched/matched_ablation.csv` (`analyze_baseline.py:41`), cioè il CSV **committato** (`bd3080b`, sha256 `f04866a952855f2f312c0ec895b506900532134ccca1370eb844cf75d25d2d95`); `git status --short results/` vuoto: verificato nella sessione 5.3b e riverificato in questa sessione (sha256 e stato di git, sola lettura). Il "diff grezzo" di a41:58 resta facoltativo (script NON TROVATO).
   **(a) Cosa riproduce la baseline:** B(2, 0) = quorum ∩ classe eleggibile (`admit` = `n_sites >= m and active_day_ratio >= tau and eligible`, `analyze_baseline.py:45-47`; classe calcolata in `:63`), mentre lo stadio `quorum` di `matched_ablation.csv` è il solo quorum |S_e| ≥ 2 senza classe (`code/scripts/v28_matched_ablation.py:36`). Nel paper "site quorum" ≠ "quorum + classe + persistenza": le due etichette non vanno confuse in `tab:threelab` e in `wip:778`.
   **(b) Rischio per l'artefatto:** `code/scripts/v28_matched_ablation.py` **non è eseguibile in questa repo**: legge `code/data/processed/*.csv` e `experiments/30_three_lab_loo/…` (`v28_matched_ablation.py:19-22, 29`), e né `code/data/processed` né `experiments/` esistono (`ls` negativo). Il CSV in `results/` non è quindi rigenerabile dallo script che lo ha prodotto; oggi lo riproduce solo `analyze_baseline.py`, che legge i dati in place da `/root/Desktop/DIB/data/processed` (`analyze_baseline.py:38-39`), fuori dalla repo.
3. **Ipotesi:** nessuna ipotesi scientifica; criterio di validità già applicato (a40:18; a41:19).
4. **Configurazione:** riceventi US, UK, YT a rotazione (a40:17-18), dati letti in place (a41:15, sha256 completi). n = 3 riceventi × 4 stadi = 12 righe.
5. **Dipendenze:** nessuna.
6. **Durata/disco:** già eseguito; per la verifica dell'attesa, secondi.
7. **Rischi:** licenza Mon(IoT)r (CLAUDE.md): niente righe per dispositivo nella repo.
8. **Stop/esclusione:** nessuno (coperta); il rischio (b) va dichiarato nel README dell'artefatto, non risolto qui.
9. **Repo:** solo l'esito in `docs/audit/`; output per dispositivo fuori dalla repo con sha256 nel manifest (a41:36).
- **Esito del run confermativo (regole letterali di a40, aggregati da `aggregates.json`):** **H-B1 falsificata** (precisione di DIB = precisione di B(2, τ_match) in 3/3 riceventi: US 0,75 = 0,75; UK 0,78385 = 0,78385; YT 0,28567 = 0,28567; `aggregates.json:347-366`); **H-B2 non falsificata** (recall identici in 3/3: US 0,06500; UK 0,06436; YT 0,22293; `aggregates.json:367-386`); **divario ||C_B(2, τ_match)| − |C_DIB|| = 0 in tutti e tre** (US 36 = 36, τ_match 0,17; UK 43 = 43, τ_match 0,0; YT 107 = 107, τ_match 0,17; `aggregates.json:27-28, 107-108, 115; 141-142, 221-222, 229; 255-256, 335-336, 343`).
- **Nota di stato:** `experiments_tnsm/baseline_quorum_persistence/run_20261012/` è **non tracciata** (git status); a41:3 dice "bozza, non committata" ma il file è committato in `2af2d89`: testo da aggiornare. a40 ha la data sbagliata (a41:3).

### A2 — 5.3b Fase C: calcolo 5.3b (differenza simmetrica, poi recall per dispositivo con bootstrap appaiato)
1. **Domanda / paper:** la baseline B(2, τ_match) seleziona lo stesso insieme di DIB? Se no, ne raggiunge il recall? Serve a `tab:threelab` e al confronto "quorum + persistenza" contro punteggio (a36:59).
2. **Goal / priorità:** G1. UTILE: i verdetti confermativi di H-B1/H-B2 esistono già (A1); la Fase C è il calcolo secondario.
3. **Passo 1 (prima del bootstrap):** |C_DIB Δ C_B(2, τ_match)| per ricevente (differenza simmetrica degli insiemi di chiavi). **Non è in `aggregates.json`** (contiene solo conteggi e metriche): da calcolare. Conteggi uguali e metriche uguali non bastano a dire che gli insiemi coincidono. **Se Δ = 0 in un ricevente, il bootstrap per quel ricevente è degenere** (d = 0 su ogni unità ⇒ IC [0, 0] ⇒ "non falsificata; nessuna differenza osservata, nessun potere", a41:34) e non si esegue come test.
   **Passo 2 (solo per riceventi con Δ > 0):** ipotesi già scritta in a41:25-36 (d = recall(5.3b) − recall(DIB), bootstrap appaiato, B = 10 000, seme 20261012, unità (ricevente, dispositivo); falsificata se l'estremo inferiore > 0). **Etichetta: POST-HOC** (a41:23).
4. **Configurazione:** n = 18 unità (a41:31); con n < 10 l'IC per ricevente è solo descrittivo (a41:31). n vincolato dai dati, non da potere.
5. **Dipendenze:** A1. Codice nuovo (passi 1 e 2) con test scritti prima e committati prima dell'esecuzione (a41:57); oggi **NON TROVATO** (solo `boot_median_ci` per S2, `analyze_baseline.py:168`).
6. **Durata/disco:** offline, minuti (stima non fondata).
7. **Rischi:** dipendenza fra dispositivi dello stesso ricevente ⇒ IC ottimistico (a41:30).
8. **Stop/esclusione:** dispositivi senza positivi esclusi (oggi 0 su 18, a41:31); Δ = 0 ovunque ⇒ ci si ferma al passo 1.
9. **Repo:** solo |Δ| per ricevente, IC, n, verdetti; insiemi e valori per dispositivo fuori dalla repo (a41:36, 57).

### A3 — 5.3b Fase C, parte secondaria POST-HOC
1. **Domanda / paper:** abbinamento con soglia 10%, H-B1 "non valutabile", H-B3 come asserzione aritmetica (a41:38-51). Nel paper al più come nota POST-HOC.
2. **Goal / priorità:** G1. UTILE (bassa): non cambia il confermativo (a41:23).
3. **Ipotesi:** nessuna nuova; regole già in a41 §1-§5, etichettate POST-HOC. S2 ritirata (a41:54).
4-6. Offline, minuti; dipende da A2.
7. **Rischi:** confondere secondario e confermativo nel testo del paper.
8. **Stop:** nessun abbinamento valido per un ricevente ⇒ "nessun confronto secondario" (a41:42).
9. **Repo:** solo aggregati.

### A4 — 5.3b Fase D: tabella di robustezza (α, θ) (audit 42 da scrivere)
1. **Domanda / paper:** perché (α, θ) = (0,6; 0,65) e non le coppie già usate (0,7;0,65), (0,6;0,7), (0,55;0,6) (a11:11; a36:57-59)? Serve a `tab:params` (`wip:444`) e a `sec:sensitivity-results` (`wip:764`); obiettivo 5 di CLAUDE.md.
2. **Goal / priorità:** G1. INDISPENSABILE per l'obiettivo 5 concordato col supervisore; la definizione **non esiste** (audit 42: NON TROVATO; a36:59 "resta da definire").
3. **Contenuto (da registrare in audit 42; tabella DESCRITTIVA, nessun criterio di falsificazione, nessuna soglia X):** per ogni coppia: f* = (θ−β)/α, r = (θ+α−1)/(1−θ) (a36:59), margine f* − 0,30, recall sui dati reali da `results/sensitivity/{moniotr,yourthings}_{alpha_margin,alpha_sweep,theta_sweep}.csv`. Margini minimi già noti (a11:36-41) da riprodurre come controllo aritmetico.
   **Nota:** a parità di conteggio dei candidati, quorum + classe + persistenza (B(2, τ_match)) dà le stesse metriche (precisione, recall) di DIB in 3/3 riceventi (H-B1 falsificata, A1); l'**identità degli insiemi è da verificare (A2 passo 1)**. Se gli insiemi coincidono, sui laboratori reali (α, θ) non cambia l'esito osservato e conta solo nel regime a N siti (f* = (θ−β)/α e K < r·h, a11:9-31), cioè nel simulatore sintetico, dove la tabella va letta; altrimenti no.
   **Priorità di A4 condizionata a Q13** (§7).
4. **Configurazione:** griglia da dichiarare in audit 42 (almeno le 4 coppie di a11:11; candidato: `analysis_fs/bound_grid.py` con (α, θ) variabile, a09:60). n = numero di coppie (vincolo: griglia finita, aritmetica esatta).
5. **Dipendenze:** audit 42 committato prima del calcolo.
6. **Durata/disco:** offline, minuti (stima non fondata).
7. **Rischi:** i CSV di `results/sensitivity/` sono trust-weighted o raw? (a36:63, voce 5.7): da verificare prima di definire la tabella.
8. **Stop:** se i CSV non coprono una coppia, si scrive "non disponibile", nessuna simulazione nuova senza OK.
9. **Repo:** tabella aggregata in `docs/audit/`; script in `analysis_fs/`.

### A5 — 5.3b Fase C bis: il breadth additivo aggiunge qualcosa a un quorum frazionario + persistenza? — RITIRATA come test (rev. 2, opzione (c), audit 44)
**Rev. 2:** il test è degenere per costruzione (q = 0: tutti i candidati stanno sul profilo, precisione 1 per entrambe le regole; a candidati pari anche il recall micro è uguale, con qualunque generatore); le alternative (b) rumore fuori profilo e (a) esito macro non reggono (assunzione nostra sul rumore; misura solo l'allocazione fra tipi). Risultato conservato: la caratterizzazione analitica (audit 44 §3). Il testo sotto è la scheda originale, mantenuta per tracciabilità, **non eseguita**.
1. **Domanda / paper:** il termine di breadth di DIB (C_s = |S_e|/|ES_d|, `wip:413-424`) è giustificato oltre a "un quorum che scala con N"? Oggi A1 mostra che con 3 laboratori (2 sorgenti per ricevente) DIB e B(2, τ_match) coincidono nelle metriche, quindi la domanda non è decidibile sui dati reali (il termine C_s non varia). Serve a `wip:778` ("Quorum accounts for most queue reduction") e al contributo G1/G2.
2. **Goal / priorità:** G1 (G2 nella numerazione del paper). UTILE; diventa INDISPENSABILE se la risposta a Q13 è "quorum + classe + persistenza".
3. **Affermazioni sul breadth verificate in lettura:** (i) il Criterion è a `wip:413-424`: evidenza solo-avversaria con quota raw ≤ f_s dà score ≤ α·f_s + β (`wip:416-421`); (ii) con α = 0,6, β = 0,4, θ = 0,65 rifiuta quote sotto f* = 5/12 e, in conteggi, K < ⌈5N/12⌉ (docstring di `experiments_tnsm/synthetic_federation/h61a.py`, sezione "Criterion 1"); (iii) il paper ammette che il breadth grezzo conta identità e che trust weighting e clustering falliscono sotto padding (`wip:778`; varianti Sybil-aware a `wip:431-437`); (iv) `h61b.py:7`: mediana di h_d = 1 e al più 5 siti indipendenti nelle federazioni reali. **Non verificato:** "un quorum frazionario eguaglia DIB" come affermazione sui dati.
4. **Il controllo "r_Bfrac dagli istogrammi `k_hist.json`" è tautologico (verificato su due punti, sola lettura):** in `runs/h61a_rho0/points.csv` la colonna `kmin` vale ⌈5N/12⌉ (N = 10: 5; N = 20: 9) e `x_dib` = Σ_{k ≥ kmin} `k_hist` (N = 10, q = 0,3: 2040 + 777 + 196 + 17 + 3 = 3033; N = 20, q = 0,3: 1335 + 583 + 265 + 79 + 24 + 4 + 1 = 2291). Quindi r_Bfrac(φ = 5/12) = r_DIB per costruzione nel regime S1 (collusione totale, persistenza 1): non è un test e non va presentato come tale (stessa natura di H-B3 ridotta ad asserzione, a41:51). Con φ < 5/12 il tasso cresce, ma è di nuovo aritmetica.
5. **Dove sta la domanda informativa (derivazione aritmetica mia, da verificare con un test sul codice):** DIB ammette sse α·C_s + β·C_t ≥ θ (`h61a.py` docstring, che cita `dib.py:272-276`: numeri di riga non coincidenti con il file attuale, dove C_s è a `dib.py:276` e C_t a `dib.py:277-279`; score `final` = α·site_conf + β·temporal_conf + γ·graph a `dib.py:281-285`, riletto). Poiché C_t ≤ 1, ciò implica C_s ≥ 5/12; a C_s dato la soglia di C_t è (θ − α·C_s)/β = 1,625 − 1,5·C_s (da 1 a C_s = 5/12 fino a 0,125 a C_s = 1). Quindi DIB = quorum frazionario φ = 5/12 con **soglia di persistenza decrescente col breadth**; la baseline frazionaria ha una soglia di persistenza **costante** τ. Le due regioni nel piano (C_s, C_t) hanno la stessa protezione contro fatti solo-avversari (per φ = 5/12) ma ammettono fatti benigni diversi: la domanda è il recall benigno a parità di candidati. Nota di definizione: la persistenza di B(m, τ) è il solo rapporto di giorni (a40:9), mentre C_t di DIB include anche il termine di volume (0,7·giorni + 0,3·frequenza, `dib.py:277-279`; in a40:9 `dib.py:269-271` è citato per il solo rapporto di giorni, riga da verificare): da allineare in audit 44.
6. **Bozza di ipotesi (da registrare in audit 44, non è la pre-registrazione):** H-A5: a numero di candidati pari, il recall benigno della baseline frazionaria B_frac(φ = 5/12, τ_match) non è inferiore a quello di DIB (se vale, il breadth additivo non aggiunge recall oltre al quorum relativo). Falsificata se il recall di DIB supera quello della baseline con IC interamente sopra 0.
7. **Configurazione (scelta dell'utente: riedizione di S2 pre-registrata):**
   - **Generatore:** `h61b.replica` (`experiments_tnsm/synthetic_federation/h61b.py:163`) con q = 0 (nessun avversario): ogni sito ospita il tipo con probabilità `presence` (`h61b.py:173`), osserva l'endpoint di rango r con probabilità r^-s (rango 1 sempre) e per giorni attivi con probabilità 0,5 (`h61b.py:191-193`), quindi i fatti benigni hanno (C_s, C_t) variabili. Punto ancorato: N_d estratto da `anchor_hd.json` su 5 siti (`h61b.py:166-170`). a40:14 prevedeva già di dichiarare un generatore benigno minimo se `replica()` non gira con q = 0: da verificare con un test prima di tutto.
   - **Punti e repliche (bozza, da fissare in audit 44):** N ∈ {10, 20, 50, 100} × presence ∈ {0,2; 0,4; 0,6; 0,8} + punto ancorato, ρ_corr = 0 (a40:14: 50 repliche per punto, seme 20261012). n = vincolo di tempo, non di potere (dichiarato).
   - **Bracci:** DIB (config raw `graph_free_unweighted_federation.yaml`, docstring di `h61b.py`: α 0,6, β 0,4, γ 0, θ 0,65, m = 2); B_frac(φ = 5/12, τ) = quota di siti ≥ φ, classe eleggibile e persistenza ≥ τ, con τ_match scelto a numero di candidati pari (regola di a41:41-42, con la stessa condizione di validità del 10%); riferimento B(2, τ) assoluta. Va allineata la definizione di persistenza (solo giorni in a40:9, giorni + frequenza in `dib.py:277-279`).
   - **Esito:** recall benigno per replica (quota degli endpoint benigni del profilo ammessi), mediana per punto con IC bootstrap sulle repliche (10 000, seme da fissare); regola di aggregazione fra i punti da fissare in audit 44 prima del lancio.
   - **Ostacolo da decidere (Q14b):** a41:54 ha **ritirato** S2 ("federazione sintetica ancorata ai profili UNSW") ed escluso UNSW; `h61b.py` usa i **profili per tipo** UNSW (`h61b.py:13-16`; letti da `/root/Desktop/DIB/data/processed/observations_enriched.csv`, fuori dalla repo, `h61b.py:104-105`), non i pseudo-siti (i siti sono sintetici: "Only the distribution over sites is synthetic", `h61b.py:16-17`). Per riaprire S2 serve o (i) una decisione esplicita che revochi il ritiro per i soli profili per tipo, dichiarata in audit 44, o (ii) un generatore benigno parametrico senza UNSW (Zipf su endpoint sintetici), che perde l'ancoraggio ai tipi reali.
8. **Dipendenze / durata / disco:** A1 (coperta); audit 44 committato prima, poi codice + test (rossi prima, mutazioni su φ e τ come per audit 40) committati prima dell'esecuzione. Offline, nessun nodo, nessuno ssh/sudo. Durata: `h61b` ha eseguito 170 punti × 200 repliche in 954,09 s con 12 worker (`runs/h61b/manifest.json`, chiavi `elapsed_s`, `workers`, `replicas`; 170 punti: docstring di `h61b.py`); per ~17 punti × 50 repliche la stima proporzionale è ~24 s, **non misurata** e senza il costo dei bracci nuovi. Disco: trascurabile, output fuori dalla repo o solo aggregati.
9. **Rischi:** il risultato può spostare il contributo ("quorum relativo con persistenza" invece di "breadth additivo"), con effetti su abstract e G1/G2: va discusso col supervisore prima di scrivere nel paper (Q13, Q14); la baseline frazionaria assume lo stesso N_d (denominatore = siti con almeno un'osservazione del tipo, `h61a.py` docstring R3).
10. **Repo:** solo definizione (audit 44), script in `experiments_tnsm/baseline_quorum_persistence/` o `analysis_fs/`, aggregati; nessun dato derivato da Mon(IoT)r.

## 3. Dopo il 16: sul nodo

### B0 — Rigenerazione PKI
1. **Domanda / paper:** nessuna (prerequisito di ogni braccio C/mTLS).
2. **Priorità:** INDISPENSABILE: la PKI scade **2026-10-13 08:22:10Z** (`M67/lan_20261011/pki_record.json:12`; a20:22); l'automazione si ferma da sola a PKI scaduta (a33:38).
3. **Ipotesi:** nessuna; controllo: SAN di `evidence` e `site-0` come in a20:22.
4. **Configurazione:** comando di a23:20-22 (`make_dist_pki.py … --valid-hours`; l'opzione accetta un float, `scripts/make_dist_pki.py:190`). **Rev. 2026-10-11: validità 336 h (14 giorni) dichiarata in `pki_record.json` e nel manifest di ogni blocco** (decisione presa, §7b Q12; sostituisce le 48 h): copre tutto il calendario di §4 senza rigenerazioni intermedie. La rigenerazione è obbligatoria comunque: la PKI attuale scade martedì 13/10 alle 10:22 ora italiana.
5. **Dipendenze:** disco verificato; vecchia PKI spostata (non cancellata) come in a23:20. Dopo ogni rigenerazione serve una cella C di prova (a23:25).
6. **Durata:** minuti (C.1 alle 08:24 UTC, a20:22). Disco: trascurabile, da verificare.
7. **Rischi:** nessuno noto oltre l'ora di scadenza.
8. **Stop:** `status` ≠ 200 nella cella di prova ⇒ stop.
9. **Repo:** `pki_record.json` (date, sha256 del manifest), mai chiavi.
- **[SSH-U]** per il comando; nessun sudo.
- **Verifica positiva dopo la scadenza (locale, nessun ssh, nessun sudo):** il 13/10 **dopo le 08:22:10Z** eseguire `python3 scripts/verify_artifact.py` e riportare "266 checks passed, 0 failed" (atteso su `revision-tnsm`, CLAUDE.md); se il numero è diverso, riportarlo com'è. Conferma sperimentale della lettura del codice qui sotto.
- **`verify_artifact.py` dipende dalla PKI? No (lettura del codice):** `scripts/verify_artifact.py` (376 righe) importa solo moduli standard (`:9-19`), non contiene alcun riferimento a `pki`, `cert`, `ssl`, `tls`, `.crt`/`.key`, `docker` o `ssh` (grep vuoto) e legge solo file sotto `results/` e `formal/` (docstring `:2-5`; `main()` `:354-375`). L'unico processo esterno è `pytest code/tests` con `--with-tests` (`run_unit_tests`, `:242-251`): i test mTLS creano una propria CA temporanea con la CLI di OpenSSL (`code/tests/tests/_mtls_ca.py:1-4`, che importa `scripts.make_dist_pki.CA` a `:15`) e nessun test legge `~/dib_tnsm/pki` (grep di `dib_tnsm`/`expanduser` in `code/tests` vuoto). La scadenza della PKI del nodo non tocca i 266 controlli; con `--with-tests` serve solo `openssl` in locale.

### B1 — Cella di fumo, test partition+restore con il vero watcher, calibrazione L_dns
**Rev. 2026-10-11:** diviso in **B1a** (smoke `lan`/`degraded` + L_dns; criteri (i) e (iii); *prima del 16*) e **B1b** (test partition+restore, criterio (ii); serve solo a B2p, *dopo il 16, condizionato a Q4+Q5*). Le voci 4-9 qui sotto valgono per B1a salvo dove citano la partition.
1. **Domanda / paper:** nessuna frase; prerequisito di B2 (a33:21-23; a36:29).
2. **Goal / priorità:** G3. INDISPENSABILE come prerequisito.
3. **Ipotesi (criteri di validità):** (i) catena `profile.applied` coerente su 11 container (a32:121-126, 173-180); (ii) `partition:site-N` → `restore` applicati e rimossi davvero (oggi nessun test di integrazione `ProfileCtl` ↔ `netem_watch2.sh`, a32:92); (iii) L_dns p95 ≤ 50 ms e poll del watcher ≤ 0,1 s, regola `ldns_decision` (`M67/night.py:38, 45-54`; a14:263).
4. **Configurazione:** smoke `lan` e `degraded` con il tree nuovo (marcatori di fumo per tree, a33:63); L_dns sito morto a `lan` e `degraded`.
5. **Dipendenze:** B0; watcher v2 attivo (**[SUDO-U]** installazione/avvio, a32:16-17, `netem_watch2.sh:38`); per (ii) servono codice e test (B2-partition non è in `run.py`: `--block` accetta solo `b1|b2kill|tcpdump`, `M67/run.py:95, 923`).
6. **Durata:** smoke `degraded` ~6,7 min (12:19:17-12:25:56, a32:173-180), smoke `lan` ~1,5 min (a32:182-186), L_dns ~1 min (a26:58); test partition: stima non fondata. Totale ~1-2 h con i passi manuali, stima non fondata. Disco trascurabile.
7. **Rischi:** **L_dns instabile** (p95 186 ms il 10/10, a21:16; ~3 ms l'11/10, a27:10, a34:52) ⇒ B2-kill potrebbe essere escluso dalla regola; due watcher in conflitto (a32:106-113); incoerenza transitoria alla creazione del cluster (a32:128-141); k3s e altri carichi di fondo sul nodo (a04:164-167; G4 non soddisfatta, a38:96); CPU QEMU generica senza AVX2 (a04:154): tempi non confrontabili con altre macchine.
8. **Stop:** battito > 10 s prima del lancio (a32:117), incoerenza del monitor (a32 §15). **L_dns: al massimo 2 tentativi di calibrazione, in giorni diversi; se entrambi danno p95 > 50 ms, B2-kill non si esegue e lo si dichiara nel paper e in un audit** (regola a14:263; nessun terzo tentativo, nessuna modifica della soglia).
9. **Repo:** marcatori, calibrazioni, sha256; nessun pcap.
- **Fine di ogni blocco:** file `STOP` (`netem_watch2.sh:26-27, 271`) e verifica positiva con `netem_show.sh` (**[SUDO-U]** per `nsenter`, `netem_show.sh:2-3, 7-9`) e `docker ps` senza container `dibtnsm` (a20:102).

### B2k — B2-kill
1. **Domanda / paper:** dopo la morte e il riavvio di un sito, quanto tempo serve perché il sito converga, e il tempo è entro un limite? Sostituisce "unreachable sites … remain outside this evaluation" (`wip:606`), l'ultima frase di `wip:640` e "no established withdrawal deadline" (`wip:780`) per la parte *dopo la riconnessione*.
2. **Goal / priorità:** G3. INDISPENSABILE: è l'unico esperimento che dà un limite misurato oltre i siti raggiungibili.
3. **Ipotesi (bozza):** (d-kill) convergenza dopo `start` ≈ 0,45 + U(0; 0,1·T) + D_run; bound 1,5 + 0,1·T + max(5 s, D_run_max); differenza delle mediane T15 − T5 in [0; 1,5] s (a14:254-257; `M67/run.py:90-92`). (e) nessuna violazione di I1-I3 e nessuna regola disputata esportabile oltre il bound (a14:261). Falsificazione: IC della mediana sopra il bound, o una violazione di (e); la differenza T15 − T5 è descrittiva (proposta §7b, Q9).
4. **Configurazione:** FANOUT 10, C e D, T ∈ {5, 15} (`M67/run.py:154-155`), 10 prove per cella (`run.py:312`). **Minimo:** `lan` e `degraded`, k ∈ {1, 10} = 1,69 h (somma righe a14:281-287 senza `wan` e senza k = 50). **Completo:** + `wan` + k = 50 a `lan` = 2,36 h (a14:288). **Potere:** con 10 ripetizioni la differenza attesa ≈ 0,5 s può non distinguersi dal jitter U(0; 0,1·T) ⇒ ~30 ripetizioni o (d-kill) solo descrittiva (a14:37): proposta in §7b (Q9): 10 ripetizioni, T15 − T5 descrittiva.
5. **Dipendenze:** B0, B1 (L_dns ≤ 50 ms p95 nello stesso blocco, watcher a 0,1 s, cella di fumo B2-kill: a32:75).
6. **Durata:** 1,69 / 2,36 h con L_dns veloce (a14:288); con L_dns = 186 ms 3,06 h (a22:49-69). Disco: dati di un blocco `degraded` B1 ~1,7 MB in repo (`du` di `M67/block_degraded_lan_after_20261011`); sul nodo da verificare.
7. **Rischi:** L_dns; fondo del watcher a poll 0,1 s (non misurato: a21:64 stima ~0,07 core solo a 0,5 s); un solo nodo; stallo fsync iniziale (a38:95) ⇒ celle di riscaldamento o ordine randomizzato; k3s e altri carichi di fondo (a04:164-167); CPU QEMU senza AVX2 (a04:154).
8. **Stop/esclusione:** `client_timeout` escluso e contato (a14:167); `transport_error_setup` escluso per episodio (a20:18); un solo nuovo tentativo e solo per un gruppo senza dati (a33:19-20); stop automatico per battito, df < 2 GB, PKI scaduta (a33:38).
9. **Repo:** `cells.jsonl`/`episodes.jsonl` del blocco (MB) e analisi; nessun numero di costo mTLS da questi dati (a33:21).

### B2p — B2-partition
1. **Domanda / paper:** convergenza dopo la rimozione di una partizione (perdita 100% in uscita da un sito, a14:160); `wip:606` cita "asymmetric partitions" come fuori valutazione.
2. **Goal / priorità:** G3. UTILE: copre il caso in cui il processo del sito resta vivo; costo alto e codice nuovo. Decisione (Q4+Q5).
3. **Ipotesi (bozza):** (d-part) convergenza ≤ 5 + 1,1·T + max(5 s, D_run_max); T15 − T5 in [3; 8] s (a14:258-260); (e) come B2k.
4. **Configurazione:** stessa griglia di B2k; disegno ridotto 260 prove (a14:303-314).
5. **Dipendenze:** codice in `run.py` (oggi assente, `run.py:95, 923`); helper sudo (`partition_helper.sh` proposto in a18:376-387, **non esiste**); il watcher v2 accetta già `partition`/`restore` (`netem_watch2.sh:10-16`; `profile_ctl.py:9, 24`); test di integrazione B1(ii).
6. **Durata:** 7,64 h (a14:314). Disco: MB, da verificare.
7. **Rischi:** come B2k (incluso k3s di fondo, a04:164-167, e CPU QEMU senza AVX2, a04:154); durata lunga ⇒ supera la validità della PKI se cade a cavallo (B0).
8. **Stop/esclusione:** come B2k.
9. **Repo:** come B2k.

### B3 — Profili `regional`, `mixed`, `extreme`
1. **Domanda / paper:** (a) e (c) fuori da `wan`/`degraded`; righe nuove in `tab:netem` (`wip:622`).
2. **Goal / priorità:** G3. `regional` (20 ms/0,1%, a14:155) sta fra `lan` e `wan`, già dentro la previsione (a) verificata a `wan`: **FUTURE WORK / taglio**. `mixed` (metà siti 80 ms/1%, a14:159) è l'unico che prova l'eterogeneità: **UTILE**. `extreme` (550 ms, "da confermare", a14:158) prova il regime di timeout al connect (a14:186-187): **FUTURE WORK**.
3. **Ipotesi (bozza):** (a) come a14:251 con R = d per i siti `wan` di `mixed`; (c) "0 osservati" a `regional`/`mixed` (a14:233-235), tutte in pending a `extreme` (a14:239).
4. **Configurazione:** C e D × FANOUT {1, 10}, 10 episodi per cella (a14:250), riferimento `lan` adiacente (a26 decisione, a20:22).
5. **Dipendenze:** B1. **`mixed` ed `extreme` esistono in `netem_apply.sh:33-40` e `run.py:120-127` ma il watcher v2 accetta solo `lan|regional|wan|degraded|restore|partition` (`netem_watch2.sh:10, 157`; `profile_ctl.py:22`)** ⇒ modifica del watcher, revisione del diff e reinstallazione **[SUDO-U]**.
6. **Durata:** per analogia con `wan` (calibrazione + B1 09:01:33-09:15:02, a27:6, 8) più due blocchi `lan` di riferimento (~4 min, a24:3): ~0,5 h per profilo; `extreme` stima non fondata (episodio C/1 fino a 30 s, a14:186). Disco: < 1 MB per blocco in copia locale.
7. **Rischi:** generatore a ~1,1 core (a18:303-313); L_dns non rilevante (siti vivi); k3s e altri carichi di fondo (a04:164-167); CPU QEMU senza AVX2 (a04:154).
8. **Stop/esclusione:** come B2k; calibrazione RTT fuori banda ⇒ blocco fallito per costruzione (a20:22, W1).
9. **Repo:** come B2k.

### B4 — Braccio `default` a `degraded` (P-a1, P-a2)
1. **Domanda / paper:** nessuna: `wip:615-640` riporta solo C e D. **Candidato al taglio.**
2. **Priorità:** taglio. Motivo: P-a1 prevede +61,5 ms a FANOUT 1 (a18:222), contro mediane di 10-17 s a `degraded` (`wip:632-633`) e IC larghi centinaia di ms; a `wan` l'effetto è già < 4% di R (a18:224). Il braccio esiste per caratterizzare il default "come spedito" solo a `lan` (a20:86; `run.py:26-29`); a `lan` P-a1/P-a2 sono già "non conclusivi" (a25:64-77).
3. **Ipotesi:** P-a1/P-a2 di a18:222-223 (definite per `lan`; a `degraded` andrebbero ridefinite).
4-9. Se tenuto: due celle nello stesso blocco di B5, 50 episodi; ~0,6 h, stima non fondata; rischi come B5 (incluso k3s di fondo, a04:164-167, e CPU QEMU senza AVX2, a04:154); repo come B2k.

### B5 — Nuova versione (a') con i tentativi falliti (pre-registrata, SOLO dati nuovi)
1. **Domanda / paper:** il modello "n_RTT·R + 1 s per tentativo fallito" prevede il tempo di ritiro a `degraded`? Il paper ha solo il calcolo post-hoc "not tested" (`wip:640`; a35:25-26, 119-143, 173). **La (a) originale resta falsificata 4/4 (a34:13-19) e non si riformula**; nessun dato vecchio entra in (a').
2. **Goal / priorità:** G3. INDISPENSABILE se il contributo è "ritiro limitato sotto rete degradata" (serve un modello del tempo che regga); altrimenti UTILE (Q4+Q5).
3. **Ipotesi (bozza):** soglia(cella) = n_RTT·R·(×10 se FANOUT 1) + E[F]·1 s + 3 × mediana `lan` adiacente, con E[F] = p + p² + p³ e **p fissato prima dai valori di profilo** (f per tentativo 0,185-0,226 D, 0,302-0,401 C, a14:236-237), non stimato dai dati che lo testano. Falsificata se l'estremo inferiore dell'IC della mediana supera la soglia (stessa forma di (a), `wip:617`); seconda clausola **chiusa (audit 46)**: verdetto separato "modello di base falsificato" se l'estremo superiore sta sotto n_RTT·R (limite fisico: il modello di base è sbagliato, non solo conservativo).
   **Trattamento del pending, fissato ora (prima dei dati):**
   - **Test pre-registrato = replica di (c), non una nuova predizione:** frazione di *consegne* in pending per cella, con IC di Clopper-Pearson, contro gli intervalli già ricavati dai valori di profilo (f³ per tentativo: D [0,004; 0,015], C [0,025; 0,08], a14:236-237; `wip:617`); falsificata se l'IC è interamente fuori dall'intervallo (stessa regola di (c), a34:54-60). Unità = consegna (come nei 9/960 e 32/960 di `wip:640`), perché è l'unità a cui si riferiscono gli intervalli.
   - **Frazione di *episodi* con almeno un pending: esito principale DESCRITTIVO, non primario.** Un intervallo atteso per episodio non è derivabile dalle fonti esistenti (a14:236-237 e a34:54-60 sono per consegna): richiederebbe un'ipotesi nuova di indipendenza fra i siti dello stesso episodio, che non è fra le predizioni registrate. Si riporta con IC di Clopper-Pearson, senza criterio.
   - **Esito su cui si valuta la soglia di (a'):** mediana del tempo di ritiro sugli episodi completi (nessuna consegna in pending), come in `tab:netem` (didascalia a `wip:621`). Tutti riportati sempre, con i rispettivi n.
   **Statuto:** è una **replica sullo stesso nodo e sullo stesso profilo** del blocco che ha falsificato (a), **non un test indipendente** (stesso host, stessa emulazione, stesso generatore co-locato); il paper deve dirlo così.
4. **Configurazione:** blocco `lan` prima → `degraded` → `lan` dopo, C e D × FANOUT {1, 10}, 50 episodi a `degraded` (a14:250) ⇒ n effettivo 31-46 per cella dopo le esclusioni del primo blocco (`wip:632-635`). n per continuità col primo blocco, non da potere.
5. **Dipendenze:** B0, B1; audit di pre-registrazione committato prima; codice di analisi con test prima (come `analyze_b1.py`/`analyze_c.py`, a20:22).
6. **Durata:** ~1,4 h (blocco 13:17:07-14:43:20, a34:6; a20:46). Disco: ~1,7 MB in repo per il blocco precedente (`du`); sul nodo da verificare.
7. **Rischi:** generatore co-locato; un solo nodo; `generator_path_ms` fresca anomala (607 ms, a34 §3, a36:70); fondo del watcher; k3s e altri carichi di fondo (a04:164-167); CPU QEMU senza AVX2 (a04:154).
8. **Stop/esclusione:** come il blocco precedente: `transport_error_setup`, `client_timeout`, esclusione per sovrapposizione (a20:55), regola R-gp (a20:55); un solo nuovo tentativo per gruppo senza dati (a33:19-20).
9. **Repo:** dati del blocco (MB), analisi, nessun pcap.

### B6 — M5 (numero di siti)
1. **Domanda / paper:** il throughput satura a N = 2? `wip:604` riporta ancora lo sweep vecchio (320,9 / 557,7 / … ops/s e "20.6% slower"), che **non si riusa** (a04:31-32, 117-119; a18:145, 231-233). Senza M5 la frase va tolta.
2. **Priorità:** UTILE per l'obiettivo 3 (scalabilità), nessun goal G1-G3. a18:204: "M5 esce dalla sequenza (stesso mix: non misurerebbe il fan-out)". Proposta (Q6, §7b): taglio e riscrittura di `wip:604`.
3. **Ipotesi:** H-M5 di a04:75 (guadagno fermo a N = 2; falsificata se N ≥ 20 supera N = 2 oltre gli IC).
4. **Configurazione:** N ∈ {1, 2, 5, 10, 20} (N = 50 escluso dal disco), 10 ripetizioni (a04:49, 62).
5. **Dipendenze:** B0; script nuovo (NON TROVATO; il vecchio è `code/scripts/distributed_site_count_sweep.sh`).
6. **Durata:** ~1,5 h (a04:62). Disco: **3-5 GB a N = 50** (a04:62), oltre i ~3,6 GB liberi (a22:85) ⇒ N ≤ 20 e/o pulizia (§5); fabbisogno a N = 20 da verificare.
7. **Rischi:** generatore a ~1,1 core (a18:303-313) può essere il limite; RAM 15 GiB (a04:155); k3s e altri carichi di fondo (a04:164-167); CPU QEMU senza AVX2 (a04:154).
8. **Stop/esclusione:** regola di scarto other_cores > 1,0 o steal > 2% (a37:10); df < 2 GB.
9. **Repo:** CSV di cella e manifest.

### B7 — M8 (firma MUD)
1. **Domanda / paper:** costo di `openssl cms` sign/verify per file esportato; il paper dice che le esportazioni non sono firmate (`wip:503`, `wip:782`).
2. **Priorità:** FUTURE WORK (o UTILE a costo minimo): misura un costo, non integra la firma nel percorso.
3. **Ipotesi:** sign + verify < 10 ms per file; falsificata se il p95 > 10 ms (a04:78).
4. **Configurazione:** 10 ripetizioni (a04:65).
5. **Dipendenze:** nessuna; codice NON TROVATO.
6. **Durata:** minuti (a04:65); disco trascurabile.
7. **Rischi:** CPU QEMU senza AVX2 (a04:154): tempi non confrontabili con altre macchine; k3s e altri carichi di fondo (a04:164-167).
8-9. Regola di scarto; CSV aggregato.

### B8 — M3 con un mix che eserciti il fan-out
1. **Domanda / paper:** `wip:602` dice "Including this fan-out, the ten-site HTTP deployment sustains 530.3 operations/s": numero vecchio (non si riusa) e, nel run nuovo, i fan-out cadono tutti nel warm-up scartato (a18:136), quindi H-M3a è "non falsificata ma non informativa" (a18:143).
2. **Priorità:** TAGLIO proposto (Q7, §7b): `wip:602` va riscritta senza "Including this fan-out" e senza 530,3.
3. **Ipotesi (bozza):** validità = contatore di fan-out nelle fasi cronometrate > 0 per cella (oggi non registrato: log non salvati, a18:121, 138); poi H-M3a nella forma ±10% (a18:29).
4. **Configurazione:** come M3 (40 celle, a18:9) con quota di dispute/restore nelle fasi cronometrate.
5. **Dipendenze:** B0 (braccio C); codice nuovo.
6. **Durata:** ~1,1 h (20:19-21:27, a18:5). Disco: MB.
7. **Rischi:** generatore a ~1,1 core (a18:313); k3s e altri carichi di fondo (a04:164-167); CPU QEMU senza AVX2 (a04:154); nessun commento sulla forma C/D o sul plateau a 100 writer (a33:21).
8-9. Come M3.

## 4. Calendario (rev. 2026-10-11 sera): ciò che resta valido qualunque cosa risponda il supervisore si esegue prima del 16

Ogni blocco: un profilo alla volta, `STOP` + `netem_show.sh` + `docker ps` puliti prima del successivo; ogni ssh **[SSH-U]**, ogni sudo **[SUDO-U]**, uno per volta, autorizzati dall'utente.
**Si esegue prima del 16:** A2 passo 1 (Δ; probabilmente chiude A2 e A3), A4 (audit 42 poi calcolo), B0, B1a, B2k completo (`lan`/`degraded`/`wan`, k = 1/10/50, 2,36 h: misura la convergenza dopo la riconnessione, utile con o senza lease; la versione completa costa +0,67 h sulla minima), B5 (1,4 h; se Q4+Q5 dice di non rifare (a'), i dati restano in `experiments_tnsm/` e non entrano nel paper), ~~A5 parametrica~~: **ritirata come test (c)**, resta l'argomento analitico.
**Si prepara ma non si lancia:** codice di B2p e helper sudo, con i test (decide Q4+Q5). **Non si lanciano:** B4, B6, B8 (tagli, §7b); B3 `mixed` solo se resta tempo giovedì (richiede modifica del watcher + revisione del diff + **[SUDO-U]**). Nessun braccio UNSW di A5 (ritirata).
**Pre-registrazioni da committare prima dei dati:** audit 42 (tabella (α, θ)); audit 44 (A5: **ritiro motivato**, non una pre-registrazione; δ non serve più); audit 45 (B2k: Q9 = 10 ripetizioni e T15 − T5 descrittiva, regola di stop su L_dns); audit 46 (B5: seconda clausola inclusa, clausola inferiore = verdetto separato "modello di base falsificato", distinto da "(a') falsificata per eccesso"; regola globale: (a') falsificata se almeno 1 cella su 4, riportata come k/4). File: `42_prereg_tabella_alpha_theta.md`, `44_ritiro_A5_quorum_frazionario.md`, `45_prereg_B2k.md`, `46_prereg_B5_aprime.md` (commit in quest'ordine: 45, 42, 44, 46).

| Giorno | Offline | Nodo ([SSH-U]/[SUDO-U], uno per volta) |
|---|---|---|
| Dom 11 (stasera) | scelta di `docs/main_wip.tex` come copia canonica (§8); A2 passo 1; scrittura e commit di audit 42, 44, 45, 46 | — |
| Lun 12 | calcolo di A4; verifica dei CSV di `results/sensitivity/` per audit 42 (solo intestazioni, configurazioni, script) | `df` → B0 (validità lunga, §7b Q12) → avvio watcher v2 [SUDO-U] → smoke `lan` e `degraded` → L_dns, tentativo 1 → se p95 ≤ 50 ms, B2k nello stesso blocco |
| Mar 13 | dopo le 10:22 ora italiana (08:22:10Z), `python3 scripts/verify_artifact.py` (atteso: 266 checks passed, 0 failed) | se lunedì L_dns è fallita: tentativo 2 e B2k; altrimenti B5 |
| Mer 14 | (libero: A5 ritirata) analisi di B2k | B5 se non fatta martedì; poi pulizia (`STOP`, `netem_show`, `docker ps`) |
| Gio 15 | riassunto di una pagina per il 16, con i risultati | margine per ripetere; facoltativi B3 `mixed` e B7 |

Le due prove di calibrazione di L_dns cadono in giorni diversi (lun 12, mar 13), come vuole la regola di B1 (stop), e lasciano un giorno di margine. Tempo sul nodo: ~5-6 h in totale su 2-3 giorni (stima dell'utente; la mia somma delle voci è sotto: B1a 0,5-1,0 + B2k 2,36 + B5 1,44 = 4,3-4,8 h, più L_dns tentativo 2, pulizie e margine). Al supervisore si portano risultati già misurati di B2k e B5 e, per Q14, la caratterizzazione analitica di A5 (DIB = quorum frazionario φ = 5/12 con soglia di persistenza decrescente 1,625 − 1,5·C_s; stessa protezione contro evidenza solo-avversaria per costruzione): Q2 e Q13/Q14 diventano "cosa ne facciamo", non "cosa misuriamo".

**Calendario precedente (percorso minimo/completo dopo il 16), conservato come riferimento per ciò che resta dopo il 16 (B1b, B2p, B3, B6-B8):**

| Giorno | Percorso MINIMO | Percorso COMPLETO (in più) |
|---|---|---|
| 0 (prima del 16) | A4 (audit 42 + calcolo), A1 | A2, A3 |
| 1 | `df`/`docker system df` [SSH-U]; B0 [SSH-U]; watcher v2 [SUDO-U]; B1 (smoke `lan`, `degraded`, partition+restore, L_dns) | — |
| 2 | B2k minimo (1,69 h) | B2k `wan` + k = 50 (+0,67 h) |
| 3 | B5 (pre-registrazione committata prima; blocco ~1,4 h) | B4 nello stesso blocco (+~0,6 h, se non tagliato) |
| 4 | — | B0 di nuovo (48 h); B3 `mixed` (+ `regional`/`extreme`) ~0,5 h ciascuno |
| 5-6 | — | B2p 7,64 h (dopo codice + helper) |
| 7 | — | B6 ~1,5 h, B7 minuti, B8 ~1,1 h |

**Totali (ore-nodo, stime), calcolo riga per riga:**

*MINIMO*
| Voce | Calcolo | Ore | Fonte |
|---|---|---|---|
| B1 | smoke, partition+restore, L_dns, passi manuali | 1,00-2,00 | stima non fondata (parti: a32:173-186, a26:58) |
| B2k `lan`, k = 1, T 5/15 | 0,035 + 0,038 | 0,073 | a14:281 |
| B2k `degraded`, k = 1 | 0,152 + 0,155 | 0,307 | a14:283 |
| B2k `lan`, k = 10 | 0,063 + 0,066 | 0,129 | a14:284 |
| B2k `degraded`, k = 10 | 0,590 + 0,593 | 1,183 | a14:286 |
| *B2k minimo* | 0,073 + 0,307 + 0,129 + 1,183 | *1,692* | |
| B5 | 13:17:07 → 14:43:20 = 86,2 min | 1,437 | a34:6 |
| **Totale MINIMO** | 1,00 + 1,692 + 1,437 = 4,129; 2,00 + 1,692 + 1,437 = 5,129 | **4,1-5,1** | |

*COMPLETO* (= MINIMO +)
| Voce | Calcolo | Ore | Fonte |
|---|---|---|---|
| B2k `wan`, k = 1 | 0,076 + 0,078 | 0,154 | a14:282 |
| B2k `wan`, k = 10 | 0,161 + 0,163 | 0,324 | a14:285 |
| B2k `lan`, k = 50 | 0,188 | 0,188 | a14:287 |
| *B2k in più* | 0,154 + 0,324 + 0,188 | *0,666* | (controllo: 1,692 + 0,666 = 2,358 ≈ 2,36, a14:288) |
| B4 | due celle × 50 episodi | 0,6 | stima non fondata |
| B3 | 3 profili × ~0,5 h | 1,5 | analogia con a27:6, 8 e a24:3 |
| B2p | disegno ridotto | 7,64 | a14:314 |
| B6 | N ≤ 20, 10 ripetizioni | 1,5 | a04:62 |
| B7 | "minuti" | 0,1 | a04:65 (0,1 h è mia stima di "minuti") |
| B8 | 20:19 → 21:27 = 68 min | 1,1 | a18:5 |
| *Somma in più* | 0,666 + 0,6 + 1,5 + 7,64 + 1,5 + 0,1 + 1,1 | *13,106* | |
| **Totale COMPLETO** | 4,129 + 13,106 = 17,235; 5,129 + 13,106 = 18,235 | **17,2-18,2** | |

*COMPLETO senza i tagli proposti (B4, B6, B8; §7b)*
| Voce | Calcolo | Ore | Fonte |
|---|---|---|---|
| Tagli | B4 0,6 + B6 1,5 + B8 1,1 | 3,2 | righe sopra |
| **Totale COMPLETO senza tagli** | 17,235 − 3,2 = 14,035; 18,235 − 3,2 = 15,035 | **14,0-15,0** | |

- Disco MINIMO: dati di blocco nell'ordine dei MB (copie locali: blocco `degraded` 1,7 MB, `du`); occupazione lato nodo (log dei container, immagini) **da verificare**.
- Disco COMPLETO: dominato da B6 (3-5 GB a N = 50, a04:62; con N ≤ 20 da verificare) ⇒ serve pulizia (§5) per restare sopra la soglia di 2 GB (a33:38).

## 5. Pulizia del disco: SOLO candidati (nessuna cancellazione; spazio da riverificare dall'utente)
Ultima lettura: `~/dib_tnsm` ~0,7 GB (venv 540 MB, out 2,3 MB, 19 tree), Docker immagini 19,54 GB di cui 11,02 GB riclamabili, cache di build 1,862 GB di cui 1,837 riclamabili, ~68 GB su 90 non spiegati (k3s e altro) (a23:35-36).
1. Immagini `dibtnsm-*` vecchie non usate (parte degli 11,02 GB): richiede prima `docker image ls` [SSH-U] (a23:37). **Unico candidato che libera GB.**
2. Cache di build 1,84 GB: `docker builder prune` agisce su tutto l'host (a23:37): solo con OK esplicito.
3. 11 tree vecchi (~0,23 GB, a23:28): sconsigliato; **tenere** `6b8a6fa`, `a7b53af`, `bf272e8` (provenienza dei dati, a23:28) e `244f1d0` (tree corrente, a33:27).
4. `~/dib_tnsm/pki_scaduta_20261011` (a23:20): trascurabile.
5. `~/dib_pcap/` (MB, copiati con sha256, a20:22): trascurabile.
6. Output già copiati con sha256 (`out/night_20261011`, smoke, blocchi): trascurabili (out 2,3 MB, a23:35).

## 6. Promozione in `results/` (oggi solo G0b): criteri e ordine, nessuna esecuzione
**Modello G0b** (a15:67-74): copia byte per byte da `experiments_tnsm/`, README con servizio congelato e sha, tree e commit del run, host, durata, "nessuna ipotesi pre-registrata" se vale; controlli nuovi in `scripts/verify_artifact.py` (`check()` a :35-44) e aggiornamento del conteggio atteso (262 → 266, a15:72-74) e di `claims.json` (`52888bd`).
**Criteri (proposta):** (1) ipotesi committate prima dei dati e verdetti in un audit; (2) numero già scritto nel paper; (3) solo aggregati, mai derivati per dispositivo da Mon(IoT)r/YourThings; (4) dati originali che `results/` sostituisce restano nella storia git; (5) ordine solo su OK dell'utente.
**Ordine proposto:** B1 `wan`/`degraded` (`tab:netem`) → M1/M2 notte (paragrafo `7091f37`) → M4 C/D (solo rapporto) → B2k → B5 → 5.3b → tabella (α, θ). **Proposta (Q10, §7b):** `results/distributed` e `results/site_count` (530,3; sweep; 20,6%) sono controllati da `verify_artifact.py:189-212` e citati in `claims.json:43, 211`: marcarli superati, senza cancellarli.

## 7. Domande aperte per il supervisore
- Q1. Numerazione dei goal: G1-G3 proposti contro `wip:153-159`; G3 diventa "limitato" (contro `wip:164` "no deadline")?
- Q2. **Lease: design o future work?** Senza lease, "limitato" vale solo per siti raggiungibili e dopo la riconnessione (`wip:179, 487, 780, 792`).
- Q4+Q5. **Ambito di G3 sotto rete degradata:** B2-partition dentro (codice + helper sudo, 7,64 h, a14:314) o solo B2-kill? E (a') su dati nuovi (replica sullo stesso nodo, non test indipendente) oppure si riporta (a) falsificata + calcolo post-hoc e basta?
- Q11. Limite di 10 pagine: quali tabelle hanno spazio (righe nuove di `tab:netem`, B2, (α, θ))?
- Q13. **Eligibility di default:** punteggio o quorum + classe + persistenza (il punteggio come politica sostituibile)? Dalla risposta dipende la priorità di A4: sui laboratori reali B(2, τ_match) dà le stesse metriche di DIB in 3/3 riceventi (A1), quindi il valore aggiunto del punteggio sta nel regime a N siti e nel bound di G1/G2.

- Q14. **Il breadth additivo è un contributo o un quorum relativo ben calibrato?** Il confronto su `k_hist.json` è una tautologia (A5, punto 4). **Rev. 2: scelta (c), A5 ritirata come test.** Scelta precedente (superata): (b) riedizione di S2 pre-registrata (simulazione benigna a N ≥ 10 siti, A5 punto 7); (a) confronto analitico e (c) "non decidibile con 3 laboratori" restano come complemento o ripiego.
- Q14b. **Decaduta con il ritiro di A5.** (Testo originale:) S2 era stata ritirata in a41:54 (profili UNSW esclusi): per rifarla si revoca il ritiro per i soli profili per tipo (siti sintetici, nessun pseudo-sito) o si usa un generatore benigno parametrico senza UNSW?

## 7b. Decisioni dell'autore (proposte, da confermare dall'utente; non vanno al supervisore)
- Q3. Profili: nessun profilo nuovo nel percorso minimo; `mixed` solo nel completo (scheda B3). *Proposta del piano: non indicata nelle correzioni dell'utente.*
- Q6, Q7, Q8. **Taglio** di M5 (B6), di M3 con fan-out (B8) e del braccio `default` (B4), e **riscrittura di `wip:602-604`** senza i numeri vecchi (530,3; sweep N; 20,6%) e senza "Including this fan-out".
- Q9. B2-kill con **10 ripetizioni** per cella; la differenza T15 − T5 è **descrittiva** (nessuna falsificazione su quel termine, per il potere di a14:37).
- Q10. `results/distributed` e `results/site_count`: **marcati come superati, senza cancellare** (README con rimando all'audit; i controlli di `verify_artifact.py:189-212` restano finché non si decide altrimenti).
- Q12. **DECISIONE PRESA (utente, 2026-10-11): PKI con validità effettiva di 336 h (14 giorni) dalla rigenerazione di lun 12/10**, dichiarata nel `pki_record.json` e nel manifest di ogni blocco (sostituisce le 48 h di a23:21; evita rigenerazioni a metà calendario). La scadenza effettiva va riletta da `pki_record.json` dopo la rigenerazione e riportata qui.

## 8. Discrepanze trovate durante la lettura (da correggere, non corrette qui)
- a41:3 e a41:58 dicono "non committata" ma a41 è in `2af2d89`; `run_20261012/` non è tracciata.
- `wip:602-604` e `docs/main_tnsm.tex:526, 528` contengono ancora 530,3, lo sweep e il 20,6%.
- Nomenclatura delle fasi di 5.3b (a41:58 nomina solo la Fase B), fissata in questo piano: **Fase B** = riproduzione di `matched_ablation.csv` (A1), **Fase C** = calcolo 5.3b (A2, A3), **Fase D** = tabella (α, θ) (A4).
- **Due copie di lavoro del paper (`docs/main_wip.tex` e `docs/main_tnsm.tex`): decidere la canonica.** CLAUDE.md nomina `docs/main_tnsm.tex` come copia di lavoro, mentre gli ultimi commit sul testo (`75d1b19`, `7091f37`) modificano `docs/main_wip.tex`. Output grezzo (righe presenti SOLO in `docs/main_tnsm.tex` nel terzo comando; nessuna modifica ai `.tex`):
```
$ sha256sum docs/main_wip.tex docs/main_tnsm.tex
d8777ac361936d3d068aab91bf9703bf2cf8827a1301b9ea24799b0495d7a190  docs/main_wip.tex
95502c33734b16da6b3fec895d35f70586d1f3420a406ebbf9b5f34652fc4f35  docs/main_tnsm.tex
$ wc -l docs/main_wip.tex docs/main_tnsm.tex
   990 docs/main_wip.tex
   885 docs/main_tnsm.tex
  1875 total
$ git diff --no-index --stat docs/main_tnsm.tex docs/main_wip.tex
 docs/{main_tnsm.tex => main_wip.tex} | 207 ++++++++++++++++++++++++++---------
 1 file changed, 156 insertions(+), 51 deletions(-)
```
```
$ git log --oneline -- docs/main_tnsm.tex | head
874aafb main_tnsm: group 4, table 'experiment -> configuration' (tab:configs) and scoring configuration in the captions of tab:threelab, fig:pareto, tab:symbols
680fe72 main_tnsm: group 3, dangling 'P5' (never defined) replaced by a reference to Criterion 1 (raw breadth)
153ca76 main_tnsm: group 2, port-masquerading paragraph reports measured values with their configuration (trust-weighted, seed 42) and the raw-breadth worst case (0.579)
6478e6c main_tnsm: group 1, state Criterion 1 and the 5/12 bound for raw breadth everywhere (Sec. III trust boundary, A2 definition, f* paragraph, Criterion, Secs. VI-D/E)
3f37dc3 docs: main_tnsm.tex, starting point, byte-identical copy of DIB_clean/docs/main.tex (sha256 3fdd7489214f328e0384d2553b30da086480ca7717ac0fb26c6a2c59548f9437)
$ git log --oneline -- docs/main_wip.tex | head
7091f37 main_wip: M1/M2 paragraph replacing the old registry paragraph (3 repetitions, 20 operations per worker, 'all 9,660 operations without unexpected errors', SQLite-attribution sentence): both configurations, 10/20 repetitions, 200 operations per worker; throughput 50 -> 100 writers; deployment H-M1b falsified (27/50 cells with errors); pool-checkout censoring reported apart from latency (default: 20/20 cells at 100 writers, 1/10 at 50 at the 30 s ceiling, no p99 reported); M2 tail shares (0.52 before the lock, 0.0002 commit, Gini 0.06, processes 1.44x, null 247x); numbers from audit 38
75d1b19 main_wip: 1.3, consolidation of Sec. III (System Model, Design Goals, Threat Model): the \todoM placeholder after 'imposes no deadline on withdrawal' replaced by the reference to the measured withdrawal times (sec:netem-results), which is also added to the sections that test G3; G1-G3, AS1-AS6 and A1-A4 are otherwise already consistent with audit 09:43 and 16:129 (A1 honest sites reporting compromised devices and extra identities are in AS2 and the adversary model)
49d43af main_wip: 3.9, new subsection 'Withdrawal Under Emulated Network Delay and Loss' (sec:netem-results, tab:netem): B1 at wan and degraded with the pre-registered predictions (a) and (c), reporting (a) FALSIFIED at degraded in 4/4 cells (excess 1.2-4.8 s), (a) holding at wan, (c) not falsified (D 9/960, C 32/960, each interval crossing a bound), 8/200 episodes excluded, and the retry arithmetic as a post-hoc, untested calculation; the two sentences that said WAN is outside the evaluation updated; numbers from audit 27, 34, 35
29873d7 main_wip: 3.10, outage/reconciliation numbers updated to the regenerated results/fault_injection (062b417): 0.480 +- 0.017 s (30 trials), 0.509 +- 0.034 s (10), restart ~0.42 s, reconciliation call 71 ms mean and 105 ms max; the abstract's 'under 100 ms' (inside the \add blocks only) becomes 'about 70 ms on average' because the maximum now exceeds 100 ms; values recomputed from results/fault_injection/trials.csv
c169c1f docs: main_wip.tex, baseline of the user's offline working version (untracked until now, 961 lines, descends from main_tnsm.tex groups 1-4: restructured Sec. III with G1-G3, AS1-AS6, adversary model; Security Analysis; parameter table with placeholders); committed unmodified so that each following edit is one reviewable commit; main_tnsm.tex untouched
$ git diff --no-index docs/main_wip.tex docs/main_tnsm.tex | grep '^+' | grep -v '^+++' | head -60
+\del{To demonstrate the robustness of this framework, an exhaustive exploration of finite lifecycle models finds no property violations, and six guard-removal mutations expose distinct authorization failures. An OpenWrt/osMUD testbed demonstrates the application and withdrawal of rules. Disconnected sites reconcile through a single collapsed update; the reconciliation logic takes under 100~ms in the evaluated deployment. Experiments on three IoT traffic datasets characterize candidate selection separately from authorization. Threshold admission restricts candidates under a bounded malicious-share assumption, while score-based ordering prioritizes review. Ranking the pooled candidate set achieves a comparable review yield at matched budgets.} \add{We evaluate DIB through exhaustive lifecycle model checking, an OpenWrt/osMUD testbed, and experiments on three IoT traffic datasets. The results show that DIB works as intended: it preserves local authorization during coordinated withdrawal and recovery, reconciles disconnected sites in under 100~ms in the evaluated deployment, and supports flexible candidate selection.} \del{These results support configurable candidate selection within a lifecycle that preserves local decisions during coordinated recovery.}\add{Overall, the tests confirm that DIB works as intended, with reconciliation taking under 100~ms in the evaluated deployment.}
+The remainder of this paper is organized as follows. Section~\ref{sec:related-work} reviews related work. Section~\ref{sec:threat} defines the setting and design goals. Section~\ref{sec:design} presents DIB. Sections~\ref{sec:impl} and~\ref{sec:eval} describe the proposed implementation and its evaluation. Finally, Section~\ref{sec:discussion} discusses implications and limitations.
+%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
+%%%     Section III: Threat Model     %%%
+%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
+\section{Design Goals and adopted Threat Model}
+In our proposed approach, we consider a closed consortium of independently administered networks, called \emph{sites}.
+Each consortium member can share network observations (i.e., endpoint facts), while each site controls the rules installed on its gateway and can locally deny any of those rules.
+\subsection{Design Goals}
+We designed DIB with those four design goals in mind:
+    \item \textbf{G1: Candidate discovery.} Propose communications from shared observations for a certain IoT device is enabled only when a MUD file for that specific device is not available.
+    % si attiva solo se i mud file non esistono (o ibrida)
+    %vogliamo proteggere, a priori, l'archi
+    \item \textbf{G2: Conditional admission protection.} To each endpoint fact is associated a reliablity score. To be exposed to other sites, the score must be higher than a certain threshold.
+    \item \textbf{G3: Local authorization.} Importing external endpoint facts is allowed only after approval by the site's administrator.
+  %\item \textbf{G3: Review workload.} Filter and prioritize candidates for administrator review.
+  %
+  \item \textbf{G4: Revoking criteria} % Evidence and score changes must not grant or revoke permissions; disputes and operator actions follow the lifecycle rules.
+  DIB implements a precise lifecycle for sending dispute messages and for automatically revoking suspicious endpoint facts.
+  % due dispute 
+  % \item \textbf{G3: Conditional admission protection.} With \emph{raw breadth} (the unweighted fraction of eligible sites reporting a fact), admission rejects adversary-only evidence under the share bound in Sec.~\ref{subsec:trust} and parameter constraint in Criterion~\ref{crit:poison-bound}. This does not establish benignity; Sec.~\ref{sec:sensitivity-results} evaluates its limits.
+Considering the presented goals, our threat model considers and analyzes the two major risks faced by our proposed approach during an update instruction received from the network: (i) the possibility that a locally denial rule is restored, and (ii) the erasing of a locally created rule.
+
+% g1 e g3 tautologici, threat model solo su g2
+\subsection{Setting and Trust Boundary}
+Deployment requires authenticated membership and role enforcement. One deployment option is mutual Transport Layer Security (TLS) with enterprise Public-Key Infrastructure (PKI), binding each member's X.509 certificate to a site identifier and its permitted API operations. Device-type labels must also be aligned before ingestion. The prototype does not validate this authentication integration; the experiments exercise the lifecycle with trusted caller identities. Admission further assumes that malicious contributors control at most a raw breadth share $f_s$ of the eligible reporting population for a device type (Sec.~\ref{sec:scoring}). Identity-inflation tests deliberately exceed this bound.
+\textbf{Policy authority}: DIB produces locally authorized MUD files: the receiving site's MUD manager signs these exports, and the gateway trusts that site's policy-signing authority. Peer sites and the shared evidence service can therefore request withdrawal, but cannot issue local permissions. This trust configuration is a deployment requirement. 
+% The enforcement testbed uses unsigned exports with signature validation disabled. - to do 
+
+We evaluate three distinct adversarial behaviors: (i)~\textbf{A1 (Poisoned Observations)}, where an honest site captures and reports real malicious flows from an already compromised device; (ii)~\textbf{A2 (Fabricated Evidence)}, where contributors report fabricated traffic that did not occur (bounded by raw breadth share $f_s$, or unbounded in Sybil stress tests); and (iii)~\textbf{A3 (Low-and-Slow Behavioral Drift)}, where actual device activity changes gradually across sites to mimic a legitimate rollout. A1 tests -----.A2 tests invented reports; A3 tests the ambiguity of observed behavior.
+Local network administrators authorize permissions within their own domain, so misuse of a local approval or revocation is an insider action. Remote contributors can introduce unsuitable candidates or raise baseless disputes, but, according to the DIB specification, they can never create local authorization. Under A3, legitimate and malicious activities with identical traffic patterns produce the same evidence and score, and separating them requires local review or out-of-band information.
+
+% report message spiegare e cambiare nome in caso
+% questa è la cosa che mappa il goal 2
+
+\textbf{Consortium authority}: Any participating site can \emph{raise a dispute}. The first dispute (executed via a report message) suspends export, and a report from a second distinct site confirms the revocation. \emph{Global restoration} is a privileged consortium operation; local approval, revocation, and restoration are reserved for the receiving site's network managers. Sec.~\ref{sec:suspension-policy} evaluates the availability trade-off of one versus two reporters. The safety properties I1--I3 (Sec.~\ref{subsec:lifecycle}) concern lifecycle transitions under authenticated identities: the prototype and finite model expose transitions to a trusted harness, so caller authentication and role enforcement are deployment assumptions rather than verified mechanisms.
+$f_s$ & assumed adversarial breadth share & 0.30 \\
+\textbf{Combined rule}: Automatic staging requires endpoint eligibility, at least $m$ reporting sites, score at least $\theta$, and no unresolved dispute. We use $m=2$ to exclude single-site reports without a larger quorum's admission cost; distinct identities do not guarantee independent observations:
+The 0.7/0.3 split weights day coverage above the pooled volume. Counts are pooled without per-site normalization, so a single reporter can supply the whole volume term (at most $0.3\beta=0.12$ of the score) and, by reporting on every active day, the whole day-coverage term. $C_t$ therefore enters Criterion~\ref{crit:poison-bound} only through $C_t\le1$: the split changes how much persistence a fact with sufficient breadth needs, not the safety bound. Because $n_{d,e}/n_d$ is structurally small for device types with many endpoints, $C_t$ is in practice dominated by day coverage. We hold this split fixed and sweep only $\theta$ and $\alpha$ (Sec.~\ref{sec:sensitivity-results}).
+\textbf{Parameter derivation.} The weights are not free. Since $\alpha+\beta=1$, only $(\alpha,\theta)$ remain, and a single quantity links them, the \emph{breadth margin}
+Because $C_t\le1$, a fact whose reporters hold raw breadth share $c$ can reach $\theta$ only if $c\ge f^\star$. Hence $f^\star$ has two readings: it is the largest adversarial share the score alone can absorb, and the smallest breadth at which a benign fact can pass even with perfect persistence. Raising $\theta$ or $\alpha$ raises $f^\star$, which gives more protection but requires more breadth from benign facts (less recall); Sec.~\ref{sec:sensitivity-results} measures this trade-off. At $(\alpha,\theta)=(0.6,0.65)$, $f^\star=5/12\approx0.417$.
+At $\theta=0.65$ and $f_s=0.30$ this requires $\alpha>0.5$. Choosing $\alpha=0.6$ gives an upper bound of 0.58 and rejects adversary-only evidence for raw-breadth shares below $5/12$. The guarantee holds per device type and the bound is a supremum: it is reached only if $C_t=1$, which requires that no honest observation of $d$ exists, so a share of exactly $5/12$ is also rejected. In counts, with $K$ adversarial and $h$ honest reporting sites for $d$, the guard holds if and only if $K<\frac{\theta+\alpha-1}{1-\theta}\,h$, that is, $K<\frac57h$ at the operating point. For example, three colluders require at least five honest sites at the margin and at least seven at the declared share $f_s=0.30$. With two or three reporting sources the quorum $m=2$, not the score, rejects single-source facts. Sec.~\ref{sec:sensitivity-results} evaluates coverage at alternative parameters.
+\textbf{Why $f_s=0.30$.} We treat $f_s$ as a budget below the margin, not as a measured prevalence. It lies below $f^\star=5/12$, leaving a margin of 0.117, and below the $1/3$ fault fraction that classical Byzantine agreement tolerates ($n\ge3f+1$)~\cite{lamport1982byzantine,castro1999pbft}. We use the latter only as an order-of-magnitude reference, because the DIB guard is a threshold on reporting share and not an agreement protocol. Measurement studies do not give one prevalence to match. Mirai peaked at about 600{,}000 infections, but the study reports no per-type share~\cite{mirai}. A home-network study finds that 1.3\% of devices in the homes seen scanning (0.37\% of homes) were already compromised through an EternalBlue backdoor, and notes that scan data rarely shows compromise~\cite{kumar2019allthings}. A ten-month study of 1{,}362{,}906 deployed devices finds 28.25\% with at least one known vulnerability, with rates by vendor from below 0.5\% (some industrial-control vendors) to 100\% (one printer vendor)~\cite{zhao2022largescale}. Vulnerable is not compromised, so 0.30 is conservative against measured compromise and matches the order of magnitude of vulnerable prevalence.
+A probabilistic reading makes the budget explicit. If $n$ devices of type $d$ share a site and each is compromised independently with probability $p$, the site reports compromised traffic with probability $q=1-(1-p)^n$; for $p=0.10$ and $n=4$, $q=0.34$. If sites are adversarial independently with probability $q$, the guard fails when $K\ge\lceil5N_d/12\rceil$. For $q=0.10$ this has probability $1.6\times10^{-3}$ at $N_d=10$, $6.0\times10^{-5}$ at $N_d=20$, and $3.7\times10^{-9}$ at $N_d=50$; for $q=0.30$ it is 0.15, 0.11, and 0.048. The deterministic guarantee therefore covers $K\le\lfloor0.30N_d\rfloor$ (three sites at $N_d=10$), and $f_s$ is better read as a quantile of the compromise distribution than as its mean. Correlated sites (shared firmware, shared vendor cloud) make the independent tail an underestimate.
+Here, $b_i$ counts site $i$'s distinct contributed facts across device types, and $b_{ref}$ is their median in a frozen clean snapshot. Only $b_{ref}$ is frozen, so current $b_i$ includes new identities and padding. Clustering instead joins sites at Jaccard endpoint-set similarity $\ge0.8$ and computes breadth over the connected components. The registry and independent-deployment experiments use raw breadth, to which Criterion~\ref{crit:poison-bound} applies. Sec.~\ref{sec:sensitivity-results} compares all three under identity inflation. These variants rely on a clean reference or informative endpoint diversity and fall outside the raw-breadth bound.
+Evidence updates are tested separately from lifecycle events (G4). With the same fact in Active, MonitorOnly, and locally Revoked states at three respective sites, repeated score changes leave decision states, authority records, and MUD export unchanged. Only Active records receive a review flag, with the change recorded in the audit history. This result comes from registry tests, since the finite model represents admission only as a Boolean.
+The registry measurements characterize both typical latency and delays under contention. On a 16-core x86\_64 Linux host running Python 3.10.13, each of 1/10/50/100 writers performs 20 mixed operations after the same warm-up procedure. At 100 writers, throughput reaches $317.5\pm10.8$ operations/s and median latency is $3.8\pm0.2$~ms (mean $\pm$ sample SD over three repetitions), but p99 approaches 5.9~s. Instrumentation attributes this tail to SQLite's single serialized writer rather than lifecycle logic. All 9,660 timed operations complete without unexpected errors.
+When a site becomes unreachable, the service retains only its latest pending target for each fact rather than every missed update. Reconnection applies that target through the same idempotent path, using a monotonic per-fact sequence number. A restore target therefore invalidates an old Active approval even if the preceding dispute never reached the site. Container stops simulate disconnection; WAN latency, packet loss, and asymmetric partitions remain outside this evaluation.
+All 40 outage trials converge after reconnection through one collapsed pending record. Missing one event type---dispute-open, confirming-dispute, or restore---leads to convergence in $0.51\pm0.03$~s over 30 trials. Missing an entire dispute/confirmation/restore episode invalidates the stale approval through the final MonitorOnly target in $0.50\pm0.04$~s over ten trials (mean $\pm$ sample SD). Another 20 trials exercise races with new fan-out events and check that sequence numbers preserve the current target. Process restart ($\sim$0.45~s) accounts for most of the recovery time; reconciliation logic takes less than 0.1~s.
+In UNSW, only 55 of the 564 reference ACEs across 28 profiles remain observable after address filtering; 61 to-device entries cannot appear in device-initiated input. DIB stages 36 of the observable ACEs, retaining 65.5\% of observable behavior but only 6.4\% of the complete reference. Macro recall is 0.079, compared with 0.124 for observable behavior. Pooling still helps at cold start: after 30 days, pooling ten pseudo-sites yields a macro agreement F1 of $0.112\pm0.002$, against $0.022\pm0.005$ for local-only monitoring of one pseudo-site (G2).
+The shared evidence service is a throughput bottleneck and single point of failure for candidate flow and withdrawal propagation. It holds no local authorization state: failure can delay withdrawal but cannot itself grant or revoke local permissions. Replication and recovery remain deployment concerns. Co-located experiments do not evaluate WAN behavior or production workloads; finite models assume authenticated callers, and gateway tests disable signature validation. Deployment requires the authentication, roles, and signing integration in Sec.~\ref{subsec:trust}.
```
