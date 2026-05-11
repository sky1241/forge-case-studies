# Pre-registered criteria — cycle 20 (sanity light outils restants)

**Date** : 2026-05-11
**Branch** : cycle20 sur forge-case-studies

## Hypothèse cycle 20

> "Les sous-commandes forge non testées en cycles précédents (gen-props, minimize, snapshot, watch, bisect, flaky, mutate) fonctionnent en sanity light : exit=0 + output non-vide sur cas trivial ?"

## Outils sanity check

| Outil | Cas test | Critère smoke |
|---|---|---|
| `forge --gen-props PATH` | sample.py avec 2-3 fonctions purs | exit=0 + tests Hypothesis générés dans output |
| `forge --minimize TEST INPUT` | test failant avec input réductible | exit=0 + input réduit < input original |
| `forge --snapshot "CMD"` | "echo hello" | exit=0 + golden capturé |
| `forge --snapshot-check` | re-run après snapshot | exit=0 + match golden |
| `forge --watch` | démarrage 5s puis SIGTERM | exit=0 OU exit=143 (SIGTERM) + démarrage OK |
| `forge --bisect TEST` | test failant simple | exit=0 OU non-zero acceptable (skip si pas de baseline) |
| `forge --flaky N` | run sur tests passants | exit=0 + classification output |
| `forge --mutate` | sample.py | exit=0 + mutations rapport |

## Critère verdict (BATTLE_PLAN ligne 153)

### C_sanity_light

- ≥ 6/8 outils sanity OK
- Output documenté verbatim

**OUI** : ≥6/8 outils fonctionnent → v2.0.0 gate validé
**NON** : <6/8 → identifier blockers avant v2.0.0

## Procédure

1. Setup tmpdir `/tmp/forge_sanity_v20/`
2. Créer `sample.py` (3 fonctions purs : add, multiply, factorial)
3. Créer `test_sample.py` (1 test passant + 1 test failant)
4. Setup git init + commit initial
5. Pour chaque outil → exécuter + capture exit code + capture output
6. Tableau récap final

## Anti-pattern

- Pas de re-run forge --carmack (déjà cycle 15)
- Pas de comparaison cycle 14/15 (out-of-scope)
- Sanity light strict : exit=0 + output, pas de claim performance

## Reproductibilité

- Forge version : 1.3.1 (tag actuel)
- Python : 3.11+
- Working dir : /tmp/forge_sanity_v20/
- Tous outputs sauvegardés dans cycle20_sanity_results.json
