# Audit 65 — Progetti (non implementati): lease per i siti irraggiungibili (a5) ed epoch del seq (b8)

Data: 2026-10-12. Branch `tnsm-fsm`. Obiettivo 4 del prompt dell'audit 61. **Solo progetto**: nessun
codice scritto. Righe di S = `service.py` a `6e6d352` (sha256 `0501b383…3d42a64`). Alla fine ti
chiedo quale dei due implementare (o nessuno).

## 0. Il problema, con le righe
- **a5.** Un sito che non riceve più eventi continua a esportare i suoi active senza limite:
  `/export_mud` legge solo `local_decisions` (S:682-709) e non sa da quanto il sito non vede
  l'evidence. Il paper lo dichiara: AS6 "after an unbounded time" (main_wip.tex:179), I3 "No timing
  bound is imposed on reconciliation" (:340), G3 "imposes no deadline" (:164). Con
  `RECONCILE_INTERVAL = 0` di default (S:143) nemmeno un sito raggiungibile ha un limite. L'unica
  misura di freschezza esistente è `last_success_at` del trigger (S:275), esposta in `/health`
  (S:288), che non è usata da nessuna decisione.
- **b8 (epoch).** `fanout_seq` è un contatore per fatto nel DB dell'evidence (S:745). Il sito scarta
  ogni evento con `seq ≤ last_applied_seq` (S:480-481). Se il DB dell'evidence viene perso e
  ricreato, i fatti ripartono da seq 0 (e lo `score_id` può anche essere riassegnato a un altro
  fatto, perché è un `INTEGER PRIMARY KEY` autoincrementato, S:743). I siti ignorano allora ogni
  dispute nuova finché il nuovo seq non supera quello vecchio. È un difetto di sicurezza: una
  withdrawal persa in silenzio. L'anti-entropia non aiuta, perché confronta lo stesso seq (S:593).
  Il docstring lo esclude già dal bound ("loss of the evidence database", S:82-83).

## 1. Lease (scadenza degli active per freschezza)

**Regola proposta.** Ogni sito tiene `fresh_at` = istante (orologio monotono locale) dell'ultima
`GET /pending` riuscita, cioè dell'ultimo snapshot `current` applicato (S:623, S:584-601). Un active
è *esportabile* solo se `now − fresh_at ≤ L`. Oltre L, `/export_mud` omette gli active (fail-closed).
Lo stato non cambia: il record resta active e torna esportabile appena una reconcile riesce. Quindi
nessun nuovo commit è necessario dopo una partizione breve.

**Prerequisiti.**
- `RECONCILE_INTERVAL = T > 0` con `T + J + 2·d_run < L` (docstring S:53-68); altrimenti il lease
  scade anche senza partizione.
- L'orologio è quello monotono del sito: nessuna sincronizzazione fra siti.
- Il gateway deve ri-scaricare l'export almeno ogni L. Oggi il testbed applica l'export una volta,
  e main_wip.tex:343 dice che un gateway irraggiungibile "can retain an older policy". Senza questo
  il lease protegge solo l'export, non l'enforcement.
- Modifica di AS6/I3 nel paper: la withdrawal diventa limitata da L + tempo di ri-scaricamento del
  gateway, anche a un sito irraggiungibile.

**Effetti su I1-I3.**
- I1: invariato (il lease toglie esportabilità, non la crea; lo stato active resta frutto di un
  commit).
- I2: invariato (solo stato locale del sito).
- I3: rafforzato. Oggi la dispute ha effetto a un sito irraggiungibile solo "upon reconciliation";
  con il lease ha effetto al più tardi dopo L, anche se il sito non si riconnette mai.
- Eq. exportable (main_wip.tex:302-303) diventa `Active ∧ grantValid ∧ fresh(s)`.

**Costo di disponibilità.** È il punto critico:
- un'evidence ferma più di L svuota gli export di **tutti** i siti, anche senza alcuna dispute
  (fail-closed globale). Con L = 1 h un guasto dell'evidence di un'ora toglie tutte le regole DIB;
- in alternativa: un fail-open per i soli fatti senza episodi recenti, ma allora il lease non
  protegge proprio il caso a5 (dispute persa durante la partizione);
- compromesso: L lungo (ore) e un allarme prima della scadenza. Va scelto in base al tempo di
  ripristino dell'evidence, che non è misurato.

