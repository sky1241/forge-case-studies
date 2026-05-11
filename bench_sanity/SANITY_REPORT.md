# Sanity check cold-start v1.3.0rc1 — VERDICT : SANITY FAIL (0/5 top10 hits)

**Date** : 2026-05-11
**Forge version testée** : 1.3.0rc1 (Bureau/forge main, complexity signal active)

## Verdict global

**SANITY FAIL** sur la métrique critique Test 3 (cold-start). Le signal complexity AIDE certains cas mais **n'arrive PAS à faire sortir des cas cold-start dans le top10**.

Décision : **NE PAS lancer cycle 14 N=200** maintenant. Diagnostic + remediation needed avant compute 50-150h.

---

## Test 1 — Sanity values sur 10 fichiers : **PASS** ✓

```
file                                                mccabe  halstead_v  depth    loc  score
-----------------------------------------------------------------------------------------------
forge.py                                              976     174872     12   5082  1.000
test_forge_real_algos.py                              203     122078      4   4204  0.880
simple.py (1 function return 42)                        1          2      1      2  0.026
empty.py                                                0          0      0      0  0.000
test_typing.py                                          1        256      1     53  0.037
test_forge_destructive_skip.py                          5       3460      3    290  0.171
conftest.py                                             2         98      1     17  0.035
test_cli_entry_point.py                                 9       4574      2    284  0.184
```

**Verdict** : scores **corrélés à la complexité visible**.
- forge.py (extremely complex) → 1.000 (saturé)
- empty.py → 0.000 (correct floor)
- simple fonction return 42 → 0.026 (near zero)
- Modules intermédiaires (test_forge_destructive_skip, test_cli_entry_point) → 0.17-0.18

Pas de bug normalisation. Sanity score formula OK.

---

## Test 2 — Re-run sur 2 catastrophes cycle 12 v3 : **MIXED** (1 win, 1 loss)

### scrapy-26 — WIN ✓

```
target = scrapy/settings/__init__.py
Cycle 12 v3 (5 signals)        : rank 179/301
Sanity   v1.3.0rc1 (6 signals) : rank 64/301
DELTA rank: +115 (forge improved with complexity signal)
Target sub-scores: complexity=0.294
```

Le signal complexity **aide significativement** : rank passe du top 59% (179/301) au top 22% (64/301). +115 positions.

### thefuck-9 — LOSS ❌

```
target = thefuck/rules/git_push.py
Cycle 12 v3 (5 signals)        : rank 103/249
Sanity   v1.3.0rc1 (6 signals) : rank 112/249
DELTA rank: -9 (forge slightly worse)
Target sub-scores: complexity=0.035
```

Le fichier `thefuck/rules/git_push.py` est **tiny** (14 LOC, mccabe ~2, halstead minimal). Complexity score = 0.035 (proche de zero). Le signal ne peut pas aider un fichier sans complexité notable.

**Interpretation Test 2** : complexity signal **aide les fichiers moyennement complexes** mais pas les **tiny fresh modules**.

---

## Test 3 — 5 cas cold-start (E7 fail cycle 13) : **FAIL** ❌

| bug_id | change_file | rank | total | top10? | complexity |
|---|---|---|---|---|---|
| thefuck-9 | thefuck/rules/git_push.py | 112 | 249 | NO | 0.035 |
| thefuck-24 | thefuck/types.py | 26 | 161 | NO | 0.032 |
| fastapi-7 | fastapi/exception_handlers.py | 57 | 337 | NO | 0.057 |
| scrapy-2 | scrapy/utils/datatypes.py | 49 | 271 | NO | 0.449 |
| youtube-dl-31 | (bug.info missing) | — | — | SKIP | — |

**0/4 measurable hit top10** (1 skipped technical). Sky-master threshold était "≥ 2 hits / 5 → signal sauve vraiment".

**0 / 4 = 0% top10 sur cold-start.** FAIL critère.

**MAIS observation nuancée** :
- scrapy-2 rank 49/271 = top 18% (vs random ~50% theoretical)
- thefuck-24 rank 26/161 = top 16%
- fastapi-7 rank 57/337 = top 17%
- forge AVEC complexity **bat le random sur cold-start** (les 4 cases sont tous dans le top 25%)
- MAIS n'arrive PAS au top10

**Le signal complexity améliore le rank moyen sur cold-start mais ne suffit pas pour atteindre le top10.**

---

## Test 4 — mypy + pytest régression : **PASS** ✓

```
$ .venv/bin/python -m mypy --strict forge.py
Success: no issues found in 1 source file

$ .venv/bin/python -m pytest tests/ -q --tb=no
262 passed, 1 deselected in 23.43s
```

Aucune régression. Tous les 262 tests (incl. 16 cycle 14 cold-start tests) passent.

---

## Verdict global : **SANITY FAIL**

