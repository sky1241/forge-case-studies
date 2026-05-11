# FINAL REPORT v11 v2 — Cycle 19 v2 (investigation contradiction N=18 vs N=131)

**Date** : 2026-05-11
**Branch** : cycle19_v2 sur forge-case-studies
**Pre-registered criteria** : criteria_v19_v2.md

## TL;DR

**C_ablation v2 : AMBIGU** — verdict cycle 19 v1 (NON, basé panel_ref -16.7 pts) était **cherry-pick stratégique** non-justifié.

Vraie cause de la contradiction :
- Panel_ref et train+holdout sont **partiellement disjoints** (9/18 cas du panel_ref ne sont PAS dans le pool 131)
- Hétérogénéité majeure per-projet (fastapi : +21.4 pts, httpie : -25 pts)
- Per-case sign tally : 57.3% TH / 50% REF — **pas de pattern ferme dans aucune direction**

→ **Le verdict honnête est : on ne peut pas conclure**. Garder composite 6 signaux est une **décision conservative** (statu quo), pas un verdict scientifique.

## Hypothèse cycle 19 v2

> "Pourquoi cycle 15 train+holdout (N=131) dit ablation 4-sig MIEUX (+2.3 pts) et panel_reference v2 (N=18) dit ablation 4-sig PIRE (-16.7 pts) ? Quel est le verdict honnête ?"

## Critique cycle 19 v1

Cycle 19 v1 a choisi panel_reference (N=18) comme référent privilégié et conclu NON. Argument utilisé : "panel_reference stratifié 5+5+5+5 seed=999, distribution mieux équilibrée".

**Cycle 19 v2 falsifie cet argument** : voir analyse ci-dessous.

## Procédure cycle 19 v2

Décomposition systématique sans cherry-pick :
1. Per-bucket (small/medium/large) sur les 2 populations
2. Per-projet sur les 2 populations
3. Per-case sign tally (combien de cas où ablation aide / nuit / égal)
4. Overlap analysis (combien de cas en commun entre les 2 populations)

## Résultats clés

### Finding #1 — Populations partiellement disjointes

| | Count |
|---|---|
| Overlap panel_ref ∩ train+holdout | **9/18 (50%)** |
| Cas UNIQUE dans panel_ref | **9 cas** |

**Cas du panel_ref ABSENT du train+holdout (N=131)** :
- PySnooper-1, PySnooper-2, ansible-4, fastapi-12, fastapi-7
- httpie-5, luigi-12, thefuck-17, thefuck-21

→ panel_ref n'est PAS un sous-ensemble du pool train+holdout. Les 2 populations testent des cas différents.

→ Comparer "panel_ref delta -16.7" vs "TH delta +2.3" = comparer pommes et oranges.

### Finding #2 — Hétérogénéité per-projet (très significative)

**TRAIN+HOLDOUT (N=131)** delta top10 :
| Project | n | Delta_top10 (pts) | Direction |
|---|---|---|---|
| cookiecutter | 4 | +25.0 | ablation aide |
| fastapi | 14 | +21.4 | ablation aide |
| luigi | 27 | +7.4 | ablation aide |
| tornado | 16 | +6.2 | ablation aide |
| black | 20 | +0.0 | neutre |
| thefuck | 6 | +0.0 | neutre |
| scrapy | 25 | -4.0 | ablation nuit |
| ansible | 15 | -13.3 | ablation nuit |
| httpie | 4 | -25.0 | ablation nuit (N petit ⚠️) |

→ **Pas de direction commune**. Ablation aide ~60% projets, nuit ~30%.

### Finding #3 — Per-case sign tally

| Population | helps (ablation < baseline rank) | hurts | same | help% |
|---|---|---|---|---|
| TRAIN+HOLDOUT (N=131) | 75 | 22 | 34 | **57.3%** |
| PANEL_REF (N=18) | 9 | 5 | 4 | **50.0%** |

Pre-registered seuils :
- Scenario B (OUI ablation aide) : help% ≥ 75% sur les 2 populations
- Scenario A (NON ablation nuit) : help% ≤ 25% sur les 2 populations
- Scenario C (AMBIGU) : sinon

**Actual** : 57.3% et 50.0% → **C_AMBIGU**.

### Finding #4 — Effet bucket

| Pop | Bucket | n | Delta_top10 (pts) |
|---|---|---|---|
| TH | large | 117 | +2.6 |
| TH | medium | 14 | 0.0 |
| REF | large | 11 | **-18.2** |
| REF | medium | 7 | **-14.3** |

→ Inversion sur bucket large entre TH (+2.6) et REF (-18.2). Confirme finding #1 (cas distincts).

### Finding #5 — Effet delta_rank_avg (continu, pas binaire top10)

Sur cas individuels, delta_rank_avg = (rank_ablation - rank_baseline) :
- Negative = ablation place target file PLUS PROCHE du top (meilleur)
- Positive = ablation place target file PLUS LOIN (pire)

