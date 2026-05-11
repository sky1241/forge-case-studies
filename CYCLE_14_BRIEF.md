# Cycle 14 Brief — N≥200 + cold-start complexity validation

**Status** : Brief prepared. **NOT YET EXECUTED.** Awaits explicit Sky GO.

## Mission

Test if `forge --carmack` with the new **cold-start complexity signal** (v1.3.0rc1, McCabe + Halstead + nesting, cf cycle 14 feat branch) beats:
- `forge --carmack` v1.2.5 (5-signal heuristic without complexity)
- `forge --predict` (churn-only baseline that beat carmack in cycle 13 v4 : 64% vs 28%)

If cycle 14 validates → v1.3.0 final release (drop the `rc1` suffix).
If cycle 14 fails → v1.3.0rc1 stays rc1 forever, no v1.3.0 release.

## Spec différences vs cycle 13 v4

| Aspect | Cycle 13 v4 | **Cycle 14** |
|---|---|---|
| N target | 50 (25+25) | **200 (160 train + 40 holdout)** |
| Seeds | 46/47 | **48 train / 49 holdout** |
| E7 filter | yes (≥3 bugfix on change_file) | yes (same) |
| Forge version | 1.2.4 (5 signals) | **1.3.0rc1 (6 signals + complexity)** |
| Bench scope | E7-filtered only | **E7-filtered + COLD-START sample** (50 cases with 0 prior bugfix on change_file, to specifically test cold-start signal) |
| Compute estimated | ~2-3h | **50-150h wall-clock** (xargs -P 3) |

## Stratification N=200

| Bucket | Train | Holdout |
|---|---|---|
| small | 0-3 (if fallback works) | 0-3 |
| medium | 50-60 | 12-15 |
| large | 100-110 | 25-30 |
| **cold-start (NEW)** | **40-50 cases with 0 bugfix on change_file** | **10-15** |
| **Total target** | **~160** | **~40** |

The cold-start subset is **crucial**: tests if the new complexity signal
covers the blind spot. Without dedicated cold-start cases, cycle 14
would have the same E7-filter bias as cycle 13.

## Critères verdict cycle 14

Same as cycles 11-13 (pre-registered, NOT modified):

1. **C1 Fisher exact** : p < 0.05 forge_top10 vs random_top10
2. **C2 Wilson CI** : precision@10 ≥ 0.50 AND lower bound ≥ 0.30
3. **C3 delta AUC holdout** : ≥ +0.05 over heuristic

Plus 2 supplementary findings to validate :

4. **C4 cold-start signal effective** : on the cold-start subset, forge --carmack v1.3.0rc1 top10 ≥ 30% (vs cycle 12 v3 ≈ 5% on similar cases)
5. **C5 carmack beats predict** : forge --carmack top10 ≥ forge --predict top10 (cycle 13 v4 was reversed : predict 64% bat carmack 28%)

Score expected if v1.3.0rc1 marches :
- C1 OUI (more N = more power)
- C2 OUI possible (Wilson CI tightens at N=160)
- C3 NON probable (ML calibration encore over-fittable même à N=160 si signaux corrélés)
- C4 OUI critical (complexity signal does its job)
- C5 OUI critical (composite beats single-signal baseline)

Score officiel cycle 14 = 3 critères pré-enregistrés (C1+C2+C3). C4/C5 = findings supplementary.

## Procedure operationnelle

```bash
# Phase 0 v5 — sample with E7 + cold-start subset
python3 phase0_v5_resample.py    # seeds 48/49, N≥200

# Phase A v5 — forge full power × case (using v1.3.0rc1)
for chunk in $(seq 0 9); do
    python3 run_phase_a_v5.py train --start $((chunk*16)) --end $((chunk*16+16))
    git add -A bench_v5/ results_v5_*.jsonl
    git commit -m "phase A v5 train chunk $chunk"
    git push origin cycle14
done
python3 run_phase_a_v5.py holdout

# Phase B v5 — calibration on 160 train
python3 phase_b_v5.py

# FINAL_REPORT_v5.md — verdict chiffré
```

