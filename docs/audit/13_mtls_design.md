# Audit 13 — Design di mTLS tra siti ed evidence service (solo progetto)

Data: 2026-10-10. Branch `revision-tnsm`. Fonte: `docs/work/DIB_piano_completo.md` §6. **Nessuna modifica a `code/src`.** Dopo il tuo OK si implementa solo ciò che questo documento prevede, un commit per passo, mai su `formal/` (regola in `CLAUDE.md`). Notazione: [C] = verificato nel codice (file:riga); [D] = deduzione o proposta; [?] = non verificato.

DIST = `code/src/dib/registry/distributed/service.py` (sha256 `48415497…`). API = `code/src/dib/registry/api.py` (registry single-node).

## 1. Stato attuale [C]

- **Nessuna autenticazione.** DIST non contiene nessuna riga TLS, SSL o certificato. Tutte le chiamate fra servizi sono in chiaro su HTTP:
  - sito → evidence: `httpx.get(f"{EVIDENCE_URL}/scores", …)` (DIST:346), `GET /pending/{site}` (DIST:502), `POST /pending/{site}/ack` (DIST:523);
  - evidence → sito: `POST {_site_url(i)}/apply_fanout` (DIST:663).
- **L'identità viene dal payload.** `/dispute` usa `req.site_id`, con il commento "Identity is supplied by the trusted harness; deployment authentication remains outside this prototype" (DIST:747-753). `GET /pending/{site_id}` e `/ack` (DIST:810, :831) accettano qualsiasi `site_id` nel path. `/restore` (DIST:781) e `/seed` (DIST:704) non hanno controlli di ruolo. Gli endpoint dell'operatore del sito (`/commit` DIST:402, `/local_revoke` :417, `/local_restore` :438, `/reconcile` :537) accettano qualsiasi chiamante. Nel registry single-node, ogni richiesta porta `site_id` nel corpo (API:28-29 `ObservationIn.site_id`, API:104 `/observation`, API:200 `/commit`, API:271 `/restore` con `actor_site_id`).
- **Connessioni.** Le chiamate fra servizi usano le funzioni di modulo `httpx.get/post`, che aprono una connessione nuova a ogni chiamata, senza pool. Il benchmark usa invece `httpx.Client` (`distributed_concurrency_benchmark.py`). Con TLS, ogni chiamata fra servizi pagherebbe un handshake completo: è rilevante per il costo (sez. 7).
- **uvicorn 0.51.0** (versione installata in 3.10 e 3.12):
  - **può richiedere** un certificato client (`Config.ssl_cert_reqs`, `ssl_ca_certs`: `uvicorn/config.py:237-238`, `:449-450`, `:465-466`);
  - **non espone il certificato del peer all'applicazione.** Lo scope HTTP (`uvicorn/protocols/http/h11_impl.py:205-219`) ha `scheme` ma nessuna chiave `extensions.tls`; l'unico uso di TLS è `is_ssl(transport)` (`protocols/utils.py:48`);
  - con uvicorn così com'è il server può quindi rifiutare chi non ha un certificato valido, ma **non può sapere quale sito chiama**, e l'autorizzazione per identità non è realizzabile.
  - `Config(http=...)` accetta però una classe di protocollo (`config.py:199`, `:479-483`), e questo rende possibile l'opzione B della sez. 4.
- Strumenti sul disco: OpenSSL 3.0.12. Non installati: step-ca e `step`, nginx, Envoy, Caddy, Hypercorn.

## 2. Obiettivi e limiti

1. mTLS **in entrambe le direzioni**: sito → evidence (lettura degli score, attestazioni, dispute, outbox) ed evidence → sito (fan-out).
2. **L'identità viene dal certificato**, mai dal payload o dal path. Il certificato porta solo un identificatore, nel SAN URI. Sito e ruolo li decide il server con una **mappatura lato server** (sez. 3.2); il ruolo nel certificato non è mai l'unica fonte.
3. **Ruoli separati:** sito membro, evidence service, amministratore del consorzio. Il ripristino globale richiede l'identità di amministratore.
4. **Chiave di trasporto separata dalla chiave di firma MUD** (sez. 3.4).
5. **CA privata e certificati a vita breve.** La vita breve risolve la revoca verso siti offline senza CRL distribuite.

