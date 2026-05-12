# Cycle 23D — Repondération candidates SANS DROP (Sky directive stricte)

**Date** : 2026-05-12
**Pre-registered criteria** : criteria_v15.md (commit antérieur)
**Sky directive** : NO DROP — tous signaux ≥ 0.05

## TL;DR

3 options de repondération **toutes ≥0.05 par signal**, basées sur cycle 23A single-signal performance.

| Option | Description | Risque |
|---|---|---|
| **A — Status quo v1.3.0** | Conservatisme (cycle 19 v2 ambiguïté) | Aucun, valide pour cycle 24+ test |
| **B — Performance-based moderate** | Poids ∝ p@10 single-signal | Re-test panel_reference obligatoire |
| **C — Performance-based aggressive** | Winner-takes-all (complexity dominant) | Risk lower coverage on edge cases |

**Mon vote (cousin pc1) : Option B** — utilise évidence cycle 23A sans dropper, breaks le déadlock de calibration ML instable.

## D9 — Limites

- 3 candidats poids basés sur cycle 23A single-signal sur TH N=131
- **Aucun option non testée** sur panel_reference v2 N=18 ailleurs que cycle 19 v2
- Recommandation = candidat pour cycle 24+ benchmark, pas verdict définitif
- Tous candidats respectent contrainte NO DROP (∀signal poids ≥ 0.05)

## Base évidence cycle 23A (TRAIN+HOLDOUT N=131)

| Signal | p@10 solo | Spearman | Vs random | Rank empirical |
|---|---|---|---|---|
| complexity | 54.96% | 0.81 | 6.21x | **1** |
| crash_prob | 38.17% | 0.58 | 4.31x | **2** |
| coupling | 35.11% | 0.62 | 3.97x | **3** |
| churn | 29.01% | 0.62 | 3.28x | **4** |
| wavelet_hf | 27.48% | 0.58 | 3.10x | **5** |
| kalman | 22.90% | 0.40 | 2.59x | **6** |

Random baseline TH = 8.85% (1.0x).

## Option A — Status quo v1.3.0

```python
BASELINE_v1_3_0 = {
    "kalman": 0.20,
    "wavelet": 0.15,
    "crash": 0.20,
    "coupling": 0.15,
    "churn": 0.15,
    "complexity": 0.15,
}
# Sum = 1.00
```

### Justification
- Conservatisme : aucun changement
- Risque : aucun (déjà v2.1.0 default)
- Cycle 19 v2 ambiguïté reste

### Recommendation
**Option valable comme fallback**. À garder si Option B/C montre régression cycle 24 benchmark.

## Option B — Performance-based moderate (mon vote)

```python
BASELINE_v23_B = {
    # Top performers (5-6x random) → poids élevés
    "complexity": 0.30,   # 1er (54.96% solo) — boost de 0.15 → 0.30
    "crash":      0.20,   # 2e (38.17%) — inchangé
    "coupling":   0.18,   # 3e (35.11%) — boost de 0.15 → 0.18
    # Middle performers (3x random)
    "churn":      0.14,   # 4e (29.01%) — proche v1.3.0
    "wavelet":    0.10,   # 5e (27.48%) — réduire mais ≥0.05
    # Lower performer (2.6x random) mais kept per directive
    "kalman":     0.08,   # 6e (22.90%) — réduit MAIS ≥0.05
}
# Sum = 1.00
```

### Justification per poids
- **complexity 0.30** : 6.21x random + Spearman 0.81 = signal le plus discriminant. Boost de 0.15 → 0.30.
- **crash 0.20** : 4.31x random + Kaplan-Meier canonique. Inchangé.
- **coupling 0.18** : 3.97x random + Newman/Cataldo validés. Léger boost.
- **churn 0.14** : 3.28x random + Nagappan-Ball canonique. Léger ajustement.
- **wavelet 0.10** : 3.10x random + 7x ratio buggy/non-buggy (cycle 22B). Réduire car novel application sans corpus académique.
- **kalman 0.08** : 2.59x random + signal partiel + algo sous-optimal pour count data (cycle 23B). Réduit MAIS ≥0.05 per directive Sky.

