# DIB: piano completo di lavoro (target: IEEE TNSM)

Stato: 9 ott 2026. Base: `main__2_.tex` con i commenti del supervisor.
Questo file **sostituisce** `piano_lavoro_DIB.md` e `scenario_ed_esperimenti_DIB.md`.
Tutti i parametri numerici sono punti di partenza da validare, non risultati.

---

## 0. Principio guida

Il **nucleo concettuale resta invariato** (al massimo si rafforza). Si interviene su formalizzazione, esperimenti, scalabilità, autenticazione, scenario e inquadramento.

**Nucleo intoccabile**
1. Separazione tra evidenza condivisa e autorizzazione locale.
2. Ciclo di vita a stati con *approvazione valida* e *origine della revoca*.
3. Ritiro coordinato che invalida le approvazioni ma preserva i veti locali.
4. Riconciliazione tramite un unico target pendente collassato (anche dopo episodi saltati).

**Nuovo asse del paper:** "il lifecycle delle policy MUD lato operatore, con evidenza condivisa e autorità indipendenti". La selezione dei candidati (score, Pareto, dataset) diventa componente abilitante, non contributo principale.

**Claim di novità (da usare con cautela):** *to the best of our knowledge*, nessun lavoro MUD tratta ritiro, ripristino e riconciliazione lato operatore tra autorità indipendenti. La ricerca fatta finora è rapida, non sistematica. Le primitive (deny-overrides, LWW, quorum) non sono nuove: il valore sta nel problema e nella composizione.

---

## 1. Domani: prime cose da fare

- [ ] Confermare i due commenti ambigui: **"active ricorsivo"** (ipotesi: ciclo Active → … → MonitorOnly → Active) e **"provare al contrario"** su `Exportable` (ipotesi: formulazione negativa).
- [ ] **Audit del codice** (sezione 7.1): riprodurre i numeri esistenti, mappa di tracciabilità modello ↔ codice ↔ test.
- [ ] Preparare la lista delle **decisioni da concordare** (sezione 2) e fissare un incontro breve col supervisor.
- [ ] Pulizia testuale indipendente da tutto (sezione 3A).
- [ ] Iniziare la lettura integrale dei lavori vicini (sezione 4).

---

## 2. Decisioni da prendere col supervisor (bloccano il resto)

1. **Caso ibrido (G1):** il lifecycle si attiva solo senza MUD del produttore, oppure anche in modalità ibrida (profilo del produttore + fatti locali sotto deny-overrides)? La Discussion già ammette l'ibrido.
2. **Estensioni del lifecycle** da includere, tutte derivate da validità + origine: versioning/sostituzione di un fatto (cambio firmware), fine vita del dispositivo, scadenza/lease, arrivo di un MUD del produttore.
3. **Goal e threat model:** G2 = "protezione dall'evidenza inadatta" (ammissione ex ante + dispute ex post)? Gli abusi di dispute entrano nel threat model (A4)? G1 e G3 declassati a requisiti/invarianti?
4. **Peso della selezione dei candidati:** rietichettata come componente abilitante e compressa se manca spazio?
5. **Scenario guida:** federazione di smart building (sezione 5).
6. **Autenticazione tra siti con certificati** (sezione 6): confermare l'ambito (mTLS tra servizi; operatore umano escluso).
7. **Limite di pagine TNSM** e scadenza.

---

## 3. Mappa dei commenti → azioni

