"""Model v5 (audit 94/95): v4 plus the observed mTLS client flight in the request burst. See test_model_v5.py for the contract. model.py (v4) is not modified."""
from __future__ import annotations

import model as m


def kwargs_for(arm: str) -> dict:
    if arm == "C":
        return {"req_segments": 3, "rto": True}
    if arm == "D":
        return {"req_segments": 2, "rto": True}
    raise ValueError(f"unknown arm {arm!r}")


def simulate(arm: str, fanout: int, **kw) -> dict:
    return m.simulate(arm, fanout, **{**kwargs_for(arm), **kw})
