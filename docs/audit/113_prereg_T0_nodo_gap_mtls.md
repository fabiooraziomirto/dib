# Audit 113 — Pre-registrazione: misura SENZA perdita sul nodo per il divario con mTLS

Scritta e committata PRIMA di ogni dato (2026-10-13). Origine: audit 109 (il v5 non chiude la sottostima con mTLS: 3-7 punti) e il calcolo sul numero efficace di pacchetti esposti: n = ln(1 − quota) / ln(1 − p) vale ≈ 4,2 senza mTLS (modello: 4) e ≈ 7,6 con mTLS (v4: 6, v5: 7): manca circa 0,6 pacchetti, quasi costante. Una delle ipotesi è un effetto di CPU o di tempi lato mTLS **indipendente dalla perdita**, che a R piccolo (soglia 0,75 R = 90 ms a R = 0,12 s) sposta consegne senza perdita oltre la soglia di "in ritardo".

## Misura
Profili `z1` (d = 60 ms, R = 0,12 s) e `z3` (d = 150 ms, R = 0,30 s), **perdita 0**, stesso ritardo di X1 e X3. `run.py b1`, arms D e C, FANOUT 10, 30 episodi per cella (300 valori per cella), `deploy_run.sh` (applicatore in user space), albero `tree-88b86a7` (`service.py` sha256 `3ffa57ee…` invariato; cambiano solo i profili in `run.py`), H-G come negli altri run (lo sha dei container deve essere `3ffa57ee…`). Quota in ritardo e spostamento mediano rispetto al nominale (1,5 R per D, 2,5 R per C): `analyze_lossless.py`.

## Ipotesi e falsificazione
- **H-Z1:** senza perdita la quota in ritardo per sito è ≤ 0,02 in tutte e quattro le celle. **Falsificata** se una cella supera 0,02: allora l'effetto di CPU/tempi esiste e **si riporta la sua entità** (quota e spostamento mediano), che entra nel modello come termine additivo.
- Se H-Z1 regge, l'effetto CPU/tempi **non spiega** il pacchetto mancante, che sta nella struttura dei pacchetti (prossima misura: cattura dentro i container).
- Nessuna soglia cambia dopo i dati.

## Limiti
Una macchina (nodo virtuale), 30 episodi per cella, una replica; senza perdita non misura gli effetti della ritrasmissione.
Esecuzione sul nodo subito dopo la copia di sicurezza (`DIB_esperimenti_snapshot_20261013`); risultati: audit 114.
