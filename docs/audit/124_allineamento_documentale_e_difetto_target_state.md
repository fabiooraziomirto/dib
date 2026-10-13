# Audit 124 — Allineamento documenti/codice e un difetto che contraddice G3

Data 2026-10-13. Lettura del codice di riferimento (`service.py` `3ffa57ee…`, `mtls.py` `4833dae3…`) contro README, `docs/main_10p.tex`, `docs/main_wip.tex`, `formal/`. Nessun file di `code/src`, `formal/`, `results/`, del paper modificato. Le voci marcate (V) le ho verificate di persona; le altre vengono dalla rilettura delegata, con file:riga da ricontrollare prima di toccare il testo.

## 1. Difetto: il sito applica `target_state` senza confrontarlo con `event_type` (V)
- Codice: `_apply_fanout_row` scrive `state = target_state` così come arriva (`service.py:508-511`). È lo stesso percorso usato da `/apply_fanout` (`:654-658`), dalla reconcile (`:714`) e dall'anti-entropy (`:673`).
- Claim contraddetto: `docs/main_10p.tex:411` (G3): "A faulty evidence service can delay withdrawal or issue unfounded disputes and restorations, but a restoration returns records to MonitorOnly …, so it cannot make a fact exportable either."
- Prova: `experiments_tnsm/evidence_trust_20261013/test_target_state_trust.py`. H-T1 (un `restore` con `target_state="active"` non crea autorizzazione) è **falsificata**: il record diventa Active ed esportato. L'assert originale resta, marcato `xfail(strict=True)`. Esito: 1 passed (percorso valido), 1 xfailed.
- Chi può farlo: con mTLS solo un'identità con ruolo `evidence` (`service.py:656`), cioè proprio il "faulty evidence service" di G3; senza mTLS chiunque.
- Influenza sugli esperimenti: nessuna. Il harness e il servizio inviano sempre le coppie della Tabella II (dispute→disputed, revoke→revoked, restore→monitor-only). Il difetto tocca solo il claim di sicurezza G3 e il modello di minaccia.
- Due vie, a scelta dell'utente:
  1. **Solo testo** (nessun rerun): G3 diventa "…assuming the evidence service sends only the transitions of Table~II; the prototype applies the target state it receives".
  2. **Correzione minima** (non applicata): `experiments_tnsm/evidence_trust_20261013/proposed_target_state_guard.patch`, 7 righe in `_apply_fanout_row`: un evento con target diverso da quello del suo tipo viene ignorato. Non cambia l'architettura né alcun percorso valido. Se adottata, il nuovo hash invalida la provenienza di tutte le campagne registrate su `3ffa57ee…`. Rerun minimi: suite unitaria, `lifecycle_rerun_20261013`, `test_target_state_trust.py` (l'xfail deve diventare passato e va rimosso il marcatore), un episodio di verifica per profilo del gateway, lo sweep `http` a N=10. B2k, R1e e R1f restano evidenza del servizio `3ffa57ee…`: comportamento identico sugli input validi, ma il paper dovrebbe dirlo.

## 2. Mutazioni M1–M6: la numerazione del paper non corrisponde al repository (V)
| Repo (`formal/mutations/mN`, proprietà da `scripts/run_formal.py:20-22`, confermata in `result.log`) | Tabella `tab:tla` (`main_10p.tex:454-459`, uguale in `main_wip.tex`) |
|---|---|
| m3: export mentre Disputed → ExportRequiresActive | M3 = local-revoke fans out |
| m4: local restore ignora la dispute aperta → DisputeSuspendsEverywhere | M4 = restore ignora l'origine |
| m5: local revoke fa fan-out → I2_LocalRevokeConfinement | M5 = local restore ignora la dispute ("I3 local-restore conservative") |
| m6: restore ignora l'origine → I3_GlobalRestorePreservesLocalRevoke | M6 = export mentre Disputed |
M1 e M2 coincidono. Correzione: riordinare le righe del paper (M3 export, M4 local restore — proprietà DisputeSuspendsEverywhere, M5 local revoke, M6 restore). Rinominare le directory romperebbe `claims.json` e il verificatore. Le mutazioni del modello di autorizzazione (`tla_authz` m1–m6) e le cinque correzioni FSM usano gli stessi nomi: nel paper vanno chiamate in un altro modo (es. A1–A6, C1–C5).

