# Audit 31 — Pcap di `degraded`: risposte a Q1-Q8 (2026-10-11)

Domande e regole di decisione: audit 30 (committate prima di aprire un pcap, `89b3d88`). Strumento: `analyze_pcap.py` (solo intestazioni, payload mai letto né stampato; pure Python), uscite complete in `experiments_tnsm/m67_retraction/degraded_20261011/pcap_analysis_{D,C}.md` (solo conteggi). I pcap restano in `/root/Desktop/dib_pcap_20261011/`, fuori dalla repo, sha256 coincidenti con il nodo (audit 30 §0). B1 `degraded` **non lanciato**.

## 0. Difetti miei trovati nel primo giro, corretti e dichiarati (tutti dopo aver visto un output; le regole di decisione non sono cambiate)
1. **Identificazione degli indirizzi.** Il primo giro prendeva come "evidence" 172.19.0.1 (il gateway del bridge, cioè il generatore): Q1 non abbinava nulla e Q3-Q6 riguardavano il percorso generatore→evidence. **Quei risultati sono stati scartati.** Ora l'indirizzo dell'host catturato è quello presente in ogni pacchetto della cattura (evidence 172.19.0.2; site-0 172.19.0.11 in D, 172.19.0.8 in C). Test aggiunto.
2. **Regola della pausa di 100 ms nei voli** (audit 30 Q5) era disattivata nel codice (`and False`): riattivata come dichiarato.
3. **Q1 sui bordi:** la cattura di site-0 è partita dopo quella di evidence e finita prima; ora si confrontano i pacchetti **inviati** nella finestra comune (con 1 s di margine in coda); i ricevuti non si tagliano. Un mio test ha mostrato che tagliare anche i ricevuti creava non abbinati fittizi.
4. **Q3:** si contano solo intervalli < 10 s (stesso tentativo di connessione; oltre, riuso di porta).
5. Aggiunta una statistica non prevista: quota di trasmissioni ripetute lato mittente.
6. Un commit intermedio (`0b44767`/successivo) conteneva un test rotto (heredoc con `\\` letterali) e la pipeline con `tail` ne ha nascosto l'errore; riparato in `7803f5a`.

## 1. Risposte
**Q1 — lato della cattura: tap DOPO la qdisc, in tutte e 4 le combinazioni (braccio × direzione)** (regola: non abbinati ≲ 1% e Δ mediana < 20 ms).

| Braccio | Direzione | Inviati visti al mittente | Abbinati | Non abbinati (CP 95%) | Δ mediana (p05/p95) |
|---|---|---|---|---|---|
| D | evidence → site-0 | 485 | 485 | 0 [0; 0,76%] | 0,02 ms (0,01/0,08) |
| D | site-0 → evidence | 561 | 561 | 0 [0; 0,66%] | 0,03 ms (0,01/0,09) |
| C | evidence → site-0 | 843 | 843 | 0 [0; 0,44%] | 0,02 ms (0,01/0,06) |
| C | site-0 → evidence | 979 | 979 | 0 [0; 0,38%] | 0,02 ms (0,01/0,09) |

Il ritardo di 200 ms è già stato applicato quando il pacchetto compare al tap del mittente (Δ ≈ 20 µs fra i due namespace), e nessun pacchetto visto dal mittente manca al ricevitore: **il tap è dopo la qdisc**, come previsto dal sorgente del kernel (docstring di `run.py`, "TO CONFIRM"). Pacchetti visti al ricevitore e non al mittente (D: 5 e 23; C: 2 e 30): attesi ai bordi della cattura, non verificato caso per caso. Il lato della cattura è un risultato: **conseguenza dichiarata** (audit 30 §2): un pacchetto perso dalla qdisc non è visibile né al mittente né al ricevitore.

**Q2 — perdita osservabile: non calcolabile come pacchetti mancanti** (conseguenza di Q1). Non si dichiara la perdita misurata dai pcap; vale la misura indiretta dai tempi (Q6 e dati del driver, §2).

**Q3 — RTO iniziale 1 s (SYN ritrasmesso):** D n = 0 (0 SYN ritrasmessi su 233 connessioni evidence→sito); C n = 1, intervallo 1,001 s. Con n < 5 **non valutabile**; il valore del caso singolo è dentro [0,9; 1,1] s. Con il tap dopo la qdisc il primo SYN perso è invisibile al mittente, quindi il conteggio dei SYN ritrasmessi sottostima.

**Q4 — ritardo delle ritrasmissioni di segmenti di dati** (valori ripetuti seq+lunghezza, visti al mittente): D n = 2: 1,428 e 1,452 s; C n = 13: 0,397 0,399 0,404 0,620 1,020 1,053 1,054 1,054 1,120 1,215 1,226 1,230 2,415 s (in site-0 un valore: 1,02 s). Previsione registrata: PTO ≈ 0,8 s, attesa dopo una perdita singola ≈ 1,2 s. **Nessun valore vicino a 0,8 s**; compaiono tre valori ≈ 0,40 s, otto fra 1,02 e 1,23 s e uno a 2,4 s (campione piccolo, D n = 2). Si riporta, senza adattare la previsione e senza spiegare.

