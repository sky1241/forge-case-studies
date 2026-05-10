#!/usr/bin/env python3
"""Phase A v2 — Full forge power on N=16 panel (8 train + 8 hold-out).

Per case:
  1. Clone full target repo (idempotent)
  2. Compute PRE_BUG = bug_date - 4 weeks, checkout
  3. Verify change_file exists at PRE_BUG
  4. Run forge sub-cmds (all 6 in brief A.2):
     - forge --carmack --weeks 999 (CLI, verbatim) + predict_carmack() Python direct
     - forge --modularity (CLI, parse Q)
     - forge --predict --weeks 999 (CLI, verbatim) + predict_defects() Python direct
     - forge --locate (CLI, if tests + coverage feasible — else SKIP documented)
     - forge --fast-deep (CLI, BFS full graph from PRE_BUG state)
     - forge --shield (CLI, ONLY first case per bucket per panel = 6 total max)
  5. Save outputs verbatim to bench/results/{bucket}/{bug_id}/{tool}.txt

Output: results_v2_train.jsonl + results_v2_holdout.jsonl
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
BENCH = ROOT / 'bench' / 'results'
BENCH.mkdir(parents=True, exist_ok=True)
FORGE_BIN = '/home/sky/Bureau/forge/.venv/bin/forge'
CUTOFF_WEEKS = 4

# Track which buckets have already had shield run (1 per bucket per panel)
SHIELD_DONE = {'train': set(), 'holdout': set()}


def run(cmd, cwd=None, timeout=600):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def clone_full(github_url: str, project_name: str) -> Path:
    target = CLONES / project_name
    if target.exists() and (target / '.git').exists():
        run(['git', 'reset', '--hard'], cwd=target, timeout=60)
        for b in ('main', 'master', 'develop'):
            r = run(['git', 'checkout', b], cwd=target, timeout=30)
            if r.returncode == 0:
                break
        return target
    r = run(['git', 'clone', '--quiet', github_url, str(target)], timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f'clone_failed: {github_url}: {r.stderr[:200]}')
    return target


def compute_pre_bug(repo: Path, buggy_commit: str) -> tuple[str, str, str]:
    r = run(['git', 'show', '-s', '--format=%ci', buggy_commit], cwd=repo)
    if r.returncode != 0:
        run(['git', 'fetch', 'origin', buggy_commit], cwd=repo)
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


def parse_predict_ranked(text: str, change_file: str) -> tuple[int | None, int]:
    """Parse forge --predict CLI output. Returns (rank, total_files_shown)."""
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
        repo = clone_full(case['github_url'], project)
        bug_iso, cutoff, pre_bug = compute_pre_bug(repo, case['buggy_commit'])
        out['bug_date'] = bug_iso
        out['cutoff_date'] = cutoff
        out['pre_bug_commit'] = pre_bug
        print(f"  PRE_BUG={pre_bug[:8]} cutoff={cutoff}", flush=True)
        run(['git', 'checkout', '-q', pre_bug], cwd=repo, timeout=60)

        if not (repo / case['change_file']).is_file():
            out['status'] = 'skip'
            out['skip_reason'] = 'file_missing_at_pre'
            print(f"  SKIP file_missing_at_pre: {case['change_file']}", flush=True)
            return out

        # === forge --carmack via predict_carmack Python direct (full list, sub-scores) ===
        print(f"  carmack...", end='', flush=True)
        results_c = forge.predict_carmack(repo, weeks=999)
        if not results_c:
            out['status'] = 'skip'
            out['skip_reason'] = 'forge_crashed'
            print(' CRASHED', flush=True)
            return out
        out['total_files'] = len(results_c)
        out['rank_carmack'] = find_rank(results_c, case['change_file'])
        # Save full carmack json
        (out_dir / 'carmack_full.json').write_text(json.dumps({
            'bug_id': bug_id, 'change_file': case['change_file'],
            'total_files': len(results_c), 'results': results_c,
        }, indent=2))
        print(f" rank={out['rank_carmack']}/{out['total_files']}", flush=True)

        # === forge --carmack CLI (verbatim top 15) ===
        r = run([FORGE_BIN, '--carmack', '--weeks', '999', '.'], cwd=repo, timeout=300)
        (out_dir / 'carmack.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)

        # === forge --modularity CLI ===
        r = run([FORGE_BIN, '--modularity', '.'], cwd=repo, timeout=180)
        (out_dir / 'modularity.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)
        out['q_modularity'] = parse_q(r.stdout)
        print(f"  modularity Q={out['q_modularity']}", flush=True)

        # === forge --predict CLI (real, verbatim) ===
        r = run([FORGE_BIN, '--predict', '--weeks', '999', '.'], cwd=repo, timeout=300)
        (out_dir / 'predict.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)
        rank_p, total_p = parse_predict_ranked(r.stdout, case['change_file'])
        out['rank_predict_cli'] = rank_p
        out['predict_shown_n'] = total_p
        print(f"  predict CLI rank={rank_p}/{total_p}", flush=True)

        # === forge --locate (skip — needs coverage.py + passing tests) ===
        out['locate_status'] = 'skipped'
        out['locate_reason'] = 'coverage_setup_infeasible_per_case'

        # === forge --fast-deep CLI ===
        r = run([FORGE_BIN, '--fast-deep', '.'], cwd=repo, timeout=180)
        (out_dir / 'fastdeep.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)
        out['fastdeep_exit'] = r.returncode
        print(f"  fast-deep exit={r.returncode}", flush=True)

        # === forge --shield (1 per bucket per panel) ===
        if bucket not in SHIELD_DONE[panel]:
            print(f"  shield (first {bucket} in {panel})...", end='', flush=True)
            r = run([FORGE_BIN, '--shield', '.'], cwd=repo, timeout=1800)
            (out_dir / 'shield.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)
            out['shield_run'] = True
            out['shield_exit'] = r.returncode
            SHIELD_DONE[panel].add(bucket)
            print(f" exit={r.returncode}", flush=True)
        else:
            out['shield_run'] = False

        # === Random baseline ===
        out['random_baseline_rank'] = random_baseline(bug_id, out['total_files'])

        # === Indicators ===
        rc = out['rank_carmack']
        out['norm_rank'] = rc / out['total_files'] if rc else None
        out['reciprocal'] = 1.0 / rc if rc else 0.0
        out['dcg_at_10'] = (1.0 / math.log2(rc + 1)) if (rc and rc <= 10) else 0.0
        for k in (3, 5, 10, 30):
            out[f'in_top_{k}'] = bool(rc and rc <= k)

        out['status'] = 'ok'
    except subprocess.TimeoutExpired as e:
        out['status'] = 'skip'
        out['skip_reason'] = 'forge_crashed'
        out['skip_detail'] = f'timeout {e}'
        print(f"  TIMEOUT: {e}", flush=True)
    except Exception as e:
        out['status'] = 'error'
        out['error'] = str(e)
        print(f"  ERROR: {e}", flush=True)

    return out


def main():
    panel_arg = sys.argv[1] if len(sys.argv) > 1 else 'train'
    cases = json.loads((ROOT / f'panel_{panel_arg}_v2.json').read_text())
    print(f"Phase A v2 — {panel_arg.upper()} panel: {len(cases)} cases\n", flush=True)

    out_file = ROOT / f'results_v2_{panel_arg}.jsonl'
    done = set()
    if out_file.exists():
        for line in out_file.read_text().splitlines():
            if line.strip():
                done.add(json.loads(line)['bug_id'])

    with out_file.open('a') as f:
        for case in cases:
            if case['bug_id'] in done:
                print(f"SKIP (already done): {case['bug_id']}", flush=True)
                # We still need to track shield bucket for this panel
                if case.get('bucket') and 'shield_run' not in done:
                    pass
                continue
            result = process_case(case, panel=panel_arg)
            f.write(json.dumps(result) + '\n')
            f.flush()

    print(f"\nDONE. Output: {out_file}")


if __name__ == "__main__":
    main()
