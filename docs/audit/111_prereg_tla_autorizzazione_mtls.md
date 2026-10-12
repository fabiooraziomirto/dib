# Audit 111 — Pre-registrazione: modello TLA+ dell'autorizzazione mTLS (identità, ruoli, denylist, "proprio sito")

Data: 2026-10-12. Branch `tnsm-authz` (da `tnsm-fsm` a 36b9c83; worktree `DIB_tnsm_authz`, perché
`DIB_tnsm_fsm` è dell'altra sessione). Scritto e committato **prima** di ogni run TLC.
Numero: 111 = primo libero sopra 110 (verificato su tutti i branch e le worktree; i 94-103 sono dell'altra sessione, il 110 dell'audit v8).

**Non è il modello del ciclo di vita** (v6/v7/v8, che non si tocca). La domanda è sul threat model: chi può fare
cosa, e una revoca di identità ha effetto immediato?

## 1. Codice letto (sola lettura)
`service.py` sha256 `0501b383…` (ultimo commit sul file: `16a6db0`), `mtls.py` sha256 `4833dae3…`.
- `Identities.resolve` (`mtls.py:134-142`): scorre i SAN del certificato; se uno è in denylist → `None`; se è mappato → quella
  voce; altrimenti il successivo. Il file è riletto quando cambia l'mtime (`mtls.py:120-122`, `_reload_if_changed`).
- `_authorize` (`service.py:177-186`): senza mTLS non controlla nulla; con mTLS ammette se `entry["role"] in roles` oppure
  (`role in site_roles` e `entry.get("site") == site`), altrimenti 403.
- `_reporter` (`service.py:867-877`): `_authorize(roles=("member","operator"))`; se il payload ha `site_id` diverso dal
  sito del certificato → 403; poi `req.site_id = entry.site`. `/attest` (:880) e `/dispute` (:894) lo chiamano per prime.
- Le 18 route (9 sito, 9 evidence) hanno `_authorize` o `_reporter` come prima istruzione (docstring esclusa):
  verificato dal parser AST `gen_rules.py`, che scrive la tabella `Rules.tla` **dal codice** (non a mano; `--check` la confronta).

**Discrepanze design/codice note PRIMA di lanciare** (design = `13_mtls_design.md` sez. 3.3 con le decisioni Q1-Q6 di sez. 9):
- **D-a** il testo 3.3 parla di "proprio sito"; il codice usa un ruolo `operator` separato (Q1 della sez. 9): coerente con la decisione, non è una discrepanza.
- **D-b** `/scores`, `/scores/by_id` (`service.py:849, 857`): il codice ammette anche `operator`; il design dice `member`, `consortium_admin`.
- **D-c** `/attest`, `/dispute` (`:871`): il codice ammette `member` **e** `operator`; il design dice `member`.
- **D-d** `/health` del sito (`:725`): il codice ammette qualunque identità mappata (anche un `member` di un altro sito); il
  design dice "proprio sito, `consortium_admin`". La risposta contiene `site_id` e `reconcile.last_error` (`:731-735`).
- **P5 (sito del payload di `/dispute`):** la regola **è nel codice** (`service.py:874-876`): il payload con altro sito → 403, e il sito usato è quello del certificato.

## 2. Cosa è modellato (`experiments_tnsm/tla_authz/AuthZ.tla`)
- 8 SAN mappati: member e operator per ciascuno di 3 siti, `ev` (evidence), `ad` (admin); più `gh`: SAN valido per la CA ma **non** mappato.
- Certificato = sequenza di 1..`MaxSans` SAN (design 3.1: 1; `MaxSans=2` serve per P1_Presented).
- Denylist centrale `master` e **una copia per servizio** `loc[x]` (3 siti + evidence). `Revoke(s)` aggiunge `s` a `master`; con
  `AtomicReload=TRUE` tutte le copie sono aggiornate subito (file condiviso), con `FALSE` ogni servizio la rilegge con `Reload(x)`.
- Azione `Call(c, ep, tgt, arg)`: il certificato `c` invoca l'endpoint `ep` sul servizio `tgt` con argomento `arg` (sito del path per
  `/pending` e `/ack`; sito del payload o nessuno per `/attest` e `/dispute`). Esito (ok o 403) deciso con le regole di `Rules.tla`
  (dal codice). L'esito autorizzato è un'etichetta (`last`: certificato, voce risolta, sito agente, copia di denylist e `master` al momento della chiamata). Nessun ciclo di vita.
- Un confronto con la tabella del design (`DesignRules`): `PD_DesignCover` = il codice non ammette più di quanto dice il design.

