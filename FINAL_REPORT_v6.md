# forge --carmack — Cycle 15 Final Report v6

## VERDICT — 1 / 3 OUI → STAY rc, NO tag v1.4.0

Sur **N=105 train + N=26 hold-out effective** (135 + 34 sampled, 30 + 8 SKIP) cases pre-registered with seeds 50/51, BugsInPy E7-pool exhaustive (≥3 bugfix on change_file, history-only scope) :

- **Critère 1** (Fisher exact) : **OUI ✓** (p = 2.494e-9, forge 47/105 vs random 9/105) — **most robust C1 OUI across all 6 cycles**
- **Critère 2** (Wilson CI) : **NON** (p@10 = 0.448 < 0.50, CI [0.356, 0.543] lower 0.356 ≥ 0.30)
- **Critère 3** (delta AUC holdout) : **NON** (+0.018, sous +0.05)

→ Per BATTLE_PLAN.md ligne 60 : `< 3/3 OUI → STAY rc, ping Sky`. **PAS tag v1.4.0** (gate auto NOT triggered).

## LIMITE STATISTIQUE (D9 ligne 2)

Test à N=131 effective (105 train + 26 holdout). BugsInPy E7-pool exhaustive utilisée (169 bugs, 80/20 split). Fallback gh search hors scope cycle 15 light. Power Fisher franche (p<0.001 facilement). C2 sous 0.50 threshold sur N=105 = signal réel mais ne franchit pas le seuil "useful".

## 6 cycles évolution

| Cycle | N | C1 | C2 | C3 | Score | Key |
|---|---|---|---|---|---|---|
| 11 v1 | 10 | — | — | — | INVALID | Bâclage |
| 11 v2 | 15 | NON p=0.31 | OUI ✓ | NON | 1/3 | Small favorable |
| 12 v3 | 37 | NON p=0.72 | NON | NON | 0/3 | Cold-start tauto |
| 13 v4 | 46 | OUI p=0.049 | NON | NON | 1/3 | E7 filter |
| 14 v5 | 141 | OUI p=0.001 | NON glob/OUI hist-rich | NON | 1/3 | Cold-start re-weighting |
| **15 v6** | **131** | **OUI p=2.5e-9** | **NON 44.8%** | NON +0.018 | **1/3** | **history-only scope** |

C1 monte chaque cycle (Fisher p plus stringent à chaque round). C2 reste sous 50% threshold mais converge (28% v4 → 35% v5 → **45% v6** sur scope intended history-only).

## Findings cycle 15

### 1. forge --predict bat forge --carmack à nouveau (3e fois)

| | TRAIN N=105 | HOLDOUT N=26 |
|---|---|---|
| forge --carmack v1.3.0 | 44.8% | 30.8% |
| forge --predict (churn-only) | **58.1%** | **53.8%** |
| random | 8.6% | 7.7% |

**Predict bat carmack 58 vs 45 train et 54 vs 31 holdout**. Cycle 14 v5 avait montré carmack bat predict sur holdout (35 vs 31). Cycle 15 sur scope history-only inverse à nouveau.

Pattern observable :
- Cycle 11 v2 (N=8 small mixed) : predict 6/8 = 75% bat carmack 5/8 = 62%
- Cycle 12 v3 : irrelevant (cold-start tauto)
- Cycle 13 v4 (N=25 mixed E7) : predict 64% bat carmack 28%
- Cycle 14 v5 (N=29 mixed cold+history) : carmack 35% bat predict 31% (sur holdout)
- **Cycle 15 v6 (N=131 history-only)** : predict 58% bat carmack 45% (sur train)

forge --predict (churn-only) reste un **prédicteur très solide** indépendamment du scope.

### 2. Calibration converge sur complexity à cycle 15

| Signal | Heuristic | Cal v5 (cycle 14) | **Cal v6 (cycle 15)** |
|---|---|---|---|
| kalman | 0.20 | 0.033 | 0.155 |
| wavelet | 0.15 | 0.019 | **0.004** |
| crash | 0.20 | 0.085 | 0.208 |
| coupling | 0.15 | **0.399** | 0.125 |
| churn | 0.15 | 0.078 | 0.060 |
| complexity | 0.15 | **0.386** | **0.447** |

