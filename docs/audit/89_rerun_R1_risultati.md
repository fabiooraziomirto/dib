# Audit 89 — R1: deployment completo sul codice corretto (`tree-dc3dd20`): verdetti dell'audit 88

Pre-registrazione: `docs/audit/88_prereg_rerun_codice_corretto_R1.md` (committata prima del lancio, bbc4d49). Dati: `experiments_tnsm/rerun_R1_20261012/` (copiati con sha256, 0 differenze, pcap esclusi). Run 2026-10-12T06:37:06Z → 07:59:18Z, rc=0, 200 episodi, 0 container rimasti. Codice: commit `dc3dd20`, `service.py` `5599f53b…129be`. Analisi: `analyze_deploy.py` e `compare_deploy.py` (nessuna soglia cambiata dopo i dati).

## Verdetti come pre-registrati
| arm | FANOUT | episodi | esclusi | quota in ritardo per sito (previsione v4) | mediana ultimo sito ms [n] (previsione v4) |
|---|---|---|---|---|---|
| D | 10 | 50 | 1 | 0.166 (0.179) | 1618 [46] (—) |
| D | 1 | 50 | 0 | — | 10771 [44] (10600.0) |
| C | 10 | 50 | 2 | 0.335 (0.251) | 2677 [30] (—) |
| C | 1 | 50 | 2 | — | 17806 [33] (16400.0) |

## Verdetti

- **H-N1 (applicatore equivalente a B5):** regge (D/10 0.166 contro 0,178; C/10 0.335 contro 0,310; tolleranza ±0,04).
- **H-N2 (modello):** NON regge (D/10 contro 0,179 ±0,04; C/10 contro 0,251 ±0,08; F1 D 10771 contro 10 600, C 17806 contro 16 400, ±25 %).
- **Modello v4 validato sulla distribuzione completa: NO.**

### Confronto con il codice vecchio (audit 86), H-R1b

| cella | vecchio | nuovo | differenza |
|---|---|---|---|
| late share D10 | 0.186 | 0.166 | -0.020 (soglia ±0,04) |
| late share C10 | 0.282 | 0.335 | +0.054 (soglia ±0,04) |
| mediana ultimo sito D1 ms | 10670 | 10771 | +1.0 % (soglia ±15 %) |
| mediana ultimo sito C1 ms | 16126 | 17806 | +10.4 % (soglia ±15 %) |

**H-R1b: FALSIFICATA, celle fuori soglia: C10.**

**Sintesi dei verdetti:** H-N1 regge. **H-N2 è FALSIFICATA** per la sola cella C/10 (0,335 contro 0,251: scarto 8,4 punti, soglia ±8; D/10 e le due mediane a FANOUT 1 sono dentro). **H-R1b è FALSIFICATA** per la sola cella C/10 (+5,4 punti contro soglia ±4; D/10, D/1 e C/1 dentro). Secondo l'audit 88 si riporta com'è, senza ritoccare soglie, e si indaga prima di proseguire con R2-R6.

## Indagine (POST-HOC, dichiarata tale: non cambia i verdetti sopra)
Intervalli bootstrap al 95 % sugli episodi (5 000 ricampionamenti, seed 1) della quota in ritardo per sito, episodi non esclusi:

| arm | codice | episodi | quota | IC 95 % |
|---|---|---|---|---|
| D/10 | vecchio (86) | 50 | 0,186 | [0,152; 0,222] |
| D/10 | nuovo (R1) | 49 | 0,166 | [0,129; 0,206] |
| C/10 | vecchio (86) | 49 | 0,282 | [0,242; 0,320] |
| C/10 | nuovo (R1) | 48 | 0,335 | [0,281; 0,400] |

- Differenza C/10 nuovo meno vecchio: IC 95 % [−0,013; +0,127], contiene 0: la differenza fra repliche non è distinguibile dal rumore a 50 episodi.
- C/10 nelle tre repliche disponibili sullo stesso nodo: 0,310 (B5), 0,282 (audit 86), 0,335 (R1); il modello prevede 0,251. L'arm C è sottostimato in tutte e tre, di 3,1-8,4 punti (B5: 5,9). La tolleranza ±8 punti, scelta prima dei dati da un solo confronto retrospettivo, era più stretta della dispersione fra repliche.
- D/10 e le mediane a FANOUT 1 sono stabili fra le due repliche (D/10 0,186 e 0,166; D/1 10 670 e 10 771 ms; C/1 16 126 e 17 806 ms, +8,6 % rispetto alla previsione).
- Esclusi: 1 (D/10), 0 (D/1), 2 (C/10), 2 (C/1), contro 0, 0, 1, 1 del vecchio; le mediane dell'ultimo sito usano gli episodi completi (n: 46, 44, 30, 33).
- Nessuna evidenza che le correzioni cambino il percorso misurato: la review (audit 87) non prevedeva effetti, e le celle D e C/1 sono stabili. Ma una differenza di 5,4 punti in C/10 non si può escludere con 50 episodi.

## Cosa si conclude
- Il modello v4 sul deployment completo: **valido senza mTLS** (D/10 entro 1,5 punti in due repliche) e per la mediana dell'ultimo sito a fan-out sequenziale (entro 9 %); **sottostima la quota in ritardo con mTLS** di 3,1-8,4 punti (due repliche qui, tre con B5). Non si può più scrivere "entro 8 punti". La causa dichiarata resta l'ipotesi dei segmenti TLS non modellati (audit 86), non dimostrata.
- Paper: la frase di `main_wip.tex` (nel paragrafo del modello di consegna) è stata riscritta di conseguenza e compila a 13 pagine.
- Limiti: una sola macchina; 2 repliche di 50 episodi a `degraded`; le repliche sono a ore diverse sullo stesso nodo; il vecchio e il nuovo codice differiscono anche per l'albero (non solo per `service.py`).
