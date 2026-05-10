# Excluded repos — population de tirage

**Date** : 2026-05-10
**Référence** : eligibility.md E1-E6

Liste des projets considérés mais exclus de la population de tirage avec raison verbatim.

---

## Exclusions BugsInPy (4 / 17 projets)

| Project | Raison eligibility | Verdict |
|---|---|---|
| matplotlib/matplotlib | E5 fail : `license=null` sur gh api (custom PSF-style license non auto-détectée) | exclu |
| huge-success/sanic | E1 fail : Python 68.4% < 80% threshold | exclu |
| explosion/spaCy | E1 fail : Python 54.1% < 80% threshold (Cython et C présents) | exclu |
| tqdm/tqdm | E5 fail : `license=NOASSERTION` sur gh api (license non auto-détectée) | exclu |

## Exclusions BugsInPy par bucket out_of_range (LOC > 200k)

| Project | LOC estimé | Raison | Bugs perdus |
|---|---|---|---|
| pandas-dev/pandas | 639 167 | LOC > 200k = hors bucket large strict | 170 |
| keras-team/keras | 318 910 | LOC > 200k = hors bucket large strict | 45 |

**Total bugs perdus** : 215 / 502 BugsInPy bugs (43% du dataset, mais sur projets ultra-larges non représentatifs des "vrais" Python apps).

## Exclusions fallback gh search (top 60 stars Python, bucket small uniquement)

| Repo | Bytes Python | LOC est. | Eligibility verdict |
|---|---|---|---|
| public-apis/public-apis | 40 479 | 1156 | E2 fail (awesome-list, pas de pytest) |
| openai/whisper | 159 343 | 4552 | E4 fail : 2 fix commits 2y < 5 |
| karpathy/nanoGPT | 51 670 | 1476 | E2 fail (no pytest) + E4 fail (2 fix 2y) |
| ageitgey/face_recognition | 35 036 | 1001 | E4 fail : 0 fix commits 2y |
| swisskyrepo/PayloadsAllTheThings | 80 988 | 2313 | E2 fail (payloads list, pas de pytest) |
| deepseek-ai/DeepSeek-V3 | 57 381 | 1639 | E2 fail (model release) + E3 fail (73 < 100 commits) |
| xai-org/grok-1 | 77 280 | 2208 | E2 fail (model release) + E3 fail (9 commits) + E4 fail (0) |

**Verdict bucket small** : 1 seul projet eligible (sherlock-project/sherlock) sur 8 candidats top-stars → insuffisant pour 3 train + 3 hold-out → bucket small documenté en friction.md.

---

## Conséquence

Population finale de tirage = 13 projets BugsInPy en range strict :
- medium (5k-30k LOC) : 4 projets / 44 bugs
- large (30k-200k LOC) : 7 projets / 171 bugs

Total population = 215 bugs eligibles, distribués 0 small + 44 medium + 171 large.
