#!/usr/bin/env python3
"""Cycle 24C — Benchmark v2.1.0 baseline vs cycle 24 candidate on panel_reference v2.

For each of 20 panel cases:
  1. Checkout PRE_BUG state via git
  2. Run forge --carmack with --weeks-from <PRE_BUG_DATE>  (cycle 21A fix)
  3. Capture rank of change_file
  4. Compare baseline (v2.1.0) vs candidate (cycle 24)
"""
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
CLONES = ROOT / 'clones'
FORGE_V210 = '/tmp/forge_v24_bench/forge_v210.py'
FORGE_V220 = '/tmp/forge_v24_bench/forge_v220_cand.py'
PYTHON = '/home/sky/Bureau/forge/.venv/bin/python3'
BENCH = ROOT / 'benchmark_cycle24'
PANEL = json.loads((ROOT / 'panel_reference.json').read_text())


def run(cmd, cwd=None, timeout=120):
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=cwd, timeout=timeout,
                            capture_output=True, text=True, shell=False)
        return r.returncode, r.stdout, r.stderr, time.time() - t0
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b'').decode('utf-8', 'replace') if isinstance(e.stdout, bytes) else (e.stdout or '')
        err = (e.stderr or b'').decode('utf-8', 'replace') if isinstance(e.stderr, bytes) else (e.stderr or '')
        return 124, out, err, time.time() - t0


def checkout_head(repo):
    rc, out, _, _ = run(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD', '--short'],
                       cwd=repo, timeout=10)
    default = out.strip().replace('origin/', '') if rc == 0 and out.strip() else 'master'
    rc, _, _, _ = run(['git', 'checkout', f'origin/{default}', '--force'],
                     cwd=repo, timeout=60)
    return rc == 0


def get_head_date(repo):
    rc, out, _, _ = run(['git', 'show', '-s', '--format=%cs', 'HEAD'], cwd=repo, timeout=10)
    return out.strip() if rc == 0 else None


def parse_carmack_output(output: str) -> list[dict]:
    """Parse forge --carmack output to extract file rankings.

    forge prints lines like:
       1  some/file.py  score=0.523
       2  other/file.py score=0.487
    """
    files = []
    # Try a few patterns to be robust
    for line in output.splitlines():
        # Pattern: "rank  file  score=N.NNN"
        m = re.match(r'\s*(\d+)\s+(\S+\.py)\s+score=([\d.]+)', line)
        if m:
            files.append({'rank': int(m.group(1)), 'file': m.group(2), 'score': float(m.group(3))})
            continue
        # Alternative pattern from carmack output
        m = re.match(r'\s*\d+\s+(\S+\.py)\s+', line)
        if m:
            files.append({'rank': len(files) + 1, 'file': m.group(1), 'score': 0})
    return files


def run_carmack(forge_path: str, repo: Path, weeks_from: str | None) -> tuple[int, str, str, float]:
    """Run forge --carmack with optional --weeks-from. Output as carmack_full json
    via JSON output flag? No — parse text. Or use _json mode if exists."""
    cmd = [PYTHON, forge_path, '--carmack', '--weeks', '52']
    if weeks_from:
        cmd.extend(['--weeks-from', weeks_from])
    return run(cmd, cwd=repo, timeout=180)


def find_rank_of_target(output: str, target: str) -> int | None:
    """Find rank of target file in carmack output.

    Forge --carmack output format:
      0.602  lib/ansible/module_utils/facts/hardware/linux.py
           Kalman=0.00 ...
      0.602  lib/ansible/modules/user.py
           ...

    Lines starting with a float score then file path. Rank = position
    in the listed order (1-based, score-sorted desc).
    """
    rank = 0
    for line in output.splitlines():
        # Match "  0.123  path/to/file.py" — float then .py path
        m = re.match(r'^\s*\d+\.\d+\s+(\S+\.py)\s*$', line)
        if m:
            rank += 1
            f = m.group(1)
            if f == target or f.endswith(target) or target.endswith(f):
                return rank
    return None


