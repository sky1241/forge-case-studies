# Frictions admises Phase 0.3 — anti-bullshit D9

**Date** : 2026-05-10

Ce document liste les écarts factuels entre le brief idéal (3+3+3 train + 3+3+3 hold-out = 18 cas) et la réalité du tirage. Documenté **avant** toute exécution forge sur le panel.

---

## Friction 1 — Bucket `small` (1k-5k LOC) impossible à filler

**Faits factuels** :
- 0 / 17 projets BugsInPy en bucket `small` (le plus petit, PySnooper, est à 5950 LOC = bucket `medium`)
- Fallback `gh search repos --language python --stars ">5000" --limit 200` → 200 repos retournés, 181 passent E5+E6, **8 tombent en bucket small (1k-5k LOC)** par bytes Python ÷ 35
- Sur ces 8, vérification E1+E2+E3+E4 (clone shallow + grep pytest + git log) :

| Repo small candidate | E2 pytest | E3 commits | E4 fix commits 2y | Verdict |
|---|---|---|---|---|
| sherlock-project/sherlock | ✓ | 2919 | 150 | **PASS** |
| openai/whisper | ✓ | 168 | 2 | E4 fail |
| karpathy/nanoGPT | ✗ | 210 | 2 | E2+E4 fail |
| ageitgey/face_recognition | ✓ | 238 | 0 | E4 fail |
| deepseek-ai/DeepSeek-V3 | ✗ | 73 | 10 | E2+E3 fail |
| xai-org/grok-1 | ✗ | 9 | 0 | E2+E3+E4 fail |
| public-apis/public-apis | ✗ (awesome-list) | — | — | E2 fail |
| swisskyrepo/PayloadsAllTheThings | ✗ (payloads list) | — | — | E2 fail |

**Verdict** : 1 seul projet eligible (sherlock-project) sur 8 candidats small avec stars>5000.

**Décision** : ne pas inclure de cas small dans le panel. Le brief Phase 0.4 dit "publier comme friction + ajouter 'domain bias' en limite admise. NE PAS re-tirer (sinon p-hacking)." Tirer 1 cas seul (sherlock-project) ne permet pas 3 train + 3 hold-out, et inclure un échantillon non-disjoint train/holdout violerait la pre-registration. Le seuil ">5000 stars" du brief est gel.

**Conséquence** : N=12 final (6 train + 6 hold-out, tous medium ou large) au lieu de N=18 prévu.

**Impact statistique** : 
- Critère 1 (Fisher exact) : reste valide à N=6 mais power encore plus limitée
- Critère 2 (precision@10 + Wilson CI) : Wilson CI s'élargit à petit N, le seuil "borne basse ≥ 0.30" devient plus difficile à atteindre
- Critère 3 (calibration AUC delta) : 6 cas train → ~300 lignes dataset au lieu de 450

**Limite admise** mise à jour pour FINAL_REPORT.md ligne 2 :
> "Test à N=6 train + N=6 hold-out (bucket small impossible à filler depuis BugsInPy ou top stars Python). Power statistique très limitée. Tests adaptés (Fisher exact, Wilson CI, bootstrap 1000) mais conclusions à confirmer sur N≥50."

---

## Friction 2 — TRAIN bucket `large` = 3 cas du même projet (luigi)

**Faits factuels** :
- random.seed(42), bucket large = 171 bugs sur 7 projets (tornado, luigi, scrapy, fastapi, black, youtube-dl, ansible)
- Tirage seed=42 sur 171 → tombe sur **luigi-32, luigi-24, luigi-19** (3/3 cas large = luigi)
- Probabilité approx : 33/171 × 32/170 × 31/169 ≈ 0.7% (rare mais pas impossible)

**Décision** : garder le tirage seed=42 verbatim, pas de re-tir. Le brief Phase 0.4 dit "NE PAS re-tirer (sinon p-hacking)".

**Conséquence** :
- TRAIN bucket large : 100% luigi (single-project bias)
- 6 train cases couvrent seulement 4 projets : luigi (3), thefuck (1), httpie (1), cookiecutter (1)
- Si forge a un bias positif/négatif spécifique sur luigi/contrib/spark.py ou luigi/scheduler.py, ça affecte disproportionnellement les 3 cas large train

**Impact** : le rapport final doit afficher les rangs par projet (pas juste agrégé) pour repérer ce biais.

---

## Friction 3 — TRAIN diversité domaine = 2 (CLI, DevOps) sous le seuil 3

**Faits factuels** :
- 6 cas TRAIN couvrent : CLI (httpie, thefuck), DevOps (cookiecutter, luigi×3) = **2 domaines**
- Brief Phase 0.4 seuil "≥ 3 domaines parmi web/CLI/data/devops/lib"

**Décision** : friction admise (brief : "publier comme friction + ajouter 'domain bias' en limite admise. NE PAS re-tirer").

**Conséquence** : le panel TRAIN ne reflète pas la diversité Python. Forge calibré sur ce panel pourrait mal généraliser hors CLI/DevOps. Le hold-out (4 domaines : CLI, DevOps, Lib/util, Web) est plus diversifié → rapport final doit comparer perf train vs hold-out par domaine.

---

## Friction 4 — pandas, keras hors range bucket large

**Faits factuels** :
- pandas : ~639k LOC estimé (bytes/35) → > 200k = HORS bucket large strict
- keras : ~319k LOC estimé → > 200k = HORS bucket large strict
- BugsInPy contient **170 bugs pandas** + 45 keras (les 2 plus gros datasets), exclus

**Décision** : strict respect du bucket large (30k-200k LOC). pandas/keras sont en bucket "out_of_range" non-utilisé.

**Conséquence** : on perd 215 bugs (170+45) du dataset BugsInPy (sur 502 total) parce qu'ils sont sur des "ultra-large" projets. Représentativité du test biased vers projets medium-large mais pas mega-projects.

---

## Liste fermée — pas d'autres frictions découvertes après pre-registration

Toute friction additionnelle découverte APRÈS l'exécution forge sur le panel sera documentée mais ne peut PAS justifier modification du panel ou des seuils. (Sauf SKIP_REASONS techniques pré-définies dans skip_reasons.md.)
