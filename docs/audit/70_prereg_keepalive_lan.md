# Audit 70 (già numerato 64 nei messaggi di commit; rinumerato per non collidere con il branch tnsm-fsm) — Pre-registrazione: controllo funzionale a `lan` delle connessioni persistenti (opt-in) nei container veri

Data: 2026-10-12. Contesto: il watcher v2 è scaduto alle 21:48Z e riavviarlo richiede sudo con password; finché non torna vivo, `degraded` (H-K1..K4 di audit 62) non si può misurare (la coda `auto_degraded_k.py` parte da sola al ritorno del watcher, fino alle 07:00Z). A `lan` non serve il watcher: si controlla che l'opt-in non rompa nulla. **Non è una misura dell'effetto** (a `lan` non c'è perdita: l'effetto atteso è nullo), è un controllo di correttezza.

## Configurazione
Tree `50c4335`, `DIB_M67_KEEPALIVE=1` nell'ambiente del driver (⇒ `DIB_DIST_FANOUT_KEEPALIVE=1`, warmer 2 s nel container evidence), `lan`, arms D e C, seme 20261014. (1) B2-kill completo (k = 1, 10, 50; T = 5/15; 10 prove per cella; `--l-dns` calibrato a `lan` nello stesso blocco) **con la correzione del driver**; (2) B1 FANOUT 10, 10 episodi per cella (default a `lan`). Riferimenti OFF: audit 69 (B2k) e B1 `lan_before/lan_after` di B5 (tree diverso: confronto descrittivo).

## Ipotesi (fissate ora)
- **H-L1 (stantia dopo riavvio):** B2k con keep-alive acceso: nessuna prova con `violation_over_bound` o `final_all_monitor_only` falso, e (d-kill) non falsificata (estremo inferiore dell'IC della mediana ≤ bound) in ogni cella con n ≥ 5. **Falsificata** da una violazione di (e) o da una cella con IC inferiore sopra il bound.
- **H-L2 (nessun costo a `lan`):** nelle celle B1 FANOUT 10 la mediana dell'ultimo sito con keep-alive acceso non supera quella dei riferimenti OFF oltre 50 ms (valutazione descrittiva con IC; nessun verdetto di falsificazione: il confronto è fra tree e orari diversi).
- **H-L3 (mTLS):** nessuna esclusione per `transport_error` o `client_timeout` nell'arm C attribuibile al keep-alive: il numero di esclusioni dell'arm C non supera 3 per cella. **Falsificata** se una cella C ne ha più di 3 di quei tipi.
- **H-L4 (warmer):** nel log del container evidence a fine blocco non compaiono eccezioni del warmer (`connection warmer failed`). **Falsificata** da una riga.
Dati in `experiments_tnsm/keepalive_lan_20261012/` (aggregati e grezzi senza pcap, `DATA.sha256`). Nessuna scrittura in `results/`.
