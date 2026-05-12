# Pre-registered criteria — cycle 22B / criteria_v14 (analyse kalman + wavelet utilité)

**Date** : 2026-05-12
**Branch** : cycle22 sur forge-case-studies
**Origine** : MESSAGE_TO_LUDO_PC1 cycle 22B directive sky-master

## Mystère à résoudre

Cycle 14 calibration ML (N=141) :
- kalman 0.033 (3.3%)
- wavelet 0.019 (1.9%)
- → "presque rien" en calibration linéaire

Cycle 19 v2 ablation (drop kalman + wavelet) :
- cycle 15 train+holdout N=131 : ablation +2.3 pts
- panel_reference v2 N=18 : ablation **-16.7 pts**

→ Calibration ML dit "inutiles", ablation panel dit "très utiles". **Pourquoi ?**

## 4 hypothèses pré-enregistrées

### H1 — Long tail signal
Kalman + Wavelet à 0 sur 90% cas, contribuent fortement sur 10% restants (bursts récents).
- Calibration linéaire ne capture pas pattern bimodal
- Test : distribution scores kalman/wavelet sur 149 fichiers cycle 15
  - médiane / moyenne / % à zéro
  - per (was_buggy=1 vs was_buggy=0)

### H2 — Panel_reference v2 biaisé
20 cas stratifiés peut-être contiennent disproportion de cas où kalman/wavelet flippent rank borderline.
- Test : sur 18 cas OK panel_ref, identifier fichiers où rank change avec ablation
- Cas frontière : was top10 baseline → out top10 ablation (perdu) OU was out top10 baseline → in top10 ablation (gagné)

### H3 — Hétérogénéité per-projet
Cycle 19 v2 a montré : cookiecutter/fastapi/luigi/tornado favorisent ablation. ansible/scrapy/httpie favorisent baseline.
- Test : per-projet, distribution kalman/wavelet contributions
- Pour projets où ablation NUIT : qu'est-ce qui distingue leur signal ?

### H4 — Composite weights mal calibrés
Cycle 14 v5 (N=141) vs cycle 15 v6 (N=131) :
- Kalman : 3.3% → 16% (5x variation)
- Wavelet : 1.9% → 0.4% (5x variation)
- → Calibration linéaire instable. Pas signal réel cohérent.

## Critères verdict cycle 22B

### Scenario A — kalman/wavelet INUTILES (drop défendable)
- Distribution unimodal (pas long-tail)
- % à zéro < 50% sur all files
- Pas de cas frontière panel_ref imputable à kalman/wavelet
- Per-projet : pas de pattern clair

### Scenario B — kalman/wavelet UTILES mais long-tail
- % à zéro > 70%
- Median ~0 mais valeurs distincts pour 10-20% des fichiers
- Cas frontière panel_ref dépendent fortement de ces signaux
- Recommandation : keep mais documenter scope-specific

### Scenario C — calibration instable, signal réel mais petit
- Variation cross-cycle kalman/wavelet > 3x
- Effet additif marginal mais cohérent direction
- Recommandation : keep avec pondération révisée + documenter incertitude

### Scenario D — AMBIGU (4 patterns mixtes)
- Pas de scenario A/B/C net
- Recommandation : keep par conservatisme, plus de cycles nécessaires

## Procédure

Pure Python stdlib (pas de re-run forge) sur :
- bench_v15/results/{bucket}/{bug_id}/carmack_full.json (131 cas)
- bench_v15_reference/results/{bucket}/{bug_id}/carmack_full.json (18 cas)
- results_v15_*.jsonl (status filter)

Computes :
1. Distribution histograms scores kalman/wavelet
2. Per-case rank delta baseline vs ablation
3. Per-projet bucketing
4. Cas frontière (rank baseline ≤10 vs rank ablation >10 et inversement)

## Anti-pattern

- Pas de cherry-pick (cycle 19 v1 erreur)
- 4 dimensions analyse en parallèle
- Recommandation chiffrée (% à zéro, médiane, etc.)
- Pre-registration committed AVANT analyse

## Reproductibilité

```
$ cd /home/sky/forge-case-studies
$ git checkout cycle22
$ git checkout origin/cycle15 -- bench_v15/ bench_v15_reference/
$ python3 run_cycle22b_kalman_wavelet_analysis.py
```

- Python : 3.x stdlib only
- Forge version source : 1.3.0 (cycle 15)

## Sortie attendue

- cycle22_algo_analysis.md (livrable principal)
- cycle22b_distributions.json (raw histograms)
- cycle22b_per_project.json
- cycle22b_borderline_cases.json
