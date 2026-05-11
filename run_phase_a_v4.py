#!/usr/bin/env python3
"""Phase A v3 — Full forge power on 48 cases, verbatim outputs by case.

Per-case full pipeline:
  1. Clone full target repo (idempotent)
  2. PRE_BUG = bug_date - 4 weeks, checkout
  3. Verify change_file exists at PRE_BUG
  4. Run forge sub-cmds, save verbatim in bench_v4/results/{bucket}/{bug_id}/:
     - carmack.txt (CLI) + carmack_full.json (Python direct, no top-15 trunc)
     - modularity.txt (parse Q)
     - predict.txt (CLI)
     - fastdeep.txt (CLI, with PRE_BUG_MINUS_1WEEK SHA if avail)
     - locate.txt + pip_install.log + pytest_cov.log (REAL setup)
       OR locate_skip_reason.md if setup fails (exit codes verbatim)
     - shield.txt (CLI, all 50 cases per cycle 12 brief — not 1/bucket)

Output: results_v4_<panel>.jsonl
Commits: per 5 cases done (script writes flag file, manual git commit between batches).

Usage: python3 run_phase_a_v3.py <train|holdout> [--start N --end N]
"""
import json
import math
import random
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/home/sky/Bureau/forge')
import forge

ROOT = Path('/home/sky/forge-case-studies')
CLONES = ROOT / 'clones'
CLONES_TMP = ROOT / 'clones_tmp_v2'  # reuse v2 cache for small projects
BENCH = ROOT / 'bench_v4' / 'results'
BENCH.mkdir(parents=True, exist_ok=True)
FORGE_BIN = '/home/sky/Bureau/forge/.venv/bin/forge'
FORGE_PYTHON = '/home/sky/Bureau/forge/.venv/bin/python'
CUTOFF_WEEKS = 4


