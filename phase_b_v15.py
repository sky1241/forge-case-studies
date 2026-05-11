#!/usr/bin/env python3
"""Phase B v5 — Calibration N=112 train + test N=29 hold-out (cycle 14)."""
import csv, json, math, random
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
BENCH = ROOT / 'bench_v15' / 'results'

HEURISTIC = {"kalman": 0.20, "wavelet": 0.15, "crash": 0.20,
              "coupling": 0.15, "churn": 0.15, "complexity": 0.15}
SIGNALS = ["kalman", "wavelet", "crash", "coupling", "churn", "complexity"]


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
    xn = [f.get('complexity', 0.0) for f in files]
    out = []
    for i, f in enumerate(files):
        s = (weights['kalman']*kn[i] + weights['wavelet']*wn[i]
             + weights['crash']*cn[i] + weights['coupling']*cpn[i]
             + weights['churn']*chn[i] + weights.get('complexity', 0.0)*xn[i])
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
    payloads = []
    results = [json.loads(l) for l in open(ROOT / f'results_v15_{panel}.jsonl') if l.strip()]
    by_id = {r['bug_id']: r for r in results}
    for jf in BENCH.rglob('carmack_full.json'):
        bug_id = jf.parent.name
        if bug_id not in by_id: continue
        meta = by_id[bug_id]
        if meta.get('status') != 'ok': continue
        if meta.get('panel') != panel: continue
        payload = json.loads(jf.read_text())
        payload['panel'] = panel
        payload['bucket'] = meta['bucket']
        payload['regime'] = meta.get('regime', 'history')
        payloads.append(payload)
    return payloads


def grid_random_search(payloads, n=5000):
    rng = random.Random(48)
    best = (0.0, HEURISTIC)
    for _ in range(n):
        raw = [rng.random() for _ in range(6)]
        s = sum(raw)
        w = {k: v/s for k, v in zip(SIGNALS, raw)}
        a, _ = panel_auc(payloads, w)
        if a > best[0]:
            best = (a, w)
    return best


def main():
    train_payloads = load_panel('train')
    holdout_payloads = load_panel('holdout')
    print(f"TRAIN: {len(train_payloads)} | HOLDOUT: {len(holdout_payloads)}\n")

    auc_h_train, _ = panel_auc(train_payloads, HEURISTIC)
    print(f"Heuristic AUC train:  {auc_h_train:.4f}")

    auc_g_train, w_grid = grid_random_search(train_payloads, n=5000)
    print(f"Grid AUC train:       {auc_g_train:.4f}  (gain {auc_g_train-auc_h_train:+.4f})")
    print(f"Grid weights: {w_grid}\n")

    auc_h_ho, aucs_h_ho = panel_auc(holdout_payloads, HEURISTIC)
    auc_c_ho, aucs_c_ho = panel_auc(holdout_payloads, w_grid)
    delta = auc_c_ho - auc_h_ho
    threshold = 0.05
    verdict_c3 = "OUI" if delta >= threshold else "NON"
    print(f"Heuristic AUC holdout:  {auc_h_ho:.4f}")
    print(f"Calibrated AUC holdout: {auc_c_ho:.4f}")
    print(f"DELTA AUC: {delta:+.4f}")
    print(f"=== CRITÈRE 3 verdict: {verdict_c3} ===\n")

    # Stratified subset AUC on holdout
    cold_h = [p for p in holdout_payloads if p.get('regime', '').startswith(('A_', 'B_'))]
    hist_h = [p for p in holdout_payloads if p.get('regime') == 'history']
    if cold_h:
        a_cs_h, _ = panel_auc(cold_h, HEURISTIC)
        a_cs_c, _ = panel_auc(cold_h, w_grid)
        print(f"Cold-start HOLDOUT AUC: heuristic={a_cs_h:.4f} calibrated={a_cs_c:.4f} (n={len(cold_h)})")
    if hist_h:
        a_h_h, _ = panel_auc(hist_h, HEURISTIC)
        a_h_c, _ = panel_auc(hist_h, w_grid)
        print(f"History HOLDOUT AUC: heuristic={a_h_h:.4f} calibrated={a_h_c:.4f} (n={len(hist_h)})")

    summary = {
        "n_train": len(train_payloads), "n_holdout": len(holdout_payloads),
        "auc_train_heuristic": auc_h_train, "auc_train_grid": auc_g_train,
        "weights_calibrated": w_grid,
        "auc_holdout_heuristic": auc_h_ho, "auc_holdout_calibrated": auc_c_ho,
        "delta_auc": delta, "threshold_c3": threshold,
        "verdict_c3": verdict_c3,
    }
    (ROOT / 'phase_b_v15_results.json').write_text(json.dumps(summary, indent=2))
    print(f"\nSaved phase_b_v15_results.json")


if __name__ == "__main__":
    main()
