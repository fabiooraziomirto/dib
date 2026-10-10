------------------------------- MODULE DIB_AE -------------------------------
(***************************************************************************)
(* Model of the REAL reconciliation protocol of the distributed prototype  *)
(* (code/src/dib/registry/distributed/service.py, HEAD b17cbab), in two    *)
(* variants selected by constants: without and with state-based            *)
(* anti-entropy (audit 06, D19). It replaces the atomic Reconcile of       *)
(* formal/distributed/DIB_Distributed.tla, which could not see D12 (ack    *)
(* race) or D19 (event lost between the state commit and the fan-out).     *)
(*                                                                         *)
(* STATUS: written and committed BEFORE any execution (audit 07, commit a).*)
(* Never run through SANY or TLC at the time of writing: syntax errors are *)
(* possible and will be reported as such, not silently fixed.              *)
(*                                                                         *)
(* Structure of one evidence event (code lines in service.py):             *)
(*   Ev* commit (dispute :747-779, restore :781-801): status + fanout_seq  *)
(*     change in ONE SQLite transaction, and `todo` receives one in-flight *)
(*     delivery per site (the fan-out :685, not yet started).              *)
(*   Deliver (_deliver_to_site :656-683): delivery reaches the site and    *)
(*     goes through ApplyResult, or fails (site unreachable from the       *)
(*     evidence) and the event is queued in the outbox, latest seq wins.   *)
(*   Lose (D19): the in-flight delivery vanishes without being queued     *)
(*     (exception between :778 and :779, non-HTTP error :675, failed       *)
(*     INSERT). One record at a time: whole-event loss = N losses.         *)
(* Site reconciliation (_reconcile_once :482-533), ONE run machine per     *)
(* site (single flight, _reconcile_lock :535): Read (GET /pending: outbox  *)
(* rows and, with AntiEntropy, the `current` list, same transaction),      *)
(* Apply (one item per step, any order), Ack (per pair or delete-all),     *)
(* re-read up to MaxRounds, then RepairStart / AntiEntropy / Finish        *)
(* (_repair_from_snapshot :463-480, on the LAST snapshot, even if the      *)
(* outbox was empty).                                                      *)
(*                                                                         *)
(* ApplyResult is ONE definition, a faithful copy of _apply_fanout_row     *)
(* (:356-379), used by delivery, reconcile and repair: the seq guard, the  *)
(* local veto and the origin rule are therefore the same everywhere.       *)
(*                                                                         *)
(* MODELLING CHOICES AND DECLARED DEVIATIONS                               *)
(*  1. `unreachable` = the evidence cannot deliver to the site (asymmetric *)
(*     partition or stopped site). The site's own reconcile run keeps going*)
(*     (site -> evidence is assumed up). The plan first said "SiteDown     *)
(*     resets the run"; that would make D12 unrepresentable (in the real   *)
(*     D12 scenario the site is reconciling while delivery to it fails),   *)
(*     so it was changed BEFORE any run.                                   *)
(*  2. Fairness is conditional: WF on a site's run steps only while the    *)
(*     site is NOT unreachable ("sites not unreachable" of the request).   *)
(*  3. Bounds (MaxEvents, MaxLoss, MaxToggles) are in the GUARDS, not in a *)
(*     TLC CONSTRAINT: a state constraint truncates behaviours and makes  *)
(*     temporal checking unreliable. Results hold ONLY within these bounds.*)
(*  4. Not modelled: time (T, J, d_run), process crash mid-transaction,    *)
(*     SQLite durability, apply errors per item, evidence unreachable      *)
(*     from the site, the 3 delivery retries (a delivery fails iff the     *)
(*     site is unreachable at that step), mTLS, SUSPENSION_QUORUM = 2,     *)
(*     admission/score (Query needs evidence status Active only, :383).    *)
(*  5. exported/grantValid of the old model are dropped: the code has no   *)
(*     such variables, export = state Active (:559-587).                   *)
(*  6. origin follows the code (:337): "Fanout" only on Revoked, else None.*)
(*  7. A fan-out dispute on a Revoked/Fanout site yields Disputed (code    *)
(*     :337-341, only the local veto is guarded); the old model kept       *)
(*     Revoked. The model follows the code.                                *)
(*  8. repair compares item.seq with `aseq`, the last_applied_seq values   *)
(*     read ONCE at the start of the repair (:528-531), as the code does;  *)
(*     ApplyResult's own seq guard is the second line of defence.          *)
(***************************************************************************)
EXTENDS Naturals, FiniteSets

CONSTANTS
    Sites, Facts, NoSite, NoFact,
    PartitionableSites,  \* sites that can become unreachable from the evidence
    AllowCommit,
    AntiEntropy,         \* the `current` list + repair step exist (audit 06)
    AckPerPair,          \* TRUE: ack deletes (score_id, seq<=applied); FALSE: delete-all
    ReRead,              \* TRUE: re-pull after a round that applied something
    MaxLoss,             \* number of Lose steps allowed (0 = D19 switched off)
    MaxRounds,           \* _RECONCILE_MAX_ROUNDS = 3 (:505)
    MaxEvents,           \* evidence commits allowed in a behaviour (also max seq)
    MaxToggles,          \* SiteDown/SiteUp steps allowed
    \* Mutation flags (all FALSE in the faithful model):
    MutIgnoreOrigin,        \* ApplyResult ignores the local veto
    MutWriteActive,         \* a restore lands in Active
    MutNoSeqGuard,          \* ApplyResult has no seq <= last_applied guard
    MutNonAtomicSnapshot,   \* outbox rows and `current` are read in two steps
    MutRestoreKeepsActive   \* a restore does not touch an Active site (old Reconcile)

VARIABLES
    estatus, eseq, edisp,      \* evidence: status, fanout_seq, disputed_by per fact
    outbox,                    \* outbox[t][f]: pending_fanout row of (site t, fact f) or NoRow
    todo,                      \* in-flight direct deliveries (the D19 window and the concurrency)
    sstate, sorigin, lastApplied,  \* site t, fact f: state, origin, last_applied_seq
    rc,                        \* rc[t]: the single reconcile run machine of site t
    unreachable, toggleCount,
    gen, commitGen,            \* ghost: dispute episodes per fact; episode of the last Commit
    evCount, lossCount,        \* ghost: bound counters
    lastOp

vars == <<estatus, eseq, edisp, outbox, todo, sstate, sorigin, lastApplied, rc,
          unreachable, toggleCount, gen, commitGen, evCount, lossCount, lastOp>>

States    == {"Absent", "MonitorOnly", "Active", "Disputed", "Revoked"}
Origins   == {"None", "Local", "Fanout"}
EStatuses == {"Active", "Disputed", "Revoked"}
Evs       == {"dispute", "revoke", "restore"}
Seqs      == 1..MaxEvents
NoRow     == [seq |-> 0, ev |-> "none"]
RowT      == {NoRow} \cup [seq: Seqs, ev: Evs]
TodoRecs  == [site: Sites, fact: Facts, seq: Seqs, ev: Evs]
Item      == [f: Facts, seq: Seqs, ev: Evs]
Pair      == [f: Facts, seq: Seqs]
Phases    == {"idle", "apply", "ack", "reread", "needcur", "needrows", "repair", "repairing"}
NoRec     == MaxEvents + 1   \* sentinel in aseq: site has no local record, nothing is newer
IdleRc    == [ph |-> "idle", rows |-> {}, done |-> {}, cur |-> {}, round |-> 0,
              aseq |-> [f \in Facts |-> 0]]
RcT       == [ph: Phases, rows: SUBSET Item, done: SUBSET Pair, cur: SUBSET Item,
              round: 0..MaxRounds, aseq: [Facts -> 0..NoRec]]
Ops       == {"Init", "Query", "Commit", "LocalRevoke", "LocalRestore",
              "EvDispute", "EvRevoke", "EvRestore", "Deliver", "Enqueue", "Lose",
              "Read", "ReadSecond", "Apply", "Ack", "RepairStart", "AntiEntropy",
              "Finish", "SiteDown", "SiteUp"}
ApplyOps  == {"Deliver", "Apply", "AntiEntropy"}
OpRecord  == [op: Ops, site: Sites \cup {NoSite}, fact: Facts \cup {NoFact},
              ev: Evs \cup {"none"}, seq: 0..MaxEvents]

TypeOK ==
    /\ estatus     \in [Facts -> EStatuses]
    /\ eseq        \in [Facts -> 0..MaxEvents]
    /\ edisp       \in [Facts -> Sites \cup {NoSite}]
    /\ outbox      \in [Sites -> [Facts -> RowT]]
    /\ todo        \in SUBSET TodoRecs
    /\ sstate      \in [Sites -> [Facts -> States]]
    /\ sorigin     \in [Sites -> [Facts -> Origins]]
    /\ lastApplied \in [Sites -> [Facts -> 0..MaxEvents]]
    /\ rc          \in [Sites -> RcT]
    /\ unreachable \in SUBSET Sites
    /\ toggleCount \in 0..MaxToggles
    /\ gen         \in [Facts -> 0..MaxEvents]
    /\ commitGen   \in [Sites -> [Facts -> 0..MaxEvents]]
    /\ evCount     \in 0..MaxEvents
    /\ lossCount   \in 0..MaxLoss
    /\ lastOp      \in OpRecord

Note(o, s, f, e, q) == lastOp' = [op |-> o, site |-> s, fact |-> f, ev |-> e, seq |-> q]

\* _STATUS_EVENT (:803-808): the event a site must apply to reach the evidence's current status.
EvOf(st) == IF st = "Disputed" THEN "dispute" ELSE IF st = "Revoked" THEN "revoke" ELSE "restore"

Init ==
    /\ estatus     = [f \in Facts |-> "Active"]
    /\ eseq        = [f \in Facts |-> 0]
    /\ edisp       = [f \in Facts |-> NoSite]
    /\ outbox      = [t \in Sites |-> [f \in Facts |-> NoRow]]
    /\ todo        = {}
    /\ sstate      = [t \in Sites |-> [f \in Facts |-> "Absent"]]
    /\ sorigin     = [t \in Sites |-> [f \in Facts |-> "None"]]
    /\ lastApplied = [t \in Sites |-> [f \in Facts |-> 0]]
    /\ rc          = [t \in Sites |-> IdleRc]
    /\ unreachable = {}
    /\ toggleCount = 0
    /\ gen         = [f \in Facts |-> 0]
    /\ commitGen   = [t \in Sites |-> [f \in Facts |-> 0]]
    /\ evCount     = 0
    /\ lossCount   = 0
    /\ lastOp      = [op |-> "Init", site |-> NoSite, fact |-> NoFact, ev |-> "none", seq |-> 0]

(***************************************************************************)
(* _apply_fanout_row (:356-379), one definition for every path.            *)
(***************************************************************************)
ApplyResult(t, f, seq, ev) ==
    LET st     == sstate[t][f]
        org    == sorigin[t][f]
        la     == lastApplied[t][f]
        noop   == [st |-> st, org |-> org, la |-> la]
        vetoed == st = "Revoked" /\ org = "Local" /\ ~MutIgnoreOrigin
        tgt    == IF ev = "restore"
                    THEN (IF MutWriteActive THEN "Active"
                          ELSE IF MutRestoreKeepsActive /\ st = "Active" THEN "Active"
                          ELSE "MonitorOnly")
                    ELSE (IF ev = "dispute" THEN "Disputed" ELSE "Revoked")
    IN  IF st = "Absent" THEN noop                                  \* :360-363 no local record
        ELSE IF seq <= la /\ ~MutNoSeqGuard THEN noop               \* :365-366 stale or duplicate
        ELSE IF vetoed THEN [st |-> st, org |-> org, la |-> seq]    \* :367-376 veto: only last_applied moves
        ELSE [st |-> tgt, org |-> (IF tgt = "Revoked" THEN "Fanout" ELSE "None"), la |-> seq]  \* :377-379

ApplyEffect(t, f, seq, ev) ==
    LET r == ApplyResult(t, f, seq, ev)
    IN  /\ sstate'      = [sstate EXCEPT ![t][f] = r.st]
        /\ sorigin'     = [sorigin EXCEPT ![t][f] = r.org]
        /\ lastApplied' = [lastApplied EXCEPT ![t][f] = r.la]

(***************************************************************************)
(* Evidence: the state commit (one transaction) and the fan-out start.     *)
(***************************************************************************)
EvCommit(f, st, e, newDisp, newGen, op, who) ==
    /\ evCount < MaxEvents
    /\ estatus' = [estatus EXCEPT ![f] = st]
    /\ eseq'    = [eseq EXCEPT ![f] = @ + 1]
    /\ edisp'   = [edisp EXCEPT ![f] = newDisp]
    /\ gen'     = [gen EXCEPT ![f] = newGen]
    /\ todo'    = todo \cup {[site |-> t, fact |-> f, seq |-> eseq[f] + 1, ev |-> e] : t \in Sites}
    /\ evCount' = evCount + 1
    /\ UNCHANGED <<outbox, sstate, sorigin, lastApplied, rc, unreachable, toggleCount,
                   commitGen, lossCount>>
    /\ Note(op, who, f, e, eseq[f] + 1)

Dispute(s, f) ==     \* dispute route :747-779 (quorum 1)
    \/ /\ estatus[f] = "Active"
       /\ EvCommit(f, "Disputed", "dispute", s, gen[f] + 1, "EvDispute", s)
    \/ /\ estatus[f] = "Disputed" /\ s # edisp[f]
       /\ EvCommit(f, "Revoked", "revoke", edisp[f], gen[f], "EvRevoke", s)

Restore(f) ==        \* restore route :781-801
    /\ estatus[f] \in {"Disputed", "Revoked"}
    /\ EvCommit(f, "Active", "restore", NoSite, gen[f], "EvRestore", NoSite)

Deliver(r) ==        \* _deliver_to_site :656-683
    /\ r \in todo
    /\ todo' = todo \ {r}
    /\ IF r.site \notin unreachable
       THEN /\ ApplyEffect(r.site, r.fact, r.seq, r.ev)
            /\ UNCHANGED outbox
            /\ Note("Deliver", r.site, r.fact, r.ev, r.seq)
       ELSE /\ outbox' = (IF r.seq > outbox[r.site][r.fact].seq
                          THEN [outbox EXCEPT ![r.site][r.fact] = [seq |-> r.seq, ev |-> r.ev]]
                          ELSE outbox)   \* ON CONFLICT ... WHERE excluded.seq > pending_fanout.seq
            /\ UNCHANGED <<sstate, sorigin, lastApplied>>
            /\ Note("Enqueue", r.site, r.fact, r.ev, r.seq)
    /\ UNCHANGED <<estatus, eseq, edisp, rc, unreachable, toggleCount, gen, commitGen,
                   evCount, lossCount>>

Lose(r) ==           \* D19: the in-flight delivery vanishes, nothing queued
    /\ lossCount < MaxLoss
    /\ r \in todo
    /\ todo' = todo \ {r}
    /\ lossCount' = lossCount + 1
    /\ UNCHANGED <<estatus, eseq, edisp, outbox, sstate, sorigin, lastApplied, rc,
                   unreachable, toggleCount, gen, commitGen, evCount>>
    /\ Note("Lose", r.site, r.fact, r.ev, r.seq)

(***************************************************************************)
(* Site-local operations, aligned to the code (not to the old model).      *)
(***************************************************************************)
Query(s, f) ==       \* :381-400, stages with last_applied_seq = fanout_seq
    /\ sstate[s][f] = "Absent"
    /\ estatus[f] = "Active"
    /\ sstate'      = [sstate EXCEPT ![s][f] = "MonitorOnly"]
    /\ sorigin'     = [sorigin EXCEPT ![s][f] = "None"]
    /\ lastApplied' = [lastApplied EXCEPT ![s][f] = eseq[f]]
    /\ UNCHANGED <<estatus, eseq, edisp, outbox, todo, rc, unreachable, toggleCount,
                   gen, commitGen, evCount, lossCount>>
    /\ Note("Query", s, f, "none", 0)

OperatorCommit(s, f) ==   \* :402-415 (global evidence Active AND local monitor-only)
    /\ AllowCommit
    /\ sstate[s][f] = "MonitorOnly"
    /\ estatus[f] = "Active"
    /\ sstate'    = [sstate EXCEPT ![s][f] = "Active"]
    /\ commitGen' = [commitGen EXCEPT ![s][f] = gen[f]]
    /\ UNCHANGED <<estatus, eseq, edisp, outbox, todo, sorigin, lastApplied, rc,
                   unreachable, toggleCount, gen, evCount, lossCount>>
    /\ Note("Commit", s, f, "none", 0)

LocalRevoke(s, f) ==      \* :417-436
    /\ \/ sstate[s][f] \in {"MonitorOnly", "Active", "Disputed"}
       \/ (sstate[s][f] = "Revoked" /\ sorigin[s][f] = "Fanout")
    /\ sstate'  = [sstate EXCEPT ![s][f] = "Revoked"]
    /\ sorigin' = [sorigin EXCEPT ![s][f] = "Local"]
    /\ UNCHANGED <<estatus, eseq, edisp, outbox, todo, lastApplied, rc, unreachable,
                   toggleCount, gen, commitGen, evCount, lossCount>>
    /\ Note("LocalRevoke", s, f, "none", 0)

LocalRestore(s, f) ==     \* :438-456 (refused while an episode is open)
    /\ sstate[s][f] = "Revoked" /\ sorigin[s][f] = "Local"
    /\ estatus[f] = "Active"
    /\ sstate'  = [sstate EXCEPT ![s][f] = "MonitorOnly"]
    /\ sorigin' = [sorigin EXCEPT ![s][f] = "None"]
    /\ UNCHANGED <<estatus, eseq, edisp, outbox, todo, lastApplied, rc, unreachable,
                   toggleCount, gen, commitGen, evCount, lossCount>>
    /\ Note("LocalRestore", s, f, "none", 0)

SiteDown(s) ==
    /\ s \in PartitionableSites /\ s \notin unreachable /\ toggleCount < MaxToggles
    /\ unreachable' = unreachable \cup {s}
    /\ toggleCount' = toggleCount + 1
    /\ UNCHANGED <<estatus, eseq, edisp, outbox, todo, sstate, sorigin, lastApplied, rc,
                   gen, commitGen, evCount, lossCount>>
    /\ Note("SiteDown", s, NoFact, "none", 0)

SiteUp(s) ==
    /\ s \in unreachable /\ toggleCount < MaxToggles
    /\ unreachable' = unreachable \ {s}
    /\ toggleCount' = toggleCount + 1
    /\ UNCHANGED <<estatus, eseq, edisp, outbox, todo, sstate, sorigin, lastApplied, rc,
                   gen, commitGen, evCount, lossCount>>
    /\ Note("SiteUp", s, NoFact, "none", 0)

(***************************************************************************)
(* The reconcile run of site t (_reconcile_once :482-533). The run does    *)
(* not require t \notin unreachable: unreachable only blocks the evidence's*)
(* deliveries (asymmetric partition); fairness is conditional instead.     *)
(***************************************************************************)
RowsOf(t) == {[f |-> f, seq |-> outbox[t][f].seq, ev |-> outbox[t][f].ev] :
                 f \in {g \in Facts : outbox[t][g].seq > 0}}
CurOf     == IF AntiEntropy
             THEN {[f |-> f, seq |-> eseq[f], ev |-> EvOf(estatus[f])] :
                     f \in {g \in Facts : eseq[g] > 0}}
             ELSE {}

RunUnch == UNCHANGED <<estatus, eseq, edisp, todo, unreachable, toggleCount, gen,
                       commitGen, evCount, lossCount>>

ReconcileRead(t) ==  \* GET /pending: one transaction (rows + current), :507-511, :810-829
    /\ rc[t].ph \in {"idle", "reread"}
    /\ LET rnd == IF rc[t].ph = "idle" THEN 1 ELSE rc[t].round + 1
       IN  IF MutNonAtomicSnapshot
           THEN \/ rc' = [rc EXCEPT ![t] = [rc[t] EXCEPT !.ph = "needcur", !.rows = RowsOf(t),
                                            !.cur = {}, !.done = {}, !.round = rnd]]
                \/ rc' = [rc EXCEPT ![t] = [rc[t] EXCEPT !.ph = "needrows", !.rows = {},
                                            !.cur = CurOf, !.done = {}, !.round = rnd]]
           ELSE rc' = [rc EXCEPT ![t] = [rc[t] EXCEPT
                         !.ph = (IF RowsOf(t) = {} THEN "repair" ELSE "apply"),
                         !.rows = RowsOf(t), !.cur = CurOf, !.done = {}, !.round = rnd]]
    /\ UNCHANGED <<outbox, sstate, sorigin, lastApplied>>
    /\ RunUnch
    /\ Note("Read", t, NoFact, "none", 0)