### A. Pulizia testuale (basso sforzo)
- [ ] Abstract: fondere la versione \del/\add. Togliere "works as intended" (ripetuto e non falsificabile); usare numeri (4,3M stati senza violazioni, 6/6 mutazioni intercettate, 40/40 riconnessioni). Specificare che i 100 ms riguardano la sola logica di riconciliazione (convergenza end-to-end ~0,5 s).
- [ ] Introduzione: riscrivere la frase su evidence/registry (l'evidenza sta nel registry condiviso, le decisioni restano per sito, quindi l'evidenza non implica mai un permesso locale).
- [ ] "To overcome this limitation": manca il referente; aggiungere frase esplicita sul gap.
- [ ] Spostare nel design i termini non ancora definiti (deny-overrides, last-writer-wins, approval validity).
- [ ] Rimuovere "To conclude" dai contributi; collegare ogni contributo all'esperimento che lo valida (commenti "the goal is / to validate…").
- [ ] G1: frase grammaticalmente rotta.
- [ ] Segnaposto "A1 tests -----." nel threat model.
- [ ] Riferimento orfano **P5** nella Discussion.
- [ ] Etichette (G2)/(G4) nella valutazione: il cold-start riguarda G1, non G2.
- [ ] Terminologia: "report" (osservazione vs dispute → rinominare *dispute notice*), "export" (verso altri siti vs verso MUD manager).
- [ ] Rimuovere markup `\del`/`\add`, blocchi G3 commentati, commenti residui.
- [ ] Micro/macro (riga ~523): scrivere "micro" per il 65,5% (36/55), aggiungere il valore macro (63,2%) e allineare `claims.json`.

### B. Concetti e formalizzazione
- [ ] Motivare perché **I1–I3** sono le proprietà giuste (oggi assunte); dichiarare che le mutazioni mostrano la necessità delle guardie rispetto a quelle proprietà.
- [ ] `Exportable = Active ∧ grantValid`: nel modello corretto Active implica grantValid. Spiegare perché i due predicati sono separati (e provare la formulazione negativa chiesta dal supervisor).
- [ ] Estendere il modello TLA+ con le fasi nuove (decisione 2) e, se regge, più siti/fatti.
- [ ] Rendere esplicita nel diagramma/tabella la natura ciclica del lifecycle (se "active ricorsivo" va in questa direzione).

### C. Score
- [ ] Separare **guardiano** (quorum + breadth, con garanzia formale) da **ranker** (persistenza e frequenza, senza garanzie).
- [ ] C_t: oggi non contribuisce alla garanzia ed è quasi solo copertura giornaliera. Semplificarlo o renderlo cross-sito (giorni con almeno m siti).
- [ ] Ablation C_s-only / C_t-only / combinata; sweep o eliminazione del 0,7/0,3.
- [ ] Giustificare f_s = 0,30: distinguere A2 (soglia 1/3 dei sistemi bizantini) da A1 (prevalenza di dispositivi infetti per tipo, studi post-Mirai).
- [ ] Eligibility (commento www.facebook.com): "any remaining FQDN" è troppo permissivo. Valutare classificazione first/support/third party (Mon(IoT)r) e misurare il costo in recall.

### D. Threat model e goal
- [ ] Riscrivere i goal come proprietà; threat model centrato su G2 con A1–A3 (+ A4 abuso di dispute, se deciso).
- [ ] Spiegare e rinominare il "report message"; chiarire che mappa G2.
- [ ] Rimuovere il caveat "autenticazione non validata" solo dopo aver implementato la sezione 6; restano veri: compromissione della CA o di una chiave, autenticazione dell'operatore.

---

## 4. Stato dell'arte (lifecycle e riconciliazione)

Ricerca rapida già fatta (tabella per fase: D = scoperta da traffico, A = approvazione locale, U = aggiornamento, W = revoca, R = ripristino, C = riconciliazione offline; ● copre, ◐ parziale, ○ no, ? da verificare, – n/a):

