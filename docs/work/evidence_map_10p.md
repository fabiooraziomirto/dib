# Mappa delle prove della bozza da 10 pagine (`docs/main_10p.tex`, costruita da `docs/work/build_10p.py`)

`main_wip.tex` non è stato modificato. Ogni affermazione sperimentale nuova dell'Evaluation poggia su un audit pre-registrato e su dati con sha256 (cartella `experiments_tnsm/`).

| Affermazione nel testo | Prova | Audit |
|---|---|---|
| Convergenza dopo kill e riavvio: mediana 0,6-4,1 s, 28 celle, 30 prove (834 completate), k fino a 50 a `lan`, 3 su 234 oltre il limite a `degraded` | `final_B2k_20261012` + `final_B2k_b_20261012` | 99 (pre-reg), 106, 110 |
| Causa della coda con mTLS (timeout dell'handshake al primo tentativo di riconciliazione, `service.py:699`) | log del sito 3 nella seconda serie | 110 |
| Ritiro a `degraded`, due repliche del codice finale (tabella VII) | `final_R1e_20261012`, `final_R1f_20261012` | 104 (pre-reg), 105, 108 |
| Modello senza mTLS entro 3,4 punti in cinque condizioni; con mTLS stima per difetto di 3-7 punti | X1-X4 sul deployment | 107 (pre-reg), 109 |
| Modello verificato fuori campione nel banco netns (sei condizioni, entro 1,7 punti) | `netns_testbed` | 75-82 |
| Fan-out concorrente 3,1-7,1 volte più veloce; 3 280 episodi con perdita senza siti non riconciliati | banco netns | 79, 81 |
| TLC: 4 311 852 e 48 960 stati (modello originale); 402 633 492 stati con 3 eventi e partizioni, cinque mutanti | `formal/` (invariato), `tla_fsm` (altra sessione) | 63-68, 92-93 |
| TLC v8 (letture fallite, giri di reconcile abbandonati, crash/riavvio con pulizia D1): X4b_V5 3 eventi 154 363 430 stati; quorum 2, 2 perdite, 2 fatti, 3 siti (712 287 745 stati), tutti senza violazione; V3 stretta FALSIFICATA con letture fallite (traccia sez. 7.2), vale V5; limiti: concorrenza, convergenza a 3 eventi con fallimenti | `DIB_tnsm_v8` branch `tnsm-fsm-v8`, audit 110 sez. 7-11 (numero in collisione con il mio 110, da rinumerare al merge) | 110 (v8) |
| Modello di autorizzazione mTLS: dieci configurazioni senza controesempio, sei mutanti | `tla_authz` (altra sessione) | 111-112 |
| Resto dell'Evaluation (mutanti M1-M6, ablazione del restore, gateway osMUD, selezione dei candidati, avversari) | invariati rispetto a `main_wip.tex` | v43-import, `results/` |

## Placeholder nella bozza
1. Modello v8 (guasti di lettura e crash): in attesa dell'altra sessione.
2. Ambito del modello di autorizzazione: tempo della revoca e certificati multi-SAN (audit 112 sez. 4).
3. Sospensione: cifre di tempo di ritiro e throughput di lettura da rimisurare sul servizio finale.
4. Nota rossa dell'autore nel Related Work (paragrafo di differenziazione), lasciata com'era.

## Cosa è stato tolto o ridotto rispetto a `main_wip.tex` (nell'artefatto)
Tabella di posizionamento, tabella delle configurazioni di scoring, tabella di ablazione del restore (il risultato resta nel testo), paragrafi sulle misure del registro in-process e dello sweep del throughput per numero di siti (dati vecchi non riutilizzabili), figura di Pareto, il paragrafo sull'output RFC 9761 e due frasi su ECH/QUIC, il paragrafo di roadmap dell'introduzione, due paragrafi di Discussion, quattro voci bibliografiche non più citate.

## Numeri non rimisurati sul codice finale (da verificare)
- "riconciliazione 71 ms in media, al massimo 105 ms" (frase dell'abstract e della sezione B): misura sul codice congelato (claims.json).
- Prove di sospensione e quorum a due segnalatori: campagna API del servizio originale (qualitative nel testo).
