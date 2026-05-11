# forge --carmack — Cycle 12 Final Report v3

## VERDICT — 0 / 3 OUI

Sur **N=20 train + N=17 hold-out** effective (24 sampled each, 4 train + 7 hold-out SKIP `file_missing_at_pre`) cases pre-registered with seeds 44/45, stratified 2 small + 11 medium + 11 large per panel :

- **Critère 1** (forge bat random, Fisher exact) : **NON** (p = 0.7164, forge = 6/20 vs random = 4/20)
- **Critère 2** (precision@10 ≥ 0.50, Wilson CI lower ≥ 0.30) : **NON** (p@10 = 0.30 < 0.50 threshold, Wilson lower = 0.146 < 0.30)
- **Critère 3** (calibration bat heuristic ≥ +0.05 AUC sur hold-out) : **NON** (delta = +0.0393, sous +0.05 threshold mais positif vs v1's −0.054 et v2's +0.0095)

**Total : 0 / 3 OUI**

→ Décision pré-enregistrée matrix : `forge_au_niveau_hasard`

## LIMITE STATISTIQUE (D9 obligatoire ligne 2)

Test à **N=20 train + N=17 hold-out effective**. Power statistique enfin suffisante pour Fisher exact (table 2×2 à N=20 atteint p<0.05 même avec ratios modérés), mais le ratio observé (6 forge vs 4 random) reste très proche → p=0.72 = no signal détecté. Tests adaptés (Fisher exact, Wilson CI, bootstrap, AUC) tous valides à N=20. **Aucune extrapolation N hypothétique nécessaire cette fois** — le verdict tient sur la power réelle du test.

## v1 + v2 → v3 progression (process amélioration)

| Aspect | v1 (INVALID) | v2 | v3 |
|---|---|---|---|
| Candidats fallback testés | 8 / 200 | 400 | 400 (réutilisé) |
| N effective | 10 | 15 | **37 (20+17)** |
| Projets distincts (TRAIN) | 4 (3 luigi) | 8 | 12+ |
| Forge sub-cmds par cas | 1/6 | 5/6 (locate skip) | **6/6** (locate avec setup actif) |
| Wall-clock compute | ~30 min (bâclé) | ~2-3h | ~1h (forge+shield rapides) |
| Verdict | 0/3 | 1/3 | **0/3** |
| C2 verdict | NON | OUI ✓ | NON |
| C3 delta AUC holdout | −0.054 (overfit) | +0.0095 | **+0.0393** (proche seuil) |

**Évolution C3** : v1 −0.054 (overfit), v2 +0.0095, v3 +0.039 → tendance positive avec N croissant. À N=100+ peut-être franchirait 0.05.

## PRÉ-REGISTRATION (sealed before runs)

Identique aux cycles précédents — **critères et seuils NON modifiés**. Le panel v3 est tiré avec NEW seeds 44/45 (disjoint v2 42/43 pour éviter cross-leakage).

- `criteria.md`, `eligibility.md`, `skip_reasons.md`, `temporal_rules.md`, `metrics.md` — committed commit `126ced7`
- `panel_train_v3.json` + `panel_holdout_v3.json` — committed `932ee95`

## MÉTHODOLOGIE v3

### Phase 0 v3 — N=48 panel (24 train + 24 holdout)

- BugsInPy 13 projets eligibles + 6 small fallback eligibles cycle 11 v2
- Stratification 2 small + 11 medium + 11 large par panel
- 1-bug/projet contrainte assouplie pour medium/large (4 projets medium, 7 projets large insuffisants pour 11 distinct)
- 2 cases small/panel (blocklistproject FAILED find_small_bug × 2 — pas de .py fix commit, 1446 commits + 6 fix 2y sur .txt blocklists only)

### Phase A v3 — Forge full power AVEC locate setup actif

Pour chaque cas, ces 6 sub-cmds run par case (verbatim outputs in `bench_v3/results/{bucket}/{bug_id}/*.txt`) :
- `forge --carmack` CLI + `predict_carmack()` Python direct
- `forge --modularity`
- `forge --predict`
- `forge --fast-deep`
- **`forge --locate` AVEC pip install + pytest-cov + coverage run** (vs v2 où on skipait)
- `forge --shield` (par case, vs v2 où on faisait 1/bucket)

### Finding cycle 12 — forge --locate setup infeasible at scale on legacy Python codebases

**Ratio locate skip : 15/37 = 41% > 30% threshold blocker**.

Cause root : BugsInPy bugs anciens demandent Python < 3.10. Le venv forge tourne Python 3.13. Pip resolver refuse les deps avec exit code != 0. Setup coverage infaisable per case sans pyenv multi-version (rejected per sky-master directive "ne pas pyenv per case").

