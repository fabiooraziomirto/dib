# Audit 75 — Pre-registrazione: validazione fuori campione del modello di consegna (v2) su un banco di prova in namespace di rete, e confronto cold/warm

Data: 2026-10-12. Contesto: `degraded` sul nodo non è misurabile senza il watcher (audit 74). Per avere comunque un **modello validato fuori campione** e una misura dell'effetto delle connessioni persistenti, si usa un banco di prova locale: ogni istanza gira in un namespace di rete proprio (`unshare -n`) con `tc netem` su `lo` (ritardo unidirezionale d e perdita p per pacchetto: ogni pacchetto attraversa `lo` una volta, come nel profilo del nodo; verificato: ping a 200 ms ⇒ RTT 400,1 ms). Servizi: evidence + 10 siti = il vero `service.py` del repo (nessun Docker, HTTP semplice = arm D del nodo; l'arm C con mTLS solo se avanza tempo). **Non sostituisce le misure sul nodo** (stessa macchina per tutti i processi, niente bridge Docker): le conferma o le contraddice in un ambiente indipendente.

## Modello v2 (generalizza audit 62)
Come audit 62, più la ritrasmissione TCP dopo l'handshake: un pacchetto perso (non SYN) arriva dopo RTO = R + max(2R, 0,2 s) (Linux: srtt + max(4·rttvar, 200 ms), srtt = R, rttvar = R/2), raddoppiato a ogni perdita ripetuta; il tentativo fallisce se la fase supera il timeout httpx di 1,0 s; la perdita di SYN/SYN-ACK fallisce sempre (RTO iniziale 1 s). A R = 0,4 s coincide con v1 (test R-9). Codice `experiments_tnsm/retry_model/model.py` (23 test, 5/5 mutazioni catturate). Non c'è nessun parametro adattato ai dati del banco.

## Previsioni (calcolate PRIMA di costruire il banco; 20 000 episodi simulati per cella, seme 20261012, FANOUT 10, 10 siti, arm D)
| delay one-way ms | R ms | loss | policy | median last-site ms | p95 ms | per-site late share | slow episodes | episodes with a pending site |
|---|---|---|---|---|---|---|---|---|
| 50 | 100 | 0.02 | P0 cold | 150 | 1150 | 0.059 | 0.454 | 0.001 |
| 50 | 100 | 0.02 | P1 warm | 50 | 350 | 0.020 | 0.184 | 0.000 |
| 50 | 100 | 0.05 | P0 cold | 1150 | 2150 | 0.142 | 0.786 | 0.010 |
| 50 | 100 | 0.05 | P1 warm | 50 | 350 | 0.050 | 0.400 | 0.000 |
| 50 | 100 | 0.10 | P0 cold | 1150 | 2150 | 0.266 | 0.954 | 0.082 |
| 50 | 100 | 0.10 | P1 warm | 350 | 950 | 0.100 | 0.650 | 0.009 |
| 100 | 200 | 0.02 | P0 cold | 300 | 1300 | 0.059 | 0.455 | 0.001 |
| 100 | 200 | 0.02 | P1 warm | 100 | 700 | 0.020 | 0.181 | 0.000 |
| 100 | 200 | 0.05 | P0 cold | 1300 | 2300 | 0.142 | 0.787 | 0.011 |
| 100 | 200 | 0.05 | P1 warm | 100 | 700 | 0.050 | 0.402 | 0.001 |
| 100 | 200 | 0.10 | P0 cold | 1300 | 2300 | 0.265 | 0.955 | 0.092 |
| 100 | 200 | 0.10 | P1 warm | 700 | 1300 | 0.100 | 0.648 | 0.013 |
| 200 | 400 | 0.02 | P0 cold | 600 | 2000 | 0.059 | 0.453 | 0.005 |
| 200 | 400 | 0.02 | P1 warm | 200 | 1600 | 0.020 | 0.186 | 0.002 |
| 200 | 400 | 0.05 | P0 cold | 1600 | 3000 | 0.139 | 0.774 | 0.061 |
| 200 | 400 | 0.05 | P1 warm | 200 | 2600 | 0.049 | 0.392 | 0.034 |
| 200 | 400 | 0.10 | P0 cold | 2000 | 3000 | 0.256 | 0.943 | 0.340 |
| 200 | 400 | 0.10 | P1 warm | 1600 | 3000 | 0.094 | 0.612 | 0.204 |

