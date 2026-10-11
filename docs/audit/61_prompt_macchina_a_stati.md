# Prompt per la chat sulla macchina a stati del lifecycle MUD (da incollare in un'altra sessione Claude)

Origine: raccolta in sola lettura da un agente (2026-10-12), poi rivista. Verificate di persona le righe di `service.py` 142, 380-389, 399-414, 416-436, 476-495; **tutte le altre righe citate sotto sono dell'agente e vanno trattate come NON VERIFICATE finché la nuova chat non le rilegge**. Correzioni rispetto al report dell'agente: (c1) la correzione del driver è già committata sul branch `tnsm-driver-retry` (`1f91d38`, test `d595ef6`); (c2) il costo di un tentativo fallito **non** è "3-4 s": l'audit 60 §3 lo modella a 1,0-1,8 s (limite superiore per fase 1 s, `ATTEMPT_HARD_S` è un tetto, non il costo tipico); il fattore dominante a `degraded` è il default sequenziale `DIB_DIST_FANOUT_CONCURRENCY=1` (`service.py:146`).

```
Contesto del progetto
Lavori nella repo /root/Desktop/DIB_tnsm (branch di partenza: tnsm-driver-retry, da revision-tnsm), progetto DIB: gestione di policy MUD (RFC 8520) autorizzate localmente a partire da osservazioni condivise fra i siti di un consorzio IoT. Il paper è per IEEE TNSM; la copia di lavoro del testo è docs/main_wip.tex (canonica per decisione dell'utente). docs/audit/NN_*.md contiene ipotesi pre-registrate, risultati e decisioni (i più rilevanti: 05, 07, 56, 57, 59, 60).

La macchina a stati
Ogni sito ha, per ogni fatto endpoint (device_type, endpoint, protocol, port), uno stato locale fra Absent, MonitorOnly ("monitor-only" nel codice), Active, Disputed, Revoked. Revoked ha un'origine: dispute (nel codice "fanout") oppure locale. Il servizio evidence tiene lo stato globale del fatto (active/disputed/revoked), disputed_by e fanout_seq per fatto.
- Una prima dispute porta a Disputed; una seconda da un sito diverso a Revoked.
- Il restore globale (solo consortium_admin) riporta i record dispute-derived a MonitorOnly e non ricrea mai un'approvazione.
- La revoca locale (local_revoke) è del solo sito, non si propaga e sopravvive al restore globale; local_restore è bloccato finché esiste un episodio di dispute aperto.
- Un sito irraggiungibile riceve gli eventi tramite outbox (una riga per (sito, fatto), vince il seq maggiore), /reconcile e anti-entropia basata sullo stato ("current").
Invarianti da preservare (paper): I1 (solo l'operator-commit del sito porta in Active), I2 (confinamento: le azioni locali non cambiano i record dei pari), I3 (inversione conservativa: la dispute invalida grant ed export, il restore richiede un nuovo commit e preserva i veti locali).
File principali: code/src/dib/registry/distributed/service.py ("S"), code/src/dib/registry/services.py ("SV", monolite), formal/base/DIB.tla, formal/distributed/DIB_Distributed.tla, formal/distributed_ae/DIB_AE.tla (+README, cfg), code/tests/tests/ (test_distributed_*.py, _dist_harness.py, test_registry_lifecycle_gaps.py), docs/main_wip.tex (G3 :157, AS6 :179, transizioni :314-330, I1-I3 :336-340, limiti :606, :640, :780).

Vincoli (obbligatori)
1. Non modificare formal/, claims.json né results/ senza chiedermelo e aspettare la risposta.
2. Niente TLC, Docker, esperimenti, ssh né comandi lunghi senza chiedere. Test pytest brevi sul codice sono consentiti.
3. Ipotesi (cosa dovrebbe succedere e cosa la falsificherebbe) scritte PRIMA di eseguire qualunque test o misura.
4. Un commit per passo. Se un test fallisce, riportalo così com'è: non indebolire né cancellare il test.
5. Ogni affermazione con file:riga; se non hai letto la riga scrivi NON VERIFICATO. Non inventare numeri.
6. Non toccare file congelati per hash (service.py e run.py dei blocchi) senza autorizzazione esplicita e senza dichiarare il nuovo hash.
7. Non scrivere nel paper né in results/; lavora su branch o commit separati. Non cancellare nulla che possa servire; non uscire dal perimetro /root/Desktop/DIB*.

Problemi noti (S = service.py, SV = services.py; le righe NON marcate "verificato" vanno rilette)
Specifica e modello
- a1. L'ammissione è un Booleano nel modello (formal/base/DIB.tla:14-16, :63); nel distribuito `accepted` vale sempre 1 (S:753) e il controllo "not admissible" (S:442) non può scattare; il Rescore non è modellato.
- a2. Il restore diverge: il monolite resetta solo DISPUTED/REVOKED (SV:750-751), il distribuito porta qualunque stato non vincolato da veto locale a monitor-only (S:401-414, verificato).
- a3. La tabella del paper (main_wip.tex:324) non elenca il restore globale su un sito Active/MonitorOnly che ha perso la dispute; "retention expiry" (:327) non risulta implementata.
- a4. I1-I3 sul codice reale sono verificate solo tramite lo stato finale monitor-only (docs/audit/57); nessun controllo a ogni passo.
- a5. Nessuna scadenza/lease per i siti irraggiungibili (AS6, main_wip.tex:179, :487, :780; audit 43 Q2): /export_mud (S:600-628) esporta ciò che è active senza freschezza.
- a6/a7. Partizioni asimmetriche fuori valutazione; AE ha un solo flag `unreachable`; 2 siti, MaxEvents ≤ 2; quorum 2, tempo, mTLS, crash non modellati; delle 43 cfg di distributed_ae risultano eseguiti pochi log (NON VERIFICATO altrove).
- a8. Query e LocalRestore sono atomici nel modello ma non nel codice (S:416-436 e S:476-495: lettura HTTP dell'evidence e poi transazione locale separata, verificato); LocalRevoke/LocalRestore non dipendono dall'evidence nel modello ma sì nel codice.
- a10. Con SUSPENSION_QUORUM=2 gli stessi due siti portano a Revoked (S:821-835; test_distributed_service_inproc.py:108-122); l'intenzione di progetto è NON VERIFICATA.
Comportamento del codice
- b1. Pending collassato per (sito, fatto) (S:666-667, S:722-724): un sito Active che perde dispute+restore torna monitor-only (S:401-414).
- b2. Fan-out fuori dalla transazione (S:838-840, S:861-862): ordine non garantito (la guardia seq rende idempotente); un 500 non implica stato invariato.
- b3. TOCTOU (verificato per lettura): /query legge l'evidence (S:419) e poi inserisce con seq letto prima (S:431); /local_restore controlla lo stato (S:482) e poi aggiorna in una transazione separata (S:485-493): una dispute arrivata nel mezzo può lasciare il record in monitor-only durante un episodio aperto con seq già avanzato. Nessun test noto lo copre.
- b4. /local_revoke e /local_restore chiamano `_evidence_get_score` (S:380-389) senza try: con evidence giù l'azione locale fallisce con 500 (verificato per lettura): il veto locale dipende dalla rete.
- b5. La revoca locale non si propaga e non conta come voto (per design, I2).
- b6. I voti del quorum 2 (suspension_reports, S:668-669) non scadono; restore e dispute concorrenti con più di 2 siti non sono testati né modellati.
- b7. Senza mTLS site_id è nel payload (S:781-792): due site_id dallo stesso client revocano.
- b8. RECONCILE_INTERVAL=0 di default (S:142, verificato: staleness illimitata); retry 3×1 s senza pausa né jitter (S:120-121, 705-716); nessun epoch sul seq (reset del DB evidence → eventi ignorati, S:399); ack in `finally` che può mascherare un'eccezione (S:561-566).
- b9. `current` di /pending cresce linearmente con i fatti (S:880, :888-892).
Difetti dalle misure
- c1. (RISOLTO sul branch tnsm-driver-retry, commit 1f91d38; nuovo hash da congelare) dopo un client_timeout il driver non riavviava site-3 (docs/audit/57).
- c2. (a) e (a′) falsificate a `degraded` (docs/audit/56); il fattore principale è il default sequenziale FANOUT_CONCURRENCY=1 (S:146): D 10,3 s e C 18,5 s con FANOUT 1 contro 1,6 e 2,8 s con FANOUT 10 (audit 60 §2).
- c3. Coda di B2k vicina al bound (98,6 %) a degraded/C; k=50 mai misurato (audit 57).
- c4. M3b: 13 errori su 1.288.000 operazioni (audit 18), causa non determinata.
Debiti
- d1. Configurazione letta all'import (S:119-170). d2. Default FANOUT_CONCURRENCY=1 e RECONCILE_INTERVAL=0 contro la compose (T=5, concorrenza 8). d3. Nomi incoerenti (monitor-only/MonitorOnly, "fanout"/"Dispute", Absent assente nel codice). d4. Righe obsolete nei commenti dei modelli e dei test. d5. Due implementazioni dello stesso FSM (SV e S).

Obiettivi, in ordine di priorità (proponi un piano e aspetta il mio OK prima di eseguirlo)
1. Specifica del FSM (tabella stato × evento × guardia × effetto, per evidence, sito e monolite) che chiuda a1, a2, a3, a10; segnala ogni divergenza fra SV e S e fra codice e main_wip.tex, senza modificare il paper.
2. Test pytest nuovi (rossi se rivelano bug) per b3 (dispute fra lettura dell'evidence e transazione locale in /query, /commit, /local_restore), b4 (/local_revoke con evidence giù) e b6 (restore e dispute concorrenti con ≥ 3 siti), con ipotesi pre-registrate.
3. Controllo differenziale: sequenze di eventi casuali (seed fisso) sul servizio in-process (_dist_harness.py) con I1-I3 verificate a ogni passo, più un mutante che deve far fallire il controllo (a4).
4. Proponi, senza implementarli, un progetto di lease/scadenza per i siti irraggiungibili (a5) e uno per l'epoch del seq (b8): prerequisiti, effetti su I1-I3, costo di disponibilità, test falsificanti. Poi chiedimi quale implementare.
5. Elenca le estensioni TLA+ (a1, a6, a7, a8, a10) con una stima dello spazio degli stati. Non modificare formal/ e non lanciare TLC senza permesso.
6. Debiti d1-d5: correzioni minime di nomi e configurazione senza cambiare comportamento, un commit ciascuna, solo dopo il mio OK.

Formato del report finale: elenco numerato di ciò che hai fatto; per ogni passo commit hash, test eseguiti con esito reale, ipotesi iniziale e se è stata confermata o falsificata; sezione "NON VERIFICATO".
```
