# Audit 66 — Estensioni TLA+ proposte (a1, a6, a7, a8, a10) con stima dello spazio degli stati

Data: 2026-10-12. Branch `tnsm-fsm`. Obiettivo 5 del prompt dell'audit 61. **Nessuna modifica a
`formal/`, nessun TLC lanciato.** Le stime sono ordini di grandezza ricavati dai log esistenti;
diventano numeri solo con un'esecuzione di TLC, che richiede il tuo permesso.

## 0. Punti di ancoraggio (verificati sui log)
| Modello e config | Stati distinti | Profondità | Tempo | Fonte |
|---|---|---|---|---|
| M0 `DIB.tla`, 3 siti × 2 fatti | 4.311.852 | 21 | 5 min 06 s | `formal/logs/full_lifecycle.log:37-40` |
| M0 solo evidence | 2.076.196 | 21 | 1 min 25 s | `formal/logs/evidence_only.log:34-37` |
| `DIB_Distributed.tla`, 3 siti × 1 fatto | 48.960 | 18 | 4 s | `formal/logs/distributed_extension.log:32-35` |
| MAE `s0_safe_l0r2` (2 siti, 1 fatto, MaxEvents 2, MaxLoss 0, MaxRounds 2, MaxToggles 3) | 14.947.820 | 32 | 3 min 29 s | `formal/distributed_ae/logs/s0_safe_l0r2_run1.log:34-37` |
| MAE `s0_safe_l0r2_e3` (idem, MaxEvents 3) | ≥ 53.548.055, **incompleto** (23.134.462 in coda) | — | interrotto a 602 s | `…/s0_safe_l0r2_e3_timeout.log:34` |

Macchina dei log: 8 worker, 16 core, heap 29.127 MB (`s0_safe_l0r2_run1.log:2`).

Da qui due fattori empirici:
- **MaxEvents 2 → 3: almeno ×5** (53,5 M + 23,1 M in coda = 76,7 M ≥ 5,1 × 14,9 M; limite
  inferiore, perché la coda cresceva ancora).
- **Un sito in più** in MAE: nessun log (le config `v0_3sites_conv.cfg`, `v1_3sites_conv.cfg`
  esistono, `v0_3sites_conv.cfg:8`, ma non hanno log in `formal/distributed_ae/logs/`). Il fattore
  per sito è quindi solo stimato: le variabili per sito (`sstate` 5 valori × `sorigin` 3 ×
  `lastApplied` ≤ MaxEvents+1 × `rc` con più fasi × `outbox`) danno **×20-100**. NON VERIFICATO.

## 1. Estensioni

### E1 — a1: ammissione e Rescore in MAE
- Oggi MAE non modella l'ammissione: "Query needs evidence status Active only" (MAE:56). M0 la
  modella come Booleano con `Rescore` non deterministico (M0:63, M0:79-82).
- **Estensione:** `admissible[f] ∈ BOOLEAN` più un'azione `Rescore(f)`; `Query` e `OperatorCommit`
  richiedono `admissible[f]`, come S:501 e S:523 (oggi sempre vero nel codice, audit 63 D5).
- **Stima:** ×2-4 su `s0_safe_l0r2`, cioè **30-60 M stati**, minuti. Fattibile.
- **Valore:** basso per il distribuito, dove `accepted` è costante; serve solo se il paper attribuisce
  l'ammissione al prototipo distribuito.

### E2 — a8: Query, Commit e LocalRestore non atomici
- Ogni azione si divide in `Read(s, f)`, che salva in `pc[s]` lo stato e il seq dell'evidence letti,
  e `Write(s, f)`, che applica la guardia locale con i valori salvati, come S:500→516, S:522→532 e
  S:560-564→575. `LocalRevoke` diventa `Read`+`Write` solo se si vuole modellare b4 (vedi E3).
- **Proprietà nuove:**
  - `NoMonitorOnlyDuringEpisodeAtReachable` (b3q, b3r);
  - `NoCommitAfterDispute` (b3c: nessun `Commit` con `eseq[f]` maggiore del seq letto quando
    `estatus[f] ≠ "Active"`).
- **Stima:** `pc[s]` ha ~1 + 3 × (3 stati × ≤ MaxEvents+1 seq) ≈ 30 valori per sito, cioè circa
  ×30 per sito in teoria. Molti valori sono irraggiungibili: stima **×5-15 per sito**. Su
  `s0_safe_l0r2` (2 siti) significa **0,4-3,4 miliardi** di stati: non fattibile in RAM.
- **Variante proposta:** split solo per il sito partizionabile `s1`, cioè ×5-15, **75-225 M**. Fattibile
  in ore con fingerprint su disco.
