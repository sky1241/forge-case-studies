# Re-sanity check post-fix cold-start re-weighting — STILL FAIL 1/4

**Date** : 2026-05-11
**Branch** : `fix/cold_start_re_weighting` on sky1241/forge
**Forge** : 1.3.0rc1 + cold-start re-weighting (2 sub-regimes A/B per coupling)

## Verdict : STILL FAIL — 1/4 top10 vs threshold ≥ 2/5

Le fix améliore PARTIELLEMENT mais ne franchit pas le seuil sky-master.

## Test 2 — Re-run catastrophes : MIXED encore

| bug_id | cycle 12 v3 | rc1 (6sig) | re-fix | regime | complexity |
|---|---|---|---|---|---|
| scrapy-26 | 179/301 | 64/301 | **112/301** | history | 0.294 |
| thefuck-9 | 103/249 | 112/249 | **63/249** | A_coupled | 0.035 |

**thefuck-9 WIN** : 112 → 63 (+49 positions). Le re-weighting cold-start fait passer le rank de top 45% à top 25%. Le sub-regime A_coupled (coupling 0.15 > 0.01 threshold) boost à 0.35 le coupling weight.

**scrapy-26 REGRESSION** : 64 → 112 (-48 positions). scrapy/settings/__init__.py a `bugfixes=2` (>0) → regime="history" → utilise les heuristic weights par défaut. Le rank régresse par rapport au rc1 testé hier.

**Mystère scrapy-26** : entre rc1 (64) et re-fix (112) les weights heuristic sont identiques `(kalman 0.20, wavelet 0.15, crash 0.20, coupling 0.15, churn 0.15, complexity 0.15)`. Le rank devrait être identique. Hypothèses :
- État non-déterministe Louvain clustering (initialization random?)
- Pollution état Python entre les calls predict_carmack consécutifs dans le script sanity
- Différence d'état clone (HEAD position, mais reset --hard avant chaque case)

À investiguer si on continue.

## Test 3 — 5 cas cold-start : 1/4 top10 hits

| bug_id | rank | top10 | regime | complexity | note |
|---|---|---|---|---|---|
| thefuck-9 | 63/249 | NO | A_coupled | 0.035 | Top 25%, mais pas top10 |
| **thefuck-24** | **9/161** | **YES ✓** | A_coupled | 0.032 | Hit ! |
| fastapi-7 | 43/337 | NO | A_coupled | 0.057 | Top 13% |
| scrapy-2 | 74/271 | NO | **history** | 0.449 | regime "history" malgré E7 fail |
| youtube-dl-31 | SKIP | — | — | — | bug.info missing |

**1/4 measurable hits**. Sky-master threshold = ≥ 2/5. **FAIL** (under).

### Note importante : scrapy-2 "regime=history" malgré E7 fail

scrapy-2 a `bugfixes != 0` (E7 fail réclame ≥3 bugfix, mais on dit cold-start si bugfixes==0). Donc fichier avec 1-2 bugfix antérieurs n'est PAS detected comme cold-start par mon code. C'est un edge case du criterion E7 vs detection cold-start.

**Possible amélioration** : changer detection à `bugfixes < 3 AND kalman < 1e-6` pour aligner avec E7. Test à faire.

## Test 4 — mypy + pytest : PASS

```
$ .venv/bin/python -m mypy --strict forge.py
Success: no issues found in 1 source file

$ .venv/bin/python -m pytest tests/ -q --tb=no
265 passed, 1 deselected in 24.63s
```

3 nouveaux tests ajoutés (cold_start_weights_a/b/coupling_threshold sums) tous pass.

## Diagnostic — Pourquoi seulement 1/4 ?

### Observation 1 : thefuck-24 hit malgré complexity=0.032

`thefuck/types.py` est cold-start, complexity très basse (0.032), mais rank=9/161 = top10 ✓. Le boost coupling (0.30 → 0.35 sous régime A) suffit à monter le rank parce que coupling = 0.30 réel sur ce fichier.

### Observation 2 : thefuck-9 rank 63/249, presque top 25%

Même profile (cold-start, coupling 0.15, complexity 0.035) mais rank plus bas. Différence : moins de fichiers concurrents en haut du top (le score absolu de 0.30+ est plus rare sur thefuck-9 que thefuck-24).

### Observation 3 : fastapi-7 et scrapy-2 ne hit pas

- fastapi-7 : coupling élevé (probably), complexity 0.057, regime A_coupled. Rank 43/337 = top 13%.
- scrapy-2 : NOT detected as cold-start malgré E7 fail (bugfixes 1-2). regime "history". Rank 74/271.

### Hypothèses pour atteindre 2/5+

1. **Aligner detection cold-start avec E7** : `bugfixes < 3` au lieu de `bugfixes == 0`. Cela inclurait scrapy-2 dans le régime cold-start. → 5/5 detected as cold-start.

2. **Boost complexity weight encore plus haut sur sub-regime B** : 0.70 au lieu de 0.60.

3. **Normaliser complexity score plus agressivement** : `mccabe / 20` au lieu de `/ 50` pour saturer plus tôt sur petits modules.

4. **Accepter que cycle 13's 28% top10 baseline** est le plafond actuel et que le complexity signal ne fait pas mieux pour ce panel. Mesure scientifique honnête.

## Recommandation

**OPTION D** (nouvelle) : Sky tranche entre :
- **D1** : retry avec `bugfixes < 3` detection + re-sanity (15 min) → si OK GO cycle 14
- **D2** : abandonner cold-start signal cycle 14, ship v1.2.5 stable, document cold-start blind spot. v1.3.0rc1 stays rc1 forever.
- **D3** : lancer cycle 14 quand même avec la version actuelle, accepter signal partiel sur cold-start (1/4 hit), mesurer precision@10 globale qui sera dominée par les cas history-rich

Mon vote : **D1** (retry detection + re-sanity, 15 min dev). Le pattern qu'on voit déjà (1/4) suggère que la voie est correcte mais le criterion strict bugfixes==0 manque trop de cas. Aligner avec E7 (<3) pourrait débloquer.

## Détails techniques

```
$ git log --oneline -2 sky1241/forge fix/cold_start_re_weighting
(local branch, not yet pushed)
[new commits with cold-start re-weighting + 3 tests]

$ ls /home/sky/forge-case-studies/bench_sanity/
RESANITY_REPORT.md
SANITY_REPORT.md
resanity_test2_3.txt
test1_complexity_scores.txt
test2_cold_start_catastrophes.txt
test3_cold_start_5_cases.txt
```