ReconcileReadSecond(t) ==   \* only with MutNonAtomicSnapshot: the second half of the read
    /\ MutNonAtomicSnapshot
    /\ rc[t].ph \in {"needcur", "needrows"}
    /\ LET rows2 == IF rc[t].ph = "needrows" THEN RowsOf(t) ELSE rc[t].rows
           cur2  == IF rc[t].ph = "needcur" THEN CurOf ELSE rc[t].cur
       IN  rc' = [rc EXCEPT ![t] = [rc[t] EXCEPT !.rows = rows2, !.cur = cur2,
                                    !.ph = (IF rows2 = {} THEN "repair" ELSE "apply")]]
    /\ UNCHANGED <<outbox, sstate, sorigin, lastApplied>>
    /\ RunUnch
    /\ Note("ReadSecond", t, NoFact, "none", 0)

ReconcileApply(t) == \* :520-528, one item per step in any order
    /\ rc[t].ph = "apply"
    /\ \E i \in rc[t].rows :
         /\ ApplyEffect(t, i.f, i.seq, i.ev)
         /\ rc' = [rc EXCEPT ![t] = [rc[t] EXCEPT
                     !.rows = @ \ {i},
                     !.done = @ \cup {[f |-> i.f, seq |-> i.seq]},
                     !.ph   = (IF rc[t].rows \ {i} = {} THEN "ack" ELSE "apply")]]
         /\ Note("Apply", t, i.f, i.ev, i.seq)
    /\ UNCHANGED outbox
    /\ RunUnch