- **Ricerca di controesempi:** costa poco. Le tracce dei test b3 sono lunghe 3-4 eventi (stage,
  dispute, commit), e i log con violazione mostrano controesempi trovati con pochi stati (es.
  `v1_lag`: 651 stati, 2.912 per `s0_smoke_run1`, NON VERIFICATO su questi due log). Per mostrare
  b3 nel modello basterebbero MaxEvents 1 e MaxToggles 1-2.
- **Valore:** alto. È l'unica estensione che porta nel modello i difetti trovati in audit 64.

### E3 — a6: partizioni asimmetriche e direzione evidence → sito
- Oggi c'è un solo flag `unreachable` = "l'evidence non consegna al sito; il sito raggiunge
  l'evidence" (MAE:41-46). "Evidence unreachable from the site" non è modellato (MAE:53).
- **Estensione:**
  - due flag per sito partizionabile, `noDeliver[s]` (quello attuale) e `noPull[s]`;
  - `ReconcileRead` richiede `¬noPull[s]`;
  - con E2, anche `Read` di Query/Commit/LocalRevoke/LocalRestore richiede `¬noPull[s]`, il che
    modella b4 (veto locale bloccato).
- **Stima:** ×2-4 (il toggle raddoppia i valori di partizione e allunga le tracce). Senza E2,
  **30-60 M**; con E2 limitato a `s1`, **150-900 M**: al limite, solo con disco.
- **Valore:** medio-alto. Rende rappresentabile b4 e la partizione di b3c.

### E4 — a7: 3 siti, MaxEvents 3, crash
- **3 siti:** stima ×20-100 su 14,9 M, cioè **0,3-1,5 miliardi**. Non fattibile senza riduzioni.
  - La simmetria sui siti non partizionabili (`Permutations({s2, s3})`) dimezza circa lo spazio, ma
    non vale con le proprietà temporali di `SpecL`.
  - Proposta: solo `Spec` (safety) con simmetria, oppure lanciare prima le config a 3 siti già
    scritte (`v0/v1_3sites_conv.cfg`), il cui costo è ignoto.
- **MaxEvents 3:** ≥ ×5 (misurato), **≥ 77 M**. Fattibile con disco, ore.
- **Crash del sito durante la reconcile:** un'azione `Crash(t)` che riporta `rc[t]` a `IdleRc` senza
  ack; `rc` è già una macchina per sito (MAE:93, MAE:158). Stima ×1,5-2.

### E5 — a10: quorum di sospensione 2
- Oggi la sospensione è fissa a 1 (MAE:55, MAE:207).
- **Estensione:**
  - variabile `votes[f] ⊆ Reporters`;
  - un'azione `Vote(r, f)` che non sospende finché `|votes| < 2`;
  - `Dispute` di conferma richiede `r ∉ votes[f]` (la regola che hai deciso) oppure
    `r ≠ edisp[f]` (il codice attuale, S:918);
  - con le due varianti come costante, il modello distingue le due regole.
- **Stima:**
  - con 2 reporter, ×4 per i sottoinsiemi di voti;
  - un evento in più per arrivare a Revoked (MaxEvents 2 → 3, ≥ ×5): ×20 su `s0_safe_l0r2`,
    cioè **~300 M**, solo con disco;
  - con 3 reporter (necessari per la tua regola: due votanti e un terzo che conferma), ×8 per i
    voti: **~600 M**.
  - Variante economica: 1 sito, solo evidence, come `evidence_only` (2,1 M in M0).
- **Valore:** alto per la regola a10, che oggi non è verificata da nessun modello.

## 2. Priorità proposta (nessuna esecuzione senza il tuo permesso)
1. **E2 ridotta** (split solo per `s1`, MaxEvents 1-2) come **ricerca di controesempi** delle finestre
   b3: veloce, e deve trovare la violazione che i test di audit 64 hanno già mostrato (controllo
   positivo del modello).
2. **E5** sulla sola evidence (variante economica): verifica la regola di a10 prima di toccare S.
3. **E3** senza E2, poi con E2 ridotta.
4. **E4** solo dopo, con disco e simmetria; prima le due config a 3 siti già esistenti.
5. **E1** ultima.

## NON VERIFICATO
- Fattori per sito e per estensione (sez. 1): stime da conteggio delle variabili, non misure.
- Conteggi dei log `v1_lag_run1.log`, `s0_smoke_run1.log`, `mut_ae*_run1.log`: riportati dall'agente,
  non riletti.
- Uso di memoria/disco di `s0_safe_l0r2_run1` (l'agente indica ~13,8 GB): non riletto.
