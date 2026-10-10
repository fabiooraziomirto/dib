# Audit 10 — Dataset per simulare federazioni di siti in DIB (ricerca del 10 ottobre 2026)

Scopo: trovare dati pubblici (o ottenibili su richiesta) che permettano di simulare più siti, più tipi di dispositivo, traffico malevolo reale e ground truth MUD per gli esperimenti di DIB (TNSM).
Metodo: ho letto le pagine ufficiali dei dataset e gli articoli collegati. **Non ho scaricato né ispezionato nessun dataset.** Dove una pagina non dice una cosa, scrivo "non dichiarato": non l'ho dedotta. Le pagine di Mon(IoT)r IMC23 (parte descrittiva) e UNSW HomeNet (ScienceDirect) erano bloccate o incomplete: HomeNet è elencato solo come candidato non verificato.

## 1. Risultato in breve

1. **Non esiste un dataset pubblico con molti siti indipendenti, gli stessi tipi di dispositivo e traffico malevolo reale.** Per simulare la federazione bisogna combinare corpora diversi, come già fa la repo con UNSW, Mon(IoT)r e YourThings.
2. **Il collo di bottiglia è la sovrapposizione dei tipi tra siti, non il numero di dataset.** Nel paper (riga 622) solo sei tipi sono comuni ai tre dataset; in `analysis_fs/REPORT.md` §4 il numero mediano di siti onesti per tipo (h_d) è 1–2 con Mon(IoT)r. Con la condizione K < 5h/7 e f_s = 0.30, servono h ≥ 3 siti onesti per tollerare 1 colluder, h ≥ 5 per 2, h ≥ 7 per 3.
3. **La fonte più utile che non avete ancora usato è la raccolta di sette dataset di Ahmed et al. (PETS 2022)**: 188 istanze, 120 make-and-model, sette siti in US, UK e Australia. Contiene già YourThings, UNSW e Mon(IoT)r, quindi l'aggiunta netta sono i dataset NCSU, PingPong e HomeSnitch.
4. **Per la scala reale dei siti (migliaia) l'unica fonte è IoT Inspector** (>63.000 device, ~6.400 utenti), ma contiene solo metadati aggregati e l'accesso passa da una richiesta. I dati Avast di Kumar et al. (500.7K case in un giorno) non sono pubblici.
5. **Per l'A1 (traffico malevolo reale)**: IoT-23 è l'unico con dispositivi reali e traffico benigno e malevolo etichettato a flusso, con pcap. N-BaIoT è inutilizzabile per i fatti di endpoint (solo feature, niente peer e porte).
6. **Per scalare e variare la prevalenza di infezione** il generatore più adatto è GothX (configurabile la percentuale di sensori compromessi).

## 2. Cosa serve a DIB

| ID | Requisito | Perché |
|---|---|---|
| R1 | Molti siti che osservano lo stesso tipo di dispositivo (h_d alto) | Garanzia di Criterion 1 per tipo, quorum m = 2 |
| R2 | Stesso make-and-model in ambienti diversi | C_s = \|S_de\| / \|ES_d\| ha senso solo con tipi condivisi |
| R3 | Finestre lunghe (giorni) | C_t usa la copertura giornaliera |
| R4 | Nomi (FQDN, SNI) oltre agli IP | I fatti di endpoint sono (tipo, direzione, protocollo, peer, porta) |
| R5 | Traffico malevolo reale e etichettato | A1: l'evidenza è vera ma proviene da un device compromesso |
| R6 | Ground truth MUD | Recall e precisione dei candidati |
| R7 | Rete e carico controllabili | Latenza, throughput, WAN, TNSM |

## 3. Schede dei dataset

Convenzione: "già usato" = presente in `docs/data_provenance.md`.

### A. Traffico benigno da più ambienti (R1–R4)

