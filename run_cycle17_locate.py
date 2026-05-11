#!/usr/bin/env python3
"""Cycle 17 — forge --locate à scale, mesure success ratio.

For each case:
1. Clone repo, checkout PRE_BUG
2. Try pip install -e .[test] + pytest-cov + coverage run
3. forge --locate
4. Mesure: success (locate produit output ranking) ou skip (reason)
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
CLONES = ROOT / 'clones'
BUGSINPY = CLONES / 'BugsInPy'
BENCH = ROOT / 'bench_v17' / 'results'
BENCH.mkdir(parents=True, exist_ok=True)
FORGE_BIN = '/home/sky/Bureau/forge/.venv/bin/forge'
FORGE_PY = '/home/sky/Bureau/forge/.venv/bin/python'


def run(cmd, cwd=None, timeout=300):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def get_buggy(case):
    proj = case['project']
    bug_n = case['bug_id'].split('-')[1]
    bug_info = BUGSINPY / 'projects' / proj / 'bugs' / bug_n / 'bug.info'
    if not bug_info.exists():
        return None
    m = re.search(r'buggy_commit_id="([^"]+)"', bug_info.read_text())
    return m.group(1) if m else None


def clone_repo(url, name):
    target = CLONES / name
    if target.exists() and (target / '.git').exists():
        run(['git', 'reset', '--hard'], cwd=target, timeout=60)
        for b in ('main', 'master', 'develop'):
            if run(['git', 'checkout', b], cwd=target, timeout=30).returncode == 0:
                break
        return target
    r = run(['git', 'clone', '--quiet', url, str(target)], timeout=600)
    return target if r.returncode == 0 else None


def compute_pre_bug(repo, buggy):
    r = run(['git', 'show', '-s', '--format=%ci', buggy], cwd=repo)
    if r.returncode != 0:
        run(['git', 'fetch', 'origin', buggy], cwd=repo, timeout=120)
        r = run(['git', 'show', '-s', '--format=%ci', buggy], cwd=repo)
        if r.returncode != 0:
            return None
    bug_dt = datetime.strptime(r.stdout.strip()[:10], '%Y-%m-%d')
    cutoff = (bug_dt - timedelta(weeks=4)).strftime('%Y-%m-%d')
    r = run(['git', 'rev-list', '-n', '1', f'--before={cutoff}', buggy], cwd=repo)
    return r.stdout.strip() or None


def process_case(case, panel):
    bug_id = case['bug_id']
    out_dir = BENCH / panel / bug_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = dict(case); out['panel'] = panel; out['status'] = 'pending'
    print(f"\n=== {bug_id} ({panel}) ===", flush=True)
    try:
        buggy = get_buggy(case)
        if not buggy:
            out['status'] = 'skip'; out['skip_reason'] = 'bug_info_missing'
            return out
        repo = clone_repo(case['github_url'], case['project'])
        if not repo:
            out['status'] = 'skip'; out['skip_reason'] = 'clone_failed'
            return out
        pre_bug = compute_pre_bug(repo, buggy)
        if not pre_bug:
            out['status'] = 'skip'; out['skip_reason'] = 'shallow_history'
            return out
        run(['git', 'checkout', '-q', pre_bug], cwd=repo, timeout=60)
        if not (repo / case['change_file']).is_file():
            out['status'] = 'skip'; out['skip_reason'] = 'file_missing_at_pre'
            return out

        # Try pip install -e .
        r = run([FORGE_PY, '-m', 'pip', 'install', '-e', '.', '--quiet'], cwd=repo, timeout=180)
        (out_dir / 'pip_install.log').write_text(f'exit={r.returncode}\n--- stdout ---\n{r.stdout}\n--- stderr ---\n{r.stderr}')
        out['pip_exit'] = r.returncode
        if r.returncode != 0:
            r2 = run([FORGE_PY, '-m', 'pip', 'install', '-e', '.[test]', '--quiet'], cwd=repo, timeout=180)
            with (out_dir / 'pip_install.log').open('a') as f:
                f.write(f'\n--- retry .[test] ---\nexit={r2.returncode}\n{r2.stderr}')
            out['pip_exit'] = r2.returncode
            if r2.returncode != 0:
                out['status'] = 'skip'; out['skip_reason'] = 'pip_install_failed'
                return out

        # pytest + coverage
        run([FORGE_PY, '-m', 'pip', 'install', 'pytest-cov', 'coverage', '--quiet'], cwd=repo, timeout=120)
        r = run([FORGE_PY, '-m', 'coverage', 'run', '-m', 'pytest', 'tests/', '-x', '--tb=no'], cwd=repo, timeout=300)
        (out_dir / 'pytest_cov.log').write_text(f'exit={r.returncode}\n--- stdout (last 50 lines) ---\n{r.stdout[-3000:]}\n--- stderr ---\n{r.stderr[-1500:]}')
        if r.returncode != 0 and not (repo / '.coverage').exists():
            out['status'] = 'skip'; out['skip_reason'] = 'pytest_collect_failed'
            return out

        # forge --locate
        r = run([FORGE_BIN, '--locate', '.'], cwd=repo, timeout=180)
        (out_dir / 'locate.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)
        out['locate_exit'] = r.returncode
        # Parse rank of change_file in locate output
        files = []
        for line in r.stdout.splitlines():
            m = re.match(r'\s+\d+\.\d+\s+(\S+\.py)', line)
            if m: files.append(m.group(1))
        rank = next((i+1 for i, f in enumerate(files) if f == case['change_file']), None)
        out['rank_locate'] = rank
        out['total_files_locate'] = len(files)
        out['in_top30'] = bool(rank and rank <= 30)
        out['status'] = 'ok'
        print(f"  locate rank={rank}/{len(files)} top30={out['in_top30']}", flush=True)
    except subprocess.TimeoutExpired:
        out['status'] = 'skip'; out['skip_reason'] = 'timeout'
    except Exception as e:
        out['status'] = 'error'; out['error'] = str(e)
        print(f"  ERROR: {e}", flush=True)
    return out


def main():
    panel = sys.argv[1] if len(sys.argv) > 1 else 'train'
    start = 0; end = 9999
    for i, arg in enumerate(sys.argv):
        if arg == '--start': start = int(sys.argv[i+1])
        if arg == '--end': end = int(sys.argv[i+1])
    pf = f'panel_train_seed54.json' if panel == 'train' else 'panel_holdout_seed55.json'
    cases = json.loads((ROOT / pf).read_text())
    out_file = ROOT / f'results_v17_{panel}.jsonl'
    done = set()
    if out_file.exists():
        for l in out_file.read_text().splitlines():
            if l.strip(): done.add(json.loads(l)['bug_id'])
    with out_file.open('a') as f:
        for i, case in enumerate(cases):
            if i < start or i >= end: continue
            if case['bug_id'] in done:
                print(f"SKIP (done): {case['bug_id']}", flush=True)
                continue
            f.write(json.dumps(process_case(case, panel)) + '\n')
            f.flush()
    print(f"\nDONE.")


if __name__ == "__main__":
    main()
