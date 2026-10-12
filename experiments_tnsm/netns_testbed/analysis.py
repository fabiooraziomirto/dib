"""Pure analysis helpers of the netns testbed (audit 75): netem commands, nominal times, cell summaries, bootstrap, T-0 validity."""
from __future__ import annotations

import random
import statistics

NET = "dev lo"


def netem_cmds(d_ms: int, loss_pct: float, initial: bool) -> list[list[str]]:
    """tc commands (argument lists). Default band 1:1 carries netem (every packet crosses `lo` once, so d is a ONE-WAY delay); band 1:2 (pfifo) carries the
    driver's address 127.0.0.2 in both directions, so the driver's own requests are not impaired."""
    loss = f" loss {loss_pct:g}%" if loss_pct else ""
    spec = f"delay {d_ms}ms{loss}".split()
    if not initial:
        return [["tc", "qdisc", "change", "dev", "lo", "parent", "1:1", "handle", "10:", "netem", *spec]]
    return [
        ["tc", "qdisc", "add", "dev", "lo", "root", "handle", "1:", "prio", "bands", "3", "priomap", *(["0"] * 16)],
        ["tc", "qdisc", "add", "dev", "lo", "parent", "1:1", "handle", "10:", "netem", *spec],
        ["tc", "qdisc", "add", "dev", "lo", "parent", "1:2", "handle", "20:", "pfifo"],
        ["tc", "filter", "add", "dev", "lo", "protocol", "ip", "parent", "1:0", "prio", "1", "u32", "match", "ip", "src", "127.0.0.2/32", "flowid", "1:2"],
        ["tc", "filter", "add", "dev", "lo", "protocol", "ip", "parent", "1:0", "prio", "1", "u32", "match", "ip", "dst", "127.0.0.2/32", "flowid", "1:2"],
    ]


def nominal(R: float, warm: bool) -> float:
    """Request arrival at the site without loss: cold = connect (R) + one way (R/2) = 1.5 R; warm connection = 0.5 R."""
    return (0.5 if warm else 1.5) * R


def is_late(apply_s: float, R: float, warm: bool) -> bool:
    return apply_s > nominal(R, warm) + 0.75 * R


def _complete(e: dict) -> bool:
    a = e["applies"]
    return e["setup_ok"] and len(a) == 10 and all(v is not None for v in a.values())


def cell_summary(episodes: list[dict], R: float, warm: bool) -> dict:
    valid = [e for e in episodes if e["setup_ok"]]
    comp = [e for e in valid if _complete(e)]
    sites = [v for e in valid for v in e["applies"].values() if v is not None]
    late = sum(1 for v in sites if is_late(v, R, warm))
    lasts = sorted(1000 * max(e["applies"].values()) for e in comp)
    slow = sum(1 for e in comp if is_late(max(e["applies"].values()), R, warm))
    q = lambda p: lasts[int(p * (len(lasts) - 1))] if lasts else None  # noqa: E731
    return {"n_episodes": len(episodes), "n_valid": len(valid), "n_setup_failed": len(episodes) - len(valid), "n_complete": len(comp),
            "pending_fraction": (len(valid) - len(comp)) / len(valid) if valid else None,
            "late_share": late / len(sites) if sites else None, "n_sites_applied": len(sites),
            "slow_episode_fraction": slow / len(comp) if comp else None,
            "median_last_ms": statistics.median(lasts) if lasts else None, "p95_last_ms": q(0.95)}


def boot_ci_share(xs: list[int], seed: int = 20261012, res: int = 10000):
    if not xs:
        return None
    rng = random.Random(seed)
    n = len(xs)
    vals = sorted(sum(rng.choices(xs, k=n)) / n for _ in range(res))
    return vals[int(0.025 * res)], vals[int(0.975 * res) - 1]


def t0_valid(episodes: list[dict], R: float, warm: bool, tol_s: float = 0.05) -> dict:
    """T-0: at p = 0 the median per-site apply time is within tol of the nominal and nothing is late."""
    sites = [v for e in episodes if e["setup_ok"] for v in e["applies"].values() if v is not None]
    if not sites:
        return {"valid": False, "reason": "no data"}
    med = statistics.median(sites)
    late = sum(1 for v in sites if is_late(v, R, warm))
    return {"valid": abs(med - nominal(R, warm)) <= tol_s and late == 0, "median_s": med, "nominal_s": nominal(R, warm), "late": late, "n": len(sites)}


def _late_counts(eps: list[dict], R: float, warm: bool) -> list[tuple[int, int]]:
    out = []
    for e in eps:
        if not e["setup_ok"]:
            continue
        v = [x for x in e["applies"].values() if x is not None]
        out.append((sum(1 for x in v if is_late(x, R, warm)), len(v)))
    return out


def boot_diff_late_share(eps_a, eps_b, R: float, warm_a: bool, warm_b: bool, seed: int = 20261012, res: int = 4000):
    """Percentile 95% CI of (late share of A) - (late share of B), resampling EPISODES independently in each group (per-site shares are not independent within an episode)."""
    ca, cb = _late_counts(eps_a, R, warm_a), _late_counts(eps_b, R, warm_b)
    if not ca or not cb:
        return None
    rng = random.Random(seed)
    diffs = []
    for _ in range(res):
        sa = rng.choices(ca, k=len(ca))
        sb = rng.choices(cb, k=len(cb))
        diffs.append(sum(x for x, _ in sa) / max(sum(n for _, n in sa), 1) - sum(x for x, _ in sb) / max(sum(n for _, n in sb), 1))
    diffs.sort()
    return diffs[int(0.025 * res)], diffs[int(0.975 * res) - 1]


def median_site_ms(eps: list[dict]):
    v = [1000 * x for e in eps if e["setup_ok"] for x in e["applies"].values() if x is not None]
    return statistics.median(v) if v else None
