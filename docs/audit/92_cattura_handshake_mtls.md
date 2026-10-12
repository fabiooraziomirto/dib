# Audit 92 — Cattura dell'handshake mTLS e della richiesta /apply_fanout (passo 1, misura locale)

Data 2026-10-12. Locale (nessun accesso al nodo), rete privata `unshare -n`, nessuna perdita. **Non è una misura di tempo** e **non è una validazione**: osserva quali pacchetti e quanti byte compongono una connessione mTLS fredda, perché il modello v4 li assumeva senza averli visti.
Codice: `experiments_tnsm/mtls_model/capture/capture_handshake.py`. Dati: `experiments_tnsm/mtls_model/capture/run1.json` (sha256 `4d…` vedi `sha256sum`). Python 3.10.13, uvicorn 0.51.0, httpx 0.28.1.

## Cosa è e cosa non è fedele al servizio
- Server: `dib.registry.distributed.mtls.server_config` (`mtls.py:88-95`, `ssl_cert_reqs=CERT_REQUIRED`), cioè la configurazione di produzione, con certificati di `make_dist_pki.py` (ECDSA P-256, 491 byte DER per foglia, CA 353 byte; sul nodo i PEM sono 692-721 byte, coerenti).
- Client: `httpx.post` con `mtls.client_context` (`mtls.py:98-103`) e lo stesso JSON di `_deliver_to_site` (`service.py:798`, 78 byte), certificato client `evidence.crt`, server `site-0.crt`.
- **Non fedele:** il server è una app ASGI minima che risponde `{"applied": true}` (17 byte): la dimensione della risposta non è quella del servizio vero. Il loopback ha MTU 65536: i pacchetti catturati sono le scritture dell'applicazione, non segmenti di rete; il numero di segmenti sul filo è DERIVATO con MSS 1448 (MTU 1500 del bridge Docker, **ipotesi non verificata sul nodo**; con le opzioni TCP timestamp diventa 1436, stessa conclusione). Ogni pacchetto compare due volte nel file (ingresso e uscita su `lo`): sotto sono deduplicati.

## Osservato (una connessione fredda, deduplicata)

| # | direzione | byte di payload | contenuto (record TLS) | segmenti a MSS 1448 |
|---|---|---|---|---|
| 1 | C→S | 0 | SYN | 1 |
| 2 | S→C | 0 | SYN-ACK | 1 |
| 3 | C→S | 517 | ClientHello | 1 |
| 4 | S→C | 1288 | ServerHello + CCS + EncryptedExtensions + CertificateRequest(?) + Certificate[879] + CertificateVerify[97] + Finished[69] | **1** (1288 < 1448) |
| 5 | C→S | 1066 | CCS + **Certificate[879] + CertificateVerify[97] + Finished[69]** (volo del client) | **1** (1066 < 1448) |
| 6 | S→C | 1502 | due NewSessionTicket da 746 | 2 |
| 7 | C→S | 240 | richiesta HTTP: intestazioni (235 byte cifrati) | 1 |
| 8 | C→S | 93 | richiesta HTTP: corpo (88 byte cifrati) | 1 |
| 9 | S→C | 147 | risposta: intestazioni | 1 |
| 10 | S→C | 39 | risposta: corpo | 1 |

Fatti letti dai dati (`run1.json`, campi `events`):
- il volo del client (riga 5) è UN segmento di 1066 byte: contiene la catena (foglia + CA = 879 byte di record Certificate), quindi **non è un solo certificato da ~500 byte come ipotizzato nell'audit 91**, ma resta sotto l'MSS;
- il server invia il volo (riga 4) in un solo segmento da 1288 byte;
- le due scritture della richiesta (righe 7 e 8) sono segmenti separati (conferma di `req_segments=2` del v4);
- il client scrive le righe 5, 7 e 8 a ~0,3 ms l'una dall'altra, **senza aspettare nulla dal server** (nel loopback i NewSessionTicket della riga 6 sono già arrivati; non è una prova sulla rete reale, ma TLS 1.3 permette al client di spedire dati subito dopo il proprio Finished);
- i NewSessionTicket (riga 6) viaggiano nello stesso flusso S→C prima della risposta: una loro perdita può ritardare la LETTURA della risposta da parte del client (blocco in ordine), non l'arrivo della richiesta al server. La quota in ritardo del paper è misurata sul log di apply del sito (arrivo della richiesta), quindi non ne dipende.

## Confronto con il modello v4 (`experiments_tnsm/retry_model/model.py:42-80`, righe del ramo `rto`)
- v4 modella: SYN, SYN-ACK, ClientHello, volo del server (1 RTT), poi la richiesta in 2 segmenti (`req_segments=2`).
- **Manca** il segmento 5 (volo del client), che viaggia nello stesso lotto della richiesta (3 segmenti spediti di fila: 5, 7, 8). Un lotto di 3 segmenti consegna la richiesta al servizio solo quando arrivano tutti e 3; con la regola già usata dal v4 (massimo dei ritardi dei segmenti) questo equivale a `req_segments=3` per il braccio C.

## Definizione del v5 (fissata dalla cattura, non da C/10)
v5 = v4 con `req_segments = 3` nel braccio C e `req_segments = 2` nel braccio D (il braccio D non ha volo del client). Nient'altro cambia: nessun parametro è stato adattato.

Previsioni del v5 alla condizione `degraded` (R=0,4 s, perdita 5 %, seed del modello, 20 000 episodi, `rto=True`), calcolate DOPO aver visto le misure in campione e quindi **non indipendenti da esse**:

| | v4 | v5 | misurato (in campione) |
|---|---|---|---|
| C/10 quota in ritardo | 0,251 | 0,280 | 0,310 (B5), 0,282 (86), 0,335 (89) |
| C/1 mediana (ms) | 16 400 | 17 200 | 16 126 (86), 17 806 (89) |

Letto onestamente: il v5 chiude la parte più grande della sottostima ma non tutta (media delle tre repliche 0,309 contro 0,280: restano ~3 punti, e il v5 coincide con la replica più bassa). La dispersione fra repliche (0,282-0,335, intervalli bootstrap larghi ±0,04-0,06 a 50 episodi) non permette di dire se il resto sia rumore o un altro elemento non modellato. Per questo il v5 va valutato FUORI CAMPIONE (audit 93, da scrivere prima di ogni dato nuovo).

## Differenza rispetto all'audit 91
L'audit 91 ipotizzava un volo del client da 1-3 segmenti sommato in sequenza prima della richiesta (0,281/0,310/0,334). La cattura dice: 1 segmento (non 2 o 3), **spedito nello stesso lotto della richiesta**, non in sequenza prima. L'ipotesi "3 segmenti" che riproduceva 0,334 è esclusa dalla cattura (nei limiti di MSS e catena); resta il valore a 1 segmento, 0,280 (burst) contro 0,281 (sequenza): praticamente lo stesso numero.

## Limiti
Una sola connessione catturata, senza perdite; MSS assunto; app ASGI minima; loopback (nessun ritardo reale), quindi niente di questo dice nulla sulla correlazione fra i ritardi dei segmenti sulla rete reale. Non esclude altri elementi non modellati (finestra di congestione iniziale, ritrasmissione di tutti i segmenti marcati persi dopo un RTO, ACK ritardati).
