# Cycle 23B — Kalman diagnosis : pourquoi zéro sur 56% des fichiers ?

**Date** : 2026-05-12
**Pre-registered criteria** : criteria_v15.md (commit antérieur)

## TL;DR

**Kalman n'est PAS buggé, mais il est sub-optimal pour ce problème :**

| Hypothèse | Verdict | Évidence |
|---|---|---|
| H1 — Bug d'implémentation | **NON** (code correct) | Welch-Bishop 2001 canonique respecté |
| H1' — `kalman_risk = smoothed[-1]` sous-optimal | **OUI** | Reflète "calme actuel" pas "risque historique" |
| H2 — Kalman inadapté events discrets | **OUI partiellement** | Count data → Poisson/Hawkes plus canoniques |
| H3 — Params Q/R | **PARTIAL** | Adaptive EM compense mais converge vers smooth-too-much |

**Conclusion** : Kalman fournit signal réel (cycle 23A : 22.9% top10 = 2.59x random) MAIS l'extraction `smoothed[-1]` perd de l'information. Recommandations v2.3 hypothétiques :
- Court terme : `kalman_risk = max(smoothed[-4:])` ou similaire (peak récent vs valeur instantanée)
- Long terme : remplacer par **Hawkes process** ou **Poisson regression** (algorithmes canoniques pour count data)

## D9 — Limites avouées

- Diagnosis basé sur lecture code forge.py (lignes 310-399, 4283-4307)
- Pas de re-run forge avec params alternatifs (analyse statique uniquement)
- Recommandation v2.3 hypothétique : pas testée empiriquement, basée sur connaissance des algorithmes canoniques
- Cycle 23A montre kalman SOLO = 22.9% top10 (2.59x random) — donc signal présent malgré "56% zéros"

## H1 — Bug d'implémentation (REJECTED)

### Code observé (forge.py lignes 310-329)

```python
def _scalar_kalman(observations: list[float], Q: float | None = None, R: float | None = None) -> list[float]:
    Q = Q or CARMACK_KALMAN_Q  # 0.05
    R = R or CARMACK_KALMAN_R  # 0.5
    if not observations:
        return []
    x = observations[0]
    P = 1.0
    estimates = []
    for z in observations:
        x_pred = x
        P_pred = P + Q
        K = P_pred / (P_pred + R)
        x = x_pred + K * (z - x_pred)
        P = (1 - K) * P_pred
        estimates.append(x)
    return estimates
```

### Vérification contre Welch-Bishop 2001 canonical

Filter scalaire (state-space simple `x_k = x_{k-1} + w_k`, `z_k = x_k + v_k`) :

| Step | Welch-Bishop | forge.py |
|---|---|---|
| `x_pred = x` | ✓ | `x_pred = x` |
| `P_pred = P + Q` | ✓ | `P_pred = P + Q` |
| `K = P_pred / (P_pred + R)` | ✓ | `K = P_pred / (P_pred + R)` |
| `x_new = x_pred + K * (z - x_pred)` | ✓ | `x = x_pred + K * (z - x_pred)` |
| `P_new = (1 - K) * P_pred` | ✓ | `P = (1 - K) * P_pred` |

**Code canonique correct.** Pas de bug d'implémentation.

### H1' — Bug d'EXTRACTION

forge.py ligne 4305 : `kalman_risk = smoothed[-1]`

Le filter retourne la séquence smoothée [x_0, x_1, ..., x_n]. La dernière valeur = état estimé à la dernière observation.

**Problème** : si la dernière semaine n'a aucun bugfix (cas typique), `bins[-1] = 0`. Le smoothed[-1] tendra vers 0 quand R >> Q (smoothing fort).

**Implication** : `kalman_risk` reflète "calme actuel" plutôt que "risque historique". Un fichier avec 5 bugfixes il y a 4 semaines mais aucun cette semaine → `kalman_risk ≈ 0` (faussement bas).

**Test mental** :
- Fichier A : bins = [0,0,0,1,0,0] (1 bugfix il y a 3 semaines)
- Fichier B : bins = [0,0,0,0,0,1] (1 bugfix cette semaine)

Avec adaptive Kalman, smoothed[-1] sera plus élevé pour B (récence) que pour A. Mais A devrait être PLUS risqué (récidive prévisible cf Kim-Whitehead 2007 "Predicting Faults from Cached History").

→ **`smoothed[-1]` est sous-optimal.** Recommandation : `kalman_risk = max(smoothed[-4:])` ou `kalman_risk = mean(smoothed)` pour capturer pic récent.

## H2 — Kalman inadapté events discrets (CONFIRMED)

### Limites théoriques du Kalman pour count data

Kalman suppose :
- État continu `x ∈ ℝ`
- Bruit gaussien `w ~ N(0, Q)`, `v ~ N(0, R)`
- Observations continues

