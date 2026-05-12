#!/usr/bin/env python3
"""Cycle 23A — Single-signal performance per algo (NO composite).

For each of 6 signals (kalman, wavelet_hf, crash_prob, coupling, churn,
complexity), compute:
- precision@10 ranking by that signal alone
- AUC (single-signal vs was_buggy)
- Spearman rank correlation
- Comparison to random baseline
"""
import json
import math
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')

SIGNALS = ['kalman', 'wavelet_hf', 'crash_prob', 'coupling', 'churn', 'complexity']


def load_payloads(bench_dir, results_jsonl):
    results = [json.loads(l) for l in open(ROOT / results_jsonl) if l.strip()]
    by_id = {r['bug_id']: r for r in results}
    payloads = []
    for jf in (ROOT / bench_dir).rglob('carmack_full.json'):
        bug_id = jf.parent.name
        if bug_id not in by_id: continue
        if by_id[bug_id].get('status') != 'ok': continue
        p = json.loads(jf.read_text())
        p['project'] = bug_id.rsplit('-', 1)[0]
        p['bucket'] = jf.parent.parent.name
        payloads.append(p)
    return payloads


def rank_by_signal(results, signal):
    """Sort files desc by signal value. Return list of file names."""
    return [r['file'] for r in sorted(results, key=lambda x: x.get(signal, 0), reverse=True)]


def precision_at_k(payloads, signal, k=10):
    """Fraction of cases where target file is in top-k by signal."""
    n_hit = 0
    n = 0
    for p in payloads:
        ranked = rank_by_signal(p['results'], signal)
        target = p['change_file']
        if target in ranked:
            rank = ranked.index(target) + 1
            n += 1
            if rank <= k:
                n_hit += 1
    return 100 * n_hit / max(n, 1), n_hit, n


def auc_single_signal(payloads, signal):
    """Mean reciprocal rank as proxy (true AUC needs continuous threshold).
    Here we use averaged-rank normalized: AUC = 1 - (rank-1)/(N-1) averaged.
    """
    rrs = []  # reciprocal ranks
    aucs = []  # normalized rank-based AUC
    for p in payloads:
        ranked = rank_by_signal(p['results'], signal)
        target = p['change_file']
        if target in ranked:
            rank = ranked.index(target) + 1
            N = len(ranked)
            rrs.append(1.0 / rank)
            # AUC ranking: 1 if rank=1, 0 if rank=N
            if N > 1:
                aucs.append(1.0 - (rank - 1) / (N - 1))
            else:
                aucs.append(0.5)
    return {
        'mrr': sum(rrs) / max(len(rrs), 1),
        'auc_rank': sum(aucs) / max(len(aucs), 1),
        'n': len(rrs),
    }


def random_baseline(payloads, k=10, n_trials=1000):
    """Simulate random ranking: target placed uniformly at random in N files."""
    import random
    rng = random.Random(58)
    n_hit = 0
    n_total = 0
    for _ in range(n_trials):
        for p in payloads:
            N = len(p['results'])
            if N == 0: continue
            rank = rng.randint(1, N)
            n_total += 1
            if rank <= k:
                n_hit += 1
    return 100 * n_hit / max(n_total, 1)


def spearman_correlation(payloads, signal):
    """For each case, compute Spearman corr between rank-by-signal and
    target-is-target binary. Approximate: mean rank of target across cases /
    max rank.
    """
    ranks = []
    for p in payloads:
        ranked = rank_by_signal(p['results'], signal)
        target = p['change_file']
        if target in ranked:
            rank = ranked.index(target) + 1
            N = len(ranked)
            # Normalize: 0=top, 1=bottom
            ranks.append((rank - 1) / max(N - 1, 1))
    if not ranks: return 0.0
    mean_norm_rank = sum(ranks) / len(ranks)
    # Spearman analog: 1 = perfect (target always top), -1 = worst
    return 1.0 - 2 * mean_norm_rank


