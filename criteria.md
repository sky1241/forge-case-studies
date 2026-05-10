# Pre-registered criteria — forge-case-studies cycle 11

**Date pré-enregistrement** : 2026-05-10
**Émetteur** : Sky (via brief sky-master 2026-05-10T22:54:20+02:00)
**Exécutant** : cousin pc1 (ludo-pc-1)
**Charte** : ANTI-BULLSHIT (RULE 4 verbatim, D9 admit losses, NO post-hoc cherry-pick)

Ce fichier est committé AVANT toute exécution forge sur le panel. Toute modification après commit = invalidation du test.

---

## Hypothèse à tester

> "forge --carmack prédit-il significativement mieux que le hasard la position du fichier modifié pour un bug Python réel pré-enregistré ?"

Test sur N=9 train + N=9 hold-out cases stratifiés (3 small + 3 medium + 3 large), seeds 42 et 43.

---

## Critère 1 — forge bat le hasard

**H1** : forge --carmack range les buggy_files significativement plus haut que le baseline aléatoire.

**Test statistique** : Fisher exact (mieux que Mann-Whitney à petit N=9)
- table : `(forge_in_top_10, random_in_top_10) × (yes, no)`
- p-value de scipy.stats.fisher_exact (two-sided)

**Seuil** : p < 0.05 ET hits_forge > hits_random

**Décision** :
- OUI si seuil atteint
- NON sinon

---

## Critère 2 — forge précision@10 atteint un seuil utile

**H2** : forge place le buggy_file dans le top-10 dans ≥ 50% des cas.

**Test statistique** : Wilson 95% CI sur precision@10
- precision@10 = forge_top10_count / 9
- Wilson lower / upper bound (formule standard)

**Seuil** :
- precision@10 ≥ 0.50 (point estimate)
- ET borne inférieure 95% CI ≥ 0.30 (robustness à petit N)

**Décision** :
- OUI si les 2 seuils atteints
- NON sinon

---

## Critère 3 — calibration bat l'heuristique sur HOLD-OUT

**H3** : Poids appris depuis le train set améliorent l'AUC sur un panel hold-out indépendant (jamais vu pendant training).

**Procédure** :
1. Phase B : entraîner poids (kalman, wavelet, crash, coupling, churn) sur les ~450 lignes de panel_train (9 cas × ~50 files/cas).
2. 3 méthodes en parallèle : grid search 5D, logistic regression, random forest feature importance.
3. Adopter la méthode la plus interprétable convergente.
4. Phase B.3 : appliquer les poids calibrés au panel_holdout. Mesurer AUC.
5. Comparer à AUC heuristic (poids actuels de forge 1.2.2).

**Test** : delta AUC sur hold-out
- delta = AUC_calibrated_holdout - AUC_heuristic_holdout

**Seuil** : delta ≥ 0.05 (5 points AUC)

**Décision** :
- OUI si delta ≥ 0.05
- NON si delta < 0.05 (heuristique reste — loss admis, doc honest)

---

## Matrice de décision (pré-enregistrée — NE PAS MODIFIER après run)

| Critères OUI | Verdict | Action |
|---|---|---|
| 3/3 | forge_supérieur_prouvé | release v1.3.0 + Sky peut publier |
| 2/3 | forge_partiellement_validé | patch + doc honest (pas release) |
| 1/3 | signal_faible_non_concluant | garder outil + heuristic + doc |
| 0/3 | forge_au_niveau_hasard | leçon dure, refactor majeur ou refonte approche |

---

## Limite statistique admise (D9 — à publier en ligne 2 du rapport final)

> "Test à N=9 train + N=9 hold-out. Power statistique limité par choix Sky d'un panel petit. Tests adaptés (Fisher exact, Wilson CI, bootstrap 1000) mais conclusions à confirmer sur N≥50."

Cette ligne est **obligatoire** dans FINAL_REPORT.md ligne 2.

---

## Charte D9 obligatoire

Si forge perd sur ≥ 1 critère :
- Le verdict NON apparaît en ligne 1 du rapport (pas dilué)
- Pas d'effacement, pas de re-run, pas de shift de seuil
- "Sky veut un VERDICT TRANCHÉ, pas une validation"

## Ce qui n'est PAS testé (out-of-scope explicite)

- Speed forge --carmack vs autres outils (pas la question)
- Coverage forge --locate (sera mesuré mais pas dans les 3 critères)
- Modularity Q absolue (relevé en sanity check, pas critère)
- forge --shield orchestration end-to-end (smoke test, pas critère)
- Stabilité release process (sera vu post-test si critère 3 OUI)

Une fois ce fichier committé, **les 3 critères et leurs seuils sont gelés**.
