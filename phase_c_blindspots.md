# Phase C — forge --carmack blind spots (diagnostic, no fix in cycle 11)

**Date** : 2026-05-11
**Référence brief** : sky-master Phase C (read-only investigation, no forge.py modif)
**Verdict cycle 11** : 0/3 OUI (forge_au_niveau_hasard)

---

## Cas catastrophes hold-out

### scrapy-26 — rank 179 / 301 (39e percentile, miss complet)

**Target** : `scrapy/settings/__init__.py`

**Sub-scores du target** :
```
kalman      = 0.000
wavelet_hf  = 331.7
crash_prob  = 0.000
coupling    = 0.07
churn       = 1.635
freq        = 19
authors     = 4
bugfixes    = 2
loc         = 211
n_distinct_days = 16
```

**Top 5 forge ranking** (les "winners" par score composite) :
```
1. 0.211 scrapy/xlib/tx/interfaces.py     wavelet=1488400 (!) churn=1.0  freq=2  bf=1
2. 0.161 scrapy/contrib/downloadermiddleware/httpcache.py  wavelet=5853 churn=185 freq=41 bf=0
3. 0.157 scrapy/contrib/pipeline/images.py  wavelet=2534 churn=169  freq=57  bf=5
4. 0.151 scrapy/exceptions.py            wavelet=89   coupling=1.00  churn=1.6  freq=10 bf=1
5. 0.112 scrapy/xlib/tx/_newclient.py    wavelet=430166 (!) churn=1.0  freq=3  bf=2
```

