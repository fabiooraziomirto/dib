---- MODULE AuthZ ----
\* Modello PICCOLO e separato dell'autorizzazione mTLS del prototipo distribuito (audit 111).
\* NON e' il modello del ciclo di vita (v6/v7/v8). Regole di autorizzazione: Rules.tla, generato
\* dal codice (gen_rules.py). Qui: identita', denylist con copie per servizio, chiamate astratte.
EXTENDS Naturals, Sequences, FiniteSets, Rules

CONSTANTS MaxRevokes,   \* quante revoche (SAN aggiunti alla denylist) al massimo
          MaxSans,      \* SAN per certificato (design 3.1: 1)
          AtomicReload, \* TRUE: la revoca arriva a tutti i servizi subito (file condiviso)
          MutNoDeny, MutNoOwnSite, MutMemberRestore, MutPayloadSite, MutFanoutAny, MutOpenSeed

Sites   == {"s1", "s2", "s3"}
NoSite  == "none"
Ev      == "E"
Svcs    == Sites \cup {Ev}
\* identita' mappate (identities.json) e un SAN valido per la CA ma NON mappato ("gh")
Map == [m1 |-> [role |-> "member",   site |-> "s1"], m2 |-> [role |-> "member",   site |-> "s2"],
        m3 |-> [role |-> "member",   site |-> "s3"], o1 |-> [role |-> "operator", site |-> "s1"],
        o2 |-> [role |-> "operator", site |-> "s2"], o3 |-> [role |-> "operator", site |-> "s3"],
        ev |-> [role |-> "evidence", site |-> NoSite], ad |-> [role |-> "admin", site |-> NoSite]]
SANs  == DOMAIN Map \cup {"gh"}
Certs == UNION {[1..n -> SANs] : n \in 1..MaxSans}

NullE    == [san |-> "-", role |-> "-", site |-> NoSite]
Mapped(e) == e.role # "-"

\* --- mutanti (non vacuita') applicati alla regola del CODICE
RolesOf(ep, r) ==
  IF MutMemberRestore /\ ep = "evidence.restore" THEN r.roles \cup {"member"}
  ELSE IF MutFanoutAny /\ ep = "site.apply_fanout" THEN {"member", "operator", "evidence", "admin"}
  ELSE r.roles

RECURSIVE ResolveFrom(_, _, _)
\* Identities.resolve (mtls.py:134-143): primo SAN mappato; se un SAN incontrato prima e' in denylist -> None
ResolveFrom(cert, i, den) ==
  IF i > Len(cert) THEN NullE
  ELSE IF cert[i] \in den /\ ~MutNoDeny THEN NullE
  ELSE IF cert[i] \in DOMAIN Map
       THEN [san |-> cert[i], role |-> Map[cert[i]].role, site |-> Map[cert[i]].site]
       ELSE ResolveFrom(cert, i + 1, den)

\* _authorize (service.py:177-186) + controllo del payload di _reporter (service.py:866-868)
Decide(ep, r, tgt, arg, e, mut) ==
  LET roles == IF mut THEN RolesOf(ep, r) ELSE r.roles
      site  == IF r.siteArg = "self" THEN tgt ELSE IF r.siteArg = "path" THEN arg ELSE NoSite
      roleOk == e.role \in roles \/ (e.role \in r.siteRoles /\ ((mut /\ MutNoOwnSite) \/ e.site = site))
      payOk  == ~r.reporter \/ (mut /\ MutPayloadSite) \/ arg = NoSite \/ arg = e.site
  IN (mut /\ MutOpenSeed /\ ep = "evidence.seed") \/ (Mapped(e) /\ roleOk /\ payOk)

\* tabella del DESIGN (13_mtls_design.md sez. 3.3 con la decisione Q1 di sez. 9: operatore separato)
OpEps == {"site.query_score", "site.operator_commit", "site.local_revoke", "site.local_restore",
          "site.reconcile", "site.export_mud"}
DesignRules ==
  [ep \in Eps |->
    IF ep \in OpEps THEN [svc |-> "site", roles |-> {}, siteRoles |-> {"operator"}, siteArg |-> "self", reporter |-> FALSE]
    ELSE IF ep = "site.apply_fanout" THEN [svc |-> "site", roles |-> {"evidence"}, siteRoles |-> {}, siteArg |-> "none", reporter |-> FALSE]
    ELSE IF ep \in {"site.get_state", "site.health"} THEN [svc |-> "site", roles |-> {"admin"}, siteRoles |-> {"operator"}, siteArg |-> "self", reporter |-> FALSE]
    ELSE IF ep \in {"evidence.seed", "evidence.restore"} THEN [svc |-> "evidence", roles |-> {"admin"}, siteRoles |-> {}, siteArg |-> "none", reporter |-> FALSE]
    ELSE IF ep \in {"evidence.get_score", "evidence.get_score_by_id"} THEN [svc |-> "evidence", roles |-> {"member", "admin"}, siteRoles |-> {}, siteArg |-> "none", reporter |-> FALSE]
    ELSE IF ep \in {"evidence.attest", "evidence.dispute"} THEN [svc |-> "evidence", roles |-> {"member"}, siteRoles |-> {}, siteArg |-> "none", reporter |-> TRUE]
    ELSE IF ep \in {"evidence.get_pending", "evidence.ack_pending"} THEN [svc |-> "evidence", roles |-> {}, siteRoles |-> {"member"}, siteArg |-> "path", reporter |-> FALSE]
    ELSE [svc |-> "evidence", roles |-> {"member", "operator", "evidence", "admin"}, siteRoles |-> {}, siteArg |-> "none", reporter |-> FALSE]]  \* evidence.health

TargetsOf(ep) == IF CodeRules[ep].svc = "site" THEN Sites ELSE {Ev}
ArgsOf(ep) == IF CodeRules[ep].siteArg = "path" THEN Sites
              ELSE IF CodeRules[ep].reporter THEN Sites \cup {NoSite} ELSE {NoSite}

VARIABLES master, loc, revokes, last
vars == <<master, loc, revokes, last>>

Idle == [cert |-> <<"gh">>, ep |-> "none", tgt |-> "none", arg |-> NoSite, ok |-> FALSE,
         ent |-> NullE, actor |-> NoSite, den |-> {}, mst |-> {}, dok |-> FALSE]

Init == /\ master = {} /\ loc = [x \in Svcs |-> {}] /\ revokes = 0 /\ last = Idle

Revoke(s) == /\ revokes < MaxRevokes /\ s \in DOMAIN Map /\ s \notin master
             /\ master' = master \cup {s}
             /\ loc' = IF AtomicReload THEN [x \in Svcs |-> master \cup {s}] ELSE loc
             /\ revokes' = revokes + 1 /\ last' = Idle

\* il servizio rilegge il file delle identita' (mtime cambiato)
Reload(x) == /\ ~AtomicReload /\ loc[x] # master
             /\ loc' = [loc EXCEPT ![x] = master] /\ UNCHANGED <<master, revokes>> /\ last' = Idle

\* "il chiamante con certificato c invoca l'endpoint ep sul servizio tgt con argomento arg"
Call(c, ep, tgt, arg) ==
  LET den == loc[tgt]
      e   == ResolveFrom(c, 1, den)
      ok  == Decide(ep, CodeRules[ep], tgt, arg, e, TRUE)
  IN /\ UNCHANGED <<master, loc, revokes>>
     /\ last' = [cert |-> c, ep |-> ep, tgt |-> tgt, arg |-> arg, ok |-> ok, ent |-> e,
                 actor |-> IF CodeRules[ep].reporter /\ MutPayloadSite /\ arg # NoSite THEN arg ELSE e.site,
                 den |-> den, mst |-> master,
                 dok |-> Decide(ep, DesignRules[ep], tgt, arg, ResolveFrom(c, 1, den), FALSE)]

