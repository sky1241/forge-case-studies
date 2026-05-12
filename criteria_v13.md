# Pre-registered criteria — cycle 21 / criteria_v13 (sanity 10 outils peu testés)

**Date** : 2026-05-12
**Branch** : cycle21 sur forge-case-studies
**Origine** : MESSAGE_TO_LUDO_PC1 cycle 21 directive

## Hypothèse cycle 21B

> "Sur 5 cas par outil dans projets GitHub actifs (5 projets × 10 outils = 50 cas), les 10 outils forge peu testés en cycles précédents maintiennent exit code 0 sur ≥ 80% des cas avec output cohérent ?"

## 10 outils testés

1. `--anomaly` (z-score outliers git metrics)
2. `--heatmap` (Pareto failing tests)
3. `--baseline` / `--diff` (compare current vs saved baseline)
4. `--init` / `--add` / `--close` (BUG tracking BUGS.md)
5. `--install-hook` / `--uninstall-hook` (git hooks pre-commit)
6. `--watch` (file watcher, vraie démo pas juste timeout 5s)
7. `--full-cycle` (orchestration pipeline complet)
8. `--predict-carmack` (clarifier la différence vs --carmack ; testé via --predict + --carmack séparément)
9. `--incremental-mutate` (cycle 6 sky-master, mutate diff lines only)
10. `--flaky-dtw` (DTW temporal pattern)

## Panel — 5 projets actifs (cycle 20 v2 panel)

ansible, scrapy, luigi, fastapi, black — tous ≥3 commits sur 4 dernières semaines (vérifié cycle 18 v2).

## Critère verdict (BATTLE_PLAN ligne 153)

### C_sanity_10_tools

Pour CHAQUE outil :
- exit code 0 sur ≥ 80% cas
- Output cohérent + verbatim documenté

### Aggregate verdict

- **OUI** : ≥ 8/10 outils PASS individuel
- **NON** : < 8/10

## Output cohérent — patterns regex par outil

| Outil | Pattern attendu (OK) | Pattern fallback (PARTIAL) |
|---|---|---|
| anomaly | `commits.*anomal\|outlier\|z-score` | `Not enough.*activity\|insufficient` |
| heatmap | `failures\|test.*fail` | `No forge log\|No failures` |
| baseline | `Baseline saved\|snapshot` | — |
| diff | `Diff vs baseline\|no diff` | `no baseline yet` |
| init | `Forge initialized\|Created` | — |
| add | `Added BUG-` | — |
| close | `marked FIXED\|marked CLOSED` | `not found` |
| install-hook | `Installed.*pre-commit` | `already installed` |
| uninstall-hook | `Removed.*hook` | `No.*hook found` |
| watch | démarrage (ANSI clear OU "Watching") | — |
| full-cycle | `forge --init\|carmack\|complete` | — |
| predict-carmack | `predict\|carmack.*score` | — |
| incremental-mutate | `mutate\|incremental\|since` | `No diff\|nothing to mutate` |
| flaky-dtw | `\d+ runs\|stable\|flaky` | — |

## Procédure v13

1. Setup tmpdir copy de chaque projet (pour install-hook/uninstall-hook, baseline, init, add, close — éviter pollution)
2. Pour chaque outil : 5 projets distincts, capture exit + output verbatim
3. bench_v13/results/<outil>/<case>/output.txt versionné

## Anti-pattern

- Pas de smoke synthétique (cycle 20 v1 erreur). Cas réels uniquement.
- Pre-registration AVANT runs
- Outputs verbatim systématiques (bench_v13/results/)
- Commits incrémentaux par 10 cas

## Comparison panel_reference v2 (BATTLE_PLAN rail)

Cycle 20 v2 panel = ansible/scrapy/luigi/fastapi/black sur 6 outils principaux. Cycle 21B = même panel sur 10 outils auxiliaires. Pas de régression attendue (outils indépendants).

## Reproductibilité

- Forge version : 2.1.0 (cycle 21A fixes mergées)
- Python : 3.13.12
- Projets actifs source : /home/sky/forge-case-studies/clones/<project>/
- Output : bench_v13/results/<tool>/<case>/{output.txt, meta.json}

## Limites avouées

- Smoke tests ≠ performance tests
- Certains outils (full-cycle) lancent baseline + carmack + heatmap → cumul long
- watch test = 5s timeout puis SIGTERM (mode interactif)
- predict-carmack n'est pas une vraie sous-commande, testé via --predict puis --carmack séparément
