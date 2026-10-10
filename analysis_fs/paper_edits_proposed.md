# Proposed edits to `docs/main.tex` (853 lines). Text only, NOT applied

Reference file: `/root/Desktop/DIB_reframe/docs/main.tex`. Each entry gives the line, the current text (verbatim excerpt), the proposed text (English, ready to paste), a one-line rationale, and the supporting result (`analysis_fs/REPORT.md` section and CSV in `analysis_fs/out/`). Where a value is not in the report, the entry says **to be computed** (*da calcolare*). Line numbers refer to the file as it is now; applying an edit shifts the lines below it.

**Ordering constraint (Punto A).** The sentences listed in §0 rest on the UNSW file that contains the 8 spurious rows. The pure date effect is nil on every admission decision tested (REPORT §11): 0 admission changes over 21 seeds, raw and trust, and 0 cells near θ in `results/`. However, re-running the scripts on a filtered file also reshuffles the partition (seed variance). Edit those sentences only after deciding whether to regenerate the results on the filtered data.

## 0. Sentences that depend on the UNSW input with spurious dates (edit only after Punto A is settled)

| Line | Claim | Exposure [C]/[D] |
|---|---|---|
| 528 | 55/564 ACEs, 36 staged, macro recall 0.079 / 0.124, cold-start F1 0.112 ± 0.002 vs 0.022 ± 0.005 | All UNSW types (`results/recall`, `results/cold_start`). Pure date effect on the affected types: no admission change (`spurious_dates_summary.csv`) |
| 530 | "Every quorum $m$ … admits the same 346 facts" | Trust weighting, seed 42, full population: 346 before and 346 after; 3,738 scores of other types move by at most 4.9e-5 (`spurious_dates_trust_seed42.csv`) |
| 627–629 | A1: 0/59, 21/150, first at $k=7$ (0.679) | A1 facts are injected into all UNSW types; whether the five A1 device types overlap the three affected types was not checked (**to be computed**) |
| 631 | 0.354, 0.562, 0.663 | Masquerade maxima are on HelloBarbie/CanaryCamera (`results/masquerade/service_masquerade.csv`), not affected types; under trust weighting other types can move (seed-42 check, REPORT §11) |
| 637 | Sybil 45/48, 0.905 | Target device is **AugustDoorBell**, an affected type (`results/sybil/sybil_sensitivity_surface.csv`, column `target_device_type`). Bound on the date effect +0.0052; no cell lies in [0.6448, 0.65) (`spurious_dates_results_scan.csv`) |
| 639 | Drift: 69 of 162 pairs | Includes the three affected types (`results/drift/*`); no cell near θ found by the scan |

## 1. Per-type assumption, in counts (lines 172 and 408)

**1a. Line 172.** Current text (last two sentences):
> Admission further assumes that malicious contributors control at most a fraction $f_s$ of the eligible reporting population for a device type (Sec.~\ref{sec:scoring}). Identity-inflation tests deliberately exceed this bound.

Proposed text:
> Admission further assumes that, for every device type, colluding malicious members make up at most a fraction $f_s=0.30$ of the sites contributing evidence for that type, and that membership governance verifies which device types each member operates; the prototype does not implement this check (Sec.~\ref{sec:scoring}). Identity-inflation tests deliberately exceed this bound.

- Rationale: in the code $ES_d$ is self-declared, so the share must be enforced by verifying which types a member operates.
- Support: REPORT §2 (H2: `services.py:71-121`, `dib.py:198`); §7 (H2 variant admitted at $k=8$, $h=10$ on 25/25 types, `worst_case_real_summary.csv`).

**1b. Line 408.** Current text:
> At $\theta=0.65$ and $f_s=0.30$ this requires $\alpha>0.5$. Choosing $\alpha=0.6$ gives an upper bound of 0.58 and rejects adversary-only evidence for raw-breadth shares below $5/12$. Sec.~\ref{sec:sensitivity-results} evaluates coverage at alternative parameters.