| Lavoro | D | A | U | W | R | C |
|---|---|---|---|---|---|---|
| RFC 8520 + draft lifecycle produttore | ○ | ◐ | ● | ◐ | ○ | ○ |
| mud-acceptable-urls | ○ | ○ | ● | ○ | ○ | ○ |
| FIDEM | ○ | ○ | ● | ○ | ○ | ? |
| MUDgee / Hamza | ● | ◐ | ◐ | ○ | ○ | ○ |
| Blockchain dynamic MUD | ● | ○ | ● | ○ | ○ | ? |
| AutoMUD | ● | ○ | ◐ | ○ | ○ | ○ |
| Closing the Loop | ○ | ○ | ○ | ● | ? | ? |
| Brevetto US 10841164 | ● | ○ | ● | ○ | ○ | ○ |
| MISP / STIX | ● | ○ | ○ | ◐ | ○ | ○ |
| PKI (CRLite, Let's Revoke) | – | – | – | ● | ○ | ◐ |
| Zanzibar | – | ○ | – | ● | ○ | ◐ |
| VERA | – | ◐ | – | ● | ? | ○ |
| **DIB** | ● | ● | ◐ | ● | ● | ● |

Valutazioni da abstract e frammenti: **vanno confermate sui testi completi.**

Da fare:
- [ ] Leggere per intero: **VERA** (arXiv 2608.30091), **Closing the Loop** (arXiv 2607.11649), **FIDEM** (arXiv 2605.29654, il PDF non era leggibile), **AutoMUD** (arXiv 2609.31594), draft IETF *mud-acceptable-urls* e *MUD lifecycle (manufacturer)*, SoK *Beyond IoT MUD Deployments*.
- [ ] Verificare nel Table I la cella FIDEM ("re-check on reconnect"); FIDEM ha un requisito di aggiornamenti sicuri (R5), ma il suo cuore è il binding sicuro dell'URL via DHCP.
- [ ] Differenziare da: revoca PKI (i nodi che saltano aggiornamenti li richiedono singolarmente), Zanzibar (autorità unica), VERA (revoca che preserva autorità indipendenti; vicino concettualmente, fuori dal MUD).
- [ ] Altre ricerche: aggiornamenti consistenti in SDN, anti-entropy/gossip, tombstone, ritiro di informazioni condivise in STIX/MISP.
- [ ] **Protocollo di ricerca documentato** (stringhe, date, IEEE Xplore / ACM DL / Scopus, criteri di inclusione) da riportare nel paper.
- [ ] Rifare la Table I come tabella per fase del lifecycle e scrivere il paragrafo rosso richiesto dal supervisor (cosa differenzia DIB e cosa porta alla community).

---

## 5. Scenario: federazione di smart building

### 5.1 Perché questo scenario
- Siti = edifici gestiti da **organizzazioni indipendenti** (enti locali, campus, gruppi ospedalieri, gestori immobiliari), ciascuna con IT/facility manager credibile come operatore locale.
- Interesse reale a condividere evidenza (flotte simili di controller, telecamere, lettori accessi) quando mancano i MUD del produttore.
- Il ritiro ha un costo operativo reale (climatizzazione, accessi).
- **Perché non la REC di famiglie:** l'operatore locale non è credibile (una famiglia non revisiona endpoint), se lo fa un gestore la REC ha un'autorità unica e il nucleo del paper si svuota, e la privacy dell'evidenza diventa un problema serio. La REC resta contesto motivazionale in introduzione o scenario secondario in Discussione.
- Da dichiarare: scenario **emulato e illustrativo**.

### 5.2 Configurazione di riferimento
| Parametro | Valore base | Sweep |
|---|---|---|
| Numero di siti N | 20 | 10, 20, 50, 100 |
| Gruppi organizzativi | 4 | – |
| Tipi di dispositivo | i 6 tipi comuni ai tre dataset (verificare quali sono nel mapping) | – |
| Fatti per sito F | ~100 | 100, 1.000, 10.000 |
| Presenza di un tipo nei siti | ogni tipo in ≥ 40% dei siti (il quorum m=2 deve avere senso) | 20–80% |
| Concentrazione vendor | Zipf sui cloud endpoint | – |
| Frazione di siti malevoli f_s | 0,30 | 0–0,5 |

- **Traffico:** riusare le catture esistenti (UNSW, Mon(IoT)r, YourThings) riassegnate ai siti con un generatore deterministico (seed); dichiarare che la partizione tra siti è sintetica.
- **Divergenza locale:** assegnare a ogni sito endpoint "legittimi solo qui", per produrre veti e approvazioni diverse.

### 5.3 Eventi di prova
| ID | Evento | Cosa testa |
|---|---|---|
| S1 | Compromissione di un cloud di vendor: un sito apre la dispute, un secondo conferma | Ritiro coordinato, tempo di ritiro, ACE rimosse |
| S2 | Episodio dispute→conferma→restore con k siti offline; alcuni con veto locale | Riconciliazione dopo episodi saltati, preservazione dei veti |
| S3 | Ingresso e uscita di membri durante un episodio | Denominatore di C_s, coda di revisione, emissione/revoca di certificati |
| S4 | Cambio firmware: cambia l'insieme di endpoint di un tipo | Versioning (solo se incluso nel modello) |
| S5 | Compare un MUD del produttore per un tipo già gestito | Caso ibrido, deny-overrides (solo se incluso) |
| S6 | Disputer malevolo/collusione: dispute ripetute su fatti legittimi | Abuso di dispute (A4), costo di disponibilità |
| S7 | Rete degradata: latenza, perdita, partizioni asimmetriche durante S1/S2 | Robustezza di fan-out e riconciliazione |
| S8 | Sito con certificato rubato/compromesso | Può aprire dispute ma non creare autorizzazione locale (sezione 6) |

### 5.4 Metriche
- **Correttezza:** violazioni di I1–I3 rilevate dall'oracolo online; ACE esportabili di fatti disputati; finestra di esposizione a regole obsolete.
- **Tempo di ritiro:** dall'apertura della dispute alla rimozione della regola in ogni sito (p50/p95/max).
- **Riconciliazione:** tempo, messaggi e byte in funzione degli episodi saltati k.
- **Stato:** dimensione per fatto e per sito.
- **Disponibilità:** flussi legittimi bloccati; throughput di lettura sotto ritiro.
- **Carico dell'operatore:** vedi 5.5.

### 5.5 Modello di carico dell'operatore (non è uno studio con utenti)
- Arrivi di candidati dalle catture (nel paper ~15,9 aggiunte per sito-giorno, picco 432).
- Tempo di decisione per candidato: distribuzione assunta (es. lognormale) con parametri dichiarati e analisi di sensitività.
- Output: lunghezza della coda, tempo di attesa, quota di candidati non revisionati entro un budget giornaliero; confronto tra politiche di selezione (unione, quorum, DIB, ranked).
- Dichiararlo come **modello**; limite esplicito: nessun dato da operatori reali.

### 5.6 Limiti da dichiarare
Scenario emulato; partizione dei dati sintetica; consorzio chiuso con appartenenza controllata; **privacy dell'evidenza condivisa** non affrontata (inventario di dispositivi esposto ai membri); governance del servizio di evidenza fuori ambito.

---

## 6. Autenticazione con certificato tra siti

### 6.1 Disegno minimo
- **mTLS in entrambe le direzioni:** sito → servizio di evidenza (osservazioni, dispute) ed evidenza → sito (fan-out, target pendenti).
- **L'identità viene dal certificato, non dal payload.** Identificatore di sito in un campo SAN (es. URI), mappato **lato server** su sito e ruolo; il ruolo non va messo nel certificato come unica fonte.
- **Ruoli separati:** sito membro, servizio di evidenza, amministratore del consorzio. Il ripristino globale è privilegiato e richiede un'identità distinta.
- **mTLS autentica il servizio, non l'operatore umano.** L'autenticazione dell'operatore locale (I1) resta un pezzo separato: dichiararlo.
- **Chiavi separate:** il certificato di trasporto è diverso da quello con cui il sito firma i MUD (stesso sito, due autorità).

### 6.2 Implementazione
- CA privata (es. step-ca), senza costruire una PKI completa; **certificati a vita breve** con rinnovo automatico (evita la gestione di CRL e risolve la revoca verso siti offline).
- Su FastAPI conviene terminare mTLS su un **reverse proxy** davanti al servizio, raggiungibile solo in locale, per evitare la falsificazione di header. Se invece si termina nel server ASGI, **verificare** come espone il certificato del peer (non confermato che uvicorn lo passi nello scope).
- Riferimenti: RFC 8446 (TLS 1.3), RFC 5280 (profilo X.509).

### 6.3 Effetti sul nucleo del paper
- Il quorum di "siti distinti" poggia su identità controllate dalla CA: l'emissione dei certificati diventa la difesa dalle identità fabbricate. Dirlo nei test Sybil.
- Un certificato rubato permette di aprire dispute a nome di quel sito ma **non** di creare autorizzazione locale: proprietà da **testare**, non da asserire (S8).
- Ingresso/uscita di membri (S3) = emissione/revoca di certificati.

### 6.4 Test
1. Funzionali: certificato valido, assente, CA sconosciuta, scaduto, revocato.
2. Autorizzazione: il sito A tenta commit sul sito B o ripristino globale: deve fallire.
3. Rieseguire l'oracolo di invarianti con autenticazione attiva.
4. Sovraccarico: latenza e throughput con e senza TLS, con riuso delle connessioni; rimisurare i fallimenti sulle connessioni in pool (oggi 6 su 64.400).

### 6.5 Modello formale
Aggiungere un attore autenticato alle azioni (solo il sito s può fare commit su s) e un avversario che è un sito compromesso con la propria identità ma non con le altre. Una **mutazione M7** che rimuove il controllo del chiamante mostra cosa difende l'autenticazione.

---

## 7. Esperimenti

### 7.1 Audit del codice (prima di tutto)
1. **Riprodurre i numeri esistenti** (regressione): script, seed, confronto con `claims.json`; etichettare un commit di riferimento.
2. **Mappa di tracciabilità** modello ↔ codice ↔ test: per ogni transizione e guardia di Table II (e per M1–M6) annotare azione TLA+, funzione nel codice, test che la copre. I buchi vanno chiusi prima di dichiarare "verificato".
3. Localizzare e leggere: logica delle transizioni, target pendente e numero di sequenza per fatto, fan-out (3 tentativi da 1 s), exporter MUD, livello database, harness degli esperimenti.
4. Annotare ciò che il codice fa e il paper non dice (e viceversa).

### 7.2 Strumentazione comune
- **Oracolo di invarianti online:** monitor indipendente che osserva gli eventi e controlla I1–I3 ed `Exportable` durante ogni esperimento; ogni violazione si registra.
- **Log strutturato** con timestamp monotoni per ogni evento (apertura dispute, fan-out, ricezione, applicazione, rimozione regola).
- **Harness parametrico:** una configurazione per esperimento (N, F, k, rete, seed), un solo comando, risultati tabellari.
- **Statistica:** ≥10 ripetizioni per le metriche di tempo (oggi 3–5), intervalli di confidenza bootstrap, seed dichiarati, hardware descritto.
- **Ipotesi dichiarate prima di lanciare** ogni esperimento (cosa ci si aspetta e cosa lo falsificherebbe).

### 7.3 Esperimento 1: baseline di riconciliazione (priorità massima)
- **Baseline:** B1 log degli eventi con tombstone e replay completo; B2 stato replicato con CRDT standard (2P-set/OR-set); B3 sovrascrittura LWW semplice senza origine della revoca.
- **Procedura:** le sei sequenze dell'ablation esistente + sequenze casuali (fuzz) per tutte le varianti; oracolo di invarianti come giudice.
- **Misure:** violazioni per variante; costo (byte, messaggi, tempo) in funzione di k ∈ {1, 2, 5, 10, 50} episodi saltati.
- **Ipotesi da testare, non da dare per scontate:** B1 corretto ma con costo crescente in k; B2/B3 violano I3 o il veto in alcune sequenze; il record collassato è corretto con costo ~costante per fatto. Se una ipotesi cade, il paper va riformulato.

### 7.4 Esperimento 2: firma MUD

**Verificato (fonti pubbliche, ottobre 2026):**
- RFC 8520 prevede una firma CMS **detached** in un file `.p7s` accanto al MUD (campo `mud-signature` nel MUD). Il campo va impostato **prima** di firmare, perché fa parte del contenuto firmato.
- Comandi standard: `openssl cms -sign ... -binary -outform DER -certfile <intermedio> -out file.p7s` e `openssl cms -verify -inform DER -content file.json -CAfile <root>`.
- NIST SP 1800-15 descrive il manager che scarica il MUD e il `.p7s` e li verifica.
- Il README di osMUD dice che i `.p7s` compaiono nella cartella dei MUD quando il processo scarica un file e che si installa un certificato CA intermedio (esempio con Let's Encrypt). Limiti noti: richiede il firewall OpenWrt, ignora le regole di movimento laterale, non gestisce LLDP né X.509.

**NON verificato (da controllare nel codice):**
- Dove e come osMUD valida la firma al commit `852918e` e quale opzione il vostro testbed disattiva. Cercare nel sorgente `p7s`, `verify`, `cms`, `openssl`, `CAfile`.
- Come installare una **CA privata** al posto di Let's Encrypt (inferenza dal README, non procedura documentata).
- Se osMUD scarica il MUD via HTTPS dal MUD URL: in tal caso l'exporter di ogni sito deve servire MUD e `.p7s` con una catena di cui osMUD si fida, e il testbed va adattato.
- Il README è molto vecchio (circa sette anni): non dare per scontato che descriva il commit usato.

**Procedura:**
- CA di prova, certificato di firma per sito (trust anchor installato nel manager), firma dei MUD esportati.
- Casi: firma valida (applicata); file manomesso (rifiutato); firmatario non autorizzato/CA sconosciuta (rifiutato); firma scaduta (rifiutato); `.p7s` mancante (comportamento da **documentare**).
- Misurare il sovraccarico sul percorso di export/applicazione.
- Strumenti: `openssl cms`; in alternativa la libreria Go `mudcerts` (`signmudfile`, `verifymudsig`).

### 7.5 Esperimento 3: rete realistica (S7)
- Emulare con `tc netem` profili: LAN (base), regionale (~20 ms, 0,1% perdita), WAN (~80 ms, 1%), degradata (~200 ms, 5%).
- Partizioni asimmetriche con regole di drop unidirezionali per la durata dell'episodio.
- Rieseguire S1/S2 e misurare tempo di ritiro e di riconciliazione, con e senza i tentativi del fan-out.

### 7.6 Esperimento 4: scalabilità
- **Fattori:** N ∈ {10, 20, 50, 100}; F ∈ {100, 1.000, 10.000}; k ∈ {1…50}; frazione di siti offline ∈ {10, 30, 50%}; numero di writer.
- **Strategie di propagazione:** fan-out sincrono (attuale), asincrono, pull con riconciliazione.
- **Tail:** ripetere le misure con un database con scritture concorrenti al posto di SQLite per verificare l'attribuzione del p99 (5,9 s) allo scrittore singolo.
- **Validità:** con 100 siti sullo stesso host i processi competono; usare limiti di CPU per sito e, se possibile, più macchine/VM; dichiarare il bias da co-locazione.
- **Tutti gli esperimenti successivi girano con mTLS attivo**, mantenendo un confronto con e senza TLS per isolarne il costo.

### 7.7 Esperimento 5: scenario completo (S1–S8)
Eseguire la federazione di N=20 siti con la configurazione 5.2, in sequenza e in combinazione, con oracolo attivo, autenticazione attiva e rete variabile; riportare le metriche di 5.4 per ogni evento.

### 7.8 Esperimento 6: score e eligibility
- Ablation C_s-only, C_t-only, combinata; sweep o eliminazione del 0,7/0,3.
- Eligibility più stretta (first/support/third party); costo in recall.
- Parte compatta: componente abilitante, non contributo principale.

### 7.9 Se il modello viene esteso (caso ibrido, versioning)
Prima aggiornare le transizioni e il modello TLA+, poi il codice, poi S4/S5. Ogni nuova transizione ha guardia, test, mutazione corrispondente e riga nella mappa di tracciabilità.

---

## 8. Specifico per TNSM

- Taglio gestionale: fattibilità operativa, integrazione con strumenti di gestione, scalabilità. Valorizzare l'aggancio con MUD/YANG e citare più lavori TNSM su policy e intent.
- Carico dell'operatore: almeno il modello di 5.5.
- Realismo di rete: WAN emulata attesa.
- Controllare il limite di pagine; se manca spazio, comprimere la selezione dei candidati.
- Stima onesta della versione attuale: rischio di **major revision**, con baseline mancante, valutazione sintetica e scarsa componente gestionale come motivi più probabili.

### Struttura target
1. Introduzione (esempio guida: federazione di edifici; REC come contesto)
2. Related work (tabella per fase del lifecycle)
3. Sistema, goal e threat model (G2 = evidenza ex ante + dispute ex post)
4. Lifecycle e proprietà (con motivazione di I1–I3)
5. Riconciliazione e verifica formale
6. Ammissione dell'evidenza (breve)
7. Implementazione (MUD firmati, mTLS)
8. Valutazione per domande di ricerca: correttezza, riconciliazione (vs baseline, WAN), scalabilità, autenticazione, carico dell'operatore, ammissione, scenario
9. Discussione e limiti
10. Conclusioni

### Contributi riordinati
1. Modello di lifecycle per policy MUD lato operatore con validità dell'approvazione e origine della revoca (completato con le estensioni decise).
2. Riconciliazione a target collassato, confrontata con log e CRDT, verificata formalmente.
3. Prototipo autenticato e firmato, valutato in uno scenario di federazione di edifici con WAN emulata, scalabilità e carico dell'operatore.
4. (Abilitante, compresso) ammissione dell'evidenza come guardiano più ranker.

---

## 9. Ordine di lavoro (minimizza i rifacimenti)

1. Decisioni di modello col supervisor (sezione 2).
2. Audit del codice e riproduzione dei risultati (7.1); oracolo e harness (7.2).
3. **Autenticazione con certificato** (sezione 6), prima delle misure di prestazione.
4. Estensione del modello formale e del prototipo (anche M7).
5. Baseline di riconciliazione (7.3); firma MUD (7.4); rete (7.5).
6. Scalabilità (7.6); scenario completo (7.7).
7. Riformulazione dello score con le ablation (7.8).
8. Stato dell'arte completo e riscrittura del related work (sezione 4).
9. Riscrittura di goal/threat model, valutazione, introduzione e abstract (per ultimi).
10. Pulizia finale; verifica che ogni claim abbia un esperimento.

---

## 10. Rischi, minacce alla validità, domande aperte

**Rischi**
- Allargare il lifecycle senza che le estensioni nascano da validità + origine: il paper si allarga senza diventare più forte.
- Novità dichiarata troppo in fretta (ricerca non sistematica).
- Scenario percepito come non realistico: dichiararlo emulato e parametrizzarlo con fonti.
- Spazio TNSM insufficiente.
- Le ipotesi sulle baseline potrebbero cadere: prevederlo.

**Minacce alla validità da scrivere nel paper**
- Scenario e partizione dei siti sintetici; sei tipi comuni di dispositivo.
- Modello formale a poche entità; scalabilità misurata solo sul prototipo.
- Co-locazione dei servizi sullo stesso host (se non si usano più macchine).
- Modello di carico dell'operatore senza dati reali.
- Consorzio chiuso; autenticazione dell'operatore e compromissione della CA fuori modello; privacy dell'evidenza non trattata.

**Domande aperte**
- Significato esatto di "active ricorsivo" e "provare al contrario".
- Quali sono i 6 tipi comuni e sono adatti a un contesto da edificio?
- Si includono il caso ibrido e il versioning?
- Quante risorse di calcolo sono disponibili (più macchine/VM)?
- Limite di pagine e scadenza TNSM?
