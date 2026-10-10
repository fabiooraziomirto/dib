# Proposed reformulation of the f_s assumption (text only, not applied to main.tex)

Version 2 (2026-10-10). This version fixes the v1 error "with h_d = 3, two colluders exceed 5/12". The claim is false: 2/5 < 5/12, and only three colluders (1/2) exceed it. It also adds the coverage requirement and the quorum sentence. Every number below was checked with exact fractions in `analysis_fs/test_followup.py` (`test_p0_*`). Supporting evidence: `analysis_fs/REPORT.md` §0, §4, §6, §7. Line references are to `docs/main.tex`.

Check table (k_tol at 5/12 = largest k with k/(k+h_d) < 5/12; at f_s = largest k with k/(k+h_d) ≤ 0.30):

| h_d | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| k_tol (5/12) | 0 | 1 | 2 | 2 | 3 | 4 | 4 | 5 |
| k_tol (f_s = 0.30) | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |

## Full variant (replaces the f_s sentence at paper:172 and the paragraph after Criterion 1, paper:408)

> **Assumption (bounded per-type adversarial share).** For each device type $d$, let $ES_d$ be the member sites whose evidence for $d$ enters scoring, $h_d$ the honest sites among them, and $k_d$ the colluding malicious members. We assume $k_d/(k_d+h_d)\le f_s$ for every $d$, with $f_s=0.30$. Because $ES_d$ is formed from submitted evidence, membership governance must enforce this share: a member contributes evidence for $d$ only after the consortium has verified that it operates devices of type $d$. The prototype does not implement this check.
>
> Under this assumption, Criterion 1 rejects adversary-only facts whenever $f_s<1-(1-\theta)/\alpha=5/12$. The guarantee holds per device type, not consortium-wide. The bound $\alpha f_s+\beta$ is a supremum that is never attained while at least one honest site observes $d$. An adversary that reports on every active day of $d$ and dominates its observation volume approaches it arbitrarily closely, and an exact share of $5/12$ is therefore still rejected.
>
> In counts, tolerating $k$ colluders for a device type requires $h_d>7k/5$ honest observers at the analytical limit and $h_d\ge 7k/3$ at the declared budget; for $k=3$, that means at least five and at least seven honest sites, respectively. Device types with few honest observers are therefore the binding case. With $h_d\le2$, a single colluder already exceeds $f_s$, although a share of $1/3$ remains below $5/12$. With $h_d=3$, two colluders stay below $5/12$ ($2/5$), and three exceed it.
>
> When only two or three sites supply evidence, as in the three-deployment cold-start comparison, the quorum $m=2$ rather than the score rejects facts reported by a single source. Once the quorum is met, every source reports the fact, and the breadth term equals one.
>
> The assumption does not cover (i) honest sites that report traffic from compromised devices (A1); (ii) adversary-controlled names, or global addresses on DNS/NTP ports, that pass endpoint eligibility; (iii) unfounded disputes, through which any two members can revoke a fact, an availability rather than integrity effect; and (iv) identity inflation (Sybil), which Sec. X evaluates separately.

## Short variant (threat model, paper:172)

> Admission further assumes that, for every device type, colluding malicious members make up at most a fraction $f_s=0.30$ of the sites contributing evidence for that type, and that membership governance verifies which device types each member operates. The guarantee is per type. It requires more than $7k/5$ honest observers to tolerate $k$ colluders and is weakest for types observed by few sites; with two or three sources, the two-site quorum provides the protection (Sec. IV-B).

## Evaluation sentences (suggested for Sec. VI-E, numbers from `analysis_fs/out/`)

The sentences below use raw breadth, the quantity to which Criterion 1 applies. If you keep the trust-weighted runs instead, the sentences must say so (paper:414 currently says the experiments use raw breadth).

> We draw $k\in\{0,\dots,5\}$ malicious sites per device type from that type's eligible population, over 20 seeds and ten pseudo-sites, with single-shot fabrication and raw breadth. For the 25 device types observed at all ten sites, the highest fabricated-fact score is $0.317\pm0.022$ (maximum $0.353$) at $k=3$ and $0.474\pm0.034$ (maximum $0.532$) at $k=5$. No fabricated fact is admitted. Two device types are observed at fewer than ten sites, and we report them separately rather than excluding them. NetatmoWeatherStation is observed at two sites: once $k\ge2$, both are malicious, its effective share is $1.0$, and the fabricated fact scores $0.94$ and is admitted in every seed. BlipCareBPMeter (four to eight sites) is admitted only when the effective share reaches $0.8$ or more. Both cases lie outside the assumption; neither contradicts the bound.
>
> A worst-case adversary that reports on every active day and supplies up to 100 times the honest volume reaches $0.579$ at $k=3$ of ten ($f_s=0.30$), just below the bound of $0.58$, and never crosses $\theta$ at $k=4$ ($0.639$ against a bound of $0.64$). At $k=5$, it is admitted once its volume reaches about 1.4 times the honest volume, which matches the analytical threshold.

(The last paragraph replaces "At $f_s=0.30$, the largest score passing quorum is 0.562 over 120 days" at paper:631. The value 0.562 is the maximum of the 120-day, trust-weighted strategy, not of the threat model.)