Proposed text:
> At $\theta=0.65$ and $f_s=0.30$ this requires $\alpha>0.5$. Choosing $\alpha=0.6$ gives an upper bound of 0.58 and rejects adversary-only evidence for raw-breadth shares below $5/12$. The guarantee holds per device type. The bound is a supremum that is never attained while at least one honest site observes $d$, so an exact share of $5/12$ is still rejected. In counts, $k_d$ colluders are tolerated only if $k_d<5h_d/7$ for $h_d$ honest observers, that is, $h_d>7k_d/5$ at the analytical limit and $h_d\ge 7k_d/3$ at the declared budget (for $k_d=3$: at least five and at least seven honest sites, respectively). With two or three sources, the quorum $m=2$, not the score, rejects single-source facts. Sec.~\ref{sec:sensitivity-results} evaluates coverage at alternative parameters.

- Rationale: the guarantee is per type and depends on the honest count, not on $N$.
- Support: REPORT §0 (tolerance table, `test_followup.py::test_p0_1/2`); §3 (`kmax_by_N.csv`); §0.3(b) (cold start, `moniotr_cross_lab.py:372`, `test_p0_5`); §7 (exact-tie case BlipCare, $h=7$, $k=5$, not admitted).

## 2. Line 631: two regimes for the A2 maximum at $f_s=0.30$

Current text (third sentence):
> At $f_s=0.30$, the largest score passing quorum is 0.562 over 120 days, still below $\theta$ and consistent with the analytical bound of 0.58.

Proposed text:
> At $f_s=0.30$, a fabrication sustained for 120 days at one report per day reaches 0.562 under trust-weighted breadth. A worst-case adversary that reports on every active day of the device type and supplies up to 100 times its honest volume reaches 0.579 under raw breadth, just below the analytical bound of 0.58. That bound is a supremum and is never attained.

- Rationale: 0.562 is the maximum of the tested strategy, not of the threat model; it was computed with trust weighting, whereas Criterion 1 bounds raw breadth.
- Support: `results/masquerade/service_masquerade.csv` (0.561679; `manifest.json:45` trust_weighted=true); REPORT §7 (`worst_case_real_summary.csv`: insider k_fs, $|ES_d|=10$, max 0.578838, gap 0.0012).

Also on line 631, the first sentence "this counterfactual and the bounded-A2 tests share a maximum score of 0.354": both values are trust-weighted (0.353815 and 0.354385). Under raw breadth the bounded-A2 maximum at $k=3$ is 0.353 (`a2_raw_k_summary.csv`); the raw-breadth masquerade value is **to be computed**. Proposed: keep 0.354 and append "(trust-weighted breadth)", or replace it with the raw values once computed.

## 3. Sec. VI-E (line 627 and following): A2 in raw breadth, explicit $k$, low-coverage types declared

Current text (end of line 627):
> … and A2 across 20 seeds and malicious-site fractions $\{.05,.1,.2,.3,.4,.5\}$, realized by uniformly sampling the rounded pseudo-site count.

Proposed text (choose one sampling model; see REPORT §12):
> … and bounded A2 with $k\in\{1,\dots,5\}$ malicious pseudo-sites ($f_s=k/10$) over 20 seeds, single-shot fabrication and raw breadth.

Then add one of the following paragraphs.

**Variant U (uniform over all ten sites, as in the original run):**
> Malicious sites are drawn uniformly among all ten pseudo-sites. For the 25 device types observed at every site, the highest fabricated-fact score is $0.317\pm0.022$ (maximum $0.353$) at $k=3$ and $0.474\pm0.034$ (maximum $0.532$) at $k=5$, and no fabricated fact is admitted. Two types are observed at fewer sites, so their effective share differs from $k/10$. NetatmoWeatherStation (two sites) is admitted whenever both of its sites are drawn: 3 of 20 seeds at $k=3$ (expected $8/120$), 8 of 20 at $k=5$. BlipCareBPMeter (four to eight sites) is never admitted under single-shot fabrication. Both cases have effective share 1.0 or lie outside the assumption.