ReconcileAck(t) ==   \* ack_pending :831-846; per pair (seq<=) or delete-all
    /\ rc[t].ph = "ack"
    /\ outbox' = [outbox EXCEPT ![t] = [f \in Facts |->
                    IF AckPerPair
                    THEN (IF \E p \in rc[t].done : p.f = f /\ outbox[t][f].seq <= p.seq
                          THEN NoRow ELSE outbox[t][f])
                    ELSE NoRow]]
    /\ rc' = [rc EXCEPT ![t] = [rc[t] EXCEPT !.done = {},
                 !.ph = (IF ReRead /\ rc[t].round < MaxRounds THEN "reread" ELSE "repair")]]
    /\ UNCHANGED <<sstate, sorigin, lastApplied>>
    /\ RunUnch
    /\ Note("Ack", t, NoFact, "none", 0)

RepairStart(t) ==    \* applied_seqs read once, :528-531
    /\ rc[t].ph = "repair"
    /\ rc' = [rc EXCEPT ![t] = [rc[t] EXCEPT !.ph = "repairing",
                 !.aseq = [f \in Facts |-> IF sstate[t][f] = "Absent" THEN NoRec
                                           ELSE lastApplied[t][f]]]]
    /\ UNCHANGED <<outbox, sstate, sorigin, lastApplied>>
    /\ RunUnch
    /\ Note("RepairStart", t, NoFact, "none", 0)

