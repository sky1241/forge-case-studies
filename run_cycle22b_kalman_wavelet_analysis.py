#!/usr/bin/env python3
"""Cycle 22B — Deep analysis kalman + wavelet utility.

Why does calibration ML say 3%/2% (cycle 14) but ablation says -16.7 pts
on panel_ref (cycle 19 v2)?

Tests 4 hypotheses via pure stdlib analysis on cycle 15 carmack_full.json.
"""
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')

BASELINE = {"kalman": 0.20, "wavelet": 0.15, "crash": 0.20,
             "coupling": 0.15, "churn": 0.15, "complexity": 0.15}
ABLATION = {"kalman": 0.0, "wavelet": 0.0, "crash": 0.2875,
             "coupling": 0.2375, "churn": 0.2375, "complexity": 0.2375}


def _minmax(values):
    if not values: return []
    lo, hi = min(values), max(values)
    if hi == lo: return [0.0]*len(values)
    return [(v - lo) / (hi - lo) for v in values]


def recompose_score(results, weights):
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


def get_rank(scored, target):
    for i, r in enumerate(scored):
        if r['file'] == target: return i + 1
    return None


def load_payloads(bench_dir, results_jsonl):
    results = [json.loads(l) for l in open(ROOT / results_jsonl) if l.strip()]
    by_id = {r['bug_id']: r for r in results}
    payloads = []
    for jf in (ROOT / bench_dir).rglob('carmack_full.json'):
        bug_id = jf.parent.name
        if bug_id not in by_id: continue
        if by_id[bug_id].get('status') != 'ok': continue
        p = json.loads(jf.read_text())
        p['bucket'] = jf.parent.parent.name
        p['project'] = bug_id.rsplit('-', 1)[0]
        payloads.append(p)
    return payloads


