# Pre-registered criteria — cycle 16 v2

**Date** : 2026-05-11
**Branch** : cycle16_v2 sur forge-case-studies
**Forge** : v1.3.1 main + feat/cold_start_similarity (commit 0942e5e)

## Hypothèse cycle 16 v2

> "Le signal cold-start similarity (AST n-gram Jaccard) ajouté au composite carmack via blend 0.5*complexity + 0.5*similarity dans la slot 'complexity' weight sauve les cold-start cases ?"

Référence cycle 14 v5 cold-start subset baseline : 15.4% top10.

Cycle 16 v1 interrompu N=14 (early stop). **Cycle 16 v2 = run propre N=50 sans early stopping** (rails BATTLE_PLAN renforcé).

## Critère verdict (BATTLE_PLAN ligne 105)

### C_similarity_v2 (panel complet N=25 holdout)

- forge --carmack baseline (sans blend) vs withSim (avec blend)
- HOLDOUT N=25 cold-start cases
- Mesure : delta top10 ratio

**OUI** si :
- WithSim top10 holdout ≥ 45.4% (cycle 14 baseline 15.4% + 30 pts)
- ET pas de régression panel_reference v2 (≥ stagnation, ≥ 9/18 top10)

**NON** si :
- WithSim top10 holdout < 25% OR
- Régression panel_reference ≥ 2 métriques (delta < cycle 15)

### Matrix décision

| Outcome | Action |
|---|---|
| C_similarity OUI ET panel_reference ≥ stagnation | Gate auto → bump v1.4.0 (cycle 16 succès) |
| C_similarity NON | Drop signal, refactor cycle 17 ou abandon |
| C_similarity OUI mais panel_reference régression | STOP ping Sky |

## Anti-pattern

- **Zero re-tirage post-hoc** des seeds 52/53
- **Zero modification du critère** +30% post-run
- **Zero early stopping unilateral** (cycle 16 v1 leçon)
- Pre-registration committed AVANT runs

## Performance sur panel_reference v2 (obligatoire FINAL_REPORT_v8)

20 cas FIXES panel_reference.json (seed=999) run avec withSim variant. Comparison vs cycle 15 (9/18 = 50.0% baseline).

## Reproductibilité

- forge.py : sky1241/forge v1.3.1 main + feat/cold_start_similarity branch (0942e5e)
- forge --version : 1.3.1
- Panel committed seeds 52/53 (cycle 16 v2)
- panel_reference v2 (seed=999) re-run pour comparison
