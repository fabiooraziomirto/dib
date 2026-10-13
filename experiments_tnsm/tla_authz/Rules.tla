---- MODULE Rules ----
\* GENERATO da gen_rules.py da service.py sha256 0501b383043a44d4
\* Non modificare a mano. Campo line = riga della chiamata _authorize/_reporter in service.py.
EXTENDS Naturals
Eps == {"site.query_score", "site.operator_commit", "site.local_revoke", "site.local_restore", "site.apply_fanout", "site.reconcile", "site.export_mud", "site.get_state", "site.health", "evidence.seed", "evidence.get_score", "evidence.get_score_by_id", "evidence.attest", "evidence.dispute", "evidence.restore", "evidence.get_pending", "evidence.ack_pending", "evidence.health"}
CodeRules == [ep \in Eps |-> CASE
     ep = "site.query_score" -> [svc |-> "site", roles |-> {}, siteRoles |-> {"operator"}, siteArg |-> "self", reporter |-> FALSE, line |-> 499]  \* /query
  [] ep = "site.operator_commit" -> [svc |-> "site", roles |-> {}, siteRoles |-> {"operator"}, siteArg |-> "self", reporter |-> FALSE, line |-> 521]  \* /commit
  [] ep = "site.local_revoke" -> [svc |-> "site", roles |-> {}, siteRoles |-> {"operator"}, siteArg |-> "self", reporter |-> FALSE, line |-> 537]  \* /local_revoke
  [] ep = "site.local_restore" -> [svc |-> "site", roles |-> {}, siteRoles |-> {"operator"}, siteArg |-> "self", reporter |-> FALSE, line |-> 559]  \* /local_restore
  [] ep = "site.apply_fanout" -> [svc |-> "site", roles |-> {"evidence"}, siteRoles |-> {}, siteArg |-> "none", reporter |-> FALSE, line |-> 580]  \* /apply_fanout
  [] ep = "site.reconcile" -> [svc |-> "site", roles |-> {}, siteRoles |-> {"operator"}, siteArg |-> "self", reporter |-> FALSE, line |-> 667]  \* /reconcile
  [] ep = "site.export_mud" -> [svc |-> "site", roles |-> {}, siteRoles |-> {"operator"}, siteArg |-> "self", reporter |-> FALSE, line |-> 689]  \* /export_mud
  [] ep = "site.get_state" -> [svc |-> "site", roles |-> {"admin"}, siteRoles |-> {"operator"}, siteArg |-> "self", reporter |-> FALSE, line |-> 713]  \* /state/{score_id}
  [] ep = "site.health" -> [svc |-> "site", roles |-> {"member", "operator", "evidence", "admin"}, siteRoles |-> {}, siteArg |-> "none", reporter |-> FALSE, line |-> 725]  \* /health
  [] ep = "evidence.seed" -> [svc |-> "evidence", roles |-> {"admin"}, siteRoles |-> {}, siteArg |-> "none", reporter |-> FALSE, line |-> 836]  \* /seed
  [] ep = "evidence.get_score" -> [svc |-> "evidence", roles |-> {"member", "operator", "admin"}, siteRoles |-> {}, siteArg |-> "none", reporter |-> FALSE, line |-> 849]  \* /scores
  [] ep = "evidence.get_score_by_id" -> [svc |-> "evidence", roles |-> {"member", "operator", "admin"}, siteRoles |-> {}, siteArg |-> "none", reporter |-> FALSE, line |-> 857]  \* /scores/by_id/{score_id}
  [] ep = "evidence.attest" -> [svc |-> "evidence", roles |-> {"member", "operator"}, siteRoles |-> {}, siteArg |-> "none", reporter |-> TRUE, line |-> 882]  \* /attest
  [] ep = "evidence.dispute" -> [svc |-> "evidence", roles |-> {"member", "operator"}, siteRoles |-> {}, siteArg |-> "none", reporter |-> TRUE, line |-> 898]  \* /dispute
  [] ep = "evidence.restore" -> [svc |-> "evidence", roles |-> {"admin"}, siteRoles |-> {}, siteArg |-> "none", reporter |-> FALSE, line |-> 931]  \* /restore
  [] ep = "evidence.get_pending" -> [svc |-> "evidence", roles |-> {}, siteRoles |-> {"member"}, siteArg |-> "path", reporter |-> FALSE, line |-> 961]  \* /pending/{site_id}
  [] ep = "evidence.ack_pending" -> [svc |-> "evidence", roles |-> {}, siteRoles |-> {"member"}, siteArg |-> "path", reporter |-> FALSE, line |-> 983]  \* /pending/{site_id}/ack
  [] ep = "evidence.health" -> [svc |-> "evidence", roles |-> {"member", "operator", "evidence", "admin"}, siteRoles |-> {}, siteArg |-> "none", reporter |-> FALSE, line |-> 1001]  \* /health
  ]
====
