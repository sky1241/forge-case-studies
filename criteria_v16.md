# Pre-registered criteria — cycle 24 / criteria_v16 (Option B + kalman fix)

**Date** : 2026-05-12
**Branch** : cycle24 sur forge-case-studies
**Origine** : MESSAGE_TO_LUDO_PC1 cycle 24 directive sky-master

## Mission cycle 24 (2 changements forge.py + 1 benchmark)

### 24A — Fix kalman extraction
- Avant : `kalman_risk = smoothed[-1]` (valeur instantanée)
- Après : `kalman_risk = max(smoothed[-4:])` (peak récent 4 dernières)
- Rationale empirique : cycle 23B finding `smoothed[-1]` reflète "calme actuel" pas "risque historique"
- Tests TDD : 3 minimums (peak récent, série courte, série vide)

### 24B — Repondération Option B (cycle 23D)
- complexity 0.30 (boost de 0.15 — cycle 23A meilleur solo 54.96%)
- crash 0.20 (unchanged)
- coupling 0.18 (+0.03)
- churn 0.14 (-0.01)
- wavelet 0.10 (-0.05)
- kalman 0.08 (-0.12, MAIS ≥0.05 per Sky directive NO DROP)
- Sum = 1.00

### 24C — Benchmark panel_reference v2
- 20 cas fixes panel_reference
- Run forge --carmack sur v2.1.0 baseline + cycle24 candidate
- Mesurer : precision@10, MRR, AUC sur panel_ref

## Critères verdict (pre-registered AVANT benchmark)

### Scenario VALIDÉ
- Delta precision@10 ≥ **+5 pts** sur panel_reference
- ET pas de régression Fisher significative (p > 0.05 contre hypothèse v2.1.0 ≥ candidate)
- → Tag v2.2.0 (24D)

### Scenario NEUTRE
- Delta precision@10 entre -2 et +5 pts
- → Garder v2.1.0 status quo (pas worth bump)

### Scenario REJECTED
- Delta precision@10 ≤ -2 pts
- → Revert changes, garder v2.1.0
- Document échec dans FINAL_REPORT_v15

## Discipline

- Pre-registration committed AVANT impl (ce fichier)
- TDD tests AVANT impl
- mypy --strict + pytest verbatim dans commit bodies
- Verbatim outputs benchmark bench_v15_panel_ref/<scenario>/<case>/
- D9 admit losses ligne 1 FINAL_REPORT_v15
- NO DROP (∀signal ≥ 0.05)
- Anti-bâclage : wall-clock < 30% ETA → warning

## Anti-pattern

- Pas de bump version v2.2.0 si NEUTRE/REJECTED
- Pas de cherry-pick métrique (precision@10 + MRR + AUC = triangulation)
- Pas de re-calibration ML linéaire (cycle 22B finding instable)

## Reproductibilité

```
$ cd /home/sky/Bureau/forge
$ git checkout cycle24_kalman_fix
$ .venv/bin/pytest tests/  # tous tests pass
$ .venv/bin/mypy --strict forge.py  # success
$ cd /home/sky/forge-case-studies
$ git checkout cycle24
$ python3 run_cycle24c_benchmark.py
```

- Python 3.13.12
- Forge version source : 2.1.0 (cycle 23 baseline) → 2.2.0-candidate (cycle 24)

## Sortie attendue

- criteria_v16.md (pre-registration, ce fichier)
- forge.py changes (kalman fix + Option B weights)
- 3+2 = 5 nouveaux tests TDD
- benchmark_cycle24/ (panel_reference 20 cas × 2 scénarios)
- FINAL_REPORT_v15.md (verdict cycle 24)
- (si VALIDÉ) tag v2.2.0
