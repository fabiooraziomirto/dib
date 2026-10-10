# Audit 09 — Derivazione dei parametri di ammissione e giustificazione di f_s = 0.30

Data: 2026-10-10. Base: `main 48.tex` (originale non modificato). Modifiche solo in Sec. IV-C (Candidate-Selection Policy) e nella bibliografia.

## File in questa repo

| File | Cosa è |
|---|---|
| `analysis_fs/fs_binomial.py`, `analysis_fs/out/fs_binomial.csv` | Probabilità che la guardia fallisca con siti avversari indipendenti (Fraction per la soglia) |
| `analysis_fs/test_fstar_math.py` | Verifica esatta di f*, della forma in conteggi e degli esempi (7 test) |

Il paper non è in questa repo (regola di `CLAUDE.md`): la copia modificata `main_48_proposta.tex` e il diff restano fuori.

## Cosa è cambiato nel testo

1. **Frase su 0.7/0.3 (riga ~389).** Corretta: i conteggi sono aggregati senza normalizzazione per sito, quindi un solo reporter può fornire tutto il termine di volume (al massimo 0.3·β = 0.12) e, riportando ogni giorno attivo, tutto il termine di copertura. C_t entra nel Criterion 1 solo tramite C_t ≤ 1. Base nel codice: `dib.py:278` (nessuna normalizzazione per sito), da `analysis_fs/REPORT.md` H1.
2. **Nuovo paragrafo "Parameter derivation" con Eq. (fstar).** f* = (θ−β)/α = 1 − (1−θ)/α = 5/12. Due letture: massima quota avversaria assorbita dal solo score, e minima ampiezza con cui un fatto benigno può passare anche con persistenza perfetta. Così θ, α e il margine non sono "scelti a caso": restano due parametri legati da una sola quantità.
3. **Criterion 1.** Ultima frase riscritta con f_s < f*.
4. **Paragrafo dopo il Criterion.** Aggiunti: bound = supremum mai raggiunto (serve C_t = 1, quindi nessuna osservazione onesta di d), forma in conteggi con r = (θ+α−1)/(1−θ) = 5/7: lo score da solo respinge l'evidenza puramente avversaria sempre se K ≤ 5h/7 (pareggio incluso); oltre il rapporto l'ammissione è possibile ma non certa (dipende dal volume ρ: es. K=8, h=11 solo con ρ ≳ 45); il quorum m = 2 respinge K = 1 a prescindere (verifica sul DIBScorer: `docs/audit/11_hd_distribution.md` sez. 1), esempio con tre colluder (almeno 5 siti onesti al margine, almeno 7 a f_s = 0.30).
5. **Nuovo paragrafo "Why f_s = 0.30".** f_s presentato come budget sotto il margine (0.117 sotto 5/12) e sotto 1/3 bizantino, non come prevalenza misurata. Ancoraggi empirici in letteratura (sotto).
6. **Nuovo paragrafo probabilistico.** Da prevalenza per dispositivo p a probabilità per sito q = 1−(1−p)^n, poi probabilità che la guardia fallisca: K ≥ ⌈5N/12⌉ con K ~ Binomiale(N, q). Con q = 0.10: 1.6e-3 (N=10), 6.0e-5 (N=20), 3.7e-9 (N=50). Con q = 0.30: 0.15, 0.11, 0.048.
7. **Bibliografia.** Aggiunte 4 voci (`lamport1982byzantine`, `castro1999pbft`, `kumar2019allthings`, `zhao2022largescale`). `mirai` esisteva già.

## Verifica

- Controllo con `Fraction`: f* = 5/12; bound 0.58 a f_s = 0.30; equivalenza `K/(K+h) < 5/12 ⇔ K < 5h/7` su K ≤ 39, h ≤ 79; esempio dei tre colluder (h = 5 e h = 7); margine 7/60 = 0.117; q = 0.34 per p = 0.10, n = 4.
- Il paper completo non compila qui perché manca la classe IEEEtran; compilata solo la sezione modificata (nessun errore). **Compila il `.tex` completo sul tuo ambiente.**

## Fonti: verificate sui PDF (10 ott 2026)

