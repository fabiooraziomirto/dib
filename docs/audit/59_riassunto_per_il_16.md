# Audit 59 — Riassunto per l'incontro del 16 ottobre: cosa è stato misurato, cosa regge, cosa no

Scritto per: il supervisore e l'autore, come base di discussione. Data: 2026-10-11. Fonti: audit 47-58 (ogni numero ha lì file e riga). Tutto su un solo nodo (CPU QEMU generica, altri carichi di fondo); nessun confronto fra macchine; nulla è stato scritto nel paper né in `results/`.

## Risultati
| Voce | Esito | Audit |
|---|---|---|
| **Ritiro dopo riconnessione (B2k)**, `lan` k = 1, `degraded` e `wan` k = 1, 10; D e C; 10 prove per cella | mediana della convergenza sotto il bound in 24/24 celle valutabili (0,6-4,3 s contro bound 7-8,6 s); 0 violazioni di (e) su 212 prove; coda vicina al bound a `degraded`/C (massimo 98,6 %); **k = 50 e `lan` k = 10 non misurati** (esclusioni a cascata dopo un timeout del client, bug del driver congelato) | 57 |
| **Ritiro sotto rete degradata (B5)** | (a′) **falsificata 4/4**, anche con p più permissivo; (c) **inconclusa** (D 5/1000, C 21/960); il modello non predice il tempo di ritiro a `degraded` (misure 1,6-18,5 s) | 56 |
| **DIB contro quorum + persistenza sui tre laboratori reali** | stessi insiemi di fatti (|Δ| = 0 in US, UK, YT); con due sorgenti C_s è costante, il breadth non è sollecitato | 47 |
| **Regione di ammissione di DIB** | = quorum frazionario φ = 5/12 con soglia di persistenza decrescente (1,625 − 1,5·C_s); verificata sul `DIBScorer` reale (43 test, mutazioni catturate) | 48 |
| **Parametri** | m = 2 vincola solo per N ≤ 2 (m = 3: N ≤ 4); sui tipi reali m = 3 lascerebbe 5 tipi ammissibili contro 36; ρ = 100 indistinguibile dal limite; (0,55; 0,6) non soddisfa il Criterion a f_s = 0,30; lo split 0,7/0,3 sta in un plateau (w 0,6-0,9: al più +2/+6 fatti), la frequenza da sola svuota il risultato; la persistenza toglie 22 fatti a YT senza perdere recall | 49, 52, 54 |
| **Firma MUD (M8)** | sign + verify con `openssl cms`: mediana 6,8-7,0 ms (ECDSA P-256), 8,0-8,2 ms (RSA-2048), p95 9,2-10,0 / 10,8-12,0 ms; "p95 < 10 ms" **falsificata per RSA-2048**; circa 3,3 ms sono lo spawn | 58 |

## Claim che i dati sostengono (e quanto)
1. Dopo una riconnessione il sito converge entro un limite misurato in tutte le celle valutabili, senza violazioni di consistenza finale — **buono per k ≤ 10, un nodo, IC larghi, coda non stimata**.
2. La regola di ammissione è un quorum frazionario con persistenza decrescente e protezione identica contro evidenza solo-avversaria — **forte (derivazione verificata sul codice)**, non un test su dati.
3. Il peso della persistenza taglia fatti non nel riferimento (YT) — **descrittivo, 3 laboratori, 2 sorgenti**.

## Cosa il paper non può dire
Che il tempo di ritiro sotto rete degradata sia prevedibile; che il breadth additivo sia un contributo dimostrato sui dati reali; che (c) sia confermata; nulla su k = 50; nessuna garanzia di coda.

## Decisioni per il supervisore
- **Q14:** inquadrare il breadth come "quorum relativo calibrato" (audit 48) o cercare dati con più sorgenti.
- **Q2/Q4+Q5:** lease (limite durante la disconnessione) e ambito di B2-partition: oggi nulla misurato.
- **Rifare `lan` k = 10/50 di B2k:** richiede una correzione del driver (nuovo tree e hash) o una pre-registrazione dell'ordine di k; non è stato deciso.
- **Q13:** punteggio o quorum + classe + persistenza come eligibility di default.