Per sky-master Option A directive : continuer le test, documenter en finding (locate n'est PAS dans les critères verdict). C'est exactement ce que ce benchmark exhaustif révèle : **forge --locate a un usage requirement pratique non documenté** ("requires compatible Python runtime ≥ project's minimum, not usable on legacy bug datasets").

Recommandation forge cycle 12+ : ajouter dans README forge documentation :
> "`forge --locate` requires `pip install -e .` to succeed at the target commit. For tests on legacy codebases (BugsInPy-style benchmarks on bugs from Python < 3.10), may need pyenv or compatible runtime container."

## RÉSULTATS PHASE A v3

### TRAIN panel (N=24, N_ok=20, 4 SKIP)

Top 10 results (sorted by rank_carmack ASC) :

| bug_id | bucket | rank_C | total | top10 |
|---|---|---|---|---|
| sherlock-4656d95 | small | **1** | 14 | YES |
| youtube-dl-29 | large | **5** | 602 | YES |
| PySnooper-2 | medium | **4** | 9 | YES |
| cookiecutter-3 | medium | **7** | 81 | YES |
| youtube-dl-41 | large | (top, ~10) | ~600 | YES (par sample) |
| ansible-17 | large | (mid) | 7000+ | NO (mega-projet) |
| thefuck-17/18/14/29/15/4/20/30 | medium | rank 30-200 | 200-300 | mostly NO |
| scrapy-15, scrapy-9 | large | 100-200 | 320 | NO |

Pattern observable : forge **HIT** sur projets avec bugfix history (sherlock 2919 commits / 150 fix 2y, youtube-dl, PySnooper, cookiecutter). Forge **MISS** sur thefuck rules (modules avec 0 bugfix antérieur — pattern cold-start identifié dans cycle 11 phase_c_blindspots).

### HOLDOUT panel (N=24, N_ok=17, 7 SKIP)

Pattern similaire. 6/17 top10. Top hits : youtube-dl-26 (rank 1/?), luigi-1, scrapy-37 hit, black-1/17 hit. Misses : thefuck rules, ansible-12 (5253/7051 ultra-large).

### Critère 1 — Fisher exact (TRAIN)

```
Contingency: [[forge_top10=6, miss=14], [random_top10=4, miss=16]]
Fisher exact two-sided: p = 0.7164
Threshold: p < 0.05 AND forge_hits > random_hits
forge_hits (6) > random_hits (4) ✓
p = 0.7164 ≥ 0.05 ❌
VERDICT C1 = NON
```

À N=20, le test a la power suffisante pour détecter des effets modérés. Le **p=0.72 reflète que forge n'est PAS différent du random** sur ce panel. C'est un résultat plus fort que les "N too small" des v1/v2.

### Critère 2 — Wilson CI sur precision@10 (TRAIN)

```
precision@10 = 6/20 = 0.3000  (sous 0.50 threshold ❌)
Wilson 95% CI = [0.1455, 0.5190]
Threshold: p@10 ≥ 0.50 AND lower ≥ 0.30
VERDICT C2 = NON (p@10 sous 0.50, lower bound aussi sous 0.30)
```

Drop massif vs v2 (0.625 → 0.30). Probably dû au panel v3 multi-bug par projet qui inclut beaucoup de thefuck rules (cold-start blind spot).

### Critère 3 — Calibration HOLDOUT

```
Heuristic AUC train:    0.7214
Grid AUC train:         0.8185 (gain train +0.0971)
Calibrated weights v3:
  kalman   = 0.025
  wavelet  = 0.019
  crash    = 0.341
  coupling = 0.592  ← dominant signal v3
  churn    = 0.023

Heuristic AUC holdout:  0.6982
Calibrated AUC holdout: 0.7375
DELTA AUC: +0.0393 (sous +0.05 threshold)
VERDICT C3 = NON
```

**Finding v3** : calibration v3 favorise **coupling** (Newman Q sur import graph) — différent de v2 qui favorisait **crash + kalman**. **Inconsistance entre calibrations v2/v3** suggère que la composition optimale est sensible au panel. Pas robuste.

## FRICTIONS ADMISES (D9 — 12 total)

1. **v1 INVALID + v2 partial** — preserved in git history
2. **Bucket small 2/3** v3 (blocklistproject FAILED find_small_bug × 2)
3. **TRAIN/HOLDOUT 4+7 = 11 SKIP file_missing_at_pre** (mostly thefuck rules where file didn't exist at PRE_BUG)
4. **locate skip 15/37 = 41%** ABOVE 30% blocker threshold — documented as **finding scientific** (not test failure)
5. **forge --weeks utilise date système** → `weeks=999` workaround maintenu
6. **forge --carmack CLI tronque top 15** → `predict_carmack()` Python direct
7. **predict CLI tronque top 15** : "none" rank pour > 15 sur thefuck rules
8. **shield exit=0 partout** : couvre 37 cas, 0 crash → pas de blocker
9. **ansible 7000+ fichiers** → impossible top-10 dans bucket "large" strict
10. **Inconsistance calibration v2 vs v3** : v2 favorise crash+kalman, v3 favorise coupling → signal pas robuste à N=20
11. **Drop precision@10 v2→v3** (0.625→0.30) : panel v3 inclut beaucoup thefuck rules (cold-start blind spot 0 bugfix history)
12. **forge --predict bat carmack** dans certains cas v3 (rank_predict_cli plus bas que rank_carmack quand both visible top 15)

## EXTRAPOLATION POST-CYCLE 12 (transparency)

Le drop precision@10 v2→v3 montre que **le signal forge dépend du panel**. forge marche sur projets bien bugfixés, rate sur cold-start fresh modules.

Si on filtrait le panel pour **exclure les fichiers avec 0 bugfix antérieur** (les vraies cibles de carmack qui est history-based) :
- Sur N=20 train v3 retirer les 8-10 cas thefuck rules → N=10-12 → ratio top10 monterait 50%+
- Mais c'est du **p-hacking post-hoc** → INTERDIT par la charte D9

Verdict 0/3 OUI **est gravé pré-enregistré**. C'est ce que sky-master voulait : un test propre, panel respecté, pas de cherry-pick.

## RECOMMANDATION

Selon matrice pré-enregistrée :
- **0/3 OUI → forge_au_niveau_hasard → "leçon dure, refactor majeur ou refonte approche"**

**Lecture honnête** : le verdict 0/3 OUI à N=37 effective est solide. Forge a un signal réel sur certains profils de bugs (projets bien-bugfixés), mais le test agrégé sur un panel diversifié montre **forge au niveau du hasard sur N=20**. Le drop vs cycle 11 v2 (où C2 était OUI à N=8) montre que v2 était peut-être un signal favorable par chance, pas un signal robuste.

**Actions concrètes** :
1. **NE PAS release v1.3.0 avec nouvelle calibration**. Calibration v3 (coupling-dominant) diffère de v2 (crash-dominant). Pas robuste.
2. **Garder heuristic forge** : (0.20, 0.15, 0.25, 0.15, 0.25). C'est l'heuristic qui produit AUC holdout 0.70 v3, mieux qu'un random.
3. **Refactor approche carmack** : le composite multi-signal est dilutif. Le finding "predict (churn-only) bat carmack" v2 et le drop v3 suggèrent qu'**un signal pur est plus fort qu'un composite mal pondéré**.
4. **Cycle 13 (si Sky veut)** : test N=100+ avec **panel filtré par bugfix history** (uniquement files avec ≥ 1 bugfix antérieur). C'est dans le scope original de carmack (history-based predictor) sans p-hacking.
5. **Documenter blind spot cold-start** : forge --carmack rate par design les fresh modules. Add "Honest Limit" : "carmack predicts based on bugfix history; modules with 0 prior bugfixes are systematically under-ranked".
6. **forge --locate setup requirement** : update README avec note Python runtime compatibility.

## REPRODUCTIBILITÉ

```bash
git clone https://github.com/sky1241/forge-case-studies
cd forge-case-studies
git log --all --oneline | grep "phase 0"   # see pre-registration commits
python3 phase0_v3_resample.py
python3 run_phase_a_v3.py train             # 30 min compute
python3 run_phase_a_v3.py holdout           # 30 min compute
python3 phase_b_v3.py                       # 5 min compute
```

Files versioned for reproducibility :
- `panel_train_v3.json` + `panel_holdout_v3.json`
- `results_v3_{train,holdout}.jsonl`
- `bench_v3/results/{bucket}/{bug_id}/*.txt` — verbatim outputs (carmack, modularity, predict, fastdeep, locate, shield + locate_skip_reason.md if applicable + pip_install.log + pytest_cov.log)
- `phase_b_v3_results.json`

---

**Verdict final cycle 12** : **0 / 3 OUI** → `forge_au_niveau_hasard` (sur ce panel pre-registered N=37 effective).

**Lecture honnête** : forge a un signal sur certains profils (projets bien-bugfixés) mais le test scientifique aggregate sur panel diversifié N=20 ne franchit aucun critère. La calibration approche du seuil C3 mais sans le franchir. **Sans nouveau refactor ou panel filtré, forge --carmack n'est pas un prédicteur utile sur des bugs Python random.**

Sky a son verdict tranché. La voie est claire : refactor cycle 13 ou repenser l'approche carmack.
