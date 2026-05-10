# Pre-registered temporal rules — anti-data-leakage

**Date pré-enregistrement** : 2026-05-10
**Référence brief** : Phase 0.6 (Sky cycle 11)

---

## Règle stricte (l'EST le test)

**Forge ne doit pas voir le futur.** Pour chaque cas, on simule la date où le bug N'EST PAS ENCORE introduit.

---

## Procédure (par cas)

```bash
PROJ=clones/<proj>

# 1. Date du bug commit
BUG_DATE=$(git -C $PROJ show -s --format=%ci <buggy_commit>)

# 2. Cutoff = bug_date - 4 weeks
CUTOFF_DATE=$(date -d "$BUG_DATE - 4 weeks" +%Y-%m-%d)

# 3. PRE_BUG = dernier commit avant CUTOFF
PRE_BUG=$(git -C $PROJ rev-list -n 1 --before=$CUTOFF_DATE HEAD)

# 4. Checkout
git -C $PROJ checkout $PRE_BUG

# 5. Vérification anti-leakage : aucun commit après PRE_BUG ne doit être visible
AFTER=$(git -C $PROJ log --since=$CUTOFF_DATE --oneline | wc -l)
if [ $AFTER -gt 0 ]; then
    SKIP_REASON="future_commits_visible"
    # voir skip_reasons.md
fi

# 6. Run forge (NE VOIT QUE le history pre-bug)
forge --carmack --weeks 4 . > carmack.txt
```

---

## Justifications

- **4 semaines avant** : permet à `--weeks 4` (history horizon) de couvrir une fenêtre temporelle complète sans voir le bug.
- **HEAD = PRE_BUG après checkout** : `--weeks 4` regarde 4 sem avant HEAD, donc 4 sem avant PRE_BUG (cohérent).
- **Vérification post-checkout** : si des commits restent visibles après le cutoff, c'est probablement une branche pollutée → SKIP.

---

## Cas particulier : bugs très anciens

Si le bug est plus vieux que 2 ans :
- E4 garantit ≥ 5 fix commits dans 2 ans → on ne tire que des bugs récents
- Mais si le bucket impose un bug ancien : checker que `--weeks 4` ne tombe pas avant le premier commit du repo

---

## Cas particulier : forks ou rebase

Si `--before=$CUTOFF_DATE HEAD` retourne vide (pas de commit antérieur trouvé) :
- SKIP avec `bug_commit_missing` ou `shallow_history` selon le diagnostic

---

## Verbatim attendu après checkout

```
$ git -C clones/<proj> log --oneline -1
<PRE_BUG_HASH> <message du PRE_BUG commit>

$ git -C clones/<proj> log --since=2026-04-15 --oneline | wc -l
0  # 0 = clean, > 0 = future_commits_visible (SKIP)
```

---

## Une fois la mesure faite

Restaurer l'état :
```bash
git -C $PROJ checkout main  # ou master, selon le repo
```

Pour ne pas polluer les runs suivants si le clone est partagé.
