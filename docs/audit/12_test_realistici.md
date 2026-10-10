# Audit 12 — Test più realistici per TNSM (solo proposta, nulla eseguito)

Data: 2026-10-10. Branch `revision-tnsm`. Fonti: `docs/work/DIB_piano_completo.md` §5.2–5.6 e §7; `docs/audit/10_dataset_survey.md`; `docs/audit/11_hd_distribution.md`; `docs/audit/04_piano_misure_tnsm.md`; `docs/audit/13_mtls_design.md`. **Nessun esperimento e nessun download.** Ogni voce richiede il tuo OK prima dell'esecuzione. Ipotesi e criterio di falsificazione vanno nel docstring prima del lancio.

## 1. Punto di partenza (dai dati, audit 11)

- Con i dati reali sul disco ci sono **al più 4 siti indipendenti** (5 con NCSU). 87 tipi su 119 hanno h = 1. K = 2 a f_s = 0,30 è coperto su 0–2 tipi.
- **Nessun corpus pubblico dà una federazione con molti siti e gli stessi tipi.** Una federazione realistica per TNSM deve quindi essere **sintetica**, con assunzioni dichiarate, e ancorata ai dati reali dove possibile.
- IoT Inspector, l'unica fonte con molte case, **esce dal percorso critico** (decisione utente: nessuna risposta da due mesi). Verifica di oggi, in sola lettura:
  - la pagina Mon(IoT)r IMC23 rimanda per "IoT Inspector dataset" al repository `https://github.com/Android-Observatory/IoT-LAN`;
  - il repository **non contiene i dati**: il README indica di contattare il team tramite `https://iotinspector.org/`, che chiederà prima l'approvazione dell'IRB della NYU, e potrebbe servire anche quella del vostro IRB, perché i dati possono contenere contenuti sensibili degli utenti;
  - nessuna licenza dichiarata, né per il repo (nessun file LICENSE) né per i dati; dimensione non indicata;
  - nessun download fatto.

## 2. Federazione sintetica (proposta principale)

**Scopo.** Rispondere a "funziona con N siti realistici?" senza fingere che i dati reali lo mostrino. Ogni parametro è un'assunzione esplicita, e ogni risultato si riporta come curva sullo sweep, non come numero singolo.

**Generatore.** Uno script nuovo, `experiments_tnsm/synthetic_federation/generate.py`, deterministico con seed. Riusa `dib.simulator.sites` (`partition_observations` con le strategie `random`, `device_balanced`, `time_window`; `apply_synthetic_site_overlap`) e le osservazioni reali (UNSW `observations_enriched.csv`, Mon(IoT)r e YourThings) come **comportamento per tipo**. Solo la loro distribuzione sui siti è sintetica.

| Assunzione | Valore base (piano §5.2) | Sweep | Ancoraggio ai dati |
|---|---|---|---|
| N siti | 20 | 10, 20, 50, 100 | — (fino a 5 indipendenti reali) |
| Presenza di un tipo (frazione dei siti che lo hanno) | 0,4 | 0,2; 0,4; 0,6; 0,8; più un punto **"ancorato"** che riproduce l'istogramma reale di h_d (audit 11, `hd_union_histogram.csv`) | audit 11 |
| Concentrazione degli endpoint cloud per vendor | Zipf con s = 1,0 | s ∈ {0,8; 1,0; 1,2} | da stimare sulle frequenze degli FQDN per vendor in UNSW e Mon(IoT)r (dato derivato non committato per Mon(IoT)r) |
| Gruppi organizzativi | 4 | — | — |
| f_s (siti malevoli per tipo) | 0,30 | 0; 0,1; 0,2; 0,3; 0,4; 0,5 | — |
| Divergenza locale (endpoint legittimi solo in un sito) | 5% degli endpoint per sito | 0, 5, 15% | — |
| Correlazione fra siti (firmware o cloud condivisi) | indipendenti | ρ_corr ∈ {0; 0,3} | serve a testare l'ipotesi H1 di `fs_binomial.py` |

