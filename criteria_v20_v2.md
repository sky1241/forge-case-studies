# Pre-registered criteria — cycle 20 v2 (sanity à scale sur projets réels)

**Date** : 2026-05-11
**Branch** : cycle20_v2 sur forge-case-studies
**Origine** : MESSAGE_TO_LUDO_PC1 cycle v2 sky-master directive

## Hypothèse cycle 20 v2

> "Sur 5-10 cas par outil dans projets GitHub RÉELS (pas tmpdirs synthétiques), forge outils principaux (gen-props, minimize, snapshot, watch, bisect, flaky) maintiennent exit=0 + output cohérent ≥ 80% des cas ?"

## Critique cycle 20 v1

Cycle 20 v1 a testé 16 outils sur **2 tmpdirs synthétiques** = 2 cas par outil. Sky-master signale : **10-20% du scope brief** (30-60 cas total = 5-10 par outil).

## Procédure v2

Pour chaque outil principal :
- **5 cas minimum** sur projets distincts depuis /home/sky/forge-case-studies/clones/
- Projets utilisés : ansible, scrapy, luigi, fastapi, black, tornado, thefuck, PySnooper, httpie, cookiecutter
- Pour chaque cas : exit code + output verbatim sauvegardés dans bench_v20_v2/results/<tool>/<case>/

### Outils testés (6 outils × 5+ cas = 30+ cas)

1. **forge --gen-props PATH** : 5 cas sur fichiers Python réels (1 par projet)
2. **forge --minimize TEST INPUT** : 5 cas avec test failant + input multi-line réel
3. **forge --snapshot "CMD"** : 5 cas avec commandes simples (`python -c`, `echo`, `python --version`)
4. **forge --watch** : 5 cas timeout 5s (mode interactif)
5. **forge --bisect TEST** : 5 cas sur projets avec git history (test passant trivial, juste vérifier exit)
6. **forge --flaky N** : 5 cas avec tests existants ou créés

## Critère verdict (BATTLE_PLAN ligne 153)

### C_sanity_scale

- Pour chaque outil : ≥ 80% des cas avec exit=0 + output cohérent
- Aggregate : ≥ 5/6 outils PASS

**OUI** : ≥ 5/6 outils PASS → outils prêts production v2.0.0
**NON** : < 5/6 → blockers à identifier avant tag

## Output cohérent — patterns regex par outil

| Outil | Pattern attendu (OK) | Pattern fallback acceptable |
|---|---|---|
| gen-props | `Generated \d+ property tests` | "no public functions" / "all skipped" |
| minimize | `DDMIN RESULT` ou `Nothing to minimize` | `Test does not fail` |
| snapshot | `Saved.*\.golden` | — |
| watch | démarrage (ANSI) OU "Watching" | — |
| bisect | `First bad commit` | `Test does not currently fail` / `Verifying` |
| flaky | `\d+ runs` ou `stable` ou `flaky` | — |

## Anti-pattern

- Réutilise clones existants pour gain temps
- Pre-registration AVANT runs
- Outputs verbatim systématiques (bench_v20_v2/results/<tool>/<case>/output.txt)
- Commit incrémentaux par outil (6 commits)

## Limites avouées

- Smoke tests ≠ performance tests
- Tests créés artificiellement pour minimize/bisect/flaky (besoin failing test)
- gen-props sur fichiers réels mais sans validation de la qualité des tests générés
- snapshot sur commandes simples, pas pipelines complexes

## Reproductibilité

- Forge version : 1.3.1
- Python : 3.13.12
- Working dirs source : /home/sky/forge-case-studies/clones/<project>/
- Output : bench_v20_v2/results/<tool>/<case>/{output.txt, meta.json}

## Sortie attendue

- cycle20_v2_summary.json
- bench_v20_v2/results/<tool>/<case>/output.txt verbatim
- FINAL_REPORT_v12_v2.md
