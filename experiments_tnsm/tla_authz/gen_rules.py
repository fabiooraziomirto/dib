#!/usr/bin/env python3
"""Estrae dal CODICE (service.py, via ast) la regola di autorizzazione di ogni route e
scrive Rules.tla (tabella CodeRules). Con --check confronta Rules.tla con il codice.
Non esegue service.py: lo legge soltanto. Segnala le route in cui _authorize/_reporter non e'
la prima istruzione (dopo l'eventuale docstring) o manca (P6, parte statica)."""
import ast, hashlib, sys
from pathlib import Path

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else \
    Path(__file__).resolve().parents[2] / "code/src/dib/registry/distributed/service.py"
OUT = Path(__file__).with_name("Rules.tla")
ALL = ["member", "operator", "evidence", "admin"]
ROLE_NAME = {"consortium_admin": "admin"}


def names(node, consts):
    if isinstance(node, ast.Name):
        return consts[node.id]
    return [ROLE_NAME.get(e.value, e.value) for e in node.elts]


def authorize_call(stmt):
    for n in ast.walk(stmt):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("_authorize", "_reporter"):
            return n
    return None


def main():
    src = SRC.read_text()
    tree = ast.parse(src)
    consts = {"_ANY_ROLE": ALL}
    # corpo di _reporter: ruoli ammessi e controllo del site_id nel payload
    rep_roles = None
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == "_reporter":
            c = authorize_call(n.body[1]) if len(n.body) > 1 else None
            c = [x for x in ast.walk(n) if isinstance(x, ast.Call) and getattr(x.func, "id", "") == "_authorize"][0]
            rep_roles = names(dict((k.arg, k.value) for k in c.keywords)["roles"], consts)
    payload_check = 'req.site_id != entry.get("site")' in src
    rows, problems = [], []
    for top in tree.body:
        if not (isinstance(top, ast.If) and isinstance(top.test, ast.Compare)
                and getattr(top.test.left, "id", "") == "ROLE"):
            continue
        svc = top.test.comparators[0].value  # "site" | "evidence"
        for fn in [f for f in top.body if isinstance(f, ast.FunctionDef)]:
            deco = [d for d in fn.decorator_list if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                    and d.func.attr in ("get", "post")]
            if not deco:
                continue
            path = deco[0].args[0].value
            body = [s for s in fn.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
            c = authorize_call(body[0]) if body else None
            name = f"{svc}.{fn.name}"
            if c is None:
                problems.append(f"{name} ({path}) riga {fn.lineno}: NESSUN _authorize/_reporter come prima istruzione")
                rows.append((name, svc, [], [], "none", False, fn.lineno, path)); continue
            if c.func.id == "_reporter":
                rows.append((name, svc, rep_roles, [], "none", payload_check, c.lineno, path)); continue
            kw = {k.arg: k.value for k in c.keywords}
            roles = names(kw["roles"], consts) if "roles" in kw else []
            sroles = names(kw["site_roles"], consts) if "site_roles" in kw else []
            site = "none"
            if "site" in kw:
                site = "self" if isinstance(kw["site"], ast.Call) else "path"
            rows.append((name, svc, roles, sroles, site, False, c.lineno, path))
    q = lambda xs: "{" + ", ".join(f'"{x}"' for x in xs) + "}"
    lines = [f"---- MODULE Rules ----",
             f"\\* GENERATO da gen_rules.py da service.py sha256 {hashlib.sha256(src.encode()).hexdigest()[:16]}",
             "\\* Non modificare a mano. Campo line = riga della chiamata _authorize/_reporter in service.py.",
             "EXTENDS Naturals", "Eps == {" + ", ".join(f'"{r[0]}"' for r in rows) + "}",
             "CodeRules == [ep \\in Eps |-> CASE"]
    for i, (name, svc, roles, sroles, site, rep, line, path) in enumerate(rows):
        lines.append(f'  {"[]" if i else "  "} ep = "{name}" -> [svc |-> "{svc}", roles |-> {q(roles)}, '
                     f'siteRoles |-> {q(sroles)}, siteArg |-> "{site}", reporter |-> {"TRUE" if rep else "FALSE"}, line |-> {line}]  \\* {path}')
    lines += ["  ]", "===="]
    text = "\n".join(lines) + "\n"
    if "--check" in sys.argv:
        print("Rules.tla coincide con il codice" if OUT.read_text() == text else "DIFFERENZA tra Rules.tla e il codice")
        sys.exit(0 if OUT.read_text() == text else 1)
    OUT.write_text(text)
    print(text)
    print("PROBLEMI:" if problems else "route senza _authorize: nessuna", *problems, sep="\n")


main()
