# Audit 80 — Modello di consegna v4 (richiesta in due segmenti) e pre-registrazione della validazione confermativa su condizioni nuove

Data: 2026-10-12. Contesto: nel run confermativo dell'audit 78/79 il modello v3 sottostima le consegne in ritardo del parallelo di 1,4-2,1 punti a perdita 3 % e di 5,0-5,6 a perdita 7 %, cioè circa un pacchetto in più esposto alla perdita. **Ipotesi di struttura (derivata dal pattern, non adattata):** la richiesta HTTP parte in due segmenti TCP (intestazioni e corpo; httpcore imposta `TCP_NODELAY`), e la richiesta arriva quando arriva il **secondo** (ognuno ritrasmesso indipendentemente dopo l'RTO): ritardo = massimo dei due. Nessun parametro nuovo (`req_segments = 2`, 34 test del modello, mutazione "somma invece di massimo" catturata). **Stato:** controllo retrospettivo ESPLORATIVO sui dati già visti: consegne in ritardo previste 0,114/0,250/0,113/0,248 contro 0,108/0,250/0,100/0,242 misurate (v3: 0,087/0,194/0,086/0,192); da qui il run su condizioni nuove. **Non verificato con una cattura di pacchetti** (nessuna cattura è stata fatta): il numero di segmenti è un'ipotesi coerente con i dati.

## Previsioni v4 per le condizioni NUOVE (calcolate PRIMA dei dati; 20 000 episodi, seme 20261012, arm D, RTO, riconciliazione, `req_segments = 2`; ritardi 60/120/180 ms e perdite 4/8 % mai usati finora)
| delay one-way ms | R ms | loss | v4 per-site late share | v4 slow episodes | v4 median last ms | v4 p95 ms | v3 per-site late share (for comparison) |
|---|---|---|---|---|---|---|---|
| 60 | 120 | 4% | 0.150 | 0.801 | 1180 | 1540 | 0.114 |
| 60 | 120 | 8% | 0.282 | 0.966 | 1180 | 2300 | 0.220 |
| 120 | 240 | 4% | 0.149 | 0.800 | 1360 | 2080 | 0.113 |
| 120 | 240 | 8% | 0.281 | 0.963 | 1360 | 2600 | 0.218 |
| 180 | 360 | 4% | 0.147 | 0.796 | 1764 | 2900 | 0.113 |
| 180 | 360 | 8% | 0.277 | 0.962 | 1900 | 4977 | 0.217 |

## Misura
Come audit 75-79 (banco netns, `service.py` invariato, P0 = parallelo, connessione nuova). Celle: 6 di perdita (3 ritardi × 2 perdite) con 60 episodi + 3 a p = 0 (uno per ritardo) con 20 episodi per la validità. Ordine mescolato con seme 20261012. Dati in `run_20261012_v4/`.

## Criteri (fissati ora, più stretti di quelli dell'audit 78)
- **T-W0 (validità):** a p = 0 la mediana per sito è entro ±50 ms di 1,5 R e 0 consegne in ritardo, per ciascun ritardo. Se fallisce, nulla si riporta.
- **T-W1 (modello v4):** in ciascuna cella la quota di consegne in ritardo sta entro **±3 punti** della previsione v4, la quota di "slow episodes" entro **±10 punti** e la quota di episodi con un sito non aggiornato entro 30 s è ≤ 2 %. **Il modello v4 è validato fuori campione se almeno 5 celle su 6 soddisfano tutto e nessuna cella eccede il doppio delle tolleranze (±6 e ±20 punti)**; altrimenti "non validato" con l'elenco.
- **T-W2 (descrittivo, nessun criterio):** quante celle avrebbe superato v3 con le stesse tolleranze.
Nessuna modifica di criteri o previsioni dopo i dati.
