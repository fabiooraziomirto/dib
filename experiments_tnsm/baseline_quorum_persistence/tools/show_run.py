import json, csv
a = json.load(open("experiments_tnsm/baseline_quorum_persistence/run_20261012/real/aggregates.json"))
ref = {(r["receiver"], r["stage"]): r for r in csv.DictReader(open("results/three_lab_matched/matched_ablation.csv"))}
print("a) RIPRODUZIONE (attese = results/three_lab_matched/matched_ablation.csv; ottenute = aggregates.json)")
for rec in a["real"]:
    for st, g in rec["stages"].items():
        e = ref[(rec["receiver"], st)]
        ok = int(e["candidates"]) == g["candidates"] and all(abs(float(e[k]) - g[k]) < 1e-12 for k in ("coverage", "precision", "recall", "f1"))
        print(rec["receiver"], st, "att:", e["candidates"], e["coverage"], e["precision"], e["recall"], e["f1"], "| ott:", g["candidates"], g["coverage"], g["precision"], g["recall"], g["f1"], "|", "OK" if ok else "DIFF")
print("\nb) |C_DIB| e baseline assoluti")
for rec in a["real"]:
    print(rec["receiver"], "|C_DIB| =", rec["stages"]["DIB"]["candidates"], " DIB prec/rec =", rec["stages"]["DIB"]["precision"], rec["stages"]["DIB"]["recall"])
    for k, g in rec["baseline"].items():
        if isinstance(g, dict) and "tau_match" not in k:
            print("  ", k, "|C_B| =", g["candidates"], "prec =", g["precision"], "rec =", g["recall"])
        elif not isinstance(g, dict):
            print("  ", k, g)
print("\nc) tau_match")
for rec in a["real"]:
    g = rec["baseline"]["m2_tau_match"]; d = rec["stages"]["DIB"]["candidates"]
    print(rec["receiver"], "tau_match =", rec["tau_match"], "|C_B| =", g["candidates"], "|C_DIB| =", d, "divario =", abs(g["candidates"] - d), "rapporto =", abs(g["candidates"] - d) / d, "prec_B =", g["precision"], "rec_B =", g["recall"])
print("\nd) verdetti come scritti nel run")
print(json.dumps(a["real_verdicts"], indent=1))