AntiEntropyStep(t) == \* _repair_from_snapshot :463-480, one item per step, no ack
    /\ rc[t].ph = "repairing"
    /\ \E i \in rc[t].cur :
         /\ i.seq > rc[t].aseq[i.f]
         /\ ApplyEffect(t, i.f, i.seq, i.ev)
         /\ rc' = [rc EXCEPT ![t] = [rc[t] EXCEPT !.cur = @ \ {i}]]
         /\ Note("AntiEntropy", t, i.f, i.ev, i.seq)
    /\ UNCHANGED outbox
    /\ RunUnch

RepairFinish(t) ==
    /\ rc[t].ph = "repairing"
    /\ \A i \in rc[t].cur : i.seq <= rc[t].aseq[i.f]
    /\ rc' = [rc EXCEPT ![t] = IdleRc]
    /\ UNCHANGED <<outbox, sstate, sorigin, lastApplied>>
    /\ RunUnch
    /\ Note("Finish", t, NoFact, "none", 0)

RcStep(t) ==
    \/ ReconcileRead(t) \/ ReconcileReadSecond(t) \/ ReconcileApply(t) \/ ReconcileAck(t)
    \/ RepairStart(t) \/ AntiEntropyStep(t) \/ RepairFinish(t)

Next ==
    \/ \E s \in Sites, f \in Facts :
          \/ Dispute(s, f) \/ Query(s, f) \/ OperatorCommit(s, f)
          \/ LocalRevoke(s, f) \/ LocalRestore(s, f)
    \/ \E f \in Facts : Restore(f)
    \/ \E r \in todo : Deliver(r) \/ Lose(r)
    \/ \E t \in Sites : RcStep(t) \/ SiteDown(t) \/ SiteUp(t)

