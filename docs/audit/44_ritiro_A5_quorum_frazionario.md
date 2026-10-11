# Audit 44 — RITIRO MOTIVATO — A5 (quorum frazionario + persistenza contro punteggio additivo, riedizione di S2): ritirata come test

Data: 2026-10-11 (orologio della macchina). **Nulla è stato calcolato.** Questo file **non è una pre-registrazione**: registra che A5 **non viene eseguita come test** (opzione (c) del draft, scelta dell'utente 2026-10-11), il motivo, e ciò che resta come risultato. Fonti: `docs/audit/43_piano_esperimenti.md` A5; draft precedente non tracciato (riassunto qui; le sezioni utili sono riportate sotto). Abbreviazioni: `aNN:r` = `docs/audit/NN_*.md` riga r; `wip:r` = `docs/main_wip.tex` riga r.

Invarianti: nessuna modifica a `code/src`, `service.py`, `formal/`, `claims.json`, `results/`; nessun ssh/sudo.

## 1. Decisione
**A5 ritirata come test; motivo: degenerazione per costruzione (q = 0, candidati pari).** Con q = 0 tutti i candidati ammessi stanno sul profilo, quindi la precisione è 1 per entrambe le regole; a numero di candidati pari anche il recall micro è uguale, con qualunque generatore (UNSW o parametrico). Di conseguenza: **H-A5 decade, D-A5-1, D-A5-2, D-A5-4 e D-A5-5 (δ) decadono, S2 non viene riaperta** (il ritiro di a41:54 non è revocato), **δ non serve più**, nessun generatore nuovo, nessuna esecuzione. Mercoledì 14 resta libero.

## 2. Perché le alternative non reggono
- **(b) rumore fuori profilo:** l'esito dipenderebbe da un modello di rumore (distribuzione di (C_s, C_t) di endpoint condivisi fuori profilo) scelto da noi: qualunque esito sarebbe attaccabile.
- **(a) esito macro per tipo:** misura solo come le due regole distribuiscono i candidati fra i tipi, non quale seleziona fatti migliori (nel generatore ogni endpoint del profilo ha lo stesso valore benigno). Può essere calcolato **solo come descrizione facoltativa, senza verdetto e senza δ**; non è nel piano.

## 3. Verifica dell'affermazione analitica sul codice (T1/T2; da scrivere rossi prima di usare l'affermazione, **non scritti né eseguiti**)
**Affermazione:** con γ = 0, α = 0,6, β = 0,4, θ = 0,65, m = 2, classe eleggibile e nessuna disputa aperta, DIB ammette un fatto se e solo se

  |S_e| ≥ m  ∧  C_s ≥ 5/12  ∧  C_t ≥ (θ − α·C_s)/β,   con 5/12 = (θ − β)/α,

dove C_s = `site_conf` (`dib.py:276`: `supporting_sites / eligible_sites`), C_t = `temporal_conf = min(1, 0,7·active_day_ratio + 0,3·frequency_ratio)` (`dib.py:277-279`), score = α·C_s + β·C_t + γ·graph (`dib.py:281-285`); l'ammissione è `admit_auto` (`dib.py:22-47`: quorum a `:45-46`, classe, `score >= theta` e assenza di disputa a `:47`; chiamata a `dib.py:297-302`). Il vincolo C_s ≥ 5/12 discende da C_t ≤ 1.
- **T1, algebra esatta (`fractions.Fraction`):** per N ∈ {5, 6, 10, 12, 20, 50, 100}, K = 0..N, C_s = K/N, C_t = j/100 con j = 0..100: `Fraction(3,5)*C_s + Fraction(2,5)*C_t >= Fraction(13,20)` ⇔ `C_s >= Fraction(5,12) and C_t >= (Fraction(13,20) − Fraction(3,5)*C_s)/Fraction(2,5)`, su tutta la griglia, punti di pareggio inclusi.
- **T2, sul codice:** su insiemi sintetici di osservazioni (siti, giorni, volumi variabili, anche endpoint `local-*`), per ogni `EndpointScore` (`site_confidence`, `temporal_confidence`, `supporting_sites`, `accepted`, `dib.py:289-304`) si ricostruisce la previsione con `Fraction` esatte dei float letti e si asserisce `accepted == previsione`. **Zona di pareggio:** i punti con |score esatto − θ| < 10⁻¹² non si asseriscono (il codice confronta float, `dib.py:47`; margini minimi noti in a11:36-41): si elencano separatamente e non contano né come fallimento né come conferma.
- **Mutazioni (devono far fallire i test):** φ = 1/3 al posto di 5/12; α e β scambiati; `>` al posto di `≥`; m = 1 al posto di 2; C_t senza il termine di frequenza.
- Se T2 fallisce fuori dalla zona di pareggio, l'affermazione è sbagliata o il codice fa altro: si riporta, non si corregge il codice di produzione.

## 4. Controllo descrittivo sui reali — NON è un verdetto, nessun criterio (riportato per completezza; non eseguito)
- Se C_s = 1 (**da verificare nel test T2 sui reali**: C_s = |S_e|/|ES_d|, `dib.py:276`), la condizione DIB diventa C_t ≥ (13/20 − 3/5)/(2/5) = 1/8.
- Con f = 0 la soglia sui giorni è d ≥ (1/8)/0,7 = 5/28 ≈ 0,179 (massimo della soglia implicita); con f > 0 è più bassa e si annulla per f ≥ 5/12. `docs/main_tnsm.tex:389` nota che f = n_{d,e}/n_d è strutturalmente piccola per tipi con molti endpoint (la frase non è più in `docs/main_wip.tex`, dove `wip:398` ha un commento SRC che dice che è stata tolta). Nessun numero di f è stato letto o calcolato.
- Confronto con i τ_match del confermativo (`aggregates.json:115, 229, 343`: US 0,17, UK 0,0, YT 0,17): τ_match è il τ minore con lo stesso conteggio (a40:19), quindi il confronto con 0,179 è descrittivo e poco discriminante; non si trae alcuna conclusione.

## 5. Argomento della degenerazione (lettura del codice, nessun calcolo)
- **Da dove si campionano i ranghi:** `eps = profiles["types"][d]` (`h61b.py:187`) e `for r, (ep, proto, port) in enumerate(eps, start=1)` con `rng.random() < r ** -ZIPF_S` (`h61b.py:189-191`): **solo i `TOP_ENDPOINTS` = 30 endpoint del profilo** (`h61b.py:108, 151`). Le sole altre osservazioni benigne sono gli endpoint locali `local-{s}-{j}.{d}.example` (`h61b.py:195-196`), con |S_e| = 1; con q = 0 il ciclo `for s in adv` è vuoto (`h61b.py:201-202`).
- **Conseguenza:** con q = 0 un candidato ammesso da DIB o da B_frac **non può** essere fuori dal profilo (il quorum `dib.py:45-46` / |S_e| ≥ 2 rifiuta gli endpoint locali). La precisione rispetto al profilo vale 1 per entrambe le regole; il recall micro è |C|/|P| con lo stesso P nella stessa replica, quindi, abbinando il numero di candidati, è uguale per costruzione entro la tolleranza del 10%. La regola "a parità il τ minore" (a40:19) ammette più candidati e può dare uno scarto sistematico a favore della baseline: un criterio "IC di d interamente > 0" potrebbe falsificarsi per artefatto di abbinamento.
- **Più in generale:** ogni endpoint del profilo ha lo stesso valore benigno nel generatore, quindi "recall a candidati pari" non distingue due regole che ammettono lo stesso numero di endpoint; dal lato sicurezza le due regole coincidono per φ = 5/12 (§3).

## 6. Cosa resta come risultato (per Q14, che resta del supervisore)
**Caratterizzazione analitica (§3):** nel regime a N siti, DIB equivale a un quorum frazionario φ = 5/12 con soglia di persistenza decrescente col breadth, τ(C_s) = (θ − α·C_s)/β = 1,625 − 1,5·C_s (da 1 a C_s = 5/12 fino a 1/8 a C_s = 1). Contro l'evidenza fornita solo da avversari la protezione è identica per costruzione (C_t ≤ 1 ⇒ C_s ≥ 5/12, `wip:416-421`). La frase da portare a Q14: **il breadth, così com'è, è un quorum relativo calibrato**; se sia un contributo lo decide il supervisore.
**Stato di verifica:** l'equivalenza è una derivazione algebrica; i test T1/T2 del §3 **non sono ancora scritti né eseguiti**. Prima di presentare la frase come risultato vanno scritti (rossi, poi verdi) e committati (offline, costo basso); altrimenti va presentata come derivazione non verificata sul codice. A5 non sostituisce H-B1/H-B2 (a41:10); S1 resta asserzione aritmetica (a41:51).
