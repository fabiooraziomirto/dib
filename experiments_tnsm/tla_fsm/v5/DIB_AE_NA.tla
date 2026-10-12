------------------------------ MODULE DIB_AE_NA ------------------------------
(***************************************************************************)
(* DIB_AE_NA = DIB_AE (formal/distributed_ae/DIB_AE.tla, copied unchanged *)
(* except where marked [NA]) extended for docs/audit/67:                  *)
(*  E2 [NA] for sites in SplitSites, Query, OperatorCommit and            *)
(*     LocalRestore are NOT atomic, as in service.py at 6e6d352:          *)
(*     an HTTP read of the evidence (S:500, S:522, S:560-564) and later a *)
(*     separate local transaction (S:505-514, S:527-530, S:567-573).      *)
(*     Evidence events and deliveries can interleave between the two.     *)
(*  FixRace [NA] the candidate correction (audit 64 sez. 3, audit 67):    *)
(*     the write refuses if last_applied_seq > the seq read (an event     *)
(*     newer than the read was applied), and a commit is two-phase:       *)
(*     write 'Committing' (not exportable), re-read the evidence, promote *)
(*     to Active only if the seq is unchanged and the status is Active.   *)
(*  E5 [NA] Quorum = 2: a first report is only a vote (suspension_reports,*)
(*     S:908-911); ConfirmOutsideVoters selects the confirmer rule:       *)
(*     FALSE = code (r # disputed_by, S:918), TRUE = user decision of     *)
(*     2026-10-12 (r not among the voters).                               *)
(*  v2 (audit 67 batch 2) FixQuery: a split Query first RESERVES a local  *)
(*     'Staging' row (not exportable, not a decision), then reads the      *)
(*     evidence, then finishes: Staging -> MonitorOnly if the read saw     *)
(*     Active, else back to Absent. A fan-out that arrives after the       *)
(*     reservation finds the row and applies (ApplyResult), closing b3q.   *)
(*     Mutation flags MutNoLRGuard / MutNoVerify remove one piece of the   *)
(*     correction each (non-vacuity of every piece).                       *)
(*  v3 (audit 67 batch 3): I3_VetoPreserved exempts LRWrite, the split    *)
(*     form of LocalRestore (v1/v2 exempted only the atomic LocalRestore:  *)
(*     a modelling error that made n5, f2, f3 of batch 2 fail on the       *)
(*     site's own legitimate local restore). Nothing else changes.         *)
(*  v4 (audit 67 batch 4): OutboxNeverDropsUnapplied treats Staging like  *)
(*     Absent (see the comment at the property). Nothing else changes.     *)
(*  v5 (audit 67 batch 5): QueryReserve requires the site's reconcile run *)
(*     to be idle (the code takes _reconcile_lock around the reservation), *)
(*     so a reservation cannot fall between a no-op apply and its ack.     *)
(* Ghost dirty[s]: an evidence event on op[s].f happened between the      *)
(* first read of a pending operation of s and its linearization point.    *)
(***************************************************************************)
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
(*  0. Reporters are abstract identifiers separate from the sites (as in the tests,  *)
(*     rep-a/rep-b). With 2 sites and 2 reporters the D12 scenario with a lagging   *)
(*     site that is NOT a reporter is covered; the case with 3 REAL sites is not,   *)
(*     except by the robustness cfgs v0_3sites/v1_3sites.                           *)
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
    Reporters,           \* abstract reporter identities (req.site_id, :747-751), NOT the sites
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
    MutRestoreKeepsActive,  \* a restore does not touch an Active site (old Reconcile)
    \* [NA]
    SplitSites,             \* sites whose Query/Commit/LocalRestore are read-then-write
    FixRace,                \* candidate correction of the read-then-write windows
    Quorum,                 \* 1 or 2 (DIB_DIST_SUSPENSION_QUORUM)
    ConfirmOutsideVoters,   \* Quorum 2 confirmer rule (see header)
    FixQuery,               \* v2: reserve-then-read Query on split sites
    MutNoLRGuard,           \* v2 mutation: FixRace without the last_applied guard of LRWrite
    MutNoVerify             \* v2 mutation: FixRace commit without the second read (guard only)

VARIABLES
    estatus, eseq, edisp,      \* evidence: status, fanout_seq, disputed_by per fact
    outbox,                    \* outbox[t][f]: pending_fanout row of (site t, fact f) or NoRow
    todo,                      \* in-flight direct deliveries (the D19 window and the concurrency)
    sstate, sorigin, lastApplied,  \* site t, fact f: state, origin, last_applied_seq
    rc,                        \* rc[t]: the single reconcile run machine of site t
    unreachable, toggleCount,
    gen, commitGen,            \* ghost: dispute episodes per fact; episode of the last Commit
    evCount, lossCount,        \* ghost: bound counters
    lastOp,
    op, votes, dirty           \* [NA] pending split operation per site; quorum votes; ghost

vars == <<estatus, eseq, edisp, outbox, todo, sstate, sorigin, lastApplied, rc,
          unreachable, toggleCount, gen, commitGen, evCount, lossCount, lastOp,
          op, votes, dirty>>

ExtraUnch == UNCHANGED <<op, votes, dirty>>   \* [NA]

States    == {"Absent", "MonitorOnly", "Active", "Disputed", "Revoked", "Committing", "Staging"}  \* [NA] Committing, v2 Staging
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
              "Finish", "SiteDown", "SiteUp",
              "QueryRead", "QueryWrite", "CommitRead", "CommitWrite", "VerifyRead", "Promote",
              "LRRead", "LRWrite", "Vote", "QueryReserve", "QueryFinish"}   \* [NA] + v2
OpKinds   == {"none", "query", "commit", "committing", "verified", "lrestore", "qreserved", "qread"}
NoOp      == [k |-> "none", f |-> NoFact, sq |-> 0, sq2 |-> 0, st2 |-> "none", g |-> 0]
OpT       == {NoOp} \cup [k: OpKinds \ {"none"}, f: Facts, sq: 0..MaxEvents, sq2: 0..MaxEvents,
                          st2: EStatuses \cup {"none"}, g: 0..MaxEvents]
ApplyOps  == {"Deliver", "Apply", "AntiEntropy"}
LocalOps  == {"Query", "Commit", "LocalRevoke", "LocalRestore", "QueryRead", "QueryWrite",
              "CommitRead", "CommitWrite", "VerifyRead", "Promote", "LRRead", "LRWrite",
              "QueryReserve", "QueryFinish"}   \* [NA] + v2
OpRecord  == [op: Ops, site: Sites \cup Reporters \cup {NoSite}, fact: Facts \cup {NoFact},
              ev: Evs \cup {"none"}, seq: 0..MaxEvents]

TypeOK ==
    /\ estatus     \in [Facts -> EStatuses]
    /\ eseq        \in [Facts -> 0..MaxEvents]
    /\ edisp       \in [Facts -> Reporters \cup {NoSite}]
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
    /\ op          \in [Sites -> OpT]
    /\ votes       \in [Facts -> SUBSET Reporters]
    /\ dirty       \in [Sites -> BOOLEAN]

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
    /\ op          = [t \in Sites |-> NoOp]
    /\ votes       = [f \in Facts |-> {}]
    /\ dirty       = [t \in Sites |-> FALSE]

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
EvCommit(f, st, e, newDisp, newGen, opn, who) ==   \* [NA] parameter op -> opn (op is a variable)
    /\ evCount < MaxEvents
    /\ estatus' = [estatus EXCEPT ![f] = st]
    /\ eseq'    = [eseq EXCEPT ![f] = @ + 1]
    /\ edisp'   = [edisp EXCEPT ![f] = newDisp]
    /\ gen'     = [gen EXCEPT ![f] = newGen]
    /\ todo'    = todo \cup {[site |-> t, fact |-> f, seq |-> eseq[f] + 1, ev |-> e] : t \in Sites}
    /\ evCount' = evCount + 1
    /\ UNCHANGED <<outbox, sstate, sorigin, lastApplied, rc, unreachable, toggleCount,
                   commitGen, lossCount, op>>
    \* [NA] ghost: an event on op[t].f before the linearization point of t's pending operation
    /\ dirty'   = [t \in Sites |-> dirty[t] \/ (op[t].k \in {"query", "commit", "committing", "lrestore"}
                                                /\ op[t].f = f)]
    /\ Note(opn, who, f, e, eseq[f] + 1)

\* [NA] quorum. Quorum 1: as DIB_AE (votes stay {}). Quorum 2: S:905-917; the vote INSERT and
\* the status change are one transaction. The confirming reporter is recorded in lastOp.site.
Vote(r, f) ==
    /\ Quorum = 2 /\ estatus[f] = "Active"
    /\ r \notin votes[f] /\ Cardinality(votes[f] \cup {r}) < 2
    /\ votes' = [votes EXCEPT ![f] = @ \cup {r}]
    /\ UNCHANGED <<estatus, eseq, edisp, outbox, todo, sstate, sorigin, lastApplied, rc,
                   unreachable, toggleCount, gen, commitGen, evCount, lossCount, op, dirty>>
    /\ Note("Vote", r, f, "none", 0)

Confirms(r, f) == IF Quorum = 2 /\ ConfirmOutsideVoters THEN r \notin votes[f] ELSE r # edisp[f]

Dispute(r, f) ==     \* dispute route :747-779 (quorum 1); r is an abstract reporter id, not a site
    \/ /\ estatus[f] = "Active"
       /\ (Quorum = 1 \/ Cardinality(votes[f] \cup {r}) >= 2)
       /\ votes' = [votes EXCEPT ![f] = IF Quorum = 2 THEN @ \cup {r} ELSE @]
       /\ EvCommit(f, "Disputed", "dispute", r, gen[f] + 1, "EvDispute", NoSite)
    \/ /\ estatus[f] = "Disputed" /\ Confirms(r, f)
       /\ UNCHANGED votes
       /\ EvCommit(f, "Revoked", "revoke", edisp[f], gen[f], "EvRevoke", r)

Restore(f) ==        \* restore route :781-801
    /\ estatus[f] \in {"Disputed", "Revoked"}
    /\ votes' = [votes EXCEPT ![f] = {}]   \* [NA] S:944
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
    /\ ExtraUnch

Lose(r) ==           \* D19: the in-flight delivery vanishes, nothing queued
    /\ lossCount < MaxLoss
    /\ r \in todo
    /\ todo' = todo \ {r}
    /\ lossCount' = lossCount + 1
    /\ UNCHANGED <<estatus, eseq, edisp, outbox, sstate, sorigin, lastApplied, rc,
                   unreachable, toggleCount, gen, commitGen, evCount>>
    /\ ExtraUnch
    /\ Note("Lose", r.site, r.fact, r.ev, r.seq)

(***************************************************************************)
(* Site-local operations, aligned to the code (not to the old model).      *)
(***************************************************************************)
Query(s, f) ==       \* :381-400, stages with last_applied_seq = fanout_seq
    /\ s \notin SplitSites   \* [NA]
    /\ sstate[s][f] = "Absent"
    /\ estatus[f] = "Active"
    /\ sstate'      = [sstate EXCEPT ![s][f] = "MonitorOnly"]
    /\ sorigin'     = [sorigin EXCEPT ![s][f] = "None"]
    /\ lastApplied' = [lastApplied EXCEPT ![s][f] = eseq[f]]
    /\ UNCHANGED <<estatus, eseq, edisp, outbox, todo, rc, unreachable, toggleCount,
                   gen, commitGen, evCount, lossCount>>
    /\ ExtraUnch
    /\ Note("Query", s, f, "none", 0)

OperatorCommit(s, f) ==   \* :402-415 (global evidence Active AND local monitor-only)
    /\ AllowCommit
    /\ s \notin SplitSites   \* [NA]
    /\ sstate[s][f] = "MonitorOnly"
    /\ estatus[f] = "Active"
    /\ sstate'    = [sstate EXCEPT ![s][f] = "Active"]
    /\ commitGen' = [commitGen EXCEPT ![s][f] = gen[f]]
    /\ UNCHANGED <<estatus, eseq, edisp, outbox, todo, sorigin, lastApplied, rc,
                   unreachable, toggleCount, gen, evCount, lossCount>>
    /\ ExtraUnch
    /\ Note("Commit", s, f, "none", 0)

LocalRevoke(s, f) ==      \* :417-436
    /\ \/ sstate[s][f] \in {"MonitorOnly", "Active", "Disputed", "Committing"}  \* [NA] Committing
       \/ (sstate[s][f] = "Revoked" /\ sorigin[s][f] = "Fanout")
    /\ sstate'  = [sstate EXCEPT ![s][f] = "Revoked"]
    /\ sorigin' = [sorigin EXCEPT ![s][f] = "Local"]
    /\ UNCHANGED <<estatus, eseq, edisp, outbox, todo, lastApplied, rc, unreachable,
                   toggleCount, gen, commitGen, evCount, lossCount>>
    /\ ExtraUnch
    /\ Note("LocalRevoke", s, f, "none", 0)

LocalRestore(s, f) ==     \* :438-456 (refused while an episode is open)
    /\ s \notin SplitSites   \* [NA]
    /\ sstate[s][f] = "Revoked" /\ sorigin[s][f] = "Local"
    /\ estatus[f] = "Active"
    /\ sstate'  = [sstate EXCEPT ![s][f] = "MonitorOnly"]
    /\ sorigin' = [sorigin EXCEPT ![s][f] = "None"]
    /\ UNCHANGED <<estatus, eseq, edisp, outbox, todo, lastApplied, rc, unreachable,
                   toggleCount, gen, commitGen, evCount, lossCount>>
    /\ ExtraUnch
    /\ Note("LocalRestore", s, f, "none", 0)

(***************************************************************************)
(* [NA] Split operations of a site s \in SplitSites (service.py 6e6d352).  *)
(* Read = GET /scores (one atomic read of status and fanout_seq); Write =  *)
(* the later local transaction. One pending operation per site (an        *)
(* operator issues one request at a time; a bound, not a code property).  *)
(***************************************************************************)
SplitUnch == UNCHANGED <<estatus, eseq, edisp, outbox, todo, rc, unreachable, toggleCount,
                         gen, evCount, lossCount, votes>>
LocalUnch == UNCHANGED <<sstate, sorigin, lastApplied, commitGen>>

StartOp(s, k, f) ==
    /\ op' = [op EXCEPT ![s] = [k |-> k, f |-> f, sq |-> eseq[f], sq2 |-> 0, st2 |-> "none", g |-> gen[f]]]
    /\ dirty' = [dirty EXCEPT ![s] = FALSE]
EndOp(s) ==
    /\ op' = [op EXCEPT ![s] = NoOp]
    /\ dirty' = [dirty EXCEPT ![s] = FALSE]

QueryRead(s, f) ==      \* S:500-502: refused unless the evidence is Active
    /\ s \in SplitSites /\ op[s].k = "none" /\ ~FixQuery
    /\ sstate[s][f] = "Absent" /\ estatus[f] = "Active"
    /\ StartOp(s, "query", f)
    /\ LocalUnch /\ SplitUnch
    /\ Note("QueryRead", s, f, "none", 0)

QueryWrite(s) ==        \* S:505-514: insert monitor-only with the seq READ BEFORE (S:512)
    /\ op[s].k = "query"
    /\ LET f == op[s].f IN
       IF sstate[s][f] = "Absent"
       THEN /\ sstate'      = [sstate EXCEPT ![s][f] = "MonitorOnly"]
            /\ sorigin'     = [sorigin EXCEPT ![s][f] = "None"]
            /\ lastApplied' = [lastApplied EXCEPT ![s][f] = op[s].sq]
            /\ UNCHANGED commitGen
       ELSE LocalUnch
    /\ EndOp(s)
    /\ SplitUnch
    /\ Note("QueryWrite", s, op[s].f, "none", 0)

\* v2 FixQuery: reserve (local txn), read (GET /scores), finish (local txn).
QueryReserve(s, f) ==
    /\ s \in SplitSites /\ FixQuery /\ op[s].k = "none"
    /\ sstate[s][f] = "Absent"
    /\ rc[s].ph = "idle"   \* v5: the reservation takes the site's _reconcile_lock (no run in progress)
    /\ sstate' = [sstate EXCEPT ![s][f] = "Staging"]
    /\ op' = [op EXCEPT ![s] = [k |-> "qreserved", f |-> f, sq |-> 0, sq2 |-> 0, st2 |-> "none", g |-> 0]]
    /\ UNCHANGED <<sorigin, lastApplied, commitGen, dirty>>
    /\ SplitUnch
    /\ Note("QueryReserve", s, f, "none", 0)

QueryRead2(s) ==
    /\ op[s].k = "qreserved"
    /\ op' = [op EXCEPT ![s].k = "qread", ![s].sq = eseq[op[s].f], ![s].st2 = estatus[op[s].f]]
    /\ LocalUnch /\ SplitUnch /\ UNCHANGED dirty
    /\ Note("QueryRead", s, op[s].f, "none", 0)

QueryFinish(s) ==
    /\ op[s].k = "qread"
    /\ LET f == op[s].f IN
       IF sstate[s][f] = "Staging"
       THEN IF op[s].st2 = "Active"
            THEN /\ sstate' = [sstate EXCEPT ![s][f] = "MonitorOnly"]
                 /\ lastApplied' = [lastApplied EXCEPT ![s][f] = IF op[s].sq > @ THEN op[s].sq ELSE @]
                 /\ UNCHANGED <<sorigin, commitGen>>
            ELSE /\ sstate' = [sstate EXCEPT ![s][f] = "Absent"]
                 /\ UNCHANGED <<sorigin, lastApplied, commitGen>>
       ELSE LocalUnch   \* a fan-out already moved the reserved row: keep its state
    /\ EndOp(s)
    /\ SplitUnch
    /\ Note("QueryFinish", s, op[s].f, "none", 0)

CommitRead(s, f) ==     \* S:522-524
    /\ AllowCommit
    /\ s \in SplitSites /\ op[s].k = "none"
    /\ sstate[s][f] = "MonitorOnly" /\ estatus[f] = "Active"
    /\ StartOp(s, "commit", f)
    /\ LocalUnch /\ SplitUnch
    /\ Note("CommitRead", s, f, "none", 0)

CommitWrite(s) ==       \* S:527-530; FixRace: refuse if a newer event was applied, else Committing
    /\ op[s].k = "commit"
    /\ LET f  == op[s].f
           ok == sstate[s][f] = "MonitorOnly" /\ (~FixRace \/ lastApplied[s][f] <= op[s].sq)
       IN  IF ok
           THEN IF FixRace /\ ~MutNoVerify
                THEN /\ sstate' = [sstate EXCEPT ![s][f] = "Committing"]
                     /\ op' = [op EXCEPT ![s].k = "committing"]
                     /\ UNCHANGED <<sorigin, lastApplied, commitGen, dirty>>
                ELSE /\ sstate' = [sstate EXCEPT ![s][f] = "Active"]
                     /\ commitGen' = [commitGen EXCEPT ![s][f] = op[s].g]
                     /\ EndOp(s)
                     /\ UNCHANGED <<sorigin, lastApplied>>
           ELSE LocalUnch /\ EndOp(s)
    /\ SplitUnch
    /\ Note("CommitWrite", s, op[s].f, "none", 0)

VerifyRead(s) ==        \* FixRace: the second GET /scores after the local write
    /\ op[s].k = "committing"
    /\ op' = [op EXCEPT ![s].k = "verified", ![s].sq2 = eseq[op[s].f], ![s].st2 = estatus[op[s].f]]
    /\ LocalUnch /\ SplitUnch /\ UNCHANGED dirty
    /\ Note("VerifyRead", s, op[s].f, "none", 0)

Promote(s) ==           \* FixRace: Committing -> Active only on an unchanged Active evidence
    /\ op[s].k = "verified"
    /\ LET f == op[s].f IN
       IF sstate[s][f] = "Committing"
       THEN IF op[s].st2 = "Active" /\ op[s].sq2 = op[s].sq
            THEN /\ sstate' = [sstate EXCEPT ![s][f] = "Active"]
                 /\ commitGen' = [commitGen EXCEPT ![s][f] = op[s].g]
                 /\ UNCHANGED <<sorigin, lastApplied>>
            ELSE /\ sstate' = [sstate EXCEPT ![s][f] = "MonitorOnly"]   \* abort: back to review
                 /\ UNCHANGED <<sorigin, lastApplied, commitGen>>
       ELSE LocalUnch
    /\ EndOp(s)
    /\ SplitUnch
    /\ Note("Promote", s, op[s].f, "none", 0)

LRRead(s, f) ==         \* S:560-564: refused while the episode is open
    /\ s \in SplitSites /\ op[s].k = "none"
    /\ sstate[s][f] = "Revoked" /\ sorigin[s][f] = "Local" /\ estatus[f] = "Active"
    /\ StartOp(s, "lrestore", f)
    /\ LocalUnch /\ SplitUnch
    /\ Note("LRRead", s, f, "none", 0)

LRWrite(s) ==           \* S:567-573; FixRace: refuse if a newer event was applied
    /\ op[s].k = "lrestore"
    /\ LET f == op[s].f IN
       IF sstate[s][f] = "Revoked" /\ sorigin[s][f] = "Local"
          /\ (~FixRace \/ MutNoLRGuard \/ lastApplied[s][f] <= op[s].sq)
       THEN /\ sstate'  = [sstate EXCEPT ![s][f] = "MonitorOnly"]
            /\ sorigin' = [sorigin EXCEPT ![s][f] = "None"]
            /\ UNCHANGED <<lastApplied, commitGen>>
       ELSE LocalUnch
    /\ EndOp(s)
    /\ SplitUnch
    /\ Note("LRWrite", s, op[s].f, "none", 0)

SplitStep(s) ==
    \/ QueryWrite(s) \/ CommitWrite(s) \/ VerifyRead(s) \/ Promote(s) \/ LRWrite(s)
    \/ QueryRead2(s) \/ QueryFinish(s)
    \/ \E f \in Facts : QueryRead(s, f) \/ CommitRead(s, f) \/ LRRead(s, f) \/ QueryReserve(s, f)

SiteDown(s) ==
    /\ s \in PartitionableSites /\ s \notin unreachable /\ toggleCount < MaxToggles
    /\ unreachable' = unreachable \cup {s}
    /\ toggleCount' = toggleCount + 1
    /\ UNCHANGED <<estatus, eseq, edisp, outbox, todo, sstate, sorigin, lastApplied, rc,
                   gen, commitGen, evCount, lossCount>>
    /\ ExtraUnch
    /\ Note("SiteDown", s, NoFact, "none", 0)

SiteUp(s) ==
    /\ s \in unreachable /\ toggleCount < MaxToggles
    /\ unreachable' = unreachable \ {s}
    /\ toggleCount' = toggleCount + 1
    /\ UNCHANGED <<estatus, eseq, edisp, outbox, todo, sstate, sorigin, lastApplied, rc,
                   gen, commitGen, evCount, lossCount>>
    /\ ExtraUnch
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
                       commitGen, evCount, lossCount, op, votes, dirty>>   \* [NA] + op, votes, dirty

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
    \/ \E r \in Reporters, f \in Facts : Dispute(r, f) \/ Vote(r, f)
    \/ \E s \in SplitSites : SplitStep(s)   \* [NA]
    \/ \E s \in Sites, f \in Facts :
          \/ Query(s, f) \/ OperatorCommit(s, f)
          \/ LocalRevoke(s, f) \/ LocalRestore(s, f)
    \/ \E f \in Facts : Restore(f)
    \/ \E r \in todo : Deliver(r) \/ Lose(r)
    \/ \E t \in Sites : RcStep(t) \/ SiteDown(t) \/ SiteUp(t)

\* VIEW for SAFETY-ONLY runs (audit 07): every variable except lastOp. lastOp is bookkeeping for the
\* action properties: they read lastOp' (set by the action) and never the unprimed lastOp, and no
\* action is enabled as a function of lastOp, so two states differing only in lastOp have the same
\* successors and the same possible violations. NOT for liveness runs. A definition only: no action.
View == <<estatus, eseq, edisp, outbox, todo, sstate, sorigin, lastApplied, rc,
          unreachable, toggleCount, gen, commitGen, evCount, lossCount, op, votes, dirty>>

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
                /\ lastOp'.op \in {"Commit", "CommitWrite", "Promote"}   \* [NA] split commit
                /\ lastOp'.site = s
                /\ sstate[s][f] \in {"MonitorOnly", "Committing"} ]_vars

I2_SiteConfinement ==
    [][ (lastOp'.op \in LocalOps) =>   \* [NA] every local operation, split or not
            \A t \in Sites \ {lastOp'.site}, g \in Facts :
                /\ sstate'[t][g] = sstate[t][g]
                /\ sorigin'[t][g] = sorigin[t][g]
                /\ lastApplied'[t][g] = lastApplied[t][g] ]_vars

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
            (sstate[t][g] = "Revoked" /\ sorigin[t][g] = "Local"
             /\ lastOp'.op \notin {"LocalRestore", "LRWrite"}) =>   \* v3: the split local restore is the site's own restore
                (sstate'[t][g] = "Revoked" /\ sorigin'[t][g] = "Local") ]_vars

UnrelatedFactIsolation ==
    [][ (lastOp'.op \in ApplyOps \cup LocalOps) =>
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
                    (sstate[t][f] \in {"Absent", "Staging"} \/ outbox[t][f].seq <= lastApplied[t][f]) ]_vars
\* v4: Staging is treated as Absent. A Staging row at ack time implies the item was applied while the
\* row was Absent (a fan-out applied to a Staging row always moves it, since its last_applied is 0), and
\* the reservation precedes the second read, which sees the event: nothing is lost (audit 67 sez. 11).

(***************************************************************************)
(* [NA] New properties (docs/audit/67).                                    *)
(***************************************************************************)
\* Table row main_wip.tex:321 ("local commit ... no dispute"), as a linearizability statement: when a
\* record becomes Active, no evidence event on that fact happened between the commit's read and its
\* linearization point (the write without FixRace, the second read with FixRace).
I1_CommitOnUndisputedEvidence ==
    [][ \A s \in Sites, f \in Facts :
            (sstate[s][f] # "Active" /\ sstate'[s][f] = "Active") => ~dirty[s] ]_vars

\* Same for main_wip.tex:326 ("local restore ... no open dispute").
LocalRestoreOnClosedEpisode ==
    [][ (lastOp'.op \in {"LocalRestore", "LRWrite"}
         /\ sstate[lastOp'.site][lastOp'.fact] = "Revoked"
         /\ sstate'[lastOp'.site][lastOp'.fact] = "MonitorOnly") => ~dirty[lastOp'.site] ]_vars

\* main_wip.tex:320 ("query/stage ... no open dispute"), in the repairable form: a staged record never
\* claims to have seen a seq newer than the evidence state it was created from.
NoMonitorOnlyCaughtUpDuringEpisode ==
    \A t \in Sites, f \in Facts :
        (sstate[t][f] = "MonitorOnly" /\ lastApplied[t][f] = eseq[f]) => estatus[f] = "Active"

\* Committing is never exported and never survives a caught-up open episode.
CommittingIsTransient ==
    \A t \in Sites, f \in Facts :
        sstate[t][f] = "Committing" => (op[t].k \in {"committing", "verified"} /\ op[t].f = f)

\* a10 (user decision 2026-10-12): with Quorum 2 a revocation is confirmed by a reporter outside the
\* reporters whose votes opened the suspension.
RevokeConfirmedByOutsider ==
    [][ (lastOp'.op = "EvRevoke") => lastOp'.site \notin votes[lastOp'.fact] ]_vars

\* v2. Export safety proper: a reachable site with nothing in flight for f never holds f Active (hence
\* never exports it, Eq. exportable) while the evidence has f disputed or revoked. This is the
\* export half of DisputeSuspendsAtReachableSites; the other half (MonitorOnly) is about review state.
ExportSafeAtReachableSites ==
    \A t \in Sites \ unreachable, f \in Facts :
        (estatus[f] # "Active" /\ NoInFlight(t, f)) => sstate[t][f] # "Active"

\* v2. DisputeSuspendsAtReachableSites with the v2 placeholder: Staging is a reservation, not a
\* decision (not exportable, no operator action, resolved by QueryFinish), and is allowed like Absent
\* only while the site's own query is pending on f.
PendingQuery(t, f) == op[t].k \in {"qreserved", "qread"} /\ op[t].f = f
DisputeSuspendsAtReachableSitesV2 ==
    \A t \in Sites \ unreachable, f \in Facts :
        (estatus[f] # "Active" /\ NoInFlight(t, f)) =>
            \/ sstate[t][f] \in {"Absent", "Disputed", "Revoked"}
            \/ (sstate[t][f] = "Staging" /\ PendingQuery(t, f))

StagingIsTransient ==
    \A t \in Sites, f \in Facts : sstate[t][f] = "Staging" => PendingQuery(t, f)

NeverMonitorOnlyOnSplitSite == \A s \in SplitSites, f \in Facts : sstate[s][f] # "MonitorOnly"

\* Non-vacuity witness (EXPECTED to be violated where revocation is reachable).
NeverRevoked == \A f \in Facts : estatus[f] # "Revoked"
NeverActiveOnSplitSite == \A s \in SplitSites, f \in Facts : sstate[s][f] # "Active"

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
