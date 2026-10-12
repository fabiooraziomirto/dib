# Audit 91 — ESPLORATIVO: il volo del certificato client (mTLS) come causa della sottostima di C/10

**Stato: esplorativo e post-hoc. Non è una validazione e non cambia il paper.** I dati di C/10 sono stati visti prima (B5 0,310; audit 86 0,282; audit 89 0,335).

Osservazione: il modello v4 (`experiments_tnsm/retry_model/model.py:61-65`) rappresenta l'handshake mTLS con ClientHello e volo del server (un RTT) ma non il secondo volo del client (Certificate, CertificateVerify, Finished di TLS 1.3), che precede la richiesta e può perdersi. Il v4 sottostima C/10 di 3-8 punti (audit 89).

Prova (script `experiments_tnsm/retry_model/exploratory_v5x/run_v5x.py`, output `out.txt`; `CERT_SEGMENTS=0` riproduce il v4 a 0,251): un solo elemento in più, derivato dal protocollo e non aggiustato, cioè il volo del client in N segmenti con la stessa regola di perdita e RTO:

| segmenti del volo client | quota in ritardo C/10 | mediana C/1 (ms) |
|---|---|---|
| 0 (v4) | 0,251 | 16 400 |
| 1 | 0,281 | 17 000 |
| 2 | 0,310 | 17 400 |
| 3 | 0,334 | 18 000 |

Misure: C/10 0,310 (B5), 0,282 (audit 86), 0,335 (audit 89); C/1 mediana 16 126 e 17 806 ms (audit 86, 89).

Quanti segmenti? I certificati client del nodo sono ECDSA P-256 (`~/dib_tnsm/pki/*.crt`, 692-721 byte in PEM, quindi circa 500 byte in DER). Il volo Certificate + CertificateVerify + Finished sta in un solo segmento (< MSS) se la catena inviata è la sola foglia: previsione v5 con 1 segmento, **0,281**, dentro l'intervallo delle tre repliche ma sotto la loro media (0,309). Non ho verificato con una cattura quale catena invia davvero il client né se la richiesta viaggia nello stesso segmento del Finished: sono ipotesi.

## Cosa NON dice
- Le tre repliche coprono l'intervallo fra 1 e 3 segmenti: i dati non distinguono fra le varianti.
- Il v5 è stato scelto dopo aver visto che il v4 sottostima: per essere una validazione serve un test fuori campione.

## Cosa servirebbe per validarlo (non fatto)
1. Registrare PRIMA il numero di segmenti con una cattura (pcap di un handshake mTLS del nodo) e la previsione.
2. Confrontarlo con dati nuovi: un altro profilo (`wan`, `lossy`) o la replica nei container con mTLS; il testbed locale non ha mTLS.
3. Se regge, aggiungere il parametro a `model.py` con test rossi prima (il default deve restare v4).

Decisione per l'utente: il paper dichiara il limite (frase già scritta, audit 89) e questa spiegazione resta un'ipotesi di lavoro, oppure si investe il test fuori campione prima della submission.
