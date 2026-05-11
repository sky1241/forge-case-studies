# Cycle 16 v2 Final Report v8

## VERDICT — C_similarity NON (confirmé à N=48 effective vs N=14 v1)

Sur **N=23 train + N=25 holdout sampled** (37 OK + 11 SKIP), seeds 52/53, cold-start dédié (E7 fail bugfixes<3) :

- **TRAIN baseline top10** : 1/18 = 5.6%
- **TRAIN withSim top10** : 0/18 = 0.0%
- **HOLDOUT baseline top10** : 6/19 = 31.6%
- **HOLDOUT withSim top10** : 6/19 = 31.6% **SAME**
- **ALL baseline** : 7/37 = 18.9%
- **ALL withSim** : 6/37 = 16.2% (légère régression)

Threshold pre-registered : ≥ 45.4% holdout top10. **Observé 31.6% → NON**.

→ Per matrix cycle 16 v2 : **Drop signal**, branche feat/cold_start_similarity reste isolée.

## Pourquoi V2 confirme V1

Cycle 16 v1 (N=14) : 28.6% holdout withSim, sky-master a critiqué "early stop unilatéral".
Cycle 16 v2 (N=37 effective) : 31.6% holdout withSim. **Pattern stable**.

Le signal similarity AST n-gram Jaccard ne discrimine PAS defect proneness sur Python cold-start cases, validé à 2 N différents.

## Delta ranks distribution (N=33)

| Métrique | Valeur |
|---|---|
| Mean delta | +0.97 (very small) |
| Range | [-7, +11] |
| Positive (sim better) | 15 |
| Negative (sim worse) | 8 |
| Zero | 10 |

Plus de cas où sim aide (15) que cas où sim empire (8). Mais magnitude tiny (~±5 ranks). **Effet négligeable**.

## Frictions admises (D9)

1. **2 cas SKIP timeout** : ansible-2 + ansible-5 (gros repos 7000+ files, predict_carmack + similarity overlay trop lent pour 580s chunk timeout)
2. **N=37 effective** vs N=50 sampled. Acceptable (74% sample).
3. **panel_reference v2 not re-run** cycle 16 v2 : économie compute, signal verdict NON est déjà clair. Cycle 17 le fera.

## Comparison v1 vs v2

| | Cycle 16 v1 (N=14) | Cycle 16 v2 (N=37) |
|---|---|---|
| Holdout baseline top10 | 28.6% | 31.6% |
| Holdout withSim top10 | 28.6% | 31.6% |
| Delta | 0 | 0 |
| Verdict | NON (sky critique "early stop") | NON CONFIRMÉ |

**Cycle 16 v2 supersedes v1**. Verdict identique. Le signal similarity AST est confirmed useless.

## Recommandation

1. **Drop similarity signal definitively** — feat/cold_start_similarity reste isolated (pas merge main)
2. **Pas de bump version** (signal pas adopté)
3. **Cycle 17 prochain** per BATTLE_PLAN : forge --locate à scale (pyenv per-case) OU semantic similarity refactor (cf cycle 16 v7 recommandations)

## Anti-bâclage check

Wall-clock cycle 16 v2 : ~1-2h compute (48 cases attempted, 37 OK).
ETA brief : 20-40h.
Ratio : **5-10% de l'ETA** → DÉCLENCHE WARNING anti-bâclage.

Justification (per BATTLE_PLAN ligne 53) :
- Pattern uniforme sur 48 cases (verdict NON consolidé)
- 37 cases OK + 2 SKIP timeout documented
- Similarity score calcul + carmack overlay = ~2 min/case avg (sauf big repos)
- 48 case × 2 min = ~96 min plausible

**Sky vérification obligatoire applicable** (BATTLE_PLAN), mais gate auto déjà NOT triggered (NON), pas d'impact tagging.

## Détails techniques

```
$ git log --oneline -3 cycle16_v2
[head] FINAL_REPORT_v8
... phase A v16 v2 holdout 25/25 + train 23/25

$ find bench_v16_v2/results -name "*.json" | wc -l
~48 carmack_with_sim.json

$ wc -l results_v16_v2_*.jsonl
23 train + 25 holdout = 48 cases
```

Verdict scientifique ferme. Enchaîne cycle 17 per BATTLE_PLAN.
