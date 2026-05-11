#!/usr/bin/env python3
"""Cycle 19 v2 — investigate why N=18 (panel_ref) disagrees with N=131 (train+holdout)."""
import json
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


def get_rank(scored, target_file):
    for i, r in enumerate(scored):
        if r['file'] == target_file:
            return i + 1
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


def per_case_deltas(payloads):
    """For each case compute (rank_baseline, rank_ablation, delta_rank).
    delta < 0 = ablation BETTER (higher rank in baseline = worse, lower rank = better).
    """
    out = []
    for p in payloads:
        sb = recompose_score(p['results'], BASELINE)
        sa = recompose_score(p['results'], ABLATION)
        target = p['change_file']
        rb = get_rank(sb, target)
        ra = get_rank(sa, target)
        if rb is None or ra is None: continue
        out.append({
            'bug_id': p['bug_id'],
            'project': p['project'],
            'bucket': p['bucket'],
            'total_files': p.get('total_files', len(p['results'])),
            'rank_baseline': rb,
            'rank_ablation': ra,
            'delta_rank': ra - rb,  # >0 = ablation worse, <0 = ablation better
            'in_top10_baseline': rb <= 10,
            'in_top10_ablation': ra <= 10,
        })
    return out


def aggregate(deltas, group_key):
    groups = defaultdict(list)
    for d in deltas:
        groups[d[group_key]].append(d)
    summary = []
    for k, cases in sorted(groups.items()):
        n = len(cases)
        top10_b = sum(1 for c in cases if c['in_top10_baseline'])
        top10_a = sum(1 for c in cases if c['in_top10_ablation'])
        delta_avg = sum(c['delta_rank'] for c in cases) / n
        delta_med = sorted(c['delta_rank'] for c in cases)[n // 2]
        summary.append({
            group_key: k,
            'n': n,
            'top10_baseline': f'{top10_b}/{n} = {100*top10_b/n:.1f}%',
            'top10_ablation': f'{top10_a}/{n} = {100*top10_a/n:.1f}%',
            'delta_top10_pts': 100*(top10_a - top10_b)/n,
            'delta_rank_avg': round(delta_avg, 2),
            'delta_rank_median': delta_med,
        })
    return summary


def main():
    train_p = load_payloads('bench_v15', 'results_v15_train.jsonl')
    holdout_p = load_payloads('bench_v15', 'results_v15_holdout.jsonl')
    ref_p = load_payloads('bench_v15_reference', 'results_v15_reference_train.jsonl')
    train_holdout = train_p + holdout_p
    print(f'Loaded {len(train_p)} train, {len(holdout_p)} holdout, {len(ref_p)} ref')

    # Overlap: which panel_ref cases are also in train+holdout ?
    th_ids = {p['bug_id'] for p in train_holdout}
    ref_ids = {p['bug_id'] for p in ref_p}
    overlap = ref_ids & th_ids
    only_ref = ref_ids - th_ids
    print(f'\noverlap panel_ref ∩ train+holdout = {len(overlap)} cas')
    print(f'panel_ref UNIQUE (not in train+holdout) = {len(only_ref)} cas')
    if only_ref:
        print(f'  IDs: {sorted(only_ref)}')

    # Per-case deltas
    deltas_th = per_case_deltas(train_holdout)
    deltas_ref = per_case_deltas(ref_p)

    # Save raw per-case
    with (ROOT / 'cycle19_v2_per_case_train_holdout.jsonl').open('w') as f:
        for d in deltas_th: f.write(json.dumps(d) + '\n')
    with (ROOT / 'cycle19_v2_per_case_ref.jsonl').open('w') as f:
        for d in deltas_ref: f.write(json.dumps(d) + '\n')

    # Aggregate per bucket and per project
    bk_th = aggregate(deltas_th, 'bucket')
    pr_th = aggregate(deltas_th, 'project')
    bk_ref = aggregate(deltas_ref, 'bucket')
    pr_ref = aggregate(deltas_ref, 'project')

    print('\n=== TRAIN+HOLDOUT (N=131) per bucket ===')
    for r in bk_th: print(f"  {r['bucket']:8s} n={r['n']:3d}  delta_top10={r['delta_top10_pts']:+6.1f} pts  delta_rank_avg={r['delta_rank_avg']:+7.2f}")
    print('\n=== TRAIN+HOLDOUT (N=131) per project ===')
    for r in pr_th: print(f"  {r['project']:15s} n={r['n']:3d}  delta_top10={r['delta_top10_pts']:+6.1f} pts  delta_rank_avg={r['delta_rank_avg']:+7.2f}")
    print('\n=== PANEL_REF (N=18) per bucket ===')
    for r in bk_ref: print(f"  {r['bucket']:8s} n={r['n']:3d}  delta_top10={r['delta_top10_pts']:+6.1f} pts  delta_rank_avg={r['delta_rank_avg']:+7.2f}")
    print('\n=== PANEL_REF (N=18) per project ===')
    for r in pr_ref: print(f"  {r['project']:15s} n={r['n']:3d}  delta_top10={r['delta_top10_pts']:+6.1f} pts  delta_rank_avg={r['delta_rank_avg']:+7.2f}")

    # Per-case sign tally
    th_help = sum(1 for d in deltas_th if d['delta_rank'] < 0)
    th_hurt = sum(1 for d in deltas_th if d['delta_rank'] > 0)
    th_same = sum(1 for d in deltas_th if d['delta_rank'] == 0)
    ref_help = sum(1 for d in deltas_ref if d['delta_rank'] < 0)
    ref_hurt = sum(1 for d in deltas_ref if d['delta_rank'] > 0)
    ref_same = sum(1 for d in deltas_ref if d['delta_rank'] == 0)
    print(f'\n=== Per-case sign tally ===')
    print(f'  TRAIN+HOLDOUT: ablation helps={th_help}, hurts={th_hurt}, same={th_same} (N={len(deltas_th)})')
    print(f'  PANEL_REF    : ablation helps={ref_help}, hurts={ref_hurt}, same={ref_same} (N={len(deltas_ref)})')

    # Verdict scenarios
    th_help_pct = 100 * th_help / len(deltas_th) if deltas_th else 0
    ref_help_pct = 100 * ref_help / len(deltas_ref) if deltas_ref else 0
    scenario = 'C_AMBIGU'
    if th_help_pct >= 75 and ref_help_pct >= 75:
        scenario = 'B_OUI_ablation_aide'
    elif th_help_pct <= 25 and ref_help_pct <= 25:
        scenario = 'A_NON_ablation_nuit'
    print(f'\n=== Pre-registered verdict ===')
    print(f'  TH help_pct = {th_help_pct:.1f}% (≥75% B, ≤25% A)')
    print(f'  REF help_pct = {ref_help_pct:.1f}%')
    print(f'  Scenario: {scenario}')

    summary = {
        'cycle': '19_v2',
        'n_train_holdout': len(deltas_th),
        'n_panel_ref': len(deltas_ref),
        'overlap_count': len(overlap),
        'only_in_panel_ref': sorted(only_ref),
        'per_bucket_train_holdout': bk_th,
        'per_project_train_holdout': pr_th,
        'per_bucket_panel_ref': bk_ref,
        'per_project_panel_ref': pr_ref,
        'th_help_pct': th_help_pct,
        'ref_help_pct': ref_help_pct,
        'verdict_scenario': scenario,
    }
    (ROOT / 'cycle19_v2_summary.json').write_text(json.dumps(summary, indent=2))
    print(f'\nSaved cycle19_v2_summary.json')


if __name__ == '__main__':
    main()
