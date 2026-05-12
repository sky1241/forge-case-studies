# Pre-registered criteria — cycle 23 / criteria_v15 (NO DROP investigation)

**Date** : 2026-05-12
**Branch** : cycle23 sur forge-case-studies
**Origine** : MESSAGE_TO_LUDO_PC1 cycle 23 directive sky-master

## Directive Sky stricte

**NO DROP des 6 signaux.** Sky veut COMPRENDRE pourquoi kalman zéro avant de juger.

Cycle 22B recommandation Option A (drop kalman) REJETÉE. Cycle 23 cherche :
1. Performance solo de chaque signal
2. Pourquoi kalman vide
3. Validité académique
4. Repondération évidence-based SANS drop

## 4 livrables pré-enregistrés

### 23A — `cycle23_single_signal_performance.md`

Pour CHACUN des 6 signaux SEUL (kalman, wavelet_hf, crash_prob, coupling, churn, complexity) :
- precision@10 sur 131 cases cycle 15 (train+holdout combined)
- precision@10 sur 18 cases panel_reference v2
- Rank corrélation Spearman entre score signal et rank target (was_buggy)
- Comparaison à random baseline

Critère verdict :
- Signal "useful solo" si precision@10 ≥ 2x random (≥16% > 8%)
- Signal "marginal" si 1-2x random
- Signal "useless solo" si ≤ random (~8%)

### 23B — `cycle23_kalman_diagnosis.md`

Lire `_kalman_filter` ou équivalent dans forge.py.

3 hypothèses :
- H1 — Bug d'implémentation (lecture code + comparaison Welch-Bishop 2001)
- H2 — Kalman inadapté events discrets (Poisson/Hawkes plus appropriés)
- H3 — Q/R parameters mal tunés (test sensibilité)

Critère verdict :
- Si bug impl → fix planning (mais pas implémenter en cycle 23)
- Si algo inadapté → recommandation v2.3 hypothétique (Hawkes, Poisson)
- Si params → recommandation tuning + dataset-specific

### 23C — `cycle23_academic_validity.md`

Pour chaque signal :
- Paper de référence (avec citation)
- Statut "validated for defect prediction" / "novel application" / "not in literature"
- Limites connues du signal

Critère verdict :
- Chaque signal classé selon validité scientifique

### 23D — `cycle23_reponderation_candidates.md`

Basé sur 23A single-signal performance :
- Poids candidat per signal (ALL ≥ 0.05, total sum = 1.0)
- Justification évidence-based per poids
- 3 options : conservateur (proche v1.3.0) / moyen (basé performance solo) / agressif (winner-takes-all sans drop)

## Discipline

- Pre-registration committed AVANT analyse (ce fichier sur cycle23)
- Verbatim outputs JSON + MD
- Pure stdlib Python (pas de re-run forge)
- D9 admit losses ligne 1 chaque livrable
- **NO DROP** quoi qu'il arrive (tous signaux ≥ 0.05)
- Document recommandations v2.3 hypothétiques (Hawkes, Poisson) sans implémenter

## Anti-pattern

- Pas de drop signal (sky directive)
- Pas de cherry-pick metric (precision@10 + AUC + Spearman = triangulation)
- Pas de re-calibration ML linéaire (instable cycle 22B finding)

## Reproductibilité

```
$ cd /home/sky/forge-case-studies
$ git checkout cycle23
$ git checkout origin/cycle15 -- bench_v15/ bench_v15_reference/
$ git checkout origin/cycle19_v2 -- results_v15_*.jsonl
$ python3 run_cycle23a_single_signal.py
```

- Python 3.x stdlib only
- Forge version source : 1.3.0 (cycle 15)

## Sortie attendue (4 livrables)

- cycle23_single_signal_performance.md (23A)
- cycle23_kalman_diagnosis.md (23B)
- cycle23_academic_validity.md (23C)
- cycle23_reponderation_candidates.md (23D)
- run_cycle23a_single_signal.py (orchestration 23A)
- cycle23a_results.json (raw 23A)
