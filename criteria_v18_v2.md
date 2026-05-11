# Pre-registered criteria — cycle 18 v2 (shield sur HEAD actuel, option 18b)

**Date** : 2026-05-11
**Branch** : cycle18_v2 sur forge-case-studies
**Origine** : MESSAGE_TO_LUDO_PC1 cycle v2 sky-master directive

## Hypothèse cycle 18 v2

> "Sur HEAD actuel des repos (pas PRE_BUG), forge --shield complète ses 3 stages (carmack → gen-props → fast-deep) ≥ 80% des cas ?"

## Pourquoi v2 (vs v1)

Cycle 18 v1 verdict (0% stages_complete) testait le bug `--weeks` date système, **pas la logique shield elle-même**. Bug `git log --since='N weeks ago'` utilise date système (2026-05) vs commit PRE_BUG (2018-2021) → carmack short-circuit cascade.

**Option 18b** : run shield sur HEAD actuel des projets (master/main). `--weeks` fonctionne (logs récents), shield s'exécute vraiment.

## Procédure v2

1. Pour chaque cas du panel_reference v2 (N=20) :
   - `cd /home/sky/forge-case-studies/clones/<project>/`
   - `git fetch origin && git checkout origin/HEAD --force` (ou main/master)
   - `python3 forge.py --init` (créer .forge/ baseline initial)
   - `timeout 600 python3 forge.py --shield 2>&1`
   - Capture exit code + stdout + stderr verbatim
   - Mesurer stages_complete (regex sur output : "Carmack signal", "Property tests", "Fast-deep")
2. Aggregation : ratio cas avec stages_complete sur N=20
3. Output : bench_v18_v2/results/<project>/<bug_id>/shield.txt verbatim + stages_complete bool

## Critère verdict (BATTLE_PLAN ligne 153)

### C_shield_v2

- ≥ 80% des cas avec exit=0 + stages_complete (les 3 stages exécutés)

**OUI** : shield logic fonctionne → documenter cas d'usage v2.0.0
**NON** : shield logic défaillante hors bug --weeks → drop scope user-facing

## Anti-pattern

- Réutilise clones existants /home/sky/forge-case-studies/clones/ (no re-clone)
- Mais checkout HEAD actuel obligatoire (pas PRE_BUG ancien)
- Timeout 600s/cas pour cas extrêmement long-running
- Pre-registration AVANT runs
- Outputs verbatim systématiques

## Reproductibilité

- Forge version : 1.3.1
- Python : 3.13.12 (system default)
- Repos : panel_reference v2 (20 cas, 11 projets)
- Working dir source : /home/sky/forge-case-studies/clones/<project>/
- Output : bench_v18_v2/results/<bucket>/<bug_id>/{shield.txt, shield_meta.json}

## Limites avouées

- Test sur HEAD actuel ≠ test sur PRE_BUG. La logique shield est testée, MAIS le verdict ne dit RIEN sur la capacité de shield à détecter le bug spécifique au commit PRE_BUG.
- Bug --weeks reste à corriger pour shield à scale (cycle futur).
- Sample N=20 (panel_reference) — pas N=131 (full pool).
