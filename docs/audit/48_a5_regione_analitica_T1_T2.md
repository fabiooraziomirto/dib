# Audit 48 — Verifica sul codice della regione di ammissione di DIB (T1/T2 di audit 44 §3)

Data: 2026-10-11. Codice: `analysis_fs/a5_region.py` (predittore con `Fraction`), test `analysis_fs/test_a5_region.py` (rossi per modulo mancante nel commit `aaffc34`, poi implementazione). Comando: `PYTHONPATH=code/src PYTHONDONTWRITEBYTECODE=1 timeout 300 python3 -m pytest analysis_fs/test_a5_region.py -q -p no:cacheprovider`. Ipotesi e criterio di falsificazione: docstring del test (scritti prima dell'esecuzione). Python 3.10.13.

## Esito: **43 passed**
- **T1** (algebra esatta, 7 valori di N × K × j = 0..100, pareggi inclusi): `α·C_s + β·C_t ≥ θ ⇔ C_s ≥ 5/12 ∧ C_t ≥ (θ − α·C_s)/β` vale su tutta la griglia; soglie: C_t ≥ 1/8 a C_s = 1, C_t ≥ 1 a C_s = 5/12.
- **T2** (40 popolazioni sintetiche, seed 0..39, sul vero `DIBScorer`, `min_reporting_sites = 2`): `accepted == previsione` su tutti i punti fuori dalla zona di pareggio. Punti esaminati (ricalcolati a parte con lo stesso generatore): 67 ammessi, 132 rifiutati, **0 nella zona di pareggio** (|score esatto − θ| < 10⁻¹²), quindi nessuna lista di pareggi da riportare.
- Test aggiuntivo: un endpoint con una sola sorgente dentro la regione (C_s = 1/2, C_t > 0,875) è rifiutato dal solo quorum (`dib.py:45-46`).

## Mutazioni (devono far fallire i test)
| Mutazione | Esito |
|---|---|
| φ = 1/3 al posto di 5/12 | 1 test fallito (T1) |
| α e β scambiati | 15 test falliti |
| `>` al posto di `≥` | 1 test fallito (T1) |
| m = 1 nello scorer (test a sorgente singola) | 1 test fallito |
| C_t senza il termine di frequenza | **non applicabile**: il predittore riceve C_t letto dallo scorer, non lo ricalcola; il termine di frequenza non è verificato qui |
Nota onesta: la prima versione del test a sorgente singola era sbagliata nella fixture (C_t = 0,85, score 0,64 < θ perché il rapporto di frequenza era 0,5): è fallita sul codice originale per un errore mio nel dato, non per il codice; ho corretto la fixture (più osservazioni per l'endpoint) senza toccare l'asserzione. La mutazione m = 1 non era catturata prima di questo test.

## Cosa autorizza a dire
La caratterizzazione di audit 44 §6 è ora **verificata sul codice** per γ = 0, (α, θ) = (0,6; 0,65), m = 2: nel regime a N siti DIB ammette sse |S_e| ≥ 2, C_s ≥ 5/12 e C_t sopra la soglia decrescente (θ − α·C_s)/β = 1,625 − 1,5·C_s. **Limiti:** popolazioni sintetiche piccole (≤ 12 siti), nessun punto nella zona di pareggio; la verifica riguarda la regione, non il valore benigno delle due regole (A5 resta ritirata).