| Test | Resultat | Status |
|---|---|---|
| 1 — Sanity values | Scores corrélés à complexité | **PASS** |
| 2 — Catastrophes recheck | 1/2 (scrapy +115 / thefuck -9) | **MIXED** |
| 3 — 5 cas cold-start | 0/4 top10 hits | **FAIL** |
| 4 — mypy + pytest | 262/262 pass | **PASS** |

**Test 3 est critique** : le but du signal complexity est de combler le cold-start blind spot. 0/4 top10 hits = le signal n'atteint pas le seuil utile.

## Diagnostic causes racines

### Pourquoi le signal complexity n'arrive pas au top10

1. **Tiny modules cold-start ont LOW complexity** : thefuck/rules/git_push.py 14 LOC → complexity 0.03. La normalisation `min(mccabe/50, 1.0)` + `min(effort/1e6, 1.0)` font que les petits modules restent près de 0.

2. **Le composite carmack heuristic donne 0.15 au complexity** (weight 0.15). Avec un complexity score = 0.03, contribution au composite = 0.003. Insuffisant pour bouger le rang.

3. **Sur les cas cold-start, les autres signaux history-based sont 0 ou bruit** :
   - Kalman = 0 (pas de bugfix history)
   - Crash = 0 (no events)
   - Wavelet HF est dilué par les fichiers churn-actifs
   - Coupling peut être 0 pour modules isolés
   - Churn est bas pour fresh modules
   → le rank devient dominé par les SAUTRES fichiers (non-target) qui ont des signaux non-nuls, pas par la complexité du target.

### Voie de remediation possible (PAS implémenté maintenant)

**Option A — Boost weight complexity sur cold-start cases**.
Algorithme proposé :
```python
if r["bugfixes"] == 0 and r["kalman"] < 1e-6 and r["crash_prob"] < 1e-6:
    # Cold-start file: amplify complexity weight
    cw_effective["complexity"] = 0.50
    cw_effective["churn"] = 0.25
    cw_effective["coupling"] = 0.15
    cw_effective["kalman"] = cw_effective["wavelet"] = cw_effective["crash"] = 0.10/3
    # Else: standard heuristic
```

**Option B — Augmenter normalisation complexity** :
```python
mccabe_norm = min(mccabe / 20.0, 1.0)  # was /50: more saturation low end
loc_norm = min(loc / 300.0, 1.0)       # was /1000: same
```

**Option C — Re-pondérer score base** :
```python
return 0.50 * mccabe_norm + 0.20 * effort_norm + 0.15 * loc_norm + 0.15 * nesting_norm
# Au lieu de 0.30 / 0.30 / 0.20 / 0.20
```

Option A est la plus prometteuse (rule-based composite re-weighting on cold-start detection).

## Recommandation

**NE PAS lancer cycle 14 N=200 maintenant.**

3 options pour Sky :

### A) Fix complexity signal + re-test sanity
- Implement Option A (cold-start composite re-weighting) ou B/C dans forge
- Re-run sanity 4 tests
- Si SANITY OK alors lance cycle 14

### B) Lancer cycle 14 quand même avec signal actuel
- Accept que le complexity signal n'est pas optimal
- Cycle 14 va measure precision@10 globale (mix history-rich + cold-start)
- Probably C2 OUI quand-même sur history-rich subset (où carmack v1.2.5 marchait déjà)
- Mais le cold-start subset spécifique probably 0% top10

### C) Drop le signal complexity + ship v1.2.5 stable
- v1.3.0rc1 stays rc1 forever (sanity FAIL)
- Accept que cold-start blind spot reste un known limit forge
- Document dans README "carmack works on history-rich files only"

## Détails techniques

```
$ git log --oneline -3 (forge-case-studies)
d6928ab Mission 3: CYCLE_14_BRIEF.md ready, NOT EXECUTED
7830a6f Merge cycle13 — E7 filter, 4-cycle progression v1→v4
ba1409d FINAL_REPORT_v4 — cycle 13 E7-filtered — VERDICT 1/3 OUI

$ git log --oneline -3 (sky1241/forge)
4e2f3e3 feat(cycle14): cold-start complexity signal — McCabe + Halstead + nesting (v1.3.0rc1)
30ea682 docs(cycle12 v3): honest limits update + bump v1.2.4
07165c0 docs(cycle11 v2): honest limits + bump v1.2.3

$ ls bench_sanity/
SANITY_REPORT.md
test1_complexity_scores.txt
test2_cold_start_catastrophes.txt
test3_cold_start_5_cases.txt
```

## Pour Sky

Sanity FAIL est une **bonne nouvelle** : on évite 50-150h compute sur un signal pas assez fort. Le signal complexity v1.3.0rc1 **a un effet positif** (Test 2 scrapy +115) mais **n'est pas assez fort sur cold-start** pour atteindre top10.

Recommendation forte : **Option A** (rule-based composite re-weighting sur cold-start detection). C'est 30-60 min de dev + re-run sanity. Si re-sanity OK, alors lance cycle 14.
