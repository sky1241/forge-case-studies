#!/usr/bin/env python3
"""Cycle 24C v2 — Benchmark via direct import predict_carmack (full ranking).

forge --carmack CLI only prints top-15. We need full ranking to compute
precision@10 reliably. Load forge.py modules dynamically (v2.1.0 baseline
vs cycle 24 candidate) and call predict_carmack(root) which returns the
COMPLETE sorted list.
"""
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
CLONES = ROOT / 'clones'
PANEL = json.loads((ROOT / 'panel_reference.json').read_text())
BENCH = ROOT / 'benchmark_cycle24'

FORGE_V210 = '/tmp/forge_v24_bench/forge_v210.py'
FORGE_V220 = '/tmp/forge_v24_bench/forge_v220_cand.py'


def load_forge_module(path: str, mod_name: str):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def run(cmd, cwd=None, timeout=60):
    try:
        r = subprocess.run(cmd, cwd=cwd, timeout=timeout,
                            capture_output=True, text=True, shell=False)
        return r.returncode, r.stdout.strip(), r.stderr
    except Exception as e:
        return -1, '', str(e)


def checkout_head(repo):
    rc, out, _ = run(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD', '--short'],
                     cwd=repo, timeout=10)
    default = out.strip().replace('origin/', '') if rc == 0 and out.strip() else 'master'
    rc, _, _ = run(['git', 'checkout', f'origin/{default}', '--force'],
                     cwd=repo, timeout=60)
    return rc == 0


def get_rank(results: list, target: str) -> int | None:
    """results is sorted desc by score. Return 1-based rank of target."""
    for i, r in enumerate(results, 1):
        f = r.get('file', '')
        if f == target or f.endswith(target) or target.endswith(f):
            return i
    return None


def run_carmack_inproc(forge_mod, repo: Path, weeks: int = 52) -> tuple[list, float]:
    """Call predict_carmack directly in-process. Returns (results, elapsed)."""
    t0 = time.time()
    try:
        results = forge_mod.predict_carmack(repo, weeks=weeks)
        if results is None: results = []
    except Exception as e:
        results = []
        print(f'    EXCEPTION: {type(e).__name__}: {e}')
    return results, time.time() - t0


def main():
    BENCH.mkdir(exist_ok=True)
    forge_v210 = load_forge_module(FORGE_V210, 'forge_v210')
    forge_v220 = load_forge_module(FORGE_V220, 'forge_v220')
    print(f'Loaded forge v2.1.0 from {FORGE_V210}')
    print(f'Loaded forge v2.2.0-cand from {FORGE_V220}\n')

    results_baseline = []
    results_candidate = []

    for case in PANEL:
        bug_id = case['bug_id']
        project = case['project']
        target = case['change_file']
        repo = CLONES / project
        if not repo.is_dir():
            print(f'[{bug_id}] NO_CLONE')
            continue

        checkout_head(repo)
        print(f'\n[{bug_id}] target={target}')

        # Baseline v2.1.0
        sys.modules['forge'] = forge_v210
        # Force re-import _load_forge_config etc from forge_v210
        b_results, b_elapsed = run_carmack_inproc(forge_v210, repo, weeks=52)
        b_rank = get_rank(b_results, target)
        print(f'  v2.1.0 baseline:   n_files={len(b_results)} rank={b_rank} top10={b_rank is not None and b_rank <= 10} elapsed={b_elapsed:.2f}s')
        results_baseline.append({
            'bug_id': bug_id, 'project': project, 'target': target,
            'n_files': len(b_results), 'rank': b_rank,
            'in_top10': b_rank is not None and b_rank <= 10,
            'elapsed': round(b_elapsed, 2),
        })

        # Candidate v2.2.0
        sys.modules['forge'] = forge_v220
        c_results, c_elapsed = run_carmack_inproc(forge_v220, repo, weeks=52)
        c_rank = get_rank(c_results, target)
        print(f'  v2.2.0 candidate:  n_files={len(c_results)} rank={c_rank} top10={c_rank is not None and c_rank <= 10} elapsed={c_elapsed:.2f}s')
        results_candidate.append({
            'bug_id': bug_id, 'project': project, 'target': target,
            'n_files': len(c_results), 'rank': c_rank,
            'in_top10': c_rank is not None and c_rank <= 10,
            'elapsed': round(c_elapsed, 2),
        })

    # Aggregate
    def metrics(rs):
        n_ranked = sum(1 for r in rs if r.get('rank') is not None)
        n_top10 = sum(1 for r in rs if r.get('in_top10'))
        ranks = [r['rank'] for r in rs if r.get('rank') is not None]
        mrr = sum(1.0 / r for r in ranks) / max(len(ranks), 1) if ranks else 0.0
        return {
            'n_total': len(rs), 'n_ranked': n_ranked, 'n_top10': n_top10,
            'p_at_10_pct': round(100 * n_top10 / max(len(rs), 1), 2),
            'mrr': round(mrr, 4),
        }

    m_baseline = metrics(results_baseline)
    m_candidate = metrics(results_candidate)
    delta_p10 = m_candidate['p_at_10_pct'] - m_baseline['p_at_10_pct']
    delta_mrr = m_candidate['mrr'] - m_baseline['mrr']

    print(f'\n=== AGGREGATE ===')
    print(f'BASELINE v2.1.0:    p@10={m_baseline["p_at_10_pct"]:.1f}% ({m_baseline["n_top10"]}/{m_baseline["n_total"]}), MRR={m_baseline["mrr"]:.4f}')
    print(f'CANDIDATE v2.2.0:   p@10={m_candidate["p_at_10_pct"]:.1f}% ({m_candidate["n_top10"]}/{m_candidate["n_total"]}), MRR={m_candidate["mrr"]:.4f}')
    print(f'DELTA:              p@10={delta_p10:+.1f} pts, MRR={delta_mrr:+.4f}')

    if delta_p10 >= 5: verdict = 'VALIDATED'
    elif delta_p10 <= -2: verdict = 'REJECTED'
    else: verdict = 'NEUTRAL'
    print(f'\nVerdict: {verdict}')

    summary = {
        'cycle': '24C_v2_inproc',
        'baseline': m_baseline,
        'candidate': m_candidate,
        'delta_p10_pts': round(delta_p10, 2),
        'delta_mrr': round(delta_mrr, 4),
        'verdict': verdict,
        'thresholds': {'validated': '≥+5', 'rejected': '≤-2', 'neutral': 'else'},
        'results_baseline': results_baseline,
        'results_candidate': results_candidate,
    }
    (ROOT / 'cycle24c_benchmark_summary.json').write_text(json.dumps(summary, indent=2))
    print(f'\nSaved cycle24c_benchmark_summary.json')


if __name__ == '__main__':
    main()
