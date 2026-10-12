# Audit 107 — Pre-registrazione: validazione fuori campione del modello v5 (mTLS) sul deployment vero (nodo)

Scritta e committata PRIMA di ogni dato (2026-10-12). Origine: audit 96 (nel banco locale H-V0, H-V1, H-V2 reggono, H-V3 cade: il banco con mTLS non riproduce il nodo; esito `not_confirmed`). Questa prova usa il **deployment vero** (11 container, mTLS reale, immagine ricostruita e verificata, audit 104), quindi non ha bisogno di un banco equivalente.

## Condizioni, modello, disegno
- Condizioni (mai usate con mTLS sul nodo; stesse del banco, audit 95): X1 (d = 60 ms, perdita 6 % per lato, R = 0,12 s), X2 (100 ms, 4 %, R = 0,20), X3 (150 ms, 6 %, R = 0,30), X4 (150 ms, 8 %, R = 0,30). Profili `x1`-`x4` in `run.py` e nell'applicatore netem in user space (stessa convenzione di `degraded`: ritardo a senso unico sull'uscita di ogni container, perdita per lato, R = 2d; bande RTT ±20 % di R).
- Previsioni (modello del 12 ottobre, audit 95, `retry_model`, invariate): quota di consegne in ritardo per sito, FANOUT 10, v4 / v5 per C e v4 per D (D non ha il volo del client: v5 = v4 per D). X1: C 0,307 / 0,348, D 0,217. X2: C 0,217 / 0,248, D 0,150. X3: C 0,288 / 0,319, D 0,210. X4: C 0,353 / 0,388, D 0,265.
- Disegno: `run.py b1`, arms D e C, FANOUT 10, **50 episodi per cella** (come B5 e R1e), un profilo alla volta (`deploy_run.sh`, applicatore in user space, quorum 1, T = 5, keep-alive e invarianti spenti), seme 20261014, albero `tree-49df46a` (`service.py` sha256 `3ffa57ee…` invariato; cambia solo `run.py` con i profili). Precondizione H-G: lo sha256 di `/app/service.py` nei container è `3ffa57ee…` (il run si ferma altrimenti). Quota in ritardo: valori P-log per sito oltre nominale + 0,75 R (nominale 1,5 R per D, 2,5 R per C), episodi non esclusi, IC bootstrap sugli episodi.
- Nessuna calibrazione P-log nuova: la quota in ritardo usa i valori per sito, non la regola `measure_rule` di B1.

## Ipotesi e criteri (soglie fissate ora)
- **H-N0 (controllo D):** per ogni condizione |D/10 − previsione D| ≤ 0,04. Una condizione che non lo rispetta non è interpretabile per C.
- **H-N1:** per ogni condizione interpretabile |C/10 − previsione v5| ≤ **0,05**. La soglia è più larga di quella del banco (0,04, 200 episodi) perché qui gli episodi sono 50 e la dispersione fra repliche di C/10 a `degraded` è nota (0,282-0,335, audit 89): dichiarato prima dei dati.
- **H-N2 (il v5 è meglio del v4):** errore assoluto medio del v5 minore di quello del v4 sulle condizioni interpretabili, e |errore firmato medio del v5| ≤ 0,04.
- **Falsificazione:** H-N1 falsificata da una condizione fuori soglia; H-N2 falsificata se MAE5 ≥ MAE4 o |ε5| > 0,04. Nessuna soglia né previsione cambia dopo i dati.
- **Cosa va nel paper:** `supports` (N1 e N2): una frase che dice che il modello con il volo del client prevede la quota in ritardo con mTLS entro 5 punti in quattro condizioni nuove sul deployment, e si toglie il limite sul v4; `coherent_not_preferred` (solo N1): il limite resta, con la frase che il v5 è coerente; `not_confirmed` o `inconclusive`: il limite resta com'è.
- **Contesto già noto (in campione, non per il criterio):** a `degraded` il nodo dà C/10 0,282-0,335 (R1e 0,314) contro v4 0,251 e v5 0,280: il v5 sottostima ancora di ~3 punti lì. Con la soglia ±0,05 quella differenza sarebbe dentro.

## Limiti dichiarati prima
Una macchina; 50 episodi per cella e una sola replica per condizione; il nodo è una macchina virtuale; FANOUT 10 soltanto (niente C/1 né D/1); il v5 è un solo elemento aggiunto (volo del client in un lotto di 3 segmenti), non è escluso che manchino altri elementi (audit 94).
Esecuzione in coda dopo R1f (`night_queue2.sh`), un profilo alla volta, circa 2,5 ore. Risultati: audit 108.