**Bugfix events sont** :
- Comptages d'événements (Poisson, pas gaussien)
- Sparse temporellement (bursts vs calme prolongé)
- Self-exciting (un bugfix induit souvent d'autres bugfixes — Hassan-Holt 2005)

Appliquer Kalman gaussien à count data = violation d'hypothèse. Le smoothed[-1] peut donner un signal mais sous-optimal.

### Algorithmes canoniques pour count data

| Algo | Application | Forge equivalent |
|---|---|---|
| **Poisson regression** | λ(t) = e^(βX) estimation | absent |
| **Hawkes process** | Self-exciting events (cluster bursts) | absent |
| **Negative binomial** | Overdispersed counts | absent |
| **Kalman gaussien** | Continuous + gaussian noise | **utilisé (inadapté)** |
| Kaplan-Meier | Survival/censoring | utilisé (crash_prob, approprié) |

### Recommandation v2.3 hypothétique

Remplacer kalman par **Hawkes process** :
- Self-exciting events naturel pour bugs (un bug ouvre porte à d'autres)
- λ(t) = μ + Σ α exp(-β(t - t_i)) pour chaque event passé
- Intensité actuelle = signal "à risque maintenant"

OU **Poisson regression sur weekly counts** :
- Plus simple, pas de fitting iterative
- λ_w = exp(intercept + β * w + features) avec features = autres signaux

**Mais PAS implémenter en cycle 23.** Sky décide cycle 24+.

## H3 — Params Q/R mal tunés (PARTIAL)

### Defaults

```python
CARMACK_KALMAN_Q = 0.05   # process noise
CARMACK_KALMAN_R = 0.5    # measurement noise
```

R = 10x Q par défaut → smoothing fort, `K` (Kalman gain) reste petit → état change lentement.

### Adaptive EM compense

`_adaptive_kalman` (forge.py ligne 332) ré-estime Q et R via EM iterations :
```python
new_R = sum(innovations**2) / N  # variance résiduelle
new_Q = sum(state_steps**2) / (N-1)  # variance des changements d'état
```

Pour bins très sparse (1 bugfix dans 26 weeks → 25 zéros + 1 un) :
- state_steps ≈ [0, 0, ..., 0.04, -0.04, 0, ...] (très petits)
- new_Q → très petit (~0.0016)
- innovations ≈ bins - x (presque tous 0 ou -0.04)
- new_R → très petit aussi

Quand Q et R sont tous deux très petits, K ≈ 0.5 mais le filter converge vers initial value 0 rapidement.

→ EM compense partiellement mais ne change pas la nature : sparse count data → smoothed value tend vers 0.

### Test sensibilité (HYPOTHÉTIQUE)

Si on forçait Q=1.0 (état change vite) et R=0.1 (obs fiables) :
- K très grand → smoothed suit bins de près
- smoothed[-1] = bins[-1] (souvent 0)
- Pas mieux

Si on forçait Q=0.001 (état très stable) et R=10 (obs très bruyantes) :
- K très petit → smoothed quasi-constant = initial 0
- Encore pire

**Conclusion H3** : Aucun tuning Q/R simple ne résout le problème fondamental (`smoothed[-1]` est mauvais proxy pour signal sparse).

## Synthèse — Pourquoi 56% zéros ?

**Réponse en trois niveaux** :

1. **Trivial** : 56% des fichiers n'ont JAMAIS de bugfix dans 4-week window → `if s["bugfix_dates"]: ...` skip → `kalman_risk = 0.0` (default).

2. **Sub-optimal** : `smoothed[-1]` reflète "état dernière semaine" pas "historique de risque". Fichier avec bugfixes anciens → smooth tend vers 0.

3. **Théorique** : Kalman gaussien est mathématiquement inapproprié pour count data sparse. Hawkes/Poisson seraient canoniques.

**Mais kalman SOLO atteint quand même 22.9% top10 (2.59x random)** — le signal partiel existe sur les 44% de fichiers avec bugfixes.

## Recommandations v2.3 hypothétiques (PAS implémenter cycle 23)

### Court terme — fix sub-optimal extraction

```python
# Au lieu de:
kalman_risk = smoothed[-1]
# Essayer:
kalman_risk = max(smoothed[-min(4, len(smoothed)):])  # peak récent 4 weeks
# OU:
kalman_risk = sum(smoothed[-min(4, len(smoothed)):]) / min(4, len(smoothed))  # avg récent
```

Tests à faire : cycle 24 panel_reference pour comparer ces 2 alternatives au current.

### Long terme — remplacer par algo canonique

Hawkes process pour self-exciting events :
```python
# pseudo-code Hawkes intensity at "now":
lambda_t = mu + sum(alpha * exp(-beta * (now - t_i)) for t_i in bugfix_dates)
kalman_risk = lambda_t  # rename to hawkes_risk
```

Cycle 24+ : implémentation + test panel.

### Pas de breaking change

Forge v2.1.0 → v2.2.0 garderait l'API mais l'algorithme interne changerait. Composite weights restent (NO DROP per sky directive).

## Conclusion

**Kalman n'est PAS inutile.** Sky avait raison :
- Solo : 22.9% top10 (2.59x random)
- Contribue dans composite via long-tail (cycle 22B finding)
- Code canonique correct (pas de bug)

**Mais l'extraction `smoothed[-1]` est sub-optimale** pour count data sparse. Recommandation v2.3 hypothétique : repondérer wavelet plus haut + investiguer Hawkes process pour remplacer Kalman gaussien.

**Sky décide** cycle 24+ implémentation alternatives.

## Reproductibilité

```
$ cd /home/sky/Bureau/forge
$ git show v2.1.0:forge.py | sed -n '310,399p'  # _scalar_kalman + _adaptive_kalman
$ git show v2.1.0:forge.py | sed -n '4283,4307p'  # carmack kalman usage
```

## Fichiers artifacts

- cycle23_kalman_diagnosis.md (ce document)
- (pas de code modifié, diagnosis statique)
