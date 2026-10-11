# Audit 54 — Risultati di audit 53: ablation C_s-only / C_t-only e sweep dello split 0,7/0,3 sui tre laboratori reali

Data: 2026-10-11. Codice: `experiments_tnsm/split_ablation/analyze_split.py` (test `test_analyze_split.py`: 55 passed; mutazioni catturate: scambio di w, gate rimosso, m = 1, β fisso, quorum del controllo H-S2; sopravvissuta: `>` al posto di `≥` sulla soglia, che richiede un pareggio esatto di float, mai osservato). Esecuzione: `python3 experiments_tnsm/split_ablation/analyze_split.py --out experiments_tnsm/split_ablation/run_20261011`, Python 3.10.13; dati letti in place; manifest con sha256 degli ingressi in `experiments_tnsm/split_ablation/run_20261011/manifest.json`; solo aggregati per ricevente (nessun valore per dispositivo). **Validità:** V0 riproduce esattamente l'insieme `locked` in tutti e tre i riceventi (asserzione di `run()` superata, altrimenti nulla sarebbe stato scritto). Ipotesi e criteri: audit 53 (committato prima del codice).

## Verdetti
- **H-S1 FALSIFICATA.** L'insieme dei candidati cambia rispetto a V0 per w ∈ {0,8; 0,9} in **US** (+2 fatti) e **YT** (+6 fatti); per w = 0,6 coincide in tutti e tre i riceventi; UK coincide per w ∈ {0,6; 0,8; 0,9}. Quindi lo split conta, ma **solo verso l'alto** (più peso ai giorni ammette fatti in più) e di poco: nessun fatto in meno nel range 0,6-0,9. A w = 0,5 UK perde 2 fatti (41 contro 43; fuori dal range di H-S1, descrittivo).
- **H-S2 non falsificata:** Cs-only coincide con {|S_e| ≥ 2, classe eleggibile} in US, UK e YT (38, 43, 129 candidati nei dispositivi bersaglio).
- **H-S3 non falsificata:** Ct-only ⊆ V0 nei tre riceventi.

## Tabella (aggregati per ricevente)
| ricevente | variante | candidati | \|Δ\| con V0 | precisione | recall | F1 |
|---|---|---|---|---|---|---|
| US | V0 | 36 | 0 | 0.7500 | 0.0650 | 0.1159 |
| US | w0.0 | 0 | 36 | 0.0000 | 0.0000 | 0.0000 |
| US | w0.5 | 36 | 0 | 0.7500 | 0.0650 | 0.1159 |
| US | w0.6 | 36 | 0 | 0.7500 | 0.0650 | 0.1159 |
| US | w0.8 | 38 | 2 | 0.7500 | 0.0678 | 0.1203 |
| US | w0.9 | 38 | 2 | 0.7500 | 0.0678 | 0.1203 |
| US | w1.0 | 38 | 2 | 0.7500 | 0.0678 | 0.1203 |
| US | Cs-only | 38 | 2 | 0.7500 | 0.0678 | 0.1203 |
| US | Ct-only | 7 | 29 | 0.5000 | 0.0203 | 0.0385 |
| UK | V0 | 43 | 0 | 0.7838 | 0.0644 | 0.1151 |
| UK | w0.0 | 0 | 43 | 0.0000 | 0.0000 | 0.0000 |
| UK | w0.5 | 41 | 2 | 0.7896 | 0.0631 | 0.1133 |
| UK | w0.6 | 43 | 0 | 0.7838 | 0.0644 | 0.1151 |
| UK | w0.8 | 43 | 0 | 0.7838 | 0.0644 | 0.1151 |
| UK | w0.9 | 43 | 0 | 0.7838 | 0.0644 | 0.1151 |
| UK | w1.0 | 43 | 0 | 0.7838 | 0.0644 | 0.1151 |
| UK | Cs-only | 43 | 0 | 0.7838 | 0.0644 | 0.1151 |
| UK | Ct-only | 23 | 20 | 0.4815 | 0.0402 | 0.0741 |
| YT | V0 | 107 | 0 | 0.2857 | 0.2229 | 0.2472 |
| YT | w0.0 | 1 | 106 | 0.0000 | 0.0000 | 0.0000 |
| YT | w0.5 | 107 | 0 | 0.2857 | 0.2229 | 0.2472 |
| YT | w0.6 | 107 | 0 | 0.2857 | 0.2229 | 0.2472 |
| YT | w0.8 | 113 | 6 | 0.2746 | 0.2229 | 0.2425 |
| YT | w0.9 | 113 | 6 | 0.2746 | 0.2229 | 0.2425 |
| YT | w1.0 | 113 | 6 | 0.2746 | 0.2229 | 0.2425 |
| YT | Cs-only | 129 | 22 | 0.2274 | 0.2229 | 0.2123 |
| YT | Ct-only | 18 | 89 | 0.2292 | 0.1017 | 0.1156 |

## Lettura (descrittiva, nessuna ottimizzazione di w)
- **La persistenza è ciò che separa DIB dal solo quorum:** Cs-only (= quorum + classe) ammette 2 fatti in più a US (38 contro 36), 0 a UK (43) e 22 in più a YT (129 contro 107). A YT quei 22 fatti non aggiungono recall (0,2229 in entrambi) e abbassano la precisione (0,2274 contro 0,2857): il termine di persistenza taglia, su YT, fatti che non sono nel riferimento.
- **Ct-only (θ = 0,65) è molto più stretto di V0** (7, 23, 18 candidati contro 36, 43, 107): a C_s = 1 la soglia di DIB su C_t è 1/8, non 0,65 (audit 44 §3); il punteggio additivo rende il breadth un "credito" che abbassa la soglia di persistenza.
- **Lo split pesa poco nel range 0,6-0,9** (≤ 6 fatti su 107 a YT, ≤ 2 su 36-43 a US/UK) e **w = 0 (solo frequenza) svuota il risultato** (0 candidati a US e UK, 1 a YT): la frequenza da sola non raggiunge la soglia 1/8, coerentemente con la nota del paper che f = n_{d,e}/n_d è piccola. Il valore 0,7/0,3 non emerge come ottimo da questi dati; è nel plateau di un intervallo ampio.
- **Limite:** 3 riceventi, due sorgenti ciascuno: C_s costante; il risultato riguarda C_t, non il breadth. Nessun IC (deterministico, n = 3). Non generalizza oltre i tre laboratori.
