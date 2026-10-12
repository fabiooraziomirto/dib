"""Delivery-cost-under-loss model of audit 60 s.3-4 (stdlib only). Structure chosen AFTER seeing the B5 data (not an independent confirmation).
Parameters are NOT fitted: R = 0.4 s (RTT of `degraded`), loss 5% per packet, httpx per-PHASE timeout 1.0 s (service.py:121), 3 attempts without pause
(service.py:120), a new connection per attempt (service.py:708-712). A retransmission arrives after >= 1 s (initial RTO), i.e. after the phase timeout, so
any lost packet of a phase fails the attempt at the phase timeout.
D: connect (SYN, SYN-ACK) -> request -> response. C (mTLS): connect -> TLS (ClientHello, server flight) -> request(+Finished) -> response.
Apply time = request arrival (idempotent: only the first arrival counts). Usage: python3 model.py"""
from __future__ import annotations

import random
import statistics

R = 0.4
P_LOSS = 0.05
TIMEOUT = 1.0
RETRIES = 3
NOMINAL = {"D": 0.6, "C": 1.0}       # request arrival without loss
SEED = 20261012


def always_lost(kind):
    return True


def rto(R_: float) -> float:
    """Linux TCP retransmission timeout after the handshake: srtt + max(4*rttvar, 200 ms) with srtt = R, rttvar = R/2 (v2, audit 75)."""
    return R_ + max(2 * R_, 0.2)


def _extra(lost, kind: str, R_: float) -> float:
    """Extra delay of one packet that may be lost repeatedly: RTO, then 2*RTO, ... (v2)."""
    extra, k = 0.0, 0
    while lost(kind) and k < 6:
        extra += rto(R_) * 2 ** k
        k += 1
    return extra


def rng_lost(rng: random.Random, p: float):
    return lambda kind: rng.random() < p


def attempt(arm: str, lost, warm: bool = False, timeout: float = TIMEOUT, hedge_s: float | None = None, R_: float = R, rto: bool = False) -> dict:
    """One attempt. Returns dur (time until it returns or fails), ok (response received), apply (request arrival time or None)."""
    t = 0.0
    if not warm:
        first_ok = not (lost("syn") or lost("synack"))
        if hedge_s is not None:
            done = R_ if first_ok else None
            if done is None or done > hedge_s:
                second_ok = not (lost("syn2") or lost("synack2"))
                cand = hedge_s + R_ if second_ok else None
                done = min([x for x in (done, cand) if x is not None], default=None)
            if done is None:
                return {"dur": hedge_s + timeout, "ok": False, "apply": None}
            t = done
        else:
            if not first_ok:
                return {"dur": timeout, "ok": False, "apply": None}
            t = R_
        if arm == "C" and not rto:
            if lost("clienthello") or lost("serverflight"):
                return {"dur": t + timeout, "ok": False, "apply": None}
            t += R_
    if rto:   # v2: packets after the handshake are retransmitted after the RTO instead of failing the phase outright
        if arm == "C" and not warm:
            extra = _extra(lost, "clienthello", R_) + _extra(lost, "serverflight", R_)
            if R_ + extra >= timeout:
                return {"dur": t + timeout, "ok": False, "apply": None}
            t += R_ + extra
        er = _extra(lost, "request", R_)
        if er + R_ / 2 >= timeout:
            return {"dur": t + timeout, "ok": False, "apply": None}
        apply = t + er + R_ / 2
        t_read = R_ + er + _extra(lost, "response", R_)
        if t_read >= timeout:
            return {"dur": t + timeout, "ok": False, "apply": apply}
        return {"dur": t + t_read, "ok": True, "apply": apply}
    if lost("request"):
        return {"dur": t + timeout, "ok": False, "apply": None}
    apply = t + R_ / 2
    if lost("response"):
        return {"dur": t + timeout, "ok": False, "apply": apply}
    return {"dur": t + R_, "ok": True, "apply": apply}


def deliver(arm: str, lost, warm_first: bool = False, **kw) -> dict:
    start, first_apply = 0.0, None
    for k in range(RETRIES):
        a = attempt(arm, lost, warm=(warm_first and k == 0), **kw)
        if a["apply"] is not None and first_apply is None:
            first_apply = start + a["apply"]
        start += a["dur"]
        if a["ok"]:
            return {"first_apply": first_apply, "ret": start, "pending": False}
    return {"first_apply": first_apply, "ret": start, "pending": True}


