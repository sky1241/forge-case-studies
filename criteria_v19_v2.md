# Pre-registered criteria — cycle 19 v2 (investigation contradiction N=18 vs N=131)

**Date** : 2026-05-11
**Branch** : cycle19_v2 sur forge-case-studies
**Origine** : MESSAGE_TO_LUDO_PC1 cycle v2 sky-master directive

## Hypothèse cycle 19 v2

> "Pourquoi cycle 15 train+holdout (N=131) dit ablation 4-sig MIEUX (+2.3 pts) et panel_reference v2 (N=18) dit ablation 4-sig PIRE (-16.7 pts) ? Quel est le verdict honnête ?"

## Critique cycle 19 v1

Cycle 19 v1 a choisi panel_reference (N=18) pour le verdict NON. Sky-master signale : **cherry-pick stratégique** car N=18 << N=131.

## Procédure v2

Décomposition systématique pour identifier la source de la contradiction :

1. **Per-bucket** : top10 BASELINE vs ABLATION pour small/medium/large séparément (train+holdout + panel_ref)
2. **Per-projet** : top10 BASELINE vs ABLATION pour chaque projet (ansible, fastapi, scrapy, etc.)
3. **Per-case** : rank BASELINE vs rank ABLATION pour CHAQUE cas individuel
   - Identifier les cas où ablation aide (rank baseline > rank ablation)
   - Identifier les cas où ablation nuit
4. **Overlap analysis** : panel_reference (20 cas) ⊆ train+holdout (131 cas) ? Quels sont les 18 cas du panel_ref dans le pool 131 ?
5. **Distribution check** : nombre de fichiers par cas (total_files), bugfix count moyen, etc.

## Critères verdict

### Scenario A — verdict ferme NON (ablation nuit)
- ≥75% des cas individuels : ablation nuit (delta rank > 0)
- ET delta panel_reference confirmé sur sub-pool de N=131

### Scenario B — verdict ferme OUI (ablation aide)
- ≥75% des cas individuels : ablation aide (delta rank < 0)
- ET delta train+holdout confirmé sur sub-pool de panel_ref

### Scenario C — verdict AMBIGU
- Delta varie selon sub-population (per-bucket ou per-projet)
- Pas de pattern stable
- Documenter la variance comme finding

## Anti-pattern

- Pas de nouveau re-run forge (re-utilise cycle 15 data)
- Pas de cherry-pick selon résultat préféré
- Si conflict : verdict ambigu, documenter pourquoi
- Pre-registration AVANT analyse

## Reproductibilité

```
$ python3 run_cycle19_v2_analysis.py
```

- Sources : bench_v15/, bench_v15_reference/, panel_reference.json
- Forge version : 1.3.0 (cycle 15)
- Python : 3.x stdlib uniquement

## Sortie attendue

- cycle19_v2_per_bucket.json
- cycle19_v2_per_project.json
- cycle19_v2_per_case.jsonl
- FINAL_REPORT_v11_v2.md avec verdict honnête
