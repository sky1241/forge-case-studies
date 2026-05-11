#!/usr/bin/env python3
"""Cycle 19 — ablation drop kalman + wavelet. Reuse cycle 15 data."""
import json
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')

# Weights
BASELINE = {"kalman": 0.20, "wavelet": 0.15, "crash": 0.20,
             "coupling": 0.15, "churn": 0.15, "complexity": 0.15}
# Drop kalman + wavelet (0.35 total). Redistribute equally on remaining 4 signals.
ABLATION = {"kalman": 0.0, "wavelet": 0.0, "crash": 0.20 + 0.0875,
             "coupling": 0.15 + 0.0875, "churn": 0.15 + 0.0875, "complexity": 0.15 + 0.0875}
# Round to nice: crash 0.2875, coupling 0.2375, churn 0.2375, complexity 0.2375 (sum 1.0)


def _minmax(values):
    if not values: return []
    lo, hi = min(values), max(values)
    if hi == lo: return [0.0]*len(values)
    return [(v - lo) / (hi - lo) for v in values]


def recompose_score(results, weights):
    """Re-rank results based on supplied weights. Returns sorted list."""
    files = list(results)
    if not files: return []
    kn = _minmax([f.get('kalman', 0) for f in files])
    wn = _minmax([f.get('wavelet_hf', 0) for f in files])
    cn = [f.get('crash_prob', 0) for f in files]
    cpn = _minmax([f.get('coupling', 0) for f in files])
    chn = _minmax([f.get('churn', 0) for f in files])
    xn = [f.get('complexity', 0) for f in files]
    out = []
    for i, f in enumerate(files):
        s = (weights['kalman']*kn[i] + weights['wavelet']*wn[i]
             + weights['crash']*cn[i] + weights['coupling']*cpn[i]
             + weights['churn']*chn[i] + weights['complexity']*xn[i])
        out.append({**f, 'new_score': s})
    out.sort(key=lambda x: x['new_score'], reverse=True)
    return out


def measure(payloads, weights, label):
    top10 = 0
    n = 0
    for p in payloads:
        scored = recompose_score(p['results'], weights)
        target = p['change_file']
        rank = next((i+1 for i,r in enumerate(scored) if r['file']==target), None)
        if rank is not None:
            n += 1
            if rank <= 10:
                top10 += 1
    ratio = 100*top10/max(n,1)
    print(f'  {label}: top10={top10}/{n} = {ratio:.1f}%')
    return ratio


def load_payloads(bench_dir, results_jsonl):
    """Load carmack_full.json for cases that passed (status=ok in results)."""
    results = [json.loads(l) for l in open(ROOT / results_jsonl) if l.strip()]
    by_id = {r['bug_id']: r for r in results}
    payloads = []
    for jf in (ROOT / bench_dir).rglob('carmack_full.json'):
        bug_id = jf.parent.name
        if bug_id not in by_id: continue
        if by_id[bug_id].get('status') != 'ok': continue
        p = json.loads(jf.read_text())
        payloads.append(p)
    return payloads


def main():
    print(f'Cycle 19 — ablation drop kalman + wavelet\n')
    print(f'BASELINE weights: {BASELINE}')
    print(f'ABLATION weights: {ABLATION}\n')

    # Cycle 15 train+holdout
    print('=== cycle 15 train+holdout ===')
    train_p = load_payloads('bench_v15', 'results_v15_train.jsonl')
    holdout_p = load_payloads('bench_v15', 'results_v15_holdout.jsonl')
    print(f'Loaded {len(train_p)} train, {len(holdout_p)} holdout payloads')
    all_p = train_p + holdout_p
    print(f'Combined N={len(all_p)}')

    print('TRAIN+HOLDOUT (cycle 15 panel):')
    base_ratio = measure(all_p, BASELINE, 'baseline (6 sig)')
    ablation_ratio = measure(all_p, ABLATION, 'ablation (4 sig)')
    delta = ablation_ratio - base_ratio
    print(f'\nDELTA = {delta:+.1f} pts (threshold ±2 pts)')
    print(f'C_ablation: {"OUI (maintien)" if abs(delta) <= 2 else "NON"}')

    print()

    # panel_reference
    print('=== panel_reference v2 (20 cas) ===')
    ref_p = load_payloads('bench_v15_reference', 'results_v15_reference_train.jsonl')
    print(f'Loaded {len(ref_p)} reference payloads')
    ref_base = measure(ref_p, BASELINE, 'baseline (6 sig)')
    ref_ablation = measure(ref_p, ABLATION, 'ablation (4 sig)')
    ref_delta = ref_ablation - ref_base
    print(f'\nPANEL_REFERENCE DELTA = {ref_delta:+.1f} pts')

    summary = {
        'baseline_weights': BASELINE,
        'ablation_weights': ABLATION,
        'cycle15_baseline_top10': base_ratio,
        'cycle15_ablation_top10': ablation_ratio,
        'cycle15_delta': delta,
        'panel_ref_baseline_top10': ref_base,
        'panel_ref_ablation_top10': ref_ablation,
        'panel_ref_delta': ref_delta,
        'verdict_c_ablation': 'OUI' if abs(delta) <= 2 else 'NON',
        'verdict_panel_ref': 'AMÉLIORATION' if ref_delta > 2 else 'STAGNATION' if abs(ref_delta) <= 2 else 'RÉGRESSION',
    }
    (ROOT / 'cycle19_ablation_results.json').write_text(json.dumps(summary, indent=2))
    print(f'\nSaved cycle19_ablation_results.json')


if __name__ == '__main__':
    main()
