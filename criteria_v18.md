# Pre-registered criteria — cycle 18 (forge --shield à scale)

**Date** : 2026-05-11
**Branch** : cycle18 sur forge-case-studies

## Hypothèse cycle 18

> "forge --shield orchestration end-to-end (carmack → gen_props → fast-deep) tourne sans crash sur N=20 cas et produit output cohérent ?"

## Critère verdict (BATTLE_PLAN ligne 142)

### C_shield

- forge --shield exit code 0 sur **≥ 80%** cas
- AND output cohérent (Stage 1 carmack + Stage 2 gen_props + Stage 3 fast-deep produits dans le shield output)

**OUI** : ≥80% exit=0 ET output cohérent
**NON** : <80% OR crashes

## Panel

- TRAIN seed=56 : 16 cas (6 medium + 10 large)
- HOLDOUT seed=57 : 4 cas (2 medium + 2 large, disjoint)
- Total N=20

## Procédure

Pour chaque cas :
1. Checkout PRE_BUG
2. `forge --shield .` avec timeout 1800s (cycle 14 brief)
3. Capture exit code + verbatim output

## Failure mode

Si shield crash > 30% → STOP cycle, ping Sky (BATTLE_PLAN ligne 144).