def run(cmd, cwd=None, timeout=600, env=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


def clone_full(github_url: str, project_name: str) -> Path:
    # Try main repo cache first (BugsInPy projects), then small_v2 cache
    for parent in (CLONES, CLONES_TMP):
        target = parent / project_name
        if target.exists() and (target / '.git').exists():
            run(['git', 'reset', '--hard'], cwd=target, timeout=60)
            for b in ('main', 'master', 'develop'):
                if run(['git', 'checkout', b], cwd=target, timeout=30).returncode == 0:
                    break
            return target
    # Not cached: clone into CLONES
    target = CLONES / project_name
    r = run(['git', 'clone', '--quiet', github_url, str(target)], timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f'clone_failed: {github_url}: {r.stderr[:200]}')
    return target


def compute_pre_bug(repo: Path, buggy_commit: str) -> tuple[str, str, str]:
    r = run(['git', 'show', '-s', '--format=%ci', buggy_commit], cwd=repo)
    if r.returncode != 0:
        run(['git', 'fetch', 'origin', buggy_commit], cwd=repo, timeout=120)
        r = run(['git', 'show', '-s', '--format=%ci', buggy_commit], cwd=repo)
        if r.returncode != 0:
            raise RuntimeError(f'bug_commit_missing: {buggy_commit}')
    bug_iso = r.stdout.strip()
    bug_dt = datetime.strptime(bug_iso[:10], '%Y-%m-%d')
    cutoff = (bug_dt - timedelta(weeks=CUTOFF_WEEKS)).strftime('%Y-%m-%d')
    r = run(['git', 'rev-list', '-n', '1', f'--before={cutoff}', buggy_commit], cwd=repo)
    pre = r.stdout.strip()
    if not pre:
        raise RuntimeError('shallow_history')
    return bug_iso, cutoff, pre


def find_rank(results: list, change_file: str) -> int | None:
    for i, r in enumerate(results, start=1):
        if r['file'] == change_file:
            return i
    return None


def parse_q(text: str) -> float | None:
    m = re.search(r'Q\s*=\s*([0-9.]+)', text)
    return float(m.group(1)) if m else None


def parse_predict_rank(text: str, change_file: str) -> tuple[int | None, int]:
    files = []
    for line in text.splitlines():
        m = re.match(r'\s+\d+\.\d+\s+(\S+\.py)', line)
        if m:
            files.append(m.group(1))
    rank = None
    for i, f in enumerate(files, start=1):
        if f == change_file:
            rank = i
            break
    return rank, len(files)


def random_baseline(bug_id: str, total: int) -> int:
    rng = random.Random(hash(bug_id) & 0xFFFFFFFF)
    return rng.randint(1, max(total, 1))


def setup_coverage_and_locate(repo: Path, out_dir: Path) -> dict:
    """Try to install deps + run pytest with coverage, then forge --locate.
    Returns dict with status: ok | skip + reason.
    """
    pip_log = out_dir / 'pip_install.log'
    pytest_log = out_dir / 'pytest_cov.log'
    locate_log = out_dir / 'locate.txt'
    skip_md = out_dir / 'locate_skip_reason.md'

    # Step 1: pip install -e .[test] or .[dev] or just .
    r = run([FORGE_PYTHON, '-m', 'pip', 'install', '-e', '.', '--quiet'], cwd=repo, timeout=300)
    pip_log.write_text(f"=== pip install -e . ===\nexit={r.returncode}\n--- stdout ---\n{r.stdout}\n--- stderr ---\n{r.stderr}\n")
    if r.returncode != 0:
        # Try with [test] extra
        r2 = run([FORGE_PYTHON, '-m', 'pip', 'install', '-e', '.[test]', '--quiet'], cwd=repo, timeout=300)
        with pip_log.open('a') as f:
            f.write(f"\n=== pip install -e .[test] (retry) ===\nexit={r2.returncode}\n--- stdout ---\n{r2.stdout}\n--- stderr ---\n{r2.stderr}\n")
        if r2.returncode != 0:
            skip_md.write_text(f"## locate skip — pip_install_failed\n\n"
                              f"pip install -e . exit code: {r.returncode}\n"
                              f"pip install -e .[test] exit code: {r2.returncode}\n\n"
                              f"### Last 30 lines of pip output (stderr):\n```\n"
                              f"{(r.stderr or '')[-1500:]}\n```\n")
            return {'status': 'skip', 'reason': 'pip_install_failed'}

    # Step 2: install pytest-cov + coverage
    r = run([FORGE_PYTHON, '-m', 'pip', 'install', 'pytest-cov', 'coverage', '--quiet'], cwd=repo, timeout=180)
    with pip_log.open('a') as f:
        f.write(f"\n=== pip install pytest-cov coverage ===\nexit={r.returncode}\n")

    # Step 3: run pytest with coverage
    r = run([FORGE_PYTHON, '-m', 'coverage', 'run', '-m', 'pytest', 'tests/', '-x', '--tb=no'], cwd=repo, timeout=600)
    pytest_log.write_text(f"=== coverage run -m pytest tests/ -x ===\nexit={r.returncode}\n--- stdout ---\n{r.stdout}\n--- stderr ---\n{r.stderr}\n")
    if r.returncode != 0 and not (repo / '.coverage').exists():
        skip_md.write_text(f"## locate skip — pytest_collect_failed\n\n"
                          f"coverage run -m pytest tests/ -x exit code: {r.returncode}\n\n"
                          f"### Last 30 lines of pytest output:\n```\n"
                          f"{(r.stdout + r.stderr)[-1500:]}\n```\n")
        return {'status': 'skip', 'reason': 'pytest_collect_failed'}

    # Step 4: forge --locate
    r = run([FORGE_BIN, '--locate', '.'], cwd=repo, timeout=300)
    locate_log.write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)
    return {'status': 'ok', 'exit': r.returncode}


