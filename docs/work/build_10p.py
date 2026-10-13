#!/usr/bin/env python3
"""Builds docs/main_10p.tex (the 10-page proposal) from docs/main_wip.tex WITHOUT modifying main_wip.tex.
Step 1: resolve the change-tracking macros (\\del{...} removed, \\add{...} kept without colour) and drop comment-only lines.
Further steps are appended below as numbered, asserted transformations (each says what it cuts and why)."""
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "main_wip.tex"
OUT = Path(__file__).resolve().parents[1] / "main_10p.tex"


def strip_macro(text: str, name: str, keep: bool) -> str:
    out, i, key = [], 0, "\\" + name + "{"
    while True:
        j = text.find(key, i)
        if j < 0:
            out.append(text[i:])
            break
        out.append(text[i:j])
        k, depth = j + len(key), 1
        while depth:
            c = text[k]
            depth += (c == "{") - (c == "}")
            k += 1
        if keep:
            out.append(text[j + len(key):k - 1])
        i = k
    return "".join(out)


def _table_block(t: str, label: str) -> str:
    """The \\begin{table}...\\end{table} environment that contains \\label{label}."""
    k = t.index("\\label{" + label + "}")
    a = t.rfind("\\begin{table}", 0, k)
    b = t.index("\\end{table}", k) + len("\\end{table}")
    return t[a:b]


def step2_evaluation(t: str) -> str:
    """Step 2 (page budget, 10 pages all included): replace Evaluation (everything from \\section{Evaluation} to \\section{Discussion}) with work/eval_10p_body.tex,
    which carries the final-code results (audits 105, 108, 109, 115) and keeps the guard-removal and three-laboratory tables verbatim; drops the restoration-ablation table,
    the throughput sweep with the number of sites (old v33 data, not reusable), the registry latency paragraphs and the Pareto figure (all in the artifact)."""
    tla, three = _table_block(t, "tab:tla"), _table_block(t, "tab:threelab")
    body = (Path(__file__).resolve().parent / "eval_10p_body.tex").read_text()
    assert "@@TABLE_TLA@@" in body and "@@TABLE_THREELAB@@" in body
    body = body.replace("@@TABLE_TLA@@", tla).replace("@@TABLE_THREELAB@@", three)
    a, b = t.index("\\section{Evaluation}"), t.index("\\section{Discussion}")
    return t[:a] + body + t[b:]


def step3_trims(t: str) -> str:
    """Step 3 (page budget): drop the table of scoring configurations per experiment (the information is in the text of each experiment) and its reference, fix the references to
    removed labels, and remove the paragraph on RFC 9761 policy output from the Discussion (artifact / future work)."""
    a = t.index("\\begin{table}[t]\n\\centering\n\\caption{Scoring configuration of each experiment")
    b = t.index("\\end{table}", a) + len("\\end{table}")
    t = t[:a] + t[b:]
    old = "unless an experiment states trust weighting (Table~\\ref{tab:configs})."
    assert t.count(old) == 1
    t = t.replace(old, "unless an experiment states trust weighting.")
    old = "and restoration-policy ablation (Table~\\ref{tab:comparison})"
    assert t.count(old) == 1
    t = t.replace(old, "and the restoration-policy ablation (Sec.~\\ref{sec:lifecycle-results})")
    a = t.index("Policy output is similarly scoped")
    b = t.index("\\section{Conclusion}")
    t = t[:a].rstrip() + "\n\n" + t[b:]
    a = t.index("The remainder of this paper is organized as follows.")
    b = t.index("\n\n", a)   # end of the roadmap paragraph
    t = t[:a].rstrip() + "\n" + t[b:]
    t = t.replace("\\begin{thebibliography}{00}", "\\setlength{\\IEEEbibitemsep}{0pt}\n\\begin{thebibliography}{00}\n\\footnotesize", 1)
    # step 4: positioning table out (the related-work text carries the comparison), two Discussion sentences on ECH/QUIC out
    a = t.index("\\begin{table}[ht]", t.index("\\section{Related Work}"))
    b = t.index("\\end{table}", a) + len("\\end{table}")
    assert "tab:positioning" in t[a:b]
    t = t[:a].rstrip() + "\n" + t[b:]
    old = " (see Table~\\ref{tab:positioning})"
    assert t.count(old) == 1
    t = t.replace(old, "")
    a = t.index("Historical captures expose names through DNS or HTTP/TLS metadata.")
    b = t.index("Coverage of fleets using these mechanisms remains unverified.")
    t = t[:a] + t[b:]
    # step 5: orphan reference, method detail and two Discussion passages out (page budget)
    old = " Table~\\ref{tab:positioning} compares the closest related systems."
    assert t.count(old) == 1
    t = t.replace(old, "")
    old = " Aggregates use seeds 0--19, A1/Sybil/drift use seed 42, and cross-lab, OpenWrt, and concurrency use seed 0."
    assert t.count(old) == 1
    t = t.replace(old, "")
    a = t.index("Operators need visibility into pending updates and installed policies;")
    b = t.index("\n\n", a)
    t = t[:a].rstrip() + "\n" + t[b:]
    a = t.index("Resolver-side telemetry or endpoint instrumentation")
    b = t.index("\n\n", a)
    t = t[:a].rstrip() + "\n" + t[b:]
    old = "(after reconnection, convergence stayed within its bound in every measured cell)"
    assert t.count(old) == 1
    t = t.replace(old, "(after reconnection, the median convergence stayed within its bound in every measured cell)")
    # step 6a (page budget, v8 text added): cite only XACML for deny-overrides
    old = "policy frameworks~\\cite{xacml3, ponder}"
    assert t.count(old) == 1, t.count(old)
    t = t.replace(old, "policy frameworks~\\cite{xacml3}")
    # step 6: drop the bibliography items that are no longer cited after the cuts
    import re as _re
    a = t.index("\\begin{thebibliography}")
    body, bib = t[:a], t[a:]
    end = bib.index("\\end{thebibliography}")
    bib_items, tail = bib[:end], bib[end:]
    cited = {k.strip() for m in _re.findall(r"\\cite\{([^}]*)\}", body) for k in m.split(",")}
    parts = _re.split(r"(?=\\bibitem\{)", bib_items)
    keep = [parts[0]] + [x for x in parts[1:] if _re.match(r"\\bibitem\{([^}]*)\}", x).group(1) in cited]
    t = body + "".join(keep).rstrip() + "\n" + tail
    return t


def main() -> None:
    t = SRC.read_text()
    t = strip_macro(t, "del", keep=False)
    t = strip_macro(t, "add", keep=True)
    t = "\n".join(l for l in t.split("\n") if not l.lstrip().startswith("%"))
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = step2_evaluation(t)
    t = step3_trims(t)
    OUT.write_text(t)
    print("written", OUT, len(t), "chars")


if __name__ == "__main__":
    main()