## Compute estimé

- Phase 0 v5 : 1-2h (filter E7 + cold-start curation)
- Phase A v5 : 50-150h wall-clock (parallel xargs -P 3)
  - clones full ~200 cases : 1-4h
  - per-case forge full power (carmack + modularity + predict + locate + fast-deep + shield) : 15-45 min/case
  - locate setup (pip install + pytest) : long sur legacy Python deps
- Phase B v5 : 4-8h (calibration on dataset ~80k rows, vs 12k cycle 13 v4)
- FINAL_REPORT v5 : 2h

**Total : 60-170h wall-clock** sur ludo-pc-1. Multi-jours. Pas une nuit.

## Pre-conditions before launch

- [ ] **GO Sky explicit** sur cycle 14
- [ ] Disk space free : ≥ 20 GB (les 200 clones + bench_v5 outputs)
- [ ] forge installé v1.3.0rc1 (pip install forge-shield==1.3.0rc1 OU venv local Bureau/forge)
- [ ] Branch `cycle14` créée sur forge-case-studies
- [ ] Pre-registration sealed AVANT Phase A : criteria_v5.md + eligibility_v5.md (avec E7 + cold-start subset definition) + skip_reasons.md (existing 9 reasons) + panel_train_v5.json + panel_holdout_v5.json

## Anti-patterns à éviter

- **Pas de modification des critères verdict pré-enregistrés** (C1, C2, C3 strict).
- **Pas de re-tirage post-hoc** si forge fait pire que prévu.
- **Pas de "ouf je suis pressé"** : 50-150h compute est le coût réel pour un test propre.
- **Pas de skip locate sans coverage setup** (sky-master directive cycle 12 Option A : document si > 30% skip).

## Branch protection cycle 14

Cycle 14 doit être :
- Workfor sur branche `cycle14` du repo forge-case-studies
- Pas mergé sur main jusqu'à FINAL_REPORT_v5 done + GO Sky pour merge

## Compute scheduling realistic

Vu que c'est 50-150h, pratique :
- Lance par batch de 10-20 cases à la fois
- Commit + push après chaque batch (proof of progression)
- Si interrupted, idempotent runner reprend où ça en était
- Total wall-clock spread sur 3-5 jours réels (machine occupied)

## Prochain ping autorisé

FINAL_REPORT_v5.md done sur branche cycle14 avec :
- C1 + C2 + C3 chiffrés
- C4 (cold-start signal effective) + C5 (carmack bat predict)
- Verdict matrice pré-enregistrée
- v1.3.0 release decision (rc1 → 1.3.0 final ou rc1 stays)

OU blocker scope MAJEUR (>30% shield fail, >30% locate skip après E7+cold-start, GitHub API rate-limit, hardware down).

## Réference papers

- McCabe T. (1976), "A Complexity Measure", IEEE TSE
- Halstead M. (1977), "Elements of Software Science"
- Menzies T., Greenwald J., Frank A. (2007), "Data Mining Static Code Attributes to Learn Defect Predictors", IEEE TSE — empirical validation McCabe + Halstead predict defects independently of history
- D'Ambros M., Lanza M., Robbes R. (2010), "An Extensive Comparison of Bug Prediction Approaches", MSR — confirms history + static metrics combined predict better than either alone

---

**Status** : Brief locked. **NOT LAUNCHED.** Awaits explicit Sky direct GO.

Si Sky GO :
1. Create branch `cycle14` on forge-case-studies
2. Pre-register criteria_v5 + eligibility_v5 (E7 + cold-start subset definition)
3. Sample N=200 with seeds 48/49
4. Launch Phase A v5 with forge 1.3.0rc1
5. Multi-day batch execution
6. FINAL_REPORT_v5 + verdict → tag v1.3.0 final or keep rc1

Sinon : brief stays as plan, v1.3.0rc1 reste rc1, refactor analysis later.
