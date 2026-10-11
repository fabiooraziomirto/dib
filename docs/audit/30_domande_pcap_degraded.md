# Audit 30 — Domande per i pcap di `degraded` (scritte e committate PRIMA di aprire un pcap; 2026-10-11)

## 0. Inventario (nessun pcap ancora aperto; aperti solo i `ls` e gli sha256)
Copiati dal nodo in `/root/Desktop/dib_pcap_20261011/` (**fuori dalla repo**: il braccio D ha payload in chiaro), sha256 coincidenti fra nodo e locale. Dati del driver del blocco in `experiments_tnsm/m67_retraction/degraded_20261011/tcpdump/` (sha256 `cells.jsonl` `53f34c6f…`, coincide), non ancora analizzati.

| File | sha256 | Byte |
|---|---|---|
| `dib_degraded_D_evidence.pcap` | `08418886…` | 2 647 800 |
| `dib_degraded_D_site0.pcap` | `4a72f4fc…` | 161 405 |
| `dib_degraded_C_evidence.pcap` | `6fe68fcc…` | 12 790 108 |
| `dib_degraded_C_site0.pcap` | `ec25ee74…` | 892 526 |

Finestre `CAPTURE_WINDOW` (epoch del nodo): D 1791712157,472 → 1791712520,233; C 1791712721,105 → 1791713265,807. Catture avviate dall'utente con `tcpdump -i eth0 'tcp port 8000'` nei namespace di evidence e di site-0 (due namespace in parallelo per braccio), filtro unico per tutto il traffico sulla porta 8000. Fatto già noto, non una domanda: la dimensione di C-evidence (12,8 MB in 545 s) è 4,8× quella di D-evidence (2,6 MB in 363 s).

## 1. Domande, in ordine; ogni domanda ha la regola di risposta dichiarata prima
Tutte le analisi usano solo intestazioni (IP/TCP: indirizzi, porte, flag, seq/ack, lunghezze, timestamp). **Il payload non si legge né si stampa** (D in chiaro). Orologio: i due namespace condividono il kernel e quindi `CLOCK_REALTIME` del nodo, i timestamp sono confrontabili.

**Q1 (lato della cattura rispetto alla qdisc).** Abbinando i pacchetti che evidence invia a site-0 (chiave: IP/porte, flag, seq, ack, lunghezza di payload, IP-ID) nelle due catture: (a) quanti pacchetti inviati (visti al tx di evidence) **non** compaiono al rx di site-0, e viceversa; (b) la mediana di Δ = t_rx(site-0) − t_tx(evidence) per i pacchetti abbinati. Regola: **tap dopo la qdisc** se i non abbinati sono ≲ 1% (con migliaia di pacchetti e perdita del 5% per lato, la perdita del tap-prima sarebbe evidente) **e** Δ mediana < 20 ms; **tap prima della qdisc** se i non abbinati sono vicini al 5% **e** Δ mediana in [180, 220] ms; altrimenti "non determinato". Stessa domanda per la direzione site-0 → evidence. Il campione per queste coppie è la sola coppia evidence↔site-0 (nel pcap di site-0 passa solo quel traffico; per D circa 20 consegne × 1 più letture).

**Q2 (perdita osservabile).** Se Q1 dà "tap prima": la frazione di pacchetti persi per direzione (5% attesa per lato, `netem_apply.sh`: `delay 200ms loss 5%`) con IC di Clopper-Pearson, per braccio. Se Q1 dà "tap dopo": la perdita **non è osservabile come pacchetti mancanti**: dichiararlo e passare a Q3-Q5 dai soli ritrasmessi.

**Q3 (a1, RTO iniziale 1 s).** Sulle connessioni con SYN ritrasmesso (stessa quadrupla, SYN ripetuto): l'intervallo fra SYN consecutivi visti nella stessa cattura. Previsione: ~1,0 s (RTO iniziale), ≥ del timeout di 1 s per fase del client. Falsificata se la mediana degli intervalli è fuori da [0,9; 1,1] s (con almeno 5 casi), o "non valutabile" con meno di 5 casi. Se il tap è dopo la qdisc il primo SYN perso è invisibile al mittente: si leggono gli intervalli fra SYN visti al ricevitore e fra il SYN visto e la riga del driver.