**Fuori ambito, da dichiarare nel paper:**
- mTLS autentica il **servizio**, non l'operatore umano: l'autenticazione dell'operatore locale (I1) resta separata;
- governance della CA (chi emette, chi approva l'ingresso di un membro);
- protezione delle chiavi su disco (HSM, TPM);
- riservatezza dell'evidenza verso gli altri membri.

## 3. Identità, mappatura, chiavi

### 3.1 Formato dell'identità

SAN URI: `spiffe://dib.consortium/site/<site-id>`, `spiffe://dib.consortium/evidence`, `spiffe://dib.consortium/admin/<nome>`. È il formato SPIFFE, usato solo come convenzione di nomi: nessun runtime SPIFFE. Il CN non si usa per l'autorizzazione.

### 3.2 Mappatura lato server

Un file di configurazione caricato all'avvio da ogni servizio e montato read-only, per esempio `identities.yaml`:

```yaml
version: 1
identities:
  "spiffe://dib.consortium/site/site-0":  {site: site-0, role: member}
  "spiffe://dib.consortium/site/site-1":  {site: site-1, role: member}
  "spiffe://dib.consortium/evidence":     {role: evidence}
  "spiffe://dib.consortium/admin/ops-1":  {role: consortium_admin}
denylist: []          # SAN revocati prima della scadenza (sez. 3.5)
```

Un SAN non presente nel file, o presente nella denylist, riceve `403` anche se il certificato è valido per la CA. Il file ha un hash, registrato nel manifest di ogni misura.

**Proposta da valutare (richiede il tuo OK; risponde a H2 del REPORT, `services.py:71-121`, `dib.py:198`).** Aggiungere per ogni sito l'elenco dei tipi che può dichiarare, per esempio `{site: site-0, role: member, device_types: [philips-hue, smartthings]}`. Il server rifiuterebbe con `403` un'osservazione o un profilo di un tipo non elencato. Così ES_d diventa **verificabile** (chi entra nel denominatore di C_s è deciso dalla governance, non autodichiarato), e la nota di `paper_edits_proposed.md` §1a ("the prototype does not implement this check") si potrebbe rimuovere.

Dove andrebbe il controllo [C]: il prototipo distribuito **non ha** un endpoint di osservazione (`contribute` è un no-op, `distributed_concurrency_benchmark.py`, docstring), quindi il controllo andrebbe nel registry single-node: `POST /observation` (API:104) e `POST /profile` (API:110). Costo: aggiornare la mappatura a ogni dispositivo nuovo, cioè un onere di governance. Rischio: un errore di elenco rende un sito onesto invisibile per quel tipo.

### 3.3 Autorizzazione per endpoint

"Proprio sito" = SAN mappato su `site == SITE_ID` del servizio che riceve la richiesta (`_site_id()`, DIST:342-343).

| Servizio | Endpoint (DIST) | Chi può chiamare | Altri controlli |
|---|---|---|---|
| sito | `POST /query` :381, `/commit` :402, `/local_revoke` :417, `/local_restore` :438, `/reconcile` :537 | solo il **proprio sito** (lo strumento dell'operatore locale usa il certificato del sito, o un certificato operatore emesso per quel sito: vedi la domanda aperta Q1) | — |
| sito | `POST /apply_fanout` :458 | solo `evidence` | — |
| sito | `GET /export_mud` :559 | proprio sito (gestore MUD locale) | [?] se osMUD scarica il MUD via HTTPS, deve fidarsi della CA del server (piano §7.4) |
| sito | `GET /state/{id}` :588, `/health` :599 | proprio sito, `consortium_admin` | `/health` espone `reconcile.last_error` (voce della checklist) |
| evidence | `POST /seed` :704 | `consortium_admin` | — |
| evidence | `GET /scores` :716, `/scores/by_id` :723 | qualsiasi `member`, `consortium_admin` | — |
| evidence | `POST /attest` :734 | `member` | sito preso dal certificato |
| evidence | `POST /dispute` :747 | `member` | **`site_id` preso dal certificato.** Se il payload contiene un `site_id` diverso: `403`. Il quorum di sospensione (DIST:757-761) conta i SAN distinti |
| evidence | `POST /restore` :781 | **solo `consortium_admin`** | ripristino globale = privilegiato |
| evidence | `GET /pending/{site_id}` :810, `POST /pending/{site_id}/ack` :831 | `member` con `site == {site_id}` del path | altrimenti `403` |
| evidence | `GET /health` :848 | qualsiasi identità mappata | — |

Registry single-node (API): stessa regola. `site_id` e `actor_site_id` nel corpo devono coincidere con l'identità del certificato, altrimenti `403`. `/restore` (API:271) è riservato a `consortium_admin`.

### 3.4 Chiavi separate

- **Trasporto:** una coppia di chiavi per servizio (sito, evidence, admin), con certificato della **CA di trasporto**, `extendedKeyUsage = clientAuth, serverAuth`, vita breve.
- **Firma MUD (piano §7.4):** una chiave diversa per sito, con certificato di una **CA di firma** distinta, `extendedKeyUsage = codeSigning` o equivalente (RFC 8520 firma con CMS detached). La chiave di firma non sta nel container del servizio HTTP. Vita più lunga, perché un MUD firmato deve restare verificabile.
- Un certificato di trasporto rubato non permette di firmare MUD, e viceversa. Le due CA non si fidano l'una dell'altra (trust anchor distinti nei servizi e nel gestore MUD).

### 3.5 CA, vita dei certificati, revoca

- **Produzione (proposta):** step-ca, con certificati a vita breve (24 h) e rinnovo automatico (`step ca renew --daemon`). **Nuova dipendenza: richiede il tuo OK.**
- **Test e misure (senza dipendenze nuove):** una CA di test generata con `openssl` (già presente) da uno script in `experiments_tnsm/` o in `code/tests/fixtures`. Certificati con scadenza configurabile, compresi uno già scaduto e uno di una CA sconosciuta.
- **Revoca:** (1) scadenza breve, come meccanismo principale; (2) **denylist** nella mappatura, per la revoca immediata (ricaricata a ogni avvio o su segnale); (3) facoltativo, CRL verificata da `ssl.VERIFY_CRL_CHECK_LEAF` nel contesto del server. Per il test "revocato" del §6.4 propongo la denylist (deterministica, nessuna infrastruttura) più un caso con CRL se sceglierai (3).
- **Ingresso e uscita dei membri (S3)** = emissione di un certificato più una riga di mappatura, e il contrario.

## 4. Dove terminare TLS: due opzioni

| | **A. Reverse proxy** (piano §6.2) | **B. Terminazione in uvicorn con protocollo personalizzato** |
|---|---|---|
| Come | nginx o Envoy nello stesso container (o pod) di ogni servizio. Valida il certificato client e inoltra l'identità verificata in un header (es. `X-DIB-Peer-SAN`) all'app, che ascolta solo su `127.0.0.1` o su un socket Unix. Il proxy **rimuove** l'header se arriva dall'esterno | sottoclasse del protocollo HTTP di uvicorn (`H11Protocol`), passata con `Config(http=...)` (`config.py:199`, `:479-483`). Legge `transport.get_extra_info("ssl_object").getpeercert()` e scrive nello scope `extensions["tls"]` (forma dell'estensione ASGI TLS: `client_cert_chain`, …). Una dipendenza FastAPI legge l'identità dallo scope |
| Pro | soluzione standard e documentata; l'app non tocca TLS; politiche TLS mature | un solo processo per servizio; nessun header di cui fidarsi; nessuna dipendenza nuova (ssl della stdlib) |
| Contro | **dipendenza nuova** (nginx o Envoy) e un componente in più in ogni container, quindi un hop in più nelle misure; serve la garanzia che l'app non sia raggiungibile senza passare dal proxy (rischio di header falsificato) | dipende dagli **interni di uvicorn** (`H11Protocol`, `self.scope`): fragile fra versioni, da fissare a `uvicorn==0.51.0` e coprire con un test. Funziona solo con `--http h11`, non `httptools` |
| Verifica | [?] configurazione del proxy da provare | [?] **non ancora provata**: va dimostrata con un test minimo prima di adottarla |

**Raccomandazione [D]: B per il prototipo**, con un test di regressione che fallisce se uvicorn smette di popolare `extensions["tls"]`. Motivi: nessuna dipendenza nuova, nessun header di cui fidarsi, e le misure non mescolano il costo di TLS con quello di un proxy. Se B fallisce la prova minima, si passa ad A. Nel paper si scrive che in produzione si usa un proxy o una service mesh.

**Client** (chiamate fra servizi e benchmark): `httpx.Client(cert=(crt, key), verify=ca_bundle)`, **un client per processo con pool di connessioni**, al posto delle funzioni di modulo (DIST:346, :502, :523, :663). Cambia anche le prestazioni senza TLS: va misurato separatamente (sez. 7, braccio "pool senza TLS").

## 5. Modifiche previste (solo dopo OK, un commit per passo)

1. **Prova minima dell'opzione B** (solo test): `code/tests/tests/test_mtls_peer_identity.py`. Avvia uvicorn con il protocollo personalizzato su una porta locale con la CA di test e verifica che l'app veda il SAN del client. Se fallisce: report e passaggio ad A.
2. **CA di test e generazione dei certificati:** script e fixture (OpenSSL), più `identities.yaml` di esempio.
3. **Dipendenza FastAPI `peer_identity()`** e matrice di autorizzazione della sez. 3.3 in DIST, attiva solo con `DIB_DIST_MTLS=1`. Con `DIB_DIST_MTLS=0` il comportamento resta quello di oggi: i test esistenti e i risultati restano confrontabili e `verify_artifact` non cambia ancora. `/dispute` legge il sito dal certificato.
4. **Client con pool e certificati** per le chiamate fra servizi (DIST:346, :502, :523, :663).
5. **Docker:** `generate_compose.py` e `docker-compose.yml` montano certificati e mappatura per servizio. Variabili `DIB_DIST_MTLS`, `DIB_DIST_TLS_CERT`, `DIB_DIST_TLS_KEY`, `DIB_DIST_TLS_CA`, `DIB_DIST_IDENTITIES`.
6. **Registry single-node (API):** stessa dipendenza e controllo `site_id == peer` (opzionale; dimmi se è in ambito).
7. **Test del §6.4** (sez. 6).
8. **Solo se approvata:** la mappatura dei tipi per sito (ES_d verificabile, sez. 3.2).

Ogni passo che modifica `service.py` ne cambia l'hash: la rigenerazione di `results/` resta **unica e alla fine** (G0b in audit 04). Il modello TLA+ (attore autenticato, mutazione M7, piano §6.5) **non ora**, per tua decisione.

## 6. Test (piano §6.4)

Tutti con il servizio in-process o su porte locali, con la CA di test. Ipotesi e criterio di falsificazione nei docstring prima di eseguire.

| # | Caso | Atteso |
|---|---|---|
| T1 | certificato valido e mappato | 200 sugli endpoint consentiti dal ruolo |
| T2 | nessun certificato client | handshake rifiutato (nessuna risposta HTTP) |
| T3 | certificato di una CA sconosciuta | handshake rifiutato |
| T4 | certificato scaduto | handshake rifiutato |
| T5 | certificato revocato (SAN in denylist; facoltativo: in CRL) | 403 (denylist) o handshake rifiutato (CRL) |
| T6 | certificato valido ma SAN non mappato | 403 |
| T7 | il sito A chiama `/commit` (e `/local_revoke`, `/local_restore`, `/reconcile`) sul sito B | 403; stato di B invariato |
| T8 | il sito A chiama `/restore` sull'evidence | 403; stato invariato; solo `consortium_admin` riesce |
| T9 | il sito A apre `/dispute` con `site_id = B` nel payload | 403; nessun voto registrato |
| T10 | due dispute dallo stesso SAN | contano come un solo sito (quorum di sospensione, DIST:757-761); la seconda segnalazione distinta viene da un SAN diverso |
| T11 | il sito A legge o fa ack su `/pending/site-B` | 403 |
| T12 | un sito chiama `/apply_fanout` su un altro sito | 403 (solo `evidence`) |
| T13 | certificato di **firma** MUD usato come certificato client | handshake rifiutato (EKU o CA sbagliata) |
| T14 | S8: il certificato di trasporto del sito A è rubato | l'attaccante apre dispute a nome di A (atteso e dichiarato), ma **non** crea autorizzazione locale su A né su altri siti: `/commit` su A richiede l'identità dell'operatore di A (vedi Q1) |
| T15 | oracolo di invarianti I1–I3 (piano §7.2) con mTLS attivo, sulle sequenze dell'ablation esistente e del fuzz | 0 violazioni; gli stessi esiti con `DIB_DIST_MTLS=0` e `=1` |
| T16 | regressione: tutti i test esistenti (412) con `DIB_DIST_MTLS=0` | invariati |

**Costo (misura M4 di audit 04, dopo l'OK sulle misure).** Tre bracci per isolare le cause: (i) HTTP senza pool, come oggi; (ii) HTTP con pool; (iii) mTLS con pool. In più (iv) mTLS senza pool, per mostrare il costo dell'handshake per chiamata. Si rimisurano anche gli errori sulle connessioni in pool (oggi 6 su 64.400, `results/site_count/README.md`).

## 7. Effetti sul paper (piano §6.3) [D]

- Il quorum di "siti distinti" diventa un quorum di **identità emesse dalla CA**: la difesa dalle identità fabbricate (Sybil) è l'emissione dei certificati, e va scritto nei test Sybil.
- Con la proposta di sez. 3.2, anche **ES_d** diventa una decisione di governance verificata e non un'autodichiarazione.
- Un sito compromesso può disputare (disponibilità) ma non autorizzare (T14).
- Ingresso e uscita dei membri (S3) = emissione e revoca.

## 8. Domande aperte per te

- **Q1.** Operatore locale: lo strumento dell'operatore usa il certificato del **sito** (un solo SAN per sito), o un certificato **operatore** separato emesso per quel sito (`spiffe://dib.consortium/site/<id>/operator`)? Il secondo rende T14 più forte: rubare il certificato di servizio non basta per `/commit`. Aggiunge un quarto tipo di identità, ma non un quarto ruolo di consorzio. Raccomandazione: il secondo.
- **Q2.** Opzione B (raccomandata) o A per la terminazione?
- **Q3.** step-ca come dipendenza (solo documentata, o anche usata nelle misure)? Per test e misure basta OpenSSL.
- **Q4.** Il registry single-node (API) è in ambito per mTLS (passo 6), o solo il prototipo distribuito?
- **Q5.** Mappatura dei tipi per sito (ES_d verificabile): sì o no?
- **Q6.** Revoca: basta la denylist, o vuoi anche la CRL?

## 9. Decisioni dell'utente e stato dell'implementazione (2026-10-10)

**Risposte:**
- **Q1:** certificato operatore separato, sì.
- **Q2:** opzione B con uvicorn bloccato; ripiego su A se richiede più di circa un giorno o risulta fragile.
- **Q3:** solo OpenSSL; step-ca solo descritto come opzione di deployment.
- **Q4:** registry single-node solo se usa lo stesso code path del distribuito e il diff è piccolo.
- **Q5:** lista dei tipi sì, opzionale, spenta di default, accesa nel braccio mTLS. **Scelta di modello da discutere col supervisore.**
- **Q6:** denylist e certificati a vita breve, niente CRL.

| Passo | Commit | Cosa | Test (scritti prima del codice, eseguiti rossi, poi verdi) |
|---|---|---|---|
| 1 | `3f8d6fd` | `code/src/dib/registry/distributed/mtls.py`: `PeerCertH11Protocol` (opzione B), `server_config`, `client_context`, `Identities` (mappatura con denylist, ricaricata quando cambia), entry point `python -m dib.registry.distributed.mtls`; pin `UVICORN_VERSION = "0.51.0"` controllato all'avvio | `test_mtls_peer_identity.py` (7): SAN visibile all'app; handshake rifiutato senza certificato (T2), con CA sconosciuta (T3), certificato scaduto (T4) o solo `codeSigning`, cioè certificato di firma MUD (T13); identità per connessione; pin |
| 2 | `9413c20` | `service.py`: `_authorize` e `_reporter` secondo la matrice della sez. 3.3, dietro `DIB_DIST_MTLS=1`; chiamate in uscita con `verify=client_context`; `DIB_DIST_TYPE_LIST=1` (richiede mTLS) | `test_mtls_authorization.py` (17), su socket TLS reali (1 evidence + 2 siti come processi): T1, T5 (denylist senza riavvio), T6, T7, T8, T9, T10, T11, T12, T14, Q5, più un controllo che la lista tipi senza mTLS impedisca l'avvio |
| 3 | `10e3aeb` | Dockerfile con `uvicorn==0.51.0` e `mtls.py`; `generate_compose.py` con `DIB_DIST_MTLS`, `DIB_DIST_TYPE_LIST`, `DIB_DIST_PKI_DIR` | `test_mtls_compose.py` (3): output senza mTLS byte per byte identico al compose committato; topologia mTLS; pin e copia nell'immagine. Nulla costruito né eseguito |
| 4 | `3cb6d34` | solo test | `test_mtls_oracle.py` (T15): lo stesso episodio con e senza mTLS dà gli stessi (stato, origine, ACE) a ogni passo; un fatto è esportato se e solo se è Active; il veto locale sopravvive; il restore globale non riattiva |

**Opzione B: tempo e fragilità.** Funzionante in meno di un giorno. Il punto di aggancio è `connection_made` più la lettura di `self.app` a ogni richiesta (`uvicorn/protocols/http/h11_impl.py:232`). La fragilità è coperta dal pin, controllato all'avvio e in un test. **Non è stato necessario passare all'opzione A.**

**Dopo ogni commit:**
- suite: 412 → 419 → 436 → 439 → 440 passed, sia su 3.10.13 sia su 3.12.15 (su 3.12 lo stesso warning di anyio);
- **i 412 test preesistenti passano invariati con mTLS spento (T16)**;
- `verify_artifact.py`: sempre 260 passed e 2 failed, gli stessi due controlli sull'hash di `service.py`. L'hash è passato da `48415497…` a `31863043…` al passo 2;
- nessuna scrittura in `results/`, nessuna rigenerazione (resta G0b).

**Scostamenti dal design, da approvare:**
1. **Mappatura in JSON, non YAML:** l'immagine non contiene pyyaml.
2. **Nessun pool di connessioni nelle chiamate fra servizi** (design §4, ultimo paragrafo). I test esistenti sostituiscono le funzioni di modulo `httpx.get` e `httpx.post` (`_dist_harness.py:172-173`); passare a `httpx.Client` richiederebbe di riscrivere il trasporto del harness per 131 test. Quindi ogni chiamata fra servizi con mTLS fa un handshake TLS completo, e M4 avrà i bracci "HTTP senza pool" e "mTLS senza pool". Il braccio con pool richiede una tua decisione sulla modifica del harness.
3. **Q4: il registry single-node resta fuori.** `api.py` passa per `services.py` (SQLAlchemy), un code path diverso da `service.py`. Limite dichiarato: nel registry single-node l'identità resta nel payload (API:28-29, :104, :200, :271).
4. **Dove agisce la lista tipi (Q5).** Il distribuito non ha un endpoint di osservazione, quindi la lista limita `/attest` e `/dispute`: un sito può dichiarare evidenza o disputare solo per i tipi che opera. **ES_d all'ingresso delle osservazioni resta non verificato** (manca un punto di ingresso nel distribuito; il single-node è fuori per Q4). La nota di `paper_edits_proposed.md` §1a ("the prototype does not implement this check") resta quindi vera per il denominatore di C_s. Scelta di modello da discutere col supervisore.
5. **Revoca senza CRL (Q6).** Un SAN revocato è rifiutato appena ogni servizio rilegge la mappatura. Un servizio con una mappatura non aggiornata continua ad accettarlo **fino alla scadenza del certificato**: 24 h nella CA di test, configurabile.
6. **Ancora da fare per M3 e M4** (non in questo passo):
   - uno script che generi la PKI per il deployment Docker: certificati server con SAN DNS `evidence` e `site-<i>`, operatori, amministratore, mappatura;
   - il benchmark (`code/scripts/distributed_concurrency_benchmark.py`) deve presentare i certificati operatore, member e admin;
   - l'immagine resta `python:3.11-slim` mentre per le misure è stato scelto 3.12 (G1): decidere se l'immagine passa a 3.12, il che cambia anche il braccio senza mTLS.

### 9.1 Aggiornamento (decisioni utente, 2026-10-10)

**Scostamenti approvati:**
1. **Nessun pool fra servizi.** L'handshake TLS completo per ogni chiamata fra servizi è il **caso peggiore**, riportato come **limite superiore dichiarato** del costo di mTLS. Se in M4 pesa troppo, si valuta un braccio con client persistente solo nel benchmark, senza toccare `service.py`.
2. **Registry single-node fuori ambito.** Limite dichiarato: lì l'identità resta nel payload.
3. **Lista tipi solo su `/attest` e `/dispute`**, senza estensioni. **Limite da discutere col supervisore:** ES_d all'ingresso delle osservazioni **non è verificato**. Il denominatore di C_s resta autodichiarato (`dib.py:198`, H2 del REPORT), e la frase proposta in `paper_edits_proposed.md` §1a resta vera.

**Preparazione di M3/M4, un commit ciascuno, test prima:**

| Commit | Cosa | Test |
|---|---|---|
| `23d7700` | `code/scripts/make_dist_pki.py`: PKI OpenSSL per Docker, deterministica tranne le chiavi, certificati da 24 h, chiave della CA in `<out>.ca/`, rifiuto di scrivere chiavi in cartelle della repo non ignorate. Cartelle predefinite in `.gitignore`. `_mtls_ca.TestCA` ora riusa la stessa CA | `test_make_dist_pki.py` (4) |
| `0ac6a51` | `distributed_concurrency_benchmark.py --pki`: identità operatore per sito e admin, `--evidence-url`/`--site-urls` per un host remoto, **403 contato come errore inatteso** (`http.403`) in entrambe le modalità | `test_benchmark_mtls.py` (3), su processi mTLS reali |
| `2afdb04` | immagine `python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1` (Python 3.12.15). Cambia anche il braccio senza mTLS | `test_mtls_compose.py::test_c4` |

Suite 448 passed su 3.10 e 3.12. `verify_artifact` sempre 260/2, con gli stessi due controlli della Fase 0 (`scripts/verify_artifact.py:250`, `:323`): stesso valore registrato in `results/` (`d09f8db5…`, v43); cambia solo l'atteso, che è l'hash corrente di `service.py` (`31863043…`).
