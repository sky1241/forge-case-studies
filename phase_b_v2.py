#!/usr/bin/env python3
"""Phase B v2 — Calibration N=8 train + test N=7 hold-out.

Uses bench/results/{bucket}/{bug_id}/carmack_full.json data.
"""
import csv, json, math, random
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
BENCH = ROOT / 'bench' / 'results'

HEURISTIC = {"kalman": 0.20, "wavelet": 0.15, "crash": 0.25, "coupling": 0.15, "churn": 0.25}


def _minmax(values):
    if not values: return []
    lo, hi = min(values), max(values)
    if hi == lo: return [0.0]*len(values)
    return [(v - lo) / (hi - lo) for v in values]


def composite(case_results, weights):
    files = list(case_results)
    kn = _minmax([f['kalman'] for f in files])
    wn = _minmax([f['wavelet_hf'] for f in files])
    cn = [f['crash_prob'] for f in files]
    cpn = _minmax([f['coupling'] for f in files])
    chn = _minmax([f['churn'] for f in files])
    out = []
    for i, f in enumerate(files):
        s = (weights['kalman']*kn[i] + weights['wavelet']*wn[i]
             + weights['crash']*cn[i] + weights['coupling']*cpn[i]
             + weights['churn']*chn[i])
        out.append({**f, 'score_c': s})
    out.sort(key=lambda x: x['score_c'], reverse=True)
    return out


def auc_case(payload, weights):
    scored = composite(payload['results'], weights)
    target = payload['change_file']
    ts = None; others = []
    for f in scored:
        if f['file'] == target:
            ts = f['score_c']
        else:
            others.append(f['score_c'])
    if ts is None or not others: return None
    wins = sum(1 for s in others if s < ts)
    ties = sum(1 for s in others if s == ts)
    return (wins + 0.5*ties) / len(others)


def panel_auc(payloads, weights):
    aucs = [auc_case(p, weights) for p in payloads]
    aucs = [a for a in aucs if a is not None]
    return (sum(aucs)/len(aucs) if aucs else 0.0), aucs


def load_panel(panel: str):
    """Load all carmack_full.json under bench/results, filter by panel."""
    payloads = []
    results = [json.loads(l) for l in open(ROOT / f'results_v2_{panel}.jsonl') if l.strip()]
    by_id = {r['bug_id']: r for r in results}
    for jf in BENCH.rglob('carmack_full.json'):
        bug_id = jf.parent.name
        if bug_id not in by_id: continue
        meta = by_id[bug_id]
        if meta.get('status') != 'ok': continue
        if meta.get('panel') != panel: continue
        payload = json.loads(jf.read_text())
        # Add panel + bucket from results metadata
        payload['panel'] = panel
        payload['bucket'] = meta['bucket']
        payloads.append(payload)
    return payloads


def grid_random_search(payloads, n=3000):
    rng = random.Random(42)
    best = (0.0, HEURISTIC)
    for _ in range(n):
        raw = [rng.random() for _ in range(5)]
        s = sum(raw)
        w = {k: v/s for k, v in zip(['kalman','wavelet','crash','coupling','churn'], raw)}
        a, _ = panel_auc(payloads, w)
        if a > best[0]:
            best = (a, w)
    return best


def main():
    train_payloads = load_panel('train')
    holdout_payloads = load_panel('holdout')
    print(f"TRAIN payloads: {len(train_payloads)}")
    print(f"HOLDOUT payloads: {len(holdout_payloads)}")
    print()

    # Dataset (transparency only)
    X, y = [], []
    for p in train_payloads:
        kn = _minmax([f['kalman'] for f in p['results']])
        wn = _minmax([f['wavelet_hf'] for f in p['results']])
        cn = [f['crash_prob'] for f in p['results']]
        cpn = _minmax([f['coupling'] for f in p['results']])
        chn = _minmax([f['churn'] for f in p['results']])
        for i, f in enumerate(p['results']):
            X.append([kn[i], wn[i], cn[i], cpn[i], chn[i]])
            y.append(1 if f['file'] == p['change_file'] else 0)
    print(f"Phase B.1 — dataset: {len(X)} rows, {sum(y)} positives ({100*sum(y)/len(X):.2f}%)")
    print()

    # Heuristic baseline
    auc_h_train, _ = panel_auc(train_payloads, HEURISTIC)
    print(f"Heuristic AUC train:  {auc_h_train:.4f}")

    # Grid random search
    auc_g_train, w_grid = grid_random_search(train_payloads, n=3000)
    print(f"Grid AUC train:       {auc_g_train:.4f}")
    print(f"Grid weights: {w_grid}")
    print()

    # Test on HOLDOUT
    print("=== Phase B.3 — HOLDOUT test ===")
    auc_h_ho, aucs_h_ho = panel_auc(holdout_payloads, HEURISTIC)
    auc_c_ho, aucs_c_ho = panel_auc(holdout_payloads, w_grid)
    print(f"Heuristic AUC holdout:  {auc_h_ho:.4f}  per-case {[f'{a:.3f}' for a in aucs_h_ho]}")
    print(f"Calibrated AUC holdout: {auc_c_ho:.4f}  per-case {[f'{a:.3f}' for a in aucs_c_ho]}")
    delta = auc_c_ho - auc_h_ho
    print(f"DELTA AUC: {delta:+.4f}")
    print()
    threshold = 0.05
    verdict_c3 = "OUI" if delta >= threshold else "NON"
    print(f"=== CRITÈRE 3 ===")
    print(f"  Threshold: delta_AUC >= {threshold}")
    print(f"  Observed: {delta:+.4f}")
    print(f"  VERDICT: {verdict_c3}")

    summary = {
        "n_train": len(train_payloads), "n_holdout": len(holdout_payloads),
        "rows_dataset": len(X), "positives": sum(y),
        "auc_train_heuristic": auc_h_train, "auc_train_grid": auc_g_train,
        "weights_calibrated": w_grid,
        "auc_holdout_heuristic": auc_h_ho, "auc_holdout_calibrated": auc_c_ho,
        "delta_auc": delta, "threshold_c3": threshold,
        "verdict_c3": verdict_c3,
    }
    (ROOT / 'phase_b_v2_results.json').write_text(json.dumps(summary, indent=2))
    print(f"\nSaved phase_b_v2_results.json")


if __name__ == "__main__":
    main()
