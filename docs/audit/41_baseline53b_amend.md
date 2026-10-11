# Audit 41 — Baseline 5.3b: risultato CONFERMATIVO dell'audit 40 (regole letterali) ed emendamento SECONDARIO, NON CIECO (POST-HOC)

Data: 2026-10-11 (orologio della macchina: `date` = Sun Oct 11 17:39 CEST 2026 = 15:39 UTC, ora della riscrittura corrente; la prima stesura era delle 17:34 CEST; l'intestazione dell'audit 40 dice 2026-10-12, in anticipo di un giorno sull'orologio: errore di data nell'audit 40, non corretto lì). **Questo file non contiene verdetti calcolati.** Stato: bozza, non committata, in attesa del via.

## 0. Che cosa è confermativo e che cosa no
**Sequenza verificata dalle date** (`git log --format='%H %ci'` e `stat`):
- audit 40 = commit `6aace7fff76d9c5640e85ffb3b313eeed3256c13`, 2026-10-11 17:25:15 +0200;
- codice + test = commit `6dc4f52baa2fb4ec20aefd9bde6429f321c24927`, 2026-10-11 17:30:23 +0200;
- run `analyze_baseline.py real --out experiments_tnsm/baseline_quorum_persistence/run_20261012/real`: file scritti 2026-10-11 17:31:04–17:31:05 +0200.
Audit 40 e codice precedono il run: **il run con le regole letterali dell'audit 40 è il risultato CONFERMATIVO** (H-B1 e H-B2 con soglia 0,02, controllo di riproduzione incluso). Non è stato rieseguito né modificato. Contiene solo il sottocomando `real` (nessun S1, nessun S2). Del suo output stampato ho visto solo la coda (H-B2: recall DIB = recall baseline nei tre riceventi; YT: precisione DIB = precisione baseline); il resto lo leggerò nel passo che lo riporta.

**sha256 dei file del run** (`run_20261012/real/`):
- `aggregates.json` `15cd3be186b01654cd1d41b6ef6133b44473460630483122a7304ba6d5a9a560`
- `manifest.json` `bc4dc51ac45b7962cbfa1f07918ff415f7c8699b1d5afa28c4b8fd5eb1cb3fac`
Dati di ingresso (sha256 completi, letti in place da `/root/Desktop/DIB/data/processed/`, nessuna copia): `moniotr_full_observations.csv` `6d2f0080b6221b4ca696687e91e3225bc37e6e7665d4575947731c4897a1911b`; `yourthings_observations.csv` `b6db48840353f7a26c62ef53842a552561f1096a7fab1187ee1ebe44ae50ef8a`.

**Quali parti della regola stavano nel testo dell'audit 40 e quali solo nel codice 6dc4f52**
- *Nel testo (40):* definizione di B(m, τ) (quorum, persistenza `dib.py:269-271`, classe `ELIGIBLE_CLASSES`); griglia τ grossolana {0; 0,05; 0,125; 0,25; 0,5}; m ∈ {1, 2}, m = 3 «non definito»; τ_match = τ della griglia fine {0; 0,005; …; 1} con numero di candidati più vicino a |locked|, a parità il τ minore (riga 19); variabile = numero di candidati; H-B1 (DIB > baseline in ≥ 2 riceventi su 3, falsificata se ≤ in ≥ 2 su 3); H-B2 (soglia 0,02, «di più di 0,02 in almeno un ricevente»); controllo di riproduzione esatto delle quattro righe.
- *Solo nel codice:* la griglia fine come `round(k·0,005, 3)`, k = 0..200 (`FINE_GRID`); il pareggio realizzato con «strettamente più vicino» (`tau_match`); la maggioranza H-B1 come `migliori·2 > 3`; il confronto H-B2 come `round(differenza, 12) > 0,02`; tolleranza 1e-12 nel controllo di riproduzione; il valore di recall = 0 per un dispositivo senza riferimento (`set_metrics`, `moniotr_cross_lab.py:578-582`, ereditato); la stringa «non definito» per m = 3.
- *In nessuno dei due:* una condizione di validità del 10% (è nuova in questo audit, §3).

