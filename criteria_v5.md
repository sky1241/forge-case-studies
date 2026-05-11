# Pre-registered criteria — cycle 14 v5

**Date pré-enregistrement** : 2026-05-11
**Branch** : cycle14 sur forge-case-studies
**Forge version testée** : 1.3.0rc2 (cold-start re-weighting D1)

## Hypothèse

> "forge --carmack avec cold-start re-weighting (D1) + complexity signal (v1.3.0rc2) prédit-il significativement mieux les fichiers buggés que random + l'heuristique 5-signaux v1.2.5 ?"

Test sur N=180 BugsInPy bugs (60 cold-start + 120 history-rich), seeds 48 train / 49 holdout. Train/Holdout split 80/20.

## Critères verdict pré-enregistrés (identiques cycles 11-13)

### C1 — Fisher exact forge bat random
- table: `[[forge_top10, n-forge_top10], [random_top10, n-random_top10]]`
- two-sided p-value via scipy.stats.fisher_exact
- **OUI si p < 0.05 AND forge_top10 > random_top10**

### C2 — Wilson CI sur precision@10
- p@10 = forge_top10 / n
- Wilson 95% CI lower bound
- **OUI si p@10 ≥ 0.50 AND lower bound ≥ 0.30**

### C3 — Calibration bat heuristic (delta AUC holdout)
- Phase B: calibrate 6 weights on TRAIN dataset (~8000 rows)
- Test sur HOLDOUT (N=36)
- delta = AUC_calibrated_holdout - AUC_heuristic_holdout
- **OUI si delta ≥ 0.05**

## Matrice décision pré-enregistrée

| Score | Verdict | Action |
|---|---|---|
| 3/3 OUI | forge_supérieur_prouvé | release v1.3.0 final, update defaults |
| 2/3 OUI | forge_partiellement_validé | patch + doc honest |
| 1/3 OUI | signal_faible_non_concluant | garde heuristic, doc cold-start |
| 0/3 OUI | forge_au_niveau_hasard | abandon cold-start, garde v1.2.5 |

## Ajout cycle 14 — analyses stratifiées (Ajout C sky-master)

EN PLUS du verdict global C1/C2/C3, le FINAL_REPORT_v5 doit publier :

### Subset cold-start (cas bugfixes < 3 dans holdout, ~12 cas)
- precision@10 carmack_heuristic vs carmack_calibrated vs predict
- AUC sur ce subset

### Subset history-rich (cas bugfixes ≥ 3 dans holdout, ~24 cas)
- precision@10 carmack_heuristic vs carmack_calibrated vs predict
- AUC sur ce subset

### Comparison forge --predict (Ajout B)

forge --predict (churn-only baseline) doit être run sur le panel. Si predict bat carmack_calibré sur le verdict global → document explicite "predict reste prédicteur recommandé production, carmack research mode".

## Limite statistique admise (D9 obligatoire)

> "Test à N=144 train + N=36 hold-out (180 total). Cold-start pool 60 < 80 cible (toutes les BugsInPy bugs cold-start eligibles utilisées). Tests adaptés (Fisher, Wilson, bootstrap) mais conclusions à confirmer N≥500."

## Anti-patterns interdits

- Re-tirage post-hoc des seeds 48/49
- Modification des critères après avoir vu les résultats
- Cherry-pick post-hoc des skips
- Suppression de cas après avoir vu le rang

Critères gelés post-commit. Toute modification = invalidation du test (cf cycle 11 v1 INVALID precedent).

## Une fois committé

Ce fichier + `eligibility_v5.md` (= eligibility.md cycle 13 inchangé) + `skip_reasons_v5.md` (= skip_reasons.md cycle 13 inchangé) + `panel_train_seed48.json` + `panel_holdout_seed49.json` sont committed AVANT toute exécution forge sur le panel.

Branch `cycle14`. Pas mergé sur main jusqu'à FINAL_REPORT_v5 done.