def main():
    train_p = load_payloads('bench_v15', 'results_v15_train.jsonl')
    holdout_p = load_payloads('bench_v15', 'results_v15_holdout.jsonl')
    ref_p = load_payloads('bench_v15_reference', 'results_v15_reference_train.jsonl')
    all_p = train_p + holdout_p
    print(f'Loaded {len(train_p)} train, {len(holdout_p)} holdout, {len(ref_p)} ref')

    rand_baseline_th = random_baseline(all_p, k=10)
    rand_baseline_ref = random_baseline(ref_p, k=10)
    print(f'\nRandom baseline TH N={len(all_p)}: {rand_baseline_th:.2f}%')
    print(f'Random baseline REF N={len(ref_p)}: {rand_baseline_ref:.2f}%')

    results_th = {}
    results_ref = {}
    for sig in SIGNALS:
        p10_th, hit_th, n_th = precision_at_k(all_p, sig, k=10)
        p10_ref, hit_ref, n_ref = precision_at_k(ref_p, sig, k=10)
        auc_th = auc_single_signal(all_p, sig)
        auc_ref = auc_single_signal(ref_p, sig)
        sp_th = spearman_correlation(all_p, sig)
        sp_ref = spearman_correlation(ref_p, sig)
        results_th[sig] = {
            'precision_at_10_pct': round(p10_th, 2),
            'hit_count': hit_th, 'n_total': n_th,
            'mrr': round(auc_th['mrr'], 4),
            'auc_rank': round(auc_th['auc_rank'], 4),
            'spearman': round(sp_th, 4),
        }
        results_ref[sig] = {
            'precision_at_10_pct': round(p10_ref, 2),
            'hit_count': hit_ref, 'n_total': n_ref,
            'mrr': round(auc_ref['mrr'], 4),
            'auc_rank': round(auc_ref['auc_rank'], 4),
            'spearman': round(sp_ref, 4),
        }

    print(f'\n=== TRAIN+HOLDOUT N={len(all_p)} (single-signal) ===')
    print(f'{"Signal":15s} {"p@10":>8s} {"MRR":>8s} {"AUC":>8s} {"Spearman":>10s} {"vs random":>12s}')
    for sig, r in results_th.items():
        ratio_rand = r['precision_at_10_pct'] / max(rand_baseline_th, 0.01)
        print(f'{sig:15s} {r["precision_at_10_pct"]:>7.2f}% {r["mrr"]:>8.4f} {r["auc_rank"]:>8.4f} {r["spearman"]:>10.4f} {ratio_rand:>11.2f}x')

    print(f'\n=== PANEL_REF N={len(ref_p)} (single-signal) ===')
    print(f'{"Signal":15s} {"p@10":>8s} {"MRR":>8s} {"AUC":>8s} {"Spearman":>10s} {"vs random":>12s}')
    for sig, r in results_ref.items():
        ratio_rand = r['precision_at_10_pct'] / max(rand_baseline_ref, 0.01)
        print(f'{sig:15s} {r["precision_at_10_pct"]:>7.2f}% {r["mrr"]:>8.4f} {r["auc_rank"]:>8.4f} {r["spearman"]:>10.4f} {ratio_rand:>11.2f}x')

    # Verdict per signal
    print(f'\n=== Verdict per signal (TH, threshold 2x random = {2*rand_baseline_th:.1f}%) ===')
    verdicts = {}
    for sig, r in results_th.items():
        if r['precision_at_10_pct'] >= 2 * rand_baseline_th:
            v = 'USEFUL_SOLO'
        elif r['precision_at_10_pct'] >= rand_baseline_th:
            v = 'MARGINAL'
        else:
            v = 'USELESS_SOLO'
        verdicts[sig] = v
        print(f'  {sig:15s} → {v}')

    summary = {
        'cycle': '23A',
        'random_baseline_th_pct': round(rand_baseline_th, 2),
        'random_baseline_ref_pct': round(rand_baseline_ref, 2),
        'train_holdout': results_th,
        'panel_ref': results_ref,
        'verdicts_th': verdicts,
        'n_train_holdout': len(all_p),
        'n_panel_ref': len(ref_p),
    }
    (ROOT / 'cycle23a_results.json').write_text(json.dumps(summary, indent=2))
    print(f'\nSaved cycle23a_results.json')


if __name__ == '__main__':
    main()
