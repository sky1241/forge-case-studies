#!/usr/bin/env python3
"""Phase B — Calibration on TRAIN + test on HOLD-OUT.

B.1 — Build dataset.csv from carmack_full/ (TRAIN only, 5 cases × ~50 files = ~250 rows)
B.2 — 3 methods: grid search 5D, logistic regression, random forest feature importance
B.3 — Test calibrated weights on HOLD-OUT (5 cases) vs heuristic (current forge weights)

Output: phase_b_results.json with delta AUC heuristic vs calibrated.
"""
import csv
import json
import math
import random
from itertools import product
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
FULL_DIR = ROOT / 'carmack_full'

# Current forge heuristic weights (from forge.py L168-180 default config)
HEURISTIC_WEIGHTS = {
    "kalman": 0.20,
    "wavelet": 0.15,
    "crash": 0.25,
    "coupling": 0.15,
    "churn": 0.25,
}


def _minmax(values):
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def composite_score(case_results, weights):
    """Recompute composite score using given weights, return list of scored dicts."""
    files = list(case_results)
    kalman_n = _minmax([f["kalman"] for f in files])
    wavelet_n = _minmax([f["wavelet_hf"] for f in files])
    crash_n = [f["crash_prob"] for f in files]
    coupling_n = _minmax([f["coupling"] for f in files])
    churn_n = _minmax([f["churn"] for f in files])
    out = []
    for i, f in enumerate(files):
        s = (weights["kalman"] * kalman_n[i] +
             weights["wavelet"] * wavelet_n[i] +
             weights["crash"] * crash_n[i] +
             weights["coupling"] * coupling_n[i] +
             weights["churn"] * churn_n[i])
        out.append({**f, "score_calibrated": s})
    out.sort(key=lambda x: x["score_calibrated"], reverse=True)
    return out


def auc_for_case(case_payload, weights):
    """AUC for a single case: probability that the change_file ranks higher than a random non-buggy file."""
    scored = composite_score(case_payload["results"], weights)
    target = case_payload["change_file"]
    target_score = None
    other_scores = []
    for f in scored:
        if f["file"] == target:
            target_score = f["score_calibrated"]
        else:
            other_scores.append(f["score_calibrated"])
    if target_score is None or not other_scores:
        return None
    # AUC = P(target_score > random_other) = #other < target / N_other (with 0.5 for ties)
    wins = sum(1 for s in other_scores if s < target_score)
    ties = sum(1 for s in other_scores if s == target_score)
    return (wins + 0.5 * ties) / len(other_scores)


def panel_auc(panel_cases, weights):
    aucs = [auc_for_case(c, weights) for c in panel_cases]
    aucs = [a for a in aucs if a is not None]
    return sum(aucs) / len(aucs) if aucs else 0.0, aucs


def build_dataset(panel='train'):
    """Build (X, y) for the panel. X = [(kalman, wavelet, crash, coupling, churn) per file],
    y = [1 if file == change_file else 0]."""
    X = []
    y = []
    case_payloads = []
    for jf in sorted(FULL_DIR.glob('*.json')):
        payload = json.loads(jf.read_text())
        if payload['panel'] != panel:
            continue
        case_payloads.append(payload)
        kn = _minmax([f["kalman"] for f in payload["results"]])
        wn = _minmax([f["wavelet_hf"] for f in payload["results"]])
        cn = [f["crash_prob"] for f in payload["results"]]
        coupn = _minmax([f["coupling"] for f in payload["results"]])
        churn_n = _minmax([f["churn"] for f in payload["results"]])
        for i, f in enumerate(payload["results"]):
            X.append([kn[i], wn[i], cn[i], coupn[i], churn_n[i]])
            y.append(1 if f["file"] == payload["change_file"] else 0)
    return X, y, case_payloads


def grid_search_5d(case_payloads, n_steps=11):
    """Maximize panel mean AUC over weights summing to 1.0."""
    best = (0.0, HEURISTIC_WEIGHTS)
    # 5D grid with step 0.1 → n_steps^5 = 161k → too many.
    # Constrained: sum = 1.0. Use stochastic search instead.
    rng = random.Random(42)
    for _ in range(2000):
        raw = [rng.random() for _ in range(5)]
        s = sum(raw)
        w = {
            "kalman": raw[0] / s,
            "wavelet": raw[1] / s,
            "crash": raw[2] / s,
            "coupling": raw[3] / s,
            "churn": raw[4] / s,
        }
        auc, _ = panel_auc(case_payloads, w)
        if auc > best[0]:
            best = (auc, w)
    return best


def logistic_regression(X, y, max_iter=200, lr=0.5):
    """Pure Python Newton-Raphson logistic regression."""
    n, d = len(X), len(X[0])
    if n == 0:
        return [0.0] * d, 0.0
    weights = [0.0] * d
    bias = 0.0
    for it in range(max_iter):
        # Compute predictions
        z = [bias + sum(weights[k] * X[i][k] for k in range(d)) for i in range(n)]
        p = [1.0 / (1.0 + math.exp(-zi)) if zi > -50 else 0.0 for zi in z]
        # Gradient
        grad = [sum((p[i] - y[i]) * X[i][k] for i in range(n)) / n for k in range(d)]
        grad_b = sum(p[i] - y[i] for i in range(n)) / n
        # Update
        weights = [weights[k] - lr * grad[k] for k in range(d)]
        bias = bias - lr * grad_b
    return weights, bias