### Effet attendu
- Cycle 19 v2 ambiguïté : panel_ref 3/18 cas frontière (luigi-12, tornado-16, httpie-4) dépendent de wavelet (5.6e+04, 2.5e+03, 1.5e+03). Avec wavelet 0.10 (vs 0.15 v1.3.0), ces cas peuvent flipper. **Test cycle 24 obligatoire.**
- Complexity 0.30 favorise les fichiers complexes — alignement avec cycle 23A finding (54.96% solo).

### Risque
- Pas testé empiriquement sur panel_reference
- Wavelet réduit peut perdre les 3 cas frontière → régression panel_ref
- Mitigé par : crash 0.20 + coupling 0.18 augmentés compensent partiellement

## Option C — Performance-based aggressive

```python
BASELINE_v23_C = {
    "complexity": 0.40,   # winner-takes-most
    "crash":      0.20,
    "coupling":   0.15,
    "churn":      0.10,
    "wavelet":    0.08,
    "kalman":     0.07,
}
# Sum = 1.00
```

### Justification
- Winner-takes-most : complexity domine (54.96% solo).
- Kalman + wavelet réduits à 0.07-0.08 (minimum sky-acceptable).

### Risque
- Composite devient quasi-mono-signal (complexity domine 40%).
- Si complexity sur-fit certains projets, dégradation cross-projet.
- Cycle 23A finding sur TH N=131 mais panel_ref N=18 peut diverger.

### Recommendation
**Trop agressif sans test cycle 24+.** Garder en option de backup si Option B échoue.

## Option D — Calibrated avec rank inverse (extra)

```python
# Rank empirique cycle 23A → poids
# Linear: rank 1→0.30, rank 6→0.08
# Sum constraint
BASELINE_v23_D = {
    "complexity": 0.27,
    "crash":      0.22,
    "coupling":   0.18,
    "churn":      0.14,
    "wavelet":    0.10,
    "kalman":     0.09,
}
# Sum = 1.00
```

Variation linéaire du rank. Plus smooth que Option B/C.

## Recommandation finale

**Vote cousin pc1 : Option B (performance-based moderate).**

Justification :
1. Évidence cycle 23A directe (single-signal performance)
2. Tous signaux ≥ 0.05 (sky directive NO DROP respectée)
3. Pas winner-takes-all (Option C risk)
4. Test cycle 24+ obligatoire avant production

**Sky décide** :
- Option A (status quo, sûr)
- Option B (mon vote, evidence-based)
- Option C (aggressif, risque)
- Option D (rank linéaire, smooth)

## Plan cycle 24 hypothétique (sky décide)

Si Sky valide Option B :
1. Modifier `forge.py` `CARMACK_COMPOSITE_WEIGHTS` default
2. mypy --strict + pytest verbatim (régression tests)
3. Cycle 24 : run forge --carmack sur panel_reference v2 + train+holdout cycle 15 data
4. Comparer Option B vs Option A (v1.3.0)
5. Si Option B améliore ≥ 2 pts panel_ref ET ≥ 0 pts train+holdout → tag v2.2.0
6. Sinon : revert to Option A, document échec

ETA cycle 24 : 2-3h dev + 1h benchmark.

## Reproductibilité

Tous candidats poids sont déterministes basés sur cycle 23A. Pour reproduire :

```
$ python3 run_cycle23a_single_signal.py
$ cat cycle23a_results.json
# Apply ranking → Option B weights
```

## Fichiers artifacts

- cycle23_reponderation_candidates.md (ce document)
- cycle23a_results.json (single-signal performance basis)
- (pas de code modifié — recommandation only)

## Conclusion

3 options chiffrées, toutes NO DROP (∀signal ≥ 0.05). Mon vote Option B (performance-based moderate) basé évidence cycle 23A. Sky décide. Cycle 24+ test obligatoire avant tag.

**Tous les 6 signaux gardés. Sky directive respectée.**