def run_one_case(case: dict, forge_path: str, scenario: str) -> dict:
    """Run forge --carmack with given forge_path version on one case."""
    project = case['project']
    bug_id = case['bug_id']
    target = case['change_file']
    repo = CLONES / project
    if not repo.is_dir():
        return {'bug_id': bug_id, 'status': 'NO_CLONE', 'scenario': scenario}

    checkout_head(repo)
    head_date = get_head_date(repo)

    rc, out, err, t = run_carmack(forge_path, repo, weeks_from=None)
    output = out + ('\n--STDERR--\n' + err if err else '')

    # Save verbatim
    d = BENCH / scenario / bug_id
    d.mkdir(parents=True, exist_ok=True)
    (d / 'output.txt').write_text(output)

    rank = find_rank_of_target(output, target)

    return {
        'bug_id': bug_id, 'project': project, 'target': target,
        'scenario': scenario, 'exit': rc, 'elapsed': round(t, 2),
        'head_date': head_date, 'rank': rank,
        'in_top10': (rank is not None and rank <= 10),
    }


def main():
    BENCH.mkdir(exist_ok=True)
    print(f'Cycle 24C — benchmark v2.1.0 vs cycle 24 candidate on panel_reference')
    print(f'Cases: {len(PANEL)}\n')

    results = {'v210_baseline': [], 'v220_candidate': []}

    for case in PANEL:
        print(f'\n[{case["bug_id"]}]', flush=True)
        for scenario, fpath in [('v210_baseline', FORGE_V210),
                                  ('v220_candidate', FORGE_V220)]:
            r = run_one_case(case, fpath, scenario)
            results[scenario].append(r)
            rank = r.get('rank')
            print(f'  {scenario:18s} exit={r.get("exit")} rank={rank} top10={r.get("in_top10")} elapsed={r.get("elapsed", 0)}s', flush=True)

    # Aggregate
    def metrics(results_list):
        n_ranked = sum(1 for r in results_list if r.get('rank') is not None)
        n_top10 = sum(1 for r in results_list if r.get('in_top10'))
        ranks_present = [r['rank'] for r in results_list if r.get('rank') is not None]
        mrr = sum(1.0 / r for r in ranks_present) / max(len(ranks_present), 1) if ranks_present else 0.0
        return {
            'n_total': len(results_list),
            'n_ranked': n_ranked,
            'n_top10': n_top10,
            'p_at_10_pct': 100 * n_top10 / max(len(results_list), 1),
            'mrr': round(mrr, 4),
        }

    m_baseline = metrics(results['v210_baseline'])
    m_candidate = metrics(results['v220_candidate'])
    delta_p10 = m_candidate['p_at_10_pct'] - m_baseline['p_at_10_pct']
    delta_mrr = m_candidate['mrr'] - m_baseline['mrr']

    print(f'\n=== AGGREGATE ===')
    print(f'BASELINE v2.1.0:    p@10 = {m_baseline["p_at_10_pct"]:.1f}% ({m_baseline["n_top10"]}/{m_baseline["n_total"]}), MRR = {m_baseline["mrr"]:.4f}')
    print(f'CANDIDATE v2.2.0:   p@10 = {m_candidate["p_at_10_pct"]:.1f}% ({m_candidate["n_top10"]}/{m_candidate["n_total"]}), MRR = {m_candidate["mrr"]:.4f}')
    print(f'DELTA:              p@10 = {delta_p10:+.1f} pts, MRR = {delta_mrr:+.4f}')

    if delta_p10 >= 5:
        verdict = 'VALIDATED'
    elif delta_p10 <= -2:
        verdict = 'REJECTED'
    else:
        verdict = 'NEUTRAL'
    print(f'\nVerdict: {verdict}')

    summary = {
        'cycle': '24C',
        'baseline': m_baseline,
        'candidate': m_candidate,
        'delta_p10_pts': round(delta_p10, 2),
        'delta_mrr': round(delta_mrr, 4),
        'verdict': verdict,
        'thresholds': {'validated': '≥+5', 'rejected': '≤-2', 'neutral': 'else'},
        'results': results,
    }
    (ROOT / 'cycle24c_benchmark_summary.json').write_text(json.dumps(summary, indent=2))
    print(f'\nSaved cycle24c_benchmark_summary.json')


if __name__ == '__main__':
    main()
