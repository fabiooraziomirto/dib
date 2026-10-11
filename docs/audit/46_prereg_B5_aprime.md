# Audit 46 — PRE-REGISTRAZIONE — B5: (a') con i tentativi falliti, SOLO dati nuovi a `degraded`

Data: 2026-10-11. **Nessun dato raccolto.** Pre-registrazione committata **prima** del blocco (via dell'utente, 2026-10-11). Fonte: `docs/audit/43_piano_esperimenti_DRAFT.md` B5; a34:13-19, 54-60; a35:25-26, 119-143, 173; a14:236-237, 250; `wip:617, 640`. Questo file non autorizza ssh, sudo né lanci (uno per volta, dell'utente).

## 1. Domanda e statuto
Il modello "n_RTT·R + 1 s per tentativo fallito" prevede il tempo di ritiro a `degraded`? **La (a) originale resta falsificata 4/4 (a34:13-19) e non si riformula; nessun dato vecchio entra in (a').** È una **replica sullo stesso nodo e sullo stesso profilo** del blocco che ha falsificato (a): stesso host, stessa emulazione, stesso generatore co-locato, **non un test indipendente**; il paper deve dirlo.

## 2. Ipotesi H-(a')
soglia(cella) = n_RTT·R·(×10 se FANOUT 1) + E[F]·1 s + 3 × mediana `lan` adiacente, con E[F] = p + p² + p³ e **p fissato prima dai valori di profilo** (per tentativo: D 0,185-0,226, C 0,302-0,401, a14:236-237), non stimato dai dati che la testano. Esito: mediana del tempo di ritiro sugli **episodi completi** (nessuna consegna in pending), come `tab:netem` (`wip:621`).
- **Verdetto 1, "(a') falsificata" (eccesso):** in una cella, l'**estremo inferiore** dell'IC bootstrap 95% della mediana supera la soglia (stessa forma di (a), `wip:617`).
- **Verdetto 2, "modello di base falsificato" (difetto), SEPARATO dal precedente:** in una cella, l'**estremo superiore** dell'IC sta **sotto n_RTT·R**. n_RTT·R è un limite fisico (nessun tentativo fallito, nessun margine): un IC sotto quel valore vuol dire che il modello di base è sbagliato, non che (a') è conservativo. Non si riporta come "(a') falsificata per eccesso".
- **Molteplicità (D-B5-1, CHIUSA):** nessuna correzione, come in (a), così il confronto col blocco che l'ha falsificata (4/4, a34:13-19) resta diretto; IC 95% per cella, k = 4 celle (C, D × FANOUT 1, 10) fissato. Verdetto per cella, riportato come **k/4** per ciascuno dei due verdetti. **Regola globale, scritta prima dei dati:** "(a') falsificata se almeno 1 cella su 4 verifica il verdetto 1" (stessa lettura del 4/4 di (a)); "modello di base falsificato se almeno 1 cella su 4 verifica il verdetto 2". Se entrambi → si riportano entrambi.

## 3. Trattamento del pending (fissato ora)
- **Test pre-registrato = replica di (c):** frazione di *consegne* in pending per cella, IC di Clopper-Pearson; intervalli di profilo (f³ per tentativo): D [0,004; 0,015], C [0,025; 0,08] (a14:236-237, `wip:617`). Falsificata se l'IC è interamente fuori dall'intervallo (a34:54-60). Unità = consegna.
- **Frazione di episodi con almeno un pending: DESCRITTIVA, non primaria** (nessun intervallo atteso derivabile; richiederebbe un'ipotesi di indipendenza fra siti non registrata). Con IC di Clopper-Pearson, senza criterio.
- Tutti gli esiti riportati sempre, con i rispettivi n.

## 4. Configurazione
Blocco `lan` prima → `degraded` → `lan` dopo; C e D × FANOUT {1, 10}; **50 episodi a `degraded`** (a14:250) ⇒ n effettivo atteso 31-46 per cella dopo le esclusioni del primo blocco (`wip:632-635`); durata ~1,4 h (a34:6). n per continuità col primo blocco, non da potere. Prerequisiti: B0 (PKI 336 h), B1a, L_dns (audit 45 §5). Seed, versione Python, hardware, hash nel manifest; dati in `experiments_tnsm/`, non in `results/`.

## 5. Esclusioni e stop
Come il blocco precedente: `transport_error_setup`, `client_timeout`, esclusione per sovrapposizione (a20:55), regola R-gp su `generator_path_ms` (a20:55; fresca anomala 607 ms in a34 §3); un solo nuovo tentativo per gruppo senza dati (a33:19-20); stop per battito, df < 2 GB, PKI scaduta. Codice di analisi con test scritti prima (come `analyze_b1.py`/`analyze_c.py`).

## 6. Destino dei dati
Se Q4+Q5 dice di non rifare (a'), i dati restano in `experiments_tnsm/` e **non entrano nel paper**: nel paper si riporta (a) falsificata + calcolo post-hoc "not tested" (`wip:640`). Questo non è una ragione per modificare ipotesi dopo i dati.
