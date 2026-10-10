# Audit 19 — Ricerche per il confronto con il supervisor (16 ottobre) e la riscrittura per TNSM

Data: 2026-10-10. Lavoro di sola lettura: nessun file modificato tranne questo, nessun esperimento lanciato, `results/`, `code/src`, il nodo, `main.tex` e `main_old.tex` non toccati.
Notazione: [C] = trovato nel file indicato (file:riga); [D] = mia deduzione; "non trovato" = cercato e assente, con i comandi usati.

**Convenzione per i riferimenti al paper.** `old:N` = `/root/Desktop/DIB_clean/docs/main_old.tex:N` (853 righe). `new:N` = `/root/Desktop/DIB_clean/docs/main.tex:N` (865 righe). Per le righe ≤ 389 i due file coincidono; da `new:390` in poi `new` = `old` + 5 (verificato per `old:505/507/617/619/650` → `new:510/512/622/624/655`).
Gli audit 01, 08 e 09 scrivono `docs/main.tex:N` o `paper:N` intendendo il testo di `main_old.tex` (stessi numeri di riga; vedi §1).

---

## 1. Quale versione del paper è quale

### 1.1 File .tex del paper

| File | Righe | Ultima modifica (mtime) | sha1 (12) | Hash git (blob) | Stato git | Note |
|---|---|---|---|---|---|---|
| `DIB_clean/docs/main_old.tex` | 853 | 2026-10-10 18:43:04 | `90a307ab2818` | `0f2cec57…` | non tracciato (`??`) | con markup `\del/\add` e commenti `%` |
| `DIB_clean/docs/main.tex` | 865 (senza newline finale) | 2026-10-10 16:52:28 | `36fdefd3ee33` | `0829561a…` | non tracciato (`??`) | `main_old.tex` + derivazione di f* e "Why f_s=0.30" (§1.3) |
| `DIB_reframe/docs/main.tex` | 853 | 2026-10-10 09:47:27 | `90a307ab2818` | — | fuori repo | **identico byte per byte a `main_old.tex`** (stesso sha1 completo `90a307ab28185d3a87d2b81416dfb2f09db85320`) |
| `DIB_reframe/main.tex` | 771 | 2026-07-23 19:32:00 | `3385ae56fc24` | — | fuori repo | quello che l'audit 08 chiama "old:N" (771 righe) |
| `DIB_reframe/main_reframed.tex` | 1480 | 2026-07-16 10:32:08 | `b7546b493a2e` | — | fuori repo | |
| `DIB/dib_TNSM.tex` | 1740 | 2026-07-13 15:24:20 | `6fe38f478d17` | — | fuori repo | |
| `DIB_reframe/dib-tnsm-artifact-v43/paper/main.tex` | 816 | (log 2026-10-06 11:08) | `04c5299a512b` | — | repo `V/` | "`main (43).tex` non modificato" (`…/docs/PAPER_SOURCE_v43.md`); `main_old.tex` ne differisce per 61 righe di diff (hunk a 31-36, 46, 48, 54-55, 81, 140-163, … 489-526), cioè è v43 + annotazioni |
| `DIB_reframe/reproducibility/last_review/main_v*.tex` | — | — | — | — | storico (v6.x … v44.0); non confrontati |

Comandi: `find / -name "*.tex"` (limitato a /root, /tmp), `stat -c '%y'`, `wc -l`, `sha1sum`, `git hash-object`, `git status --short docs`, `git log -- docs/main.tex docs/main_old.tex` (nessun commit: entrambi mai committati).
**Branch e worktree.** `git ls-tree -r --name-only <branch> | grep -c '\.tex$'` = 0 su tutti e 9 i branch locali; `find` nei worktree `DIB_tnsm`, `DIB_integration`, `DIB_clean_formal` = nessun `.tex`. Nessun hash di commit esiste quindi per il paper.

### 1.2 `main__6_.tex` (la copia caricata in chat)

**Non trovato sul disco.** Comandi: `find / -name "main__6_*"` (nessun risultato), `find / \( -iname "main__*" -o -iname "*main*6*.tex" \)` (solo `main_v6.1/6.2/6.3.tex`, `main_v16.0.tex`, `main_v26.0.tex`, `main_v36.0.tex` in `DIB_reframe/reproducibility/last_review/`, `main.pass6.tex` e un backup BioDevOps: nessuno è "main (6)"), `find / -iname "*(6)*"` (nessun risultato), `ls ~/Downloads` (non esiste). **Il diff con `main_old.tex` non è quindi eseguibile.** Serve il percorso, oppure copiarlo in una cartella a tua scelta.
Indizio [D], non prova: la frase "threshold-then-rank" sta a `:619` solo in `main_old.tex` (`new:624`; `v43/paper/main.tex:582`; `last_review/main_v42.0.tex:528`, `main_v43.0.tex:530`, `main_v44.0.tex:548`). Se nella tua copia è a `:619`, la numerazione coincide con `main_old.tex`. Non basta a dire che il contenuto coincide.

### 1.3 Differenze `main_old.tex` → `main.tex` (diff completo eseguito)

Cambiano solo tre blocchi, tutti in Sec. IV-C (Candidate-Selection Policy); Design Goals, Evaluation e Discussion sono **identici** (stesso testo, righe spostate di +5 dopo `:389`):
- `:389` (`new:389`): frase 0.7/0.3 riscritta ("Counts are pooled without per-site normalization…", "$C_t$ therefore enters Criterion… only through $C_t\le1$").
- `:391-395` → `new:391-396`: i tre commenti `% attacco 30%`, `% cercare studi…`, `% giochi cooperativi…` e la frase "We choose weights that reject facts…" sostituiti dal paragrafo **"Parameter derivation"** con Eq. `eq:fstar` $f^\star=(\theta-\beta)/\alpha$.
- `:405` → `new:406`: ultima frase del Criterion in forma $f_s<f^\star$.
- `:408` → `new:409-413`: aggiunti la forma in conteggi ($K<\frac57 h$), il paragrafo **"Why $f_s=0.30$"** (`new:411`) e il paragrafo probabilistico (`new:413`).
- Bibliografia: aggiunte `lamport1982byzantine`, `castro1999pbft`, `kumar2019allthings`, `zhao2022largescale` (`new:~674-682`); `mirai` con le pagine.
- Ultima riga: `\end{document}` senza newline.
Coincide con quanto descritto in `docs/audit/09_f_s_derivazione_e_letteratura.md:9-22`.

### 1.4 I riferimenti `main_old.tex:NNN` degli audit

