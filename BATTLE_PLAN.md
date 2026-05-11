# BATTLE_PLAN cycles 15-20+ — forge orchestration scientifique autonome

**Date** : 2026-05-11
**Contexte** : forge v1.3.0 shipped on PyPI ([package page](https://pypi.org/project/forge-shield/1.3.0/)) après 5 cycles d'iteration empirique (cycle 11 v2 → cycle 14 v5). Verdict cumulé : C1 OUI robust (Fisher p=0.001 à N=141), C2 OUI sur scope history-rich (53% top10), C3 NON (calibration delta +0.021).

**Plan** : 6 cycles (15-20) sur ~200-460h compute multi-semaines pour valider definitively forge + livrer v2.0.0 produit complet.

**3 gates Sky obligatoires** :
1. **Cycle 20 v2.0.0** : release "produit complet" = décision business Sky
2. **PyPI publish (tous cycles)** : jamais auto
3. **Merge feature refactor forge.py** (cycles 16/19) : auto si comparison panel_reference stable, sinon ping Sky

---

## Rails communs (charte anti-bullshit applicable à TOUS les cycles)

1. **Pre-registration committed AVANT runs** : criteria_vN.md + eligibility_vN.md + panel_train_seedN.json + panel_holdout_seedN+1.json committed sur la branche cycle dédiée AVANT toute exécution forge sur le panel.
2. **Verbatim outputs** : `bench_vN/results/<bucket>/<bug_id>/*.txt` (carmack/modularity/predict/fastdeep/locate/shield selon cycle) commits avec hash git du HEAD forge utilisé.
3. **Commits incrémentaux par 10 cas minimum** : si total commits < N_panel / 10, FINAL_REPORT doit justifier (e.g. "batch script crash recovery"). Sinon = suspect.
4. **mypy --strict + pytest verbatim dans commit bodies** si touche `forge.py`. Pas optionnel.
5. **D9 admit losses ligne 1 du FINAL_REPORT_vN.md** : si verdict négatif, mettre l'aveu en premier. Pas de soft-pedal.
6. **Skip reasons fermées par cycle** : `skip_reasons_vN.md` liste fermée des motifs valides pour exclure un cas après tirage. Pas de nouveau motif post-run.
7. **Hold-out indépendant** : seeds disjoints inter-cycles (cycle 14 = 48/49 ; cycle 15 = 50/51 ; cycle 16 = 52/53 ; etc.). Vérification empty intersect train ∩ holdout.
8. **Anti-pattern strict** :
   - **Zero re-tirage post-hoc** (même si verdict défavorable)
   - **Zero modification des critères post-run**
   - **Zero cherry-pick** des skips (raisons doivent être dans la liste fermée)

---

## Panel reference constant (panel_reference.json, seed=999)

20 cas FIXES, committed permanent, **tirés une fois maintenant**. Chaque cycle 15+ doit run forge --carmack sur ces 20 cas et publier les ranks dans le FINAL_REPORT. Permet comparison cycle-après-cycle sur même bugs.

Stratification :
- **5 history-rich** (bugfixes ≥ 3 sur change_file) — scope intended forge --carmack
- **5 cold-start** (bugfixes 0) — blind spot identifié cycle 12-14
- **5 medium-history** (bugfixes 1-2) — transition
- **5 mixed** (random sample) — sanity

### Tableau obligatoire dans CHAQUE FINAL_REPORT_vN+1

```markdown
## Performance sur panel_reference vs cycle précédent

| Métrique | Cycle N-1 | Cycle N | Delta | Verdict |
|---|---|---|---|---|
| precision@10 panel_reference | X% | Y% | +Z | AMÉLIORATION / STAGNATION / RÉGRESSION |
| AUC panel_reference | X | Y | +Z | idem |
| Fisher p panel_reference | X | Y | mieux/pareil/pire | idem |
```

**Si RÉGRESSION sur ≥ 2 métriques → STOP cycle suivant, ping Sky obligatoire.**

---

## Anti-bâclage smoke check

```
SI wall-clock effectif cycle N < 30% de l'ETA estimé :
  → FINAL_REPORT inclut WARNING "completed in X% of estimated time, possible bâclage"
  → Sky vérification obligatoire avant gate auto
  → Gate auto NE déclenche PAS le bump version
```

Précédent : cycle 11 v1 was 30 min vs 5-6 jours brief = 0.4% → bâclage admis, INVALID reverted.

---

## Gates auto vs Gates Sky

| Gate | Type | Condition |
|---|---|---|
| Cycle 15 verdict | Auto | si critères pré-reg atteints, `git tag v1.4.0` + push, **PAS PyPI** |
| Cycle 16 cold-start signal | Auto | si comparison panel_reference = AMÉLIORATION ou STAGNATION, bump v1.5.x |
| Cycle 17 locate scale | Auto | si verdict OK + no regression panel_reference, bump v1.6.x |
| Cycle 18 shield scale | Auto | si verdict OK + no regression, bump v1.7.x |
| Cycle 19 ablation | Auto | si performance maintenue panel_reference, bump v1.8.x |
| **Cycle 20 v2.0.0** | **SKY OBLIGATOIRE** | Décision business "produit complet" |
| **PyPI publish (tous cycles)** | **SKY OBLIGATOIRE** | jamais auto, twine upload manuel après GO |
| **Merge feature → main forge.py** (cycles 16/19) | Auto si comparison stable, sinon ping Sky | dépend du cycle |

---

## Cycles 15-20 briefs détaillés

### Cycle 15 — carmack scope-intended (history-only N=500)

**Mission** : valider C2 OUI propre sur le scope intended de forge --carmack (files avec bugfix history riche).

| Champ | Valeur |
|---|---|
| Panel | N=500 (400 train + 100 holdout), E7 strict (≥3 bugfix), seeds 50/51 |
| Source | BugsInPy E7 pool 169 + fallback gh search Python projects |
| Pre-registration files | criteria_v15.md + eligibility_v15.md (E1-E7) + panel_train_seed50.json + panel_holdout_seed51.json |
| Forge sub-cmds | Light : carmack + modularity + predict + fast-deep (pas locate, pas shield) |
| Critères verdict | C1 Fisher exact p<0.05, C2 Wilson p@10≥0.50 lower≥0.30, C3 delta AUC≥+0.05 |
| Compute estimé | **40-80h wall-clock** (xargs -P 3) |
| Gate post-cycle | Auto : si 3/3 OUI → tag v1.4.0 (pas PyPI) ; si <3 → STAY rc, ping Sky |
| Failure modes | Si >30% pip_install fail → fallback gh search. Si forge crash >30% → STOP ping Sky. Si BugsInPy rate-limited → suspend. |

### Cycle 16 — cold-start signal refactor (similarity-based)

**Mission** : ajouter signal "code similarity" (n-grams Python ou AST embedding) au carmack pour sauver les cas cold-start (cycle 14 v5 : 15.4% top10 sur cold-start subset).

| Champ | Valeur |
|---|---|
| Dev | 5-10h forge.py — nouvelle fonction `_compute_similarity_score` pure Python stdlib (n-grams ou Jaccard AST nodes). |
| Panel | Cold-start dédié N=50 (E7 fail, bugfixes < 3), seeds 52/53 |
| Critère principal | Signal aide cold-start ≥ +30% top10 vs cycle 14 baseline (15.4% → ≥45%) |
| Panel reference check | Pas de régression sur 20 cas constants (≥ stagnation) |
| Compute estimé | **20-40h** (dev + run cold-start panel) |
| Gate post-cycle | Auto si signal aide ET pas régression panel_reference → bump v1.5.x. **Merge feature forge.py auto si OK**. Sinon ping Sky. |
| Failure mode | Si signal n'aide pas (delta < +10% cold-start) → drop feature, STOP, ping Sky |

### Cycle 17 — locate à scale (pyenv per-case)

**Mission** : tester forge --locate sur 30 cas avec setup pyenv 3.7/3.8/3.9/3.10 dynamique selon `bug.info` BugsInPy `python_version`.

| Champ | Valeur |
|---|---|
| Mission | Setup pyenv per-case + run forge --locate + capture verbatim |
| Panel | 30 cas pré-tirés pour Python 3.7-3.10 coverage, seeds 54/55 |
| Compute estimé | **30-60h** (5-10 min pyenv per case + 30s locate) |
| Critère verdict | forge --locate produit ranking exploitable ≥ 70% cas (rang change_file dans top 30) |
| Gate post-cycle | Auto si OK → bump v1.6.x (doc README "--locate works with pyenv") |
| Failure mode | Si crash systématique pyenv (>50% cas) → drop --locate scope. Document limit "requires Python runtime match". |

### Cycle 18 — shield à scale

**Mission** : tester forge --shield orchestration end-to-end sur 20 cas (1 par bucket × 6 buckets × ~3 cycles).

| Champ | Valeur |
|---|---|
| Panel | 20 cas mixed (E7 + cold-start), seeds 56/57 |
| Compute estimé | **20-40h** (shield 1800s timeout / cas) |
| Critère verdict | shield exit code 0 sur ≥ 80% cas + output cohérent (stages 1→2→3 produits) |
| Gate post-cycle | Auto si OK → bump v1.7.x |
| Failure mode | Si shield crash >30% → STOP, ping Sky pour refactor shield orchestration |

### Cycle 19 — ablation study (drop kalman + wavelet)

**Mission** : re-run cycle 15 panel mais avec carmack 4 signaux (sans kalman, sans wavelet) — vérifier si le composite simplifié maintient performance.

| Champ | Valeur |
|---|---|
| Panel | Réutilise cycle 15 panel (seeds 50/51 — pas re-tirage = comparison directe) |
| Dev | 2-3h forge.py : flag `--carmack-minimal` qui drop kalman + wavelet |
| Compute estimé | **20-40h** (réutilise dataset cycle 15, juste re-compute composite scores) |
| Critère verdict | precision@10 maintenue sur panel_reference (delta < ±2%) |
| Gate post-cycle | Auto si performance maintenue → simplifier carmack defaults (4 signaux), bump v1.8.x. **Merge feature forge.py auto si OK**. Sinon ping Sky. |
| Failure mode | Si performance chute > 5% precision@10 → garder 6 signaux, document, STOP |

### Cycle 20 — sanity light outils restants (gen-props, minimize, snapshot, watch)

**Mission** : sanity check chaque outil forge non-testé sur 5-10 cas démo, vérifier qu'il marche en pratique.

| Champ | Valeur |
|---|---|
| Outils testés | --gen-props (10 cas), --minimize (5 cas), --snapshot (5 cas), --watch (3 cas démo), --bisect (3 cas), --flaky (3 cas) |
| Compute estimé | **5-10h total** (pas tests à scale, juste sanity) |
| Critère verdict | Chaque outil exit code 0 + output documenté ≥ 80% cas |
| Gate post-cycle | **SKY OBLIGATOIRE** : tag v2.0.0 = décision Sky "produit complet ready" |
| Failure mode | Si crash systématique sur 1 outil → document Honest Limit, drop par décision Sky |

---

## Failure modes globaux (applicables tous cycles)

| Trigger | Action |
|---|---|
| Forge crash > 30% panel | STOP cycle, ping Sky |
| BugsInPy access issue (GitHub rate-limit) | Suspend cycle, reprise après reset |
| Compute machine down | Suspend, reprise au chunk suivant (idempotent runner) |
| Régression panel_reference ≥ 2 métriques | STOP, ping Sky obligatoire |
| Cycle N wall-clock < 30% ETA | WARNING dans FINAL_REPORT, Sky check obligatoire |
| Pre-registration committed APRÈS run (oubli) | INVALID le cycle entier, revert tag, recommencer (cf cycle 11 v1) |

---

## Reproductibilité

Pour chaque cycle, le commit du FINAL_REPORT_vN doit contenir :

```markdown
## Reproductibilité

- criteria : [criteria_vN.md](criteria_vN.md) commit hash X
- eligibility : [eligibility_vN.md](eligibility_vN.md) commit hash Y
- panel files : [panel_train_seed*.json] + [panel_holdout_seed*.json]
- forge.py hash : git show forge.git HEAD → SHA
- forge --version output verbatim
- wall-clock start/end : 2026-XX-XX HH:MM → HH:MM (UTC+2)
- Compute machine : ludo-pc-1 ou autre

```bash
git clone forge-case-studies && git checkout cycle{N}
python3 phase0_v{N}_sample.py
python3 run_phase_a_v{N}.py train
python3 run_phase_a_v{N}.py holdout
python3 phase_b_v{N}.py
\```
```

---

## Récap timing total

| Cycle | ETA compute |
|---|---|
| 15 | 40-80h |
| 16 | 20-40h |
| 17 | 30-60h |
| 18 | 20-40h |
| 19 | 20-40h |
| 20 | 5-10h |
| **Total** | **135-270h compute + 65-190h Sky review/dev = 200-460h multi-semaines** |

---

## Démarrage cycle 15

**PAS LANCER sans GO Sky explicite.** Sky veut review ce BATTLE_PLAN d'abord.

Quand Sky GO → :
1. `git checkout -b cycle15` sur forge-case-studies
2. Code phase0_v15_sample.py (E7 strict, N=500, seed=50/51)
3. Pre-register criteria_v15 + eligibility_v15 + panel files
4. Phase A v15 par chunks de 25-50 cas (commits incrémentaux)
5. Phase B v15 calibration grid 10000 samples + logreg + RF
6. FINAL_REPORT_v15.md avec verdict 3/3 ou inférieur + panel_reference comparison
7. Si gate auto déclenche : git tag v1.4.0 + push (pas PyPI)
8. Ping Sky avec FINAL_REPORT_v15 chiffré + comparison panel_reference

— sky-master / cousin pc1 (orchestration agréée)