| Citazione | Esito |
|---|---|
| Antonakakis et al., USENIX Sec 2017, pp. 1093-1110 | Confermato: picco di 600.000 infezioni a fine novembre 2016 (§4.2). Il paper non stima la quota di device compromessi. Aggiunte le pagine alla voce già presente |
| Kumar et al., USENIX Sec 2019, pp. 1169-1185 | Titolo e autori confermati. L'1.3% è "dei device nelle case che scansionano" (0.37% delle case), compromessi via backdoor EternalBlue; il paper avverte che i dati di scansione di solito non indicano la compromissione. **Frase del `.tex` corretta di conseguenza** |
| Zhao et al., IEEE TDSC vol. 19 n. 3, pp. 1826-1840, mag/giu 2022 (DOI 10.1109/TDSC.2020.3037908) | Confermato: 1.362.906 device, 385.060 (28.25%) con almeno una vulnerabilità N-day. L'intervallo per vendor nel testo ora è "sotto 0.5% (alcuni vendor ICS) fino a 100% (Octoprint)", ricavato dal testo; la Tabella 5 è un'immagine non estraibile. Il "0.04%" che avevo scritto prima non è verificabile e l'ho tolto |
| Lamport–Shostak–Pease, ACM TOPLAS 4(3), luglio 1982, pp. 382-401 | Confermato, compreso "risolvibile se e solo se più di due terzi dei generali sono leali" (oral messages) |
| Castro–Liskov, OSDI 1999, New Orleans, 22-25 feb 1999, pp. 173-186 | Confermato venue e pagine dal sito USENIX; soglia n ≥ 3f+1 / "no more than ⌊(n−1)/3⌋ replicas are faulty" confermata nella sezione "Service Properties" |

## Assunzioni e limiti del modello probabilistico

- Indipendenza tra siti e tra device (ipotesi H1/H3 nello script). Con firmware o cloud condivisi la coda reale è più pesante.
- La guardia riguarda solo evidenza avversaria pura (fatto riportato solo da avversari), come nel Criterion 1.
- Il collegamento A1: un sito è "avversario" se ospita un device compromesso del tipo d e ne riporta i flussi reali. Va dichiarato nel threat model (Sec. III, fuori ambito per ora).

## Commenti `%` rimossi dal .tex

Ho tolto i tre commenti sul 30% (righe 393-395) e la frase "We choose weights that reject...". Dell'ultimo commento ("giochi cooperativi, competitivi, azienda... azionisti o % di rischio") non ho trattato l'idea di teoria dei giochi: se vuoi svilupparla, va recuperata dall'originale.

## Non toccato (da fare)

- Sec. III: refuso "A1 tests -----." (riga 177), riscrittura G1–G4 e threat model.
- Riga 523-526: "micro" per 65.5% (36/55) e aggiunta del 63.2% macro (claims.json: `observable_retention`).
- Riga 631: 0.562 è il massimo con trust weighting; con breadth grezza e worst case si arriva a 0.579 (`analysis_fs/paper_edits_proposed.md`, modifica 2). Riga 627: A2 con k esplicito.
- Ablation C_s-only / C_t-only e sweep del 0.7/0.3 (nel testo ho scritto solo che lo split non entra nel bound, non che l'ablation esista).
- Righe 35-36: markup `\del`/`\add`.

## Passi successivi per i test

- Regole della repo (`CLAUDE.md`): non toccare `code/src`, `formal/`, `claims.json`, `results/`; scrivere i risultati in `docs/audit/`; dichiarare le ipotesi prima di ogni esperimento.
- Candidati per i test: (a) rieseguire `analysis_fs/bound_grid.py` con (α, θ) variabili e confrontare con f*; (b) un test che verifichi la forma in conteggi K < ((θ+α−1)/(1−θ))h su `DIBScorer`; (c) simulare la frazione di fallimenti della guardia con siti avversari estratti da Binomiale(N, q) e confrontarla con `fs_binomial.csv`; (d) latenza e throughput con almeno 10 ripetizioni (oggi 3–5), vedi `docs/work/DIB_piano_completo.md` §7.2 e §7.6.
