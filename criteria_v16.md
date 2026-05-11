# Pre-registered criteria — cycle 16 v7

**Date** : 2026-05-11
**Branch** : cycle16 sur forge-case-studies
**Forge** : 1.3.1 + feat/cold_start_similarity (Jaccard AST n-grams)

## Hypothèse cycle 16

> "Le signal cold-start similarity (AST n-gram Jaccard vs historiquement-buggy files) ajouté à carmack composite **sauve les cas cold-start** ?"

Référence cycle 14 v5 baseline : cold-start subset 15.4% top10 (avec complexity signal seul).

## Critère principal (BATTLE_PLAN.md ligne 105)

**C_similarity** : signal aide cold-start ≥ +30% top10 vs cycle 14 baseline (15.4% → ≥ 45.4%)

- Mesure : run forge --carmack baseline (v1.3.1, sans similarity) vs forge --carmack + similarity (50/50 blend complexity + similarity)
- Sur N=40 cold-start train + N=10 holdout
- Calcule top10 ratio pour chaque variant

**OUI** si :
- similarity-blend top10 holdout ≥ 45% (4/10) ET
- Pas de régression panel_reference (≥ stagnation)

**NON** si :
- similarity-blend top10 < 25% OR
- Régression panel_reference ≥ 2 métriques

## Critère secondaire — comparison panel_reference v2

20 cas FIXES (panel_reference.json) re-run avec similarity-blend variant. Comparison vs cycle 15 (9/18 = 50%) :
- AMÉLIORATION si ≥ 11/18 top10
- STAGNATION si 9-10/18
- RÉGRESSION si ≤ 8/18

## Matrice décision

| Outcome | Action |
|---|---|
| C_similarity OUI ET panel_reference AMÉLIORATION/STAGNATION | Gate auto → bump v1.4.0 (cycle 16 succès) |
| C_similarity NON | Drop signal, STOP, ping Sky |
| C_similarity OUI mais panel_reference RÉGRESSION | STOP, ping Sky |

## Anti-pattern

- Zero re-tirage post-hoc des seeds 52/53
- Zero modification du critère +30% post-run
- Pre-registration committed AVANT runs
- Verbatim outputs bench_v16/results/cold-start/{bug_id}/*.txt

## Reproductibilité

- forge.py hash : feat/cold_start_similarity branch 0942e5e
- forge --version : 1.3.1 (sky1241/forge main HEAD)
- N=50 panel pre-registered seeds 52/53
- panel_reference.json v2 commun (seed=999)