| Dataset | Contenuto verificato | Ambienti | Accesso e licenza | Uso per DIB | Limiti |
|---|---|---|---|---|---|
| **UNSW-IoTraffic** (già usato) | 27 device, 203 giorni (set 2016–apr 2017), 95,5 M pacchetti (26,9 GB), 4,9 M flussi; PCAP e CSV per device, parametri di protocollo | Un laboratorio UNSW | Dryad, DOI 10.5061/dryad.w0vt4b94b. Articolo CC BY 4.0; licenza dati separata non dichiarata | R3 (finestre lunghe), R4 | Un solo sito; 2016; 14 lacune di cattura (~869 h); IP e MAC non anonimizzati; attività sparsa |
| **Mon(IoT)r IMC 2019** (già usato) | 34.586 esperimenti controllati + 112 h di idle; PCAP con solo header | Northeastern e Imperial College (anche con egress VPN) | Richiesta e data sharing agreement dalla pagina del paper | R1, R2 (due laboratori) | Numero di device non dichiarato nel README; dati riservati: niente ridistribuzione |
| **Mon(IoT)r IMC 2023** (traffico locale) | Traffico locale smart home, honeypot, scansioni | Non dichiarato | Email a moniotr@ccs.neu.edu; licenza non commerciale, dati riservati | Non prioritario: traffico locale, non verso il cloud | Descrizione incompleta sulla pagina |
| **YourThings** (già usato, solo 40 PCAP) | PCAP di ~10–13 GB al giorno (20, 21, 28 mar 2018 e 10–19 apr 2018), mapping device→IP | Un ambiente | Archivi .tgz su Dropbox; nessuna licenza, citare due paper | R2 | Dichiarato nel repo: solo un sottoinsieme usato |
| **NCSU IoT-Lab 2020 e 2021** | 8,2 GB e 4,3 GB, `device_mappings.csv`; campione da 476 MB | Laboratorio NCSU, due anni diversi | Download diretto da privacy-datahub.csc.ncsu.edu | R1, R2: due raccolte dello stesso laboratorio possono fare da due siti | Setup, durata, formato interno e licenza non dichiarati |
| **Raccolta di Ahmed et al.** (PETS 2022) | 188 istanze, 120 make-and-model, 7 dataset, siti in US, UK e Australia | 7 siti (laboratori) | Repo `dilawer11/iot-device-fingerprinting`: dati scaricabili da Docker o dalle fonti; HomeSnitch su richiesta. Struttura attesa: `datasets/<nome>/RAW` + `device_mappings.csv` | **Miglior candidato per R1/R2 con dati reali multi-sito** | Quanti make-and-model sono davvero condivisi tra i siti non è riportato: va misurato |
| **PingPong** (NDSS 2020) | 22 device; PCAP su wlan1 ed eth0 del router; timestamp degli eventi; esperimenti standalone e smarthome | Un laboratorio UCI | Form di richiesta; licenza non commerciale, non condivisibile | Attività etichettata per evento | Pochi device; accesso con restrizioni |
| **IoT Sentinel / Aalto** | 31 device, 27 tipi; setup ripetuto ≥ 20 volte da persone diverse; 25,4 MB | Un laboratorio | Download diretto; licenza "Unspecified", diritti riservati anche per text-and-data mining | Variabilità tra ripetizioni dello stesso device | Solo fase di setup; 2016; i diritti riservati vanno verificati prima dell'uso |
| **CIC IoT Dataset 2022** | Classi audio, camera, home automation; esperimenti power, idle, interazioni, scenari e attivo; idle e attivo su 30 giorni | Un laboratorio UNB | cicresearch.ca; licenza non dichiarata | R3 (30 giorni) | Lista dei device non sulla pagina |
| **GHOST-IoT** | Una smart home reale, sei interfacce (Ethernet, Wi-Fi, PPP, Bluetooth, RF869, Zigbee), 12 CSV | Una casa | `data.rar` su GitHub; disponibilità dichiarata dopo la pubblicazione del paper | Casa reale con anomalie provocate | Modelli, durata e licenza non dichiarati |
| **DATA16 / DATA25** (arXiv 2601.19315) | DATA16: 60 giorni, ~3,1 M flussi, 19 tipi. DATA25v1: 57 giorni, ~7,7 M flussi, 18 tipi. DATA25v2: ambiente universitario separato, ~8,8 M flussi, 10 tipi condivisi con v1 | Testbed domestico e laboratorio/campus | DATA16 su Dryad. DATA25 solo "sarà rilasciato" | Prova diretta che gli stessi tipi si comportano diversamente tra ambienti | DATA25 non ancora scaricabile |
| **UNSW HomeNet** (2025) | Titolo: "network traffic flow dataset for AI-based smart home device classification" | **Non verificato** | Non verificato | Da controllare a mano | Pagina bloccata ai miei strumenti |