def process_case(case: dict, panel: str) -> dict:
    bug_id = case['bug_id']
    bucket = case['bucket']
    project = case['project']
    print(f"\n=== {bug_id} ({bucket}, {panel}) ===", flush=True)

    out_dir = BENCH / bucket / bug_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = dict(case); out['panel'] = panel; out['status'] = 'pending'

    try:
        repo = clone_full(case['github_url'], project)
        bug_iso, cutoff, pre_bug = compute_pre_bug(repo, case['buggy_commit'])
        out['bug_date'] = bug_iso; out['cutoff_date'] = cutoff; out['pre_bug_commit'] = pre_bug
        print(f"  PRE_BUG={pre_bug[:8]} cutoff={cutoff}", flush=True)
        run(['git', 'checkout', '-q', pre_bug], cwd=repo, timeout=60)

        if not (repo / case['change_file']).is_file():
            out['status'] = 'skip'; out['skip_reason'] = 'file_missing_at_pre'
            print(f"  SKIP file_missing_at_pre", flush=True)
            return out

        # === carmack (Python direct for full rank) ===
        print(f"  carmack...", end='', flush=True)
        results_c = forge.predict_carmack(repo, weeks=999)
        if not results_c:
            out['status'] = 'skip'; out['skip_reason'] = 'forge_crashed'
            print(' CRASHED', flush=True)
            return out
        out['total_files'] = len(results_c)
        out['rank_carmack'] = find_rank(results_c, case['change_file'])
        (out_dir / 'carmack_full.json').write_text(json.dumps({
            'bug_id': bug_id, 'change_file': case['change_file'],
            'total_files': len(results_c), 'results': results_c,
        }, indent=2))
        print(f" rank={out['rank_carmack']}/{out['total_files']}", flush=True)

        # carmack CLI (verbatim)
        r = run([FORGE_BIN, '--carmack', '--weeks', '999', '.'], cwd=repo, timeout=300)
        (out_dir / 'carmack.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)

        # === modularity ===
        r = run([FORGE_BIN, '--modularity', '.'], cwd=repo, timeout=180)
        (out_dir / 'modularity.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)
        out['q_modularity'] = parse_q(r.stdout)
        print(f"  Q={out['q_modularity']}", flush=True)

        # === predict ===
        r = run([FORGE_BIN, '--predict', '--weeks', '999', '.'], cwd=repo, timeout=300)
        (out_dir / 'predict.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)
        rank_p, total_p = parse_predict_rank(r.stdout, case['change_file'])
        out['rank_predict_cli'] = rank_p
        out['predict_shown_n'] = total_p
        print(f"  predict rank={rank_p}/{total_p}", flush=True)

        # === fast-deep ===
        r = run([FORGE_BIN, '--fast-deep', '.'], cwd=repo, timeout=180)
        (out_dir / 'fastdeep.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)
        out['fastdeep_exit'] = r.returncode

        # === locate (REAL setup) ===
        loc = setup_coverage_and_locate(repo, out_dir)
        out['locate_status'] = loc['status']
        out['locate_reason'] = loc.get('reason', '')
        print(f"  locate: {loc['status']} {loc.get('reason', '')}", flush=True)

        # === shield (per case, brief cycle 12) ===
        print(f"  shield...", end='', flush=True)
        r = run([FORGE_BIN, '--shield', '.'], cwd=repo, timeout=1800)
        (out_dir / 'shield.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)
        out['shield_exit'] = r.returncode
        print(f" exit={r.returncode}", flush=True)

        # === metrics ===
        out['random_baseline_rank'] = random_baseline(bug_id, out['total_files'])
        rc = out['rank_carmack']
        out['norm_rank'] = rc / out['total_files'] if rc else None
        out['reciprocal'] = 1.0 / rc if rc else 0.0
        out['dcg_at_10'] = (1.0 / math.log2(rc + 1)) if (rc and rc <= 10) else 0.0
        for k in (3, 5, 10, 30):
            out[f'in_top_{k}'] = bool(rc and rc <= k)

        out['status'] = 'ok'

    except subprocess.TimeoutExpired as e:
        out['status'] = 'skip'; out['skip_reason'] = 'forge_crashed'
        out['skip_detail'] = f'timeout {e}'
        print(f"  TIMEOUT: {e}", flush=True)
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

    cases = json.loads((ROOT / f'panel_{panel}_v4.json').read_text())
    print(f"Phase A v3 — {panel.upper()} panel: {len(cases)} cases [start={start}, end={end}]\n", flush=True)

    out_file = ROOT / f'results_v4_{panel}.jsonl'
    done = set()
    if out_file.exists():
        for line in out_file.read_text().splitlines():
            if line.strip():
                done.add(json.loads(line)['bug_id'])

    with out_file.open('a') as f:
        for i, case in enumerate(cases):
            if i < start or i >= end:
                continue
            if case['bug_id'] in done:
                print(f"SKIP (already done): {case['bug_id']}", flush=True)
                continue
            result = process_case(case, panel=panel)
            f.write(json.dumps(result) + '\n')
            f.flush()
    print(f"\nChunk DONE. Output: {out_file}")


if __name__ == "__main__":
    main()
