#!/usr/bin/env python3
"""Cycle 18 v2 — run forge --shield on HEAD actuel des repos (option 18b)."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
CLONES = ROOT / 'clones'
FORGE = '/home/sky/Bureau/forge/forge.py'
BENCH = ROOT / 'bench_v18_v2'
TIMEOUT_SHIELD = 600  # 10 min max per case


def run(cmd, cwd=None, timeout=120):
    """Run cmd, return (exit, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, cwd=cwd, timeout=timeout,
                           capture_output=True, text=True, shell=False)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        return 124, e.stdout or '', e.stderr or ''
    except Exception as e:
        return -1, '', str(e)


def detect_stages_complete(output: str) -> dict:
    """Detect which forge --shield stages ran. Return dict of bool."""
    text = output.lower()
    return {
        'carmack': bool(re.search(r'carmack|6-signal|composite', text)),
        'gen_props': bool(re.search(r'gen.?prop|property|hypothesis', text)),
        'fast_deep': bool(re.search(r'fast.?deep|inverted graph|impact', text)),
    }


def checkout_head(repo_dir: Path) -> tuple[bool, str]:
    """Checkout HEAD actuel (origin/HEAD). Returns (success, info).

    Use git symbolic-ref to find origin/HEAD (more robust than parsing
    `git remote show origin` which needs network)."""
    # Find default branch via symbolic-ref (no network needed)
    rc, out, _ = run(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD', '--short'],
                     cwd=repo_dir, timeout=10)
    if rc == 0 and out.strip():
        default = out.strip().replace('origin/', '')
    else:
        # Fallback: try common defaults
        default = None
        for cand in ['master', 'main', 'devel']:
            rc2, _, _ = run(['git', 'rev-parse', '--verify', f'origin/{cand}'],
                            cwd=repo_dir, timeout=10)
            if rc2 == 0:
                default = cand
                break
        if not default:
            return False, 'no default branch found'

    # Skip fetch — use existing origin/<default> ref in local clone.
    # The point of cycle 18 v2 is testing shield logic on a recent commit,
    # not the bleeding edge. Faster, deterministic, no network surprises.

    # Checkout
    rc, _, err = run(['git', 'checkout', f'origin/{default}', '--force'],
                     cwd=repo_dir, timeout=60)
    if rc != 0:
        return False, f'checkout {default}: {err[:200]}'
    # Get HEAD commit
    rc, out, _ = run(['git', 'rev-parse', '--short', 'HEAD'], cwd=repo_dir, timeout=10)
    return True, f'{default} @ {out.strip()}'


def run_shield(case: dict) -> dict:
    """Run forge --shield on HEAD of one case's project. Return result dict."""
    project = case['project']
    bug_id = case['bug_id']
    bucket = case['bucket']
    repo = CLONES / project
    out_dir = BENCH / 'results' / bucket / bug_id
    out_dir.mkdir(parents=True, exist_ok=True)

    result = {
        'bug_id': bug_id,
        'project': project,
        'bucket': bucket,
        'change_file': case['change_file'],
    }

    if not repo.is_dir():
        result['status'] = 'no_clone'
        return result

    # Checkout HEAD
    ok, info = checkout_head(repo)
    result['checkout'] = info
    if not ok:
        result['status'] = 'checkout_fail'
        return result

    # forge --init (idempotent)
    rc_init, _, _ = run(['python3', FORGE, '--init'], cwd=repo, timeout=120)
    result['init_exit'] = rc_init

    # forge --shield
    rc, stdout, stderr = run(['python3', FORGE, '--shield'],
                              cwd=repo, timeout=TIMEOUT_SHIELD)
    out = (stdout or '') + '\n' + (stderr or '')

    # Save verbatim
    (out_dir / 'shield.txt').write_text(out)

    stages = detect_stages_complete(out)
    stages_complete = all(stages.values())

    result.update({
        'shield_exit': rc,
        'stages_carmack': stages['carmack'],
        'stages_gen_props': stages['gen_props'],
        'stages_fast_deep': stages['fast_deep'],
        'stages_complete': stages_complete,
        'output_chars': len(out),
        'status': 'ok' if rc == 0 else f'exit_{rc}',
    })
    # Save meta
    (out_dir / 'shield_meta.json').write_text(json.dumps(result, indent=2))
    return result


def main():
    panel = json.loads((ROOT / 'panel_reference.json').read_text())
    print(f'Cycle 18 v2 — shield on HEAD actuel ({len(panel)} cas)')
    print(f'Forge: {FORGE}')
    print(f'Bench output: {BENCH}\n')

    BENCH.mkdir(exist_ok=True)
    results = []
    for i, case in enumerate(panel, 1):
        print(f'[{i:2d}/{len(panel)}] {case["bug_id"]:25s}', flush=True, end=' ')
        r = run_shield(case)
        results.append(r)
        flag_complete = 'OK' if r.get('stages_complete') else 'PARTIAL' if r.get('status') == 'ok' else 'FAIL'
        print(f'-> {r.get("status"):15s} stages={flag_complete}', flush=True)
        # Commit incremental every 5 cases
        if i % 5 == 0:
            results_path = ROOT / 'cycle18_v2_results_partial.jsonl'
            with results_path.open('w') as f:
                for r2 in results:
                    f.write(json.dumps(r2) + '\n')
            print(f'  (saved {i} results)', flush=True)

    # Final aggregate
    n_ok = sum(1 for r in results if r.get('status') == 'ok')
    n_complete = sum(1 for r in results if r.get('stages_complete'))
    ratio_complete = 100 * n_complete / len(results)
    print()
    print(f'=== Aggregate ===')
    print(f'  exit=0     : {n_ok}/{len(results)} = {100*n_ok/len(results):.1f}%')
    print(f'  stages_complete : {n_complete}/{len(results)} = {ratio_complete:.1f}%')
    print(f'  Threshold ≥80%')
    print(f'  C_shield_v2 : {"OUI" if ratio_complete >= 80 else "NON"}')

    summary = {
        'cycle': '18_v2',
        'n_total': len(results),
        'n_exit0': n_ok,
        'n_stages_complete': n_complete,
        'ratio_stages_complete': ratio_complete,
        'threshold': 80.0,
        'verdict_c_shield_v2': 'OUI' if ratio_complete >= 80 else 'NON',
        'results': results,
    }
    (ROOT / 'cycle18_v2_summary.json').write_text(json.dumps(summary, indent=2))
    print(f'\nSaved cycle18_v2_summary.json')


if __name__ == '__main__':
    main()
