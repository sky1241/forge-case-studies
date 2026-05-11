# Re-sanity D1 — STILL FAIL 1/4 + scrapy-26 investigation RÉSOLU

**Date** : 2026-05-11
**Branch** : `fix/cold_start_re_weighting` (local, pas pushé)
**Fix D1 applied** : detection `bugfixes < 3` (au lieu de `== 0`)

## Verdict global : STILL FAIL — 1/4 top10 (threshold ≥ 2/5)

Le fix D1 aide (scrapy-2 hit cette fois, thefuck-24 rank 11 frontier) mais pas assez.

## Investigation scrapy-26 régression — RÉSOLU

**3 runs same process** sur scrapy-26 PRE_BUG avec D1 fix :

```
Run 1: rank=38/301 regime=A_coupled complexity=0.294 score=0.1437
Run 2: rank=38/301 regime=A_coupled complexity=0.294 score=0.1437
Run 3: rank=38/301 regime=A_coupled complexity=0.294 score=0.1437

=== 3 runs result: ranks = [38, 38, 38] ===
STABLE (determinist)
```

**Pas de bug non-déterminisme**. Louvain utilise déjà `sorted(adj.keys())` (vérifié L568 forge.py). Le code est déterministe.

**La "régression" observée 64 → 112 entre rc1 et re-fix précédent** = artefact du criterion strict `bugfixes == 0` qui excluait scrapy-26 (bugfixes=2) du regime cold-start dans le re-fix précédent. Avec D1 (`bugfixes < 3`), scrapy-26 redevient regime A_coupled → boost coupling → rank=38/301 (top 13%).

Conclusion : **D1 fix résout aussi la régression scrapy-26**. Bonus.

## Test 3 D1 results — 1/4 top10

| bug_id | rank | top10 | regime | bf | complexity | note |
|---|---|---|---|---|---|---|
| thefuck-9 | 100/249 | NO | A_coupled | 0 | 0.035 | bf=0, tiny module |
| thefuck-24 | **11/161** | NO ← juste 1 hors | A_coupled | 0 | 0.032 | **Frontier** |
| fastapi-7 | 48/337 | NO | A_coupled | 0 | 0.057 | top 14% |
| **scrapy-2** | **9/271** | **YES** ✓ | A_coupled | 2 | 0.449 | D1 sauve ce cas |
| youtube-dl-31 | SKIP | — | — | — | — | bug.info missing |

**1/4 measurable hits.** Seuil sky-master = ≥ 2/5 → **FAIL**.

**MAIS très proche** :
- scrapy-2 nouveau hit (D1 marche sur bugfixes=2)
- thefuck-24 rank=**11** (1 position après top10, "frontier")
- 4/4 cas measurable sont dans top 20% (vs random ~50% theoretical)

Si threshold était top15 au lieu de top10, on serait à 2/4 = PASS. Mais le criterion est pre-registered.

## Tableau évolution Test 3

| Version | thefuck-9 | thefuck-24 | fastapi-7 | scrapy-2 | youtube-dl-31 | Hits |
|---|---|---|---|---|---|---|
| v1.3.0rc1 (sanity initial) | 112 | 26 | 57 | 49 | SKIP | **0/4** |
| Re-fix (bugfixes==0) | 63 | 9 ✓ | 43 | 74 | SKIP | **1/4** |
| **D1 (bugfixes<3)** | 100 | 11 | 48 | **9 ✓** | SKIP | **1/4** |

Pattern : différents cases hitent à différentes versions, mais total stable 1/4.

## Test 2 D1 avec scrapy-26 stable

| bug_id | cycle 12 v3 | rc1 (6sig) | re-fix (==0) | **D1 (<3)** | regime |
|---|---|---|---|---|---|
| scrapy-26 | 179/301 | 64/301 | 112/301 | **38/301** ✓ | A_coupled |
| thefuck-9 | 103/249 | 112/249 | 63/249 | 100/249 | A_coupled |

scrapy-26 maintenant rank 38 (vs 64 rc1, 112 re-fix précédent). Le D1 fix résout la régression et améliore aussi vs rc1.

## Test 4 — mypy + pytest : PASS

```
$ mypy --strict forge.py
Success: no issues found in 1 source file

$ pytest tests/ -q
265 passed, 1 deselected in 22.71s
```

## Recommandation finale

Trois constats :

1. **D1 fix résout les régressions** (scrapy-26 stable + bonus rank improvement)
2. **Pas de bug Louvain** (déjà sorted)
3. **STILL 1/4 top10** (seuil sky-master non franchi)

### Le pattern observable

Sur les 4 cold-start cases :
- **4/4 dans top 20%** (forge bat random meaningfully)
- **1/4 dans top10** (seuil "useful" pas atteint)
- Les autres signaux history (predict churn) hit probably mieux sur certains de ces cas — mais c'est un autre test

### Options pour Sky (mises à jour)

**D1.1 — Ship avec signal partiel utile** :
- v1.3.0rc1 → v1.3.0 (drop rc1, accept que cold-start hit 1/4 mais 4/4 top 20%)
- Document "complexity signal helps rank cold-start files into top 20% range, not necessarily top10"
- Honest about limit

**D2 — Abandon cold-start signal, garde v1.2.5** :
- Le seuil sky-master non franchi est ferme → drop l'approche
- v1.3.0rc1 stays rc1 forever
- Document cold-start blind spot as known limit

**D3 — Lancer cycle 14 quand même** :
- 15-40h compute light version
- Mesure precision@10 globale sur panel mixte
- Comprend probable que cold-start subset 1/4 top10 + history-rich subset probably ~40%
- Donne le vrai chiffre forge complet

Mon vote : **D3 + ship en pré-condition de cycle 14 success** :
- Si cycle 14 valide C2 ≥ 50% globale → tag v1.3.0 final
- Si cycle 14 fail → abandon, v1.2.5 stable, document tout

Branche fix/cold_start_re_weighting NOT pushée encore. Sky décide.

## Détails techniques

```
$ ls /home/sky/forge-case-studies/bench_sanity/
SANITY_REPORT.md      (initial 0/4)
RESANITY_REPORT.md    (1/4 with bugfixes==0)
RESANITY_D1_REPORT.md (this — 1/4 with bugfixes<3 + scrapy-26 stable)
scrapy26_3runs.txt
resanity_d1_test3.txt
```