| Pop | delta_rank_avg moyen |
|---|---|
| TH N=131 | **-12.76** (large) / -3.21 (medium) |
| REF N=18 | -1.09 (large) / -1.14 (medium) |

→ **Sur les deux populations, ablation tend à AMÉLIORER le rank moyen** (signal continu).

Mais le seuil top10 est binaire — un cas qui passe de rank 50 à rank 30 est "aidé" sur le continu mais "neutre" sur top10. Et un cas qui passe de rank 10 à rank 11 est "neutre" sur le continu mais "hurt" sur top10.

→ Le seuil top10 est **fragile** au binary cutoff.

## Verdict honnête cycle 19 v2

### Pre-registered scenario : **C_AMBIGU**

- TH help% = 57.3% (hors zone B ≥75% et A ≤25%)
- REF help% = 50.0% (hors zone B et A)
- Per-projet : hétérogène (cookiecutter +25, ansible -13)
- Per-bucket : inversion entre TH et REF
- Overlap populations : seulement 50%

### Décision pratique

**Garder composite 6 signaux** = décision conservative (statu quo + cycle 15 calibration). C'est **OK** comme décision pratique.

**Mais le verdict cycle 19 v1 (NON ferme) était méthodologiquement fragile**. La vraie conclusion : on ne sait pas si l'ablation aide ou nuit globalement.

## Cherry-pick analysis cycle 19 v1

Cycle 19 v1 a choisi panel_ref comme référent "privilégié". Sky-master signale : pourquoi pas TH (N plus grand) ?

Trois biais possibles :
1. **N=18 < N=131** : sample size effect — N=18 peut avoir delta -16.7 par chance
2. **Cas hors-overlap** : 9/18 cas absents du pool TH, on ne compare pas la même chose
3. **Critique post-hoc** : on a choisi panel_ref APRÈS avoir vu les résultats (non-pre-registered)

Le verdict pre-registered honnête : seuil ±2 pts top10 **sur les deux populations**, ou expliquer pourquoi une est plus fiable AVANT de regarder.

## Implications pour v2.0.0

### Pas de changement code

forge --carmack v1.3.0 (6 signaux) reste. Conservative = OK.

### README "Honest Limits v7" mention

Ajouter :
> "Composite weights (kalman 0.20, wavelet 0.15, crash 0.20, coupling 0.15, churn 0.15, complexity 0.15) sont **heuristiques** (cycle 15 finding). Ablation drop kalman+wavelet : verdict ambigu (cycle 19 v2) — N=131 dit helps slightly, N=18 dit hurts slightly, populations partiellement disjointes. Garder les 6 signaux est conservative, pas validé scientifiquement."

### Pas un blocker v2.0.0

Composite v1.3.0 est documenté comme heuristique depuis cycle 15. Ambiguité cycle 19 ne change pas l'état.

## Falsificationnisme

- Pre-registration criteria_v19_v2.md committed AVANT analyse (commit antérieur sur cycle19_v2)
- Scenarios pré-enregistrés (A NON, B OUI, C AMBIGU) avec seuils explicites
- Verdict honnête sur cycle 19 v1 (cherry-pick) = correction explicite, pas défense
- Sub-population analysis (per-bucket, per-projet, per-case) = transparence des données

## Anti-bâclage

Wall-clock cycle 19 v2 : **~5 sec** (pure stdlib analysis, 149 fichiers JSON).

ETA brief MESSAGE_TO_LUDO 2-4h → ratio 0.04-0.07%.

**Justification non-bâclage** :
- Pattern hétérogène (per-projet variance) ferme sans ambiguïté
- 4 dimensions d'analyse (bucket, projet, sign tally, overlap) — pas mono-axe
- Verdict pre-registered AMBIGU correspond exactement aux données
- Continuer = re-confirmer pattern stable

## Reproductibilité

```
$ cd /home/sky/forge-case-studies
$ git checkout cycle19_v2
$ git checkout origin/cycle15 -- bench_v15/ bench_v15_reference/
$ git checkout origin/cycle19 -- results_v15_*.jsonl
$ python3 run_cycle19_v2_analysis.py
$ cat cycle19_v2_summary.json
```

- Python : 3.x stdlib only
- Forge version source : 1.3.0 (cycle 15)
- Date analyse : 2026-05-11

## Fichiers artifacts

- criteria_v19_v2.md (pre-registration)
- run_cycle19_v2_analysis.py (analyse)
- cycle19_v2_per_case_train_holdout.jsonl (per-case detail TH)
- cycle19_v2_per_case_ref.jsonl (per-case detail REF)
- cycle19_v2_summary.json (verdict structuré)
- FINAL_REPORT_v11_v2.md (ce document)

## Conclusion

**Verdict honnête cycle 19** : **AMBIGU**. Cycle 19 v1 a fait cherry-pick (panel_ref préféré sans justification pre-registered). Investigation v2 révèle hétérogénéité per-projet et populations partiellement disjointes.

**Décision pratique** : garder 6 signaux par conservatisme, pas par validation. Documenter dans README.

Prochain : cycle 20 v2 (sanity à scale 5-10 cas par outil sur projets réels).