### B. Scala reale dei siti

| Dataset | Contenuto verificato | Accesso | Uso | Limiti |
|---|---|---|---|---|
| **IoT Inspector** | Da aprile 2019 a giugno 2022: >63.000 device, ~6.400 utenti. Metadati aggregati a finestre di 5 s: IP remoti, hostname, porte; nomi e produttori per circa un quarto dei device | Richiesta tramite la pagina FAQ per ricercatori; il processo non è descritto; esiste un campione | Stima realistica di N, h_d e della sovrapposizione degli endpoint tra case | Niente pcap; etichette incoerenti o errate (documentato dagli autori); unità = casa, non organizzazione |
| **WiFi Inspector / Avast** (in Kumar et al.) | 500,7 K case in un giorno | **Non pubblico** | Solo come ordine di grandezza | — |

### C. Traffico malevolo (A1)

| Dataset | Contenuto verificato | Accesso e licenza | Uso | Limiti |
|---|---|---|---|---|
| **IoT-23** | 23 catture: 20 malevole, 3 benigne con device reali (Philips Hue, Amazon Echo, Somfy). Famiglie: Mirai, Torii, Okiru, Hajime e altre. Full ~21 GB, versione leggera ~8,8 GB. Etichette a flusso (`conn.log.labeled`) | Stratosphere Lab; licenza non dichiarata sulla pagina | **A1 con device reali**: fatti di endpoint veri provenienti da device infetti | Solo tre tipi di device benigni; i device infetti non sono tutti identificati per tipo |
| **UNSW IoT attack traces** (SOSR 2019, già nel repo) | Flussi + annotazioni (inizio, fine, categoria MUD, etichetta) + `attackinfo.xlsx` | MIT-0 (gruppo UNSW) | Già usato per A1 | Il repo segnala la mancanza delle annotazioni a livello di pacchetto (`BLOCKER.md`); il link ai PCAP non è sulla pagina |
| **CICIoT2023** e **CIC IoT-DIAD 2024** | 105 device; 33 attacchi in 7 categorie, eseguiti da device malevoli verso altri device; PCAP e CSV | cicresearch.ca; licenza non dichiarata | Attacchi tra device in un'unica topologia | Un solo laboratorio; l'identificazione per tipo non è sulla pagina |
| **N-BaIoT** | 9 device realmente infettati da Mirai e BASHLITE; 7.062.606 istanze; **solo feature statistiche** | CC BY 4.0 | Nessuno per DIB | Senza peer e porte non si costruiscono fatti di endpoint |
| **Bot-IoT** | >72 M record; PCAP 69,3 GB, CSV 16,7 GB | Gratuito per uso accademico | Volume di attacchi | La pagina non dice se i device sono reali o simulati |
| **ToN_IoT** | Testbed Industry 4.0 a tre livelli, >10 sensori; rete (PCAP, Zeek), telemetria, OS; DoS, DDoS, ransomware | Gratuito per uso accademico | Scenario IIoT | Poco rilevante per MUD consumer |

