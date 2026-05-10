# forge-case-studies — cycle 11

> **⚠️ STATUS : v1 INVALID — cycle 11 v2 in progress (2026-05-11)**
>
> The first run (commits `126ced7` → `ed0c950`, including FINAL_REPORT
> verdict 0/3 OUI) was reverted by sky-master after audit. Reasons:
> Phase A wall-clock too short for "forge full power" claim,
> bucket small fallback not exhausted, luigi×3 bias accepted,
> N=5 calibration overfit. Verdict not on forge — on the bâclage.
>
> Cycle 11 v2 with proper exhaustive sampling + all 6 forge sub-commands
> per case is in progress. ETA 12-30h wall-clock.
>
> **DO NOT cite the FINAL_REPORT v1 results.**

Honest scientific test of `forge --carmack` (https://github.com/sky1241/forge) on real-world Python bugs.

> "forge --carmack predicts files likely to contain bugs based on multi-signal scoring (Kalman + wavelet + crash + coupling + churn).
> Does it actually beat random baseline on real Python bugs from public repos?"

## Pre-registered

This test is **pre-registered** before any forge execution. Criteria, eligibility, panels, seeds are committed BEFORE measurements. No post-hoc cherry-picking. No threshold shifting. No silent skip reasons.

| Doc | Purpose |
|---|---|
| [criteria.md](criteria.md) | 3 hypotheses + thresholds + decision matrix (frozen post-commit) |
| [eligibility.md](eligibility.md) | E1-E6 criteria for repos to enter the population |
| [skip_reasons.md](skip_reasons.md) | 8 closed reasons to skip a case (anti cherry-pick) |
| [temporal_rules.md](temporal_rules.md) | Anti-data-leakage cutoff procedure |
| [metrics.md](metrics.md) | Variables + statistical tests (Fisher, Wilson CI, bootstrap) |
| [phase0_compat_check.md](phase0_compat_check.md) | Forge subcmds availability + flags compat verdict |

## The 3 criteria (verdict on each → 0/3, 1/3, 2/3, or 3/3)

1. **Forge beats random** — Fisher exact `p < 0.05` on `forge_top_10 vs random_top_10`
2. **Precision@10 ≥ 0.50** with Wilson 95% CI lower bound ≥ 0.30
3. **Calibration beats heuristic on hold-out** — `delta AUC ≥ 0.05`

## Decision matrix (pre-registered)

| Outcome | Verdict |
|---|---|
| 3/3 | forge_supérieur_prouvé → release v1.3.0 |
| 2/3 | forge_partiellement_validé → patch + doc honest |
| 1/3 | signal_faible_non_concluant |
| 0/3 | forge_au_niveau_hasard → refactor |

## Statistical caveat (D9 obligatory line 2 of FINAL_REPORT.md)

Test on N=9 train + N=9 hold-out. Statistical power is limited by Sky's choice of a small panel. Tests adapted for small N (Fisher exact, Wilson CI, bootstrap 1000) but conclusions to confirm on N≥50.

## Status

Phase 0 — pre-registration in progress.
- ✅ Phase 0.1 — Forge compat check
- ✅ Phase 0.2 — Eligibility criteria
- ✅ Phase 0.5 — Skip reasons (closed list)
- ✅ Phase 0.6 — Temporal rules (anti-leakage)
- ✅ Phase 0.7 — Metrics
- 🔄 Phase 0.3 — Panel sampling (BugsInPy or fallback gh search) **— NEXT**
- ⏳ Phase 0.4 — Domain diversity sanity check
- ⏳ Phase A — Case studies + forge full power
- ⏳ Phase B — Calibration
- ⏳ Phase C — Iteration (optional)

## Reproduce

```bash
git clone https://github.com/sky1241/forge-case-studies
cd forge-case-studies
bash run_all.sh  # to be added once Phase A complete
```