def normalize_weights(raw_weights):
    """Normalize raw logreg coefficients to sum to 1 (positive only)."""
    pos = [max(w, 0) for w in raw_weights]
    s = sum(pos)
    if s == 0:
        return HEURISTIC_WEIGHTS  # fallback
    return {
        "kalman": pos[0] / s,
        "wavelet": pos[1] / s,
        "crash": pos[2] / s,
        "coupling": pos[3] / s,
        "churn": pos[4] / s,
    }


def main():
    print("=== Phase B.1 — Build dataset (TRAIN only) ===")
    X_train, y_train, train_cases = build_dataset('train')
    print(f"Train: {len(X_train)} rows from {len(train_cases)} cases")
    print(f"Positives (was_buggy=1): {sum(y_train)}")
    print()

    # Save dataset.csv for transparency
    with open(ROOT / 'dataset.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['kalman', 'wavelet', 'crash', 'coupling', 'churn', 'was_buggy'])
        for row, label in zip(X_train, y_train):
            w.writerow(row + [label])

    print("=== Phase B.2 — Calibration (3 methods) ===\n")

    # Method 1: Grid search (stochastic 2000 samples)
    print("Method 1: Stochastic search (2000 samples)")
    auc_grid, w_grid = grid_search_5d(train_cases)
    print(f"  Best train panel AUC: {auc_grid:.4f}")
    print(f"  Weights: {w_grid}\n")

    # Method 2: Logistic regression
    print("Method 2: Logistic regression (Newton-Raphson 200 iter)")
    raw_w, bias = logistic_regression(X_train, y_train)
    print(f"  Raw coefficients: {[f'{w:.3f}' for w in raw_w]} bias={bias:.3f}")
    w_logreg = normalize_weights(raw_w)
    auc_logreg, _ = panel_auc(train_cases, w_logreg)
    print(f"  Normalized weights: {w_logreg}")
    print(f"  Train panel AUC: {auc_logreg:.4f}\n")

    # Method 3: Random forest feature importance (skip — would need impl, use logreg as proxy)
    print("Method 3: Random forest — SKIP (using logreg as primary; grid as backup)\n")

    # Method 4: Heuristic baseline
    auc_heuristic_train, _ = panel_auc(train_cases, HEURISTIC_WEIGHTS)
    print(f"Heuristic baseline (current forge) on train: AUC={auc_heuristic_train:.4f}")
    print()

    # Pick best calibrated method (highest train AUC)
    if auc_grid >= auc_logreg:
        w_calibrated = w_grid
        method = "grid"
    else:
        w_calibrated = w_logreg
        method = "logreg"
    print(f"Selected calibration method: {method}")
    print(f"Calibrated weights: {w_calibrated}\n")

    # === Phase B.3 — Test on HOLD-OUT ===
    print("=== Phase B.3 — Test on HOLD-OUT ===\n")
    _, _, holdout_cases = build_dataset('holdout')
    print(f"Hold-out cases: {len(holdout_cases)}")

    auc_heuristic_ho, hauc_h = panel_auc(holdout_cases, HEURISTIC_WEIGHTS)
    auc_calibrated_ho, hauc_c = panel_auc(holdout_cases, w_calibrated)

    print(f"Heuristic AUC on hold-out:   {auc_heuristic_ho:.4f}  (per-case: {[f'{a:.3f}' for a in hauc_h]})")
    print(f"Calibrated AUC on hold-out:  {auc_calibrated_ho:.4f}  (per-case: {[f'{a:.3f}' for a in hauc_c]})")
    delta = auc_calibrated_ho - auc_heuristic_ho
    print(f"Delta AUC (calib - heur):    {delta:+.4f}")
    print()

    # === CRITÈRE 3 ===
    threshold_c3 = 0.05
    c3_pass = delta >= threshold_c3
    print(f"=== CRITÈRE 3 — calibration bat heuristic ≥ +0.05 AUC sur hold-out ===")
    print(f"  Threshold: delta AUC >= {threshold_c3}")
    print(f"  Observed: {delta:+.4f}")
    print(f"  VERDICT C3: {'OUI' if c3_pass else 'NON'}")
    print()

    summary = {
        "n_train_cases": len(train_cases),
        "n_train_rows": len(X_train),
        "n_holdout_cases": len(holdout_cases),
        "method": method,
        "weights_calibrated": w_calibrated,
        "weights_heuristic": HEURISTIC_WEIGHTS,
        "auc_train_grid": auc_grid,
        "auc_train_logreg": auc_logreg,
        "auc_train_heuristic": auc_heuristic_train,
        "auc_holdout_heuristic": auc_heuristic_ho,
        "auc_holdout_calibrated": auc_calibrated_ho,
        "delta_auc": delta,
        "threshold_c3": threshold_c3,
        "verdict_c3": "OUI" if c3_pass else "NON",
    }
    (ROOT / 'phase_b_results.json').write_text(json.dumps(summary, indent=2))
    print(f"Saved phase_b_results.json")


if __name__ == "__main__":
    main()
