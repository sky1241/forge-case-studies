#!/usr/bin/env python3
"""Phase A v5 (cycle 14 light) — Run forge on 180 panel cases.

Light version per sky-master brief:
- carmack (Python direct + CLI verbatim)
- modularity (CLI)
- predict (CLI)
- fast-deep (CLI)
- PAS de --locate (40% skip already observed, not in criteria)
- PAS de --shield (timeout 1800s, not in criteria)

Per case: PRE_BUG = bug_date - 4 weeks, checkout, run 4 sub-cmds,
save verbatim outputs in bench_v5/results/{bucket}/{bug_id}/*.txt
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
BUGSINPY = CLONES / 'BugsInPy'
BENCH = ROOT / 'bench_v5' / 'results'
BENCH.mkdir(parents=True, exist_ok=True)
FORGE_BIN = '/home/sky/Bureau/forge/.venv/bin/forge'


def run(cmd, cwd=None, timeout=600):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def get_buggy_commit(case: dict) -> str | None:
    """Lookup buggy_commit_id from BugsInPy bug.info."""
    proj = case['project']
    bug_n = case['bug_id'].split('-')[1]
    bug_info = BUGSINPY / 'projects' / proj / 'bugs' / bug_n / 'bug.info'
    if not bug_info.exists():
        return None
    text = bug_info.read_text()
    m = re.search(r'buggy_commit_id="([^"]+)"', text)
    return m.group(1) if m else None


def clone_full(github_url: str, project_name: str) -> Path:
    target = CLONES / project_name
    if target.exists() and (target / '.git').exists():
        run(['git', 'reset', '--hard'], cwd=target, timeout=60)
        for b in ('main', 'master', 'develop'):
            if run(['git', 'checkout', b], cwd=target, timeout=30).returncode == 0:
                break
        return target
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
    cutoff = (bug_dt - timedelta(weeks=4)).strftime('%Y-%m-%d')
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


def process_case(case: dict, panel: str) -> dict:
    bug_id = case['bug_id']
    bucket = case['bucket']
    project = case['project']
    print(f"\n=== {bug_id} ({bucket}, {panel}) ===", flush=True)

    out_dir = BENCH / bucket / bug_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = dict(case)
    out['panel'] = panel
    out['status'] = 'pending'

    try:
        buggy = get_buggy_commit(case)
        if not buggy:
            out['status'] = 'skip'; out['skip_reason'] = 'bug_info_missing'
            return out
        out['buggy_commit'] = buggy

        repo = clone_full(case['github_url'], project)
        bug_iso, cutoff, pre_bug = compute_pre_bug(repo, buggy)
        out['bug_date'] = bug_iso
        out['cutoff_date'] = cutoff
        out['pre_bug_commit'] = pre_bug
        print(f"  PRE_BUG={pre_bug[:8]} cutoff={cutoff}", flush=True)
        run(['git', 'checkout', '-q', pre_bug], cwd=repo, timeout=60)

        if not (repo / case['change_file']).is_file():
            out['status'] = 'skip'
            out['skip_reason'] = 'file_missing_at_pre'
            print(f"  SKIP file_missing_at_pre", flush=True)
            return out

        # === carmack (Python direct, full rank, v1.3.0rc2 cold-start) ===
        print(f"  carmack...", end='', flush=True)
        results_c = forge.predict_carmack(repo, weeks=999)
        if not results_c:
            out['status'] = 'skip'; out['skip_reason'] = 'forge_crashed'
            print(' CRASHED', flush=True)
            return out
        out['total_files'] = len(results_c)
        out['rank_carmack'] = find_rank(results_c, case['change_file'])
        target_data = next((r for r in results_c if r['file'] == case['change_file']), None)
        if target_data:
            out['regime'] = target_data.get('cold_start_regime', '?')
            out['complexity'] = target_data.get('complexity', 0.0)
        (out_dir / 'carmack_full.json').write_text(json.dumps({
            'bug_id': bug_id, 'change_file': case['change_file'],
            'total_files': len(results_c), 'results': results_c,
        }, indent=2))
        print(f" rank={out['rank_carmack']}/{out['total_files']} regime={out.get('regime', '?')}", flush=True)

        # === carmack CLI ===
        r = run([FORGE_BIN, '--carmack', '--weeks', '999', '.'], cwd=repo, timeout=300)
        (out_dir / 'carmack.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)

        # === modularity ===
        r = run([FORGE_BIN, '--modularity', '.'], cwd=repo, timeout=180)
        (out_dir / 'modularity.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)
        out['q_modularity'] = parse_q(r.stdout)

        # === predict ===
        r = run([FORGE_BIN, '--predict', '--weeks', '999', '.'], cwd=repo, timeout=300)
        (out_dir / 'predict.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)
        rank_p, total_p = parse_predict_rank(r.stdout, case['change_file'])
        out['rank_predict_cli'] = rank_p
        out['predict_shown_n'] = total_p

        # === fast-deep ===
        r = run([FORGE_BIN, '--fast-deep', '.'], cwd=repo, timeout=180)
        (out_dir / 'fastdeep.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)
        out['fastdeep_exit'] = r.returncode

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

    panel_file = 'panel_train_seed48.json' if panel == 'train' else 'panel_holdout_seed49.json'
    cases = json.loads((ROOT / panel_file).read_text())
    print(f"Phase A v5 — {panel.upper()} panel: {len(cases)} cases [start={start}, end={end}]\n", flush=True)

    out_file = ROOT / f'results_v5_{panel}.jsonl'
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