Verificati leggendo le righe: `old:505` (service retiene solo l'ultimo target pendente; "WAN latency, packet loss, and asymmetric partitions remain outside this evaluation"), `old:507` ("All 40 outage trials converge… 0.51±0.03… 0.50±0.04… ~0.45 s… less than 0.1 s"), `old:617` ("Ordering alone nevertheless recovers…"), `old:619` ("We recommend threshold-then-rank"), `old:650` ("Local control does not eliminate withdrawal's availability costs") **corrispondono alle stesse frasi**. Anche gli audit 01/08/09 (`docs/main.tex:172,174,175,303-324,326,422`; `paper:414,631`; `:523-526`) puntano al testo di `main_old.tex` [C: `old:172` trust boundary, `old:174` policy authority, `old:326` retention window, `old:422` "Exports are unsigned", `old:414` raw breadth, `old:631` 0,562]. **Attenzione:** nel `docs/main.tex` attuale (865 righe) quegli stessi riferimenti sono sbagliati di 5 righe per N > 389 (es. `:422` è nel paragrafo "Why f_s").
Comando: `grep -n "<frase>" docs/main_old.tex docs/main.tex`.

---

## 2. Configurazione degli esperimenti riportati (trust_weighted)

**Fatti di base [C].**
- `ScoringConfig.trust_weighted` ha default `False` (`code/src/dib/evaluation/dib.py:66`); con `True` C_s è la quota di peso (`dib.py:256-259`).
- `configs/graph_free_selected.yaml:44` ha `trust_weighted: true`. `configs/LOCKED_CONFIGS.md` la chiama "**Configurazione selezionata**" e dice che è usata per Table II, ablation 20 seed, export osMUD, A1 breakdown e sensitivity (riga della tabella a `:12`).
- `configs/graph_free_unweighted_federation.yaml:13` (`trust_weighted: false`) è usata **solo** da `tnsm_federation_comparison.py` (LOCKED_CONFIGS.md), che il paper non cita.
- Gli script del cold-start a tre lab **non usano né YAML né `DIBScorer`**: riscrivono la regola a mano con 0.6/0.4/0.65 fissi e `site_conf = len(supporters)/len(eligible)` (`code/scripts/moniotr_cross_lab.py:346,368-372`), cioè breadth grezza. Audit 08 §0.3(b): non verificata riga per riga l'equivalenza con `DIBScorer`.

### 2.1 Catena paper → results → script → config

| Elemento (riga `old`) | `results/` | Script | Config / parametro | trust_weighted |
|---|---|---|---|---|
| **Table threelab** (`old:545-569`) e testo `:543,615-617` | `three_lab_matched/matched_ablation.csv` | `v28_matched_ablation.py` (usa `moniotr_cross_lab.py`) | pesi fissi nello script; `v28_matched_ablation.py:68` `scoring="raw breadth"`; `three_lab_matched/README.md:10` "Scoring uses raw breadth, not trust weights" | **false (raw)** |
| **Fig. pareto** (`old:571-613`) | `pareto_frontier/{sweep,frontier_points}.csv`, `union_ranked/…` | `pareto_frontier.py`, `union_ranked_budget.py` | importano da `moniotr_cross_lab` (`pareto_frontier.py:35`, `union_ranked_budget.py:31`); nessun `trust` nei due script (`grep`); `union_ranked/manifest.json` `"theta": "not applied (ranking only)"` | **false (raw)** |
| Review volume, 24.886/840/697/462 (`old:534-536`) | `workload/*.csv` | `moniotr_cross_lab.py` | `workload/manifest.json:10-15` (0.6/0.4/0.65) | **false (raw)** |
| Bootstrap CI, busiest days (`old:547,622`) | `three_lab_loo/{bootstrap_ci,…}.csv` | `moniotr_cross_lab.py` | idem | **false (raw)** |
| 5,46/4,31/28,31 ispezioni (`old:615`) | `review_cost/review_cost.csv` | `review_cost_curve.py` | `review_cost/manifest.json:18-21` | non esplicitato nel manifest [D: stessi insiemi della three-lab] |
| **tab:comparison** (`old:471-485`) | `restore_ablation/results.json` | `v36_restore_ablation.py` | nessuno scoring | n/a |
| Recall funnel, 55/564, 36, 65,5 %, 6,4 %, 0,079, 0,124 (`old:528`) | `recall/recall_funnel.csv` | `recall_funnel.py:191` legge `trust_weighted` dal YAML | `recall/manifest.json:15` `../configs/graph_free_selected.yaml` | **true** (`recall/manifest.json:19`) |
| Cold start 0,112 ± 0,002 vs 0,022 ± 0,005 (`old:528`) | `cold_start/cold_start_local_vs_registry_detail.csv` | `cold_start_local_vs_registry_multiseed.py:39` (da YAML) | `cold_start/manifest.json:4` `graph_free_selected.yaml` | **true** (il paper lo dichiara a `old:530`: "This experiment uses trust weighting") |
| 346 fatti per ogni quorum (`old:530`) | `quorum/site_quorum_sensitivity_rerun.csv` | `site_quorum_sensitivity.py:25` riusa `scoring_config` di `recall_funnel.py` | `quorum/manifest.json:8-9` | **true** |
| A1 catturato, 59 fatti/165 oss. (`old:629`) | `a1_baselines/compromised_baseline_table.csv`, `a1/…` | `compromised_baseline.py:60-66` "Forced vanilla regardless of scoring.trust_weighted" | `a1_baselines/README.md` (`graph_free_selected.yaml`, ma la riga DIB è forzata vanilla) | **false** per la riga vanilla |
| A1 con nome risolvibile, 0/150 → 21/150, primo a k=7, 120 g, score 0,679 (`old:629`) | `a1_resolvable/a1_resolvable_counterfactual.csv` | `a1_resolvable_counterfactual.py:200` (da YAML) | `a1_resolvable/manifest.json:41` | **true** |
| A2 mascheramento, 0,354 / 0,562 / 0,663 (`old:631`) | `masquerade/service_masquerade.csv` | `service_masquerade_probe.py:83` (da YAML) | `masquerade/manifest.json:45`; `masquerade/README.md:36` "trust-weighted" | **true** |
| Sensitivity θ, α su Mon(IoT)r, 0,071 vs 0,054 (`old:635`) | `sensitivity/moniotr_{theta,alpha}_sweep.csv` | `parameter_sensitivity_external.py:44` `ScoringConfig(alpha, beta, gamma=0, theta, graph_enabled=False)` senza `trust_weighted` | default Python | **false (raw)** |
| Identity inflation, 45/48 raw; trust e clustering respingono; RWV 48/48 (`old:637`) | `sybil/sybil_sensitivity_surface.csv` | `sybil_sensitivity_surface.py:148` costruisce le varianti vanilla/trust/independence nello stesso run | `sybil/manifest.json:8` `trust_weighted: true` (ma lo script costruisce tutte le varianti) | **entrambe** (colonne `*_vanilla`, `*_trust`) |
| Padding / Jaccard (`old:637`) | `sybil_jaccard/sybil_padding_sweep.csv` | `sybil_padding_sweep.py:152` | `sybil_jaccard/manifest.json:3` | varianti |
| **A3** drift, 69/162, mediana 7 giorni (`old:639`) | `drift/*.csv` | `nonstationarity_drift_sweep.py:70` `trust_weighted=True` | `drift/README.md:12` | **true** |

### 2.2 Risposte

- **Esiste un esperimento riportato nel paper che usa la configurazione pesata?** Sì: recall funnel e cold start UNSW (`old:528,530`), quorum (`old:530`), A1 con nome risolvibile (`old:629`), A2 con porte mascherate e il test a f_s = 0,30/0,50 (`old:631`), A3 (`old:639`), e la colonna trust dell'identity inflation (`old:637`). **Non usano la pesata**: Table threelab, Fig. pareto, workload, bootstrap, review cost, sensitivity θ/α, la riga vanilla di A1.
- **Il paper lo dice?** Solo in parte: `old:414` "The registry and independent-deployment experiments use raw breadth, to which Criterion~\ref{crit:poison-bound} applies" e `old:543` "Scored rows use raw breadth"; `old:530` ammette il trust per l'esperimento UNSW pooled. **Non dice** che `old:629` (A1 risolvibile), `old:631` (A2, 0,562, 0,663) e `old:639` (A3) sono pesati. `old:631` aggiunge "consistent with the analytical bound of 0.58", che è la forma grezza del Criterion.
- **Conferma da altri audit.** Audit 08 riga 232: "I numeri A2 e lo 0,562 vengono da run trust-weighted (`results/masquerade/manifest.json:45`)… il paper dice che il Criterion si applica alla raw breadth (paper:414)". Audit 16 §5.1 (`16_federazione_sintetica.md:~100-130`): D0' (quota pesata) non falsificata, ma con pesi gonfiati un avversario fa ammettere fatti con quota grezza fino a 0,30 < 5/12 (245 casi su 3700): il Criterion grezzo non protegge la configurazione selezionata.
- **Dove il paper definisce "trust-weighted" / "reliability weight".** "Trust weighting" è definito a `old:410-414` (Sec. IV-C, paragrafo "Sybil-aware variants", formula $C_s^{trust}$ con $w_i=\min(1,b_i/b_{ref})$). Compare ancora a `old:530` e `old:637`. **Non è presentato come default**: è una "variante" che "fall[s] outside the raw-breadth bound" (`old:414`). "Reliability weight" **non trovato** (`grep -n "reliab" docs/main_old.tex` → solo `old:156`, "reliablity score" con refuso, riferito a G2). Il default del paper è la breadth grezza (Eq. `eq:score`, `old:373-378`, `C_s=|S|/|ES|` a `old:384`); il default **del repository** (YAML selezionato) è il pesato. Questa è la discrepanza principale da portare al supervisor.

---

## 3. Design goal

### 3.1 Testo esatto (`old:150-168`, identico in `new`)

```
150  \subsection{Design Goals}
151  We designed DIB with those four design goals in mind:
152  \begin{itemize}
153      \item \textbf{G1: Candidate discovery.} Propose communications from shared observations for a certain IoT device is enabled only when a MUD file for that specific device is not available.
154      % si attiva solo se i mud file non esistono (o ibrida)
155      %vogliamo proteggere, a priori, l'archi
156      \item \textbf{G2: Conditional admission protection.} To each endpoint fact is associated a reliablity score. To be exposed to other sites, the score must be higher than a certain threshold.
157      \item \textbf{G3: Local authorization.} Importing external endpoint facts is allowed only after approval by the site's administrator.
158    %\item \textbf{G3: Review workload.} Filter and prioritize candidates for administrator review.
159    %
160    \item \textbf{G4: Revoking criteria} % Evidence and score changes must not grant or revoke permissions; disputes and operator actions follow the lifecycle rules.
161    DIB implements a precise lifecycle for sending dispute messages and for automatically revoking suspicious endpoint facts.
162    % due dispute 
163    % \item \textbf{G3: Conditional admission protection.} With \emph{raw breadth} (the unweighted fraction of eligible sites reporting a fact), admission rejects adversary-only evidence under the share bound in Sec.~\ref{subsec:trust} and parameter constraint in Criterion~\ref{crit:poison-bound}. This does not establish benignity; Sec.~\ref{sec:sensitivity-results} evaluates its limits.
164  \end{itemize}
165  
166  Considering the presented goals, our threat model considers and analyzes the two major risks faced by our proposed approach during an update instruction received from the network: (i) the possibility that a locally denial rule is restored, and (ii) the erasing of a locally created rule.
167  
168  % g1 e g3 tautologici, threat model solo su g2
```
Altri commenti a ridosso: `old:143` titolo "Design Goals and adopted Threat Model"; `old:181-182` "% report message spiegare e cambiare nome in caso / % questa è la cosa che mappa il goal 2"; `old:95` "defines the setting and design goals".

**Conteggio.** "four design goals" (`:151`): **4 attivi** (G1 `:153`, G2 `:156`, G3 `:157`, G4 `:160-161`). **2 voci commentate**: `:158` "G3: Review workload" e `:163` "G3: Conditional admission protection" (versione con raw breadth e Criterion). Commenti annessi: `:154-155`, `:160` (coda: testo di un vecchio G4 "Evidence and score changes must not grant or revoke permissions…"), `:162`, `:168`.
Osservazioni [C]: la numerazione G3 compare tre volte con tre significati; il G4 attivo ("Revoking criteria") non coincide con il G4 commentato (rescoring non distruttivo).

### 3.2 Dove i goal sono citati

Nel paper (`grep -nE "\bG[1-4]\b|design goal" docs/main_old.tex`): `:95`, `:143`, `:150-151`, `:153-163` (definizione), **`:491` "(G4)"** (test del rescoring: "Evidence updates are tested separately from lifecycle events (G4)"), **`:528` "(G2)"** (cold-start pooled vs local-only: "…against $0.022\pm0.005$ for local-only monitoring of one pseudo-site (G2)"). **G1 e G3 non sono citati in nessuna tabella, figura o frase della valutazione.** `main.tex` ha le stesse occorrenze.
Incoerenze [D]: **(correzione 2026-10-10, ricontrollato `old:491` contro `old:160-161`)** l'etichetta (G4) a `:491` (aggiornamenti di evidenza separati dagli eventi del lifecycle) è coerente con G4 se si legge il commento di `:160` ("Evidence and score changes must not grant or revoke permissions; disputes and operator actions follow the lifecycle rules"); il testo **attivo** di G4 (`:161`, lifecycle delle dispute e revoca automatica) la copre solo in parte, quindi G4 va riformulato, non l'etichetta rimossa. È invece non coerente l'etichetta (G2) a `:528` riguarda il cold start, che mappa G1 (candidate discovery) secondo `docs/work/DIB_piano_completo.md:58` ("il cold-start riguarda G1, non G2"). G2 ("conditional admission") è l'unico che mappa su un esperimento (`old:539-631`) senza essere etichettato.

Nella repo: `grep -rnE "\bG[1-4]\b|design goal"` (escluso il paper):
- `code/tests/tests/test_rescoring_non_destructive.py:1-5` ("G4 (non-destructive rescoring)… The paper's G4 is the stronger, general statement") — usa il G4 vecchio.
- `formal/base/DIB.tla:208` (e le copie in `formal/mutations/m*/DIB.tla`): "G1: only a locally Active fact can be exported" — numerazione ancora diversa (G1 = export gate).
- `docs/work/DIB_piano_completo.md:37,39,55,58,60,77,78,276,303` e `CLAUDE.md:28`.
(Le sigle G1–G3 di `docs/audit/04,12,13,17,18` sono gate operativi del piano di misure, non design goal.)

### 3.3 Elenco di design goal diverso o più recente

**Non esiste un elenco G1–Gn alternativo.** Esistono solo proposte nel piano (`docs/work/DIB_piano_completo.md`, copia di `DIB_reframe/docs/DIB_piano_completo.md`):
- `:39` "Goal e threat model: G2 = 'protezione dall'evidenza inadatta' (ammissione ex ante + dispute ex post)? Gli abusi di dispute entrano nel threat model (A4)? **G1 e G3 declassati a requisiti/invarianti?**" (decisione aperta, §2.3 "Decisioni da prendere col supervisor").
- `:37` "Caso ibrido (G1): il lifecycle si attiva solo senza MUD del produttore, oppure anche in modalità ibrida?"
- `:55` "G1: frase grammaticalmente rotta"; `:58` etichette (G2)/(G4); `:60` rimuovere i blocchi G3 commentati; `:77` "Riscrivere i goal come proprietà; threat model centrato su G2 con A1–A3 (+ A4…)"; `:78` rinominare il "report message"; `:276` "Sistema, goal e threat model (G2 = evidenza ex ante + dispute ex post)".
- `docs/audit/09_f_s_derivazione_e_letteratura.md:51`: "Sec. III: refuso 'A1 tests -----.' (riga 177), riscrittura G1–G4 e threat model" (da fare).
Comandi: `grep -rnE "goal|G[1-4]" docs/work docs/audit`, `ls docs/work`. Nessun elenco in `PRE_PUBLICATION_CHECKLIST.md` o `regenerate-results-after-service-changes.md`.

---

## 4. Qualità dei profili MUD (G1)

### 4.1 Metriche riportate

Riferimento di verità: **U** = profili UNSW normalizzati; **R** = osservazioni del ricevente (leave-one-receiver-out).

| Metrica e valore | Riga `old` | Fonte in `results/` | Script | GT |
|---|---|---|---|---|
| 55/564 ACE osservabili; 36 staged; 65,5 % (=36/55, **micro**); 6,4 % (=36/564, **micro**) | `:528` | `recall/recall_funnel.csv` (righe `observed_in_capture` 55; `staged_by_dib` 36; micro 0,0974 / 0,0638) | `recall_funnel.py` | U |
| Recall macro 0,079 (0,0786) e 0,124 (0,1245) per il comportamento osservabile | `:528` | `recall/recall_funnel.csv` (`macro_share` 0,078633; 0,124485) | idem | U |
| Cold start: F1 macro 0,112 ± 0,002 (pooled 10 pseudo-siti, 30 g) vs 0,022 ± 0,005 (local-only) | `:528` | `cold_start/cold_start_local_vs_registry_detail.csv`; `cold_start/README.md` | `cold_start_local_vs_registry_multiseed.py` | U |
| 346 fatti per m = 2…10 | `:530` | `quorum/site_quorum_sensitivity_rerun.csv` | `site_quorum_sensitivity.py` | (conteggio) |
| Table threelab: N, Cov., P/R/F1, 12 righe (US 1005/42/40/36 …; UK; YT 1387/177/146/107; es. DIB US P .750 R .065 F1 .116; YT .286/.223/.247) | `:545-569` | `three_lab_matched/matched_ablation.csv` (valori letti: coincidono) | `v28_matched_ablation.py` | R |
| IC bootstrap F1 [.033,.198]/[.044,.186]/[.116,.384]; F1 giorni più attivi 0,241/0,213/0,258 | `:547,622` | `three_lab_loo/bootstrap_ci.csv` (letto: coincide), `leave_one_out_three_lab_single_day.csv` | `moniotr_cross_lab.py` | R |
| Fig. pareto: recall per candidati (US 0,0650 a N=36; ranked 0,0682…) | `:586-607` | `pareto_frontier/{sweep,frontier_points}.csv` | `pareto_frontier.py` | R |
| Endpoint confermati 184/178/49 su 1005/767/1387; 35/39/40 vs 35/37/37; ispezioni per endpoint 5,46/4,31/28,31 vs 1,03/1,16/2,89; 6,6/10,0/3,8 attesi (union non ordinata) | `:615-617` | `union_ranked/union_ranked_budget.csv` (`union_ranked_expected` 35,0/39,0/40,0; `dib_confirmed` 35/37/37), `review_cost/review_cost.csv` | `union_ranked_budget.py`, `review_cost_curve.py` | R |
| Sensitivity: miglior F1 macro 0,071 contro 0,054 scelto (Mon(IoT)r) | `:635` | `sensitivity/moniotr_theta_sweep.csv` (θ=0,5: 0,071208; θ=0,65: 0,053799), `moniotr_alpha_sweep.csv` (α=0,85: 0,071327) | `parameter_sensitivity_external.py` | **U** (`sensitivity/README.md`: "F1 semantica contro il ground truth UNSW normalizzato") |
| Coverage per dispositivo: 83,3 %/83,3 %/100 % | `:547` (tabella) | `matched_ablation.csv` colonna `coverage` | idem | R |
| Precisione/recall dei profili A1/A2: non riportati come P/R/F1 (conteggi di ammissione) | `:629-631` | — | — | — |

**Conteggio.** Gruppi di numeri con GT UNSW: **3** (funnel/recall, cold start, sensitivity θ/α). Con osservazioni del ricevente: **4 gruppi** (Table threelab, IC bootstrap/giorni più attivi, Fig. pareto, rese/ispezioni 184/178/49, 35/39/40). Il paper (`old:528` vs `old:543`) dichiara la GT di UNSW e quella "receiver-observed" nei rispettivi paragrafi; **non dichiara** che la sensitivity di `old:635` (Mon(IoT)r) è misurata contro i profili UNSW [C: `results/sensitivity/README.md`, script `parameter_sensitivity_external.py:22` e import di `load_profile_dir`, `canonical_device_name`].

### 4.2 Il recall macro 0,079

Sì, il paper lo commenta, in `old:528`: "DIB stages 36 of the observable ACEs, retaining 65.5% of observable behavior but only 6.4% of the complete reference. Macro recall is 0.079, compared with 0.124 for observable behavior." Spiegazione scritta: "only 55 of the 564 reference ACEs across 28 profiles remain observable after address filtering; 61 to-device entries cannot appear in device-initiated input." Nota del autore non nel PDF: `old:523-526` ("65.5% = 36/55 è una ritenzione MICRO… `observable_retention` in claims.json riporta 63.2% MACRO… Esplicitare 'micro' nel testo o aggiungere il 63.2% macro").
Precisazioni [C]: **6,4 % è micro (36/564 = 0,0638), non macro**; il macro corrispondente è 7,86 % (0,0786 ≈ "0.079"). Retention macro = 0,0786/0,1245 = 63,2 % (`recall/README.md`, "Retained share of the capture-observable ceiling: 63.1% macro"; `claims.json` claim 9: 63,2 %; `verify_artifact.py:173` controlla 63,17 %). "0,079 = 6,4 %" mescola quindi le due medie; il testo del paper non dice "macro" per il 6,4 %.

---

## 5. Il 30 %

### 5.1 Dove compare f_s = 0,30

Paper (`old`): `:172` (assunzione "malicious contributors control at most a fraction $f_s$"), `:177` (A2 "bounded by breadth share $f_s$"), **`:356` tabella dei simboli ($f_s$ = 0.30)**, `:399-405` (Criterion), **`:408`** ("At θ=0.65 and f_s=0.30 this requires α>0.5. Choosing α=0.6 gives an upper bound of 0.58…"), `:627` (malicious-site fractions {.05,.1,.2,.3,.4,.5}), `:631` ("At $f_s=0.30$, the largest score passing quorum is 0.562… At $f_s=0.50$… 0.663"). "0.3" come 0.3 del volume in $C_t$ (`:386`) è un'altra cosa.
**Giustificazione scritta in `main_old.tex`:** nessuna. Solo i commenti `old:393-395`: "% attacco 30% / % cercare studi con % di device compromessa (mirai) / % giochi cooperativi, competitivi, azienda quando deve prendere una decisione % azionisti o % di rischio".
`main.tex`: giustificazione in `new:411` ("budget sotto il margine, non prevalenza misurata": sotto $f^\star=5/12$ con margine 0,117; sotto 1/3 bizantino citando Lamport e Castro-Liskov "as an order-of-magnitude reference"; Mirai ~600.000 infezioni senza quota per tipo; Kumar 1,3 %; Zhao 28,25 % vulnerabili), `new:413` (probabilistica, q=1−(1−p)^n).
Repo: `docs/work/DIB_piano_completo.md:73` ("Giustificare f_s = 0,30: distinguere A2 (soglia 1/3 dei sistemi bizantini) da A1 (prevalenza di dispositivi infetti per tipo, studi post-Mirai)"), `:133` (tabella parametri: f_s 0,30; intervallo 0–0,5); `claims.json:147`; `scripts/verify_artifact.py:164-167`; `results/masquerade/README.md:52-70`; `results/a1_baselines/README.md` ("A1, k=3, f=0.30"); `configs/strict_alternative.yaml:8,26` (frazioni di siti malevoli 0,01…0,30; "theta-bound = 0.16 at f=0.30"); `code/tests/tests/test_poison_bound.py:12-31`; `analysis_fs/{fs_binomial.py,finite_n.py,reformulation_fs.md,test_*.py}`; audit `08_assunzione_fs.md` (analisi completa), `09_f_s_derivazione_e_letteratura.md` (derivazione e fonti), `11_hd_distribution.md:84,113,125` (copertura per tipo a f_s=0,30), `12_test_realistici.md:7,27,37` (piano: f_s ∈ {0…0,5}), `14_priorita…`, `16_federazione_sintetica.md`.
Comando: `grep -rlE "f_s|f=0[.,]30|0[.,]30\b"` su `DIB_clean` e `DIB_tnsm`.

### 5.2 Bibliografia

**Nessun file `.bib` per il paper DIB** (`find /root -name "*.bib"`: solo altri progetti: csur_project, offloading_s4t, survey_end). La bibliografia è `thebibliography` inline.
Voci pertinenti (`old:666-821`):

| Chiave | Titolo | In `main_old.tex` | In `main.tex` |
|---|---|---|---|
| `mirai` (`old:668`) | Antonakakis et al., "Understanding the Mirai Botnet", USENIX Sec. 2017 | sì (citata a `:72`, `:74`) | sì, con pagine 1093-1110 |
| `lamport1982byzantine` | Lamport, Shostak, Pease, "The Byzantine Generals Problem", TOPLAS 1982 | no | sì (`new:411`) |
| `castro1999pbft` | Castro, Liskov, "Practical Byzantine Fault Tolerance", OSDI 1999 | no | sì (`new:411`) |
| `kumar2019allthings` | Kumar et al., "All Things Considered: … IoT Devices on Home Networks", USENIX Sec. 2019 | no | sì |
| `zhao2022largescale` | Zhao et al., "A Large-Scale Empirical Study on the Vulnerability of Deployed IoT Devices", IEEE TDSC 2022 | no | sì |
| `eigentrust`, `trustsurvey` | EigenTrust; Jøsang et al. survey (reputazione) | sì (`:107`) | sì |
| `allowlistvariability`, `hernandezramos2021mudreview` | He et al. EuroS&P 2024; Hernández-Ramos et al. IEEE Access 2021 | sì | sì |

Non ci sono voci su "soglie per voti" oltre a Lamport/Castro (solo in `main.tex`).
**Frazione di dispositivi compromessi nei file locali:** **non verificabile offline**. Nessun PDF di queste fonti è sul disco (`find / \( -iname "*mirai*" -o -iname "*antonakakis*" -o -iname "*kumar*" -o -iname "*zhao*" -o -iname "*lamport*" -o -iname "*castro*" \) -name "*.pdf"`: solo PDF USENIX Sec. 26 non pertinenti dello SoK). L'audit 09 (`docs/audit/09_f_s_derivazione_e_letteratura.md:31-37`) dichiara di averle verificate sui PDF il 10 ott 2026, ma quei PDF non sono né in repo né sul disco: **riporto quanto scrive l'audit, senza averlo ricontrollato**: Antonakakis — picco di 600.000 infezioni, nessuna quota per tipo; Kumar — 1,3 % dei device nelle case che scansionano (0,37 % delle case), backdoor EternalBlue; Zhao — 385.060 di 1.362.906 (28,25 %) con almeno una vulnerabilità, "vulnerabile ≠ compromesso"; Lamport — soglia di due terzi; Castro-Liskov — n ≥ 3f+1.

### 5.3 Citazioni su Criterion 1 e bound 5/12

**Nessuna in `main_old.tex`.** Il Criterion (`:397-406`) e l'unica occorrenza di 5/12 (`:408`) non hanno `\cite`. Il testo cita altre fonti solo per le varianti Sybil (nessuna). In `main.tex`: 5/12 a `new:391-396,409,411` e Lamport/Castro a `new:411`, citati per il confronto con il 1/3 bizantino, non per il Criterion. Comando: `grep -nE "5/12|Criterion|crit:poison" docs/main_old.tex docs/main.tex`.

---

## 6. Verificatore e numeri collegati a fault_injection

### 6.1 Controlli di `scripts/verify_artifact.py`

(Identico in `DIB_clean` e `DIB_tnsm`: `diff` vuoto.) `check()` a `:35-45`, tolleranza di default 0.

| Righe | Controllo | Atteso | Tolleranza |
|---|---|---|---|
| `:215` | carica `results/fault_injection/results.csv` | — | — |
| `:216` | n. prove totali | 40 | 0 |
| `:217` | tutte consistenti (`trials == consistent_trials`) | True | — |
| `:218-220` | convergenza media evento singolo (media pesata sulle 30 prove) | **0,51 s** (arrotondata a 2 decimali) | **0,005** |
| `:221-222` | convergenza scenario composto `dispute_and_restore` | **0,50 s** | **0,005** |
| `:247-263` | `restore_ablation`: hash di `service.py` (`:250`) e dello script (`:253`), 18 combinazioni (`:255-256`), per policy 12/6, 0/0, 0/6 (`:257-261`), tracce (`:262-264`) | come scritto | 0 |
| `:265-274` | `lifecycle_v35/api_campaign.json` (sospensione q=1,2; 100 veti) | | 0 |
| `:275-280` | `dispute_flood` 1000; 11,3 s; 21,6 s; 11 richieste/fatto | | 0 (`round(…,1)`) |
| `:320-345` | `offline_veto`: hash script (`:321`) e service (`:323`), 10 prove, veti preservati, approvazioni cancellate, fatti non correlati, recuperi, per ogni prova origine "local", `monitor-only`, export `[0,0,0]`, `[1,1,1]`, replay stantio ignorato, commit diretto bloccato | | 0 |
| `:225-232` | `check_claims_index`: ogni `result` dei claim 27 (fault_injection), 30 (restore_ablation), 35 (offline_veto) esiste | | — |
| `:164-167` | (collegato) 0,562 a f_s=0,30 e stagiona a f_s=0,5 | 0,562 | 0,0005 |

**Numeri 0,45 s e 0,1 s: nessun controllo** (`grep -nE "0\.45|0\.1\b" scripts/verify_artifact.py` → nessuna riga pertinente). "0,1 s" e "~0,45 s" del paper (`old:507`) non sono verificati dallo script. Anche "20 prove di race con fan-out nuovi" non ha controllo né file in `results/` (`ls results/*race*` → assente).
Stato (audit 15 §3-§4): il verificatore dà 260 passed/2 failed **prima** della copia di `restore_ablation` e `offline_veto` (hash di `service.py` a `:250,323`), poi risolto da `b29bade`. `fault_injection` non è stata copiata in `results/` perché `:220` fallirebbe con 0,48 s.

### 6.2 Numeri del paper che dipendono da questi risultati

| Riga `old` (`new`) | Numero / affermazione | File di `results/` |
|---|---|---|
| `:53` (abstract, sia nel blocco `\del` sia nell'`\add`: "reconciles disconnected sites in under 100 ms in the evaluated deployment" / "reconciliation taking under 100 ms") | < 100 ms | `fault_injection/trials.csv` colonna `reconcile_call_s` (max 0,0755 s nei dati vecchi) |
| `:489`, `:471-485` tab:comparison (12/18, 6/6; 0/18, 0/6; 0/18, 6/6) | restore ablation | `restore_ablation/results.json` |
| `:493` (non richiesto, per completezza: 10 casi gateway, 7 cicli) | | `openwrt/campaign-10runs/` |
| `:505` (`new:510`): "WAN latency, packet loss, and asymmetric partitions remain outside this evaluation" | qualitativo | — |
| **`:507` (`new:512`)**: 40 prove; **0,51 ± 0,03 s** su 30; **0,50 ± 0,04 s** su 10; "Another 20 trials"; "~0,45 s" riavvio; "less than 0,1 s" | | `fault_injection/results.csv` (`total_convergence_s_mean` 0,5128/0,5151/0,5078 e 0,4962; `health_check_s_mean` 0,4487/0,454/0,4475/0,4323; `reconcile_s_mean` 0,064/0,061/0,0604/0,0639; max `reconcile_call_s` 0,0755); le 20 prove race non hanno file |
| `:509` (`new:514`): dieci prove, veto preservato, 3 fatti | | `offline_veto/results.json` |
| `:332` (I3: "including those recorded at sites that missed the entire dispute/restore episode") | | `offline_veto/results.json` |
| `:514` (11,3 s, 1.000, 85 %, 432,3→366,0, p99 30,6→39,0, 11 richieste, 21,6 s) e `:516` | sospensione | `dispute_flood/dispute_flood_summary.json`, `lifecycle_v35/api_campaign.json` |
| `:650` ("no established withdrawal deadline") e `:662` (conclusione "Outage experiments show…"; "mechanisms to bound gateway withdrawal time") | qualitativo | — |
| `claims.json:217-224` (claim 27) e `:281-290` (claim 35) | stesse cifre | idem |

Dati rigenerati (fuori da `results/`, `experiments_tnsm/g0b_regen/`, audit 15 §2): evento singolo **0,480 ± 0,017 s**, episodio intero **0,509 ± 0,034 s**, riavvio 0,416 s, riconciliazione max **0,105 s** (media 0,071 s: "< 0,1 s" non vale più per il massimo), race 20/20. Decisioni dell'utente in audit 15 §4.

### 6.3 Manifest/README di `results/fault_injection/`

**Conferma: nessuno.** `ls -la results/fault_injection` → solo `results.csv` (404 B) e `trials.csv` (2.795 B); in `results/restore_ablation` c'è un `README.md`, in `offline_veto` no. `git log --format='%h %ad %an %s' --date=iso -- results/fault_injection` → **un solo commit**: `bd3080b` 2026-10-10 10:07:20 +0200, "Import dib-tnsm-artifact-v43 (implementation files only)". Date di produzione: solo i mtime dei file, **2026-09-05 21:28:39** (`stat`; conservati dalla copia); `restore_ablation/results.json` 2026-09-06 00:16:57, `offline_veto/results.json` 2026-09-06 13:53:16. Gli unici metadati sono il generatore in `claims.json:221` e il docstring di `code/scripts/fault_injection_experiment.py:1-40`; i CSV non contengono host, versione Python né hash di `service.py` (colonne in `trials.csv`: scenario, trial, tempi, stato). I JSON di `restore_ablation` e `offline_veto` hanno `service_sha256`/`script_sha256`, `offline_veto` anche `python` (`python3 -c "…keys()"`: `scope, python, service_sha256, script_sha256, trials, summary`).

---

## 7. Formato e vincoli di TNSM

- **Classe e opzioni:** `\documentclass[journal]{IEEEtran}` (`old:1`, uguale in `new:1`, `DIB_reframe/main.tex:1`, `main_reframed.tex:1`, `DIB/dib_TNSM.tex:1`). Nessuna opzione `onecolumn`/`twocolumn`/`12pt` ([C]; la classe `IEEEtran` in modalità `journal` è a due colonne per sua definizione [D, non verificato nel .cls]). `IEEEtran.cls` presente in `/usr/share/texlive/texmf-dist/tex/latex/ieeetran/` (`kpsewhich`), `pdflatex`/`latexmk` installati: l'audit 09 diceva che mancava la classe; ora c'è (non ho compilato, come richiesto).
- **Pacchetti** (`old:3-33`): `cite`, `amsmath,amssymb,amsfonts,amsthm`, `graphicx` (`\graphicspath{{figures/}}`), `textcomp,xcolor,booktabs,array,url,enumitem,multirow`, `tikz` (+librerie), `pgfplots` (compat 1.18, `groupplots`), `ulem[normalem]`; **nessun pacchetto di template aggiuntivo** (`IEEEtran` standard, `\author{Anonymous Authors}` a `:41`; biografie commentate a `:824-851`). Regolazioni di float e spaziature a `:16-31` (per comprimere). `\newcommand{\del}`/`\add` a `:35-36` (markup di revisione).
- **Pagine del PDF:** **nessun PDF compilato di `main_old.tex` o `main.tex`** (`ls docs/*.pdf` → nessun file; `find / -name "*.pdf" -path "*DIB*"`). PDF esistenti di altre versioni: `DIB_reframe/dib-tnsm-artifact-v43/paper/main.pdf` **10 pagine** (log: "Output written on main.pdf (10 pages, 273088 bytes)", 2026-10-06 11:08; sorgente = `main (43).tex`, 816 righe, diverso da `main_old.tex` per 61 righe); `DIB_reframe/main.pdf` 10 pagine (2026-07-14, ma `main.tex` è del 07-23: può non corrispondere); `DIB_reframe/main_reframed.pdf` 11 pagine (2026-07-16); `DIB/dib_TNSM.pdf` 17 pagine (2026-07-13).
- **Note su limiti di pagine/formato/istruzioni agli autori:** **limite non trovato**. Comando: `grep -rniE "page limit|pagine|TNSM|TNSE|IEEEtran|8 pages|twocolumn|author instruction" docs/*.md docs/audit/*.md docs/work/*.md CLAUDE.md README.md`. Trovato solo: `docs/work/DIB_piano_completo.md:43` ("7. **Limite di pagine TNSM** e scadenza" tra le decisioni da prendere col supervisor), `:270` ("Controllare il limite di pagine; se manca spazio, comprimere la selezione dei candidati"), `:314` ("Spazio TNSM insufficiente"), `:329` ("Limite di pagine e scadenza TNSM?") e `:265-268` ("Taglio gestionale… WAN emulata attesa… almeno il modello di 5.5"). Nessuna istruzione agli autori né numero.
- **Sezioni, righe e parole stimate** (`old`; parole: script che toglie commenti `%`, `tikz/tabular/table/figure`, matematica e comandi; stima grezza ±10 %; la bibliografia sono ~1.076 parole di voci):

| Righe | Sezione | Righe | Parole ~ |
|---|---|---|---|
| 47-69 | Abstract (con `\del` + `\add`) | 23 | 325 |
| 70-101 | I Introduction | 32 | 556 |
| 102-142 | II Related Work (con Table I) | 41 | 334 |
| 143-187 | III Design Goals and Threat Model (3.1: 150-169; 3.2: 170-187) | 45 | 51+168+391 = 610 |
| 188-336 | IV Proposed Approach (fig. architettura 192-224; IV-A 227-255; IV-B 256-336) | 149 | 57+412+372 = 841 |
| 337-417 | IV-C Candidate-Selection Policy | 81 | 569 |
| 418-436 | V Implementation and Evaluation Method | 19 | 435 |
| 437-441 | VI Evaluation (intro) | 5 | 60 |
| 442-494 | VI-A Authorization and Recovery (tab:tla, tab:comparison) | 53 | 493 |
| 495-511 | VI-B Management-Path Feasibility and Reconciliation | 17 | 616 |
| 512-517 | VI-C Suspension Policy and Availability | 6 | 172 |
| 518-531 | VI-D Candidate Selection on Captured Traffic | 14 | 160 |
| 532-537 | VI-D1 Candidate Review Volume | 6 | 142 |
| 538-624 | VI-D2 Proposals for a New Receiving Site (tab:threelab, fig:pareto) | 87 | 490 |
| 625-632 | VI-E Adversarial Observations and Fabricated Evidence | 8 | 291 |
| 633-642 | VI-E1 Parameter Sensitivity, Identity Inflation, and Drift | 10 | 250 |
| 643-659 | VII Discussion | 17 | 404 |
| 660-665 | VIII Conclusion | 6 | 81 |
| 666-821 | Bibliografia (41 voci) | ~155 | ~1.076 |

Corpo del testo (abstract→conclusione) ≈ 6.000 parole, più 8 tabelle/figure (Table I posizionamento, record-example, transizioni (largo `table*`), simboli, tla, comparison, threelab; fig. architettura (`figure*`), lifecycle, pareto). Le pagine di dove stanno non sono determinabili senza compilare; con il v43 (stessa struttura) il PDF è di 10 pagine.

---

## 8. Cosa il paper dice su ritiro, WAN e partizioni

Frasi esatte (`old:N`; `new` = +5 oltre `:389`):
- `:49` (abstract): "In the event of compromise, their lifecycle may require coordinated withdrawal while preserving local control over permissions."
- `:53` (nel blocco `\add`): "…reconciles disconnected sites in under 100~ms in the evaluated deployment…" (anche nel blocco `\del` ma barrato).
- `:76` (intro): "If a contributor later disputes that service, the participating networks must withdraw the associated permissions… It must preserve this distinction when reconciling a network that was disconnected throughout the episode."
- `:184` (Consortium authority): "Any participating site can raise a dispute. The first dispute… suspends export, and a report from a second distinct site confirms the revocation… Sec. VI-C evaluates the availability trade-off of one versus two reporters."
- `:326`: retention window $W$ (non è un "withdrawal deadline").
- `:332` (I3): "A dispute invalidates grants and export eligibility at reachable sites during fan-out and at other sites upon reconciliation… **No timing bound is imposed on reconciliation.**"
- `:335`: "Gateway application follows export, so an unreachable gateway can retain an older policy until reconnection."
- `:446`: "Both checks are exhaustive only within their finite configurations; they do not cover gateway timing, authentication, or distributed linearizability."
- `:497`: "On a 16-core x86_64 Linux host running Python 3.10.13…"; `:501`: "Dispute-open, confirming-dispute, and restore events fan out synchronously, with **up to three attempts of 1~s each**… All services run in separate processes on the same host."
- **`:505`: "Container stops simulate disconnection; WAN latency, packet loss, and asymmetric partitions remain outside this evaluation."**
- `:507`, `:509`: vedi §6.2.
- **`:650`: "Unreachable gateways can retain stale rules until reconnection, with no established withdrawal deadline. Operators need visibility into pending updates and installed policies; rule leases could bound stale permissions at an additional availability cost."**
- **`:652`: "Co-located experiments do not evaluate WAN behavior or production workloads; finite models assume authenticated callers, and gateway tests disable signature validation."**
- `:662` (conclusione): "Future work will evaluate operator review, mechanisms to bound gateway withdrawal time, and recovery of the shared evidence service."
- **"T":** non trovato come simbolo di un termine di ritiro (`grep -nE '\$T\$|\bT\b' docs/main_old.tex` → nessun uso pertinente). "Timeout": solo `:501` ("1 s each"). "Withdrawal deadline": solo `:650`.
- **Sezione Limitations:** **non esiste**; le limitazioni stanno nella Discussion (`:643-656`: valutazione con operatori `:646`; costi di disponibilità e ritiro `:650`; evidence service come collo di bottiglia, WAN, autenticazione `:652`; pseudo-siti e sei tipi `:654`; RFC 9761 `:656`) e in Evaluation (`:440`, `:505`, `:528-530`, `:541`, `:622`, `:627`).

**Criterion 1 e 5/12: tutte le occorrenze (`old`).**

| Riga | Contenuto | Enunciato per raw breadth? |
|---|---|---|
| `:6` | `\newtheorem{criterion}` | — |
| `:163` | **commentato**, G3 con "With raw breadth (the unweighted fraction…) admission rejects adversary-only evidence under… Criterion" | sì, esplicito (ma è nel commento) |
| `:172` | assunzione $f_s$ ("Admission further assumes…") | no (non nomina raw/trust) |
| `:177` | A2 "bounded by breadth share $f_s$" | no |
| `:397-406` | **Criterion** `crit:poison-bound`: "$C_s\le f_s$" | **non lo dice**: "breadth share" senza qualificare (la forma $C_s=|S|/|ES|$ è la grezza, `:384`) |
| `:408` | "…rejects adversary-only evidence for raw-breadth shares below **5/12**" (**unica occorrenza di 5/12**) | **sì**, "raw-breadth shares" |
| `:414` | "…use raw breadth, to which Criterion~\ref{crit:poison-bound} applies… These variants… fall outside the raw-breadth bound." | **sì** |
| `:619` | "admission excludes adversary-only evidence under Criterion" | no |
| `:627` | "lets us control the malicious share $f_s$ in Criterion" | no |
| `:631` | "consistent with the analytical bound of 0.58" (forma grezza) — ma i dati sono trust-weighted (§2) | implicito; **in contraddizione con i dati** |
| `:648` | "bounded-share assumption required by **P5**" | **"P5" non è definito nel paper** (`grep -n "P5"` → solo `:648`): riferimento orfano |

Quindi il paper dice "raw breadth" in `:163`(commento), `:408`, `:414`, `:543`, ma il Criterion stesso (`:397-406`) e le sue citazioni a `:619`, `:627`, `:648` non lo qualificano.

---

## 9. Coerenza fra affermazioni del paper e risultati nuovi (solo classificazione)

Legenda: **conferma** / **limita** / **contraddice** / **non testata**. Dati di §9 da audit 14-16 e `experiments_tnsm/synthetic_federation/` (fuori da `results/`).

### 9.1 "Threshold-then-rank" come raccomandazione (`old:619`; `new:624`)

- **H6-1b** (audit 16 §6, `16_federazione_sintetica.md:146-182`): **falsificata** (Holm rifiuta H0 in 802 test su 892; non rifiuta in 90/90 test di *ranked-sites* a budget 1×, dove il ranking per supporto presenta **meno** fatti A2 di DIB, differenza media −0,48). **Limita** l'affermazione "l'ammissione protegge meglio del ranking a budget uguale".
- **H6-1c** (esplorativa, seed nuovi, `:217-231`): C1 ranked-volume 510/510 e C2 ranked-sites a 2×/5× 289/289 con più A2 di DIB: **confermano** il vantaggio dell'ammissione contro il flood e a budget maggiori; **C3** (budget uguale, quota avversaria ≥ 5/12): ranked-sites altrettanto o più protettivo, **non falsificata**; più protettivo in 85/90 punti.
- Il paper dice "threshold-then-rank" **con** la condizione "when that condition holds" (`:619`). Nessuna delle prove testa "threshold-then-rank" come strategia composta [D]: i confronti sono DIB (coda ammessa) contro baseline ordinate. Riferimento `ranked-support-2` (audit 16 `:179`): "identico a DIB a 1× (0,000 in tutti i punti)… il ranking per score con quorum 2 a budget B coincide con la coda" [D: coincide con la parte "rank sulla coda ammessa" della raccomandazione, quindi non la contraddice]. `ranked-score` ≈ DIB a 1× (+0,17), +5,8/+19,9/+31,6 a 2×/5×/10× (`:178`).
- Sui dati reali (assenza di avversari): `results/union_ranked/union_ranked_budget.csv` conferma `old:617` (35/39/40 vs 35/37/37; `dib_minus_ranked_expected` 0,0/−2,0/−3,0): il ranking dell'intera unione **batte** o pareggia DIB; **limita** il vantaggio dell'ammissione a "esclusione di evidenza solo-avversaria".
- Cautele dell'utente (audit 16 `:243-250`): il budget B è fissato da DIB; sopra 5/12 Criterion 1 non si applica; i casi negativi sono tutti fuori dal dominio di garanzia (controllo esatto per tipo in H6-1c: 0 ammissioni sotto soglia su 34.000 repliche).

### 9.2 Vantaggio dell'ammissione sul ranking per score (Fig. pareto, linee tratteggiate)

- Sui dati reali la figura mostra già il ranking (tratteggiato) sopra DIB a pari candidati: US 0,0682 contro 0,0650 a N=36 (`old:588`, `:594`); `results/pareto_frontier/sweep.csv`. **Conferma** che l'ammissione non migliora la resa; il paper lo dice (`:617`).
- Sintetico (audit 16 §6): il vantaggio contro **ranked-score** compare solo a budget ≥ 2× la coda (+5,8, +19,9, +31,6 A2) e a 1× è ≈ 0 (+0,17); contro volume +8,8 a 1×. **Limita**: il vantaggio dipende dal budget scelto dall'operatore, non dall'ammissione in sé.
- Ipotesi di partenza del pilota (`:82-95`): con baseline ordinate per lo stesso score il confronto non isola ammissione vs ranking (il gate di classe fa le differenze).

### 9.3 L'assunzione f_s = 0,30 e il test oltre il bound (f_s = 0,5)

- **Conferma (D0 deterministico):** nessuna ammissione sotto soglia: H6-1a non falsificata, D0 0 violazioni; con collusione totale e ρ=100, DIB ammette **esattamente** quando n_avv ≥ ⌈5N/12⌉ (audit 16 `:131-137`). Forma in conteggi sul `DIBScorer` (audit 11 §1): `K > 5h/7` confermata per lo score da solo; il quorum m = 2 respinge K = 1 (H falsificata, `xfail strict`).
- **Limita:** copertura per tipo: K = 2 colluder coperto solo su 4–7 tipi su ~117 al margine e su nessuno a f_s = 0,30; K = 3 mai coperto (`11_hd_distribution.md:113`); mediana di h_d = 1; al più 4–5 siti indipendenti (`12_test_realistici.md:7`). Con correlazione ρ_corr = 0,3 il bound binomiale sottostima la frequenza di superamento di 1-2 ordini (H6-2, `16_federazione_sintetica.md:138-144`, es. 0,304 contro 0,0072 a N=100, q=0,3).
- **Contraddice (in parte):** `old:631` "0.562 è il massimo a f_s=0,30": il worst-case su dati reali dà **0,5788** (audit 08 `:208`, a 0,0012 dal bound 0,58); 0,562 è un massimo trust-weighted di una strategia (120 g, 1 riga/giorno). Inoltre la configurazione **pesata** non è coperta dal Criterion grezzo: con peso gonfiato 245 casi su 3700 ammessi a quota grezza ≥ 0,30 (audit 16 `:119`); D0' (quota pesata) non falsificata.
- **Test a f_s = 0,5 (`old:631`, 0,663 a 30 giorni):** `masquerade/README.md:53` (0,663 admitted); coerente con "fuori dal bound"; ma anche questo è trust-weighted. Per f_s = 0,5 un'ammissione è attesa (K/N ≥ 5/12), quindi **conferma** che oltre il bound la guardia non protegge.
- Giustificazione di 0,30 (budget sotto 5/12 e 1/3 bizantino) **non testata** da dati: nessuna fonte locale dà una prevalenza (audit 09).

### 9.4 "Failure of admission filtering creates a false proposal, not permission to communicate" (`old:631`) rispetto a G3 e approvazione locale

- **Conferma strutturale:** G3 (`old:157`) e I1 (`old:330`): solo `operator-commit` porta a Active; `formal/logs/evidence_only.log:34` "2076196 distinct states found" senza stati Active (claim 3 di `claims.json`); `results/openwrt/campaign-10runs/` (claim 7): MonitorOnly non produce regola; `openwrt` 10/10. La tabella delle transizioni (`old:312-313`): Absent → MonitorOnly "no" export. H6-1a/c: un A2 ammesso entra solo in revisione.
- **Limita:** il test copre il lifecycle, non la **qualità della decisione dell'operatore**: "operator time and decision quality remain to be evaluated" (`old:440`), "The review process still requires evaluation with operators" (`old:646`). Una proposta falsa ammessa è un costo di revisione e un rischio se approvata; la frase del paper non quantifica quanti A2 arrivano in coda (H6-1b: media 6,3 fatti A2 nella coda DIB).
- Audit 16 §5.4 (`:190-196`): la breadth dei pesi è calcolata dal registro su **evidenza auto-dichiarata**; "adv-high" è realistico nel prototipo; nel prototipo distribuito `contribute` è un no-op (audit 04 §1).
- **Non verificate qui:** autenticazione e ruoli (`old:172,184`; audit 13 mTLS in attesa di approvazione).

---

**Nota per chi rilegge gli audit.** Gli audit 01, 08, 09 scrivono `docs/main.tex:N` o `paper:N` ma i numeri di riga sono quelli di `main_old.tex`; in `docs/main.tex` (865 righe) le righe > 389 slittano di +5.

---

## Tabella finale: domanda aperta / risolta / da chiedere a te

| # | Domanda | Stato | Note |
|---|---|---|---|
| 1a | Elenco .tex, date, hash, righe | **Risolta** | §1.1 |
| 1b | `main__6_.tex` coincide con `main_old.tex`? | **Risolta (su tua indicazione)** | file non sul disco; l'utente indica sha256 `bf61868d…977c51` della copia caricata; `sha256sum docs/main_old.tex` = identico (verificato). `main.tex` = `3fdd7489…` |
| 1c | I riferimenti `old:505/507/617/619/650` | **Risolta** | stessi testi; in `main.tex` slittano di +5 |
| 1d | Quale file è la base del lavoro: `main_old.tex` o `main.tex` (865 righe)? | **Da chiedere a te** | gli audit puntano a `main_old` con il nome `main.tex` |
| 2a | Config per ogni tabella/figura | **Risolta** | §2.1 |
| 2b | Un esperimento pesato esiste? | **Risolta** | sì: UNSW funnel/cold start/quorum, A1 risolvibile, A2 (0,562/0,663), A3 |
| 2c | Il paper deve dichiarare quali risultati sono pesati; decisione sulla config di riferimento | **Da chiedere a te** | audit 08 riga 232 aperta; D0' va esplicitato (decisione già presa, audit 16 §5) |
| 3a | Testo e goal attivi/commentati | **Risolta** | 4 attivi, 2 voci commentate |
| 3b | Goal più recenti in `docs/` | **Risolta (assenti)** | solo proposte nel piano (`:39,77`) |
| 3c | Quale numerazione G1–G4 si adotta (G4 attivo vs G4 dei test e `(G4)` a `:491`, `(G2)` a `:528`) | **Da chiedere a te** | piano §2.3 punto 3 |
| 4a | Metriche con valore, riga, CSV, GT | **Risolta** | §4.1 |
| 4b | Spiegazione del recall macro 0,079 | **Risolta** | `old:528`; 6,4 % è micro, non macro |
| 4c | Sensitivity di `:635` misurata contro i profili UNSW, non dichiarata | **Risolta (da decidere se dirlo)** | `sensitivity/README.md` |
| 5a | Occorrenze e giustificazione di f_s = 0,30 | **Risolta** | `main_old`: nessuna; `main.tex:411,413` e audit 09 |
| 5b | Voci .bib sul Mirai/prevalenza/soglie | **Risolta** (nessun .bib; voci elencate) | |
| 5c | Frazione compromessa dai PDF locali | **Non trovato / non verificabile offline** | PDF assenti; uso i numeri di audit 09 (non ricontrollati) |
| 5d | Citazioni su Criterion 1 e 5/12 | **Risolta (nessuna)** | |
| 6a | Controlli del verificatore | **Risolta** | §6.1; 0,45 s e 0,1 s non controllati |
| 6b | Numeri dipendenti da fault_injection | **Risolta** | §6.2 |
| 6c | Manifest di `results/fault_injection` | **Risolta (assente)** | un solo commit `bd3080b`, mtime 2026-09-05 |
| 6d | Copia di `fault_injection` nuova in `results/` (richiede cambiare `verify_artifact.py:220,222` e il paper) | **Da chiedere a te** | audit 15 §4 |
| 7a | Classe, opzioni, pacchetti | **Risolta** | `[journal]{IEEEtran}`, nessun pacchetto di template |
| 7b | Pagine del PDF | **Non trovato** (per `main_old`) | v43: 10 pagine |
| 7c | Limite di pagine TNSM | **Non trovato** | da chiedere al supervisor (piano `:43,329`) |
| 8a | Frasi su WAN, partizioni, ritiro, T | **Risolta** | "T" e Limitations assenti |
| 8b | Occorrenze di Criterion 1 e 5/12 | **Risolta** | "P5" orfano a `:648`; il Criterion non qualifica "raw" |
| 9 | Coerenza con i risultati nuovi | **Risolta (classificazione)** | §9; H6-1b falsificata, H6-1c C3 non falsificata, 0,5788 ≠ 0,562 |
| 9b | "Threshold-then-rank" come strategia composta non è stata testata direttamente | **Da chiedere a te** | solo `ranked-support-2` ≈ DIB a 1× |
