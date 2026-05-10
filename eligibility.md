# Pre-registered eligibility — population de tirage

**Date pré-enregistrement** : 2026-05-10
**Référence brief** : Phase 0.2 (Sky cycle 11)
**Charte** : ANTI "MESURER L'EAU" — un repo n'entre dans la population QUE s'il satisfait E1-E6.
Cherry-picking post-hoc INTERDIT (cf. Phase 0.5 SKIP_REASONS list fermée).

---

## Critères d'éligibilité (E1-E6)

Un repo entre dans la population de tirage **uniquement si** TOUS les critères suivants sont satisfaits.

### E1 — Language : Python ≥ 80% du LOC source

**Vérification** : github.linguist API (`gh api repos/<owner>/<repo>/languages`) ou `cloc --include-lang=Python,JavaScript,TypeScript,C,C++ --csv` localement.

**Seuil** : Python LOC / total LOC ≥ 0.80.

**Justification** : forge est un outil Python. Un repo majoritairement HTML/notebooks ne testera pas l'algo correctement.

### E2 — Test framework : pytest est utilisé

**Vérification** : au moins UN des indicateurs suivants :
- `grep -rE "^import pytest|^from pytest" tests/` retourne ≥ 1 ligne
- `pyproject.toml` contient une référence à pytest
- `setup.py` mentionne pytest dans `tests_require` ou `extras_require`

**Justification** : forge --locate / --gen-props / --shield s'appuient sur pytest. Pas pytest = forge sous-utilisable = test biaisé.

### E3 — History : ≥ 100 commits sur main/master

**Vérification** : `git log --oneline | wc -l` ≥ 100.

**Justification** : forge --carmack a besoin d'historique pour Kalman/wavelet/coupling. < 100 commits = signal trop pauvre pour comparaison équitable.

### E4 — Bug history : ≥ 5 commits "fix" dans 2 dernières années

**Vérification** : `git log --since="2 years ago" --grep="fix\|bug\|regression" --oneline | wc -l` ≥ 5.

**Justification** : pas de bugs documentés dans 2 ans = soit project mort, soit tests insuffisants. Dans les 2 cas le test forge serait biaisé.

### E5 — Public + license open source

**Vérification** : `gh api repos/<owner>/<repo>` → `private: false` ET `license.spdx_id` ∈ {MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, PSF-2.0, LGPL-3.0, GPL-3.0, GPL-2.0, ISC}.

**Justification** : reproducibilité publique du test. Repos closed-source = test non-vérifiable.

### E6 — Pas archivé / pas read-only / pas fork

**Vérification** : `gh api repos/<owner>/<repo>` → `archived: false` ET `disabled: false` ET `fork: false`.

**Justification** : forks copient l'histoire mais peuvent diverger. Archived = state gelé non-représentatif.

---

## Stratification (Phase 0.3)

### Buckets définis (Sky-spec)

| Bucket | LOC range | Cible |
|---|---|---|
| `small` | 1 000 ≤ LOC ≤ 5 000 | 3 cas train + 3 cas hold-out |
| `medium` | 5 000 < LOC ≤ 30 000 | 3 cas train + 3 cas hold-out |
| `large` | 30 000 < LOC ≤ 200 000 | 3 cas train + 3 cas hold-out |

### Source de population

**Tentative 1** : BugsInPy (https://github.com/soarsmu/BugsInPy)
- Si chaque bucket a ≥ 6 cas eligibles E1-E6 → utiliser BugsInPy
- Cas pré-isolé bug commit + fix commit + tests dispo

**Fallback** : `gh search repos --language python --stars ">5000" --limit 200`
- Filtrer par E1-E6
- Calculer LOC pour chaque repo
- Bucket par taille
- Pour chaque repo tiré : identifier 1 bug via `git log --since="2 years ago" --grep="fix\|bug\|regression"` puis `random.seed(hash(repo_url) ^ 42)` choix dans la liste

### Tirage déterministe

```python
import random

# Train panel
random.seed(42)
panel_train = []
for bucket in ["small", "medium", "large"]:
    eligible = [r for r in population if eligible(r) and bucket_of(r) == bucket]
    panel_train.extend(random.sample(eligible, 3))

# Hold-out panel (DISJOINT)
random.seed(43)
panel_holdout = []
for bucket in ["small", "medium", "large"]:
    eligible_remaining = [r for r in population if eligible(r) and bucket_of(r) == bucket and r not in panel_train]
    panel_holdout.extend(random.sample(eligible_remaining, 3))

assert set(panel_train).isdisjoint(set(panel_holdout))  # CRITIQUE
```

### Diversité domaine (Phase 0.4 sanity check)

Après tirage, vérifier que les 9 cas train couvrent ≥ 3 domaines parmi :
- Web (django, flask, fastapi, sanic, tornado)
- CLI (httpie, thefuck, click, tqdm)
- Data/ML (pandas, keras, matplotlib, spaCy, scrapy)
- DevOps (ansible, luigi, cookiecutter)
- Lib/util (PySnooper, black)

Si < 3 domaines → publier comme friction + ajouter "domain bias" en limite admise. **NE PAS re-tirer** (sinon p-hacking).

---

## Conséquence : list excluded_repos.md

Tout repo qui ne passe pas E1-E6 → EXCLU. Documenté dans `excluded_repos.md` avec raison(s) verbatim. Pas de cherry-pick post-hoc.

---

## Une fois committé

Ce fichier + `criteria.md` + `phase0_compat_check.md` sont committés et pushés AVANT toute exécution forge sur le panel. Voir disclipline git Phase A.0.