**Diagnostic** :
- Top 1 et Top 5 sont des fichiers **`scrapy/xlib/tx/`** (twisted port) avec **wavelet HF énorme** (1.488M et 430K) mais freq=2-3 et bf=1-2 → ce sont des **fichiers importés en bulk** une seule fois (translation port from Twisted lib). Burst Wavelet faux positif.
- Les "vrais" candidats forge (top 2-3) ont aussi des biais : downloadermiddleware/httpcache.py rank 2 a **0 bugfix antérieur** mais wavelet et churn élevés.
- `scrapy/settings/__init__.py` est un **fichier de config**, low churn par nature (les configs changent peu), low coupling local (peu d'imports vers/depuis), peu de bugs visibles.

### thefuck-9 — rank 103 / 249 (41e percentile, miss complet)

**Target** : `thefuck/rules/git_push.py`

**Sub-scores du target** :
```
kalman      = 0.000
wavelet_hf  = 11.4
crash_prob  = 0.000
coupling    = 0.15
churn       = 2.429
freq        = 8
authors     = 3
bugfixes    = 0  ← KEY
loc         = 14
n_distinct_days = 7
```

**Top 5 forge ranking** :
```
1. 0.389 thefuck/conf.py                kalman=0  wavelet=4171  coupling=0.85  churn=7.1  bf=5
2. 0.238 tests/rules/test_fix_file.py   wavelet=4641  churn=1.4  bf=5
3. 0.237 thefuck/types.py              wavelet=3815  churn=2.4  bf=5
4. 0.228 thefuck/main.py               wavelet=771   churn=13.0  bf=15
5. 0.216 thefuck/shells/__init__.py    wavelet=789   coupling=0.88  churn=4.4  bf=0
```

**Diagnostic** :
- Tous les top 5 ont **bugfixes ≥ 5** sauf shells/__init__.py.
- Le target `git_push.py` a **0 bugfix antérieur** → tous les signaux "history-based" sont nuls :
  - Kalman = 0 (aucune dérive bug visible)
  - Crash = 0 (Kaplan-Meier sans event = survival 100% = crash 0)
- forge ne peut **pas prédire un premier bug** sur un fichier vierge (cold-start problem).

---

## Hypothèses des causes racines

### Blind spot 1 : Forge récompense les bursts, pénalise la stabilité

forge composite score = 0.20·kalman + 0.15·wavelet + 0.25·crash + 0.15·coupling + 0.25·churn

**Tous les 5 signaux sont *bursts-based* ou *history-based*** :
- Kalman : dérive bayésienne sur bugfix events → besoin d'historique
- Wavelet HF : multi-scale churn → besoin de variations
- Crash : Kaplan-Meier sur bugfix → besoin d'event
- Coupling : Newman Q sur import graph → mesure structurelle (pas history-based)
- Churn : modifications fréquentes → besoin de variations

**Coupling** est le seul signal "structurel" non history-based. Mais pondéré 0.15 (le plus bas avec wavelet).

**Conséquence** : un fichier stable + central fonctionnellement (config, exceptions, init) reçoit un score bas. Mais ces fichiers sont précisément ceux où les bugs subtils peuvent dormir (modifications rares = peu de revue, invariants critiques).

### Blind spot 2 : Cold-start problem (zero bugfix history → score≈0)

Les rules `thefuck/rules/git_push.py` ont 0 bugfix antérieur. Le pattern de forge :
- Kalman s'initialise à 0
- Kaplan-Meier sans event ne peut pas estimer la survie probabilité
- Crash_prob = `bugfixes / max(freq, 1)` = 0 / 8 = 0 (fallback aussi)

→ Toute la signature "history" est neutralisée pour les fichiers nouveaux ou rarement bugfixés.

**Mais le pattern empirique est** : *tous les fichiers reçoivent leur premier bug un jour*. forge ne peut pas le prédire. C'est un trade-off acceptable si on assume "les fichiers bugged-before sont les mieux candidates", mais pas si on veut détecter les bugs sur fichiers vierges.

### Pattern conjoint observable

Sur les 4 catastrophes (rank > 30) du panel cycle 11 :
- **thefuck-29** train rank 31 : `thefuck/types.py`, **0 bugfix** au PRE_BUG
- **cookiecutter-2** train rank 27 : `cookiecutter/hooks.py`, 4 bugfixes
- **scrapy-26** holdout rank 179 : `scrapy/settings/__init__.py`, 2 bugfixes (config file stable)
- **thefuck-9** holdout rank 103 : `thefuck/rules/git_push.py`, **0 bugfix**

**3 / 4 catastrophes** ont **0-2 bugfix** antérieurs. **1 / 4** est un fichier de config stable. Les 2 blind spots se chevauchent.

---

## Fix proposé (PAS dans cycle 11 — pour cycle 12 ou ultérieur)

### Fix A — Bayésien prior sur Kaplan-Meier (cold-start patch)

Dans `forge.py:_kaplan_meier()` ou la formule fallback `crash_prob = bugfixes / max(freq, 1)` :

Remplacer par un **prior Beta(0.5, 0.5)** (Jeffreys prior) :
```python
crash_prob = (bugfixes + 0.5) / (freq + 1)
```

→ Un fichier 0 bugfix avec freq=8 reçoit `crash_prob = 0.5/9 = 0.056` au lieu de 0.000.

Ça évite que le signal soit complètement éteint pour les fresh modules. Petit boost mais cohérent.

**Test impact** : à appliquer sur le panel cycle 11 + verifier que les non-rate ne régressent pas. Devrait booster thefuck-9 et scrapy-26 modérément.

### Fix B — Ajouter un signal "centralité fonctionnelle" (PageRank import graph)

forge --modularity calcule déjà Newman-Girvan Q. PageRank du même graph donnerait la **centralité fonctionnelle** (un fichier de config est central même si peu connecté localement).

Ajouter un 6e signal `pagerank_centrality` au composite score, par exemple poids 0.10 :
```python
cw = {kalman: 0.18, wavelet: 0.12, crash: 0.22, coupling: 0.13, churn: 0.25, pagerank: 0.10}
```

**Test impact** : `scrapy/settings/__init__.py` est probably high PageRank (importé partout) → boost rank vers le top 30.

### Fix C — Compteur de "freshness" (boost les fichiers récents)

Si un fichier a été créé/modifié dans les N dernières weeks ET a 0 bugfix → potentiellement un nouveau code introduisant des bugs.

Ajouter un signal `freshness = recent_creations / freq` qui détecte les fichiers "fraîchement remaniés".

---

## Quel fix tester en priorité ?

**Recommandé** : **Fix A** (Bayésien prior) — 1 ligne de code, intuitif, traçable, faible risque de régression. Test sur panel cycle 11 → si positif, peut être suite cycle 12.

**Fix B** (PageRank) demande plus de design (intégration import graph, normalisation, calibration).

**Fix C** (freshness) demande définition rigoureuse de "fresh" (paramètre `--weeks` lui-même problématique cf phase_a_workarounds.md).

---

## Recommandation finale Phase C

**Pas de modification de forge.py dans cycle 11** (sky-master directive). Document ce diagnostic, ouvrir issue/branch dans cycle 12 :

1. Issue `cycle12_blindspot_cold_start.md` à créer dans sky1241/forge
2. Branche `cycle12_phase_C_fix_kaplan_prior` à proposer après cycle 11 close
3. Re-run panel cycle 11 sur la branche pour mesurer l'impact

**Aucun fix proposé en commit séparé pour cycle 11** : le fix A nécessite re-run + validation, et serait un cycle 12 propre. Pas de courte-circuit.

---

## Conséquence pour cycle 11 verdict

Le verdict 0/3 OUI reste **pré-enregistré et gravé**. Les blind spots identifiés expliquent **pourquoi** forge a raté ces 2 cas, mais ne modifient PAS le verdict statistique.

Le fix A (cold-start Bayésien prior) sera testé en cycle 12 sur un panel élargi (N≥50), conforme à la recommandation FINAL_REPORT § 11.
