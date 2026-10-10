# DIB lifecycle (implementazione, import pulito di v43)

Progetto: gestione del lifecycle di policy MUD da evidenza condivisa (IEEE TNSM).
Piano di lavoro: `/root/Desktop/DIB_reframe/docs/DIB_piano_completo.md` (fuori da questa repo).
Audit di partenza (ID B*/D*): `/root/Desktop/DIB_reframe/docs/audit/01_tracciabilita.md`.
Provenienza e inventario: `docs/audit/00_inventario_repo_pulita.md`. Import = tag `v43-import`.

## Regole
- Non modificare codice di produzione (`code/src`), modelli TLA+ (`formal/`), `claims.json` né i dati in `results/` senza dirmelo.
- Se un test fallisce, riportalo: non indebolire l'asserzione e non correggere il codice.
- Ogni affermazione sul codice cita file:riga.
- Dichiara le ipotesi prima di ogni esperimento (nei docstring dei test).
- Scrivi i risultati in `docs/audit/`, non solo in chat.
- Comandi lunghi (TLC completo, Docker/OpenWrt, esperimenti completi): chiedi prima di lanciarli.
- Modifiche sempre su branch/copia; mai sovrascrivere gli originali.
- Nessuna modifica al paper (non è in questa repo).

## Come si esegue
- Test: `cd code && PYTHONDONTWRITEBYTECODE=1 timeout 300 python3 -m pytest tests -q -p no:cacheprovider` (atteso 281 passed al tag `v43-import`, ~6 s). `pytest-timeout` non è installato: usa `timeout`.
- Numeri indicizzati: `python3 scripts/verify_artifact.py [--with-tests]` (secondi, atteso 262 checks passed al tag `v43-import`, 266 su `revision-tnsm` dal commit `062b417`).
- TLC: `python3 scripts/run_formal.py --jar <tla2tools.jar> [--mutations-only] --output <dir>` (richiede Java; versione dei log: TLC2 2026.05.26.235334, rev 4ba7d88). Modello completo: minuti → chiedere.
- Esperimenti registry senza dati terzi: `PYTHONPATH=code/src python3 code/scripts/<script>.py` (v36_restore_ablation, v35_lifecycle_experiment, v28_lifecycle_trace, offline_veto_reconciliation --trials 10).
- Cluster distribuito e gateway OpenWrt: Docker, comandi lunghi → chiedere.
- Python: l'ambiente è 3.10.13, `pyproject.toml` dichiara >=3.12 (D18, lasciato invariato).

## Fase revisione TNSM (ottobre 2026)
Obiettivi concordati col supervisor, senza cambiare i concetti principali del paper (interventi dal capitolo 4 in poi):
1. Ripartire dai design goal e definire il threat model.
2. Giustificare f_s = 0.30 con la letteratura e con una derivazione (vedi `docs/audit/09_f_s_derivazione_e_letteratura.md`).
3. Rifare i test per TNSM: latenza, throughput, scalabilità, con rete realistica.
4. Valutare test più realistici (dataset: `docs/audit/10_dataset_survey.md`).
5. Dare una spiegazione scientifica ai valori numerici dei parametri (θ, α, β, m, 0.7/0.3).

Ordine di lavoro: baseline (281 test, 262 check) → integrazione dei file nuovi → distribuzione di h_d sui dati reali → piano delle misure di prestazione → solo dopo il mio OK, esecuzione.

Regole aggiuntive per questa fase:
- Lavora su un branch dedicato (`tnsm-revision`), un commit per passo, messaggio che dice cosa cambia e perché.
- File nuovi solo in `analysis_fs/`, `docs/audit/` (numerazione successiva: 11, 12, ...) e in una cartella nuova `experiments_tnsm/<nome>/` per i risultati non ancora promossi. Niente scritture in `results/` finché non lo dico io.
- Ogni esperimento: ipotesi e criterio di falsificazione nel docstring, prima di lanciarlo; seed, versione di Python, hardware e hash dei dati nel manifest.
- Misure di tempo: almeno 10 ripetizioni, intervalli di confidenza bootstrap, nessun confronto fra macchine diverse.
- Dati con data sharing agreement (Mon(IoT)r, PingPong): non copiarli nella repo e non committare dati derivati prima di aver verificato la licenza.
- Il paper non è in questa repo; i numeri da riportare vanno in `docs/audit/`, con file:riga.
- mTLS è dentro l'ambito della revisione: prima il design (`docs/audit/13_mtls_design.md`), poi il mio OK. Nessuna modifica a `code/src` prima di quell'OK; dopo, solo per ciò che il design approvato prevede, un commit per passo, mai su `formal/`.
