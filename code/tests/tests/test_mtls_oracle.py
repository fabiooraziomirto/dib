"""T15 of the mTLS design (audit 13 sez. 6): lifecycle invariants with authentication on.

The same S2-style episode runs (a) on real mTLS processes (DIB_DIST_MTLS=1,
DIB_DIST_TYPE_LIST=1; every call authenticated by certificate) and (b) on the in-process
cluster without mTLS (_dist_harness, the setting of the existing 412 tests):
  stage+commit at both sites -> local veto at site-0 -> dispute by site-1 ->
  confirmation by site-0 -> global restore by the admin -> re-commit at site-1.

Hypotheses (stated before running):
  O1. After every step the (state, origin) of the fact at each site is identical in (a)
      and (b): authentication changes who may act, not what an allowed action does.
  O2. Exportable: a fact is exported (one ACE in /export_mud) at a site iff its local
      state there is Active; nothing disputed or revoked is exported.
  O3. The local veto survives the episode (site-0 stays revoked with local origin) and
      the global restore never re-activates a site automatically (site-1 returns to
      monitor-only and is Active again only after its operator commits): I2 and I3 of
      the paper, checked here on this one sequence, not proved.
Falsification: any assertion below failing. Not covered: offline sites during the
episode with mTLS (needs process stop/start; left to M6 in audit 04).
"""
from __future__ import annotations

import pytest

from _dist_harness import make_cluster  # noqa: F401  (fixture)
from _mtls_ca import requires_openssl
from _mtls_cluster import FACT, cl  # noqa: F401  (fixture)

pytestmark = requires_openssl

ENDPOINT = "oracle.vendor.test"


class MtlsDriver:
    def __init__(self, cl):
        self.cl = cl
        self.body = {**FACT, "endpoint": ENDPOINT}

    def _post(self, who, where, path):
        with self.cl.client(who) as c:
            r = c.post(f"{self.cl.url[where]}{path}", json=self.body)
        assert r.status_code == 200, (who, path, r.status_code, r.text)

    def seed(self):
        with self.cl.client("admin") as c:
            self.id = c.post(f"{self.cl.url['evidence']}/seed", json=self.body).json()["id"]

    def stage(self, s): self._post(f"op{s}", s, "/query")
    def commit(self, s): self._post(f"op{s}", s, "/commit")
    def veto(self, s): self._post(f"op{s}", s, "/local_revoke")
    def dispute(self, s): self._post(f"member{s}", "evidence", "/dispute")
    def restore(self): self._post("admin", "evidence", "/restore")

    def observe(self, s):
        with self.cl.client(f"op{s}") as c:
            st = c.get(f"{self.cl.url[s]}/state/{self.id}").json()
            doc = c.get(f"{self.cl.url[s]}/export_mud", params={"device_type": FACT["device_type"]}).json()
        aces = doc["ietf-access-control-list:access-lists"]["acl"][0]["aces"]["ace"]
        return st["state"], st["origin"], len(aces)


class InprocDriver:
    def __init__(self, cluster):
        self.c = cluster

    def seed(self): self.id = self.c.seed(ENDPOINT, FACT["device_type"])
    def stage(self, s): assert self.c.stage(s, ENDPOINT).status_code == 200
    def commit(self, s): assert self.c.commit(s, ENDPOINT).status_code == 200
    def veto(self, s): assert self.c.local_revoke(s, ENDPOINT).status_code == 200
    def dispute(self, s): assert self.c.dispute(f"site-{s}", ENDPOINT).status_code == 200
    def restore(self): assert self.c.restore(ENDPOINT).status_code == 200

    def observe(self, s):
        st = self.c.state(s, self.id)
        return st["state"], st["origin"], self.c.ace_count(s, FACT["device_type"])


def _episode(d) -> list[tuple]:
    trace = []

    def snap(label):
        trace.append((label, d.observe(0), d.observe(1)))

    d.seed()
    for s in (0, 1):
        d.stage(s)
        d.commit(s)
    snap("committed")
    d.veto(0)
    snap("veto at site-0")
    d.dispute(1)
    snap("dispute by site-1")
    d.dispute(0)
    snap("confirmed by site-0")
    d.restore()
    snap("global restore")
    d.commit(1)
    snap("re-commit at site-1")
    return trace


def test_o1_o2_o3_same_episode_with_and_without_mtls(cl, make_cluster):
    with_mtls = _episode(MtlsDriver(cl))
    without = _episode(InprocDriver(make_cluster(n_sites=2)))
    assert with_mtls == without  # O1
    for label, *sites in with_mtls:  # O2
        for state, _origin, aces in sites:
            assert aces == (1 if state == "active" else 0), (label, state, aces)
    trace = {label: sites for label, *sites in with_mtls}
    assert trace["global restore"][0][:2] == ("revoked", "local")       # O3: veto survives
    assert trace["global restore"][1][0] == "monitor-only"              # O3: no automatic Active
    assert trace["re-commit at site-1"][1][0] == "active"
    assert trace["re-commit at site-1"][0][:2] == ("revoked", "local")