**Variant E (drawn within each type's eligible population):**
> Malicious sites are drawn within each device type's eligible population, so the effective share is $\min(k,|ES_d|)/|ES_d|$. For the 25 device types observed at every site, the highest fabricated-fact score is $0.317\pm0.022$ (maximum $0.353$) at $k=3$ and $0.474\pm0.034$ (maximum $0.532$) at $k=5$, and no fabricated fact is admitted. NetatmoWeatherStation (two sites) reaches share 1.0 for every $k\ge2$ and is admitted in all 20 seeds (score 0.94). BlipCareBPMeter (four to eight sites) is admitted in 2 and 11 of 20 seeds at $k=4$ and $k=5$, always with an effective share of at least 0.8. Neither case contradicts the bound.

- Rationale: the rounded fraction $f=0.05$ realises 0 adversaries (`poisoning.py:24`). The low-coverage types were excluded silently in the original run. Criterion 1 bounds raw breadth.
- Support:
  - REPORT §6 (`a2_raw_k_summary.csv`, `a2_raw_k_low_coverage.csv`);
  - REPORT §12 (`netatmo_sampling_table.csv`; the uniform model reproduces seeds 1, 6, 13 of the original run);
  - the uniform model's full-coverage maxima are not separately computed. The values above come from the within-$ES_d$ draw, which equals the uniform draw for full-coverage types only in distribution, not seed by seed (**to be computed** if Variant U is chosen and per-seed values are needed).

## 4. Sentence after Eq. (ct) (line 389)

Current text:
> The 0.7/0.3 split weights day coverage above the pooled volume, reducing the influence of high traffic volume from a single reporter.

Proposed text:
> The 0.7/0.3 split weights day coverage above the pooled volume. Counts are pooled without per-site normalization, so a single reporter can supply the whole volume term (at most $0.3\beta=0.12$ of the score) and, by reporting on every active day, the whole day-coverage term; Criterion 1 therefore bounds $C_t$ only by one.

- Rationale: there is no per-site cap (`dib.py:278`, `:204`, `:277`).
- Support: REPORT §2 (H1, `test_h1_*`); §7 (worst case reaches the bound to within 0.0012).

## 5. $\neg openDispute$ (after Eq. (admitauto), lines 362-370)

Current text (line 371, after the equation):
> Passing permits staging, not export, and does not override existing local decisions (Sec.~\ref{subsec:endpoint-facts}).

Proposed text (prepend one sentence):
> In the prototype, the scorer evaluates eligibility, quorum, and threshold, and the registry enforces $\neg openDispute$ by staging a fact only while its consortium status is active. Passing permits staging, not export, and does not override existing local decisions (Sec.~\ref{subsec:endpoint-facts}).

- Rationale: `DIBScorer` never passes `open_dispute` (`dib.py:297-303`); `query_score` requires `STATUS_ACTIVE` (`services.py:439`).
- Support: REPORT §2 (H6a, `test_h6a_*`).

## 6. Line 177: typo

Current text:
> … A1 tests -----.A2 tests invented reports; A3 tests the ambiguity of observed behavior.

Proposed text:
> … A1 tests real malicious observations from honest sites; A2 tests invented reports; A3 tests the ambiguity of observed behavior.

- Rationale: incomplete sentence and missing space. [?] The A1 wording is my proposal, derived from the definition earlier in the same line; confirm the intended phrasing.

## 7. (OPTIONAL, discussion only, not a design change) per-site cap

Proposed sentence for Sec. VII (Discussion), if desired:
> A per-site cap on the counts entering $n_{d,e}$ would remove most of a single reporter's volume contribution. With at most one counted row per site and fact, the tolerated share rises from $5/12$ to about $0.514$ in the worst case over data, and on the UNSW partition no admitted fact is lost. Day coverage, which carries $0.7\beta$, is unaffected, so the bound keeps its form. We leave this option unevaluated in deployment.

- Rationale: the option was evaluated, not recommended.
- Support: REPORT §8 (`mitigation_tau.csv`: 0.5139 at c=1; `mitigation_recall_cost.csv`: 0 lost, +1 gained for c ≤ 100).