def episode(arm: str, fanout: int, lost_by_site: dict, reconcile: bool = False, phases: dict | None = None, **kw) -> dict:
    """v3: with reconcile=True each site also applies at phi_i + 2R (its next periodic pull, phase phi_i after the evidence commit): apply = min(fan-out, pull)."""
    n = len(lost_by_site)
    Rr = kw.get("R_", R)
    applies, pending, t0 = [], False, 0.0
    for i in range(n):
        d = deliver(arm, lost_by_site[i], **kw)
        a = t0 + d["first_apply"] if d["first_apply"] is not None else None
        if reconcile:
            pull = max(0.0, (phases or {}).get(i, 0.0)) + 2 * Rr
            a = pull if a is None else min(a, pull)
        else:
            pending |= d["pending"]
        applies.append(a)
        if fanout == 1:
            t0 += d["ret"]
    done = [a for a in applies if a is not None]
    return {"apply_last": max(done) if done and not pending else None, "pending": pending, "applies": applies}


def simulate(arm: str, fanout: int, episodes: int = 20000, seed: int = SEED, p_loss: float = P_LOSS, n_sites: int = 10, T_reconcile: float = 5.0,
             J_reconcile: float = 0.5, **kw) -> dict:
    rng = random.Random(seed)
    phase_rng = random.Random(seed + 1)       # separate stream: the loss draws of v2 are unchanged when reconcile is off
    lasts, pend, late, tot = [], 0, 0, 0
    for _ in range(episodes):
        ph = {i: phase_rng.uniform(0.0, T_reconcile + J_reconcile) for i in range(n_sites)} if kw.get("reconcile") else None
        ep = episode(arm, fanout, {i: rng_lost(rng, p_loss) for i in range(n_sites)}, phases=ph, **kw)
        pend += ep["pending"]
        if fanout == 10:                                       # per-site lateness only where all sites start at 0 (comparable to the measured late share)
            for a in ep["applies"]:
                if a is not None:
                    tot += 1
                    Rr = kw.get("R_", R)
                    nominal = (0.5 if kw.get("warm_first") else (1.5 if arm == "D" else 2.5)) * Rr   # request arrival without loss (cold D 1.5 R, cold C 2.5 R)
                    late += a > nominal + 0.75 * Rr
        if ep["apply_last"] is not None:
            lasts.append(ep["apply_last"])
    Rr = kw.get("R_", R)
    nominal_last = (0.5 if kw.get("warm_first") else (1.5 if arm == "D" else 2.5)) * Rr
    slow = sum(1 for x in lasts if x > nominal_last + 0.75 * Rr) / len(lasts) if lasts and fanout == 10 else None   # episodes slower than the lossless time + 0.75 R
    lasts.sort()
    q = lambda p: 1000 * lasts[int(p * (len(lasts) - 1))] if lasts else None  # noqa: E731
    return {"arm": arm, "fanout": fanout, "episodes": episodes, "pending_fraction": pend / episodes, "median_ms": q(0.5), "p95_ms": q(0.95),
            "late_share": (late / tot) if tot else 0.0, "slow_episode_fraction": slow}


POLICIES = {"P0 current": {}, "P1 warm connection": {"warm_first": True}, "P2 phase timeout 0.6 s": {"timeout": 0.6}, "P3 hedged connect 0.5 s": {"hedge_s": 0.5}}
MEASURED = {("D", 10): {"median_ms": 1639.0, "late_share": 68 / 499}, ("C", 10): {"median_ms": 2826.0, "late_share": 114 / 455},
            ("D", 1): {"median_ms": 10316.0}, ("C", 1): {"median_ms": 18516.0}}


def main() -> None:
    print("| policy | arm | FANOUT | median ms | p95 ms | pending | late share |\n|---|---|---|---|---|---|---|")
    for name, kw in POLICIES.items():
        for arm in ("D", "C"):
            for fo in (10, 1):
                r = simulate(arm, fo, **kw)
                print(f"| {name} | {arm} | {fo} | {r['median_ms']:.0f} | {r['p95_ms']:.0f} | {r['pending_fraction']:.4f} | {r['late_share']:.3f} |")


if __name__ == "__main__":
    main()
