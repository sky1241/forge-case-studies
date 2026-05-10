# Pre-registered metrics — Phase 0.7

**Date pré-enregistrement** : 2026-05-10
**Référence brief** : Phase 0.7 (Sky cycle 11)

---

## Métriques par cas

Pour chaque cas du panel (train + hold-out), forge --carmack produit un classement de N fichiers. On mesure la position du `change_file` du bug.

### Variables mesurées

| Variable | Définition | Type |
|---|---|---|
| `rank_carmack` | position du change_file dans la sortie `forge --carmack` (1 = top) | int |
| `rank_predict` | position dans `forge --predict` (baseline churn-only) | int |
| `rank_locate` | position dans `forge --locate` si tests dispo (Ochiai SBFL) | int ou null |
| `total_files` | total fichiers scorés par forge | int |
| `norm_rank` | `rank_carmack / total_files` | float ∈ [0, 1] |
| `reciprocal` | `1 / rank_carmack` | float |
| `dcg_at_10` | `1 / log2(rank_carmack + 1)` si rank ≤ 10 sinon 0 | float |
| `random_baseline_rank` | `random.randint(1, total_files)` avec `random.seed(hash(bug_id))` | int |

### Indicateurs binaires (top-K)

Pour K ∈ {3, 5, 10, 30} :
- `in_top_K_carmack` : 1 si rank_carmack ≤ K, 0 sinon
- `in_top_K_predict` : pour comparaison
- `in_top_K_random` : pour comparaison

---

## Métriques agrégées (panel entier)

### Précision @ K

Pour K ∈ {3, 5, 10, 30} :
- `precision_at_K = sum(in_top_K_carmack) / 9`
- pareil pour predict, locate, random

### MRR (Mean Reciprocal Rank)

`MRR = mean([1 / rank_carmack for r in panel])`

### nDCG@10

`nDCG_at_10 = mean([dcg_at_10 for r in panel])`

### Statistical tests

#### Wilson 95% CI sur precision@10

Formule (Wilson 1927, robuste à petit N) :
```python
def wilson_ci(k, n, alpha=0.05):
    """k successes out of n. Returns (lower, upper)."""
    from math import sqrt
    z = 1.959963984540054  # z_{1-alpha/2} for alpha=0.05
    p_hat = k / n
    denom = 1 + z**2 / n
    center = p_hat + z**2 / (2 * n)
    margin = z * sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))
    lower = (center - margin) / denom
    upper = (center + margin) / denom
    return lower, upper
```

Implémentation pure Python (numpy/scipy autorisés mais formule reste impl).

#### Bootstrap 1000 resamples

Pour CI sur precision@10, MRR, nDCG@10 :
```python
import random
def bootstrap_ci(values, n_boot=1000, alpha=0.05):
    means = []
    for _ in range(n_boot):
        sample = [random.choice(values) for _ in values]
        means.append(sum(sample) / len(sample))
    means.sort()
    return means[int(n_boot * alpha/2)], means[int(n_boot * (1-alpha/2))]
```

#### Fisher exact test

Pour CRITÈRE 1 :
```python
from scipy.stats import fisher_exact

forge_top10 = sum(in_top_10_carmack)
random_top10 = sum(in_top_10_random)
table = [[forge_top10, 9 - forge_top10],
         [random_top10, 9 - random_top10]]
odds_ratio, p_value = fisher_exact(table)  # two-sided
```

scipy.stats déjà installé sur ludo-pc-1 (verified : scipy 1.16.3).

---

## Output JSONL par cas

```json
{
  "project": "<owner>/<repo>",
  "bug_id": "<id ou hash>",
  "bucket": "small|medium|large",
  "panel": "train|holdout",
  "pre_bug_commit": "<sha>",
  "buggy_commit": "<sha>",
  "bug_date": "2025-XX-XX",
  "cutoff_date": "2025-XX-XX",
  "change_file": "path/to/file.py",
  "total_files": 142,
  "rank_carmack": 5,
  "rank_predict": 12,
  "rank_locate": null,
  "random_baseline_rank": 78,
  "norm_rank": 0.0352,
  "reciprocal": 0.2,
  "dcg_at_10": 0.387,
  "in_top_3": false,
  "in_top_5": true,
  "in_top_10": true,
  "in_top_30": true,
  "q_modularity": 0.42,
  "shield_summary": null
}
```

Append à `results_train.jsonl` ou `results_holdout.jsonl`.

---

## Reproductibilité

Tous les seeds, formules, et thresholds sont gelés post-commit. Une seule run par cas (pas de re-run "pour avoir un meilleur résultat"). Si re-run nécessaire pour debug, journaliser dans `re_runs.md` avec timestamp.
