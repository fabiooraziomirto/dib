# M1 interrotto il 2026-10-10: celle conservate, NON analizzate

**Non usare questi dati in nessuna statistica, figura o affermazione del paper.**

**Configurazione censurata.** Queste celle sono state generate con la configurazione di **default** del database (`DIB_SQLITE_WAL` e `DIB_SQLITE_POOL_SIZE` non impostati: journal_mode=delete, pool di 5 + 10 connessioni, timeout di checkout di 30 s). A 100 writer il p99 è **censurato** a 30 s dal timeout del pool (es. 30001,1 ms nella prima cella del log): è un tetto, non una latenza. Non sono confrontabili con il braccio `deploy` del rerun (Passo 7) e non sostituiscono il braccio `default` del rerun.

- **Cosa:** run M1 (`experiments_tnsm/m1_single_node/run.py`, commit `c23d1e3`) sul nodo 192.168.100.57, configurazione SQLite e pool di default.
- **Perché interrotto:** riprioritizzazione (piano rev. 5, audit 14). Con la configurazione di default il p99 a 100 writer è troncato a 30 s dal timeout di checkout del pool di SQLAlchemy (audit 04 §7.4). M1 sarà rifatto con due bracci, `default` e `deploy` (Passo 7).
- **Stop:** `kill -TERM 22376` (solo il PID, verificato con `ps` che fosse ancora `run.py … --commit c23d1e3`) alle **2026-10-10T17:14:10Z**. Il processo è uscito entro 3 s, senza processi residui.
- **Celle scritte: 40 su 50** (n_workers 100: 17, 1: 9, 10: 8, 50: 6). La cella 41 (100 writer, warm-up in corso) non è stata scritta.
- **Validazione:** tutte le 40 righe di `cells.jsonl`, compresa l'ultima, sono JSON valido (`json.loads`); nessuna riga troncata. I file non sono stati modificati.
- **File, copiati dal nodo (`~/dib_tnsm/out/`) senza modifiche:**
  - `cells.jsonl`, sha256 `e50d5f97c180344177ff65863c17ce1c6d005d88de474805745380c5b9ed8644`;
  - `m1.log` (stdout e stderr del run), sha256 `a7d30a2725b542766a39ed54de71f23a93bcf83afea867c0af15d9a62f3c9ec0`. È aggiunto con `git add -f`, perché `*.log` è in `.gitignore`.
- **Sul nodo** restano `~/dib_tnsm/venv/` e `~/dib_tnsm/tree-c23d1e3/`, per i passi successivi.