**Test falsificanti (in-process, `FakeClock`, nessuna rete).**
1. Sito active, evidence giù, orologio avanzato di L − ε: l'export contiene il fatto; di L + ε:
   non lo contiene. Lo stato resta active.
2. Dopo una reconcile riuscita il fatto torna nell'export senza commit.
3. Dispute persa (sito down) + L + ε: il fatto non è esportato anche senza reconcile (è il caso a5).
4. Il lease non rende esportabile niente che oggi non lo sia (differenziale: export_lease ⊆ export_oggi
   a ogni passo del generatore di audit 64).
5. Mutante: confronto `≤` invertito → il test 1 deve fallire.

## 2. Epoch del seq

**Regola proposta.** L'evidence crea un `epoch` casuale (128 bit) alla creazione del DB e lo
restituisce in `/scores`, `/pending` e in ogni `/apply_fanout`. Il sito memorizza l'epoch per
fatto (o globalmente) accanto a `last_applied_seq`. Un evento con epoch diverso da quello noto
viene trattato come "più nuovo di tutto". Il sito applica lo stato attuale in modo conservativo:
- un fatto `disputed`/`revoked` nel nuovo epoch applica quel target;
- un fatto `active` nel nuovo epoch porta il record (non revocato localmente) a monitor-only, come un
  restore: un'approvazione del vecchio epoch non sopravvive;
- un fatto assente nel nuovo epoch (DB vuoto): il record non viene toccato, ma diventa non
  esportabile finché l'evidence non lo conosce di nuovo.
Poi `last_applied_seq` riparte dal seq del nuovo epoch. In più, il sito deve legare `score_id` alla
tupla `(device_type, endpoint, protocol, port)` (già in `local_decisions`, S:440-442), così uno
`score_id` riassegnato non viene applicato al fatto sbagliato.

**Prerequisiti.** Un campo `epoch` nello schema dell'evidence e in quello del sito (migrazione).
Senza mTLS (AS1) chiunque può inviare `/apply_fanout` con un epoch nuovo e forzare un reset: con
mTLS solo il ruolo `evidence` può farlo (S:578-582).

**Effetti su I1-I3.**
- I1: invariato (nessun reset porta in active).
- I2: invariato.
- I3: chiude il caso "loss of the evidence database" oggi escluso dal bound (S:82-83). Il veto
  locale resta preservato (stessa guardia di provenienza S:482-490).

**Costo di disponibilità.** Dopo la ricostruzione dell'evidence tutti gli active tornano
monitor-only e servono nuovi commit in ogni sito. È il comportamento conservativo voluto da I3,
ma costa un ciclo di revisione completo. Il costo di rete è nullo (un campo in più per messaggio).

**Test falsificanti (in-process).**
1. Ricreare il DB evidence nel harness (nuova istanza evidence, stessi siti): una dispute nuova
   (seq 1) deve arrivare a un sito che aveva `last_applied_seq = 3`. Oggi è ignorata (S:480-481):
   test rosso atteso sul codice attuale, da pre-registrare.
2. Uno `score_id` riassegnato a un altro fatto non deve cambiare il record del fatto vecchio.
3. Veto locale preservato attraverso il cambio di epoch.
4. Un evento con l'epoch vecchio dopo il cambio è ignorato.
5. Mutante: confronto di epoch rimosso → il test 1 torna rosso.

## 3. Confronto e raccomandazione
| | Lease | Epoch |
|---|---|---|
| Problema chiuso | withdrawal senza limite di tempo a un sito irraggiungibile (a5) | withdrawal persa dopo la ricostruzione dell'evidence (b8) |
| Cambia il paper | sì (AS6, I3, Eq. exportable, G3) | no, toglie un'esclusione dal bound |
| Rischio | fail-closed globale se l'evidence è giù più di L | reset forzabile senza mTLS |
| Dimensione stimata | export + un timestamp; test con FakeClock | schema di due DB, payload, guardia di apply |

Raccomando di implementare per primo l'**epoch**: è locale, non cambia le promesse del paper e
chiude un difetto silenzioso di sicurezza. Il lease cambia le assunzioni del paper e ha un costo di
disponibilità che va deciso con il supervisor (valore di L, comportamento del gateway).
