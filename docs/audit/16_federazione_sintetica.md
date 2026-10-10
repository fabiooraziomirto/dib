# Audit 16 — Federazione sintetica: DIB contro ranked union sotto A2 (Passi 6a e 6)

Data: 2026-10-10. Branch `revision-tnsm`. Piano: `14_priorita_esperimenti_tnsm.md` §4 (rev. 5) e GATE 1 e 4 (§3). Il numero 15 è riservato al diff di G0b (Passo 2). Notazione: [C] verificato nel codice o nei dati; [D] deduzione.

## 1. Passo 6a: istogramma reale di h_d (riuso, nessun download)

Nessun dato nuovo: si riusano i risultati di audit 11 (§2.3 e §2.6). File di ancoraggio per il generatore: `experiments_tnsm/synthetic_federation/anchor_hd.json`. Contiene solo conteggi di tipi, senza etichette di dispositivi, quindi nessun dato derivato da Mon(IoT)r con etichette.

| Variante | h = 1 | 2 | 3 | 4 | 5 | Tipi | Fonte |
|---|---|---|---|---|---|---|---|
| 4 siti indipendenti (UNSW, Mon(IoT)r US, UK, YourThings) | 87 | 28 | 1 | 3 | 0 | 119 | `analysis_fs/out/hd_union_histogram.csv` (sha256 `80333491…`), corpus `union_canonical_h_indep` |
| più NCSU, mapping stretto | 87 | 28 | 1 | 2 | 1 | 119 | audit 11 §2.6: ring-doorbell passa da 4 a 5 |
| **più NCSU, mapping per famiglia (ancora usata)** | 83 | 31 | 2 | 1 | 2 | 119 | audit 11 §2.6: 7 tipi guadagnano un sito |

- Mediana di h_d = 1 in tutte le varianti; al più 5 siti indipendenti.
- Come ancora si usa la variante "per famiglia", la più favorevole alla guardia fra quelle misurate. [D] Con h ≤ 5, K = 2 a f_s = 0,30 è coperto al più su 2 tipi e K = 3 su nessuno (audit 11 §2.6).
- **Dichiarazione (piano, Passo 6a):** il Passo 6 con N ≥ 10 esplora una popolazione **più favorevole alla guardia** di quella reale.
- Estensioni opzionali (PingPong, HomeSnitch): non avviate. Ognuna richiede un OK separato e aggiunge al più un sito.