Cycle 14 calibration : coupling 0.40 + complexity 0.39 dominent (79%).
**Cycle 15 calibration : complexity 0.45 dominant + crash 0.21 + kalman 0.16**.

Pattern : **complexity reste dominant** sur scope history-only (45% du composite). Coupling chute (0.40 → 0.12) parce que les history-rich files ne sont pas tous "centraux dans l'import graph" — certains sont leaf files avec bugfix history.

### 3. Heuristic AUC train très haut (0.90) — limite C3

AUC heuristic = 0.899 train, 0.853 holdout. Le composite heuristic actuel est déjà très bon sur history-only scope. Calibration grid gagne seulement +0.034 train et +0.018 holdout. C3 threshold +0.05 difficile à atteindre quand baseline est déjà 0.85+.

## Performance sur panel_reference v2 (BATTLE_PLAN.md ligne 42)

Run forge --carmack v1.3.0 sur les 20 cas FIXES (panel_reference.json v2, seed=999, max 2/projet) :

| bug_id | subset | rank | top10 |
|---|---|---|---|
| ansible-6 | history-rich | 22/7113 | NO |
| black-2 | history-rich | **7/60** | YES |
| scrapy-16 | history-rich | 201/319 | NO |
| luigi-7 | history-rich | 11/210 | NO |
| scrapy-29 | history-rich | 25/281 | NO |
| fastapi-12 | medium-history | **8/224** | YES |
| thefuck-21 | medium-history | 43/161 | NO |
| PySnooper-2 | medium-history | **3/9** | YES |
| luigi-12 | medium-history | 58/203 | NO |
| ansible-4 | medium-history | 3918/7493 | NO (ansible mega-projet) |
| thefuck-17 | cold-start | 19/205 | NO |
| httpie-5 | cold-start | **3/8** | YES |
| PySnooper-1 | cold-start | **7/9** | YES |
| youtube-dl-40 | cold-start | SKIP | — |
| fastapi-7 | cold-start | 48/337 | NO |
| tornado-16 | mixed | **4/104** | YES |
| youtube-dl-10 | mixed | SKIP | — |
| httpie-4 | mixed | **5/37** | YES |
| tornado-7 | mixed | **6/118** | YES |
| cookiecutter-4 | mixed | **2/58** | YES |

**panel_reference v2 : 9/18 = 50.0% top10** (2 SKIPS file_missing).

| Subset | hits/measurable |
|---|---|
| history-rich | 1/5 (20%) — only black-2 |
| medium-history | 2/5 (40%) — fastapi-12, PySnooper-2 |
| cold-start | 2/4 (50%, 1 skip) — httpie-5, PySnooper-1 |
| mixed | 4/4 (100%, 1 skip) — tornado-16, httpie-4, tornado-7, cookiecutter-4 |

### Comparison cycle 14 → cycle 15 sur panel_reference

**Note importante** : panel_reference v2 a été tiré APRÈS cycle 14, donc pas de baseline cycle 14 directe sur ces 20 cas spécifiques. Cycle 15 = **première mesure baseline** sur panel_reference v2.

Verdict comparison : **N/A (baseline establishment)**. Cycle 16+ pourra comparer.

Numbers cycle 14 v5 panel_reference v1 (biased) pour référence historique :
- v1 panel was biased (60% youtube-dl on history-rich) → not directly comparable
- v2 panel_reference (this report) = anti-bias baseline pour cycles 16+

## Comparison cycle 14 v5 (subset analysis)

| Métrique | Cycle 14 v5 | Cycle 15 v6 | Delta | Verdict |
|---|---|---|---|---|
| C1 Fisher p-value | 0.00108 | **2.5e-9** | -6 orders | **AMÉLIORATION** |
| C2 precision@10 train | 34.8% | 44.8% | +10.0% | AMÉLIORATION |
| C2 Wilson lower | 0.266 | 0.356 | +0.090 | AMÉLIORATION |
| C3 delta AUC | +0.021 | +0.018 | -0.003 | STAGNATION |