**Q4 (a2/a3, RTO minimo 200 ms, TLP, PTO ≈ 2R).** Per i segmenti di dati ritrasmessi (stessi seq e lunghezza, tempo successivo): il ritardo fra la trasmissione originale (vista) e la prima ritrasmissione/sonda. Previsioni registrate (audit 14, "Predizione (c), scomposta per fase"): a `degraded` (R = 0,4 s) PTO ≈ max(2R, 1,5R + 200 ms) = 0,8 s e attesa dopo perdita singola ≈ PTO + R ≈ 1,2 s. Distinguere per braccio la distribuzione dei ritardi (picchi vicino a 0,8 s = TLP/PTO, o a ~1,2 s = RTO, o altro) e **riportare i picchi osservati, senza adattare le previsioni**; il TLP è presente se compaiono ritrasmissioni di segmenti già inviati < 1 s dopo l'ultimo segmento senza che siano passati RTO.

**Q5 (a4, n_c: numero di attraversamenti per consegna).** Per ogni connessione evidence→sito completata (una per tentativo?), il numero di "voli" unidirezionali (raggruppando i pacchetti consecutivi nella stessa direzione senza pausa > 100 ms, ACK puri esclusi) nelle fasi connect, TLS, richiesta/risposta. Previsione: D 4-5 voli totali, C 7-10. Falsificata se la mediana per braccio è fuori dall'intervallo. Domanda collegata: quante connessioni TCP per consegna e quanti tentativi (fino a 3) con timeout di 1 s per fase, e quante connessioni sono chiuse dal client (FIN/RST di evidence) a ~1 s.

**Q6 (quota di fasi in timeout, base di (c)).** Per braccio, la frazione di connessioni dove la fase di connect non completa entro 1 s (previsione ≈ 2p ≈ 10%, p = 5%) e la frazione dove TLS o richiesta/risposta non completano entro 1 s (previsione: scade sempre alla prima perdita, `degraded` ≈ 1,2 s > 1 s). Confronto con la quota di consegne in pending dai dati del driver (la previsione (c) è condizionale a questa calibrazione, audit 14).

**Q7 (coerenza con il driver).** Il numero di consegne `POST /apply_fanout` (D: 200 = 20 episodi × 10 siti) viste nel pcap di evidence contro le righe `plog_apply_ts` e `plog_ack_ts` di `tcpdump/cells.jsonl`; la copertura temporale (primo e ultimo pacchetto contro le finestre `CAPTURE_WINDOW`).

**Q8 (completezza della cattura).** Non c'è il conteggio dei pacchetti scartati dal kernel (stampato da `tcpdump` all'uscita, non salvato): dichiarare come limite; verificare indirettamente la continuità (pacchetti ricevuti prima di un ACK che ne cita il numero di sequenza).

## 2. Decisioni dichiarate prima di aprire
1. **Q1 decide cosa si può dire dopo**: se "tap dopo" o "non determinato", Q2 non si calcola come perdita da pacchetti mancanti; Q3-Q6 si riportano con il limite che il primo pacchetto perso è invisibile al mittente.
2. Nessuna previsione registrata si modifica; se un intervallo è violato, si riporta il valore osservato (regola: "interamente fuori" per le soglie che hanno un intervallo).
3. Il **lato della cattura** (Q1) è un risultato in sé: si congela dopo, come da `run.py` (docstring: "TO CONFIRM in the first `degraded` capture").
4. Nessun pcap viene copiato nella repo né committato; nella repo vanno solo conteggi e statistiche (non contengono payload).
5. Nessun tcpdump, nessun comando sul nodo per questa analisi (solo lettura di file locali). Il parser dei pcap è pure Python (nessuna dipendenza: né `tcpdump` né `scapy` sono installati sulla workstation), provato su pcap sintetico.
