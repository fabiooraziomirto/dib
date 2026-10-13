# Audit 125 — Consolidamento delle evidenze esistenti per il paper (nessun rerun)

Data 2026-10-13. I numeri sono ricalcolati dai CSV/JSON salvati. Nessuna evidenza è stata rigenerata: sono valide e tracciabili. Le voci (V) le ho ricontate di persona.

## 1. Ranked union a budget uguale (`results/union_ranked/`)
Budget = dimensione della coda di DIB per ricevitore. Ranking per score di DIB (α=0,6, β=0,4), senza soglia, quorum e filtro di classe. "Confirmed" = endpoint osservato dal ricevitore (accordo con il traffico, non benignità).

| Rx | budget | DIB | ranked union | union in ordine arbitrario |
|---|---|---|---|---|
| US | 36 | 35 | 35 | 6,6 |
| UK | 43 | 37 | 39 | 10,0 |
| YT | 107 | 37 | 40 | 3,8 |

**DIB non supera la ranked union in nessun ricevitore**: pareggio a US, −2 a UK, −3 a YT (`union_ranked_budget.csv`; controllato in `scripts/verify_artifact.py:120-133`). Il quorum non ordinato è già vicino a DIB a US e UK (35,1 e 36,7 contro 35 e 37; `results/review_cost/fixed_budget.csv`). Va mantenuto. `main_10p.tex:552` dice "ranked union yields slightly more"; `main_10p.tex` non riporta 35/39/40. Consiglio: riportare i tre numeri in una frase.

## 2. Composizione del prefisso ranked (`ranked_prefix_composition.csv`)
| Rx | ammessi da DIB | esclusi dal filtro di classe | sotto θ | senza quorum |
|---|---|---|---|---|
| US | 32 (88,9 %) | 4 | 0 | 0 |
| UK | 39 (90,7 %) | 4 | 0 | 0 |
| YT | 93 (86,9 %) | 14 | 0 | 0 |
Tutto ciò che il prefisso ha in più rispetto a DIB viene dal **filtro di eligibilità**, non dalla soglia né dal quorum. Il rendimento marginale scende da 0,97/0,91/0,37 confermati per voce dentro il prefisso a 0,69/0,65/0,06 nel blocco successivo.

## 3. Ordinamento, soglia di ammissione, filtro di eligibilità: tre cose diverse
| Meccanismo | Dove sta | Cosa fa |
|---|---|---|
| Soglia di ammissione θ (con quorum m) | `code/src/dib/evaluation/dib.py:22-47` (`admit_auto`: score ≥ θ e `supporting_sites ≥ m`); registro α=0,6, β=0,4, θ=0,65, m=2 (`registry/services.py:42-44`) | decide se un fatto entra in coda |
| Filtro di eligibilità A(d,e) | `dib.py:19` (`ELIGIBLE_CLASSES` = dns, ntp, update, vendor-cloud), applicato a `dib.py:47` | esclude classi di endpoint a prescindere dallo score |
| Ordinamento | solo valutazione: `code/scripts/union_ranked_budget.py:136` | il registro **non** ordina per score (`services.py:414-418`); "threshold-then-rank" è una raccomandazione (`main_10p.tex:539`), non un comportamento implementato |
Attenzione al nome: `eligible_sites` in `dib.py:255-276` è ES_d (siti che osservano il device type), un concetto diverso dall'eligibilità dell'endpoint.

## 4. Ablation Cs-only/Ct-only e split temporale
- `experiments_tnsm/split_ablation/run_20261011` (audit 53/54; deterministico, θ=0,65, m=2, filtro di classe attivo):

| Rx | DIB | solo Cs | solo Ct |
|---|---|---|---|
| US | 36, F1 0,116 | 38, 0,120 | 7, 0,038 |
| UK | 43, 0,115 | 43, 0,115 | 23, 0,074 |
| YT | 107, 0,247 | 129, 0,212 | 18, 0,116 |

  Esiti: H-S1 falsificata (lo split cambia l'insieme a w = 0,8–0,9 per US e YT); H-S2 regge (solo Cs = quorum + classe); H-S3 regge (solo Ct ⊆ DIB). Lo split 0,7/0,3 sta su un plateau e non è ottimale.
- `results/ablation_multiseed`: le varianti `no_site`/`no_temporal` **non rinormalizzano** i pesi (`dib.py:281-285`) e θ resta 0,65. Con α=0,6 e β=0,4 il massimo è 0,6 o 0,4 < θ, quindi 0 ammissioni per costruzione aritmetica. **Non usare** questa ablation come evidenza sui dati.
- Né (a) né (b) è nel paper. Se lo spazio lo permette, (a) in una frase: "Cs alone admits a superset close to quorum-plus-class; Ct alone admits a subset of DIB; the fixed 0.7/0.3 split lies on a plateau, not at an optimum."

## 5. Campagne finali R1e/R1f e B2k
**R1e/R1f** (degraded, 50 episodi per cella, 400 episodi, hash `3ffa57ee` negli 11 container di ogni cella): tutte le ipotesi pre-registrate reggono (audit 105, 108). Il paper (Tab. `tab:netem`) riporta mediane calcolate **solo sugli episodi senza consegna pendente** (n = 35–48 su 50). Da aggiungere nella didascalia: il numero di episodi, i massimi (fino a 28,1 s per C/1 contro una mediana di 17,2 s) e i retry di setup (R1e 38, R1f 26). Un ack tardivo ridondante in R1f C/10 ep. 20 (il sito aveva già applicato il ritiro a 2,42 s) non è in audit 108.

**B2k** (V): 840 prove pianificate (28 celle × 30), **834 analizzate**. Esclusioni: 5 `setup_failed` nella serie 1, che non faceva retry di setup, e 1 `queues_not_empty_at_start` nella serie 2, tutte degraded/C/k10. 16 retry di setup nella serie 2. **3 superamenti del limite**, tutti degraded: D T5 k10 7,10 s su 7,0; C T15 k1 11,61 s su 8,6; C T5 k10 11,56 s su 7,6 (timeout dell'handshake TLS al primo tentativo di reconcile). Stato finale: tutti monitor-only, **letto solo al sito riavviato** (`m67_retraction/run.py:918`).

**Definizione di k** (V, `run.py:864-884`): k = numero di **endpoint distinti**, ciascuno con **un** episodio dispute (site-1) → conferma (site-2) → restore (admin), tutti mentre site-3 è ucciso. Il recovery misurato è **dopo il riavvio del processo** (`compose kill` / `compose start`, convergenza da `t_start`, comprende il boot del container fino a 2,9 s a degraded). Non è il recovery di un servizio rimasto attivo durante una partizione, che non è misurato.

## 6. Frasi del paper da correggere (mediana ≠ garanzia per prova)
- `main_10p.tex:51` (abstract): "reconciles disconnected sites within a measured bound" → "with median convergence within a pre-registered bound (3 of 234 degraded trials exceeded it)".
- `main_10p.tex:466-470`: titolo "Recovery After Disconnection" → "Recovery After a Site Restart". k: "$k$ distinct endpoints, each disputed, confirmed and restored while the site is down". "six excluded for a refused setup request" → "six excluded (five refused setup requests in a series without setup retry, one with non-empty queues at start); 16 setup retries". "every site in the MonitorOnly state" → "the restarted site holds every fact in MonitorOnly".
- `main_wip.tex:800`: "within its bound in every measured cell" va riferito alla mediana per i dati finali.
- Non estendere il modello di costo TCP/TLS. La sottostima con mTLS (3–7 punti in 4 condizioni su 5) e i criteri pre-registrati non soddisfatti restano dichiarati.