## 3. Proprietà (state invariant su `last`)
| Id | Formula | Ipotesi |
|---|---|---|
| P1_Local | `ok => voce risolta ∉ loc[tgt]` | regge (denylist del servizio rispettata) |
| P1_Global | `ok => voce risolta ∉ master` | regge con `AtomicReload=TRUE`; **violata** con `FALSE`: finestra fra revoca e rilettura (limite noto, design 9.1 punto 5) |
| P1_Presented | `ok => nessun SAN del certificato ∈ loc[tgt]` | regge con `MaxSans=1`; **violata** con `MaxSans=2` (`resolve` ammette `[A mappato, B revocato]` come A, `mtls.py:134-142`): esplorativa, rilevante solo se la CA emette certificati multi-SAN (design 3.1: no) |
| P2_Confine | `ok` su `/query,/commit,/local_revoke,/local_restore,/reconcile,/export_mud` ⇒ ruolo `operator` e sito = servizio chiamato | regge |
| P3_Fanout | `ok` su `/apply_fanout` ⇒ ruolo `evidence` | regge |
| P4_Admin | `ok` su `/restore`, `/seed` ⇒ `consortium_admin` | regge |
| P5_Dispute | `ok` su `/attest`,`/dispute` ⇒ sito agente = sito del certificato e payload assente o uguale | regge |
| P5b_Pending | `ok` su `/pending`,`/ack` ⇒ `member` con sito = sito del path | regge |
| P6_Identity | `ok ⇒ identità mappata` (nessun endpoint raggiungibile con SAN non mappato o revocato); la parte statica (ogni route chiama `_authorize`) è in `gen_rules.py` | regge |
| PD_DesignCover | `ok(codice) ⇒ ok(design)` | **violata** per D-b, D-c, D-d (il codice ammette di più del testo) |

## 4. Mutanti (non vacuità), uno per proprietà
| cfg | Mutante | Deve violare |
|---|---|---|
| m1_nodeny | `resolve` ignora la denylist | P1_Local |
| m2_noownsite | niente controllo `site == proprio sito` | P2_Confine |
| m3_memberrestore | `/restore` ammette anche `member` | P4_Admin |
| m4_payloadsite | `/dispute` usa il `site_id` del payload | P5_Dispute |
| m5_fanoutany | `/apply_fanout` ammette ogni ruolo | P3_Fanout |
| m6_openseed | `/seed` senza autorizzazione | P6_Identity |
Un mutante che **non** viola la sua proprietà rende il modello vacuo su di essa: la proprietà non si afferma.

## 5. Configurazioni (`experiments_tnsm/tla_authz/*.cfg`, invarianti `TypeOK` + la proprietà)
Base (codice non mutato, `MaxRevokes=2`, `MaxSans=1`, copie asincrone): `b_P1L`, `b_P1S_single`, `b_P1G_atomic` (atomico), `b_P2`, `b_P3`,
`b_P4`, `b_P5`, `b_P5b`, `b_P6` → tutte **nessuna violazione**. Esplorative con violazione prevista: `x_P1G_async` (`MaxRevokes=1`),
`x_P1S_multisan` (`MaxSans=2`, `MaxRevokes=1`, atomico), `x_PD_design`. Mutanti: `m1`…`m6` → ciascuno una violazione.
Spazio stimato: decine di migliaia a pochi milioni di stati; si lancia con `-Xmx2g`, 2 worker, `nice 19`, in parallelo alla v8 (che usa 28 GB su 64 GB).

## 6. Falsificazione e lettura
- Un controesempio a una proprietà base (non esplorativa) **falsifica "il codice rispetta il design"**: si riporta la traccia minima
  in chiaro, senza correggere il codice (regola di CLAUDE.md).
- Le tre esplorative: la violazione prevista **non** falsifica nulla (è la finestra di revoca, il multi-SAN, e le discrepanze D-b/c/d);
  l'**assenza** di violazione le falsificherebbe (modello che non vede la differenza).
- Per il paper: tutte le base reggono e tutti i mutanti violano ⇒ una frase sul fatto che le regole sono verificate a modello;
  l'immediatezza della revoca vale solo con la denylist condivisa (o rilettura) e il limite va dichiarato.

## 7. Limiti dichiarati
Non è la sicurezza di TLS (handshake, validità, scadenza: fuori ambito del design sez. 2). Non modella l'operatore umano, la governance
della CA, i tempi, il contenuto delle operazioni. Non verifica che il codice **realizzi** le regole nelle parti non lette come tabella
(corpo degli handler, `_reporter` oltre la riga del controllo): sono lette a mano e citate sopra. Mtime con granularità insufficiente
(modifica del file nello stesso `mtime_ns`) non modellata. Revoca = solo aggiunta alla denylist (nessun "un-revoke").
