# Audit 117 — Risultati della cattura dentro i container sul nodo (pre-registrazione: audit 116)

Eseguita il 2026-10-13 07:59:08Z → 08:02:29Z sul nodo, `deploy_capture.sh` su `tree-88b86a7` (`service.py` sha256 `3ffa57ee…`, `run.py` `0de9652c…`, hash congelati: 0 differenze), profilo `z1` (d = 60 ms, perdita 0), arms D e C, FANOUT 10, 10 episodi per arm (nessuno escluso), `rc=0`, nessun container residuo. Sniffer in `evidence` e nei 10 siti (helper: tutti `rc=0`). Dati: `experiments_tnsm/node_cap_20261013/cap_z1_20261013/capture/gen1` (arm D) e `gen2` (arm C), `SHA256SUMS`. Il verdetto è stato calcolato **sul nodo** con `analyze_capture.py` prima di copiare i dati (`verdict.md`), poi ricalcolato in locale (`verdict_local.md`, stesso risultato). Comandi: `node_commands.txt`.

## Verdetti (regole dell'audit 116, meccaniche)
| arm | connessioni | valide | ipotesi | verdetto | esito |
|---|---|---|---|---|---|
| D | 160 | 100 | H-P1a (MSS 1460) | **confermata** | moda 1460 (200 valori su 200) |
| D | 160 | 100 | H-P1b (2 segmenti E→S) | **confermata** | 100/100 |
| C | 100 | 100 | H-P1a (MSS 1460) | **confermata** | moda 1460 (200 su 200) |
| C | 100 | 100 | H-P1c (4 segmenti E→S, 1 segmento del volo del server, tre voli < 1448) | **FALSIFICATA** | 0/100 |

(Le 60 connessioni D non valide sono le sonde TCP di RTT dell'harness: SYN e FIN senza dati.)

## Cosa dicono i dati
- **Conteggio dei segmenti: come nel v5.** Arm D: firma (E→S, S→E, volo del server) = (2, 2, 0) in 100/100. Arm C: (4, 4, 1) in 100/100: ClientHello, volo del client e due scritture della richiesta da E; un solo segmento di volo del server prima del volo del client. Sono i 4 (D) e 7 (C) pacchetti del v5 (SYN, SYN-ACK più i segmenti con dati).
- **La clausola sulle lunghezze è falsificata, e per tutte le 100 connessioni C:** lunghezze mediane E→S = 1537 (ClientHello), 853 (volo del client), 226 e 93 (richiesta); S→E = 2393 (volo del server), 1502 (due NewSessionTicket), 147, 38. Il ClientHello (1537) e il volo del server (2393) superano l'MSS effettivo 1448. Nell'audit 94 (loopback locale, altra versione di OpenSSL) il ClientHello era 517 byte e il volo del server 1288: sul nodo sono molto più grandi (a prima vista coerente con una key share ibrida post-quantistica del client, **ipotesi non verificata**).
- **Osservazione (non pre-registrata nel primo run):** nel tap in ingresso del sito il ClientHello (1537 byte) e il volo del server (2393 byte, visto in ingresso a `evidence`) arrivano **come un'unica unità** con la stessa lunghezza con cui sono partiti: 100/100 connessioni C, e 100/100 per D. Non c'è spezzettamento a 1448 fra il tap in uscita e quello in ingresso. I tap vedono quindi pacchetti più grandi dell'MTU 1500 del bridge (offload, segmentazione rimandata): l'MSS "1448 sul filo" dell'audit 94 non descrive questo percorso virtuale. Se la perdita di `netem` colpisce l'unità intera, i pacchetti esposti sono quelli contati dal v5 (7 per C); se la segmentasse, sarebbero 9 (ClientHello 2, volo del server 2). **Questa misura è a perdita zero e non può dirlo.**

## Conclusione (come pre-registrato)
H-P1c è falsificata nella lettera (la clausola sulle lunghezze), ma la struttura in unità (conteggio dei segmenti per direzione) è quella del v5. Il conteggio dei pacchetti esposti **non** viene corretto da questa misura. Il residuo del modello con mTLS (≈ 7,6 effettivi contro 7) non è spiegato dalla struttura a perdita zero. Per sapere se `netem` con perdita spezza le unità (7 o 9 pacchetti esposti) serve la cattura con perdita (addendum 1 dell'audit 116, pre-registrato prima del lancio).

## Limiti
Una macchina, 10 episodi per arm, una replica, `z1`, senza perdita; il tap in uscita è dopo la coda `netem`; i tap vedono le unità del kernel, non il filo (non c'è un filo fisico). L'ipotesi sulla key share post-quantistica non è verificata (non si è letto il contenuto del ClientHello).