## 3. Autenticazione e ruoli
- (V) `README.md:199-201` dice che DIB "does not implement caller authentication or role enforcement". Il codice implementa mTLS opzionale (`DIB_DIST_MTLS=1`, `service.py:157-187`, `mtls.py`), spento per default; da spento ogni endpoint è aperto e il `site_id` del payload è fidato (`_reporter`, `service.py:946-952`). Testo proposto: "Caller authentication and role enforcement are implemented as opt-in mTLS (`DIB_DIST_MTLS=1`); with the default (off) every endpoint is unauthenticated and the payload `site_id` is trusted." `docs/KNOWN_LIMITATIONS.md` non contiene la voce citata.
- `main_10p.tex:114`: i member leggono tutti gli score (`:928`, `:936`), e anche gli operatori possono fare attest e dispute (`:950`). Testo più largo del codice: "members and site operators…".
- `main_10p.tex:443`: il modello di autorizzazione è stato estratto da `service.py` `0501b383…`; le regole sono invariate in `3ffa57ee…`. Le configurazioni `x_*` mostrano che la revoca di un'identità vale alla prima richiesta dopo la rilettura del file delle identità (altrimenti alla scadenza del certificato) e che il modello assume un SAN per certificato. Questo testo può sostituire il placeholder di `:443`.
- Commento `service.py:194`/`:803` ("/health is unauthenticated"): vero solo senza mTLS. Il commento è codice: lo segnalo e non lo cambio.

## 4. Local revoke e local restore rispetto all'evidence service (V)
- `/local_revoke` è puramente locale (`service.py:607-628`): nessuna chiamata all'evidence. Richiede un record locale esistente, altrimenti risponde 409.
- `/local_restore` legge l'evidence (`:633`). Se l'evidence non è raggiungibile risponde 503: il comportamento è fail-closed.
- Il modello `formal/distributed/DIB_Distributed.tla:192-199` permette invece a un sito non raggiungibile di fare LocalRestore leggendo direttamente `OpenDispute` globale. Il codice è quindi più restrittivo del modello. Va scritto: "local restore requires the evidence service to be reachable; local revoke does not" (`main_10p.tex:441`, `main_wip.tex:548`).

## 5. Versione del servizio per campagna
| Evidenza citata nel paper | Servizio registrato | Azione |
|---|---|---|
| Recovery B2k (28 celle, 834 prove) | `3ffa57ee` nei container | OK |
| Withdrawal degraded R1e/R1f | `3ffa57ee` nei container | OK |
| Banco netns (3,1–7,1×, 3 280 episodi) | `0501b383`, `a6bb1d22` | dire "earlier service version, same fan-out path" |
| Restore ablation / offline veto | `31863043` → rerun su `3ffa57ee` (audit 120) | citare il rerun |
| OpenWrt 10/10 (`results/openwrt/campaign-10runs`) | nessuno: registro **in-process** (`openwrt/prepare_policy.py`) | sostituire con la campagna di audit 121–122 (servizio distribuito, mTLS) |
| Dispute flood / sospensione (placeholder `:499`) | nessuno (import v43) | non riempire con i numeri vecchi |
| Sweep di scalabilità (`results/site_count`) | `54f635cb` | sostituito da audit 123 |
`docs/work/evidence_map_10p.md:32` attribuisce `3ffa57ee` al commit `dc3dd20`, ma l'hash è del commit `864101f` (V, storia in audit 119).

## 6. Firma CMS
Il gateway usa MUD unsigned con osMUD `-i` (`openwrt/router-entrypoint.sh:40`). Il paper lo dice già (`main_10p.tex:421`, AS5). Il costo CMS misurato a parte (`experiments_tnsm/m8_mud_sig`) non è citato. Se lo si cita, va scritto "measured offline, not in the gateway path". Nessuna frase dice che il gateway verifica la firma.

## 7. Limiti del model checking e dei test su un solo host
- (V) `main_10p.tex:441` presenta "three events (154,363,430 states), partitions, two lost deliveries, quorum two, two facts, and three sites (712,287,745 states)" come un'unica verifica. Sono configurazioni separate: 712 287 745 stati = 3 siti, 1 fatto, 2 eventi, nessuna perdita, nessuna partizione (`experiments_tnsm/tla_fsm/v8/S3_three_sites.cfg`). Va riscritto dimensione per dimensione.
- Abstract (`main_10p.tex:51`): aggiungere "bounded" al model checking. "within a measured bound" va riferito alla **mediana** (3 prove degraded su 234 superano il limite).
- `main_10p.tex:419`: SQLAlchemy e i dieci retry appartengono al registro in-process (`services.py`); i servizi distribuiti usano `sqlite3` direttamente.
- `main_10p.tex:557`: "one host pair" va sostituito con "a single host".
