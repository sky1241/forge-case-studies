# Pre-registered criteria — cycle 17 (forge --locate à scale)

**Date** : 2026-05-11
**Branch** : cycle17 sur forge-case-studies
**Forge** : v1.3.1 main

## Hypothèse cycle 17

> "forge --locate (Ochiai SBFL) produit un ranking exploitable sur les Python bugs réels avec coverage setup actif ?"

Cycle 12 v3 baseline : 40% locate skip cause pip_install_failed. Cycle 17 mesure si on peut atteindre ≥70% success ratio avec retry/pyenv strategy.

## Critère verdict (BATTLE_PLAN ligne 127)

### C_locate

- forge --locate ranking exploitable ≥ 70% cas (rang change_file dans top 30 sur sortie locate)
- OR
- Si crash systématique > 50% → drop locate scope per BATTLE_PLAN failure mode (ligne 132)

**OUI** si : ≥ 70% cas avec ranking exploitable
**NON** si : < 70% (drop locate scope, document)

## Adaptation pragmatique pour ETA realistic

Pyenv per-case setup (BATTLE_PLAN ligne 124) demande 5-10 min × 30 cas = 2.5-5h juste pour setup. Plus pyenv install Python multi-versions (3.7/3.8/3.9/3.10) = ~30 min initial.

**Strategy cycle 17** :
1. **Phase A.1 (light)** : Try `forge --locate` avec venv forge actuel (Python 3.13) sur N=30 cas. Measure success ratio.
2. **Phase A.2 (skip pyenv)** : Si Phase A.1 success ratio < 70% (probable cause pip_install fail), document blocker pyenv requirement et drop locate scope.

Si crash > 50% → drop scope = critère failure mode triggered, FINAL_REPORT documente, cycle 17 close avec verdict "drop locate scope, pyenv per-case setup required, hors ETA cycle 17 actuel".

## Panel cycle 17

- TRAIN seed=54 : 24 cas (12 medium + 12 large)
- HOLDOUT seed=55 : 6 cas (3 medium + 3 large, disjoint train)
- Total N=30 (sky-master brief target)

## Performance panel_reference v2 (obligatoire FINAL_REPORT_v9)

20 cas FIXES re-run forge --locate. Comparison vs cycle 15 (panel_reference baseline).

## Anti-pattern

- Zero re-tirage seeds 54/55
- Zero modification critère ≥70% post-run
- Pre-registration committed AVANT runs
