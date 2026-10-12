# Audit 77 — Pre-registrazione: il fan-out parallelo contro quello sequenziale nel banco netns (validazione della decisione sul default di concorrenza)

Data: 2026-10-12. Contesto: le connessioni persistenti non si propongono (audit 76). Resta la leva che ha già evidenza forte sul nodo (B5: D 10,3 s con FANOUT 1 contro 1,6 s con FANOUT 10 a 200 ms e 5 %): il **default** `min(N_SITES, 16)` introdotto nel commit `16a6db0`. Qui lo si valida su **9 condizioni di rete diverse** nel banco di prova (audit 75-76, stesso `service.py`, plain HTTP, 10 siti) e si testa la parte sequenziale del modello v2, che somma 10 consegne e dipende meno dalla struttura della coda.

## Previsioni del modello v2 (calcolate PRIMA dei dati; 20 000 episodi, seme 20261012, arm D, RTO attivo)
| delay one-way ms | loss | model median last-site, sequential (S1) ms | model p95 S1 ms | model median, parallel (P0) ms | predicted ratio S1/P0 |
|---|---|---|---|---|---|
| 50 | 2% | 2250 | 3950 | 150 | 15.0 |
| 50 | 5% | 3250 | 5250 | 1150 | 2.8 |
| 50 | 10% | 4550 | 7750 | 1150 | 4.0 |
| 100 | 2% | 4500 | 5900 | 300 | 15.0 |
| 100 | 5% | 5500 | 7700 | 1300 | 4.2 |
| 100 | 10% | 7100 | 10500 | 1300 | 5.5 |
| 200 | 2% | 8800 | 10800 | 600 | 14.7 |
| 200 | 5% | 10200 | 13600 | 1600 | 6.4 |
| 200 | 10% | 12200 | 16400 | 2000 | 6.1 |

La previsione del rapporto a (50 ms, 5 %) è 2,8 perché la mediana del parallelo salta a 1 150 ms (episodi con una consegna in ritardo di 1 s al 50 %): è la cella più sensibile.

## Misura
Come audit 75: episodi con netem acceso, tempi fuori banda dalle righe SQLite. Politica **S1** = `DIB_DIST_FANOUT_CONCURRENCY=1` (sequenziale, connessione nuova per tentativo, nessun keep-alive); riferimento **P0** = i dati del run 2 (`run_20261012b`, `FANOUT_CONCURRENCY=10`, stesso codice e stesso banco, 60 episodi per cella; dichiarato ora). **40 episodi per cella S1** (n da vincolo di tempo), 9 celle, tetto di attesa per episodio 120 s (il default di 30 s taglierebbe gli episodi sequenziali lenti e distorcerebbe la mediana). Mediana e p95 dell'ultimo sito sugli episodi **completi** (tutti i 10 siti applicano), IC bootstrap 95 % della mediana (10 000 ricampionamenti, seme 20261012), quota di episodi incompleti riportata.

## Ipotesi e criteri (fissati ora)
- **T-S0 (validità):** per costruzione S1 deve essere sequenziale: in ogni episodio completo i tempi di applicazione dei 10 siti, ordinati, crescono di almeno 0,5·n_RTT·R tra siti consecutivi in mediana (la consegna al sito i+1 parte dopo il ritorno della precedente). **Falsificata** se la mediana degli intervalli fra applicazioni consecutive è < 0,5·R·1,5 = 0,75 R in più di 2 celle.
- **T-S1 (modello sequenziale):** la mediana misurata dell'ultimo sito sta entro ±25 % della previsione in **almeno 7 celle su 9**; altrimenti "non validato". Descrittivo: p95 contro previsione.
- **T-S2 (decisione sul default):** il rapporto mediana(S1)/mediana(P0) è **≥ 2,0 in tutte le 9 condizioni** (la previsione minima è 2,8). **Falsificata** se in una condizione il rapporto è < 2,0. Se regge, il default parallelo è giustificato come riduzione ≥ 2× del tempo di ritiro su tutto l'intervallo di RTT (100-400 ms) e perdite (2-10 %) provato.
- **Cosa non si fa:** nessun cambio di criteri dopo i dati; il risultato non sostituisce B5 (nodo, Docker) e non va in `results/`.
