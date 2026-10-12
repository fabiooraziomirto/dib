"""EXPLORATORY (audit 91), not a test and not a validation. model_v5x.py = model.py of v4 plus ONE protocol-derived element: the client Certificate/CertificateVerify/Finished
flight of mTLS (TLS 1.3), CERT_SEGMENTS segments each lost with the same probability and delayed by the same RTO rule; 0 reproduces v4 exactly.
Run: python3 run_v5x.py  (degraded: R=0.4 s, p=5%, rto, req_segments=2, reconcile off, 20 000 episodes, model seed)."""
import model_v5x as m

for cs in (0, 1, 2, 3):
    m.CERT_SEGMENTS = cs
    r = m.simulate("C", 10, episodes=20000, R_=0.4, rto=True, req_segments=2)
    f = m.simulate("C", 1, episodes=4000, R_=0.4, rto=True, req_segments=2)
    print(f"CERT_SEGMENTS={cs} late_share_C10={r['late_share']:.3f} median_C10_ms={r['median_ms']:.0f} median_C1_ms={f['median_ms']:.0f}")