# === H1: Distribution analysis ===
def analyze_distribution(payloads, signal_name: str) -> dict:
    """Collect all file-level values of `signal_name` across all payloads."""
    all_vals = []
    buggy_vals = []
    non_buggy_vals = []
    for p in payloads:
        change_file = p['change_file']
        for r in p['results']:
            v = r.get(signal_name, 0.0)
            all_vals.append(v)
            if r['file'] == change_file:
                buggy_vals.append(v)
            else:
                non_buggy_vals.append(v)

    def stats(vals):
        if not vals: return {'n': 0}
        n = len(vals)
        n_zero = sum(1 for v in vals if v == 0.0 or abs(v) < 1e-30)
        n_micro = sum(1 for v in vals if abs(v) < 1e-10)
        sorted_v = sorted(vals)
        return {
            'n': n,
            'n_zero': n_zero,
            'pct_zero': round(100 * n_zero / n, 2),
            'n_micro_below_1e10': n_micro,
            'pct_micro': round(100 * n_micro / n, 2),
            'min': sorted_v[0],
            'max': sorted_v[-1],
            'median': sorted_v[n // 2],
            'mean': sum(vals) / n,
            'p75': sorted_v[int(n * 0.75)],
            'p90': sorted_v[int(n * 0.90)],
            'p95': sorted_v[int(n * 0.95)],
            'p99': sorted_v[min(int(n * 0.99), n-1)],
        }

    return {
        'signal': signal_name,
        'all': stats(all_vals),
        'buggy_files': stats(buggy_vals),
        'non_buggy_files': stats(non_buggy_vals),
    }


# === H2: Borderline cases on panel_reference ===
def find_borderline(payloads):
    """For each case, identify if rank flips top10 between baseline and ablation."""
    out = []
    for p in payloads:
        sb = recompose_score(p['results'], BASELINE)
        sa = recompose_score(p['results'], ABLATION)
        target = p['change_file']
        rb = get_rank(sb, target)
        ra = get_rank(sa, target)
        if rb is None or ra is None: continue
        in_top10_b = rb <= 10
        in_top10_a = ra <= 10
        flip = 'NONE'
        if in_top10_b and not in_top10_a:
            flip = 'LOST_baseline_top10_to_outside'
        elif not in_top10_b and in_top10_a:
            flip = 'GAINED_outside_to_ablation_top10'
        # Find kalman/wavelet values for target file
        target_row = next((r for r in p['results'] if r['file'] == target), None)
        out.append({
            'bug_id': p['bug_id'],
            'project': p['project'],
            'bucket': p['bucket'],
            'rank_baseline': rb,
            'rank_ablation': ra,
            'in_top10_baseline': in_top10_b,
            'in_top10_ablation': in_top10_a,
            'flip': flip,
            'target_kalman': target_row.get('kalman', 0) if target_row else None,
            'target_wavelet_hf': target_row.get('wavelet_hf', 0) if target_row else None,
        })
    return out


# === H3: Per-project distribution ===
def per_project_signal_dist(payloads):
    groups = defaultdict(lambda: {'kalman': [], 'wavelet': []})
    for p in payloads:
        for r in p['results']:
            groups[p['project']]['kalman'].append(r.get('kalman', 0))
            groups[p['project']]['wavelet'].append(r.get('wavelet_hf', 0))
    out = {}
    for proj, signals in groups.items():
        out[proj] = {}
        for sn, vals in signals.items():
            if not vals: continue
            n_zero = sum(1 for v in vals if abs(v) < 1e-30)
            out[proj][sn] = {
                'n': len(vals),
                'pct_zero': round(100 * n_zero / len(vals), 1),
                'mean': sum(vals) / len(vals),
                'max': max(vals),
            }
    return out


# === H4: Calibration variation cross-cycle ===
def calibration_variation():
    """Comparison cycle 14 v5 vs cycle 15 v6 weights (from rapport historique)."""
    return {
        'cycle_14_v5_N141': {
            'kalman': 0.033, 'wavelet': 0.019, 'crash': 0.09,
            'coupling': 0.40, 'churn': 0.08, 'complexity': 0.39,
        },
        'cycle_15_v6_N131': {
            'kalman': 0.16, 'wavelet': 0.004, 'crash': 0.21,
            'coupling': 0.13, 'churn': 0.06, 'complexity': 0.45,
        },
        'kalman_variation_factor': round(0.16 / max(0.033, 1e-6), 2),
        'wavelet_variation_factor': round(0.019 / max(0.004, 1e-6), 2),
    }


def main():
    train_p = load_payloads('bench_v15', 'results_v15_train.jsonl')
    holdout_p = load_payloads('bench_v15', 'results_v15_holdout.jsonl')
    ref_p = load_payloads('bench_v15_reference', 'results_v15_reference_train.jsonl')
    all_p = train_p + holdout_p
    print(f'Loaded {len(train_p)} train, {len(holdout_p)} holdout, {len(ref_p)} ref')

    # H1 — Distribution
    print(f'\n=== H1: Distribution analysis ===')
    h1_kalman_th = analyze_distribution(all_p, 'kalman')
    h1_wavelet_th = analyze_distribution(all_p, 'wavelet_hf')
    h1_kalman_ref = analyze_distribution(ref_p, 'kalman')
    h1_wavelet_ref = analyze_distribution(ref_p, 'wavelet_hf')

    print(f'TRAIN+HOLDOUT N={len(all_p)} kalman: {h1_kalman_th["all"]["pct_zero"]}% zero, median={h1_kalman_th["all"]["median"]:.4e}, p95={h1_kalman_th["all"]["p95"]:.4e}')
    print(f'TRAIN+HOLDOUT N={len(all_p)} wavelet: {h1_wavelet_th["all"]["pct_zero"]}% zero, median={h1_wavelet_th["all"]["median"]:.4e}, p95={h1_wavelet_th["all"]["p95"]:.4e}')
    print(f'PANEL_REF N={len(ref_p)}     kalman: {h1_kalman_ref["all"]["pct_zero"]}% zero, median={h1_kalman_ref["all"]["median"]:.4e}, p95={h1_kalman_ref["all"]["p95"]:.4e}')
    print(f'PANEL_REF N={len(ref_p)}     wavelet: {h1_wavelet_ref["all"]["pct_zero"]}% zero, median={h1_wavelet_ref["all"]["median"]:.4e}, p95={h1_wavelet_ref["all"]["p95"]:.4e}')

    # Buggy vs non-buggy distribution
    print(f'\n  Buggy vs non-buggy (TRAIN+HOLDOUT) kalman:')
    print(f'    buggy:     n={h1_kalman_th["buggy_files"]["n"]} median={h1_kalman_th["buggy_files"]["median"]:.4e} mean={h1_kalman_th["buggy_files"]["mean"]:.4e}')
    print(f'    non-buggy: n={h1_kalman_th["non_buggy_files"]["n"]} median={h1_kalman_th["non_buggy_files"]["median"]:.4e} mean={h1_kalman_th["non_buggy_files"]["mean"]:.4e}')
    print(f'\n  Buggy vs non-buggy (TRAIN+HOLDOUT) wavelet:')
    print(f'    buggy:     n={h1_wavelet_th["buggy_files"]["n"]} median={h1_wavelet_th["buggy_files"]["median"]:.4e} mean={h1_wavelet_th["buggy_files"]["mean"]:.4e}')
    print(f'    non-buggy: n={h1_wavelet_th["non_buggy_files"]["n"]} median={h1_wavelet_th["non_buggy_files"]["median"]:.4e} mean={h1_wavelet_th["non_buggy_files"]["mean"]:.4e}')

    # H2 — Borderline cases on panel_ref
    print(f'\n=== H2: Panel_reference borderline cases ===')
    h2_ref = find_borderline(ref_p)
    n_lost = sum(1 for c in h2_ref if c['flip'] == 'LOST_baseline_top10_to_outside')
    n_gained = sum(1 for c in h2_ref if c['flip'] == 'GAINED_outside_to_ablation_top10')
    n_stable = sum(1 for c in h2_ref if c['flip'] == 'NONE')
    print(f'  N={len(h2_ref)} cases')
    print(f'  LOST top10 with ablation: {n_lost}')
    print(f'  GAINED top10 with ablation: {n_gained}')
    print(f'  Stable: {n_stable}')

    flipped = [c for c in h2_ref if c['flip'] != 'NONE']
    print(f'\n  Borderline cases (flipped):')
    for c in flipped:
        print(f'    {c["bug_id"]:18s} {c["flip"]:35s} rank {c["rank_baseline"]}→{c["rank_ablation"]} '
              f'kalman={c["target_kalman"]:.2e} wavelet={c["target_wavelet_hf"]:.2e}')

    # H3 — Per-project
    print(f'\n=== H3: Per-project signal distribution (TRAIN+HOLDOUT) ===')
    h3_th = per_project_signal_dist(all_p)
    for proj, sigs in sorted(h3_th.items()):
        kw = sigs.get('kalman', {})
        ww = sigs.get('wavelet', {})
        print(f'  {proj:15s} kalman: {kw.get("pct_zero", 0):5.1f}% zero, max={kw.get("max", 0):.2e} | '
              f'wavelet: {ww.get("pct_zero", 0):5.1f}% zero, max={ww.get("max", 0):.2e}')

    # H4 — Calibration variation
    print(f'\n=== H4: Calibration variation cross-cycle ===')
    h4 = calibration_variation()
    print(f'  Kalman v5→v6: {h4["cycle_14_v5_N141"]["kalman"]} → {h4["cycle_15_v6_N131"]["kalman"]} (x{h4["kalman_variation_factor"]})')
    print(f'  Wavelet v5→v6: {h4["cycle_14_v5_N141"]["wavelet"]} → {h4["cycle_15_v6_N131"]["wavelet"]} (x{h4["wavelet_variation_factor"]})')

    # Save
    out_full = {
        'cycle': '22B',
        'methodology': 'pure stdlib analysis on cycle 15 data',
        'h1_distribution': {
            'train_holdout_kalman': h1_kalman_th,
            'train_holdout_wavelet': h1_wavelet_th,
            'panel_ref_kalman': h1_kalman_ref,
            'panel_ref_wavelet': h1_wavelet_ref,
        },
        'h2_borderline_panel_ref': {
            'cases': h2_ref,
            'n_lost': n_lost,
            'n_gained': n_gained,
            'n_stable': n_stable,
        },
        'h3_per_project_train_holdout': h3_th,
        'h4_calibration_variation': h4,
    }
    (ROOT / 'cycle22b_full_analysis.json').write_text(json.dumps(out_full, indent=2, default=str))
    print(f'\nSaved cycle22b_full_analysis.json')


if __name__ == '__main__':
    main()