### D. Ground truth MUD

| Risorsa | Contenuto | Note |
|---|---|---|
| **UNSW MUD profiles** (già usato) | 28 device, profili RFC 8520 generati con MUDgee; licenza MIT-0 | Pagina senza link diretto; strumento su GitHub (`ayyoob/mudgee`) |
| **MUD-PD (NIST)**, **Cisco DevNet MUD** | Strumenti per generare allowlist MUD | Non sono dataset |
| **SoK "Beyond IoT MUD Deployments"** | Nessun dato di diffusione dei file MUD e nessun repository pubblico | Conferma che il ground truth reale è scarso |

### E. Generatori e testbed (R7, A1 parametrico)

| Risorsa | Contenuto | Note |
|---|---|---|
| **Gotham dataset** (Zenodo 14502760) | 78 device virtualizzati, smart city simulata, 23,8 GB, PCAP + CSV, metadati di etichettatura; CC BY 4.0; tracce per device (non-IID) | Dati sintetici; durata e numero di siti non dichiarati |
| **GothX** | Generatore: sensori configurabili, **percentuale di sensori compromessi**, forza degli attacchi; test con 450 sensori simulati (498 nodi Docker, ~20,4 GB RAM); output PCAP + CICFlowMeter + etichette per flusso | Repo `fukuda-lab/GothX`; licenza da verificare; multi-sito non descritto esplicitamente |
| **IoT-Flock, STGen** | Frameworks di generazione di traffico (solo titoli verificati) | Da valutare |

## 4. Mappa requisiti → fonti

| Requisito | Meglio | In aggiunta |
|---|---|---|
| R1/R2: stessi tipi in più siti | Raccolta PETS 2022 (7 siti), NCSU 2020/2021 come due siti, Mon(IoT)r US/UK | DATA16/DATA25 se rilasciato |
| R1 su scala reale | IoT Inspector (metadati) | — |
| R3: finestre lunghe | UNSW-IoTraffic (203 giorni), DATA16 (60), CIC 2022 (30) | YourThings (10 giorni) |
| R4: nomi | Quelli dove l'enrichment FQDN funziona (UNSW, Mon(IoT)r) | PCAP con TLS/HTTP/DNS |
| R5: A1 reale | IoT-23 | CICIoT2023, UNSW attack, GothX per sweep sulla prevalenza |
| R6: ground truth | UNSW MUD profiles | MUDgee su altri PCAP (ground truth derivato, non del produttore) |
| R7: rete e carico | GothX/Gotham per N grande | `tc netem` sul testbed OpenWrt (piano §7.5) |

## 5. Simulazioni proposte (ipotesi da dichiarare prima di eseguire)

1. **Distribuzione di h_d sui dati reali.** Per ogni tipo, numero di siti che lo osservano nei 7 dataset PETS + UNSW. *Attesa:* pochi tipi con h ≥ 5. *Falsificata se:* la maggioranza dei tipi supera h = 5. Output: tabella dei tipi che soddisfano K < 5h/7 per K = 1, 2, 3.
2. **Prevalenza di infezione parametrica.** GothX con percentuale di compromessi p ∈ {1%, 5%, 10%, 30%} e N ∈ {10, 20, 50}; frequenza di fallimento della guardia da confrontare con `fs_binomial.csv`. *Attesa:* in accordo con la binomiale a siti indipendenti, peggiore con correlazione per firmware condiviso.
3. **Fatti A1 con IoT-23.** Fatti di endpoint estratti dalle tre catture benigne e dalle 20 malevole; misura di quanti passano l'ammissione a k siti. Risolve in parte il blocco delle annotazioni UNSW.
4. **Casa come sito, con IoT Inspector (se ottenuto).** Distribuzione di C_s per endpoint sui device etichettati; stima della quota di endpoint che superano 5/12 con N reale.
5. **Latenza e throughput sotto rete degradata.** Già pianificato in `docs/work/DIB_piano_completo.md` §7.5–7.6 (≥ 10 ripetizioni, mTLS, `tc netem`).