**Metriche.**
- Ammissione: recall e precisione rispetto ai profili MUD UNSW (`data/unsw/profiles`), solo per i tipi UNSW.
- Frequenza con cui la guardia fallisce, confrontata con `analysis_fs/out/fs_binomial.csv`.
- Quota di tipi coperti per K = 1, 2, 3 (regola H', audit 11 sez. 1).
- Carico dell'operatore (piano §5.5, solo come modello).

**Ipotesi (bozza).** (i) La frequenza osservata di fallimento della guardia con siti indipendenti cade nell'IC binomiale di `fs_binomial.csv`. *Falsificata se* è fuori dall'IC al 95% per qualche (N, q). (ii) Con ρ_corr = 0,3 la coda è più pesante della binomiale. *Falsificata se* non lo è.

**Costo:** ~2–3 giorni di codice (generatore, Zipf, correlazione) più minuti o ore di calcolo in-process. **Dipendenze:** nessuna nuova. **Rischio:** il realismo dipende interamente dalle assunzioni; l'ancoraggio ad h_d reale ne limita l'arbitrarietà solo in parte. Il paper deve chiamarlo "emulato e illustrativo" (piano §5.1, §5.6).

## 3. Eventi S1–S8: cosa si può fare ora e cosa no

Legenda: **ora** = con il codice e i dati nella repo, in-process o con il Docker locale; **codice** = serve codice nuovo; **dati** = servono dati nuovi.

| Evento | Si può eseguire con | Manca | Costo | Dipendenze | Rischio |
|---|---|---|---|---|---|
| **S1** compromissione del cloud di un vendor (dispute + conferma, ritiro coordinato) | **ora:** `code/scripts/v35_lifecycle_experiment.py` (in-process, `TestClient`), `fault_injection_experiment.py` (Docker, scenari `dispute_open` e `dispute_confirm`) | **codice:** tempo di ritiro p50/p95/max per sito con timestamp monotoni (M6, audit 04) | ½–1 giorno | Docker (locale o nodo libero) | basso |
| **S2** dispute → conferma → restore con k siti offline e veti locali | **ora:** `offline_veto_reconciliation.py`, `v36_restore_ablation.py`, `reconcile_race_experiment.py`, `fault_injection_experiment.py` (scenario composto) | **codice:** sweep k ∈ {1, 2, 5, 10, 50} con costo in messaggi e byte; oracolo I1–I3 online (piano §7.2) | 1–2 giorni | Docker | medio: richiede la rigenerazione unica dopo mTLS (G0b) |
| **S3** ingresso e uscita di membri durante un episodio | — | **codice:** il prototipo ha N fisso nel compose (`generate_compose.py`), nessun join o leave a runtime; con mTLS = emissione e revoca di un certificato più una riga di mappatura (audit 13 §3.5) | 2–3 giorni | mTLS approvato | medio: tocca il denominatore di C_s, va legato alla proposta ES_d (audit 13 §3.2) |
| **S4** cambio di firmware (cambia l'insieme di endpoint) | **parziale, ora:** `dib.experiments.firmware`, `drift` e `nonstationarity_drift_sweep.py` lato score | **modello:** versioning nel lifecycle, solo se incluso (piano §7.9); **dati:** catture prima e dopo un aggiornamento (`data/testbed/firmware_update/` è vuota) | 1 giorno (solo score) | — | alto se si vuole il lifecycle: richiede di estendere il modello |
| **S5** compare un MUD del produttore (caso ibrido, deny-overrides) | — | **modello e codice:** non previsto dalle transizioni attuali | — | decisione sul modello | fuori ambito finché il modello non cambia |
| **S6** disputer malevolo, dispute ripetute | **ora:** `dispute_flood.py` (Docker, 10 siti; `results/dispute_flood/`) | **codice:** con mTLS il limite e l'attribuzione diventano per identità certificata (T9, T10 in audit 13); oggi l'identità è un input fidato | ½ giorno dopo mTLS | mTLS | basso |
| **S7** rete degradata durante S1 e S2 | — | **codice:** M6 e M7 (audit 04); **infrastruttura:** servizi sul nodo libero, generatore su questo host, netem solo sul nodo libero (G3) | 1–2 giorni più ~1,5 h di misura | nodo libero accessibile e caratterizzato; netem verificato | medio: la LAN fra i due nodi ha RTT di 0,25 ms (`ping`), quindi la WAN è solo emulata; il bias di emulazione va dichiarato |
| **S8** sito con certificato rubato | — | **codice:** mTLS (audit 13, T14) | incluso nei test di mTLS | mTLS approvato, risposta a Q1 (certificato operatore separato) | basso |

**Scenario completo (piano §7.7).** S1, S2, S6, S7 e S8 in sequenza sulla federazione sintetica (sez. 2) con N = 20, mTLS attivo, oracolo attivo e rete variabile. Possibile solo dopo mTLS, M6/M7 e il generatore.

## 4. A1 e prevalenza di infezione

### 4.1 IoT-23 (A1 con dispositivi reali)

- **Cosa dà** (survey §3.C): 23 catture, 20 malevole (Mirai, Torii, Okiru, Hajime e altre) e 3 benigne con dispositivi reali (Philips Hue, Amazon Echo, Somfy). Etichette per flusso in `conn.log.labeled` (Zeek).
- **Buco che colma.** Oggi l'A1 usa le tracce di attacco UNSW (`data/unsw_attack_2018/`, 14 MB), senza annotazioni a livello di pacchetto (`/root/Desktop/DIB_reframe/reproducibility/experiments/06_synthetic_a1_blocked/BLOCKER.md`, fuori repo; citato anche in `docs/data_provenance.md`). IoT-23 dà fatti di endpoint **veri** (peer, porta, protocollo) prodotti da dispositivi infetti.
- **Uso.** Un adapter nuovo `conn.log.labeled` → `Observation` (endpoint = `id.resp_h`/`id.resp_p`, protocollo, timestamp; il tipo dalla cattura). Poi si iniettano i fatti malevoli come evidenza A1 di k siti nella federazione sintetica e si misura quanti passano l'ammissione.
- **Costo:** download della versione leggera **~8,8 GB** (fuori dalla repo; dimensione e licenza da confermare prima, la survey dice "licenza non dichiarata"), adapter ~1 giorno.
- **Rischio:** solo 3 tipi benigni, che si allineano con `philips-hue` e `amazon-echo` (h_indep 4 e 2, audit 11); i dispositivi infetti non sono tutti identificati per tipo; catture di laboratorio con malware avviato a mano. Disco: 35 GB liberi su questo host.

### 4.2 GothX (prevalenza di infezione parametrica)

- **Cosa dà** (survey §3.E): un generatore con percentuale configurabile di sensori compromessi, intensità degli attacchi, output PCAP più etichette per flusso. Testato con 450 sensori (498 nodi Docker, **~20,4 GB di RAM**).
- **Buco che colma.** Verificare `fs_binomial.py` (H1 indipendenza, H3 dalla prevalenza per dispositivo p a quella per sito q) con p ∈ {1%, 5%, 10%, 30%} e N ∈ {10, 20, 50} (survey §5.2).
- **Costo:** clonare il repo (licenza da verificare), container Docker, esecuzione di ore. Va sul **nodo libero**, se ha la RAM (da caratterizzare), non su questo host.
- **Rischio:** smart city simulata, non dispositivi consumer MUD; multi-sito non descritto esplicitamente. Serve solo per la statistica della guardia, non per il realismo degli endpoint.

### 4.3 IoT Inspector (solo opzione)

Se arrivassero i dati: case come siti, N reale e distribuzione di C_s per endpoint (survey §5.4), con il gate esistente `code/scripts/prepare_iot_inspector_conditional.py` (campi `home_id`, `device_id`, `timestamp`, `hostname`, `port`, `protocol`, `vendor`, `product`). Requisiti: IRB della NYU e licenza (sez. 1). Non è nel percorso critico.

## 5. Ordine proposto

1. Generatore della federazione sintetica (sez. 2): nessuna dipendenza, sblocca tutto il resto.
2. S1, S2 e S6 in-process e con il Docker locale, con quanto esiste (rigenerazione esclusa finché non c'è G0b).
3. mTLS (dopo l'OK su audit 13), poi S3, S6 per identità, S8.
4. Nodo libero caratterizzato e netem verificato (G3), poi S7 con M6 e M7.
5. IoT-23 (dopo l'OK sul download), poi A1 sulla federazione sintetica.
6. GothX sul nodo libero (dopo l'OK e se la RAM basta).
7. Scenario completo (piano §7.7).

## 6. Cosa serve da te

- OK sul generatore sintetico e sui suoi valori base e sweep (sez. 2).
- Accesso SSH al nodo libero (audit 04 §7.2) per S7 e GothX.
- OK al download di IoT-23 leggero (~8,8 GB, licenza da verificare) e al clone di GothX.
- Decisione su S4 e S5 (estensione del modello: oggi esclusi).

## 7. Aggiornamento (decisioni utente, 2026-10-10)

**GothX: clonato, non eseguito.**
- Comando: `git clone --depth 1 https://github.com/fukuda-lab/GothX.git /root/Desktop/DIB/external_src/GothX` (fuori dalla repo); commit `004f5853fdad9dc692c0bba539a9bd58d6fc3dd4` del 16 set 2026; 312 MB (di cui `Dockerfiles/` 148 MB e `dataset_details/` 31 MB).
- **Licenza: MIT** ("Copyright (c) 2024 Manuel Poisson and Fukuda-lab, National Institute of Informatics, Japan", file `LICENSE`).
- Requisiti dal README, non eseguiti: GNS3 server e GUI (`./install.sh gns3`), reinstallazione di Docker (`./install.sh docker`), utente nei gruppi `ubridge libvirt docker`, **virtualizzazione KVM** (nested se GNS3 gira in una VM), un venv con `requirements.txt` e la build di tutte le immagini con `make`. Testato su Ubuntu 20.04, 22.04 e Fedora 35.
- [D] Su questo host (LXC) KVM non è disponibile. Sul nodo libero (guest KVM) servirebbe la nested virtualization, che va verificata, e mancano RAM (15 GiB contro ~20 GB) e disco (4,4 GB). Inoltre `install.sh docker` reinstallerebbe Docker, toccando i container di altri progetti: **non va lanciato su nessuno dei due host**. Per eseguire GothX serve una VM dedicata.

**IoT-23: licenza verificata, non scaricato.**
- **Licenza: Creative Commons Attribution 4.0 International**, dal record Zenodo `https://zenodo.org/records/4743746` (DOI 10.5281/zenodo.4743746), che ospita solo la versione completa (`iot_23_datasets_full.tar.gz`, 21,5 GB, md5 `7132e603f9750b8580b6cebdbcd43e9c`). La pagina Stratosphere non dichiara la licenza e chiede solo la citazione (Garcia, Parmisano, Erquiaga, 2020). [?] Ho assunto che la CC BY 4.0 valga anche per la versione leggera ospitata su `mcfp.felk.cvut.cz`, che è lo stesso dataset senza PCAP.
- Versione leggera (solo flussi etichettati): `https://mcfp.felk.cvut.cz/publicDatasets/IoT-23-Dataset/iot_23_datasets_small.tar.gz`, **9.373.916.249 byte (8,7 GiB) compressi** (HEAD: `Content-Length`, `Last-Modified` 25 mar 2022). La pagina dice 8,7 o 8,8 GB. La dimensione decompressa non è dichiarata e va stimata dall'indice dell'archivio senza estrarlo.
- **Destinazione proposta:** `/root/Desktop/DIB/data/external/iot23/` su questo host, l'unico filesystem con spazio (ZFS `poolarray/subvol-170-disk-0`, 34 GB liberi). Dopo il download il pool passa da ~94% a ~96%. L'archivio **non va estratto**: lo si legge in streaming con `tarfile` (come lo zip NCSU, `analysis_fs/ncsu_overlap.py`) e si tengono solo i fatti di endpoint aggregati (pochi MB). Il nodo libero (4,4 GB) è escluso. Alternativa più pulita: allargare il subvolume o aggiungere un disco dall'amministratore Proxmox.
- Quando: dopo M1/M2 e solo se serve (decisione utente).
