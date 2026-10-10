# main_tnsm.tex: elenco delle modifiche (riportabili)

Punto di partenza: `main_tnsm.tex` = copia identica di `DIB_clean/docs/main.tex`, sha256 `3fdd7489214f328e0384d2553b30da086480ca7717ac0fb26c6a2c59548f9437` (commit `3f37dc3`). Per estrarre le modifiche: `git diff 3f37dc3 HEAD -- docs/main_tnsm.tex` (o un commit per gruppo, sotto). Righe = `main_tnsm.tex` dopo i gruppi indicati. Non applicati: goal (attesa del 16 ottobre), gruppo 5 e 6.

| Gruppo | Commit | Righe | Cosa cambia | Perché |
|---|---|---|---|---|
| 1 | `6478e6c` | 172, 177, 396, 398, 400, 644, 652 | "raw breadth" esplicito in assunzione su f_s, definizione di A2, paragrafo f*, titolo e testo del Criterion, rimandi al Criterion in VI-D e VI-E | il Criterion era qualificato raw solo a old:408/414; la config selezionata (YAML) è pesata (audit 19 §2, §8) |
| 2 | `153ca76` | 656 | paragrafo port masquerading: dichiara config pesata, seed 42, 10 pseudo-siti; 0,562 = massimo della strategia, non del modello; worst case raw 0,579; 0,663 sotto trust | "consistent with 0.58" confrontava dati pesati con un bound raw (audit 08 §7 W4) |
| 3 | `680fe72` | 673 | "P5" sostituito da riferimento al Criterion 1 (raw) | "P5" mai definito |
| 4 | `874aafb` | 343, 440 (tab:configs), 572, 636 | nuova tabella esperimento → configurazione; config nei caption di tab:symbols, tab:threelab, fig:pareto | il paper mescolava raw e pesato senza dirlo |
| 5 | da fare | | 245 casi come limite della config pesata + breadth calcolata dal registro su osservazioni inviate dal sito | audit 16 §5.1, §5.4 |
| 6 | da fare | | numeri fault_injection allineati a `062b417` (0,48 ± 0,02 s; 0,51 ± 0,03 s; riavvio 0,416 s; riconciliazione media 0,071 s, max 0,105 s) | `results/fault_injection/README.md` |

Note:
- Il valore 0,579 (gruppo 2) viene da `analysis_fs/worst_case_real.py` (audit 08 §7), non da `results/`; il paper lo cita senza file di `results/` a supporto: da decidere se promuoverlo.
- Le righe della tabella `tab:configs` seguono `results/*/manifest.json`; la riga "A1 baseline … raw" si basa su `compromised_baseline.py:60-66` (vanilla forzato). Controllare al momento dell'applicazione.
- Compilazione di prova: `pdflatex` 11 pagine, nessun errore (PDF non salvato in repo).