## 6. Licenze e cautele

- La repo è pubblica: **non committare dati** di Mon(IoT)r, PingPong o altri con data sharing agreement (non ridistribuibili, dati riservati). Meglio solo evidenze aggregate, dopo verifica della licenza.
- Molte pagine non dichiarano la licenza (IoT-23, CIC IoT 2022 e 2023, GHOST, NCSU, YourThings): da chiedere o verificare prima di ridistribuire derivati.
- Dati del 2016–2018: nomi e protocolli sono cambiati (ECH, DNS cifrato); il paper lo dichiara già nella Discussion.
- Etichette dei device: IoT Inspector e IoT-23 hanno limiti di etichettatura documentati dagli autori.

## 7. Prossimi passi, in ordine

1. Scaricare la raccolta PETS 2022 (campione da 476 MB) e misurare h_d (simulazione 1).
2. Inviare la richiesta per IoT Inspector (FAQ del progetto) e, se serve, per Mon(IoT)r IMC23.
3. Scaricare IoT-23 (versione leggera da 8,8 GB) per l'A1 (simulazione 3).
4. Provare GothX su una macchina con almeno ~20 GB di RAM (simulazione 2).
5. Verificare a mano UNSW HomeNet e le licenze mancanti.

## Fonti

- UNSW-IoTraffic: https://www2.ee.unsw.edu.au/~hhabibi/pubs/jrnl/25unsw-iotraffic.pdf
- Mon(IoT)r IMC19 (README): https://github.com/NEU-SNS/intl-iot
- Mon(IoT)r IMC23: https://moniotrlab.khoury.northeastern.edu/iot-local-dataset-imc23/
- YourThings: https://yourthings.info/data/
- NCSU IoT-Lab: https://privacy-datahub.csc.ncsu.edu/publication/ahmed-pets-2021/
- Ahmed et al., PETS 2022: https://petsymposium.org/popets/2022/popets-2022-0057.pdf e https://github.com/dilawer11/iot-device-fingerprinting
- PingPong: https://athinagroup.eng.uci.edu/projects/pingpong/data/
- IoT Sentinel (Aalto): https://research.aalto.fi/en/datasets/iot-devices-captures/
- CIC IoT 2022: https://www.unb.ca/cic/datasets/iotdataset-2022.html
- CICIoT2023: https://www.unb.ca/cic/datasets/iotdataset-2023.html
- CIC IoT-DIAD 2024: https://unb.ca/cic/datasets/iot-diad-2024.html
- GHOST-IoT: https://github.com/gspathoulas/ghost-iot-dataset
- DATA16/DATA25: https://arxiv.org/html/2601.19315
- UNSW HomeNet: https://www.sciencedirect.com/science/article/pii/S0360835225001871 (non verificato)
- IoT Inspector: https://www.usenix.org/publications/loginonline/three-years-crowdsourcing-smart-home-network-traffic
- IoT-23: https://www.stratosphereips.org/datasets-iot23
- UNSW attack traces: https://iotanalytics.unsw.edu.au/attack-data.html
- N-BaIoT: https://archive.ics.uci.edu/dataset/442/detection+of+iot+botnet+attacks+n+baiot
- Bot-IoT: https://research.unsw.edu.au/projects/bot-iot-dataset
- ToN_IoT: https://research.unsw.edu.au/projects/toniot-datasets
- UNSW MUD profiles: https://iotanalytics.unsw.edu.au/mudprofiles.html
- SoK Beyond IoT MUD Deployments: https://arxiv.org/pdf/2004.08003
- Gotham dataset: https://zenodo.org/records/14502760
- GothX: https://arxiv.org/html/2407.07456v2
- Kumar et al., USENIX Security 2019 (dati Avast): fornito da te
