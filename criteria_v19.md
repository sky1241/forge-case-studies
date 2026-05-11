# Pre-registered criteria — cycle 19 (ablation drop kalman + wavelet)

**Date** : 2026-05-11
**Branch** : cycle19 sur forge-case-studies

## Hypothèse cycle 19

> "Si on drop kalman + wavelet du composite carmack (4 signaux : crash + coupling + churn + complexity), performance maintenue à ±2% sur panel_reference ?"

## Critère verdict (BATTLE_PLAN ligne 153)

### C_ablation

- precision@10 sur panel_reference avec composite minimal (4 sig) vs baseline (6 sig)
- Delta < ±2 pts top10

**OUI** : maintien performance → simplifier carmack defaults
**NON** : chute > 2 pts → garder 6 signaux

## Procédure

Réutilise cycle 15 carmack_full.json data (déjà computed, signal values stored per file).

Re-compose composite scores avec :
- Baseline (6 sig) : kalman 0.20 + wavelet 0.15 + crash 0.20 + coupling 0.15 + churn 0.15 + complexity 0.15 (sum 1.0)
- Minimal (4 sig) : crash + coupling + churn + complexity, weights renormalized (drop kalman 0.20 + wavelet 0.15 = 0.35 redistributed)
  → crash 0.31, coupling 0.23, churn 0.23, complexity 0.23

Compare top10 ratio sur cycle 15 panel (135 train + 34 holdout) + panel_reference (20 cas constants).

## Anti-pattern

- Réutilise cycle 15 data (pas re-run forge)
- Zero modification critère ±2% post-run
- Pre-registration AVANT comparison

## Reproductibilité

- Source : bench_v15/results/{bucket}/{bug_id}/carmack_full.json (149 files)
- Source : bench_v15_reference/results/{bucket}/{bug_id}/carmack_full.json (20 files)
- Forge version reference : 1.3.0 (cycle 15)