## 1. Statuto dell'emendamento
Tutto ciò che questo audit introduce è un'**analisi SECONDARIA NON CIECA, i cui verdetti si etichettano POST-HOC**: non sono stati scritti prima del run e conoscono la coda del suo output. Elenco: l'IC bootstrap di H-B2 con d = 5.3b − DIB (§2); la griglia fine come specifica esplicita (§3); la regola di abbinamento con soglia 10% (§3); lo stato «non valutabile» in H-B1; la rimozione del criterio p* di H-B3 e la sua riduzione ad asserzione aritmetica (§5); il ritiro di S2 (§6). I verdetti confermativi restano quelli del run letterale; **nessun verdetto secondario sostituisce o corregge il confermativo**, si riportano accanto.

## 2. H-B2, versione secondaria: IC bootstrap appaiato (POST-HOC)
- **Segno (confermato):** d = recall(5.3b) − recall(DIB); falsificata se l'IC è interamente sopra 0.
- **Statistica:** d = media sulle unità (ricevente, dispositivo) di recall_dev(B(2, τ_match)) − recall_dev(DIB), `set_metrics`; con tutte le 18 unità coincide con la media dei tre recall macro per ricevente (`v28_matched_ablation.py:30`).
- **Metodo:** bootstrap appaiato, percentile 95% (quantili 2,5% e 97,5% di d*), B = 10 000, seme 20261012 (`random.Random`).
- seme 20261012 derivato dalla data errata dell'audit 40; mantenuto invariato.
- **Unità di ricampionamento:** la coppia (ricevente, dispositivo), con reinserimento, DIB e baseline appaiati sulla stessa unità. Perché: i riceventi sono 3 (al più 10 ricampionamenti distinti); i dispositivi sono l'unità su cui è definita la media macro; l'appaiamento toglie la varianza fra dispositivi. **Limite:** i dispositivi dello stesso ricevente condividono le sorgenti e gli stessi tipi ricorrono in più riceventi, quindi l'IC è ottimistico. Si riporta anche l'IC per ricevente (6 unità), descrittivo.
- **Dispositivi senza positivi nella verità di riferimento** (|osservati| = 0): il recall non è definito, quindi le unità **sono ESCLUSE dal bootstrap**. Conteggio sui dati (solo conteggi, nessun valore per dispositivo): **0 su 6 in US, 0 su 6 in UK, 0 su 6 in YT**; quindi nessuna unità esclusa e **n effettivo = 18** (6 per ricevente). **Regola:** con n < 10 l'IC è **descrittivo, non un test** e il verdetto non si formula; l'IC per ricevente (n = 6) è quindi sempre descrittivo, l'IC complessivo (n = 18) è valutato con la regola letterale ma con il limite di dipendenza sopra.
- **Recall macro del run confermativo:** `matched_ablation.csv` e il run confermativo calcolano la media sui 6 dispositivi **includendo** anche le unità a riferimento vuoto, con il valore che restituisce `set_metrics` (`moniotr_cross_lab.py:578-582`: `recall = matched/len(observed) if observed else 0.0`, cioè 0,0). Nei dati attuali nessuna unità è in quel caso, quindi le due definizioni coincidono; la dichiarazione resta per completezza.
- **Regola letterale:** falsificata solo se l'estremo inferiore dell'IC è > 0; altrimenti «non falsificata».
- **IC degenere** (tutte le unità con d = 0, quindi IC = [0, 0]): verdetto **«non falsificata; nessuna differenza osservata, nessun potere»**, non «confermata».
- Per un ricevente senza abbinamento valido (§3) le unità sono escluse e n è riportato.
- Le coppie (ricevente, dispositivo) sono dati derivati: fuori dalla repo, sha256 nel manifest; in `docs/audit/` solo IC, n, verdetti.