**Q5 — voli per connessione evidence→sito completata (server ha inviato payload):**

| Braccio | Connessioni (con SYN) / completate | Distribuzione dei voli | Mediana | Previsione n_c | Esito (regola: mediana fuori → falsificata) |
|---|---|---|---|---|---|
| D | 233 / 213 | 4: 193, 5: 20 | **4** | 4-5 | **non falsificata** |
| C | 273 / 255 | 4: 12, 5: 16, 6: 172, 7: 41, 8: 11, 9: 3 | **6** | 7-10 | **falsificata** (mediana sotto l'intervallo) |

Per C, il numero di voli misurato è 6, sotto la previsione 7-10. Attenzione alla definizione: i voli sono cambi di direzione di pacchetti non-ACK-puri e non-FIN/RST, con pausa > 100 ms che separa due voli; la previsione di audit 14 contava messaggi/attraversamenti per fase. La falsificazione vale per la regola dichiarata; non si adatta la previsione. Connessioni per consegna: D 233 per 200 consegne (+33), C 273 per 200 (+73): i tentativi in più sono nei dati del driver e nei ritiri; non si derivano dalle sole intestazioni.

**Q6 — fasi in timeout (evidence→sito):** SYN ritrasmessi (connect non completato entro il primo RTO, **visibili**): D 0/233, C 2/273; ma con il tap dopo la qdisc un SYN perso non è visibile, quindi **non è una misura della quota di connect in timeout** (previsione 2p ≈ 10%). Connessioni **senza payload dal server e chiuse dal client** (timeout visibili nelle fasi successive): D 20/233 (8,6%), C 18/273 (6,6%). Durata delle connessioni completate (mediana; eccessi sulla mediana in bin da 0,5 s): D mediana 1,204 s, 151 su 213 senza eccesso, 17 con +0,5 s, 37 con +1,0 s, 2 con +1,5, 5 con +2,0, 1 con +3,5; C mediana 1,609 s, 155 su 255 senza eccesso, 58 con +0,5, 29 con +1,0, 7 con +1,5, 4 con +2,0, 1 con +2,5 (e una durata di 384 s, riuso di porta).

**Q7 — copertura:** le due catture coprono le finestre del driver (evidence: D 1791712134,7-1791712525,7 contro la finestra 157,5-520,2; C 691,0-3270,4 contro 721,1-3265,8; site-0 parte 16 s e 23 s dopo evidence). Dati del driver `tcpdump/cells.jsonl`: 20 episodi per braccio, 0 esclusi, 200 consegne attese per braccio; in evidence: 233 (D) e 273 (C) connessioni evidence→sito.

**Q8 — completezza:** nessun indizio di vuoti (ACK di byte mai visti: 0/15669 e 0/963 per D, 0/27604 e 0/1704 per C); il conteggio dei pacchetti scartati dal kernel non è disponibile (limite dichiarato).

## 2. Dati del driver del blocco `tcpdump` per contesto (descrittivi; il blocco `tcpdump` NON entra nei conteggi di (c))
Per consegna (FANOUT 1, 20 episodi × 10 siti = 200 consegne per braccio; tempo per consegna = differenza fra i ritiri consecutivi dei siti): base D 0,804 s, C 1,209 s (= n_RTT·R con R = 0,4 s); consegne con eccesso ≥ 0,25 s sulla base: D 63/200 (31,5%), C 100/200 (50%) (eccessi in bin da 0,5 s: D 0,5: 13, 1,0: 19, 1,5: 3, 2,0: 9, 2,5: 6, 3,0: 1, 4,0: 2; C 0,5: 20, 1,0: 9, 1,5: 8, 2,0: 10, 2,5: 5, 3,0: 6, 3,5: 1, 7,0: 1). Mediana dell'ultimo sito: D 11,356 s, C 17,104 s (previste senza perdite: 8,0 e 12,0 s). Consegne in pending dal log di evidence: **D 2/200 (0,010), C 6/200 (0,030)**; queste cadono dentro gli intervalli previsti di (c) a `degraded` (D 0,0063-0,0115; C 0,028-0,064), ma sono campioni da 200 consegne (non il conteggio di (c), che è B1) e non cambiano la regola.

## 3. Cosa ne segue e cosa decide l'utente (nulla modificato)
- **Lato della cattura (Q1):** tap dopo la qdisc: si congela (come richiesto dal docstring) solo con l'OK dell'utente; la perdita non è misurabile dai pcap, solo dai tempi.
- **(c) a `degraded` è condizionale alla cattura** (audit 14): l'intervallo di C dipende da n_c = 7-10, e la misura dà 6 voli (falsificata, secondo la regola dichiarata); a D la previsione n_c è confermata. Se e come ricongelare gli intervalli di (c) è una decisione dell'utente **prima di B1**; la mia raccomandazione è non modificarli, lasciare che B1 (50 episodi per cella) faccia da test confermativo con gli intervalli registrati e riportare n_c = 6 per C come risultato.
- **B1 `degraded` non lanciato:** aspetto l'OK dell'utente, che include la verifica con `netem_show.sh` della calibrazione (non ricevuta) e la scelta su (c).