"slow episodes" = quota di episodi completi con ultimo sito più lento di (tempo senza perdita + 0,75 R). Il tempo senza perdita è 1,5 R (freddo) e 0,5 R (connessione calda).

## Banco di prova e misura
Per episodio: fatto nuovo, commit di un'approvazione su tutti i 10 siti **senza** netem (netem acceso solo per la fase di disputa), netem acceso, `POST /dispute` dal sito 1; **tempi misurati fuori banda, senza passare dalla rete emulata**: t0 = istante in cui la riga del fatto nel DB dell'evidence passa a `disputed` (lettura SQLite in sola lettura ogni 2 ms), t_i = istante in cui il record del sito i passa a `disputed` (stessa lettura sul DB del sito i); episodio **completo** = tutti i 10 siti applicano entro 30 s; altrimenti pending (escluso dalla mediana). Dopo l'episodio netem spento e attesa che i pending si svuotino (riconciliazione T = 5 s). Politiche: **P0** (default del repo con `DIB_DIST_FANOUT_CONCURRENCY=10`, connessione nuova per tentativo) e **P1** (`DIB_DIST_FANOUT_KEEPALIVE=1`, warmer 2 s; gli episodi distano meno di 5 s, il keep-alive del server). 3 ritardi × 3 perdite × 2 politiche = 18 celle, **60 episodi per cella** (n da vincolo di tempo, non da potere); ordine delle celle mescolato (seme 20261012); nessun confronto con i tempi del nodo in valore assoluto fuori da B5 (audit 56) a (200 ms, 5 %).

## Ipotesi e criteri (fissati ora)
- **T-0 (validità del banco, obbligatoria):** con p = 0 la mediana per sito del tempo di applicazione sta entro ±50 ms di 1,5 R (P0) e di 0,5 R (P1) per ciascun d, e la quota di consegne in ritardo è 0. **Se fallisce, il banco non è valido e nulla di ciò che segue si riporta.**
- **T-1 (modello fuori campione, P0):** in ciascuna delle 9 condizioni, la quota misurata di consegne in ritardo sta entro ±4 punti (assoluti) della previsione **e** la quota misurata di "slow episodes" entro ±12 punti. Verdetto per cella; **modello valido se ≥ 7 celle su 9 soddisfano entrambe e nessuna ha una discrepanza oltre il doppio dei punti consentiti**; altrimenti "non validato" con elenco delle celle. La mediana è solo descrittiva (salta di ~1 s vicino al 50 %).
- **T-2 (effetto di P1):** in ogni condizione in cui il modello prevede una riduzione delle consegne in ritardo di almeno 30 % (tutte), la quota misurata con P1 è **minore** di quella con P0 (IC bootstrap 95 % della differenza interamente < 0 oppure, se non si può dire, nessun verdetto di conferma) e la mediana per sito con P1 è minore di quella con P0. **Falsificata** se in almeno 3 condizioni su 9 P1 non riduce le consegne in ritardo.
- **T-3 (sicurezza):** la quota di episodi con almeno un sito in pending con P1 non supera quella con P0 di più di 3 punti in nessuna condizione. **Falsificata** altrimenti.
## Cosa non si fa
Nessuna modifica di previsioni o criteri dopo i dati; nessuna sostituzione delle misure del nodo; i risultati del banco non entrano in `results/`; se T-0 fallisce, si riporta e si ferma.