## 3. Abbinamento, griglie, m
- **m:** m = 2 equivale all'unanimità delle due sorgenti (|S_e| ≥ 2 con due sorgenti) ed è l'unica baseline dei verdetti. **m = 1 è solo descrittivo** (unione con filtro di persistenza e di classe, nessun verdetto). m = 3: «non definito (due sole sorgenti)».
- **τ grossolano (descrittivo):** {0; 0,05; 0,125; 0,25; 0,5}. **τ fine (abbinamento):** k·0,005, k = 0..200 (201 valori, 0…1). Nessun altro valore.
- **Variabile dell'abbinamento (il «10%»):** numero totale di candidati |C| = chiavi (dispositivo, endpoint, protocollo, porta) ammesse con dispositivo fra i 6 del ricevente; riferimento |C_DIB| = |locked| (`v28_matched_ablation.py:29,39`). Né numero per dispositivo, né precisione, né recall.
- **Scelta:** τ della griglia fine che minimizza ||C_B(2,τ)| − |C_DIB||, a parità il τ minore. **Validità:** solo se ||C_B| − |C_DIB|| ≤ 0,10·|C_DIB|; se nessun τ lo soddisfa, per quel ricevente **nessun confronto secondario** («nessun abbinamento»), nessun allargamento.
- **Run confermativo:** la condizione del 10% **non si applica**; per ciascun ricevente si riporta, descrittivamente, il divario ||C_B| − |C_DIB|| e il suo rapporto con |C_DIB|. La condizione vale solo per l'analisi secondaria.
- **Differenza rispetto a 6dc4f52:** la regola di scelta del τ è **identica** (stessa variabile, stesso minimo, stesso pareggio: `tau_match`, `analyze_baseline.py` in 6dc4f52, e testo dell'audit 40 riga 19). Cambia solo la **condizione di validità del 10%**, assente nel codice e nel testo del 40; nel run confermativo non si applica (sopra) e il divario è riportato come descrittivo. Quindi il τ scelto non può differire; se la condizione non è soddisfatta per un ricevente, per il confermativo resta τ_match (già calcolato), per il secondario «nessun abbinamento».
- **H-B1 secondaria:** criterio «≤» **invariato** (falsificata se la precisione di DIB è ≤ quella della baseline in ≥ 2 riceventi su 3). Aggiunta POST-HOC: «non valutabile» se per i riceventi senza abbinamento non si può arrivare a 2 su 3 in nessun senso.

## 4. Invarianti
`code/src` invariato dal commit 6aace7f; sha256 di `code/src/dib/registry/distributed/service.py` = `3186304363ed309241134752689423088dda98b9d8fe3bcdf9669749264398fd`. Nulla in `results/`, nessun ssh al nodo, script solo in `experiments_tnsm/`, solo aggregati nella repo.

## 5. H-B3 (POST-HOC): aritmetica, non test
Per N ≥ 5, ⌈5N/12⌉ ≥ 3 > m = 2 (audit 40 §2 S1) ⇒ r_B(2) ≥ r_DIB a ogni punto. Diventa un'**asserzione** su `k_hist.json`/`points.csv` con i rapporti r_B(m)/r_DIB riportati; asserzione fallita = bug dell'import, non un verdetto. Il criterio «p* < 10⁻³» dell'audit 40 §4 è rimosso (in contrasto con «rilevabile con 20 000 prove»). `verdict_hb3` (6dc4f52) non viene usato.

## 6. Dataset e S2 (POST-HOC)
Solo Mon(IoT)r US, Mon(IoT)r UK, YourThings, ricevente a rotazione con le altre due sorgenti. **UNSW esclusa; nessuno sweep di m sui pseudo-siti UNSW.** S2 dell'audit 40 (federazione sintetica ancorata ai profili UNSW) è **ritirata** e non verrà eseguita; il codice relativo resta inutilizzato in `analyze_baseline.py` finché non viene tolto in un commit dedicato. S1 non usa UNSW (istogrammi sintetici già registrati) e resta solo come asserzione di §5.

## 7. Passi successivi (non avviati)
**Codice nuovo per il recall per dispositivo:** la rielaborazione è codice nuovo in `experiments_tnsm/baseline_quorum_persistence/`, con test scritti prima, **committato prima dell'esecuzione**; i valori per dispositivo (derivati da Mon(IoT)r/YourThings) restano **fuori dalla repo**, in una cartella di lavoro esterna, con sha256 registrato nel manifest; nella repo solo IC, n e verdetti.
Dopo il tuo via: commit di questo file (`git add docs/audit/41_baseline53b_amend.md`); output confermativo del run (solo aggregati, in questo ordine: righe di riproduzione, baseline per m e τ, τ_match, verdetti letterali di H-B1 e H-B2 del run); poi Fase B (riproduzione di `matched_ablation.csv`, diff grezzo).
