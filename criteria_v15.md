# Pre-registered criteria — cycle 15 v6

**Date** : 2026-05-11
**Branch** : cycle15 sur forge-case-studies
**Forge version** : 1.3.0 (final, PyPI), with cold-start re-weighting v1.3.0rc2 + complexity signal

## Hypothèse

> "forge --carmack v1.3.0 prédit-il les fichiers buggés avec **C2 OUI sur scope intended** (history-rich only, E7 strict ≥3 bugfix) ?"

Cycle 14 v5 avait montré C2 OUI sur subset history-rich N=15 (53%). Cycle 15 valide à N=135 train + 34 holdout (BugsInPy E7-pool exhaustive).

## Critères verdict pré-enregistrés (BATTLE_PLAN.md ligne 21)

### C1 — Fisher exact forge bat random
- table: `[[forge_top10, n-forge_top10], [random_top10, n-random_top10]]`
- p-value scipy.stats.fisher_exact (two-sided)
- **OUI si p < 0.05 AND forge_top10 > random_top10**

### C2 — Wilson CI sur precision@10
- p@10 = forge_top10 / n
- Wilson 95% CI lower bound
- **OUI si p@10 ≥ 0.50 AND lower bound ≥ 0.30**

### C3 — Calibration bat heuristic
- Phase B: calibrate 6 weights on TRAIN dataset (~6000 rows)
- Test sur HOLDOUT N=34
- delta = AUC_calibrated_holdout - AUC_heuristic_holdout
- **OUI si delta ≥ 0.05**

## Matrice décision (BATTLE_PLAN.md ligne 60)

| Score | Action |
|---|---|
| 3/3 OUI | tag v1.4.0 (gate auto, PAS PyPI) |
| 2/3 OUI | STAY rc, ping Sky |
| 1/3 OUI | STAY rc, ping Sky |
| 0/3 OUI | STAY rc, ping Sky |

## Friction acceptée — N=169 < N=500 brief

BugsInPy E7-pool exhaustive = 169 bugs (out of 502 BugsInPy total, 233 E1-E6 eligible). Fallback gh search hors scope cycle 15 light (multi-jour clone + E1-E7 verification par candidat). **Cycle 15 documented as 'BugsInPy-only N=169'** rather than N=500 brief target.

Power statistique reste suffisante :
- Fisher exact à N=135 train : peut détecter effects modérés (forge ratio top10 >25% vs random ~10% → p<<0.05)
- Wilson CI à N=135 : margin ~±8 pts on p@10
- AUC calibration à ~6000 rows dataset : robust calibration ML

## Anti-pattern (BATTLE_PLAN.md ligne 27)

- Zero re-tirage post-hoc des seeds 50/51
- Zero modification des critères post-run
- Zero cherry-pick des skips
- Pre-registration committed AVANT runs

## Performance sur panel_reference v2 (obligatoire FINAL_REPORT v6, BATTLE_PLAN.md ligne 42)

20 cas FIXES (panel_reference.json v2, seed=999, max 2/projet) — run forge --carmack v1.3.0 + report :
- precision@10 panel_reference vs cycle 14
- AUC panel_reference vs cycle 14
- Verdict AMÉLIORATION / STAGNATION / RÉGRESSION

Si RÉGRESSION sur ≥ 2 métriques → STOP cycle 16, ping Sky.

## Reproductibilité

- forge.py git hash : à capturer au moment du run
- forge --version : `forge-shield 1.3.0`
- pre-registration commit : ce fichier + eligibility_v15.md + panel files committed BEFORE Phase A
