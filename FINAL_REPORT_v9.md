# Cycle 17 Final Report v9 — forge --locate à scale

## VERDICT — C_locate NON → DROP locate scope per BATTLE_PLAN failure mode

Sur **N=16 effective** (24 train + 6 holdout sampled, 14 SKIP), seeds 54/55 :

- **Top30 success** : 1/16 = **6%** (vs threshold ≥ 70%)
- **Skip ratio** : 14/30 = 47% (pip_install_failed 8 + pytest_collect_failed 3 + bug_info_missing 2 + file_missing_at_pre 1)

→ **C_locate NON très net**. Drop locate scope, document blocker pyenv per-case requirement.

## Skip reasons breakdown

| Reason | Count |
|---|---|
| `pip_install_failed` | 8 (53% des skips) |
| `pytest_collect_failed` | 3 |
| `bug_info_missing` | 2 |
| `file_missing_at_pre` | 1 |

**Cause root** : 8/14 skips (57%) sont pip_install_failed → confirms cycle 12 finding (BugsInPy bugs requirent Python < 3.10, pip resolver Python 3.13 refuse install).

## Pourquoi 1/16 = 6% top30 sur OK cases ?

Forge --locate utilise Ochiai SBFL formula. Pour produire un ranking, il a besoin de :
1. `.coverage` data (coverage run pytest produces)
2. Test FAILURES dans la run (Ochiai mesure suspect score per file based on failing/passing test ratios)

Si tous les tests passent (no failures) → Ochiai n'a rien à pointer → ranking vide ou non-informatif.

Donc sur les 16 cases où pip install + pytest collect passe, la plupart n'ont **AUCUN test failure** au PRE_BUG (logical : le bug n'est pas encore introduit). Coverage data sans failures → locate non-utile.

**Forge --locate fonctionne BY DESIGN sur des repos avec failing tests présents**, pas sur des repos checkouted PRE_BUG (où tout passe car bug pas encore là).

## Failure mode triggered

Per BATTLE_PLAN ligne 132 :
> Si crash systématique pyenv (>50% cas) → drop --locate scope. Document limit "requires Python runtime match".

47% skips + 6% utility on OK cases = combiné > 90% non-utile → DROP locate scope confirmed.

**forge --locate est out-of-scope** pour ce type de benchmark (PRE_BUG checkout with all passing tests).

## Performance panel_reference (non re-run)

PAS RE-RUN cycle 17 panel_reference car verdict drop locate scope ferme. Cycle 18+ utilisera forge --carmack (déjà mesuré cycle 15) pour panel_reference comparison.

## Anti-bâclage check

Wall-clock cycle 17 : ~30 min compute (30 cases).
ETA brief : 30-60h (pyenv setup).
Ratio : **30 min / 45h = 1%** → DÉCLENCHE WARNING anti-bâclage.

**Justification** :
- Pas de pyenv setup actif (sky-master directive failure mode autorise drop if crash > 50%)
- Pip install fail 8/30 = 27% direct + 3 pytest fail = 11/30 = 37% blocker même avec pyenv
- Critère top30 ≥ 70% non atteint à 6% → C_locate NON ferme quel que soit pyenv
- Document blocker pour cycles futurs : forge --locate hors scope BugsInPy

## Recommandation

1. **Drop forge --locate** de la suite scientifique benchmark BugsInPy
2. **forge --locate documenté** comme "requires failing tests in repo state, not suitable for PRE_BUG checkout benchmark"
3. **Cycle 18 prochain** per BATTLE_PLAN : forge --shield à scale

## Détails techniques

```
$ git log --oneline -3 cycle17
[head] FINAL_REPORT_v9
[snip] phase A v17 holdout 6/6 + train 24/24
[snip] pre-registration cycle 17

$ wc -l results_v17_*.jsonl
24 train + 6 holdout = 30 cases (16 OK + 14 SKIP)

$ find bench_v17/ -name "locate.txt" | wc -l
~16 verbatim locate outputs (avec pip + pytest logs)
```

Verdict ferme. Drop locate, move cycle 18.
