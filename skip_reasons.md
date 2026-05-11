# Pre-registered SKIP_REASONS — liste fermée (anti cherry-picking post-hoc)

**Date pré-enregistrement** : 2026-05-10
**Référence brief** : Phase 0.5 (Sky cycle 11)

---

## Règle d'or

**TOUTE raison de skipper un cas APRÈS tirage doit être dans cette liste fermée.**

Si je trouve un nouveau motif non listé → je l'ajoute ici **AVANT d'avoir vu le résultat du run forge** (commit dans le repo). Sinon = INTERDIT, le cas reste dans le panel même si "raté".

---

## Liste fermée (9 SKIP_REASONS — E7 ajouté cycle 13)

| Code | Description | Vérification |
|---|---|---|
| `not_git` | Pas de `.git` après clone | `[[ -d clones/<proj>/.git ]]` faux |
| `shallow_history` | git log < 30 commits effectifs après clone full | `git -C <proj> log --oneline \| wc -l` < 30 |
| `no_test_dir` | Ni `tests/`, ni `test/`, ni `*_test.py`, ni `test_*.py` | trouvé via `find . -name "tests" -o -name "test" -o -name "*_test.py" -o -name "test_*.py"` |
| `forge_crashed` | timeout 600s OU exit code ≠ 0 sur `forge --carmack` | `[[ $? -ne 0 ]]` |
| `bug_commit_missing` | `git checkout <buggy_commit>` échoue (force-push) | exit ≠ 0 |
| `file_missing_at_pre` | change_file n'existe pas au commit PRE_BUG | `git -C <proj> show $PRE_BUG:<file>` exit ≠ 0 |
| `docker_required` | BugsInPy bug requiert Docker non disponible | `info.txt` du bug mentionne `docker` |
| `future_commits_visible` | Après checkout PRE_BUG, des commits postérieurs au cutoff sont visibles | `git -C <proj> log --since=$CUTOFF --oneline \| wc -l` > 0 |
| `cold_start_blind_e7` (cycle 13) | change_file a < 3 bugfix commits avant PRE_BUG → carmack signals all 0 par construction (mesurer eau sur voltmètre) | `git log --until=PRE_BUG_DATE --grep=fix\|bug\|patch\|regression -i -- $change_file \| wc -l` < 3 |

---

## Procédure de re-tirage

Si **2+ skip dans un même bucket** :
1. Documenter chaque skip avec verbatim de la commande qui a échoué
2. Re-tirer pour ce bucket avec `seed=42+1`, puis 42+2, etc.
3. Continuer jusqu'à atteindre 3 cas validés par bucket
4. Documenter chaque re-tirage dans `panel_train_seed42.json` (champ `re_tirages: [{seed: 43, reason: ...}, ...]`)

**Limite** : si 5 re-tirages par bucket ne suffisent pas → bucket failed, publier en friction + N réduit dans le rapport final.

---

## Conséquence : interdiction stricte

**INTERDIT** :
- "Le cas X marche pas comme je voulais" (pas de raison technique = on le garde)
- "Le résultat semble bizarre" (D9 admit losses)
- "Forge a un score étrange ici" (c'est l'observation, pas une raison de skip)
- Modifier ce fichier APRÈS avoir vu un résultat de run forge

Si la pression mentale pousse à skipper un cas → relire ce fichier + criteria.md.
