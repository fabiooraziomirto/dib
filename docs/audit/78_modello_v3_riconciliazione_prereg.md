# Audit 78 — Modello di consegna v3 (con la riconciliazione) e pre-registrazione della validazione confermativa su condizioni nuove

Data: 2026-10-12. Contesto: nel run sequenziale dell'audit 77 il modello v2 non è validato (5/9) perché ignora che un sito applica l'evento **anche** quando la sua riconciliazione periodica (ogni T = 5 s, jitter 0,5 s, `generate_compose.py`) lo trova nello stato dell'evidence (anti-entropia, `service.py` docstring): l'applicazione effettiva è il **minimo** fra consegna del fan-out e prossima riconciliazione. Il P-log del nodo (audit 56) conta solo le applicazioni del fan-out: misura un'altra grandezza; qui la grandezza è "il record del sito passa a `disputed`" per qualunque via.

## Modello v3 (`experiments_tnsm/retry_model/model.py`, 29 test, mutazioni catturate)
v2 più: ogni sito ha una riconciliazione con fase φ ~ U(0, T + J) dopo il commit dell'evidence e applica a φ + 2R (connect + richiesta/risposta); applicazione = min(fan-out, riconciliazione). Parametri **non adattati**: T = 5 s e J = 0,5 s sono la configurazione del servizio. Con la riconciliazione nessun episodio resta "pending" (il sito riceve l'evento dalla riconciliazione). **Stato:** valutazione retrospettiva ESPLORATIVA sui dati sequenziali già visti (audit 77): mediane previste 2 050/2 950/3 850 ms (50 ms), 3 900/4 300/4 875 (100 ms), 5 400/5 561/5 681 (200 ms) per perdita 2/5/10 % contro 2 020/3 564/4 270, 3 951/4 030/5 435, 5 729/5 711/6 519 misurate: **non è una validazione** (il meccanismo è stato scelto dopo aver visto i dati), da qui il run confermativo.

## Previsioni v3 per le condizioni NUOVE (calcolate PRIMA dei dati; 20 000 episodi, seme 20261012, arm D, RTO e riconciliazione attivi)
| delay one-way ms | R ms | loss | P0 per-site late share | P0 slow episodes | P0 median last ms | P0 p95 ms | P0 pending | S1 median last ms | S1 p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| 75 | 150 | 3% | 0.087 | 0.597 | 675 | 1225 | 0.000 | 3325 | 4775 |
| 75 | 150 | 7% | 0.194 | 0.884 | 1225 | 2225 | 0.000 | 4025 | 5475 |
| 150 | 300 | 3% | 0.086 | 0.592 | 1450 | 2270 | 0.000 | 5050 | 5954 |
| 150 | 300 | 7% | 0.192 | 0.883 | 1750 | 3050 | 0.000 | 5281 | 6022 |

## Misura
Come audit 75-77 (banco netns, service.py invariato dal commit `75836c8`, tempi fuori banda dalle righe SQLite; "completo" = tutti i 10 siti applicano entro 30 s (parallelo) o 120 s (sequenziale)). Celle: **P0** (concorrenza 10, connessione nuova): 4 celle di perdita (75/150 ms × 3/7 %) con 60 episodi + 2 celle a p = 0 (75 e 150 ms) con 20 episodi per la validità; **S1** (sequenziale): le stesse 4 celle di perdita con 40 episodi. Ordine mescolato con seme 20261012. Dati in `run_20261012_v3/`.

## Criteri (fissati ora)
- **T-V0 (validità):** a p = 0, P0: mediana per sito entro ±50 ms di 1,5 R e 0 consegne in ritardo (stessa regola dell'audit 75). Se fallisce, nulla si riporta.
- **T-V1 (parallelo):** in **almeno 3 celle su 4** la quota misurata di consegne in ritardo sta entro ±4 punti della previsione, la quota di "slow episodes" entro ±12 punti e la quota di episodi con un sito non applicato entro 30 s è ≤ 2 % (la previsione è 0).
- **T-V2 (sequenziale):** in **almeno 3 celle su 4** la mediana misurata dell'ultimo sito sta entro ±25 % della previsione.
- **T-V3 (descrittivo):** p95 dell'ultimo sito contro previsione; nessun criterio.
- **Il modello v3 è "validato fuori campione" se T-V0, T-V1 e T-V2 reggono tutti**; altrimenti "non validato" con l'elenco delle celle fuori. Nessuna modifica di criteri o previsioni dopo i dati.