Spec == Init /\ [][Next]_vars

\* Conditional fairness: a site's run steps only while it is not unreachable; every
\* in-flight delivery is eventually attempted. Needed only for liveness (SpecL).
Fairness ==
    /\ \A t \in Sites : WF_vars(RcStep(t) /\ t \notin unreachable)
    /\ \A r \in TodoRecs : WF_vars(Deliver(r))

SpecL == Spec /\ Fairness

(***************************************************************************)
(* SAFETY: state invariants (INVARIANT in the cfg).                        *)
(***************************************************************************)
NoInFlight(t, f) ==
    /\ \A r \in todo : ~(r.site = t /\ r.fact = f)
    /\ outbox[t][f].seq = 0

\* The explicit-window form of DisputeSuspendsAtReachableSites (Dist.tla:305): a reachable
\* site with nothing in flight for the fact must not be enforcing it while the evidence is
\* disputed/revoked. HOLDS only if no event can be lost (MaxLoss = 0) and the ack is per pair;
\* with a lost event (D19) the window lasts until the next repair: see ExposureEnds.
DisputeSuspendsAtReachableSites ==
    \A t \in Sites \ unreachable, f \in Facts :
        (estatus[f] # "Active" /\ NoInFlight(t, f)) =>
            sstate[t][f] \in {"Absent", "Disputed", "Revoked"}

\* Safety form of the window: exposure is possible only while the site lags the evidence.
CaughtUpIsCoherent ==
    \A t \in Sites, f \in Facts :
        (sstate[t][f] # "Absent" /\ lastApplied[t][f] = eseq[f]) =>
            (estatus[f] = "Active" \/ sstate[t][f] \in {"Disputed", "Revoked"})

\* Diagnostic for V0/V1 only: a lagging site has an event queued or in flight for it.
\* Tautological with AntiEntropy (the repair covers the lag), so NOT required of V2/V3.
LagCoveredByQueue ==
    \A t \in Sites, f \in Facts :
        (sstate[t][f] # "Absent" /\ lastApplied[t][f] < eseq[f]) =>
            \/ \E r \in todo : r.site = t /\ r.fact = f /\ r.seq > lastApplied[t][f]
            \/ outbox[t][f].seq > lastApplied[t][f]

\* D6/B3: an Active site that is fully caught up has committed in the CURRENT episode, i.e.
\* a site that stayed Active through a whole dispute+restore episode ends in monitor-only.
NoStaleActiveAfterEpisode ==
    \A t \in Sites, f \in Facts :
        (sstate[t][f] = "Active" /\ lastApplied[t][f] = eseq[f]) => commitGen[t][f] = gen[f]

(***************************************************************************)
(* SAFETY: action properties (PROPERTY in the cfg).                        *)
(***************************************************************************)
I1_NonEscalation ==
    [][ \A s \in Sites, f \in Facts :
            (sstate[s][f] # "Active" /\ sstate'[s][f] = "Active") =>
                /\ lastOp'.op = "Commit"
                /\ lastOp'.site = s
                /\ sstate[s][f] = "MonitorOnly" ]_vars

I2_SiteConfinement ==
    [][ (lastOp'.op = "Commit") =>
            \A t \in Sites \ {lastOp'.site}, g \in Facts : sstate'[t][g] = sstate[t][g] ]_vars

I2_ApplyConfinement ==
    [][ (lastOp'.op \in ApplyOps) =>
            \A t \in Sites, g \in Facts :
                (t # lastOp'.site \/ g # lastOp'.fact) =>
                    /\ sstate'[t][g] = sstate[t][g]
                    /\ sorigin'[t][g] = sorigin[t][g]
                    /\ lastApplied'[t][g] = lastApplied[t][g] ]_vars

\* Corrected after the first s0_smoke run (audit 07): a restore that the site DISCARDS (seq <=
\* last_applied_seq, a no-op, service.py:365-366) cannot be constrained: a late duplicate
\* delivery must not (and does not) change a site that has since committed. The property
\* concerns a restore that is APPLIED (seq > last_applied before the step). Original text, kept
\* for the record: antecedent `lastOp'.op \in ApplyOps /\ lastOp'.ev = "restore"` only.
\* Non-vacuity: MutWriteActive must violate this corrected form (cfg mut_ae2_i3).
I3_ConservativeRestore ==
    [][ (lastOp'.op \in ApplyOps /\ lastOp'.ev = "restore"
         /\ lastOp'.seq > lastApplied[lastOp'.site][lastOp'.fact]) =>
            sstate'[lastOp'.site][lastOp'.fact] # "Active" ]_vars

I3_VetoPreserved ==
    [][ \A t \in Sites, g \in Facts :
            (sstate[t][g] = "Revoked" /\ sorigin[t][g] = "Local" /\ lastOp'.op # "LocalRestore") =>
                (sstate'[t][g] = "Revoked" /\ sorigin'[t][g] = "Local") ]_vars

UnrelatedFactIsolation ==
    [][ (lastOp'.op \in ApplyOps \cup {"Query", "Commit", "LocalRevoke", "LocalRestore"}) =>
            \A t \in Sites, g \in Facts \ {lastOp'.fact} : sstate'[t][g] = sstate[t][g] ]_vars

LastAppliedMonotone ==
    [][ \A t \in Sites, f \in Facts : lastApplied'[t][f] >= lastApplied[t][f] ]_vars

\* A stale event (seq <= last_applied) never changes a site's state or origin.
NoRegression ==
    [][ (lastOp'.op \in ApplyOps /\ lastOp'.seq <= lastApplied[lastOp'.site][lastOp'.fact]) =>
            /\ sstate'[lastOp'.site][lastOp'.fact]  = sstate[lastOp'.site][lastOp'.fact]
            /\ sorigin'[lastOp'.site][lastOp'.fact] = sorigin[lastOp'.site][lastOp'.fact] ]_vars

\* D12: the ack never deletes a row the site has not applied (seq greater than the applied
\* one, or a row of another fact). A row of a site with no local record is acked as a no-op.
OutboxNeverDropsUnapplied ==
    [][ (lastOp'.op = "Ack") =>
            \A t \in Sites, f \in Facts :
                (outbox[t][f].seq > 0 /\ outbox'[t][f].seq = 0) =>
                    (sstate[t][f] = "Absent" \/ outbox[t][f].seq <= lastApplied[t][f]) ]_vars

(***************************************************************************)
(* LIVENESS (needs SpecL; bounds are in the guards).                       *)
(***************************************************************************)
Converged ==
    \A t \in Sites \ unreachable, f \in Facts :
        sstate[t][f] = "Absent" \/ lastApplied[t][f] = eseq[f]

ConvergedEventually == <>[] Converged

Exposed(t, f) == sstate[t][f] = "Active" /\ estatus[f] # "Active"

\* An exposed site that is eventually reachable for good stops being exposed.
ExposureEnds ==
    \A t \in Sites, f \in Facts :
        (<>[](t \notin unreachable)) => (Exposed(t, f) ~> ~Exposed(t, f))

=============================================================================
