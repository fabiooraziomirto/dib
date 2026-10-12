# Audit 87 — Code review di service.py, correzioni integrate e stima dei tempi del rerun

Data: 2026-10-12. Decisione dell'utente (stessa data): le correzioni fondamentali, cioè quelle che possono cambiare il paper, si fanno e gli esperimenti si rieseguono; tetto accettato 48 h. Righe di `service.py` riferite a `tnsm-driver-retry` prima della correzione (hash `0501b383…` del congelato a `6e6d352` più i commit keep-alive e concorrenza).

## 1. Review (lettura del codice, nessuna esecuzione; sub-agente in sola lettura, verificata a campione da me)

| # | Gravità | Difetto | File:riga | Tocca B1/B5/B2k? |
|---|---|---|---|---|
| 1 | media-alta | `/local_restore`: un evento arrivato fra lettura e scrittura lascia il sito `monitor-only` con evidence DISPUTED/REVOKED; il reconcile non lo ripara perché `item["seq"] <= last` | service.py:559-577, 473-496, 594 | no |
| 2 | media | keep-alive: un client chiuso da un altro thread solleva `RuntimeError`, che non è `httpx.HTTPError`: esce dal retry senza passare dall'outbox | service.py:795-814 | solo con `DIB_DIST_FANOUT_KEEPALIVE=1` |
| 3 | media | quorum 2: chi ha votato la sospensione può confermare la revoca | service.py:919 (quorum letto a :127, default 1) | solo con quorum 2 |
| 4 | bassa-media | `/query` può perdere un evento fra lettura e INSERT (riparato dal reconcile entro T) | service.py:501-515 | no |
| 5 | bassa | `/commit` transitoriamente active; `/local_revoke` dà 500 con evidence irraggiungibile | service.py:520-556 | no |

Quorum usato dalle misure: `run.py` non imposta `DIB_DIST_SUSPENSION_QUORUM`, quindi default 1. B1, B5, B2k, il testbed e audit 86 non sono toccati dal punto 3. Keep-alive spento in tutte le misure tranne audit 62/76, che quindi risentono del punto 2 (già falsificate, non proposte). Nessun deadlock, nessun fan-out fuori ordine con effetto, nessun leak a keep-alive spento (review).

## 2. Correzioni integrate (branch `tnsm-fixes`, worktree `/root/Desktop/DIB_tnsm_fixes`, commit `dc3dd20`)
- FQ, FC, FR, FV, FQ2: sostituzioni di testo di `test_distributed_fsm_fix_copy.py:48-195`, applicate con ancore uniche.
- Punto 2: `RuntimeError` del client keep-alive diventa `httpx.TransportError` solo nel ramo keep-alive e il client si scarta; test K-11 rosso prima, verde dopo. Un primo tentativo più largo faceva fallire 4 test (D19 s2, F8): scartato, i test non sono stati toccati.
- Test: 491 passed, 7 skipped, 8 xfailed. Le 5 ipotesi che erano xfail ora passano; il vecchio comportamento resta come caratterizzazione xfail strict; `b3q_2` riformulato come H-F3 (riga assente o disputed). `service.py` nuovo: sha256 `5599f53b486c838a6866f5cd8b5037da4ad5cdec779dc6d68d354f1a9ea129be`.
- Rischi residui dichiarati dalla review sulle correzioni (non coperti da test): righe `staging`/`committing` dopo un crash (permanenti con `fanout_seq == 0`), `/query` senza timeout durante un reconcile, `/local_revoke` 404→409 per fatto sconosciuto, vincolo UNIQUE assente sul lookup per (device_type, endpoint, protocol, port) (service.py:442-443).

## 3. Cosa va rieseguito sul codice corretto e quanto costa

Regola: si rieseguisce ciò che passa da `/query`, `/commit` (setup di ogni episodio), `/dispute` e dal fan-out, perché l'hash cambia e la review non ha eseguito nulla. Una macchina alla volta (niente esecuzioni concorrenti sul nodo: contaminerebbero i tempi). Il netem è applicato dall'applicatore in user space (audit 85/86), quindi senza sudo né watcher.

| Blocco | Cosa | Stima (h) | Fondamento della stima |
|---|---|---|---|
| R0 | Albero congelato nuovo da `tnsm-fixes` + hash + smoke `lan` | 0,3 | smoke `lan` ~1,5 min e `degraded` ~6,7 min (a43:125), più margine |
| R1 | Deployment completo B1 `degraded`, D e C × FANOUT 10 e 1, 50 episodi (replica di audit 86) | 1,4 | misurato: 05:12-06:33Z = 1,35 h (a86) |
| R2 | B5 `degraded` (criteri audit 46, soglie come audit 50) | 1,4 | a43:181 (13:17-14:43 = 1,4 h) |
| R3 | B2k completo (`lan`/`degraded`/`wan`, k = 1/10/50, DNS fix) | 2,4-3,1 | a43:135 (2,36 h; 3,06 h con L_dns lento): stima non fondata con l'applicatore in user space |
| R4 | Replica nei container del nodo (audit 83/84) | 1,3 | non registrata in questo audit: stima non fondata |
| R5 | Testbed locale: suite v4/s1/v3 | 2-3 | stima non fondata (non ho i tempi di parete registrati) |
| R6 | Offline (A2 passo 1, A4, T1/T2, m/rho, split-ablation, M8) | 0,5-1 | secondi/minuti ciascuno; M8 stima non fondata |
| **Totale core (R0-R6)** | | **≈ 9,3-11,5 h** | somma delle righe |

Estensioni possibili con il margine delle 48 h (ognuna da decidere):
- B3 `mixed`/`regional`/`extreme`: ~0,5 h per profilo (a43:159, `extreme` non fondata).
- B2p (partizioni asimmetriche): 7,64 h (a43:148), solo se Q4+Q5 lo include.
- Seconda ripetizione indipendente di R1/R2 in un altro giorno, per verificare la stabilità fra repliche sullo stesso nodo: +2,8 h.
- Test dei punti 4 e 5 della review in un blocco dedicato (veto offline con evidence giù, quorum 2 a 3 siti, race `/query`/`/commit` con thread reali): da progettare, stima non disponibile.

## 4. Ordine proposto e criteri
1. R0, poi R1 (stessa pre-registrazione di audit 85, stessi criteri H-N1/H-N2, nessuna modifica): se H-N1 o H-N2 cadono sul codice nuovo si ferma e si riporta.
2. R2, R3, R4, R5, R6 nell'ordine; per ogni blocco ipotesi e criterio di falsificazione prima dei dati, come per 42/45/46.
3. Confronto vecchio contro nuovo codice sullo stesso nodo e sugli stessi criteri: differenze entro gli intervalli di confidenza = il paper non cambia; fuori = si riporta e si decide.

## 5. Da decidere (non decido io)
- Albero del nodo da `tnsm-fixes`: nuovo `tree-<hash>` e `frozen_hashes_<hash>.txt`, senza toccare `467a711` (mai cancellare).
- Se adottare le correzioni in `tnsm-driver-retry` o tenere `tnsm-fixes` come branch di rilascio.
- Se i residui della review (sez. 2) vanno corretti prima del rerun o dichiarati nel paper.
