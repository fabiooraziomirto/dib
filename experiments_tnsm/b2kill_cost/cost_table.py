"""B2-kill cost table as a function of the measured L_dns (user instruction 2026-10-11, point C.4). Does NOT run B2-kill.

Model, read off docs/audit/14_priorita_esperimenti_tnsm.md:268-273 and checked against its published rows (test_cost_table.py):
  duration of a trial = F_p + conv + k * ep
  F_p   = fixed costs per profile: lan 5 s, wan 10 s, degraded 15 s
  conv  = 0.45 + 0.05 T + D_run(profile, arm)                     (kill convergence, audit 14:271)
  ep    = 0.5 + 3 * max(E_p, 3 * L_dns)                           (an episode = 3 fan-outs, service.py V7; the dead site costs
          3 attempts x L_dns per fan-out, FANOUT 10 runs the sites in parallel, service.py:700-712; the 0.5 s is the driver pause)
  E_p   = per-fan-out time without dead-site delay: lan 0.02, wan 0.4, degraded 2.75 s (from the "fast" episode 0.56 / 1.7 / 8.75 s)
Hypothesis (declared before running): with L_dns = 0.186 s the episode becomes 0.5 + 3 * 0.558 = 2.17 s at lan and wan (3 L_dns
dominates E_p) and stays 8.75 s at degraded (E_p dominates); the model reproduces audit 14's fast rows (L = 2.6 ms) and its slow rows at
lan and wan (L = 1.0 s -> 9.5 s). It does NOT reproduce the slow `degraded` row (11.0 s vs 9.5 s): that row is reported as published.
Falsification: test_cost_table.py fails if the fast rows or the slow lan/wan rows are not reproduced to 0.1 s.
"""
from __future__ import annotations

F = {"lan": 5.0, "wan": 10.0, "degraded": 15.0}
E = {"lan": 0.02, "wan": 0.4, "degraded": 2.75}
D_RUN = {"lan": {"D": 0.06, "C": 0.06}, "wan": {"D": 0.96, "C": 1.44}, "degraded": {"D": 2.4, "C": 3.6}}
# (k, profile, T-list, trials per T: 10 per arm x 2 arms), audit 14:277-288
DESIGN = [(1, "lan", (5, 15)), (1, "wan", (5, 15)), (1, "degraded", (5, 15)),
          (10, "lan", (5, 15)), (10, "wan", (5, 15)), (10, "degraded", (5, 15)), (50, "lan", (5,))]
TRIALS_PER_T = 20


def episode_s(profile: str, l_dns: float) -> float:
    return 0.5 + 3.0 * max(E[profile], 3.0 * l_dns)


def trial_s(profile: str, arm: str, T: float, k: int, l_dns: float) -> float:
    return F[profile] + 0.45 + 0.05 * T + D_RUN[profile][arm] + k * episode_s(profile, l_dns)


def table(l_dns: float) -> tuple[list[dict], float]:
    rows, total = [], 0.0
    for k, profile, Ts in DESIGN:
        for T in Ts:
            d, c = trial_s(profile, "D", T, k, l_dns), trial_s(profile, "C", T, k, l_dns)
            hours = (TRIALS_PER_T // 2) * (d + c) / 3600.0
            rows.append({"k": k, "profile": profile, "T": T, "trials": TRIALS_PER_T, "D_s": d, "C_s": c, "hours": hours})
            total += hours
    return rows, total


def markdown(l_dns: float, label: str) -> str:
    rows, total = table(l_dns)
    out = [f"*{label} (L_dns = {l_dns * 1000:.1f} ms)*", "", "| k | Profilo | T (s) | Prove | Durata per prova D / C (s) | Ore |", "|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['k']} | {r['profile']} | {r['T']} | {r['trials']} | {r['D_s']:.1f} / {r['C_s']:.1f} | {r['hours']:.3f} |")
    out.append(f"| **Totale** | | | **{sum(r['trials'] for r in rows)}** | | **{total:.2f}** |")
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    for v, lab in ((0.0026, "veloce, misura a lan della notte"), (0.186, "misurato a wan, p95"), (1.0, "lento, ipotesi dell'audit 14")):
        print(markdown(v, lab), "\n")
    print("episodio (s):", {p: [round(episode_s(p, v), 2) for v in (0.0026, 0.186, 1.0)] for p in F}, file=sys.stderr)