Next == \/ \E s \in SANs : Revoke(s)
        \/ \E x \in Svcs : Reload(x)
        \/ \E c \in Certs : \E ep \in Eps : \E t \in TargetsOf(ep) : \E a \in ArgsOf(ep) : Call(c, ep, t, a)
Spec == Init /\ [][Next]_vars

TypeOK == /\ master \subseteq DOMAIN Map /\ revokes <= MaxRevokes
          /\ \A x \in Svcs : loc[x] \subseteq master
          /\ last.ok \in BOOLEAN

\* ---- proprieta' (scritte dal design, non dalla tabella del codice)
P1_Local     == last.ok => last.ent.san \notin last.den       \* identita' risolta non e' nella denylist DEL SERVIZIO
P1_Global    == last.ok => last.ent.san \notin last.mst       \* ... ne' in quella centrale (revoca immediata)
P1_Presented == last.ok => \A i \in DOMAIN last.cert : last.cert[i] \notin last.den  \* nessun SAN presentato e' revocato
P2_Confine   == (last.ok /\ last.ep \in OpEps) => (last.ent.role = "operator" /\ last.ent.site = last.tgt)
P3_Fanout    == (last.ok /\ last.ep = "site.apply_fanout") => last.ent.role = "evidence"
P4_Admin     == (last.ok /\ last.ep \in {"evidence.restore", "evidence.seed"}) => last.ent.role = "admin"
P5_Dispute   == (last.ok /\ last.ep \in {"evidence.attest", "evidence.dispute"})
                  => (last.actor = last.ent.site /\ (last.arg = NoSite \/ last.arg = last.ent.site))
P5b_Pending  == (last.ok /\ last.ep \in {"evidence.get_pending", "evidence.ack_pending"})
                  => (last.ent.role = "member" /\ last.ent.site = last.arg)
P6_Identity  == last.ok => Mapped(last.ent)
PD_DesignCover == last.ok => last.dok    \* il codice non ammette piu' di quanto dice il design
====
