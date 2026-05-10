# Phase 0.1 — Forge compatibility check

**Date** : 2026-05-10
**Forge version testée** : forge-shield 1.2.2 (PyPI)
**Binaire** : `/home/sky/Bureau/forge/.venv/bin/forge`

## Verdict

**GO sans patch forge.py** — fallback texte + checkout PRE_BUG.

## Subcommandes (toutes présentes)

| Subcmd | Présent | Note |
|---|---|---|
| `--carmack [--weeks N]` | ✅ | multi-signal defect score (Kalman + wavelet + coupling) |
| `--modularity` | ✅ | Newman-Girvan Q over import graph |
| `--predict [--weeks N]` | ✅ | churn-based defect risk (baseline simple pour comparaison) |
| `--locate` | ✅ | Ochiai SBFL (needs coverage.py) |
| `--fast-deep` | ✅ | transitive impact via inverted import graph |
| `--shield` | ✅ | orchestrate carmack→gen-props→fast-deep with feedback (cycle 9) |
| `--gen-props PATH` | ✅ | Hypothesis property tests |

## Flags critiques

| Flag | Présent | Implication |
|---|---|---|
| `--weeks N` | ✅ | history horizon — `forge --carmack --weeks 4` regarde 4 sem avant HEAD |
| `--since SHA` | ✅ | mais réservé à `--incremental-mutate`, pas à `--carmack` |
| `--json` | ❌ | absent (test : `forge --carmack --json` → "unrecognized flag") |
| `--cutoff-date` | ❌ | absent |
| `--until` | ❌ | absent |

## Décisions de fallback (autorisées par le brief)

### --json absent → parser texte

Le brief Phase 0.1 dit : "Si --json absent sur --carmack → patcher forge dans cycle11_json branch (1-2h) AVANT phase A. **Sinon parser texte.**"

Choix : **parser texte**. Justifications :
- Patcher forge 1.2.2 (publié PyPI) demande version bump + republier OU dev branch séparée → friction
- Le format texte de `forge --carmack` est stable et lisible (rangs + scores + fichier)
- Risque parsing < risque dev/release sur produit publié

Parser script à écrire : `parse_carmack.py` (regex `^\s*\d+\.\s+(\d+\.\d+)\s+(.+\.py)`).

### --cutoff-date absent → checkout PRE_BUG

Le brief Phase 0.6 prévoit ce fallback : "git checkout PRE_BUG... OU Si forge --cutoff-date dispo : passer --cutoff-date=$CUTOFF_DATE à forge directement."

Choix : **checkout PRE_BUG**. Le `--weeks 4` regardera 4 semaines avant HEAD, qui = PRE_BUG après checkout. Anti-leakage maintenu.

## Sortie commandes (verbatim)

```
$ /home/sky/Bureau/forge/.venv/bin/forge --version
forge-shield 1.2.2

$ /home/sky/Bureau/forge/.venv/bin/forge --carmack --json --weeks 4 /home/sky/Bureau/forge
  ERROR: unrecognized flag: --json
  Did you mean: --version
  Run `forge --help` for the full list.

$ /home/sky/Bureau/forge/.venv/bin/forge --carmack --cutoff-date 2026-04-01 /home/sky/Bureau/forge
  ERROR: unrecognized flag: --cutoff-date
  Did you mean: --mutate
  Run `forge --help` for the full list.
```

## Aucune modification de forge.py prévue

Phase A.2 utilisera :
- `forge --carmack --weeks 4` après `git checkout PRE_BUG` → output texte parsé
- `forge --modularity` → output texte parsé (récup `Q = X.XXX`)
- `forge --predict --weeks 4` → baseline churn-only, output texte parsé
- `forge --locate` → si tests + coverage dispo
- `forge --fast-deep` → transitive impact
- `forge --shield` → 1× par bucket pour orchestration check
