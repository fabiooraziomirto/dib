# Prompt di continuazione per una nuova chat (scritto 2026-10-11 ~13:25 UTC)

```
Contesto: lavoro sulla revisione TNSM di DIB in /root/Desktop/DIB_tnsm (worktree, branch `revision-tnsm`). Leggi PRIMA: CLAUDE.md del progetto,
docs/audit/20_stato_di_avanzamento.md (le prime righe sono le più recenti), docs/audit/32_automazione_blocchi_design.md (§1-§22: tutto ciò che è stato
costruito e deciso oggi) e docs/audit/33_prompt_continuazione.md (questo file). Rispondi in italiano, conciso, citando file:riga. Per le persone usa they/them
se i pronomi non sono dichiarati.

REGOLE (hanno la precedenza sul resto):
- NESSUN comando sudo da parte tua. Nessuna modifica a code/src, service.py, results/, ai 18 file congelati di bf272e8 né agli script già hashati
  (netem_watch2.sh, profile_ctl.py, auto_block.py, make_plog_thresholds.py, launch_auto_block.sh, copy_block.py) senza dirlo all'utente.
- Ogni comando ssh sul nodo lo autorizza l'utente, UNO PER VOLTA: chiedi sempre il comando esatto (testo completo) e non aggirare un rifiuto. Nodo:
  ubuntu@192.168.100.57, chiave ~/.ssh/id_ed25519_lab. Sola lettura salvo dove l'utente autorizza altro.
- `git add` con percorsi espliciti; `git status` prima di ogni commit; scrittura, test e commit concatenati con `&&`; messaggi che dicono cosa e perché;
  fine messaggio: "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>". Risultati scritti in docs/audit/ (numerazione successiva: 34, 35, ...),
  mai solo in chat. Mai scrivere in results/.
- Test: `PYTHONDONTWRITEBYTECODE=1 /opt/conda/envs/dib312/bin/python -m pytest experiments_tnsm/common experiments_tnsm/m67_retraction -q -p no:cacheprovider`
  (circa 190 test, ~100 s; test_netem_scripts n6/n9 v1 erano instabili, ora corretti). Se un test fallisce, riportalo: non indebolire l'asserzione.
- Test PRIMA del codice quando si può; dichiara le ipotesi nei docstring prima di ogni esperimento; un solo nuovo tentativo, solo se un gruppo non ha
  prodotto dati; un gruppo con dati non si rilancia. Non cambiare i criteri pre-registrati dopo aver visto i dati.
- NON: commentare la forma della curva C/D né il plateau a 100 writer; riportare numeri di costo mTLS da M6/M7; spiegare oltre i dati i ~67 ms in più del braccio
  C a wan, le ritrasmissioni di Q4, le code dei tempi per episodio senza pcap; analizzare M1/M2 finché i blocchi di rete non sono chiusi; eseguire B2-kill o
  partition (non sono nella sequenza; richiedono cella di fumo, test partition+restore con il vero watcher e decisione dell'utente).
- Se incolli un diff o un output, incollalo INTERO dall'output del comando (mai ritrascritto o abbreviato senza dirlo).

STATO AL MOMENTO DELLA SCRITTURA (verifica sempre prima di affermare: il nodo può essere cambiato):
- Albero sul nodo: ~/dib_tnsm/tree-244f1d0 (git archive del commit 244f1d0; elenco hash ~/dib_tnsm/frozen_hashes_244f1d0.txt, 24 righe; sha256sum -c = 24/24 OK;
  auto_block.py b58d58f0…, netem_watch2.sh d1c8f392…). Python del nodo: ~/dib_tnsm/venv/bin/python (3.12). Il repo locale è oltre quel commit (analisi, docs).
- Watcher v2 INSTALLATO in /usr/local/lib/dib-netem/netem_watch2.sh, hash d1c8f392d686c63aa56bf09628844dd29cfec2c1d2f5c7d37fd94694d7df5534, in tmux
  sessione `watch2` (sudo timeout 9h … --dir /home/ubuntu/dib_tnsm/m67 --owner ubuntu --poll 0.5), avviato 12:48:20 UTC. NON toccare quella finestra
  (un Ctrl-C l'ha già fermato alle 12:43:47). Se il battito (~/dib_tnsm/m67/watch2.heartbeat, epoch_ms) è > 10 s: fermati e dillo all'utente. Il watch2.log si
  riscrive a ogni riavvio del watcher: COPIALO (ssh cat) subito dopo ogni blocco, prima di qualunque riavvio.
- BLOCCO REALE IN CORSO O FINITO: lanciato 13:17:09 UTC, pid 3057429, `auto_block.py --blocks degraded,lan_after` (--commit-wait-min 0, --end-utc
  2026-10-11T19:30:00Z), output ~/dib_tnsm/out/block_degraded_lan_after_20261011 (state.json, DONE a fine corsa, degraded/ e lan_after/). Durata prevista ~40 min.
  Già completato e copiato in locale: lan_before (experiments_tnsm/m67_retraction/block_lan_before_20261011, analisi analysis_lan_before.md: mediane n=10, 0 esclusi).
  Controllo (sola lettura, aspetta DONE fino a 540 s): ssh … 'O=~/dib_tnsm/out/block_degraded_lan_after_20261011; for i in $(seq 1 108); do [ -f $O/DONE ] && break;
  sleep 5; done; … state.json eventi, BLOCK.json, profile_events.jsonl, watch2.log filtrato, docker ps -a con label dibtnsm, df' (modello: audit 32 §20).
- Il blocco si ferma da solo (e richiede lan) se: battito vecchio, df < 2 GB, PKI scaduta (scade 2026-10-13 08:22:10Z), profile.applied incoerente > 10 s o più di 3
  incoerenze transitorie in 60 s, RTT non conforme su 3 celle. Un gruppo senza dati si rilancia una volta; con dati mai.
- L'hash del file delle soglie (plog_thresholds_degraded.json, evento threshold_file in state.json) è registrato PRIMA di b1_start; sul nodo non c'è git: committalo
  dopo (copia con copy_block.py) e verifica che l'hash coincida con lo stato; se no il dato non è pre-registrato e va dichiarato.

DOPO IL BLOCCO (ordine):
1. copy_block.py (ssh autorizzato) per `degraded` e `lan_after` (cartelle locali nuove sotto experiments_tnsm/m67_retraction/block_degraded_lan_after_20261011/), più
   watch2.log (ssh cat) nella stessa cartella. Mai sovrascrivere; sha256 verificati sui due lati; niente pcap.
2. Analisi: `analyze_b1.py <block>/degraded --lan-ref <lan_before>/lan_before --lan-ref <lan_after> --profile-events <block>/degraded/profile_events.jsonl --watch-log
   <watch2.log> --out …`; `analyze_c.py <block>/degraded --profile-events … --watch-log …`. Riporta: mediane e IC bootstrap (n=50 a degraded, 10 a lan), esclusioni per causa
   (incluse quelle per sovrapposizione), other_cores e steal_pct, generator_path_ms con flag, tipo di misura, P-log accettato o no per cella, tempo per sito
   (withdrawn_plog_s), consegne in pending con righe di ack e read_undercount_sites, L_dns a degraded, polling effettivo del watcher e tempi di applicazione.
3. Esito di (a) (riferimento lan adiacente, stesso braccio e FANOUT, mediana più alta fra prima e dopo; FANOUT 1: 10×n_RTT×R più servizio; eccesso sempre
   riportato; regola R-gp: cella con reused_ok falso = "not evaluable", non esclusa) e di (c) (intervalli D [0,004;0,015] e C [0,025;0,08] INVARIATI; falsificata se
   l'IC di Clopper-Pearson di un braccio è interamente fuori dal suo intervallo, o se l'IC di C è interamente sotto quello di D; i dati tcpdump 2/200 D e 6/200 C
   erano noti prima: B1 è il test confermativo, 1000 consegne per braccio; n e x sugli stessi episodi, asserzione dei 10 siti, definizione alternativa se > 3
   episodi senza dispute_rtt_s). Senza altre interpretazioni. Scrivi tutto in docs/audit/34_… e aggiorna audit 20. POI FERMATI e aspetta le decisioni dell'utente.
4. Solo dopo che i blocchi di rete sono chiusi: M1/M2 della notte, poi (se l'utente vuole) rilettura di audit 04, 12, 14, 19 per un elenco di cosa manca per i cinque
   obiettivi della fase revisione TNSM (CLAUDE.md).

LEZIONI DI OGGI (dettagli in audit 32): (1) un watcher v1 `netem_watch.sh … degraded` lasciato attivo ha riapplicato degraded sopra il v2: controlla sempre
   `ps … | grep "[n]etem_wa""tch"` e che resti SOLO la catena di netem_watch2.sh (auto_block lo verifica già); (2) un processo avviato con `&` ignora SIGINT: corretto in
   System.spawn; (3) durante la creazione di un cluster compaiono container uno alla volta: il watcher ora non scrive profile.applied se l'elenco cambia durante
   l'applicazione (applicazione a 11 container ~1,2 s); (4) i campioni grezzi di generator_path_ms NON sono registrati da run.py (solo mediane; 944 ms in una calibrazione, non
   spiegato); (5) cartelle di output DIVERSE per ogni invocazione di auto_block (riscrive manifest.json e state.json); (6) marcatori smoke_ok_<profilo> in
   ~/dib_tnsm/m67/smoke/ valgono per gli hash del tree (hashes_id 4a0f22e1… per tree-244f1d0): un tree nuovo richiede nuovi smoke.
```
