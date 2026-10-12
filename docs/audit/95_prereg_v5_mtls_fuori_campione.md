# Audit 95 — Pre-registrazione: validazione FUORI CAMPIONE del modello v5 (mTLS)

Scritta e committata PRIMA di ogni dato nuovo (2026-10-12). Premessa: `docs/audit/94_cattura_handshake_mtls.md` (cattura locale; v5 definito da essa, senza parametri adattati). Ogni dato di C/10 visto finora (B5 0,310; audit 86 0,282; audit 89 0,335; condizione `degraded`, R=0,4 s, perdita 5 %) è IN CAMPIONE e non conta come validazione.

## Modello
- v4: `experiments_tnsm/retry_model/model.py` invariato (default). v5: stesso modello con `req_segments=3` nel braccio C (volo del client + 2 segmenti di richiesta spediti di fila, audit 94 tabella righe 5, 7, 8) e `req_segments=2` nel braccio D. Si usa solo `rto=True`, senza riconciliazione (come le previsioni v4 di audit 85).

## Ambiente
Testbed locale con mTLS (`experiments_tnsm/netns_testbed/`, da estendere: servizi con `DIB_DIST_MTLS=1`, PKI di `make_dist_pki.py`, server `mtls.server_config`, certificati ECDSA P-256, 10 siti + evidence in un netns con `tc netem` su `lo`, come i blocchi D validati in audit 79-81). Una macchina, nessun confronto con i tempi del nodo. **Le misure partono solo se nessun processo `tlc2.TLC` gira (controllo con `ps`) e il load average a 1 minuto è sotto 4**: il manifest registra load e processi.

## Controllo di equivalenza del testbed con mTLS (H-V3), prima dei dati fuori campione
Condizione `degraded` (R=0,4 s, p=5 %), 100 episodi per braccio, FANOUT 10.
- H-V3a: D/10 entro ±0,04 da 0,176 (media delle repliche del nodo 0,186 e 0,166).
- H-V3b: C/10 entro ±0,05 da 0,309 (media delle tre repliche del nodo).
Se H-V3 cade, il testbed non è equivalente al nodo con mTLS: le conclusioni valgono solo per il testbed, e la validazione fuori campione resta comunque eseguibile ma si riporta come tale. Non si cambiano soglie.

## Condizioni fuori campione (mai usate con mTLS; R = RTT, p = perdita per direzione)
| id | R (s) | p | previsione v4 C/10 | previsione v5 C/10 | previsione D/10 |
|---|---|---|---|---|---|
| X1 | 0,12 | 6 % | 0,307 | 0,348 | 0,217 |
| X2 | 0,20 | 4 % | 0,217 | 0,248 | 0,150 |
| X3 | 0,30 | 6 % | 0,288 | 0,319 | 0,210 |
| X4 | 0,30 | 8 % | 0,353 | 0,388 | 0,265 |
(modello, 20 000 episodi, seed del modello `20261012`, `rto=True`; calcolo nel commit di questo audit.) Mediane C/1 (4 000 episodi): X1 v4 5 900 / v5 5 980 ms; X2 v4 7 700 / v5 8 100 ms; D/1: X1 4 060, X2 5 100 ms.
Campione: 200 episodi per braccio e per condizione, in 10 blocchi indipendenti da 20 (cluster riavviato per blocco), FANOUT 10; per C/1 e D/1, 60 episodi in X1 e X2 (3 blocchi da 20). Quota in ritardo = valori di apply per sito sopra nominale + 0,75 R (definizione del modello, `model.py:134-140`) sugli episodi non esclusi; intervalli bootstrap al 95 % ricampionando gli episodi (5 000 ricampionamenti). Seed del generatore e dell'ordine dei blocchi nel manifest. Criteri di esclusione degli episodi: quelli del testbed già validato (audit 79), applicati prima di guardare le quote.

## Ipotesi e falsificazione
- **H-V0 (controllo, braccio D):** in ogni condizione |D/10 misurato − previsione D| ≤ 0,04. Se cade in una condizione, quella condizione non è interpretabile per C e si riporta così.
- **H-V1:** in ogni condizione interpretabile |C/10 misurato − previsione v5| ≤ 0,04. **Falsificata** se una condizione esce.
- **H-V2 (il v5 è meglio del v4):** errore firmato medio ε = media su X1-X4 di (C/10 misurato − previsione): |ε5| ≤ 0,02 **e** ε4 > 0,02. **Falsificata** se |ε5| > 0,02 o ε4 ≤ 0,02.
- Secondaria, solo descrittiva: mediana C/1 in X1 e X2 entro ±15 % dalla previsione v5 (v4 e v5 differiscono meno del 5 %: non discrimina).

## Cosa va nel paper per ciascun esito (una sola frase in `main_wip.tex`, 13 pagine)
- H-V3, H-V0, H-V1 e H-V2 reggono: il modello con il volo del client prevede la quota in ritardo con mTLS entro 4 punti in 4 condizioni nuove del testbed; il limite con mTLS si riduce a "validato nel testbed, non ancora sul nodo".
- H-V1 regge ma H-V2 cade (v4 e v5 indistinguibili): si scrive che il v5 è coerente ma i dati non lo preferiscono al v4; il limite resta.
- H-V1 cade, oppure H-V3 cade: il limite con mTLS resta com'è e si riporta che la spiegazione del volo del client non è confermata fuori campione.
- Inconcludente (H-V0 cade in ≥ 2 condizioni, o blocchi persi): niente di nuovo nel paper.

## Limiti dichiarati prima
Testbed locale, non nodo; una macchina; il confronto con il nodo si basa su tre repliche a `degraded` e su H-V3; la cattura (audit 94) ha una sola connessione senza perdita, MSS assunto a 1448. Una replica sul nodo con mTLS su X1-X4 sarebbe la conferma, e spetta a te decidere se farla.
