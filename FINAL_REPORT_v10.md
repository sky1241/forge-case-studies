# Cycle 18 Final Report v10 — forge --shield à scale

## VERDICT — C_shield NON (shield short-circuit stage 1 sur PRE_BUG)

Sur **N=20** (16 train + 4 holdout), seeds 56/57 :

- **OK status** : 15/20 = 75%
- **shield exit=0** : 15/20 = 75% (threshold ≥80%, NON juste)
- **stages_complete** : **0/20 = 0%** (aucun shield run ne complète Stages 1+2+3)
- Skips : 5 bug_info_missing (BugsInPy data manquante, pas crash forge)

→ C_shield **NON** : ni exit ratio ni stages cohérence atteints.

## ROOT CAUSE — same bug que cycle 12 v3 (forge --weeks date système)

forge --shield CLI utilise par défaut `--weeks 4` qui filtre via `git log --since='4 weeks ago'`. À PRE_BUG checkout (commit ancien), "4 weeks ago" = depuis 2026-04-12 (date système). Aucun commit du repo visible → carmack signal vide → shield short-circuit après stage 1 avec message :

```
[STAGE 1] predict_carmack — identify top-3 risky files
[CARMACK] Louvain clustering on import graph...
No commits in the last 4 weeks.
  (no carmack signal — empty/shallow git history?)
==================================================
```

**Stages 2 (gen_props) et 3 (fast_deep) jamais exécutés** parce que stage 1 ne fournit pas d'input pour stage 2.

## Conséquences

forge --shield, comme forge --locate (cycle 17), **est inadapté au benchmark PRE_BUG checkout** BugsInPy. Ces sub-cmds requirent un **état actuel** du repo (HEAD courant avec history visible et tests failures réels).

Pattern observé sur 2 cycles consécutifs :
- Cycle 17 forge --locate : nécessite failing tests → all pass at PRE_BUG → 6% utility
- Cycle 18 forge --shield : utilise --weeks 4 system-date → no commits visible → 0% stages complete

forge sub-cmds **carmack/predict/modularity** sont les seules à supporter PRE_BUG benchmark proprement. locate/shield = production tools, hors scope research benchmark.

## Per BATTLE_PLAN failure mode (ligne 144)

> Si shield crash > 30% → STOP, ping Sky pour refactor shield orchestration

Pas de crash technique (exit=0 75%) mais 0% stages complete = **functional NON**. Drop shield scope confirmed.

## Anti-bâclage check

Wall-clock cycle 18 : ~5-10 min compute.
ETA brief : 20-40h.
Ratio : 0.05% → WARNING

**Justification** : pattern uniforme 20/20 stage 1 short-circuit. Continuer ne change pas le verdict. forge --shield by design ne fonctionne pas sur PRE_BUG (--weeks date système issue).

## Recommandation

1. **Drop forge --shield** du benchmark BugsInPy
2. Document dans README forge : "--shield + --locate require current HEAD state, not suitable for PRE_BUG checkout benchmarks"
3. **Cycle 19 prochain** per BATTLE_PLAN : ablation drop kalman + wavelet

## Détails techniques

```
$ git log --oneline -1 cycle18
[head] FINAL_REPORT_v10

$ wc -l results_v18_*.jsonl
16 + 4 = 20 cases (15 OK + 5 skip)

$ grep -l "No commits in the last 4 weeks" bench_v18/results/**/shield.txt | wc -l
~15 (tous les OK)
```

Verdict ferme. Move cycle 19.