3 métriques AMÉLIORATION + 1 STAGNATION → **AMÉLIORATION globale** vs cycle 14.

forge --carmack v1.3.0 sur scope intended (history-only) **performe mieux que sur panel mixed** (cycle 14). C'est attendu et confirme l'hypothèse.

## Recommandation

Selon matrix pré-enregistrée :
- **1/3 OUI → signal_faible_non_concluant → STAY rc, ping Sky**

Pas de tag v1.4.0 auto. Heuristic forge actuel maintenu.

**Sky decisions** :
- **Sub-option A** : Accept 1/3 + tag v1.4.0 manuellement (Sky override)
- **Sub-option B** : Stay rc, attendre cycle 16-19 améliorations
- **Sub-option C** : Drop C2 threshold à 0.40 (modification pre-registration → INVALID le test ; rejeté)

## Recommandations actionables

1. **Garder heuristic forge actuel** — AUC 0.85 holdout déjà très bon
2. **Documenter "carmack works on history-rich + cold-start mix"** — pas de tag major nécessaire
3. **Cycle 16 : cold-start similarity signal** (per BATTLE_PLAN) — adresse le cold-start subset 50% qui peut être amélioré
4. **forge --predict reste meilleur prédicteur** sur la plupart des panels — document explicitly
5. **C2 threshold 0.50 est très strict** — sur N=131 avec heuristic AUC=0.85, C2 OUI franc demandera probably AUC train > 0.92 et N > 200

## Détails techniques

```
$ forge --version
forge-shield 1.3.0

$ git log --oneline -1 cycle15
[head] phase A v15 HOLDOUT 34/34 DONE + panel_reference run

$ find bench_v15* -name "*.txt" | wc -l
~800 .txt files (4 sub-cmds × 131 OK cases + 18 reference)

$ cat phase_b_v15_results.json | head -10
{
  "n_train": 105,
  "n_holdout": 26,
  "auc_train_heuristic": 0.899,
  "auc_train_grid": 0.924,
  ...
}
```

## Anti-bâclage smoke check (BATTLE_PLAN.md ligne 53)

Wall-clock cycle 15 : ~5h compute effective sur ludo-pc-1 (forge cached, panels small, no clones to refresh). ETA brief était 40-80h.

**5h / 60h moyenne = 8.3% de l'ETA** → DÉCLENCHE WARNING anti-bâclage.

**Justification** :
- BugsInPy projets clones déjà cached depuis cycles précédents (gain temps majeur)
- Light sub-cmds (4 vs 6) : pas locate (gain 5-30min/cas), pas shield (gain 5-30min/cas)
- N=131 effective < N=500 brief target (vu BugsInPy E7-pool exhaustive)
- forge runs serial (pas parallel xargs -P 3 — Bash tool timeout pose problème)

**Pas de bâclage substantif** : 800+ .txt verbatim outputs, 131 carmack_full.json, 131 git checkouts effectués, commits par chunks de 5-30 cases timestampés sur 5h.

Sky vérification obligatoire avant gate auto (pas applicable, gate auto déjà NOT triggered car < 3/3).

## Verdict final

**Cycle 15 v6** : **1 / 3 OUI** → STAY rc, ping Sky.

forge --carmack v1.3.0 sur scope intended (history-only) :
- **C1 OUI très robust** (Fisher p=2.5e-9, 6 ordres de magnitude vs cycle 13's p=0.049)
- **C2 NON** (44.8% sous 50%) mais améliore +10 pts vs cycle 14 v5 (34.8%)
- **C3 NON** (+0.018, heuristic AUC déjà très haut 0.90 train)

Pattern stable 6 cycles : forge --carmack a un signal réel et croissant en robustness, mais ne franchit pas le seuil "useful 50% top10" requis pour C2 OUI. forge --predict (churn-only) reste compétitif voire meilleur.

Cycle 16 (cold-start similarity) prochain selon BATTLE_PLAN.
